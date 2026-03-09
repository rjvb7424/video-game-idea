import math
import random

from core.math_utils import clamp


class PoliticsBaseMixin:
    def _get_npc_target(self, rid=None):
        if rid is None:
            if self.selected_province is None:
                return None
            rid = self.selected_province.realm_id
        if rid == self.player_realm_id:
            return None
        if not (0 <= rid < len(self.world.realm_rulers)):
            return None
        ruler = self.world.realm_rulers[rid]
        if not isinstance(ruler, dict):
            return None
        realm_name = None
        if 0 <= rid < len(self.world.realm_names):
            realm_name = self.world.realm_names[rid]
        return {
            "id": rid,
            "name": ruler.get("name", "Ruler"),
            "title": ruler.get("title", "—"),
            "faith": ruler.get("faith", "—"),
            "culture": ruler.get("culture", "—"),
            "traits": ruler.get("traits", []),
            "realm_name": realm_name or "Realm",
            "manpower_total": self._realm_total_manpower(rid),
        }
    @staticmethod
    def _stat_value(character, key, default=8):
        if not isinstance(character, dict):
            return int(default)
        stats = character.get("stats", [])
        for k, v in stats:
            if k != key:
                continue
            try:
                return int(v)
            except (TypeError, ValueError):
                break
        return int(default)
    def _perk_level(self, focus):
        return 0
    @staticmethod
    def _lifestyle_label(focus):
        labels = {
            "diplomacy": "Diplomacy",
            "martial": "Martial",
            "stewardship": "Stewardship",
            "intrigue": "Intrigue",
            "learning": "Learning",
        }
        return labels.get(str(focus), str(focus).title())
    def _focus_stat_key(self, focus):
        mapping = {
            "diplomacy": "Diplomacy",
            "martial": "Martial",
            "stewardship": "Stewardship",
            "intrigue": "Intrigue",
            "learning": "Learning",
        }
        return mapping.get(focus, "Stewardship")
    @staticmethod
    def _scheme_label(scheme_type):
        labels = {
            "sway": "Sway",
            "claim": "Fabricate Claim",
            "murder": "Murder",
        }
        return labels.get(scheme_type, str(scheme_type).title())
    @staticmethod
    def _scheme_category(scheme_type):
        if scheme_type == "sway":
            return "personal"
        return "hostile"
    @staticmethod
    def _traits_of(character):
        if not isinstance(character, dict):
            return set()
        return set(character.get("traits", []))
    def _realm_size(self, rid):
        if hasattr(self.world, "realm_sizes") and 0 <= rid < len(self.world.realm_sizes):
            return max(1, int(self.world.realm_sizes[rid]))
        return max(1, sum(1 for p in self.world.provinces if p.realm_id == rid))
    def _realm_total_manpower(self, rid):
        if rid is None or not (0 <= rid < len(self.world.realm_names)):
            return 0
        pop = self.world.total_population_for_realm(rid)
        effects = self._realm_building_effects(rid)
        levy_mult = 1.0 + float(effects.get("levy_mult_bonus", 0.0))
        manpower = int(round(pop * self.army_pop_ratio * max(0.20, levy_mult)))
        return max(0, manpower)
    def _player_province_count(self, rid=None):
        if rid is None:
            rid = self.player_realm_id
        return sum(1 for p in self.world.provinces if p.realm_id == rid)
    def _compute_campaign_target_provinces(self, start_count=None):
        if start_count is None:
            start_count = self._player_province_count()
        start_count = max(1, int(start_count))
        total = max(1, len(self.world.provinces))
        share_target = int(math.ceil(total * 0.22))
        return max(start_count + 1, min(total, max(start_count + 3, share_target)))
    def _campaign_progress_percent(self):
        start = max(1, int(self._campaign_start_provinces))
        target = max(start + 1, int(self._campaign_target_provinces))
        held = self._player_province_count()
        if held <= start:
            return 0
        span = max(1, target - start)
        return int(clamp(round(((held - start) / span) * 100.0), 0, 100))
    @staticmethod
    def _realm_core_name(realm_name):
        if " of " in realm_name:
            return realm_name.split(" of ", 1)[1]
        return realm_name
    def _rank_for_realm(self, rid, gender):
        size = self._realm_size(rid)
        if size >= 3:
            return "King" if gender == "male" else "Queen"
        if size == 2:
            return "Duke" if gender == "male" else "Duchess"
        return "Count" if gender == "male" else "Countess"
    @staticmethod
    def _extract_first_name(display_name):
        titles = {
            "King",
            "Queen",
            "Duke",
            "Duchess",
            "Count",
            "Countess",
            "Prince",
            "Princess",
            "Heir",
            "Baron",
            "Baroness",
        }
        parts = str(display_name).replace(",", " ").split()
        while parts and parts[0] in titles:
            parts = parts[1:]
        if "of" in parts:
            parts = parts[:parts.index("of")]
        if not parts:
            return "Unnamed"
        if len(parts) >= 2:
            return f"{parts[0]} {parts[1]}"
        return parts[0]
    def _get_neighbor_realms(self, rid):
        neighbors = set()
        for pid, prov in enumerate(self.world.provinces):
            if prov.realm_id != rid or pid >= len(self._prov_adj):
                continue
            for nb in self._prov_adj[pid]:
                other = self.world.provinces[nb].realm_id
                if other != rid:
                    neighbors.add(other)
        return neighbors
    def _init_diplomacy_state(self):
        self.realm_relations = {}
        self.realm_claims = set()
        self.realm_truces = {}
        self.claim_fabrication_cooldowns = {}
        self.alliances = set()
        self.subjugation_cooldown_days = 0

        seed = self.world.seed * 1009 + self.player_realm_id * 53
        rnd = random.Random(seed)
        for rid in range(len(self.world.realm_names)):
            if rid == self.player_realm_id:
                continue
            self.realm_relations[rid] = rnd.randint(-30, 25)

        neighbors = list(self._get_neighbor_realms(self.player_realm_id))
        rnd.shuffle(neighbors)
        if neighbors:
            self.realm_claims.add(neighbors[0])
            if len(neighbors) > 1 and rnd.random() < 0.35:
                self.realm_claims.add(neighbors[1])
    def _get_realm_opinion(self, rid):
        try:
            rid = int(rid)
        except (TypeError, ValueError):
            return 0
        return int(self.realm_relations.get(rid, 0))
    def _change_realm_opinion(self, rid, delta):
        try:
            rid = int(rid)
        except (TypeError, ValueError):
            return 0
        cur = self._get_realm_opinion(rid)
        nxt = int(clamp(cur + int(delta), -100, 100))
        self.realm_relations[rid] = nxt
        return nxt
    def _diplomacy_snapshot(self, rid):
        if rid is None or rid == self.player_realm_id:
            return None
        truce = int(self.realm_truces.get(rid, 0))
        claim_cd = int(self.claim_fabrication_cooldowns.get(rid, 0))
        hook = getattr(self, "hooks", {}).get(rid)
        hook_days = int(hook.get("days", 0)) if isinstance(hook, dict) else 0
        hook_strength = hook.get("strength", "none") if isinstance(hook, dict) else "none"
        schemes = [s for s in getattr(self, "active_schemes", []) if s.get("target_id") == rid]
        scheme = schemes[0] if schemes else None
        return {
            "opinion": self._get_realm_opinion(rid),
            "claimed": rid in self.realm_claims,
            "allied": rid in self.alliances,
            "truce_days": truce,
            "claim_cooldown_days": claim_cd,
            "hook_days": hook_days,
            "hook_strength": hook_strength,
            "scheme_name": self._scheme_label(scheme.get("type")) if isinstance(scheme, dict) else None,
            "scheme_progress": float(scheme.get("progress", 0.0)) if isinstance(scheme, dict) else 0.0,
        }
    @staticmethod
    def _days_label(days):
        d = max(0, int(days))
        if d < 365:
            return f"{d}d"
        years = d / 365.0
        return f"{years:.1f}y"
    @staticmethod
    def _decrement_days_map(values):
        for key in list(values.keys()):
            values[key] = int(values[key]) - 1
            if values[key] <= 0:
                values.pop(key, None)
