"""Thin wrapper around the Census Bureau API.

Handles:
- Variable chunking (≤44 vars + NAME per request, safely under the 50-var cap)
- Retries with exponential backoff (3 attempts)
- Multi-chunk merge on geo key columns
- GEOID construction
- Optional dry-run mode (prints URLs, skips fetches)
"""

import os
import time
import sys
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

from downloader.geo_resolver import (
    get_for_param,
    get_in_param,
    get_geo_key_cols,
    filter_to_city,
    build_geoid,
)

load_dotenv()

_CHUNK_SIZE = 44  # variables per request; +NAME = 45 total, safely under API cap of 50
_MAX_RETRIES = 3


class CensusClient:
    def __init__(self, year: int, dataset: str):
        self.year = year
        self.dataset = dataset
        self.base_url = f"https://api.census.gov/data/{year}/{dataset}"
        self.api_key = os.getenv("CENSUS_API_KEY")
        if not self.api_key:
            print(
                "WARNING: CENSUS_API_KEY not set. Requests will be unauthenticated "
                "and subject to lower rate limits (~500/day). "
                "Get a free key at https://api.census.gov/signup.html",
                file=sys.stderr,
            )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def fetch(
        self,
        variables: list[str],
        city_config: dict,
        geo_level: str,
        dry_run: bool = False,
    ) -> pd.DataFrame | None:
        """Fetch all variables for a city at a given geo level.

        Returns a merged DataFrame with a GEOID column, or None on dry-run.
        """
        for_param = get_for_param(geo_level, city_config)
        in_param  = get_in_param(geo_level, city_config)
        geo_keys  = get_geo_key_cols(geo_level)

        chunks = [
            variables[i: i + _CHUNK_SIZE]
            for i in range(0, len(variables), _CHUNK_SIZE)
        ]

        if dry_run:
            for i, chunk in enumerate(chunks):
                url = self._build_url("NAME," + ",".join(v for v in chunk if v != "NAME"), for_param, in_param)
                print(f"  [dry-run] [{geo_level}] batch {i+1}/{len(chunks)}: {url}")
            return None

        chunk_dfs: list[pd.DataFrame] = []
        for i, chunk in enumerate(chunks):
            # NAME is always prepended; drop it from the chunk to avoid duplicate columns
            get_str = "NAME," + ",".join(v for v in chunk if v != "NAME")
            url = self._build_url(get_str, for_param, in_param)
            print(
                f"  [{geo_level}] batch {i+1}/{len(chunks)}"
                f" ({len(chunk)} vars) …"
            )
            df = self._fetch_with_retry(url)
            if df is None:
                return None
            print(f"    → {len(df)} rows returned")

            if i > 0 and "NAME" in df.columns:
                df = df.drop(columns=["NAME"])
            chunk_dfs.append(df)

        result = chunk_dfs[0]
        for df in chunk_dfs[1:]:
            result = result.merge(df, on=geo_keys, how="outer")

        result = filter_to_city(result, geo_level, city_config)

        if result.empty:
            # Empty DataFrame after filtering — return early so the pipeline skips cleanly.
            # Calling apply() on a 0-row DataFrame in pandas 2.x returns a DataFrame
            # (not a Series), which would crash insert().
            return result

        result.insert(0, "GEOID", result.apply(build_geoid, axis=1, geo_level=geo_level))
        result.insert(1, "geo_level", geo_level)

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_url(self, get_str: str, for_param: str, in_param: str) -> str:
        """Build a Census API URL without re-encoding already-encoded characters."""
        url = f"{self.base_url}?get={get_str}&for={for_param}&in={in_param}"
        if self.api_key:
            url += f"&key={self.api_key}"
        return url

    def _fetch_with_retry(self, url: str) -> pd.DataFrame | None:
        for attempt in range(_MAX_RETRIES):
            try:
                resp = requests.get(url, timeout=120)
                if resp.status_code == 200:
                    return self._parse_response(resp)
                # The Census API sometimes returns 204 or error JSON
                msg = f"HTTP {resp.status_code}: {resp.text[:300]}"
                print(f"    WARNING: {msg}", file=sys.stderr)
                if resp.status_code in (400, 404):
                    # Non-retriable client errors
                    return None
            except requests.RequestException as exc:
                print(f"    WARNING: request error ({exc})", file=sys.stderr)

            wait = 2 ** (attempt + 1)
            print(f"    Retrying in {wait}s (attempt {attempt+2}/{_MAX_RETRIES}) …")
            time.sleep(wait)

        print(f"    ERROR: all {_MAX_RETRIES} attempts failed.", file=sys.stderr)
        return None

    @staticmethod
    def _parse_response(resp: requests.Response) -> pd.DataFrame | None:
        try:
            data = resp.json()
        except ValueError:
            print(f"    ERROR: non-JSON response: {resp.text[:200]}", file=sys.stderr)
            return None

        if not data or not isinstance(data, list) or len(data) < 2:
            print("    WARNING: empty or malformed response.", file=sys.stderr)
            return pd.DataFrame()

        headers, *rows = data
        df = pd.DataFrame(rows, columns=headers)

        # Geo and label columns stay as strings; all variable columns go numeric.
        # -666666666 is the Census suppression/N/A sentinel → convert to NaN.
        _GEO_COLS = frozenset({"NAME", "state", "county", "tract", "block group", "block", "place"})
        for col in df.columns:
            if col not in _GEO_COLS:
                df[col] = pd.to_numeric(df[col], errors="coerce").replace(-666666666, float("nan"))

        return df
