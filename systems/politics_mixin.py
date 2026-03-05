from systems.politics_actions_mixin import PoliticsActionsMixin
from systems.politics_base_mixin import PoliticsBaseMixin
from systems.politics_overview_mixin import PoliticsOverviewMixin
from systems.politics_systems_mixin import PoliticsSystemsMixin


class PoliticsMixin(
    PoliticsBaseMixin,
    PoliticsSystemsMixin,
    PoliticsActionsMixin,
    PoliticsOverviewMixin,
):
    pass
