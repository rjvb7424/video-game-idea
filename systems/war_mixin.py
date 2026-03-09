import pygame

from core.math_utils import clamp


class WarMixin:
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
            "war_type": "Conquest",
            "goal_pid": goal_pid,
            "progress": 0.0,
            "days": 0,
            "ready_prompted": False,
            "sieged": set(),
            "total_provs": total_provs,
            "attacker": "ai",
            "attacker_broken_days": 0,
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
        self.push_log(f"{self.date}: {attacker_name} declares a conquest war.")
        if not self.modal.open:
            self.modal.show(
                "Enemy Declaration",
                [
                    f"{attacker_name} declared a conquest war on your realm.",
                    "Raise levies and hold your frontier.",
                ],
                [
                    ("View War", "accept", lambda wid=war["id"]: self._open_war_details(wid)),
                ],
            )
        self._mark_progress_unsaved()
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

    def _realms_share_land_border(self, rid_a, rid_b):
        if rid_a is None or rid_b is None:
            return False
        if rid_a == rid_b:
            return True
        for prov in self.world.provinces:
            if prov.realm_id != rid_a:
                continue
            pid = prov.id
            if not (0 <= pid < len(self._prov_adj)):
                continue
            for nb in self._prov_adj[pid]:
                if 0 <= nb < len(self.world.provinces) and self.world.provinces[nb].realm_id == rid_b:
                    return True
        return False

    def _can_declare_war_type(self, target_rid, war_type):
        if target_rid is None or target_rid == self.player_realm_id:
            return False, "Invalid target."

        if war_type == "Conquest":
            if not self._valid_war_goal_provinces(target_rid):
                return False, "No bordering provinces available to conquer."
            return True, "Available. Choose a bordering province from the dropdown, then declare."

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
        if war_type == "Subjugation":
            self.resources["prestige"] = max(0, int(self.resources.get("prestige", 0)) - 320)
            self.subjugation_cooldown_days = max(self.subjugation_cooldown_days, 3650)
        elif war_type == "Holy War":
            self.resources["piety"] = max(0, int(self.resources.get("piety", 0)) - 250)
            self.resources["prestige"] = max(0, int(self.resources.get("prestige", 0)) - 60)
        self.dread = clamp(float(self.dread) + 4.0, 0.0, 100.0)
        self._change_realm_opinion(target_rid, -18)

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

    def _resolve_war_if_complete(self, war):
        if not war:
            return None
        self._update_war_progress(war)
        if float(war.get("progress", 0.0)) < 100.0:
            return None
        if war.get("attacker") == "ai":
            return self._resolve_defender_victory(war, reason="Defender victory secured.")
        self._apply_war_demands(war)
        target_name = self._get_war_target_name(war)
        return f"Won war against {target_name}."

    def _attacker_army_state(self, war):
        if not war:
            return 0, False
        if war.get("attacker") == "player":
            return int(self.army.get("raised", 0)), bool(self.army_raising)
        rid = war.get("target_id")
        enemy = self._get_enemy_army_for_realm(rid)
        if enemy is None:
            return 0, False
        return int(enemy.get("army", {}).get("raised", 0)), bool(enemy.get("raising", False))

    def _war_reparation_amount(self, war):
        days = max(0, int((war or {}).get("days", 0)))
        sieged = len(self._get_war_sieged_set(war or {}))
        raw = 40 + (days // 8) + (sieged * 10)
        return int(clamp(raw, 35, 220))

    def _apply_defender_reparations(self, war):
        due = self._war_reparation_amount(war)
        if war.get("attacker") == "player":
            treasury = int(self.resources.get("gold", 0))
            paid = min(due, treasury)
            debt = due - paid
            self.resources["gold"] = max(0, treasury - paid)
            prestige_loss = 24 + (debt // 3)
            renown_loss = 10 + (debt // 6)
            self.resources["prestige"] = max(0, int(self.resources.get("prestige", 0)) - prestige_loss)
            self.resources["renown"] = max(0, int(self.resources.get("renown", 0)) - renown_loss)
            self._adjust_stress(+8.0)
            self._recompute_resource_rates()
            return {"due": due, "paid": paid, "debt": debt}

        self.resources["gold"] = int(self.resources.get("gold", 0)) + due
        self.resources["prestige"] = int(self.resources.get("prestige", 0)) + 18
        self.resources["renown"] = int(self.resources.get("renown", 0)) + 10
        self._adjust_stress(-4.0)
        self._recompute_resource_rates()
        return {"due": due, "paid": due, "debt": 0}

    def _resolve_defender_victory(self, war, reason=None):
        if not war:
            return "War ended."
        target_name = self._get_war_target_name(war)
        rep = self._apply_defender_reparations(war)
        if war.get("attacker") == "player":
            detail = f"{target_name} held their lines. You paid {rep['paid']} gold in reparations."
            if rep.get("debt", 0) > 0:
                detail += " Unable to pay in full; prestige and renown were lost."
            if reason:
                return f"{reason} {detail}"
            return detail
        detail = f"You repelled {target_name}'s invasion and received {rep['paid']} gold in reparations."
        if reason:
            return f"{reason} {detail}"
        return detail

    def _check_attacker_breakdown(self, war):
        raised, raising = self._attacker_army_state(war)
        broken_days = int(war.get("attacker_broken_days", 0))
        if raised <= 0 and not raising:
            broken_days += 1
        else:
            broken_days = 0
        war["attacker_broken_days"] = broken_days
        if broken_days < 14:
            return None
        return self._resolve_defender_victory(war, reason="Attacker forces collapsed.")

    def _update_war_tick(self):
        if not self.wars:
            return
        resolved = []
        for war in list(self.wars):
            war["days"] += 1
            self._update_war_progress(war)
            defender_msg = self._check_attacker_breakdown(war)
            if defender_msg is not None:
                resolved.append((war.get("id"), defender_msg))
                continue
            done_msg = self._resolve_war_if_complete(war)
            if done_msg is not None:
                resolved.append((war.get("id"), done_msg))
        for wid, msg in resolved:
            if wid is not None and self._get_war_by_id(wid):
                self._end_war(wid, msg)

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
        if progress >= 100.0:
            done_msg = self._resolve_war_if_complete(war)
            wid = war.get("id")
            if done_msg is not None and wid is not None and self._get_war_by_id(wid):
                self._end_war(wid, done_msg)

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
        if self._battle_state:
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
        if self._battle_state is not None:
            if self._siege_state is not None:
                self._clear_siege_state()
            return
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
        war_type = "Conquest"
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
            return False
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
            return False
        if not isinstance(goal_pid, int) or not (0 <= goal_pid < len(self.world.provinces)):
            self.modal.show(
                "No Province Selected",
                [
                    "Select a target province before declaring war.",
                ],
                [
                    ("OK", "accept", lambda: self.modal.close()),
                ],
            )
            return False
        valid_pids = self._valid_war_goal_provinces(target_rid)
        if goal_pid not in valid_pids:
            target_name = self._get_war_target_name(target_rid)
            self.modal.show(
                "Invalid War Goal",
                [
                    f"The selected province must border your realm and belong to {target_name}.",
                ],
                [
                    ("OK", "accept", lambda: self.modal.close()),
                ],
            )
            return False
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
            "attacker_broken_days": 0,
        }
        self._war_next_id += 1
        self._pay_war_cost(target_rid, war_type)
        self.wars.append(war)
        self._ensure_enemy_army_for_war(target_rid)
        self._war_focus_id = war["id"]
        self._update_war_progress(war)
        self._recompute_resource_rates()
        self._mark_progress_unsaved()
        target_name = self._get_war_target_name(target_rid)
        self.push_log(f"{self.date}: Declared war on {target_name}.")
        self._open_war_details(war["id"])
        return True

    def _open_war_type_modal(self, target_rid):
        war_type = "Conquest"
        target_name = self._get_war_target_name(target_rid)
        allowed, reason = self._can_declare_war_type(target_rid, war_type)
        if not self._pending_war or self._pending_war.get("target_id") != target_rid:
            self._pending_war = {"target_id": target_rid, "war_type": war_type, "goal_pid": None, "dropdown_index": 0}

        valid_pids = self._valid_war_goal_provinces(target_rid)

        goal_pid = self._pending_war.get("goal_pid")
        goal_name = "None selected"
        goal_realm_name = "—"
        goal_ready = False
        if isinstance(goal_pid, int) and 0 <= goal_pid < len(self.world.provinces) and goal_pid in valid_pids:
            goal_prov = self.world.provinces[goal_pid]
            goal_name = goal_prov.name
            if 0 <= goal_prov.realm_id < len(self.world.realm_names):
                goal_realm_name = self.world.realm_names[goal_prov.realm_id]
            if goal_prov.realm_id == target_rid:
                goal_ready = True
        else:
            self._pending_war["goal_pid"] = None
            if valid_pids:
                idx = max(0, min(int(self._pending_war.get("dropdown_index", 0)), len(valid_pids) - 1))
                self._pending_war["dropdown_index"] = idx

        self._war_goal_selecting = False
        lines = [
            f"Target realm: {target_name}.",
            f"Selected province: {goal_name}.",
            f"Province realm: {goal_realm_name}.",
            reason,
            "Use Select Province dropdown, then press Declare.",
        ]
        if not valid_pids:
            lines.append("No valid provinces.")
        elif goal_pid is not None and not goal_ready:
            lines.append(f"Declare is disabled: province must border your realm and belong to {target_name}.")
        self.modal.show(
            "Declare War",
            lines,
            [
                ("Cancel", "deny", lambda: self._cancel_pending_war()),
                (
                    "Select Province",
                    "secondary" if (allowed and bool(valid_pids)) else "disabled",
                    (lambda rid=target_rid: self._begin_war_goal_selection(rid)) if allowed else (lambda: None),
                ),
                (
                    "Declare",
                    "accept" if (allowed and goal_ready and bool(valid_pids)) else "disabled",
                    (lambda rid=target_rid: self._declare_pending_war(rid)) if (allowed and goal_ready) else (lambda: None),
                ),
            ],
        )

    def _begin_war_goal_selection(self, target_rid, war_type="Conquest"):
        war_type = "Conquest"
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
        if not self._pending_war or self._pending_war.get("target_id") != target_rid:
            self._pending_war = {"target_id": target_rid, "war_type": war_type, "goal_pid": None, "dropdown_index": 0}
        else:
            self._pending_war["war_type"] = war_type
        idx = int(self._pending_war.get("dropdown_index", 0))
        self._open_war_province_dropdown(target_rid, idx)

    def _valid_war_goal_provinces(self, target_rid):
        if target_rid is None:
            return []
        border_pids = set()
        for prov in self.world.provinces:
            if prov.realm_id != self.player_realm_id:
                continue
            pid = prov.id
            if not (0 <= pid < len(self._prov_adj)):
                continue
            for nb in self._prov_adj[pid]:
                if 0 <= nb < len(self.world.provinces) and self.world.provinces[nb].realm_id == target_rid:
                    border_pids.add(nb)
        pids = sorted(border_pids, key=lambda pid: self.world.provinces[pid].name.lower())
        return pids

    def _open_war_province_dropdown(self, target_rid, index=0):
        war_type = "Conquest"
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
        if not self._pending_war or self._pending_war.get("target_id") != target_rid:
            self._pending_war = {"target_id": target_rid, "war_type": war_type, "goal_pid": None, "dropdown_index": 0}

        valid_pids = self._valid_war_goal_provinces(target_rid)
        if not valid_pids:
            self.modal.show(
                "Province List",
                ["No valid provinces."],
                [("Back", "secondary", lambda rid=target_rid: self._open_war_type_modal(rid))],
            )
            return
        index = max(0, min(int(index), len(valid_pids) - 1))
        self._pending_war["dropdown_index"] = index
        current_pid = valid_pids[index]
        current_name = self.world.provinces[current_pid].name

        actions = [
            ("Prev", "secondary", lambda rid=target_rid, idx=index - 1: self._open_war_province_dropdown(rid, idx)),
            ("Next", "secondary", lambda rid=target_rid, idx=index + 1: self._open_war_province_dropdown(rid, idx)),
            ("Select", "accept", lambda rid=target_rid, pid=current_pid, idx=index: self._select_war_goal_from_dropdown(rid, pid, idx)),
            ("Back", "deny", lambda rid=target_rid: self._open_war_type_modal(rid)),
        ]

        self.modal.show(
            "Select Province",
            [
                f"Dropdown list ({index + 1}/{len(valid_pids)}).",
                f"Target realm: {self._get_war_target_name(target_rid)}.",
                f"Current province: {current_name}.",
                "Only valid provinces are shown.",
            ],
            actions,
        )

    def _select_war_goal_from_dropdown(self, target_rid, goal_pid, index=0):
        valid_pids = self._valid_war_goal_provinces(target_rid)
        if goal_pid not in valid_pids:
            self._open_war_province_dropdown(target_rid, index)
            return
        if not self._pending_war or self._pending_war.get("target_id") != target_rid:
            self._pending_war = {"target_id": target_rid, "war_type": "Conquest", "goal_pid": None, "dropdown_index": 0}
        self._pending_war["goal_pid"] = goal_pid
        self._pending_war["dropdown_index"] = max(0, int(index))
        self.push_log(f"{self.date}: Selected {self.world.provinces[goal_pid].name} from dropdown.")
        self._open_war_type_modal(target_rid)

    def _declare_pending_war(self, target_rid=None):
        if not isinstance(self._pending_war, dict):
            self.modal.close()
            return
        rid = self._pending_war.get("target_id") if target_rid is None else target_rid
        if rid is None:
            self.modal.close()
            return
        if rid != self._pending_war.get("target_id"):
            self._open_war_type_modal(rid)
            return
        goal_pid = self._pending_war.get("goal_pid")
        if not isinstance(goal_pid, int) or not (0 <= goal_pid < len(self.world.provinces)):
            self._open_war_type_modal(rid)
            return
        if self.world.provinces[goal_pid].realm_id != rid:
            self._open_war_type_modal(rid)
            return
        self._war_goal_selecting = False
        if self._start_war(rid, war_type=self._pending_war.get("war_type", "Conquest"), goal_pid=goal_pid):
            self._pending_war = None

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
        self._mark_progress_unsaved()

    def _handle_war_goal_click(self, prov):
        return False

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
        attacker_rid = self.player_realm_id if attacker == "player" else war.get("target_id")
        defender_rid = war.get("target_id") if attacker == "player" else self.player_realm_id
        attacker_manpower = self._realm_total_manpower(attacker_rid)
        defender_manpower = self._realm_total_manpower(defender_rid)
        reparations = self._war_reparation_amount(war)
        self.modal.show(
            "War Status",
            [
                f"War against {target_name}.",
                f"War type: {war_type}.",
                f"Initiator: {'Enemy Realm' if attacker == 'ai' else 'Your Realm'}.",
                f"War progress: {progress}%.",
                f"Sieged provinces: {len(sieged)}/{total}.",
                f"Attacker manpower: {attacker_manpower:,}.",
                f"Defender manpower: {defender_manpower:,}.",
                "Attacker wins at 100% and gains territory.",
                f"Defender victory keeps current borders and forces about {reparations}g reparations from attacker.",
                "War resolves automatically when attacker reaches 100% progress.",
                "Surrender concedes territory and pays reparations." if attacker == "ai" else "Surrender concedes the war and pays reparations.",
            ],
            [
                ("Surrender", "deny", lambda: self._surrender_war(war_id)),
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
        msg = self._resolve_defender_victory(war, reason=f"You surrendered against {target_name}.")
        self._end_war(war_id, msg)

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
        self._mark_progress_unsaved()
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
        if war.get("attacker") == "ai":
            msg = self._resolve_defender_victory(war, reason="Defender victory secured.")
            self._end_war(war_id, msg)
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
        if self._battle_state and target_id is not None and self._battle_state.get("enemy_realm_id") == target_id:
            self._battle_state = None
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
        self._mark_progress_unsaved()
        self.modal.show(
            "War Resolved",
            [
                log_message,
            ],
            [
                ("OK", "accept", lambda: self.modal.close()),
            ],
        )

    def _ensure_enemy_army_for_war(self, rid):
        enemy = self._get_enemy_army_for_realm(rid)
        if enemy is None:
            enemy = self._spawn_enemy_army_for_realm(rid)
        if enemy is not None:
            enemy["raising"] = True
            enemy["ai_state"] = "raising"
        return enemy
