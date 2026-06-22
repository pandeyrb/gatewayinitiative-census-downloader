"""Cross-check YAML variable codes and labels against the Census API.

For each variable in a topic YAML that has a configured label, this module:
  1. Fetches the full table shell from the Census API (cached to disk).
  2. Checks that the code actually exists in its parent table.
  3. Checks that key terms in the configured label do not contradict the
     Census label (e.g., label says "Female" but Census says "Male").

Why contradictions only, not full-text matching?
  YAML labels are user-chosen summaries; they are often more descriptive
  than the raw Census label ("Total civilian employed 16+" vs. "Total:").
  Trying to match them word-for-word produces too many false positives.
  The class of errors we actually saw (C24010, B11003, B17001, B17010) all
  share one trait: a keyword in the label flatly contradicts the Census
  path (Female vs. Male, Below vs. Above). That is what we detect here.

Usage
-----
    from downloader.variable_validator import validate_topic, print_report
    issues = validate_topic("economic", config_dir, output_dir)
    print_report(issues, "economic")
    if issues:
        sys.exit(1)
"""

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import requests

_BASE = "https://api.census.gov/data"
_REQUEST_TIMEOUT = 30  # seconds per table-shell fetch

# Each tuple is (set_A, set_B): if the YAML label contains a word from set_A
# while the Census label contains a word from set_B (or vice versa), the
# variable is almost certainly misassigned.
#
# Uses word-boundary matching so "female" does not trigger "male" detection.
_CONTRADICTION_PAIRS: list[tuple[set[str], set[str]]] = [
    ({"female", "women", "woman"}, {"male", "men", "man"}),
    ({"below poverty", "under poverty"},  {"above poverty", "at or above"}),
]


@dataclass
class ValidationIssue:
    code: str
    yaml_label: str
    census_label: str       # human-readable breadcrumb
    group_key: str          # YAML variable_group key
    group_label: str        # human-readable group name
    reason: Literal["missing", "mismatch"]
    detail: str             # one-line explanation


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_topic(
    topic: str,
    config_dir: Path,
    output_dir: Path,
    year: int | None = None,
    dataset: str | None = None,
) -> list[ValidationIssue]:
    """Return a list of ValidationIssues for all labeled variables in a topic YAML.

    An empty list means every configured label is consistent with the Census API.
    Variables without a configured label are skipped — there is nothing to check.

    Parameters
    ----------
    topic       : YAML file stem, e.g. "economic"
    config_dir  : directory that contains topics/<topic>.yaml
    output_dir  : used for the disk cache (outputs/cache/shells/...)
    year        : Census vintage year (default: read from YAML)
    dataset     : Census dataset slug (default: read from YAML)
    """
    import yaml
    from downloader.variable_loader import load_topic

    yaml_path = config_dir / "topics" / f"{topic}.yaml"
    with yaml_path.open() as fh:
        cfg = yaml.safe_load(fh)

    year    = year    or cfg.get("year",    2022)
    dataset = dataset or cfg.get("dataset", "acs/acs5")

    variables, var_to_group, var_to_label = load_topic(topic, config_dir)

    # Build group_key lookup (variable code → YAML group key)
    var_to_gkey: dict[str, str] = {}
    for gk, grp in cfg.get("variable_groups", {}).items():
        for entry in grp.get("variables", []):
            c = entry.get("code", entry) if isinstance(entry, dict) else entry
            var_to_gkey[str(c)] = gk

    # Group codes by table prefix so we fetch each table shell only once
    table_to_codes: dict[str, list[str]] = {}
    for code in variables:
        tid = _table_id(code)
        if tid:
            table_to_codes.setdefault(tid, []).append(code)

    cache_dir = output_dir / "cache" / "shells" / str(year) / dataset.replace("/", "_")
    issues: list[ValidationIssue] = []

    for table_id, codes in sorted(table_to_codes.items()):
        shell = _fetch_shell_cached(table_id, year, dataset, cache_dir)
        if shell is None:
            print(f"  [validate] Could not reach Census API for {table_id} — skipped.",
                  file=sys.stderr)
            continue

        for code in codes:
            yaml_label = var_to_label.get(code, "")
            if not yaml_label:
                continue  # no label to compare

            if code not in shell:
                issues.append(ValidationIssue(
                    code=code,
                    yaml_label=yaml_label,
                    census_label="(variable not found in this table)",
                    group_key=var_to_gkey.get(code, ""),
                    group_label=var_to_group.get(code, ""),
                    reason="missing",
                    detail=(
                        f"{code} does not exist in {table_id} for "
                        f"{year} {dataset}. Check the variable number."
                    ),
                ))
                continue

            census_raw = shell[code]
            census_readable = _readable(census_raw)
            conflict = _find_contradiction(yaml_label, census_raw)

            if conflict:
                issues.append(ValidationIssue(
                    code=code,
                    yaml_label=yaml_label,
                    census_label=census_readable,
                    group_key=var_to_gkey.get(code, ""),
                    group_label=var_to_group.get(code, ""),
                    reason="mismatch",
                    detail=conflict,
                ))

    return issues


