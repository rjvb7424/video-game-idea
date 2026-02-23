# event_content.py
from events import event
from systems.characters import ensure_ruler_identity, generate_heir, generate_spouse

DEFAULT_CULTURE = "Nordfolken"
DEFAULT_FAITH = "Nordfolken Mythology"
DEFAULT_HOUSE = "House"
DEFAULT_GENDER = "male"

DEFAULT_REALM_NAME = "Realm"
DEFAULT_REALM_SIZE = 1

TOWER_REPAIR_COSTS = [250, 350, 500]
TOWER_ACTIVATE_PIETY = 350



def _clamp_index(index, length):
    if length <= 0:
        return 0
    try:
        index = int(index)
    except (TypeError, ValueError):
        index = 0
    return max(0, min(index, length - 1))



def _player_realm_info(ctx):
    world = ctx.get("world")
    if not world:
        return DEFAULT_REALM_NAME, DEFAULT_REALM_SIZE

    realm_names = getattr(world, "realm_names", None) or []
    realm_sizes = getattr(world, "realm_sizes", None) or []
    index_base = len(realm_names) or len(realm_sizes) or 1
    rid = _clamp_index(getattr(world, "player_realm_id", 0), index_base)

    realm_name = realm_names[rid] if realm_names else DEFAULT_REALM_NAME
    realm_size = realm_sizes[rid] if 0 <= rid < len(realm_sizes) else DEFAULT_REALM_SIZE
    return realm_name, realm_size



def _log_with_date(api, ctx, message: str) -> None:
    api.log(f"{ctx['date']}: {message}")



@event("stray_cat_001", weight=6, can_fire=lambda ctx: not ctx["flags"].get("has_cat", False))
def stray_cat(ctx, E):
    def adopt(ctx2, api):
        api.flag_set("has_cat", True)
        _log_with_date(api, ctx2, "You adopted a cat.")
        api.schedule("cat_followup_001", days=7)

    def ignore(ctx2, api):
        _log_with_date(api, ctx2, "You ignored the stray cat.")

    return (E.make(
        "A Stray Cat Appears",
        [
            "A small cat slips into your hall. Servants whisper of omens.",
            "It watches you with unsettling intelligence."
        ]
    )
    .option("Adopt the cat", kind="accept", on_choose=adopt)
    .option("Ignore it", kind="secondary", on_choose=ignore)
    .done())



@event("cat_followup_001", weight=0)  # chain-only
def cat_followup(ctx, E):
    def keep(ctx2, api):
        _log_with_date(api, ctx2, "The cat stays. Court morale improves.")
        api.schedule("cat_finale_001", days=14)

    def send_away(ctx2, api):
        api.flag_set("has_cat", False)
        _log_with_date(api, ctx2, "You sent the cat away. The omens fade.")

    return (E.make(
        "The Cat’s Omen",
        "The cat has become the court’s obsession. Some say it brings fortune. Others say it watches for something."
    )
    .option("Keep it close", kind="primary", on_choose=keep)
    .option("Send it away", kind="deny", on_choose=send_away)
    .done())



@event("cat_finale_001", weight=0)  # chain-only
def cat_finale(ctx, E):
    def accept(ctx2, api):
        _log_with_date(api, ctx2, "Tales spread of your ‘witch-cat’.")

    return (E.make(
        "A Courtly Tale Spreads",
        "Travelers whisper of your strange companion. The story grows in every retelling."
    )
    .option("Let the legend grow", kind="accept", on_choose=accept)
    .done())



