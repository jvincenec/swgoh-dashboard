"""
server.py — A tiny local web server that reads the JSON files produced by
fetch.py / fetch_guilds.py / snapshot.py and renders them in a dashboard.

Run with:
    python dashboard/server.py

Then open http://localhost:5050 in your browser.
"""

import csv
import io
import json
import sys
from pathlib import Path

from flask import Flask, render_template, Response

sys.path.insert(0, str(Path(__file__).parent.parent / "analysis"))
from squad_templates import SQUAD_TEMPLATES  # noqa: E402

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
GUILDS_DIR = DATA_DIR / "guilds"
HISTORY_LOG = DATA_DIR / "history" / "log.json"

app = Flask(__name__, template_folder="templates", static_folder="static")


def load_alignment():
    p = BASE_DIR / "game_data" / "unit_alignment.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}

ALIGNMENT = load_alignment()


def load_zeta_map():
    p = BASE_DIR / "game_data" / "zeta_map.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


ZETA_MAP = load_zeta_map()  # skill_id -> {is_zeta, is_omicron, omicron_mode, name}


def load_gl_requirements():
    p = BASE_DIR / "game_data" / "gl_requirements.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_datacron_sets():
    p = BASE_DIR / "game_data" / "datacron_sets.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_leaderboards():
    p = BASE_DIR / "data" / "leaderboards.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_player_stats(ally_code):
    """Load computed stats from fetch_stats.py output."""
    p = BASE_DIR / "data" / "stats" / f"{ally_code}.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def load_tb_platoons():
    p = BASE_DIR / "game_data" / "tb_platoons.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


GL_REQUIREMENTS = load_gl_requirements()
DATACRON_SETS   = load_datacron_sets()

# Balance labels matching the original Lamers tooltip scale (confirmed from
# reading the real guild-stats.html source — data-order stores numeric score,
# the visible text is the label)
_BALANCE_LABELS = [
    (500,  "Jedi Council"),
    (300,  "Jedi Master"),
    (200,  "Jedi Guardian"),
    (150,  "Jedi Sentinel"),
    (100,  "Jedi Consular"),
    (50,   "Jedi Knight"),
    (20,   "Padawan"),
    (5,    "Youngling"),
    (-5,   "Neutral"),
    (-20,  "Sith Sympathizer"),
    (-50,  "Sith"),
    (-150, "Sith Lord"),
    (-300, "Darth"),
    (-500, "Sith Council"),
]

def balance_label(score):
    if score is None:
        return None
    for threshold, label in _BALANCE_LABELS:
        if score >= threshold:
            return label
    return "Sith Council"

NAMED_TOONS = {
    "JKR":      "JEDIKNIGHTREVAN",
    "DR":       "DARTHREVAN",
    "Malak":    "DARTHMALAK",
    "GAS":      "GENERALSKYWALKER",
    "JML":      "GRANDMASTERLUKE",
    "JMK":      "JEDIMASTERKENOBI",
    "JKL":      "JEDIKNIGHTLUKE",
    "LV":       "LORDVADER",
    "Rey":      "GLREY",
    "SEE":      "SITHPALPATINE",
    "SLK":      "SUPREMELEADERKYLOREN",
    "Ahsoka":   "GLAHSOKATANO",
    "Jabba":    "JABBATHEHUTT",
    "Neg":      "NEGOTIATOR",
    "Mal":      "MALEVOLENCE",
    "Exec":     "CAPITALEXECUTOR",
    "Chimaera": "CAPITALCHIMAERA",
}

# Extended list for the important-toons page (30 chars)
IMPORTANT_TOONS = {
    **NAMED_TOONS,
    "Padme":    "PADMEAMIDALA",
    "Thrawn":   "GRANDADMIRALTHRAWN",
    "CLS":      "COMMANDERLUKESKYWALKER",
    "Shaak Ti": "SHAAKTI",
    "IPD":      "IMPERIALPROBEDROID",
    "Merrin":   "NIGHTSISTERMERRIN",
    "Wat":      "WATTAMBOR",
    "Geos":     "GEONOSIANBROODALPHA",
    "BB-8":     "BB8",
    "Mando":    "THEMANDALORIANBESKARARMOR",
    "Starkiller":"STARKILLER",
    "Reva":     "SEVENTHSISTER",
    "Baylan":   "BAYLANSKOLL",
}

GL_BASE_IDS = {
    "GLREY","SITHPALPATINE","SUPREMELEADERKYLOREN","GRANDMASTERLUKE",
    "JEDIMASTERKENOBI","JEDIKNIGHTLUKE","LORDVADER","GLAHSOKATANO","JABBATHEHUTT",
}


def load_icon_base_ids():
    """base_ids with a real icon available in static/toons.css (264 chars,
    a 2021 snapshot from the BRG/Lamers toolchain — newer characters won't
    have an icon here, fall back to plain text for those)."""
    css_path = Path(__file__).parent / "static" / "toons.css"
    if not css_path.exists():
        return set()
    content = css_path.read_text()
    import re
    return set(re.findall(r"\.([A-Z0-9_]+)-i \{", content))


ICON_BASE_IDS = load_icon_base_ids()


def load_json(filename: str, default=None):
    path = DATA_DIR / filename
    if not path.exists():
        return default if default is not None else {}
    return json.loads(path.read_text())


def relic_tier_to_level(tier: int) -> int:
    """Comlink relic tiers are offset by 2 from the in-game Relic level."""
    return max(0, tier - 2)


def load_guild_analyses():
    analyses = []
    if not DATA_DIR.exists():
        return analyses
    for path in sorted(DATA_DIR.glob("guild_analysis_*.json")):
        try:
            data = json.loads(path.read_text())
            analyses.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return analyses


def load_raid_tb_report():
    path = DATA_DIR / "raid_tb_report.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def load_member_activity_report():
    path = DATA_DIR / "member_activity_report.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def load_player_pvp_report():
    path = DATA_DIR / "player_pvp_report.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def load_mods_report():
    path = DATA_DIR / "mods_report.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def load_relic_gap_report():
    path = DATA_DIR / "relic_gap_report.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def load_tracked_guilds():
    """Current state of every tracked guild, from data/guilds/*.json."""
    guilds = []
    if not GUILDS_DIR.exists():
        return guilds
    for path in sorted(GUILDS_DIR.glob("*.json")):
        try:
            guilds.append(json.loads(path.read_text()))
        except (json.JSONDecodeError, OSError):
            continue
    guilds.sort(key=lambda g: -(g.get("guild_gp") or 0))
    return guilds


def load_history_log():
    if not HISTORY_LOG.exists():
        return []
    try:
        return json.loads(HISTORY_LOG.read_text())
    except json.JSONDecodeError:
        return []


