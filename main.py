# main.py
import pygame
import random

# NEW: event popup system (make sure you created event_ui.py from earlier)
from event_ui import EventUIManager, EventData, EventOption

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

    def is_first_day_of_month(self) -> bool:
        return self.day == 1

    def is_first_day_of_year(self) -> bool:
        return self.month == 1 and self.day == 1

    def __str__(self):
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"

class GameTime:
    """
    Converts real dt to in-game days. Your simulation runs on day ticks.
    """
    SPEEDS = [0.0, 1.0, 2.0, 4.0, 8.0]  # index 0 paused

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
# Replace later with your real
# Character / Realm classes.
# ----------------------------
class Character:
    def __init__(self, fname, lname, age):
        self.fname = fname
        self.lname = lname
        self.age = age
        self.gold = 0.0
        self.xp = 0
        self.inventory = []

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
        self.development = 12  # placeholder “total dev”

    def daily_income(self) -> float:
        # Placeholder income model: dev drives daily income
        return 0.05 * self.development


# ----------------------------
# “Checks” / Systems hub
# (the place you asked for)
# ----------------------------
class GameSystems:
    def __init__(self, seed=42):
        self.rng = random.Random(seed)

    # Example event function you mentioned
    def character_gets_cat(self, character: Character):
        if "Cat 🐈" not in character.inventory:
            character.inventory.append("Cat 🐈")

    def on_day(self, realm: Realm, characters: list[Character], date: GameDate):
        # 1) Daily economy tick
        realm.gold += realm.daily_income()

        # 2) Daily drip XP / gold to characters (example)
        for ch in characters:
            ch.xp += 1
            ch.gold += 0.02

    def on_year(self, realm: Realm, characters: list[Character], date: GameDate):
        # Example yearly tick
        for ch in characters:
            ch.age += 1


# ----------------------------
# Event creation helpers
# ----------------------------
def push_cat_event(event_ui: EventUIManager, systems: GameSystems, realm: Realm, status_ref: dict):
    """
    Queues a CK3-like event popup with multiple choices.
    status_ref is a dict so callbacks can edit status text.
    """
    ctx = {"realm": realm, "ruler": realm.ruler, "systems": systems, "status": status_ref}

    def adopt_cat(ctx):
        ctx["systems"].character_gets_cat(ctx["ruler"])
        ctx["status"]["text"] = "You adopted a cat 🐈"

    def shoo_cat(ctx):
        # small gold gain (flavor)
        ctx["realm"].gold += 10
        ctx["status"]["text"] = "You shooed the cat away (+10 gold?)"

    def ignore(ctx):
        ctx["status"]["text"] = "You ignored the strange visitor."

    def can_adopt(ctx):
        return "Cat 🐈" not in ctx["ruler"].inventory

    event_ui.push(
        EventData(
            title="A Stray Cat Appears",
            subtitle="A Curious Visitor",
            body=lambda c: (
                f"A small cat follows {c['ruler'].fname} through the halls, "
                "watching every step. The servants whisper it may be an omen."
            ),
            options=[
                EventOption("Adopt the cat 🐈", on_choose=adopt_cat, enabled=can_adopt),
                EventOption("Feed it, then send it away (+10 gold)", on_choose=shoo_cat),
                EventOption("Ignore it.", on_choose=ignore),
            ],
            event_id="stray_cat_001",
        ),
        ctx
    )

def push_training_event(event_ui: EventUIManager, realm: Realm, status_ref: dict):
    ctx = {"realm": realm, "ruler": realm.ruler, "status": status_ref}

    def study(ctx):
        ctx["ruler"].xp += 75
        ctx["status"]["text"] = "You spend the evening studying. (+75 XP)"

    def feast(ctx):
        ctx["realm"].gold -= 15
        ctx["status"]["text"] = "You hold a small feast. (-15 gold, +prestige vibe)"

    def can_feast(ctx):
        return ctx["realm"].gold >= 15

    event_ui.push(
        EventData(
            title="An Evening Decision",
            subtitle="Time is a resource",
            body=lambda c: (
                f"The day ends in {c['realm'].name}. "
                "How will you spend your evening?"
            ),
            options=[
                EventOption("Study statecraft (+75 XP)", on_choose=study),
                EventOption("Hold a feast (-15 gold)", on_choose=feast, enabled=can_feast),
                EventOption("Sleep early.", on_choose=lambda c: c["status"].update(text="You rest.")),
            ],
            event_id="evening_decision_001",
        ),
        ctx
    )


