from core.math_utils import clamp


class ArmyMixin:
    def _compute_threat(self):
        # Baseline threat comes from population size; growth adds a slow pressure on top.
        growth_ratio = (self.population - self._baseline_population) / self._baseline_population
        growth_ratio = max(0.0, growth_ratio)
        base_threat = clamp(self.population / 3000.0, 3.0, 15.0)
        growth_threat = growth_ratio * 30.0  # scaled so growth adds slowly
        threat = base_threat + growth_threat
        return int(clamp(round(threat), 0, 100))

    def _init_threat_state(self):
        baseline = self._compute_threat()
        self.baseline_threat = int(baseline)
        self._threat_level = float(baseline)
        self._threat_inactive_days = 0
        self._threat_activity_today = False
        self.threat = int(baseline)

    def _sync_baseline_threat(self):
        baseline = int(self._compute_threat())
        self.baseline_threat = baseline
        if not hasattr(self, "_threat_level"):
            self._threat_level = float(baseline)
        if self._threat_level < baseline:
            self._threat_level = float(baseline)
        self.threat = int(clamp(round(self._threat_level), 0, 100))

    def _register_threat_activity(self, amount):
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return
        if amount <= 0.0:
            return
        if not hasattr(self, "_threat_level"):
            self._init_threat_state()
        self._sync_baseline_threat()
        self._threat_activity_today = True
        self._threat_inactive_days = 0
        self._threat_level = clamp(self._threat_level + amount, 0.0, 100.0)
        self.threat = int(clamp(round(self._threat_level), 0, 100))

    def _update_threat_day(self):
        if not hasattr(self, "_threat_level"):
            self._init_threat_state()
            return
        self._sync_baseline_threat()
        if self._threat_activity_today:
            self._threat_activity_today = False
            return
        self._threat_inactive_days = max(0, int(getattr(self, "_threat_inactive_days", 0))) + 1
        if self._threat_level <= float(self.baseline_threat):
            self._threat_level = float(self.baseline_threat)
            self.threat = int(self.baseline_threat)
            return
        grace_days = max(0, int(getattr(self, "threat_decay_grace_days", 5)))
        if self._threat_inactive_days <= grace_days:
            return
        decay = max(0.0, float(getattr(self, "threat_decay_per_day", 0.35)))
        self._threat_level = max(float(self.baseline_threat), self._threat_level - decay)
        self.threat = int(clamp(round(self._threat_level), 0, 100))

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

    def _realm_marshal_value(self, rid, default=8):
        try:
            rid = int(rid)
        except (TypeError, ValueError):
            return max(0, min(40, int(default)))
        if not (0 <= rid < len(self.world.realm_rulers)):
            return max(0, min(40, int(default)))
        ruler = self.world.realm_rulers[rid]
        if not isinstance(ruler, dict):
            return max(0, min(40, int(default)))
        value = int(default)
        for key, stat_value in ruler.get("stats", []):
            if key != "Martial":
                continue
            try:
                value = int(stat_value)
            except (TypeError, ValueError):
                value = int(default)
            break
        return max(0, min(40, value))

    @staticmethod
    def _marshal_multiplier(marshal):
        value = max(0, min(40, int(marshal)))
        return 0.70 + 0.05 * value

    def _effective_strength(self, army, marshal=8, luck=1.0):
        if not army:
            return 0.0
        raised = float(army.get("raised", 0))
        morale = float(army.get("morale", 50))
        morale_mult = 0.4 + 0.6 * clamp(morale / 100.0, 0.0, 1.0)
        marshal_mult = self._marshal_multiplier(marshal)
        luck_mult = clamp(float(luck), 0.75, 1.25)
        return raised * morale_mult * marshal_mult * luck_mult

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
        enemy_rid = enemy.get("realm_id")
        enemy_marshal = self._realm_marshal_value(enemy_rid, default=8)
        player_marshal = self._realm_marshal_value(self.player_realm_id, default=8)
        enemy_strength = self._effective_strength(enemy.get("army", {}), enemy_marshal)
        player_strength = self._effective_strength(self.army, player_marshal)
        if player_strength <= 0:
            return True
        ratio = enemy_strength / max(1.0, player_strength)
        if ratio >= self.ai_engage_ratio:
            return True
        if ratio <= self.ai_avoid_ratio:
            return False

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

    def _clear_battle_state(self):
        self._battle_state = None

    def _start_battle(self, enemy, battle_pid, attacker_is_player=True):
        if enemy is None:
            return False
        if battle_pid is None or not (0 <= battle_pid < len(self.world.provinces)):
            return False

        enemy_rid = enemy.get("realm_id")
        if enemy_rid is None:
            return False

        if self._battle_state:
            if (
                self._battle_state.get("pid") == battle_pid
                and self._battle_state.get("enemy_realm_id") == enemy_rid
            ):
                return True
            return False

        if int(self.army.get("raised", 0)) <= 0 or int(enemy.get("army", {}).get("raised", 0)) <= 0:
            return False
        if self.army_prov_id != battle_pid or enemy.get("prov_id") != battle_pid:
            return False

        # Armies are locked in place while the battle resolves over several days.
        self.army_route = []
        self.army_step_from = None
        self.army_step_to = None
        self.army_step_progress = 0.0
        enemy["route"] = []
        enemy["target_pid"] = battle_pid
        enemy["ai_state"] = "engage"

        if self._siege_state and self._siege_state.get("pid") == battle_pid:
            self._clear_siege_state()

        self._battle_state = {
            "pid": battle_pid,
            "enemy_realm_id": enemy_rid,
            "attacker_is_player": bool(attacker_is_player),
            "stage": "prep",
            "days": 0,
            "prep_days": max(1, int(self.battle_prep_days)),
            "assault_days": max(1, int(self.battle_assault_days)),
        }
        prov_name = self.world.provinces[battle_pid].name
        self.push_log(f"{self.date}: Clash forming in {prov_name}.")
        self._register_threat_activity(5.0)
        return True

    def _update_battle_tick(self):
        if self._battle_state is None:
            return

        pid = self._battle_state.get("pid")
        rid = self._battle_state.get("enemy_realm_id")
        if pid is None or rid is None:
            self._clear_battle_state()
            return
        if not (0 <= pid < len(self.world.provinces)):
            self._clear_battle_state()
            return

        enemy = self._get_enemy_army_for_realm(rid)
        if enemy is None:
            self._clear_battle_state()
            return
        if self.army_prov_id != pid or enemy.get("prov_id") != pid:
            self._clear_battle_state()
            return
        if int(self.army.get("raised", 0)) <= 0 or int(enemy.get("army", {}).get("raised", 0)) <= 0:
            self._clear_battle_state()
            return

        stage = self._battle_state.get("stage", "prep")
        self._battle_state["days"] = int(self._battle_state.get("days", 0)) + 1
        days = self._battle_state["days"]

        if stage == "prep":
            if days >= self._battle_state.get("prep_days", 1):
                self._battle_state["stage"] = "assault"
                self._battle_state["days"] = 0
                prov_name = self.world.provinces[pid].name
                self.push_log(f"{self.date}: Battle begins at {prov_name}.")
            return

        if days >= self._battle_state.get("assault_days", 1):
            attacker_is_player = bool(self._battle_state.get("attacker_is_player", True))
            self._clear_battle_state()
            player_wins = self._resolve_battle(enemy, pid, attacker_is_player=attacker_is_player)
            if player_wins and self.army_prov_id == pid and self._enemy_army_at(pid) is None:
                self._start_siege(pid)

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
            if (
                self._battle_state is not None
                and self._battle_state.get("enemy_realm_id") == rid
            ):
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
                self._start_battle(enemy, player_pid, attacker_is_player=False)

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

    def _compute_battle_losses(self, player_size, enemy_size, player_wins, player_power, enemy_power):
        if player_size <= 0 or enemy_size <= 0:
            return 0, 0
        winner_size = player_size if player_wins else enemy_size
        loser_size = enemy_size if player_wins else player_size
        winner_power = float(player_power) if player_wins else float(enemy_power)
        loser_power = float(enemy_power) if player_wins else float(player_power)

        ratio = max(1.0, winner_power / max(1.0, loser_power))
        win_loss_rate = clamp(0.10 + (0.20 / ratio), 0.08, 0.30)
        lose_loss_rate = clamp(0.34 + 0.36 * (ratio / (ratio + 1.0)), 0.38, 0.78)

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

        if player_wins:
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

        player_morale = float(self.army.get("morale", 60))
        enemy_morale = float(enemy.get("army", {}).get("morale", 60))
        player_marshal = self._realm_marshal_value(self.player_realm_id, default=8)
        enemy_marshal = self._realm_marshal_value(enemy.get("realm_id"), default=8)
        player_power = self._effective_strength(self.army, player_marshal, luck=self.world.rnd.uniform(0.90, 1.10))
        enemy_power = self._effective_strength(enemy.get("army", {}), enemy_marshal, luck=self.world.rnd.uniform(0.90, 1.10))
        if abs(player_power - enemy_power) < 0.001:
            player_power += player_size * 0.01
        player_wins = player_power >= enemy_power
        player_loss, enemy_loss = self._compute_battle_losses(
            player_size,
            enemy_size,
            player_wins,
            player_power,
            enemy_power,
        )

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
            f"Marshal skill: You {player_marshal} vs Enemy {enemy_marshal}",
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
        intensity = (player_loss + enemy_loss) / max(1, player_size + enemy_size)
        self._register_threat_activity(4.0 + intensity * 8.0)
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
        if self._battle_state is not None:
            return
        if not self.army_route or self.army_prov_id is None:
            return
        if self.army.get("raised", 0) <= 0:
            return
        if self.army_step_to is None:
            self.army_step_from = self.army_prov_id
            self.army_step_to = self.army_route[0]
            self.army_step_progress = 0.0
        if self.army_step_to is None or self.army_step_from is None:
            return
        if not (0 <= self.army_step_from < len(self.world.provinces)):
            self.army_route = []
            self.army_step_from = None
            self.army_step_to = None
            return
        if not (0 <= self.army_step_to < len(self.world.provinces)):
            self.army_route = []
            self.army_step_from = None
            self.army_step_to = None
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
                self._start_battle(enemy, self.army_prov_id, attacker_is_player=True)
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
        before = int(self.army["raised"])
        self.army["raised"] = min(max_army, before + per_day)
        gained = max(0, int(self.army["raised"]) - before)
        if gained > 0:
            raise_ratio = gained / max(1.0, float(max_army))
            self._register_threat_activity(0.15 + (raise_ratio * 4.0))

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
            self._refresh_fog_only()
