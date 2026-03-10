from systems.buildings import (
    BUILDINGS,
    make_building,
    get_building_id,
    get_building_level,
    building_food_output,
    building_gold_upkeep,
    building_gold_rate_bonus,
    building_piety_rate_bonus,
    building_levy_mult_bonus,
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

    def _force_exit_game(self):
        self.running = False

    def _exit_game(self):
        self._confirm_unsaved_progress("Exit Without Saving", "deny", self._force_exit_game)

    def _realm_building_effects(self, rid):
        effects = {
            "gold_upkeep": 0.0,
            "gold_rate_bonus": 0.0,
            "piety_rate_bonus": 0.0,
            "levy_mult_bonus": 0.0,
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
                effects["levy_mult_bonus"] += building_levy_mult_bonus(b)
        return effects

    def _monthly_population_tax_income(self):
        population = max(0, int(self.population))
        try:
            stewardship = int(self._stat_value(self.character, "Stewardship", default=8))
        except Exception:
            stewardship = 8
        stewardship = max(0, min(40, stewardship))

        # Gold is driven by population tax yield and scaled by ruler stewardship.
        base_tax_per_pop = 0.0014
        stewardship_multiplier = 0.75 + (0.06 * stewardship)
        return max(0, int(round(population * base_tax_per_pop * stewardship_multiplier)))

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
        build_pressure = 1.4 + min(3.0, build_cost / 120.0)
        self._register_threat_activity(build_pressure)
        self._building_menu_slot = None
        self._mark_progress_unsaved()

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
        upgrade_pressure = 1.0 + min(2.4, upgrade_cost / 150.0)
        self._register_threat_activity(upgrade_pressure)
        self._building_menu_slot = None
        self._mark_progress_unsaved()

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
        self._mark_progress_unsaved()
        self.food = self._compute_food_values()
        self._recompute_resource_rates()
        self._update_army_max()
        self._register_threat_activity(0.6)
        self._building_menu_slot = None

    def _recompute_resource_rates(self):
        effects = self._realm_building_effects(self.player_realm_id)
        tax_income = self._monthly_population_tax_income()
        building_gold = int(round(float(effects.get("gold_rate_bonus", 0.0))))
        upkeep_penalty = int(round(float(effects.get("gold_upkeep", 0.0)) * 0.45))
        self.resources["gold_rate"] = int(tax_income + building_gold - upkeep_penalty)

        piety_rate = compute_piety_rate(self.character)[0]
        piety_rate += int(round(float(effects.get("piety_rate_bonus", 0.0))))
        self.resources["piety_rate"] = int(piety_rate)

    def _apply_monthly_resource_rates(self):
        self._recompute_resource_rates()

        for res in ("gold", "piety"):
            rate = self.resources.get(f"{res}_rate", 0)
            if rate == 0:
                continue
            self.resources[res] += rate

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
        self._sync_baseline_threat()
        self._update_army_max()
