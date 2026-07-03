\# SWGOH Alliance Dashboard — Project Knowledge

\*Source of truth for all Claude sessions. Update at end of each session.\*

\*Last updated: 2026-07-03 | Owner: Jakub Vincenec (jvincenec / carovnicek)\*



\---



\## SYSTEM PROMPT (paste at session start)



```

You are an experienced CTO and entrepreneur working on a project you treat as your own.

Full project context is in the attached Project Knowledge document — read it before responding.

Treat it as source of truth. Do not rely on session memory for project facts.

Communication: dense and direct. No preamble, no unnecessary questions.

Code and commands always complete and copy-paste ready using known project values.

Make autonomous decisions on architecture, tooling, and sequencing.

Consult only on decisions with significant impact on money, security, or time.

Away from machine: full design work. At machine: exact sequential commands, anticipate failure points.

Proactively identify improvements, technical debt, and risks.

Suggest context doc updates at end of each session.

NEVER ASSUME — ALWAYS VERIFY before fixing. Run probe scripts, check actual file content.

Keyword "CTO mode" = recalibrate if slipping into generic assistant behavior.

```



\---



\## 1. Project Overview



Self-hosted Flask dashboard for managing a 5-guild SWGOH alliance (\~214 players). Replaces manual swgoh.gg browsing with automated data collection, historical trends, and alliance management tools. Data sourced via self-hosted Comlink (EA game API proxy) + swgoh-stats (stat calculator).



\*\*Local\*\*: http://127.0.0.1:5050  

\*\*Public\*\*: https://jvincenec.github.io/swgoh-dashboard/  

\*\*Source\*\*: https://github.com/jvincenec/swgoh-dashboard  

\*\*Reference\*\*: https://jvincenec.github.io/Lamers/alliance/ | https://gorgatron1.github.io/brg/alliance/



\---



\## 2. Environment



| Item | Value |

|---|---|

| Machine | Windows 11, "mini komputer" |

| User | Jakub Vincenec / carovnicek |

| Ally code | 979789966 |

| PowerShell | 5.1 — `\&\&` NOT supported, use separate lines |

| Python | `C:\\Users\\mini komputer\\AppData\\Local\\Programs\\Python\\Python312\\python.exe` |

| Venv | `C:\\swgoh-dashboard\\venv\\` — always use `.\\venv\\Scripts\\python.exe` |

| Conda | Installed but NOT used (init error on every PS session — ignore it) |

| Docker | Desktop running (also hosts Odysseus AI agent containers) |

| Git user | jvincenec / jakub.vincenec@gmail.com |

| NoMachine | Remote access via Tailscale from operator machine "carovnicek" |



\---



\## 3. Infrastructure



\### Docker Containers

```yaml

\# docker-compose.yml at C:\\swgoh-dashboard\\docker-compose.yml

swgoh-comlink:   port 3000   ghcr.io/swgoh-utils/swgoh-comlink:latest

swgoh-stats:     port 3223   ghcr.io/swgoh-utils/swgoh-stats:latest

\# swgoh-stats depends\_on swgoh-comlink (healthcheck)

\# statCalcData volume: ./statCalcData:/app/statCalcData

\# Both on network: comlink

\# ACCESS\_KEY: my-access-key / SECRET\_KEY: my-secret-key

```



```powershell

docker start swgoh-comlink swgoh-stats   # start

docker ps                                 # verify

```



\### Flask Server

```powershell

cd C:\\swgoh-dashboard

.\\venv\\Scripts\\python.exe dashboard\\server.py

\# Starts on http://127.0.0.1:5050

\# Debug mode on, port 5050, host 127.0.0.1

```



\*\*Critical\*\*: `app.run()` is at the very END of `dashboard/server.py` (line \~1583). Any script that slices server.py content around route boundaries risks deleting it silently. Always check `tail -5 dashboard/server.py` after any automated edit.



\### Requirements

```

requests==2.31.0

flask==3.0.3

```

Install: `.\\venv\\Scripts\\pip.exe install -r requirements.txt`



\---



\## 4. Guild Configuration



\*\*config.json\*\* (at `C:\\swgoh-dashboard\\config.json`):

