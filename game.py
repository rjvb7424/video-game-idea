import pygame

import event_content
from core.camera import Camera
from core.date import GameDate
from core.math_utils import clamp
from core.surfaces import tile_fill
from events import EventRegistry, EventSystem, register_all
from rendering.map_view import MapRenderer
from systems.buildings import BUILDINGS
from systems.traits import _stats_list_to_dict, apply_trait_effects, compute_piety_rate, normalize_traits
from ui.layout import Layout
from ui.manager import UIManager
from ui.modal import Modal
from ui.theme import BG_COLOR, FOOTER_FONT
from ui.utils import clip_draw
from world.map import MapWorld


class GameApp:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("CK1-Inspired Grand Strategy UI (Pygame)")
        self.screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()

        self.ui = UIManager(seed=11)
        self.layout = Layout(*self.screen.get_size())

        self.world = MapWorld(seed=7, world_size=(3200, 2200), cell_scale=4)
        self.camera = Camera(viewport_size=(100, 100), world_size=(self.world.world_w, self.world.world_h))
        self.map_renderer = MapRenderer(self.world, self.camera)

        self.modal = Modal()

        self.date = GameDate(1067, 1, 21)
        self.speed_level = 0  # 0 paused, 1..3 speeds
        self.speed_days_per_sec = {0: 0, 1: 1, 2: 3, 3: 7}
        self._time_accum = 0.0

        self.selected_province = None

        # --- EVENTS: minimal integration ---
        self._event_flags = {}
        self._event_pending = []
        self._event_resume_speed = None

        self.event_registry = EventRegistry(seed=123)
        register_all(self.event_registry, event_content)
        self.events = EventSystem(self, self.event_registry, daily_chance=0.05, seed=999)

        self.resources = {
            "gold": 200,
            "gold_rate": +1,
            "piety": 1000,
        }

        # Player character = ruler of player realm
        self.player_realm_id = self.world.player_realm_id
        self.character = dict(self.world.realm_rulers[self.player_realm_id])

        if "base_stats" not in self.character:
            self.character["base_stats"] = _stats_list_to_dict(self.character.get("stats", []))
        apply_trait_effects(self.character)
        self.character["traits"] = normalize_traits(self.character.get("traits", []))
        self.resources["piety_rate"] = compute_piety_rate(self.character)[0]

        self.army = {"raised": 928, "max": 1712, "morale": 77}
        self.population = self.world.total_population_for_realm(self.player_realm_id)
        self.food = (0.0, 0.0)  # (produced, consumed)
        farm_def = BUILDINGS.get("farm")
        self.food_production_per_farm = farm_def.food_bonus if farm_def else 0.0
        self.food_consumption_per_pop = 0.4  # monthly consumption per person
        self._baseline_population = max(1, self.population)
        self.food = self._compute_food_values()
        self.threat = self._compute_threat()

        self.log = [
            "January 8, 1067: Rumors of usurpation spread in Carinthia.",
            "January 11, 1067: A distant court recognizes new claims.",
            "January 18, 1067: A master of arms returns from pilgrimage.",
        ]

        # map interaction
        self._mouse_down_in_map = False
        self._mouse_down_pos = (0, 0)
        self._mouse_drag_threshold = 5
        self._drag_started = False
        self._prev_mouse_down = False

        self.running = True

    def _try_open_tower_event(self, screen_pos):
        tower_pid = getattr(self.world, "tower_pid", -1)
        if not (0 <= tower_pid < len(self.world.provinces)):
            return False

        tprov = self.world.provinces[tower_pid]
        sp = self.camera.world_to_screen(tprov.center, self.layout.map, use_target=False)
        x, y = int(sp.x), int(sp.y)

        label = "Tower of Heaven"
        text = FOOTER_FONT.render(label, True, (0, 0, 0))
        text_rect = text.get_rect(midtop=(x, y + 8))
        icon_rect = pygame.Rect(x - 8, y - 28, 16, 30)
        hit_rect = icon_rect.union(text_rect.inflate(6, 4))

        if hit_rect.collidepoint(screen_pos):
            opened = self.events.open_event_by_id("tower_of_heaven_approach")
            if opened:
                self.selected_province = tprov
            return opened
        return False

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
                "This is a functional UI modal (no assets) to demonstrate real flow.",
                "Exit cleanly to desktop, or close to return to the map.",
            ],
            [
                ("Close", "secondary", lambda: self.modal.close()),
                ("Exit", "deny", lambda: self._exit_game()),
            ],
        )

    def _exit_game(self):
        self.running = False

    def _compute_threat(self):
        # Threat rises only when population grows above the starting baseline.
        growth_threat = int(((self.population - self._baseline_population) / self._baseline_population) * 100)
        # Always keep a small base threat tied to overall population.
        base_threat = clamp(int(self.population / 3000), 3, 15)
        threat = max(base_threat, growth_threat)
        if self.population > self._baseline_population:
            threat = max(1, threat)
        return max(0, min(100, threat))

    def _compute_food_values(self):
        farm_count = self.world.count_buildings(self.player_realm_id, "farm")
        production = self.food_production_per_farm * farm_count
        consumption = self.population * self.food_consumption_per_pop
        return production, consumption

    def _build_selected_building(self, building_id):
        prov = self.selected_province
        if prov is None:
            self.push_log("No province selected.")
            return
        if prov.realm_id != self.player_realm_id:
            self.push_log("Cannot build outside your realm.")
            return
        slot = prov.add_building(building_id)
        if slot < 0:
            self.push_log(f"{prov.name} has no empty building slots.")
            return
        bdef = BUILDINGS.get(building_id)
        bname = bdef.name if bdef else building_id
        self.push_log(f"{self.date}: Built {bname} in {prov.name} (slot {slot + 1}).")
        self.food = self._compute_food_values()

    def _handle_action(self, action):
        if action == "toggle_pause":
            self.toggle_pause()
        elif action == "speed_1":
            self.set_speed(1)
        elif action == "speed_2":
            self.set_speed(2)
        elif action == "speed_3":
            self.set_speed(3)
        elif action == "open_menu":
            self.open_menu()
        elif action == "build_farm":
            self._build_selected_building("farm")
        elif action in (
            "ledger",
            "realm",
            "military",
            "decisions",
            "court",
            "council",
            "view_realm",
            "set_rally",
            "raise_army",
            "rally",
            "disband",
        ):
            self.modal.show(
                "Not Implemented",
                [
                    f"'{action}' is a placeholder action.",
                    "The UI is fully functional; game logic can be connected here.",
                ],
                [
                    ("OK", "accept", lambda: self.modal.close()),
                ],
            )

    def _update_time(self, dt):
        days_per_sec = self.speed_days_per_sec.get(self.speed_level, 0)
        if days_per_sec <= 0:
            return
        self._time_accum += dt * days_per_sec
        whole = int(self._time_accum)
        if whole > 0:
            for _ in range(whole):
                self.date.advance_days(1)

                # daily tick for events (random + chain)
                self.events.on_day()

                if self.date.day == 1:
                    self._apply_monthly_resource_rates()

            self._time_accum -= whole

    def _apply_monthly_resource_rates(self):
        for res in ("gold", "piety"):
            rate = self.resources.get(f"{res}_rate", 0)
            if rate == 0:
                continue
            self.resources[res] += rate
        # Food production comes from farms; consumption scales with population.
        production, consumption = self._compute_food_values()
        self.food = (production, consumption)

        # Population growth/decline based on food surplus/deficit.
        if consumption <= 0:
            food_balance = 1.0
        else:
            food_balance = (production - consumption) / consumption
        food_balance = max(-1.0, min(1.0, food_balance))

        if food_balance >= 0:
            pop_rate = 0.002 * food_balance  # up to +0.2% per month
        else:
            pop_rate = 0.006 * food_balance  # down to -0.6% per month

        if abs(pop_rate) > 0.00001:
            self.world.adjust_population_for_realm(self.player_realm_id, pop_rate)

        self.population = self.world.total_population_for_realm(self.player_realm_id)
        self.threat = self._compute_threat()

    def _map_controls(self, dt):
        keys = pygame.key.get_pressed()
        if self.modal.open:
            return

        # Keyboard panning (weighty due to camera smoothing)
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

        # +/- zoom
        if keys[pygame.K_EQUALS] or keys[pygame.K_PLUS]:
            mx, my = pygame.mouse.get_pos()
            if self.layout.map.collidepoint((mx, my)):
                self.camera.zoom_at(1.03, (mx, my), self.layout.map)
        if keys[pygame.K_MINUS]:
            mx, my = pygame.mouse.get_pos()
            if self.layout.map.collidepoint((mx, my)):
                self.camera.zoom_at(0.97, (mx, my), self.layout.map)

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                elif event.type == pygame.VIDEORESIZE:
                    w = max(1024, event.w)
                    h = max(640, event.h)
                    self.screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
                    self.layout.update(w, h)
                    self.camera.set_viewport(self.layout.map.size)

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.modal.open:
                            self.modal.close()
                        else:
                            self.open_menu()
                    elif event.key == pygame.K_SPACE:
                        if not self.modal.open:
                            self.toggle_pause()

                # Mouse wheel zoom (pygame 2)
                elif event.type == pygame.MOUSEWHEEL and not self.modal.open:
                    mx, my = pygame.mouse.get_pos()
                    if self.layout.map.collidepoint((mx, my)):
                        factor = 1.12 if event.y > 0 else 0.89
                        self.camera.zoom_at(factor, (mx, my), self.layout.map)

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1 and not self.modal.open:
                        if self.layout.map.collidepoint(event.pos):
                            self._mouse_down_in_map = True
                            self._mouse_down_pos = event.pos
                            self._drag_started = False

                    # fallback wheel (old style)
                    if not self.modal.open and self.layout.map.collidepoint(event.pos):
                        if event.button == 4:
                            self.camera.zoom_at(1.12, event.pos, self.layout.map)
                        elif event.button == 5:
                            self.camera.zoom_at(0.89, event.pos, self.layout.map)

                elif event.type == pygame.MOUSEMOTION:
                    if not self.modal.open and self._mouse_down_in_map:
                        dx = abs(event.pos[0] - self._mouse_down_pos[0])
                        dy = abs(event.pos[1] - self._mouse_down_pos[1])
                        if not self._drag_started and (dx + dy) > self._mouse_drag_threshold:
                            self._drag_started = True
                            self.camera.begin_drag(self._mouse_down_pos)

                        if self._drag_started:
                            self.camera.drag_to(event.pos)

                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        if self._mouse_down_in_map:
                            if self._drag_started:
                                self.camera.end_drag()
                            else:
                                if self.layout.map.collidepoint(event.pos):
                                    if not self._try_open_tower_event(event.pos):
                                        wp = self.camera.screen_to_world(event.pos, self.layout.map, use_target=False)
                                        prov = self.world.province_at_world(wp)
                                        if prov is not None:
                                            self.selected_province = prov
                                            self.push_log(f"{self.date}: Selected {prov.name}.")
                            self._mouse_down_in_map = False
                            self._drag_started = False

            # Continuous controls
            self._map_controls(dt)

            # Time + camera easing
            self._update_time(dt)
            self.camera.update(dt)

            # Draw
            self.screen.fill(BG_COLOR)

            # Decorative background panels behind everything
            bg = pygame.Surface(self.screen.get_size())
            bg.fill(BG_COLOR)
            tile = self.ui.bottom_tile
            tile_fill(bg, bg.get_rect(), tile)
            bg.set_alpha(70)
            self.screen.blit(bg, (0, 0))

            # Map
            self.map_renderer.draw(self.screen, self.layout.map)

            # UI panels
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
                "player_realm_id": self.player_realm_id,
                "population": self.population,
                "food": self.food,
                "threat": self.threat,
            }

            clickables = []

            clip_draw(self.screen, self.layout.top, lambda: clickables.extend(self.ui.draw_top_bar(self.screen, self.layout.top, state)))
            clip_draw(self.screen, self.layout.left, lambda: clickables.extend(self.ui.draw_left_panel(self.screen, self.layout.left, state)))
            clip_draw(self.screen, self.layout.right, lambda: clickables.extend(self.ui.draw_right_panel(self.screen, self.layout.right, state)))
            clip_draw(self.screen, self.layout.bottom, lambda: clickables.extend(self.ui.draw_bottom_bar(self.screen, self.layout.bottom, state)))

            # Modal on top
            modal_clickables = self.modal.draw(self.screen, self.ui.panel_tile)

            # Edge-triggered click dispatch
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


if __name__ == "__main__":
    GameApp().run()
