"""
Bird Species Observation Analysis — Streamlit Dashboard
"""
import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DB_PATH = Path(__file__).parent / "data" / "bird_observations.db"

st.set_page_config(
    page_title="Bird Species Observation Analysis",
    page_icon="🐦",
    layout="wide",
)

EARTH_COLORS = [
    "#6B8E4E", "#A0522D", "#C9A66B", "#4A5D23",
    "#B08968", "#8FA998", "#D9C36A", "#5C4033",
]
px.defaults.color_discrete_sequence = EARTH_COLORS
px.defaults.color_continuous_scale = "YlOrBr"

st.markdown(
    """
    <style>
    .stMetric {
        background-color: #E9DFC6;
        border: 1px solid #C9A66B;
        border-radius: 10px;
        padding: 12px 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #E9DFC6;
        border-radius: 8px 8px 0 0;
        padding: 8px 16px;
        color: #3E2C23;
    }
    .stTabs [aria-selected="true"] {
        background-color: #6B8E4E !important;
        color: #F7F3E9 !important;
    }
    section[data-testid="stSidebar"] {
        background-color: #EFE8D6;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM observations", conn, parse_dates=["Date"])
    conn.close()
    for col in ["Flyover_Observed", "PIF_Watchlist_Status", "Regional_Stewardship_Status"]:
        if col in df.columns:
            df[col] = df[col].astype("boolean")
    return df


if not DB_PATH.exists():
    st.title("🐦 Bird Species Observation Analysis")
    st.error(
        "No database found yet.\n\n"
        "Run the cleaning pipeline first:\n\n"
        "```\npython scripts/01_clean_data.py --input data/YOUR_FILE.xlsx\n```"
    )
    st.stop()

df = load_data()

st.sidebar.title("🐦 Filters")

admin_units = sorted(df["Admin_Unit_Code"].dropna().unique())
sel_units = st.sidebar.multiselect("Admin Unit", admin_units, default=admin_units)

loc_types = sorted(df["Location_Type"].dropna().unique())
sel_loc = st.sidebar.multiselect("Habitat Type", loc_types, default=loc_types)

years = sorted(df["Year"].dropna().unique())
sel_years = st.sidebar.multiselect("Year", years, default=years)

species_options = sorted(df["Common_Name"].dropna().unique())
sel_species = st.sidebar.multiselect("Species (optional)", species_options, default=[])

watchlist_only = st.sidebar.checkbox("Watchlist species only", value=False)

f = df[
    df["Admin_Unit_Code"].isin(sel_units)
    & df["Location_Type"].isin(sel_loc)
    & df["Year"].isin(sel_years)
]
if sel_species:
    f = f[f["Common_Name"].isin(sel_species)]
if watchlist_only:
    f = f[f["PIF_Watchlist_Status"] == True]  # noqa: E712

st.sidebar.markdown(f"**{len(f):,}** observations match your filters")

st.title("🐦 Bird Species Observation Analysis")
st.caption("Forest vs. grassland habitats across National Park Service units")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Observations", f"{len(f):,}")
c2.metric("Species", f["Scientific_Name"].nunique())
c3.metric("Sites", f["Plot_Name"].nunique())
c4.metric("Watchlist Species", f.loc[f["PIF_Watchlist_Status"] == True, "Scientific_Name"].nunique())  # noqa: E712

tabs = st.tabs([
    "Temporal", "Spatial", "Species", "Environmental",
    "Distance & Behavior", "Observers", "Conservation",
])

with tabs[0]:
    st.subheader("Seasonal & Yearly Trends")
    colA, colB = st.columns(2)
    with colA:
        by_year = f.groupby("Year").size().reset_index(name="Observations")
        fig = px.bar(by_year, x="Year", y="Observations", title="Observations by Year")
        st.plotly_chart(fig, use_container_width=True)
    with colB:
        by_season = f.groupby("Season").size().reindex(
            ["Winter", "Spring", "Summer", "Fall"]).reset_index(name="Observations")
        fig = px.bar(by_season, x="Season", y="Observations", title="Observations by Season")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Year × Month Heatmap")
    heat = f.groupby(["Year", "Month"]).size().reset_index(name="Observations")
    fig = px.density_heatmap(
        heat, x="Month", y="Year", z="Observations", histfunc="sum",
        color_continuous_scale=["#F7F3E9", "#C9A66B", "#6B8E4E", "#3E2C23"],
        title="Observation Density by Year & Month",
    )
    st.plotly_chart(fig, use_container_width=True)

with tabs[1]:
    st.subheader("Habitat & Site Comparison")
    colA, colB = st.columns(2)
    with colA:
        by_habitat = f.groupby("Location_Type").size().reset_index(name="Observations")
        fig = px.pie(by_habitat, names="Location_Type", values="Observations",
                     title="Observations by Habitat Type", hole=0.4)
        st.plotly_chart(fig, use_container_width=True)
    with colB:
        by_unit = f.groupby("Admin_Unit_Code").size().reset_index(name="Observations")
        fig = px.bar(by_unit.sort_values("Observations"), x="Observations", y="Admin_Unit_Code",
                     orientation="h", title="Observations by Admin Unit")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Plot-Level Species Richness")
    plot_rich = f.groupby(["Plot_Name", "Location_Type"])["Scientific_Name"].nunique().reset_index(
        name="Species_Count").sort_values("Species_Count", ascending=False).head(20)
    fig = px.bar(plot_rich, x="Plot_Name", y="Species_Count", color="Location_Type",
                 title="Top 20 Plots by Species Richness")
    st.plotly_chart(fig, use_container_width=True)

with tabs[2]:
    st.subheader("Species Diversity & Activity")
    colA = f.groupby("Common_Name").size().reset_index(name="Count").sort_values(
        "Count", ascending=False).head(15)
    fig = px.bar(colA, x="Count", y="Common_Name", orientation="h",
                 title="Top 15 Most-Observed Species")
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        method = f.groupby("ID_Method").size().reset_index(name="Count")
        fig = px.pie(method, names="ID_Method", values="Count", title="Identification Method")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        sex = f.groupby("Sex").size().reset_index(name="Count")
        fig = px.pie(sex, names="Sex", values="Count", title="Sex Ratio")
        st.plotly_chart(fig, use_container_width=True)

    div_by_habitat = f.groupby("Location_Type")["Scientific_Name"].nunique().reset_index(
        name="Unique_Species")
    fig = px.bar(div_by_habitat, x="Location_Type", y="Unique_Species",
                 title="Species Diversity by Habitat")
    st.plotly_chart(fig, use_container_width=True)

with tabs[3]:
    st.subheader("Weather & Disturbance Effects")
    col1, col2 = st.columns(2)
    with col1:
        fig = px.scatter(f, x="Temperature", y="Initial_Three_Min_Cnt", color="Location_Type",
                          trendline="ols" if len(f) > 1 else None,
                          title="Temperature vs. Bird Count (first 3 min)",
                          opacity=0.5)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.scatter(f, x="Humidity", y="Initial_Three_Min_Cnt", color="Location_Type",
                          title="Humidity vs. Bird Count", opacity=0.5)
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        sky = f.groupby("Sky").size().reset_index(name="Count")
        fig = px.bar(sky, x="Sky", y="Count", title="Observations by Sky Condition")
        st.plotly_chart(fig, use_container_width=True)
    with col4:
        dist = f.groupby("Disturbance").size().reset_index(name="Count")
        fig = px.bar(dist, x="Disturbance", y="Count", title="Observations by Disturbance Level")
        st.plotly_chart(fig, use_container_width=True)

with tabs[4]:
    st.subheader("Distance & Flight Behavior")
    col1, col2 = st.columns(2)
    with col1:
        dist_counts = f.groupby("Distance").size().reset_index(name="Count")
        fig = px.bar(dist_counts, x="Distance", y="Count", title="Observation Distance Bands")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        flyover = f.groupby("Flyover_Observed").size().reset_index(name="Count")
        flyover["Flyover_Observed"] = flyover["Flyover_Observed"].map({True: "Flyover", False: "Perched/Ground"})
        fig = px.pie(flyover, names="Flyover_Observed", values="Count", title="Flyover vs. Non-Flyover")
        st.plotly_chart(fig, use_container_width=True)

with tabs[5]:
    st.subheader("Observer Trends")
    col1, col2 = st.columns(2)
    with col1:
        by_observer = f.groupby("Observer").size().reset_index(name="Observations").sort_values(
            "Observations", ascending=False)
        fig = px.bar(by_observer, x="Observer", y="Observations", title="Observations per Observer")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        by_visit = f.groupby("Visit")["Scientific_Name"].nunique().reset_index(name="Unique_Species")
        fig = px.line(by_visit, x="Visit", y="Unique_Species", markers=True,
                       title="Species Diversity by Visit Number")
        st.plotly_chart(fig, use_container_width=True)

with tabs[6]:
    st.subheader("Conservation Priorities")
    col1, col2 = st.columns(2)
    with col1:
        watch = f[f["PIF_Watchlist_Status"] == True]  # noqa: E712
        watch_counts = watch.groupby("Common_Name").size().reset_index(name="Count").sort_values(
            "Count", ascending=False).head(10)
        fig = px.bar(watch_counts, x="Count", y="Common_Name", orientation="h",
                     title="Top Watchlist Species (PIF)")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        steward = f.groupby(["Location_Type", "Regional_Stewardship_Status"]).size().reset_index(
            name="Count")
        steward["Regional_Stewardship_Status"] = steward["Regional_Stewardship_Status"].map(
            {True: "Stewardship Priority", False: "Not Flagged"})
        fig = px.bar(steward, x="Location_Type", y="Count", color="Regional_Stewardship_Status",
                     barmode="group", title="Regional Stewardship Status by Habitat")
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        watch[["Common_Name", "Scientific_Name", "Admin_Unit_Code", "Location_Type", "Date"]]
        .sort_values("Date", ascending=False),
        use_container_width=True,
        height=300,
    )

st.divider()
with st.expander("View filtered raw data"):
    st.dataframe(f, use_container_width=True)