```json

{

&#x20; "guild\_ally\_codes": \["979789966"],

&#x20; "\_comment": "One ally code per guild. fetch\_guilds.py resolves ally code -> guildId via /player."

}

```



\*\*How multi-guild works\*\*: `fetch\_guilds.py` has `ALLY\_CODE = "979789966"` hardcoded. It reads `guild\_ally\_codes` from config.json, appends ALLY\_CODE if not present, then resolves each to a guildId via `/player` call. To add more guilds: add one member's ally code per guild to `guild\_ally\_codes` array.



\*\*5 tracked guilds\*\* → slugs in `data/guilds/`:

\- `return-of-the-oddballs` (carovnicek's guild)

\- `oddworld-abe-exodus`

\- `banes-disciples`

\- `ender-s`

\- `thick-as-thieves`



\---



\## 5. Data Pipeline — Exact Run Order



```powershell

cd C:\\swgoh-dashboard



\# --- PREREQUISITES ---

docker start swgoh-comlink swgoh-stats



\# --- DAILY / PER SESSION ---

.\\venv\\Scripts\\python.exe fetch\_guilds.py          # \~30s — guild rosters, member list, TW/raid results

.\\venv\\Scripts\\python.exe fetch\_player\_rosters.py  # \~2 min — per-player stats, zetas, omicrons

.\\venv\\Scripts\\python.exe snapshot.py              # \~5s — seeds history/player\_stats for trend charts



\# --- COMPUTED STATS (slow, run weekly or after roster changes) ---

.\\venv\\Scripts\\python.exe fetch\_stats.py           # \~7 min — real speed/health via swgoh-stats



\# --- AFTER GAME UPDATES (one-time or when game data changes) ---

.\\venv\\Scripts\\python.exe analysis\\build\_unit\_alignment.py  # → unit\_alignment.json + ship\_ids.json

.\\venv\\Scripts\\python.exe analysis\\build\_zeta\_map.py        # → zeta\_map.json + omicron\_abilities.json

.\\venv\\Scripts\\python.exe analysis\\build\_gl\_requirements.py # → gl\_requirements.json

.\\venv\\Scripts\\python.exe analysis\\build\_datacron\_sets.py   # → datacron\_sets.json

.\\venv\\Scripts\\python.exe analysis\\build\_tb\_platoons.py     # → tb\_platoons.json (currently empty — see bugs)



\# --- LOCALIZATION (BROKEN — skip until fixed) ---

.\\venv\\Scripts\\python.exe fetch\_localization.py    # BROKEN: HTTP 400, loc\_id format wrong



\# --- LESS FREQUENT ---

.\\venv\\Scripts\\python.exe fetch\_leaderboards.py    # guild GP global rankings (top 200 only)



\# --- STATIC SITE BUILD + DEPLOY ---

\# Terminal 1 (keep open):

.\\venv\\Scripts\\python.exe dashboard\\server.py

\# Terminal 2:

.\\venv\\Scripts\\python.exe build\_static.py          # \~60 min — 1431 files to docs/

git add -f docs\\

git commit -m "refresh YYYY-MM-DD"

git push origin main

```



\---



\## 6. Key Data Files



\### Game Data (`C:\\swgoh-dashboard\\game\_data\\`)

| File | Size | Contents | Built by | Status |

|---|---|---|---|---|

| `full\_data\_dump\_enums.json` | 811MB | Full Comlink dump with enums=True | `fetch\_guilds.py` one-time | ✅ |

| `unit\_alignment.json` | small | 514 units → LIGHT/DARK/NEUTRAL | `build\_unit\_alignment.py` | ✅ |

| `ship\_ids.json` | small | \~1050 ship base\_ids (combatType=SHIP from dump) | `build\_unit\_alignment.py` | ✅ |

| `zeta\_map.json` | medium | skill\_id → {is\_zeta, is\_omicron, zeta\_player\_tier, omicron\_player\_tier, omicron\_mode, name} | `build\_zeta\_map.py` | ✅ |

| `omicron\_abilities.json` | small | ability\_id → mode string (from skill.abilityReference where skill.omicronMode != ALL\_OMICRON) | `build\_zeta\_map.py` | ✅ |

| `gl\_requirements.json` | small | 9 GLs with prerequisite unit lists (hardcoded fallback if game data parse fails) | `build\_gl\_requirements.py` | ✅ |

| `datacron\_sets.json` | small | Datacron set definitions | `build\_datacron\_sets.py` | ✅ |

| `tb\_platoons.json` | empty | TB platoon unit requirements | `build\_tb\_platoons.py` | ❌ empty |

| `localization\_en.json` | — | nameKey → display string | `fetch\_localization.py` | ❌ BROKEN |



\### Runtime Data (`C:\\swgoh-dashboard\\data\\`)

| Path | Contents |

|---|---|

| `guilds/\*.json` | Per-guild state: members, TW results, raid results, contributions |

| `rosters/roster\_stats.json` | Per-player processed stats (\~214 players) |

| `rosters/history/\*.json` | Timestamped roster archives (created each fetch\_player\_rosters.py run) |

| `history/log.json` | Guild snapshot history (transfer detection) |

| `history/player\_stats/\*.json` | Compact stats snapshots for trend charts (created by snapshot.py) |

| `history/transfers.json` | Detected cross-guild transfers |

| `stats/<ally\_code>.json` | Computed character stats from swgoh-stats |

| `leaderboards.json` | Guild GP global rankings |



\### Legacy Files (do not use)

\- `fetch.py` — old single-player fetch script, predates this dashboard. Still on disk. Caused wrong index.html in early deployment.

\- `currencies.json` — old static data file from fetch.py era

\- `arena.json`, `player.json`, `guild.json` — if these exist, they're from fetch.py era and will be loaded by old index route if it still exists



\---



\## 7. Dashboard Routes (48 total)



\### Fixed routes

| Route | Template | Notes |

|---|---|---|

| `/` | redirect | → /community |

| `/community` | community.html | Alliance overview + D3 charts. Also exported as docs/index.html |

| `/players` | players.html | All players DataTable |

| `/player/<ally\_code>` | player\_detail.html | Tabs: Stats/Roster/Zetas/Omicrons/Mods/Squads/GAC/Contributions/Datacrons/Progression |

| `/characters` | characters.html | Character catalogue |

| `/c/<base\_id>` | character\_detail.html | Per-character detail |

| `/squads` | squads.html | Meta squads |

| `/squad-templates` | squad\_templates.html | Squad templates |

| `/farming` | farming.html | Farming guide |

| `/mods` | mods.html | Alliance mod overview |

| `/history` | history.html | Snapshot history |

| `/transfers` | transfers.html | Transfer log |

| `/trends` | trends.html | 10 D3 trend charts |

| `/events` | events.html | Game events schedule |

| `/raids` | raids.html | Raid damage report |

| `/inactivity` | inactivity.html | Last active tracking |

| `/gl-readiness` | gl\_readiness.html | All players vs 9 GLs |

| `/leaderboards` | leaderboards.html | Guild global GP rank |

| `/alliance/health` | alliance\_health.html | Composite health scores 0-100 |

| `/alliance/mods` | alliance\_mods.html | Alliance mod scores |

| `/alliance/gac` | alliance\_gac.html | GAC league standings |

| `/export/<dataset>.csv` | — | CSV exports |



\### Per-guild routes (×5 guilds, slug = guild name lowercased)

| Route | Template |

|---|---|

| `/guild/<slug>` | guild\_detail.html |

| `/guild/<slug>/mods` | guild\_mods.html |

| `/guild/<slug>/mods-characters` | guild\_mods\_characters.html |

| `/guild/<slug>/important-toons` | guild\_important\_toons.html |

| `/guild/<slug>/rare-units` | guild\_rare\_units.html |

| `/guild/<slug>/squads-all` | guild\_squads\_all.html |

| `/guild/<slug>/tw-history` | guild\_tw\_history.html |

| `/guild/<slug>/contributions` | guild\_contributions.html |

| `/guild/<slug>/tb-platoons` | guild\_tb\_platoons.html |



\### JSON data endpoints

```

/data/community-gp-stats.json

/data/community-player-stats.json

/data/guilds-gp-stats.json

/data/trends/alliance-relic.json

/data/trends/alliance-r5plus.json

/data/trends/named-toons.json

/data/trends/guild-relic.json

/data/trends/alliance-zetas.json

/data/trends/alliance-omicrons.json

/data/trends/alliance-mod-score.json

/data/trends/alliance-gl.json

/data/trends/guild-health.json

/data/trends/guild-zetas.json

/data/trends/player/<ally\_code>/relic.json

/data/trends/player/<ally\_code>/gp.json

/data/trends/player/<ally\_code>/zetas.json

/data/stats/<ally\_code>.json

```



\---



\## 8. Confirmed Comlink API Facts



\### Endpoints

| Endpoint | Status | Notes |

|---|---|---|

| `POST /player` | ✅ | Full roster, skills, mods, datacrons, pvpProfile, seasonStatus |

| `POST /guild` | ✅ | Members, TW/TB/raid results, contributions |

| `POST /getEvents` | ✅ | Events schedule including Conquest, Coliseum |

| `POST /data` | ✅ | 811MB game dump (enums=True) |

| `POST /metadata` | ✅ | Game version: `0.40.1:Ye7X8XSqSUmdSqhKsISpTA` |

| `POST /localization` | ❌ | HTTP 400. Tried: `{hash}:ENG\_US`. Format unknown for v0.40.1 |

| `POST /getLeaderboard` | ⚠️ | Built, untested. Only returns top-200 guilds globally |

| `POST /getGuildLeaderboard` | ❌ | Not implemented |

| `POST /getGuilds` | ❌ | Not used |



\### Critical field facts (confirmed from probes)



\*\*`rosterUnit` in `/player` response:\*\*

\- `combatType`: NOT PRESENT — only in game\_data dump's `units` collection. Use `ship\_ids.json` to identify ships.

\- `purchasedAbilityId\[]`: IS present at unit level. Contains ability IDs for applied omicrons. Example: `\['ultimateability\_grandmasterluke']` for JML TW omicron.

\- `skill\[].tier`: Uses +2 offset — `player\_tier + 2 == in-game tier index (1-based)`

\- `relic`: Present on ALL 289 units including ships (can't use to distinguish chars from ships)

\- `equippedStatMod\[].secondaryStat\[]`: Contains all 4 secondaries per mod with stat name + value

\- `currentLevel`: Present on characters AND ships



\*\*`pvpProfile\[]` in `/player`:\*\*

\- tab 0 = squad arena rank

\- tab 1 = fleet arena rank



\*\*`seasonStatus\[]` in `/guild` member data:\*\*

\- Contains GAC history: seasonId, league, division, wins, losses, seasonPoints, rank



\*\*`memberContribution` in `/guild` member data:\*\*

\- raid\_tickets, gear\_donations, guild\_tokens with current + lifetime values



\### Hard limits (Comlink cannot access)

\- Unequipped mods, gear pieces, shard inventory, currencies

\- Live TW placement / attack orders (only completed TW results via `recentTerritoryWarResult`)

\- Live TB deployment

\- Conquest individual player progress



\---



\## 9. swgoh-stats API (Confirmed from probe 2026-07-02)



```

POST http://localhost:3223/api?flags=withModCalc

Body: \[full /player response]   ← array wrapping the player object

Response: same array with unit.stats added to each rosterUnit

```



\*\*Response format\*\* (confirmed, MAGMATROOPER example):

```json

{

&#x20; "stats": {

&#x20;   "base": {"Health": 17576, "Speed": 119, "Physical Damage": 1526, "Armor": 195, ...},

&#x20;   "gear": {"Health": 250, "Physical Damage": 30, ...},

&#x20;   "mods": {"Health": 103, "Speed": 45, "Physical Damage": 358, ...},

&#x20;   "growthModifiers": {"Strength": 8.2, "Agility": 5.4, "Intelligence": 4.5}

&#x20; }

}

```



\*\*Total stat\*\* = `base\[name] + gear.get(name, 0) + mods.get(name, 0)`  

Keys are \*\*string names\*\* (not integer stat IDs). Case-sensitive.



Stat names used: `Speed`, `Health`, `Protection`, `Physical Damage`, `Special Damage`, `Potency`, `Tenacity`, `Armor`, `Resistance`, `Physical Critical Chance`, `Special Critical Chance`, `Critical Damage`



\---



\## 10. Zeta / Omicron Detection



\### Game data field names (confirmed from probe\_game\_data.py)

```

skill collection keys: \['tier', 'id', 'nameKey', 'iconKey', 'abilityReference', 'skillType', 'isZeta', 'omicronMode']

skill.tier\[] (NOT tierList) — array of tier entries

tier entry keys include: isZetaTier, isOmicronTier (booleans)

skill.isZeta — top-level boolean on skill

skill.omicronMode — string on skill (ALL\_OMICRON = default/no omicron)

ability collection: has NO omicronMode field

```



\### Zeta detection algorithm

```python

\# In build\_zeta\_map.py:

for idx, t in enumerate(sk.get("tier") or \[]):

&#x20;   if t.get("isZetaTier"):

&#x20;       zeta\_player\_tier = max(0, idx - 1)



\# In fetch\_player\_rosters.py:

\# player has zeta if:

skill.tier >= zeta\_player\_tier AND zeta\_player\_tier >= 1

\# zeta\_player\_tier == 0 → GL auto-zeta (event-applied, not via material) → EXCLUDED

```



\### Omicron detection algorithm

```python

\# Source: purchasedAbilityId\[] at unit level — authoritative

\# omicron\_abilities.json: {ability\_id → mode} built from skill.abilityReference

\# where skill.omicronMode not in (ALL\_OMICRON, OMICRON\_MODE\_NONE, "")



unit\_omicrons = list(unit.get("purchasedAbilityId") or \[])

\# ANY entry in purchasedAbilityId is an omicron

mode = OMICRON\_ABILITIES.get(ref, "Unknown")

```



\### omicronMode values

```

OMICRON\_MODE\_GRAND\_ARENA      → "GAC"

OMICRON\_MODE\_GRAND\_ARENA\_3V3  → "GAC 3v3"

OMICRON\_MODE\_GRAND\_ARENA\_5V5  → "GAC 5v5"

OMICRON\_MODE\_TERRITORY\_WAR    → "TW"

OMICRON\_MODE\_TERRITORY\_BATTLE → "TB"

OMICRON\_MODE\_RAID             → "Raid"

OMICRON\_MODE\_CONQUEST         → "CQ"

ALL\_OMICRON / OMICRON\_MODE\_NONE → None (not an omicron)

```



\### Accuracy (carovnicek 979789966 vs swgoh.gg)

\- 7★ chars: ✅ 188 (was 239 — ships were included, fixed with ship\_ids.json)

\- Zetas: ✅ \~165 (was 186 — GL auto-zetas now excluded with zpt >= 1)

\- Omicrons: ✅ 1 (JML TW — via purchasedAbilityId)



\---



\## 11. Alliance Health Formula



```python

health = min(100, round(

&#x20;   min(25, avg\_relic\_total / 600 \* 25) +   # relic depth (avg per player, max \~600)

&#x20;   min(20, avg\_mod\_score / 5 \* 20) +        # mod quality (mod\_score = speed≥15/chars\_gp/100k)

&#x20;   min(30, gl\_per\_player / 5 \* 30) +        # GL coverage (5 GLs/player = max)

&#x20;   min(25, r5\_pct \* 25),                     # R5+ breadth (r5\_plus / seven\_star)

&#x20;   1

))

```



Current scores: OAE \~92, Return of Oddballs \~87, Bane's \~88, Thick as Thieves \~88, Ender's \~73



\---



\## 12. Key Constants in server.py



```python

NAMED\_TOONS = {  # 17 chars — players table columns

&#x20;   "JKR":"JEDIKNIGHTREVAN", "DR":"DARTHREVAN", "Malak":"DARTHMALAK",

&#x20;   "GAS":"GENERALSKYWALKER", "JML":"GRANDMASTERLUKE", "JMK":"JEDIMASTERKENOBI",

&#x20;   "JKL":"JEDIKNIGHTLUKE", "LV":"LORDVADER", "Rey":"GLREY",

&#x20;   "SEE":"SITHPALPATINE", "SLK":"SUPREMELEADERKYLOREN", "Ahsoka":"GLAHSOKATANO",

&#x20;   "Jabba":"JABBATHEHUTT", "Neg":"NEGOTIATOR", "Mal":"MALEVOLENCE",

&#x20;   "Exec":"CAPITALEXECUTOR", "Chimaera":"CAPITALCHIMAERA",

}



IMPORTANT\_TOONS = {  # 30 chars — important-toons page

&#x20;   \*\*NAMED\_TOONS,

&#x20;   "Padme":"PADMEAMIDALA", "Thrawn":"GRANDADMIRALTHRAWN",

&#x20;   "CLS":"COMMANDERLUKESKYWALKER", "Shaak Ti":"SHAAKTI",

&#x20;   "IPD":"IMPERIALPROBEDROID", "Merrin":"NIGHTSISTERMERRIN",

&#x20;   "Wat":"WATTAMBOR", "Geos":"GEONOSIANBROODALPHA", "BB-8":"BB8",

&#x20;   "Mando":"THEMANDALORIANBESKARARMOR", "Starkiller":"STARKILLER",

&#x20;   "Reva":"SEVENTHSISTER", "Baylan":"BAYLANSKOLL",

}



GL\_BASE\_IDS = {

&#x20;   "GLREY","SITHPALPATINE","SUPREMELEADERKYLOREN","GRANDMASTERLUKE",

&#x20;   "JEDIMASTERKENOBI","JEDIKNIGHTLUKE","LORDVADER","GLAHSOKATANO","JABBATHEHUTT",

}

```



\---



\## 13. Static Site Export (build\_static.py)



\- Fetches all routes from `http://localhost:5050` → writes HTML to `docs/`

\- \*\*`BASE\_PATH = "/swgoh-dashboard"`\*\* — prefixed on all internal `href` and `src` attributes

\- `rewrite\_links()` function called inside `fetch()` at line \~54: `body = rewrite\_links(r.text) if outfile.endswith(".html") else r.text`

\- `/community` exported as both `docs/community.html` AND `docs/index.html`

\- `docs/.nojekyll` required (prevents GitHub Pages Jekyll processing)

\- Runtime: \~60 min for 1,431 files



\### Verified regex (2026-07-03):

```python

html = re.sub(r'href="(/\[^"#]\*)"', lambda m: fix("href", m), html)

html = re.sub(r'src="(/\[^"#]\*)"', lambda m: fix("src", m), html)

html = re.sub(r'"(/data/\[^"]+)"', lambda m: '"' + BASE\_PATH + m.group(1) + '"', html)

```

`\[^"#]\*` (not `\[^"#]\[^"]\*`) — correctly handles bare `href="/"`.



\### GitHub Pages setup

```

Repo: https://github.com/jvincenec/swgoh-dashboard

Branch: main, Folder: /docs

URL: https://jvincenec.github.io/swgoh-dashboard/

```



\---



\## 14. Open Bugs



\### P0 — GitHub Pages links

\*\*Status\*\*: build\_static.py fix was deployed (swgoh-linkfix2.zip). Final build ran, git showed 1 file changed (index.html). `community.html` was verified WRONG before the build. Not re-verified after.



\*\*Verify first thing next session:\*\*

```powershell

Select-String -Path docs\\community.html -Pattern 'href="/swgoh-dashboard' | Select-Object -First 1

Select-String -Path docs\\community.html -Pattern 'href="/community"' | Select-Object -First 1

```

If second returns results → rebuild needed. If first returns results → links are correct.



\### P1 — fetch\_localization.py HTTP 400

\*\*Status\*\*: Broken since day 1. Current code uses `{hash}:ENG\_US` format where hash = `Ye7X8XSqSUmdSqhKsISpTA`. All zeta/omicron ability names show as raw nameKeys everywhere.



\*\*Impact\*\*: UX only — data is correct, names are ugly keys.



\*\*To debug next session:\*\*

```powershell

\# Try bare locale with no version prefix

.\\venv\\Scripts\\python.exe -c "

import requests

r = requests.post('http://localhost:3000/localization', json={'payload':{'id':'ENG\_US'}, 'enums':False})

print(r.status\_code, r.text\[:200])

"

```



\### P2 — TB platoon tool empty

`territoryBattleDefinition` in dump has 10 entries but keys are `conflictZoneDefinition`, `strikeZoneDefinition` etc — no `platoon` key with unit lists. The `/guild/<slug>/tb-platoons` page exists but shows "No platoon data found." Needs deeper structure probe.



\### P3 — Trend charts need data accumulation

`data/history/player\_stats/` accumulates one file per `snapshot.py` run. Currently 1-2 files exist. All 10 trend charts are flat/empty. Fix: run `snapshot.py` daily (after `fetch\_guilds.py`).



\### P4 — Legacy files at root

`fetch.py` and `currencies.json` are old fetch.py-era files. They don't break anything but add confusion. The old `/` route used to load `player.json`/`arena.json` from these — now fixed to redirect to `/community`. Safe to delete `fetch.py` next session after verifying it's not referenced anywhere.



\---



\## 15. Technical Debt



| Item | Risk | Fix |

|---|---|---|

| `app.run()` at end of server.py vulnerable to script slicing | Medium — happened once, lost server start | Add `# DO NOT DELETE` comment above it |

| Docker started manually | Low — just habit | Could add to startup script |

| build\_static.py takes 60 min | Low | No pagination/parallelism. Add `concurrent.futures` pool |

| No scheduled data refresh | Medium — stale data | Windows Task Scheduler calling fetch\_guilds.py + snapshot.py daily |

| `fetch.py` legacy file at root | Low — confusion risk | Delete it |

| No error alerting | Medium — fetch failures silent | Log to file, check on next session |

| `data/stats/` not rebuilt after roster changes | Medium — stale computed stats | Include `fetch\_stats.py` in weekly pipeline |



\---



\## 16. Feature Parity vs Lamers/BRG Reference



| Feature | Lamers | Us | Status |

|---|---|---|---|

| Players DataTable | ✅ | ✅ | Parity |

| Balance labels | ✅ | ✅ | Parity |

| Mod scores | ✅ | ✅ | Parity |

| Named toon columns | 19 | 17 | Minor gap |

| Zeta counts | ✅ | ✅ | Accurate |

| Omicron counts | ✅ | ✅ | Accurate |

| GL readiness | ✅ | ✅ | Built |

| Alliance health | ✅ | ✅ | Built |

| TW history | ✅ | ✅ | Built |

| Contributions | ✅ | ✅ | Built |

| GAC standings | ✅ | ✅ | Built |

| Computed stats (speed) | ✅ | ✅ | Via swgoh-stats |

| TW planning/live | ✅ | ❌ | Comlink hard limit |

| Farm progress | ✅ | ❌ | Comlink hard limit |

| Counters | ✅ | ❌ | Needs swgoh.gg API (ToS check needed) |

| TB platoon tool | ✅ | ⚠️ | Built but empty data |

| Ability names localized | ✅ | ❌ | Blocked by localization 400 error |



\---



\## 17. Git Workflow



```powershell

\# Source code changes:

cd C:\\swgoh-dashboard

git add dashboard\\ analysis\\ \*.py .gitignore

git commit -m "feat/fix: description"

git push origin main



\# Static site rebuild:

\# Terminal 1: .\\venv\\Scripts\\python.exe dashboard\\server.py

\# Terminal 2:

.\\venv\\Scripts\\python.exe build\_static.py

git add -f docs\\

git commit -m "refresh YYYY-MM-DD"

git push origin main



\# Branch workflow for new features:

git checkout -b feature/name

\# work, test locally

git checkout main

git merge feature/name

\# rebuild static + push

```



\---



\## 18. Probe Scripts (debug only, not part of pipeline)



Located in `analysis/`:

\- `probe\_ability\_omicron.py` — checks ability/skill omicronMode values + JML data

\- `probe\_game\_data.py` — inspects full\_data\_dump\_enums.json structure

\- `probe\_player\_fields.py` — inspects /player response field names (used to confirm combatType absent)

\- `probe\_stats\_response.py` — confirms swgoh-stats response format (used to find base/gear/mods structure)

\- `probe\_zeta\_accuracy.py` — zeta count accuracy check



Run pattern:

```powershell

.\\venv\\Scripts\\python.exe analysis\\probe\_XYZ.py 2>\&1 | Tee-Object probe\_output.txt

Get-Content probe\_output.txt

```



