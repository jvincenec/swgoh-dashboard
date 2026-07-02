import json, re
from pathlib import Path
DUMP_PATH = Path(__file__).parent.parent / "game_data" / "full_data_dump_enums.json"
data = json.loads(DUMP_PATH.read_text())
units = data.get("units", [])

# Broader, unfiltered search across ALL units for relevant substrings in EITHER field
patterns = ["CX", "SKIFFGUARD", "SKIFF"]
for u in units:
    bid = u.get("baseId", "") or ""
    nk = u.get("nameKey", "") or ""
    if any(p in bid.upper() or p in nk.upper() for p in patterns):
        print(f"baseId={bid!r}  nameKey={nk!r}  obtainable={u.get('obtainable')}")
