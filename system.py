# systems.py
from domain import Realm, Character
from time_system import GameDate

class GameSystems:
    def on_day(self, realm: Realm, characters: list[Character], date: GameDate):
        realm.gold += realm.daily_income()
        for ch in characters:
            ch.xp += 1
            ch.gold += 0.02

    def on_year(self, realm: Realm, characters: list[Character], date: GameDate):
        for ch in characters:
            ch.age += 1
