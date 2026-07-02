"""probe_player_fields.py — inspect Comlink /player for combatType and purchasedAbilityId.
Run: .\venv\Scripts\python.exe analysis\probe_player_fields.py
"""
import json, requests
COMLINK_URL = "http://localhost:3000"
ALLY_CODE   = "979789966"   # carovnicek

resp = requests.post(f"{COMLINK_URL}/player",
    json={"payload": {"allyCode": ALLY_CODE}, "enums": False}, timeout=30)
resp.raise_for_status()
player = resp.json()

print("=== PLAYER-LEVEL KEYS ===")
print(sorted(player.keys()))
print("\n=== purchasedAbilityId at PLAYER level ===")
print(player.get("purchasedAbilityId"))

roster = player.get("rosterUnit", [])
print(f"\n=== ROSTER: {len(roster)} units ===")
for u in roster[:3]:
    print(f"\n  {u.get('definitionId','?')}")
    print(f"  keys: {sorted(u.keys())}")
    print(f"  combatType: {u.get('combatType')}")
    print(f"  purchasedAbilityId: {u.get('purchasedAbilityId')}")

chars  = [u for u in roster if "relic" in u]
ships  = [u for u in roster if "relic" not in u]
print(f"\nWith 'relic' key: {len(chars)}   Without 'relic' key: {len(ships)}")
if ships:
    print("Ship sample keys:", sorted(ships[0].keys()))

with_omi = [u for u in roster if u.get("purchasedAbilityId")]
print(f"\nUnits with purchasedAbilityId set: {len(with_omi)}")
for u in with_omi[:5]:
    print(f"  {u.get('definitionId')}: {u.get('purchasedAbilityId')}")
