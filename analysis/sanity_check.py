import json
from pathlib import Path
DUMP_PATH = Path(__file__).parent.parent / "game_data" / "full_data_dump_enums.json"
print(f"File exists: {DUMP_PATH.exists()}")
print(f"File size: {DUMP_PATH.stat().st_size / 1024 / 1024:.1f} MB" if DUMP_PATH.exists() else "N/A")

data = json.loads(DUMP_PATH.read_text())
print(f"Top-level keys: {list(data.keys())[:5]} ... ({len(data.keys())} total)")
units = data.get("units", [])
print(f"Units count: {len(units)}")

# known-good sanity check
known_good = [u for u in units if u.get("baseId") == "AAYLASECURA"]
print(f"AAYLASECURA found: {len(known_good)}")

# now check CX2 specifically
cx2 = [u for u in units if u.get("baseId") == "CX2"]
print(f"CX2 found: {len(cx2)}")
if cx2:
    print(cx2[0])

# print first 3 raw entries fully to see actual field types
print("\nFirst unit entry, all keys and types:")
if units:
    for k, v in units[0].items():
        print(f"  {k}: {type(v).__name__} = {repr(v)[:80]}")
