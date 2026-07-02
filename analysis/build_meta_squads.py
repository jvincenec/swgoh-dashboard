"""
build_meta_squads.py — Builds verified squad_templates entries from current
SWGOH.GG GAC meta data (Season 80, 663K battles — real statistical data,
not guessed), resolved against the REAL units collection already cached
locally (game_data/full_data_dump_enums.json from trace_gl_campaign.py).

Why this exists: swgoh.gg uses URL slugs (ezra-bridger-exile), Comlink
uses base IDs (EZRABRIDGEREXILE). These don't always transform
predictably, so this resolves by matching nameKey/localized name against
the real cached units list rather than guessing the ID.

Run with:
    python analysis/build_meta_squads.py

Requires game_data/full_data_dump_enums.json to already exist (from
trace_gl_campaign.py, run earlier this session).
"""

import json
import re
from pathlib import Path

GAME_DATA_DIR = Path(__file__).parent.parent / "game_data"
DUMP_PATH = GAME_DATA_DIR / "full_data_dump_enums.json"

# Current GAC meta squads, Season 80 (663K battles analyzed), swgoh.gg/gac/squads/
# Format: (squad_label, hold_pct, banners, [character display names])
# Each entry: (label, mode, hold_pct_or_None, banners_or_None, [character names])
# mode values: gac_5v5, gac_3v3, tw, raid_order66, raid_tank, raid_pit, raid_sith,
#   tb_hoth, tb_geo_ds, tb_geo_ls (only modes with actual entries below are populated —
#   rest are real gaps, not silently guessed)