def build_history_rows():
    """Group log entries by guild_id, diff each snapshot against the
    previous one for that same guild (added/left members, GP delta).
    Returns newest-first, grouped by guild."""
    log = load_history_log()

    by_guild = {}
    for entry in log:
        gid = entry.get("guild_id")
        if not gid:
            continue
        by_guild.setdefault(gid, []).append(entry)

    grouped = []
    for guild_id, entries in by_guild.items():
        entries.sort(key=lambda e: e["timestamp"])
        rows = []
        for i in range(len(entries) - 1, -1, -1):
            entry = entries[i]
            prev = entries[i - 1] if i > 0 else None

            row = {
                "timestamp": entry["timestamp"],
                "guild_name": entry["guild_name"],
                "member_count": entry["member_count"],
                "guild_gp": entry["guild_gp"],
                "gp_change": None,
                "added": [],
                "left": [],
            }

            if prev:
                row["gp_change"] = entry["guild_gp"] - prev["guild_gp"]
                prev_codes = {m["ally_code"] for m in prev.get("members", [])}
                curr_codes = {m["ally_code"] for m in entry.get("members", [])}
                curr_by_code = {m["ally_code"]: m["name"] for m in entry.get("members", [])}
                prev_by_code = {m["ally_code"]: m["name"] for m in prev.get("members", [])}
                row["added"] = [curr_by_code[c] for c in (curr_codes - prev_codes)]
                row["left"] = [prev_by_code[c] for c in (prev_codes - curr_codes)]

            rows.append(row)

        grouped.append({
            "guild_id": guild_id,
            "guild_name": entries[-1]["guild_name"],
            "rows": rows,
        })

    grouped.sort(key=lambda g: g["guild_name"])
    return grouped


def build_community_history():
    """Sum guild_gp and member_count across all guilds, grouped by
    timestamp (each fetch_guilds.py + snapshot.py run shares one
    timestamp across all guilds it fetched)."""
    log = load_history_log()
    by_timestamp = {}
    for entry in log:
        ts = entry.get("timestamp")
        if not ts:
            continue
        bucket = by_timestamp.setdefault(ts, {"timestamp": ts, "total_gp": 0, "total_members": 0, "guild_count": 0})
        bucket["total_gp"] += entry.get("guild_gp", 0)
        bucket["total_members"] += entry.get("member_count", 0)
        bucket["guild_count"] += 1
    out = list(by_timestamp.values())
    out.sort(key=lambda b: b["timestamp"])
    return out


@app.route("/data/community-gp-stats.json")
def community_gp_stats_json():
    """{y, dates, series} shape that graph.js (the real D3 chart library
    from BRG/Lamers, copied verbatim — public Observable multi-line-chart
    example) expects. Built from our own real, currently-accumulating
    history log, not guessed/faked data."""
    log = load_history_log()
    by_date = {}
    for entry in log:
        ts = entry.get("timestamp")
        if not ts:
            continue
        by_date.setdefault(ts, 0)
        by_date[ts] += entry.get("guild_gp", 0)
    dates_sorted = sorted(by_date.keys())
    formatted_dates = []
    for ts in dates_sorted:
        y, m, d = ts[:10].split("-")
        formatted_dates.append(f"{m}/{d}/{y}")
    values = [by_date[ts] for ts in dates_sorted]
    return {
        "y": "Galactic Power",
        "dates": formatted_dates,
        "series": [{"name": "Community", "id": "community", "values": {"total": values}}],
    }


@app.route("/data/community-player-stats.json")
def community_player_stats_json():
    log = load_history_log()
    by_date = {}
    for entry in log:
        ts = entry.get("timestamp")
        if not ts:
            continue
        by_date.setdefault(ts, 0)
        by_date[ts] += entry.get("member_count", 0)
    dates_sorted = sorted(by_date.keys())
    formatted_dates = []
    for ts in dates_sorted:
        y, m, d = ts[:10].split("-")
        formatted_dates.append(f"{m}/{d}/{y}")
    values = [by_date[ts] for ts in dates_sorted]
    return {
        "y": "Players",
        "dates": formatted_dates,
        "series": [{"name": "Community", "id": "community", "values": {"total": values}}],
    }


@app.route("/data/guilds-gp-stats.json")
def guilds_gp_stats_json():
    log = load_history_log()
    by_guild = {}
    for entry in log:
        gid = entry.get("guild_id")
        ts = entry.get("timestamp")
        if not gid or not ts:
            continue
        by_guild.setdefault(gid, {"name": entry.get("guild_name", gid), "points": {}})
        by_guild[gid]["points"][ts] = entry.get("guild_gp", 0)

    all_dates = sorted({ts for g in by_guild.values() for ts in g["points"].keys()})
    formatted_dates = []
    for ts in all_dates:
        y, m, d = ts[:10].split("-")
        formatted_dates.append(f"{m}/{d}/{y}")

    series = []
    for gid, g in by_guild.items():
        values = [g["points"].get(ts, -1) for ts in all_dates]
        series.append({"name": g["name"], "id": gid, "values": {"total": values}})

    return {"y": "Galactic Power", "dates": formatted_dates, "series": series}


@app.route("/history")
def history():
    groups = build_history_rows()
    community = build_community_history()
    return render_template("history.html", groups=groups, community=community)


@app.route("/squad-templates")
def squad_templates_page():
    return render_template("squad_templates.html", templates=SQUAD_TEMPLATES)


@app.route("/export/<dataset>.csv")
def export_csv(dataset):
    rows = []
    fieldnames = []

    if dataset == "players":
        rows = build_players_index()
        fieldnames = ["ally_code", "name", "guild_name", "gp", "chars_gp", "ships_gp",
                      "relic_total", "seven_star", "r5_plus", "g13_plus", "g12_plus", "g10_plus"]
    elif dataset == "characters":
        rows = build_characters_index()
        fieldnames = ["base_id", "owner_count", "relic_sum"]
    elif dataset == "community":
        rows = load_tracked_guilds()
        fieldnames = ["guild_id", "name", "member_count", "guild_gp"]
    elif dataset == "squads":
        rows = build_squads_index()
        fieldnames = ["ally_code", "name", "guild_name", "squad_count"]
    elif dataset == "farming":
        costs = load_unlock_costs()
        rows = []
        for base_id, info in costs.items():
            shard_ing = next((i for i in info["ingredients"] if i["type"] == "MATERIAL"), None)
            currency_ing = next((i for i in info["ingredients"] if i["type"] == "CURRENCY"), None)
            rows.append({
                "base_id": base_id, "name_key": info.get("name_key", ""),
                "combat_type": info.get("combat_type", ""),
                "shards": shard_ing["quantity"] if shard_ing else None,
                "currency": currency_ing["quantity"] if currency_ing else None,
            })
        fieldnames = ["base_id", "name_key", "combat_type", "shards", "currency"]
    elif dataset == "mods":
        _, rows = build_mods_index()
        fieldnames = ["ally_code", "name", "guild_name", "total_mods"]
    else:
        return Response("Unknown dataset. Use: players, characters, community, squads, farming, mods", status=404)

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={dataset}.csv"},
    )


def load_transfers():
    path = DATA_DIR / "history" / "transfers.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return []


def load_unlock_costs():
    path = BASE_DIR / "game_data" / "unlock_costs.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}


