"""
guild_analyzer.py — Pull and analyze any guild's full roster, including
your own or an opposing Territory War guild, using only their guild name.

Usage:
    python analysis/guild_analyzer.py "Banes disciples"
    python analysis/guild_analyzer.py "Opponent Guild Name"

What it does:
    1. Searches for the guild by name via Comlink's /getGuilds
    2. Pulls the full guild profile (member list + ally codes) via /guild
    3. For each member, pulls their full roster via /player
    4. Runs squad-template detection on each member's roster
    5. Saves a JSON report + prints a readable summary to the terminal

Honesty notes:
    - Step 3 means one /player call per guild member. A 50-person guild is
      ~50 requests. Comlink rate limits are roughly 20 req/sec, so this
      script paces itself — expect it to take a little while for a full
      guild, not be instant.
    - Team detection is a best-guess based on ownership + relic thresholds
      against known squad templates (see squad_templates.py), NOT a read of
      the player's actual saved squads — Comlink has no access to that.
"""

import json
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from squad_templates import detect_teams  # noqa: E402

COMLINK_URL = "http://localhost:3000"
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

REQUEST_PACE_SECONDS = 0.6  # stay comfortably under Comlink's rate limits


def comlink_post(endpoint: str, payload: dict) -> dict:
    resp = requests.post(
        f"{COMLINK_URL}{endpoint}",
        json={"payload": payload, "enums": False},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def find_guild_id_by_name(name: str) -> tuple[str, dict] | tuple[None, None]:
    print(f"Searching for guild '{name}' ...")
    result = comlink_post(
        "/getGuilds",
        {"filterType": 4, "name": name, "count": 10},
    )
    guilds = result.get("guild", [])
    if not guilds:
        return None, None
    if len(guilds) > 1:
        print(f"  Found {len(guilds)} matches, using the first:")
        for g in guilds:
            print(f"    - {g.get('name')} (GP: {g.get('guildGalacticPower', '?')})")
    chosen = guilds[0]
    return chosen.get("id"), chosen


def fetch_guild_profile(guild_id: str) -> dict:
    print("Pulling full guild profile ...")
    return comlink_post(
        "/guild",
        {"guildId": guild_id, "includeRecentGuildActivityInfo": True},
    )


def fetch_member_roster(ally_code: str) -> dict | None:
    try:
        return comlink_post("/player", {"allyCode": ally_code})
    except requests.exceptions.HTTPError:
        return None


def analyze_guild(name: str) -> dict:
    guild_id, guild_search_result = find_guild_id_by_name(name)
    if not guild_id:
        print(f"No guild found matching '{name}'.")
        sys.exit(1)

    guild_profile = fetch_guild_profile(guild_id)
    members = guild_profile.get("member", [])
    guild_name = guild_profile.get("profile", {}).get("name", name)
    guild_gp = guild_profile.get("profile", {}).get("guildGalacticPower", "?")
    member_count = len(members)

    print(f"\nGuild: {guild_name}")
    print(f"Members: {member_count}")
    print(f"Guild GP: {guild_gp}")
    print(f"\nPulling individual rosters for {member_count} members "
          f"(paced at ~{REQUEST_PACE_SECONDS}s/request, this will take a bit)...\n")

    member_reports = []
    for i, member in enumerate(members, 1):
        ally_code = member.get("playerId")  # Comlink guild member uses playerId
        player_name = member.get("playerName", "?")
        player_gp = member.get("galacticPower", "?")

        print(f"  [{i}/{member_count}] {player_name} (GP {player_gp}) ...", end=" ")

        # Guild member list gives playerId, not allyCode — /player accepts
        # either, so we try playerId directly.
        player_data = None
        try:
            player_data = comlink_post("/player", {"playerId": ally_code})
        except requests.exceptions.HTTPError as e:
            print(f"FAILED ({e})")
        time.sleep(REQUEST_PACE_SECONDS)

        if not player_data:
            member_reports.append(
                {
                    "name": player_name,
                    "gp": player_gp,
                    "error": "Could not fetch roster",
                }
            )
            continue

        roster = player_data.get("rosterUnit", [])
        detected = detect_teams(roster)
        viable_meta = [t for t in detected if t["viable"] and t["category"] == "gac_meta"]

        print(f"OK — {len(viable_meta)} viable meta squad(s) detected")

        member_reports.append(
            {
                "name": player_name,
                "gp": player_gp,
                "level": player_data.get("level"),
                "detected_teams": detected,
            }
        )

    report = {
        "guild_name": guild_name,
        "guild_id": guild_id,
        "guild_gp": guild_gp,
        "member_count": member_count,
        "members": member_reports,
    }

    return report


def print_summary(report: dict):
    print("\n" + "=" * 60)
    print(f"SUMMARY — {report['guild_name']}")
    print("=" * 60)
    print(f"Members: {report['member_count']}  |  Guild GP: {report['guild_gp']}\n")

    for m in sorted(
        report["members"],
        key=lambda x: -(x["gp"] if isinstance(x.get("gp"), int) else 0),
    ):
        if "error" in m:
            print(f"  {m['name']:<25} ERROR: {m['error']}")
            continue
        meta_teams = [
            t["name"] for t in m.get("detected_teams", [])
            if t["viable"] and t["category"] == "gac_meta"
        ]
        teams_str = ", ".join(meta_teams) if meta_teams else "no current meta squad detected"
        print(f"  {m['name']:<25} GP {m['gp']:<12} {teams_str}")


def build_squad_inventory(member_reports: list) -> list:
    """Aggregate per-member detected teams into a guild-wide inventory:
    for each known squad template, how many members can field it (viable
    relic level), and who they are. This is the guild-wide equivalent of
    the old tool's 'TW Squad Inventory' page."""
    inventory = {}

    for m in member_reports:
        if "error" in m:
            continue
        for t in m.get("detected_teams", []):
            if not t["viable"]:
                continue
            key = t["name"]
            if key not in inventory:
                inventory[key] = {
                    "name": t["name"],
                    "category": t["category"],
                    "count": 0,
                    "members": [],
                }
            inventory[key]["count"] += 1
            inventory[key]["members"].append(m["name"])

    # Sort by count descending — most-available squads first
    return sorted(inventory.values(), key=lambda x: -x["count"])


def print_squad_inventory(inventory: list, member_count: int):
    print("\n" + "=" * 60)
    print("GUILD SQUAD INVENTORY (who can field what)")
    print("=" * 60)
    if not inventory:
        print("  No viable squads detected across any member.")
        return
    for entry in inventory:
        tag = "[META]" if entry["category"] == "gac_meta" else "[legacy]"
        print(f"  {tag:<9} {entry['name']:<45} {entry['count']}/{member_count} members")



def main():
    if len(sys.argv) < 2:
        print('Usage: python analysis/guild_analyzer.py "Guild Name"')
        sys.exit(1)

    guild_name = sys.argv[1]
    report = analyze_guild(guild_name)

    # Build guild-wide squad inventory from per-member detections
    report["squad_inventory"] = build_squad_inventory(report["members"])

    # Save JSON — filename based on guild name, sanitized
    safe_name = "".join(c if c.isalnum() else "_" for c in report["guild_name"]).lower()
    out_path = DATA_DIR / f"guild_analysis_{safe_name}.json"
    out_path.write_text(json.dumps(report, indent=2))
    print(f"\nSaved full report -> {out_path}")

    print_summary(report)
    print_squad_inventory(report["squad_inventory"], report["member_count"])


if __name__ == "__main__":
    main()
