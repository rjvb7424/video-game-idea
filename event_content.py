# event_content.py
from events import event

TOWER_REPAIR_COSTS = [250, 350, 500]
TOWER_ACTIVATE_PIETY = 350

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
        ctx2["resources"]["prestige"] += 5
        api.log(f"{ctx2['date']}: Tales spread of your ‘witch-cat’. (+5 Prestige)")

    return (E.make(
        "A Courtly Tale Spreads",
        "Travelers whisper of your strange companion. The story grows in every retelling."
    )
    .option("Let the legend grow", kind="accept", on_choose=accept)
    .done())


@event("tower_of_heaven_approach", weight=0)  # triggered by button
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
