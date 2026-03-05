import pygame

from ui.theme import BG_COLOR
from ui.utils import clip_draw


class GameLoopMixin:
    def _set_rally_point(self, pid, announce=True):
        if pid is None or not (0 <= pid < len(self.world.provinces)):
            return False
        prov = self.world.provinces[pid]
        if prov.realm_id != self.player_realm_id:
            return False
        self.world.player_capital_pid = pid
        if self.army.get("raised", 0) <= 0 and not self.army_raising:
            self._set_army_prov(pid)
        if announce:
            self.push_log(f"{self.date}: Rally point moved to {prov.name}.")
        return True

    def _rally_army_to_capital(self):
        rally_pid = self._get_player_capital_pid()
        if rally_pid is None:
            self.push_log("No rally point available.")
            return
        if self.army.get("raised", 0) <= 0:
            self._set_army_prov(rally_pid)
            self.push_log("Army is not raised; rally point updated for future mustering.")
            self._open_military_overview()
            return
        self._ensure_army_position()
        start_pid = self.army_prov_id
        if start_pid is None or start_pid == rally_pid:
            self.push_log("Army already at rally point.")
            self._open_military_overview()
            return
        route = self._find_province_path(start_pid, rally_pid)
        if not route:
            self.push_log("No route to rally point.")
            self._open_military_overview()
            return
        self.army_route = route
        self.army_step_from = start_pid
        self.army_step_to = route[0]
        self.army_step_progress = 0.0
        self.army_selected = True
        self.push_log(f"{self.date}: Army rally ordered.")
        self._open_military_overview()

    def _open_campaign_briefing(self):
        self.modal.show(
            "Realm Briefing",
            [
                "Sandbox mode enabled.",
                "Expand, fight wars, and manage your realm freely.",
            ],
            [
                ("Begin", "accept", lambda: self.modal.close()),
            ],
        )

    def _handle_action(self, action):
        if action == "menu_start":
            self.storyteller = None
            self._storyteller_start_day = None
            self.realm_select_page = 0
            self.realm_candidate_id = None
            self.mode = "storyteller"
            self.modal.close()
            return
        if action == "menu_load":
            self._open_load_game_modal()
            return
        if action == "menu_settings":
            self._open_settings_modal()
            return
        if action == "storyteller_back":
            self.realm_candidate_id = None
            self.selected_province = None
            self.right_panel_open = False
            self.mode = "menu"
            return
        if action.startswith("storyteller:"):
            sid = action.split(":", 1)[1]
            st = next((s for s in self.storytellers if s["id"] == sid), None)
            if st:
                self._apply_storyteller(st)
                self.realm_select_page = 0
                self.realm_candidate_id = None
                self.selected_province = None
                self.right_panel_open = False
                self._set_full_visibility()
                self.mode = "realm_select"
            return
        if action == "realm_back":
            self.realm_candidate_id = None
            self.selected_province = None
            self.right_panel_open = False
            self.mode = "storyteller"
            return
        if action == "realm_confirm":
            if self.realm_candidate_id is None:
                return
            self._start_game_for_realm(self.realm_candidate_id)
            self.mode = "game"
            self.camera.set_viewport(self._get_map_rect().size)
            self.left_panel_open = False
            self._left_panel_anim = 0.0
            self.right_panel_open = True
            self._right_panel_anim = 1.0
            return
        if action == "right_panel_close":
            self.right_panel_open = False
            return
        if action == "left_panel_close":
            self.left_panel_open = False
            return
        if action == "left_panel_open":
            self.left_panel_open = True
            return
        if action == "npc_promote_relations":
            self._action_promote_relations()
            return
        if action == "npc_fabricate_claim":
            self._action_fabricate_claim()
            return
        if action == "npc_arrange_marriage":
            self._action_arrange_marriage()
            return
        if action == "npc_plot_murder":
            self._action_plot_murder()
            return
        if action == "npc_declare_war":
            target_rid = None
            if self.selected_province is not None and self.selected_province.realm_id != self.player_realm_id:
                target_rid = self.selected_province.realm_id
            if target_rid is None:
                self.modal.show(
                    "No Target Selected",
                    [
                        "Select a foreign realm (click a province) before declaring war.",
                    ],
                    [
                        ("OK", "accept", lambda: self.modal.close()),
                    ],
                )
            else:
                self._open_war_type_modal(target_rid)
            return
        if action == "open_war_overview":
            self._open_war_overview()
            return
        if action.startswith("war_details:"):
            try:
                war_id = int(action.split(":", 1)[1])
            except ValueError:
                self.push_log("Invalid war action.")
                return
            self._open_war_details(war_id)
            return
        if action == "raise_army":
            if self.army_raising:
                self.army_raising = False
                if self.army.get("raised", 0) <= 0:
                    self.army_selected = False
                    self.army_route = []
                    self.army_step_from = None
                    self.army_step_to = None
                    self.army_step_progress = 0.0
                    self._update_fog_from_army()
                self.push_log("You halt the muster.")
            else:
                if self.army.get("max", 0) <= 0:
                    self.push_log("No population available to raise an army.")
                elif self.army.get("raised", 0) >= self.army.get("max", 0):
                    self.push_log("Your army is already fully raised.")
                else:
                    self._ensure_army_position()
                    self.army_raising = True
                    self._update_fog_from_army()
                    self.push_log("Your levies begin to muster.")
            return
        if action == "disband":
            action = "disband_army"
        if action == "disband_army":
            if self.army.get("raised", 0) <= 0:
                return
            if self.army_prov_id is None or not (0 <= self.army_prov_id < len(self.world.provinces)):
                return
            prov = self.world.provinces[self.army_prov_id]
            if prov.realm_id != self.player_realm_id:
                self.modal.show(
                    "Cannot Disband",
                    [
                        "You can only disband your army within your own realm.",
                    ],
                    [
                        ("OK", "accept", lambda: self.modal.close()),
                    ],
                )
                return
            self.army["raised"] = 0
            self.army_raising = False
            self.army_selected = False
            self.army_route = []
            self.army_step_from = None
            self.army_step_to = None
            self.army_step_progress = 0.0
            self.army_pos = None
            self.army_prov_id = None
            self._update_fog_from_army()
            self.push_log("You disband the army.")
            return
        if action == "toggle_pause":
            self.toggle_pause()
            return
        elif action == "speed_1":
            self.set_speed(1)
            return
        elif action == "speed_2":
            self.set_speed(2)
            return
        elif action == "speed_3":
            self.set_speed(3)
            return
        elif action == "open_menu":
            self.open_menu()
            return
        elif action == "save_game":
            self._save_game_to_file(self.latest_save_path, autosave=False)
            return
        elif action == "load_game":
            self._open_load_game_modal()
            return
        elif action in ("realm", "view_realm"):
            self._open_realm_overview()
            return
        elif action == "ledger":
            self._open_ledger_overview()
            return
        elif action == "military":
            self._open_military_overview()
            return
        elif action == "set_rally":
            if self.selected_province is None or self.selected_province.realm_id != self.player_realm_id:
                self.modal.show(
                    "No Valid Rally Point",
                    [
                        "Select one of your own provinces to set a rally point.",
                    ],
                    [
                        ("OK", "accept", lambda: self.modal.close()),
                    ],
                )
            else:
                self._set_rally_point(self.selected_province.id, announce=True)
                self._open_military_overview()
            return
        elif action == "rally":
            self._rally_army_to_capital()
            return
        elif action == "decisions":
            self._open_decisions_modal()
            return
        elif action == "council":
            self._open_scheme_overview()
            return
        elif action == "court":
            self._open_scheme_overview()
            return
        elif action == "build_farm":
            self._build_selected_building("farm")
            return
        elif action.startswith("building_slot:"):
            parts = action.split(":")
            if len(parts) < 3:
                self.push_log("Invalid building action.")
                return
            try:
                slot_idx = int(parts[1])
            except ValueError:
                self.push_log("Invalid building slot action.")
                return
            verb = parts[2]
            if verb == "toggle":
                if self._building_menu_slot == slot_idx:
                    self._building_menu_slot = None
                else:
                    self._building_menu_slot = slot_idx
            elif verb == "build" and len(parts) >= 4:
                self._build_selected_building(parts[3], slot_idx=slot_idx)
            elif verb == "upgrade":
                self._upgrade_selected_building(slot_idx)
            elif verb == "demolish":
                self._demolish_selected_building(slot_idx)
            else:
                self.push_log(f"Unknown building action: {verb}")
            return

        self.push_log(f"Unknown UI action: {action}")

    def _update_time(self, dt):
        days_per_sec = self.speed_days_per_sec.get(self.speed_level, 0)
        if days_per_sec <= 0:
            return
        self._time_accum += dt * days_per_sec
        whole = int(self._time_accum)
        if whole > 0:
            for _ in range(whole):
                self.date.advance_days(1)

                self._update_storyteller_event_chance()
                self.events.on_day()
                self._update_war_tick()
                self._update_army_raising()
                self._update_army_morale_tick()
                self._update_siege_tick()
                self._update_army_movement()
                self._update_enemy_ai_tick()
                self._tick_politics_day()

                if self.date.day == 1:
                    self._apply_monthly_resource_rates()
                    if self._autosave_interval_months > 0 and ((self.date.month - 1) % self._autosave_interval_months == 0):
                        self._save_game_to_file(self.autosave_path, autosave=True)
                    if self.date.month == 1:
                        self._annual_dynasty_tick()

            self._time_accum -= whole

    def _map_controls(self, dt):
        keys = pygame.key.get_pressed()
        if self.modal.open:
            return
        map_rect = self._get_map_rect()
        mx, my = pygame.mouse.get_pos()
        over_ui = self._point_in_ui((mx, my))

        pan_speed = 720.0 / max(self.camera.target_zoom, 0.001)
        dx = dy = 0.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx -= pan_speed * dt
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx += pan_speed * dt
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy -= pan_speed * dt
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy += pan_speed * dt
        if dx != 0.0 or dy != 0.0:
            self.camera.pan(dx, dy)

        if keys[pygame.K_EQUALS] or keys[pygame.K_PLUS]:
            if map_rect.collidepoint((mx, my)) and not over_ui:
                self.camera.zoom_at(1.03, (mx, my), map_rect)
        if keys[pygame.K_MINUS]:
            if map_rect.collidepoint((mx, my)) and not over_ui:
                self.camera.zoom_at(0.97, (mx, my), map_rect)

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0

            if self.mode == "game":
                self._bottom_bar_rect = self.ui.compute_bottom_bar_rect(
                    self.layout.bottom,
                    {
                        "date": self.date,
                        "army": self.army,
                        "army_raising": self.army_raising,
                        "speed_level": self.speed_level,
                        "wars": self.wars,
                    },
                )
            else:
                self._bottom_bar_rect = None

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                elif event.type == pygame.VIDEORESIZE:
                    self._apply_window_size((event.w, event.h), remember=True)

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.modal.open:
                            self.modal.close()
                        elif self.mode == "game":
                            self.open_menu()
                        elif self.mode == "storyteller":
                            self.mode = "menu"
                        elif self.mode == "realm_select":
                            self.mode = "storyteller"
                    elif event.key == pygame.K_SPACE:
                        if self.mode == "game":
                            self.toggle_pause()

                elif event.type == pygame.MOUSEWHEEL and not self.modal.open and self.mode in ("game", "realm_select"):
                    mx, my = pygame.mouse.get_pos()
                    map_rect = self._get_map_rect()
                    if map_rect.collidepoint((mx, my)) and not self._point_in_ui((mx, my)):
                        factor = 1.12 if event.y > 0 else 0.89
                        self.camera.zoom_at(factor, (mx, my), map_rect)

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1 and not self.modal.open and self.mode in ("game", "realm_select"):
                        map_rect = self._get_map_rect()
                        if map_rect.collidepoint(event.pos) and not self._point_in_ui(event.pos):
                            self._mouse_down_in_map = True
                            self._mouse_down_pos = event.pos
                            self._drag_started = False

                    if not self.modal.open and self.mode in ("game", "realm_select"):
                        map_rect = self._get_map_rect()
                        if map_rect.collidepoint(event.pos) and not self._point_in_ui(event.pos):
                            if event.button == 4:
                                self.camera.zoom_at(1.12, event.pos, map_rect)
                            elif event.button == 5:
                                self.camera.zoom_at(0.89, event.pos, map_rect)

                elif event.type == pygame.MOUSEMOTION:
                    if not self.modal.open and self.mode in ("game", "realm_select") and self._mouse_down_in_map:
                        dx = abs(event.pos[0] - self._mouse_down_pos[0])
                        dy = abs(event.pos[1] - self._mouse_down_pos[1])
                        if not self._drag_started and (dx + dy) > self._mouse_drag_threshold:
                            self._drag_started = True
                            self.camera.begin_drag(self._mouse_down_pos)

                        if self._drag_started:
                            self.camera.drag_to(event.pos)

                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        if self.mode in ("game", "realm_select") and self._mouse_down_in_map:
                            if self._drag_started:
                                self.camera.end_drag()
                            else:
                                map_rect = self._get_map_rect()
                                if map_rect.collidepoint(event.pos) and not self._point_in_ui(event.pos):
                                    if self.mode == "game":
                                        if self._handle_army_click(event.pos, map_rect):
                                            self._mouse_down_in_map = False
                                            self._drag_started = False
                                            continue
                                        if not self._try_open_tower_event(event.pos):
                                            wp = self.camera.screen_to_world(event.pos, map_rect, use_target=False)
                                            prov = self.world.province_at_world(wp)
                                            if prov is not None:
                                                if self._handle_war_goal_click(prov):
                                                    self._mouse_down_in_map = False
                                                    self._drag_started = False
                                                    continue
                                                self.army_selected = False
                                                self.selected_province = prov
                                                self.right_panel_open = True
                                                if prov.realm_id != self.player_realm_id:
                                                    self.left_panel_open = True
                                                self._building_menu_slot = None
                                                self.push_log(f"{self.date}: Selected {prov.name}.")
                                    elif self.mode == "realm_select":
                                        wp = self.camera.screen_to_world(event.pos, map_rect, use_target=False)
                                        prov = self.world.province_at_world(wp)
                                        if prov is not None:
                                            self.selected_province = prov
                                            self.realm_candidate_id = prov.realm_id
                            self._mouse_down_in_map = False
                            self._drag_started = False
                    elif event.button == 3:
                        if self.mode == "game" and not self.modal.open:
                            map_rect = self._get_map_rect()
                            if map_rect.collidepoint(event.pos) and not self._point_in_ui(event.pos):
                                self._handle_army_move(event.pos, map_rect)

            if self.mode in ("game", "realm_select"):
                self._map_controls(dt)

            if self.mode == "game":
                self._update_time(dt)
            if self.mode in ("game", "realm_select"):
                self.camera.update(dt)
            self._update_right_panel_anim(dt)
            self._update_left_panel_anim(dt)
            if self.mode == "game":
                self._update_army_flash(dt)

            clickables = []
            if self.mode == "menu":
                clickables = self._draw_main_menu(self.screen)
                modal_clickables = self.modal.draw(self.screen, self.ui.panel_tile)
            elif self.mode == "storyteller":
                clickables = self._draw_storyteller_menu(self.screen)
                modal_clickables = self.modal.draw(self.screen, self.ui.panel_tile)
            elif self.mode == "realm_select":
                clickables = self._draw_realm_menu(self.screen)
                modal_clickables = self.modal.draw(self.screen, self.ui.panel_tile)
            else:
                self.screen.fill(BG_COLOR)

                bg = self._get_game_bg(self.screen.get_size())
                self.screen.blit(bg, (0, 0))

                map_rect = self._get_map_rect()
                war_overlay, war_overlay_key = self._get_war_border_overlay()
                siege_overlay, siege_overlay_key = self._get_siege_overlay()
                overlays = []
                overlay_key = []
                if siege_overlay is not None:
                    overlays.append(siege_overlay)
                    overlay_key.append(("siege", siege_overlay_key))
                if war_overlay is not None:
                    overlays.append(war_overlay)
                    overlay_key.append(("war", war_overlay_key))
                if not overlays:
                    overlays = None
                    overlay_key = None
                else:
                    overlay_key = tuple(overlay_key)
                self.map_renderer.draw(self.screen, map_rect, overlays, overlay_key)
                self._draw_selected_province_highlight(self.screen, map_rect)
                self._draw_army_muster_marker(self.screen, map_rect)
                self._draw_enemy_armies(self.screen, map_rect)
                self._draw_army_route_arrow(self.screen, map_rect)
                self._draw_siege_status(self.screen, map_rect)

                state = {
                    "date": self.date,
                    "resources": self.resources,
                    "speed_level": self.speed_level,
                    "character": self.character,
                    "army": self.army,
                    "selected_province": self.selected_province,
                    "log": self.log,
                    "realm_names": self.world.realm_names,
                    "realm_rulers": self.world.realm_rulers,
                    "realm_colors": self.world.realm_colors,
                    "player_realm_id": self.player_realm_id,
                    "population": self.population,
                    "army_raising": self.army_raising,
                    "food": self.food,
                    "threat": self.threat,
                    "building_menu_slot": self._building_menu_slot,
                    "wars": self.wars,
                    "stress": int(round(self.stress)),
                    "dread": int(round(self.dread)),
                    "lifestyle_focus": self.lifestyle_focus,
                    "lifestyle_perks": dict(self.lifestyle_perks),
                    "active_schemes": list(self.active_schemes),
                    "selected_realm_manpower": (
                        self._realm_total_manpower(self.selected_province.realm_id)
                        if self.selected_province is not None
                        else None
                    ),
                }

                clip_draw(
                    self.screen,
                    self.layout.top,
                    lambda: clickables.extend(self.ui.draw_top_bar(self.screen, self.layout.top, state)),
                )
                war_btns, war_rects = self.ui.draw_war_floating(self.screen, self.layout.top, state)
                clickables.extend(war_btns)
                self._war_float_rects = war_rects
                left_character = self.character
                left_realm_id = self.player_realm_id
                if self.selected_province is not None and self.selected_province.realm_id != self.player_realm_id:
                    rid = self.selected_province.realm_id
                    if 0 <= rid < len(self.world.realm_rulers):
                        left_character = self.world.realm_rulers[rid]
                        left_realm_id = rid
                left_state = dict(state)
                left_state["character"] = left_character
                left_state["character_realm_id"] = left_realm_id
                npc_target = self._get_npc_target()
                left_state["npc_target"] = npc_target
                left_state["npc_actions_enabled"] = True
                left_state["diplomacy"] = self._diplomacy_snapshot(npc_target.get("id")) if npc_target else None
                left_state["character_realm_manpower"] = self._realm_total_manpower(left_realm_id)

                clickables.extend(self._draw_left_panel_animated(self.screen, left_state))
                clickables.extend(self._draw_right_panel_animated(self.screen, state))
                clickables.extend(self.ui.draw_bottom_bar(self.screen, self.layout.bottom, state))

                modal_clickables = self.modal.draw(self.screen, self.ui.panel_tile)

            now_down = pygame.mouse.get_pressed(num_buttons=3)[0]
            if self._prev_mouse_down and (not now_down):
                mx, my = pygame.mouse.get_pos()
                if self.modal.open:
                    for r, cb in modal_clickables:
                        if r.collidepoint((mx, my)):
                            cb()
                            break
                else:
                    for r, action in clickables:
                        if r.collidepoint((mx, my)):
                            self._handle_action(action)
                            break
            self._prev_mouse_down = now_down

            pygame.display.flip()

        pygame.quit()
