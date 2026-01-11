# time_system.py
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