def build_mods_index():
    """Aggregate equipped mod sets across every player with roster data
    (Phase 2), plus a per-player mod-count summary. Set/slot/rarity only
    (decoded from definitionId digits, per mods_report.py) — no raw stat
    rolls, since that needs deeper statMod collection decoding not yet
    built."""
    roster_stats = load_roster_stats()
    set_counts = {}
    player_summaries = []

    for ally_code, stats in roster_stats.items():
        units = stats.get("units", {})
        total_mods = 0
        for base_id, unit in units.items():
            for mod in unit.get("mods", []):
                total_mods += 1
                set_name = mod.get("set", "?")
                set_counts[set_name] = set_counts.get(set_name, 0) + 1
        if total_mods:
            player_summaries.append({
                "ally_code": ally_code,
                "name": stats.get("name", "?"),
                "guild_name": stats.get("guild_name", "?"),
                "total_mods": total_mods,
            })

    player_summaries.sort(key=lambda p: -p["total_mods"])
    set_distribution = sorted(set_counts.items(), key=lambda kv: -kv[1])
    return set_distribution, player_summaries


@app.route("/mods")
def mods():
    set_distribution, player_summaries = build_mods_index()
    return render_template("mods.html", set_distribution=set_distribution, players=player_summaries)


@app.route("/farming")
def farming():
    costs = load_unlock_costs()
    rows = []
    for base_id, info in costs.items():
        shard_ing = next((i for i in info["ingredients"] if i["type"] == "MATERIAL"), None)
        currency_ing = next((i for i in info["ingredients"] if i["type"] == "CURRENCY"), None)
        rows.append({
            "base_id": base_id,
            "name_key": info.get("name_key", ""),
            "combat_type": info.get("combat_type", ""),
            "force_alignment": info.get("force_alignment", ""),
            "shards": shard_ing["quantity"] if shard_ing else None,
            "currency": currency_ing["quantity"] if currency_ing else None,
        })
    rows.sort(key=lambda r: r["base_id"])
    return render_template("farming.html", rows=rows)


def load_roster_stats():
    path = DATA_DIR / "rosters" / "roster_stats.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}


def build_players_index():
    """Unique players across all currently-tracked guilds, current GP + guild,
    enriched with roster stats (zetas, relic total, gear tiers) if Phase 2
    (fetch_player_rosters.py) has been run."""
    tracked = load_tracked_guilds()
    roster_stats = load_roster_stats()
    players = {}
    for g in tracked:
        for m in g.get("members", []):
            entry = {
                "ally_code": m["ally_code"],
                "name": m["name"],
                "gp": m["gp"],
                "chars_gp": m.get("chars_gp", 0),
                "ships_gp": m.get("ships_gp", 0),
                "guild_name": g["name"],
                "contributions": m.get("contributions", {}),
                "gac_history": m.get("gac_history", []),
            }
            stats = roster_stats.get(m["ally_code"])
            if stats:
                units   = stats.get("units", {})
                chars_gp = (m.get("chars_gp") or 0) or 1
                g13p = stats.get("g13_plus", 0) or 0
                r5p  = stats.get("r5_plus",  0) or 0
                rt   = stats.get("relic_total", 0) or 0
                # Gear Score: matches DSR-bot formula confirmed from Lamers tooltip
                gear_score = round((g13p + r5p + rt / 5) / chars_gp * 100_000, 2)
                # Mod Score = speed_secondary_count / chars_gp * 100_000
                spd_sec = stats.get("speed_secondary_count")
                mod_score = round(spd_sec / chars_gp * 100_000, 2) if (spd_sec is not None and chars_gp) else None
                # Balance: LS units owned minus DS units owned
                ls = sum(1 for bid in units if ALIGNMENT.get(bid) == "LIGHT")
                ds = sum(1 for bid in units if ALIGNMENT.get(bid) == "DARK")
                balance = ls - ds
                blabel = balance_label(balance)
                # Named toon ownership
                named = {label: (1 if bid in units else 0)
                         for label, bid in NAMED_TOONS.items()}
                entry.update({
                    "relic_total": rt,
                    "seven_star": stats.get("seven_star"),
                    "r5_plus":   r5p,
                    "g13_plus":  g13p,
                    "g12_plus":  stats.get("g12_plus"),
                    "g10_plus":  stats.get("g10_plus"),
                    "gear_score": gear_score,
                    "mod_score":  mod_score,
                    "balance":    balance,
                    "balance_label": blabel,
                    "zeta_count":  stats.get("zeta_count", 0),
                    "omicron_count": len(stats.get("omicrons") or []),
                    "named":      named,
                })
            players[m["ally_code"]] = entry
    out = list(players.values())
    out.sort(key=lambda p: (p["guild_name"], -(p["gp"] or 0)))
    return out


def build_player_history(ally_code: str):
    """All snapshot appearances of this ally_code across the log, oldest first."""
    log = load_history_log()
    history = []
    for entry in sorted(log, key=lambda e: e["timestamp"]):
        for m in entry.get("members", []):
            if m["ally_code"] == ally_code:
                history.append({
                    "timestamp": entry["timestamp"],
                    "guild_name": entry["guild_name"],
                    "gp": m["gp"],
                    "name": m["name"],
                })
                break
    return history


@app.route("/guild/<slug>")
def guild_detail(slug):
    import re as _re
    slug_clean = _re.sub(r"[^a-z0-9-]", "", slug.lower())
    guild_file = BASE_DIR / "data" / "guilds" / f"{slug_clean}.json"
    if not guild_file.exists():
        return f"Guild '{slug_clean}' not found in data/guilds/", 404
    guild = json.loads(guild_file.read_text())
    return render_template("guild_detail.html", guild=guild)


def fetch_events():
    """Current + upcoming in-game events cached 1hr."""
    import time
    cache_file = BASE_DIR / "data" / "events_cache.json"
    if cache_file.exists() and (time.time() - cache_file.stat().st_mtime) < 3600:
        try:
            return json.loads(cache_file.read_text())
        except Exception:
            pass
    try:
        resp = requests.post(f"{COMLINK_URL}/getEvents",
                             json={"payload": {}, "enums": True}, timeout=30)
        resp.raise_for_status()
        events = resp.json().get("gameEvent", [])
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(events))
        return events
    except Exception:
        return []


# --- Stats history loader ---

def load_stats_snapshots():
    """All compact player-stats snapshots, sorted oldest-first.
    Returns list of summary dicts. Fast: each file is ~50-100KB."""
    stats_dir = BASE_DIR / "data" / "history" / "player_stats"
    if not stats_dir.exists():
        return []
    snapshots = []
    for p in sorted(stats_dir.glob("*.json")):
        try:
            snapshots.append(json.loads(p.read_text()))
        except Exception:
            pass
    return sorted(snapshots, key=lambda s: s.get("timestamp", ""))


