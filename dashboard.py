"""Lawrence, MA — Multi-Topic Demographic Dashboard · ACS 5-Year 2022."""

import math
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Lawrence MA · Census Dashboard",
    page_icon="🏙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Color palette ─────────────────────────────────────────────────────────────
NAVY    = "#1B3A6B"
CRIMSON = "#BE2D2C"
GOLD    = "#D4A724"
TEAL    = "#2A9D8F"
PLUM    = "#6B4C8C"
AMBER   = "#CA7000"
SAGE    = "#52796F"
SLATE   = "#4A5568"
GREEN   = "#276749"
ORANGE  = "#C05621"

RACE_PAL  = [NAVY, CRIMSON, GOLD, TEAL, PLUM, AMBER, SAGE]
HISP_PAL  = [NAVY, TEAL, CRIMSON, GOLD, PLUM, AMBER, SAGE, SLATE]
MULTI_PAL = [NAVY, CRIMSON, GOLD, TEAL, PLUM, AMBER, SAGE, SLATE, GREEN, ORANGE]

# ── Data directories ──────────────────────────────────────────────────────────
ROOT        = Path(__file__).parent
OUTPUTS_DIR = ROOT / "outputs" / "lawrence"
YEAR        = "2022"

TOPIC_DIRS: dict[str, Path] = {
    "demographics":   OUTPUTS_DIR / "demographics"   / YEAR,
    "income_poverty": OUTPUTS_DIR / "income_poverty" / YEAR,
    "education":      OUTPUTS_DIR / "education"      / YEAR,
    "housing":        OUTPUTS_DIR / "housing"        / YEAR,
    "economic":       OUTPUTS_DIR / "economic"       / YEAR,
    "health":         OUTPUTS_DIR / "health"         / YEAR,
    "commuting":      OUTPUTS_DIR / "commuting"      / YEAR,
    "internet_access":OUTPUTS_DIR / "internet_access"/ YEAR,
}

DOWNLOAD_CMDS: dict[str, str] = {
    "demographics":   "python main.py --city lawrence --topic demographics --year 2022 --geo all",
    "income_poverty": "python main.py --city lawrence --topic income_poverty --year 2022 --geo all",
    "education":      "python main.py --city lawrence --topic education --year 2022 --geo all",
    "housing":        "python main.py --city lawrence --topic housing --year 2022 --geo all",
    "economic":       "python main.py --city lawrence --topic economic --year 2022 --geo all",
    "health":         "python main.py --city lawrence --topic health --year 2022 --geo all",
    "commuting":      "python main.py --city lawrence --topic commuting --year 2022 --geo all",
    "internet_access":"python main.py --city lawrence --topic internet_access --year 2022 --geo all",
}

# ── Demographics variable definitions ────────────────────────────────────────
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

# Income distribution labels
INCOME_BANDS = [
    ("B19001_002E", "< $10k"),
    ("B19001_003E", "$10–15k"),
    ("B19001_004E", "$15–20k"),
    ("B19001_005E", "$20–25k"),
    ("B19001_006E", "$25–30k"),
    ("B19001_007E", "$30–35k"),
    ("B19001_008E", "$35–40k"),
    ("B19001_009E", "$40–45k"),
    ("B19001_010E", "$45–50k"),
    ("B19001_011E", "$50–60k"),
    ("B19001_012E", "$60–75k"),
    ("B19001_013E", "$75–100k"),
    ("B19001_014E", "$100–125k"),
    ("B19001_015E", "$125–150k"),
    ("B19001_016E", "$150–200k"),
    ("B19001_017E", "$200k+"),
]

POVERTY_DEPTH_BANDS = [
    ("B17002_002E", "< 0.50 (deep poverty)"),
    ("B17002_003E", "0.50–0.99 (below poverty)"),
    ("B17002_004E", "1.00–1.24"),
    ("B17002_005E", "1.25–1.49"),
    ("B17002_006E", "1.50–1.74"),
    ("B17002_007E", "1.75–1.84"),
    ("B17002_008E", "1.85–1.99"),
    ("B17002_009E", "2.00+ (200% of poverty)"),
]

RENT_BURDEN_BANDS = [
    ("B25070_002E", "< 10%"),
    ("B25070_003E", "10–14.9%"),
    ("B25070_004E", "15–19.9%"),
    ("B25070_005E", "20–24.9%"),
    ("B25070_006E", "25–29.9%"),
    ("B25070_007E", "30–34.9%"),
    ("B25070_008E", "35–39.9%"),
    ("B25070_009E", "40–49.9%"),
    ("B25070_010E", "50%+"),
]

COMMUTE_MODES = [
    ("B08301_003E", "Drove alone"),
    ("B08301_004E", "Carpooled"),
    ("B08301_010E", "Public transit"),
    ("B08301_018E", "Bicycle"),
    ("B08301_019E", "Walked"),
    ("B08301_021E", "Worked from home"),
    ("B08301_020E", "Other"),
]

TRAVEL_TIME_BANDS = [
    ("B08303_002E", "< 5 min"),
    ("B08303_003E", "5–9"),
    ("B08303_004E", "10–14"),
    ("B08303_005E", "15–19"),
    ("B08303_006E", "20–24"),
    ("B08303_007E", "25–29"),
    ("B08303_008E", "30–34"),
    ("B08303_009E", "35–39"),
    ("B08303_010E", "40–44"),
    ("B08303_011E", "45–59"),
    ("B08303_012E", "60–89"),
    ("B08303_013E", "90+ min"),
]