META_SQUADS = [
    # --- GAC 5v5 meta, Season 80, 663K battles analyzed (swgoh.gg/gac/squads/) ---
    ("Ahsoka / Ezra (Exile) / Syndulla / Huyang / Sabine", "gac_5v5", 20, 50.62,
     ["Ahsoka Tano", "Ezra Bridger (Exile)", "General Syndulla", "Huyang", "Padawan Sabine Wren"]),
    ("Lord Vader / Appo / Disguised Clone / CX-2 / Scorch", "gac_5v5", 28, 45.73,
     ["Lord Vader", "CC-1119 \"Appo\"", "Disguised Clone Trooper", "CX-2", "RC-1262 \"Scorch\""]),
    ("Pirate King Hondo / Brutus / Silvo / SM-33 / Vane", "gac_5v5", 18, 51.38,
     ["Pirate King Hondo Ohnaka", "Brutus", "Captain Silvo", "SM-33", "Vane"]),
    ("Jabba / Boushh / Embo / Krrsantan / Skiff Lando", "gac_5v5", 21, 49.68,
     ["Jabba the Hutt", "Boushh (Leia Organa)", "Embo", "Krrsantan", "Skiff Guard Lando Calrissian"]),
    ("JM Mace Windu / Aayla / Depa / Jocasta / Temple Guard", "gac_5v5", 14, 53.75,
     ["Jedi Master Mace Windu", "Aayla Secura", "Depa Billaba", "Jocasta Nu", "Temple Guard"]),
    ("Boss Nass / Boomadier / Tarpals / Phalanx / Jar Jar", "gac_5v5", 8, 57.7,
     ["Boss Nass", "Gungan Boomadier", "Captain Tarpals", "Gungan Phalanx", "Jar Jar Binks"]),
    ("Cassian (Undercover) / Cinta / Kleya / Luthen / Vel", "gac_5v5", 32, 43.35,
     ["Cassian Andor (Undercover)", "Cinta Kaz", "Kleya Marki", "Luthen Rael", "Vel Sartha"]),
    ("Emperor Palpatine / Tarkin / Mara Jade / Royal Guard / DV Duel's End", "gac_5v5", 25, 47,
     ["Emperor Palpatine", "Grand Moff Tarkin", "Mara Jade (The Emperor's Hand)", "Royal Guard", "Darth Vader (Duel's End)"]),
    ("The Stranger / Barriss / Maul (Hate Fueled) / Starkiller / Visas", "gac_5v5", 51, 30.85,
     ["The Stranger", "Barriss Offee", "Maul (Hate Fueled)", "Starkiller", "Visas Marr"]),
    ("Jabba / Boba Fett / Boushh / Krrsantan / Skiff Lando", "gac_5v5", 18, 51.93,
     ["Jabba the Hutt", "Boba Fett", "Boushh (Leia Organa)", "Krrsantan", "Skiff Guard Lando Calrissian"]),
    ("Third Sister / Eighth Brother / Fifth Brother / Grand Inquisitor / Seventh Sister", "gac_5v5", 24, 47.36,
     ["Third Sister", "Eighth Brother", "Fifth Brother", "Grand Inquisitor", "Seventh Sister"]),
    ("Darth Malgus / Bastila (Fallen) / Malak / Revan / Sith Marauder", "gac_5v5", 13, 53.88,
     ["Darth Malgus", "Bastila Shan (Fallen)", "Darth Malak", "Darth Revan", "Sith Marauder"]),
    ("Baylan Skoll / Dengar / Hondo / Marrok / Shin Hati", "gac_5v5", 23, 48.6,
     ["Baylan Skoll", "Dengar", "Hondo Ohnaka", "Marrok", "Shin Hati"]),
    ("Satele Shan / Bastila / Jedi Knight Revan / Jolee / Juhani", "gac_5v5", 22, 47.08,
     ["Satele Shan", "Bastila Shan", "Jedi Knight Revan", "Jolee Bindo", "Juhani"]),
    ("Great Mothers / Death Trooper (Peridea) / Morgan Elsbeth / NS Spirit / Night Trooper", "gac_5v5", 10, 55.85,
     ["Great Mothers", "Death Trooper (Peridea)", "Morgan Elsbeth", "Nightsister Spirit", "Night Trooper"]),
    ("Major Partagaz / Dedra / Krennic / Imperial Probe Droid / KX Security Droid", "gac_5v5", 26, 46.48,
     ["Major Partagaz", "Dedra Meero", "Director Krennic", "Imperial Probe Droid", "KX Security Droid"]),
    ("Finn / RH Finn / RH Poe / Rose Tico / Zorii", "gac_5v5", 14, 54.91,
     ["Finn", "Resistance Hero Finn", "Resistance Hero Poe", "Rose Tico", "Zorii Bliss"]),
    ("Queen Amidala / GM Yoda / Qui-Gon / Padawan Obi-Wan / Shaak Ti", "gac_5v5", 15, 54.31,
     ["Queen Amidala", "Grand Master Yoda", "Master Qui-Gon Jinn", "Padawan Obi-Wan", "Shaak Ti"]),
    ("Saw Gerrera / Baze / Chirrut / Kyle Katarn / Luthen", "gac_5v5", 21, 49.17,
     ["Saw Gerrera", "Baze Malbus", "Chirrut Imwe", "Kyle Katarn", "Luthen Rael"]),
    ("Rey / 50R-T / Ben Solo / Cal Kestis / General Kenobi", "gac_5v5", 32, 41.74,
     ["Rey", "50R-T", "Ben Solo", "Cal Kestis", "General Kenobi"]),
    # --- Order 66 Raid (launched June 2025) — verified via EA forums dev post +
    # starwars-fans.com raid guide. No statistical hold%/banners data exists for
    # this (it's a raid, not PvP), so hold_pct/banners are None — score-based mode.
    ("JM Mace Windu / Depa / Temple Guard (Jedi Vanguard)", "raid_order66", None, None,
     ["Jedi Master Mace Windu", "Depa Billaba", "Temple Guard"]),
    ("Grand Moff Tarkin / Dark Side Clones (Scorch)", "raid_order66", None, None,
     ["Grand Moff Tarkin", "RC-1262 \"Scorch\""]),
    ("Pirate King Hondo (Pirates)", "raid_order66", None, None,
     ["Pirate King Hondo Ohnaka", "Brutus", "Captain Silvo", "SM-33", "Vane"]),
]