def stats_to_chart(snapshots, series_fn, value_fn, y_label="value"):
    """Convert snapshots to graph.js {y, dates, series} shape.
    series_fn(snap) -> list of (name, id) tuples for this snapshot.
    value_fn(snap, series_id) -> numeric value or None."""
    all_ids = {}  # id -> name (last seen)
    dates = []
    for snap in snapshots:
        ts = snap.get("timestamp", "")
        date_part = ts[:10]  # YYYY-MM-DD
        if date_part:
            y, m, d = date_part.split("-")
            dates.append(f"{m}/{d}/{y}")
        for name, sid in series_fn(snap):
            all_ids[sid] = name

    series = []
    for sid, name in sorted(all_ids.items()):
        values = []
        for snap in snapshots:
            v = value_fn(snap, sid)
            values.append(-1 if v is None else v)
        series.append({"name": name, "id": sid, "values": {"total": values}})

    return {"y": y_label, "dates": dates, "series": series}


@app.route("/data/trends/alliance-relic.json")
def trends_alliance_relic():
    snaps = load_stats_snapshots()
    return stats_to_chart(
        snaps,
        lambda s: [("Alliance", "alliance")],
        lambda s, _: s.get("alliance", {}).get("relic_total"),
        y_label="Total Relic Levels"
    )


@app.route("/data/trends/alliance-r5plus.json")
def trends_alliance_r5plus():
    snaps = load_stats_snapshots()
    return stats_to_chart(
        snaps,
        lambda s: [("Alliance R5+", "alliance")],
        lambda s, _: s.get("alliance", {}).get("r5_plus"),
        y_label="R5+ Units"
    )


@app.route("/data/trends/named-toons.json")
def trends_named_toons():
    snaps = load_stats_snapshots()
    if not snaps:
        return {"y": "Owners", "dates": [], "series": []}
    all_labels = list(snaps[-1].get("alliance", {}).get("named", {}).keys())
    return stats_to_chart(
        snaps,
        lambda s: [(label, label) for label in all_labels],
        lambda s, label: s.get("alliance", {}).get("named", {}).get(label),
        y_label="Players Who Own"
    )


@app.route("/data/trends/guild-relic.json")
def trends_guild_relic():
    snaps = load_stats_snapshots()
    all_guilds = set()
    for s in snaps:
        all_guilds.update(s.get("guilds", {}).keys())
    return stats_to_chart(
        snaps,
        lambda s: [(g, g) for g in all_guilds],
        lambda s, g: s.get("guilds", {}).get(g, {}).get("relic_total"),
        y_label="Total Relic Levels"
    )


@app.route("/data/trends/player/<ally_code>/relic.json")
def trends_player_relic(ally_code):
    snaps = load_stats_snapshots()
    name = None
    for s in snaps:
        p = s.get("players", {}).get(ally_code)
        if p:
            name = p.get("name", ally_code)
            break
    label = name or ally_code
    return stats_to_chart(
        snaps,
        lambda s: [(label, ally_code)],
        lambda s, ac: s.get("players", {}).get(ac, {}).get("relic_total"),
        y_label="Relic Total"
    )


@app.route("/trends")
def trends():
    snaps = load_stats_snapshots()
    has_data = len(snaps) >= 2
    # Player list for the per-player selector
    players = []
    if snaps:
        for ac, ps in snaps[-1].get("players", {}).items():
            players.append({"ally_code": ac, "name": ps.get("name", "?"),
                            "guild": ps.get("guild", "?")})
        players.sort(key=lambda p: p["name"])
    return render_template("trends.html", has_data=has_data, players=players,
                           snap_count=len(snaps))


@app.route("/events")
def events_page():
    import time
    now = int(time.time())
    events = [e for e in fetch_events() if int(e.get("endTime", 0) or 0) > now]
    events.sort(key=lambda e: int(e.get("startTime", 0) or 0))
    return render_template("events.html", events=events, now=now)


def build_raid_damage_report():
    guilds = load_tracked_guilds()
    report = []
    for g in guilds:
        for raid in g.get("recent_raid_results", []):
            for m in raid.get("members", []):
                pid = m.get("player_id")
                name = next((gm["name"] for gm in g.get("members", []) if gm.get("ally_code") == pid), pid or "?")
                report.append({
                    "guild": g["name"], "raid_id": raid.get("raid_id", "?"),
                    "end_time": raid.get("end_time", ""), "outcome": raid.get("outcome", 0),
                    "name": name, "ally_code": pid,
                    "damage": m.get("damage", 0), "rank": m.get("rank"),
                })
    report.sort(key=lambda r: -r["damage"])
    return report


@app.route("/raids")
def raids():
    return render_template("raids.html", report=build_raid_damage_report())


def build_inactivity_report():
    import time
    now_ms = int(time.time() * 1000)
    roster_stats = load_roster_stats()
    members = []
    for g in load_tracked_guilds():
        for m in g.get("members", []):
            ac = m.get("ally_code") or ""
            # Use lastActivityTime from roster_stats (more accurate, from /player fetch)
            # falling back to guild-level last_activity (from /guild endpoint)
            rs_last = None
            rs = roster_stats.get(ac, {})
            rs_raw = rs.get("last_activity_time")
            if rs_raw:
                rs_last = int(rs_raw) if int(rs_raw) > 1e12 else int(rs_raw) * 1000

            guild_last = int(m.get("last_activity", 0) or 0)
            last = rs_last or guild_last
            inactive_ms = (now_ms - last) if last else None
            role = rs.get("guild_role") or m.get("member_level", "")
            members.append({
                "guild": g["name"], "name": m["name"], "ally_code": ac,
                "last_activity": last,
                "days_inactive": round(inactive_ms / 86_400_000, 1) if inactive_ms else None,
                "member_level": role,
                "gp": m.get("gp", 0), "league_id": m.get("league_id", ""),
                "lifetime_score": m.get("lifetime_season_score", 0),
                "flagged": (inactive_ms or 0) > 72 * 3_600_000,
                "source": "roster" if rs_last else "guild",
            })
    members.sort(key=lambda m: m.get("last_activity") or 0)
    return members


@app.route("/inactivity")
def inactivity():
    return render_template("inactivity.html", members=build_inactivity_report())


@app.route("/community")
def community():
    tracked = load_tracked_guilds()
    total_members = sum(g.get("member_count", 0) for g in tracked)
    total_gp = sum(g.get("guild_gp", 0) or 0 for g in tracked)
    return render_template(
        "community.html", guilds=tracked, total_members=total_members, total_gp=total_gp
    )


def build_characters_index():
    """Aggregate ownership counts per base_id across every player with
    roster stats (Phase 2 data)."""
    roster_stats = load_roster_stats()
    chars = {}
    for ally_code, stats in roster_stats.items():
        for base_id, unit in stats.get("units", {}).items():
            entry = chars.setdefault(base_id, {"base_id": base_id, "owner_count": 0, "relic_sum": 0})
            entry["owner_count"] += 1
            entry["relic_sum"] += unit.get("relic", 0)
    out = list(chars.values())
    out.sort(key=lambda c: -c["owner_count"])
    return out


