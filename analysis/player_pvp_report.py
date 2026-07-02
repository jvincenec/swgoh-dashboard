"""
player_pvp_report.py — Parse the player data already pulled by fetch.py for
live GAC standing and the actual last-used Squad Arena / Fleet Arena teams.

Usage:
    python analysis/player_pvp_report.py

Requires data/player.json to exist — run fetch.py first.

What this is built on (verified against the official Comlink wiki):
    - player.playerRating: the player's CURRENT Grand Arena Skill Rating,
      League, and Division — this is live standing, different from
      seasonStatus which is a history of the last 3 completed seasons.
    - player.pvpProfile: the player's Squad Arena and Fleet Arena ranks
      ALONG WITH the actual team used in them last. This is the closest
      thing to "their real squad" available anywhere in the API — unlike
      our squad_templates.py inference, this is the actual last-deployed
      team, for arena specifically (not GAC, TW, raids, or TB, which have
      no equivalent field).
Honesty note on schema certainty:
    The Comlink wiki confirms pvpProfile's PURPOSE (arena rank + last-used
    team) but does not document its exact internal field names. The
    parsing below is written defensively against multiple possible shapes
    and will print "no data found" rather than crash or invent values if
    the actual response doesn't match. If your real data comes back empty
    here, the fix is to inspect data/player.json directly for the actual
    pvpProfile structure and adjust parse_pvp_teams() accordingly — this
    is flagged rather than silently guessed.
"""

import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def load_player_data() -> dict:
    path = DATA_DIR / "player.json"
    if not path.exists():
        print(f"ERROR: {path} not found. Run fetch.py first.")
        sys.exit(1)
    return json.loads(path.read_text())


def parse_gac_rating(player_data: dict) -> dict:
    rating = player_data.get("playerRating", {})
    if not rating:
        return {}
    # playerRating shape varies by Comlink version; handle both flat and
    # nested forms defensively rather than assuming one.
    if isinstance(rating, list):
        rating = rating[0] if rating else {}
    return {
        "league": rating.get("league"),
        "division": rating.get("division"),
        "skill_rating": rating.get("playerSkillRating", {}).get("skillRating")
        if isinstance(rating.get("playerSkillRating"), dict)
        else rating.get("skillRating"),
    }


def parse_pvp_teams(player_data: dict) -> dict:
    pvp = player_data.get("pvpProfile", [])
    result = {"squad_arena": None, "fleet_arena": None}

    for entry in pvp:
        # tab 0 historically = Squad Arena, tab 1 = Fleet Arena, per
        # community-documented Comlink usage. Treated defensively.
        tab = entry.get("tab")
        rank = entry.get("rank")
        team = [
            u.split(":")[0]  # strip the gear/rarity suffix, keep base id
            for u in entry.get("squad", {}).get("cell", [])
            if u
        ] if isinstance(entry.get("squad"), dict) else []

        bucket = {"rank": rank, "last_used_team": team}
        if tab == 0:
            result["squad_arena"] = bucket
        elif tab == 1:
            result["fleet_arena"] = bucket
        else:
            result.setdefault("other", []).append({"tab": tab, **bucket})

    return result


def print_report(rating: dict, teams: dict):
    print("=" * 60)
    print("LIVE GAC STANDING")
    print("=" * 60)
    if rating:
        print(f"  League: {rating.get('league')}")
        print(f"  Division: {rating.get('division')}")
        print(f"  Skill Rating: {rating.get('skill_rating')}")
    else:
        print("  No playerRating data found.")

    print("\n" + "=" * 60)
    print("LAST-USED ARENA TEAMS")
    print("=" * 60)
    sq = teams.get("squad_arena")
    fl = teams.get("fleet_arena")
    if sq:
        print(f"  Squad Arena (rank {sq['rank']}): {', '.join(sq['last_used_team']) or 'unknown'}")
    else:
        print("  Squad Arena: no data found")
    if fl:
        print(f"  Fleet Arena (rank {fl['rank']}): {', '.join(fl['last_used_team']) or 'unknown'}")
    else:
        print("  Fleet Arena: no data found")


def main():
    player_data = load_player_data()
    rating = parse_gac_rating(player_data)
    teams = parse_pvp_teams(player_data)

    report = {"gac_rating": rating, "arena_teams": teams}
    out_path = DATA_DIR / "player_pvp_report.json"
    out_path.write_text(json.dumps(report, indent=2))
    print(f"Saved report -> {out_path}\n")

    print_report(rating, teams)


if __name__ == "__main__":
    main()
