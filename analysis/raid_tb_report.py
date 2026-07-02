"""
raid_tb_report.py — Parse the guild data already pulled by fetch.py and
produce a readable report of the last raid attempt(s) and last Territory
Battle result.

Usage:
    python analysis/raid_tb_report.py

Requires data/guild.json to exist — run fetch.py first.

What this is built on (verified against the official Comlink wiki):
    - guild.recentRaidResult: last attempt for EACH raid type, including
      per-member damage contribution (raidMember), completion status
      (outcome), and how long it took (duration).
    - guild.profile.guildEventTracker: Territory Battles completed in the
      last 60 days, but ONLY the single best-starred run per TB, not a
      full history and not a per-member contribution breakdown.

Honesty notes:
    - This is real, structured data returned by Comlink — not an inference,
      unlike squad detection.
    - TB data is limited to "best run in the last 60 days" — there is no
      way to see every individual TB attempt or per-member TB section
      contributions via Comlink.
    - There is no readiness/gear-requirement guidance baked in here. I
      looked for a reliable, clearly-dated source for current raid gear
      thresholds and didn't find one solid enough to encode without risking
      the same staleness problem we caught with old GAC squad data. Treat
      the raw numbers below as the source of truth, not a target to hit.
"""

import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

# outcome codes per the Comlink wiki
OUTCOME_LABELS = {
    0: "Not attempted",
    1: "Completed",
    2: "Expired",
    3: "In Progress",
    4: "Abandoned",
    5: "Simmed",
}


def load_guild_data() -> dict:
    path = DATA_DIR / "guild.json"
    if not path.exists():
        print(f"ERROR: {path} not found. Run fetch.py first.")
        sys.exit(1)
    return json.loads(path.read_text())


def build_member_name_lookup(guild_data: dict) -> dict:
    return {
        m.get("playerId"): m.get("playerName", "?")
        for m in guild_data.get("member", [])
    }


def parse_raid_results(guild_data: dict, name_lookup: dict) -> list:
    raids = []
    for raid in guild_data.get("recentRaidResult", []):
        outcome_code = raid.get("outcome", 0)
        members = []
        for rm in raid.get("raidMember", []):
            player_id = rm.get("playerId")
            members.append(
                {
                    "name": name_lookup.get(player_id, player_id),
                    "damage": rm.get("memberProgress", 0),
                    "rank": rm.get("rank"),
                }
            )
        members.sort(key=lambda x: -(x["damage"] if isinstance(x["damage"], int) else 0))

        raids.append(
            {
                "raid_id": raid.get("raidId"),
                "outcome": OUTCOME_LABELS.get(outcome_code, f"Unknown ({outcome_code})"),
                "duration_seconds": raid.get("duration"),
                "end_time": raid.get("endTime"),
                "members": members,
            }
        )
    return raids


def parse_tb_results(guild_data: dict) -> list:
    tracker = guild_data.get("profile", {}).get("guildEventTracker", [])
    results = []
    for tb in tracker:
        tb_id = tb.get("territoryBattleDefId")
        if tb_id is None:
            tb_id = tb.get("id", "?")
        stars = tb.get("starsEarned")
        if stars is None:
            stars = tb.get("stars")
        results.append(
            {
                "tb_id": tb_id,
                "stars": stars,
                "end_time": tb.get("endTime"),
            }
        )
    return results


def parse_tw_history(guild_data: dict) -> list:
    """recentTerritoryWarResult: the past 8 Territory Wars with your
    guild's score, the opponent's score, and total GP from signed-up
    members. Real, structured data — not an inference."""
    def first_present(d: dict, *keys):
        for k in keys:
            if d.get(k) is not None:
                return d.get(k)
        return None

    results = []
    for tw in guild_data.get("recentTerritoryWarResult", []):
        own_score = first_present(tw, "guildScore", "score")
        opp_score = first_present(tw, "opponentScore", "enemyScore")
        won = None
        if isinstance(own_score, (int, float)) and isinstance(opp_score, (int, float)):
            won = own_score > opp_score
        results.append(
            {
                "end_time": tw.get("endTime"),
                "own_score": own_score,
                "opponent_score": opp_score,
                "opponent_name": first_present(tw, "opponentName", "opponentGuildName"),
                "own_gp": first_present(tw, "guildGalacticPower", "galacticPower"),
                "won": won,
            }
        )
    return results


