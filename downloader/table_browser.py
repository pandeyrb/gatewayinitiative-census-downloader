"""Browse Census ACS table shells and generate topic YAML files.

Public API
----------
fetch_groups(year, dataset, cache_dir)          → list of {name, description}
fetch_table_shell(table_id, year, dataset)      → {code: raw_label}  (Estimate vars only)
shell_to_readable(shell)                        → {code: readable_label}
generate_topic_yaml(tables, ...)               → topic-YAML dict ready to dump
"""

import json
import os
import sys
import time
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv

load_dotenv()

_BASE = "https://api.census.gov/data"
_MAX_RETRIES = 3


# ---------------------------------------------------------------------------
# Internal HTTP helper
# ---------------------------------------------------------------------------

def _get(url: str) -> dict:
    api_key = os.getenv("CENSUS_API_KEY")
    if api_key:
        sep = "&" if "?" in url else "?"
        url = url + sep + f"key={api_key}"

    for attempt in range(_MAX_RETRIES):
        try:
            resp = requests.get(url, timeout=60)
            if resp.status_code == 200:
                return resp.json()
            print(f"  WARNING: HTTP {resp.status_code}: {resp.text[:200]}", file=sys.stderr)
            if resp.status_code in (400, 404):
                return {}
        except requests.RequestException as exc:
            print(f"  WARNING: {exc}", file=sys.stderr)

        if attempt < _MAX_RETRIES - 1:
            wait = 2 ** (attempt + 1)
            print(f"  Retrying in {wait}s …", file=sys.stderr)
            time.sleep(wait)

    return {}


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def fetch_groups(year: int, dataset: str, cache_dir: Path | None = None) -> list[dict]:
    """Return all table groups sorted by table ID.

    Result: [{name: "B01001", description: "Sex by Age"}, ...]

    Groups are cached as JSON in cache_dir so subsequent calls don't hit the API.
    """
    if cache_dir:
        slug = dataset.replace("/", "_")
        cache_file = cache_dir / f"groups_{year}_{slug}.json"
        if cache_file.exists():
            return json.loads(cache_file.read_text())

    url = f"{_BASE}/{year}/{dataset}/groups.json"
    print(f"  Fetching table list from Census API …", file=sys.stderr)
    data = _get(url)
    groups = sorted(data.get("groups", []), key=lambda g: g.get("name", ""))

    if cache_dir and groups:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(groups))

    return groups


def fetch_table_shell(table_id: str, year: int, dataset: str) -> dict[str, str]:
    """Return {variable_code: raw_label} for Estimate-only variables in a table.

    Keeps only codes that end in 'E' but not 'EA' (annotation) or 'M'/'MA'.
    Raw label format: 'Estimate!!Total:!!Male:!!Under 5 years'
    """
    url = f"{_BASE}/{year}/{dataset}/groups/{table_id.upper()}.json"
    data = _get(url)
    variables = data.get("variables", {})

    result = {}
    for code, meta in variables.items():
        if code.endswith("E") and not code.endswith("EA"):
            result[code] = meta.get("label", code)

    return dict(sorted(result.items()))


def shell_to_readable(shell: dict[str, str]) -> dict[str, str]:
    """Convert raw Census labels to human-readable strings.

    'Estimate!!Total:!!Male:!!Under 5 years' → 'Total > Male > Under 5 years'
    """
    out = {}
    for code, label in shell.items():
        parts = [p.strip().rstrip(":") for p in label.split("!!") if p.strip()]
        if parts and parts[0].lower() == "estimate":
            parts = parts[1:]
        out[code] = " > ".join(parts)
    return out


def generate_topic_yaml(
    table_ids: list[str],
    topic_name: str,
    year: int,
    dataset: str,
    groups_lookup: dict[str, str],       # {TABLE_ID: description}
    shells: dict[str, dict[str, str]],   # {TABLE_ID: {code: raw_label}}
) -> dict:
    """Build a topic YAML dict from one or more table shells.

    Each table becomes one variable_group keyed by its table ID (lowercase).
    The group label is the table's human-readable description from groups.json.
    """
    variable_groups = {}
    for tid in table_ids:
        tid = tid.upper()
        shell = shells.get(tid)
        if not shell:
            print(f"  WARNING: no variables found for {tid} — skipped.", file=sys.stderr)
            continue
        readable = shell_to_readable(shell)
        variable_groups[tid.lower()] = {
            "label": groups_lookup.get(tid, tid),
            "variables": [{"code": code, "label": readable[code]} for code in shell.keys()],
        }

    return {
        "topic_name": topic_name,
        "dataset": dataset,
        "year": year,
        "variable_groups": variable_groups,
    }