def build_character_detail(base_id):
    """Every player who owns this base_id, with their relic/gear/rarity,
    sorted by relic then gear descending."""
    roster_stats = load_roster_stats()
    owners = []
    for ally_code, stats in roster_stats.items():
        unit = stats.get("units", {}).get(base_id)
        if unit:
            owners.append({
                "ally_code": ally_code,
                "name": stats.get("name", "?"),
                "guild_name": stats.get("guild_name", "?"),
                "relic": unit.get("relic", 0),
                "gear": unit.get("gear", 0),
                "rarity": unit.get("rarity", 0),
            })
    owners.sort(key=lambda o: (-o["relic"], -o["gear"]))
    return owners


def build_squads_index():
    """Rank players by viable squad count, with the squad list per player.
    NOT counter/matchup data — squad viability only (owns the units, meets
    relic/omicron thresholds), per squad_templates.py's own documented
    limits."""
    roster_stats = load_roster_stats()
    out = []
    for ally_code, stats in roster_stats.items():
        squads = stats.get("squads", [])
        if not squads:
            continue
        out.append({
            "ally_code": ally_code,
            "name": stats.get("name", "?"),
            "guild_name": stats.get("guild_name", "?"),
            "squad_count": len(squads),
            "squads": squads,
        })
    out.sort(key=lambda p: -p["squad_count"])
    return out


@app.route("/squads")
def squads():
    return render_template("squads.html", players=build_squads_index())


@app.context_processor
def inject_icon_base_ids():
    return {"icon_base_ids": ICON_BASE_IDS}


@app.route("/characters")
def characters():
    return render_template("characters.html", characters=build_characters_index())


@app.route("/c/<base_id>")
def character_detail(base_id):
    owners = build_character_detail(base_id)
    return render_template("character_detail.html", base_id=base_id, owners=owners)


@app.route("/players")
def players():
    return render_template("players.html", players=build_players_index())


def find_current_member(ally_code):
    for g in load_tracked_guilds():
        for m in g.get("members", []):
            if m["ally_code"] == ally_code:
                return m
    return {}


@app.route("/player/<ally_code>")
def player_detail(ally_code):
    history = build_player_history(ally_code)
    name = history[-1]["name"] if history else ally_code
    rs = load_roster_stats().get(ally_code, {})
    units = rs.get("units", {})
    current = find_current_member(ally_code)
    contributions = current.get("contributions", {})
    gac_history = current.get("gac_history", [])

    # Full character roster sorted by relic desc, gear desc
    all_units = sorted(
        [{"base_id": bid, **u} for bid, u in units.items()],
        key=lambda u: (-u.get("relic", 0), -u.get("gear", 0))
    )

    # Stat summary card
    chars_gp   = current.get("chars_gp", 0) or 0
    ships_gp   = current.get("ships_gp", 0) or 0
    total_gp   = current.get("gp", 0) or 0
    g13p       = rs.get("g13_plus", 0) or 0
    r5p        = rs.get("r5_plus", 0) or 0
    rt         = rs.get("relic_total", 0) or 0
    gear_score = round((g13p + r5p + rt / 5) / chars_gp * 100_000, 2) if chars_gp else None
    spd_sec    = rs.get("speed_secondary_count")
    mod_score  = round(spd_sec / chars_gp * 100_000, 2) if (spd_sec is not None and chars_gp) else None
    ls = sum(1 for bid in units if ALIGNMENT.get(bid) == "LIGHT")
    ds = sum(1 for bid in units if ALIGNMENT.get(bid) == "DARK")
    bal = ls - ds

    summary = {
        "gp": total_gp, "chars_gp": chars_gp, "ships_gp": ships_gp,
        "player_level": rs.get("player_level") or current.get("level"),
        "seven_star": rs.get("seven_star"), "r5_plus": r5p, "g13_plus": g13p,
        "g12_plus": rs.get("g12_plus"), "g10_plus": rs.get("g10_plus"),
        "relic_total": rt, "zeta_count": rs.get("zeta_count", 0),
        "omicron_count": len(rs.get("omicrons") or []),
        "datacron_count": rs.get("datacron_count", 0),
        "mod_score": mod_score, "gear_score": gear_score,
        "balance": bal, "balance_label": balance_label(bal),
        "squad_arena_rank": rs.get("squad_arena_rank"),
        "fleet_arena_rank": rs.get("fleet_arena_rank"),
        "lifetime_stats": rs.get("lifetime_stats", {}),
    }

    # Resolved zeta list for Zetas tab
    zetas_list = []
    for base_id, u in units.items():
        for sk_id in (u.get("zeta_skills") or []):
            info = ZETA_MAP.get(sk_id, {})
            if not info.get("is_omicron"):  # pure zetas only
                zetas_list.append({
                    "base_id":  base_id,
                    "skill_id": sk_id,
                    "name":     info.get("name", sk_id),
                })

    # Omicrons grouped by mode for the UI
    omicrons_by_mode = {}
    for om in (rs.get("omicrons") or []):
        mode = om.get("mode") or "Unknown"
        omicrons_by_mode.setdefault(mode, []).append(om)

    # GP history for D3 chart — build JSON shape graph.js expects
    gp_history = []
    dates_set = {}
    for h in sorted(history, key=lambda x: x["timestamp"]):
        ts = h["timestamp"][:10]
        y, m, d = ts.split("-")
        dates_set[ts] = f"{m}/{d}/{y}"
    date_list = sorted(dates_set.keys())
    gp_values = []
    gp_by_date = {h["timestamp"][:10]: h["gp"] for h in history}
    for dt in date_list:
        gp_values.append(gp_by_date.get(dt, -1))
    player_gp_chart = {
        "y": "GP",
        "dates": [dates_set[d] for d in date_list],
        "series": [{"name": name, "id": ally_code, "values": {"total": gp_values}}]
    }

    # Load computed stats from fetch_stats.py if available
    computed_stats = load_player_stats(ally_code)

    return render_template(
        "player_detail.html",
        ally_code=ally_code, name=name, history=history,
        squads=rs.get("squads", []), squads_close=rs.get("squads_close", []),
        all_units=all_units, contributions=contributions, gac_history=gac_history,
        summary=summary, omicrons_by_mode=omicrons_by_mode,
        player_gp_chart=player_gp_chart,
        datacrons=rs.get("datacrons", []),
        zetas_list=zetas_list,
        datacron_sets=DATACRON_SETS,
        guild_role=rs.get("guild_role", ""),
        last_activity=rs.get("last_activity_time"),
        computed_stats=computed_stats,
    )


