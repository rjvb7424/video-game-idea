# main.py
import pygame
import random

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
    def __init__(self, seed=42):
        self.rng = random.Random(seed)

    def on_day(self, realm: Realm, characters: list[Character], date: GameDate):
        realm.gold += realm.daily_income()
        for ch in characters:
            ch.xp += 1
            ch.gold += 0.02

    def on_year(self, realm: Realm, characters: list[Character], date: GameDate):
        for ch in characters:
            ch.age += 1


# ----------------------------
# Event Builders (many!)
# (kept in main for easy testing)
# ----------------------------
def build_event_stray_cat(systems: GameSystems, realm: Realm, status_ref: dict) -> tuple[EventData, dict]:
    ctx = {"realm": realm, "ruler": realm.ruler, "status": status_ref, "systems": systems}

    def adopt(c):
        r = c["ruler"]
        if "Cat 🐈" not in r.inventory:
            r.inventory.append("Cat 🐈")
        c["status"]["text"] = "You adopted a cat 🐈"

    def buy_food(c):
        c["realm"].gold -= 10
        c["status"]["text"] = "You buy food for the cat. (-10 gold)"

    def ignore(c):
        c["status"]["text"] = "You ignore the strange visitor."

    def can_adopt(c):
        return "Cat 🐈" not in c["ruler"].inventory

    def can_buy_food(c):
        return c["realm"].gold >= 10

    ev = EventData(
        title="A Stray Cat Appears",
        subtitle="A Curious Visitor",
        body=lambda c: f"A small cat follows {c['ruler'].fname} through the halls. The servants whisper it may be an omen.",
        options=[
            EventOption("Adopt the cat 🐈", on_choose=adopt, enabled=can_adopt),
            EventOption("Buy food for it (-10 gold)", on_choose=buy_food, enabled=can_buy_food),
            EventOption("Ignore it.", on_choose=ignore),
        ],
        event_id="stray_cat_001",
        allow_close=False,      # NO X / NO ESC
        allow_esc_close=False,
    )
    return ev, ctx


def build_event_wandering_merchant(realm: Realm, status_ref: dict) -> tuple[EventData, dict]:
    ctx = {"realm": realm, "ruler": realm.ruler, "status": status_ref}

    def buy_relic(c):
        c["realm"].gold -= 30
        c["ruler"].inventory.append("Curious Relic ✨")
        c["status"]["text"] = "You bought a relic. (-30 gold)"

    def haggle(c):
        c["ruler"].xp += 30
        c["status"]["text"] = "You haggle and learn. (+30 XP)"

    def dismiss(c):
        c["status"]["text"] = "You dismiss the merchant."

    ev = EventData(
        title="A Wandering Merchant",
        subtitle="Opportunity knocks",
        body="A merchant arrives with odd trinkets and bold promises. One item catches your eye.",
        options=[
            EventOption("Buy the relic (-30 gold)", on_choose=buy_relic, enabled=lambda c: c["realm"].gold >= 30),
            EventOption("Haggle (+30 XP)", on_choose=haggle),
            EventOption("Dismiss them.", on_choose=dismiss),
        ],
        event_id="merchant_001",
        allow_close=False,
    )
    return ev, ctx


def build_event_bad_omens(realm: Realm, status_ref: dict) -> tuple[EventData, dict]:
    ctx = {"realm": realm, "ruler": realm.ruler, "status": status_ref}

    def prayers(c):
        c["realm"].piety += 10
        c["status"]["text"] = "You hold prayers. (+10 piety)"

    def blame(c):
        c["realm"].prestige += 5
        c["status"]["text"] = "You blame a rival. (+5 prestige)"

    def ignore(c):
        c["status"]["text"] = "You ignore the omens."

    ev = EventData(
        title="Bad Omens",
        subtitle="Whispers spread",
        body=lambda c: f"Unusual signs are reported across {c['realm'].name}. The court watches your reaction.",
        options=[
            EventOption("Hold prayers (+10 piety)", on_choose=prayers),
            EventOption("Blame a rival (+5 prestige)", on_choose=blame),
            EventOption("Ignore it.", on_choose=ignore),
        ],
        event_id="omens_001",
        allow_close=False,
    )
    return ev, ctx


