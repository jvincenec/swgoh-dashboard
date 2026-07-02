"""
squad_templates.py — A small database of known squad compositions, used to
detect which teams a player can field based on their owned roster.

IMPORTANT — honesty about what this is:
Comlink does NOT expose a player's saved/built squads. There is no API for
"what team does this player actually run." This module works around that by
checking ownership + gear/relic thresholds against KNOWN squad templates
(the same kind of squads listed on https://swgoh.gg/gac/squads/) and saying
"this player COULD run this team" rather than "this player DOES run this
team." Treat detected teams as a strong hint, not certainty.

This list will go stale. Re-check https://swgoh.gg/gac/squads/ periodically
and update SQUAD_TEMPLATES below — there is no auto-update mechanism.

OMICRON AWARENESS (optional, added after setup_game_data.py exists):
If a template specifies "requires_omicron": ["BASE_ID", ...] and game data
has been fetched via setup_game_data.py, detect_teams() will check REAL
omicron status (via name_resolver.has_omicron, which reads the player's
actual skill tier against the documented omicron tier in game data) rather
than just relic level. If game data hasn't been fetched, this check is
silently skipped and viability falls back to relic level only — this is a
deliberate degrade-gracefully choice, not a bug.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from name_resolver import GameDataResolver
    _resolver = GameDataResolver()
except ImportError:
    _resolver = None


# Each template: name, list of required base ids, and a minimum relic level
# considered "viable" for that squad to be a real threat (not just unlocked).
SQUAD_TEMPLATES = [
    {
        "name": "Jabba / Boushh / Krrsantan",
        "base_ids": ["JABBATHEHUTT", "BOUSHH", "KRRSANTAN"],
        "min_relic": 5,
        "category": "gac_meta",
    },
    {
        "name": "Lord Vader / Appo / CX-2",
        "base_ids": ["LORDVADER", "CC1119APPO", "OPERATIVE"],
        "min_relic": 5,
        "category": "gac_meta",
        # CX-2's real Comlink base_id is "OPERATIVE" — confirmed directly
        # against the live cached units collection (game_data/full_data_dump_enums.json),
        # not the "CX2" literal that was previously here unverified (that
        # baseId does not exist in real game data — checked, zero matches).
        # CX-2's 3v3 GAC omicron grants Empire allies 100% Max Health plus
        # conditional Offense/health-recovery bonuses if all allies are
        # Dark Side Clone Troopers/Vader (EA kit reveal, swgoh.gg unit page).
        "requires_omicron": ["OPERATIVE"],
    },
    {
        "name": "Tarkin / Disguised Clone / Scorch",
        "base_ids": ["GRANDMOFFTARKIN", "DISGUISEDCLONETROOPER", "RC1262SCORCH"],
        "min_relic": 5,
        "category": "gac_meta",
        # CONFIRMED (EA kit-reveal forum post + swgoh.gg unit page, both
        # May 2025): Tarkin's LEADER ability has a 3v3-GAC-specific
        # omicron that unlocks the squad's core synergy package (Stealth
        # for Supports, Protection Up for Tanks, assist mechanics, Fear)
        # conditional on all allies being Dark Side Clone Troopers.
        "requires_omicron": ["GRANDMOFFTARKIN"],
    },
    {
        "name": "Queen Amidala / Qui-Gon / Padawan Obi-Wan",
        "base_ids": ["QUEENAMIDALA", "MASTERQUIGON", "PADAWANOBIWAN"],
        "min_relic": 5,
        "category": "gac_meta",
        # CONFIRMED NOT REQUIRED: a swgoh.gg developer Q&A states the
        # omicron is "intended to make things easier... but not required"
        # and that the character is "still a powerful character" without
        # it. No requires_omicron entry — relic-only viability is correct
        # here, and adding one would be wrong, not just unverified.
    },
    {
        "name": "Baylan Skoll / Marrok / Shin Hati",
        "base_ids": ["BAYLANSKOLL", "MARROK", "SHINHATI"],
        "min_relic": 5,
        "category": "gac_meta",
        # UNCONFIRMED: sources describe Baylan's GAC omicron as a strong
        # upgrade ("extremely dangerous in Grand Arena") but nothing found
        # states the squad is non-functional without it, unlike the
        # CX-2/Tarkin/Vader cases. Left without requires_omicron rather
        # than guess.
    },
    {
        "name": "Ahsoka / Ezra Bridger (Exile) / Huyang",
        "base_ids": ["AHSOKATANO", "EZRABRIDGEREXILE", "HUYANG"],
        "min_relic": 5,
        "category": "gac_meta",
        # CONFIRMED: Ezra's GAC omicron is treated as a baseline assumption
        # in build analysis (swgoh.gg forum). Reinforced by a kit-adjustment
        # patch that specifically gated key power to requiring a full
        # Spectre squad and reset/refunded omicron investment when it went
        # live — confirms this is current, not legacy.
        "requires_omicron": ["EZRABRIDGEREXILE"],
    },
    {
        "name": "Mace Windu / Depa Billaba / Temple Guard",
        "base_ids": ["JEDIMASTERMACEWINDU", "DEPABILLABA", "TEMPLEGUARD"],
        "min_relic": 5,
        "category": "gac_meta",
        # UNCONFIRMED: no clear "required for squad function" signal found
        # in kit reveals or unit pages. Left without requires_omicron.
    },
    {
        "name": "Rey / Ben Solo / Cal Kestis",
        "base_ids": ["REY", "BENSOLO", "CALKESTIS"],
        "min_relic": 5,
        "category": "gac_meta",
        # UNCONFIRMED: no clear current source found describing an
        # omicron as required for this specific squad's GAC function.
        # Left without requires_omicron.
    },
    {
        "name": "Palpatine / Mara Jade / Vader (Duel's End)",
        "base_ids": ["EMPERORPALPATINE", "MARAJADETHEEMPERORSHAND", "DARTHVADERDUELSEND"],
        "min_relic": 5,
        "category": "gac_meta",
        # CONFIRMED (EA kit-reveal forum post, Nov 2025 + swgoh.gg omicron
        # listing): Vader's omicron "I Am What Remains" is GAC-specific and
        # requires Emperor Palpatine in the leader slot to inflict Fracture
        # on two enemies — a defining lockout effect described directly as
        # creating "brutal lockouts in GAC." Not a minor stat boost.
        "requires_omicron": ["DARTHVADERDUELSEND"],
    },
    # Legacy / older squads still relevant for TB, raids, or GAC undersizing
    {
        "name": "Jedi Master Luke Skywalker (GL) squad core",
        "base_ids": ["GRANDMASTERLUKE", "GENERALKENOBI", "JEDIKNIGHTLUKE"],
        "min_relic": 5,
        "category": "legacy_strong",
    },
    {
        "name": "Darth Vader Empire core",
        "base_ids": ["VADER", "EMPERORPALPATINE", "GRANDMOFFTARKIN"],
        "min_relic": 4,
        "category": "legacy_strong",
    },
    {
        "name": "General Skywalker 501st",
        "base_ids": ["GENERALSKYWALKER", "CT7567", "CT5555", "ARCTROOPER501ST"],
        "min_relic": 3,
        "category": "legacy_strong",
    },
]


def relic_tier_to_level(tier: int) -> int:
    return max(0, tier - 2)


def detect_teams(roster_units: list) -> list:
    """Given a player's rosterUnit list from Comlink, return which squad
    templates they could plausibly field, with the limiting (lowest) relic
    level among the required members, plus real omicron status where
    available and required by the template."""
    by_base_id = {}
    for unit in roster_units:
        base_id = unit.get("definitionId", "").split(":")[0]
        relic = relic_tier_to_level((unit.get("relic") or {}).get("currentTier", 0))
        by_base_id[base_id] = {"relic": relic, "unit": unit}

    results = []
    for template in SQUAD_TEMPLATES:
        owned_relics = []
        missing = []
        for base_id in template["base_ids"]:
            if base_id in by_base_id:
                owned_relics.append(by_base_id[base_id]["relic"])
            else:
                missing.append(base_id)

        if missing:
            # Doesn't own the full squad at all
            continue

        limiting_relic = min(owned_relics)
        viable = limiting_relic >= template["min_relic"]

        # Additive omicron check — only runs if the template requires it
        # AND game data has been fetched. Otherwise this is silently
        # skipped and viability stays relic-based only.
        omicron_check = None
        required_omicron_units = template.get("requires_omicron", [])
        if required_omicron_units and _resolver and _resolver.available:
            missing_omicron = []
            for base_id in required_omicron_units:
                entry = by_base_id.get(base_id)
                if not entry:
                    missing_omicron.append(base_id)
                    continue
                unlocked = _resolver.has_omicron(entry["unit"])
                if not unlocked:
                    missing_omicron.append(base_id)
            omicron_check = {
                "checked": True,
                "missing_omicron_on": missing_omicron,
                "all_omicrons_present": len(missing_omicron) == 0,
            }
            if missing_omicron:
                viable = False

        results.append(
            {
                "name": template["name"],
                "category": template["category"],
                "limiting_relic": limiting_relic,
                "required_relic": template["min_relic"],
                "viable": viable,
                "omicron_check": omicron_check,
            }
        )

    return results
