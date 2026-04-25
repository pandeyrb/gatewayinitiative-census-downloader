"""Lawrence, MA Demographic Dashboard — ACS 5-Year 2022."""

import math
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Lawrence MA Demographics",
    page_icon="🏙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Lawrence color palette ────────────────────────────────────────────────────
NAVY    = "#1B3A6B"   # primary
CRIMSON = "#BE2D2C"   # female / contrast
GOLD    = "#D4A724"   # accent
TEAL    = "#2A9D8F"
PLUM    = "#6B4C8C"
AMBER   = "#CA7000"
SAGE    = "#52796F"
SLATE   = "#4A5568"

RACE_PAL = [NAVY, CRIMSON, GOLD, TEAL, PLUM, AMBER, SAGE]
HISP_PAL = [NAVY, TEAL, CRIMSON, GOLD, PLUM, AMBER, SAGE, SLATE]

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT     = Path(__file__).parent
DATA_DIR = ROOT / "outputs" / "lawrence" / "demographics" / "2022"

# ── Variable definitions ──────────────────────────────────────────────────────
# Age pyramid: each entry is (label, [male_codes], [female_codes]).
# Adjacent Census age bands are merged into standard 5-year groups.
AGE_GROUPS = [
    ("Under 5",  ["B01001_003E"],                                      ["B01001_027E"]),
    ("5–9",      ["B01001_004E"],                                      ["B01001_028E"]),
    ("10–14",    ["B01001_005E"],                                      ["B01001_029E"]),
    ("15–19",    ["B01001_006E", "B01001_007E"],                       ["B01001_030E", "B01001_031E"]),
    ("20–24",    ["B01001_008E", "B01001_009E", "B01001_010E"],        ["B01001_032E", "B01001_033E", "B01001_034E"]),
    ("25–29",    ["B01001_011E"],                                      ["B01001_035E"]),
    ("30–34",    ["B01001_012E"],                                      ["B01001_036E"]),
    ("35–39",    ["B01001_013E"],                                      ["B01001_037E"]),
    ("40–44",    ["B01001_014E"],                                      ["B01001_038E"]),
    ("45–49",    ["B01001_015E"],                                      ["B01001_039E"]),
    ("50–54",    ["B01001_016E"],                                      ["B01001_040E"]),
    ("55–59",    ["B01001_017E"],                                      ["B01001_041E"]),
    ("60–64",    ["B01001_018E", "B01001_019E"],                       ["B01001_042E", "B01001_043E"]),
    ("65–69",    ["B01001_020E", "B01001_021E"],                       ["B01001_044E", "B01001_045E"]),
    ("70–74",    ["B01001_022E"],                                      ["B01001_046E"]),
    ("75–79",    ["B01001_023E"],                                      ["B01001_047E"]),
    ("80–84",    ["B01001_024E"],                                      ["B01001_048E"]),
    ("85+",      ["B01001_025E"],                                      ["B01001_049E"]),
]

RACE_VARS = {
    "B02001_002E": "White alone",
    "B02001_003E": "Black or African American",
    "B02001_004E": "Amer. Indian & Alaska Native",
    "B02001_005E": "Asian",
    "B02001_006E": "Native Hawaiian & Pacific Isl.",
    "B02001_007E": "Some other race",
    "B02001_008E": "Two or more races",
}

# B03001_002E = Not Hispanic/Latino (large baseline group kept for full picture)
# B03001_008E / _016E are sub-total codes for Central/South American
HISPANIC_VARS = {
    "B03001_002E": "Not Hispanic/Latino",
    "B03001_005E": "Puerto Rican",
    "B03001_007E": "Dominican",
    "B03001_008E": "Central American",
    "B03001_004E": "Mexican",
    "B03001_016E": "South American",
    "B03001_006E": "Cuban",
    "B03001_027E": "Other Hispanic/Latino",
}

