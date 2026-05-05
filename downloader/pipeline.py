"""Orchestrate a full Census data download run.

Usage (called from main.py):
    run_pipeline(city_slug="lawrence", topic="demographics", year=2022,
                 geo_levels=["place","tract","block_group","block"],
                 output_dir=Path("outputs"), output_format="csv", dry_run=False)
"""

import csv
import sys
from pathlib import Path

import pandas as pd
import yaml

from downloader.census_client import CensusClient
from downloader.geo_resolver import GEO_LEVELS
from downloader.variable_loader import load_cities, load_topic


def run_pipeline(
    city_slug: str,
    topic: str,
    year: int,
    geo_levels: list[str],
    output_dir: Path,
    config_dir: Path,
    output_format: str = "csv",
    dry_run: bool = False,
) -> None:
    # --- Load configs ---
    cities = load_cities(config_dir)
    if city_slug not in cities:
        available = ", ".join(sorted(cities))
        raise SystemExit(f"Unknown city slug '{city_slug}'. Available: {available}")
    city_config = cities[city_slug]

    variables, var_to_group, _var_to_label = load_topic(topic, config_dir)
    dataset = _get_dataset(config_dir, topic)

    print(f"\nCity:      {city_config['name']}")
    print(f"Topic:     {topic}  ({len(variables)} variables)")
    print(f"Dataset:   {dataset}  year={year}")
    print(f"Geo levels: {geo_levels}")

    if dry_run:
        print("\n--- DRY RUN: printing variable list ---")
        for v in variables:
            print(f"  {v}  [{var_to_group[v]}]")
        print(f"\n--- DRY RUN: constructed API URLs ---")

    client = CensusClient(year=year, dataset=dataset)
    out_base = output_dir / city_slug / topic / str(year)

    results: dict[str, pd.DataFrame] = {}

    for level in geo_levels:
        # ACS (1-year and 5-year) only goes down to block group; blocks require Decennial Census.
        if "acs" in dataset.lower() and level == "block":
            print(
                f"\n[block] SKIPPED: ACS datasets do not support block-level geography.\n"
                f"  Block-level data is only in the Decennial Census (e.g., dec/sf1)."
            )
            continue

        print(f"\n[{level}] Fetching …")
        try:
            df = client.fetch(variables, city_config, level, dry_run=dry_run)
        except Exception as exc:
            print(f"  ERROR fetching {level}: {exc}", file=sys.stderr)
            continue

        if dry_run or df is None:
            continue

        if df.empty:
            print(f"  WARNING: no data returned for {level} — skipping.")
            continue

        _warn_nulls(df, variables, level)
        results[level] = df

        if not dry_run:
            _write_output(df, out_base / f"{level}", output_format)
            print(f"  → {len(df)} rows written to {out_base / level}.*")

    if not dry_run and len(results) > 1:
        combined = pd.concat(list(results.values()), ignore_index=True, sort=False)
        _write_output(combined, out_base / "all_geo_levels", output_format)
        print(f"\nCombined output: {out_base / 'all_geo_levels'}.* ({len(combined)} rows)")

    # Summary
    print("\n=== Summary ===")
    for level, df in results.items():
        print(f"  {level:15s}  {len(df):>6} rows  {len(df.columns):>4} columns")

    if not dry_run:
        cb_path = _write_codebook(topic, config_dir, output_dir)
        print(f"\nCodebook:  {cb_path}")


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _write_codebook(topic: str, config_dir: Path, output_dir: Path) -> Path:
    """Write outputs/codebooks/{topic}_codebook.csv and return its path."""
    yaml_path = config_dir / "topics" / f"{topic}.yaml"
    with yaml_path.open() as fh:
        config = yaml.safe_load(fh)

    topic_name = config.get("topic_name", topic)
    dataset    = config.get("dataset", "acs/acs5")
    year       = config.get("year", "")
    groups     = config.get("variable_groups", {})

    variables, var_to_group, var_to_label = load_topic(topic, config_dir)

    var_to_group_key: dict[str, str] = {}
    for group_key, group in groups.items():
        for entry in group.get("variables", []):
            code = entry.get("code", entry) if isinstance(entry, dict) else entry
            var_to_group_key[str(code)] = group_key

    rows = [
        {
            "topic":         topic_name,
            "dataset":       dataset,
            "year":          year,
            "group_key":     var_to_group_key.get(code, ""),
            "sub_theme":     var_to_group.get(code, ""),
            "variable_code": code,
            "label":         var_to_label.get(code, ""),
        }
        for code in variables
    ]

    out_dir = output_dir / "codebooks"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{topic}_codebook.csv"

    with out_path.open("w", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["topic", "dataset", "year", "group_key", "sub_theme", "variable_code", "label"],
        )
        writer.writeheader()
        writer.writerows(rows)

    return out_path


def _get_dataset(config_dir: Path, topic: str) -> str:
    path = config_dir / "topics" / f"{topic}.yaml"
    with path.open() as fh:
        return yaml.safe_load(fh).get("dataset", "acs/acs5")


def _warn_nulls(df: pd.DataFrame, variables: list[str], level: str) -> None:
    threshold = 0.20
    present_vars = [v for v in variables if v in df.columns]
    null_counts = df[present_vars].isnull().sum()
    high_null = null_counts[null_counts / len(df) > threshold]
    if not high_null.empty:
        print(
            f"  WARNING [{level}]: {len(high_null)} variable(s) have >20% null values:"
        )
        for var, count in high_null.items():
            pct = count / len(df) * 100
            print(f"    {var}  {count}/{len(df)} ({pct:.0f}% null)")


def _write_output(df: pd.DataFrame, base_path: Path, fmt: str) -> None:
    base_path.parent.mkdir(parents=True, exist_ok=True)
    if fmt in ("csv", "both"):
        df.to_csv(f"{base_path}.csv", index=False)
    if fmt in ("excel", "both"):
        df.to_excel(f"{base_path}.xlsx", index=False)
