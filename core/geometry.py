def shield_points(center, size):
    cx, cy = center
    w = size
    h = int(size * 1.25)
    return [
        (cx - w // 2, cy - h // 2),
        (cx + w // 2, cy - h // 2),
        (cx + int(w * 0.45), cy + int(h * 0.08)),
        (cx, cy + h // 2),
        (cx - int(w * 0.45), cy + int(h * 0.08)),
    ]
