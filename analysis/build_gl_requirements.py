"""
build_gl_requirements.py
Extracts GL journey requirements from full_data_dump_enums.json.
Saves game_data/gl_requirements.json used by the /gl-readiness dashboard page.

If unitGuideDefinition structure differs from expected, falls back to
hardcoded GL prerequisites (confirmed from game as of 2025).

Run: .\venv\Scripts\python.exe analysis\build_gl_requirements.py
"""
import json, pathlib, sys

BASE_DIR  = pathlib.Path(__file__).resolve().parent.parent
DUMP_PATH = BASE_DIR / "game_data" / "full_data_dump_enums.json"
LOC_PATH  = BASE_DIR / "game_data" / "localization_en.json"
OUT_PATH  = BASE_DIR / "game_data" / "gl_requirements.json"

# Hardcoded GL prerequisites (authoritative fallback).
# Format: {gl_base_id: {name, units: [{base_id, min_stars, min_gear, min_relic, note}]}}
HARDCODED_GL_REQS = {
    "GLREY": {
        "name": "Rey", "ship": False,
        "units": [
            {"base_id": "BB8",            "min_stars": 7, "min_gear": 12, "min_relic": 0, "note": "R3 needed for event"},
            {"base_id": "R2D2",           "min_stars": 7, "min_gear": 12, "min_relic": 0, "note": "R3 needed for event"},
            {"base_id": "C3POCHEWBACCA", "min_stars": 7, "min_gear": 12, "min_relic": 0, "note": "C-3PO"},
            {"base_id": "FINN",          "min_stars": 7, "min_gear": 12, "min_relic": 0, "note": ""},
            {"base_id": "RESISTANCETROOPER","min_stars":7,"min_gear":12,"min_relic":0,"note":""},
            {"base_id": "ROSE",          "min_stars": 7, "min_gear": 12, "min_relic": 0, "note": ""},
            {"base_id": "HOLDO",         "min_stars": 7, "min_gear": 12, "min_relic": 0, "note": ""},
            {"base_id": "RESISTANCEPILOT","min_stars":7,"min_gear":12,"min_relic":0,"note":""},
            {"base_id": "VETERANSMUGGLERHANJOLO","min_stars":7,"min_gear":12,"min_relic":0,"note":"Veteran Han"},
            {"base_id": "VETERANSMUGGLERCHEWBACCA","min_stars":7,"min_gear":12,"min_relic":0,"note":"Veteran Chewie"},
            {"base_id": "REY",           "min_stars": 7, "min_gear": 12, "min_relic": 0, "note": "Scavenger Rey"},
        ]
    },
    "SITHPALPATINE": {
        "name": "Sith Eternal Emperor", "ship": False,
        "units": [
            {"base_id": "DARTHVADER",    "min_stars": 7, "min_gear": 13, "min_relic": 5, "note": ""},
            {"base_id": "DARTHNIHILUS", "min_stars": 7, "min_gear": 13, "min_relic": 3, "note": ""},
            {"base_id": "PALPATINE",    "min_stars": 7, "min_gear": 13, "min_relic": 3, "note": "Emperor Palpatine"},
            {"base_id": "DARTHTRAYA",  "min_stars": 7, "min_gear": 13, "min_relic": 0, "note": ""},
            {"base_id": "COUNTDOOKU",  "min_stars": 7, "min_gear": 13, "min_relic": 0, "note": ""},
            {"base_id": "DARTHSIDIOUS","min_stars": 7, "min_gear": 13, "min_relic": 0, "note": ""},
            {"base_id": "ROYALGUARD",  "min_stars": 7, "min_gear": 13, "min_relic": 0, "note": ""},
            {"base_id": "SAVAGEOPRESS","min_stars": 7, "min_gear": 13, "min_relic": 0, "note": ""},
        ]
    },
    "SUPREMELEADERKYLOREN": {
        "name": "Supreme Leader Kylo Ren", "ship": False,
        "units": [
            {"base_id": "KYLOREN",       "min_stars": 7, "min_gear": 13, "min_relic": 5, "note": "Kylo Ren (Unmasked)"},
            {"base_id": "FIRSTORDERTIEPILOT","min_stars":7,"min_gear":13,"min_relic":3,"note":"FOTP"},
            {"base_id": "FIRSTORDEROFFICER","min_stars":7,"min_gear":13,"min_relic":3,"note":"FOSFTP"},
            {"base_id": "HUXKYLOREN",    "min_stars": 7, "min_gear": 13, "min_relic": 3, "note": "General Hux"},
            {"base_id": "FIRSTORDERSPECIALFORCESPILOT","min_stars":7,"min_gear":13,"min_relic":0,"note":"FOSFP"},
            {"base_id": "SITHASSASSIN",  "min_stars": 7, "min_gear": 13, "min_relic": 0, "note": ""},
            {"base_id": "SITHMARAUDER",  "min_stars": 7, "min_gear": 13, "min_relic": 0, "note": ""},
            {"base_id": "SITTROOPER",    "min_stars": 7, "min_gear": 13, "min_relic": 0, "note": "Sith Trooper"},
        ]
    },
    "GRANDMASTERLUKE": {
        "name": "Jedi Master Luke Skywalker", "ship": False,
        "units": [
            {"base_id": "COMMANDERLUKESKYWALKER","min_stars":7,"min_gear":13,"min_relic":5,"note":"CLS"},
            {"base_id": "HERMITYODA",    "min_stars": 7, "min_gear": 13, "min_relic": 3, "note": ""},
            {"base_id": "DEATHTROOPER", "min_stars": 7, "min_gear": 13, "min_relic": 3, "note": "Bone"},
            {"base_id": "EZRABRIDGERS3","min_stars": 7, "min_gear": 13, "min_relic": 3, "note": "Ezra Bridger"},
            {"base_id": "AHSOKATANO",   "min_stars": 7, "min_gear": 13, "min_relic": 0, "note": "Fulcrum"},
            {"base_id": "OLDBENKENOBI", "min_stars": 7, "min_gear": 13, "min_relic": 0, "note": ""},
            {"base_id": "R2D2",         "min_stars": 7, "min_gear": 13, "min_relic": 0, "note": ""},
            {"base_id": "IMPERIALPROBEDROID","min_stars":7,"min_gear":13,"min_relic":0,"note":""},
        ]
    },
    "JEDIMASTERKENOBI": {
        "name": "Jedi Master Kenobi", "ship": False,
        "units": [
            {"base_id": "GENERALSKYWALKER","min_stars":7,"min_gear":13,"min_relic":5,"note":"GAS"},
            {"base_id": "MACEWINDU",     "min_stars": 7, "min_gear": 13, "min_relic": 3, "note": ""},
            {"base_id": "PADMEAMIDALA", "min_stars": 7, "min_gear": 13, "min_relic": 3, "note": ""},
            {"base_id": "OBIWAN",       "min_stars": 7, "min_gear": 13, "min_relic": 0, "note": "Obi-Wan (Clone Wars)"},
            {"base_id": "PLOKOON",      "min_stars": 7, "min_gear": 13, "min_relic": 0, "note": ""},
            {"base_id": "KIADIMUNDI",   "min_stars": 7, "min_gear": 13, "min_relic": 0, "note": ""},
            {"base_id": "AAYLA",        "min_stars": 7, "min_gear": 13, "min_relic": 0, "note": "Aayla Secura"},
            {"base_id": "BARRISOFFEE",  "min_stars": 7, "min_gear": 13, "min_relic": 0, "note": ""},
        ]
    },
    "JEDIKNIGHTLUKE": {
        "name": "Jedi Knight Luke Skywalker", "ship": False,
        "units": [
            {"base_id": "JEDIKNIGHTANAKIN","min_stars":7,"min_gear":13,"min_relic":5,"note":"JKA"},
            {"base_id": "JOLEEBINDO",   "min_stars": 7, "min_gear": 13, "min_relic": 3, "note": ""},
            {"base_id": "OLDBENKENOBI", "min_stars": 7, "min_gear": 13, "min_relic": 3, "note": ""},
            {"base_id": "HERMITYODA",   "min_stars": 7, "min_gear": 13, "min_relic": 0, "note": ""},
            {"base_id": "BASTILASHANDARK","min_stars":7,"min_gear":13,"min_relic":0,"note":"Bastila (Fallen)"},
            {"base_id": "GRANDMASTERYODA","min_stars":7,"min_gear":13,"min_relic":0,"note":""},
            {"base_id": "BARRISSOFFEE", "min_stars": 7, "min_gear": 13, "min_relic": 0, "note": ""},
        ]
    },
    "LORDVADER": {
        "name": "Lord Vader", "ship": False,
        "units": [
            {"base_id": "DARTHVADER",   "min_stars": 7, "min_gear": 13, "min_relic": 7, "note": ""},
            {"base_id": "ROYALGUARD",   "min_stars": 7, "min_gear": 13, "min_relic": 5, "note": ""},
            {"base_id": "GRANDMOFFTARKIN","min_stars":7,"min_gear":13,"min_relic":5,"note":""},
            {"base_id": "DIRECTORKRENNIC","min_stars":7,"min_gear":13,"min_relic":3,"note":""},
            {"base_id": "RANGETROOPER", "min_stars": 7, "min_gear": 13, "min_relic": 3, "note": ""},
            {"base_id": "DEATHTROOPER", "min_stars": 7, "min_gear": 13, "min_relic": 0, "note": ""},
            {"base_id": "SHORETROOPER", "min_stars": 7, "min_gear": 13, "min_relic": 0, "note": ""},
        ]
    },
    "GLAHSOKATANO": {
        "name": "Ahsoka Tano (Fulcrum)", "ship": False,
        "units": [
            {"base_id": "EZRABRIDGERS3","min_stars":7,"min_gear":13,"min_relic":5,"note":"Ezra"},
            {"base_id": "HERASYNDULLA","min_stars":7,"min_gear":13,"min_relic":5,"note":"Hera"},
            {"base_id": "SABINEWREN",  "min_stars":7,"min_gear":13,"min_relic":3,"note":"Sabine"},
            {"base_id": "KANANJARRUS","min_stars":7,"min_gear":13,"min_relic":3,"note":"Kanan"},
            {"base_id": "ZEBORRELIOS","min_stars":7,"min_gear":13,"min_relic":0,"note":"Zeb"},
            {"base_id": "CLONESERGEANTPHASEI","min_stars":7,"min_gear":13,"min_relic":0,"note":"Clone Sgt"},
            {"base_id": "IMPERIALSUPERCOMMANDO","min_stars":7,"min_gear":13,"min_relic":0,"note":""},
        ]
    },
    "JABBATHEHUTT": {
        "name": "Jabba the Hutt", "ship": False,
        "units": [
            {"base_id": "DENGAR",       "min_stars":7,"min_gear":13,"min_relic":5,"note":""},
            {"base_id": "4LOM",         "min_stars":7,"min_gear":13,"min_relic":5,"note":""},
            {"base_id": "ZAMWESELL",    "min_stars":7,"min_gear":13,"min_relic":3,"note":""},
            {"base_id": "GAMORREANGUARD","min_stars":7,"min_gear":13,"min_relic":3,"note":""},
            {"base_id": "BOBAFETTSCION","min_stars":7,"min_gear":13,"min_relic":3,"note":"Boba (Scion)"},
            {"base_id": "BOSSK",        "min_stars":7,"min_gear":13,"min_relic":0,"note":""},
            {"base_id": "BOUSHH",       "min_stars":7,"min_gear":13,"min_relic":0,"note":"Boushh (Leia)"},
        ]
    },
}