@app.route("/guild/<slug>/mods")
def guild_mods(slug):
    """Per-guild mod quality report — per-player speed secondary summary."""
    import re as _re
    slug_clean = _re.sub(r"[^a-z0-9-]", "", slug.lower())
    guild_file = BASE_DIR / "data" / "guilds" / f"{slug_clean}.json"
    if not guild_file.exists():
        return f"Guild '{slug_clean}' not found", 404
    guild = json.loads(guild_file.read_text())
    roster_stats = load_roster_stats()

    rows = []
    for m in guild.get("members", []):
        ac = m.get("ally_code")
        rs = roster_stats.get(ac, {})
        units = rs.get("units", {})
        chars_gp = m.get("chars_gp", 0) or 1
        spd = rs.get("speed_secondary_count") or 0
        mod_score = round(spd / chars_gp * 100_000, 2) if chars_gp else None
        # Best 5 chars by speed secondary count
        top_chars = sorted(
            [{"base_id": bid, "speed_sec": u.get("speed_secondary_count", 0), "relic": u.get("relic", 0)}
             for bid, u in units.items() if u.get("speed_secondary_count", 0) > 0],
            key=lambda x: -x["speed_sec"]
        )[:5]
        rows.append({
            "name": m.get("name"), "ally_code": ac,
            "gp": m.get("gp", 0), "chars_gp": chars_gp,
            "speed_15plus": spd,
            "mod_score": mod_score,
            "top_chars": top_chars,
            "zeta_count": rs.get("zeta_count", 0),
            "omicron_count": len(rs.get("omicrons") or []),
        })
    rows.sort(key=lambda r: -(r["mod_score"] or 0))
    return render_template("guild_mods.html", guild=guild, rows=rows)


@app.route("/alliance/mods")
def alliance_mods():
    """Alliance-wide mod overview — best/worst mod scores across all guilds."""
    roster_stats = load_roster_stats()
    tracked = load_tracked_guilds()
    rows = []
    for g in tracked:
        for m in g.get("members", []):
            ac = m.get("ally_code")
            rs = roster_stats.get(ac, {})
            chars_gp = m.get("chars_gp", 0) or 1
            spd = rs.get("speed_secondary_count") or 0
            mod_score = round(spd / chars_gp * 100_000, 2) if chars_gp else None
            rows.append({
                "name": m.get("name"), "ally_code": ac,
                "guild": g.get("name", "?"),
                "chars_gp": chars_gp,
                "speed_15plus": spd,
                "mod_score": mod_score,
                "zeta_count": rs.get("zeta_count", 0),
                "omicron_count": len(rs.get("omicrons") or []),
            })
    rows.sort(key=lambda r: -(r["mod_score"] or 0))
    return render_template("alliance_mods.html", rows=rows)


@app.route("/gl-readiness")
def gl_readiness():
    roster_stats = load_roster_stats()
    all_gls = GL_REQUIREMENTS
    rows = []
    for ac, rs in roster_stats.items():
        units = rs.get("units", {})
        name  = rs.get("name", ac)
        guild = rs.get("guild_name", "")
        player_gls = {}
        for gl_id, gl in all_gls.items():
            if gl_id in units:
                player_gls[gl_id] = {"owned": True, "relic": units[gl_id].get("relic", 0)}
                continue
            reqs = gl.get("units", [])
            met = 0
            gaps = []
            for req in reqs:
                bid = req.get("base_id", "")
                u   = units.get(bid, {})
                rarity = u.get("rarity", 0)
                gear   = u.get("gear", 0)
                relic  = u.get("relic", 0)
                needed_stars = req.get("min_stars", 7)
                needed_gear  = req.get("min_gear", 0)
                needed_relic = req.get("min_relic", 0)
                if rarity >= needed_stars and gear >= needed_gear and relic >= needed_relic:
                    met += 1
                else:
                    gaps.append({
                        "base_id": bid,
                        "have_stars": rarity, "need_stars": needed_stars,
                        "have_gear": gear, "need_gear": needed_gear,
                        "have_relic": relic, "need_relic": needed_relic,
                        "note": req.get("note", ""),
                    })
            player_gls[gl_id] = {"owned": False, "met": met, "total": len(reqs), "gaps": gaps}
        rows.append({"name": name, "ally_code": ac, "guild": guild, "gls": player_gls})

    rows.sort(key=lambda r: -sum(1 for v in r["gls"].values() if v.get("owned")))
    return render_template("gl_readiness.html", rows=rows, all_gls=all_gls)


@app.route("/leaderboards")
def leaderboards():
    lb = load_leaderboards()
    tracked = load_tracked_guilds()
    # Enrich with current GP from guild files
    rows = []
    for g in tracked:
        gid  = g.get("id") or g.get("guildId") or ""
        name = g.get("name", "?")
        gp   = g.get("gp") or 0
        entry = lb.get(gid, {})
        rows.append({
            "name":    name,
            "gp":      gp,
            "gp_rank": entry.get("gp_rank"),
            "slug":    entry.get("slug", ""),
        })
    rows.sort(key=lambda r: r["gp"] or 0, reverse=True)
    return render_template("leaderboards.html", rows=rows)


@app.route("/guild/<slug>/important-toons")
def guild_important_toons(slug):
    import re as _re
    slug_clean = _re.sub(r"[^a-z0-9-]", "", slug.lower())
    gf = BASE_DIR / "data" / "guilds" / f"{slug_clean}.json"
    if not gf.exists():
        return f"Guild {slug_clean!r} not found", 404
    guild = json.loads(gf.read_text())
    rs_all = load_roster_stats()
    members = guild.get("members", [])
    n = len(members) or 1
    rows = []
    for label, bid in IMPORTANT_TOONS.items():
        owners = []
        for m in members:
            ac = m.get("ally_code") or ""
            rs = rs_all.get(ac, {})
            u  = (rs.get("units") or {}).get(bid)
            if u:
                owners.append({"name": m.get("name"), "ally_code": ac,
                                "relic": u.get("relic", 0), "gear": u.get("gear", 0)})
        owners.sort(key=lambda x: -x["relic"])
        rows.append({"label": label, "base_id": bid,
                     "count": len(owners), "pct": round(len(owners)/n*100, 1),
                     "owners": owners})
    rows.sort(key=lambda r: -r["pct"])
    return render_template("guild_important_toons.html", guild=guild, rows=rows, n=n)


@app.route("/guild/<slug>/rare-units")
def guild_rare_units(slug):
    import re as _re
    slug_clean = _re.sub(r"[^a-z0-9-]", "", slug.lower())
    gf = BASE_DIR / "data" / "guilds" / f"{slug_clean}.json"
    if not gf.exists():
        return f"Guild {slug_clean!r} not found", 404
    guild = json.loads(gf.read_text())
    rs_all = load_roster_stats()
    members = guild.get("members", [])
    n = len(members) or 1
    unit_counts = {}  # base_id -> {count, relic_sum, owners}
    for m in members:
        ac = m.get("ally_code") or ""
        rs = rs_all.get(ac, {})
        for bid, u in (rs.get("units") or {}).items():
            e = unit_counts.setdefault(bid, {"count": 0, "relic_sum": 0, "owners": []})
            e["count"] += 1
            e["relic_sum"] += u.get("relic", 0)
            e["owners"].append({"name": m.get("name"), "relic": u.get("relic", 0)})
    threshold = max(1, int(n * 0.30))  # <30% ownership = rare
    rare = [{"base_id": bid, "count": d["count"],
             "pct": round(d["count"]/n*100, 1),
             "avg_relic": round(d["relic_sum"]/d["count"], 1),
             "owners": sorted(d["owners"], key=lambda x: -x["relic"])}
            for bid, d in unit_counts.items() if d["count"] <= threshold]
    rare.sort(key=lambda r: r["pct"])
    return render_template("guild_rare_units.html", guild=guild, rows=rare, n=n)


