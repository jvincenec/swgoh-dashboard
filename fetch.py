"""
fetch.py — Pulls live data from your local SWGoH Comlink instance and
saves it as JSON for the dashboard to display.

Run this any time you want to refresh your data:
    python fetch.py

Requires:
    - docker compose up -d   (Comlink running on localhost:3000)
    - pip install -r requirements.txt
"""

import json
import sys
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# CONFIG — edit these two values for your account
# ---------------------------------------------------------------------------
ALLY_CODE = "979789966"          # your ally code, no dashes
COMLINK_URL = "http://localhost:3000"

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def comlink_post(endpoint: str, payload: dict) -> dict:
    """POST to a Comlink endpoint and return the parsed JSON response."""
    url = f"{COMLINK_URL}{endpoint}"
    body = {"payload": payload, "enums": False}
    resp = requests.post(url, json=body, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_player(ally_code: str) -> dict:
    print(f"Fetching player profile for ally code {ally_code} ...")
    return comlink_post("/player", {"allyCode": ally_code})


def fetch_guild(guild_id: str) -> dict:
    print(f"Fetching guild profile for guild id {guild_id} ...")
    return comlink_post(
        "/guild",
        {"guildId": guild_id, "includeRecentGuildActivityInfo": True},
    )


def fetch_player_arena(ally_code: str) -> dict:
    print(f"Fetching arena profile for ally code {ally_code} ...")
    return comlink_post("/playerArena", {"allyCode": ally_code})


# ---------------------------------------------------------------------------
# Recommendation logic — built from your roster, not guesses
# ---------------------------------------------------------------------------

# Current meta-relevant base IDs worth knowing about (Season 79, 3v3 GAC).
# This list is intentionally short and should be refreshed periodically by
# checking https://swgoh.gg/gac/squads/ — it is NOT auto-updated by this script.
META_RELEVANT_BASE_IDS = {
    "GRANDMOFFTARKIN": "Tarkin appears in a current top-usage GAC squad "
                        "(Tarkin / Dark Side Clones). You already own him — "
                        "this is your closest piece to the current meta.",
}

# Characters worth prioritizing relics on, based on earlier roster analysis
PRIORITY_RELIC_TARGETS = [
    "GRANDMASTERLUKE",     # Jedi Master Luke Skywalker (GL)
    "VADER",               # Darth Vader
    "GENERALKENOBI",       # General Kenobi
    "GENERALSKYWALKER",    # General Skywalker
    "JEDIKNIGHTLUKE",      # JK Luke
    "R2D2_LEGENDARY",      # R2-D2
    "CHEWBACCALEGENDARY",  # Chewbacca
    "HANSOLO",             # Han Solo
]


def build_recommendations(player_data: dict) -> dict:
    """Look at the live roster and produce a short, concrete set of
    recommendations rather than generic advice."""
    roster = player_data.get("rosterUnit", [])

    # Index roster by base id for quick lookup
    by_base_id = {}
    for unit in roster:
        base_id = unit.get("definitionId", "").split(":")[0]
        by_base_id[base_id] = unit

    recommendations = {
        "meta_relevant_owned": [],
        "relic_push_targets": [],
        "missing_meta_pieces": [],
        "general": [],
    }

    # 1. Flag any owned characters relevant to current meta
    for base_id, note in META_RELEVANT_BASE_IDS.items():
        if base_id in by_base_id:
            recommendations["meta_relevant_owned"].append(
                {"base_id": base_id, "note": note}
            )

    # 2. Relic push targets — show current relic tier vs recommended next step
    for base_id in PRIORITY_RELIC_TARGETS:
        unit = by_base_id.get(base_id)
        if not unit:
            continue
        relic_tier = unit.get("relic", {}).get("currentTier", 0)
        # Comlink relic tiers are offset; tier 2 = Relic 0, so subtract 2
        relic_level = max(0, relic_tier - 2)
        recommendations["relic_push_targets"].append(
            {
                "base_id": base_id,
                "current_relic": relic_level,
                "suggested_action": (
                    "Push higher with Lightspeed Tokens / relic mats — "
                    "this is a core squad piece."
                ),
            }
        )

    # 3. General reminders that don't depend on roster specifics
    recommendations["general"] = [
        "Check Shipments tabs for time-limited currency before it expires.",
        "Spend Fleet Arena Tokens on Zeta/Omega ability materials if any "
        "priority character is missing key abilities.",
        "Run Conquest every cycle — it's the best non-meta-dependent source "
        "of Datacron materials and Razor Crest shards.",
        "Re-check https://swgoh.gg/gac/squads/ periodically — the meta list "
        "in this script is a manual snapshot, not live.",
    ]

    return recommendations


def main():
    if len(sys.argv) > 1:
        ally_code = sys.argv[1]
    else:
        ally_code = ALLY_CODE

    try:
        player_data = fetch_player(ally_code)
    except requests.exceptions.ConnectionError:
        print(
            "\nERROR: Could not connect to Comlink at "
            f"{COMLINK_URL}.\n"
            "Make sure it's running: docker compose up -d\n"
        )
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"\nERROR: Comlink returned an error: {e}\n")
        sys.exit(1)

    # Save raw player data
    (DATA_DIR / "player.json").write_text(json.dumps(player_data, indent=2))
    print(f"Saved player data -> {DATA_DIR / 'player.json'}")

    # Fetch arena data (squad/fleet/GAC rank)
    try:
        arena_data = fetch_player_arena(ally_code)
        (DATA_DIR / "arena.json").write_text(json.dumps(arena_data, indent=2))
        print(f"Saved arena data -> {DATA_DIR / 'arena.json'}")
    except Exception as e:
        print(f"Warning: could not fetch arena data ({e})")

    # Fetch guild data if we know our guild id
    guild_id = player_data.get("guildId")
    if guild_id:
        try:
            guild_data = fetch_guild(guild_id)
            (DATA_DIR / "guild.json").write_text(json.dumps(guild_data, indent=2))
            print(f"Saved guild data -> {DATA_DIR / 'guild.json'}")
        except Exception as e:
            print(f"Warning: could not fetch guild data ({e})")
    else:
        print("No guildId found on player profile — skipping guild fetch.")

    # Build and save recommendations
    recs = build_recommendations(player_data)
    (DATA_DIR / "recommendations.json").write_text(json.dumps(recs, indent=2))
    print(f"Saved recommendations -> {DATA_DIR / 'recommendations.json'}")

    print("\nDone. Refresh the dashboard in your browser to see the update.")


if __name__ == "__main__":
    main()