# Human-readable label for every variable in the demographics topic.
# Used to rename data columns in the raw-data expander.
VAR_LABELS: dict[str, str] = {
    "B01001_001E": "Total population",
    "B01002_001E": "Median age",
    "B01001_002E": "Male: total",
    "B01001_003E": "Male: Under 5",
    "B01001_004E": "Male: 5–9",
    "B01001_005E": "Male: 10–14",
    "B01001_006E": "Male: 15–17",
    "B01001_007E": "Male: 18–19",
    "B01001_008E": "Male: 20",
    "B01001_009E": "Male: 21",
    "B01001_010E": "Male: 22–24",
    "B01001_011E": "Male: 25–29",
    "B01001_012E": "Male: 30–34",
    "B01001_013E": "Male: 35–39",
    "B01001_014E": "Male: 40–44",
    "B01001_015E": "Male: 45–49",
    "B01001_016E": "Male: 50–54",
    "B01001_017E": "Male: 55–59",
    "B01001_018E": "Male: 60–61",
    "B01001_019E": "Male: 62–64",
    "B01001_020E": "Male: 65–66",
    "B01001_021E": "Male: 67–69",
    "B01001_022E": "Male: 70–74",
    "B01001_023E": "Male: 75–79",
    "B01001_024E": "Male: 80–84",
    "B01001_025E": "Male: 85+",
    "B01001_026E": "Female: total",
    "B01001_027E": "Female: Under 5",
    "B01001_028E": "Female: 5–9",
    "B01001_029E": "Female: 10–14",
    "B01001_030E": "Female: 15–17",
    "B01001_031E": "Female: 18–19",
    "B01001_032E": "Female: 20",
    "B01001_033E": "Female: 21",
    "B01001_034E": "Female: 22–24",
    "B01001_035E": "Female: 25–29",
    "B01001_036E": "Female: 30–34",
    "B01001_037E": "Female: 35–39",
    "B01001_038E": "Female: 40–44",
    "B01001_039E": "Female: 45–49",
    "B01001_040E": "Female: 50–54",
    "B01001_041E": "Female: 55–59",
    "B01001_042E": "Female: 60–61",
    "B01001_043E": "Female: 62–64",
    "B01001_044E": "Female: 65–66",
    "B01001_045E": "Female: 67–69",
    "B01001_046E": "Female: 70–74",
    "B01001_047E": "Female: 75–79",
    "B01001_048E": "Female: 80–84",
    "B01001_049E": "Female: 85+",
    "B02001_001E": "Race: total",
    "B02001_002E": "White alone",
    "B02001_003E": "Black or African American alone",
    "B02001_004E": "American Indian & Alaska Native alone",
    "B02001_005E": "Asian alone",
    "B02001_006E": "Native Hawaiian & Other Pacific Islander alone",
    "B02001_007E": "Some other race alone",
    "B02001_008E": "Two or more races",
    "B02001_009E": "Two races incl. some other race",
    "B02001_010E": "Two races excl. some other race / three or more races",
    "B03001_001E": "Hispanic/Latino: total",
    "B03001_002E": "Not Hispanic or Latino",
    "B03001_003E": "Hispanic or Latino (total)",
    "B03001_004E": "Mexican",
    "B03001_005E": "Puerto Rican",
    "B03001_006E": "Cuban",
    "B03001_007E": "Dominican",
    "B03001_008E": "Central American (total)",
    "B03001_009E": "Costa Rican",
    "B03001_010E": "Guatemalan",
    "B03001_011E": "Honduran",
    "B03001_012E": "Nicaraguan",
    "B03001_013E": "Panamanian",
    "B03001_014E": "Salvadoran",
    "B03001_015E": "Other Central American",
    "B03001_016E": "South American (total)",
    "B03001_017E": "Argentinean",
    "B03001_018E": "Bolivian",
    "B03001_019E": "Chilean",
    "B03001_020E": "Colombian",
    "B03001_021E": "Ecuadorian",
    "B03001_022E": "Paraguayan",
    "B03001_023E": "Peruvian",
    "B03001_024E": "Uruguayan",
    "B03001_025E": "Venezuelan",
    "B03001_026E": "Other South American",
    "B03001_027E": "Other Hispanic or Latino",
    "B03001_028E": "Spaniard",
    "B03001_029E": "Spanish",
    "B03001_030E": "Spanish American",
    "B03001_031E": "All other Hispanic or Latino",
    "B05001_001E": "Citizenship: total",
    "B05001_002E": "US citizen, born in US",
    "B05001_003E": "US citizen, born in PR/territories",
    "B05001_004E": "US citizen, born abroad of US parent(s)",
    "B05001_005E": "US citizen by naturalization",
    "B05001_006E": "Not a US citizen",
    "B06007_001E": "Language: total",
    "B06007_002E": "Speak only English",
    "B06007_003E": "Speak Spanish",
    "B06007_004E": "Spanish — English less than very well",
    "B06007_005E": "Speak other Indo-European languages",
    "B06007_006E": "Indo-European — English less than very well",
    "B06007_007E": "Speak Asian & Pacific Island languages",
    "B06007_008E": "Asian/PI — English less than very well",
    "B06007_009E": "Speak other languages",
    "B19013_001E": "Median household income ($)",
    "B19001_001E": "HH income: total",
    "B19001_002E": "HH income: Less than $10,000",
    "B19001_003E": "HH income: $10,000–$14,999",
    "B19001_004E": "HH income: $15,000–$19,999",
    "B19001_005E": "HH income: $20,000–$24,999",
    "B19001_006E": "HH income: $25,000–$29,999",
    "B19001_007E": "HH income: $30,000–$34,999",
    "B19001_008E": "HH income: $35,000–$39,999",
    "B19001_009E": "HH income: $40,000–$44,999",
    "B19001_010E": "HH income: $45,000–$49,999",
    "B19001_011E": "HH income: $50,000–$59,999",
    "B19001_012E": "HH income: $60,000–$74,999",
    "B19001_013E": "HH income: $75,000–$99,999",
    "B19001_014E": "HH income: $100,000–$124,999",
    "B19001_015E": "HH income: $125,000–$149,999",
    "B19001_016E": "HH income: $150,000–$199,999",
    "B19001_017E": "HH income: $200,000 or more",
    "B17001_001E": "Poverty status: total",
    "B17001_002E": "Below poverty level",
    "B17001_003E": "Male: below poverty level",
    "B17001_004E": "Female: below poverty level",
    "B17020_001E": "Poverty by race: total",
    "B17020_002E": "Below poverty level (race)",
    "B17020_003E": "At or above poverty level (race)",
    "B25001_001E": "Total housing units",
    "B25002_001E": "Occupancy status: total",
    "B25002_002E": "Occupied housing units",
    "B25002_003E": "Vacant housing units",
    "B25003_001E": "Tenure: total",
    "B25003_002E": "Owner occupied",
    "B25003_003E": "Renter occupied",
    "B25064_001E": "Median gross rent ($)",
    "B25077_001E": "Median home value ($)",
    "B25070_001E": "Gross rent as % of income: total",
    "B25070_002E": "Rent burden: Less than 10%",
    "B25070_003E": "Rent burden: 10–14.9%",
    "B25070_004E": "Rent burden: 15–19.9%",
    "B25070_005E": "Rent burden: 20–24.9%",
    "B25070_006E": "Rent burden: 25–29.9%",
    "B25070_007E": "Rent burden: 30–34.9%",
    "B25070_008E": "Rent burden: 35–39.9%",
    "B25070_009E": "Rent burden: 40–49.9%",
    "B25070_010E": "Rent burden: 50%+",
    "B25070_011E": "Rent burden: not computed",
    "B25091_001E": "Owner costs as % of income: total",
    "B25091_002E": "Owner burden (w/ mortgage): <10%",
    "B25091_003E": "Owner burden (w/ mortgage): 10–14.9%",
    "B25091_004E": "Owner burden (w/ mortgage): 15–19.9%",
    "B25091_005E": "Owner burden (w/ mortgage): 20–24.9%",
    "B25091_006E": "Owner burden (w/ mortgage): 25–29.9%",
    "B25091_007E": "Owner burden (w/ mortgage): 30–34.9%",
    "B25091_008E": "Owner burden (w/ mortgage): 35–39.9%",
    "B25091_009E": "Owner burden (w/ mortgage): 40–49.9%",
    "B25091_010E": "Owner burden (w/ mortgage): 50%+",
    "B25091_011E": "Owner burden (w/ mortgage): not computed",
    "B25091_012E": "Owner burden (w/o mortgage): <10%",
    "B25091_013E": "Owner burden (w/o mortgage): 10–14.9%",
    "B25091_014E": "Owner burden (w/o mortgage): 15–19.9%",
    "B25091_015E": "Owner burden (w/o mortgage): 20–24.9%",
    "B25091_016E": "Owner burden (w/o mortgage): 25–29.9%",
    "B25091_017E": "Owner burden (w/o mortgage): 30–34.9%",
    "B25091_018E": "Owner burden (w/o mortgage): 35–39.9%",
    "B25091_019E": "Owner burden (w/o mortgage): 40–49.9%",
    "B25091_020E": "Owner burden (w/o mortgage): 50%+",
    "B25091_021E": "Owner burden (w/o mortgage): not computed",
    "B25091_022E": "Owner burden: zero/negative income (w/ mortgage)",
    "B25091_023E": "Owner burden: zero/negative income (w/o mortgage)",
}

