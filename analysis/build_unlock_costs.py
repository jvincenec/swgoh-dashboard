"""
build_unlock_costs.py — Builds a static reference table of unlock/promotion
shard costs for every obtainable unit, from Comlink's real game data
(units.creationRecipeReference -> recipe.ingredients).

SCOPE LIMIT (verified, not a guess): this gives the REQUIREMENT (e.g.
"needs 330 shards"), not a player's PROGRESS toward it. Comlink cannot
see shard inventory for units a player doesn't yet own — that's private
inventory data the API explicitly doesn't expose, same category as
unequipped mods/mats. This is a reference table, not a tracker.

Run with:
    python analysis/build_unlock_costs.py

Slow (~5 segment fetch, few minutes) — not part of the normal refresh
cycle, run once and re-run only when you suspect new characters/costs
have changed.
"""

import json
import sys
from pathlib import Path

import requests

COMLINK_URL = "http://localhost:3000"
GAME_DATA_DIR = Path(__file__).parent.parent / "game_data"
GAME_DATA_DIR.mkdir(exist_ok=True)
MAX_SEGMENTS = 30


def comlink_post(endpoint: str, payload: dict, timeout=300) -> dict:
    resp = requests.post(
        f"{COMLINK_URL}{endpoint}",
        json={"payload": payload, "enums": True},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_all_segments(version: str) -> dict:
    merged = {}
    prev_total = -1
    for segment in range(MAX_SEGMENTS):
        print(f"Fetching segment {segment} ...")
        data = comlink_post(
            "/data",
            {"version": version, "includePveUnits": False, "requestSegment": segment},
        )
        total = sum(len(v) for v in data.values() if isinstance(v, list))
        if total == 0 and segment > 0:
            break
        for k, v in data.items():
            if isinstance(v, list):
                merged.setdefault(k, [])
                merged[k].extend(v)
            elif k not in merged:
                merged[k] = v
        new_total = sum(len(v) for v in merged.values() if isinstance(v, list))
        if new_total == prev_total:
            break
        prev_total = new_total
    return merged


def main():
    print("Fetching /metadata ...")
    meta = comlink_post("/metadata", {})
    version = meta.get("latestGamedataVersion")
    if not version:
        print("ERROR: no version found.")
        sys.exit(1)

    data = fetch_all_segments(version)
    units = data.get("units", [])
    recipes_by_id = {r["id"]: r for r in data.get("recipe", [])}

    print(f"\n{len(units)} unit definitions, {len(recipes_by_id)} recipes loaded.")

    results = {}
    skipped_no_recipe = 0
    for unit in units:
        base_id = unit.get("baseId")
        if not base_id or not unit.get("obtainable", False):
            continue

        recipe_ref = unit.get("creationRecipeReference")
        if not recipe_ref or recipe_ref not in recipes_by_id:
            skipped_no_recipe += 1
            continue

        recipe = recipes_by_id[recipe_ref]
        ingredients = []
        for ing in recipe.get("ingredients", []):
            ingredients.append({
                "id": ing.get("id"),
                "type": ing.get("type"),
                "quantity": ing.get("minQuantity"),
            })

        results[base_id] = {
            "name_key": unit.get("nameKey"),
            "combat_type": unit.get("combatType"),
            "force_alignment": unit.get("forceAlignment"),
            "recipe_id": recipe_ref,
            "ingredients": ingredients,
        }

    out_path = GAME_DATA_DIR / "unlock_costs.json"
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\nSaved {len(results)} unit unlock costs -> {out_path}")
    print(f"Skipped {skipped_no_recipe} obtainable units with no resolvable creation recipe "
          f"(likely GL-event-specific variants, ship crew, or other special cases — flagged, not silently dropped).")


if __name__ == "__main__":
    main()
