"""probe_ability_omicron.py — check ability omicronMode values and JML data.
Run: .\venv\Scripts\python.exe analysis\probe_ability_omicron.py
"""
import json, requests
from pathlib import Path

COMLINK = "http://localhost:3000"
GAME = Path(__file__).parent.parent / "game_data"

# 1. Check omicron_abilities.json
omi_path = GAME / "omicron_abilities.json"
data = json.loads(omi_path.read_text()) if omi_path.exists() else []
print(f"omicron_abilities.json: {len(data)} entries")

# 2. Probe ability collection for omicronMode values
dump = GAME / "full_data_dump_enums.json"
print(f"\nLoading dump ({dump.stat().st_size/1e6:.0f}MB)...")
d = json.loads(dump.read_text())
abilities = d.get("ability") or []
print(f"ability collection: {len(abilities)} entries")
if abilities:
    print("First ability keys:", list(abilities[0].keys())[:10])
    sample_modes = set(a.get("omicronMode","") for a in abilities[:100])
    print("omicronMode sample values:", sample_modes)

# Find abilities with real omicron modes
real_omis = [a for a in abilities if a.get("omicronMode") and
             a.get("omicronMode") not in ("", "ALL_OMICRON", "OMICRON_MODE_NONE", "OMICRON_MODE_UNKNOWN")]
print(f"Abilities with real omicronMode: {len(real_omis)}")
for a in real_omis[:5]:
    print(f"  {a.get('id')}: {a.get('omicronMode')}")

# 3. Check JML ability
jml = next((a for a in abilities if a.get("id") == "ultimateability_grandmasterluke"), None)
print(f"\nultimateability_grandmasterluke: {jml}")

# 4. JML in zeta_map
zeta_map = json.loads((GAME / "zeta_map.json").read_text())
jml_skills = {k:v for k,v in zeta_map.items() if "grandmasterluke" in k.lower()}
print(f"\nJML in zeta_map: {jml_skills}")

# 5. Carovnicek JML unit
print("\nFetching carovnicek JML...")
resp = requests.post(f"{COMLINK}/player",
    json={"payload":{"allyCode":"979789966"},"enums":False}, timeout=30)
for u in resp.json().get("rosterUnit",[]):
    if "GRANDMASTERLUKE" in (u.get("definitionId") or ""):
        print(f"  purchasedAbilityId: {u.get('purchasedAbilityId')}")
        print(f"  skills: {[(s.get('id'),s.get('tier')) for s in (u.get('skill') or [])]}")
        break
