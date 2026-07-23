# Census ACS Downloader

A modular Python CLI for downloading US Census Bureau ACS 5-year data for all 26 Massachusetts Gateway Cities. It handles API authentication, variable chunking, per-city geography filtering, GEOID construction, and null-code handling automatically. Outputs tidy CSVs at the place, census tract, and block-group level — plus a Streamlit dashboard for Lawrence, MA.

---

## Table of Contents

1. [Setup](#1-setup)
2. [Project Layout](#2-project-layout)
3. [End-to-End Workflow](#3-end-to-end-workflow)
   - [Step 1 — Pick a topic](#step-1--pick-a-topic)
   - [Step 2 — Download the data](#step-2--download-the-data)
   - [Step 3 — Use the codebook](#step-3--use-the-codebook)
   - [Step 4 — Launch the dashboard](#step-4--launch-the-dashboard)
   - [Advanced: Building a custom topic](#advanced-building-a-custom-topic)
4. [CLI Reference](#4-cli-reference)
5. [How the Downloader Works](#5-how-the-downloader-works)
6. [Config Files](#6-config-files)
7. [Output Files](#7-output-files)
8. [Adding Cities and Topics](#8-adding-cities-and-topics)
9. [Data Quality & Verification](#9-data-quality--verification)
10. [Data Notes](#10-data-notes)

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
├── main.py                           # CLI entry point (Click)
├── dashboard.py                      # Streamlit multi-topic dashboard (Lawrence, MA)
├── lookup_table.py                   # Local ACS Table Shells viewer (no API needed)
├── explore.py                        # Terminal data explorer
├── requirements.txt
├── .env                              # Census API key (not committed)
│
├── config/
│   ├── cities.yaml                   # 26 MA Gateway Cities — FIPS codes + tract crosswalks
│   └── topics/
│       ├── demographics.yaml         # Population, age, race, language, nativity
│       ├── income_poverty.yaml       # Income distribution, poverty, SNAP
│       ├── education.yaml            # Attainment, enrollment, digital access
│       ├── housing.yaml              # Tenure, rent burden, home value, overcrowding
│       ├── economic.yaml             # Employment status, occupation, earnings
│       ├── health.yaml               # Health insurance, disability, veteran status
│       ├── commuting.yaml            # Commute mode, travel time, vehicles
│       └── internet_access.yaml      # Computer & internet subscriptions by income/age
│
├── downloader/
│   ├── __init__.py
│   ├── census_client.py              # Census API wrapper (chunking, retries, parsing)
│   ├── geo_resolver.py               # Geography parameter builder + per-city filter
│   ├── variable_loader.py            # Topic YAML loader + variable code validation
│   ├── pipeline.py                   # Orchestrates validate → fetch → filter → export
│   ├── variable_validator.py         # Cross-checks every variable code against Census API
│   └── table_browser.py              # Census table discovery + topic YAML generation
│
└── outputs/                          # All generated files (gitignored)
    ├── cache/
    │   └── groups_2022_acs_acs5.json # Cached table list (auto-created)
    ├── codebooks/
    │   └── {topic}_codebook.csv
    └── {city_slug}/
        └── {topic}/
            └── {year}/
                ├── place.csv
                ├── tract.csv
                ├── block_group.csv
                └── all_geo_levels.csv
```

---

## 3. End-to-End Workflow

### Step 1 — Pick a topic

Nine curated topic files ship with the tool. Each covers a distinct research domain and can be downloaded independently.

| Topic slug | What it covers | Key Census tables |
|---|---|---|
| `demographics` | Population, age pyramid, race, Hispanic origin, nativity, language, household type, disability | B01001, B02001, B03001, B05001, B06007, B11001, B18101 |
| `income_poverty` | Income distribution, median income by race, poverty depth, SNAP, family poverty | B19001, B19013, B17001, C17002, B22001 |
| `education` | Educational attainment (25+), attainment by sex, school enrollment, digital access | B15003, B15002, B14001, B28001, B28002 |
| `housing` | Units, tenure, overcrowding, structure type, age of housing, rent, rent burden, home value | B25001–B25014, B25024, B25034, B25063–B25064, B25070, B25077 |
| `economic` | Employment status, occupation by sex, median earnings, income inequality (Gini) | B23025, C24010, B20002, B19083 |
| `health` | Health insurance by age/sex/nativity/income/type, disability by type/age/sex, disability × insurance/poverty cross-tabs, veteran status, veteran employment, veteran disability ratings | B27001, B27010, C27007, B27020, C27001I, B27015, B18101–B18106, B18135, C18130, B21001, B21005, B21100 |
| `commuting` | Commute mode, travel time, vehicles available | B08301, B08303, B08013, B08201 |
| `internet_access` | Computer types, internet subscriptions, access by age and income | B28001, B28002, B28004, B28005 |
| `disability_characteristics` | Disability prevalence by sex, race, age, and type (hearing/vision/cognitive/ambulatory/self-care/independent living) — counts and percentages | S1810 |

### Step 2 — Download the data

```bash
# Download all topics for Lawrence (runs 8 commands)
python main.py --city lawrence --topic demographics   --year 2022 --geo all
python main.py --city lawrence --topic income_poverty --year 2022 --geo all
python main.py --city lawrence --topic education      --year 2022 --geo all
python main.py --city lawrence --topic housing        --year 2022 --geo all
python main.py --city lawrence --topic economic       --year 2022 --geo all
python main.py --city lawrence --topic health         --year 2022 --geo all
python main.py --city lawrence --topic commuting      --year 2022 --geo all
python main.py --city lawrence --topic internet_access --year 2022 --geo all
python main.py --city lawrence --topic disability_characteristics --year 2022 --geo all --dataset acs/acs5/subject
```

Each command writes four files to `outputs/lawrence/{topic}/2022/`:

| File | Rows | Notes |
|---|---|---|
| `place.csv` | 1 (city total) | Always available for all 26 cities |
| `tract.csv` | 1 per census tract | Requires `tract_codes` in `cities.yaml` |
| `block_group.csv` | 1 per block group | Requires `tract_codes` in `cities.yaml` |
| `all_geo_levels.csv` | All levels stacked | Includes `geo_level` column |

For other Gateway Cities (place-level only, no tract filtering needed):

```bash
python main.py --city brockton --topic demographics --year 2022 --geo place
python main.py --city springfield --topic income_poverty --year 2022 --geo place
```

### Step 3 — Use the codebook

Column headers in output CSVs are raw Census variable codes (e.g. `B15003_022E`). Generate a human-readable lookup:

```bash
python main.py --topic demographics --codebook
python main.py --topic economic --codebook
# ...one per topic
```

Each command writes `outputs/codebooks/{topic}_codebook.csv` with columns:
`topic`, `dataset`, `year`, `group_key`, `sub_theme`, `variable_code`, `label`.

**Join in Python:**

```python
import pandas as pd

df = pd.read_csv("outputs/lawrence/economic/2022/place.csv")
codebook = pd.read_csv("outputs/codebooks/economic_codebook.csv")
rename = dict(zip(codebook["variable_code"], codebook["label"]))
df_labeled = df.rename(columns=rename)
```

**Join in Excel:**

Open the data file and codebook. Use `VLOOKUP(B1, codebook!$A:$B, 2, FALSE)` in a header row to decode variable codes across all columns, where column A is `variable_code` and column B is `label`.

### Step 4 — Launch the dashboard

The Streamlit dashboard covers Lawrence, MA across all eight topics. It automatically shows a "not downloaded" prompt for any topic whose data files are missing.

```bash
streamlit run dashboard.py
```

Open <http://localhost:8501>. The sidebar lets you switch between **City Total** and **Census Tract** views. Tabs cover:

- **Demographics** — age pyramid, race/ethnicity, Hispanic origin breakdown
- **Income & Poverty** — income distribution, poverty depth, income by race
- **Education** — attainment, enrollment, digital access
- **Housing** — tenure, rent burden, median rent and home value
- **Economic** — employment status, occupation, earnings by sex
- **Health** — uninsured by age, disability, veteran status
- **Commuting** — commute mode, travel time distribution
- **Internet Access** — internet subscriptions by income and age

Each tab loads its data independently — download topics in any order.

---

### Advanced: Building a custom topic

#### A — Search for tables by keyword

```bash
python main.py --list-census-tables --search "disability"
python main.py --list-census-tables --search "veteran"
python main.py --list-census-tables --search "broadband"
```

#### B — Inspect a table's variables

```bash
python lookup_table.py B18101              # print all variables for a table
python lookup_table.py B18101 B28002       # multiple tables at once
python lookup_table.py B18101 --yaml       # print as ready-to-paste YAML snippet
```

Or query the live API:

```bash
python main.py --table B18101 --shell
```

#### C — Generate a topic YAML and download

```bash
python main.py --table B18101 --table B28002 --create-topic disability_internet
python main.py --city lawrence --topic disability_internet --year 2022 --geo all
```

`--create-topic` writes `config/topics/disability_internet.yaml` automatically.

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
| `--validate` | Check every labeled variable code in `--topic` (or all topics) against the Census API. Prints a report and exits 1 if mismatches are found. |
| `--export-labeled` | Write `*_labeled.csv` files alongside existing downloads, with columns renamed from variable codes to human-readable labels. Requires `--city` (or omit for all cities). Topic is optional; omit to export all downloaded topics. |

### Table browser flags

| Flag | Description |
|------|-------------|
| `--list-census-tables` | List all Census ACS tables for `--year`/`--dataset` |
| `--search KEYWORD` | Keyword filter for `--list-census-tables` |
| `--table TABLE_ID` | Census table ID — repeatable |
| `--shell` | Print variable codes and labels for `--table`(s) |
| `--create-topic NAME` | Generate a topic YAML from `--table`(s) |

### Examples

```bash
# Download demographics at all geo levels for Brockton
python main.py --city brockton --topic demographics --year 2022 --geo all

# Preview API calls without fetching
python main.py --city lawrence --topic economic --dry-run

# Search for broadband-related tables
python main.py --list-census-tables --search "broadband"

# Generate codebook for all topics
for topic in demographics income_poverty education housing economic health commuting internet_access disability_characteristics; do
  python main.py --topic $topic --codebook
done
```

---

## 5. How the Downloader Works

### Data flow

```
main.py
  └─ pipeline.run_pipeline()
       ├─ variable_loader.load_topic()        reads topic YAML → variable list
       ├─ variable_loader.load_cities()       reads cities.yaml → city FIPS + tract codes
       ├─ variable_validator.validate_topic() ← checks every code against Census API (cached)
       │    └─ prints warnings for any label mismatches; does not block the download
       └─ for each geo_level:
            ├─ census_client.CensusClient.fetch()
            │    ├─ geo_resolver.get_for_param()    builds ?for= clause
            │    ├─ geo_resolver.get_in_param()     builds &in= clause
            │    ├─ splits variables into batches of 44
            │    ├─ for each batch: _fetch_with_retry() → _parse_response()
            │    └─ merges batches on geo key columns
            ├─ geo_resolver.filter_to_city()   drops rows outside city (uses tract_codes)
            ├─ geo_resolver.build_geoid()      constructs GEOID column
            └─ pipeline._write_output()        writes CSV / Excel
```

### Module descriptions

#### `downloader/geo_resolver.py` — Geography resolution and city filtering

Builds Census API `for=` and `in=` parameters from a city config and geo level, then filters county-wide tract/block-group responses to city boundaries.

**City filtering**

Tract and block-group queries return every row in the county. `filter_to_city()` reads `city_config["tract_codes"]` and keeps only matching rows. If `tract_codes` is empty, all county rows are returned with a warning — useful for exploratory downloads before tract codes are configured.

```python
# In config/cities.yaml for Lawrence:
tract_codes: ["250100", "250200", ..., "251800"]   # 18 tracts
```

For any city without `tract_codes`, add them to `cities.yaml` using the process described in [Adding Cities and Topics](#8-adding-cities-and-topics).

**GEOID construction**

| Level | Formula | Length |
|---|---|---|
| Place | `state + place` | 7 digits |
| Tract | `state + county + tract` | 11 digits |
| Block group | `state + county + tract + block_group` | 12 digits |

GEOIDs match Census TIGER/Line shapefiles and ArcGIS Living Atlas layers — use them directly as join keys.

#### `downloader/census_client.py` — API wrapper

Chunks variables into batches of 44, retries with exponential backoff, parses JSON responses, and replaces the Census null sentinel (`-666666666`) with `NaN`.

#### `downloader/variable_loader.py` — Topic YAML loader

Parses topic YAML files, validates variable codes against `^[A-Z][0-9]+[A-Z]?_[0-9]+[EM]$`, and returns a flat ordered variable list plus code-to-label and code-to-group mappings.

#### `downloader/pipeline.py` — Orchestration

Loops over geography levels, calls `CensusClient.fetch()`, warns on variables with >20% null values (indicating Census suppression), writes output files, and generates codebooks.

#### `downloader/variable_validator.py` — Label cross-check against the Census API

Runs automatically before every data fetch. For each variable in the topic YAML that has a configured label, it:

1. Fetches the full table shell from the Census API (cached to disk at `outputs/cache/shells/`).
2. Checks that the variable code exists in its parent table.
3. Checks that key terms in the configured label don't contradict the Census label — specifically, flags cases where the label says "female" but the Census reports "male" (or vice versa), and where the label says "below poverty" but the Census reports "above poverty" (or vice versa).

Uses word-boundary regex so "female" never accidentally triggers on "male" as a substring.

**What it catches:** wrong variable codes whose sex or poverty direction flatly contradicts the Census path — the most common class of error when tables are written by hand.

**What it doesn't catch:** wrong sub-group within the correct sex/poverty direction (e.g., picking "married-couple with children" instead of "married-couple total" — both are "at or above poverty"). Those require the manual sanity checks in [Data Quality & Verification](#9-data-quality--verification).

#### `downloader/table_browser.py` — Census table discovery

Fetches the full ACS table list from the Census metadata API (cached locally). Provides `generate_topic_yaml()` to auto-generate topic YAML from one or more table shells.

---

## 6. Config Files

### `config/cities.yaml`

Defines all 26 Massachusetts Gateway Cities. Each entry has:

```yaml
lawrence:
  name: Lawrence
  state_fips: "25"        # Massachusetts state FIPS
  place_fips: "34550"     # 5-digit Census place FIPS (verified against live API)
  county_fips: "009"      # 3-digit Essex County FIPS
  tract_codes:            # 6-digit Census API "tract" column values inside city limits
    - "250100"            # 18 tracts verified via Census Geocoder (2022 vintage)
    - "250200"
    # ... through "251800"
```

Cities without `tract_codes` populated will return all county tracts with a warning when queried at tract or block-group level. Place-level queries (`--geo place`) always work for all 26 cities.

### `config/topics/*.yaml`

Each file defines a named set of Census variables grouped into sub-themes:

```yaml
topic_name: economic
dataset: acs/acs5
year: 2022

variable_groups:
  employment_status:
    label: "Employment Status (Population 16+)"
    variables:
      - code: B23025_001E
        label: "Total population 16 years and over"
      - code: B23025_004E
        label: "In labor force: Civilian: Employed"
      ...
```

| Field | Description |
|---|---|
| `topic_name` | Human-readable label used in codebook output |
| `dataset` | Census API dataset path (e.g. `acs/acs5`) |
| `year` | Default vintage year — overridden by `--year` on the CLI |
| `variable_groups` | Dict of group keys, each with a `label` and `variables` list |

Variable codes must match `^[A-Z][0-9]+[A-Z]?_[0-9]+[EM]$`. The `E` suffix is the estimate; `M` is the margin of error. Use `lookup_table.py` or `--shell` to verify codes before adding them.

---

## 7. Output Files

All outputs land in `outputs/{city}/{topic}/{year}/`.

### Per-level files

| File | Rows | Key columns |
|---|---|---|
| `place.csv` | 1 (the city) | `GEOID`, `geo_level`, `NAME`, then variable codes |
| `tract.csv` | 1 per census tract | `GEOID`, `geo_level`, `NAME`, `state`, `county`, `tract` |
| `block_group.csv` | 1 per block group | `GEOID`, `geo_level`, `NAME`, `state`, `county`, `tract`, `block group` |
| `all_geo_levels.csv` | all stacked | `geo_level` column identifies each row's source |

### Codebook

`outputs/codebooks/{topic}_codebook.csv`:

| Column | Description |
|---|---|
| `topic` | Topic name |
| `dataset` | Census dataset |
| `year` | Vintage year |
| `group_key` | Variable group key from the YAML |
| `sub_theme` | Human-readable group label |
| `variable_code` | Census variable code (e.g. `B23025_004E`) |
| `label` | Variable description |

### Matching outputs to spatial data

The `GEOID` column matches the format used by:
- Census TIGER/Line shapefiles
- ArcGIS Living Atlas Census boundary layers
- Census Geocoder API responses

Use `GEOID` as the join key to merge demographic outputs with geometry for mapping.

---

## 8. Adding Cities and Topics

### Adding tract codes for a city

Place-level downloads (`--geo place`) work immediately for all 26 cities. To enable tract and block-group filtering for a city, add its tract codes to `cities.yaml`.

**Step 1 — Find which county tracts fall inside the city**

Download all county tracts for your city's county (e.g. Middlesex County for Lowell):

```bash
python main.py --city lowell --topic demographics --year 2022 --geo tract
```

Since Lowell has no `tract_codes` configured, this returns all Middlesex County tracts with a warning. Open the resulting `tract.csv` and filter the `NAME` column for rows containing "Lowell" — those are the candidate tracts.

**Step 2 — Verify with Census Geocoder (optional but recommended)**

Cross-check tract centroids at <https://geocoding.geo.census.gov> or via the Census Geocoder API to confirm tract boundaries match city limits.

**Step 3 — Add to `cities.yaml`**

```yaml
lowell:
  name: Lowell
  state_fips: "25"
  place_fips: "37000"
  county_fips: "017"
  tract_codes:
    - "210101"
    - "210102"
    # ... verified Middlesex County tract codes for Lowell
```

After adding `tract_codes`, re-run `--geo tract` to get city-filtered output.

### Adding a new topic

**Automatic (recommended):**

```bash
python main.py --list-census-tables --search "food insecurity"
python main.py --table B22001 --shell
python main.py --table B22001 --create-topic food_assistance
python main.py --city lawrence --topic food_assistance --year 2022 --geo all
```

**Manual:** Create a YAML file in `config/topics/` following the existing format. Use `lookup_table.py` or `--shell` to verify all variable codes before running a download.

---

## 9. Data Quality & Verification

Census ACS tables are hierarchically nested. Variable numbers are **not sequential across major groups** — the female or "at or above poverty" section of a table always begins much later than you might expect, after dozens of male or "below poverty" sub-rows. When topic YAML files are written by hand without verifying codes against the Census API, it's easy to pick the wrong variable for an entire section.

### Automatic validation

The pipeline runs a label cross-check automatically before every data fetch:

```
Validating variable labels …
  ✓  All labeled variables match their Census API definitions.
```

If any code is misassigned, you'll see a report instead:

```
  ✗  health: 3 issue(s) found

  [MISMATCH]  B21001_007E  —  group: veteran_status
    config label : "Female: Total"
    Census label : Total > Male > 18 to 34 years
    detail       : Label says "female" but Census variable belongs to the "male" category.
```

To run validation alone (no data download), across all topics or one:

```bash
python main.py --validate                       # all 10 topics, exits 1 if any issues
python main.py --validate --topic health        # one topic
```

Table shells are cached after the first check, so subsequent validation runs are instant.

### Manual sanity checks

The automatic validator catches sex and poverty-direction contradictions. To catch subtler errors — wrong sub-group within the correct section — run these checks on downloaded data:

**Rule 1 — Male + Female must equal the stated total**

```python
import pandas as pd

df = pd.read_csv("outputs/lawrence/health/2022/place.csv")
row = df.iloc[0]

# B27001 health insurance
assert row["B27001_002E"] + row["B27001_030E"] == row["B27001_001E"], \
    f"Health insurance: male + female != total"

# B23001 employment by sex/age
assert row["B23001_002E"] + row["B23001_088E"] == row["B23001_001E"], \
    f"Employment: male + female != total"
```

**Rule 2 — Below poverty + at or above must equal the universe**

```python
pov = pd.read_csv("outputs/lawrence/income_poverty/2022/place.csv")
row = pov.iloc[0]

assert row["B17001_002E"] + row["B17001_031E"] == row["B17001_001E"], \
    f"B17001: below + above != total universe"
```

**Rule 3 — Sex sub-totals within each poverty direction must sum correctly**

```python
# Below poverty: male + female should equal below poverty total
below_male   = row["B17001_003E"]
below_female = row["B17001_017E"]
below_total  = row["B17001_002E"]
assert below_male + below_female == below_total, \
    f"Below poverty male+female mismatch"
```

**Expected values for Lawrence, MA (2022 ACS5)**

The following checks all pass after the variable codes were corrected. Use these as a baseline — if a re-download produces very different numbers, something may be wrong.

| Table | Variable | Value | What it measures |
|-------|----------|------:|-----------------|
| B27001 | Male + Female = Total | 43,242 + 44,094 = 87,336 | Health insurance universe |
| B21001 | Male + Female = Total | 31,205 + 32,932 = 64,137 | Veteran status universe |
| B23001 | Male + Female = Total | 32,474 + 34,147 = 66,621 | Employment 16+ universe |
| B17001 | Below + Above = Total | 16,901 + 70,111 = 87,012 | Poverty status universe |
| B20017 | Female/Male earnings ratio | $40,021 / $49,414 = 81¢ | Median earnings gender gap |

### What to do if validation flags an issue

1. Run `python main.py --validate --topic <topic>` to see the full report.
2. Look up the correct variable code: `python main.py --table <TABLE_ID> --shell` or `python lookup_table.py <TABLE_ID>`.
3. Fix the code in `config/topics/<topic>.yaml`.
4. Re-run validation to confirm it passes.
5. Re-download the topic.

---

## 10. Data Notes

### Census suppression → NaN

The Census Bureau uses `-666666666` as a sentinel for suppressed or unavailable data. All output files replace this with `NaN`. A null value means the Census did not publish the estimate (typically due to small sample size), not that the download failed.

The pipeline warns when more than 20% of rows for a variable are null — this surfaces tables that are suppressed at the requested geography level.

### Tables suppressed at block-group level

Several ACS tables are not published at block-group granularity. Variables from these tables appear as 100% null in `block_group.csv`:

| Table | Topic |
|---|---|
| B03001 | Hispanic or Latino origin by specific subgroup |
| B05001 | Nativity and citizenship |
| B06007 | Language spoken at home by place of birth |
| B17001 | Poverty status by sex by age |
| B17020 | Poverty status by race (suppressed at block group) |
| B27001 | Health insurance by sex and age |
| C27007 | Medicaid coverage by sex and age |
| B27020 | Health insurance by nativity |
| B18135 | Disability × health insurance cross-tab |
| C18130 | Disability × poverty cross-tab |
| B21005 | Veteran employment status by age |
| B21100 | Veteran disability ratings |

Switch to `--geo tract` or `--geo place` for these variables.

### ACS does not publish block-level data

`--geo block` is silently skipped for all ACS datasets. Block-level data requires the Decennial Census (`dec/dhc`), not the ACS.

### GEOID format

| Level | Formula | Length |
|---|---|---|
| Place | state(2) + place(5) | 7 digits |
| Tract | state(2) + county(3) + tract(6) | 11 digits |
| Block group | state(2) + county(3) + tract(6) + bg(1) | 12 digits |

### Lawrence tract crosswalk

Lawrence sits in Essex County (18 tracts, codes 250100–251800). These were verified by reverse-geocoding all tract centroids through the Census Geocoder API — all 18 resolve to "Lawrence city, Massachusetts" with no cross-city overlap. Tract codes for other Gateway Cities can be populated in `cities.yaml` using the process in [Adding Cities and Topics](#8-adding-cities-and-topics).

### API rate limits and variable chunking

The Census API rejects requests with more than 50 variables. This tool batches 44 variables per request (plus `NAME` = 45) and merges results on geography key columns. For the `demographics` topic (174 variables), each geography level requires 4 API calls. Without an API key: ~500 requests/day. With a key: much higher.
