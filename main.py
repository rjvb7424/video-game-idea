# external imports
import pygame

# internal imports
from ui_elements import (
    draw_title_text, draw_header_text, draw_body_text,
    draw_accept_button, draw_deny_button, BG_COLOR
)

# import your Character / Skills
from character import Character, Skills

# NEW: import your Realm stuff
from realm import Realm, County, Faith, Culture, GovernmentType


def main():
    pygame.init()

    # Create initial window
    screen = pygame.display.set_mode(
        (1280, 720),
        pygame.RESIZABLE | pygame.SCALED,
        vsync=1
    )
    pygame.display.set_caption("Video Game Idea")
    clock = pygame.time.Clock()

    # Always track the actual screen size from pygame (important for resizable)
    WIDTH, HEIGHT = screen.get_size()

    # Create a character to test skill generation
    c = Character("Julio", "Oliveira", 19)

    # Create a regent character to test "controller != ruler"
    regent = Character("Ana", "Regent", 45)

    # --- REALM TEST SETUP ---
    catholic = Faith(name="Catholic", tenets=["Communion", "Monasticism"])
    orthodox = Faith(name="Orthodox", tenets=["Icons", "Monasticism"])

    frankish = Culture(name="Frankish", ethos="stoic", traditions=["Chivalry"], language="frankish")
    iberian = Culture(name="Iberian", ethos="egalitarian", traditions=["Conciliation"], language="iberian")

    realm = Realm(
        name="Kingdom of Westvale",
        government=GovernmentType.FEUDAL,
        faith=catholic,
        culture=frankish,
        gold=120,
        prestige=80,
        piety=35,
    )
    realm.set_ruler(c)  # ruler also becomes controller by default

    # Counties
    county1 = County(
        name="Dunford",
        faith=catholic,
        culture=frankish,
        development=8,
        control=72.5,
        holder=c
    )
    county2 = County(
        name="Stonebridge",
        faith=catholic,
        culture=iberian,
        development=4,
        control=61.0,
        holder=c
    )

    realm.add_county(county1, make_capital=True)
    realm.add_county(county2)

    # --- UI STATE ---
    status_text = "Accept rerolls skills. Deny sets values. Keys: R=Regency, A=Add County, F=Swap Faith."
    running = True
    skill_names = ["diplomacy", "martial", "stewardship", "intrigue", "learning", "prowess"]

    # Helper: make unique county names
    county_counter = 3

    while running:
        screen.fill(BG_COLOR)

        padding = 40

        # Two-column layout
        left_x = padding
        right_x = max(padding, WIDTH // 2 + padding // 2)

        y_left = padding
        y_right = padding

        # Buttons near the bottom-left
        btn_w, btn_h = 180, 40
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

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    # Toggle regency (controller)
                    if realm.controller is regent:
                        realm.set_controller(realm.ruler)  # back to ruler
                        status_text = "Controller set back to ruler ✅"
                    else:
                        realm.set_controller(regent)
                        status_text = "Regency active: controller is Ana Regent 👑"

                elif event.key == pygame.K_a:
                    # Add a new county
                    county_name = f"New County {county_counter}"
                    county_counter += 1

                    new_county = County(
                        name=county_name,
                        faith=realm.faith,
                        culture=realm.culture,
                        development=2,
                        control=55.0,
                        holder=realm.ruler
                    )
                    realm.add_county(new_county)
                    status_text = f"Added county: {county_name} 🏰"

                elif event.key == pygame.K_f:
                    # Swap realm faith
                    realm.convert_realm_faith(orthodox if realm.faith.name == "Catholic" else catholic)
                    status_text = f"Realm faith changed to: {realm.faith.name} ✝️"

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

        # ---------------- LEFT PANEL: Skills ----------------
        y_left = draw_title_text(screen, "Video Game Idea", left_x, y_left)
        y_left = draw_header_text(screen, "Skill Generation Test", left_x, y_left)
        y_left = draw_body_text(screen, f"Character: {c.fname} {c.lname} (Age {c.age})", left_x, y_left)
        y_left = draw_body_text(screen, f"Status: {status_text}", left_x, y_left)
        y_left += 10

        for name in skill_names:
            val = c.skills.get(name)
            y_left = draw_body_text(screen, f"{name.title():<12}: {val}", left_x, y_left)

        # Buttons
        _ = draw_accept_button(screen, "Reroll Skills", padding, btn_y, btn_w, btn_h)
        _ = draw_deny_button(screen, "Set Some Values", padding + btn_w + 12, btn_y, btn_w, btn_h)

        # ---------------- RIGHT PANEL: Realm ----------------
        y_right = draw_header_text(screen, "Realm Test", right_x, y_right)

        ruler_name = f"{realm.ruler.fname} {realm.ruler.lname}" if realm.ruler else "None"
        controller_name = (
            f"{realm.controller.fname} {realm.controller.lname}" if realm.controller else "None"
        )

        cap = realm.get_capital()
        cap_name = cap.name if cap else "None"

        y_right = draw_body_text(screen, f"Realm: {realm.name}", right_x, y_right)
        y_right = draw_body_text(screen, f"Government: {realm.government.value}", right_x, y_right)
        y_right = draw_body_text(screen, f"Ruler: {ruler_name}", right_x, y_right)
        y_right = draw_body_text(screen, f"Controller: {controller_name}", right_x, y_right)
        y_right = draw_body_text(screen, f"Capital: {cap_name}", right_x, y_right)

        y_right += 8
        y_right = draw_body_text(screen, f"Realm Faith: {realm.faith.name}", right_x, y_right)
        y_right = draw_body_text(screen, f"Realm Culture: {realm.culture.name}", right_x, y_right)

        y_right += 8
        y_right = draw_body_text(screen, f"Gold: {realm.gold}", right_x, y_right)
        y_right = draw_body_text(screen, f"Prestige: {realm.prestige}", right_x, y_right)
        y_right = draw_body_text(screen, f"Piety: {realm.piety}", right_x, y_right)

        y_right += 8
        y_right = draw_body_text(screen, f"Counties: {len(realm.counties)}", right_x, y_right)
        y_right = draw_body_text(screen, f"Total Dev: {realm.total_development(include_vassals=False)}", right_x, y_right)
        y_right = draw_body_text(screen, f"Avg Control: {realm.average_control(include_vassals=False):.1f}", right_x, y_right)
        y_right = draw_body_text(screen, f"Stability: {realm.realm_stability_score():.1f}", right_x, y_right)

        y_right += 12
        y_right = draw_header_text(screen, "Counties (Demesne)", right_x, y_right)
        for ct in realm.counties[:10]:  # cap draw to avoid overflow
            holder = f"{ct.holder.fname} {ct.holder.lname}" if ct.holder else "None"
            y_right = draw_body_text(
                screen,
                f"- {ct.name} | dev {ct.development} | ctrl {ct.control:.0f} | {ct.culture.name}/{ct.faith.name} | holder {holder}",
                right_x,
                y_right
            )

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
