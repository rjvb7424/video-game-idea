from core.math_utils import clamp
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
from systems.traits import compute_piety_rate


class EconomyMixin:
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
        self.modal.show(
            "Game Menu",
            [
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

        production, consumption = self._compute_food_values()
        self.food = (production, consumption)

        if consumption <= 0:
            food_balance = 1.0
        else:
            food_balance = (production - consumption) / consumption
        food_balance = max(-1.0, min(1.0, food_balance))

        if food_balance >= 0:
            pop_rate = 0.001 + 0.004 * food_balance
        else:
            pop_rate = 0.001 + 0.010 * food_balance

        if abs(pop_rate) > 0.00001:
            self.world.adjust_population_for_realm(self.player_realm_id, pop_rate)

        self.population = self.world.total_population_for_realm(self.player_realm_id)
        self.threat = self._compute_threat()
        self._update_army_max()
