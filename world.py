# world.py
import random
from domain import Character, Realm, County

def build_demo_world(seed: int = 123):
    """
    Produces:
      - player realm + court characters (like your original)
      - neighboring realms
      - a grid of counties owned by realms
    """
    rng = random.Random(seed)

    # Player + court
    ruler = Character("Julio", "Oliveira", 19, role="Ruler")
    regent = Character("Ana", "Regent", 45, role="Regent", loyalty=75, opinion_of_player=20, intrigue=14)
    spymaster = Character("Vasco", "Silva", 33, role="Spymaster", loyalty=40, opinion_of_player=-15, intrigue=22)
    steward = Character("Ines", "Coelho", 28, role="Steward", loyalty=68, opinion_of_player=10, intrigue=12)
    rival = Character("Duarte", "Mendes", 41, role="Rival Courtier", loyalty=30, opinion_of_player=-30, intrigue=18)

    characters = [ruler, regent, spymaster, steward, rival]
    player_realm = Realm("Kingdom of Westvale", ruler)

    # Neighbor realms
    neighbor_realms: list[Realm] = []
    neighbor_names = [
        "Duchy of Greyfen",
        "Kingdom of Asterhall",
        "Duchy of Thornmarch",
        "Realm of Highmere",
        "Duchy of Redwater",
        "Kingdom of Stonegate",
    ]
    for i, rname in enumerate(neighbor_names):
        rr = Character(
            fname=rng.choice(["Edric", "Maeve", "Roland", "Selene", "Garrick", "Isolde"]),
            lname=rng.choice(["Thorne", "Ashford", "Blackwood", "Vale", "Wyvern", "Roth"]),
            age=rng.randint(22, 55),
            role="Ruler",
            loyalty=rng.randint(35, 85),
            opinion_of_player=rng.randint(-40, 25),
            intrigue=rng.randint(6, 24),
        )
        neighbor_realms.append(Realm(rname, rr, gold=80 + rng.random() * 120, prestige=rng.randint(30, 120), piety=rng.randint(10, 90), development=rng.randint(6, 18)))

    # Map grid: put player in center, neighbors around
    grid_w, grid_h = 7, 5
    center_x, center_y = grid_w // 2, grid_h // 2

    counties: list[County] = []
    realm_choices = [player_realm] + neighbor_realms

    # Assign ownership: center is player; others distributed
    for y in range(grid_h):
        for x in range(grid_w):
            if x == center_x and y == center_y:
                realm = player_realm
                cname = "Westvale (Capital)"
                cid = "westvale_capital"
            else:
                # choose neighbors more often than player
                realm = rng.choice(neighbor_realms)
                cname = f"{rng.choice(['Oak', 'River', 'Iron', 'Sun', 'Wolf', 'Mist'])}{rng.choice(['ford', 'watch', 'moor', 'hold', 'field', 'crest'])}"
                cid = f"c_{x}_{y}"
            counties.append(County(id=cid, name=cname, realm=realm, grid_x=x, grid_y=y))

    world = {
        "player_realm": player_realm,
        "characters": characters,               # your court + player
        "neighbor_realms": neighbor_realms,     # rulers exist (clickable)
        "counties": counties,
        "grid_size": (grid_w, grid_h),
        "center": (center_x, center_y),
    }
    return world