def normalize(name: str) -> str:
    """Strip to a dense lowercase alphanumeric string for exact comparison
    against the baseId fragment embedded in nameKey. Confirmed real pattern
    (not guessed): nameKey == "UNIT_" + baseId + "_NAME" (+ optional _V2
    suffix), e.g. baseId=AAYLASECURA -> nameKey=UNIT_AAYLASECURA_NAME.
    There is no actual translated English text in this collection at all —
    that needs a separate localization fetch not yet built. So matching is
    done by stripping the SAME way on both sides: drop parens content,
    drop all non-alphanumeric characters, lowercase, no spaces."""
    name = re.sub(r"\(.*?\)", "", name)
    name = re.sub(r"[^a-zA-Z0-9]", "", name)
    return name.strip().lower()


NAME_KEY_PATTERN = re.compile(r"^UNIT_(.+?)_NAME(?:_V\d+)?$")


# Manual overrides for cases where the display name has zero textual
# relationship to the real base_id (confirmed individually against real
# cached unit data — see squad_templates.py comment for CX-2's case).
MANUAL_OVERRIDES = {
    "cx2": "OPERATIVE",  # normalize("CX-2") == "cx2" — confirmed via ability namespace match
    "ezrabridger": "EZRABRIDGERS3",  # confirmed via find_missing.py — normalize() strips "(Exile)" entirely, real key is "ezrabridger" not "ezrabridgerexile" (verified by testing normalize() directly before shipping, not assumed)
    "masterquigonjinn": "MASTERQUIGON",  # confirmed via find_missing.py — NOT "QUIGONJINN", that's a different unit
    "skiffguardlandocalrissian": "UNDERCOVERLANDO",  # confirmed directly via swgoh.gg unit page "Base ID: UNDERCOVERLANDO" field
}


def main():
    if not DUMP_PATH.exists():
        print(f"ERROR: {DUMP_PATH} not found. Run trace_gl_campaign.py first to cache real unit data.")
        return

    print("Loading cached units collection ...")
    data = json.loads(DUMP_PATH.read_text())
    units = data.get("units", [])

    # Comlink's enum-decoded response still gives nameKey as a localization
    # KEY (e.g. "UNIT_NAME_AAYLA_SECURA"), not the resolved English string.
    # Build a normalized nameKey -> baseId index, since that's what we can
    # actually match against without a separate localization fetch.
    name_index = {}
    for u in units:
        base_id = u.get("baseId")
        name_key = u.get("nameKey", "")
        if not (base_id and name_key):
            continue
        match = NAME_KEY_PATTERN.match(name_key)
        fragment = match.group(1) if match else name_key
        name_index[normalize(fragment)] = base_id
        # also index by the baseId itself directly, since for many units
        # the dense display name IS the baseId once stripped (e.g.
        # "Aayla Secura" -> "aaylasecura" == baseId.lower())
        name_index.setdefault(normalize(base_id), base_id)

    print(f"Indexed {len(name_index)} unit name keys.\n")

    resolved_squads = []
    unresolved_total = 0

    for label, mode, hold_pct, banners, char_names in META_SQUADS:
        base_ids = []
        unresolved = []
        for name in char_names:
            norm = normalize(name)
            base_id = MANUAL_OVERRIDES.get(norm) or name_index.get(norm)
            if not base_id:
                # try a loose contains-match as fallback
                candidates = [bid for key, bid in name_index.items() if norm in key or key in norm]
                base_id = candidates[0] if len(candidates) == 1 else None
            if base_id:
                base_ids.append(base_id)
            else:
                unresolved.append(name)
                unresolved_total += 1

        resolved_squads.append({
            "name": label,
            "mode": mode,
            "base_ids": base_ids,
            "unresolved": unresolved,
            "hold_pct": hold_pct,
            "banners": banners,
        })

        status = "OK" if not unresolved else f"MISSING: {unresolved}"
        print(f"  [{mode}] {label}: {len(base_ids)}/{len(char_names)} resolved — {status}")

    out_path = GAME_DATA_DIR / "meta_squads_resolved.json"
    out_path.write_text(json.dumps(resolved_squads, indent=2))
    print(f"\nSaved -> {out_path}")
    print(f"Total unresolved names across all squads: {unresolved_total}")
    print("Review unresolved names manually — likely nameKey format mismatch, not missing units.")


if __name__ == "__main__":
    main()
