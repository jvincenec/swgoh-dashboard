"""
member_activity_report.py — Parse the guild data already pulled by
fetch.py for per-member activity: guild activity contributions, raid
ticket usage, gear donations, GAC season history, and inactivity.

Usage:
    python analysis/member_activity_report.py [inactive_days_threshold]

Requires data/guild.json to exist — run fetch.py first.

What this is built on (verified against the official Comlink wiki):
    - member.memberContribution: per-member contribution data with type
      1 = Guild Activities (Guild Tokens), 2 = Raid Tickets,
      3 = Gear Donations. Each entry has a currentValue (since last Guild
      Reset) and a lifetime value.
    - member.seasonStatus: the last three GAC seasons for this member —
      points, league, division, start/end times.
    - member.lastActivityTime: epoch seconds of the player's last login.

Honesty notes:
    - currentValue for contributions resets to 0 at Guild Reset. A snapshot
      taken right after someone's reset will show 0 even if they're active
      — this is a real quirk of the data, not a bug here. For a reliable
      daily number you either need to fetch close to reset time, or track
      lifetime values over repeated fetches and diff them yourself (not
      implemented here — this script shows a single snapshot only).
    - seasonStatus only ever contains the last 3 GAC seasons; there is no
      deeper history available via Comlink.
"""

import json
import sys
import time
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

CONTRIBUTION_TYPE_LABELS = {
    1: "guild_activities",
    2: "raid_tickets",
    3: "gear_donations",
}

DEFAULT_INACTIVE_DAYS = 3


def load_guild_data() -> dict:
    path = DATA_DIR / "guild.json"
    if not path.exists():
        print(f"ERROR: {path} not found. Run fetch.py first.")
        sys.exit(1)
    return json.loads(path.read_text())


def parse_contributions(member: dict) -> dict:
    contributions = {label: {"current": 0, "lifetime": 0} for label in CONTRIBUTION_TYPE_LABELS.values()}
    for entry in member.get("memberContribution", []):
        c_type = entry.get("type")
        label = CONTRIBUTION_TYPE_LABELS.get(c_type)
        if not label:
            continue
        contributions[label] = {
            "current": entry.get("currentValue", 0),
            "lifetime": entry.get("lifetimeValue", entry.get("currentValue", 0)),
        }
    return contributions


def parse_gac_history(member: dict) -> list:
    seasons = []
    for s in member.get("seasonStatus", []):
        seasons.append(
            {
                "league": s.get("league"),
                "division": s.get("division"),
                "points": s.get("points") or s.get("score"),
                "end_time": s.get("endTime"),
            }
        )
    return seasons


def parse_inactivity(member: dict, threshold_days: int, now_epoch: int) -> dict:
    last_active_raw = member.get("lastActivityTime")
    if last_active_raw is None:
        return {"last_active_epoch": None, "days_inactive": None, "flagged": False}

    try:
        last_active_epoch = int(last_active_raw) / 1000  # ms -> s, per Comlink wiki example
    except (TypeError, ValueError):
        return {"last_active_epoch": None, "days_inactive": None, "flagged": False}

    days_inactive = (now_epoch - last_active_epoch) / 86400
    return {
        "last_active_epoch": last_active_epoch,
        "days_inactive": round(days_inactive, 1),
        "flagged": days_inactive >= threshold_days,
    }


def build_report(guild_data: dict, threshold_days: int) -> list:
    now_epoch = time.time()
    report = []
    for member in guild_data.get("member", []):
        report.append(
            {
                "name": member.get("playerName", "?"),
                "gp": member.get("galacticPower"),
                "contributions": parse_contributions(member),
                "gac_history": parse_gac_history(member),
                "inactivity": parse_inactivity(member, threshold_days, now_epoch),
            }
        )
    return report


def print_report(report: list, threshold_days: int):
    print("=" * 70)
    print("PER-MEMBER ACTIVITY REPORT")
    print("=" * 70)
    print(f"Inactivity threshold: {threshold_days} day(s)\n")

    for m in sorted(report, key=lambda x: -(x["gp"] if isinstance(x.get("gp"), int) else 0)):
        flag = " [INACTIVE]" if m["inactivity"]["flagged"] else ""
        print(f"\n{m['name']}{flag}")
        days = m["inactivity"]["days_inactive"]
        print(f"  Last active: {days} day(s) ago" if days is not None else "  Last active: unknown")

        c = m["contributions"]
        print(
            f"  Guild Activities: {c['guild_activities']['current']} (current) / "
            f"{c['guild_activities']['lifetime']} (lifetime)"
        )
        print(
            f"  Raid Tickets:     {c['raid_tickets']['current']} (current) / "
            f"{c['raid_tickets']['lifetime']} (lifetime)"
        )
        print(
            f"  Gear Donations:   {c['gear_donations']['current']} (current) / "
            f"{c['gear_donations']['lifetime']} (lifetime)"
        )

        if m["gac_history"]:
            print("  GAC history (last 3 seasons):")
            for s in m["gac_history"]:
                print(f"    League {s['league']}, Division {s['division']}, Points {s['points']}")
        else:
            print("  GAC history: none found")


def main():
    threshold_days = DEFAULT_INACTIVE_DAYS
    if len(sys.argv) > 1:
        try:
            threshold_days = int(sys.argv[1])
        except ValueError:
            print(f"Invalid threshold '{sys.argv[1]}', using default {DEFAULT_INACTIVE_DAYS}")

    guild_data = load_guild_data()
    report = build_report(guild_data, threshold_days)

    out_path = DATA_DIR / "member_activity_report.json"
    out_path.write_text(json.dumps({"threshold_days": threshold_days, "members": report}, indent=2))
    print(f"Saved report -> {out_path}\n")

    print_report(report, threshold_days)


if __name__ == "__main__":
    main()
