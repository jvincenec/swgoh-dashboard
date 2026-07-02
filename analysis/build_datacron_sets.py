"""build_datacron_sets.py
Extracts datacron set definitions from full_data_dump_enums.json.
Saves game_data/datacron_sets.json.
Run: .\\venv\\Scripts\\python.exe analysis\\build_datacron_sets.py
"""
import json, pathlib, sys

BASE_DIR  = pathlib.Path(__file__).resolve().parent.parent
DUMP_PATH = BASE_DIR / "game_data" / "full_data_dump_enums.json"
LOC_PATH  = BASE_DIR / "game_data" / "localization_en.json"
OUT_PATH  = BASE_DIR / "game_data" / "datacron_sets.json"


def load_loc():
    if not LOC_PATH.exists():
        return {}
    try:
        raw = json.loads(LOC_PATH.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {e.get("key"): e.get("value") for e in raw if isinstance(e, dict) and "key" in e}
    except Exception:
        return {}


def main():
    if not DUMP_PATH.exists():
        print(f"ERROR: {DUMP_PATH} not found."); sys.exit(1)
    loc = load_loc()
    print(f"Loading {DUMP_PATH.name} ({DUMP_PATH.stat().st_size/1e6:.0f} MB)...")
    data = json.loads(DUMP_PATH.read_text(encoding="utf-8"))

    dcs = data.get("datacronSet") or []
    print(f"datacronSet: {len(dcs)} entries")
    if dcs:
        print("Keys:", list(dcs[0].keys()))
        print("Sample:", {k: v for k, v in dcs[0].items() if k not in ("tier",)})

    sets_out = {}
    for s in dcs:
        sid = s.get("id") or ""
        if not sid:
            continue
        name_key = s.get("nameKey") or s.get("displayNameKey") or sid
        name = loc.get(name_key, name_key)
        faction = s.get("requiredCategory") or s.get("targetFaction") or s.get("faction") or ""
        max_level = s.get("maxLevel") or len(s.get("tier") or [])
        sets_out[sid] = {"name": name, "name_key": name_key, "faction": faction, "max_level": max_level, "id": sid}

    OUT_PATH.write_text(json.dumps(sets_out, indent=2), encoding="utf-8")
    print(f"Saved {len(sets_out)} datacron sets -> {OUT_PATH.name}")
    for k, v in list(sets_out.items())[:3]:
        print(f"  {k}: {v['name']}  faction={v['faction']}  max_level={v['max_level']}")


if __name__ == "__main__":
    main()
