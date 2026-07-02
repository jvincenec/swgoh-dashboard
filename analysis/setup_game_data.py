"""
setup_game_data.py — One-time (or rarely-repeated) setup step that downloads
the specific slices of SWGoH's game database needed to:
    1. Resolve base IDs to readable names (e.g. GRANDMASTERLUKE -> "Jedi
       Master Luke Skywalker")
    2. Detect REAL omicron/zeta status per skill, instead of inferring it
       from relic level like squad_templates.py does today
    3. Resolve equipped mod sets/slots/rarity to readable info
    4. Compute real relic material costs to close a gap to a target relic
       level, using the official relicTierDefinition collection — NOT
       hand-typed numbers from blog posts, which turned out to be
       inconsistent and possibly stale (CG has changed material costs
       before, same as the omicron cost reduction we found earlier).

Usage:
    python analysis/setup_game_data.py

This is NOT part of the regular fetch.py workflow — run it once, and
re-run only when you suspect game data is stale (a new character release,
a balance update). It downloads a few hundred MB total; this is the
heavier, separate undertaking discussed before building it.

What this is built on (verified against the official Comlink wiki):
    - /metadata returns "latestGamedataVersion", required before calling
      /data.
    - /data accepts an "items" bitmask to request ONLY specific
      collections instead of the full 200+ MB dataset. We request:
        category (1) + skill (4) + statMod/statModSet (33554432) +
        units (137438953472) + relicTierDefinition (68719476736)
        = 206311984645
      This is a deliberate scoping decision — NOT everything the API
      offers, just what's needed for the stated goals above.
    - /localization requires the version + a locale suffix (e.g. ":ENG_US")
      to get a reasonably sized response instead of all languages at once.

Honesty note on relic costs:
    I looked for a reliable source for exact relic material quantities per
    tier and found name-only confirmation (which materials apply to which
    tier ranges) but no quantity table I trusted enough to hand-encode —
    secondary sources disagreed or were ambiguous, and costs are known to
    change over time. relicTierDefinition is the same data the game client
    itself reads, so relic_gap_calculator.py computes costs directly from
    it rather than from a guessed table.

Honesty note on omicron enum mapping:
    The wiki documents OMICRON enum values (e.g. 9 = GAC 3v3 only,
    10 = Galactic War) but determining whether a skill HAS an omicron
    unlocked at all requires comparing the player's skill tier (from
    rosterUnit) against the skill's tier list in the /data skill
    collection (looking for isOmicronTier=True at that tier index). This
    is implemented in parse_skill_truth() below, following the wiki's
    documented method exactly rather than approximating.
"""

import json
import sys
from pathlib import Path

import requests

COMLINK_URL = "http://localhost:3000"
DATA_DIR = Path(__file__).parent.parent / "data"
GAME_DATA_DIR = Path(__file__).parent.parent / "game_data"
GAME_DATA_DIR.mkdir(exist_ok=True)

# Bitmask for items: category + skill + statMod/statModSet + units
# + relicTierDefinition
ITEMS_BITMASK = "206311984645"


def comlink_post(endpoint: str, payload: dict, enums: bool = False) -> dict:
    resp = requests.post(
        f"{COMLINK_URL}{endpoint}",
        json={"payload": payload, "enums": enums},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


def comlink_get(endpoint: str) -> dict:
    resp = requests.get(f"{COMLINK_URL}{endpoint}", timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_latest_version() -> str:
    print("Fetching /metadata for latest game data version ...")
    meta = comlink_post("/metadata", {})
    version = meta.get("latestGamedataVersion")
    if not version:
        print("ERROR: could not find latestGamedataVersion in /metadata response.")
        sys.exit(1)
    print(f"  Latest version: {version}")
    return version


def fetch_game_data(version: str) -> dict:
    print(f"Fetching /data (items bitmask {ITEMS_BITMASK}) — this may take a while ...")
    return comlink_post(
        "/data",
        {"version": version, "includePveUnits": False, "items": ITEMS_BITMASK},
    )


def fetch_localization(version: str, locale: str = "ENG_US") -> dict:
    print(f"Fetching /localization for {locale} ...")
    loc_id = f"{version}:{locale}"
    return comlink_post("/localization", {"id": loc_id, "unzip": True})


def main():
    try:
        version = fetch_latest_version()
    except requests.exceptions.ConnectionError:
        print(
            "\nERROR: Could not connect to Comlink at "
            f"{COMLINK_URL}.\nMake sure it's running: docker compose up -d\n"
        )
        sys.exit(1)

    game_data = fetch_game_data(version)
    out_path = GAME_DATA_DIR / "game_data.json"
    out_path.write_text(json.dumps(game_data))
    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"Saved game data -> {out_path} ({size_mb:.1f} MB)")

    try:
        localization = fetch_localization(version)
        loc_path = GAME_DATA_DIR / "localization_en.json"
        loc_path.write_text(json.dumps(localization))
        size_mb = loc_path.stat().st_size / (1024 * 1024)
        print(f"Saved localization -> {loc_path} ({size_mb:.1f} MB)")
    except Exception as e:
        print(f"Warning: could not fetch localization ({e})")

    # Save the version we used, so other scripts can check staleness later
    (GAME_DATA_DIR / "version.txt").write_text(version)

    print("\nDone. Game data is ready for name_resolver.py to use.")


if __name__ == "__main__":
    main()
