import random

from core.math_utils import clamp
from events import date_ordinal
from systems.characters import generate_heir, generate_ruler, generate_spouse
from systems.traits import _stats_list_to_dict, apply_trait_effects, compute_piety_rate, normalize_traits


class PoliticsMixin:
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
            "manpower_total": self._realm_total_manpower(rid),
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
    def _realm_total_manpower(self, rid):
        if rid is None or not (0 <= rid < len(self.world.realm_names)):
            return 0
        pop = self.world.total_population_for_realm(rid)
        effects = self._realm_building_effects(rid)
        levy_mult = 1.0 + float(effects.get("levy_mult_bonus", 0.0))
        manpower = int(round(pop * self.army_pop_ratio * max(0.20, levy_mult)))
        return max(0, manpower)
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
        # Realm goal/campaign win-condition checks are disabled for sandbox play.
        return
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
        claims = len(self.realm_claims)
        alliances = len(self.alliances)
        lines = [
            f"Realm size: {held}/{len(self.world.provinces)} provinces",
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
