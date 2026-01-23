def clip_draw(surface, rect, draw_fn):
    prev = surface.get_clip()
    surface.set_clip(rect)
    try:
        draw_fn()
    finally:
        surface.set_clip(prev)
