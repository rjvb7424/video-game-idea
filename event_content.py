# event_content.py
from events import event
from systems.characters import ensure_ruler_identity, generate_heir, generate_spouse

TOWER_REPAIR_COSTS = [250, 350, 500]
TOWER_ACTIVATE_PIETY = 350


def _player_realm_info(ctx):
    world = ctx.get("world")
    rid = getattr(world, "player_realm_id", 0)
    realm_name = world.realm_names[rid] if world and world.realm_names else "Realm"
    realm_size = world.realm_sizes[rid] if world and hasattr(world, "realm_sizes") else 1
    return realm_name, realm_size

@event("stray_cat_001", weight=6, can_fire=lambda ctx: not ctx["flags"].get("has_cat", False))
def stray_cat(ctx, E):
    def adopt(ctx2, api):
        api.flag_set("has_cat", True)
        api.log(f"{ctx2['date']}: You adopted a cat.")
        api.schedule("cat_followup_001", days=7)

    def ignore(ctx2, api):
        api.log(f"{ctx2['date']}: You ignored the stray cat.")

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
        api.log(f"{ctx2['date']}: The cat stays. Court morale improves.")
        api.schedule("cat_finale_001", days=14)

    def send_away(ctx2, api):
        api.flag_set("has_cat", False)
        api.log(f"{ctx2['date']}: You sent the cat away. The omens fade.")

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
        api.log(f"{ctx2['date']}: Tales spread of your ‘witch-cat’.")

    return (E.make(
        "A Courtly Tale Spreads",
        "Travelers whisper of your strange companion. The story grows in every retelling."
    )
    .option("Let the legend grow", kind="accept", on_choose=accept)
    .done())


@event("tower_of_heaven_approach", weight=0)
def tower_of_heaven(ctx, E):
    stage = int(ctx["flags"].get("tower_repairs", 0))
    completed = bool(ctx["flags"].get("tower_completed", False))
    remaining = max(0, len(TOWER_REPAIR_COSTS) - stage)

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
        f"Repairs remaining: {remaining} of {len(TOWER_REPAIR_COSTS)}."
    ]

    builder = E.make("The Tower of Heaven", body).allow_close(True)

    if stage < len(TOWER_REPAIR_COSTS):
        cost = TOWER_REPAIR_COSTS[stage]

        def fund_repair(ctx2, api, c=cost, s=stage):
            ctx2["resources"]["gold"] -= c
            api.flag_set("tower_repairs", s + 1)
            if s + 1 >= len(TOWER_REPAIR_COSTS):
                api.flag_set("tower_repaired", True)
                api.log(f"{ctx2['date']}: The Tower's repairs are complete.")
            else:
                api.log(f"{ctx2['date']}: The Tower repair advances. ({s + 1}/{len(TOWER_REPAIR_COSTS)})")

        builder.option(
            lambda _ctx, c=cost, s=stage: f"Fund repair {s + 1}/{len(TOWER_REPAIR_COSTS)} ({c} gold)",
            kind="accept",
            enabled=lambda _ctx, c=cost: _ctx["resources"]["gold"] >= c,
            on_choose=fund_repair,
        )

    if stage >= len(TOWER_REPAIR_COSTS):
        def activate(ctx2, api, c=TOWER_ACTIVATE_PIETY):
            ctx2["resources"]["piety"] -= c
            api.flag_set("tower_completed", True)
            api.log(f"{ctx2['date']}: You ascend at the Tower of Heaven. The realm is transformed.")

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
            lambda _ctx, c=TOWER_ACTIVATE_PIETY: f"Activate the Tower ({c} piety)",
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
        ensure_ruler_identity(ctx2["rng"], ruler, culture=ruler.get("culture", "Nordfolken"))
        spouse = generate_spouse(
            ctx2["rng"],
            realm_name=realm_name,
            realm_size=realm_size,
            culture=ruler.get("culture", "Nordfolken"),
            faith=ruler.get("faith", "Nordfolken Mythology"),
            house=ruler.get("house", "House"),
            ruler_gender=ruler.get("gender", "male"),
        )
        ruler["spouse"] = spouse
        api.log(f"{ctx2['date']}: You wed {spouse['name']}.")

    def decline(ctx2, api):
        api.log(f"{ctx2['date']}: You remain unwed.")

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
        ensure_ruler_identity(ctx2["rng"], ruler, culture=ruler.get("culture", "Nordfolken"))
        heir = generate_heir(
            ctx2["rng"],
            realm_name=realm_name,
            realm_size=realm_size,
            culture=ruler.get("culture", "Nordfolken"),
            faith=ruler.get("faith", "Nordfolken Mythology"),
            house=ruler.get("house", "House"),
        )
        ruler["heir"] = heir
        api.log(f"{ctx2['date']}: An heir is born: {heir['name']}.")

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