# ── Helpers ───────────────────────────────────────────────────────────────────
def safe(row, key, default=0):
    """Return row[key], substituting default for missing or NaN values."""
    v = row.get(key, default)
    try:
        if math.isnan(float(v)):
            return default
    except (TypeError, ValueError):
        pass
    return v


def _nice_tick(max_val: float) -> int:
    for step in [50, 100, 250, 500, 1000, 2500, 5000, 10000]:
        if max_val / step <= 7:
            return step
    return 10000


def _tract_label(name_str) -> str:
    if isinstance(name_str, str) and "Census Tract" in name_str:
        num = name_str.split(";")[0].replace("Census Tract", "").strip()
        return f"Tract {num}"
    return str(name_str)


def _is_null(val) -> bool:
    if val is None:
        return True
    try:
        return math.isnan(float(val))
    except (TypeError, ValueError):
        return False


# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    place = pd.read_csv(DATA_DIR / "place.csv")
    tract = pd.read_csv(DATA_DIR / "tract.csv")
    tract["_label"] = tract["NAME"].apply(_tract_label)
    return place, tract


def labeled_df(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with Census variable codes replaced by human-readable labels."""
    return df.rename(columns={k: v for k, v in VAR_LABELS.items() if k in df.columns})


# ── Chart builders ────────────────────────────────────────────────────────────
def fig_age_pyramid(row: pd.Series, subtitle: str) -> go.Figure:
    labels, males, females = [], [], []
    for lbl, m_codes, f_codes in AGE_GROUPS:
        labels.append(lbl)
        males.append(sum(safe(row, c) for c in m_codes))
        females.append(sum(safe(row, c) for c in f_codes))

    max_val = max(max(males), max(females)) * 1.15
    step = _nice_tick(max_val)
    tick_vals = list(range(-round(max_val // step) * step, round(max_val // step) * step + step, step))

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Male",
        y=labels,
        x=[-v for v in males],
        orientation="h",
        marker_color=NAVY,
        marker_line_width=0,
        customdata=males,
        hovertemplate="<b>%{y}</b><br>Male: %{customdata:,}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Female",
        y=labels,
        x=females,
        orientation="h",
        marker_color=CRIMSON,
        marker_line_width=0,
        hovertemplate="<b>%{y}</b><br>Female: %{x:,}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=f"Age Pyramid  ·  {subtitle}", font_size=15, font_color=SLATE),
        barmode="overlay",
        bargap=0.12,
        xaxis=dict(
            tickvals=tick_vals,
            ticktext=[f"{abs(v):,}" for v in tick_vals],
            title="Population",
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor="#bbb",
            gridcolor="#efefef",
        ),
        yaxis=dict(title="", gridcolor="#efefef"),
        legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center", font_size=13),
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=560,
        margin=dict(l=70, r=30, t=70, b=50),
    )
    return fig


def fig_race(row: pd.Series, subtitle: str) -> go.Figure:
    total = safe(row, "B02001_001E", 1) or 1
    data = [(lbl, safe(row, var)) for var, lbl in RACE_VARS.items()]
    data.sort(key=lambda x: x[1], reverse=True)

    labels = [d[0] for d in data]
    vals   = [d[1] for d in data]
    pcts   = [v / total * 100 for v in vals]
    colors = [RACE_PAL[i % len(RACE_PAL)] for i in range(len(labels))]

    fig = go.Figure(go.Bar(
        y=labels,
        x=vals,
        orientation="h",
        marker_color=colors,
        marker_line_width=0,
        text=[f"{p:.1f}%" for p in pcts],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>%{x:,}  (%{text})<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=f"Race  ·  {subtitle}", font_size=15, font_color=SLATE),
        xaxis=dict(title="Population", gridcolor="#efefef"),
        yaxis=dict(autorange="reversed"),
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=380,
        margin=dict(l=215, r=90, t=60, b=50),
    )
    return fig


def fig_hispanic(row: pd.Series, subtitle: str) -> go.Figure:
    total = safe(row, "B03001_001E", 1) or 1
    data = [(lbl, safe(row, var)) for var, lbl in HISPANIC_VARS.items()]
    data.sort(key=lambda x: x[1], reverse=True)

    labels = [d[0] for d in data]
    vals   = [d[1] for d in data]
    pcts   = [v / total * 100 for v in vals]
    colors = [HISP_PAL[i % len(HISP_PAL)] for i in range(len(labels))]

    fig = go.Figure(go.Bar(
        y=labels,
        x=vals,
        orientation="h",
        marker_color=colors,
        marker_line_width=0,
        text=[f"{p:.1f}%" for p in pcts],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>%{x:,}  (%{text})<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=f"Hispanic/Latino Ethnicity  ·  {subtitle}", font_size=15, font_color=SLATE),
        xaxis=dict(title="Population", gridcolor="#efefef"),
        yaxis=dict(autorange="reversed"),
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=380,
        margin=dict(l=185, r=90, t=60, b=50),
    )
    return fig


# ── Metric helpers ────────────────────────────────────────────────────────────
def _weighted_mean(df: pd.DataFrame, val_col: str, weight_col: str) -> float | None:
    """Population-weighted mean of a median variable across tracts."""
    mask = ~df[val_col].isna() & ~df[weight_col].isna() & (df[val_col] > 0)
    if mask.sum() == 0:
        return None
    w = df.loc[mask, weight_col]
    v = df.loc[mask, val_col]
    return float((v * w).sum() / w.sum())


# ── Main layout ───────────────────────────────────────────────────────────────
place_df, tract_df = load_data()

ALL_TRACTS_LABEL = "All tracts (aggregate)"

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<div style='background:#1B3A6B;padding:14px 14px 12px;border-radius:8px;"
        "margin-bottom:20px;border-left:4px solid #D4A724'>"
        "<div style='color:white;font-size:1.15rem;font-weight:700'>🏙 Lawrence, MA</div>"
        "<div style='color:#D4A724;font-size:0.82rem;margin-top:2px'>"
        "ACS 5-Year Estimates · 2022</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("**Geography Level**")
    geo_level = st.radio(
        label="geo",
        options=["City Total", "Census Tract"],
        label_visibility="collapsed",
    )

    tract_choice = None
    if geo_level == "Census Tract":
        st.markdown("**Select Tract**")
        tract_labels = tract_df["_label"].tolist()
        tract_choice = st.selectbox(
            label="tract",
            options=[ALL_TRACTS_LABEL] + tract_labels,
            label_visibility="collapsed",
        )

    st.divider()
    st.caption("Source: US Census Bureau")
    st.caption("Essex County, MA · FIPS 009")
    st.caption("Gateway Cities Initiative")

# ── Resolve selected data ─────────────────────────────────────────────────────
is_aggregate = False

if geo_level == "City Total":
    row = place_df.iloc[0]
    subtitle = "Lawrence city"
    med_age_display = safe(row, "B01002_001E", None)
    inc_display     = safe(row, "B19013_001E", None)

elif tract_choice == ALL_TRACTS_LABEL:
    row = tract_df.select_dtypes("number").sum()
    subtitle = "All 18 Lawrence tracts (aggregate)"
    is_aggregate = True
    med_age_display = _weighted_mean(tract_df, "B01002_001E", "B01001_001E")
    inc_display     = _weighted_mean(tract_df, "B19013_001E", "B01001_001E")

else:
    row = tract_df.loc[tract_df["_label"] == tract_choice].iloc[0]
    subtitle = f"Lawrence — {tract_choice}"
    med_age_display = safe(row, "B01002_001E", None)
    inc_display     = safe(row, "B19013_001E", None)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='margin-bottom:0;color:#1B3A6B'>"
    "Lawrence, MA · Demographic Dashboard</h1>"
    "<p style='color:#4A5568;margin-top:4px;font-size:0.95rem'>"
    "American Community Survey 5-Year Estimates · 2022 · Essex County</p>",
    unsafe_allow_html=True,
)
st.divider()

# ── Key metrics ───────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)

pop    = int(safe(row, "B01001_001E"))
hisp_n = safe(row, "B03001_003E", None)
hisp_t = safe(row, "B03001_001E", None)
pov_n  = safe(row, "B17001_002E", None)
pov_t  = safe(row, "B17001_001E", None)

c1.metric("Total Population",   f"{pop:,}")
c2.metric(
    "Median Age",
    f"{med_age_display:.1f}" if med_age_display is not None else "—",
    help="Population-weighted mean of tract medians for aggregate view." if is_aggregate else None,
)
c3.metric(
    "Hispanic/Latino",
    f"{hisp_n / hisp_t * 100:.1f}%" if hisp_n is not None and hisp_t else "—",
)
c4.metric(
    "Median HH Income",
    f"${int(inc_display):,}" if inc_display is not None and inc_display > 0 else "—",
    help="Population-weighted mean of tract medians for aggregate view." if is_aggregate else None,
)
c5.metric(
    "Below Poverty",
    f"{pov_n / pov_t * 100:.1f}%" if pov_n is not None and pov_t else "—",
)

st.divider()

# ── Age pyramid ───────────────────────────────────────────────────────────────
st.plotly_chart(fig_age_pyramid(row, subtitle), use_container_width=True)

st.divider()

# ── Race + Hispanic/Latino side by side ───────────────────────────────────────
col_race, col_hisp = st.columns(2)

with col_race:
    st.plotly_chart(fig_race(row, subtitle), use_container_width=True)

with col_hisp:
    b03_null = _is_null(row.get("B03001_001E"))
    if b03_null:
        st.info(
            "Hispanic/Latino detail (B03001) is not published at this geography "
            "level by the Census Bureau. Switch to **City Total** or a **Census Tract** "
            "to see this chart.",
            icon="ℹ️",
        )
    else:
        st.plotly_chart(fig_hispanic(row, subtitle), use_container_width=True)

st.divider()

# ── Raw data expander ─────────────────────────────────────────────────────────
with st.expander("📋  View underlying data with human-readable column names"):
    if geo_level == "City Total":
        display_df = labeled_df(place_df)
    else:
        display_df = labeled_df(tract_df.drop(columns=["_label"], errors="ignore"))

    # Move GEOID, NAME, geo_level to front; drop raw geo columns
    geo_cols = [c for c in ["GEOID", "geo_level", "NAME"] if c in display_df.columns]
    other_cols = [c for c in display_df.columns if c not in geo_cols]
    st.dataframe(
        display_df[geo_cols + other_cols],
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        f"{len(display_df)} row(s) · {len(display_df.columns)} columns  "
        "| Variable codes renamed using the demographics codebook"
    )
