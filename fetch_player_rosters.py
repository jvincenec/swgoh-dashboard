"""
fetch_player_rosters.py — Phase 2. Full /player fetch for every alliance member.
Captures: relic/gear/rarity/level per unit, all mod secondary stats, zeta count,
omicron list, datacrons, lifetime stats, squad/fleet arena rank, squad viability.
NOT available from Comlink: unequipped mods, currencies, shard inventory.
Run: .\venv\Scripts\python.exe fetch_player_rosters.py
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent / "analysis"))
from squad_templates import detect_teams
from name_resolver import GameDataResolver

_mod_resolver = GameDataResolver()

COMLINK_URL         = "http://localhost:3000"
DATA_DIR            = Path(__file__).parent / "data"
GUILDS_DIR          = DATA_DIR / "guilds"
ROSTERS_DIR         = DATA_DIR / "rosters"
ROSTERS_HISTORY_DIR = ROSTERS_DIR / "history"
GAME_DATA_DIR       = Path(__file__).parent / "game_data"
ROSTERS_DIR.mkdir(parents=True, exist_ok=True)
ROSTERS_HISTORY_DIR.mkdir(parents=True, exist_ok=True)

REQUEST_PACE_SECONDS = 0.6

STAT_NAMES = {1:"Health",5:"Speed",14:"Crit Chance",16:"Crit Damage",
              17:"Potency",18:"Offense",28:"Protection",55:"Defense"}

NAMED_TOONS = {
    "JKR":"JEDIKNIGHTREVAN","DR":"DARTHREVAN","Malak":"DARTHMALAK",
    "GAS":"GENERALSKYWALKER","JML":"GRANDMASTERLUKE","JMK":"JEDIMASTERKENOBI",
    "JKL":"JEDIKNIGHTLUKE","LV":"LORDVADER","Rey":"GLREY","SEE":"SITHPALPATINE",
    "SLK":"SUPREMELEADERKYLOREN","Ahsoka":"GLAHSOKATANO","Jabba":"JABBATHEHUTT",
    "Neg":"NEGOTIATOR","Mal":"MALEVOLENCE","Exec":"CAPITALEXECUTOR",
    "Chimaera":"CAPITALCHIMAERA",
}


def load_zeta_map():
    p = GAME_DATA_DIR / "zeta_map.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


ZETA_MAP = load_zeta_map()


def load_ship_ids():
    p = GAME_DATA_DIR / "ship_ids.json"
    if not p.exists():
        return set()
    try:
        return set(json.loads(p.read_text(encoding="utf-8")))
    except Exception:
        return set()


def load_omicron_abilities():
    """Returns {ability_id: mode_string} — maps purchasedAbilityId values to omicron modes.
    Built from skill.abilityReference where skill.omicronMode is a real game mode."""
    p = GAME_DATA_DIR / "omicron_abilities.json"
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        # New format: already a flat dict {ability_id: mode}
        if isinstance(data, dict):
            return data
        # Old format: list of {id, mode}
        return {entry["id"]: entry["mode"] for entry in data}
    except Exception:
        return {}


SHIP_IDS         = load_ship_ids()
OMICRON_ABILITIES = load_omicron_abilities()


def comlink_post(endpoint, payload):
    resp = requests.post(f"{COMLINK_URL}{endpoint}",
                         json={"payload": payload, "enums": False}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def relic_tier_to_level(tier):
    return max(0, tier - 2)


def decode_secondaries(secondary_stats):
    out = {}
    for sec in secondary_stats:
        ss = sec.get("stat") or {}
        stat_id = ss.get("unitStatId") or ss.get("unitStat")
        raw_val = ss.get("statValueDecimal") or ss.get("unscaledDecimalValue") or "0"
        try:
            val = float(raw_val)
        except (TypeError, ValueError):
            val = 0.0
        name = STAT_NAMES.get(stat_id, f"stat_{stat_id}")
        out[name] = round(val, 2)
    return out


def compute_player_stats(player):
    roster = player.get("rosterUnit", [])
    base_ids_owned = set()
    units_owned = {}
    relic_total = seven_star = r5_plus = g13_plus = g12_plus = g10_plus = 0
    speed_secondary_count = zeta_count = 0
    all_omicrons = []

    for unit in roster:
        base_id = unit.get("definitionId", "").split(":")[0]
        base_ids_owned.add(base_id)   # track ALL units (chars+ships) for named toon detection

        # Skip ships for char-specific stats (gear/relic/zeta/mods).
        # combatType is NOT in player roster data — use game_data/ship_ids.json instead.
        if SHIP_IDS and base_id in SHIP_IDS:
            continue

        relic_level = relic_tier_to_level((unit.get("relic") or {}).get("currentTier", 0))
        gear        = unit.get("currentTier", 0)
        rarity      = unit.get("currentRarity", 0)
        char_level  = unit.get("currentLevel", 0)

        # --- Mods ---
        unit_speed_sec = 0
        equipped_mods = []
        for m in unit.get("equippedStatMod") or []:
            resolved = _mod_resolver.resolve_mod(m.get("definitionId", ""))
            resolved["level"] = m.get("level", 0)
            primary = m.get("primaryStat") or {}
            if primary:
                ps = primary.get("stat") or {}
                resolved["primary_id"] = ps.get("unitStatId")
                raw_pval = ps.get("statValueDecimal") or ps.get("unscaledDecimalValue") or "0"
                try:
                    resolved["primary_val"] = float(raw_pval)
                except (TypeError, ValueError):
                    resolved["primary_val"] = 0.0
            secondaries = decode_secondaries(m.get("secondaryStat") or [])
            resolved["secondaries"] = secondaries
            speed_val = secondaries.get("Speed", 0.0)
            if speed_val >= 15:
                unit_speed_sec += 1
                speed_secondary_count += 1
            resolved["speed_secondary"] = round(speed_val, 1)
            equipped_mods.append(resolved)

        # --- Zetas ---
        # player.skill.tier + 2 == in-game tier index (1-based), confirmed from name_resolver.py
        # A skill is zetaed when player_tier >= zeta_player_tier (stored in zeta_map).
        # Only applies to characters (ships are already filtered above).
        unit_zetas = []
        for sk in unit.get("skill") or []:
            sk_id   = sk.get("id") or ""
            sk_tier = sk.get("tier", 0)
            info = ZETA_MAP.get(sk_id)
            if info is None:
                continue
            zpt = info.get("zeta_player_tier")
            # zpt >= 1: skip GL auto-zetas (zeta_pt=0 = applied during event, not via material)
            # Probe confirmed: GL skills have zeta_pt=0 because isZetaTier at idx=1 -> max(0,0)=0
            if info.get("is_zeta") and zpt is not None and zpt >= 1 and sk_tier >= zpt:
                zeta_count += 1
                unit_zetas.append(sk_id)

        # --- Omicrons ---
        # purchasedAbilityId contains ability IDs that exactly match omicron_abilities.json.
        # probe confirmed: player has ['ultimateability_grandmasterluke'] for JML omicron.
        unit_omicrons = []   # list of ability_id strings (for roster display)
        purchased_refs = list(unit.get("purchasedAbilityId") or [])
        for ref in purchased_refs:
            if not ref:
                continue
            unit_omicrons.append(ref)   # store ability_id string only

        for ref in unit_omicrons:
            mode = OMICRON_ABILITIES.get(ref, "Unknown")
            all_omicrons.append({
                "base_id":    base_id,
                "ability_id": ref,
                "mode":       mode,
            })

        units_owned[base_id] = {
            "relic": relic_level, "gear": gear, "rarity": rarity, "level": char_level,
            "mods": equipped_mods, "speed_secondary_count": unit_speed_sec,
            "zeta_skills": unit_zetas, "omicron_skills": unit_omicrons,
        }

        relic_total += relic_level
        if relic_level >= 5: r5_plus  += 1
        if gear >= 13:        g13_plus += 1
        if gear >= 12:        g12_plus += 1
        if gear >= 10:        g10_plus += 1
        if rarity >= 7:       seven_star += 1

    named_ownership = {label: (1 if bid in base_ids_owned else 0)
                       for label, bid in NAMED_TOONS.items()}

    return {
        "relic_total": relic_total, "seven_star": seven_star,
        "r5_plus": r5_plus, "g13_plus": g13_plus,
        "g12_plus": g12_plus, "g10_plus": g10_plus,
        "named": named_ownership, "units": units_owned,
        "speed_secondary_count": speed_secondary_count,
        "zeta_count": zeta_count, "omicrons": all_omicrons,
    }


def main():
    if not GUILDS_DIR.exists() or not any(GUILDS_DIR.glob("*.json")):
        print("ERROR: no files in data/guilds/. Run fetch_guilds.py first.")
        return

    members = {}
    for guild_file in sorted(GUILDS_DIR.glob("*.json")):
        try:
            guild = json.loads(guild_file.read_text())
        except Exception:
            continue
        guild_name = guild.get("name", guild_file.stem)
        for m in guild.get("members", []):
            ac = m.get("ally_code") or m.get("playerId")
            if ac and ac not in members:
                members[ac] = {"name": m.get("name", "?"), "guild_name": guild_name}

    if not members:
        print("ERROR: no members found.")
        return

    total = len(members)
    print(f"Fetching full rosters for {total} unique player(s) ... (~{total * REQUEST_PACE_SECONDS / 60:.1f} min minimum)")
    if ZETA_MAP:
        zetas_in_map = sum(1 for v in ZETA_MAP.values() if v.get("is_zeta") and not v.get("is_omicron"))
        omics_in_map = sum(1 for v in ZETA_MAP.values() if v.get("is_omicron"))
        print(f"  Zeta map: {zetas_in_map} zetas, {omics_in_map} omicrons")
    else:
        print("  NOTE: zeta_map.json missing — run analysis\\build_zeta_map.py first for zeta/omicron counts.")

    results = {}
    for i, (ally_code, meta) in enumerate(members.items(), 1):
        try:
            player = comlink_post("/player", {"playerId": ally_code})
        except requests.exceptions.RequestException as e:
            print(f"  [{i}/{total}] SKIP {meta['name']}: {e}")
            time.sleep(REQUEST_PACE_SECONDS)
            continue

        stats = compute_player_stats(player)
        stats["ally_code"]    = ally_code
        stats["name"]         = player.get("name", meta["name"])
        stats["guild_name"]   = meta["guild_name"]
        stats["player_level"]     = player.get("level", 0)
        stats["guild_role"]       = player.get("guildMemberLevel") or player.get("memberLevel") or ""
        last_act = player.get("lastActivityTime") or player.get("profileStat") and next(
            (int(ps.get("value", 0)) for ps in (player.get("profileStat") or []) if ps.get("nameKey") == "LAST_ACTIVE_TIME"), None)
        stats["last_activity_time"] = last_act

        for p in player.get("pvpProfile") or []:
            if p.get("tab") == 0:
                stats["squad_arena_rank"] = p.get("rank")
            elif p.get("tab") == 1:
                stats["fleet_arena_rank"] = p.get("rank")

        stats["datacron_count"] = len(player.get("datacronList") or [])
        stats["datacrons"] = [
            {"id": dc.get("id"), "defId": dc.get("definitionId") or dc.get("defId") or "",
             "level": dc.get("level", 0), "rerollCount": dc.get("rerollCount", 0)}
            for dc in (player.get("datacronList") or [])
        ]

        profile_stats = {}
        for ps in player.get("profileStat") or []:
            key = ps.get("nameKey", "")
            if key in ("BATTLES_WON", "PVP_BATTLES_WON", "GUILD_RAID_WON", "TOTAL_DAMAGE_DONE"):
                profile_stats[key] = int(ps.get("value", 0) or 0)
        stats["lifetime_stats"] = profile_stats

        squads = detect_teams(player.get("rosterUnit", []))
        stats["squads"]       = [s for s in squads if s["viable"]]
        stats["squads_close"] = [s for s in squads if not s["viable"]]

        results[ally_code] = stats
        print(f"  [{i}/{total}] {stats['name']}: relic {stats['relic_total']}, "
              f"{stats['seven_star']} 7★, R5+ {stats['r5_plus']}, "
              f"zetas {stats['zeta_count']}, omicrons {len(stats['omicrons'])}")
        time.sleep(REQUEST_PACE_SECONDS)

    out_path = ROSTERS_DIR / "roster_stats.json"
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\nSaved {len(results)} player roster stat(s) -> {out_path}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (ROSTERS_HISTORY_DIR / f"{stamp}.json").write_text(json.dumps(results, indent=2))
    print(f"Archived -> {ROSTERS_HISTORY_DIR / (stamp + '.json')}")


if __name__ == "__main__":
    main()
