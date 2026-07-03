"""
fetch_stats.py — fetches computed character stats via swgoh-stats (port 3223).
Saves data/stats/<ally_code>.json  {base_id: {speed, health, protection, offense, 
physical_damage, special_damage, armor, resistance, crit_chance, crit_damage}}

swgoh-stats API (verified from expressServer.js):
  POST http://localhost:3223/api?flags=withModCalc
  Body: [full /player response]   (array of player objects with rosterUnit[])
  Returns: same array with .stats added to each unit

Run AFTER fetch_guilds.py:
  .\venv\Scripts\python.exe fetch_stats.py
"""
import json, time
from pathlib import Path
import requests

COMLINK_URL    = "http://localhost:3000"
STATS_URL      = "http://localhost:3223"
DATA_DIR       = Path(__file__).parent / "data"
GUILDS_DIR     = DATA_DIR / "guilds"
STATS_DIR      = DATA_DIR / "stats"
ROSTER_PATH    = DATA_DIR / "rosters" / "roster_stats.json"
STATS_DIR.mkdir(parents=True, exist_ok=True)

PACE = 0.5   # seconds between /player fetches

# Confirmed from probe 2026-07-02:
# unit.stats = {"base": {name:val}, "gear": {name:val}, "mods": {name:val}, "growthModifiers": {...}}
# Total stat = base[name] + gear.get(name,0) + mods.get(name,0)
STAT_NAMES = ["Speed", "Health", "Protection", "Physical Damage",
              "Special Damage", "Potency", "Tenacity", "Armor",
              "Resistance", "Physical Critical Chance", "Special Critical Chance",
              "Critical Damage"]


def comlink_post(endpoint, payload):
    r = requests.post(f"{COMLINK_URL}{endpoint}",
                      json={"payload": payload, "enums": False}, timeout=30)
    r.raise_for_status()
    return r.json()


def calc_stats(player_response):
    """POST full /player response to swgoh-stats, returns computed stats."""
    try:
        r = requests.post(
            f"{STATS_URL}/api?flags=withModCalc",
            json=[player_response],
            timeout=60,
        )
        r.raise_for_status()
        result = r.json()
        if not result:
            return {}
        player_with_stats = result[0]
        # Extract compact stats per unit
        out = {}
        for unit in player_with_stats.get("rosterUnit", []):
            base_id = unit.get("definitionId", "").split(":")[0]
            if not base_id:
                continue
            raw_stats = unit.get("stats", {})
            if not raw_stats:
                continue
            base = raw_stats.get("base", {})
            gear = raw_stats.get("gear", {})
            mods = raw_stats.get("mods", {})
            final = {}
            for name in STAT_NAMES:
                total = (base.get(name, 0) or 0) + (gear.get(name, 0) or 0) + (mods.get(name, 0) or 0)
                if total:
                    final[name.lower().replace(" ", "_")] = round(float(total), 1)
            if final.get("speed"):
                out[base_id] = final
        return out
    except Exception as e:
        return {"_error": str(e)}


def get_member_list():
    members = {}
    for f in sorted(GUILDS_DIR.glob("*.json")):
        try:
            g = json.loads(f.read_text())
        except Exception:
            continue
        guild_name = g.get("name", f.stem)
        for m in g.get("members", []):
            ac = m.get("ally_code") or m.get("playerId") or ""
            if ac and ac not in members:
                members[ac] = {"name": m.get("name", "?"), "guild": guild_name}
    return members


def main():
    # Verify swgoh-stats is running
    try:
        requests.get(f"{STATS_URL}/", timeout=5)
        print(f"swgoh-stats OK at {STATS_URL}")
    except Exception:
        print(f"ERROR: swgoh-stats not responding at {STATS_URL}")
        print("Start it: docker start swgoh-stats")
        return

    members = get_member_list()
    if not members:
        print("ERROR: no guild files. Run fetch_guilds.py first.")
        return

    total = len(members)
    print(f"Computing stats for {total} players (~{total * PACE * 2 / 60:.1f} min)...")

    for i, (ac, meta) in enumerate(members.items(), 1):
        out_path = STATS_DIR / f"{ac}.json"
        try:
            player = comlink_post("/player", {"playerId": ac})
            time.sleep(PACE)
            stats = calc_stats(player)
            out_path.write_text(json.dumps(stats))
            speed_chars = sum(1 for v in stats.values() if isinstance(v, dict) and v.get("speed"))
            print(f"  [{i}/{total}] {meta['name']}: {speed_chars} chars with computed speed")
        except Exception as e:
            print(f"  [{i}/{total}] SKIP {meta['name']}: {e}")
        time.sleep(PACE)

    print(f"\nDone. Stats saved to {STATS_DIR}/")


if __name__ == "__main__":
    main()
