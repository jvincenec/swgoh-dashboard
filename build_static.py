import re
"""
build_static.py — exports the Flask dashboard to static HTML in docs/
Run AFTER fetch cycle with server running on port 5050.

Usage:
  # Terminal 1:
  .\\venv\\Scripts\\python.exe dashboard\\server.py

  # Terminal 2:
  .\\venv\\Scripts\\python.exe build_static.py

Then: git add docs\\ && git commit -m "refresh" && git push
"""
import json, shutil, time
from pathlib import Path

import requests

BASE     = "http://localhost:5050"
OUT      = Path("docs")
DATA_DIR = Path("data")
GAME_DIR = Path("game_data")

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "swgoh-static-builder/1.0"

ERRORS = []
BASE_PATH = "/swgoh-dashboard"


def rewrite_links(html):
    def fix(attr, m):
        p = m.group(1)
        if p.startswith(BASE_PATH) or p.startswith("http") or p.startswith("//"):
            return m.group(0)
        if p == "/":
            return attr + '="' + BASE_PATH + '/"'
        return attr + '="' + BASE_PATH + p + '"'
    html = re.sub(r'href="(/[^"#]*)"', lambda m: fix("href", m), html)
    html = re.sub(r'src="(/[^"#]*)"', lambda m: fix("src", m), html)
    html = re.sub(r'"(/data/[^"]+)"', lambda m: '"' + BASE_PATH + m.group(1) + '"', html)
    return html


def fetch(route, outfile, binary=False):
    dest = OUT / outfile
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = SESSION.get(f"{BASE}{route}", timeout=60)
        r.raise_for_status()
        if binary:
            dest.write_bytes(r.content)
        else:
            body = rewrite_links(r.text) if outfile.endswith(".html") else r.text
            dest.write_text(body, encoding="utf-8")
        print(f"  OK  {outfile}")
    except Exception as e:
        print(f"  ERR {outfile}: {e}")
        ERRORS.append((route, str(e)))