@app.route("/guild/<slug>/squads-all")
def guild_squads_all(slug):
    import re as _re
    slug_clean = _re.sub(r"[^a-z0-9-]", "", slug.lower())
    gf = BASE_DIR / "data" / "guilds" / f"{slug_clean}.json"
    if not gf.exists():
        return f"Guild {slug_clean!r} not found", 404
    guild = json.loads(gf.read_text())
    rs_all = load_roster_stats()
    rows = []
    for m in guild.get("members", []):
        ac  = m.get("ally_code") or ""
        rs  = rs_all.get(ac, {})
        for sq in (rs.get("squads") or []):
            rows.append({"player": m.get("name", "?"), "ally_code": ac,
                         "squad": sq.get("name", "?"), "category": sq.get("category", ""),
                         "limiting_relic": sq.get("limiting_relic"), "required_relic": sq.get("required_relic")})
    rows.sort(key=lambda r: (r["squad"], -r.get("limiting_relic") or 0))
    return render_template("guild_squads_all.html", guild=guild, rows=rows)


@app.route("/guild/<slug>/mods-characters")
def guild_mods_characters(slug):
    import re as _re
    slug_clean = _re.sub(r"[^a-z0-9-]", "", slug.lower())
    gf = BASE_DIR / "data" / "guilds" / f"{slug_clean}.json"
    if not gf.exists():
        return f"Guild {slug_clean!r} not found", 404
    guild = json.loads(gf.read_text())
    rs_all = load_roster_stats()
    char_mods = {}  # base_id -> {speeds: [], owners: []}
    for m in guild.get("members", []):
        ac = m.get("ally_code") or ""
        rs = rs_all.get(ac, {})
        for bid, u in (rs.get("units") or {}).items():
            spd = u.get("speed_secondary_count", 0)
            if spd == 0 and not u.get("mods"):
                continue
            entry = char_mods.setdefault(bid, {"speeds": [], "owners": 0})
            entry["speeds"].append(spd)
            entry["owners"] += 1
    rows = [{"base_id": bid,
             "owners": d["owners"],
             "avg_speed_sec": round(sum(d["speeds"])/len(d["speeds"]), 2) if d["speeds"] else 0,
             "max_speed_sec": max(d["speeds"]) if d["speeds"] else 0}
            for bid, d in char_mods.items()]
    rows.sort(key=lambda r: -r["avg_speed_sec"])
    return render_template("guild_mods_characters.html", guild=guild, rows=rows[:200])


@app.route("/alliance/health")
def alliance_health():
    snaps = load_stats_snapshots()
    rs_all = load_roster_stats()
    tracked = load_tracked_guilds()
    guilds = []
    for g in tracked:
        guild_name = g.get("name", "?")
        members = g.get("members", [])
        n = len(members) or 1
        member_acs = [m.get("ally_code") for m in members if m.get("ally_code")]
        # Compute live health
        metrics = []
        for ac in member_acs:
            rs = rs_all.get(ac, {})
            if not rs:
                continue
            cgp = next((m.get("chars_gp", 1) for m in members if m.get("ally_code") == ac), 1) or 1
            spd = rs.get("speed_secondary_count", 0)
            gl  = sum(1 for bid in (rs.get("units") or {}) if bid in GL_BASE_IDS)
            metrics.append({
                "relic_total": rs.get("relic_total", 0),
                "r5_plus":     rs.get("r5_plus", 0),
                "seven_star":  rs.get("seven_star", 1),
                "mod_score":   round(spd / cgp * 100_000, 2) if cgp else 0,
                "gl_count":    gl,
            })
        if not metrics:
            continue
        avg_relic  = sum(m["relic_total"] for m in metrics) / len(metrics)
        avg_mod    = sum(m["mod_score"] for m in metrics) / len(metrics)
        total_gl   = sum(m["gl_count"] for m in metrics)
        r5_total   = sum(m["r5_plus"] for m in metrics)
        star_total = sum(m["seven_star"] for m in metrics) or 1
        r5_pct     = r5_total / star_total
        health = min(100, round(
            min(25, avg_relic / 600 * 25) +
            min(20, avg_mod / 5 * 20) +
            min(30, (total_gl / n) / 5 * 30) +
            min(25, r5_pct * 25), 1
        ))
        guilds.append({
            "name":          guild_name,
            "health_score":  health,
            "gp":            g.get("guild_gp") or g.get("gp") or 0,
            "avg_relic":     round(avg_relic, 1),
            "avg_mod_score": round(avg_mod, 2),
            "gl_count":      total_gl,
            "gl_per_player": round(total_gl/n, 2),
            "r5_pct":        round(r5_pct*100, 1),
            "members":       n,
        })
    guilds.sort(key=lambda g: -g["health_score"])
    # Historical health trend from snapshots
    health_history = {"y": "Health Score", "dates": [], "series": []}
    if len(snaps) >= 2:
        gnames = set(guilds_dict for s in snaps for guilds_dict in s.get("guilds", {}))
        dates = []
        for s in snaps:
            ts = s.get("timestamp", "")[:10]
            if ts:
                y, m, d = ts.split("-")
                dates.append(f"{m}/{d}/{y}")
        health_history["dates"] = dates
        for gname in sorted(gnames):
            vals = [s.get("guilds", {}).get(gname, {}).get("health_score", -1) for s in snaps]
            health_history["series"].append({"name": gname, "id": gname, "values": {"total": vals}})
    return render_template("alliance_health.html", guilds=guilds, health_history=health_history)


# --- Extended trend endpoints ---
@app.route("/data/trends/alliance-zetas.json")
def trends_alliance_zetas():
    snaps = load_stats_snapshots()
    return stats_to_chart(snaps, lambda s: [("Zetas", "alliance")],
                          lambda s, _: s.get("alliance", {}).get("zeta_count"),
                          y_label="Total Zetas")


@app.route("/data/trends/alliance-omicrons.json")
def trends_alliance_omicrons():
    snaps = load_stats_snapshots()
    return stats_to_chart(snaps, lambda s: [("Omicrons", "alliance")],
                          lambda s, _: s.get("alliance", {}).get("omicron_count"),
                          y_label="Total Omicrons")


@app.route("/data/trends/alliance-mod-score.json")
def trends_alliance_mod_score():
    snaps = load_stats_snapshots()
    return stats_to_chart(snaps, lambda s: [("Avg Mod Score", "alliance")],
                          lambda s, _: s.get("alliance", {}).get("avg_mod_score"),
                          y_label="Avg Mod Score")


