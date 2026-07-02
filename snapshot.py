"""
snapshot.py — Run AFTER fetch_guilds.py.
Appends one history entry per guild to data/history/log.json (GP delta,
member changes, transfers). Also creates compact per-run stat snapshots
in data/history/player_stats/<timestamp>.json for trend charts.
These snapshots are small (~50-100KB each) and accumulate over time.

Run: .\venv\Scripts\python.exe snapshot.py
"""

import json
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR     = Path(__file__).parent
DATA_DIR     = BASE_DIR / "data"
GUILDS_DIR   = DATA_DIR / "guilds"
HISTORY_DIR  = DATA_DIR / "history"
HISTORY_DIR.mkdir(parents=True, exist_ok=True)
STATS_DIR    = HISTORY_DIR / "player_stats"
STATS_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH       = HISTORY_DIR / "log.json"
TRANSFERS_PATH = HISTORY_DIR / "transfers.json"
ROSTER_PATH    = DATA_DIR / "rosters" / "roster_stats.json"

# The 9 GL base_ids used for GL-count metric
GL_BASE_IDS = {
    "GLREY", "SITHPALPATINE", "SUPREMELEADERKYLOREN", "GRANDMASTERLUKE",
    "JEDIMASTERKENOBI", "JEDIKNIGHTLUKE", "LORDVADER", "GLAHSOKATANO", "JABBATHEHUTT",
}

NAMED_TOON_IDS = {
    "JKR": "JEDIKNIGHTREVAN", "DR": "DARTHREVAN", "Malak": "DARTHMALAK",
    "GAS": "GENERALSKYWALKER", "JML": "GRANDMASTERLUKE", "JMK": "JEDIMASTERKENOBI",
    "JKL": "JEDIKNIGHTLUKE", "LV": "LORDVADER", "Rey": "GLREY",
    "SEE": "SITHPALPATINE", "SLK": "SUPREMELEADERKYLOREN", "Ahsoka": "GLAHSOKATANO",
    "Jabba": "JABBATHEHUTT", "Neg": "NEGOTIATOR", "Mal": "MALEVOLENCE",
    "Exec": "CAPITALEXECUTOR", "Chimaera": "CAPITALCHIMAERA",
}


def load_json_list(path):
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return []


def load_roster_stats():
    if not ROSTER_PATH.exists():
        return {}
    try:
        return json.loads(ROSTER_PATH.read_text())
    except Exception:
        return {}


def compute_player_metrics(rs, chars_gp=None):
    """Compact metrics for one player from their roster_stats entry."""
    units = rs.get("units") or {}
    spd   = rs.get("speed_secondary_count") or 0
    cgp   = chars_gp or 1
    mod_score = round(spd / cgp * 100_000, 3) if cgp else 0.0
    gl_count  = sum(1 for bid in units if bid in GL_BASE_IDS)
    return {
        "name":          rs.get("name", "?"),
        "guild":         rs.get("guild_name", "?"),
        "gp":            rs.get("gp", 0),
        "relic_total":   rs.get("relic_total", 0),
        "r5_plus":       rs.get("r5_plus", 0),
        "seven_star":    rs.get("seven_star", 0),
        "g13_plus":      rs.get("g13_plus", 0),
        "zeta_count":    rs.get("zeta_count", 0),
        "omicron_count": len(rs.get("omicrons") or []),
        "mod_score":     mod_score,
        "gl_count":      gl_count,
    }


def compute_guild_aggregate(player_metrics_list):
    """Aggregate player metrics into a guild summary."""
    n = len(player_metrics_list)
    if n == 0:
        return {}
    def avg(key):
        vals = [p[key] for p in player_metrics_list if p.get(key) is not None]
        return round(sum(vals) / len(vals), 2) if vals else 0.0
    def total(key):
        return sum(p.get(key, 0) for p in player_metrics_list)
    # Health score: weighted composite 0-100
    avg_relic   = avg("relic_total")
    avg_mod     = avg("mod_score")
    gl_per      = total("gl_count") / n
    r5_total    = total("r5_plus")
    star_total  = total("seven_star") or 1
    r5_pct      = r5_total / star_total
    health = min(100, round(
        min(25, avg_relic / 600 * 25) +
        min(20, avg_mod / 5 * 20) +
        min(30, gl_per / 5 * 30) +
        min(25, r5_pct * 25),
        1
    ))
    return {
        "member_count":     n,
        "relic_total":      total("relic_total"),
        "avg_relic_total":  avg("relic_total"),
        "r5_plus":          r5_total,
        "g13_plus":         total("g13_plus"),
        "seven_star":       star_total,
        "zeta_count":       total("zeta_count"),
        "omicron_count":    total("omicron_count"),
        "avg_mod_score":    avg("mod_score"),
        "gl_count":         total("gl_count"),
        "health_score":     health,
    }


