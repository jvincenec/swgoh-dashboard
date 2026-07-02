"""Probe full_data_dump_enums.json structure for zeta/omicron fields."""
import json, pathlib

DUMP = pathlib.Path(__file__).resolve().parent.parent / "game_data" / "full_data_dump_enums.json"
print(f"Loading {DUMP.stat().st_size/1e6:.0f}MB...")
data = json.loads(DUMP.read_text(encoding="utf-8"))

print("\n=== ALL TOP-LEVEL KEYS ===")
print(sorted(data.keys()))

skills = data.get("skill") or []
print(f"\n=== SKILL: {len(skills)} entries ===")
if skills:
    s = skills[0]
    print("First skill keys:", list(s.keys()))
    tiers = s.get("tierList") or s.get("tier") or []
    if tiers:
        print("First tier keys:", list(tiers[0].keys()))
    long_skills = sorted(skills, key=lambda x: len(x.get("tierList") or x.get("tier") or []), reverse=True)[:2]
    for ls in long_skills:
        tl = ls.get("tierList") or ls.get("tier") or []
        print(f"\nSkill {ls.get('id')} tiers:")
        for i, t in enumerate(tl):
            print(f"  [{i}]", t)

recipes = data.get("recipe") or []
print(f"\n=== RECIPE: {len(recipes)} entries ===")
if recipes:
    print("First recipe keys:", list(recipes[0].keys()))
    zr = [r for r in recipes if "ZETA" in str(r.get("id","")).upper()]
    omr = [r for r in recipes if "OMICRON" in str(r.get("id","")).upper()]
    print(f"Zeta recipes: {len(zr)}, Omicron recipes: {len(omr)}")
    if zr: print("Zeta sample:", zr[0])
    if omr: print("Omicron sample:", omr[0])

for k in sorted(data.keys()):
    v = data[k]
    if isinstance(v, list) and v and isinstance(v[0], dict):
        if "omicronMode" in v[0] or any("omicronMode" in x for x in v[:5]):
            print(f"\n=== '{k}' has omicronMode ({len(v)} entries) ===")
            print("Keys:", list(v[0].keys())[:20])
            with_omi = [x for x in v if x.get("omicronMode")]
            print(f"With omicronMode set: {len(with_omi)}")
            if with_omi: print("Sample:", with_omi[0])
