"""Look up variable codes from the ACS 2022 Table Shells.

Usage:
    python lookup_table.py B14002          # print all variables for a table
    python lookup_table.py B14002 --yaml   # print as YAML snippet ready to paste
    python lookup_table.py B14002 B15002   # multiple tables at once
"""

import sys
from pathlib import Path

import pandas as pd

SHELLS_PATH = Path(__file__).parent / "ACS2022_Table_Shells.xlsx"


def load_shells() -> pd.DataFrame:
    if not SHELLS_PATH.exists():
        raise SystemExit(
            f"Table Shells file not found at {SHELLS_PATH}\n"
            "Download it from:\n"
            "  https://www2.census.gov/programs-surveys/acs/tech_docs/table_shells/2022/ACS2022_Table_Shells.xlsx"
        )
    return pd.read_excel(SHELLS_PATH)


def lookup(df: pd.DataFrame, table_id: str, as_yaml: bool = False) -> None:
    rows = df[df["Table ID"] == table_id]

    title_row = rows[rows["UniqueID"].isna() & rows["Stub"].notna()]
    title = title_row["Stub"].iloc[0].strip() if not title_row.empty else table_id

    vars_rows = rows.dropna(subset=["UniqueID"])

    if vars_rows.empty:
        print(f"Table '{table_id}' not found in Table Shells.")
        return

    if as_yaml:
        group_key = table_id.lower()
        print(f"\n  {group_key}:")
        print(f'    label: "{title}"')
        print(f"    variables:")
        for _, r in vars_rows.iterrows():
            code = str(r["UniqueID"]).strip() + "E"
            label = str(r["Stub"]).strip()
            print(f"      - code: {code}")
            print(f'        label: "{label}"')
    else:
        print(f"\n{'='*60}")
        print(f"  {table_id}: {title}")
        print(f"  {len(vars_rows)} variables")
        print(f"{'='*60}")
        for _, r in vars_rows.iterrows():
            code = str(r["UniqueID"]).strip() + "E"
            label = str(r["Stub"]).strip()
            print(f"  {code:<20}  {label}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    as_yaml = "--yaml" in sys.argv

    if not args:
        print(__doc__)
        return

    df = load_shells()
    for table_id in args:
        lookup(df, table_id.upper(), as_yaml=as_yaml)


if __name__ == "__main__":
    main()
