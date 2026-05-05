"""Geography resolution for Census API queries.

Returns for/in clause strings and post-fetch city filters.
The Census API uses "+" as the hierarchy separator in the `in` parameter and
requires "block%20group" (URL-encoded space) in the `for` parameter.

Tract filtering uses per-city tract_codes lists stored in config/cities.yaml.
Cities without tract_codes configured return all county tracts with a warning.
"""

import pandas as pd

GEO_LEVELS = ["place", "tract", "block_group", "block"]

# Census API column names that identify a row's geography.
GEO_KEY_COLS: dict[str, list[str]] = {
    "place":       ["state", "place"],
    "tract":       ["state", "county", "tract"],
    "block_group": ["state", "county", "tract", "block group"],
    "block":       ["state", "county", "tract", "block"],
}


def get_for_param(geo_level: str, city_config: dict) -> str:
    """Return the Census API `for` parameter value (space encoded as %20)."""
    place = city_config["place_fips"]
    if geo_level == "place":
        return f"place:{place}"
    if geo_level == "tract":
        return "tract:*"
    if geo_level == "block_group":
        return "block%20group:*"
    if geo_level == "block":
        return "block:*"
    raise ValueError(f"Unknown geo_level: {geo_level!r}")


def get_in_param(geo_level: str, city_config: dict) -> str:
    """Return the Census API `in` parameter value (+ separates hierarchy levels)."""
    state = city_config["state_fips"]
    county = city_config["county_fips"]
    if geo_level == "place":
        return f"state:{state}"
    if geo_level == "tract":
        return f"state:{state}+county:{county}"
    if geo_level == "block_group":
        return f"state:{state}+county:{county}+tract:*"
    if geo_level == "block":
        return f"state:{state}+county:{county}+tract:*+block%20group:*"
    raise ValueError(f"Unknown geo_level: {geo_level!r}")


def get_geo_key_cols(geo_level: str) -> list[str]:
    """Return the list of geo-identifier column names the API includes in responses."""
    return GEO_KEY_COLS[geo_level]


def filter_to_city(
    df: pd.DataFrame,
    geo_level: str,
    city_config: dict | None = None,
) -> pd.DataFrame:
    """Post-fetch filter: keep only rows inside the requested city.

    Place-level queries already scope to a single place; no filtering needed.
    Tract/block-group queries return the entire county — we keep only rows whose
    tract code appears in city_config["tract_codes"].

    If city_config is missing or tract_codes is empty, all county rows are
    returned with a warning. Populate tract_codes in config/cities.yaml to
    enable sub-city filtering for a given city.
    """
    if geo_level == "place":
        return df

    if "tract" not in df.columns:
        return df

    tract_codes = (city_config or {}).get("tract_codes") or []
    if not tract_codes:
        city_name = (city_config or {}).get("name", "this city")
        print(
            f"  [filter] WARNING: no tract_codes configured for {city_name}. "
            "Returning all county tracts — add tract_codes to config/cities.yaml "
            "to filter to city boundaries."
        )
        return df

    tract_set = frozenset(str(c) for c in tract_codes)
    filtered = df[df["tract"].isin(tract_set)].copy()
    dropped = len(df) - len(filtered)
    if dropped:
        city_name = (city_config or {}).get("name", "city")
        print(f"  [filter] Removed {dropped} non-{city_name} rows (kept {len(filtered)}).")
    return filtered


def build_geoid(row: pd.Series, geo_level: str) -> str:
    """Construct a Census GEOID from a DataFrame row.

    Lengths: place=7, tract=11, block_group=12, block=15.
    All component fields come from the Census API response columns.
    """
    state  = row.get("state",  "")
    county = row.get("county", "")
    tract  = row.get("tract",  "")

    if geo_level == "place":
        return state + row.get("place", "")
    if geo_level == "tract":
        return state + county + tract
    if geo_level == "block_group":
        return state + county + tract + str(row.get("block group", ""))
    if geo_level == "block":
        # block column is 4 digits; first digit equals the block group
        return state + county + tract + str(row.get("block", ""))
    return ""