def build_event_bandit_problem(realm: Realm, status_ref: dict) -> tuple[EventData, dict]:
    ctx = {"realm": realm, "ruler": realm.ruler, "status": status_ref}

    def pay_guard(c):
        c["realm"].gold -= 20
        c["realm"].prestige += 2
        c["status"]["text"] = "You hire guards. (-20 gold, +2 prestige)"

    def ignore(c):
        c["realm"].prestige -= 3
        c["status"]["text"] = "You do nothing. (-3 prestige)"

    def lead_patrol(c):
        c["ruler"].xp += 60
        c["status"]["text"] = "You lead a patrol. (+60 XP)"

    ev = EventData(
        title="Bandits on the Road",
        subtitle="Safety and reputation",
        body="Merchants report raids along the main road. The people demand action.",
        options=[
            EventOption("Hire extra guards (-20 gold)", on_choose=pay_guard, enabled=lambda c: c["realm"].gold >= 20),
            EventOption("Personally lead a patrol (+60 XP)", on_choose=lead_patrol),
            EventOption("Do nothing (-3 prestige)", on_choose=ignore),
        ],
        event_id="bandits_001",
        allow_close=False,
    )
    return ev, ctx


def build_event_rare_book(realm: Realm, status_ref: dict) -> tuple[EventData, dict]:
    ctx = {"realm": realm, "ruler": realm.ruler, "status": status_ref}

    def buy(c):
        c["realm"].gold -= 25
        c["ruler"].xp += 120
        c["ruler"].inventory.append("Rare Book 📜")
        c["status"]["text"] = "You buy a rare book. (-25 gold, +120 XP)"

    def borrow(c):
        c["ruler"].xp += 40
        c["status"]["text"] = "You borrow it briefly. (+40 XP)"

    def burn(c):
        c["realm"].piety += 5
        c["status"]["text"] = "You denounce it as heresy. (+5 piety)"

    ev = EventData(
        title="A Rare Book",
        subtitle="Knowledge has a price",
        body="A scholar offers a rare manuscript—dangerous ideas, or priceless wisdom?",
        options=[
            EventOption("Buy it (-25 gold, +120 XP)", on_choose=buy, enabled=lambda c: c["realm"].gold >= 25),
            EventOption("Borrow it (+40 XP)", on_choose=borrow),
            EventOption("Denounce it (+5 piety)", on_choose=burn),
        ],
        event_id="book_001",
        allow_close=False,
    )
    return ev, ctx


def build_event_harvest(realm: Realm, status_ref: dict) -> tuple[EventData, dict]:
    ctx = {"realm": realm, "ruler": realm.ruler, "status": status_ref}

    def invest(c):
        c["realm"].gold -= 18
        c["realm"].prestige += 4
        c["status"]["text"] = "You invest in tools and storage. (-18 gold, +4 prestige)"

    def tax_more(c):
        c["realm"].gold += 22
        c["realm"].prestige -= 4
        c["status"]["text"] = "You squeeze the peasants. (+22 gold, -4 prestige)"

    def celebrate(c):
        c["realm"].prestige += 2
        c["status"]["text"] = "You celebrate with the people. (+2 prestige)"

    ev = EventData(
        title="The Harvest",
        subtitle="A season turns",
        body="The harvest comes in. Some say it is plentiful—others warn of hard months ahead.",
        options=[
            EventOption("Invest in storage (-18 gold, +4 prestige)", on_choose=invest, enabled=lambda c: c["realm"].gold >= 18),
            EventOption("Raise taxes (+22 gold, -4 prestige)", on_choose=tax_more),
            EventOption("Hold celebrations (+2 prestige)", on_choose=celebrate),
        ],
        event_id="harvest_001",
        allow_close=False,
    )
    return ev, ctx