def main():
    if not GUILDS_DIR.exists() or not any(GUILDS_DIR.glob("*.json")):
        print("ERROR: no files in data/guilds/. Run fetch_guilds.py first.")
        return

    log       = load_json_list(LOG_PATH)
    transfers = load_json_list(TRANSFERS_PATH)
    roster_stats = load_roster_stats()
    if not roster_stats:
        print("NOTE: roster_stats.json not found — stat snapshot will be incomplete. Run fetch_player_rosters.py first.")

    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # Build per-guild data from guild JSON files
    current_entries    = []
    current_location   = {}

    # Compact stats snapshot structure
    snap_players = {}  # ally_code -> compact metrics
    snap_guilds  = {}  # guild_name -> aggregate
    snap_named   = {label: 0 for label in NAMED_TOON_IDS}

    for guild_file in sorted(GUILDS_DIR.glob("*.json")):
        guild      = json.loads(guild_file.read_text())
        members    = guild.get("members", [])
        guild_id   = guild.get("guild_id", guild_file.stem)
        guild_name = guild.get("name", guild_file.stem)

        # log.json entry (lightweight)
        entry = {
            "timestamp": timestamp,
            "guild_id": guild_id,
            "guild_name": guild_name,
            "member_count": len(members),
            "guild_gp": guild.get("guild_gp", 0),
            "members": [
                {"ally_code": m["ally_code"], "name": m["name"], "gp": m["gp"]}
                for m in members
            ],
        }
        current_entries.append(entry)
        for m in members:
            current_location[m["ally_code"]] = (guild_id, guild_name, m["name"])

        # Compact stats per player in this guild
        guild_metrics = []
        for m in members:
            ac      = m.get("ally_code") or m.get("playerId") or ""
            rs      = roster_stats.get(ac, {})
            cgp     = m.get("chars_gp") or 1
            metrics = compute_player_metrics(rs, cgp)
            metrics["name"]  = m.get("name", metrics["name"])
            metrics["guild"] = guild_name
            if rs:
                snap_players[ac] = metrics
                guild_metrics.append(metrics)
                # Count named toon ownership
                units = rs.get("units") or {}
                for label, bid in NAMED_TOON_IDS.items():
                    if bid in units:
                        snap_named[label] = snap_named.get(label, 0) + 1

        if guild_metrics:
            snap_guilds[guild_name] = compute_guild_aggregate(guild_metrics)

    # Alliance aggregates
    all_metrics = list(snap_players.values())
    snap_alliance = compute_guild_aggregate(all_metrics) if all_metrics else {}
    snap_alliance["named"] = snap_named

    # Write compact stats snapshot
    snap = {
        "timestamp": timestamp,
        "alliance":  snap_alliance,
        "guilds":    snap_guilds,
        "players":   snap_players,
    }
    ts_file = timestamp.replace(":", "-").replace("+", "Z")[:19]
    snap_path = STATS_DIR / f"{ts_file}.json"
    snap_path.write_text(json.dumps(snap))
    snap_kb = snap_path.stat().st_size // 1024
    print(f"Stats snapshot -> {snap_path.name} ({snap_kb}KB)")
    if snap_guilds:
        for gname, agg in snap_guilds.items():
            print(f"  {gname}: health={agg.get('health_score')} zetas={agg.get('zeta_count')} omicrons={agg.get('omicron_count')} GLs={agg.get('gl_count')}")

    # Transfer detection (unchanged logic)
    by_guild_prev_latest = {}
    for e in log:
        gid = e.get("guild_id")
        if not gid:
            continue
        existing = by_guild_prev_latest.get(gid)
        if existing is None or e["timestamp"] > existing["timestamp"]:
            by_guild_prev_latest[gid] = e

    prev_location = {}
    for gid, e in by_guild_prev_latest.items():
        for m in e.get("members", []):
            prev_location[m["ally_code"]] = (gid, e["guild_name"], m["name"])

    for ally_code, (curr_gid, curr_gname, name) in current_location.items():
        if ally_code in prev_location:
            prev_gid, prev_gname, _ = prev_location[ally_code]
            if prev_gid != curr_gid:
                transfers.append({
                    "timestamp":  timestamp,
                    "ally_code":  ally_code,
                    "name":       name,
                    "from_guild": prev_gname,
                    "to_guild":   curr_gname,
                })
                print(f"  TRANSFER: {name} ({ally_code}) {prev_gname} -> {curr_gname}")

    log.extend(current_entries)
    LOG_PATH.write_text(json.dumps(log, indent=2))
    TRANSFERS_PATH.write_text(json.dumps(transfers, indent=2))

    print(f"Log -> {LOG_PATH} ({len(log)} entries)  Transfers -> {TRANSFERS_PATH} ({len(transfers)} total)")


if __name__ == "__main__":
    main()
