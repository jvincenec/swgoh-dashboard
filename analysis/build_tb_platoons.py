"""
build_tb_platoons.py — extracts Territory Battle platoon requirements from game data dump.
Saves game_data/tb_platoons.json used by the /guild/<slug>/tb-platoons page.

Run: .\venv\Scripts\python.exe analysis\build_tb_platoons.py
"""
import json, pathlib, sys

BASE_DIR  = pathlib.Path(__file__).resolve().parent.parent
DUMP_PATH = BASE_DIR / "game_data" / "full_data_dump_enums.json"
LOC_PATH  = BASE_DIR / "game_data" / "localization_en.json"
OUT_PATH  = BASE_DIR / "game_data" / "tb_platoons.json"

# Known TB identifiers from community knowledge
TB_DEFS = {
    "TERRITORY_BATTLE_GEONOSISLIGHT":  "LS Geo TB",
    "TERRITORY_BATTLE_GEONOSISDARK":   "DS Geo TB",
    "TERRITORY_BATTLE_RAITH":          "Coruscant Undercity TB",
}


def main():
    if not DUMP_PATH.exists():
        print(f"ERROR: {DUMP_PATH} not found."); sys.exit(1)

    loc = {}
    if LOC_PATH.exists():
        try:
            raw = json.loads(LOC_PATH.read_text(encoding="utf-8"))
            loc = raw if isinstance(raw, dict) else {e["key"]: e["value"] for e in raw if isinstance(e, dict) and "key" in e}
        except Exception:
            pass

    print(f"Loading {DUMP_PATH.name} ({DUMP_PATH.stat().st_size/1e6:.0f}MB)...")
    data = json.loads(DUMP_PATH.read_text(encoding="utf-8"))

    # Print top-level keys to understand structure
    all_keys = sorted(data.keys())
    tb_keys = [k for k in all_keys if "territory" in k.lower() or "battle" in k.lower() or "platoon" in k.lower()]
    print(f"TB-related keys in dump: {tb_keys}")

    # Try to extract platoon data
    tb_out = {}

    for tb_key in ["territoryBattle", "territoryBattleDefinition", "platoonDefinition"]:
        tb_data = data.get(tb_key) or []
        if tb_data:
            print(f"Found {tb_key}: {len(tb_data)} entries")
            print(f"  Sample keys: {list(tb_data[0].keys())[:10] if tb_data else []}")

            for tb in tb_data:
                tb_id = tb.get("id") or tb.get("definitionId") or ""
                if not tb_id:
                    continue
                name = loc.get(tb.get("nameKey", ""), tb_id)
                phases = []
                for phase in (tb.get("phase") or tb.get("phaseList") or []):
                    platoons = []
                    for pl in (phase.get("platoon") or phase.get("platoonList") or []):
                        units = []
                        for squad in (pl.get("squadList") or pl.get("squad") or []):
                            for u in (squad.get("unitList") or squad.get("unit") or []):
                                uid = u.get("baseId") or u.get("unitId") or u.get("id") or ""
                                if uid:
                                    units.append(uid)
                        if units:
                            platoons.append({
                                "id": pl.get("id", ""),
                                "units": units,
                            })
                    if platoons:
                        phases.append({
                            "id": phase.get("id", ""),
                            "platoons": platoons,
                        })
                if phases:
                    tb_out[tb_id] = {"name": name, "id": tb_id, "phases": phases}

    OUT_PATH.write_text(json.dumps(tb_out, indent=2), encoding="utf-8")
    print(f"Saved {len(tb_out)} TB definitions -> {OUT_PATH.name}")
    if not tb_out:
        print("NOTE: No platoon data found. TB platoon tool will show empty.")
        print("Available keys:", all_keys[:20])


if __name__ == "__main__":
    main()