ATTAINMENT_BANDS = [
    ("B15003_002E", "No schooling"),
    ("B15003_016E", "12th, no diploma"),
    ("B15003_017E", "HS diploma"),
    ("B15003_018E", "GED"),
    ("B15003_019E", "Some college < 1 yr"),
    ("B15003_020E", "Some college ≥ 1 yr"),
    ("B15003_021E", "Associate's"),
    ("B15003_022E", "Bachelor's"),
    ("B15003_023E", "Master's"),
    ("B15003_024E", "Professional"),
    ("B15003_025E", "Doctorate"),
]

OCCUPATION_GROUPS = [
    ("C24010_003E", "Mgmt / Business / Science / Arts"),
    ("C24010_007E", "Service"),
    ("C24010_008E", "Sales & Office"),
    ("C24010_009E", "Natural Resources / Construction"),
    ("C24010_010E", "Production / Transportation"),
]


# ── Helpers ───────────────────────────────────────────────────────────────────
def safe(row, key, default=0):
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


def _weighted_mean(df: pd.DataFrame, val_col: str, weight_col: str) -> float | None:
    mask = ~df[val_col].isna() & ~df[weight_col].isna() & (df[val_col] > 0)
    if mask.sum() == 0:
        return None
    w = df.loc[mask, weight_col]
    v = df.loc[mask, val_col]
    return float((v * w).sum() / w.sum())


def _pct(n, d, default="—") -> str:
    if n is None or d is None or d == 0:
        return default
    try:
        return f"{float(n) / float(d) * 100:.1f}%"
    except (TypeError, ValueError):
        return default


# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data
def load_topic(topic: str) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    d = TOPIC_DIRS[topic]
    try:
        place = pd.read_csv(d / "place.csv")
        tract = pd.read_csv(d / "tract.csv")
        tract["_label"] = tract["NAME"].apply(_tract_label)
        return place, tract
    except FileNotFoundError:
        return None, None


def _not_downloaded(topic: str) -> None:
    st.info(
        f"Data for this topic has not been downloaded yet. Run:\n\n"
        f"```\n{DOWNLOAD_CMDS[topic]}\n```",
        icon="ℹ️",
    )


# ── Chart builders ────────────────────────────────────────────────────────────
def fig_age_pyramid(row: pd.Series, subtitle: str) -> go.Figure:
    labels, males, females = [], [], []
    for lbl, m_codes, f_codes in AGE_GROUPS:
        labels.append(lbl)
        males.append(sum(safe(row, c) for c in m_codes))
        females.append(sum(safe(row, c) for c in f_codes))

    max_val = max(max(males), max(females)) * 1.15 or 1
    step = _nice_tick(max_val)
    tick_range = round(max_val // step) * step
    tick_vals = list(range(-tick_range, tick_range + step, step))

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Male", y=labels, x=[-v for v in males], orientation="h",
        marker_color=NAVY, marker_line_width=0,
        customdata=males, hovertemplate="<b>%{y}</b><br>Male: %{customdata:,}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Female", y=labels, x=females, orientation="h",
        marker_color=CRIMSON, marker_line_width=0,
        hovertemplate="<b>%{y}</b><br>Female: %{x:,}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=f"Age Pyramid  ·  {subtitle}", font_size=15, font_color=SLATE),
        barmode="overlay", bargap=0.12,
        xaxis=dict(tickvals=tick_vals, ticktext=[f"{abs(v):,}" for v in tick_vals],
                   title="Population", zeroline=True, zerolinewidth=2, zerolinecolor="#bbb", gridcolor="#efefef"),
        yaxis=dict(title="", gridcolor="#efefef"),
        legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center", font_size=13),
        plot_bgcolor="white", paper_bgcolor="white", height=560,
        margin=dict(l=70, r=30, t=70, b=50),
    )
    return fig


