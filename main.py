#!/usr/bin/env python3
"""Census ACS downloader CLI for Massachusetts Gateway Cities."""

from pathlib import Path

import click
import yaml

CONFIG_DIR  = Path(__file__).parent / "config"
OUTPUT_DIR  = Path(__file__).parent / "outputs"
CACHE_DIR   = OUTPUT_DIR / "cache"
GEO_CHOICES = ["all", "place", "tract", "block_group", "block"]
ALL_LEVELS  = ["place", "tract", "block_group", "block"]


@click.command()
@click.option("--city",                default=None,      help="City slug (e.g. lawrence).")
@click.option("--topic",               default=None,      help="Topic slug (e.g. demographics).")
@click.option("--year",                default=2022,      show_default=True, type=int,
              help="ACS 5-year vintage year.")
@click.option("--geo",                 default="all",     show_default=True,
              type=click.Choice(GEO_CHOICES, case_sensitive=False),
              help="Geography level(s) to fetch.")
@click.option("--dataset",             default="acs/acs5", show_default=True,
              help="Census dataset identifier (e.g. acs/acs5, dec/dhc).")
@click.option("--output-format",       default="csv",     show_default=True,
              type=click.Choice(["csv", "excel", "both"], case_sensitive=False),
              help="Output file format.")
@click.option("--dry-run",             is_flag=True,      help="Print URLs without fetching.")
@click.option("--codebook",            is_flag=True,      help="Write variable codebook for --topic and exit.")
@click.option("--list-cities",         is_flag=True,      help="List all city slugs and exit.")
@click.option("--list-topics",         is_flag=True,      help="List all local topic files and exit.")
# --- Census table browser ---
@click.option("--list-census-tables",  is_flag=True,      help="List all Census tables for --year/--dataset.")
@click.option("--search",              default=None,       help="Keyword filter for --list-census-tables.")
@click.option("--table",               multiple=True,      metavar="TABLE_ID",
              help="Census table ID(s), e.g. --table B01001 --table B02001.")
@click.option("--shell",               is_flag=True,       help="Print variable shell for --table(s) and exit.")
@click.option("--create-topic",        default=None,       metavar="TOPIC_NAME",
              help="Generate a topic YAML from --table(s) and save to config/topics/.")
def main(city, topic, year, geo, dataset, output_format, dry_run, codebook,
         list_cities, list_topics,
         list_census_tables, search, table, shell, create_topic):
    """Download US Census ACS 5-year data for MA Gateway Cities."""

    # ------------------------------------------------------------------ #
    # Informational / one-shot commands                                   #
    # ------------------------------------------------------------------ #

    if list_cities:
        cities = yaml.safe_load((CONFIG_DIR / "cities.yaml").read_text())
        click.echo("Available city slugs:")
        for slug, cfg in sorted(cities.items()):
            click.echo(f"  {slug:20s}  {cfg['name']}")
        return

    if list_topics:
        topic_dir = CONFIG_DIR / "topics"
        click.echo("Available topic files:")
        for path in sorted(topic_dir.glob("*.yaml")):
            click.echo(f"  {path.stem}")
        return

    if codebook:
        if not topic:
            raise click.UsageError("--topic is required with --codebook.")
        _write_codebook(topic, CONFIG_DIR, OUTPUT_DIR)
        return

    # ------------------------------------------------------------------ #
    # Census table browser commands                                       #
    # ------------------------------------------------------------------ #

    if list_census_tables:
        _list_census_tables(year, dataset, search)
        return

    if shell:
        if not table:
            raise click.UsageError("--table TABLE_ID is required with --shell.")
        _print_shell(list(table), year, dataset)
        return

    if create_topic:
        if not table:
            raise click.UsageError("--table TABLE_ID is required with --create-topic.")
        _create_topic_from_tables(list(table), create_topic, year, dataset, CONFIG_DIR)
        return

    # ------------------------------------------------------------------ #
    # Main download pipeline                                              #
    # ------------------------------------------------------------------ #

    if not city or not topic:
        raise click.UsageError(
            "--city and --topic are required unless using "
            "--list-cities, --list-topics, --codebook, "
            "--list-census-tables, --shell, or --create-topic."
        )

    from downloader.pipeline import run_pipeline

    geo_levels = ALL_LEVELS if geo == "all" else [geo]

    run_pipeline(
        city_slug=city,
        topic=topic,
        year=year,
        geo_levels=geo_levels,
        output_dir=OUTPUT_DIR,
        config_dir=CONFIG_DIR,
        output_format=output_format,
        dry_run=dry_run,
    )


# ======================================================================= #
# Helper: codebook                                                         #
# ======================================================================= #

