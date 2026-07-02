"""
fetch_leaderboards.py - guild GP leaderboard positions via Comlink /getLeaderboard.
Saves data/leaderboards.json. GP rank shows null if guild is outside top 200.
Run: .\venv\Scripts\python.exe fetch_leaderboards.py
"""
import json, time
from pathlib import Path
import requests

COMLINK_URL = "http://localhost:3000"
DATA_DIR    = Path(__file__).parent / "data"
GUILDS_DIR  = DATA_DIR / "guilds"
OUT_PATH    = DATA_DIR / "leaderboards.json"


def comlink_post(endpoint, payload):
    resp = requests.post(f"{COMLINK_URL}{endpoint}",
                         json={"payload": payload, "enums": False}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_guild_ids():
    ids = {}
    for f in sorted(GUILDS_DIR.glob("*.json")):
        try:
            g = json.loads(f.read_text())
            gid  = g.get("id") or g.get("guildId") or (g.get("profile") or {}).get("id") or ""
            name = g.get("name") or (g.get("profile") or {}).get("name") or f.stem
            gp   = g.get("gp") or (g.get("profile") or {}).get("guildGalacticPower") or 0
            if gid:
                ids[gid] = {"name": name, "gp": gp, "slug": f.stem}
        except Exception:
            continue
    return ids


def main():
    guild_ids = get_guild_ids()
    if not guild_ids:
        print("ERROR: no guild files found. Run fetch_guilds.py first.")
        return

    print(f"Fetching GP leaderboard (top 200)...")
    gp_lb = {}
    try:
        result = comlink_post("/getLeaderboard", {
            "leaderboardId": [{"leaderboardType": 3, "defId": ""}],
            "count": 200
        })
        guilds = result.get("guild") or result.get("leaderboard") or []
        for i, g in enumerate(guilds):
            gid = g.get("id") or g.get("guildId") or ""
            if gid:
                gp_lb[gid] = i + 1
        print(f"  Got {len(guilds)} guilds in leaderboard")
    except Exception as e:
        print(f"  Warning: leaderboard fetch failed ({e})")
        print("  Saving with null ranks")

    results = {}
    for gid, meta in guild_ids.items():
        results[gid] = {
            "name":    meta["name"],
            "slug":    meta["slug"],
            "gp":      meta["gp"],
            "gp_rank": gp_lb.get(gid),
        }
        rank_str = f"#{results[gid]['gp_rank']}" if results[gid]["gp_rank"] else "not in top 200"
        print(f"  {meta['name']}: GP rank {rank_str}")

    OUT_PATH.write_text(json.dumps(results, indent=2))
    print(f"Saved -> {OUT_PATH}")


if __name__ == "__main__":
    main()