def parse_raid_launch_config(guild_data: dict) -> list:
    """Which raids are currently configured for auto-launch / sim
    eligibility for this guild."""
    configs = []
    for cfg in guild_data.get("profile", {}).get("raidLaunchConfig", []):
        sim_eligible = cfg.get("simAllowed")
        if sim_eligible is None:
            sim_eligible = cfg.get("simEligible")
        configs.append(
            {
                "raid_id": cfg.get("raidId") or cfg.get("id"),
                "auto_launch": cfg.get("autoLaunch"),
                "sim_eligible": sim_eligible,
            }
        )
    return configs


def print_raid_report(raids: list):
    print("=" * 60)
    print("LAST RAID RESULTS (per raid type)")
    print("=" * 60)
    if not raids:
        print("  No raid results found in guild data.")
        return
    for r in raids:
        print(f"\n  Raid: {r['raid_id']}")
        print(f"  Outcome: {r['outcome']}   Duration: {r['duration_seconds']}s")
        print(f"  {'Member':<25}{'Damage':>15}{'Rank':>8}")
        for m in r["members"][:50]:
            print(f"  {m['name']:<25}{m['damage']:>15}{str(m['rank']):>8}")


def print_tb_report(tbs: list):
    print("\n" + "=" * 60)
    print("LAST TERRITORY BATTLE RESULT (best run, last 60 days)")
    print("=" * 60)
    if not tbs:
        print("  No Territory Battle results found in guild data.")
        print("  Note: Comlink only returns the single highest-star run per")
        print("  TB within the last 60 days — not a full history and not a")
        print("  per-member contribution breakdown.")
        return
    for tb in tbs:
        print(f"\n  Territory Battle: {tb['tb_id']}")
        print(f"  Stars earned: {tb['stars']}")
        print(f"  End time (epoch): {tb['end_time']}")


def print_tw_report(tws: list):
    print("\n" + "=" * 60)
    print("TERRITORY WAR HISTORY (last 8 wars)")
    print("=" * 60)
    if not tws:
        print("  No Territory War results found in guild data.")
        return
    for tw in tws:
        result = "WON" if tw["won"] is True else "LOST" if tw["won"] is False else "?"
        opp = tw["opponent_name"] or "unknown opponent"
        print(
            f"  [{result:<4}] vs {opp:<25} "
            f"{tw['own_score']} - {tw['opponent_score']}"
        )


def print_raid_config(configs: list):
    print("\n" + "=" * 60)
    print("RAID LAUNCH CONFIG (currently active for this guild)")
    print("=" * 60)
    if not configs:
        print("  No raid launch config found in guild data.")
        return
    for c in configs:
        print(f"  {c['raid_id']:<25} auto_launch={c['auto_launch']}  sim_eligible={c['sim_eligible']}")


def main():
    guild_data = load_guild_data()
    name_lookup = build_member_name_lookup(guild_data)

    raids = parse_raid_results(guild_data, name_lookup)
    tbs = parse_tb_results(guild_data)
    tws = parse_tw_history(guild_data)
    raid_configs = parse_raid_launch_config(guild_data)

    report = {
        "raids": raids,
        "territory_battles": tbs,
        "territory_wars": tws,
        "raid_launch_config": raid_configs,
    }
    out_path = DATA_DIR / "raid_tb_report.json"
    out_path.write_text(json.dumps(report, indent=2))
    print(f"Saved report -> {out_path}\n")

    print_raid_report(raids)
    print_tb_report(tbs)
    print_tw_report(tws)
    print_raid_config(raid_configs)


if __name__ == "__main__":
    main()
