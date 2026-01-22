# event_content.py
from events import event

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