"""
build_zeta_map.py — builds game_data/zeta_map.json
Confirmed field names from probe_game_data.py 2026-07-01:
  skill.tier[]  (NOT tierList), tier.isZetaTier, tier.isOmicronTier
  skill.isZeta (top-level bool), skill.omicronMode
  Player-tier offset: player.skill.tier + 2 == in-game tier index (1-based)

Run: .\venv\Scripts\python.exe analysis\build_zeta_map.py
"""
import json, pathlib, sys

BASE_DIR  = pathlib.Path(__file__).resolve().parent.parent
DUMP_PATH = BASE_DIR / "game_data" / "full_data_dump_enums.json"
LOC_PATH  = BASE_DIR / "game_data" / "localization_en.json"
OUT_PATH  = BASE_DIR / "game_data" / "zeta_map.json"

OMICRON_MODE_MAP = {
    "OMICRON_MODE_GRAND_ARENA":      "GAC",
    "OMICRON_MODE_GRAND_ARENA_3V3":  "GAC 3v3",
    "OMICRON_MODE_GRAND_ARENA_5V5":  "GAC 5v5",
    "OMICRON_MODE_TERRITORY_WAR":    "TW",
    "OMICRON_MODE_TERRITORY_BATTLE": "TB",
    "OMICRON_MODE_RAID":             "Raid",
    "OMICRON_MODE_CONQUEST":         "CQ",
    "ALL_OMICRON": None, "OMICRON_MODE_NONE": None, "OMICRON_MODE_UNKNOWN": None,
}


def main():
    if not DUMP_PATH.exists():
        print(f"ERROR: {DUMP_PATH} not found."); sys.exit(1)

    loc = {}
    if LOC_PATH.exists():
        try:
            raw = json.loads(LOC_PATH.read_text(encoding="utf-8"))
            loc = raw if isinstance(raw, dict) else {e.get("key"): e.get("value") for e in raw if isinstance(e, dict) and "key" in e}
            print(f"Localization loaded: {len(loc)} strings")
        except Exception as ex:
            print(f"Warning: could not load localization ({ex})")

    print(f"Loading {DUMP_PATH.name} ({DUMP_PATH.stat().st_size/1e6:.0f} MB)...")
    data = json.loads(DUMP_PATH.read_text(encoding="utf-8"))

    skill_to_unit = {}
    for u in (data.get("units") or []):
        base_id = u.get("baseId") or ""
        for sd in (u.get("skillData") or []):
            sid = sd.get("id") or ""
            if sid:
                skill_to_unit[sid] = base_id

    # Build omicron_abilities.json: maps ability_id -> mode
    # Source: skill.abilityReference (matches purchasedAbilityId) + skill.omicronMode
    # Probe confirmed: ability collection has NO omicronMode field; skill collection does.
    # Also: ANY non-empty purchasedAbilityId entry is an omicron — use that as fallback.
    omi_map = {}  # ability_id -> mode string
    for sk in (data.get("skill") or []):
        raw_mode = sk.get("omicronMode") or ""
        if not raw_mode or raw_mode in ("ALL_OMICRON", "OMICRON_MODE_NONE",
                                         "OMICRON_MODE_UNKNOWN", ""):
            continue
        mode = OMICRON_MODE_MAP.get(raw_mode)
        ability_ref = sk.get("abilityReference") or ""
        if ability_ref and mode is not None:
            omi_map[ability_ref] = mode
    omi_path = BASE_DIR / "game_data" / "omicron_abilities.json"
    omi_path.write_text(json.dumps(omi_map, indent=2), encoding="utf-8")
    print(f"Saved {len(omi_map)} omicron ability mappings -> omicron_abilities.json")
    if omi_map:
        print(f"  Sample: {list(omi_map.items())[:3]}")
    else:
        print("  WARNING: 0 entries — purchasedAbilityId will use 'Unknown' mode")

    skills = data.get("skill") or []
    print(f"Skills in dump: {len(skills)}")

    zeta_map = {}
    for sk in skills:
        sk_id = sk.get("id") or ""
        if not sk_id:
            continue
        is_zeta_skill, is_omicron_skill = bool(sk.get("isZeta")), False
        raw_mode = sk.get("omicronMode") or ""
        omicron_mode = OMICRON_MODE_MAP.get(raw_mode)
        zeta_player_tier = omicron_player_tier = None

        for idx, t in enumerate(sk.get("tier") or []):
            if t.get("isZetaTier"):
                is_zeta_skill = True
                zeta_player_tier = max(0, idx - 1)
            if t.get("isOmicronTier"):
                is_omicron_skill = True
                omicron_player_tier = max(0, idx - 1)

        if not is_zeta_skill and not is_omicron_skill:
            continue

        name_key = sk.get("nameKey") or sk_id
        zeta_map[sk_id] = {
            "name":               loc.get(name_key, name_key),
            "name_key":           name_key,
            "ability_ref":        sk.get("abilityReference") or "",
            "unit_base_id":       skill_to_unit.get(sk_id, ""),
            "is_zeta":            is_zeta_skill,
            "is_omicron":         is_omicron_skill,
            "zeta_player_tier":   zeta_player_tier,
            "omicron_player_tier":omicron_player_tier,
            "omicron_mode":       omicron_mode,
        }

    OUT_PATH.write_text(json.dumps(zeta_map, indent=2), encoding="utf-8")
    zetas    = sum(1 for v in zeta_map.values() if v["is_zeta"] and not v["is_omicron"])
    omicrons = sum(1 for v in zeta_map.values() if v["is_omicron"])
    print(f"Saved {len(zeta_map)} entries -> {OUT_PATH.name}  (zetas:{zetas} omicrons:{omicrons})")
    for k, v in list(zeta_map.items())[:3]:
        print(f"  {k}: zeta_pt={v['zeta_player_tier']} omicron_pt={v['omicron_player_tier']} name={v['name'][:50]}")


if __name__ == "__main__":
    main()