def build_event_mystic(realm: Realm, status_ref: dict) -> tuple[EventData, dict]:
    ctx = {"realm": realm, "ruler": realm.ruler, "status": status_ref}

    def pay(c):
        c["realm"].gold -= 12
        c["ruler"].xp += 35
        c["status"]["text"] = "You pay the mystic. (-12 gold, +35 XP)"

    def arrest(c):
        c["realm"].prestige += 3
        c["status"]["text"] = "You arrest the mystic. (+3 prestige)"

    def listen(c):
        c["ruler"].xp += 10
        c["status"]["text"] = "You listen politely. (+10 XP)"

    ev = EventData(
        title="A Mystic Arrives",
        subtitle="Truth or trickery?",
        body="A mystic claims to foresee your future. The court watches, amused and wary.",
        options=[
            EventOption("Pay for a reading (-12 gold, +35 XP)", on_choose=pay, enabled=lambda c: c["realm"].gold >= 12),
            EventOption("Arrest them (+3 prestige)", on_choose=arrest),
            EventOption("Listen politely (+10 XP)", on_choose=listen),
        ],
        event_id="mystic_001",
        allow_close=False,
    )
    return ev, ctx


# Event list for random rolling
def roll_random_event(event_ui: EventUIManager, systems: GameSystems, realm: Realm, status_ref: dict, rng: random.Random):
    builders = [
        lambda: build_event_stray_cat(systems, realm, status_ref),
        lambda: build_event_wandering_merchant(realm, status_ref),
        lambda: build_event_bad_omens(realm, status_ref),
        lambda: build_event_bandit_problem(realm, status_ref),
        lambda: build_event_rare_book(realm, status_ref),
        lambda: build_event_harvest(realm, status_ref),
        lambda: build_event_mystic(realm, status_ref),
    ]

    # weighted-ish via duplication (simple for testing)
    weighted = (
        [builders[0]] * 5 +  # stray cat
        [builders[1]] * 3 +  # merchant
        [builders[2]] * 4 +  # omens
        [builders[3]] * 4 +  # bandits
        [builders[4]] * 3 +  # rare book
        [builders[5]] * 4 +  # harvest
        [builders[6]] * 3    # mystic
    )

    pick = rng.choice(weighted)
    ev, ctx = pick()
    event_ui.push(ev, ctx)


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

    # Core objects
    ruler = Character("Julio", "Oliveira", 19)
    regent = Character("Ana", "Regent", 45)
    realm = Realm("Kingdom of Westvale", ruler)
    characters = [ruler, regent]

    time = GameTime(seconds_per_day_at_speed1=0.5)
    systems = GameSystems(seed=42)

    # NEW: Event UI manager
    event_ui = EventUIManager()

    status_ref = {"text": "SPACE pause. 1/2/3/4 speeds. E forces event. Esc quits."}
    running = True

    # Random events tuning
    daily_event_chance = 0.010  # 1% per day tick (fast testing)
    rng = random.Random(123)

    while running:
        real_dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            # Modal popup consumes input first
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
                    # Force random event popup now
                    roll_random_event(event_ui, systems, realm, status_ref, rng)
                    status_ref["text"] = "Forced random event popup 🎲"

        # Stop time while event popup is open (CK3 feel)
        if not event_ui.is_open():
            time.update(real_dt)
            days_advanced = time.pop_day_ticks()

            for _ in range(days_advanced):
                systems.on_day(realm, characters, time.date)

                # random events on daily tick
                if rng.random() < daily_event_chance:
                    roll_random_event(event_ui, systems, realm, status_ref, rng)

                if time.date.is_first_day_of_year():
                    systems.on_year(realm, characters, time.date)

        # Open queued events if any
        event_ui.update()

        # Draw
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
        y = draw_text(screen, "E = Force random event popup", x, y, font_small, MUTED_COLOR)
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

        # Draw popup last
        event_ui.draw(screen)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