def main():
    OUT.mkdir(exist_ok=True)
    (OUT / "static").mkdir(exist_ok=True)

    # Verify server is up
    try:
        requests.get(f"{BASE}/", timeout=5).raise_for_status()
        print(f"Server OK at {BASE}")
    except Exception:
        print(f"ERROR: server not responding at {BASE}")
        print("Start it first: .\\venv\\Scripts\\python.exe dashboard\\server.py")
        return

    # --- Fixed pages ---
    FIXED = [
        ("/community",         "index.html"),   # / redirects to community — export community as root
        ("/community",         "community.html"),  # also keep as community.html
        ("/players",           "players.html"),
        ("/characters",        "characters.html"),
        ("/squads",            "squads.html"),
        ("/squad-templates",   "squad-templates.html"),
        ("/farming",           "farming.html"),
        ("/mods",              "mods.html"),
        ("/history",           "history.html"),
        ("/transfers",         "transfers.html"),
        ("/trends",            "trends.html"),
        ("/events",            "events.html"),
        ("/raids",             "raids.html"),
        ("/inactivity",        "inactivity.html"),
        ("/alliance/mods",     "alliance/mods.html"),
        ("/alliance/health",   "alliance/health.html"),
        ("/gl-readiness",      "gl-readiness.html"),
        ("/leaderboards",      "leaderboards.html"),
    ]
    print("\n--- Fixed pages ---")
    for route, out in FIXED:
        fetch(route, out)

    # --- JSON data endpoints ---
    JSON_ENDPOINTS = [
        "/data/community-gp-stats.json",
        "/data/community-player-stats.json",
        "/data/guilds-gp-stats.json",
        "/data/trends/alliance-relic.json",
        "/data/trends/alliance-r5plus.json",
        "/data/trends/named-toons.json",
        "/data/trends/guild-relic.json",
        "/data/trends/alliance-zetas.json",
        "/data/trends/alliance-omicrons.json",
        "/data/trends/alliance-mod-score.json",
        "/data/trends/alliance-gl.json",
        "/data/trends/guild-health.json",
        "/data/trends/guild-zetas.json",
    ]
    print("\n--- JSON data ---")
    for ep in JSON_ENDPOINTS:
        fetch(ep, ep.lstrip("/"))

    # --- Per-guild pages ---
    guilds = []
    for f in sorted((DATA_DIR / "guilds").glob("*.json")):
        try:
            g = json.loads(f.read_text())
            slug = f.stem
            guilds.append((slug, g.get("name", slug)))
        except Exception:
            continue

    print(f"\n--- Guild pages ({len(guilds)} guilds x 6 pages) ---")
    for slug, name in guilds:
        fetch(f"/guild/{slug}",                 f"guild/{slug}/index.html")
        fetch(f"/guild/{slug}/mods",            f"guild/{slug}/mods.html")
        fetch(f"/guild/{slug}/important-toons", f"guild/{slug}/important-toons.html")
        fetch(f"/guild/{slug}/rare-units",      f"guild/{slug}/rare-units.html")
        fetch(f"/guild/{slug}/squads-all",      f"guild/{slug}/squads-all.html")
        fetch(f"/guild/{slug}/mods-characters", f"guild/{slug}/mods-characters.html")

    # --- Per-player pages ---
    roster_path = DATA_DIR / "rosters" / "roster_stats.json"
    ally_codes = []
    if roster_path.exists():
        rs = json.loads(roster_path.read_text())
        ally_codes = list(rs.keys())

    print(f"\n--- Player pages ({len(ally_codes)} players) ---")
    for i, ac in enumerate(ally_codes, 1):
        fetch(f"/player/{ac}", f"player/{ac}.html")
        fetch(f"/data/trends/player/{ac}/relic.json", f"data/trends/player/{ac}/relic.json")
        fetch(f"/data/trends/player/{ac}/gp.json",    f"data/trends/player/{ac}/gp.json")
        fetch(f"/data/trends/player/{ac}/zetas.json", f"data/trends/player/{ac}/zetas.json")
        if i % 20 == 0:
            print(f"    ...{i}/{len(ally_codes)}")

    # --- Per-character pages ---
    char_ids = []
    alignment_path = GAME_DIR / "unit_alignment.json"
    if alignment_path.exists():
        chars = json.loads(alignment_path.read_text())
        char_ids = list(chars.keys())

    print(f"\n--- Character pages ({len(char_ids)} characters) ---")
    for i, cid in enumerate(char_ids, 1):
        fetch(f"/c/{cid}", f"c/{cid}.html")
        if i % 50 == 0:
            print(f"    ...{i}/{len(char_ids)}")

    # --- Static assets ---
    print("\n--- Static assets ---")
    src_static = Path("dashboard/static")
    if src_static.exists():
        shutil.copytree(src_static, OUT / "static", dirs_exist_ok=True)
        print(f"  Copied {len(list(src_static.iterdir()))} files from dashboard/static")

    # --- GitHub Pages needs index redirect or direct index ---
    # Ensure root index.html is correct
    root_idx = OUT / "index.html"
    if root_idx.exists():
        content = root_idx.read_text(encoding="utf-8")
        # Fix all absolute paths — GitHub Pages serves from /repo-name/
        # so we use relative paths in HTML; Flask already uses url_for which
        # produces absolute paths — patch them to be root-relative
        # (This is a no-op if you use a custom domain or serve from root)
        print("  Root index.html present")

    # Summary
    print(f"\n{'='*50}")
    total = sum(1 for _ in OUT.rglob("*.html")) + sum(1 for _ in OUT.rglob("*.json"))
    print(f"Export complete: {total} files in docs/")
    if ERRORS:
        print(f"\nERRORS ({len(ERRORS)}):")
        for route, err in ERRORS:
            print(f"  {route}: {err}")
    else:
        print("No errors.")
    print(f"\nNext steps:")
    print(f"  git add docs\\")
    print(f"  git commit -m \"refresh $(Get-Date -Format yyyy-MM-dd)\"")
    print(f"  git push origin main")


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"\nTime: {time.time()-t0:.0f}s")
