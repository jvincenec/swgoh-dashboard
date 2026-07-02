"""
build_unit_alignment.py — extracts forceAlignment per baseId from the cached
Comlink game data dump, writes game_data/unit_alignment.json.

server.py loads this file for the Balance column (LS chars - DS chars owned).

Run: .\venv\Scripts\python.exe analysis\build_unit_alignment.py
"""

import json
import pathlib
import sys

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
DUMP_PATH = BASE_DIR / "game_data" / "full_data_dump_enums.json"
OUT_PATH  = BASE_DIR / "game_data" / "unit_alignment.json"


def main():
    if not DUMP_PATH.exists():
        print(f"ERROR: {DUMP_PATH} not found.")
        sys.exit(1)

    print(f"Loading {DUMP_PATH.name} ({DUMP_PATH.stat().st_size / 1e6:.0f} MB)...")
    data = json.loads(DUMP_PATH.read_text(encoding="utf-8"))

    units = data.get("units") or data.get("unit") or []
    if not units:
        units = (data.get("data") or {}).get("units") or (data.get("data") or {}).get("unit") or []

    if not units:
        print("ERROR: could not locate units list. Top-level keys:", list(data.keys())[:10])
        sys.exit(1)

    alignment_map = {}
    for u in units:
        base_id = u.get("baseId") or u.get("base_id")
        if not base_id:
            continue
        raw = u.get("forceAlignment", "") or ""
        if "LIGHT" in raw:
            alignment_map[base_id] = "LIGHT"
        elif "DARK" in raw:
            alignment_map[base_id] = "DARK"
        else:
            alignment_map[base_id] = "NEUTRAL"

    OUT_PATH.write_text(json.dumps(alignment_map, indent=2), encoding="utf-8")
    light = sum(1 for v in alignment_map.values() if v == "LIGHT")
    dark  = sum(1 for v in alignment_map.values() if v == "DARK")
    print(f"Saved {len(alignment_map)} units -> {OUT_PATH.name}")
    print(f"  LIGHT: {light}  DARK: {dark}  NEUTRAL: {len(alignment_map)-light-dark}")

    # Also save ship_ids.json — combatType in enums=True dump is a string
    ship_ids = []
    for u in units:
        base_id = u.get("baseId") or u.get("base_id") or ""
        if not base_id:
            continue
        ct = u.get("combatType") or ""
        is_ship = (ct == 2 or (isinstance(ct, str) and "SHIP" in ct.upper()))
        if is_ship:
            ship_ids.append(base_id)
    ship_path = BASE_DIR / "game_data" / "ship_ids.json"
    ship_path.write_text(json.dumps(ship_ids), encoding="utf-8")
    print(f"Saved {len(ship_ids)} ship IDs -> ship_ids.json  sample: {ship_ids[:4]}")


if __name__ == "__main__":
    main()
