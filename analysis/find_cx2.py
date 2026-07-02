import json
from pathlib import Path
DUMP_PATH = Path(__file__).parent.parent / "game_data" / "full_data_dump_enums.json"
data = json.loads(DUMP_PATH.read_text())
units = data.get("units", [])

# Search nameKey for anything containing "CX" as a standalone-ish token,
# and also search descKey/thumbnailName as backup signals
for u in units:
    bid = u.get("baseId", "") or ""
    nk = u.get("nameKey", "") or ""
    thumb = u.get("thumbnailName", "") or ""
    if "CX" in bid.upper() or "CX" in nk.upper() or "cx" in thumb.lower():
        print(f"baseId={bid!r}  nameKey={nk!r}  thumbnailName={thumb!r}  obtainable={u.get('obtainable')}")
