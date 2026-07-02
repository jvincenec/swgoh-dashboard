"""
trace_gl_unlock.py — Trace one known Galactic Legend's actual unlock chain
through real Comlink game data, with enums=true so type codes come back
as readable strings instead of opaque integers.

Target: Jedi Master Luke Skywalker GL (base_id GRANDMASTERLUKE) — long-
standing, stable GL, good first trace target.

Does NOT save the full ~700MB dump again — only keeps and prints what's
relevant to this one character, to keep this fast and inspectable.

Usage:
    python analysis/trace_gl_unlock.py
"""

import json
import sys
from pathlib import Path

import requests

COMLINK_URL = "http://localhost:3000"
TARGET_BASE_ID = "GRANDMASTERLUKE"
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
        print(f"Fetching segment {segment} (enums=true) ...")
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

    # 1. Find the unit definition itself
    units = data.get("units", [])
    target_unit = None
    for u in units:
        if u.get("baseId") == TARGET_BASE_ID or u.get("id") == TARGET_BASE_ID:
            target_unit = u
            break

    if target_unit:
        print(f"\n=== Unit definition for {TARGET_BASE_ID} (top-level keys) ===")
        print(list(target_unit.keys()))
        # Print any key whose name hints at unlock/requirement/recipe
        for k, v in target_unit.items():
            if any(term in k.lower() for term in ["unlock", "require", "recipe", "journey"]):
                print(f"\n--- field '{k}' ---")
                print(json.dumps(v, indent=2)[:1500])
    else:
        print(f"\nWARNING: no units entry found with baseId/id == {TARGET_BASE_ID}")

    # 2. Search requirement collection for anything referencing this character
    print(f"\n=== Searching 'requirement' collection for '{TARGET_BASE_ID}' ===")
    matches = [r for r in data.get("requirement", []) if TARGET_BASE_ID in json.dumps(r)]
    print(f"Found {len(matches)} matching requirement entries")
    for m in matches[:5]:
        print(json.dumps(m, indent=2)[:1500])
        print("---")

    # 3. Search recipe collection
    print(f"\n=== Searching 'recipe' collection for '{TARGET_BASE_ID}' ===")
    recipe_matches = [r for r in data.get("recipe", []) if TARGET_BASE_ID in json.dumps(r)]
    print(f"Found {len(recipe_matches)} matching recipe entries")
    for m in recipe_matches[:5]:
        print(json.dumps(m, indent=2)[:1500])
        print("---")

    # 4. Search campaign collection (raw string search, campaign is deeply nested)
    print(f"\n=== Searching 'campaign' collection for '{TARGET_BASE_ID}' ===")
    campaign_str_matches = 0
    for c in data.get("campaign", []):
        if TARGET_BASE_ID in json.dumps(c):
            campaign_str_matches += 1
    print(f"Found {TARGET_BASE_ID} mentioned in {campaign_str_matches} campaign entries")


if __name__ == "__main__":
    main()