# ----------------------------
# Main
# ----------------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE | pygame.SCALED, vsync=1)
    pygame.display.set_caption("CK3-Inspired Time + Events Demo")
    clock = pygame.time.Clock()

    font_title = pygame.font.SysFont("consolas", 26, bold=True)
    font = pygame.font.SysFont("consolas", 18)
    font_small = pygame.font.SysFont("consolas", 16)

    # Create your core objects
    ruler = Character("Julio", "Oliveira", 19)
    regent = Character("Ana", "Regent", 45)
    realm = Realm("Kingdom of Westvale", ruler)
    characters = [ruler, regent]

    # Time + Systems
    time = GameTime(seconds_per_day_at_speed1=0.5)
    systems = GameSystems(seed=42)

    # NEW: Event UI manager
    event_ui = EventUIManager()

    # UI state stored in a dict so event callbacks can mutate it
    status_ref = {"text": "SPACE pause. 1/2/3/4 speeds. E forces event. Esc quits."}
    running = True

    # Random event tuning (feel free to change)
    daily_event_chance = 0.006  # ~0.6% per day tick (with speedups, it will happen fairly often)
    rng = random.Random(123)

    while running:
        real_dt = clock.tick(60) / 1000.0

        # Handle events
        for event in pygame.event.get():
            # If popup is open, it consumes input first (modal)
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
                    # Force an event right now (for testing)
                    push_cat_event(event_ui, systems, realm, status_ref)
                    status_ref["text"] = "Forced event popup: Stray Cat 🐈"

        # Update time + run checks (but don't advance simulation while a popup is open)
        # CK3 style: time stops while modal event is open
        if not event_ui.popup.is_open():
            time.update(real_dt)
            days_advanced = time.pop_day_ticks()

            for _ in range(days_advanced):
                systems.on_day(realm, characters, time.date)

                # Random events happen on day ticks (only when no popup is open)
                if rng.random() < daily_event_chance:
                    # pick an event type
                    if rng.random() < 0.55:
                        push_cat_event(event_ui, systems, realm, status_ref)
                    else:
                        push_training_event(event_ui, realm, status_ref)

                if time.date.is_first_day_of_year():
                    systems.on_year(realm, characters, time.date)

        # Let the event UI open queued events
        event_ui.update()

        # -----------------
        # Draw
        # -----------------
        w, h = screen.get_size()
        screen.fill(BG_COLOR)

        pad = 22
        left = pygame.Rect(pad, pad, (w - pad * 3) // 2, h - pad * 2)
        right = pygame.Rect(left.right + pad, pad, (w - pad * 3) // 2, h - pad * 2)

        draw_panel(screen, left)
        draw_panel(screen, right)

        # Left panel: Time & controls
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
        y = draw_text(screen, "E = Force event popup", x, y, font_small, MUTED_COLOR)
        y = draw_text(screen, "ESC = Quit", x, y, font_small, MUTED_COLOR)

        # Right panel: Realm + Characters
        y2 = right.y + 18
        x2 = right.x + 18
        y2 = draw_text(screen, "Simulation State", x2, y2, font_title, ACCENT)
        y2 = draw_text(screen, f"Realm: {realm.name}", x2, y2, font)
        y2 = draw_text(screen, f"Realm Gold: {realm.gold:.2f}", x2, y2, font)
        y2 = draw_text(screen, f"Prestige: {realm.prestige}  |  Piety: {realm.piety}", x2, y2, font_small, MUTED_COLOR)

        y2 += 12
        y2 = draw_text(screen, "Characters:", x2, y2, font, ACCENT)
        for ch in characters:
            inv = ", ".join(ch.inventory) if ch.inventory else "—"
            y2 = draw_text(screen, f"- {ch.name} (Age {ch.age})", x2, y2, font)
            y2 = draw_text(screen, f"   Gold: {ch.gold:.2f} | XP: {ch.xp} | Inv: {inv}", x2, y2, font_small, MUTED_COLOR)

        # Draw popup last (on top)
        event_ui.draw(screen)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
