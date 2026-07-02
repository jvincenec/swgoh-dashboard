import json
from pathlib import Path
DUMP_PATH = Path(__file__).parent.parent / "game_data" / "full_data_dump_enums.json"
data = json.loads(DUMP_PATH.read_text())
units = data.get("units", [])
for u in units:
    bid = u.get("baseId", "") or ""
    if "OPERATIVE" in bid.upper():
        print(f"baseId={bid!r}  nameKey={u.get('nameKey')!r}  thumbnailName={u.get('thumbnailName')!r}  obtainable={u.get('obtainable')}")
