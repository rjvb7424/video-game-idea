
class PoliticsOverviewMixin:
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
