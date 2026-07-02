import json, re
from pathlib import Path
DUMP_PATH = Path(__file__).parent.parent / "game_data" / "full_data_dump_enums.json"
data = json.loads(DUMP_PATH.read_text())
units = data.get("units", [])

targets = ["EZRA", "CX2", "CX-2", "SKIFF", "LANDO", "QUIGON", "QUI-GON", "QUIGONJINN"]
seen = set()
for u in units:
    bid = u.get("baseId", "")
    if any(t.replace("-","") in bid.upper() for t in targets) and bid not in seen:
        seen.add(bid)
        print(f"baseId={bid!r}  nameKey={u.get('nameKey')!r}  obtainable={u.get('obtainable')}")