@event("tower_of_heaven_approach", weight=0)
def tower_of_heaven(ctx, E):
    flags = ctx["flags"]
    stage = int(flags.get("tower_repairs", 0))
    completed = bool(flags.get("tower_completed", False))
    total_repairs = len(TOWER_REPAIR_COSTS)
    remaining = max(0, total_repairs - stage)

    if completed:
        return (E.make(
            "The Tower of Heaven",
            [
                "The Tower stands serene and silent. Its purpose fulfilled.",
            ]
        )
        .allow_close(True)
        .done())

    body = [
        "Even through the haze, the Tower's pale crown pierces the sky.",
        "Legends say it was built to bridge the mortal realm and the heavens.",
        f"Repairs remaining: {remaining} of {total_repairs}."
    ]

    builder = E.make("The Tower of Heaven", body).allow_close(True)

    if stage < total_repairs:
        cost = TOWER_REPAIR_COSTS[stage]
        next_stage = stage + 1

        def fund_repair(ctx2, api, c=cost, ns=next_stage, total=total_repairs):
            resources = ctx2["resources"]
            resources["gold"] -= c
            api.flag_set("tower_repairs", ns)
            if ns >= total:
                api.flag_set("tower_repaired", True)
                _log_with_date(api, ctx2, "The Tower's repairs are complete.")
            else:
                _log_with_date(api, ctx2, f"The Tower repair advances. ({ns}/{total})")

        builder.option(
            f"Fund repair {next_stage}/{total_repairs} ({cost} gold)",
            kind="accept",
            enabled=lambda _ctx, c=cost: _ctx["resources"]["gold"] >= c,
            on_choose=fund_repair,
        )

    if stage >= total_repairs:
        def activate(ctx2, api, c=TOWER_ACTIVATE_PIETY):
            resources = ctx2["resources"]
            resources["piety"] -= c
            api.flag_set("tower_completed", True)
            _log_with_date(api, ctx2, "You ascend at the Tower of Heaven. The realm is transformed.")

            def _ascend():
                api.app._exit_game()

            api.app.modal.show(
                "Ascension",
                [
                    "Light floods the tower. The world below grows distant.",
                    "You have ascended. Your story ends in glory."
                ],
                [("Ascend", "accept", _ascend)],
            )

        builder.option(
            f"Activate the Tower ({TOWER_ACTIVATE_PIETY} piety)",
            kind="primary",
            enabled=lambda _ctx, c=TOWER_ACTIVATE_PIETY: _ctx["resources"]["piety"] >= c,
            on_choose=activate,
            close_on_choose=False,
        )

    return builder.done()



@event("ruler_marriage_001", weight=5, can_fire=lambda ctx: not ctx["character"].get("spouse"))
def ruler_marriage(ctx, E):
    def accept(ctx2, api):
        ruler = ctx2["character"]
        realm_name, realm_size = _player_realm_info(ctx2)
        culture = ruler.get("culture", DEFAULT_CULTURE)
        faith = ruler.get("faith", DEFAULT_FAITH)
        house = ruler.get("house", DEFAULT_HOUSE)
        gender = ruler.get("gender", DEFAULT_GENDER)
        ensure_ruler_identity(ctx2["rng"], ruler, culture=culture)
        spouse = generate_spouse(
            ctx2["rng"],
            realm_name=realm_name,
            realm_size=realm_size,
            culture=culture,
            faith=faith,
            house=house,
            ruler_gender=gender,
        )
        ruler["spouse"] = spouse
        _log_with_date(api, ctx2, f"You wed {spouse['name']}.")

    def decline(ctx2, api):
        _log_with_date(api, ctx2, "You remain unwed.")

    return (E.make(
        "A Match for the Throne",
        [
            "The council urges you to secure the dynasty with a marriage.",
            "A suitable match is presented before your court."
        ]
    )
    .option("Arrange the marriage", kind="accept", on_choose=accept)
    .option("Decline for now", kind="secondary", on_choose=decline)
    .done())



@event("ruler_heir_001", weight=5, can_fire=lambda ctx: ctx["character"].get("spouse") and not ctx["character"].get("heir"))
def ruler_heir(ctx, E):
    def celebrate(ctx2, api):
        ruler = ctx2["character"]
        realm_name, realm_size = _player_realm_info(ctx2)
        culture = ruler.get("culture", DEFAULT_CULTURE)
        faith = ruler.get("faith", DEFAULT_FAITH)
        house = ruler.get("house", DEFAULT_HOUSE)
        ensure_ruler_identity(ctx2["rng"], ruler, culture=culture)
        heir = generate_heir(
            ctx2["rng"],
            realm_name=realm_name,
            realm_size=realm_size,
            culture=culture,
            faith=faith,
            house=house,
        )
        ruler["heir"] = heir
        _log_with_date(api, ctx2, f"An heir is born: {heir['name']}.")

    spouse_name = "your spouse"
    spouse = ctx.get("character", {}).get("spouse")
    if isinstance(spouse, dict):
        spouse_name = spouse.get("name", spouse_name)

    return (E.make(
        "A New Heir",
        [
            f"Joy fills the hall as {spouse_name} gives birth.",
            "The line is secured, and the court celebrates."
        ]
    )
    .option("Celebrate the birth", kind="accept", on_choose=celebrate)
    .done())
