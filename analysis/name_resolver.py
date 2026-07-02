"""
name_resolver.py — Loads the game data downloaded by setup_game_data.py
and provides lookup functions: base ID -> readable name, real omicron/zeta
truth per skill (not inferred from relic level), and mod set/slot
resolution.

Usage (as a library, imported by other scripts):
    from name_resolver import GameDataResolver
    resolver = GameDataResolver()
    resolver.unit_name("GRANDMASTERLUKE")  # -> "Jedi Master Luke Skywalker"
    resolver.has_omicron(unit_roster_entry)  # -> list of unlocked omicron skill ids

Requires game_data/game_data.json and game_data/localization_en.json to
exist — run setup_game_data.py first.

Honesty note:
    If the game data files don't exist, every method here returns the
    input unchanged (e.g. unit_name("GRANDMASTERLUKE") just returns
    "GRANDMASTERLUKE") rather than crashing. This means the rest of the
    dashboard keeps working with base IDs if this setup step hasn't been
    run — it's an enhancement layer, not a hard dependency.
"""

import json
from pathlib import Path

GAME_DATA_DIR = Path(__file__).parent.parent / "game_data"

# Stat mod set/slot lookups, per the Comlink wiki's documented mapping
MOD_SET_NAMES = {
    1: "Health", 2: "Offense", 3: "Defense", 4: "Speed",
    5: "Critical Chance", 6: "Critical Damage", 7: "Potency", 8: "Tenacity",
}
MOD_SLOT_NAMES = {
    1: "Square", 2: "Arrow", 3: "Diamond", 4: "Triangle", 5: "Circle", 6: "Plus/Cross",
}


class GameDataResolver:
    def __init__(self):
        self.available = False
        self.units_by_base_id = {}
        self.skills_by_id = {}
        self.localized_strings = {}
        self.relic_tiers_by_id = {}

        game_data_path = GAME_DATA_DIR / "game_data.json"
        loc_path = GAME_DATA_DIR / "localization_en.json"

        if not game_data_path.exists():
            return  # available stays False — callers degrade gracefully

        try:
            game_data = json.loads(game_data_path.read_text())
        except (json.JSONDecodeError, OSError):
            return

        for unit in game_data.get("units", []):
            base_id = unit.get("baseId")
            if base_id:
                self.units_by_base_id[base_id] = unit

        for skill in game_data.get("skill", []):
            skill_id = skill.get("id")
            if skill_id:
                self.skills_by_id[skill_id] = skill

        for relic_tier in game_data.get("relicTierDefinition", []):
            tier_id = relic_tier.get("id")
            if tier_id:
                self.relic_tiers_by_id[tier_id] = relic_tier

        if loc_path.exists():
            try:
                loc_data = json.loads(loc_path.read_text())
                # Localization bundle format: list of {key, value} or a dict —
                # handle both defensively since exact shape isn't documented.
                if isinstance(loc_data, dict):
                    self.localized_strings = loc_data
                elif isinstance(loc_data, list):
                    self.localized_strings = {
                        entry.get("key"): entry.get("value")
                        for entry in loc_data
                        if isinstance(entry, dict) and "key" in entry
                    }
            except (json.JSONDecodeError, OSError):
                pass

        self.available = True

    def _localize(self, key: str, fallback: str) -> str:
        if not key:
            return fallback
        return self.localized_strings.get(key, fallback)

    def unit_name(self, base_id: str) -> str:
        """Resolve a base ID to its readable in-game name. Falls back to
        the base ID itself if game data isn't loaded or the unit isn't
        found."""
        if not self.available:
            return base_id
        unit = self.units_by_base_id.get(base_id)
        if not unit:
            return base_id
        name_key = unit.get("nameKey")
        return self._localize(name_key, base_id)

    def has_omicron(self, roster_unit: dict) -> list:
        """Given a single unit entry from rosterUnit (the player's actual
        roster data), return the list of skill ids that have a REAL,
        unlocked omicron — determined by comparing the player's current
        skill tier against the skill's documented omicron tier, exactly as
        described in the Comlink wiki's Player-Data expansion guide.
        Returns an empty list if game data isn't loaded (degrades safely
        rather than guessing)."""
        if not self.available:
            return []

        unlocked_omicrons = []
        for player_skill in roster_unit.get("skill", []):
            skill_id = player_skill.get("id")
            player_tier = player_skill.get("tier")
            if skill_id is None or player_tier is None:
                continue

            skill_def = self.skills_by_id.get(skill_id)
            if not skill_def:
                continue

            tiers = skill_def.get("tier", [])
            # Per the wiki: add +2 to the player's tier value to get the
            # actual in-game tier when comparing.
            actual_tier = player_tier + 2
            for idx, tier_def in enumerate(tiers):
                tier_index_ingame = idx + 1
                if tier_index_ingame == actual_tier and tier_def.get("isOmicronTier"):
                    unlocked_omicrons.append(skill_id)
                    break

        return unlocked_omicrons

    def has_zeta(self, roster_unit: dict) -> list:
        """Same method as has_omicron, but for zeta tiers."""
        if not self.available:
            return []

        unlocked_zetas = []
        for player_skill in roster_unit.get("skill", []):
            skill_id = player_skill.get("id")
            player_tier = player_skill.get("tier")
            if skill_id is None or player_tier is None:
                continue

            skill_def = self.skills_by_id.get(skill_id)
            if not skill_def:
                continue

            tiers = skill_def.get("tier", [])
            actual_tier = player_tier + 2
            for idx, tier_def in enumerate(tiers):
                tier_index_ingame = idx + 1
                if tier_index_ingame == actual_tier and tier_def.get("isZetaTier"):
                    unlocked_zetas.append(skill_id)
                    break

        return unlocked_zetas

    def relic_tier_raw(self, relic_tier_enum: int) -> dict:
        """Return the raw relicTierDefinition entry for a given tier enum,
        unmodified — caller (or a human) inspects this to find the actual
        material-cost field names for their installed game version.

        Honesty note — why this returns raw data instead of parsed costs:
            I looked for a confirmed schema for relicTierDefinition's
            material-cost fields and could not verify one. The Comlink
            wiki confirms the collection's purpose (relic archetypes per
            tier, referenced by units.relicDefinition) but not the exact
            key names for "what it costs to reach this tier." Rather than
            guess at field names and risk silently wrong numbers, this
            returns the raw entry. relic_gap_calculator.py prints this
            raw structure on first run so you (or I, in a follow-up) can
            confirm the real field names from your actual data before any
            cost math is presented as fact.
        """
        if not self.available:
            return {}
        return self.relic_tiers_by_id.get(str(relic_tier_enum), {})

    def resolve_mod(self, definition_id: str) -> dict:
        """Resolve a mod's definitionId (e.g. '7Bdc' style 3-character
        code per the wiki) into set/slot/rarity. Falls back to raw parsing
        of the id digits if game data isn't loaded, per the manual mapping
        the Comlink wiki provides as an alternative to the statMod lookup."""
        if not definition_id or len(definition_id) < 3:
            return {"set": "?", "slot": "?", "rarity": "?"}

        try:
            set_id = int(definition_id[0])
            rarity = int(definition_id[1])
            slot_raw = int(definition_id[2])
        except ValueError:
            return {"set": "?", "slot": "?", "rarity": "?"}

        return {
            "set": MOD_SET_NAMES.get(set_id, f"Unknown ({set_id})"),
            "slot": MOD_SLOT_NAMES.get(slot_raw + 1, f"Unknown ({slot_raw})"),
            "rarity": rarity,
        }
