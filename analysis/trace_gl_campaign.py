"""
trace_gl_campaign.py — Phase B investigation. Finds the actual GL Journey
roster-gating prerequisites (what you need built on OTHER characters
before the GL event/campaign unlocks) by digging into the 'campaign'
collection entries that reference GRANDMASTERLUKE.

Saves the full matching campaign entries to game_data/ for inspection
(they're deeply nested — too large to usefully print in full to a
terminal), and prints just the requirement-related key names found at
each nesting level so we know what to extract next, without guessing.

Reuses the same enums=true, requestSegment-paginated fetch already
verified working — also saves the full merged dump this time so we don't
need to re-fetch for follow-up investigation.

Usage:
    python analysis/trace_gl_campaign.py
"""

import json
import sys
from pathlib import Path

import requests

COMLINK_URL = "http://localhost:3000"
TARGET_BASE_ID = "GRANDMASTERLUKE"
GAME_DATA_DIR = Path(__file__).parent.parent / "game_data"
GAME_DATA_DIR.mkdir(exist_ok=True)
MAX_SEGMENTS = 30


def comlink_post(endpoint: str, payload: dict, timeout=300) -> dict:
    resp = requests.post(
        f"{COMLINK_URL}{endpoint}",
        json={"payload": payload, "enums": True},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_all_segments(version: str) -> dict:
    merged = {}
    prev_total = -1
    for segment in range(MAX_SEGMENTS):
        print(f"Fetching segment {segment} ...")
        data = comlink_post(
            "/data",
            {"version": version, "includePveUnits": False, "requestSegment": segment},
        )
        total = sum(len(v) for v in data.values() if isinstance(v, list))
        if total == 0 and segment > 0:
            break
        for k, v in data.items():
            if isinstance(v, list):
                merged.setdefault(k, [])
                merged[k].extend(v)
            elif k not in merged:
                merged[k] = v
        new_total = sum(len(v) for v in merged.values() if isinstance(v, list))
        if new_total == prev_total:
            break
        prev_total = new_total
    return merged


def find_requirement_keys(obj, path="", found=None):
    """Recursively walk a nested structure, collecting the path to any
    key whose name suggests it gates something (requirement, condition,
    unlock, prereq)."""
    if found is None:
        found = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if any(term in k.lower() for term in ["requirement", "condition", "unlock", "prereq"]):
                found.append((path + "." + k if path else k, type(v).__name__,
                               (v if not isinstance(v, (dict, list)) else f"<{type(v).__name__}>")))
            find_requirement_keys(v, path + "." + k if path else k, found)
    elif isinstance(obj, list):
        for i, item in enumerate(obj[:3]):  # only first few to avoid explosion
            find_requirement_keys(item, f"{path}[{i}]", found)
    return found


def main():
    print("Fetching /metadata ...")
    meta = comlink_post("/metadata", {})
    version = meta.get("latestGamedataVersion")
    if not version:
        print("ERROR: no version found.")
        sys.exit(1)

    data = fetch_all_segments(version)

    out_path = GAME_DATA_DIR / "full_data_dump_enums.json"
    out_path.write_text(json.dumps(data))
    print(f"\nSaved full enum-decoded dump -> {out_path} ({out_path.stat().st_size / 1024 / 1024:.1f} MB)")

    matches = [c for c in data.get("campaign", []) if TARGET_BASE_ID in json.dumps(c)]
    print(f"\n{len(matches)} campaign entries reference {TARGET_BASE_ID}")

    for i, entry in enumerate(matches):
        entry_path = GAME_DATA_DIR / f"campaign_match_{i}.json"
        entry_path.write_text(json.dumps(entry, indent=2))
        print(f"\n=== Campaign match {i} (campaign id: {entry.get('id', '?')}) saved -> {entry_path} ===")

        req_keys = find_requirement_keys(entry)
        print(f"Requirement-related keys found ({len(req_keys)}):")
        seen_paths = set()
        for path, vtype, val in req_keys:
            # dedupe by stripping array indices, since same structure repeats per node
            generic_path = path.split("[")[0] if "[" in path else path
            if generic_path in seen_paths:
                continue
            seen_paths.add(generic_path)
            print(f"  {path} ({vtype}): {val}")


if __name__ == "__main__":
    main()