@app.route("/data/trends/alliance-gl.json")
def trends_alliance_gl():
    snaps = load_stats_snapshots()
    return stats_to_chart(snaps, lambda s: [("GL Count", "alliance")],
                          lambda s, _: s.get("alliance", {}).get("gl_count"),
                          y_label="Total GLs")


@app.route("/data/trends/guild-health.json")
def trends_guild_health():
    snaps = load_stats_snapshots()
    all_guilds = set()
    for s in snaps:
        all_guilds.update(s.get("guilds", {}).keys())
    return stats_to_chart(snaps,
                          lambda s: [(g, g) for g in all_guilds],
                          lambda s, g: s.get("guilds", {}).get(g, {}).get("health_score"),
                          y_label="Health Score")


@app.route("/data/trends/guild-zetas.json")
def trends_guild_zetas():
    snaps = load_stats_snapshots()
    all_guilds = set()
    for s in snaps:
        all_guilds.update(s.get("guilds", {}).keys())
    return stats_to_chart(snaps,
                          lambda s: [(g, g) for g in all_guilds],
                          lambda s, g: s.get("guilds", {}).get(g, {}).get("zeta_count"),
                          y_label="Total Zetas")


@app.route("/data/trends/player/<ally_code>/gp.json")
def trends_player_gp(ally_code):
    snaps = load_stats_snapshots()
    name = next((s.get("players", {}).get(ally_code, {}).get("name", ally_code)
                 for s in snaps if s.get("players", {}).get(ally_code)), ally_code)
    return stats_to_chart(snaps, lambda s: [(name, ally_code)],
                          lambda s, ac: s.get("players", {}).get(ac, {}).get("gp"),
                          y_label="GP")


@app.route("/data/trends/player/<ally_code>/zetas.json")
def trends_player_zetas(ally_code):
    snaps = load_stats_snapshots()
    name = next((s.get("players", {}).get(ally_code, {}).get("name", ally_code)
                 for s in snaps if s.get("players", {}).get(ally_code)), ally_code)
    return stats_to_chart(snaps, lambda s: [(name, ally_code)],
                          lambda s, ac: s.get("players", {}).get(ac, {}).get("zeta_count"),
                          y_label="Zetas")


@app.route("/guild/<slug>/tw-history")
def guild_tw_history(slug):
    import re as _re
    slug_clean = _re.sub(r"[^a-z0-9-]", "", slug.lower())
    gf = BASE_DIR / "data" / "guilds" / f"{slug_clean}.json"
    if not gf.exists():
        return f"Guild not found: {slug_clean}", 404
    guild = json.loads(gf.read_text())
    raw_tw = guild.get("recent_tw_results", [])
    results = []
    for tw in raw_tw:
        our_score    = int(tw.get("score", 0) or tw.get("bannerScore", 0) or 0)
        opp_score    = int(tw.get("opponentScore", 0) or tw.get("opponentBannerScore", 0) or 0)
        opp_name     = tw.get("opponentGuildName") or tw.get("opponentName") or "Unknown"
        opp_gp       = int(tw.get("opponentGuildGP", 0) or 0)
        end_time     = tw.get("endTime") or tw.get("startTime") or ""
        win          = our_score > opp_score
        results.append({
            "our_score":  our_score,
            "opp_score":  opp_score,
            "opp_name":   opp_name,
            "opp_gp":     opp_gp,
            "end_time":   end_time,
            "win":        win,
            "margin":     our_score - opp_score,
        })
    wins   = sum(1 for r in results if r["win"])
    losses = len(results) - wins
    return render_template("guild_tw_history.html", guild=guild, results=results, wins=wins, losses=losses)


@app.route("/guild/<slug>/contributions")
def guild_contributions(slug):
    import re as _re
    slug_clean = _re.sub(r"[^a-z0-9-]", "", slug.lower())
    gf = BASE_DIR / "data" / "guilds" / f"{slug_clean}.json"
    if not gf.exists():
        return f"Guild not found: {slug_clean}", 404
    guild = json.loads(gf.read_text())
    members = sorted(guild.get("members", []),
                     key=lambda m: -(m.get("contributions", {}).get("raid_tickets", {}).get("current", 0) or 0))
    return render_template("guild_contributions.html", guild=guild, members=members)


@app.route("/alliance/gac")
def alliance_gac():
    """Alliance-wide GAC league standings from guild member data."""
    tracked = load_tracked_guilds()
    rows = []
    for g in tracked:
        for m in g.get("members", []):
            history = m.get("gac_history", [])
            latest = history[0] if history else {}
            rows.append({
                "name":         m.get("name", "?"),
                "ally_code":    m.get("ally_code", ""),
                "guild":        g.get("name", "?"),
                "league":       latest.get("league") or m.get("league_id") or "—",
                "division":     latest.get("division") or "—",
                "wins":         latest.get("wins", 0),
                "losses":       latest.get("losses", 0),
                "season_points":latest.get("season_points", 0),
                "rank":         latest.get("rank"),
                "lifetime_score": m.get("lifetime_season_score", 0),
                "history":      history,
            })
    # Sort by league tier then points
    LEAGUE_ORDER = {"KYBER": 0, "AURODIUM": 1, "CHROMIUM": 2, "BRONZIUM": 3, "CARBONITE": 4}
    rows.sort(key=lambda r: (LEAGUE_ORDER.get((r["league"] or "").upper(), 99), -(r["season_points"] or 0)))
    return render_template("alliance_gac.html", rows=rows)


@app.route("/guild/<slug>/tb-platoons")
def guild_tb_platoons(slug):
    import re as _re
    slug_clean = _re.sub(r"[^a-z0-9-]", "", slug.lower())
    gf = BASE_DIR / "data" / "guilds" / f"{slug_clean}.json"
    if not gf.exists():
        return f"Guild not found: {slug_clean}", 404
    guild = json.loads(gf.read_text())
    tb_platoons = load_tb_platoons()
    rs_all = load_roster_stats()
    # Build per-unit ownership for this guild
    member_acs = [m.get("ally_code") for m in guild.get("members", [])]
    unit_owners = {}   # base_id -> list of player names who own it at 7*
    for ac in member_acs:
        rs = rs_all.get(ac, {})
        name = rs.get("name") or ac
        for bid, u in (rs.get("units") or {}).items():
            if (u.get("rarity") or 0) >= 7:
                unit_owners.setdefault(bid, []).append(name)
    n = len(member_acs) or 1
    return render_template("guild_tb_platoons.html", guild=guild, tb_platoons=tb_platoons,
                           unit_owners=unit_owners, n=n)


@app.route("/data/stats/<ally_code>.json")
def player_stats_json(ally_code):
    stats = load_player_stats(ally_code)
    from flask import jsonify
    return jsonify(stats)


@app.route("/transfers")
def transfers():
    log = sorted(load_transfers(), key=lambda t: t["timestamp"], reverse=True)
    return render_template("transfers.html", transfers=log)


@app.route("/")
def index():
    """Home page — redirect to community overview."""
    from flask import redirect, url_for
    return redirect(url_for("community"))



if __name__ == "__main__":
    app.run(debug=True, port=5050, host="127.0.0.1")
