# app.py
import pygame
import random

from config import BG_COLOR, draw_panel
from time_system import GameTime
from systems import GameSystems
from world import build_demo_world
from map_view import MapView
from panels import draw_time_panel, draw_realm_panel, draw_county_inspector

from event_ui import EventUIManager
from events import default_registry

class GameApp:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE | pygame.SCALED, vsync=1)
        pygame.display.set_caption("CK3-Inspired: Time + Events + Map")
        self.clock = pygame.time.Clock()

        # World
        self.world = build_demo_world(seed=123)
        self.player_realm = self.world["player_realm"]
        self.characters = self.world["characters"]

        # Time + Systems
        self.time = GameTime(seconds_per_day_at_speed1=0.5)
        self.systems = GameSystems()

        # Events
        self.event_ui = EventUIManager()
        self.registry = default_registry(seed=999)
        self.rng = random.Random(123)
        self.daily_event_chance = 0.012

        # UI State
        self.status_ref = {"text": "SPACE pause. 1/2/3/4 speeds. E forces event. Esc quits."}

        # Map
        self.map_view = MapView(
            self.world["counties"],
            self.world["grid_size"],
            self.player_realm,
            self.world.get("river_points", [])
        )


        self.running = True

    def make_event_ctx(self) -> dict:
        return {
            "realm": self.player_realm,
            "player": self.player_realm.ruler,
            "characters": self.characters,
            "status": self.status_ref,
            "rng": self.rng,
        }

    def handle_keydown(self, key: int):
        if key == pygame.K_ESCAPE:
            self.running = False

        elif key == pygame.K_SPACE:
            self.time.toggle_pause()
            self.status_ref["text"] = "Paused ⏸️" if self.time.paused else f"Playing ▶️ (x{self.time.speed_multiplier:g})"

        elif key == pygame.K_1:
            self.time.set_speed_index(1); self.status_ref["text"] = "Speed x1"
        elif key == pygame.K_2:
            self.time.set_speed_index(2); self.status_ref["text"] = "Speed x2"
        elif key == pygame.K_3:
            self.time.set_speed_index(3); self.status_ref["text"] = "Speed x4"
        elif key == pygame.K_4:
            self.time.set_speed_index(4); self.status_ref["text"] = "Speed x8"

        elif key == pygame.K_e:
            ctx = self.make_event_ctx()
            ev = self.registry.roll(ctx)
            if ev:
                self.event_ui.push(ev, ctx)
                self.status_ref["text"] = f"Forced event: {ev.event_id or ev.title}"
            else:
                self.status_ref["text"] = "No valid events to fire."

    def handle_events(self, map_rect: pygame.Rect):
        for event in pygame.event.get():
            # Event popup is modal: consumes input first
            if self.event_ui.handle_event(event):
                continue

            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.VIDEORESIZE:
                self.screen = pygame.display.set_mode(
                    (event.w, event.h),
                    pygame.RESIZABLE | pygame.SCALED,
                    vsync=1
                )

            elif event.type == pygame.KEYDOWN:
                self.handle_keydown(event.key)

            # Only allow map interaction if popup not open (CK3 feel)
            if not self.event_ui.is_open():
                self.map_view.handle_event(event, map_rect)

    def simulate(self, real_dt: float):
        # CK3 feel: time stops while popup open
        if self.event_ui.is_open():
            return

        self.time.update(real_dt)
        days_advanced = self.time.pop_day_ticks()

        for _ in range(days_advanced):
            self.systems.on_day(self.player_realm, self.characters, self.time.date)

            # Random events
            if self.rng.random() < self.daily_event_chance:
                ctx = self.make_event_ctx()
                ev = self.registry.roll(ctx)
                if ev:
                    self.event_ui.push(ev, ctx)

            if self.time.date.is_first_day_of_year():
                self.systems.on_year(self.player_realm, self.characters, self.time.date)

    def draw(self):
        w, h = self.screen.get_size()
        self.screen.fill(BG_COLOR)

        pad = 22
        left = pygame.Rect(pad, pad, int((w - pad * 3) * 0.36), h - pad * 2)
        right = pygame.Rect(left.right + pad, pad, w - pad * 3 - left.w, h - pad * 2)

        draw_panel(self.screen, left)
        draw_panel(self.screen, right)

        # Right split: map top, inspector bottom
        map_h = int(right.h * 0.62)
        map_rect = pygame.Rect(right.x + 14, right.y + 14, right.w - 28, map_h - 18)
        inspector_rect = pygame.Rect(right.x, right.y + map_h, right.w, right.h - map_h)

        # Panels
        draw_time_panel(self.screen, left, self.time, self.status_ref["text"])

        # Map
        self.map_view.draw(self.screen, map_rect)

        # Realm + inspector (bottom area)
        # Split inspector area into two sub-panels visually via padding (still inside right panel)
        realm_info_rect = pygame.Rect(inspector_rect.x, inspector_rect.y, inspector_rect.w, int(inspector_rect.h * 0.45))
        county_info_rect = pygame.Rect(inspector_rect.x, realm_info_rect.bottom, inspector_rect.w, inspector_rect.h - realm_info_rect.h)

        draw_realm_panel(self.screen, realm_info_rect, self.player_realm)
        draw_county_inspector(self.screen, county_info_rect, self.map_view.selection.county)

        # Popup last
        self.event_ui.draw(self.screen)
        pygame.display.flip()

        return map_rect  # returned so we can use it for input mapping

    def run(self):
        while self.running:
            real_dt = self.clock.tick(60) / 1000.0

            # draw once to know exact map rect (resizable window)
            map_rect = self.draw()

            # input
            self.handle_events(map_rect)

            # simulation
            self.simulate(real_dt)

            # open queued events
            self.event_ui.update()

        pygame.quit()
