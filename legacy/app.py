# app.py
import pygame
import random

from config import BG_COLOR, draw_panel
from time_system import GameTime
from systems import GameSystems

from mapgen import generate_province_raster
from world2 import build_world_from_raster
from mapview2 import MapView2

from event_ui import EventUIManager
from events import default_registry

from panels2 import draw_left_panel, draw_county_and_buildings, BuildClickRouter
from buildings import BUILDINGS
from domain import Construction

class GameApp:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE | pygame.SCALED, vsync=1)
        pygame.display.set_caption("CK3 Inspired Prototype (Real Province Map + Buildings)")
        self.clock = pygame.time.Clock()

        # time + systems
        self.time = GameTime(seconds_per_day_at_speed1=0.5)
        self.systems = GameSystems()

        # events
        self.event_ui = EventUIManager()
        self.registry = default_registry(seed=999)
        self.rng = random.Random(123)
        self.daily_event_chance = 0.010
        self.status_ref = {"text": "SPACE pause | 1..4 speed | E event | click map"}

        # map raster (THIS is the key)
        raster = generate_province_raster(seed=123, w=220, h=130, province_count=140, relax_steps=2)
        self.world = build_world_from_raster(seed=123, raster=raster)

        self.player_realm = self.world["player_realm"]
        self.characters = self.world["characters"]
        self.counties = self.world["counties"]
        self.raster = self.world["raster"]

        self.map_view = MapView2(self.raster, self.counties, self.player_realm)

        # build click routing
        self.build_router = BuildClickRouter()

        self.running = True

    def make_event_ctx(self) -> dict:
        return {
            "realm": self.player_realm,
            "player": self.player_realm.ruler,
            "characters": self.characters,
            "status": self.status_ref,
            "rng": self.rng,
        }

    def try_start_construction(self, county, building_id: str, slot: int):
        # only player-controlled
        if county.realm is not self.player_realm:
            self.status_ref["text"] = "You don't control this county."
            return

        h = county.holding
        if h.construction is not None:
            self.status_ref["text"] = "Already constructing."
            return
        if h.buildings[slot] is not None:
            self.status_ref["text"] = "Slot not empty."
            return

        bdef = BUILDINGS[building_id]
        if self.player_realm.gold < bdef.cost:
            self.status_ref["text"] = "Not enough gold."
            return

        # pay + start
        self.player_realm.gold -= bdef.cost
        h.construction = Construction(building_id=building_id, days_left=bdef.build_days, slot_index=slot)
        self.status_ref["text"] = f"Started: {bdef.name}"

    def handle_keydown(self, key: int):
        if key == pygame.K_ESCAPE:
            self.running = False
        elif key == pygame.K_SPACE:
            self.time.toggle_pause()
        elif key == pygame.K_1:
            self.time.set_speed_index(1)
        elif key == pygame.K_2:
            self.time.set_speed_index(2)
        elif key == pygame.K_3:
            self.time.set_speed_index(3)
        elif key == pygame.K_4:
            self.time.set_speed_index(4)
        elif key == pygame.K_e:
            ctx = self.make_event_ctx()
            ev = self.registry.roll(ctx)
            if ev:
                self.event_ui.push(ev, ctx)

    def simulate(self, real_dt: float):
        if self.event_ui.is_open():
            return
        self.time.update(real_dt)
        days = self.time.pop_day_ticks()
        for _ in range(days):
            self.systems.on_day(self.player_realm, self.characters, self.time.date, counties=self.counties)

            if self.rng.random() < self.daily_event_chance:
                ctx = self.make_event_ctx()
                ev = self.registry.roll(ctx)
                if ev:
                    self.event_ui.push(ev, ctx)

            if self.time.date.is_first_day_of_year():
                self.systems.on_year(self.player_realm, self.characters, self.time.date)

    def run(self):
        while self.running:
            real_dt = self.clock.tick(60) / 1000.0
            w, h = self.screen.get_size()
            self.screen.fill(BG_COLOR)

            pad = 18
            left = pygame.Rect(pad, pad, 380, h - pad * 2)
            right = pygame.Rect(left.right + pad, pad, w - (left.w + pad * 3), h - pad * 2)

            draw_panel(self.screen, left)
            draw_panel(self.screen, right)

            # map area top, info bottom
            map_rect = pygame.Rect(right.x + 14, right.y + 14, right.w - 28, int(right.h * 0.60))
            info_rect = pygame.Rect(right.x, map_rect.bottom + 8, right.w, right.bottom - (map_rect.bottom + 8))

            # draw left
            draw_left_panel(self.screen, left, self.time, self.status_ref["text"])

            # draw map
            self.map_view.draw(self.screen, map_rect)

            # selected county
            selected = self.counties[self.map_view.selected_pid] if self.map_view.selected_pid is not None else None

            # buildings panel buttons setup
            self.build_router.clear()
            draw_county_and_buildings(self.screen, info_rect, selected, self.player_realm, self.build_router)

            # input
            for event in pygame.event.get():
                if self.event_ui.handle_event(event):
                    continue

                if event.type == pygame.QUIT:
                    self.running = False

                elif event.type == pygame.KEYDOWN:
                    self.handle_keydown(event.key)

                elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                    # map selection
                    if not self.event_ui.is_open():
                        self.map_view.handle_event(event, map_rect)

                    # building clicks
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        hit = self.build_router.handle_click(event.pos)
                        if hit:
                            county, bid, slot = hit
                            self.try_start_construction(county, bid, slot)

            self.simulate(real_dt)
            self.event_ui.update()
            self.event_ui.draw(self.screen)
            pygame.display.flip()

        pygame.quit()
