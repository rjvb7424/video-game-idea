# main.py
import pygame

from ui_elements import (
    draw_title_text,
    draw_header_text,
    draw_body_text,
    draw_accept_button,
    draw_deny_button,
)

BG_COLOR = (20, 20, 25)

def main():
    pygame.init()

    # Start windowed (resizable)
    WIDTH, HEIGHT = 900, 600
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("Video Game Idea")
    clock = pygame.time.Clock()

    status_text = "Click a button..."

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.VIDEORESIZE:
                WIDTH, HEIGHT = event.w, event.h
                screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if accept_rect.collidepoint(mx, my):
                    status_text = "Accepted ✅"
                elif deny_rect.collidepoint(mx, my):
                    status_text = "Denied ❌"

        screen.fill(BG_COLOR)

        padding = 40
        y = padding

        y = draw_title_text(screen, "Video Game Idea", padding, y)
        y = draw_header_text(screen, "Prototype UI", padding, y)
        y = draw_body_text(screen, "This is a simple main loop using your UI helpers.", padding, y)
        y = draw_body_text(screen, f"Status: {status_text}", padding, y)

        # Buttons near the bottom-left
        btn_w, btn_h = 140, 40
        btn_y = HEIGHT - padding - btn_h

        accept_rect = draw_accept_button(screen, "Accept", padding, btn_y, btn_w, btn_h)
        deny_rect = draw_deny_button(screen, "Deny", padding + btn_w + 12, btn_y, btn_w, btn_h)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
