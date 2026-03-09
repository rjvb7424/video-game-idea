from core.math_utils import clamp


class PoliticsActionsMixin:
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

        gold_cost = 70
        if self.resources.get("gold", 0) < gold_cost:
            self.modal.show(
                "Insufficient Gold",
                [
                    f"Marriage diplomacy costs {gold_cost} gold.",
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

        self.resources["gold"] = max(0, int(self.resources.get("gold", 0)) - gold_cost)
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
        if self.resources.get("gold", 0) < gold_cost:
            self.modal.show(
                "Insufficient Gold",
                [
                    f"Assassination plots cost {gold_cost} gold.",
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
    def _decision_available(self, key, *, gold=0, piety=0, requires_peace=False):
        cd = int(self.decision_cooldowns.get(key, 0))
        if cd > 0:
            return False, f"Cooldown: {self._days_label(cd)}"
        if requires_peace and self.wars:
            return False, "Unavailable while at war."
        if self.resources.get("gold", 0) < gold:
            return False, f"Need {gold} gold."
        if self.resources.get("piety", 0) < piety:
            return False, f"Need {piety} piety."
        return True, "Ready"
    def _open_decisions_modal(self):
        feast_ok, feast_msg = self._decision_available("feast", gold=55, requires_peace=True)
        pilgrim_ok, pilgrim_msg = self._decision_available("pilgrimage", gold=85, requires_peace=False)
        epic_ok, epic_msg = self._decision_available("epic", gold=75, requires_peace=False)

        lines = [
            "Major Decisions",
            f"Hold Feast: {feast_msg}",
            f"Go on Pilgrimage: {pilgrim_msg}",
            f"Commission Epic: {epic_msg}",
            "",
            f"Resources: Gold {int(self.resources.get('gold', 0))}, "
            f"Piety {int(self.resources.get('piety', 0))}",
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
                "Stress reduced and foreign opinion improved.",
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
                "Piety increased; stress reduced.",
            ],
            [
                ("OK", "accept", lambda: self._open_decisions_modal()),
            ],
        )
    def _decision_commission_epic(self):
        ok, msg = self._decision_available("epic", gold=75)
        if not ok:
            self.modal.show("Decision Unavailable", [msg], [("OK", "accept", lambda: self._open_decisions_modal())])
            return

        self.resources["gold"] = max(0, int(self.resources.get("gold", 0)) - 75)
        self.resources["piety"] = int(self.resources.get("piety", 0)) + 35
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
                "Piety rises, but the campaign is expensive.",
            ],
            [
                ("OK", "accept", lambda: self._open_decisions_modal()),
            ],
        )
