"""
mods_report.py — Resolve equipped mod details (set, slot, rarity) for
every character in the player's roster, using the digit-mapping method
documented in the Comlink wiki (works even without setup_game_data.py,
since mod set/slot mapping is fixed game data that doesn't change).

Usage:
    python analysis/mods_report.py

Requires data/player.json to exist — run fetch.py first.

What this is built on (verified against the official Comlink wiki):
    - rosterUnit.equippedStatMod: array of equipped mods per character.
    - Each mod's definitionId encodes set (1st digit), rarity/pips (2nd
      digit), and slot-1 (3rd digit) — documented directly in the
      Player-Data wiki page as an alternative to looking up the statMod
      collection from /data.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from name_resolver import GameDataResolver  # noqa: E402

DATA_DIR = Path(__file__).parent.parent / "data"


def load_player_data() -> dict:
    path = DATA_DIR / "player.json"
    if not path.exists():
        print(f"ERROR: {path} not found. Run fetch.py first.")
        sys.exit(1)
    return json.loads(path.read_text())


def build_mods_report(player_data: dict, resolver: GameDataResolver) -> list:
    report = []
    for unit in player_data.get("rosterUnit", []):
        mods = unit.get("equippedStatMod", [])
        if not mods:
            continue

        base_id = unit.get("definitionId", "").split(":")[0]
        readable_name = resolver.unit_name(base_id)

        resolved_mods = []
        for mod in mods:
            definition_id = mod.get("definitionId", "")
            resolved_mods.append(resolver.resolve_mod(definition_id))

        report.append(
            {
                "base_id": base_id,
                "name": readable_name,
                "mod_count": len(resolved_mods),
                "mods": resolved_mods,
            }
        )
    return report


def print_report(report: list):
    print("=" * 70)
    print("EQUIPPED MODS REPORT")
    print("=" * 70)
    if not report:
        print("  No characters with equipped mods found.")
        return
    for entry in report:
        print(f"\n{entry['name']} ({entry['mod_count']}/6 mods equipped)")
        for m in entry["mods"]:
            print(f"  {m['slot']:<12} {m['set']:<16} rarity {m['rarity']}")


def main():
    player_data = load_player_data()
    resolver = GameDataResolver()

    if not resolver.available:
        print(
            "Note: setup_game_data.py hasn't been run, so character names "
            "will show as base IDs. Mod set/slot/rarity still resolves "
            "fine since that mapping is fixed and doesn't need game data.\n"
        )

    report = build_mods_report(player_data, resolver)

    out_path = DATA_DIR / "mods_report.json"
    out_path.write_text(json.dumps(report, indent=2))
    print(f"Saved report -> {out_path}\n")

    print_report(report)


if __name__ == "__main__":
    main()
