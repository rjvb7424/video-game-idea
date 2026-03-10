import random

from core.math_utils import clamp
from events import date_ordinal
from systems.characters import generate_heir, generate_ruler, generate_spouse
from systems.traits import _stats_list_to_dict, apply_trait_effects, compute_piety_rate, normalize_traits


class PoliticsSystemsMixin:
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
                self._change_realm_opinion(target_rid, -10 if exposed else -4)
                self._adjust_stress(+2.0)
                self.push_log(f"{self.date}: Fabricated claim on {target_name}.")
            else:
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
                self._adjust_stress(+14.0 if exposed else +7.0)
                self.push_log(f"{self.date}: Murder scheme failed in {target_name}.")
            self._recompute_resource_rates()
            return
    def _adjust_stress(self, delta, reason=None):
        self.stress = 0.0
        self._stress_break_level = 0
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
            line = "You seek relief in excess."
        elif event == "charity":
            self.resources["gold"] = max(0, int(self.resources.get("gold", 0)) - (22 + 8 * level))
            self.resources["piety"] = int(self.resources.get("piety", 0)) + (15 + 8 * level)
            line = "You donate heavily to quiet your conscience."
        else:
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
            self.resources["piety"] = max(0, int(self.resources.get("piety", 0)) - 30)
            self.resources["piety_rate"] = compute_piety_rate(self.character)[0]
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

    def _non_human_attack_daily_chance(self):
        threat_value = int(clamp(getattr(self, "threat", 0), 0, 100))
        threat_ratio = threat_value / 100.0
        chance = 0.00045 + (threat_ratio ** 1.35) * 0.018
        if self.wars:
            chance *= 1.18
        return float(clamp(chance, 0.00035, 0.035))

    def _non_human_attack_scenario(self, severity):
        if severity >= 0.85:
            pool = [
                (
                    "Night Infiltration",
                    "Non-human infiltrators slipped into the realm at night, looted estates, and murdered sleeping households.",
                ),
                (
                    "Shadow Stalkers",
                    "Predatory stalkers shadowed travelers for days before killing isolated victims across the countryside.",
                ),
                (
                    "Frontier Gate Breach",
                    "A coordinated beast-pack overwhelmed a frontier gate and tore through nearby settlements.",
                ),
            ]
        elif severity >= 0.50:
            pool = [
                (
                    "Midnight Raids",
                    "Non-human raiders hit villages under darkness, killing defenders and carrying off valuables.",
                ),
                (
                    "Roadside Hunts",
                    "Roaming killers stalked caravans and struck when escorts were separated.",
                ),
                (
                    "Granary Massacre",
                    "A raiding pack slaughtered granary guards and stripped local stores.",
                ),
            ]
        else:
            pool = [
                (
                    "Outskirts Assault",
                    "A small non-human warband attacked outlying farms and murdered isolated families.",
                ),
                (
                    "Dusk Predation",
                    "Predators stalked workers at dusk, killing stragglers and seizing supplies.",
                ),
                (
                    "Hamlet Break-In",
                    "Night prowlers slipped into a hamlet, killed watchmen, and looted homes.",
                ),
            ]
        return self.world.rnd.choice(pool)

    def _resolve_non_human_attack(self):
        threat_value = int(clamp(getattr(self, "threat", 0), 0, 100))
        threat_ratio = threat_value / 100.0
        severity = float(clamp(0.18 + (threat_ratio * 0.95) + self.world.rnd.uniform(-0.10, 0.22), 0.08, 1.25))
        title, flavor = self._non_human_attack_scenario(severity)

        pop_before = int(self.population)
        pop_loss_rate = 0.00025 + (0.0045 * severity)
        if self.wars:
            pop_loss_rate += 0.0006
        self.world.adjust_population_for_realm(self.player_realm_id, -pop_loss_rate)
        self.population = self.world.total_population_for_realm(self.player_realm_id)
        pop_killed = max(0, pop_before - int(self.population))
        if pop_killed <= 0:
            victims = [p for p in self.world.provinces if p.realm_id == self.player_realm_id and p.population > 1]
            if victims:
                target = self.world.rnd.choice(victims)
                target.population = max(1, int(target.population) - 1)
                self.population = self.world.total_population_for_realm(self.player_realm_id)
                pop_killed = 1

        treasury = int(self.resources.get("gold", 0))
        loot_base = 12 + int(round(pop_before * 0.0007))
        loot_target = int(round(loot_base * (0.7 + 2.2 * severity)))
        gold_taken = min(treasury, max(5, loot_target))
        self.resources["gold"] = max(0, treasury - gold_taken)

        self.food = self._compute_food_values()
        self._update_army_max()
        self._sync_baseline_threat()
        self._recompute_resource_rates()
        self._adjust_stress(2.0 + severity * 7.0)

        severity_tag = "Severe" if severity >= 0.85 else ("Major" if severity >= 0.50 else "Minor")
        self.push_log(
            f"{self.date}: {title} ({severity_tag}). Lost {gold_taken} gold and {pop_killed:,} population."
        )
        if not self.modal.open:
            self.modal.show(
                "Non-Human Attack",
                [
                    flavor,
                    f"Loot taken: {gold_taken} gold.",
                    f"Deaths: {pop_killed:,} people.",
                    f"Threat at attack time: {threat_value}%.",
                    "Higher threat increases attack chance and severity.",
                ],
                [
                    ("OK", "accept", lambda: self.modal.close()),
                ],
            )

        next_cd = int(round(24 - (threat_ratio * 16.0) + self.world.rnd.randint(-3, 4)))
        self._non_human_attack_cooldown_days = max(4, min(32, next_cd))

    def _tick_non_human_attack_day(self):
        if self.campaign_result is not None:
            return
        cd = max(0, int(getattr(self, "_non_human_attack_cooldown_days", 0)))
        if cd > 0:
            self._non_human_attack_cooldown_days = cd - 1
            return
        chance = self._non_human_attack_daily_chance()
        if self.world.rnd.random() >= chance:
            return
        self._resolve_non_human_attack()

    def _tick_politics_day(self):
        self._decrement_days_map(self.realm_truces)
        self._decrement_days_map(self.claim_fabrication_cooldowns)
        self.active_schemes = []
        self.hooks = {}
        self.decision_cooldowns = {}
        self.dread = 0.0
        self.stress = 0.0
        if self.subjugation_cooldown_days > 0:
            self.subjugation_cooldown_days -= 1
        self._tick_non_human_attack_day()
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