def _write_codebook(topic: str, config_dir: Path, output_dir: Path) -> None:
    """Generate a CSV codebook for a topic: variable_code, group_key, sub_theme, topic, dataset, year."""
    import csv

    yaml_path = config_dir / "topics" / f"{topic}.yaml"
    if not yaml_path.exists():
        raise click.UsageError(f"Topic file not found: {yaml_path}")

    with yaml_path.open() as fh:
        config = yaml.safe_load(fh)

    topic_name = config.get("topic_name", topic)
    dataset    = config.get("dataset", "acs/acs5")
    year       = config.get("year", "")
    groups     = config.get("variable_groups", {})

    rows = []
    for group_key, group in groups.items():
        label = group.get("label", group_key)
        for code in group.get("variables", []):
            rows.append({
                "topic":         topic_name,
                "dataset":       dataset,
                "year":          year,
                "group_key":     group_key,
                "sub_theme":     label,
                "variable_code": code,
            })

    out_dir = output_dir / "codebooks"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{topic}_codebook.csv"

    with out_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["topic", "dataset", "year", "group_key", "sub_theme", "variable_code"])
        writer.writeheader()
        writer.writerows(rows)

    click.echo(f"Codebook written: {out_path}  ({len(rows)} variables)")
    click.echo()
    click.echo(f"  {'group_key':<22}  {'sub_theme':<35}  {'n_vars':>6}")
    click.echo("  " + "-" * 68)
    seen = {}
    for row in rows:
        k = row["group_key"]
        seen[k] = seen.get(k, {"sub_theme": row["sub_theme"], "count": 0})
        seen[k]["count"] += 1
    for k, v in seen.items():
        click.echo(f"  {k:<22}  {v['sub_theme']:<35}  {v['count']:>6}")


# ======================================================================= #
# Helper: list Census tables                                               #
# ======================================================================= #

def _list_census_tables(year: int, dataset: str, search: str | None) -> None:
    from downloader.table_browser import fetch_groups

    groups = fetch_groups(year, dataset, cache_dir=CACHE_DIR)

    if search:
        kw = search.lower()
        groups = [g for g in groups if kw in g.get("name", "").lower()
                                    or kw in g.get("description", "").lower()]

    click.echo(f"\n{'Table ID':<12}  Description")
    click.echo("-" * 80)
    for g in groups:
        name = g.get("name", "")
        desc = g.get("description", "")
        click.echo(f"  {name:<10}  {desc}")
    click.echo(f"\n{len(groups)} table(s) listed.")
    if not search:
        click.echo("Tip: narrow results with --search KEYWORD  (e.g. --search poverty)")


# ======================================================================= #
# Helper: print table shell                                                #
# ======================================================================= #

def _print_shell(table_ids: list[str], year: int, dataset: str) -> None:
    from downloader.table_browser import fetch_table_shell, shell_to_readable

    for tid in table_ids:
        shell = fetch_table_shell(tid, year, dataset)
        if not shell:
            click.echo(f"\n{tid.upper()}: no estimate variables found (check table ID).")
            continue
        readable = shell_to_readable(shell)
        click.echo(f"\n{tid.upper()} — {len(shell)} estimate variable(s)  [{year} {dataset}]")
        click.echo("-" * 72)
        click.echo(f"  {'Variable':<14}  Label")
        click.echo(f"  {'-'*14}  {'-'*52}")
        for code, label in readable.items():
            click.echo(f"  {code:<14}  {label}")


# ======================================================================= #
# Helper: create topic YAML from table shells                              #
# ======================================================================= #

def _create_topic_from_tables(
    table_ids: list[str],
    topic_name: str,
    year: int,
    dataset: str,
    config_dir: Path,
) -> None:
    from downloader.table_browser import fetch_groups, fetch_table_shell, generate_topic_yaml

    out_path = config_dir / "topics" / f"{topic_name}.yaml"
    if out_path.exists():
        click.confirm(
            f"Topic '{topic_name}' already exists ({out_path}). Overwrite?",
            abort=True,
        )

    # Build lookup: TABLE_ID → description
    click.echo(f"Fetching group list for {year} {dataset} …")
    groups = fetch_groups(year, dataset, cache_dir=CACHE_DIR)
    groups_lookup = {g["name"]: g.get("description", g["name"]) for g in groups}

    # Fetch shell for each requested table
    shells: dict[str, dict[str, str]] = {}
    total_vars = 0
    for tid in table_ids:
        tid_upper = tid.upper()
        click.echo(f"  Fetching shell for {tid_upper} …")
        shell = fetch_table_shell(tid_upper, year, dataset)
        shells[tid_upper] = shell
        total_vars += len(shell)
        desc = groups_lookup.get(tid_upper, "unknown table")
        click.echo(f"    → {len(shell)} estimate variables  ({desc})")

    # Generate and write the YAML
    topic_data = generate_topic_yaml(
        table_ids=[t.upper() for t in table_ids],
        topic_name=topic_name,
        year=year,
        dataset=dataset,
        groups_lookup=groups_lookup,
        shells=shells,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as fh:
        yaml.dump(topic_data, fh, default_flow_style=False, sort_keys=False, allow_unicode=True)

    click.echo(f"\nTopic YAML written: {out_path}")
    click.echo(f"  Tables:    {', '.join(t.upper() for t in table_ids)}")
    click.echo(f"  Variables: {total_vars} total")
    click.echo(f"\nNext step:")
    click.echo(f"  python main.py --city lawrence --topic {topic_name} --year {year} --geo all")


if __name__ == "__main__":
    main()
