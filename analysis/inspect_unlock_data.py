"""
inspect_unlock_data.py — ONE-TIME diagnostic, v2.

v1 omitted the "items" bitmask assuming that meant "return everything" —
wrong: Comlink treats a missing/zero items bitmask as "return nothing",
which is why every collection came back empty. There's no verified table
for which bit corresponds to recipe/requirement/unlockAnnouncementDefinition,
and guessing it would repeat the same mistake already made twice this
session on the zeta field and the /player payload key.

Instead: use requestSegment pagination, which the Comlink wiki documents
as the mechanism for pulling the FULL dataset without an items bitmask at
all (used when responses are too large for one request). This requires no
guessing — just iterate segments until they stop returning new data.

Usage:
    python analysis/inspect_unlock_data.py
"""

import json
import sys
from pathlib import Path

import requests

COMLINK_URL = "http://localhost:3000"
GAME_DATA_DIR = Path(__file__).parent.parent / "game_data"
GAME_DATA_DIR.mkdir(exist_ok=True)

MAX_SEGMENTS = 30  # safety cap


def comlink_post(endpoint: str, payload: dict, timeout=300) -> dict:
    resp = requests.post(
        f"{COMLINK_URL}{endpoint}",
        json={"payload": payload, "enums": False},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()


def main():
    print("Fetching /metadata for latest game data version ...")
    meta = comlink_post("/metadata", {})
    version = meta.get("latestGamedataVersion")
    if not version:
        print("ERROR: no latestGamedataVersion in /metadata response.")
        sys.exit(1)
    print(f"  Version: {version}")

    merged = {}
    prev_total_entries = -1

    for segment in range(MAX_SEGMENTS):
        print(f"\nFetching /data requestSegment={segment} ...")
        data = comlink_post(
            "/data",
            {"version": version, "includePveUnits": False, "requestSegment": segment},
            timeout=600,
        )

        total_entries_this_segment = sum(
            len(v) for v in data.values() if isinstance(v, list)
        )
        print(f"  Segment {segment}: {total_entries_this_segment} total list entries across {len(data)} keys")

        if total_entries_this_segment == 0 and segment > 0:
            print(f"  Segment {segment} empty — stopping (assuming {segment} segments total).")
            break

        for k, v in data.items():
            if isinstance(v, list):
                merged.setdefault(k, [])
                merged[k].extend(v)
            elif k not in merged:
                merged[k] = v

        new_total = sum(len(v) for v in merged.values() if isinstance(v, list))
        if new_total == prev_total_entries:
            print("  No growth from previous segment — stopping.")
            break
        prev_total_entries = new_total

    print(f"\nMerged collections ({len(merged)} total):")
    for k in sorted(merged.keys()):
        size = len(merged[k]) if isinstance(merged[k], list) else "n/a"
        print(f"  - {k}  (entries: {size})")

    out_path = GAME_DATA_DIR / "full_data_dump.json"
    out_path.write_text(json.dumps(merged))
    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"\nSaved merged dump -> {out_path} ({size_mb:.1f} MB)")

    interesting = [k for k in merged.keys() if any(
        term in k.lower() for term in ["unlock", "recipe", "requirement", "journey", "campaign"]
    )]
    print(f"\nUnlock/recipe/requirement/journey/campaign-related keys: {interesting}")
    for k in interesting:
        items = merged[k]
        print(f"\n--- '{k}': {len(items) if isinstance(items, list) else 'n/a'} entries ---")
        if isinstance(items, list) and items:
            print(json.dumps(items[0], indent=2)[:2000])
        else:
            print("  (empty)")


if __name__ == "__main__":
    main()
