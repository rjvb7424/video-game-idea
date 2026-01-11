# main.py
import pygame
import random

from event_ui import EventUIManager
from events import default_registry  # <-- IMPORTANT: now using events.py registry


# ----------------------------
# Minimal UI helpers (no deps)
# ----------------------------
BG_COLOR = (18, 18, 22)
PANEL_COLOR = (28, 28, 34)
TEXT_COLOR = (230, 230, 235)
MUTED_COLOR = (170, 170, 180)
ACCENT = (90, 160, 255)

def draw_text(surface, text, x, y, font, color=TEXT_COLOR):
    img = font.render(text, True, color)
    surface.blit(img, (x, y))
    return y + img.get_height() + 6

def draw_panel(surface, rect):
    pygame.draw.rect(surface, PANEL_COLOR, rect, border_radius=10)


# ----------------------------
# Game Time (pause/speeds/date)
# ----------------------------
DAYS_IN_MONTH = 30
MONTHS_IN_YEAR = 12
DAYS_IN_YEAR = DAYS_IN_MONTH * MONTHS_IN_YEAR

class GameDate:
    def __init__(self, year=1066, month=1, day=1):
        self.year = year
        self.month = month
        self.day = day

    def add_days(self, n: int):
        total = (self.year * DAYS_IN_YEAR) + ((self.month - 1) * DAYS_IN_MONTH) + (self.day - 1)
        total += n
        self.year = total // DAYS_IN_YEAR
        rem = total % DAYS_IN_YEAR
        self.month = (rem // DAYS_IN_MONTH) + 1
        self.day = (rem % DAYS_IN_MONTH) + 1

    def is_first_day_of_year(self) -> bool:
        return self.month == 1 and self.day == 1

    def __str__(self):
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"

class GameTime:
    SPEEDS = [0.0, 1.0, 2.0, 4.0, 8.0]

    def __init__(self, seconds_per_day_at_speed1=0.5):
        self.seconds_per_day_at_speed1 = seconds_per_day_at_speed1
        self.speed_index = 1
        self.date = GameDate()
        self._accum_days = 0.0
        self._popped_days = 0

    @property
    def paused(self):
        return self.speed_index == 0

    @property
    def speed_multiplier(self):
        return self.SPEEDS[self.speed_index]

    def toggle_pause(self):
        self.speed_index = 1 if self.speed_index == 0 else 0

    def set_speed_index(self, idx: int):
        self.speed_index = max(0, min(idx, len(self.SPEEDS) - 1))

    def update(self, real_dt_seconds: float):
        self._popped_days = 0
        mult = self.speed_multiplier
        if mult <= 0.0:
            return

        days_per_second = mult / self.seconds_per_day_at_speed1
        self._accum_days += real_dt_seconds * days_per_second

        whole_days = int(self._accum_days)
        if whole_days > 0:
            self._accum_days -= whole_days
            self._popped_days = whole_days
            self.date.add_days(whole_days)

    def pop_day_ticks(self) -> int:
        return self._popped_days


# ----------------------------
# Tiny domain model (example)
# ----------------------------
class Character:
    def __init__(self, fname, lname, age):
        self.fname = fname
        self.lname = lname
        self.age = age
        self.gold = 0.0
        self.xp = 0
        self.inventory = []

        # OPTIONAL: these make multi-character events feel better
        # (events.py will also auto-create these if missing, but it's nice to see them)
        self.loyalty = 50              # 0..100
        self.opinion_of_player = 0     # -100..100
        self.intrigue = 10             # 0..30-ish
        self.role = "Courtier"

    @property
    def name(self):
        return f"{self.fname} {self.lname}"

class Realm:
    def __init__(self, name, ruler: Character):
        self.name = name
        self.ruler = ruler
        self.gold = 120.0
        self.prestige = 80
        self.piety = 35
        self.development = 12

    def daily_income(self) -> float:
        return 0.05 * self.development


# ----------------------------
# Systems / Ticks
# ----------------------------
class GameSystems:
    def on_day(self, realm: Realm, characters: list[Character], date: GameDate):
        realm.gold += realm.daily_income()
        for ch in characters:
            ch.xp += 1
            ch.gold += 0.02

    def on_year(self, realm: Realm, characters: list[Character], date: GameDate):
        for ch in characters:
            ch.age += 1


# ----------------------------
# Main
# ----------------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE | pygame.SCALED, vsync=1)
    pygame.display.set_caption("CK3-Inspired Time + Character Events")
    clock = pygame.time.Clock()

    font_title = pygame.font.SysFont("consolas", 26, bold=True)
    font = pygame.font.SysFont("consolas", 18)
    font_small = pygame.font.SysFont("consolas", 16)

    # ----------------------------
    # Core objects (player + court)
    # ----------------------------
    ruler = Character("Julio", "Oliveira", 19)
    ruler.role = "Ruler"

    regent = Character("Ana", "Regent", 45)
    regent.role = "Regent"
    regent.loyalty = 75
    regent.opinion_of_player = 20
    regent.intrigue = 14

    spymaster = Character("Vasco", "Silva", 33)
    spymaster.role = "Spymaster"
    spymaster.loyalty = 40
    spymaster.opinion_of_player = -15
    spymaster.intrigue = 22

    steward = Character("Ines", "Coelho", 28)
    steward.role = "Steward"
    steward.loyalty = 68
    steward.opinion_of_player = 10
    steward.intrigue = 12

    rival = Character("Duarte", "Mendes", 41)
    rival.role = "Rival Courtier"
    rival.loyalty = 30
    rival.opinion_of_player = -30
    rival.intrigue = 18

    characters = [ruler, regent, spymaster, steward, rival]

    realm = Realm("Kingdom of Westvale", ruler)
    systems = GameSystems()

    # Time
    time = GameTime(seconds_per_day_at_speed1=0.5)

    # UI + Events
    event_ui = EventUIManager()
    registry = default_registry(seed=999)  # from events.py
    rng = random.Random(123)

    status_ref = {"text": "SPACE pause. 1/2/3/4 speeds. E forces event. Esc quits."}
    running = True

    # Random event tuning
    daily_event_chance = 0.012  # ~1.2% per day tick for testing

    while running:
        real_dt = clock.tick(60) / 1000.0

        # ----------------------------
        # Input
        # ----------------------------
        for event in pygame.event.get():
            # Popup consumes input first
            if event_ui.handle_event(event):
                continue

            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode(
                    (event.w, event.h),
                    pygame.RESIZABLE | pygame.SCALED,
                    vsync=1
                )

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                elif event.key == pygame.K_SPACE:
                    time.toggle_pause()
                    status_ref["text"] = "Paused ⏸️" if time.paused else f"Playing ▶️ (x{time.speed_multiplier:g})"

                elif event.key == pygame.K_1:
                    time.set_speed_index(1)
                    status_ref["text"] = "Speed x1"

                elif event.key == pygame.K_2:
                    time.set_speed_index(2)
                    status_ref["text"] = "Speed x2"

                elif event.key == pygame.K_3:
                    time.set_speed_index(3)
                    status_ref["text"] = "Speed x4"

                elif event.key == pygame.K_4:
                    time.set_speed_index(4)
                    status_ref["text"] = "Speed x8"

                elif event.key == pygame.K_e:
                    # Force an event from registry
                    ctx = {
                        "realm": realm,
                        "player": realm.ruler,
                        "characters": characters,
                        "status": status_ref,
                        "rng": rng,
                    }
                    ev = registry.roll(ctx)
                    if ev:
                        event_ui.push(ev, ctx)
                        status_ref["text"] = f"Forced event: {ev.event_id or ev.title}"
                    else:
                        status_ref["text"] = "No valid events to fire."

        # ----------------------------
        # Simulation
        # ----------------------------
        # CK3 feel: time stops while popup open
        if not event_ui.is_open():
            time.update(real_dt)
            days_advanced = time.pop_day_ticks()

            for _ in range(days_advanced):
                systems.on_day(realm, characters, time.date)

                # Random events from registry
                if rng.random() < daily_event_chance:
                    ctx = {
                        "realm": realm,
                        "player": realm.ruler,
                        "characters": characters,
                        "status": status_ref,
                        "rng": rng,
                    }
                    ev = registry.roll(ctx)
                    if ev:
                        event_ui.push(ev, ctx)

                if time.date.is_first_day_of_year():
                    systems.on_year(realm, characters, time.date)

        # open queued events
        event_ui.update()

        # ----------------------------
        # Draw
        # ----------------------------
        w, h = screen.get_size()
        screen.fill(BG_COLOR)

        pad = 22
        left = pygame.Rect(pad, pad, (w - pad * 3) // 2, h - pad * 2)
        right = pygame.Rect(left.right + pad, pad, (w - pad * 3) // 2, h - pad * 2)

        draw_panel(screen, left)
        draw_panel(screen, right)

        # Left panel
        y = left.y + 18
        x = left.x + 18
        y = draw_text(screen, "Time System", x, y, font_title, ACCENT)
        y = draw_text(screen, f"Date: {time.date}", x, y, font)
        y = draw_text(screen, f"Speed: x{time.speed_multiplier:g}  ({'Paused' if time.paused else 'Running'})", x, y, font)
        y += 6
        y = draw_text(screen, f"Status: {status_ref['text']}", x, y, font_small, MUTED_COLOR)

        y += 14
        y = draw_text(screen, "Controls:", x, y, font, ACCENT)
        y = draw_text(screen, "SPACE = Pause/Play", x, y, font_small, MUTED_COLOR)
        y = draw_text(screen, "1 = x1, 2 = x2, 3 = x4, 4 = x8", x, y, font_small, MUTED_COLOR)
        y = draw_text(screen, "E = Force event from registry", x, y, font_small, MUTED_COLOR)
        y = draw_text(screen, "ESC = Quit", x, y, font_small, MUTED_COLOR)

        # Right panel
        y2 = right.y + 18
        x2 = right.x + 18
        y2 = draw_text(screen, "Realm + Court", x2, y2, font_title, ACCENT)
        y2 = draw_text(screen, f"Realm: {realm.name}", x2, y2, font)
        y2 = draw_text(screen, f"Gold: {realm.gold:.2f}", x2, y2, font)
        y2 = draw_text(screen, f"Prestige: {realm.prestige}  |  Piety: {realm.piety}", x2, y2, font_small, MUTED_COLOR)

        y2 += 12
        y2 = draw_text(screen, "Characters:", x2, y2, font, ACCENT)
        for ch in characters:
            inv = ", ".join(ch.inventory) if ch.inventory else "—"
            y2 = draw_text(screen, f"- {ch.name} ({ch.role})", x2, y2, font)
            y2 = draw_text(
                screen,
                f"   Age {ch.age} | Gold {ch.gold:.2f} | XP {ch.xp} | Loyalty {ch.loyalty} | Opinion {ch.opinion_of_player} | Intrigue {ch.intrigue} | Inv {inv}",
                x2, y2, font_small, MUTED_COLOR
            )

        # Popup last
        event_ui.draw(screen)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
