# game_time.py
from dataclasses import dataclass

# Simple 30-day months calendar (good enough for now)
DAYS_IN_MONTH = 30
MONTHS_IN_YEAR = 12
DAYS_IN_YEAR = DAYS_IN_MONTH * MONTHS_IN_YEAR


@dataclass
class GameDate:
    year: int = 1066
    month: int = 1   # 1..12
    day: int = 1     # 1..30

    def add_days(self, n: int) -> None:
        total_days = (self.year * DAYS_IN_YEAR) + ((self.month - 1) * DAYS_IN_MONTH) + (self.day - 1)
        total_days += n

        self.year = total_days // DAYS_IN_YEAR
        rem = total_days % DAYS_IN_YEAR

        self.month = (rem // DAYS_IN_MONTH) + 1
        self.day = (rem % DAYS_IN_MONTH) + 1

    def is_first_day_of_month(self) -> bool:
        return self.day == 1

    def is_first_day_of_year(self) -> bool:
        return self.month == 1 and self.day == 1

    def __str__(self) -> str:
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"


class GameTime:
    """
    Converts real-time delta into in-game days and exposes "popped" day ticks.
    """
    SPEEDS = [0.0, 1.0, 2.0, 4.0, 8.0]  # index 0 = paused

    def __init__(self, seconds_per_day_at_speed1: float = 0.5):
        # Example: at speed 1, 1 in-game day passes every 0.5 real seconds
        self.seconds_per_day_at_speed1 = seconds_per_day_at_speed1
        self.speed_index = 1
        self.date = GameDate()
        self._accum_days = 0.0
        self._popped_days = 0

    @property
    def speed_multiplier(self) -> float:
        return self.SPEEDS[self.speed_index]

    @property
    def paused(self) -> bool:
        return self.speed_index == 0

    def toggle_pause(self) -> None:
        self.speed_index = 1 if self.speed_index == 0 else 0

    def set_speed_index(self, idx: int) -> None:
        self.speed_index = max(0, min(idx, len(self.SPEEDS) - 1))

    def update(self, real_dt_seconds: float) -> None:
        """
        Call every frame with real dt seconds. Internally accumulates fractional days.
        """
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
        """
        Returns how many in-game "days" advanced since last update().
        You use this to run daily/monthly/yearly checks deterministically.
        """
        return self._popped_days
