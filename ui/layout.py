import pygame

from ui.theme import TOP_BAR_H, BOTTOM_BAR_H, SIDE_W_L, SIDE_W_R


class Layout:
    def __init__(self, w, h):
        self.w = w
        self.h = h

        self.top = pygame.Rect(0, 0, w, TOP_BAR_H)
        self.bottom = pygame.Rect(0, h - BOTTOM_BAR_H, w, BOTTOM_BAR_H)

        # FLUSH to edges, and start immediately below top bar
        self.left = pygame.Rect(
            0,
            TOP_BAR_H,
            SIDE_W_L,
            h - TOP_BAR_H,
        )

        self.right = pygame.Rect(
            w - SIDE_W_R,
            TOP_BAR_H,
            SIDE_W_R,
            h - TOP_BAR_H - BOTTOM_BAR_H,
        )

        # Map fills the space between panels, also flush vertically
        mx = self.left.right
        my = TOP_BAR_H
        mw = self.right.left - mx
        mh = self.bottom.top - my
        self.map = pygame.Rect(mx, my, mw, mh)

    def update(self, w, h):
        self.__init__(w, h)
