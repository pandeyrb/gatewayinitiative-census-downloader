# Census ACS Downloader

A modular Python CLI for downloading US Census Bureau ACS 5-year data for Massachusetts Gateway Cities. It handles API authentication, variable chunking, geography filtering, GEOID construction, and null-code handling automatically. Outputs tidy CSVs or Excel files at the place, census tract, and block-group level.

---

## Table of Contents

1. [Setup](#1-setup)
2. [Project Layout](#2-project-layout)
3. [End-to-End Workflow](#3-end-to-end-workflow)
4. [CLI Reference](#4-cli-reference)
5. [How the Downloader Works](#5-how-the-downloader-works)
6. [Config Files](#6-config-files)
7. [Output Files](#7-output-files)
8. [Adding Cities and Topics](#8-adding-cities-and-topics)
9. [Data Notes](#9-data-notes)

---

## 1. Setup

### Requirements

Python 3.10 or later. Install dependencies:

```bash
pip install -r requirements.txt
```

### Census API key (recommended)

Register for a free key at <https://api.census.gov/signup.html>. Without one, the Census Bureau allows roughly 500 unauthenticated requests per day; with a key, limits are much higher.

Create a `.env` file in the project root:

```
CENSUS_API_KEY=your_key_here
```

The tool works without a key but prints a warning at startup.

---

## 2. Project Layout

```
census_downloader/
│
├── main.py                          # CLI entry point (Click)
├── requirements.txt
├── .env                             # Census API key (not committed)
│
├── config/
│   ├── cities.yaml                  # 26 MA Gateway Cities with FIPS codes
│   └── topics/
│       ├── demographics.yaml        # 174 variables across 9 groups
│       └── income_poverty.yaml      # Example auto-generated topic
│
├── downloader/
│   ├── __init__.py
│   ├── census_client.py             # Census API wrapper (chunking, retries, parsing)
│   ├── geo_resolver.py              # Geography parameter builder + city filter
│   ├── variable_loader.py           # Topic YAML loader + variable code validation
│   ├── pipeline.py                  # Orchestrates fetch → filter → export
│   └── table_browser.py             # Census table discovery + topic YAML generation
│
└── outputs/                         # All generated files (gitignored)
    ├── cache/
    │   └── groups_2022_acs_acs5.json  # Cached table list (auto-created)
    ├── codebooks/
    │   └── demographics_codebook.csv
    └── lawrence/
        └── demographics/
            └── 2022/
                ├── place.csv
                ├── tract.csv
                ├── block_group.csv
                └── all_geo_levels.csv
```

---

## 3. End-to-End Workflow

The intended workflow goes from discovery → topic creation → data download → visualization.

### Step 1 — Find the Census tables you need

The Census Bureau publishes over 1,100 ACS 5-year tables organized by topic. Search them by keyword:

```bash
python main.py --list-census-tables --search "education"
python main.py --list-census-tables --search "language"
python main.py --list-census-tables --search "income"
```

Each line in the output is a table ID (e.g. `B15003`) and its description (e.g. `Educational Attainment for the Population 25 Years and Over`).

### Step 2 — Inspect a table's shell

A table shell lists every variable code and its label. This shows exactly what data is inside a table before you commit to downloading it:

```bash
python main.py --table B15003 --shell
```

Output:
```
B15003 — 26 estimate variable(s)  [2022 acs/acs5]
------------------------------------------------------------------------
  Variable        Label
  --------------  --------------------------------------------------------
  B15003_001E     Total
  B15003_002E     Total > No schooling completed
  B15003_003E     Total > Nursery school
  ...
  B15003_022E     Total > Bachelor's degree
  B15003_023E     Total > Master's degree
  B15003_025E     Total > Doctorate degree
```

You can inspect multiple tables at once:

```bash
python main.py --table B15003 --table B16004 --shell
```

### Step 3 — Create a topic YAML

Once you've identified the tables you want, generate a topic configuration file in one command:

```bash
python main.py --table B15003 --table B16004 --create-topic education_language
```

This fetches both table shells, groups variables by table, and writes `config/topics/education_language.yaml` — ready to use immediately with no manual editing required.

### Step 4 — Download the data

```bash
python main.py --city lawrence --topic education_language --year 2022 --geo all
```

This writes four files to `outputs/lawrence/education_language/2022/`:
- `place.csv` — one row for Lawrence city
- `tract.csv` — one row per census tract (18 tracts for Lawrence)
- `block_group.csv` — one row per block group
- `all_geo_levels.csv` — all levels stacked

---

## 4. CLI Reference

### Download flags

| Flag | Default | Description |
|------|---------|-------------|
| `--city SLUG` | required | City slug from `config/cities.yaml` (e.g. `lawrence`, `brockton`) |
| `--topic SLUG` | required | Topic slug matching a file in `config/topics/` |
| `--year INT` | `2022` | ACS 5-year vintage year |
| `--geo LEVEL` | `all` | Geography level: `all`, `place`, `tract`, `block_group` |
| `--dataset STRING` | `acs/acs5` | Census dataset identifier |
| `--output-format` | `csv` | `csv`, `excel`, or `both` |
| `--dry-run` | off | Print variable list and API URLs without fetching |

### Informational flags

| Flag | Description |
|------|-------------|
| `--list-cities` | Print all 26 city slugs and exit |
| `--list-topics` | Print all local topic YAML files and exit |
| `--codebook` | Write a variable codebook CSV for `--topic` and exit |

### Table browser flags

| Flag | Description |
|------|-------------|
| `--list-census-tables` | List all Census ACS tables for `--year`/`--dataset` |
| `--search KEYWORD` | Keyword filter for `--list-census-tables` |
| `--table TABLE_ID` | Census table ID — repeatable (e.g. `--table B01001 --table B02001`) |
| `--shell` | Print variable codes and labels for `--table`(s) and exit |
| `--create-topic NAME` | Generate a topic YAML from `--table`(s) and save to `config/topics/` |

### Examples

```bash
# Search for tables related to housing costs
python main.py --list-census-tables --search "gross rent"

# Preview B25063 (gross rent) variable shell
python main.py --table B25063 --shell

# Create a housing topic from two tables
python main.py --table B25063 --table B25070 --create-topic housing_costs

# Download for Brockton at tract level only
python main.py --city brockton --topic housing_costs --year 2022 --geo tract

# Preview API URLs without fetching (useful for debugging)
python main.py --city lawrence --topic demographics --dry-run

# Generate a variable codebook CSV
python main.py --topic demographics --codebook

# Export to Excel in addition to CSV
python main.py --city springfield --topic demographics --output-format both
```

---

## 5. How the Downloader Works

Understanding the internals helps when adding new cities, debugging unexpected null values, or extending the tool to new datasets.

### Data flow

```
main.py
  └─ pipeline.run_pipeline()
       ├─ variable_loader.load_topic()        reads topic YAML → variable list
       ├─ variable_loader.load_cities()       reads cities.yaml → city FIPS codes
       └─ for each geo_level:
            ├─ census_client.CensusClient.fetch()
            │    ├─ geo_resolver.get_for_param()    builds ?for= clause
            │    ├─ geo_resolver.get_in_param()     builds &in= clause
            │    ├─ splits variables into batches of 44
            │    ├─ for each batch: _fetch_with_retry() → _parse_response()
            │    └─ merges batches on geo key columns
            ├─ geo_resolver.filter_to_city()   drops non-Lawrence rows
            ├─ build_geoid()                   constructs GEOID column
            └─ pipeline._write_output()        writes CSV / Excel
```

### Module descriptions

#### `main.py` — CLI entry point

Uses [Click](https://click.palletsprojects.com/) to define all flags. Handles three categories of commands:

- **Informational**: `--list-cities`, `--list-topics`, `--codebook` — read config files, print, and exit.
- **Table browser**: `--list-census-tables`, `--shell`, `--create-topic` — hit the Census API metadata endpoints and exit.
- **Download**: requires `--city` and `--topic`, calls `pipeline.run_pipeline()`.

---

#### `downloader/table_browser.py` — Census table discovery

Wraps the Census Bureau's metadata API to let you explore what data exists before writing any config.

**`fetch_groups(year, dataset, cache_dir)`**

Calls `https://api.census.gov/data/{year}/{dataset}/groups.json`, which returns the complete list of 1,100+ tables with their IDs and descriptions. Results are cached as JSON in `outputs/cache/` so the second call is instant — no repeat API hit.

**`fetch_table_shell(table_id, year, dataset)`**

Calls `https://api.census.gov/data/{year}/{dataset}/groups/{TABLE}.json`. Each table's response contains every variable code with its raw hierarchical label:

```
B01001_003E → "Estimate!!Total:!!Male:!!Under 5 years"
```

This function filters to Estimate-only codes — codes ending in `E` but not `EA` (annotation codes). Margin-of-error codes (`M`, `MA`) are excluded. Returns `{code: raw_label}`.

**`shell_to_readable(shell)`**

Converts raw Census labels to a readable form by splitting on `!!`, dropping the leading `Estimate` token, and joining with ` > `:

```
"Estimate!!Total:!!Male:!!Under 5 years"  →  "Total > Male > Under 5 years"
```

**`generate_topic_yaml(...)`**

Assembles the topic YAML dict from one or more table shells. Each table becomes one `variable_group` keyed by its table ID (lowercase). The group label is taken from the table's description in `groups.json`. The result is written to `config/topics/{name}.yaml` by `main.py`.

---

#### `downloader/variable_loader.py` — Topic YAML loader

Reads a topic YAML and returns two things consumed by `pipeline.py`:

- **`variables`** — flat ordered list of all variable codes (`["B01001_001E", "B01001_002E", ...]`). Deduplicates codes that appear in multiple groups.
- **`var_to_group`** — dict mapping each code to its sub-theme label, used for codebook generation and pipeline diagnostics.

Validates all codes against the pattern `^[A-Z][0-9]+_[0-9]+[EM]$` and raises a descriptive error if any code is malformed.

---

#### `downloader/census_client.py` — API wrapper

`CensusClient.fetch(variables, city_config, geo_level, dry_run)` handles everything between having a variable list and getting a clean DataFrame back.

**Variable chunking**

The Census API rejects requests with more than 50 variables in the `get=` parameter. This client splits the full variable list into chunks of 44 (leaving room for `NAME` = 45 per request, safely under the cap). Multiple chunk results are merged on geo-identifier columns (e.g., `["state", "county", "tract"]`) after fetching.

For the default `demographics` topic (174 variables), each geography level requires 4 API calls.

**Retry logic**

Each chunk request retries up to 3 times with exponential backoff (2s, then 4s) on network errors or non-400/404 HTTP errors. 400 and 404 responses are treated as non-retriable client errors and return immediately.

**Response parsing**

The Census API returns a JSON array where the first element is the header row and subsequent elements are data rows:

```json
[["NAME","B01001_001E","state","county","tract"],
 ["Census Tract 2501","4820","25","009","250100"],
 ...]
```

This is parsed into a DataFrame. All non-geography columns (`NAME`, `state`, `county`, `tract`, `block group`, `place`) are converted to numeric with `pd.to_numeric(errors="coerce")`. The Census null sentinel value `-666666666` is replaced with `NaN`.

**GEOID construction**

After all chunks are merged and the city filter applied, `geo_resolver.build_geoid()` is applied row-by-row using `DataFrame.apply()` to construct standard Census GEOIDs from the component FIPS columns.

---

#### `downloader/geo_resolver.py` — Geography resolution and city filtering

**Parameter building**

The Census API uses a hierarchical geography syntax expressed as two URL parameters. This module builds them from a city config and geo level:

| `geo_level` | `for=` | `in=` |
|---|---|---|
| `place` | `place:34550` | `state:25` |
| `tract` | `tract:*` | `state:25+county:009` |
| `block_group` | `block%20group:*` | `state:25+county:009+tract:*` |

The `+` character separates hierarchy levels in the `in=` parameter. `block%20group` uses URL-encoded space because the Census API column name contains a literal space — this is not a typo.

**City filtering**

Tract and block-group queries return every row in the entire county, not just those inside the city. For Lawrence (Essex County, MA), this means the API returns all ~100 Essex County tracts. `filter_to_city()` keeps only the 18 tracts whose 6-digit code appears in `LAWRENCE_TRACT_CODES`:

```python
LAWRENCE_TRACT_CODES = frozenset({
    "250100", "250200", ..., "251800"   # 18 tracts verified via Census Geocoder
})
```

These codes were established by: (1) downloading all Essex County tract centroids from the Census Gazetteer file, (2) reverse-geocoding all candidate centroids through the Census Geocoder API, and (3) confirming every centroid resolved to "Lawrence city, Massachusetts" with no cross-city contamination.

**GEOID construction**

GEOIDs are built from the component FIPS columns that the API includes in every response:

| Level | Formula | Length | Example |
|---|---|---|---|
| Place | `state + place` | 7 digits | `2534550` |
| Tract | `state + county + tract` | 11 digits | `25009250100` |
| Block group | `state + county + tract + block_group` | 12 digits | `250092501001` |

---

#### `downloader/pipeline.py` — Orchestration

`run_pipeline()` loops over the requested geography levels and for each:

1. **Skips `block` level** for ACS datasets with an explanatory message. ACS only goes down to block group; block-level data requires the Decennial Census.
2. **Calls `CensusClient.fetch()`** to get a filtered DataFrame.
3. **Calls `_warn_nulls()`** — prints a warning for any variable where more than 20% of rows are null. This surfaces Census-suppressed tables that aren't published at a given geography (e.g., B03001 Hispanic origin is suppressed at block group).
4. **Calls `_write_output()`** to write CSV and/or Excel.

After all levels complete, it stacks all results into `all_geo_levels.csv` with a `geo_level` column identifying each row's source geography.

---

## 6. Config Files

### `config/cities.yaml`

Defines all 26 Massachusetts Gateway Cities. Each entry has:

```yaml
lawrence:
  name: Lawrence
  state_fips: "25"        # Massachusetts state FIPS
  place_fips: "34550"     # 5-digit Census place FIPS
  county_fips: "009"      # 3-digit Essex County FIPS
```

All FIPS codes have been verified against the live Census ACS API. Many place FIPS codes in earlier versions were wrong — for example, Lawrence's was previously `37000`, which is actually Lowell's code. All 26 were cross-referenced by querying `place:*&in=state:25` and matching against the `NAME` field returned by the API.

### `config/topics/*.yaml`

Each topic file defines a named set of Census variables grouped into sub-themes:

```yaml
topic_name: demographics
dataset: acs/acs5
year: 2022

variable_groups:
  population_age:
    label: "Population by Age and Sex"
    variables:
      - B01001_001E   # Total population
      - B01001_002E   # Male
      - B01001_003E   # Male: Under 5 years
      ...
  race:
    label: "Race"
    variables:
      - B02001_001E   # Total
      - B02001_002E   # White alone
      ...
```

| Field | Description |
|---|---|
| `topic_name` | Human-readable label used in codebook output |
| `dataset` | Census API dataset path (e.g. `acs/acs5`, `acs/acs1`, `dec/dhc`) |
| `year` | Vintage year — overridden by `--year` on the CLI |
| `variable_groups` | Dict of group keys, each with a `label` and `variables` list |

Variable codes must follow the pattern `^[A-Z][0-9]+_[0-9]+[EM]$`. Use `E` suffix for estimates, `M` for margins of error.

The `demographics` topic ships with 174 variables across 9 groups: population and age, race, Hispanic/Latino origin, nativity, language spoken at home, income, poverty, housing units, and housing costs.

---

## 7. Output Files

All outputs land in `outputs/{city}/{topic}/{year}/`.

### Per-level files

| File | Rows | Key columns |
|---|---|---|
| `place.csv` | 1 (the city) | `GEOID`, `geo_level`, `NAME`, then all variable codes |
| `tract.csv` | 1 per census tract | `GEOID`, `geo_level`, `NAME`, `state`, `county`, `tract` |
| `block_group.csv` | 1 per block group | `GEOID`, `geo_level`, `NAME`, `state`, `county`, `tract`, `block group` |
| `all_geo_levels.csv` | all of the above stacked | `geo_level` column identifies each row's source |

### GEOID column

The `GEOID` column is the standard Census identifier — 11 digits for tracts, 12 for block groups. Use it as the join key when merging with Census TIGER/Line shapefiles, ArcGIS Hub layers, or any other spatial dataset.

### Codebook

`--codebook` generates `outputs/codebooks/{topic}_codebook.csv`:

| Column | Description |
|---|---|
| `topic` | Topic name |
| `dataset` | Census dataset |
| `year` | Vintage year |
| `group_key` | Variable group key from the YAML |
| `sub_theme` | Human-readable group label |
| `variable_code` | Census variable code (e.g. `B01001_003E`) |

Use this to translate raw variable-code column headers in the output CSVs to readable labels.

### Cache

`outputs/cache/groups_{year}_{dataset}.json` — the full Census table list, fetched once and reused on all subsequent `--list-census-tables` calls. Delete this file to force a refresh from the API.

---

## 8. Adding Cities and Topics

### Adding a city

Add an entry to `config/cities.yaml`:

```yaml
new_city:
  name: New City
  state_fips: "25"
  place_fips: "XXXXX"     # 5-digit zero-padded place FIPS
  county_fips: "XXX"      # 3-digit county FIPS
```

Look up place FIPS codes by querying the API directly:

```bash
curl "https://api.census.gov/data/2022/acs/acs5?get=NAME,place&for=place:*&in=state:25&key=YOUR_KEY"
```

Or use the Census ANSI reference: <https://www.census.gov/library/reference/code-lists/ansi.html>

**Important limitation:** Place-level queries (`--geo place`) work immediately for any city in `cities.yaml`. Tract and block-group queries return the entire county and are post-filtered using a city-specific tract crosswalk. Currently the crosswalk only covers Lawrence. To support sub-city geographies for another city, add its tract codes to `LAWRENCE_TRACT_CODES` in `geo_resolver.py` (renaming and generalizing the structure as needed) and update `filter_to_city()` to dispatch by city slug.

### Adding a topic — automatic (recommended)

```bash
# Find the tables you want
python main.py --list-census-tables --search "employment"

# Inspect one
python main.py --table B23025 --shell

# Generate the YAML
python main.py --table B23025 --create-topic employment

# Download
python main.py --city lawrence --topic employment --year 2022 --geo all
```

### Adding a topic — manually

Create a YAML file in `config/topics/`. The auto-generated format uses one group per table; you can hand-edit to split a table into finer sub-groups or combine select variables from multiple tables:

```yaml
topic_name: housing
dataset: acs/acs5
year: 2022

variable_groups:
  tenure:
    label: "Housing Tenure"
    variables:
      - B25003_001E   # Total occupied housing units
      - B25003_002E   # Owner occupied
      - B25003_003E   # Renter occupied
  gross_rent:
    label: "Gross Rent"
    variables:
      - B25063_001E   # Total
      - B25063_002E   # With cash rent
      - B25063_026E   # No cash rent
      - B25064_001E   # Median gross rent (dollars)
```

---

## 10. Data Notes

### Census suppression → NaN

The Census Bureau uses `-666666666` as a sentinel value for suppressed or unavailable data. This is automatically replaced with `NaN` in all output files. A null value does not mean the tool failed — it means the Census did not publish that estimate, typically because the sample size at that geography was too small to meet reliability standards.

### Tables suppressed at block-group level

Several ACS tables are not published at block-group granularity. Variables from these tables will be 100% null in `block_group.csv`:

| Table | Topic |
|---|---|
| B03001 | Hispanic or Latino origin by specific subgroup |
| B05001 | Nativity |
| B06007 | Language spoken at home by place of birth |
| B17001 | Poverty status by sex by age |
| B17020 | Poverty status by race |

The pipeline logs a warning for any variable where more than 20% of rows are null.

### ACS does not publish block-level data

The `--geo block` flag is silently skipped for all ACS datasets with a printed explanation. Block-level data (individual census blocks, not block groups) is only available from the Decennial Census (e.g., `dec/dhc`). The ACS is a sample survey and does not produce statistically reliable estimates at the block level.

### GEOID format

GEOIDs are fully padded strings:

| Level | Format | Length |
|---|---|---|
| Place | state(2) + place(5) | 7 |
| Tract | state(2) + county(3) + tract(6) | 11 |
| Block group | state(2) + county(3) + tract(6) + bg(1) | 12 |

These match the GEOID format used by Census TIGER/Line shapefiles and ArcGIS Living Atlas layers — use them directly as join keys.

### Lawrence tract crosswalk

Lawrence, MA sits in Essex County. Tract and block-group queries return all ~100 Essex County tracts; the tool filters to Lawrence's 18 tracts using a verified crosswalk. The 18 tract codes (`250100`–`251800`) were confirmed by reverse-geocoding all tract centroids through the Census Geocoder API — all 18 resolve to "Lawrence city, Massachusetts."

### API rate limits and chunking

Without an API key: ~500 requests/day. With a key: much higher (Anthropic does not publish an exact cap; it is rarely hit in practice for city-scale work).

The Census API rejects requests with more than 50 variables. This tool batches 44 variables per request (plus `NAME` = 45 total) and merges results on geography key columns. For the default `demographics` topic (174 variables), each geography level requires 4 API calls.
