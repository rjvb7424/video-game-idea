import os

import pygame

import event_content
from core.camera import Camera
from core.date import GameDate
from events import EventRegistry, EventSystem, register_all
from rendering.map_view import MapRenderer
from systems.traits import _stats_list_to_dict, apply_trait_effects, compute_piety_rate, normalize_traits
from ui.layout import Layout
from ui.manager import UIManager
from ui.modal import Modal
from world.map import MapWorld


class BootstrapMixin:
    def _bootstrap(self):
        self._init_runtime()
        self._init_save_state()
        self._init_storytellers()
        self._init_ui_and_world()
        self._init_time_and_panels()
        self._init_events()
        self._init_resources_and_character()
        self._init_politics()
        self._init_lifestyle_systems()
        self._init_armies_and_food()
        self._init_campaign_state()
        self._init_input_state()
        self.running = True
        self._apply_window_size_desktop()

    def _init_runtime(self):
        os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
        os.environ.setdefault("SDL_VIDEO_WINDOW_POS", "center")
        pygame.init()
        pygame.display.set_caption("CK1-Inspired Grand Strategy UI (Pygame)")
        self.windowed_size = (1280, 720)
        self.screen = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
        self.clock = pygame.time.Clock()

    def _init_save_state(self):
        self.mode = "menu"
        self.save_dir = os.path.join(os.path.dirname(__file__), "..", "saves")
        self.save_dir = os.path.abspath(self.save_dir)
        self.latest_save_path = os.path.join(self.save_dir, "campaign_latest.json")
        self.autosave_path = os.path.join(self.save_dir, "campaign_autosave.json")
        self._autosave_interval_months = 3

    def _init_storytellers(self):
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
            },
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

    def _init_ui_and_world(self):
        self.ui = UIManager(seed=11)
        self.layout = Layout(*self.screen.get_size())
        self._game_bg_cache = {}

        self.world = MapWorld(seed=7, world_size=(3200, 2200), cell_scale=4)
        self.camera = Camera(viewport_size=(100, 100), world_size=(self.world.world_w, self.world.world_h))
        self.map_renderer = MapRenderer(self.world, self.camera)
        self.camera.set_viewport(self._get_map_rect().size)
        self._prov_adj = self.world._build_province_adjacency()

        self.modal = Modal()

    def _init_time_and_panels(self):
        self.date = GameDate(1067, 1, 21)
        self.speed_level = 0
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

    def _init_events(self):
        self._event_flags = {}
        self._event_pending = []
        self._event_resume_speed = None

        self.event_registry = EventRegistry(seed=123)
        register_all(self.event_registry, event_content)
        self.base_event_daily_chance = 0.05
        self.events = EventSystem(self, self.event_registry, daily_chance=self.base_event_daily_chance, seed=999)

    def _init_resources_and_character(self):
        self.resources = {
            "gold": 200,
            "gold_rate": +1,
            "piety": 1000,
            "prestige": 350,
            "renown": 120,
            "renown_rate": 1,
        }

        self.wars = []
        self._war_next_id = 1
        self._war_focus_id = None
        self._war_border_overlay = None
        self._war_border_overlay_key = None
        self._pending_war = None
        self._war_goal_selecting = False

        self.siege_prep_days = 7
        self.siege_assault_days = 21
        self._siege_state = None
        self._siege_overlay = None
        self._siege_overlay_key = None
        self._siege_stripe_base = None
        self._siege_stripe_base_key = None

        self.enemy_raise_rate = 0.12
        self.ai_engage_ratio = 1.1
        self.ai_avoid_ratio = 0.85
        self.stack_wipe_attacker_morale = 60
        self.stack_wipe_defender_morale = 15
        self.morale_recovery_per_day = 1.5

        self.player_realm_id = self.world.player_realm_id
        self.character = self.world.realm_rulers[self.player_realm_id]

        if "base_stats" not in self.character:
            self.character["base_stats"] = _stats_list_to_dict(self.character.get("stats", []))
        apply_trait_effects(self.character)
        self.character["traits"] = normalize_traits(self.character.get("traits", []))
        self.resources["piety_rate"] = compute_piety_rate(self.character)[0]
        self.resources["prestige_rate"] = self._compute_prestige_rate(self.character)

    def _init_politics(self):
        self.realm_relations = {}
        self.realm_claims = set()
        self.realm_truces = {}
        self.claim_fabrication_cooldowns = {}
        self.alliances = set()
        self.subjugation_cooldown_days = 0

    def _init_lifestyle_systems(self):
        self.active_schemes = []
        self._next_scheme_id = 1
        self.hooks = {}
        self.lifestyle_focuses = ("diplomacy", "martial", "stewardship", "intrigue", "learning")
        self.lifestyle_focus = "stewardship"
        self.lifestyle_xp = {k: 0.0 for k in self.lifestyle_focuses}
        self.lifestyle_perks = {k: 0 for k in self.lifestyle_focuses}
        self._lifestyle_picker_index = self.lifestyle_focuses.index(self.lifestyle_focus)
        self.stress = 0.0
        self._stress_break_level = 0
        self.dread = 0.0
        self.decision_cooldowns = {}
        self._raid_cooldown_days = 0
        self._ai_war_cooldown_days = 0
        self.resources["piety_rate"] = compute_piety_rate(self.character)[0]
        self.resources["prestige_rate"] = self._compute_prestige_rate(self.character)

    def _init_armies_and_food(self):
        self.army_pop_ratio = 0.12
        self.army_raise_rate = 0.15
        self.army_move_speed = 110
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
        self.food = (0, 0)
        self.food_consumption_per_pop = 0.39
        self._rebalance_population_to_farms()
        self.population = self.world.total_population_for_realm(self.player_realm_id)
        self._baseline_population = max(1, self.population)
        self.food = self._compute_food_values()
        self.threat = self._compute_threat()
        self._update_army_max()
        self._init_enemy_armies()

    def _init_campaign_state(self):
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

    def _init_input_state(self):
        self._mouse_down_in_map = False
        self._mouse_down_pos = (0, 0)
        self._mouse_drag_threshold = 5
        self._drag_started = False
        self._prev_mouse_down = False
