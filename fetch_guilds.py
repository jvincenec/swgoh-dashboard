"""
fetch_guilds.py — Fetches full rosters for every guild reachable via the
ally codes listed in config.json (resolved exactly: ally code -> guildId
via /player, no fuzzy name matching), plus your own guild (ALLY_CODE)
if not already covered.

Saves one file per guild: data/guilds/{slug}.json

Run with:
    python fetch_guilds.py

Requires Comlink running (docker compose up -d). Safe to re-run repeatedly.
"""

import json
import re
import sys
import time
from pathlib import Path

import requests

COMLINK_URL = "http://localhost:3000"
DATA_DIR = Path(__file__).parent / "data"
GUILDS_DIR = DATA_DIR / "guilds"
GUILDS_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_PATH = Path(__file__).parent / "config.json"

ALLY_CODE = "979789966"

REQUEST_PACE_SECONDS = 0.6


def comlink_post(endpoint: str, payload: dict) -> dict:
    resp = requests.post(
        f"{COMLINK_URL}{endpoint}",
        json={"payload": payload, "enums": False},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "guild"


def resolve_guild_id(ally_code: str):
    """Exact resolution: ally code -> player profile -> guildId. No fuzzy matching."""
    try:
        player = comlink_post("/player", {"allyCode": ally_code})
    except requests.exceptions.HTTPError as e:
        print(f"  Could not resolve ally code {ally_code}: {e}")
        return None
    gid = player.get("guildId")
    if not gid:
        print(f"  Ally code {ally_code} ({player.get('name', '?')}) has no guild.")
        return None
    print(f"  {ally_code} ({player.get('name', '?')}) -> guildId {gid}")
    return gid


def extract_member_contributions(member):
    """Type 1 = Guild Activities (tokens), 2 = Raid Tickets, 3 = Gear Donations.
    Per the Comlink wiki's documented Guild-Data contribution types."""
    TYPE_NAMES = {1: "guild_tokens", 2: "raid_tickets", 3: "gear_donations"}
    out = {}
    for c in member.get("memberContribution", []):
        name = TYPE_NAMES.get(c.get("type"))
        if name:
            out[name] = {
                "current": int(c.get("currentValue", 0) or 0),
                "lifetime": int(c.get("lifetimeValue", 0) or 0),
            }
    return out


def extract_gac_history(member):
    """Last 3 GAC seasons per member: league, division, wins, losses, points."""
    return [
        {
            "season_id": s.get("seasonId"),
            "league": s.get("league"),
            "division": s.get("division"),
            "wins": s.get("wins", 0),
            "losses": s.get("losses", 0),
            "season_points": s.get("seasonPoints", 0),
            "rank": s.get("rank"),
        }
        for s in member.get("seasonStatus", [])
    ]


def fetch_and_save_guild(guild_id: str):
    response = comlink_post(
        "/guild", {"guildId": guild_id, "includeRecentGuildActivityInfo": True}
    )
    # Comlink wraps the actual guild object under a "guild" key
    profile = response.get("guild", response)
    name = profile.get("profile", {}).get("name", guild_id)
    members = profile.get("member", [])
    out = {
        "guild_id": guild_id,
        "name": name,
        "member_count": len(members),
        "guild_gp": int(profile.get("profile", {}).get("guildGalacticPower", 0) or 0),
        "members": [
            {
                "ally_code": m.get("playerId", ""),
                "name": m.get("playerName", "?"),
                "gp": int(m.get("galacticPower", 0) or 0),
                "chars_gp": int(m.get("characterGalacticPower", 0) or 0),
                "ships_gp": int(m.get("shipGalacticPower", 0) or 0),
                "level": m.get("playerLevel", "?"),
                "contributions": extract_member_contributions(m),
                "gac_history": extract_gac_history(m),
            }
            for m in members
        ],
        # Guild-level recent activity — completed/historical only, Comlink
        # has no access to live in-progress raid/TB/TW state.
        "recent_raid_results": profile.get("recentRaidResult", []),
        "recent_tw_results": profile.get("recentTerritoryWarResult", []),
        "recent_tb_results": profile.get("recentTerritoryBattleResult", []),
    }
    slug = slugify(name)
    (GUILDS_DIR / f"{slug}.json").write_text(json.dumps(out, indent=2))
    print(f"  Saved -> data/guilds/{slug}.json ({len(members)} members, GP {out['guild_gp']})")
    return out


def main():
    config = {}
    if CONFIG_PATH.exists():
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    ally_codes = list(config.get("guild_ally_codes", []))

    if ALLY_CODE not in ally_codes:
        ally_codes.append(ALLY_CODE)

    resolved_ids = set()
    for ally_code in ally_codes:
        gid = resolve_guild_id(ally_code)
        time.sleep(REQUEST_PACE_SECONDS)
        if gid:
            resolved_ids.add(gid)

    if not resolved_ids:
        print("No guilds resolved — check config.json ally codes and Comlink connectivity.")
        sys.exit(1)

    print(f"\nFetching {len(resolved_ids)} unique guild(s) ...")
    for gid in resolved_ids:
        fetch_and_save_guild(gid)
        time.sleep(REQUEST_PACE_SECONDS)

    print("\nDone.")


if __name__ == "__main__":
    main()
