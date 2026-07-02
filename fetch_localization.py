"""
fetch_localization.py — fetch localization bundle from Comlink.
Saves game_data/localization_en.json {KEY: "Display Name"}.
Run ONCE before build_zeta_map.py to get human-readable ability names.
Run: .\venv\Scripts\python.exe fetch_localization.py
"""
import json, sys
from pathlib import Path
import requests

COMLINK_URL   = "http://localhost:3000"
GAME_DATA_DIR = Path(__file__).parent / "game_data"
OUT_PATH      = GAME_DATA_DIR / "localization_en.json"


def comlink_post(endpoint, payload):
    resp = requests.post(f"{COMLINK_URL}{endpoint}", json={"payload": payload, "enums": False}, timeout=60)
    resp.raise_for_status()
    return resp.json()


def main():
    print("Fetching game version...")
    meta = comlink_post("/metadata", {})
    version = meta.get("latestGamedataVersion") or meta.get("gameVersion") or ""
    if not version:
        print("ERROR: could not get game version from /metadata")
        print("Response:", meta)
        sys.exit(1)
    print(f"Game version: {version}")

    # Strip any "X.Y.Z:" prefix — Comlink /localization only wants the hash portion
    hash_part = version.split(":")[-1] if ":" in version else version
    loc_id = f"{hash_part}:ENG_US"
    print(f"Fetching /localization for {loc_id} ...")
    response = comlink_post("/localization", {"id": loc_id, "unzip": True})

    # Comlink returns the localization as a dict {KEY: value} or sometimes
    # as a raw pipe-delimited string in a wrapper. Handle both.
    loc = {}
    if isinstance(response, dict):
        # May have a wrapper key like "localizationBundle"
        if "localizationBundle" in response:
            raw = response["localizationBundle"]
            # pipe-delimited: KEY|Value\nKEY2|Value2
            for line in raw.splitlines():
                if "|" in line:
                    k, _, v = line.partition("|")
                    loc[k.strip()] = v.strip()
        else:
            # Already a flat dict
            loc = {k: v for k, v in response.items() if isinstance(v, str)}
    elif isinstance(response, str):
        for line in response.splitlines():
            if "|" in line:
                k, _, v = line.partition("|")
                loc[k.strip()] = v.strip()
    elif isinstance(response, list):
        loc = {e.get("key"): e.get("value") for e in response if isinstance(e, dict) and "key" in e}

    if not loc:
        print("WARNING: localization appears empty. Response type:", type(response).__name__)
        print("Response sample:", str(response)[:200])
        sys.exit(1)

    OUT_PATH.write_text(json.dumps(loc, ensure_ascii=False, indent=None), encoding="utf-8")
    size_mb = OUT_PATH.stat().st_size / 1e6
    print(f"Saved {len(loc)} strings -> {OUT_PATH.name} ({size_mb:.1f} MB)")
    sample = [(k, v) for k, v in loc.items() if "NAME" in k][:5]
    print("Sample NAME strings:", sample)


if __name__ == "__main__":
    main()
