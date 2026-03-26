import traceback

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
    try:
        GameApp().run()
    except Exception:
        tb = traceback.format_exc()
        print(tb)
        with open("crash.log", "w") as f:
            f.write(tb)
        input("Crash logged to crash.log — press Enter to exit")
