import math
import os
import random
import json
import pygame

import event_content
from core.camera import Camera
from core.date import GameDate
from core.math_utils import clamp
from core.surfaces import tile_fill
from events import EventRegistry, EventSystem, register_all, date_ordinal
from rendering.map_view import MapRenderer
from systems.buildings import (
    BUILDINGS,
    make_building,
    get_building_id,
    get_building_level,
    building_food_output,
    building_gold_upkeep,
    building_gold_rate_bonus,
    building_piety_rate_bonus,
    building_prestige_rate_bonus,
    building_levy_mult_bonus,
    building_stress_monthly_relief,
    building_max_level,
)
from systems.characters import generate_heir, generate_ruler, generate_spouse
from systems.traits import _stats_list_to_dict, apply_trait_effects, compute_piety_rate, normalize_traits
from ui.layout import Layout
from ui.manager import UIManager
from ui.modal import Modal
from ui.text import wrap_text
from ui.theme import BG_COLOR, FOOTER_FONT
from ui.utils import clip_draw
from world.map import MapWorld


class GameApp:
    def __init__(self):
        os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
        os.environ.setdefault("SDL_VIDEO_WINDOW_POS", "center")
        pygame.init()
        pygame.display.set_caption("CK1-Inspired Grand Strategy UI (Pygame)")
        self.windowed_size = (1280, 720)
        self.screen = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
        self.clock = pygame.time.Clock()

        self.mode = "menu"
        self.save_dir = os.path.join(os.path.dirname(__file__), "saves")
        self.latest_save_path = os.path.join(self.save_dir, "campaign_latest.json")
        self.autosave_path = os.path.join(self.save_dir, "campaign_autosave.json")
        self._autosave_interval_months = 3
        self.storyteller = None
        self._storyteller_start_day = None
        self.realm_select_page = 0
        self.realm_candidate_id = None
        self._realm_ui_rects = []
        self.storytellers = [
            {
                "id": "cassius_classic",
                "name": "Cassius Classic",
                "desc": "Vanilla and fair. A steady cadence of events with no strong bias.",
                "event_chance_mult": 1.0,
                "event_chance_ramp_per_year": 0.0,
                "event_chance_max_mult": 1.0,
            },
            {
                "id": "edgar_extinction",
                "name": "Edgar Extinction",
                "desc": "Harsher events and a rising tempo as the years pass.",
                "event_chance_mult": 1.25,
                "event_chance_ramp_per_year": 0.15,
                "event_chance_max_mult": 2.0,
            }
        ]
        self._storyteller_portraits = self._load_storyteller_portraits()
        self._storyteller_portrait_cache = {}

        self._menu_bg = self._load_menu_background()
        self._menu_bg_cache = {}
        font_path = pygame.font.match_font("arial")
        self.menu_title_font = pygame.font.Font(font_path, 72)
        self.menu_header_font = pygame.font.Font(font_path, 40)
        self.menu_subtitle_font = pygame.font.Font(font_path, 24)
        self.menu_button_font = pygame.font.Font(font_path, 22)
        self.menu_caption_font = pygame.font.Font(font_path, 18)

        self.ui = UIManager(seed=11)
        self.layout = Layout(*self.screen.get_size())
        self._game_bg_cache = {}

        self.world = MapWorld(seed=7, world_size=(3200, 2200), cell_scale=4)
        self.camera = Camera(viewport_size=(100, 100), world_size=(self.world.world_w, self.world.world_h))
        self.map_renderer = MapRenderer(self.world, self.camera)
        self.camera.set_viewport(self._get_map_rect().size)
        self._prov_adj = self.world._build_province_adjacency()

        self.modal = Modal()

        self.date = GameDate(1067, 1, 21)
        self.speed_level = 0  # 0 paused, 1..3 speeds
        self.speed_days_per_sec = {0: 0, 1: 1, 2: 3, 3: 7}
        self._time_accum = 0.0

        self.selected_province = None
        self._building_menu_slot = None
        self.right_panel_open = True
        self._right_panel_anim = 0.0
        self.left_panel_open = False
        self._left_panel_anim = 0.0
        self._left_panel_toggle_rect = None
        self._bottom_bar_rect = None
        self._war_float_rects = []

        # --- EVENTS: minimal integration ---
        self._event_flags = {}
        self._event_pending = []
        self._event_resume_speed = None

        self.event_registry = EventRegistry(seed=123)
        register_all(self.event_registry, event_content)
        self.base_event_daily_chance = 0.05
        self.events = EventSystem(self, self.event_registry, daily_chance=self.base_event_daily_chance, seed=999)

        self.resources = {
            "gold": 200,
            "gold_rate": +1,
            "piety": 1000,
            "prestige": 350,
            "renown": 120,
            "renown_rate": 1,
        }

        # War state (multiple active wars supported)
        self.wars = []
        self._war_next_id = 1
        self._war_focus_id = None
        self._war_border_overlay = None
        self._war_border_overlay_key = None
        self._pending_war = None
        self._war_goal_selecting = False

        # Siege system (CK-style timing)
        self.siege_prep_days = 7
        self.siege_assault_days = 21
        self._siege_state = None
        self._siege_overlay = None
        self._siege_overlay_key = None
        self._siege_stripe_base = None
        self._siege_stripe_base_key = None

        # Enemy AI + morale / stack wipe tuning
        self.enemy_raise_rate = 0.12
        self.ai_engage_ratio = 1.1
        self.ai_avoid_ratio = 0.85
        self.stack_wipe_attacker_morale = 60
        self.stack_wipe_defender_morale = 15
        self.morale_recovery_per_day = 1.5

        # Player character = ruler of player realm
        self.player_realm_id = self.world.player_realm_id
        self.character = self.world.realm_rulers[self.player_realm_id]

        if "base_stats" not in self.character:
            self.character["base_stats"] = _stats_list_to_dict(self.character.get("stats", []))
        apply_trait_effects(self.character)
        self.character["traits"] = normalize_traits(self.character.get("traits", []))
        self.resources["piety_rate"] = compute_piety_rate(self.character)[0]
        self.resources["prestige_rate"] = self._compute_prestige_rate(self.character)

        # CK2-style political layer
        self.realm_relations = {}
        self.realm_claims = set()
        self.realm_truces = {}
        self.claim_fabrication_cooldowns = {}
        self.alliances = set()
        self.subjugation_cooldown_days = 0
        self._init_diplomacy_state()

        # CK3-style character systems
        self.active_schemes = []
        self._next_scheme_id = 1
        self.hooks = {}
        self.lifestyle_focuses = ("diplomacy", "martial", "stewardship", "intrigue", "learning")
        self.lifestyle_focus = "stewardship"
        self.lifestyle_xp = {k: 0.0 for k in self.lifestyle_focuses}
        self.lifestyle_perks = {k: 0 for k in self.lifestyle_focuses}
        self._lifestyle_picker_index = self.lifestyle_focuses.index(self.lifestyle_focus)
        self.stress = 12.0
        self._stress_break_level = 0
        self.dread = 0.0
        self.decision_cooldowns = {}
        self._raid_cooldown_days = 45
        self._ai_war_cooldown_days = 120
        self.resources["piety_rate"] = compute_piety_rate(self.character)[0]
        self.resources["prestige_rate"] = self._compute_prestige_rate(self.character)

        # Approximation: able-bodied levy pool (~12% of total population).
        self.army_pop_ratio = 0.12
        self.army_raise_rate = 0.15  # fraction of max raised per day while mustering
        self.army_move_speed = 110  # world units per day
        self.army = {"raised": 0, "max": 0, "morale": 77}
        self.army_raising = False
        self.army_selected = False
        self.army_pos = None
        self.army_prov_id = None
        self.army_route = []
        self.army_step_from = None
        self.army_step_to = None
        self.army_step_progress = 0.0
        self.army_step_flash = 0.0
        self.army_last_step = None
        self.enemy_armies = []
        self.food = (0, 0)  # (produced, consumed)
        self.food_consumption_per_pop = 0.39  # monthly consumption per person
        self._rebalance_population_to_farms()
        self.population = self.world.total_population_for_realm(self.player_realm_id)
        self._baseline_population = max(1, self.population)
        self.food = self._compute_food_values()
        self.threat = self._compute_threat()
        self._update_army_max()
        self._init_enemy_armies()
        self._campaign_start_provinces = self._player_province_count()
        self._campaign_target_provinces = self._compute_campaign_target_provinces(self._campaign_start_provinces)
        self._insolvency_days = 0
        self._famine_days = 0
        self._crisis_days = 0
        self.campaign_result = None
        self._campaign_over_day = None
        self.last_played_realm_id = self.player_realm_id
        self._recompute_resource_rates()

        self.log = [
            "January 8, 1067: Rumors of usurpation spread in Carinthia.",
            "January 11, 1067: A distant court recognizes new claims.",
            "January 18, 1067: A master of arms returns from pilgrimage.",
        ]

        # map interaction
        self._mouse_down_in_map = False
        self._mouse_down_pos = (0, 0)
        self._mouse_drag_threshold = 5
        self._drag_started = False
        self._prev_mouse_down = False

        self.running = True

        # Start maximized but still resizable.
        self._apply_window_size_desktop()

    def _load_menu_background(self):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "assets"))
        path = os.path.join(base_dir, "boreal_forest.png")
        if os.path.exists(path):
            return pygame.image.load(path).convert()
        return None

    def _load_storyteller_portraits(self):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "storytellers"))
        portraits = {}
        for st in self.storytellers:
            path = os.path.join(base_dir, f"{st['id']}.png")
            if os.path.exists(path):
                portraits[st["id"]] = pygame.image.load(path).convert_alpha()
        return portraits

    def _get_storyteller_portrait(self, storyteller_id, size):
        src = self._storyteller_portraits.get(storyteller_id)
        if src is None:
            return None
        key = (storyteller_id, int(size[0]), int(size[1]))
        cached = self._storyteller_portrait_cache.get(key)
        if cached is not None:
            return cached
        sw, sh = src.get_size()
        if sw <= 0 or sh <= 0:
            return None
        scale = min(size[0] / sw, size[1] / sh)
        new_w = max(1, int(sw * scale))
        new_h = max(1, int(sh * scale))
        scaled = pygame.transform.smoothscale(src, (new_w, new_h))
        self._storyteller_portrait_cache[key] = scaled
        return scaled

    def _get_menu_bg_scaled(self, size):
        if self._menu_bg is None:
            return None, (0, 0)
        cache_key = (int(size[0]), int(size[1]))
        cached = self._menu_bg_cache.get(cache_key)
        if cached is not None:
            return cached
        bg_w, bg_h = self._menu_bg.get_size()
        scale = max(size[0] / bg_w, size[1] / bg_h)
        new_w = max(1, int(bg_w * scale))
        new_h = max(1, int(bg_h * scale))
        scaled = pygame.transform.smoothscale(self._menu_bg, (new_w, new_h))
        offset = ((size[0] - new_w) // 2, (size[1] - new_h) // 2)
        cached = (scaled, offset)
        self._menu_bg_cache[cache_key] = cached
        return cached

    def _draw_menu_background(self, surface):
        size = surface.get_size()
        if self._menu_bg is None:
            surface.fill(BG_COLOR)
            return
        scaled, offset = self._get_menu_bg_scaled(size)
        if scaled is None:
            surface.fill(BG_COLOR)
            return
        surface.blit(scaled, offset)

    def _get_game_bg(self, size):
        key = (int(size[0]), int(size[1]))
        cached = self._game_bg_cache.get(key)
        if cached is not None:
            return cached
        bg = pygame.Surface(size).convert()
        bg.fill(BG_COLOR)
        tile_fill(bg, bg.get_rect(), self.ui.bottom_tile)
        bg.set_alpha(70)
        self._game_bg_cache[key] = bg
        return bg

    def _get_map_rect(self):
        if self.mode in ("realm_select", "game"):
            w, h = self.screen.get_size()
            return pygame.Rect(0, 0, w, h)
        return self.layout.map

    def _get_npc_target(self, rid=None):
        if rid is None:
            if self.selected_province is None:
                return None
            rid = self.selected_province.realm_id
        if rid == self.player_realm_id:
            return None
        if not (0 <= rid < len(self.world.realm_rulers)):
            return None
        ruler = self.world.realm_rulers[rid]
        if not isinstance(ruler, dict):
            return None
        realm_name = None
        if 0 <= rid < len(self.world.realm_names):
            realm_name = self.world.realm_names[rid]
        return {
            "id": rid,
            "name": ruler.get("name", "Ruler"),
            "title": ruler.get("title", "—"),
            "faith": ruler.get("faith", "—"),
            "culture": ruler.get("culture", "—"),
            "traits": ruler.get("traits", []),
            "realm_name": realm_name or "Realm",
        }

    @staticmethod
    def _stat_value(character, key, default=8):
        if not isinstance(character, dict):
            return int(default)
        stats = character.get("stats", [])
        for k, v in stats:
            if k != key:
                continue
            try:
                return int(v)
            except (TypeError, ValueError):
                break
        return int(default)

    def _perk_level(self, focus):
        if not isinstance(getattr(self, "lifestyle_perks", None), dict):
            return 0
        return int(self.lifestyle_perks.get(focus, 0))

    @staticmethod
    def _lifestyle_label(focus):
        labels = {
            "diplomacy": "Diplomacy",
            "martial": "Martial",
            "stewardship": "Stewardship",
            "intrigue": "Intrigue",
            "learning": "Learning",
        }
        return labels.get(str(focus), str(focus).title())

    def _focus_stat_key(self, focus):
        mapping = {
            "diplomacy": "Diplomacy",
            "martial": "Martial",
            "stewardship": "Stewardship",
            "intrigue": "Intrigue",
            "learning": "Learning",
        }
        return mapping.get(focus, "Stewardship")

    @staticmethod
    def _scheme_label(scheme_type):
        labels = {
            "sway": "Sway",
            "claim": "Fabricate Claim",
            "murder": "Murder",
        }
        return labels.get(scheme_type, str(scheme_type).title())

    @staticmethod
    def _scheme_category(scheme_type):
        if scheme_type == "sway":
            return "personal"
        return "hostile"

    @staticmethod
    def _traits_of(character):
        if not isinstance(character, dict):
            return set()
        return set(character.get("traits", []))

    def _compute_prestige_rate(self, character):
        dip = self._stat_value(character, "Diplomacy", default=8)
        martial = self._stat_value(character, "Martial", default=8)
        prowess = self._stat_value(character, "Prowess", default=8)
        rate = int(round((dip + martial + prowess) / 9.0)) - 2
        traits = self._traits_of(character)
        if "proud" in traits:
            rate += 1
        if "humble" in traits:
            rate -= 1
        if "diligent" in traits:
            rate += 1
        if "lazy" in traits:
            rate -= 1
        focus = getattr(self, "lifestyle_focus", None)
        if focus in ("diplomacy", "martial"):
            rate += 1
        rate += max(0, self._perk_level("diplomacy") // 2)
        rate += max(0, self._perk_level("martial") // 3)
        stress_now = float(getattr(self, "stress", 0.0))
        if stress_now >= 200:
            rate -= 3
        elif stress_now >= 100:
            rate -= 1
        return int(clamp(rate, -5, 8))

    def _realm_size(self, rid):
        if hasattr(self.world, "realm_sizes") and 0 <= rid < len(self.world.realm_sizes):
            return max(1, int(self.world.realm_sizes[rid]))
        return max(1, sum(1 for p in self.world.provinces if p.realm_id == rid))

    def _player_province_count(self, rid=None):
        if rid is None:
            rid = self.player_realm_id
        return sum(1 for p in self.world.provinces if p.realm_id == rid)

    def _compute_campaign_target_provinces(self, start_count=None):
        if start_count is None:
            start_count = self._player_province_count()
        start_count = max(1, int(start_count))
        total = max(1, len(self.world.provinces))
        share_target = int(math.ceil(total * 0.22))
        return max(start_count + 1, min(total, max(start_count + 3, share_target)))

    def _campaign_progress_percent(self):
        start = max(1, int(self._campaign_start_provinces))
        target = max(start + 1, int(self._campaign_target_provinces))
        held = self._player_province_count()
        if held <= start:
            return 0
        span = max(1, target - start)
        return int(clamp(round(((held - start) / span) * 100.0), 0, 100))

    @staticmethod
    def _realm_core_name(realm_name):
        if " of " in realm_name:
            return realm_name.split(" of ", 1)[1]
        return realm_name

    def _rank_for_realm(self, rid, gender):
        size = self._realm_size(rid)
        if size >= 3:
            return "King" if gender == "male" else "Queen"
        if size == 2:
            return "Duke" if gender == "male" else "Duchess"
        return "Count" if gender == "male" else "Countess"

    @staticmethod
    def _extract_first_name(display_name):
        titles = {
            "King",
            "Queen",
            "Duke",
            "Duchess",
            "Count",
            "Countess",
            "Prince",
            "Princess",
            "Heir",
            "Baron",
            "Baroness",
        }
        parts = str(display_name).replace(",", " ").split()
        while parts and parts[0] in titles:
            parts = parts[1:]
        if "of" in parts:
            parts = parts[:parts.index("of")]
        if not parts:
            return "Unnamed"
        if len(parts) >= 2:
            return f"{parts[0]} {parts[1]}"
        return parts[0]

    def _get_neighbor_realms(self, rid):
        neighbors = set()
        for pid, prov in enumerate(self.world.provinces):
            if prov.realm_id != rid or pid >= len(self._prov_adj):
                continue
            for nb in self._prov_adj[pid]:
                other = self.world.provinces[nb].realm_id
                if other != rid:
                    neighbors.add(other)
        return neighbors

    def _init_diplomacy_state(self):
        self.realm_relations = {}
        self.realm_claims = set()
        self.realm_truces = {}
        self.claim_fabrication_cooldowns = {}
        self.alliances = set()
        self.subjugation_cooldown_days = 0

        seed = self.world.seed * 1009 + self.player_realm_id * 53
        rnd = random.Random(seed)
        for rid in range(len(self.world.realm_names)):
            if rid == self.player_realm_id:
                continue
            self.realm_relations[rid] = rnd.randint(-30, 25)

        neighbors = list(self._get_neighbor_realms(self.player_realm_id))
        rnd.shuffle(neighbors)
        if neighbors:
            self.realm_claims.add(neighbors[0])
            if len(neighbors) > 1 and rnd.random() < 0.35:
                self.realm_claims.add(neighbors[1])

    def _get_realm_opinion(self, rid):
        try:
            rid = int(rid)
        except (TypeError, ValueError):
            return 0
        return int(self.realm_relations.get(rid, 0))

    def _change_realm_opinion(self, rid, delta):
        try:
            rid = int(rid)
        except (TypeError, ValueError):
            return 0
        cur = self._get_realm_opinion(rid)
        nxt = int(clamp(cur + int(delta), -100, 100))
        self.realm_relations[rid] = nxt
        return nxt

    def _diplomacy_snapshot(self, rid):
        if rid is None or rid == self.player_realm_id:
            return None
        truce = int(self.realm_truces.get(rid, 0))
        claim_cd = int(self.claim_fabrication_cooldowns.get(rid, 0))
        hook = getattr(self, "hooks", {}).get(rid)
        hook_days = int(hook.get("days", 0)) if isinstance(hook, dict) else 0
        hook_strength = hook.get("strength", "none") if isinstance(hook, dict) else "none"
        schemes = [s for s in getattr(self, "active_schemes", []) if s.get("target_id") == rid]
        scheme = schemes[0] if schemes else None
        return {
            "opinion": self._get_realm_opinion(rid),
            "claimed": rid in self.realm_claims,
            "allied": rid in self.alliances,
            "truce_days": truce,
            "claim_cooldown_days": claim_cd,
            "hook_days": hook_days,
            "hook_strength": hook_strength,
            "scheme_name": self._scheme_label(scheme.get("type")) if isinstance(scheme, dict) else None,
            "scheme_progress": float(scheme.get("progress", 0.0)) if isinstance(scheme, dict) else 0.0,
        }

    @staticmethod
    def _days_label(days):
        d = max(0, int(days))
        if d < 365:
            return f"{d}d"
        years = d / 365.0
        return f"{years:.1f}y"

    @staticmethod
    def _decrement_days_map(values):
        for key in list(values.keys()):
            values[key] = int(values[key]) - 1
            if values[key] <= 0:
                values.pop(key, None)

    def _set_lifestyle_focus(self, focus):
        if focus not in self.lifestyle_focuses:
            return False
        if focus == self.lifestyle_focus:
            return False
        self.lifestyle_focus = focus
        self._lifestyle_picker_index = self.lifestyle_focuses.index(focus)
        # Focus swaps are powerful in CK3-like play, so they carry some stress.
        self._adjust_stress(8.0, reason="Changed lifestyle focus")
        self.push_log(f"{self.date}: You adopt a {self._lifestyle_label(focus)} focus.")
        self._recompute_resource_rates()
        return True

    def _lifestyle_xp_threshold(self, focus):
        perks = self._perk_level(focus)
        return 70.0 + 30.0 * perks

    def _tick_lifestyle_day(self):
        focus = self.lifestyle_focus
        stat_key = self._focus_stat_key(focus)
        stat_val = self._stat_value(self.character, stat_key, default=8)
        perk = self._perk_level(focus)

        gain = 0.28 + (stat_val * 0.035) + (perk * 0.01)
        if self.wars and focus == "martial":
            gain += 0.20
        if focus == "intrigue" and any(s.get("type") == "murder" for s in self.active_schemes):
            gain += 0.08
        if focus == "learning" and self.stress >= 120:
            gain += 0.05
        if self.stress >= 220:
            gain *= 0.85

        self.lifestyle_xp[focus] = float(self.lifestyle_xp.get(focus, 0.0)) + max(0.05, gain)
        threshold = self._lifestyle_xp_threshold(focus)
        unlocked = False
        while self.lifestyle_xp[focus] >= threshold:
            self.lifestyle_xp[focus] -= threshold
            self.lifestyle_perks[focus] = self._perk_level(focus) + 1
            self.resources["prestige"] = int(self.resources.get("prestige", 0)) + 20
            self.resources["renown"] = int(self.resources.get("renown", 0)) + 10
            unlocked = True
            self.push_log(
                f"{self.date}: {self._lifestyle_label(focus)} perk unlocked "
                f"(Tier {self._perk_level(focus)})."
            )
            threshold = self._lifestyle_xp_threshold(focus)
        if unlocked:
            self._recompute_resource_rates()

    def _add_hook(self, target_rid, strength="weak", days=365 * 5):
        if target_rid is None:
            return
        strength = "strong" if strength == "strong" else "weak"
        old = self.hooks.get(target_rid)
        if isinstance(old, dict):
            old_strength = old.get("strength", "weak")
            if old_strength == "strong":
                strength = "strong"
            days = max(int(old.get("days", 0)), int(days))
        self.hooks[target_rid] = {
            "strength": strength,
            "days": max(1, int(days)),
        }

    def _consume_hook(self, target_rid):
        hook = self.hooks.get(target_rid)
        if not isinstance(hook, dict):
            return None
        self.hooks.pop(target_rid, None)
        return hook

    def _tick_hooks_day(self):
        for rid in list(self.hooks.keys()):
            entry = self.hooks.get(rid)
            if not isinstance(entry, dict):
                self.hooks.pop(rid, None)
                continue
            entry["days"] = int(entry.get("days", 0)) - 1
            if entry["days"] <= 0:
                self.hooks.pop(rid, None)

    def _active_scheme(self, *, scheme_type=None, target_id=None, category=None):
        for scheme in self.active_schemes:
            if scheme_type is not None and scheme.get("type") != scheme_type:
                continue
            if target_id is not None and scheme.get("target_id") != target_id:
                continue
            if category is not None and scheme.get("category") != category:
                continue
            return scheme
        return None

    def _scheme_speed(self, scheme):
        if not isinstance(scheme, dict):
            return 0.0
        scheme_type = scheme.get("type")
        if scheme_type == "sway":
            stat_key = "Diplomacy"
            focus = "diplomacy"
        elif scheme_type == "claim":
            stat_key = "Learning"
            focus = "learning"
        else:
            stat_key = "Intrigue"
            focus = "intrigue"

        stat = self._stat_value(self.character, stat_key, default=8)
        perk = self._perk_level(focus)
        base = float(scheme.get("base_power", 0.8))
        mult = 0.45 + (stat / 18.0) + (perk * 0.07)
        if self.lifestyle_focus == focus:
            mult += 0.20
        if self.stress >= 200:
            mult *= 0.80
        elif self.stress >= 100:
            mult *= 0.92
        return max(0.10, base * mult)

    def _start_scheme(self, scheme_type, target_rid, *, success_chance, exposure_chance, base_power, min_days=45):
        if target_rid is None or target_rid == self.player_realm_id:
            return False, "Invalid target."
        if self._active_scheme(scheme_type=scheme_type, target_id=target_rid):
            return False, "Scheme already running on this target."

        category = self._scheme_category(scheme_type)
        if self._active_scheme(category=category):
            return False, f"You already have an active {category} scheme."

        scheme = {
            "id": self._next_scheme_id,
            "type": scheme_type,
            "target_id": int(target_rid),
            "category": category,
            "progress": 0.0,
            "days": 0,
            "base_power": float(base_power),
            "success_chance": float(clamp(success_chance, 0.05, 0.95)),
            "exposure_chance": float(clamp(exposure_chance, 0.05, 0.95)),
            "min_days": max(20, int(min_days)),
        }
        self._next_scheme_id += 1
        self.active_schemes.append(scheme)
        return True, "Scheme started."

    def _tick_schemes_day(self):
        if not self.active_schemes:
            return
        finished_ids = []
        for scheme in self.active_schemes:
            scheme["days"] = int(scheme.get("days", 0)) + 1
            scheme["progress"] = float(scheme.get("progress", 0.0)) + self._scheme_speed(scheme)
            if scheme["progress"] >= 100.0 and scheme["days"] >= int(scheme.get("min_days", 20)):
                finished_ids.append(scheme.get("id"))
        if not finished_ids:
            return
        for sid in finished_ids:
            scheme = next((s for s in self.active_schemes if s.get("id") == sid), None)
            if scheme is None:
                continue
            self._resolve_scheme(scheme)
        self.active_schemes = [s for s in self.active_schemes if s.get("id") not in set(finished_ids)]

    def _resolve_scheme(self, scheme):
        if not isinstance(scheme, dict):
            return
        scheme_type = scheme.get("type")
        target_rid = scheme.get("target_id")
        target_name = self._get_war_target_name(target_rid)
        success_roll = self.world.rnd.random()
        success = success_roll < float(scheme.get("success_chance", 0.5))
        exposed = self.world.rnd.random() < float(scheme.get("exposure_chance", 0.35))

        if scheme_type == "sway":
            if success:
                gain = 14 + self.world.rnd.randint(5, 14)
                op = self._change_realm_opinion(target_rid, gain)
                if op >= 55 and self.world.rnd.random() < 0.25:
                    self._add_hook(target_rid, "weak", days=365 * 3)
                    self.push_log(f"{self.date}: You gained a weak hook on {target_name}.")
                self._adjust_stress(-4.0)
                self.push_log(f"{self.date}: Sway scheme succeeded against {target_name} ({op:+d}).")
            else:
                self._change_realm_opinion(target_rid, -7 if exposed else -3)
                self._adjust_stress(3.0)
                self.push_log(f"{self.date}: Sway scheme failed against {target_name}.")
            self._recompute_resource_rates()
            return

        if scheme_type == "claim":
            self.claim_fabrication_cooldowns[target_rid] = max(
                int(self.claim_fabrication_cooldowns.get(target_rid, 0)),
                365,
            )
            if success:
                self.realm_claims.add(target_rid)
                self.resources["prestige"] = int(self.resources.get("prestige", 0)) + 40
                self.resources["renown"] = int(self.resources.get("renown", 0)) + 15
                self._change_realm_opinion(target_rid, -10 if exposed else -4)
                self._adjust_stress(+2.0)
                self.push_log(f"{self.date}: Fabricated claim on {target_name}.")
            else:
                self.resources["prestige"] = max(0, int(self.resources.get("prestige", 0)) - 25)
                self._change_realm_opinion(target_rid, -20 if exposed else -8)
                self._adjust_stress(+6.0)
                self.push_log(f"{self.date}: Claim fabrication failed against {target_name}.")
            self._recompute_resource_rates()
            return

        if scheme_type == "murder":
            if success:
                self._change_realm_opinion(target_rid, -32)
                self.alliances.discard(target_rid)
                self.dread = clamp(float(self.dread) + 24.0, 0.0, 100.0)
                self._adjust_stress(+8.0)
                self._handle_ruler_death(target_rid, "was murdered")
                self.push_log(f"{self.date}: Murder scheme succeeded in {target_name}.")
                if not self.modal.open:
                    self.modal.show(
                        "Murder Scheme Success",
                        [
                            f"You eliminated the ruler of {target_name}.",
                            "Succession upheaval weakens the realm.",
                        ],
                        [
                            ("OK", "accept", lambda: self.modal.close()),
                        ],
                    )
            else:
                self._change_realm_opinion(target_rid, -42 if exposed else -12)
                if exposed:
                    self.resources["prestige"] = max(0, int(self.resources.get("prestige", 0)) - 35)
                self._adjust_stress(+14.0 if exposed else +7.0)
                self.push_log(f"{self.date}: Murder scheme failed in {target_name}.")
            self._recompute_resource_rates()
            return

    def _adjust_stress(self, delta, reason=None):
        old = float(self.stress)
        self.stress = clamp(old + float(delta), 0.0, 300.0)
        if self.stress < (self._stress_break_level * 100) - 10:
            self._stress_break_level = int(self.stress // 100)
        if reason and int(old // 25) != int(self.stress // 25):
            self.push_log(f"{self.date}: Stress {reason.lower()} ({int(round(self.stress))}/300).")
        self._check_stress_break()

    def _daily_stress_delta(self):
        traits = self._traits_of(self.character)
        delta = 0.05
        if self.wars:
            delta += 0.12
        if self.active_schemes:
            delta += 0.06
        if "patient" in traits:
            delta -= 0.10
        if "temperate" in traits:
            delta -= 0.05
        if "wrathful" in traits:
            delta += 0.08
        if "vengeful" in traits:
            delta += 0.04
        if self.lifestyle_focus == "learning":
            delta -= 0.05
        if self._perk_level("learning") >= 3:
            delta -= 0.04
        if self._perk_level("intrigue") >= 3 and any(s.get("type") == "murder" for s in self.active_schemes):
            delta -= 0.03
        return delta

    def _check_stress_break(self):
        level = int(self.stress // 100)
        level = max(0, min(3, level))
        if level <= self._stress_break_level:
            return
        self._stress_break_level = level
        self._trigger_stress_break(level)

    def _trigger_stress_break(self, level):
        relief = 25 + level * 20
        event = self.world.rnd.choice(("drink", "charity", "isolate"))
        if event == "drink":
            self.resources["gold"] = max(0, int(self.resources.get("gold", 0)) - (18 + 9 * level))
            self.resources["prestige"] = max(0, int(self.resources.get("prestige", 0)) - (8 + 6 * level))
            line = "You seek relief in excess."
        elif event == "charity":
            self.resources["gold"] = max(0, int(self.resources.get("gold", 0)) - (22 + 8 * level))
            self.resources["piety"] = int(self.resources.get("piety", 0)) + (15 + 8 * level)
            line = "You donate heavily to quiet your conscience."
        else:
            self.resources["prestige"] = max(0, int(self.resources.get("prestige", 0)) - (15 + 10 * level))
            self.resources["piety"] = max(0, int(self.resources.get("piety", 0)) - (6 + 5 * level))
            line = "You withdraw from court and governance."

        self.stress = clamp(self.stress - relief, 0.0, 300.0)
        self.push_log(f"{self.date}: A stress break hits your court. {line}")
        if not self.modal.open:
            self.modal.show(
                "Stress Break",
                [
                    f"Stress reached a dangerous level ({level}/3).",
                    line,
                    f"Stress reduced to {int(round(self.stress))}/300.",
                ],
                [
                    ("Continue", "accept", lambda: self.modal.close()),
                ],
            )

    @staticmethod
    def _age_person(person):
        if not isinstance(person, dict):
            return
        age = person.get("age", 0)
        try:
            age = int(age)
        except (TypeError, ValueError):
            age = 0
        person["age"] = max(0, age) + 1

    def _annual_death_chance(self, ruler):
        age = ruler.get("age", 35)
        try:
            age = int(age)
        except (TypeError, ValueError):
            age = 35

        if age < 35:
            chance = 0.004
        elif age < 45:
            chance = 0.012
        elif age < 55:
            chance = 0.035
        elif age < 65:
            chance = 0.085
        elif age < 75:
            chance = 0.19
        else:
            chance = 0.34

        traits = set(ruler.get("traits", []))
        if "temperate" in traits:
            chance *= 0.85
        if "diligent" in traits:
            chance *= 0.92
        if "gluttonous" in traits:
            chance *= 1.20
        if "lazy" in traits:
            chance *= 1.12
        return float(clamp(chance, 0.001, 0.85))

    def _maybe_generate_family_for_realm(self, rid, ruler):
        if not isinstance(ruler, dict):
            return
        realm_name = self.world.realm_names[rid] if 0 <= rid < len(self.world.realm_names) else "Realm"
        realm_size = self._realm_size(rid)
        culture = ruler.get("culture", "Nordfolken")
        faith = ruler.get("faith", "Nordfolken Mythology")
        house = ruler.get("house", "House Unknown")
        gender = ruler.get("gender", "male")
        age = ruler.get("age", 18)
        try:
            age = int(age)
        except (TypeError, ValueError):
            age = 18

        if not isinstance(ruler.get("spouse"), dict) and 18 <= age <= 60:
            chance = 0.12 if age <= 24 else 0.18
            if self.world.rnd.random() < chance:
                ruler["spouse"] = generate_spouse(
                    self.world.rnd,
                    realm_name=realm_name,
                    realm_size=realm_size,
                    culture=culture,
                    faith=faith,
                    house=house,
                    ruler_gender=gender,
                )

        has_spouse = isinstance(ruler.get("spouse"), dict)
        if not isinstance(ruler.get("heir"), dict) and 16 <= age <= 65:
            chance = 0.36 if has_spouse else 0.16
            if self.world.rnd.random() < chance:
                ruler["heir"] = generate_heir(
                    self.world.rnd,
                    realm_name=realm_name,
                    realm_size=realm_size,
                    culture=culture,
                    faith=faith,
                    house=house,
                )

    def _build_successor(self, rid, deceased):
        candidate = deceased.get("heir")
        source = "heir"
        if not isinstance(candidate, dict):
            candidate = deceased.get("spouse")
            source = "spouse" if isinstance(candidate, dict) else "noble"

        realm_name = self.world.realm_names[rid] if 0 <= rid < len(self.world.realm_names) else "Realm"
        realm_size = self._realm_size(rid)
        culture = (candidate or {}).get("culture", deceased.get("culture", "Nordfolken"))
        faith = (candidate or {}).get("faith", deceased.get("faith", "Nordfolken Mythology"))

        seed = (self.world.seed * 65537 + rid * 131 + date_ordinal(self.date) * 17) & 0xFFFFFFFF
        rr = random.Random(seed)
        successor = generate_ruler(
            rr,
            realm_name=realm_name,
            realm_size=realm_size,
            culture=culture,
            faith=faith,
        )

        candidate = candidate if isinstance(candidate, dict) else {}
        gender = candidate.get("gender", successor.get("gender", "male"))
        if gender not in ("male", "female"):
            gender = successor.get("gender", "male")
        rank = self._rank_for_realm(rid, gender)
        first_name = self._extract_first_name(candidate.get("name", successor.get("name", "Unnamed")))

        successor["gender"] = gender
        successor["name"] = f"{rank} {first_name}".strip()
        successor["title"] = f"{rank} of {self._realm_core_name(realm_name)}"
        successor["house"] = candidate.get("house") or deceased.get("house") or successor.get("house")
        successor["culture"] = culture
        successor["faith"] = faith

        age = candidate.get("age", successor.get("age", 18))
        try:
            age = int(age)
        except (TypeError, ValueError):
            age = 18
        successor["age"] = max(0, age)

        if "base_stats" not in successor:
            successor["base_stats"] = _stats_list_to_dict(successor.get("stats", []))
        successor["traits"] = normalize_traits(successor.get("traits", []))
        apply_trait_effects(successor)
        self._maybe_generate_family_for_realm(rid, successor)
        return successor, source

    def _handle_ruler_death(self, rid, reason):
        if rid is None or not (0 <= rid < len(self.world.realm_rulers)):
            return
        deceased = self.world.realm_rulers[rid]
        if not isinstance(deceased, dict):
            return
        deceased_name = deceased.get("name", "Ruler")
        successor, source = self._build_successor(rid, deceased)
        self.world.realm_rulers[rid] = successor

        realm_name = self.world.realm_names[rid] if 0 <= rid < len(self.world.realm_names) else "Realm"
        source_label = {
            "heir": "heir",
            "spouse": "spouse",
            "noble": "noble claimant",
        }.get(source, "successor")
        self.push_log(
            f"{self.date}: {deceased_name} of {realm_name} {reason}. "
            f"{successor.get('name', 'Successor')} inherits as {source_label}."
        )

        if rid == self.player_realm_id:
            self.character = successor
            self.resources["prestige"] = max(0, int(self.resources.get("prestige", 0)) - 75)
            self.resources["piety"] = max(0, int(self.resources.get("piety", 0)) - 30)
            self.resources["piety_rate"] = compute_piety_rate(self.character)[0]
            self.resources["prestige_rate"] = self._compute_prestige_rate(self.character)
            self.stress = clamp(float(self.stress) * 0.45, 0.0, 300.0)
            self._stress_break_level = int(self.stress // 100)
            self.dread = clamp(float(self.dread) * 0.40, 0.0, 100.0)
            self._recompute_resource_rates()
            if not self.modal.open:
                self.modal.show(
                    "Succession",
                    [
                        f"{deceased_name} {reason}.",
                        f"You now play as {self.character.get('name', 'your heir')}.",
                    ],
                    [
                        ("Continue", "accept", lambda: self.modal.close()),
                    ],
                )

    def _annual_dynasty_tick(self):
        deaths = []
        for rid, ruler in enumerate(self.world.realm_rulers):
            if not isinstance(ruler, dict):
                continue
            self._age_person(ruler)
            self._age_person(ruler.get("spouse"))
            self._age_person(ruler.get("heir"))
            self._maybe_generate_family_for_realm(rid, ruler)
            if self.world.rnd.random() < self._annual_death_chance(ruler):
                deaths.append(rid)
        for rid in deaths:
            self._handle_ruler_death(rid, "passed away")

    def _tick_politics_day(self):
        self._decrement_days_map(self.realm_truces)
        self._decrement_days_map(self.claim_fabrication_cooldowns)
        self._decrement_days_map(self.decision_cooldowns)
        self._tick_hooks_day()
        self._tick_schemes_day()
        self._tick_lifestyle_day()
        self._tick_border_pressure_day()
        self._tick_ai_war_day()
        self._adjust_stress(self._daily_stress_delta())
        if self.subjugation_cooldown_days > 0:
            self.subjugation_cooldown_days -= 1
        self._tick_campaign_day()

    def _tick_border_pressure_day(self):
        if self.campaign_result is not None:
            return
        if self._raid_cooldown_days > 0:
            self._raid_cooldown_days -= 1
            return

        neighbors = list(self._get_neighbor_realms(self.player_realm_id))
        if not neighbors:
            self._raid_cooldown_days = 25
            return

        hostiles = []
        for rid in neighbors:
            if rid in self.alliances:
                continue
            if int(self.realm_truces.get(rid, 0)) > 0:
                continue
            opinion = self._get_realm_opinion(rid)
            if opinion <= 10:
                hostiles.append((rid, opinion))
        if not hostiles:
            self._raid_cooldown_days = 20
            return

        avg_hostility = -sum(op for _, op in hostiles) / max(1, len(hostiles))
        chance = 0.0015 + (self.threat / 18000.0) + (avg_hostility / 18000.0)
        if self.wars:
            chance *= 1.15
        if self.world.rnd.random() >= chance:
            return

        hostiles.sort(key=lambda item: item[1])  # lowest opinion first
        attacker_rid = hostiles[0][0]
        attacker_name = self._get_war_target_name(attacker_rid)

        raised = int(self.army.get("raised", 0))
        max_army = int(self.army.get("max", 0))
        morale = float(self.army.get("morale", 0))
        defended = raised >= max(180, int(max_army * 0.35)) and morale >= 45.0

        if defended:
            self.resources["prestige"] = int(self.resources.get("prestige", 0)) + 18
            self.resources["renown"] = int(self.resources.get("renown", 0)) + 6
            self._adjust_stress(-2.0)
            self._change_realm_opinion(attacker_rid, -8)
            self.push_log(f"{self.date}: {attacker_name} raids your border, but your levies repel them.")
        else:
            gold_loss = 22 + self.world.rnd.randint(10, 45)
            self.resources["gold"] = max(0, int(self.resources.get("gold", 0)) - gold_loss)
            self.world.adjust_population_for_realm(self.player_realm_id, -0.004)
            self.population = self.world.total_population_for_realm(self.player_realm_id)
            self.food = self._compute_food_values()
            self._update_army_max()
            self._adjust_stress(+5.0)
            self._change_realm_opinion(attacker_rid, -14)
            self.push_log(
                f"{self.date}: {attacker_name} raids your border. "
                f"You lose {gold_loss} gold and local holdings are damaged."
            )
            if not self.modal.open:
                self.modal.show(
                    "Border Raid",
                    [
                        f"{attacker_name} launched a raid into your frontier.",
                        f"Losses: {gold_loss} gold and reduced local population.",
                        "Raise and position your army to deter future raids.",
                    ],
                    [
                        ("OK", "accept", lambda: self.modal.close()),
                    ],
                )

        self._recompute_resource_rates()
        self._raid_cooldown_days = 110 + self.world.rnd.randint(0, 120)

    def _pick_enemy_war_goal_against_player(self, attacker_rid):
        if attacker_rid is None or not (0 <= attacker_rid < len(self.world.realm_names)):
            return None
        player_provs = [p for p in self.world.provinces if p.realm_id == self.player_realm_id]
        if not player_provs:
            return None

        border = []
        for prov in player_provs:
            if any(self.world.provinces[nb].realm_id == attacker_rid for nb in self._prov_adj[prov.id]):
                border.append(prov)

        candidates = border if border else player_provs
        cap_pid = self._get_player_capital_pid()
        if cap_pid is not None and len(candidates) > 1:
            candidates = [p for p in candidates if p.id != cap_pid] or candidates
        candidates.sort(key=lambda p: p.population)
        return candidates[0].id if candidates else None

    def _start_defensive_war(self, attacker_rid):
        if attacker_rid is None or attacker_rid == self.player_realm_id:
            return False
        if attacker_rid in self.alliances:
            return False
        if self._get_war_by_target(attacker_rid):
            return False
        if int(self.realm_truces.get(attacker_rid, 0)) > 0:
            return False

        goal_pid = self._pick_enemy_war_goal_against_player(attacker_rid)
        if goal_pid is None:
            return False

        if hasattr(self.world, "realm_sizes") and 0 <= attacker_rid < len(self.world.realm_sizes):
            total_provs = int(self.world.realm_sizes[attacker_rid])
        else:
            total_provs = sum(1 for p in self.world.provinces if p.realm_id == attacker_rid)

        war = {
            "id": self._war_next_id,
            "target_id": attacker_rid,
            "war_type": "Invasion",
            "goal_pid": goal_pid,
            "progress": 0.0,
            "days": 0,
            "ready_prompted": False,
            "sieged": set(),
            "total_provs": total_provs,
            "attacker": "ai",
        }
        self._war_next_id += 1
        self.wars.append(war)
        self._ensure_enemy_army_for_war(attacker_rid)
        self._war_focus_id = war["id"]
        self._update_war_progress(war)
        self._change_realm_opinion(attacker_rid, -20)
        self._adjust_stress(+3.0)
        self._recompute_resource_rates()

        attacker_name = self._get_war_target_name(attacker_rid)
        goal_name = self.world.provinces[goal_pid].name if 0 <= goal_pid < len(self.world.provinces) else "frontier lands"
        self.push_log(f"{self.date}: {attacker_name} declares an invasion for {goal_name}.")
        if not self.modal.open:
            self.modal.show(
                "Enemy Declaration",
                [
                    f"{attacker_name} declared war on your realm.",
                    f"They demand {goal_name} if you surrender.",
                    "Raise levies and hold your frontier.",
                ],
                [
                    ("View War", "accept", lambda wid=war["id"]: self._open_war_details(wid)),
                ],
            )
        return True

    def _tick_ai_war_day(self):
        if self.campaign_result is not None:
            return
        if self._ai_war_cooldown_days > 0:
            self._ai_war_cooldown_days -= 1
            return
        if len(self.wars) >= 3:
            self._ai_war_cooldown_days = 45
            return

        neighbors = list(self._get_neighbor_realms(self.player_realm_id))
        if not neighbors:
            self._ai_war_cooldown_days = 30
            return

        player_effects = self._realm_building_effects(self.player_realm_id)
        player_strength = max(
            1.0,
            self.population * self.army_pop_ratio * (1.0 + float(player_effects.get("levy_mult_bonus", 0.0))),
        )

        candidates = []
        for rid in neighbors:
            if rid in self.alliances:
                continue
            if self._get_war_by_target(rid):
                continue
            if int(self.realm_truces.get(rid, 0)) > 0:
                continue

            opinion = self._get_realm_opinion(rid)
            if opinion > -18:
                continue

            enemy_pop = self.world.total_population_for_realm(rid)
            enemy_strength = max(1.0, enemy_pop * self.army_pop_ratio)
            ratio = enemy_strength / player_strength
            hostility = max(0, -opinion)
            chance = 0.0007 + hostility * 0.000035 + max(0.0, ratio - 0.90) * 0.0022 + self.threat * 0.000015
            if self.wars:
                chance *= 0.85
            candidates.append((min(0.32, chance), rid))

        if not candidates:
            self._ai_war_cooldown_days = 25
            return

        candidates.sort(key=lambda item: item[0], reverse=True)
        chance, rid = candidates[0]
        if self.world.rnd.random() >= chance:
            self._ai_war_cooldown_days = 12
            return

        if self._start_defensive_war(rid):
            self._ai_war_cooldown_days = 220
        else:
            self._ai_war_cooldown_days = 35

    def _finish_campaign(self, result, summary_lines):
        if self.campaign_result is not None:
            return
        if result not in ("victory", "defeat"):
            return
        self.campaign_result = result
        self._campaign_over_day = date_ordinal(self.date)
        self.speed_level = 0
        title = "Dynasty Victory" if result == "victory" else "Dynasty Defeat"
        self.push_log(f"{self.date}: Campaign {result}.")
        self.modal.show(
            title,
            summary_lines,
            [
                ("Continue", "accept", lambda: self.modal.close()),
                ("Realm", "secondary", lambda: self._open_realm_overview()),
                ("Main Menu", "deny", lambda: self._return_to_main_menu()),
            ],
        )

    def _tick_campaign_day(self):
        if self.campaign_result is not None:
            return

        held = self._player_province_count()
        if held <= 0:
            self._finish_campaign(
                "defeat",
                [
                    "Your dynasty has no land remaining.",
                    "You can continue in sandbox or return to the main menu.",
                ],
            )
            return

        gold = int(self.resources.get("gold", 0))
        if gold < 0:
            self._insolvency_days += 1
        else:
            self._insolvency_days = max(0, self._insolvency_days - 3)

        production, consumption = self.food
        severe_famine = consumption > 0 and production < (consumption * 0.80)
        if severe_famine:
            self._famine_days += 1
        else:
            self._famine_days = max(0, self._famine_days - 2)

        if self.stress >= 285:
            self._crisis_days += 1
        else:
            self._crisis_days = max(0, self._crisis_days - 3)

        if self._insolvency_days >= 540:
            self._finish_campaign(
                "defeat",
                [
                    "Your realm has been insolvent for too long.",
                    "Vassals and levies abandon the crown.",
                ],
            )
            return

        if self._famine_days >= 240:
            self._finish_campaign(
                "defeat",
                [
                    "A prolonged famine shattered your realm.",
                    "Control collapses as provinces revolt.",
                ],
            )
            return

        if self._crisis_days >= 180:
            self._finish_campaign(
                "defeat",
                [
                    "You ruled under unbearable stress for too long.",
                    "Court authority breaks down into chaos.",
                ],
            )
            return

        target = int(self._campaign_target_provinces)
        renown = int(self.resources.get("renown", 0))
        prestige = int(self.resources.get("prestige", 0))
        if held >= target and (renown >= 260 or prestige >= 650):
            self._finish_campaign(
                "victory",
                [
                    f"You secured {held} provinces (target: {target}).",
                    f"Dynasty standing reached Renown {renown} and Prestige {prestige}.",
                ],
            )

    def _can_declare_war_type(self, target_rid, war_type):
        if target_rid is None or target_rid == self.player_realm_id:
            return False, "Invalid target."
        if target_rid in self.alliances:
            return False, "Cannot declare on an ally."
        truce_days = int(self.realm_truces.get(target_rid, 0))
        if truce_days > 0:
            return False, f"Truce active ({self._days_label(truce_days)} left)."

        if war_type == "Conquest":
            if target_rid not in self.realm_claims:
                claim_scheme = self._active_scheme(scheme_type="claim", target_id=target_rid)
                if claim_scheme is not None:
                    prog = int(round(float(claim_scheme.get("progress", 0.0))))
                    return False, f"Claim scheme in progress ({prog}%)."
                return False, "Requires a fabricated claim."
            if self.resources.get("prestige", 0) < 75:
                return False, "Need 75 prestige."
            return True, "Use an existing claim (cost: 75 prestige)."

        if war_type == "Subjugation":
            if self.resources.get("prestige", 0) < 320:
                return False, "Need 320 prestige."
            if self.subjugation_cooldown_days > 0:
                return False, f"On cooldown ({self._days_label(self.subjugation_cooldown_days)})."
            return True, "Major war (cost: 320 prestige)."

        if war_type == "Holy War":
            target_faith = None
            if 0 <= target_rid < len(self.world.realm_rulers):
                target_faith = self.world.realm_rulers[target_rid].get("faith")
            if target_faith == self.character.get("faith"):
                return False, "Target follows your faith."
            if self.resources.get("piety", 0) < 250:
                return False, "Need 250 piety."
            if self.resources.get("prestige", 0) < 60:
                return False, "Need 60 prestige."
            return True, "Religious war (cost: 250 piety, 60 prestige)."

        return False, "Unavailable war type."

    def _pay_war_cost(self, target_rid, war_type):
        if war_type == "Conquest":
            self.resources["prestige"] = max(0, int(self.resources.get("prestige", 0)) - 75)
        elif war_type == "Subjugation":
            self.resources["prestige"] = max(0, int(self.resources.get("prestige", 0)) - 320)
            self.subjugation_cooldown_days = max(self.subjugation_cooldown_days, 3650)
        elif war_type == "Holy War":
            self.resources["piety"] = max(0, int(self.resources.get("piety", 0)) - 250)
            self.resources["prestige"] = max(0, int(self.resources.get("prestige", 0)) - 60)
        self.dread = clamp(float(self.dread) + 4.0, 0.0, 100.0)
        self._change_realm_opinion(target_rid, -18)

    def _selected_target_realm(self):
        if self.selected_province is None:
            return None
        rid = self.selected_province.realm_id
        if rid == self.player_realm_id:
            return None
        if not (0 <= rid < len(self.world.realm_names)):
            return None
        return rid

    def _action_promote_relations(self):
        target_rid = self._selected_target_realm()
        if target_rid is None:
            self.modal.show(
                "No Target Selected",
                [
                    "Select a foreign realm before sending diplomatic envoys.",
                ],
                [
                    ("OK", "accept", lambda: self.modal.close()),
                ],
            )
            return

        gold_cost = 18
        if self.resources.get("gold", 0) < gold_cost:
            self.modal.show(
                "Insufficient Gold",
                [
                    f"Starting a sway scheme costs {gold_cost} gold.",
                ],
                [
                    ("OK", "accept", lambda: self.modal.close()),
                ],
            )
            return

        if self._active_scheme(scheme_type="sway", target_id=target_rid):
            self.modal.show(
                "Scheme Already Running",
                [
                    "You already have an active sway scheme on this ruler.",
                ],
                [
                    ("OK", "accept", lambda: self.modal.close()),
                ],
            )
            return

        dip = self._stat_value(self.character, "Diplomacy", default=8)
        chance = float(clamp(0.62 + dip * 0.02 + self._perk_level("diplomacy") * 0.03, 0.35, 0.95))
        ok, msg = self._start_scheme(
            "sway",
            target_rid,
            success_chance=chance,
            exposure_chance=0.10,
            base_power=0.95,
            min_days=35,
        )
        if not ok:
            self.modal.show(
                "Cannot Start Scheme",
                [msg],
                [("OK", "accept", lambda: self.modal.close())],
            )
            return

        self.resources["gold"] -= gold_cost
        target_name = self._get_war_target_name(target_rid)
        sway_stress = 1.5
        traits = self._traits_of(self.character)
        if "wrathful" in traits or "vengeful" in traits:
            sway_stress += 2.0
        if "forgiving" in traits or "patient" in traits:
            sway_stress -= 1.0
        self._adjust_stress(max(-1.0, sway_stress))
        self.push_log(f"{self.date}: You begin a sway scheme targeting {target_name}.")
        self.modal.show(
            "Sway Scheme Started",
            [
                f"Your chancellor begins swaying {target_name}.",
                "Progress advances each day and resolves automatically.",
            ],
            [
                ("OK", "accept", lambda: self.modal.close()),
            ],
        )

    def _action_fabricate_claim(self):
        target_rid = self._selected_target_realm()
        if target_rid is None:
            self.modal.show(
                "No Target Selected",
                [
                    "Select a foreign realm to fabricate a claim.",
                ],
                [
                    ("OK", "accept", lambda: self.modal.close()),
                ],
            )
            return

        if target_rid in self.realm_claims:
            self.modal.show(
                "Claim Already Held",
                [
                    "You already have a claim on this realm.",
                ],
                [
                    ("OK", "accept", lambda: self.modal.close()),
                ],
            )
            return

        cooldown = int(self.claim_fabrication_cooldowns.get(target_rid, 0))
        if cooldown > 0:
            self.modal.show(
                "Scheme Already Running",
                [
                    f"You must wait {self._days_label(cooldown)} before trying again.",
                ],
                [
                    ("OK", "accept", lambda: self.modal.close()),
                ],
            )
            return

        if self._active_scheme(scheme_type="claim", target_id=target_rid):
            self.modal.show(
                "Scheme Already Running",
                [
                    "Your court chaplain is already fabricating this claim.",
                ],
                [
                    ("OK", "accept", lambda: self.modal.close()),
                ],
            )
            return

        gold_cost = 45
        piety_cost = 35
        if self.resources.get("gold", 0) < gold_cost or self.resources.get("piety", 0) < piety_cost:
            self.modal.show(
                "Insufficient Resources",
                [
                    f"Fabricating a claim costs {gold_cost} gold and {piety_cost} piety.",
                ],
                [
                    ("OK", "accept", lambda: self.modal.close()),
                ],
            )
            return

        learning = self._stat_value(self.character, "Learning", default=8)
        intrigue = self._stat_value(self.character, "Intrigue", default=8)
        chance = float(clamp(0.20 + learning * 0.03 + intrigue * 0.015 + self._perk_level("learning") * 0.03, 0.15, 0.88))
        exposure = float(clamp(0.45 - intrigue * 0.015 - self._perk_level("intrigue") * 0.03, 0.12, 0.65))
        ok, msg = self._start_scheme(
            "claim",
            target_rid,
            success_chance=chance,
            exposure_chance=exposure,
            base_power=0.72,
            min_days=80,
        )
        if not ok:
            self.modal.show(
                "Cannot Start Scheme",
                [msg],
                [("OK", "accept", lambda: self.modal.close())],
            )
            return

        self.resources["gold"] -= gold_cost
        self.resources["piety"] -= piety_cost
        target_name = self._get_war_target_name(target_rid)
        self._adjust_stress(+2.0)
        self.push_log(f"{self.date}: Claim fabrication scheme started in {target_name}.")

        self.modal.show(
            "Claim Scheme Started",
            [
                f"Your clergy begins forging evidence against {target_name}.",
                f"Estimated success chance: {int(round(chance * 100))}%.",
            ],
            [
                ("OK", "accept", lambda: self.modal.close()),
            ],
        )

    def _action_arrange_marriage(self):
        target_rid = self._selected_target_realm()
        if target_rid is None:
            self.modal.show(
                "No Target Selected",
                [
                    "Select a foreign realm before proposing a dynastic marriage.",
                ],
                [
                    ("OK", "accept", lambda: self.modal.close()),
                ],
            )
            return

        if target_rid in self.alliances:
            self.modal.show(
                "Already Allied",
                [
                    "You already have a marriage alliance with this realm.",
                ],
                [
                    ("OK", "accept", lambda: self.modal.close()),
                ],
            )
            return

        prestige_cost = 70
        if self.resources.get("prestige", 0) < prestige_cost:
            self.modal.show(
                "Insufficient Prestige",
                [
                    f"Marriage diplomacy costs {prestige_cost} prestige.",
                ],
                [
                    ("OK", "accept", lambda: self.modal.close()),
                ],
            )
            return

        target_ruler = self.world.realm_rulers[target_rid]
        dip = self._stat_value(self.character, "Diplomacy", default=8)
        target_dip = self._stat_value(target_ruler, "Diplomacy", default=8)
        opinion = self._get_realm_opinion(target_rid)
        heirs_ready = isinstance(self.character.get("heir"), dict) and isinstance(target_ruler.get("heir"), dict)
        hook = self.hooks.get(target_rid)

        chance = 0.28 + (opinion + 100) / 260.0 + (dip - target_dip) * 0.02
        if heirs_ready:
            chance += 0.12
        if self.lifestyle_focus == "diplomacy":
            chance += 0.06
        chance += self._perk_level("diplomacy") * 0.02
        chance += float(self.dread) * 0.001
        if isinstance(hook, dict):
            if hook.get("strength") == "strong":
                chance += 0.40
            else:
                chance += 0.20
        chance = float(clamp(chance, 0.10, 0.92))

        self.resources["prestige"] -= prestige_cost
        success = self.world.rnd.random() < chance
        target_name = self._get_war_target_name(target_rid)
        used_hook = False

        if not success and isinstance(hook, dict):
            # Use leverage to force the final negotiation step.
            success = True
            used_hook = True
            self._consume_hook(target_rid)

        if success:
            self.alliances.add(target_rid)
            self.realm_truces[target_rid] = max(int(self.realm_truces.get(target_rid, 0)), 365)
            new_opinion = self._change_realm_opinion(target_rid, +24)
            self.resources["renown"] = int(self.resources.get("renown", 0)) + 25
            self._recompute_resource_rates()
            self.push_log(f"{self.date}: Marriage alliance signed with {target_name}.")
            self.modal.show(
                "Marriage Alliance",
                [
                    f"{target_name} accepted your dynastic marriage proposal.",
                    "Leverage from a hook secured the terms." if used_hook else "The match is celebrated by both courts.",
                    f"Opinion is now {new_opinion:+d}.",
                ],
                [
                    ("OK", "accept", lambda: self.modal.close()),
                ],
            )
            return

        new_opinion = self._change_realm_opinion(target_rid, -8)
        self._adjust_stress(+3.0)
        self.push_log(f"{self.date}: {target_name} rejected a marriage proposal.")
        self.modal.show(
            "Proposal Rejected",
            [
                f"{target_name} declined your marriage offer.",
                f"Opinion is now {new_opinion:+d}.",
            ],
            [
                ("OK", "accept", lambda: self.modal.close()),
            ],
        )

    def _action_plot_murder(self):
        target_rid = self._selected_target_realm()
        if target_rid is None:
            self.modal.show(
                "No Target Selected",
                [
                    "Select a foreign ruler before opening an assassination plot.",
                ],
                [
                    ("OK", "accept", lambda: self.modal.close()),
                ],
            )
            return

        if self._active_scheme(scheme_type="murder", target_id=target_rid):
            self.modal.show(
                "Scheme Already Running",
                [
                    "A murder scheme is already active on this ruler.",
                ],
                [
                    ("OK", "accept", lambda: self.modal.close()),
                ],
            )
            return

        gold_cost = 60
        prestige_cost = 30
        if self.resources.get("gold", 0) < gold_cost or self.resources.get("prestige", 0) < prestige_cost:
            self.modal.show(
                "Insufficient Resources",
                [
                    f"Assassination plots cost {gold_cost} gold and {prestige_cost} prestige.",
                ],
                [
                    ("OK", "accept", lambda: self.modal.close()),
                ],
            )
            return

        target_ruler = self.world.realm_rulers[target_rid]
        intrigue = self._stat_value(self.character, "Intrigue", default=8)
        target_intrigue = self._stat_value(target_ruler, "Intrigue", default=8)
        opinion = self._get_realm_opinion(target_rid)

        chance = 0.10 + (intrigue - target_intrigue) * 0.035 + max(0, -opinion) * 0.002
        if self.lifestyle_focus == "intrigue":
            chance += 0.06
        chance += self._perk_level("intrigue") * 0.02
        chance = float(clamp(chance, 0.05, 0.82))
        exposure = float(clamp(0.62 - intrigue * 0.02 - self._perk_level("intrigue") * 0.03, 0.12, 0.72))
        ok, msg = self._start_scheme(
            "murder",
            target_rid,
            success_chance=chance,
            exposure_chance=exposure,
            base_power=0.66,
            min_days=95,
        )
        if not ok:
            self.modal.show(
                "Cannot Start Scheme",
                [msg],
                [("OK", "accept", lambda: self.modal.close())],
            )
            return

        self.resources["gold"] -= gold_cost
        self.resources["prestige"] = max(0, int(self.resources.get("prestige", 0)) - prestige_cost)
        target_name = self._get_war_target_name(target_rid)
        murder_stress = 5.0
        traits = self._traits_of(self.character)
        if "forgiving" in traits or "humble" in traits:
            murder_stress += 6.0
        if "vengeful" in traits or "wrathful" in traits:
            murder_stress -= 2.0
        self._adjust_stress(max(0.0, murder_stress))
        self.push_log(f"{self.date}: Murder scheme started against {target_name}.")
        self.modal.show(
            "Murder Scheme Started",
            [
                f"Agents infiltrate the court of {target_name}.",
                f"Estimated success chance: {int(round(chance * 100))}%.",
            ],
            [
                ("OK", "accept", lambda: self.modal.close()),
            ],
        )

    def _decision_available(self, key, *, gold=0, piety=0, prestige=0, requires_peace=False):
        cd = int(self.decision_cooldowns.get(key, 0))
        if cd > 0:
            return False, f"Cooldown: {self._days_label(cd)}"
        if requires_peace and self.wars:
            return False, "Unavailable while at war."
        if self.resources.get("gold", 0) < gold:
            return False, f"Need {gold} gold."
        if self.resources.get("piety", 0) < piety:
            return False, f"Need {piety} piety."
        if self.resources.get("prestige", 0) < prestige:
            return False, f"Need {prestige} prestige."
        return True, "Ready"

    def _open_decisions_modal(self):
        feast_ok, feast_msg = self._decision_available("feast", gold=55, requires_peace=True)
        pilgrim_ok, pilgrim_msg = self._decision_available("pilgrimage", gold=85, requires_peace=False)
        epic_ok, epic_msg = self._decision_available("epic", gold=75, prestige=25, requires_peace=False)

        lines = [
            "Major Decisions",
            f"Hold Feast: {feast_msg}",
            f"Go on Pilgrimage: {pilgrim_msg}",
            f"Commission Epic: {epic_msg}",
            "",
            f"Resources: Gold {int(self.resources.get('gold', 0))}, "
            f"Piety {int(self.resources.get('piety', 0))}, "
            f"Prestige {int(self.resources.get('prestige', 0))}",
        ]
        self.modal.show(
            "Decisions",
            lines,
            [
                (
                    "Feast",
                    "primary" if feast_ok else "disabled",
                    (lambda: self._decision_hold_feast()) if feast_ok else (lambda: None),
                ),
                (
                    "Pilgrimage",
                    "secondary" if pilgrim_ok else "disabled",
                    (lambda: self._decision_go_on_pilgrimage()) if pilgrim_ok else (lambda: None),
                ),
                (
                    "Epic",
                    "secondary" if epic_ok else "disabled",
                    (lambda: self._decision_commission_epic()) if epic_ok else (lambda: None),
                ),
                ("Close", "secondary", lambda: self.modal.close()),
            ],
        )

    def _decision_hold_feast(self):
        ok, msg = self._decision_available("feast", gold=55, requires_peace=True)
        if not ok:
            self.modal.show("Decision Unavailable", [msg], [("OK", "accept", lambda: self._open_decisions_modal())])
            return

        self.resources["gold"] = max(0, int(self.resources.get("gold", 0)) - 55)
        self.resources["prestige"] = int(self.resources.get("prestige", 0)) + 22
        self.decision_cooldowns["feast"] = 720

        relief = -26.0
        traits = self._traits_of(self.character)
        if "greedy" in traits:
            relief += 6.0
        if "charitable" in traits or "patient" in traits:
            relief -= 4.0
        self._adjust_stress(relief, reason="managed through feasting")

        for rid in range(len(self.world.realm_names)):
            if rid == self.player_realm_id:
                continue
            self._change_realm_opinion(rid, +4)

        self._recompute_resource_rates()
        self.push_log(f"{self.date}: You hold a grand feast to calm the court.")
        self.modal.show(
            "Feast Held",
            [
                "The court celebrates and rivalries cool for a while.",
                "Stress reduced, prestige gained, and foreign opinion improved.",
            ],
            [
                ("OK", "accept", lambda: self._open_decisions_modal()),
            ],
        )

    def _decision_go_on_pilgrimage(self):
        ok, msg = self._decision_available("pilgrimage", gold=85)
        if not ok:
            self.modal.show("Decision Unavailable", [msg], [("OK", "accept", lambda: self._open_decisions_modal())])
            return

        self.resources["gold"] = max(0, int(self.resources.get("gold", 0)) - 85)
        self.resources["piety"] = int(self.resources.get("piety", 0)) + 140
        self.resources["prestige"] = int(self.resources.get("prestige", 0)) + 12
        self.decision_cooldowns["pilgrimage"] = 960

        relief = -19.0
        traits = self._traits_of(self.character)
        if "temperate" in traits or "humble" in traits:
            relief -= 3.0
        if "wrathful" in traits:
            relief += 2.0
        self._adjust_stress(relief, reason="eased by pilgrimage")

        self._recompute_resource_rates()
        self.push_log(f"{self.date}: You complete a long pilgrimage.")
        self.modal.show(
            "Pilgrimage Complete",
            [
                "Your ruler returns with renewed spiritual authority.",
                "Piety and prestige increased; stress reduced.",
            ],
            [
                ("OK", "accept", lambda: self._open_decisions_modal()),
            ],
        )

    def _decision_commission_epic(self):
        ok, msg = self._decision_available("epic", gold=75, prestige=25)
        if not ok:
            self.modal.show("Decision Unavailable", [msg], [("OK", "accept", lambda: self._open_decisions_modal())])
            return

        self.resources["gold"] = max(0, int(self.resources.get("gold", 0)) - 75)
        self.resources["prestige"] = max(0, int(self.resources.get("prestige", 0)) - 25)
        self.resources["prestige"] = int(self.resources.get("prestige", 0)) + 68
        self.resources["renown"] = int(self.resources.get("renown", 0)) + 34
        self.decision_cooldowns["epic"] = 1080

        stress_change = 3.0
        traits = self._traits_of(self.character)
        if "proud" in traits:
            stress_change -= 1.5
        if "humble" in traits:
            stress_change += 2.0
        self._adjust_stress(stress_change, reason="strained by court pageantry")

        self._recompute_resource_rates()
        self.push_log(f"{self.date}: Court poets spread your dynasty's epic across the realm.")
        self.modal.show(
            "Epic Commissioned",
            [
                "Your legend grows in neighboring courts.",
                "Renown and prestige rise, but the campaign is expensive.",
            ],
            [
                ("OK", "accept", lambda: self._open_decisions_modal()),
            ],
        )

    def _open_lifestyle_focus_modal(self):
        focus = self.lifestyle_focuses[self._lifestyle_picker_index]
        current = self.lifestyle_focus
        stat_key = self._focus_stat_key(focus)
        stat_val = self._stat_value(self.character, stat_key, default=8)
        xp = float(self.lifestyle_xp.get(focus, 0.0))
        need = self._lifestyle_xp_threshold(focus)
        lines = [
            f"Current focus: {self._lifestyle_label(current)}",
            f"Candidate focus: {self._lifestyle_label(focus)}",
            f"{self._lifestyle_label(focus)} perks: {self._perk_level(focus)}",
            f"XP progress: {int(xp)}/{int(need)}",
            f"{stat_key}: {stat_val}",
            f"Stress: {int(round(self.stress))}/300",
        ]
        self.modal.show(
            "Lifestyle Focus",
            lines,
            [
                ("Prev", "secondary", lambda: self._cycle_lifestyle_focus(-1)),
                ("Adopt", "accept", lambda: self._adopt_lifestyle_focus()),
                ("Next", "secondary", lambda: self._cycle_lifestyle_focus(+1)),
            ],
        )

    def _cycle_lifestyle_focus(self, delta):
        if not self.lifestyle_focuses:
            return
        self._lifestyle_picker_index = (self._lifestyle_picker_index + int(delta)) % len(self.lifestyle_focuses)
        self._open_lifestyle_focus_modal()

    def _adopt_lifestyle_focus(self):
        focus = self.lifestyle_focuses[self._lifestyle_picker_index]
        self._set_lifestyle_focus(focus)
        self._open_lifestyle_focus_modal()

    def _open_scheme_overview(self):
        lines = [
            f"Stress: {int(round(self.stress))}/300",
            f"Dread: {int(round(self.dread))}/100",
            f"Focus: {self._lifestyle_label(self.lifestyle_focus)}",
            f"Renown: {int(self.resources.get('renown', 0))}",
            "",
            "Active schemes:",
        ]
        if not self.active_schemes:
            lines.append("None")
        else:
            for scheme in self.active_schemes:
                target = self._get_war_target_name(scheme.get("target_id"))
                p = int(round(float(scheme.get("progress", 0.0))))
                lines.append(f"{self._scheme_label(scheme.get('type'))}: {target} ({p}%)")
        lines.append("")
        lines.append(f"Active hooks: {len(self.hooks)}")
        self.modal.show(
            "Court & Schemes",
            lines,
            [
                ("Lifestyle", "primary", lambda: self._open_lifestyle_focus_modal()),
                ("Military", "secondary", lambda: self._handle_action("military")),
                ("Close", "secondary", lambda: self.modal.close()),
            ],
        )

    def _open_realm_overview(self):
        held = self._player_province_count()
        target = int(self._campaign_target_provinces)
        progress = self._campaign_progress_percent()
        claims = len(self.realm_claims)
        alliances = len(self.alliances)
        lines = [
            f"Realm size: {held}/{len(self.world.provinces)} provinces",
            f"Campaign progress: {progress}% ({held}/{target} provinces toward victory)",
            f"Dynasty: Prestige {int(self.resources.get('prestige', 0))}, Renown {int(self.resources.get('renown', 0))}",
            f"Diplomacy: {claims} claims, {alliances} alliances, {len(self.wars)} active wars",
            f"Stress and dread: {int(round(self.stress))}/300, {int(round(self.dread))}/100",
            f"Border pressure: next raid check in {self._days_label(self._raid_cooldown_days)}",
        ]
        remaining = [int(v) for v in self.decision_cooldowns.values() if int(v) > 0]
        if remaining:
            lines.append(f"Major decision cooldown: {self._days_label(min(remaining))}")
        else:
            lines.append("Major decision cooldown: Ready")
        if self.campaign_result is None:
            lines.append("Victory condition: hold target provinces and reach high renown or prestige.")
            if self._insolvency_days > 0:
                lines.append(f"Insolvency pressure: {self._insolvency_days}/540 days")
            if self._famine_days > 0:
                lines.append(f"Famine pressure: {self._famine_days}/240 days")
            if self._crisis_days > 0:
                lines.append(f"Stress crisis pressure: {self._crisis_days}/180 days")
        elif self.campaign_result == "victory":
            lines.append("Campaign status: Victory achieved.")
        else:
            lines.append("Campaign status: Defeat condition reached.")
        self.modal.show(
            "Realm Overview",
            lines,
            [
                ("Ledger", "primary", lambda: self._handle_action("ledger")),
                ("Military", "secondary", lambda: self._handle_action("military")),
                ("Court", "secondary", lambda: self._handle_action("court")),
                ("Close", "secondary", lambda: self.modal.close()),
            ],
        )

    def _open_military_overview(self):
        raised = int(self.army.get("raised", 0))
        max_army = int(self.army.get("max", 0))
        morale = int(round(float(self.army.get("morale", 0))))
        raising = "Yes" if self.army_raising else "No"
        rally_pid = self._get_player_capital_pid()
        rally_name = "None"
        if rally_pid is not None and 0 <= rally_pid < len(self.world.provinces):
            rally_name = self.world.provinces[rally_pid].name

        lines = [
            f"Levies raised: {raised:,}/{max_army:,}",
            f"Army morale: {morale}/100",
            f"Currently mustering: {raising}",
            f"Rally point: {rally_name}",
            f"Active wars: {len(self.wars)}",
        ]
        if self._siege_state is not None:
            pid = self._siege_state.get("pid")
            prov_name = self.world.provinces[pid].name if isinstance(pid, int) and 0 <= pid < len(self.world.provinces) else "Unknown"
            stage = str(self._siege_state.get("stage", "prep")).title()
            lines.append(f"Current siege: {prov_name} ({stage})")

        if self.wars:
            for war in self.wars[:3]:
                name = self._get_war_target_name(war)
                prog = self._format_war_progress(war.get("progress", 0.0))
                lines.append(f"{name}: {prog}% war score")
        else:
            lines.append("No wars are currently active.")

        war_action = (
            ("War List", "primary", lambda: self._handle_action("open_war_overview"))
            if self.wars
            else ("War List", "disabled", lambda: None)
        )
        rally_action = ("Rally Army", "secondary", lambda: self._handle_action("rally"))
        utility_action = (
            ("Disband", "deny", lambda: self._handle_action("disband"))
            if raised > 0
            else ("Set Rally", "secondary", lambda: self._handle_action("set_rally"))
        )
        self.modal.show(
            "Military Overview",
            lines,
            [
                war_action,
                rally_action,
                utility_action,
                ("Close", "secondary", lambda: self.modal.close()),
            ],
        )

    def _open_ledger_overview(self):
        gold = int(self.resources.get("gold", 0))
        piety = int(self.resources.get("piety", 0))
        prestige = int(self.resources.get("prestige", 0))
        renown = int(self.resources.get("renown", 0))
        gold_rate = int(self.resources.get("gold_rate", 0))
        piety_rate = int(self.resources.get("piety_rate", 0))
        prestige_rate = int(self.resources.get("prestige_rate", 0))
        renown_rate = int(self.resources.get("renown_rate", 0))
        farms = int(self.world.count_buildings(realm_id=self.player_realm_id, building_id="farm"))
        tradeports = int(self.world.count_buildings(realm_id=self.player_realm_id, building_id="tradeport"))
        temples = int(self.world.count_buildings(realm_id=self.player_realm_id, building_id="temple"))
        barracks = int(self.world.count_buildings(realm_id=self.player_realm_id, building_id="barracks"))
        effects = self._realm_building_effects(self.player_realm_id)
        production, consumption = self.food
        net_food = int(production - consumption)
        lines = [
            f"Gold: {gold} ({gold_rate:+d}/month)",
            f"Piety: {piety} ({piety_rate:+d}/month)",
            f"Prestige: {prestige} ({prestige_rate:+d}/month)",
            f"Renown: {renown} ({renown_rate:+d}/month)",
            f"Food: {int(production):,} produced vs {int(consumption):,} consumed ({net_food:+,})",
            f"Holdings: Farms {farms}, Tradeports {tradeports}, Temples {temples}, Barracks {barracks}",
            f"Building effects: +{int(round(effects.get('gold_rate_bonus', 0.0)))} gold rate, "
            f"+{int(round(effects.get('piety_rate_bonus', 0.0)))} piety rate, "
            f"+{int(round(effects.get('prestige_rate_bonus', 0.0)))} prestige rate, "
            f"+{int(round(float(effects.get('levy_mult_bonus', 0.0)) * 100))}% levies",
        ]
        if self.wars:
            lines.append("War pressure: active wars increase upkeep risk and political stress.")
        if self.stress >= 220:
            lines.append("High stress is currently reducing your effective income.")

        self.modal.show(
            "Realm Ledger",
            lines,
            [
                ("Build Farm", "secondary", lambda: self._handle_action("build_farm")),
                ("Realm", "primary", lambda: self._handle_action("view_realm")),
                ("Close", "secondary", lambda: self.modal.close()),
            ],
        )

    def _set_rally_point(self, pid, announce=True):
        if pid is None or not (0 <= pid < len(self.world.provinces)):
            return False
        prov = self.world.provinces[pid]
        if prov.realm_id != self.player_realm_id:
            return False
        self.world.player_capital_pid = pid
        if self.army.get("raised", 0) <= 0 and not self.army_raising:
            self._set_army_prov(pid)
        if announce:
            self.push_log(f"{self.date}: Rally point moved to {prov.name}.")
        return True

    def _rally_army_to_capital(self):
        rally_pid = self._get_player_capital_pid()
        if rally_pid is None:
            self.push_log("No rally point available.")
            return
        if self.army.get("raised", 0) <= 0:
            self._set_army_prov(rally_pid)
            self.push_log("Army is not raised; rally point updated for future mustering.")
            self._open_military_overview()
            return
        self._ensure_army_position()
        start_pid = self.army_prov_id
        if start_pid is None or start_pid == rally_pid:
            self.push_log("Army already at rally point.")
            self._open_military_overview()
            return
        route = self._find_province_path(start_pid, rally_pid)
        if not route:
            self.push_log("No route to rally point.")
            self._open_military_overview()
            return
        self.army_route = route
        self.army_step_from = start_pid
        self.army_step_to = route[0]
        self.army_step_progress = 0.0
        self.army_selected = True
        self.push_log(f"{self.date}: Army rally ordered.")
        self._open_military_overview()

    def _open_campaign_briefing(self):
        held = self._player_province_count()
        target = int(self._campaign_target_provinces)
        self.modal.show(
            "Campaign Briefing",
            [
                f"You begin with {held} provinces.",
                f"Primary goal: secure at least {target} provinces and build dynasty renown.",
                "Use schemes, alliances, and wars to expand while managing stress, food, and treasury.",
            ],
            [
                ("Begin", "accept", lambda: self.modal.close()),
                ("Realm Goals", "secondary", lambda: self._handle_action("view_realm")),
            ],
        )

    def _set_window_preset(self, mode):
        if mode == "desktop":
            self._apply_window_size_desktop()
        elif mode == "1280":
            self._apply_window_size((1280, 720), remember=True)
        elif mode == "1600":
            self._apply_window_size((1600, 900), remember=True)
        self._open_settings_modal()

    def _set_autosave_interval(self, months):
        months = int(months)
        self._autosave_interval_months = max(0, min(12, months))
        if self._autosave_interval_months == 0:
            self.push_log("Autosave disabled.")
        else:
            self.push_log(f"Autosave set to every {self._autosave_interval_months} month(s).")
        self._open_settings_modal()

    def _open_settings_modal(self):
        w, h = self.screen.get_size()
        if self._autosave_interval_months <= 0:
            autosave_line = "Autosave interval: Off."
        else:
            autosave_line = f"Autosave interval: every {self._autosave_interval_months} months."
        self.modal.show(
            "Settings",
            [
                f"Current window: {w}x{h}",
                "Choose a resolution preset for this session.",
                autosave_line,
            ],
            [
                ("1280x720", "primary", lambda: self._set_window_preset("1280")),
                ("1600x900", "secondary", lambda: self._set_window_preset("1600")),
                ("Autosave 1M", "secondary", lambda: self._set_autosave_interval(1)),
                ("Autosave 3M", "secondary", lambda: self._set_autosave_interval(3)),
                ("Autosave Off", "secondary", lambda: self._set_autosave_interval(0)),
                ("Close", "secondary", lambda: self.modal.close()),
            ],
        )

    def _ensure_save_dir(self):
        os.makedirs(self.save_dir, exist_ok=True)

    @staticmethod
    def _decode_int_map(raw, *, min_value=None, max_value=None):
        out = {}
        if not isinstance(raw, dict):
            return out
        for key, value in raw.items():
            try:
                ik = int(key)
                iv = int(value)
            except (TypeError, ValueError):
                continue
            if min_value is not None:
                iv = max(int(min_value), iv)
            if max_value is not None:
                iv = min(int(max_value), iv)
            out[ik] = iv
        return out

    def _serialize_world_state(self):
        provinces = []
        for prov in self.world.provinces:
            buildings = []
            for entry in getattr(prov, "buildings", []):
                if entry is None:
                    buildings.append(None)
                    continue
                bid = get_building_id(entry)
                if bid not in BUILDINGS:
                    buildings.append(None)
                    continue
                buildings.append({
                    "id": bid,
                    "level": max(1, int(get_building_level(entry))),
                })
            provinces.append({
                "id": int(prov.id),
                "realm_id": int(prov.realm_id),
                "population": int(prov.population),
                "buildings": buildings,
            })
        return {
            "provinces": provinces,
            "realm_capitals": list(getattr(self.world, "realm_capitals", [])),
            "realm_rulers": list(getattr(self.world, "realm_rulers", [])),
            "realm_sizes": list(getattr(self.world, "realm_sizes", [])),
        }

    def _serialize_game_state(self):
        return {
            "save_version": 2,
            "storyteller_id": self.storyteller.get("id") if isinstance(self.storyteller, dict) else None,
            "state": {
                "date": {"year": int(self.date.year), "month": int(self.date.month), "day": int(self.date.day)},
                "player_realm_id": int(self.player_realm_id),
                "resources": {
                    "gold": int(self.resources.get("gold", 0)),
                    "piety": int(self.resources.get("piety", 0)),
                    "prestige": int(self.resources.get("prestige", 0)),
                    "renown": int(self.resources.get("renown", 0)),
                },
                "realm_relations": {str(k): int(v) for k, v in self.realm_relations.items()},
                "realm_claims": sorted(int(v) for v in self.realm_claims),
                "realm_truces": {str(k): int(v) for k, v in self.realm_truces.items()},
                "claim_fabrication_cooldowns": {str(k): int(v) for k, v in self.claim_fabrication_cooldowns.items()},
                "alliances": sorted(int(v) for v in self.alliances),
                "subjugation_cooldown_days": int(self.subjugation_cooldown_days),
                "active_schemes": list(self.active_schemes),
                "hooks": {str(k): dict(v) for k, v in self.hooks.items()},
                "lifestyle_focus": str(self.lifestyle_focus),
                "lifestyle_xp": {k: float(v) for k, v in self.lifestyle_xp.items()},
                "lifestyle_perks": {k: int(v) for k, v in self.lifestyle_perks.items()},
                "stress": float(self.stress),
                "dread": float(self.dread),
                "decision_cooldowns": {str(k): int(v) for k, v in self.decision_cooldowns.items()},
                "raid_cooldown_days": int(self._raid_cooldown_days),
                "ai_war_cooldown_days": int(self._ai_war_cooldown_days),
                "wars": [
                    {
                        "id": int(war.get("id", 0)),
                        "target_id": int(war.get("target_id", -1)),
                        "war_type": str(war.get("war_type", "Conquest")),
                        "goal_pid": war.get("goal_pid"),
                        "progress": float(war.get("progress", 0.0)),
                        "days": int(war.get("days", 0)),
                        "ready_prompted": bool(war.get("ready_prompted", False)),
                        "sieged": sorted(int(pid) for pid in self._get_war_sieged_set(war)),
                        "total_provs": int(war.get("total_provs", 0)),
                        "attacker": str(war.get("attacker", "player")),
                    }
                    for war in self.wars
                ],
                "war_next_id": int(self._war_next_id),
                "war_focus_id": self._war_focus_id,
                "army": {
                    "raised": int(self.army.get("raised", 0)),
                    "morale": float(self.army.get("morale", 0)),
                    "raising": bool(self.army_raising),
                    "selected": bool(self.army_selected),
                    "prov_id": self.army_prov_id,
                    "route": list(self.army_route),
                },
                "enemy_armies": [
                    {
                        "realm_id": int(enemy.get("realm_id", -1)),
                        "prov_id": int(enemy.get("prov_id", -1)),
                        "army": {
                            "raised": int(enemy.get("army", {}).get("raised", 0)),
                            "max": int(enemy.get("army", {}).get("max", 0)),
                            "morale": float(enemy.get("army", {}).get("morale", 0)),
                        },
                        "raising": bool(enemy.get("raising", False)),
                        "route": list(enemy.get("route", [])),
                        "target_pid": enemy.get("target_pid"),
                        "ai_state": str(enemy.get("ai_state", "idle")),
                    }
                    for enemy in self.enemy_armies
                ],
                "selected_province_id": self.selected_province.id if self.selected_province is not None else None,
                "campaign_start_provinces": int(self._campaign_start_provinces),
                "campaign_target_provinces": int(self._campaign_target_provinces),
                "insolvency_days": int(self._insolvency_days),
                "famine_days": int(self._famine_days),
                "crisis_days": int(self._crisis_days),
                "campaign_result": self.campaign_result,
                "campaign_over_day": self._campaign_over_day,
                "last_played_realm_id": self.last_played_realm_id,
                "baseline_population": int(self._baseline_population),
                "log": list(self.log[-30:]),
            },
            "world": self._serialize_world_state(),
        }

    def _save_game_to_file(self, path=None, autosave=False):
        if self.mode != "game":
            if not autosave:
                self.modal.show(
                    "Save Unavailable",
                    ["Start a campaign before saving."],
                    [("OK", "accept", lambda: self.modal.close())],
                )
            return False
        if path is None:
            path = self.latest_save_path
        try:
            self._ensure_save_dir()
            payload = self._serialize_game_state()
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=True, indent=2)
        except OSError as exc:
            if not autosave:
                self.modal.show(
                    "Save Failed",
                    [f"Could not write save file: {exc}"],
                    [("OK", "accept", lambda: self.modal.close())],
                )
            return False

        if autosave:
            self.push_log(f"{self.date}: Autosaved campaign.")
            return True

        self.push_log(f"{self.date}: Saved campaign.")
        self.modal.show(
            "Game Saved",
            [f"Saved to {os.path.basename(path)}."],
            [("OK", "accept", lambda: self.modal.close())],
        )
        return True

    def _rebuild_realm_metadata(self, preferred_capitals=None):
        realm_n = len(self.world.realm_names)
        sizes = [0 for _ in range(realm_n)]
        first_prov = [-1 for _ in range(realm_n)]
        for prov in self.world.provinces:
            rid = int(prov.realm_id)
            if not (0 <= rid < realm_n):
                rid = 0
                prov.realm_id = rid
            sizes[rid] += 1
            if first_prov[rid] == -1:
                first_prov[rid] = prov.id

        capitals = [-1 for _ in range(realm_n)]
        if isinstance(preferred_capitals, list):
            for rid in range(min(realm_n, len(preferred_capitals))):
                try:
                    pid = int(preferred_capitals[rid])
                except (TypeError, ValueError):
                    continue
                if 0 <= pid < len(self.world.provinces) and self.world.provinces[pid].realm_id == rid:
                    capitals[rid] = pid
        for rid in range(realm_n):
            if capitals[rid] == -1:
                capitals[rid] = first_prov[rid]

        self.world.realm_sizes = sizes
        self.world.realm_capitals = capitals
        for prov in self.world.provinces:
            prov.is_capital = False
        for pid in capitals:
            if isinstance(pid, int) and 0 <= pid < len(self.world.provinces):
                self.world.provinces[pid].is_capital = True
        if 0 <= self.player_realm_id < len(capitals):
            self.world.player_capital_pid = capitals[self.player_realm_id]

    def _apply_loaded_state(self, payload):
        if not isinstance(payload, dict):
            return False, "Invalid save payload."
        state = payload.get("state")
        world_state = payload.get("world")
        if not isinstance(state, dict) or not isinstance(world_state, dict):
            return False, "Save file is missing required sections."

        try:
            rid = int(state.get("player_realm_id", self.player_realm_id))
        except (TypeError, ValueError):
            return False, "Save file has an invalid player realm id."
        if not (0 <= rid < len(self.world.realm_names)):
            return False, "Saved realm id is out of bounds for this map."

        self._start_game_for_realm(rid)

        date_data = state.get("date", {})
        try:
            year = int(date_data.get("year", self.date.year))
            month = int(date_data.get("month", self.date.month))
            day = int(date_data.get("day", self.date.day))
        except (TypeError, ValueError):
            year, month, day = self.date.year, self.date.month, self.date.day
        month = max(1, min(12, month))
        max_day = GameDate.MONTH_LEN[month - 1]
        day = max(1, min(max_day, day))
        self.date = GameDate(year, month, day)

        prov_data = world_state.get("provinces", [])
        if isinstance(prov_data, list):
            for idx, item in enumerate(prov_data):
                if not isinstance(item, dict):
                    continue
                try:
                    pid = int(item.get("id", idx))
                except (TypeError, ValueError):
                    continue
                if not (0 <= pid < len(self.world.provinces)):
                    continue
                prov = self.world.provinces[pid]
                try:
                    realm_id = int(item.get("realm_id", prov.realm_id))
                except (TypeError, ValueError):
                    realm_id = prov.realm_id
                if 0 <= realm_id < len(self.world.realm_names):
                    prov.realm_id = realm_id
                try:
                    population = int(item.get("population", prov.population))
                except (TypeError, ValueError):
                    population = prov.population
                prov.population = max(1, population)
                raw_buildings = item.get("buildings", [])
                parsed_buildings = []
                if isinstance(raw_buildings, list):
                    for entry in raw_buildings[:prov.building_slots]:
                        if entry is None:
                            parsed_buildings.append(None)
                            continue
                        if isinstance(entry, str):
                            if entry in BUILDINGS:
                                parsed_buildings.append(make_building(entry, level=1))
                            else:
                                parsed_buildings.append(None)
                            continue
                        if not isinstance(entry, dict):
                            parsed_buildings.append(None)
                            continue
                        bid = str(entry.get("id", ""))
                        if bid not in BUILDINGS:
                            parsed_buildings.append(None)
                            continue
                        try:
                            lvl = int(entry.get("level", 1))
                        except (TypeError, ValueError):
                            lvl = 1
                        parsed_buildings.append(make_building(bid, level=max(1, lvl)))
                while len(parsed_buildings) < prov.building_slots:
                    parsed_buildings.append(None)
                prov.buildings = parsed_buildings

        preferred_caps = world_state.get("realm_capitals")
        self._rebuild_realm_metadata(preferred_caps if isinstance(preferred_caps, list) else None)

        rulers = world_state.get("realm_rulers")
        if isinstance(rulers, list) and len(rulers) == len(self.world.realm_rulers):
            cleaned = []
            for idx, entry in enumerate(rulers):
                if not isinstance(entry, dict):
                    cleaned.append(self.world.realm_rulers[idx])
                    continue
                ruler = dict(entry)
                if "base_stats" not in ruler:
                    ruler["base_stats"] = _stats_list_to_dict(ruler.get("stats", []))
                ruler["traits"] = normalize_traits(ruler.get("traits", []))
                apply_trait_effects(ruler)
                cleaned.append(ruler)
            self.world.realm_rulers = cleaned

        resources = state.get("resources", {})
        if isinstance(resources, dict):
            for key in ("gold", "piety", "prestige", "renown"):
                try:
                    self.resources[key] = int(resources.get(key, self.resources.get(key, 0)))
                except (TypeError, ValueError):
                    pass

        self.realm_relations = self._decode_int_map(state.get("realm_relations", {}), min_value=-100, max_value=100)
        self.realm_claims = set(
            int(v) for v in state.get("realm_claims", [])
            if isinstance(v, (int, float, str)) and str(v).lstrip("-").isdigit()
        )
        self.realm_claims = {rid for rid in self.realm_claims if 0 <= rid < len(self.world.realm_names)}
        self.realm_truces = self._decode_int_map(state.get("realm_truces", {}), min_value=0)
        self.claim_fabrication_cooldowns = self._decode_int_map(
            state.get("claim_fabrication_cooldowns", {}),
            min_value=0,
        )
        self.alliances = set(
            int(v) for v in state.get("alliances", [])
            if isinstance(v, (int, float, str)) and str(v).lstrip("-").isdigit()
        )
        self.alliances = {rid for rid in self.alliances if 0 <= rid < len(self.world.realm_names)}
        self.subjugation_cooldown_days = max(0, int(state.get("subjugation_cooldown_days", 0)))

        self.active_schemes = []
        for entry in state.get("active_schemes", []):
            if not isinstance(entry, dict):
                continue
            stype = entry.get("type")
            if stype not in ("sway", "claim", "murder"):
                continue
            try:
                target = int(entry.get("target_id"))
            except (TypeError, ValueError):
                continue
            if not (0 <= target < len(self.world.realm_names)) or target == self.player_realm_id:
                continue
            self.active_schemes.append(
                {
                    "id": int(entry.get("id", self._next_scheme_id)),
                    "type": stype,
                    "target_id": target,
                    "category": self._scheme_category(stype),
                    "progress": float(clamp(float(entry.get("progress", 0.0)), 0.0, 100.0)),
                    "days": max(0, int(entry.get("days", 0))),
                    "base_power": float(entry.get("base_power", 0.8)),
                    "success_chance": float(clamp(float(entry.get("success_chance", 0.5)), 0.05, 0.95)),
                    "exposure_chance": float(clamp(float(entry.get("exposure_chance", 0.35)), 0.05, 0.95)),
                    "min_days": max(20, int(entry.get("min_days", 45))),
                }
            )
        self._next_scheme_id = max(
            int(state.get("next_scheme_id", 1)),
            max((int(s.get("id", 0)) for s in self.active_schemes), default=0) + 1,
        )

        self.hooks = {}
        hooks_data = state.get("hooks", {})
        if isinstance(hooks_data, dict):
            for key, value in hooks_data.items():
                try:
                    rid_key = int(key)
                except (TypeError, ValueError):
                    continue
                if not isinstance(value, dict):
                    continue
                strength = "strong" if value.get("strength") == "strong" else "weak"
                days = max(1, int(value.get("days", 1)))
                self.hooks[rid_key] = {"strength": strength, "days": days}

        focus = str(state.get("lifestyle_focus", self.lifestyle_focus))
        if focus in self.lifestyle_focuses:
            self.lifestyle_focus = focus
            self._lifestyle_picker_index = self.lifestyle_focuses.index(focus)
        xp_data = state.get("lifestyle_xp", {})
        perk_data = state.get("lifestyle_perks", {})
        self.lifestyle_xp = {}
        self.lifestyle_perks = {}
        for key in self.lifestyle_focuses:
            try:
                self.lifestyle_xp[key] = float((xp_data or {}).get(key, 0.0))
            except (TypeError, ValueError):
                self.lifestyle_xp[key] = 0.0
            try:
                self.lifestyle_perks[key] = max(0, int((perk_data or {}).get(key, 0)))
            except (TypeError, ValueError):
                self.lifestyle_perks[key] = 0

        self.stress = clamp(float(state.get("stress", self.stress)), 0.0, 300.0)
        self._stress_break_level = int(self.stress // 100)
        self.dread = clamp(float(state.get("dread", self.dread)), 0.0, 100.0)
        self.decision_cooldowns = self._decode_int_map(state.get("decision_cooldowns", {}), min_value=0)
        self._raid_cooldown_days = max(0, int(state.get("raid_cooldown_days", 45)))
        self._ai_war_cooldown_days = max(0, int(state.get("ai_war_cooldown_days", 120)))

        self.wars = []
        for entry in state.get("wars", []):
            if not isinstance(entry, dict):
                continue
            try:
                war_id = int(entry.get("id", 0))
                target_id = int(entry.get("target_id", -1))
            except (TypeError, ValueError):
                continue
            if not (0 <= target_id < len(self.world.realm_names)):
                continue
            goal_pid = entry.get("goal_pid")
            if isinstance(goal_pid, (int, float, str)) and str(goal_pid).lstrip("-").isdigit():
                goal_pid = int(goal_pid)
            else:
                goal_pid = None
            sieged = set()
            for pid in entry.get("sieged", []):
                try:
                    pid = int(pid)
                except (TypeError, ValueError):
                    continue
                if 0 <= pid < len(self.world.provinces):
                    sieged.add(pid)
            war = {
                "id": war_id,
                "target_id": target_id,
                "war_type": str(entry.get("war_type", "Conquest")),
                "goal_pid": goal_pid,
                "progress": float(clamp(float(entry.get("progress", 0.0)), 0.0, 100.0)),
                "days": max(0, int(entry.get("days", 0))),
                "ready_prompted": bool(entry.get("ready_prompted", False)),
                "sieged": sieged,
                "total_provs": max(0, int(entry.get("total_provs", 0))),
                "attacker": str(entry.get("attacker", "player")),
            }
            self.wars.append(war)
        self._war_next_id = max(
            int(state.get("war_next_id", 1)),
            max((int(w.get("id", 0)) for w in self.wars), default=0) + 1,
        )
        focus_id = state.get("war_focus_id")
        if isinstance(focus_id, (int, float, str)) and str(focus_id).lstrip("-").isdigit():
            focus_id = int(focus_id)
        else:
            focus_id = None
        self._war_focus_id = focus_id if any(w.get("id") == focus_id for w in self.wars) else (self.wars[0]["id"] if self.wars else None)

        army_data = state.get("army", {})
        if not isinstance(army_data, dict):
            army_data = {}
        self.army["raised"] = max(0, int(army_data.get("raised", 0)))
        self.army["morale"] = clamp(float(army_data.get("morale", 60.0)), 0.0, 100.0)
        self.army_raising = bool(army_data.get("raising", False))
        self.army_selected = bool(army_data.get("selected", False))
        self.army_prov_id = None
        try:
            pid = int(army_data.get("prov_id"))
            if 0 <= pid < len(self.world.provinces):
                self.army_prov_id = pid
        except (TypeError, ValueError):
            pass
        self.army_route = []
        for pid in army_data.get("route", []):
            try:
                pid = int(pid)
            except (TypeError, ValueError):
                continue
            if 0 <= pid < len(self.world.provinces):
                self.army_route.append(pid)
        self.army_step_from = None
        self.army_step_to = None
        self.army_step_progress = 0.0
        if self.army_prov_id is not None:
            self.army_pos = self.world.provinces[self.army_prov_id].center.copy()
        else:
            self.army_pos = None

        self.enemy_armies = []
        for entry in state.get("enemy_armies", []):
            if not isinstance(entry, dict):
                continue
            try:
                rid_enemy = int(entry.get("realm_id", -1))
                pid_enemy = int(entry.get("prov_id", -1))
            except (TypeError, ValueError):
                continue
            if not (0 <= rid_enemy < len(self.world.realm_names)):
                continue
            if not (0 <= pid_enemy < len(self.world.provinces)):
                continue
            army_entry = entry.get("army", {})
            if not isinstance(army_entry, dict):
                army_entry = {}
            enemy = {
                "realm_id": rid_enemy,
                "prov_id": pid_enemy,
                "pos": self.world.provinces[pid_enemy].center.copy(),
                "army": {
                    "raised": max(0, int(army_entry.get("raised", 0))),
                    "max": max(1, int(army_entry.get("max", 1))),
                    "morale": clamp(float(army_entry.get("morale", 55)), 0.0, 100.0),
                },
                "raising": bool(entry.get("raising", False)),
                "route": [int(v) for v in entry.get("route", []) if isinstance(v, int) and 0 <= v < len(self.world.provinces)],
                "target_pid": entry.get("target_pid") if isinstance(entry.get("target_pid"), int) else None,
                "ai_state": str(entry.get("ai_state", "idle")),
            }
            self.enemy_armies.append(enemy)
        if not self.enemy_armies:
            self._init_enemy_armies()

        self.campaign_result = state.get("campaign_result")
        self._campaign_start_provinces = max(1, int(state.get("campaign_start_provinces", self._campaign_start_provinces)))
        self._campaign_target_provinces = max(
            self._campaign_start_provinces + 1,
            int(state.get("campaign_target_provinces", self._campaign_target_provinces)),
        )
        self._insolvency_days = max(0, int(state.get("insolvency_days", 0)))
        self._famine_days = max(0, int(state.get("famine_days", 0)))
        self._crisis_days = max(0, int(state.get("crisis_days", 0)))
        self._campaign_over_day = state.get("campaign_over_day")
        self.last_played_realm_id = int(state.get("last_played_realm_id", self.player_realm_id))

        sel_pid = state.get("selected_province_id")
        if isinstance(sel_pid, int) and 0 <= sel_pid < len(self.world.provinces):
            self.selected_province = self.world.provinces[sel_pid]
        else:
            cap_pid = self._get_player_capital_pid()
            self.selected_province = self.world.provinces[cap_pid] if cap_pid is not None and 0 <= cap_pid < len(self.world.provinces) else None

        log_data = state.get("log", [])
        if isinstance(log_data, list):
            self.log = [str(line) for line in log_data[-30:]]

        self.character = self.world.realm_rulers[self.player_realm_id]
        if "base_stats" not in self.character:
            self.character["base_stats"] = _stats_list_to_dict(self.character.get("stats", []))
        self.character["traits"] = normalize_traits(self.character.get("traits", []))
        apply_trait_effects(self.character)

        self.population = self.world.total_population_for_realm(self.player_realm_id)
        self._baseline_population = max(1, int(state.get("baseline_population", self.population)))
        self.food = self._compute_food_values()
        self.threat = self._compute_threat()
        self._update_army_max()
        self._recompute_resource_rates()

        self._war_goal_selecting = False
        self._pending_war = None
        self._siege_state = None
        self._war_border_overlay = None
        self._war_border_overlay_key = None
        self._update_fog_from_army()

        if hasattr(self.world, "_realm_border_cache"):
            self.world._realm_border_cache = {}
        self.world._realm_border_points = None
        if hasattr(self.world, "_compute_fog_of_war"):
            self.world._compute_fog_of_war()
        if hasattr(self.world, "_render_borders_and_coast"):
            self.world._render_borders_and_coast()
        self._refresh_fog_visuals()
        return True, "Loaded"

    def _load_game_from_file(self, path, show_feedback=True):
        if not path or not os.path.exists(path):
            self.modal.show(
                "Load Failed",
                ["Save file was not found."],
                [("OK", "accept", lambda: self.modal.close())],
            )
            return False
        try:
            with open(path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            self.modal.show(
                "Load Failed",
                [f"Could not read save file: {exc}"],
                [("OK", "accept", lambda: self.modal.close())],
            )
            return False

        ok, msg = self._apply_loaded_state(payload)
        if not ok:
            self.modal.show(
                "Load Failed",
                [msg],
                [("OK", "accept", lambda: self.modal.close())],
            )
            return False

        sid = payload.get("storyteller_id")
        if sid:
            st = next((s for s in self.storytellers if s.get("id") == sid), None)
            if st:
                self._apply_storyteller(st)

        self.mode = "game"
        self.camera.set_viewport(self._get_map_rect().size)
        self.left_panel_open = False
        self._left_panel_anim = 0.0
        self.right_panel_open = True
        self._right_panel_anim = 1.0
        self.speed_level = 0
        if show_feedback:
            self.modal.show(
                "Game Loaded",
                [f"Loaded {os.path.basename(path)}."],
                [("Continue", "accept", lambda: self.modal.close())],
            )
        return True

    def _open_load_game_modal(self):
        saves = []
        if os.path.exists(self.latest_save_path):
            saves.append(("Latest", self.latest_save_path))
        if os.path.exists(self.autosave_path):
            saves.append(("Autosave", self.autosave_path))

        can_resume_session = (
            self.mode == "menu"
            and isinstance(self.last_played_realm_id, int)
            and 0 <= self.last_played_realm_id < len(self.world.realm_names)
        )

        if not saves and not can_resume_session:
            self.modal.show(
                "No Save Found",
                ["No save files are available yet."],
                [("OK", "accept", lambda: self.modal.close())],
            )
            return

        lines = ["Select a save file to load:"]
        if can_resume_session:
            rid = int(self.last_played_realm_id)
            realm_name = self.world.realm_names[rid] if 0 <= rid < len(self.world.realm_names) else f"Realm {rid}"
            lines.append(f"Session Resume: {realm_name}")
        for label, path in saves:
            lines.append(f"{label}: {os.path.basename(path)}")
        actions = []
        if can_resume_session:
            resume_style = "primary" if not saves else "secondary"
            actions.append(("Session Resume", resume_style, lambda: self._resume_last_realm_from_menu()))
        for idx, (label, path) in enumerate(saves):
            style = "accept" if idx == 0 and not can_resume_session else "secondary"
            actions.append((f"Load {label}", style, (lambda p=path: self._load_game_from_file(p, show_feedback=True))))
        actions.append(("Cancel", "secondary", lambda: self.modal.close()))
        self.modal.show("Load Game", lines, actions)

    def _resume_last_realm_from_menu(self):
        rid = self.last_played_realm_id
        if rid is None or not (0 <= rid < len(self.world.realm_names)):
            self.modal.show(
                "No Campaign Available",
                [
                    "No previous realm is available in this session.",
                ],
                [
                    ("OK", "accept", lambda: self.modal.close()),
                ],
            )
            return
        if not self.storyteller and self.storytellers:
            self._apply_storyteller(self.storytellers[0])
        self._start_game_for_realm(rid)
        self.mode = "game"
        self.camera.set_viewport(self._get_map_rect().size)
        self.left_panel_open = False
        self._left_panel_anim = 0.0
        self.right_panel_open = True
        self._right_panel_anim = 1.0
        self._open_campaign_briefing()

    def _return_to_main_menu(self):
        self.modal.close()
        self.mode = "menu"
        self.speed_level = 0
        self.selected_province = None
        self.left_panel_open = False
        self.right_panel_open = False
        self._left_panel_anim = 0.0
        self._right_panel_anim = 0.0
        self._war_goal_selecting = False
        self._pending_war = None

    def _left_panel_draw_rect(self):
        rect = self.layout.left
        offset = -int((1.0 - self._left_panel_anim) * rect.w)
        return rect.move(offset, 0)

    def _point_in_ui(self, pos):
        if self.mode == "realm_select":
            return any(r.collidepoint(pos) for r in self._realm_ui_rects)
        if self.mode == "game":
            if self.layout.top.collidepoint(pos):
                return True
            if self._bottom_bar_rect and self._bottom_bar_rect.collidepoint(pos):
                return True
            if self._left_panel_anim > 0.01 and self._left_panel_draw_rect().collidepoint(pos):
                return True
            if self._left_panel_toggle_rect and self._left_panel_toggle_rect.collidepoint(pos):
                return True
            if self._right_panel_anim > 0.01 and self.layout.right.collidepoint(pos):
                return True
            if self._war_float_rects and any(r.collidepoint(pos) for r in self._war_float_rects):
                return True
        return False

    def _draw_selected_province_highlight(self, surface, map_rect):
        if self.selected_province is None:
            return
        sp = self.camera.world_to_screen(self.selected_province.center, map_rect, use_target=False)
        x, y = int(sp.x), int(sp.y)
        if not map_rect.collidepoint(x, y):
            return
        t = pygame.time.get_ticks() / 350.0
        pulse = 0.5 + 0.5 * math.sin(t)
        base = 14
        ring = base + int(8 * pulse)
        pygame.draw.circle(surface, (250, 220, 120), (x, y), ring, 3)
        pygame.draw.circle(surface, (255, 245, 230), (x, y), base, 2)

    def _get_war_border_overlay(self):
        if not self.wars:
            self._war_border_overlay = None
            self._war_border_overlay_key = None
            return None, None
        targets = tuple(sorted({war.get("target_id") for war in self.wars if war.get("target_id") is not None}))
        if not targets:
            self._war_border_overlay = None
            self._war_border_overlay_key = None
            return None, None
        if targets == self._war_border_overlay_key and self._war_border_overlay is not None:
            return self._war_border_overlay, targets

        overlay = pygame.Surface((self.world.world_w, self.world.world_h), pygame.SRCALPHA)
        has_any = False
        for rid in targets:
            border = self.world.get_realm_border_surface(rid)
            if border is None:
                continue
            overlay.blit(border, (0, 0))
            has_any = True

        if not has_any:
            self._war_border_overlay = None
            self._war_border_overlay_key = None
            return None, None

        self._war_border_overlay = overlay
        self._war_border_overlay_key = targets
        return overlay, targets

    def _get_all_sieged_provinces(self):
        sieged = set()
        for war in self.wars:
            sieged.update(self._get_war_sieged_set(war))
        return sieged

    def _get_siege_stripe_base(self):
        key = (self.world.world_w, self.world.world_h)
        if self._siege_stripe_base is not None and self._siege_stripe_base_key == key:
            return self._siege_stripe_base

        tile_size = 24
        stripe_gap = 6
        stripe = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
        stripe.fill((0, 0, 0, 0))
        stripe_color = (235, 225, 205, 70)
        for x in range(-tile_size, tile_size * 2, stripe_gap):
            pygame.draw.line(stripe, stripe_color, (x, 0), (x + tile_size, tile_size), 2)

        base = pygame.Surface((self.world.world_w, self.world.world_h), pygame.SRCALPHA)
        tile_fill(base, base.get_rect(), stripe)
        self._siege_stripe_base = base
        self._siege_stripe_base_key = key
        return base

    def _build_siege_overlay(self, sieged_set):
        if not sieged_set:
            return None

        mask = pygame.Surface((self.world.gw, self.world.gh), pygame.SRCALPHA)
        for y in range(self.world.gh):
            row = self.world.prov_id[y]
            for x in range(self.world.gw):
                pid = row[x]
                if pid >= 0 and pid in sieged_set:
                    mask.set_at((x, y), (255, 255, 255, 255))

        mask_big = pygame.transform.scale(mask, (self.world.world_w, self.world.world_h))
        overlay = self._get_siege_stripe_base().copy()
        overlay.blit(mask_big, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return overlay

    def _get_siege_overlay(self):
        sieged = self._get_all_sieged_provinces()
        if not sieged:
            self._siege_overlay = None
            self._siege_overlay_key = None
            return None, None

        key = tuple(sorted(sieged))
        if key == self._siege_overlay_key and self._siege_overlay is not None:
            return self._siege_overlay, key

        overlay = self._build_siege_overlay(sieged)
        if overlay is None:
            self._siege_overlay = None
            self._siege_overlay_key = None
            return None, None

        self._siege_overlay = overlay
        self._siege_overlay_key = key
        return overlay, key

    def _draw_army_stack(self, surface, map_rect, pos, raised, max_army, friendly=True, selected=False):
        if max_army <= 0:
            return
        ratio = 0.0 if max_army <= 0 else max(0.0, min(1.0, raised / max_army))
        sp = self.camera.world_to_screen(pos, map_rect, use_target=False)
        x, y = int(sp.x), int(sp.y)
        if not map_rect.collidepoint(x, y):
            return

        # CK2-style stack icon: number + vertical morale/raise bar
        body_w, body_h = 64, 22
        bar_w = 7
        body_rect = pygame.Rect(x - body_w // 2, y - 30, body_w, body_h)
        body_bg = (30, 75, 35) if friendly else (90, 35, 35)
        pygame.draw.rect(surface, body_bg, body_rect, border_radius=3)
        pygame.draw.rect(surface, (8, 8, 10), body_rect, 1, border_radius=3)

        # right vertical bar (red background + green fill)
        bar_rect = pygame.Rect(body_rect.right - bar_w - 2, body_rect.top + 2, bar_w, body_rect.h - 4)
        pygame.draw.rect(surface, (130, 35, 35), bar_rect, border_radius=2)
        fill_h = int(bar_rect.h * ratio)
        if fill_h > 0:
            fill_rect = pygame.Rect(bar_rect.left, bar_rect.bottom - fill_h, bar_rect.w, fill_h)
            pygame.draw.rect(surface, (65, 150, 70), fill_rect, border_radius=2)
        pygame.draw.rect(surface, (0, 0, 0), bar_rect, 1, border_radius=2)

        # troop count
        raised_text = f"{int(raised):,}"
        label = FOOTER_FONT.render(raised_text, True, (235, 228, 210))
        label_rect = label.get_rect(center=(body_rect.centerx - bar_w // 2, body_rect.centery))
        surface.blit(label, label_rect)

        if selected:
            pygame.draw.rect(surface, (230, 210, 120), body_rect.inflate(6, 6), 2, border_radius=4)

    def _draw_army_muster_marker(self, surface, map_rect):
        if self.army.get("raised", 0) <= 0 and not self.army_raising:
            return
        if self.army_pos is None:
            return
        max_army = int(self.army.get("max", 0))
        raised = int(self.army.get("raised", 0))
        friendly = False
        if self.army_prov_id is not None and 0 <= self.army_prov_id < len(self.world.provinces):
            friendly = self.world.provinces[self.army_prov_id].realm_id == self.player_realm_id
        self._draw_army_stack(
            surface,
            map_rect,
            self.army_pos,
            raised,
            max_army,
            friendly=friendly,
            selected=self.army_selected,
        )

    def _draw_enemy_armies(self, surface, map_rect):
        if not self.enemy_armies:
            return
        for enemy in self.enemy_armies:
            army = enemy.get("army", {})
            raised = int(army.get("raised", 0))
            max_army = int(army.get("max", 0))
            if raised <= 0 or max_army <= 0:
                continue
            pid = enemy.get("prov_id")
            if pid is None or not (0 <= pid < len(self.world.provinces)):
                continue
            if not self._is_province_visible(pid):
                continue
            pos = enemy.get("pos")
            if pos is None:
                pos = self.world.provinces[pid].center
            self._draw_army_stack(surface, map_rect, pos, raised, max_army, friendly=False, selected=False)

    def _draw_army_route_arrow(self, surface, map_rect):
        def draw_arrow_head(p0, p1, color, width=3):
            vx = p1[0] - p0[0]
            vy = p1[1] - p0[1]
            length = max(1.0, math.hypot(vx, vy))
            ux, uy = vx / length, vy / length
            left = (p1[0] - ux * 10 - uy * 6, p1[1] - uy * 10 + ux * 6)
            right = (p1[0] - ux * 10 + uy * 6, p1[1] - uy * 10 - ux * 6)
            pygame.draw.polygon(surface, color, [p1, left, right])

        if not self.army_route or self.army_pos is None:
            return
        if self.army_step_to is None:
            return

        points_world = [self.army_pos] + [self.world.provinces[pid].center for pid in self.army_route]
        if len(points_world) < 2:
            return

        points = [
            (int(self.camera.world_to_screen(p, map_rect, use_target=False).x),
             int(self.camera.world_to_screen(p, map_rect, use_target=False).y))
            for p in points_world
        ]

        # White base arrow path
        pygame.draw.lines(surface, (230, 230, 230), False, points, 3)
        draw_arrow_head(points[-2], points[-1], (230, 230, 230), width=3)

        # Red fill along the first segment only (progress to next province)
        p0, p1 = points[0], points[1]
        progress = max(0.0, min(1.0, self.army_step_progress))
        mid = (p0[0] + (p1[0] - p0[0]) * progress, p0[1] + (p1[1] - p0[1]) * progress)
        pygame.draw.line(surface, (200, 60, 60), p0, mid, 4)

    def _draw_siege_status(self, surface, map_rect):
        if not self._siege_state:
            return
        pid = self._siege_state.get("pid")
        if pid is None or not (0 <= pid < len(self.world.provinces)):
            return
        if not self._is_province_visible(pid):
            return

        prep_days = int(self._siege_state.get("prep_days", 1))
        assault_days = int(self._siege_state.get("assault_days", 1))
        stage = self._siege_state.get("stage", "prep")
        days = int(self._siege_state.get("days", 0))
        total_days = max(1, prep_days + assault_days)
        if stage == "prep":
            elapsed = max(0, min(days, prep_days))
            remaining = max(0, prep_days - days + assault_days)
            stage_label = "Prep"
        else:
            elapsed = prep_days + max(0, min(days, assault_days))
            remaining = max(0, assault_days - days)
            stage_label = "Siege"

        progress = max(0.0, min(1.0, elapsed / total_days))

        sp = self.camera.world_to_screen(self.world.provinces[pid].center, map_rect, use_target=False)
        x, y = int(sp.x), int(sp.y)
        if not map_rect.collidepoint(x, y):
            return

        w, h = 110, 34
        panel = pygame.Rect(0, 0, w, h)
        panel.center = (x, y - 42)

        pygame.draw.rect(surface, (20, 18, 16), panel, border_radius=6)
        pygame.draw.rect(surface, (0, 0, 0), panel, 2, border_radius=6)

        bar_pad = 6
        bar_h = 6
        bar = pygame.Rect(panel.left + bar_pad, panel.bottom - bar_pad - bar_h, panel.w - bar_pad * 2, bar_h)
        pygame.draw.rect(surface, (70, 62, 50), bar, border_radius=3)
        fill_w = int(bar.w * progress)
        if fill_w > 0:
            fill = pygame.Rect(bar.left, bar.top, fill_w, bar.h)
            pygame.draw.rect(surface, (180, 120, 60), fill, border_radius=3)

        label = FOOTER_FONT.render(f"{stage_label} {remaining}d", True, (230, 220, 200))
        surface.blit(label, label.get_rect(center=(panel.centerx, panel.centery - 4)))

    def _is_province_visible(self, pid):
        vis = self.world.visibility_by_prov.get(pid, 0.45)
        if vis >= 0.78:
            return True
        return pid in getattr(self.world, "extra_visible_provs", set())

    def _army_icon_rect(self, map_rect):
        if self.army_pos is None:
            return None
        if self.army.get("raised", 0) <= 0 and not self.army_raising:
            return None
        sp = self.camera.world_to_screen(self.army_pos, map_rect, use_target=False)
        x, y = int(sp.x), int(sp.y)
        return pygame.Rect(x - 32, y - 30, 64, 22)

    def _handle_army_click(self, screen_pos, map_rect):
        icon = self._army_icon_rect(map_rect)
        if icon and icon.collidepoint(screen_pos):
            if self.army.get("raised", 0) <= 0 and not self.army_raising:
                return True
            self.army_selected = not self.army_selected
            if self.army_selected:
                self.selected_province = None
                self._building_menu_slot = None
                self.push_log(f"{self.date}: Army selected.")
            return True
        return False

    def _handle_army_move(self, screen_pos, map_rect):
        if not self.army_selected:
            return False
        if self.army.get("raised", 0) <= 0:
            self.push_log("Army is still mustering.")
            return True
        wp = self.camera.screen_to_world(screen_pos, map_rect, use_target=False)
        prov = self.world.province_at_world(wp)
        if prov is None:
            return True
        self._ensure_army_position()
        start_pid = self.army_prov_id
        if start_pid is None:
            return True
        if prov.id == start_pid:
            self.army_route = []
            self.army_step_from = None
            self.army_step_to = None
            self.army_step_progress = 0.0
            return True
        route = self._find_province_path(start_pid, prov.id)
        if not route:
            self.push_log("No route for the army.")
            return True
        self.army_route = route
        self.army_step_from = start_pid
        self.army_step_to = route[0]
        self.army_step_progress = 0.0
        self.push_log(f"{self.date}: Army marching to {prov.name}.")
        return True

    def _draw_right_panel_animated(self, surface, state):
        if self._right_panel_anim <= 0.01:
            return []
        rect = self.layout.right
        offset = int((1.0 - self._right_panel_anim) * rect.w)
        draw_rect = rect.move(offset, 0)
        panel_layer = pygame.Surface(rect.size, pygame.SRCALPHA)
        btns_local = self.ui.draw_right_panel(panel_layer, panel_layer.get_rect(), state)
        panel_layer.set_alpha(int(255 * self._right_panel_anim))
        surface.blit(panel_layer, draw_rect.topleft)

        btns = []
        for r, action in btns_local:
            btns.append((r.move(draw_rect.left, draw_rect.top), action))
        return btns

    def _draw_left_panel_animated(self, surface, state):
        if self._left_panel_anim <= 0.01:
            self._left_panel_toggle_rect = None
            btns = self.ui.draw_left_panel_toggle(surface, self.layout.left, state)
            if btns:
                self._left_panel_toggle_rect = btns[0][0]
            return btns

        self._left_panel_toggle_rect = None
        rect = self.layout.left
        draw_rect = self._left_panel_draw_rect()

        panel_layer = pygame.Surface(rect.size, pygame.SRCALPHA)
        btns_local = self.ui.draw_left_panel(panel_layer, panel_layer.get_rect(), state, show_close=True)
        panel_layer.set_alpha(int(255 * self._left_panel_anim))
        surface.blit(panel_layer, draw_rect.topleft)

        btns = []
        for r, action in btns_local:
            btns.append((r.move(draw_rect.left, draw_rect.top), action))
        return btns

    def _get_desktop_size(self):
        if hasattr(pygame.display, "get_desktop_sizes"):
            sizes = pygame.display.get_desktop_sizes()
            if sizes:
                w, h = sizes[0]
                if w > 0 and h > 0:
                    return int(w), int(h)
        info = pygame.display.Info()
        if info.current_w > 0 and info.current_h > 0:
            return int(info.current_w), int(info.current_h)
        return self.windowed_size

    def _apply_window_size_desktop(self):
        # Let SDL pick the desktop-sized window, but keep it resizable.
        self.screen = pygame.display.set_mode((0, 0), pygame.RESIZABLE)
        w, h = self.screen.get_size()
        if w <= 0 or h <= 0:
            w, h = self._get_desktop_size()
            self.screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
        self.windowed_size = (w, h)
        self._center_window()
        self.layout.update(w, h)
        self.camera.set_viewport(self._get_map_rect().size)

    def _apply_window_size(self, size, remember=True):
        w = max(1024, int(size[0]))
        h = max(640, int(size[1]))
        if remember:
            self.windowed_size = (w, h)
        self.screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
        self._center_window()
        self.layout.update(w, h)
        self.camera.set_viewport(self._get_map_rect().size)

    def _center_window(self):
        if not hasattr(pygame.display, "set_window_position"):
            return
        w, h = self.screen.get_size()
        sw, sh = self._get_desktop_size()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        pygame.display.set_window_position(x, y)

    def _draw_menu_button(self, surface, rect, text, enabled=True):
        mx, my = pygame.mouse.get_pos()
        hovered = enabled and rect.collidepoint(mx, my)
        if enabled:
            bg = (55, 55, 60) if not hovered else (80, 80, 90)
            border = (10, 10, 10)
            text_color = (235, 228, 210)
        else:
            bg = (35, 35, 38)
            border = (18, 18, 20)
            text_color = (140, 135, 125)
        pygame.draw.rect(surface, bg, rect, border_radius=6)
        pygame.draw.rect(surface, border, rect, width=2, border_radius=6)
        label = self.menu_button_font.render(text, True, text_color)
        surface.blit(label, label.get_rect(center=rect.center))
        return rect

    @staticmethod
    def _ellipsize(text, font, max_w):
        if font.size(text)[0] <= max_w:
            return text
        ell = "..."
        max_w -= font.size(ell)[0]
        if max_w <= 0:
            return ell
        trimmed = text
        while trimmed and font.size(trimmed)[0] > max_w:
            trimmed = trimmed[:-1]
        return trimmed.rstrip() + ell

    def _draw_main_menu(self, surface):
        self._draw_menu_background(surface)

        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 95))
        surface.blit(overlay, (0, 0))

        w, h = surface.get_size()
        title = "Ascention"
        subtitle = "northen lords"

        title_surf = self.menu_title_font.render(title, True, (235, 228, 210))
        subtitle_surf = self.menu_subtitle_font.render(subtitle, True, (210, 202, 185))

        title_rect = title_surf.get_rect(center=(w // 2, int(h * 0.18)))
        subtitle_rect = subtitle_surf.get_rect(center=(w // 2, title_rect.bottom + 18))

        shadow = self.menu_title_font.render(title, True, (0, 0, 0))
        surface.blit(shadow, (title_rect.x + 3, title_rect.y + 3))
        surface.blit(title_surf, title_rect)
        surface.blit(subtitle_surf, subtitle_rect)

        btn_w = min(420, int(w * 0.55))
        btn_h = 46
        gap = 12
        start_y = int(h * 0.45)
        left = (w - btn_w) // 2

        labels = [
            ("Start Game", "menu_start"),
            ("Load Game", "menu_load"),
            ("Settings", "menu_settings"),
        ]

        clickables = []
        for i, (label, action) in enumerate(labels):
            rect = pygame.Rect(left, start_y + i * (btn_h + gap), btn_w, btn_h)
            self._draw_menu_button(surface, rect, label)
            clickables.append((rect, action))
        return clickables

    def _draw_storyteller_menu(self, surface):
        self._draw_menu_background(surface)

        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 110))
        surface.blit(overlay, (0, 0))

        w, h = surface.get_size()
        title_surf = self.menu_header_font.render("Choose Storyteller", True, (235, 228, 210))
        subtitle_surf = self.menu_subtitle_font.render(
            "Storytellers shape how often events appear.",
            True,
            (210, 202, 185),
        )
        surface.blit(title_surf, title_surf.get_rect(center=(w // 2, int(h * 0.16))))
        surface.blit(subtitle_surf, subtitle_surf.get_rect(center=(w // 2, int(h * 0.22))))

        clickables = []
        total = max(1, len(self.storytellers))
        gap = 16
        top = int(h * 0.3)
        bottom_margin = 70
        available_h = max(0, h - top - bottom_margin)
        card_h = int((available_h - gap * (total - 1)) / total) if total > 0 else 180
        card_h = max(140, min(220, card_h))
        card_w = min(720, int(w * 0.82))
        left = (w - card_w) // 2

        for idx, st in enumerate(self.storytellers):
            card_rect = pygame.Rect(left, top + idx * (card_h + gap), card_w, card_h)
            pygame.draw.rect(surface, (26, 26, 30), card_rect, border_radius=10)
            pygame.draw.rect(surface, (8, 8, 8), card_rect, 2, border_radius=10)

            portrait_size = max(60, card_h - 32)
            portrait_rect = pygame.Rect(card_rect.left + 16, card_rect.top + 16, portrait_size, portrait_size)
            pygame.draw.rect(surface, (18, 18, 22), portrait_rect, border_radius=6)
            pygame.draw.rect(surface, (8, 8, 10), portrait_rect, 2, border_radius=6)

            portrait = self._get_storyteller_portrait(st["id"], portrait_rect.size)
            if portrait is not None:
                pr = portrait.get_rect(center=portrait_rect.center)
                surface.blit(portrait, pr)

            text_x = portrait_rect.right + 16
            text_w = card_rect.right - text_x - 16
            name_surf = self.menu_subtitle_font.render(st["name"], True, (235, 228, 210))
            surface.blit(name_surf, (text_x, card_rect.top + 14))

            desc_lines = wrap_text(st["desc"], self.menu_caption_font, text_w)
            y = card_rect.top + 48
            desc_limit = card_rect.bottom - 52
            for line in desc_lines:
                line_surf = self.menu_caption_font.render(line, True, (200, 192, 175))
                if y + line_surf.get_height() > desc_limit:
                    break
                surface.blit(line_surf, (text_x, y))
                y += line_surf.get_height() + 3

            mult = float(st.get("event_chance_mult", 1.0))
            ramp = float(st.get("event_chance_ramp_per_year", 0.0))
            max_mult = float(st.get("event_chance_max_mult", mult))
            if ramp > 0 and max_mult > mult:
                detail = f"Event rate: x{mult:.2f} -> x{max_mult:.2f} over time"
            else:
                detail = f"Event rate: x{mult:.2f}"
            detail_surf = self.menu_caption_font.render(detail, True, (178, 170, 156))
            detail_y = min(desc_limit - 18, card_rect.bottom - 70)
            surface.blit(detail_surf, (text_x, detail_y))

            label = f"Select {st['name']}"
            label_w = self.menu_button_font.size(label)[0] + 24
            btn_w = min(card_rect.w - 40, max(160, label_w))
            btn_rect = pygame.Rect(card_rect.right - btn_w - 16, card_rect.bottom - 40, btn_w, 30)
            self._draw_menu_button(surface, btn_rect, label)
            clickables.append((btn_rect, f"storyteller:{st['id']}"))

        hint = "After choosing a storyteller, pick your starting realm."
        hint_lines = wrap_text(hint, self.menu_caption_font, int(card_w * 0.9))
        hint_y = top + total * (card_h + gap) + 6
        for line in hint_lines:
            if hint_y > h - 70:
                break
            line_surf = self.menu_caption_font.render(line, True, (180, 172, 160))
            surface.blit(line_surf, line_surf.get_rect(center=(w // 2, hint_y)))
            hint_y += line_surf.get_height() + 2

        back_rect = pygame.Rect(20, h - 56, 140, 36)
        self._draw_menu_button(surface, back_rect, "Back")
        clickables.append((back_rect, "storyteller_back"))
        return clickables

    def _draw_realm_menu(self, surface):
        surface.fill(BG_COLOR)

        # Decorative background panels behind everything
        bg = pygame.Surface(surface.get_size())
        bg.fill(BG_COLOR)
        tile_fill(bg, bg.get_rect(), self.ui.bottom_tile)
        bg.set_alpha(60)
        surface.blit(bg, (0, 0))

        # Map (clickable selection)
        map_rect = self._get_map_rect()
        self.map_renderer.draw(surface, map_rect)

        # Left panel with ruler details for selected realm
        if self.realm_candidate_id is not None and 0 <= self.realm_candidate_id < len(self.world.realm_rulers):
            ruler = self.world.realm_rulers[self.realm_candidate_id]
        else:
            ruler = {
                "name": "No Ruler Selected",
                "title": "Select a realm",
                "house": "",
                "faith": "—",
                "culture": "—",
                "gender": "—",
                "age": "—",
                "traits": [],
                "stats": [
                    ("Diplomacy", "—"),
                    ("Martial", "—"),
                    ("Stewardship", "—"),
                    ("Intrigue", "—"),
                    ("Learning", "—"),
                    ("Prowess", "—"),
                ],
            }
        clip_draw(
            surface,
            self.layout.left,
            lambda: self.ui.draw_left_panel(
                surface,
                self.layout.left,
                {
                    "character": ruler,
                    "npc_target": self._get_npc_target(self.realm_candidate_id),
                    "npc_actions_enabled": False,
                },
            ),
        )

        # Highlight selected province / realm capital
        if self.realm_candidate_id is not None and 0 <= self.realm_candidate_id < len(self.world.realm_capitals):
            cap_pid = self.world.realm_capitals[self.realm_candidate_id]
            if 0 <= cap_pid < len(self.world.provinces):
                cap = self.world.provinces[cap_pid]
                sp = self.camera.world_to_screen(cap.center, map_rect, use_target=False)
                pygame.draw.circle(surface, (240, 210, 120), (int(sp.x), int(sp.y)), 18, 3)

        self._draw_selected_province_highlight(surface, map_rect)

        w, h = surface.get_size()
        st_name = self.storyteller["name"] if self.storyteller else "None"

        header_rect = pygame.Rect(int(w * 0.18), 16, int(w * 0.64), 96)
        pygame.draw.rect(surface, (18, 18, 20), header_rect, border_radius=8)
        pygame.draw.rect(surface, (5, 5, 6), header_rect, 2, border_radius=8)
        title_surf = self.menu_subtitle_font.render("Choose Your Realm", True, (235, 228, 210))
        surface.blit(title_surf, (header_rect.left + 16, header_rect.top + 10))
        sub_surf = self.menu_caption_font.render(f"Storyteller: {st_name}", True, (200, 192, 175))
        surface.blit(sub_surf, (header_rect.left + 16, header_rect.top + 40))
        hint = "Click a realm on the map, then confirm to begin."
        for i, line in enumerate(wrap_text(hint, self.menu_caption_font, header_rect.w - 32)):
            line_surf = self.menu_caption_font.render(line, True, (180, 172, 160))
            surface.blit(line_surf, (header_rect.left + 16, header_rect.top + 64 + i * 18))

        info_rect = pygame.Rect(int(w * 0.2), h - 150, int(w * 0.6), 110)
        pygame.draw.rect(surface, (20, 20, 22), info_rect, border_radius=8)
        pygame.draw.rect(surface, (6, 6, 7), info_rect, 2, border_radius=8)
        self._realm_ui_rects = [header_rect, info_rect, self.layout.left]

        clickables = []
        if self.realm_candidate_id is None:
            msg = self.menu_caption_font.render("No realm selected.", True, (190, 182, 168))
            surface.blit(msg, (info_rect.left + 16, info_rect.top + 16))
        else:
            realm_name = self.world.realm_names[self.realm_candidate_id]
            ruler = self.world.realm_rulers[self.realm_candidate_id].get("name", "Ruler")
            r1 = self.menu_caption_font.render(realm_name, True, (235, 228, 210))
            r2 = self.menu_caption_font.render(f"Ruler: {ruler}", True, (200, 192, 175))
            surface.blit(r1, (info_rect.left + 16, info_rect.top + 16))
            surface.blit(r2, (info_rect.left + 16, info_rect.top + 40))

        back_rect = pygame.Rect(info_rect.left + 12, info_rect.bottom - 40, 120, 30)
        self._draw_menu_button(surface, back_rect, "Back")
        clickables.append((back_rect, "realm_back"))

        confirm_rect = pygame.Rect(info_rect.right - 220, info_rect.bottom - 40, 200, 30)
        enabled = self.realm_candidate_id is not None
        self._draw_menu_button(surface, confirm_rect, "Start Game", enabled=enabled)
        if enabled:
            clickables.append((confirm_rect, "realm_confirm"))

        return clickables

    def _apply_storyteller(self, storyteller):
        self.storyteller = storyteller
        self._storyteller_start_day = date_ordinal(self.date)
        self._update_storyteller_event_chance()

    def _update_storyteller_event_chance(self):
        if not self.storyteller:
            self.events.daily_chance = self.base_event_daily_chance
            return
        mult = float(self.storyteller.get("event_chance_mult", 1.0))
        ramp = float(self.storyteller.get("event_chance_ramp_per_year", 0.0))
        max_mult = float(self.storyteller.get("event_chance_max_mult", mult))
        if ramp > 0.0 and self._storyteller_start_day is not None:
            days = max(0, date_ordinal(self.date) - self._storyteller_start_day)
            years = days / 365.0
            mult = min(max_mult, mult + ramp * years)
        else:
            mult = min(mult, max_mult)
        self.events.daily_chance = self.base_event_daily_chance * mult

    def _refresh_fog_visuals(self):
        if hasattr(self.world, "_render_base"):
            self.world._render_base()
        if hasattr(self.world, "_render_labels_and_markers"):
            self.world._render_labels_and_markers()

    def _set_full_visibility(self):
        self.world.visibility_by_prov = {p.id: 1.0 for p in self.world.provinces}
        self._refresh_fog_visuals()

    def _start_game_for_realm(self, rid):
        rid = max(0, min(int(rid), len(self.world.realm_names) - 1))
        self.player_realm_id = rid
        self.world.player_realm_id = rid
        self.resources["gold"] = 200
        self.resources["gold_rate"] = 1
        self.resources["piety"] = 1000
        self.resources["prestige"] = 350
        self.resources["renown"] = 120
        self.resources["renown_rate"] = 1

        cap_pid = None
        if 0 <= rid < len(self.world.realm_capitals):
            cap_pid = self.world.realm_capitals[rid]
            self.world.player_capital_pid = cap_pid

        if hasattr(self.world, "_compute_fog_of_war"):
            if hasattr(self.world, "extra_visible_provs"):
                self.world.extra_visible_provs = set()
            self.world._compute_fog_of_war()
            self._refresh_fog_visuals()

        self.character = self.world.realm_rulers[rid]
        if "base_stats" not in self.character:
            self.character["base_stats"] = _stats_list_to_dict(self.character.get("stats", []))
        apply_trait_effects(self.character)
        self.character["traits"] = normalize_traits(self.character.get("traits", []))
        self.resources["piety_rate"] = compute_piety_rate(self.character)[0]
        self.resources["prestige_rate"] = self._compute_prestige_rate(self.character)

        self.population = self.world.total_population_for_realm(self.player_realm_id)
        self._baseline_population = max(1, self.population)
        self.food = self._compute_food_values()
        self.threat = self._compute_threat()
        self._update_army_max()
        self.army["raised"] = 0
        self.army["morale"] = 77
        self.army_raising = False
        self.army_selected = False
        self.army_route = []
        self.army_step_from = None
        self.army_step_to = None
        self.army_step_progress = 0.0
        self.army_pos = None
        self.army_prov_id = None
        self._init_enemy_armies()
        self._init_diplomacy_state()
        self.active_schemes = []
        self._next_scheme_id = 1
        self.hooks = {}
        self.lifestyle_focus = "stewardship"
        self.lifestyle_xp = {k: 0.0 for k in self.lifestyle_focuses}
        self.lifestyle_perks = {k: 0 for k in self.lifestyle_focuses}
        self._lifestyle_picker_index = self.lifestyle_focuses.index(self.lifestyle_focus)
        self.stress = 12.0
        self._stress_break_level = 0
        self.dread = 0.0
        self.decision_cooldowns = {}
        self._raid_cooldown_days = 45
        self._ai_war_cooldown_days = 120

        if cap_pid is not None and 0 <= cap_pid < len(self.world.provinces):
            self.selected_province = self.world.provinces[cap_pid]
            center = self.selected_province.center
            self.camera.center = center.copy()
            self.camera.target_center = center.copy()
            self.camera.zoom = 1.0
            self.camera.target_zoom = 1.0
            self.camera._clamp_target()
            self.camera._clamp_actual()
        else:
            self.selected_province = None

        # Reset war state on new game start.
        self.wars = []
        self._war_next_id = 1
        self._war_focus_id = None
        self._war_border_overlay = None
        self._war_border_overlay_key = None

        # Reset siege state on new game start.
        self._siege_state = None
        self._siege_overlay = None
        self._siege_overlay_key = None
        self._siege_stripe_base = None
        self._siege_stripe_base_key = None
        self.last_played_realm_id = rid
        self._campaign_start_provinces = self._player_province_count()
        self._campaign_target_provinces = self._compute_campaign_target_provinces(self._campaign_start_provinces)
        self._insolvency_days = 0
        self._famine_days = 0
        self._crisis_days = 0
        self.campaign_result = None
        self._campaign_over_day = None
        self._recompute_resource_rates()

    def _get_war_by_id(self, war_id):
        for war in self.wars:
            if war.get("id") == war_id:
                return war
        return None

    def _get_war_by_target(self, target_rid):
        for war in self.wars:
            if war.get("target_id") == target_rid:
                return war
        return None

    @staticmethod
    def _format_war_progress(value):
        try:
            progress = int(round(float(value)))
        except (TypeError, ValueError):
            progress = 0
        return max(0, min(100, progress))

    def _get_war_sieged_set(self, war):
        sieged = war.get("sieged")
        if isinstance(sieged, set):
            return sieged
        if isinstance(sieged, (list, tuple)):
            sieged = set(sieged)
        else:
            sieged = set()
        war["sieged"] = sieged
        return sieged

    def _get_war_total_provs(self, war):
        total = war.get("total_provs")
        if isinstance(total, int):
            return total
        rid = war.get("target_id")
        if rid is None:
            total = 0
        elif hasattr(self.world, "realm_sizes") and 0 <= rid < len(self.world.realm_sizes):
            total = int(self.world.realm_sizes[rid])
        else:
            total = sum(1 for p in self.world.provinces if p.realm_id == rid)
        war["total_provs"] = total
        return total

    def _update_war_progress(self, war):
        if not war:
            return 0.0
        total = self._get_war_total_provs(war)
        sieged = self._get_war_sieged_set(war)
        if total <= 0:
            progress = 0.0
        else:
            progress = (min(len(sieged), total) / total) * 100.0
        war["progress"] = max(0.0, min(100.0, progress))
        return war["progress"]

    def _update_war_tick(self):
        if not self.wars:
            return
        war_to_prompt = None
        for war in self.wars:
            war["days"] += 1
            self._update_war_progress(war)
            if war["progress"] >= 100.0 and not war.get("ready_prompted"):
                war["ready_prompted"] = True
                if war_to_prompt is None:
                    war_to_prompt = war
        if war_to_prompt and not self.modal.open:
            self._open_war_details(war_to_prompt["id"])

    def _siege_province(self, pid):
        if pid is None or not (0 <= pid < len(self.world.provinces)):
            return
        prov = self.world.provinces[pid]
        if prov.realm_id == self.player_realm_id:
            return
        war = self._get_war_by_target(prov.realm_id)
        if not war:
            return
        sieged = self._get_war_sieged_set(war)
        if pid in sieged:
            return
        sieged.add(pid)
        progress = self._update_war_progress(war)
        total = war.get("total_provs") or 0
        self.push_log(f"{self.date}: Sieged {prov.name} ({len(sieged)}/{total}).")
        if progress >= 100.0 and not war.get("ready_prompted"):
            war["ready_prompted"] = True
            if not self.modal.open:
                self._open_war_details(war["id"])

    def _clear_siege_state(self):
        self._siege_state = None

    def _start_siege(self, pid):
        if pid is None or not (0 <= pid < len(self.world.provinces)):
            return False
        prov = self.world.provinces[pid]
        if prov.realm_id == self.player_realm_id:
            return False
        war = self._get_war_by_target(prov.realm_id)
        if not war:
            return False
        sieged = self._get_war_sieged_set(war)
        if pid in sieged:
            return False
        if self._siege_state and self._siege_state.get("pid") == pid:
            return True
        self._siege_state = {
            "pid": pid,
            "target_id": prov.realm_id,
            "stage": "prep",
            "days": 0,
            "prep_days": max(1, int(self.siege_prep_days)),
            "assault_days": max(1, int(self.siege_assault_days)),
        }
        self.push_log(f"{self.date}: Begin siege preparations in {prov.name}.")
        return True

    def _maybe_start_siege(self):
        if self._siege_state:
            return False
        if self.army_prov_id is None:
            return False
        if self.army_step_to is not None or self.army_route:
            return False
        if self.army.get("raised", 0) <= 0:
            return False
        if self._enemy_army_at(self.army_prov_id) is not None:
            return False
        return self._start_siege(self.army_prov_id)

    def _update_siege_tick(self):
        if self._siege_state is None:
            self._maybe_start_siege()
            return

        pid = self._siege_state.get("pid")
        if pid is None or not (0 <= pid < len(self.world.provinces)):
            self._clear_siege_state()
            return

        # Must remain stationary with troops to maintain siege.
        if self.army_prov_id != pid or self.army_step_to is not None or self.army_route:
            self._clear_siege_state()
            return
        if self.army.get("raised", 0) <= 0:
            self._clear_siege_state()
            return

        prov = self.world.provinces[pid]
        if prov.realm_id == self.player_realm_id:
            self._clear_siege_state()
            return

        war = self._get_war_by_target(prov.realm_id)
        if not war:
            self._clear_siege_state()
            return
        sieged = self._get_war_sieged_set(war)
        if pid in sieged:
            self._clear_siege_state()
            return

        stage = self._siege_state.get("stage", "prep")
        self._siege_state["days"] = int(self._siege_state.get("days", 0)) + 1
        days = self._siege_state["days"]

        if stage == "prep":
            if days >= self._siege_state.get("prep_days", 1):
                self._siege_state["stage"] = "assault"
                self._siege_state["days"] = 0
                self.push_log(f"{self.date}: Siege of {prov.name} begins.")
        else:
            if days >= self._siege_state.get("assault_days", 1):
                self._clear_siege_state()
                self._siege_province(pid)

    def _start_war(self, target_rid, war_type="Conquest", goal_pid=None):
        allowed, reason = self._can_declare_war_type(target_rid, war_type)
        if not allowed:
            self.modal.show(
                "Cannot Declare War",
                [
                    reason,
                ],
                [
                    ("OK", "accept", lambda: self.modal.close()),
                ],
            )
            return
        if self._get_war_by_target(target_rid):
            target_name = self._get_war_target_name(target_rid)
            self.modal.show(
                "Already At War",
                [
                    f"You are already at war with {target_name}.",
                ],
                [
                    ("OK", "accept", lambda: self.modal.close()),
                ],
            )
            return
        if hasattr(self.world, "realm_sizes") and 0 <= target_rid < len(self.world.realm_sizes):
            total_provs = int(self.world.realm_sizes[target_rid])
        else:
            total_provs = sum(1 for p in self.world.provinces if p.realm_id == target_rid)
        war = {
            "id": self._war_next_id,
            "target_id": target_rid,
            "war_type": war_type,
            "goal_pid": goal_pid,
            "progress": 0.0,
            "days": 0,
            "ready_prompted": False,
            "sieged": set(),
            "total_provs": total_provs,
            "attacker": "player",
        }
        self._war_next_id += 1
        self._pay_war_cost(target_rid, war_type)
        self.wars.append(war)
        self._ensure_enemy_army_for_war(target_rid)
        self._war_focus_id = war["id"]
        self._update_war_progress(war)
        self._recompute_resource_rates()
        target_name = self._get_war_target_name(target_rid)
        self.push_log(f"{self.date}: Declared war on {target_name}.")
        self._open_war_details(war["id"])

    def _open_war_type_modal(self, target_rid):
        target_name = self._get_war_target_name(target_rid)
        claim_ok, claim_msg = self._can_declare_war_type(target_rid, "Conquest")
        sub_ok, sub_msg = self._can_declare_war_type(target_rid, "Subjugation")
        holy_ok, holy_msg = self._can_declare_war_type(target_rid, "Holy War")

        self.modal.show(
            "Declare War",
            [
                f"Select a war type against {target_name}.",
                "Then choose a province to annex as your war goal.",
                f"Claim War: {claim_msg}",
                f"Subjugation: {sub_msg}",
                f"Holy War: {holy_msg}",
            ],
            [
                (
                    "Claim War",
                    "accept" if claim_ok else "disabled",
                    (lambda rid=target_rid: self._begin_war_goal_selection(rid, "Conquest")) if claim_ok else (lambda: None),
                ),
                (
                    "Subjugation",
                    "primary" if sub_ok else "disabled",
                    (lambda rid=target_rid: self._begin_war_goal_selection(rid, "Subjugation")) if sub_ok else (lambda: None),
                ),
                (
                    "Holy War",
                    "secondary" if holy_ok else "disabled",
                    (lambda rid=target_rid: self._begin_war_goal_selection(rid, "Holy War")) if holy_ok else (lambda: None),
                ),
                ("Cancel", "deny", lambda: self._cancel_pending_war()),
            ],
        )

    def _begin_war_goal_selection(self, target_rid, war_type):
        allowed, reason = self._can_declare_war_type(target_rid, war_type)
        if not allowed:
            self.modal.show(
                "War Not Available",
                [
                    reason,
                ],
                [
                    ("OK", "accept", lambda: self.modal.close()),
                ],
            )
            return
        self.modal.close()
        self._pending_war = {"target_id": target_rid, "war_type": war_type, "goal_pid": None}
        self._war_goal_selecting = True
        target_name = self._get_war_target_name(target_rid)
        self.push_log(f"{self.date}: Select a war goal province in {target_name}.")

    def _cancel_pending_war(self):
        self._pending_war = None
        self._war_goal_selecting = False
        self.modal.close()

    def _apply_war_demands(self, war):
        if not war:
            return
        goal_pid = war.get("goal_pid")
        if goal_pid is None or not (0 <= goal_pid < len(self.world.provinces)):
            return
        prov = self.world.provinces[goal_pid]
        old_rid = prov.realm_id
        new_rid = self.player_realm_id
        if old_rid == new_rid:
            return

        prov.realm_id = new_rid
        if hasattr(self.world, "realm_sizes"):
            if 0 <= old_rid < len(self.world.realm_sizes):
                self.world.realm_sizes[old_rid] = max(0, self.world.realm_sizes[old_rid] - 1)
            if 0 <= new_rid < len(self.world.realm_sizes):
                self.world.realm_sizes[new_rid] += 1

        if hasattr(self.world, "realm_capitals") and 0 <= old_rid < len(self.world.realm_capitals):
            if self.world.realm_capitals[old_rid] == goal_pid:
                new_cap = next((p.id for p in self.world.provinces if p.realm_id == old_rid), None)
                self.world.realm_capitals[old_rid] = new_cap if new_cap is not None else -1

        for p in self.world.provinces:
            p.is_capital = False
        if hasattr(self.world, "realm_capitals"):
            for cap_pid in self.world.realm_capitals:
                if isinstance(cap_pid, int) and 0 <= cap_pid < len(self.world.provinces):
                    self.world.provinces[cap_pid].is_capital = True

        if hasattr(self.world, "_realm_border_cache"):
            self.world._realm_border_cache.pop(old_rid, None)
            self.world._realm_border_cache.pop(new_rid, None)
        if isinstance(getattr(self.world, "_realm_border_points", None), dict):
            self.world._realm_border_points.pop(old_rid, None)
            self.world._realm_border_points.pop(new_rid, None)

        if hasattr(self.world, "_compute_fog_of_war"):
            self.world._compute_fog_of_war()
        if hasattr(self.world, "_render_borders_and_coast"):
            self.world._render_borders_and_coast()
        self._refresh_fog_visuals()
        self._war_border_overlay = None
        self._war_border_overlay_key = None

        self.population = self.world.total_population_for_realm(self.player_realm_id)
        self._baseline_population = max(1, self.population)
        self.food = self._compute_food_values()
        self._update_army_max()
        self.resources["renown"] = int(self.resources.get("renown", 0)) + 12
        self._recompute_resource_rates()
        if war.get("war_type") == "Conquest":
            self.realm_claims.discard(old_rid)

        self.push_log(f"{self.date}: Annexed {prov.name}.")

    def _handle_war_goal_click(self, prov):
        if not self._war_goal_selecting or not self._pending_war or prov is None:
            return False
        target_rid = self._pending_war.get("target_id")
        if target_rid is None:
            return False
        if prov.realm_id != target_rid:
            target_name = self._get_war_target_name(target_rid)
            self.push_log(f"{self.date}: War goal must be in {target_name}.")
            return True
        war_type = self._pending_war.get("war_type", "Conquest")
        self._war_goal_selecting = False
        self._pending_war = None
        self._start_war(target_rid, war_type=war_type, goal_pid=prov.id)
        return True

    def _get_war_target_name(self, war_or_rid):
        if isinstance(war_or_rid, dict):
            rid = war_or_rid.get("target_id")
        else:
            rid = war_or_rid
        if rid is None:
            return "Unknown Realm"
        if 0 <= rid < len(self.world.realm_rulers):
            return self.world.realm_rulers[rid].get(
                "name",
                self.world.realm_names[rid] if 0 <= rid < len(self.world.realm_names) else "NPC Realm",
            )
        return "Unknown Realm"

    def _cycle_war_focus(self):
        if not self.wars:
            self._war_focus_id = None
            self.modal.close()
            return
        ids = [war["id"] for war in self.wars]
        if self._war_focus_id in ids:
            idx = ids.index(self._war_focus_id)
            self._war_focus_id = ids[(idx + 1) % len(ids)]
        else:
            self._war_focus_id = ids[0]
        self._open_war_overview()

    def _open_war_overview(self):
        if not self.wars:
            self.modal.show(
                "Active Wars",
                [
                    "No active wars.",
                ],
                [
                    ("OK", "accept", lambda: self.modal.close()),
                ],
            )
            return
        ids = [war["id"] for war in self.wars]
        if self._war_focus_id not in ids:
            self._war_focus_id = ids[0]
        lines = []
        for war in self.wars:
            name = self._get_war_target_name(war)
            self._update_war_progress(war)
            progress = self._format_war_progress(war.get("progress", 0))
            war_tag = " (Defensive)" if war.get("attacker") == "ai" else ""
            prefix = ">" if war["id"] == self._war_focus_id else " "
            lines.append(f"{prefix} {name}{war_tag} - {progress}%")
        actions = [
            ("Details", "primary", lambda: self._open_war_details(self._war_focus_id)),
        ]
        if len(self.wars) > 1:
            actions.append(("Next", "secondary", lambda: self._cycle_war_focus()))
        actions.append(("Close", "secondary", lambda: self.modal.close()))
        self.modal.show(
            "Active Wars",
            [
                "Select a war to manage:",
                *lines,
            ],
            actions,
        )

    def _open_war_details(self, war_id):
        war = self._get_war_by_id(war_id)
        if not war:
            self._open_war_overview()
            return
        self._war_focus_id = war_id
        target_name = self._get_war_target_name(war)
        self._update_war_progress(war)
        progress = self._format_war_progress(war.get("progress", 0))
        sieged = self._get_war_sieged_set(war)
        total = war.get("total_provs") or 0
        war_type = war.get("war_type", "Conquest")
        attacker = war.get("attacker", "player")
        goal_pid = war.get("goal_pid")
        goal_name = None
        if goal_pid is not None and 0 <= goal_pid < len(self.world.provinces):
            goal_name = self.world.provinces[goal_pid].name
        if progress >= 100:
            press_action = ("Press Demands", "accept", lambda: self._press_war_demands(war_id))
        else:
            press_action = ("Press Demands", "disabled", lambda: None)
        self.modal.show(
            "War Status",
            [
                f"War against {target_name}.",
                f"War type: {war_type}.",
                f"Initiator: {'Enemy Realm' if attacker == 'ai' else 'Your Realm'}.",
                f"War goal: {goal_name if goal_name else 'None'}.",
                f"War progress: {progress}%.",
                f"Sieged provinces: {len(sieged)}/{total}.",
                "Surrender cedes territory in defensive wars." if attacker == "ai" else "Surrender ends this war immediately.",
                "Press demands is available at 100%.",
            ],
            [
                ("Surrender", "deny", lambda: self._surrender_war(war_id)),
                press_action,
                ("Back", "secondary", lambda: self._open_war_overview()),
            ],
        )

    def _surrender_war(self, war_id):
        war = self._get_war_by_id(war_id)
        if not war:
            self.modal.close()
            return
        target_name = self._get_war_target_name(war)
        if war.get("attacker") == "ai":
            ceded = self._apply_enemy_demands(war)
            if ceded:
                self._end_war(war_id, f"Surrendered to {target_name}; ceded {ceded}.")
            else:
                self._end_war(war_id, f"Surrendered to {target_name}.")
            return
        self._end_war(war_id, f"Surrendered to {target_name}.")

    def _apply_enemy_demands(self, war):
        if not war:
            return None
        target_rid = war.get("target_id")
        if target_rid is None or not (0 <= target_rid < len(self.world.realm_names)):
            return None

        goal_pid = war.get("goal_pid")
        if not isinstance(goal_pid, int) or not (0 <= goal_pid < len(self.world.provinces)):
            goal_pid = self._pick_enemy_war_goal_against_player(target_rid)
        if goal_pid is None or not (0 <= goal_pid < len(self.world.provinces)):
            return None

        prov = self.world.provinces[goal_pid]
        old_rid = prov.realm_id
        if old_rid != self.player_realm_id:
            fallback = self._pick_enemy_war_goal_against_player(target_rid)
            if fallback is None:
                return None
            goal_pid = fallback
            prov = self.world.provinces[goal_pid]
            old_rid = prov.realm_id
            if old_rid != self.player_realm_id:
                return None

        new_rid = target_rid
        prov.realm_id = new_rid

        if hasattr(self.world, "realm_sizes"):
            if 0 <= old_rid < len(self.world.realm_sizes):
                self.world.realm_sizes[old_rid] = max(0, self.world.realm_sizes[old_rid] - 1)
            if 0 <= new_rid < len(self.world.realm_sizes):
                self.world.realm_sizes[new_rid] += 1

        if hasattr(self.world, "realm_capitals") and 0 <= old_rid < len(self.world.realm_capitals):
            if self.world.realm_capitals[old_rid] == goal_pid:
                new_cap = next((p.id for p in self.world.provinces if p.realm_id == old_rid), None)
                self.world.realm_capitals[old_rid] = new_cap if new_cap is not None else -1
                if old_rid == self.player_realm_id:
                    self.world.player_capital_pid = self.world.realm_capitals[old_rid]

        if hasattr(self.world, "_realm_border_cache"):
            self.world._realm_border_cache.pop(old_rid, None)
            self.world._realm_border_cache.pop(new_rid, None)
        if isinstance(getattr(self.world, "_realm_border_points", None), dict):
            self.world._realm_border_points.pop(old_rid, None)
            self.world._realm_border_points.pop(new_rid, None)

        for p in self.world.provinces:
            p.is_capital = False
        if hasattr(self.world, "realm_capitals"):
            for cap_pid in self.world.realm_capitals:
                if isinstance(cap_pid, int) and 0 <= cap_pid < len(self.world.provinces):
                    self.world.provinces[cap_pid].is_capital = True

        if hasattr(self.world, "_compute_fog_of_war"):
            self.world._compute_fog_of_war()
        if hasattr(self.world, "_render_borders_and_coast"):
            self.world._render_borders_and_coast()
        self._refresh_fog_visuals()
        self._war_border_overlay = None
        self._war_border_overlay_key = None

        self.population = self.world.total_population_for_realm(self.player_realm_id)
        self.food = self._compute_food_values()
        self._update_army_max()
        self.resources["prestige"] = max(0, int(self.resources.get("prestige", 0)) - 35)
        self.resources["renown"] = max(0, int(self.resources.get("renown", 0)) - 20)
        self._adjust_stress(+10.0)
        self._recompute_resource_rates()
        return prov.name

    def _press_war_demands(self, war_id):
        war = self._get_war_by_id(war_id)
        if not war:
            self.modal.close()
            return
        self._update_war_progress(war)
        progress = self._format_war_progress(war.get("progress", 0))
        if progress < 100:
            self.modal.show(
                "Demands Not Ready",
                [
                    f"War progress is only {progress}%.",
                    "Reach 100% before pressing demands.",
                ],
                [
                    ("OK", "accept", lambda: self.modal.close()),
                ],
            )
            return
        self._apply_war_demands(war)
        target_name = self._get_war_target_name(war)
        self._end_war(war_id, f"Pressed demands against {target_name}.")

    def _end_war(self, war_id, log_message):
        war = self._get_war_by_id(war_id)
        target_id = war.get("target_id") if war else None
        self.wars = [war for war in self.wars if war.get("id") != war_id]
        if self._war_focus_id == war_id:
            self._war_focus_id = self.wars[0]["id"] if self.wars else None
        if self._siege_state and target_id is not None and self._siege_state.get("target_id") == target_id:
            self._clear_siege_state()
        if target_id is not None:
            enemy = self._get_enemy_army_for_realm(target_id)
            if enemy is not None:
                enemy["ai_state"] = "idle"
                enemy["route"] = []
                enemy["target_pid"] = None
                enemy["raising"] = False
            self.realm_truces[target_id] = max(int(self.realm_truces.get(target_id, 0)), 365 * 5)
        self._recompute_resource_rates()
        self.push_log(f"{self.date}: {log_message}")
        self.modal.show(
            "War Resolved",
            [
                log_message,
            ],
            [
                ("OK", "accept", lambda: self.modal.close()),
            ],
        )

    def _try_open_tower_event(self, screen_pos):
        tower_pid = getattr(self.world, "tower_pid", -1)
        if not (0 <= tower_pid < len(self.world.provinces)):
            return False

        tprov = self.world.provinces[tower_pid]
        map_rect = self._get_map_rect()
        sp = self.camera.world_to_screen(tprov.center, map_rect, use_target=False)
        x, y = int(sp.x), int(sp.y)

        label = "Tower of Heaven"
        text = FOOTER_FONT.render(label, True, (0, 0, 0))
        text_rect = text.get_rect(midtop=(x, y + 8))
        icon_rect = pygame.Rect(x - 8, y - 28, 16, 30)
        hit_rect = icon_rect.union(text_rect.inflate(6, 4))

        if hit_rect.collidepoint(screen_pos):
            opened = self.events.open_event_by_id("tower_of_heaven_approach")
            if opened:
                self.selected_province = tprov
                self.right_panel_open = True
                if tprov.realm_id != self.player_realm_id:
                    self.left_panel_open = True
                self._building_menu_slot = None
            return opened
        return False

    def push_log(self, text):
        self.log.append(text)
        if len(self.log) > 30:
            self.log = self.log[-30:]

    def toggle_pause(self):
        if self.speed_level == 0:
            self.speed_level = 1
            self.push_log("Time resumes.")
        else:
            self.speed_level = 0
            self.push_log("Time paused.")

    def set_speed(self, level):
        self.speed_level = level
        if level == 0:
            self.push_log("Time paused.")
        else:
            self.push_log(f"Time speed set to {level}.")

    def open_menu(self):
        held = self._player_province_count()
        target = int(self._campaign_target_provinces)
        progress = self._campaign_progress_percent()
        self.modal.show(
            "Game Menu",
            [
                f"Campaign progress: {progress}% ({held}/{target} provinces).",
                "Pause, review your realm, or return to desktop.",
            ],
            [
                ("Resume", "accept", lambda: self.modal.close()),
                ("Save", "primary", lambda: self._handle_action("save_game")),
                ("Load", "secondary", lambda: self._handle_action("load_game")),
                ("Exit", "deny", lambda: self._exit_game()),
            ],
        )

    def _exit_game(self):
        self.running = False

    def _compute_threat(self):
        # Base threat comes from population size; growth adds a slow pressure on top.
        growth_ratio = (self.population - self._baseline_population) / self._baseline_population
        growth_ratio = max(0.0, growth_ratio)
        base_threat = clamp(self.population / 3000.0, 3.0, 15.0)
        growth_threat = growth_ratio * 30.0  # scaled so growth adds slowly
        threat = base_threat + growth_threat
        return int(clamp(round(threat), 0, 100))

    def _update_army_max(self):
        base_max = int(round(self.population * self.army_pop_ratio))
        effects = self._realm_building_effects(self.player_realm_id)
        levy_mult = 1.0 + float(effects.get("levy_mult_bonus", 0.0))
        max_army = int(round(base_max * max(0.20, levy_mult)))
        max_army = max(0, max_army)
        self.army["max"] = max_army
        if self.army["raised"] > max_army:
            self.army["raised"] = max_army
        if max_army == 0:
            self.army_raising = False
            self.army_selected = False
            self.army_route = []
            self.army_step_from = None
            self.army_step_to = None
            self.army_step_progress = 0.0
            self.army_pos = None
            self.army_prov_id = None
            self._update_fog_from_army()

    def _init_enemy_armies(self):
        self.enemy_armies = []
        if not self.world.realm_names:
            return
        candidates = [rid for rid in range(len(self.world.realm_names)) if rid != self.player_realm_id]
        if not candidates:
            return
        candidates.sort(key=lambda rid: self.world.total_population_for_realm(rid), reverse=True)
        rid = candidates[0]

        pid = None
        if hasattr(self.world, "realm_capitals") and 0 <= rid < len(self.world.realm_capitals):
            pid = self.world.realm_capitals[rid]
        if pid is None or not (0 <= pid < len(self.world.provinces)):
            for prov in self.world.provinces:
                if prov.realm_id == rid:
                    pid = prov.id
                    break
        if pid is None:
            return

        max_army = int(round(self.world.total_population_for_realm(rid) * self.army_pop_ratio))
        max_army = max(1, max_army)
        raised = max(1, int(round(max_army * 0.85)))

        self.enemy_armies.append(
            {
                "realm_id": rid,
                "prov_id": pid,
                "pos": self.world.provinces[pid].center.copy(),
                "army": {"raised": raised, "max": max_army, "morale": 70},
                "raising": False,
                "route": [],
                "target_pid": None,
                "ai_state": "idle",
            }
        )

    def _enemy_army_at(self, pid):
        for enemy in self.enemy_armies:
            if enemy.get("prov_id") == pid and int(enemy.get("army", {}).get("raised", 0)) > 0:
                return enemy
        return None

    def _get_enemy_army_for_realm(self, rid):
        for enemy in self.enemy_armies:
            if enemy.get("realm_id") == rid:
                return enemy
        return None

    def _spawn_enemy_army_for_realm(self, rid):
        if rid is None or rid < 0 or rid >= len(self.world.realm_names):
            return None
        pid = None
        if hasattr(self.world, "realm_capitals") and 0 <= rid < len(self.world.realm_capitals):
            pid = self.world.realm_capitals[rid]
        if pid is None or not (0 <= pid < len(self.world.provinces)):
            for prov in self.world.provinces:
                if prov.realm_id == rid:
                    pid = prov.id
                    break
        if pid is None:
            return None

        max_army = int(round(self.world.total_population_for_realm(rid) * self.army_pop_ratio))
        max_army = max(1, max_army)
        enemy = {
            "realm_id": rid,
            "prov_id": pid,
            "pos": self.world.provinces[pid].center.copy(),
            "army": {"raised": 0, "max": max_army, "morale": 55},
            "raising": True,
            "route": [],
            "target_pid": None,
            "ai_state": "raising",
        }
        self.enemy_armies.append(enemy)
        return enemy

    def _ensure_enemy_army_for_war(self, rid):
        enemy = self._get_enemy_army_for_realm(rid)
        if enemy is None:
            enemy = self._spawn_enemy_army_for_realm(rid)
        if enemy is not None:
            enemy["raising"] = True
            enemy["ai_state"] = "raising"
        return enemy

    def _update_enemy_raising(self, enemy):
        if not enemy or not enemy.get("raising"):
            return
        army = enemy.get("army", {})
        max_army = int(army.get("max", 0))
        if max_army <= 0:
            enemy["raising"] = False
            return
        raised = int(army.get("raised", 0))
        if raised >= max_army:
            army["raised"] = max_army
            enemy["raising"] = False
            return
        per_day = max(1, int(round(max_army * self.enemy_raise_rate)))
        army["raised"] = min(max_army, raised + per_day)

    def _effective_strength(self, army):
        if not army:
            return 0.0
        raised = float(army.get("raised", 0))
        morale = float(army.get("morale", 50))
        morale_mult = 0.4 + 0.6 * clamp(morale / 100.0, 0.0, 1.0)
        return raised * morale_mult

    def _path_length(self, start_pid, target_pid):
        if start_pid is None or target_pid is None:
            return 9999
        if start_pid == target_pid:
            return 0
        path = self._find_province_path(start_pid, target_pid)
        if not path:
            return 9999
        return len(path)

    def _ai_should_engage(self, enemy, player_pid):
        if enemy is None or player_pid is None:
            return False
        enemy_strength = self._effective_strength(enemy.get("army", {}))
        player_strength = self._effective_strength(self.army)
        if player_strength <= 0:
            return True
        ratio = enemy_strength / max(1.0, player_strength)
        if ratio >= self.ai_engage_ratio:
            return True
        if ratio <= self.ai_avoid_ratio:
            return False

        enemy_rid = enemy.get("realm_id")
        if enemy_rid is None:
            return False
        if 0 <= enemy_rid < len(self.world.realm_capitals):
            cap_pid = self.world.realm_capitals[enemy_rid]
            if 0 <= player_pid < len(self.world.provinces):
                if self.world.provinces[player_pid].realm_id == enemy_rid:
                    dist = self._path_length(player_pid, cap_pid)
                    if dist <= 2:
                        return True
        return False

    def _pick_enemy_safe_province(self, enemy, player_pid):
        if enemy is None or player_pid is None:
            return None
        from_pid = enemy.get("prov_id")
        rid = enemy.get("realm_id")
        if from_pid is None or rid is None:
            return None
        best_pid = None
        best_score = -1.0
        for nb in self._prov_adj[from_pid]:
            if self.world.provinces[nb].realm_id != rid:
                continue
            if nb == player_pid:
                continue
            p = self.world.provinces[nb].center
            q = self.world.provinces[player_pid].center
            score = (p.x - q.x) ** 2 + (p.y - q.y) ** 2
            if score > best_score:
                best_score = score
                best_pid = nb
        if best_pid is None and 0 <= rid < len(self.world.realm_capitals):
            best_pid = self.world.realm_capitals[rid]
        return best_pid

    def _set_enemy_route(self, enemy, target_pid):
        if enemy is None or target_pid is None:
            return
        start_pid = enemy.get("prov_id")
        if start_pid is None:
            return
        if start_pid == target_pid:
            enemy["route"] = []
            enemy["target_pid"] = target_pid
            return
        route = self._find_province_path(start_pid, target_pid)
        enemy["route"] = route or []
        enemy["target_pid"] = target_pid

    def _move_enemy_one_step(self, enemy):
        if enemy is None:
            return
        route = enemy.get("route", [])
        if not route:
            return
        next_pid = route.pop(0)
        enemy["prov_id"] = next_pid
        enemy["pos"] = self.world.provinces[next_pid].center.copy()
        enemy["route"] = route

    def _update_enemy_ai_tick(self):
        if not self.enemy_armies or not self.wars:
            return

        for enemy in self.enemy_armies:
            rid = enemy.get("realm_id")
            if rid is None:
                continue
            war = self._get_war_by_target(rid)
            if not war:
                enemy["ai_state"] = "idle"
                enemy["route"] = []
                enemy["target_pid"] = None
                continue

            self._update_enemy_raising(enemy)
            enemy_army = enemy.get("army", {})
            if int(enemy_army.get("raised", 0)) <= 0:
                continue

            player_pid = self.army_prov_id if self.army.get("raised", 0) > 0 else None
            if player_pid is None:
                continue

            engage = self._ai_should_engage(enemy, player_pid)
            if engage:
                enemy["ai_state"] = "engage"
                if enemy.get("target_pid") != player_pid or not enemy.get("route"):
                    self._set_enemy_route(enemy, player_pid)
                self._move_enemy_one_step(enemy)
            else:
                enemy["ai_state"] = "avoid"
                safe_pid = self._pick_enemy_safe_province(enemy, player_pid)
                if safe_pid is not None:
                    if enemy.get("target_pid") != safe_pid or not enemy.get("route"):
                        self._set_enemy_route(enemy, safe_pid)
                    self._move_enemy_one_step(enemy)

            if enemy.get("prov_id") == player_pid and self.army.get("raised", 0) > 0:
                self._resolve_battle(enemy, player_pid, attacker_is_player=False)

    def _update_army_morale_tick(self):
        if self.army.get("raised", 0) > 0:
            morale = float(self.army.get("morale", 50))
            self.army["morale"] = clamp(morale + self.morale_recovery_per_day, 0.0, 100.0)
        for enemy in self.enemy_armies:
            army = enemy.get("army", {})
            if int(army.get("raised", 0)) <= 0:
                continue
            morale = float(army.get("morale", 50))
            army["morale"] = clamp(morale + self.morale_recovery_per_day, 0.0, 100.0)

    def _pick_retreat_province(self, from_pid, realm_id):
        if 0 <= from_pid < len(self._prov_adj):
            options = [pid for pid in self._prov_adj[from_pid] if self.world.provinces[pid].realm_id == realm_id]
            if options:
                return self.world.rnd.choice(options)
        if hasattr(self.world, "realm_capitals") and 0 <= realm_id < len(self.world.realm_capitals):
            return self.world.realm_capitals[realm_id]
        for prov in self.world.provinces:
            if prov.realm_id == realm_id:
                return prov.id
        return from_pid

    def _compute_battle_losses(self, player_size, enemy_size):
        if player_size <= 0 or enemy_size <= 0:
            return 0, 0
        if player_size >= enemy_size:
            winner_size = player_size
            loser_size = enemy_size
            player_is_winner = True
        else:
            winner_size = enemy_size
            loser_size = player_size
            player_is_winner = False

        ratio = winner_size / max(1, loser_size)
        win_loss_rate = 0.12 + 0.18 * (loser_size / winner_size)
        lose_loss_rate = 0.45 + 0.35 * (ratio / (ratio + 1.0))

        win_loss = int(round(winner_size * win_loss_rate))
        lose_loss = int(round(loser_size * lose_loss_rate))

        if winner_size > 1:
            win_loss = min(win_loss, winner_size - 1)
        else:
            win_loss = 0
        if loser_size > 1:
            lose_loss = min(lose_loss, loser_size - 1)
        else:
            lose_loss = 0

        if player_is_winner:
            return win_loss, lose_loss
        return lose_loss, win_loss

    def _apply_battle_morale(self, morale, loss, size, won):
        if size <= 0:
            return 0.0
        loss_ratio = loss / max(1, size)
        drop = 12 + 60 * loss_ratio
        if not won:
            drop += 15
        morale = clamp(morale - drop, 0.0, 100.0)
        if won:
            morale = clamp(morale + 6, 0.0, 100.0)
        return morale

    def _resolve_battle(self, enemy, battle_pid, attacker_is_player=True):
        if enemy is None:
            return False
        player_size = int(self.army.get("raised", 0))
        enemy_size = int(enemy.get("army", {}).get("raised", 0))
        if player_size <= 0 or enemy_size <= 0:
            return False

        player_wins = player_size >= enemy_size
        player_loss, enemy_loss = self._compute_battle_losses(player_size, enemy_size)

        player_morale = float(self.army.get("morale", 60))
        enemy_morale = float(enemy.get("army", {}).get("morale", 60))
        attacker_morale = player_morale if attacker_is_player else enemy_morale
        defender_morale = enemy_morale if attacker_is_player else player_morale
        attacker_wins = player_wins if attacker_is_player else not player_wins
        stack_wipe = (
            attacker_wins
            and defender_morale <= self.stack_wipe_defender_morale
            and attacker_morale >= self.stack_wipe_attacker_morale
        )
        if stack_wipe:
            if attacker_is_player:
                enemy_loss = enemy_size
            else:
                player_loss = player_size

        new_player = max(0, player_size - player_loss)
        new_enemy = max(0, enemy_size - enemy_loss)

        self.army["raised"] = new_player
        enemy["army"]["raised"] = new_enemy
        if isinstance(enemy, dict):
            enemy["route"] = []
            enemy["target_pid"] = None

        player_morale = self._apply_battle_morale(player_morale, player_loss, player_size, player_wins)
        enemy_morale = self._apply_battle_morale(enemy_morale, enemy_loss, enemy_size, not player_wins)
        if stack_wipe:
            if attacker_is_player:
                enemy_morale = 0.0
            else:
                player_morale = 0.0
        self.army["morale"] = player_morale
        enemy["army"]["morale"] = enemy_morale

        self.army_route = []
        self.army_step_from = None
        self.army_step_to = None
        self.army_step_progress = 0.0

        retreat_name = None
        if player_wins:
            retreat_pid = self._pick_retreat_province(battle_pid, enemy.get("realm_id"))
            enemy["prov_id"] = retreat_pid
            enemy["pos"] = self.world.provinces[retreat_pid].center.copy()
            retreat_name = self.world.provinces[retreat_pid].name
            outcome = "Victory"
            self.resources["prestige"] = int(self.resources.get("prestige", 0)) + 6
            self.dread = clamp(float(self.dread) + 1.5, 0.0, 100.0)
            self._adjust_stress(-1.8)
        else:
            retreat_pid = self._pick_retreat_province(battle_pid, self.player_realm_id)
            self._set_army_prov(retreat_pid)
            retreat_name = self.world.provinces[retreat_pid].name
            outcome = "Defeat"
            self._adjust_stress(+4.0)

        self._update_fog_from_army()

        prov_name = self.world.provinces[battle_pid].name
        lines = [
            f"Battle of {prov_name}",
            f"Outcome: {outcome}",
            f"Your army: {player_size:,} -> {new_player:,} (lost {player_loss:,})",
            f"Enemy army: {enemy_size:,} -> {new_enemy:,} (lost {enemy_loss:,})",
        ]
        if stack_wipe:
            if attacker_is_player:
                lines.append("Enemy army is wiped out!")
            else:
                lines.append("Your army is wiped out!")
        if retreat_name:
            if player_wins:
                lines.append(f"Enemy retreats to {retreat_name}.")
            else:
                lines.append(f"Your army retreats to {retreat_name}.")
        self.modal.show(
            "Battle Summary",
            lines,
            [
                ("Close", "accept", lambda: self.modal.close()),
            ],
        )
        self.push_log(f"{self.date}: Battle at {prov_name}. {outcome}.")
        return player_wins

    def _get_player_capital_pid(self):
        pid = getattr(self.world, "player_capital_pid", None)
        if pid is None or not (0 <= pid < len(self.world.provinces)):
            if 0 <= self.player_realm_id < len(self.world.realm_capitals):
                pid = self.world.realm_capitals[self.player_realm_id]
        if pid is not None and 0 <= pid < len(self.world.provinces):
            return pid
        return None

    def _get_player_capital_center(self):
        pid = self._get_player_capital_pid()
        if pid is not None:
            return self.world.provinces[pid].center
        return pygame.Vector2(self.world.world_w * 0.5, self.world.world_h * 0.5)

    def _ensure_army_position(self):
        if self.army_pos is None or self.army_prov_id is None:
            pid = self._get_player_capital_pid()
            if pid is None:
                self.army_pos = self._get_player_capital_center().copy()
                return
            self._set_army_prov(pid)

    def _set_army_prov(self, pid):
        if pid is None or not (0 <= pid < len(self.world.provinces)):
            return
        self.army_prov_id = pid
        self.army_pos = self.world.provinces[pid].center.copy()

    def _find_province_path(self, start_pid, target_pid):
        if start_pid == target_pid:
            return []
        adj = self._prov_adj
        prev = {start_pid: None}
        queue = [start_pid]
        head = 0
        while head < len(queue):
            cur = queue[head]
            head += 1
            if cur == target_pid:
                break
            for nb in adj[cur]:
                if nb in prev:
                    continue
                prev[nb] = cur
                queue.append(nb)
        if target_pid not in prev:
            return []
        path = []
        cur = target_pid
        while cur is not None and cur != start_pid:
            path.append(cur)
            cur = prev[cur]
        path.reverse()
        return path

    def _update_army_movement(self):
        if not self.army_route or self.army_prov_id is None:
            return
        if self.army.get("raised", 0) <= 0:
            return
        if self.army_step_to is None:
            self.army_step_from = self.army_prov_id
            self.army_step_to = self.army_route[0]
            self.army_step_progress = 0.0
        if self.army_step_to is None:
            return
        start = self.world.provinces[self.army_step_from].center
        end = self.world.provinces[self.army_step_to].center
        dist = max(1.0, (end - start).length())
        self.army_step_progress += self.army_move_speed / dist
        interp = max(0.0, min(1.0, self.army_step_progress))
        self.army_pos = start + (end - start) * interp
        if self.army_step_progress >= 1.0:
            self.army_step_progress = 1.0
            self.army_last_step = (self.army_step_from, self.army_step_to)
            self.army_step_flash = 0.25
            self._set_army_prov(self.army_step_to)
            self.army_route.pop(0)
            if self.army_route:
                self.army_step_from = self.army_prov_id
                self.army_step_to = self.army_route[0]
                self.army_step_progress = 0.0
            else:
                self.army_step_from = None
                self.army_step_to = None
                self.army_step_progress = 0.0
            self._update_fog_from_army()
            enemy = self._enemy_army_at(self.army_prov_id)
            if enemy is not None:
                player_wins = self._resolve_battle(enemy, self.army_prov_id, attacker_is_player=True)
                if player_wins:
                    self._start_siege(self.army_prov_id)
            else:
                if not self.army_route and self.army_step_to is None:
                    self._start_siege(self.army_prov_id)

    def _update_army_raising(self):
        if not self.army_raising:
            return
        self._ensure_army_position()
        self._update_fog_from_army()
        max_army = self.army.get("max", 0)
        if max_army <= 0:
            self.army_raising = False
            return
        if self.army["raised"] >= max_army:
            self.army["raised"] = max_army
            self.army_raising = False
            return
        per_day = max(1, int(round(max_army * self.army_raise_rate)))
        self.army["raised"] = min(max_army, self.army["raised"] + per_day)

    def _update_army_flash(self, dt):
        if self.army_step_flash > 0.0:
            self.army_step_flash = max(0.0, self.army_step_flash - dt)
            if self.army_step_flash <= 0.0:
                self.army_last_step = None

    def _update_fog_from_army(self):
        if not hasattr(self.world, "extra_visible_provs"):
            return
        extra = set()
        if (self.army.get("raised", 0) > 0 or self.army_raising) and self.army_prov_id is not None:
            extra.add(self.army_prov_id)
            if 0 <= self.army_prov_id < len(self._prov_adj):
                extra.update(self._prov_adj[self.army_prov_id])
        if extra == getattr(self.world, "extra_visible_provs", set()):
            return
        self.world.extra_visible_provs = extra
        if hasattr(self.world, "_compute_fog_of_war"):
            self.world._compute_fog_of_war()
            self._refresh_fog_visuals()

    def _update_right_panel_anim(self, dt):
        should_show = (
            self.mode == "game"
            and self.selected_province is not None
            and self.right_panel_open
        )
        target = 1.0 if should_show else 0.0
        speed = 6.0
        step = speed * dt
        if self._right_panel_anim < target:
            self._right_panel_anim = min(target, self._right_panel_anim + step)
        elif self._right_panel_anim > target:
            self._right_panel_anim = max(target, self._right_panel_anim - step)

    def _update_left_panel_anim(self, dt):
        should_show = self.mode == "game" and self.left_panel_open
        target = 1.0 if should_show else 0.0
        speed = 6.0
        step = speed * dt
        if self._left_panel_anim < target:
            self._left_panel_anim = min(target, self._left_panel_anim + step)
        elif self._left_panel_anim > target:
            self._left_panel_anim = max(target, self._left_panel_anim - step)

    def _realm_building_effects(self, rid):
        effects = {
            "gold_upkeep": 0.0,
            "gold_rate_bonus": 0.0,
            "piety_rate_bonus": 0.0,
            "prestige_rate_bonus": 0.0,
            "levy_mult_bonus": 0.0,
            "stress_monthly_relief": 0.0,
        }
        for prov in self.world.provinces:
            if prov.realm_id != rid:
                continue
            for b in getattr(prov, "buildings", []):
                if b is None:
                    continue
                effects["gold_upkeep"] += building_gold_upkeep(b)
                effects["gold_rate_bonus"] += building_gold_rate_bonus(b)
                effects["piety_rate_bonus"] += building_piety_rate_bonus(b)
                effects["prestige_rate_bonus"] += building_prestige_rate_bonus(b)
                effects["levy_mult_bonus"] += building_levy_mult_bonus(b)
                effects["stress_monthly_relief"] += building_stress_monthly_relief(b)
        return effects

    def _compute_food_values(self):
        production = 0.0
        for prov in self.world.provinces:
            if prov.realm_id != self.player_realm_id:
                continue
            for b in getattr(prov, "buildings", []):
                production += building_food_output(b)
        consumption = self.population * self.food_consumption_per_pop
        production = int(round(production))
        consumption = int(round(consumption))
        return max(0, production), max(0, consumption)

    def _rebalance_population_to_farms(self, target_ratio=1.0):
        if self.food_consumption_per_pop <= 0:
            return

        realms = {}
        for prov in self.world.provinces:
            rid = prov.realm_id
            data = realms.setdefault(rid, {"provs": [], "current": 0, "food_output": 0.0})
            data["provs"].append(prov)
            data["current"] += prov.population
            for b in getattr(prov, "buildings", []):
                data["food_output"] += building_food_output(b)

        for data in realms.values():
            current = data["current"]
            if current <= 0:
                continue
            capacity = data["food_output"] / self.food_consumption_per_pop
            if capacity <= 0:
                continue
            target = int(capacity * target_ratio)
            if target <= 0 or current == target:
                continue
            scale = target / current
            for prov in data["provs"]:
                prov.population = max(1, int(round(prov.population * scale)))

    def _build_selected_building(self, building_id, slot_idx=None):
        prov = self.selected_province
        if prov is None:
            self.push_log("No province selected.")
            return
        if prov.realm_id != self.player_realm_id:
            self.push_log("Cannot build outside your realm.")
            return
        bdef = BUILDINGS.get(building_id)
        if bdef is None:
            self.push_log("Unknown building type.")
            return
        if slot_idx is None:
            slot = next((idx for idx, entry in enumerate(prov.buildings) if entry is None), -1)
            if slot < 0:
                self.push_log(f"{prov.name} has no empty building slots.")
                return
        else:
            if not (0 <= slot_idx < len(prov.buildings)):
                self.push_log("Invalid building slot.")
                return
            if prov.buildings[slot_idx] is not None:
                self.push_log(f"Slot {slot_idx + 1} is already occupied.")
                return
            slot = slot_idx
        build_cost = max(0, int(getattr(bdef, "build_cost_gold", 0)))
        if self.resources.get("gold", 0) < build_cost:
            self.push_log(f"Need {build_cost} gold to build {bdef.name}.")
            return
        prov.buildings[slot] = make_building(building_id, level=1)
        bname = bdef.name if bdef else building_id
        self.resources["gold"] = max(0, int(self.resources.get("gold", 0)) - build_cost)
        self.push_log(
            f"{self.date}: Built {bname} in {prov.name} (slot {slot + 1}) "
            f"for {build_cost} gold."
        )
        self.food = self._compute_food_values()
        self._recompute_resource_rates()
        self._update_army_max()
        self._building_menu_slot = None

    def _upgrade_selected_building(self, slot_idx):
        prov = self.selected_province
        if prov is None:
            self.push_log("No province selected.")
            return
        if prov.realm_id != self.player_realm_id:
            self.push_log("Cannot build outside your realm.")
            return
        if not (0 <= slot_idx < len(prov.buildings)):
            self.push_log("Invalid building slot.")
            return
        entry = prov.buildings[slot_idx]
        if entry is None:
            self.push_log(f"Slot {slot_idx + 1} is empty.")
            return
        level = get_building_level(entry)
        max_level = building_max_level(entry)
        if max_level and level >= max_level:
            self.push_log("Building is already at max level.")
            return
        new_level = level + 1
        if isinstance(entry, dict):
            entry["level"] = new_level
        else:
            prov.buildings[slot_idx] = make_building(get_building_id(entry), level=new_level)
        bdef = BUILDINGS.get(get_building_id(entry))
        bname = bdef.name if bdef else get_building_id(entry)
        base_cost = max(0, int(getattr(bdef, "upgrade_cost_gold", 0)))
        upgrade_cost = int(round(base_cost * (1.0 + (0.55 * max(0, level - 1)))))
        if self.resources.get("gold", 0) < upgrade_cost:
            self.push_log(f"Need {upgrade_cost} gold to upgrade {bname}.")
            if isinstance(entry, dict):
                entry["level"] = level
            else:
                prov.buildings[slot_idx] = make_building(get_building_id(entry), level=level)
            return
        self.resources["gold"] = max(0, int(self.resources.get("gold", 0)) - upgrade_cost)
        self.push_log(
            f"{self.date}: Upgraded {bname} in {prov.name} (slot {slot_idx + 1}) "
            f"for {upgrade_cost} gold."
        )
        self.food = self._compute_food_values()
        self._recompute_resource_rates()
        self._update_army_max()
        self._building_menu_slot = None

    def _demolish_selected_building(self, slot_idx):
        prov = self.selected_province
        if prov is None:
            self.push_log("No province selected.")
            return
        if prov.realm_id != self.player_realm_id:
            self.push_log("Cannot build outside your realm.")
            return
        if not (0 <= slot_idx < len(prov.buildings)):
            self.push_log("Invalid building slot.")
            return
        entry = prov.buildings[slot_idx]
        if entry is None:
            self.push_log(f"Slot {slot_idx + 1} is already empty.")
            return
        bdef = BUILDINGS.get(get_building_id(entry))
        bname = bdef.name if bdef else get_building_id(entry)
        prov.buildings[slot_idx] = None
        self.push_log(f"{self.date}: Demolished {bname} in {prov.name} (slot {slot_idx + 1}).")
        self.food = self._compute_food_values()
        self._recompute_resource_rates()
        self._update_army_max()
        self._building_menu_slot = None

    def _handle_action(self, action):
        if action == "menu_start":
            self.storyteller = None
            self._storyteller_start_day = None
            self.realm_select_page = 0
            self.realm_candidate_id = None
            self.mode = "storyteller"
            self.modal.close()
            return
        if action == "menu_load":
            self._open_load_game_modal()
            return
        if action == "menu_settings":
            self._open_settings_modal()
            return
        if action == "storyteller_back":
            self.realm_candidate_id = None
            self.selected_province = None
            self.right_panel_open = False
            self.mode = "menu"
            return
        if action.startswith("storyteller:"):
            sid = action.split(":", 1)[1]
            st = next((s for s in self.storytellers if s["id"] == sid), None)
            if st:
                self._apply_storyteller(st)
                self.realm_select_page = 0
                self.realm_candidate_id = None
                self.selected_province = None
                self.right_panel_open = False
                self._set_full_visibility()
                self.mode = "realm_select"
            return
        if action == "realm_back":
            self.realm_candidate_id = None
            self.selected_province = None
            self.right_panel_open = False
            self.mode = "storyteller"
            return
        if action == "realm_confirm":
            if self.realm_candidate_id is None:
                return
            self._start_game_for_realm(self.realm_candidate_id)
            self.mode = "game"
            self.camera.set_viewport(self._get_map_rect().size)
            self.left_panel_open = False
            self._left_panel_anim = 0.0
            self.right_panel_open = True
            self._right_panel_anim = 1.0
            self._open_campaign_briefing()
            return
        if action == "right_panel_close":
            self.right_panel_open = False
            return
        if action == "left_panel_close":
            self.left_panel_open = False
            return
        if action == "left_panel_open":
            self.left_panel_open = True
            return
        if action == "npc_promote_relations":
            self._action_promote_relations()
            return
        if action == "npc_fabricate_claim":
            self._action_fabricate_claim()
            return
        if action == "npc_arrange_marriage":
            self._action_arrange_marriage()
            return
        if action == "npc_plot_murder":
            self._action_plot_murder()
            return
        if action == "npc_declare_war":
            target_rid = None
            if self.selected_province is not None and self.selected_province.realm_id != self.player_realm_id:
                target_rid = self.selected_province.realm_id
            if target_rid is None:
                self.modal.show(
                    "No Target Selected",
                    [
                        "Select a foreign realm (click a province) before declaring war.",
                    ],
                    [
                        ("OK", "accept", lambda: self.modal.close()),
                    ],
                )
            else:
                self._open_war_type_modal(target_rid)
            return
        if action == "open_war_overview":
            self._open_war_overview()
            return
        if action.startswith("war_details:"):
            try:
                war_id = int(action.split(":", 1)[1])
            except ValueError:
                self.push_log("Invalid war action.")
                return
            self._open_war_details(war_id)
            return
        if action == "raise_army":
            if self.army_raising:
                self.army_raising = False
                if self.army.get("raised", 0) <= 0:
                    self.army_selected = False
                    self.army_route = []
                    self.army_step_from = None
                    self.army_step_to = None
                    self.army_step_progress = 0.0
                    self._update_fog_from_army()
                self.push_log("You halt the muster.")
            else:
                if self.army.get("max", 0) <= 0:
                    self.push_log("No population available to raise an army.")
                elif self.army.get("raised", 0) >= self.army.get("max", 0):
                    self.push_log("Your army is already fully raised.")
                else:
                    self._ensure_army_position()
                    self.army_raising = True
                    self._update_fog_from_army()
                    self.push_log("Your levies begin to muster.")
            return
        if action == "disband":
            action = "disband_army"
        if action == "disband_army":
            if self.army.get("raised", 0) <= 0:
                return
            if self.army_prov_id is None or not (0 <= self.army_prov_id < len(self.world.provinces)):
                return
            prov = self.world.provinces[self.army_prov_id]
            if prov.realm_id != self.player_realm_id:
                self.modal.show(
                    "Cannot Disband",
                    [
                        "You can only disband your army within your own realm.",
                    ],
                    [
                        ("OK", "accept", lambda: self.modal.close()),
                    ],
                )
                return
            self.army["raised"] = 0
            self.army_raising = False
            self.army_selected = False
            self.army_route = []
            self.army_step_from = None
            self.army_step_to = None
            self.army_step_progress = 0.0
            self.army_pos = None
            self.army_prov_id = None
            self._update_fog_from_army()
            self.push_log("You disband the army.")
            return
        if action == "toggle_pause":
            self.toggle_pause()
            return
        elif action == "speed_1":
            self.set_speed(1)
            return
        elif action == "speed_2":
            self.set_speed(2)
            return
        elif action == "speed_3":
            self.set_speed(3)
            return
        elif action == "open_menu":
            self.open_menu()
            return
        elif action == "save_game":
            self._save_game_to_file(self.latest_save_path, autosave=False)
            return
        elif action == "load_game":
            self._open_load_game_modal()
            return
        elif action in ("realm", "view_realm"):
            self._open_realm_overview()
            return
        elif action == "ledger":
            self._open_ledger_overview()
            return
        elif action == "military":
            self._open_military_overview()
            return
        elif action == "set_rally":
            if self.selected_province is None or self.selected_province.realm_id != self.player_realm_id:
                self.modal.show(
                    "No Valid Rally Point",
                    [
                        "Select one of your own provinces to set a rally point.",
                    ],
                    [
                        ("OK", "accept", lambda: self.modal.close()),
                    ],
                )
            else:
                self._set_rally_point(self.selected_province.id, announce=True)
                self._open_military_overview()
            return
        elif action == "rally":
            self._rally_army_to_capital()
            return
        elif action == "decisions":
            self._open_decisions_modal()
            return
        elif action == "council":
            self._open_scheme_overview()
            return
        elif action == "court":
            self._open_scheme_overview()
            return
        elif action == "build_farm":
            self._build_selected_building("farm")
            return
        elif action.startswith("building_slot:"):
            parts = action.split(":")
            if len(parts) < 3:
                self.push_log("Invalid building action.")
                return
            try:
                slot_idx = int(parts[1])
            except ValueError:
                self.push_log("Invalid building slot action.")
                return
            verb = parts[2]
            if verb == "toggle":
                if self._building_menu_slot == slot_idx:
                    self._building_menu_slot = None
                else:
                    self._building_menu_slot = slot_idx
            elif verb == "build" and len(parts) >= 4:
                self._build_selected_building(parts[3], slot_idx=slot_idx)
            elif verb == "upgrade":
                self._upgrade_selected_building(slot_idx)
            elif verb == "demolish":
                self._demolish_selected_building(slot_idx)
            else:
                self.push_log(f"Unknown building action: {verb}")
            return

        self.push_log(f"Unknown UI action: {action}")

    def _update_time(self, dt):
        days_per_sec = self.speed_days_per_sec.get(self.speed_level, 0)
        if days_per_sec <= 0:
            return
        self._time_accum += dt * days_per_sec
        whole = int(self._time_accum)
        if whole > 0:
            for _ in range(whole):
                self.date.advance_days(1)

                # daily tick for events (random + chain)
                self._update_storyteller_event_chance()
                self.events.on_day()
                self._update_war_tick()
                self._update_army_raising()
                self._update_army_morale_tick()
                self._update_siege_tick()
                self._update_army_movement()
                self._update_enemy_ai_tick()
                self._tick_politics_day()

                if self.date.day == 1:
                    self._apply_monthly_resource_rates()
                    if self._autosave_interval_months > 0 and ((self.date.month - 1) % self._autosave_interval_months == 0):
                        self._save_game_to_file(self.autosave_path, autosave=True)
                    if self.date.month == 1:
                        self._annual_dynasty_tick()

            self._time_accum -= whole

    def _recompute_resource_rates(self):
        effects = self._realm_building_effects(self.player_realm_id)
        stewardship_bonus = self._perk_level("stewardship") // 2
        if self.lifestyle_focus == "stewardship":
            stewardship_bonus += 1
        stress_penalty = 2 if self.stress >= 220 else (1 if self.stress >= 120 else 0)
        building_gold = int(round(float(effects.get("gold_rate_bonus", 0.0))))
        upkeep_penalty = int(round(float(effects.get("gold_upkeep", 0.0)) * 0.45))
        self.resources["gold_rate"] = 1 + stewardship_bonus + building_gold - stress_penalty - upkeep_penalty

        piety_rate = compute_piety_rate(self.character)[0]
        piety_rate += self._perk_level("learning") // 2
        if self.lifestyle_focus == "learning":
            piety_rate += 1
        piety_rate += int(round(float(effects.get("piety_rate_bonus", 0.0))))
        self.resources["piety_rate"] = int(piety_rate)

        prestige_rate = self._compute_prestige_rate(self.character)
        prestige_rate += int(round(float(effects.get("prestige_rate_bonus", 0.0))))
        self.resources["prestige_rate"] = int(prestige_rate)
        renown_rate = 1 + (self._realm_size(self.player_realm_id) // 3)
        renown_rate += len(self.alliances) // 2
        renown_rate += self._perk_level("diplomacy") // 4
        if self.wars:
            renown_rate += 1
        self.resources["renown_rate"] = int(max(0, renown_rate))

    def _apply_monthly_resource_rates(self):
        self._recompute_resource_rates()

        for res in ("gold", "piety", "prestige", "renown"):
            rate = self.resources.get(f"{res}_rate", 0)
            if rate == 0:
                continue
            self.resources[res] += rate

        # Opinions drift slowly toward neutral over time.
        for rid, opinion in list(self.realm_relations.items()):
            if opinion > 0:
                self.realm_relations[rid] = opinion - 1
            elif opinion < 0:
                self.realm_relations[rid] = opinion + 1

        self.dread = clamp(float(self.dread) - 3.5, 0.0, 100.0)
        monthly_stress_relief = -2.0 - (0.5 * self._perk_level("learning"))
        if self.lifestyle_focus == "learning":
            monthly_stress_relief -= 1.0
        effects = self._realm_building_effects(self.player_realm_id)
        monthly_stress_relief -= float(effects.get("stress_monthly_relief", 0.0))
        self._adjust_stress(monthly_stress_relief)

        # Food production comes from farms; consumption scales with population.
        production, consumption = self._compute_food_values()
        self.food = (production, consumption)

        # Population growth/decline based on food surplus/deficit.
        if consumption <= 0:
            food_balance = 1.0
        else:
            food_balance = (production - consumption) / consumption
        food_balance = max(-1.0, min(1.0, food_balance))

        if food_balance >= 0:
            pop_rate = 0.001 + 0.004 * food_balance  # base growth + surplus bonus
        else:
            pop_rate = 0.001 + 0.010 * food_balance  # stronger penalty for deficits

        if abs(pop_rate) > 0.00001:
            self.world.adjust_population_for_realm(self.player_realm_id, pop_rate)

        self.population = self.world.total_population_for_realm(self.player_realm_id)
        self.threat = self._compute_threat()
        self._update_army_max()

    def _map_controls(self, dt):
        keys = pygame.key.get_pressed()
        if self.modal.open:
            return
        map_rect = self._get_map_rect()
        mx, my = pygame.mouse.get_pos()
        over_ui = self._point_in_ui((mx, my))

        # Keyboard panning (weighty due to camera smoothing)
        pan_speed = 720.0 / max(self.camera.target_zoom, 0.001)
        dx = dy = 0.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx -= pan_speed * dt
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx += pan_speed * dt
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy -= pan_speed * dt
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy += pan_speed * dt
        if dx != 0.0 or dy != 0.0:
            self.camera.pan(dx, dy)

        # +/- zoom
        if keys[pygame.K_EQUALS] or keys[pygame.K_PLUS]:
            if map_rect.collidepoint((mx, my)) and not over_ui:
                self.camera.zoom_at(1.03, (mx, my), map_rect)
        if keys[pygame.K_MINUS]:
            if map_rect.collidepoint((mx, my)) and not over_ui:
                self.camera.zoom_at(0.97, (mx, my), map_rect)

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0

            if self.mode == "game":
                self._bottom_bar_rect = self.ui.compute_bottom_bar_rect(
                    self.layout.bottom,
                    {
                        "date": self.date,
                        "army": self.army,
                        "army_raising": self.army_raising,
                        "speed_level": self.speed_level,
                        "wars": self.wars,
                    },
                )
            else:
                self._bottom_bar_rect = None

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                elif event.type == pygame.VIDEORESIZE:
                    self._apply_window_size((event.w, event.h), remember=True)

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.modal.open:
                            self.modal.close()
                        elif self.mode == "game":
                            self.open_menu()
                        elif self.mode == "storyteller":
                            self.mode = "menu"
                        elif self.mode == "realm_select":
                            self.mode = "storyteller"
                    elif event.key == pygame.K_SPACE:
                        if self.mode == "game":
                            self.toggle_pause()

                # Mouse wheel zoom (pygame 2)
                elif event.type == pygame.MOUSEWHEEL and not self.modal.open and self.mode in ("game", "realm_select"):
                    mx, my = pygame.mouse.get_pos()
                    map_rect = self._get_map_rect()
                    if map_rect.collidepoint((mx, my)) and not self._point_in_ui((mx, my)):
                        factor = 1.12 if event.y > 0 else 0.89
                        self.camera.zoom_at(factor, (mx, my), map_rect)

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1 and not self.modal.open and self.mode in ("game", "realm_select"):
                        map_rect = self._get_map_rect()
                        if map_rect.collidepoint(event.pos) and not self._point_in_ui(event.pos):
                            self._mouse_down_in_map = True
                            self._mouse_down_pos = event.pos
                            self._drag_started = False

                    # fallback wheel (old style)
                    if not self.modal.open and self.mode in ("game", "realm_select"):
                        map_rect = self._get_map_rect()
                        if map_rect.collidepoint(event.pos) and not self._point_in_ui(event.pos):
                            if event.button == 4:
                                self.camera.zoom_at(1.12, event.pos, map_rect)
                            elif event.button == 5:
                                self.camera.zoom_at(0.89, event.pos, map_rect)

                elif event.type == pygame.MOUSEMOTION:
                    if not self.modal.open and self.mode in ("game", "realm_select") and self._mouse_down_in_map:
                        dx = abs(event.pos[0] - self._mouse_down_pos[0])
                        dy = abs(event.pos[1] - self._mouse_down_pos[1])
                        if not self._drag_started and (dx + dy) > self._mouse_drag_threshold:
                            self._drag_started = True
                            self.camera.begin_drag(self._mouse_down_pos)

                        if self._drag_started:
                            self.camera.drag_to(event.pos)

                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        if self.mode in ("game", "realm_select") and self._mouse_down_in_map:
                            if self._drag_started:
                                self.camera.end_drag()
                            else:
                                map_rect = self._get_map_rect()
                                if map_rect.collidepoint(event.pos) and not self._point_in_ui(event.pos):
                                    if self.mode == "game":
                                        if not self._try_open_tower_event(event.pos):
                                            if self._handle_army_click(event.pos, map_rect):
                                                self._mouse_down_in_map = False
                                                self._drag_started = False
                                                continue
                                            wp = self.camera.screen_to_world(event.pos, map_rect, use_target=False)
                                            prov = self.world.province_at_world(wp)
                                            if prov is not None:
                                                self._handle_war_goal_click(prov)
                                                self.army_selected = False
                                                self.selected_province = prov
                                                self.right_panel_open = True
                                                if prov.realm_id != self.player_realm_id:
                                                    self.left_panel_open = True
                                                self._building_menu_slot = None
                                                self.push_log(f"{self.date}: Selected {prov.name}.")
                                    elif self.mode == "realm_select":
                                        wp = self.camera.screen_to_world(event.pos, map_rect, use_target=False)
                                        prov = self.world.province_at_world(wp)
                                        if prov is not None:
                                            self.selected_province = prov
                                            self.realm_candidate_id = prov.realm_id
                            self._mouse_down_in_map = False
                            self._drag_started = False
                    elif event.button == 3:
                        if self.mode == "game" and not self.modal.open:
                            map_rect = self._get_map_rect()
                            if map_rect.collidepoint(event.pos) and not self._point_in_ui(event.pos):
                                self._handle_army_move(event.pos, map_rect)

            # Continuous controls
            if self.mode in ("game", "realm_select"):
                self._map_controls(dt)

            # Time + camera easing
            if self.mode == "game":
                self._update_time(dt)
            if self.mode in ("game", "realm_select"):
                self.camera.update(dt)
            self._update_right_panel_anim(dt)
            self._update_left_panel_anim(dt)
            if self.mode == "game":
                self._update_army_flash(dt)

            # Draw
            clickables = []
            if self.mode == "menu":
                clickables = self._draw_main_menu(self.screen)
                modal_clickables = self.modal.draw(self.screen, self.ui.panel_tile)
            elif self.mode == "storyteller":
                clickables = self._draw_storyteller_menu(self.screen)
                modal_clickables = self.modal.draw(self.screen, self.ui.panel_tile)
            elif self.mode == "realm_select":
                clickables = self._draw_realm_menu(self.screen)
                modal_clickables = self.modal.draw(self.screen, self.ui.panel_tile)
            else:
                self.screen.fill(BG_COLOR)

                # Decorative background panels behind everything
                bg = self._get_game_bg(self.screen.get_size())
                self.screen.blit(bg, (0, 0))

                # Map
                map_rect = self._get_map_rect()
                war_overlay, war_overlay_key = self._get_war_border_overlay()
                siege_overlay, siege_overlay_key = self._get_siege_overlay()
                overlays = []
                overlay_key = []
                if siege_overlay is not None:
                    overlays.append(siege_overlay)
                    overlay_key.append(("siege", siege_overlay_key))
                if war_overlay is not None:
                    overlays.append(war_overlay)
                    overlay_key.append(("war", war_overlay_key))
                if not overlays:
                    overlays = None
                    overlay_key = None
                else:
                    overlay_key = tuple(overlay_key)
                self.map_renderer.draw(self.screen, map_rect, overlays, overlay_key)
                self._draw_selected_province_highlight(self.screen, map_rect)
                self._draw_army_muster_marker(self.screen, map_rect)
                self._draw_enemy_armies(self.screen, map_rect)
                self._draw_army_route_arrow(self.screen, map_rect)
                self._draw_siege_status(self.screen, map_rect)

                # UI panels
                state = {
                    "date": self.date,
                    "resources": self.resources,
                    "speed_level": self.speed_level,
                    "character": self.character,
                    "army": self.army,
                    "selected_province": self.selected_province,
                    "log": self.log,
                    "realm_names": self.world.realm_names,
                    "realm_rulers": self.world.realm_rulers,
                    "realm_colors": self.world.realm_colors,
                    "player_realm_id": self.player_realm_id,
                    "population": self.population,
                    "army_raising": self.army_raising,
                    "food": self.food,
                    "threat": self.threat,
                    "building_menu_slot": self._building_menu_slot,
                    "wars": self.wars,
                    "stress": int(round(self.stress)),
                    "dread": int(round(self.dread)),
                    "lifestyle_focus": self.lifestyle_focus,
                    "lifestyle_perks": dict(self.lifestyle_perks),
                    "active_schemes": list(self.active_schemes),
                }

                clip_draw(self.screen, self.layout.top, lambda: clickables.extend(self.ui.draw_top_bar(self.screen, self.layout.top, state)))
                war_btns, war_rects = self.ui.draw_war_floating(self.screen, self.layout.top, state)
                clickables.extend(war_btns)
                self._war_float_rects = war_rects
                left_character = self.character
                left_realm_id = self.player_realm_id
                if self.selected_province is not None and self.selected_province.realm_id != self.player_realm_id:
                    rid = self.selected_province.realm_id
                    if 0 <= rid < len(self.world.realm_rulers):
                        left_character = self.world.realm_rulers[rid]
                        left_realm_id = rid
                left_state = dict(state)
                left_state["character"] = left_character
                left_state["character_realm_id"] = left_realm_id
                npc_target = self._get_npc_target()
                left_state["npc_target"] = npc_target
                left_state["npc_actions_enabled"] = True
                left_state["diplomacy"] = self._diplomacy_snapshot(npc_target.get("id")) if npc_target else None

                clickables.extend(self._draw_left_panel_animated(self.screen, left_state))
                clickables.extend(self._draw_right_panel_animated(self.screen, state))
                clickables.extend(self.ui.draw_bottom_bar(self.screen, self.layout.bottom, state))

                # Modal on top
                modal_clickables = self.modal.draw(self.screen, self.ui.panel_tile)

            # Edge-triggered click dispatch
            now_down = pygame.mouse.get_pressed(num_buttons=3)[0]
            if self._prev_mouse_down and (not now_down):
                mx, my = pygame.mouse.get_pos()
                if self.modal.open:
                    for r, cb in modal_clickables:
                        if r.collidepoint((mx, my)):
                            cb()
                            break
                else:
                    for r, action in clickables:
                        if r.collidepoint((mx, my)):
                            self._handle_action(action)
                            break
            self._prev_mouse_down = now_down

            pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    GameApp().run()
