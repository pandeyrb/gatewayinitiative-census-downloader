"""Quick explorer for Census ACS output data.

Run examples:
    python explore.py                        # print all available groups
    python explore.py race                   # show race distribution for Lawrence
    python explore.py hispanic_latino        # show Hispanic/Latino breakdown
    python explore.py income                 # show income brackets
    python explore.py housing_costs tract    # show housing costs at tract level
"""

import sys
from pathlib import Path

import pandas as pd

ROOT     = Path(__file__).parent
DATA_DIR = ROOT / "outputs" / "lawrence" / "demographics" / "2022"
CODEBOOK = ROOT / "outputs" / "codebooks" / "demographics_codebook.csv"


def load(geo: str = "place") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the data file and codebook for the requested geography."""
    data_path = DATA_DIR / f"{geo}.csv"
    if not data_path.exists():
        available = [p.stem for p in DATA_DIR.glob("*.csv")]
        raise SystemExit(f"No file for '{geo}'. Available: {available}")
    return pd.read_csv(data_path), pd.read_csv(CODEBOOK)


def show_groups(codebook: pd.DataFrame) -> None:
    """Print all available group keys and their sub-theme names."""
    groups = codebook[["group_key", "sub_theme"]].drop_duplicates()
    print("\nAvailable groups:")
    print(f"  {'group_key':<25}  sub_theme")
    print("  " + "-" * 55)
    for _, row in groups.iterrows():
        print(f"  {row['group_key']:<25}  {row['sub_theme']}")
    print("\nUsage:  python explore.py <group_key>  [place|tract|block_group]")


def show_group(group_key: str, data: pd.DataFrame, codebook: pd.DataFrame) -> None:
    """Print a distribution table for one variable group."""
    group_rows = codebook[codebook["group_key"] == group_key]
    if group_rows.empty:
        print(f"Unknown group '{group_key}'. Run without arguments to see all groups.")
        return

    sub_theme = group_rows["sub_theme"].iloc[0]
    codes     = group_rows["variable_code"].tolist()
    labels    = group_rows.set_index("variable_code")["label"].to_dict()

    # For place-level there's one row; for tract there are many — show city total
    if len(data) > 1:
        row = data.select_dtypes("number").sum()
        geo_name = f"All {len(data)} tracts (aggregated)"
    else:
        row = data.iloc[0]
        geo_name = data["NAME"].iloc[0] if "NAME" in data.columns else "City total"

    # Find the universe/total for this group (first variable whose label contains "Total")
    total = None
    for code in codes:
        lbl = labels.get(code, "").lower()
        if "total" in lbl and "universe" in lbl or lbl in ("total", "total population"):
            val = row.get(code)
            if val and val > 0:
                total = float(val)
                break

    print(f"\n{'='*65}")
    print(f"  {sub_theme}")
    print(f"  {geo_name}")
    print(f"{'='*65}")
    print(f"  {'Label':<45}  {'Count':>8}  {'Share':>7}")
    print(f"  {'-'*45}  {'-'*8}  {'-'*7}")

    for code in codes:
        if code not in data.columns and code not in row.index:
            continue
        val = row.get(code, float("nan"))
        try:
            val = int(val)
        except (ValueError, TypeError):
            val = None

        lbl   = labels.get(code, code)
        count = f"{val:,}" if val is not None else "—"
        share = f"{val/total*100:.1f}%" if (total and val is not None) else ""
        print(f"  {lbl:<45}  {count:>8}  {share:>7}")

    print()


# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]

    data, codebook = load(args[1] if len(args) > 1 else "place")

    if not args:
        show_groups(codebook)
        return

    show_group(args[0], data, codebook)


if __name__ == "__main__":
    main()