def fig_hbar(labels, vals, pcts, title, colors, height=380, margin_l=200) -> go.Figure:
    fig = go.Figure(go.Bar(
        y=labels, x=vals, orientation="h",
        marker_color=colors, marker_line_width=0,
        text=[f"{p:.1f}%" for p in pcts], textposition="outside",
        hovertemplate="<b>%{y}</b><br>%{x:,}  (%{text})<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=title, font_size=15, font_color=SLATE),
        xaxis=dict(title="Population", gridcolor="#efefef"),
        yaxis=dict(autorange="reversed"),
        plot_bgcolor="white", paper_bgcolor="white",
        height=height, margin=dict(l=margin_l, r=90, t=60, b=50),
    )
    return fig


def fig_race(row, subtitle) -> go.Figure:
    total = safe(row, "B02001_001E", 1) or 1
    data = sorted([(lbl, safe(row, var)) for var, lbl in RACE_VARS.items()], key=lambda x: x[1], reverse=True)
    labels, vals = zip(*data)
    pcts = [v / total * 100 for v in vals]
    colors = [RACE_PAL[i % len(RACE_PAL)] for i in range(len(labels))]
    return fig_hbar(list(labels), list(vals), pcts, f"Race  ·  {subtitle}", colors, 380, 215)


def fig_hispanic(row, subtitle) -> go.Figure:
    total = safe(row, "B03001_001E", 1) or 1
    data = sorted([(lbl, safe(row, var)) for var, lbl in HISPANIC_VARS.items()], key=lambda x: x[1], reverse=True)
    labels, vals = zip(*data)
    pcts = [v / total * 100 for v in vals]
    colors = [HISP_PAL[i % len(HISP_PAL)] for i in range(len(labels))]
    return fig_hbar(list(labels), list(vals), pcts, f"Hispanic/Latino Ethnicity  ·  {subtitle}", colors, 380, 185)


def fig_income_dist(row, subtitle) -> go.Figure:
    total = safe(row, "B19001_001E", 1) or 1
    vals = [safe(row, code) for code, _ in INCOME_BANDS]
    labels = [lbl for _, lbl in INCOME_BANDS]
    pcts = [v / total * 100 for v in vals]
    colors = [NAVY if lbl.startswith("$") and int(lbl.replace("$", "").split("k")[0].replace("<", "").replace("+", "").replace("–", " ").split()[0]) < 50 else TEAL for lbl in labels]
    colors = [CRIMSON if "< $10" in lbl else (AMBER if "$10" in lbl or "$15" in lbl or "$20" in lbl or "$25" in lbl or "$30" in lbl else TEAL) for lbl in labels]
    fig = go.Figure(go.Bar(
        x=labels, y=vals, marker_color=NAVY, marker_line_width=0,
        text=[f"{p:.1f}%" for p in pcts], textposition="outside",
        hovertemplate="<b>%{x}</b><br>%{y:,} households (%{text})<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=f"Household Income Distribution  ·  {subtitle}", font_size=15, font_color=SLATE),
        xaxis=dict(title="Income Band", gridcolor="#efefef"),
        yaxis=dict(title="Households", gridcolor="#efefef"),
        plot_bgcolor="white", paper_bgcolor="white",
        height=420, margin=dict(l=60, r=30, t=70, b=80),
    )
    return fig


def fig_poverty_depth(row, subtitle) -> go.Figure:
    total = safe(row, "B17002_001E", 1) or 1
    vals = [safe(row, code) for code, _ in POVERTY_DEPTH_BANDS]
    labels = [lbl for _, lbl in POVERTY_DEPTH_BANDS]
    pcts = [v / total * 100 for v in vals]
    palette = [CRIMSON, AMBER, GOLD, TEAL, TEAL, SAGE, GREEN, GREEN]
    fig = go.Figure(go.Bar(
        x=labels, y=vals,
        marker_color=[palette[i % len(palette)] for i in range(len(labels))],
        marker_line_width=0,
        text=[f"{p:.1f}%" for p in pcts], textposition="outside",
        hovertemplate="<b>%{x}</b><br>%{y:,} people (%{text})<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=f"Poverty Depth (Income-to-Poverty Ratio)  ·  {subtitle}", font_size=15, font_color=SLATE),
        xaxis=dict(title="Income/Poverty Ratio", gridcolor="#efefef"),
        yaxis=dict(title="People", gridcolor="#efefef"),
        plot_bgcolor="white", paper_bgcolor="white",
        height=400, margin=dict(l=60, r=30, t=70, b=100),
    )
    return fig


def fig_attainment(row, subtitle) -> go.Figure:
    total = safe(row, "B15003_001E", 1) or 1
    vals = [safe(row, code) for code, _ in ATTAINMENT_BANDS]
    labels = [lbl for _, lbl in ATTAINMENT_BANDS]
    pcts = [v / total * 100 for v in vals]
    colors = [NAVY if i >= 6 else (AMBER if i >= 2 else CRIMSON) for i in range(len(labels))]
    fig = go.Figure(go.Bar(
        x=labels, y=vals,
        marker_color=colors, marker_line_width=0,
        text=[f"{p:.1f}%" for p in pcts], textposition="outside",
        hovertemplate="<b>%{x}</b><br>%{y:,} people (%{text})<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=f"Educational Attainment (Population 25+)  ·  {subtitle}", font_size=15, font_color=SLATE),
        xaxis=dict(title="Attainment Level", gridcolor="#efefef"),
        yaxis=dict(title="People", gridcolor="#efefef"),
        plot_bgcolor="white", paper_bgcolor="white",
        height=420, margin=dict(l=60, r=30, t=70, b=100),
    )
    return fig


def fig_rent_burden(row, subtitle) -> go.Figure:
    total = safe(row, "B25070_001E", 1) or 1
    vals = [safe(row, code) for code, _ in RENT_BURDEN_BANDS]
    labels = [lbl for _, lbl in RENT_BURDEN_BANDS]
    pcts = [v / total * 100 for v in vals]
    colors = [GREEN, SAGE, TEAL, GOLD, AMBER, CRIMSON, CRIMSON, CRIMSON, CRIMSON]
    fig = go.Figure(go.Bar(
        x=labels, y=vals,
        marker_color=[colors[i % len(colors)] for i in range(len(labels))],
        marker_line_width=0,
        text=[f"{p:.1f}%" for p in pcts], textposition="outside",
        hovertemplate="<b>%{x}</b><br>%{y:,} renters (%{text})<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=f"Rent Burden (Gross Rent as % of Income)  ·  {subtitle}", font_size=15, font_color=SLATE),
        xaxis=dict(title="Rent Burden Band", gridcolor="#efefef"),
        yaxis=dict(title="Renter Households", gridcolor="#efefef"),
        plot_bgcolor="white", paper_bgcolor="white",
        height=400, margin=dict(l=60, r=30, t=70, b=60),
    )
    return fig


def fig_commute_mode(row, subtitle) -> go.Figure:
    total = safe(row, "B08301_001E", 1) or 1
    data = [(lbl, safe(row, code)) for code, lbl in COMMUTE_MODES]
    data.sort(key=lambda x: x[1], reverse=True)
    labels, vals = zip(*data) if data else ([], [])
    pcts = [v / total * 100 for v in vals]
    colors = [MULTI_PAL[i % len(MULTI_PAL)] for i in range(len(labels))]
    return fig_hbar(list(labels), list(vals), pcts, f"Commute Mode  ·  {subtitle}", colors, 340, 200)


def fig_travel_time(row, subtitle) -> go.Figure:
    total = safe(row, "B08303_001E", 1) or 1
    vals = [safe(row, code) for code, _ in TRAVEL_TIME_BANDS]
    labels = [lbl for _, lbl in TRAVEL_TIME_BANDS]
    pcts = [v / total * 100 for v in vals]
    fig = go.Figure(go.Bar(
        x=labels, y=vals, marker_color=NAVY, marker_line_width=0,
        text=[f"{p:.1f}%" for p in pcts], textposition="outside",
        hovertemplate="<b>%{x}</b><br>%{y:,} workers (%{text})<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=f"Travel Time to Work  ·  {subtitle}", font_size=15, font_color=SLATE),
        xaxis=dict(title="Travel Time", gridcolor="#efefef"),
        yaxis=dict(title="Workers", gridcolor="#efefef"),
        plot_bgcolor="white", paper_bgcolor="white",
        height=380, margin=dict(l=60, r=30, t=70, b=60),
    )
    return fig


def fig_occupation(row, subtitle) -> go.Figure:
    total = safe(row, "C24010_001E", 1) or 1
    vals = [safe(row, code) for code, _ in OCCUPATION_GROUPS]
    labels = [lbl for _, lbl in OCCUPATION_GROUPS]
    pcts = [v / total * 100 for v in vals]
    colors = [MULTI_PAL[i % len(MULTI_PAL)] for i in range(len(labels))]
    return fig_hbar(list(labels), list(vals), pcts, f"Occupation (Civilian Employed 16+)  ·  {subtitle}", colors, 340, 260)


def fig_internet(row, subtitle) -> go.Figure:
    total = safe(row, "B28002_001E", 1) or 1
    labels = ["Has internet subscription", "Access w/o subscription", "No internet access"]
    vals = [safe(row, "B28002_002E"), safe(row, "B28002_012E"), safe(row, "B28002_013E")]
    pcts = [v / total * 100 for v in vals]
    colors = [NAVY, GOLD, CRIMSON]
    return fig_hbar(labels, vals, pcts, f"Internet Access  ·  {subtitle}", colors, 280, 240)


def fig_health_insurance(row, subtitle) -> go.Figure:
    total = safe(row, "B27001_001E", 1) or 1
    # Sum no-insurance rows for males and females by age group
    age_labels = ["Under 6", "6–17", "18–24", "25–34", "35–44", "45–54", "55–64", "65–74", "75+"]
    male_no_ins = ["B27001_004E","B27001_006E","B27001_008E","B27001_010E",
                   "B27001_012E","B27001_014E","B27001_016E","B27001_018E","B27001_020E"]
    female_no_ins = ["B27001_023E","B27001_025E","B27001_027E","B27001_029E",
                     "B27001_031E","B27001_033E","B27001_035E","B27001_037E","B27001_039E"]

    male_vals   = [safe(row, c) for c in male_no_ins]
    female_vals = [safe(row, c) for c in female_no_ins]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Male uninsured",   x=age_labels, y=male_vals,   marker_color=NAVY,   marker_line_width=0))
    fig.add_trace(go.Bar(name="Female uninsured", x=age_labels, y=female_vals, marker_color=CRIMSON, marker_line_width=0))
    fig.update_layout(
        title=dict(text=f"Uninsured Population by Age  ·  {subtitle}", font_size=15, font_color=SLATE),
        barmode="group",
        xaxis=dict(title="Age Group", gridcolor="#efefef"),
        yaxis=dict(title="People without health insurance", gridcolor="#efefef"),
        legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center"),
        plot_bgcolor="white", paper_bgcolor="white",
        height=400, margin=dict(l=60, r=30, t=70, b=60),
    )
    return fig


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
        label="geo", options=["City Total", "Census Tract"],
        label_visibility="collapsed",
    )

    tract_choice = None
    ALL_TRACTS_LABEL = "All tracts (aggregate)"
    if geo_level == "Census Tract":
        demo_place, demo_tract = load_topic("demographics")
        if demo_tract is not None:
            st.markdown("**Select Tract**")
            tract_labels = demo_tract["_label"].tolist()
            tract_choice = st.selectbox(
                label="tract",
                options=[ALL_TRACTS_LABEL] + tract_labels,
                label_visibility="collapsed",
            )

    st.divider()
    st.caption("Source: US Census Bureau")
    st.caption("Essex County, MA · FIPS 009")
    st.caption("Gateway Cities Initiative")

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='margin-bottom:0;color:#1B3A6B'>"
    "Lawrence, MA · Census Dashboard</h1>"
    "<p style='color:#4A5568;margin-top:4px;font-size:0.95rem'>"
    "American Community Survey 5-Year Estimates · 2022 · Essex County</p>",
    unsafe_allow_html=True,
)

# ── Key metrics (demographics) ────────────────────────────────────────────────
demo_place, demo_tract = load_topic("demographics")

is_aggregate = False
if demo_place is not None:
    if geo_level == "City Total":
        row = demo_place.iloc[0]
        subtitle = "Lawrence city"
        med_age_display = safe(row, "B01002_001E", None)
        inc_display     = safe(row, "B19013_001E", None)
    elif demo_tract is not None and tract_choice == ALL_TRACTS_LABEL:
        row = demo_tract.select_dtypes("number").sum()
        subtitle = "All 18 Lawrence tracts (aggregate)"
        is_aggregate = True
        med_age_display = _weighted_mean(demo_tract, "B01002_001E", "B01001_001E")
        inc_display     = _weighted_mean(demo_tract, "B19013_001E", "B01001_001E")
    elif demo_tract is not None and tract_choice:
        row = demo_tract.loc[demo_tract["_label"] == tract_choice].iloc[0]
        subtitle = f"Lawrence — {tract_choice}"
        med_age_display = safe(row, "B01002_001E", None)
        inc_display     = safe(row, "B19013_001E", None)
    else:
        row = demo_place.iloc[0]
        subtitle = "Lawrence city"
        med_age_display = safe(row, "B01002_001E", None)
        inc_display     = safe(row, "B19013_001E", None)

    c1, c2, c3, c4, c5 = st.columns(5)
    pop    = int(safe(row, "B01001_001E"))
    hisp_n = safe(row, "B03001_003E", None)
    hisp_t = safe(row, "B03001_001E", None)
    pov_n  = safe(row, "B17001_002E", None)
    pov_t  = safe(row, "B17001_001E", None)
    c1.metric("Total Population", f"{pop:,}")
    c2.metric("Median Age",
              f"{med_age_display:.1f}" if med_age_display is not None else "—",
              help="Population-weighted mean of tract medians (aggregate view)." if is_aggregate else None)
    c3.metric("Hispanic/Latino", _pct(hisp_n, hisp_t))
    c4.metric("Median HH Income",
              f"${int(inc_display):,}" if inc_display and inc_display > 0 else "—",
              help="Population-weighted mean of tract medians (aggregate view)." if is_aggregate else None)
    c5.metric("Below Poverty", _pct(pov_n, pov_t))
    st.divider()

# ── Topic tabs ────────────────────────────────────────────────────────────────
tab_demo, tab_inc, tab_edu, tab_hous, tab_eco, tab_hlth, tab_com, tab_net = st.tabs([
    "Demographics", "Income & Poverty", "Education", "Housing",
    "Economic", "Health", "Commuting", "Internet Access",
])

# ── Demographics tab ──────────────────────────────────────────────────────────
with tab_demo:
    if demo_place is None:
        _not_downloaded("demographics")
    else:
        st.plotly_chart(fig_age_pyramid(row, subtitle), use_container_width=True)
        st.divider()
        col_race, col_hisp = st.columns(2)
        with col_race:
            st.plotly_chart(fig_race(row, subtitle), use_container_width=True)
        with col_hisp:
            if _is_null(row.get("B03001_001E")):
                st.info("Hispanic/Latino detail (B03001) is suppressed at this geography level. "
                        "Switch to City Total or a specific Census Tract.", icon="ℹ️")
            else:
                st.plotly_chart(fig_hispanic(row, subtitle), use_container_width=True)
        st.divider()
        with st.expander("View underlying demographics data"):
            if geo_level == "City Total":
                st.dataframe(demo_place, use_container_width=True, hide_index=True)
            elif demo_tract is not None:
                st.dataframe(demo_tract.drop(columns=["_label"], errors="ignore"),
                             use_container_width=True, hide_index=True)

# ── Income & Poverty tab ──────────────────────────────────────────────────────
with tab_inc:
    inc_place, inc_tract = load_topic("income_poverty")
    if inc_place is None:
        _not_downloaded("income_poverty")
    else:
        if geo_level == "City Total":
            irow = inc_place.iloc[0]
            isubtitle = "Lawrence city"
        elif inc_tract is not None and tract_choice == ALL_TRACTS_LABEL:
            irow = inc_tract.select_dtypes("number").sum()
            isubtitle = "All 18 Lawrence tracts (aggregate)"
        elif inc_tract is not None and tract_choice:
            matches = inc_tract.loc[inc_tract["_label"] == tract_choice]
            irow = matches.iloc[0] if not matches.empty else inc_place.iloc[0]
            isubtitle = f"Lawrence — {tract_choice}"
        else:
            irow = inc_place.iloc[0]
            isubtitle = "Lawrence city"

        m1, m2, m3, m4 = st.columns(4)
        med_inc   = safe(irow, "B19013_001E", None)
        pov_pct   = _pct(safe(irow, "B17001_002E", None), safe(irow, "B17001_001E", None))
        snap_pct  = _pct(safe(irow, "B22001_002E", None), safe(irow, "B22001_001E", None))
        deep_pov  = _pct(safe(irow, "B17002_002E", None), safe(irow, "B17002_001E", None))

        m1.metric("Median HH Income", f"${int(med_inc):,}" if med_inc and med_inc > 0 else "—")
        m2.metric("Below Poverty", pov_pct)
        m3.metric("SNAP/Food Stamps", snap_pct)
        m4.metric("Deep Poverty (< 50%)", deep_pov)

        st.plotly_chart(fig_income_dist(irow, isubtitle), use_container_width=True)
        st.plotly_chart(fig_poverty_depth(irow, isubtitle), use_container_width=True)

        st.subheader("Median Household Income by Race/Ethnicity")
        race_inc = {
            "White alone":              safe(irow, "B19013A_001E", None),
            "Black/African American":   safe(irow, "B19013B_001E", None),
            "Asian":                    safe(irow, "B19013D_001E", None),
            "Hispanic/Latino":          safe(irow, "B19013I_001E", None),
        }
        ri_labels = [k for k, v in race_inc.items() if v and v > 0]
        ri_vals   = [v for v in race_inc.values() if v and v > 0]
        if ri_labels:
            fig_ri = go.Figure(go.Bar(
                x=ri_labels, y=ri_vals,
                marker_color=[NAVY, CRIMSON, GOLD, TEAL][:len(ri_labels)],
                text=[f"${int(v):,}" for v in ri_vals], textposition="outside",
                hovertemplate="<b>%{x}</b><br>Median HH Income: $%{y:,}<extra></extra>",
            ))
            fig_ri.update_layout(
                title=dict(text=f"Median HH Income by Race  ·  {isubtitle}", font_size=15, font_color=SLATE),
                yaxis=dict(title="Median Income ($)", gridcolor="#efefef"),
                plot_bgcolor="white", paper_bgcolor="white",
                height=360, margin=dict(l=60, r=30, t=70, b=60),
            )
            st.plotly_chart(fig_ri, use_container_width=True)

# ── Education tab ─────────────────────────────────────────────────────────────
with tab_edu:
    edu_place, edu_tract = load_topic("education")
    if edu_place is None:
        _not_downloaded("education")
    else:
        if geo_level == "City Total":
            erow = edu_place.iloc[0]; esubtitle = "Lawrence city"
        elif edu_tract is not None and tract_choice == ALL_TRACTS_LABEL:
            erow = edu_tract.select_dtypes("number").sum(); esubtitle = "All tracts (aggregate)"
        elif edu_tract is not None and tract_choice:
            matches = edu_tract.loc[edu_tract["_label"] == tract_choice]
            erow = matches.iloc[0] if not matches.empty else edu_place.iloc[0]
            esubtitle = f"Lawrence — {tract_choice}"
        else:
            erow = edu_place.iloc[0]; esubtitle = "Lawrence city"

        total_25 = safe(erow, "B15003_001E", 1) or 1
        enrolled  = safe(erow, "B14001_002E", None)
        total_3   = safe(erow, "B14001_001E", None)
        hs_plus = sum(safe(erow, c) for c in
                      ["B15003_017E","B15003_018E","B15003_019E","B15003_020E",
                       "B15003_021E","B15003_022E","B15003_023E","B15003_024E","B15003_025E"])
        ba_plus = sum(safe(erow, c) for c in ["B15003_022E","B15003_023E","B15003_024E","B15003_025E"])

        e1, e2, e3 = st.columns(3)
        e1.metric("HS Diploma or Higher", _pct(hs_plus, total_25))
        e2.metric("Bachelor's or Higher", _pct(ba_plus, total_25))
        e3.metric("Currently Enrolled", _pct(enrolled, total_3))

        st.plotly_chart(fig_attainment(erow, esubtitle), use_container_width=True)

        st.subheader("School Enrollment (Population 3+)")
        enroll_labels = ["Pre-K / Nursery", "Kindergarten", "Grades 1–4", "Grades 5–8",
                         "Grades 9–12", "College UG", "Graduate/Prof", "Not enrolled"]
        enroll_codes  = ["B14001_003E","B14001_004E","B14001_005E","B14001_006E",
                         "B14001_007E","B14001_008E","B14001_009E","B14001_010E"]
        enroll_vals = [safe(erow, c) for c in enroll_codes]
        enroll_total = safe(erow, "B14001_001E", 1) or 1
        enroll_pcts  = [v / enroll_total * 100 for v in enroll_vals]
        fig_enroll = go.Figure(go.Bar(
            x=enroll_labels, y=enroll_vals,
            marker_color=[NAVY if i < 7 else SLATE for i in range(len(enroll_labels))],
            text=[f"{p:.1f}%" for p in enroll_pcts], textposition="outside",
            hovertemplate="<b>%{x}</b><br>%{y:,} people (%{text})<extra></extra>",
        ))
        fig_enroll.update_layout(
            title=dict(text=f"School Enrollment  ·  {esubtitle}", font_size=15, font_color=SLATE),
            yaxis=dict(title="People", gridcolor="#efefef"),
            plot_bgcolor="white", paper_bgcolor="white",
            height=400, margin=dict(l=60, r=30, t=70, b=80),
        )
        st.plotly_chart(fig_enroll, use_container_width=True)

# ── Housing tab ───────────────────────────────────────────────────────────────
with tab_hous:
    hous_place, hous_tract = load_topic("housing")
    if hous_place is None:
        _not_downloaded("housing")
    else:
        if geo_level == "City Total":
            hrow = hous_place.iloc[0]; hsubtitle = "Lawrence city"
        elif hous_tract is not None and tract_choice == ALL_TRACTS_LABEL:
            hrow = hous_tract.select_dtypes("number").sum(); hsubtitle = "All tracts (aggregate)"
        elif hous_tract is not None and tract_choice:
            matches = hous_tract.loc[hous_tract["_label"] == tract_choice]
            hrow = matches.iloc[0] if not matches.empty else hous_place.iloc[0]
            hsubtitle = f"Lawrence — {tract_choice}"
        else:
            hrow = hous_place.iloc[0]; hsubtitle = "Lawrence city"

        h1, h2, h3, h4 = st.columns(4)
        med_rent  = safe(hrow, "B25064_001E", None)
        med_val   = safe(hrow, "B25077_001E", None)
        own_pct   = _pct(safe(hrow, "B25003_002E"), safe(hrow, "B25003_001E"))
        rent_burd = _pct(sum(safe(hrow, c) for c in
                             ["B25070_007E","B25070_008E","B25070_009E","B25070_010E"]),
                         safe(hrow, "B25070_001E"))

        h1.metric("Median Gross Rent", f"${int(med_rent):,}" if med_rent and med_rent > 0 else "—")
        h2.metric("Median Home Value",  f"${int(med_val):,}"  if med_val  and med_val  > 0 else "—")
        h3.metric("Owner-Occupied", own_pct)
        h4.metric("Rent Burdened 30%+", rent_burd)

        col_tenure, col_burden = st.columns(2)
        with col_tenure:
            own_n  = safe(hrow, "B25003_002E")
            rent_n = safe(hrow, "B25003_003E")
            fig_ten = go.Figure(go.Pie(
                labels=["Owner occupied", "Renter occupied"],
                values=[own_n, rent_n],
                marker_colors=[NAVY, CRIMSON],
                hole=0.4,
                hovertemplate="<b>%{label}</b><br>%{value:,} (%{percent})<extra></extra>",
            ))
            fig_ten.update_layout(
                title=dict(text=f"Housing Tenure  ·  {hsubtitle}", font_size=15, font_color=SLATE),
                height=360, margin=dict(l=20, r=20, t=60, b=20),
            )
            st.plotly_chart(fig_ten, use_container_width=True)
        with col_burden:
            st.plotly_chart(fig_rent_burden(hrow, hsubtitle), use_container_width=True)

# ── Economic tab ──────────────────────────────────────────────────────────────
with tab_eco:
    eco_place, eco_tract = load_topic("economic")
    if eco_place is None:
        _not_downloaded("economic")
    else:
        if geo_level == "City Total":
            xrow = eco_place.iloc[0]; xsubtitle = "Lawrence city"
        elif eco_tract is not None and tract_choice == ALL_TRACTS_LABEL:
            xrow = eco_tract.select_dtypes("number").sum(); xsubtitle = "All tracts (aggregate)"
        elif eco_tract is not None and tract_choice:
            matches = eco_tract.loc[eco_tract["_label"] == tract_choice]
            xrow = matches.iloc[0] if not matches.empty else eco_place.iloc[0]
            xsubtitle = f"Lawrence — {tract_choice}"
        else:
            xrow = eco_place.iloc[0]; xsubtitle = "Lawrence city"

        lf_total = safe(xrow, "B23025_001E", 1) or 1
        lf_in    = safe(xrow, "B23025_002E")
        employed = safe(xrow, "B23025_004E")
        unemployed = safe(xrow, "B23025_005E")
        unemp_rate = _pct(unemployed, safe(xrow, "B23025_003E"))

        x1, x2, x3, x4 = st.columns(4)
        x1.metric("Labor Force Participation", _pct(lf_in, lf_total))
        x2.metric("Unemployment Rate", unemp_rate)
        med_earn_m = safe(xrow, "B20002_002E", None)
        med_earn_f = safe(xrow, "B20002_003E", None)
        x3.metric("Median Earnings — Male",   f"${int(med_earn_m):,}" if med_earn_m and med_earn_m > 0 else "—")
        x4.metric("Median Earnings — Female", f"${int(med_earn_f):,}" if med_earn_f and med_earn_f > 0 else "—")

        col_emp, col_occ = st.columns(2)
        with col_emp:
            emp_labels = ["Employed (civilian)", "Unemployed", "Armed Forces", "Not in labor force"]
            emp_vals   = [safe(xrow, "B23025_004E"), safe(xrow, "B23025_005E"),
                          safe(xrow, "B23025_006E"), safe(xrow, "B23025_007E")]
            emp_total  = safe(xrow, "B23025_001E", 1) or 1
            emp_pcts   = [v / emp_total * 100 for v in emp_vals]
            fig_emp = go.Figure(go.Bar(
                x=emp_labels, y=emp_vals,
                marker_color=[GREEN, CRIMSON, AMBER, SLATE],
                text=[f"{p:.1f}%" for p in emp_pcts], textposition="outside",
                hovertemplate="<b>%{x}</b><br>%{y:,} people (%{text})<extra></extra>",
            ))
            fig_emp.update_layout(
                title=dict(text=f"Employment Status  ·  {xsubtitle}", font_size=15, font_color=SLATE),
                yaxis=dict(title="People", gridcolor="#efefef"),
                plot_bgcolor="white", paper_bgcolor="white",
                height=380, margin=dict(l=60, r=30, t=70, b=80),
            )
            st.plotly_chart(fig_emp, use_container_width=True)
        with col_occ:
            st.plotly_chart(fig_occupation(xrow, xsubtitle), use_container_width=True)

# ── Health tab ────────────────────────────────────────────────────────────────
with tab_hlth:
    hlth_place, hlth_tract = load_topic("health")
    if hlth_place is None:
        _not_downloaded("health")
    else:
        if geo_level == "City Total":
            hlrow = hlth_place.iloc[0]; hlsubtitle = "Lawrence city"
        elif hlth_tract is not None and tract_choice == ALL_TRACTS_LABEL:
            hlrow = hlth_tract.select_dtypes("number").sum(); hlsubtitle = "All tracts (aggregate)"
        elif hlth_tract is not None and tract_choice:
            matches = hlth_tract.loc[hlth_tract["_label"] == tract_choice]
            hlrow = matches.iloc[0] if not matches.empty else hlth_place.iloc[0]
            hlsubtitle = f"Lawrence — {tract_choice}"
        else:
            hlrow = hlth_place.iloc[0]; hlsubtitle = "Lawrence city"

        total_pop = safe(hlrow, "B27001_001E", 1) or 1
        male_uninsumed   = sum(safe(hlrow, c) for c in
                               ["B27001_004E","B27001_006E","B27001_008E","B27001_010E",
                                "B27001_012E","B27001_014E","B27001_016E","B27001_018E","B27001_020E"])
        female_uninsured = sum(safe(hlrow, c) for c in
                               ["B27001_023E","B27001_025E","B27001_027E","B27001_029E",
                                "B27001_031E","B27001_033E","B27001_035E","B27001_037E","B27001_039E"])
        total_uninsured  = male_uninsumed + female_uninsured

        vet_n = safe(hlrow, "B21001_002E", None)
        vet_t = safe(hlrow, "B21001_001E", None)
        disab_m = sum(safe(hlrow, c) for c in
                      ["B18101_004E","B18101_007E","B18101_010E","B18101_013E","B18101_016E"])
        disab_f = sum(safe(hlrow, c) for c in
                      ["B18101_021E","B18101_024E","B18101_027E","B18101_030E","B18101_033E"])

        hl1, hl2, hl3 = st.columns(3)
        hl1.metric("Uninsured (total)", _pct(total_uninsured, total_pop))
        hl2.metric("Veteran Population", _pct(vet_n, vet_t))
        hl3.metric("With a Disability (est.)",
                   _pct(disab_m + disab_f, safe(hlrow, "B18101_001E", None)))

        st.plotly_chart(fig_health_insurance(hlrow, hlsubtitle), use_container_width=True)

# ── Commuting tab ─────────────────────────────────────────────────────────────
with tab_com:
    com_place, com_tract = load_topic("commuting")
    if com_place is None:
        _not_downloaded("commuting")
    else:
        if geo_level == "City Total":
            crow = com_place.iloc[0]; csubtitle = "Lawrence city"
        elif com_tract is not None and tract_choice == ALL_TRACTS_LABEL:
            crow = com_tract.select_dtypes("number").sum(); csubtitle = "All tracts (aggregate)"
        elif com_tract is not None and tract_choice:
            matches = com_tract.loc[com_tract["_label"] == tract_choice]
            crow = matches.iloc[0] if not matches.empty else com_place.iloc[0]
            csubtitle = f"Lawrence — {tract_choice}"
        else:
            crow = com_place.iloc[0]; csubtitle = "Lawrence city"

        wfh_pct    = _pct(safe(crow, "B08301_021E"), safe(crow, "B08301_001E"))
        transit_pct = _pct(safe(crow, "B08301_010E"), safe(crow, "B08301_001E"))
        mean_tt    = safe(crow, "B08013_001E", None)
        no_vehicle = _pct(safe(crow, "B08201_002E"), safe(crow, "B08201_001E"))

        cm1, cm2, cm3, cm4 = st.columns(4)
        cm1.metric("Work from Home", wfh_pct)
        cm2.metric("Public Transit", transit_pct)
        cm3.metric("Mean Travel Time", f"{mean_tt:.1f} min" if mean_tt and mean_tt > 0 else "—")
        cm4.metric("No Vehicle", no_vehicle)

        col_mode, col_time = st.columns(2)
        with col_mode:
            st.plotly_chart(fig_commute_mode(crow, csubtitle), use_container_width=True)
        with col_time:
            st.plotly_chart(fig_travel_time(crow, csubtitle), use_container_width=True)

# ── Internet Access tab ───────────────────────────────────────────────────────
with tab_net:
    net_place, net_tract = load_topic("internet_access")
    if net_place is None:
        _not_downloaded("internet_access")
    else:
        if geo_level == "City Total":
            nrow = net_place.iloc[0]; nsubtitle = "Lawrence city"
        elif net_tract is not None and tract_choice == ALL_TRACTS_LABEL:
            nrow = net_tract.select_dtypes("number").sum(); nsubtitle = "All tracts (aggregate)"
        elif net_tract is not None and tract_choice:
            matches = net_tract.loc[net_tract["_label"] == tract_choice]
            nrow = matches.iloc[0] if not matches.empty else net_place.iloc[0]
            nsubtitle = f"Lawrence — {tract_choice}"
        else:
            nrow = net_place.iloc[0]; nsubtitle = "Lawrence city"

        n1, n2, n3 = st.columns(3)
        n1.metric("Has Internet", _pct(safe(nrow, "B28002_002E"), safe(nrow, "B28002_001E")))
        n2.metric("Has Computer",  _pct(safe(nrow, "B28001_002E"), safe(nrow, "B28001_001E")))
        n3.metric("No Internet",   _pct(safe(nrow, "B28002_013E"), safe(nrow, "B28002_001E")))

        col_int, col_comp = st.columns(2)
        with col_int:
            st.plotly_chart(fig_internet(nrow, nsubtitle), use_container_width=True)
        with col_comp:
            comp_labels = ["Desktop/Laptop", "Smartphone", "Tablet", "No computer"]
            comp_codes  = ["B28001_003E", "B28001_005E", "B28001_007E", "B28001_011E"]
            comp_total  = safe(nrow, "B28001_001E", 1) or 1
            comp_vals   = [safe(nrow, c) for c in comp_codes]
            comp_pcts   = [v / comp_total * 100 for v in comp_vals]
            fig_comp = go.Figure(go.Bar(
                x=comp_labels, y=comp_vals,
                marker_color=[NAVY, TEAL, GOLD, CRIMSON],
                text=[f"{p:.1f}%" for p in comp_pcts], textposition="outside",
                hovertemplate="<b>%{x}</b><br>%{y:,} households (%{text})<extra></extra>",
            ))
            fig_comp.update_layout(
                title=dict(text=f"Computer Type  ·  {nsubtitle}", font_size=15, font_color=SLATE),
                yaxis=dict(title="Households", gridcolor="#efefef"),
                plot_bgcolor="white", paper_bgcolor="white",
                height=340, margin=dict(l=60, r=30, t=70, b=60),
            )
            st.plotly_chart(fig_comp, use_container_width=True)

        if net_place is not None:
            st.subheader("Internet Access by Income Level")
            inc_labels = ["Income < $20k", "Income $20k–$75k", "Income $75k+"]
            inc_no_int = [safe(nrow, "B28004_006E"), safe(nrow, "B28004_011E"), safe(nrow, "B28004_016E")]
            inc_totals = [safe(nrow, "B28004_002E"), safe(nrow, "B28004_007E"), safe(nrow, "B28004_012E")]
            inc_pcts   = [_pct(n, t) for n, t in zip(inc_no_int, inc_totals)]
            st.caption("Share of households with **no internet access** by income band:")
            for lbl, pct in zip(inc_labels, inc_pcts):
                st.metric(lbl, pct)