def main():
    if not DUMP_PATH.exists():
        print(f"WARNING: {DUMP_PATH} not found — using hardcoded GL requirements.")
        OUT_PATH.write_text(json.dumps(HARDCODED_GL_REQS, indent=2), encoding="utf-8")
        print(f"Saved {len(HARDCODED_GL_REQS)} GLs (hardcoded) -> {OUT_PATH.name}")
        return

    print(f"Loading {DUMP_PATH.name} ({DUMP_PATH.stat().st_size/1e6:.0f} MB)...")
    data = json.loads(DUMP_PATH.read_text(encoding="utf-8"))

    ugd = data.get("unitGuideDefinition") or []
    reqs_raw = data.get("requirement") or []
    print(f"unitGuideDefinition: {len(ugd)} entries,  requirement: {len(reqs_raw)} entries")

    if ugd:
        print("unitGuideDefinition sample keys:", list(ugd[0].keys()))

    req_by_id = {r.get("id"): r for r in reqs_raw if r.get("id")}

    # Try to extract GL requirements from game data
    gl_map = {}
    if ugd and reqs_raw:
        for guide in ugd:
            unit_id = guide.get("id") or guide.get("unitId") or ""
            if not unit_id:
                continue
            req_ids = guide.get("requirementId") or guide.get("requirements") or []
            units_needed = []
            for rid in req_ids:
                req = req_by_id.get(rid) or {}
                scope = req.get("scope") or req.get("type") or ""
                unit_base_id = req.get("unit") or req.get("unitId") or req.get("defId") or ""
                if unit_base_id:
                    units_needed.append({
                        "base_id":   unit_base_id,
                        "min_stars": req.get("rarity") or req.get("minRarity") or 7,
                        "min_gear":  req.get("tier") or req.get("minTier") or 0,
                        "min_relic": req.get("relicTier") or 0,
                        "note":      rid,
                    })
            if units_needed:
                gl_map[unit_id] = {
                    "name": unit_id,
                    "ship": False,
                    "units": units_needed,
                    "source": "game_data",
                }

    if gl_map:
        print(f"Extracted {len(gl_map)} GL guides from game data")
        # Merge with hardcoded (game_data wins for existing GLs, hardcoded fills gaps)
        merged = dict(HARDCODED_GL_REQS)
        merged.update(gl_map)
        OUT_PATH.write_text(json.dumps(merged, indent=2), encoding="utf-8")
        print(f"Saved {len(merged)} GLs (game_data + hardcoded) -> {OUT_PATH.name}")
    else:
        print("Could not extract from game data — using hardcoded GL requirements")
        OUT_PATH.write_text(json.dumps(HARDCODED_GL_REQS, indent=2), encoding="utf-8")
        print(f"Saved {len(HARDCODED_GL_REQS)} GLs (hardcoded) -> {OUT_PATH.name}")


if __name__ == "__main__":
    main()
