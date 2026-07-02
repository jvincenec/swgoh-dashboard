"""
relic_gap_calculator.py — For any squad template in squad_templates.py,
show exactly what's missing to make it viable: which character is the
bottleneck, how many relic levels short they are, and (for any character
not yet owned) that they're not owned at all — Comlink has no
"shards remaining" field for unowned characters, so that part is a hard
limit, not an oversight.

Usage:
    python analysis/relic_gap_calculator.py

Requires data/player.json — run fetch.py first.

WHAT THIS DOES, HONESTLY:
1. Relic-level gap: fully reliable. rosterUnit.relic.currentTier is real,
   live data, and the -2 offset to get the player-facing relic LEVEL is
   directly documented by the Comlink wiki. "You need relic 7, you're at
   relic 5" is a confirmed fact, not an estimate.
2. Material cost to close that gap: NOT YET COMPUTED AS NUMBERS. I looked
   for a reliable source for exact relic material quantities and didn't
   find one I trusted — independent sources gave inconsistent or
   ambiguous numbers, and CG has changed costs before (same pattern we
   saw with the omicron price reduction). relicTierDefinition (from
   setup_game_data.py) is the actual source of truth the game client
   itself uses, but I don't have a confirmed schema for its material-cost
   field names. Rather than guess, this script PRINTS THE RAW STRUCTURE
   for one relic tier on first run, so the real field names can be
   confirmed from your actual data and the cost math added correctly in
   a follow-up — not invented now.
3. Shard gap for UNOWNED characters: not available at all. Comlink's
   rosterUnit only lists characters you've already unlocked; there is no
   field anywhere in the API for "shards owned toward unlocking X."
   This script reports unowned characters as "not owned — shard
   count isn't available via this API," not a guessed number.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from name_resolver import GameDataResolver  # noqa: E402
from squad_templates import SQUAD_TEMPLATES, relic_tier_to_level  # noqa: E402

DATA_DIR = Path(__file__).parent.parent / "data"


def load_player_data() -> dict:
    path = DATA_DIR / "player.json"
    if not path.exists():
        print(f"ERROR: {path} not found. Run fetch.py first.")
        sys.exit(1)
    return json.loads(path.read_text())


def build_roster_lookup(player_data: dict) -> dict:
    lookup = {}
    for unit in player_data.get("rosterUnit", []):
        base_id = unit.get("definitionId", "").split(":")[0]
        lookup[base_id] = unit
    return lookup


def analyze_gaps(roster_lookup: dict, resolver: GameDataResolver) -> list:
    results = []
    for template in SQUAD_TEMPLATES:
        members = []
        for base_id in template["base_ids"]:
            name = resolver.unit_name(base_id)
            unit = roster_lookup.get(base_id)

            if not unit:
                members.append(
                    {
                        "base_id": base_id,
                        "name": name,
                        "owned": False,
                        "current_relic": None,
                        "relic_gap": None,
                        "note": "Not owned — shard count toward unlocking "
                        "isn't available via Comlink (no such field exists "
                        "in the API for unowned characters).",
                    }
                )
                continue

            current_relic = relic_tier_to_level(unit.get("relic", {}).get("currentTier", 0))
            target_relic = template["min_relic"]
            gap = max(0, target_relic - current_relic)

            members.append(
                {
                    "base_id": base_id,
                    "name": name,
                    "owned": True,
                    "current_relic": current_relic,
                    "target_relic": target_relic,
                    "relic_gap": gap,
                    "note": "Material cost to close this gap is not yet "
                    "computed — see the schema note printed below."
                    if gap > 0
                    else "At or above target relic.",
                }
            )

        # The bottleneck is whoever has the largest relic_gap, or any
        # unowned member (which is a harder blocker than a relic gap).
        unowned = [m for m in members if not m["owned"]]
        relic_gaps = [m for m in members if m["owned"] and m["relic_gap"] > 0]

        if unowned:
            bottleneck = f"Not owned: {', '.join(m['name'] for m in unowned)}"
        elif relic_gaps:
            worst = max(relic_gaps, key=lambda m: m["relic_gap"])
            bottleneck = f"{worst['name']} needs +{worst['relic_gap']} relic level(s)"
        else:
            bottleneck = "None — squad meets relic requirements"

        results.append(
            {
                "name": template["name"],
                "category": template["category"],
                "members": members,
                "bottleneck": bottleneck,
            }
        )
    return results


def print_report(results: list, resolver: GameDataResolver):
    print("=" * 70)
    print("SQUAD GAP REPORT")
    print("=" * 70)
    for r in results:
        print(f"\n{r['name']} [{r['category']}]")
        for m in r["members"]:
            if not m["owned"]:
                print(f"  {m['name']:<35} NOT OWNED")
            elif m["relic_gap"] > 0:
                print(
                    f"  {m['name']:<35} relic {m['current_relic']} "
                    f"-> need {m['target_relic']} (gap: {m['relic_gap']})"
                )
            else:
                print(f"  {m['name']:<35} relic {m['current_relic']} (OK)")
        print(f"  Bottleneck: {r['bottleneck']}")

    print("\n" + "=" * 70)
    print("MATERIAL COST SCHEMA CHECK")
    print("=" * 70)
    if not resolver.available:
        print(
            "  Game data not loaded — run setup_game_data.py first to "
            "see the raw relicTierDefinition structure here."
        )
        return

    sample = resolver.relic_tier_raw(7)  # relic level 5 = enum 7
    if sample:
        print(
            "  Raw relicTierDefinition entry for tier enum 7 (relic level "
            "5) — inspect this to confirm real material-cost field names:"
        )
        print(json.dumps(sample, indent=2)[:1500])
    else:
        print(
            "  No relicTierDefinition entry found for tier enum 7. This "
            "may mean the id format differs from what was assumed "
            "('7' as a plain string key) — inspect game_data/game_data.json "
            "directly under the 'relicTierDefinition' key to confirm."
        )


def main():
    player_data = load_player_data()
    roster_lookup = build_roster_lookup(player_data)
    resolver = GameDataResolver()

    if not resolver.available:
        print(
            "Note: setup_game_data.py hasn't been run, so names will show "
            "as base IDs and the material-cost schema check at the end "
            "will be skipped. Relic-level gaps still work fine without it.\n"
        )

    results = analyze_gaps(roster_lookup, resolver)

    out_path = DATA_DIR / "relic_gap_report.json"
    out_path.write_text(json.dumps(results, indent=2))
    print(f"Saved report -> {out_path}\n")

    print_report(results, resolver)


if __name__ == "__main__":
    main()
