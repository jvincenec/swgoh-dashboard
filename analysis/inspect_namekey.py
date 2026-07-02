"""inspect_namekey.py — print real nameKey values for a few known units,
no guessing this time."""
import json
from pathlib import Path

DUMP_PATH = Path(__file__).parent.parent / "game_data" / "full_data_dump_enums.json"
data = json.loads(DUMP_PATH.read_text())
units = data.get("units", [])
print(f"Total units in cache: {len(units)}")

targets = ["GRANDMASTERLUKE", "AAYLASECURA", "JEDIKNIGHTREVAN", "EZRABRIDGEREXILE", "AHSOKATANO"]
for u in units:
    bid = u.get("baseId")
    if bid in targets or any(t in (bid or "") for t in targets):
        print(f"baseId={bid!r}  nameKey={u.get('nameKey')!r}  obtainable={u.get('obtainable')}")

print("\nFirst 10 units regardless of match, raw baseId+nameKey:")
for u in units[:10]:
    print(f"  baseId={u.get('baseId')!r}  nameKey={u.get('nameKey')!r}")
