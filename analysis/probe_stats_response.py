"""probe_stats_response.py - verify actual swgoh-stats response format.
Run: .\venv\Scripts\python.exe analysis\probe_stats_response.py
"""
import json, requests

COMLINK = "http://localhost:3000"
STATS   = "http://localhost:3223"
ALLY    = "979789966"

print("Fetching player from Comlink...")
resp = requests.post(f"{COMLINK}/player",
    json={"payload":{"allyCode": ALLY},"enums":False}, timeout=30)
player = resp.json()
print(f"rosterUnit count: {len(player.get('rosterUnit',[]))}")

print("POSTing to swgoh-stats /api?flags=withModCalc ...")
r = requests.post(f"{STATS}/api?flags=withModCalc",
    json=[player], timeout=120)
print(f"HTTP status: {r.status_code}")
result = r.json()

print(f"Response: type={type(result).__name__} len={len(result) if isinstance(result,list) else 'n/a'}")
if isinstance(result, list) and result:
    p = result[0]
    print(f"Player top-level keys: {sorted(p.keys())}")
    units = p.get("rosterUnit", [])
    print(f"Units in response: {len(units)}")
    if units:
        u = units[0]
        print(f"\nFirst unit definitionId: {u.get('definitionId','?')}")
        print(f"Unit keys: {sorted(u.keys())}")
        stats = u.get("stats")
        print(f"unit.stats type: {type(stats).__name__}")
        if isinstance(stats, dict):
            print(f"stats keys count: {len(stats)}")
            print(f"First 5 stats: {dict(list(stats.items())[:5])}")
            # Check if speed (key 5) is present
            for k in ["5","5.0",5,"speed","Speed"]:
                if k in stats:
                    print(f"Speed found at key {repr(k)}: {stats[k]}")
        elif stats is None:
            print("stats is None - checking unit for stat-like keys:")
            for k in u.keys():
                if "stat" in k.lower() or "speed" in k.lower():
                    print(f"  {k}: {str(u[k])[:100]}")
elif isinstance(result, dict):
    print("Response is dict, keys:", sorted(result.keys())[:10])
    print("Sample:", str(result)[:300])
