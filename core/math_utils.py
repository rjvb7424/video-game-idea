import math


def clamp(value, lo, hi):
    return lo if value < lo else hi if value > hi else value


def lerp(a, b, t):
    return a + (b - a) * t


def exp_smooth_t(sharpness, dt):
    return 1.0 - math.exp(-sharpness * dt)
