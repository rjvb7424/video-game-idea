import json
import os

from core.date import GameDate
from core.math_utils import clamp
from systems.buildings import BUILDINGS, get_building_id, get_building_level, make_building
from systems.traits import _stats_list_to_dict, apply_trait_effects, normalize_traits


class PersistenceMixin:
    def _ensure_save_dir(self):
        os.makedirs(self.save_dir, exist_ok=True)

    def _has_unsaved_progress_to_warn(self):
        return self.mode == "game" and bool(getattr(self, "_has_unsaved_progress", False))

    def _mark_progress_unsaved(self):
        if self.mode == "game":
            self._has_unsaved_progress = True

    def _mark_progress_saved(self):
        self._has_unsaved_progress = False

    def _confirm_unsaved_progress(self, continue_label, continue_kind, on_continue):
        if not self._has_unsaved_progress_to_warn():
            on_continue()
            return

        def continue_without_save():
            self.modal.close()
            on_continue()

        def save_then_continue():
            if self._save_game_to_file(self.latest_save_path, autosave=False, show_feedback=False):
                self.modal.close()
                on_continue()

        self.modal.show(
            "Unsaved Progress",
            [
                "You have unsaved progress.",
                "If you leave without saving, all progress since your last save will be lost.",
            ],
            [
                ("Save & Continue", "primary", save_then_continue),
                (continue_label, continue_kind, continue_without_save),
                ("Cancel", "secondary", lambda: self.modal.close()),
            ],
        )

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
            "save_version": 4,
            "storyteller_id": self.storyteller.get("id") if isinstance(self.storyteller, dict) else None,
            "state": {
                "date": {"year": int(self.date.year), "month": int(self.date.month), "day": int(self.date.day)},
                "player_realm_id": int(self.player_realm_id),
                "resources": {
                    "gold": int(self.resources.get("gold", 0)),
                    "piety": int(self.resources.get("piety", 0)),
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
                        "war_type": "Conquest",
                        "goal_pid": war.get("goal_pid"),
                        "progress": float(war.get("progress", 0.0)),
                        "days": int(war.get("days", 0)),
                        "ready_prompted": bool(war.get("ready_prompted", False)),
                        "sieged": sorted(int(pid) for pid in self._get_war_sieged_set(war)),
                        "total_provs": int(war.get("total_provs", 0)),
                        "attacker": str(war.get("attacker", "player")),
                        "attacker_broken_days": max(0, int(war.get("attacker_broken_days", 0))),
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
                "threat_level": float(getattr(self, "_threat_level", self.threat)),
                "threat_inactive_days": int(getattr(self, "_threat_inactive_days", 0)),
                "log": list(self.log[-30:]),
            },
            "world": self._serialize_world_state(),
        }

    def _save_game_to_file(self, path=None, autosave=False, show_feedback=True):
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

        self._mark_progress_saved()

        if autosave:
            self.push_log(f"{self.date}: Autosaved campaign.")
            return True

        self.push_log(f"{self.date}: Saved campaign.")
        if show_feedback:
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
            for key in ("gold", "piety"):
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
            try:
                attacker_broken_days = max(0, int(entry.get("attacker_broken_days", 0)))
            except (TypeError, ValueError):
                attacker_broken_days = 0
            war = {
                "id": war_id,
                "target_id": target_id,
                "war_type": "Conquest",
                "goal_pid": goal_pid,
                "progress": float(clamp(float(entry.get("progress", 0.0)), 0.0, 100.0)),
                "days": max(0, int(entry.get("days", 0))),
                "ready_prompted": bool(entry.get("ready_prompted", False)),
                "sieged": sieged,
                "total_provs": max(0, int(entry.get("total_provs", 0))),
                "attacker": str(entry.get("attacker", "player")),
                "attacker_broken_days": attacker_broken_days,
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
        self._init_threat_state()
        try:
            loaded_threat = float(state.get("threat_level", state.get("threat", self.threat)))
        except (TypeError, ValueError):
            loaded_threat = float(self.threat)
        self._threat_level = clamp(loaded_threat, float(self.baseline_threat), 100.0)
        try:
            self._threat_inactive_days = max(0, int(state.get("threat_inactive_days", 0)))
        except (TypeError, ValueError):
            self._threat_inactive_days = 0
        self._threat_activity_today = False
        self.threat = int(clamp(round(self._threat_level), 0, 100))
        self._update_army_max()
        # Stripped character/diplomacy layer: enforce neutral state on load.
        self.realm_relations = {}
        self.realm_claims = set()
        self.realm_truces = {}
        self.claim_fabrication_cooldowns = {}
        self.alliances = set()
        self.active_schemes = []
        self.hooks = {}
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
        self._recompute_resource_rates()

        self._war_goal_selecting = False
        self._pending_war = None
        self._siege_state = None
        self._battle_state = None
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
        self._mark_progress_saved()
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