def print_report(
    issues: list[ValidationIssue],
    topic: str,
    verbose: bool = False,
) -> None:
    """Print a human-readable validation report to stdout."""
    if not issues:
        print(f"  ✓  {topic}: all labeled variables match Census API definitions.")
        return

    print(f"\n  ✗  {topic}: {len(issues)} issue(s) found\n")
    for iss in issues:
        tag = "MISSING" if iss.reason == "missing" else "MISMATCH"
        print(f"  [{tag}]  {iss.code}  —  group: {iss.group_key}")
        print(f"    config label : \"{iss.yaml_label}\"")
        print(f"    Census label : {iss.census_label}")
        print(f"    detail       : {iss.detail}")
        print()


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _table_id(code: str) -> str | None:
    """'C24010_001E' → 'C24010', 'B17020A_002E' → 'B17020A', else None."""
    m = re.match(r'^([A-Z][0-9]+[A-Z]?)_', code)
    return m.group(1) if m else None


def _fetch_shell_cached(
    table_id: str,
    year: int,
    dataset: str,
    cache_dir: Path,
) -> dict[str, str] | None:
    """Return {variable_code: raw_label} for all Estimate vars in a table.

    Results are cached as JSON so subsequent runs do not hit the API.
    Returns None if the API could not be reached.
    """
    cache_file = cache_dir / f"{table_id}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())

    url = f"{_BASE}/{year}/{dataset}/groups/{table_id}.json"
    try:
        resp = requests.get(url, timeout=_REQUEST_TIMEOUT)
    except requests.RequestException:
        return None

    if resp.status_code != 200:
        return None

    try:
        variables = resp.json().get("variables", {})
    except ValueError:
        return None

    shell = {
        code: meta.get("label", code)
        for code, meta in variables.items()
        if code.endswith("E") and not code.endswith("EA")
    }

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(shell))
    return shell


def _readable(census_raw: str) -> str:
    """'Estimate!!Total:!!Male:!!Under 5 years' → 'Total > Male > Under 5 years'."""
    parts = [p.strip().rstrip(":") for p in census_raw.split("!!") if p.strip()]
    if parts and parts[0].lower() == "estimate":
        parts = parts[1:]
    return " > ".join(parts)


def _has_term(text: str, term: str) -> bool:
    """Return True if `term` appears in `text` as a complete word (or phrase)."""
    if " " in term:
        return term in text
    return bool(re.search(r"\b" + re.escape(term) + r"\b", text))


def _find_contradiction(yaml_label: str, census_raw: str) -> str | None:
    """Return a one-line description of a keyword contradiction, or None."""
    yl = yaml_label.lower()
    cl = census_raw.lower()

    for side_a, side_b in _CONTRADICTION_PAIRS:
        yaml_a = next((t for t in side_a if _has_term(yl, t)), None)
        yaml_b = next((t for t in side_b if _has_term(yl, t)), None)
        cens_a = next((t for t in side_a if _has_term(cl, t)), None)
        cens_b = next((t for t in side_b if _has_term(cl, t)), None)

        # Label says A, Census says B (and not A) → contradiction
        if yaml_a and not yaml_b and cens_b and not cens_a:
            return (
                f"Label says \"{yaml_a}\" but Census variable belongs to "
                f"the \"{cens_b}\" category."
            )
        # Label says B, Census says A (and not B) → contradiction
        if yaml_b and not yaml_a and cens_a and not cens_b:
            return (
                f"Label says \"{yaml_b}\" but Census variable belongs to "
                f"the \"{cens_a}\" category."
            )

    return None
