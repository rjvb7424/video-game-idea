# external imports
import pygame

# internal imports
from ui_elements import (
    draw_title_text, draw_header_text, draw_body_text,
    draw_accept_button, draw_deny_button, BG_COLOR
)

# import your Character / Skills
from character import Character, Skills

def main():
    pygame.init()

    display_info = pygame.display.Info()
    WIDTH, HEIGHT = display_info.current_w, display_info.current_h

    screen = pygame.display.set_mode(
        (1280, 720),
        pygame.RESIZABLE | pygame.SCALED,
        vsync=1
    )
    pygame.display.set_caption("Video Game Idea")
    clock = pygame.time.Clock()

    # Create a character to test skill generation
    c = Character("Julio", "Oliveira", 19)

    status_text = "Click Accept to reroll skills, Deny to set some values."
    running = True

    skill_names = ["diplomacy", "martial", "stewardship", "intrigue", "learning", "prowess"]

    while running:
        screen.fill(BG_COLOR)

        padding = 40
        y = padding

        # Buttons near the bottom-left (define rects BEFORE event handling)
        btn_w, btn_h = 160, 40
        btn_y = HEIGHT - padding - btn_h

        accept_rect = pygame.Rect(padding, btn_y, btn_w, btn_h)
        deny_rect = pygame.Rect(padding + btn_w + 12, btn_y, btn_w, btn_h)

        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.VIDEORESIZE:
                WIDTH, HEIGHT = event.w, event.h
                screen = pygame.display.set_mode(
                    (WIDTH, HEIGHT),
                    pygame.RESIZABLE | pygame.SCALED,
                    vsync=1
                )

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos

                if accept_rect.collidepoint(mx, my):
                    # Reroll all skills
                    c.skills = Skills()
                    status_text = "Rerolled skills 🎲"

                elif deny_rect.collidepoint(mx, my):
                    # Set some skills manually (tests set/get)
                    c.skills.set("diplomacy", 20)
                    c.skills.set("martial", 0)
                    c.skills.set("learning", 15)
                    status_text = "Set diplomacy=20, martial=0, learning=15 ✅"

        # Draw UI elements
        y = draw_title_text(screen, "Video Game Idea", padding, y)
        y = draw_header_text(screen, "Skill Generation Test", padding, y)
        y = draw_body_text(screen, f"Character: {c.fname} {c.lname} (Age {c.age})", padding, y)
        y = draw_body_text(screen, f"Status: {status_text}", padding, y)
        y += 10

        # Draw skill list
        for name in skill_names:
            val = c.skills.get(name)
            y = draw_body_text(screen, f"{name.title():<12}: {val}", padding, y)

        # Draw buttons
        _ = draw_accept_button(screen, "Reroll Skills", padding, btn_y, btn_w, btn_h)
        _ = draw_deny_button(screen, "Set Some Values", padding + btn_w + 12, btn_y, btn_w, btn_h)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
