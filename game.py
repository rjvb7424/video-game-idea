from systems.army_mixin import ArmyMixin
from systems.bootstrap_mixin import BootstrapMixin
from systems.economy_mixin import EconomyMixin
from systems.game_loop_mixin import GameLoopMixin
from systems.map_ui_mixin import MapUIMixin
from systems.menu_mixin import MenuMixin
from systems.persistence_mixin import PersistenceMixin
from systems.politics_mixin import PoliticsMixin
from systems.war_mixin import WarMixin


class GameApp(
    BootstrapMixin,
    GameLoopMixin,
    EconomyMixin,
    MapUIMixin,
    PersistenceMixin,
    PoliticsMixin,
    MenuMixin,
    ArmyMixin,
    WarMixin,
):
    def __init__(self):
        self._bootstrap()


if __name__ == "__main__":
    GameApp().run()
