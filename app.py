# ChargeSense EV Infrastructure Intelligence Platform
# © 2026 Benjamin Joseph. All rights reserved.
# This code is for portfolio and  demonstration purposes only.
import random  
import math  
import requests  
import numpy as np 
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st 

st.set_page_config(page_title="EVAtlas", layout="wide")
from chargesense_crazy_ui import inject_crazy_ui, render_crazy_home_hero

inject_crazy_ui()

@st.cache_data
def load_data():
    nsw_df = pd.read_csv("ev_chargers_nsw_enriched.csv")
    ocm_df = pd.read_csv("openchargemap_au_enriched.csv")
    ev_market_df = pd.read_csv("australia_ev_market_data.csv")
    return nsw_df, ocm_df, ev_market_df

nsw_df, ocm_df, ev_market_df = load_data()

# -----------------------------
# DATA PREP
# -----------------------------

city_coordinates = {
    "Sydney": [151.2093, -33.8688],
    "Melbourne": [144.9631, -37.8136],
    "Brisbane": [153.0251, -27.4698],
    "Adelaide": [138.6007, -34.9285],
    "Perth": [115.8605, -31.9505],
    "Canberra": [149.1300, -35.2809],
    "Hobart": [147.3272, -42.8821],
    "Darwin": [130.8456, -12.4634]
}


def infer_state_from_coordinates(lat, lon):
    if pd.isna(lat) or pd.isna(lon):
        return "Other / Needs Review"

    # Rough Australian state and territory bounding boxes.
    # Prototype cleanup only, not official boundary matching.

    state_bounds = {
        "Australian Capital Territory": {
            "lat_min": -35.95,
            "lat_max": -35.10,
            "lon_min": 148.75,
            "lon_max": 149.45
        },
        "New South Wales": {
            "lat_min": -37.60,
            "lat_max": -28.00,
            "lon_min": 141.00,
            "lon_max": 154.20
        },
        "Victoria": {
            "lat_min": -39.30,
            "lat_max": -33.90,
            "lon_min": 140.90,
            "lon_max": 150.10
        },
        "Queensland": {
            "lat_min": -29.20,
            "lat_max": -9.00,
            "lon_min": 137.80,
            "lon_max": 153.80
        },
        "South Australia": {
            "lat_min": -38.20,
            "lat_max": -25.90,
            "lon_min": 129.00,
            "lon_max": 141.10
        },
        "Western Australia": {
            "lat_min": -35.20,
            "lat_max": -13.00,
            "lon_min": 112.00,
            "lon_max": 129.10
        },
        "Tasmania": {
            "lat_min": -44.00,
            "lat_max": -39.00,
            "lon_min": 143.50,
            "lon_max": 148.60
        },
        "Northern Territory": {
            "lat_min": -26.10,
            "lat_max": -10.50,
            "lon_min": 129.00,
            "lon_max": 138.10
        }
    }

    # ACT must be checked before NSW because ACT sits inside the NSW bounding area.
    ordered_states = [
        "Australian Capital Territory",
        "New South Wales",
        "Victoria",
        "Queensland",
        "South Australia",
        "Western Australia",
        "Tasmania",
        "Northern Territory"
    ]

    for state in ordered_states:
        bounds = state_bounds[state]

        if (
            lat >= bounds["lat_min"]
            and lat <= bounds["lat_max"]
            and lon >= bounds["lon_min"]
            and lon <= bounds["lon_max"]
        ):
            return state

    return "Other / Needs Review"


# -----------------------------
# Numeric cleanup
# -----------------------------

ocm_df["max_power_kw"] = pd.to_numeric(
    ocm_df["max_power_kw"],
    errors="coerce"
)

ocm_df["latitude"] = pd.to_numeric(
    ocm_df["latitude"],
    errors="coerce"
)

ocm_df["longitude"] = pd.to_numeric(
    ocm_df["longitude"],
    errors="coerce"
)

ocm_df["date_last_verified"] = pd.to_datetime(
    ocm_df["date_last_verified"],
    errors="coerce"
)


# -----------------------------
# Keep only Australian charger records
# -----------------------------
# This removes accidental overseas records such as UK/Europe points.

ocm_df["is_in_australia"] = (
    ocm_df["latitude"].between(-44.5, -9.0)
    & ocm_df["longitude"].between(112.0, 154.5)
)

ocm_df = ocm_df[
    ocm_df["is_in_australia"]
].copy()


# -----------------------------
# Clean / infer state labels
# -----------------------------

ocm_df["state_clean"] = (
    ocm_df["state_clean"]
    .fillna("Other / Needs Review")
    .astype(str)
    .str.strip()
)

state_name_map = {
    "NSW": "New South Wales",
    "VIC": "Victoria",
    "QLD": "Queensland",
    "WA": "Western Australia",
    "SA": "South Australia",
    "TAS": "Tasmania",
    "ACT": "Australian Capital Territory",
    "NT": "Northern Territory"
}

ocm_df["state_clean"] = (
    ocm_df["state_clean"]
    .replace(state_name_map)
)

valid_states = [
    "New South Wales",
    "Victoria",
    "Queensland",
    "Western Australia",
    "South Australia",
    "Tasmania",
    "Australian Capital Territory",
    "Northern Territory"
]

ocm_df["state_from_coordinates"] = ocm_df.apply(
    lambda row: infer_state_from_coordinates(
        row["latitude"],
        row["longitude"]
    ),
    axis=1
)

# Coordinate-based state is treated as the source of truth where available.
# This fixes records where metadata says NSW but the point is physically in Victoria, etc.
ocm_df["state_clean"] = ocm_df.apply(
    lambda row: row["state_from_coordinates"]
    if row["state_from_coordinates"] in valid_states
    else row["state_clean"],
    axis=1
)

# Remove anything still not assigned to a valid Australian state/territory
ocm_df = ocm_df[
    ocm_df["state_clean"].isin(valid_states)
].copy()


# -----------------------------
# Reliability scoring
# -----------------------------

latest_date = ocm_df["date_last_verified"].max()

ocm_df["days_since_verified"] = (
    latest_date - ocm_df["date_last_verified"]
).dt.days

ocm_df["is_recently_verified"] = (
    ocm_df["is_recently_verified"]
    .astype(str)
    .str.lower()
    .map(
        {
            "true": 1,
            "false": 0,
            "1": 1,
            "0": 0
        }
    )
    .fillna(0)
)

ocm_df["data_quality_level"] = pd.to_numeric(
    ocm_df["data_quality_level"],
    errors="coerce"
).fillna(0)

ocm_df["reliability_score"] = (
    (ocm_df["is_recently_verified"] * 40)
    +
    (ocm_df["data_quality_level"] * 15)
    +
    (
        100
        - (
            ocm_df["days_since_verified"]
            .fillna(365)
            .clip(upper=365)
            / 365
        ) * 100
    ) * 0.45
)

ocm_df["reliability_score"] = (
    ocm_df["reliability_score"]
    .clip(lower=0, upper=100)
    .round(2)
)


def haversine_distance(lat1, lon1, lat2, lon2):
    import math

    radius_km = 6371

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.asin(math.sqrt(a))

    return radius_km * c


def reliability_label(score):
    if score >= 70:
        return "High"
    elif score >= 40:
        return "Medium"
    elif score > 0:
        return "Low"
    return "Unknown / Stale"


ocm_df["reliability_label"] = (
    ocm_df["reliability_score"]
    .apply(reliability_label)
)


# -----------------------------
# State-level population and infrastructure metrics
# -----------------------------

state_population = {
    "New South Wales": 8500000,
    "Victoria": 6900000,
    "Queensland": 5600000,
    "Western Australia": 3000000,
    "South Australia": 1900000,
    "Tasmania": 575000,
    "Australian Capital Territory": 470000,
    "Northern Territory": 260000,
}

ocm_df["population"] = ocm_df["state_clean"].map(state_population)

state_metrics = (
    ocm_df.groupby("state_clean")
    .agg(
        total_stations=("station_name", "count"),
        avg_power_kw=("max_power_kw", "mean"),
        avg_reliability=("reliability_score", "mean"),
        ultra_fast_sites=("speed_category", lambda x: (x == "Ultra-fast DC").sum()),
        population=("population", "first"),
    )
    .reset_index()
)

state_metrics = state_metrics[
    state_metrics["state_clean"].isin(state_population.keys())
].copy()

state_metrics["chargers_per_million"] = (
    state_metrics["total_stations"]
    / state_metrics["population"]
) * 1_000_000

state_metrics["chargers_per_million"] = (
    state_metrics["chargers_per_million"]
    .replace([float("inf"), -float("inf")], 0)
    .fillna(0)
)

state_metrics["ultra_fast_ratio"] = (
    state_metrics["ultra_fast_sites"]
    / state_metrics["total_stations"]
)

state_metrics["ultra_fast_ratio"] = (
    state_metrics["ultra_fast_ratio"]
    .replace([float("inf"), -float("inf")], 0)
    .fillna(0)
)

state_metrics["infrastructure_gap_score"] = (
    (100 - state_metrics["chargers_per_million"].clip(upper=100)) * 0.4
    + (100 - state_metrics["avg_reliability"].fillna(0)) * 0.3
    + (1 - state_metrics["ultra_fast_ratio"].fillna(0)) * 100 * 0.3
)

state_metrics["infrastructure_gap_score"] = (
    state_metrics["infrastructure_gap_score"]
    .clip(lower=0, upper=100)
    .round(2)
)


# -----------------------------
# EV market and investment priority metrics
# -----------------------------

state_metrics = state_metrics.merge(
    ev_market_df,
    on="state_clean",
    how="left"
)

state_metrics["chargers_per_1000_evs"] = (
    state_metrics["total_stations"]
    / state_metrics["estimated_ev_count"]
) * 1000

state_metrics["chargers_per_1000_evs"] = (
    state_metrics["chargers_per_1000_evs"]
    .replace([float("inf"), -float("inf")], 0)
    .fillna(0)
    .round(2)
)

state_metrics["investment_priority_score"] = (
    (100 - state_metrics["chargers_per_1000_evs"].clip(upper=100)) * 0.35
    + state_metrics["annual_ev_growth_rate"].fillna(0).clip(upper=100) * 0.25
    + (100 - state_metrics["avg_reliability"].fillna(0)) * 0.25
    + (1 - state_metrics["ultra_fast_ratio"].fillna(0)) * 100 * 0.15
)

state_metrics["investment_priority_score"] = (
    state_metrics["investment_priority_score"]
    .clip(lower=0, upper=100)
    .round(2)
)

high_threshold = state_metrics["investment_priority_score"].quantile(0.67)
medium_threshold = state_metrics["investment_priority_score"].quantile(0.33)


def investment_priority_label(score):
    if score >= high_threshold:
        return "High Priority"
    elif score >= medium_threshold:
        return "Medium Priority"
    return "Lower Priority"


state_metrics["investment_priority_label"] = (
    state_metrics["investment_priority_score"]
    .apply(investment_priority_label)
)



# -----------------------------
# SIDEBAR
# -----------------------------

st.sidebar.title("⚡ EVAtlas")


app_mode = st.sidebar.radio(
    "Choose Mode",
    [
        "EV Trip Planner",
        "Infrastructure Intelligence"
    ]
)

if app_mode == "EV Trip Planner":
    page = st.sidebar.radio(
        "Navigate",
        [
            "Home",
            "Real Route Optimizer",
            "Route Comparison Mode",
            "Charger Recommendation",
            "Charging Cost Simulator",
            "Reservation Simulation",
            "Data Reality & Production Needs",
            "Station Feedback"
        ]
    )

else:
    page = st.sidebar.radio(
        "Navigate",
        [
            "Home",
            "Infrastructure Overview",
            "Interactive Map",
            "Infrastructure Gap Analysis",
            "Demand  Forecast Model",
            "Fleet & Council Intelligence",
            "Fleet Route Upload",
            "Operator Performance",
            "Reliability Intelligence",
            "Reliability Risk Model",
            "Queue Simulation Engine",
            "Data Reality & Production Needs",
            "Model Assumptions",
            "Project Insights"
        ]
    )



# -----------------------------
# HOME
# -----------------------------

if page == "Home":

    render_crazy_home_hero()

    st.subheader("EV Infrastructure Intelligence & Route Planning Platform")

    st.markdown("""
    EVAtlas is a prototype platform for EV route planning and  EV infrastructure intelligence in Australia.

    It combines public charger data, EV registration-based signals, routing APIs, demand  forecasting,
    reliability scoring, corridor risk analysis, operator benchmarking and fleet/council planning analytics.
    """)

    st.markdown("### Two Product Modes")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        #### 🚗 EV Trip Planner

        Helps EV drivers plan trips by estimating:
        - charging stops
        - charging time
        - charging cost
        - route risk
        - charger reliability
        - rest-stop quality
        - weather-adjusted range
        """)

    with col2:
        st.markdown("""
        #### 🏛️ Infrastructure Intelligence

        Helps fleets, councils, planners and operators analyse:
        - infrastructure gaps
        - future charging demand 
        - investment priority
        - operator performance
        - fleet route risk
        - additional station needs
        """)

    st.success("Platform loaded successfully")

    st.markdown("---")

    st.markdown("""
    ### Key Features

    - Real EV route optimization using OSRM
    - Custom suburb/place routing using geocoding
    - Battery-aware charging stop sequencing
    - Weather-adjusted EV range
    - Charging cost estimation
    - Corridor risk scoring
    - Demand  forecasting
    - Investment priority ranking
    - Operator performance benchmarking
    - Fleet route CSV upload
    - Fleet & council planning reports
    """)

    st.markdown("---")

    st.caption(
        "Built using Python, Streamlit, OpenChargeMap data, OSRM routing, Nominatim geocoding and EV registration-derived inputs."
    )

    st.link_button(
        "View GitHub Repository",
        "YOUR_GITHUB_REPO_LINK_HERE"
    )

    st.caption("© 2026 Benjamin Joseph. All rights reserved.")

# -----------------------------
# INFRASTRUCTURE OVERVIEW
# -----------------------------

elif page == "Infrastructure Overview":
    st.title("📊 Infrastructure Overview")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Stations", len(ocm_df))
    col2.metric("Ultra-fast Chargers", len(ocm_df[ocm_df["max_power_kw"] >= 150]))
    col3.metric("Average Charger Power", round(ocm_df["max_power_kw"].mean(), 1))
    col4.metric("States Covered", ocm_df["state_clean"].nunique())

    st.divider()

    state_summary = (
        ocm_df.groupby("state_clean")
        .size()
        .reset_index(name="stations")
        .sort_values("stations", ascending=False)
    )

    st.subheader("EV Charging Stations by State")
    st.bar_chart(state_summary.set_index("state_clean"))

# -----------------------------
# INFRASTRUCTURE GAP ANALYSIS
# -----------------------------

elif page == "Infrastructure Gap Analysis":

    st.title("🏙️ Infrastructure Gap Analysis")

    st.markdown("""
    Identify states that may require stronger EV charging investment based on
    charger density, EV adoption, ultra-fast charger availability and  reliability.
    """)

    st.caption(
        "Investment priority combines chargers per 1,000 EVs, EV growth rate, charger reliability and  ultra-fast charger coverage."
    )

    gap_view = (
        state_metrics[
            [
                "state_clean",
                "population",
                "estimated_ev_count",
                "annual_ev_growth_rate",
                "total_stations",
                "chargers_per_million",
                "chargers_per_1000_evs",
                "ultra_fast_sites",
                "ultra_fast_ratio",
                "avg_reliability",
                "infrastructure_gap_score",
                "investment_priority_score",
                "investment_priority_label"
            ]
        ]
        .dropna(subset=["population"])
        .copy()
    )

    gap_view = gap_view.sort_values(
        "investment_priority_score",
        ascending=False
    )

    highest_gap = gap_view.sort_values(
        "infrastructure_gap_score",
        ascending=False
    ).iloc[0]

    highest_investment_priority = gap_view.sort_values(
        "investment_priority_score",
        ascending=False
    ).iloc[0]

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Highest Gap State",
        highest_gap["state_clean"]
    )

    col2.metric(
        "Gap Score",
        round(highest_gap["infrastructure_gap_score"], 1)
    )

    col3.metric(
        "Chargers / 1,000 EVs",
        round(highest_gap["chargers_per_1000_evs"], 2)
    )

    col4.metric(
        "Top Investment Priority",
        highest_investment_priority["state_clean"]
    )

    st.subheader("Infrastructure Gap and  Investment Ranking")

    st.dataframe(
        gap_view,
        use_container_width=True
    )

    st.subheader("Infrastructure Gap Score by State")

    gap_score_view = gap_view.sort_values(
        "infrastructure_gap_score",
        ascending=False
    )

    st.bar_chart(
        gap_score_view.set_index("state_clean")["infrastructure_gap_score"]
    )

    st.subheader("Investment Priority Score by State")

    investment_view = gap_view.sort_values(
        "investment_priority_score",
        ascending=False
    )

    st.bar_chart(
        investment_view.set_index("state_clean")["investment_priority_score"]
    )

    st.subheader("Chargers per Million People")

    chargers_population_view = gap_view.sort_values(
        "chargers_per_million",
        ascending=False
    )

    st.bar_chart(
        chargers_population_view.set_index("state_clean")["chargers_per_million"]
    )

    st.subheader("Chargers per 1,000 EVs")

    chargers_ev_view = gap_view.sort_values(
        "chargers_per_1000_evs",
        ascending=False
    )

    st.bar_chart(
        chargers_ev_view.set_index("state_clean")["chargers_per_1000_evs"]
    )

    st.markdown("""
    ### How to interpret this

    **Infrastructure Gap Score** shows where charging infrastructure may be weak relative to population,
    charger reliability and  ultra-fast charger availability.

    **Chargers per 1,000 EVs** compares charging supply against actual EV registrations, making it more demand -aware
    than population-only metrics.

    **Investment Priority Score** highlights where infrastructure investment may be most urgent by combining:
    - low chargers per EV
    - high EV growth
    - weaker reliability
    - low ultra-fast charger coverage
    """)
# -----------------------------
# INTERACTIVE MAP
# -----------------------------

elif page == "Interactive Map":

    st.title("🗺️ Interactive Charger Map")

    st.markdown(
        "Explore EV charging stations across Australia using OpenChargeMap data."
    )

    # -----------------------------
    # Prepare map data
    # -----------------------------

    map_df = ocm_df.copy()

    map_df["latitude"] = pd.to_numeric(
        map_df["latitude"],
        errors="coerce"
    )

    map_df["longitude"] = pd.to_numeric(
        map_df["longitude"],
        errors="coerce"
    )

    map_df["max_power_kw"] = pd.to_numeric(
        map_df["max_power_kw"],
        errors="coerce"
    ).fillna(0)

    map_df["station_name"] = map_df["station_name"].fillna("Unknown Station")
    map_df["town"] = map_df["town"].fillna("")
    map_df["state_clean"] = map_df["state_clean"].fillna("Unknown")

    map_df = map_df.dropna(
        subset=[
            "latitude",
            "longitude"
        ]
    )

    # Keep only official Australian states/territories
    valid_states = [
        "New South Wales",
        "Victoria",
        "Queensland",
        "Western Australia",
        "South Australia",
        "Tasmania",
        "Australian Capital Territory",
        "Northern Territory"
    ]

    map_df = map_df[
        map_df["state_clean"].isin(valid_states)
    ].copy()

    # -----------------------------
    # State-specific map view settings
    # -----------------------------

    state_map_view = {
        "New South Wales": {
            "lat": -32.8,
            "lon": 147.0,
            "zoom": 5.0
        },
        "Victoria": {
            "lat": -37.0,
            "lon": 144.5,
            "zoom": 5.5
        },
        "Queensland": {
            "lat": -22.5,
            "lon": 144.5,
            "zoom": 4.3
        },
        "Western Australia": {
            "lat": -25.5,
            "lon": 122.0,
            "zoom": 4.0
        },
        "South Australia": {
            "lat": -30.0,
            "lon": 135.0,
            "zoom": 4.6
        },
        "Tasmania": {
            "lat": -42.0,
            "lon": 147.0,
            "zoom": 6.2
        },
        "Australian Capital Territory": {
            "lat": -35.3,
            "lon": 149.1,
            "zoom": 8.2
        },
        "Northern Territory": {
            "lat": -19.5,
            "lon": 133.5,
            "zoom": 4.8
        }
    }

    # -----------------------------
    # Filters
    # -----------------------------

    col1, col2 = st.columns(2)

    with col1:
        selected_state = st.selectbox(
            "Select State",
            sorted(map_df["state_clean"].dropna().unique())
        )

    with col2:
        min_power_kw = st.slider(
            "Minimum Charger Power (kW)",
            0,
            350,
            0,
            10
        )

    filtered_map_df = map_df[
        (map_df["state_clean"] == selected_state)
        & (map_df["max_power_kw"] >= min_power_kw)
    ].copy()

    st.markdown(
        f"Showing **{len(filtered_map_df)}** charging stations"
    )

    if len(filtered_map_df) == 0:
        st.warning(
            "No charging stations match the selected filters."
        )
        st.stop()

    # -----------------------------
    # Build map
    # -----------------------------

    selected_view = state_map_view.get(
        selected_state,
        {
            "lat": -25.2744,
            "lon": 133.7751,
            "zoom": 3.2
        }
    )

    fig = px.scatter_mapbox(
        filtered_map_df,
        lat="latitude",
        lon="longitude",
        hover_name="station_name",
        hover_data=[
            "town",
            "state_clean",
            "max_power_kw",
            "speed_category",
            "reliability_score",
            "reliability_label"
        ],
        color="speed_category",
        size="max_power_kw",
        size_max=18,
        zoom=selected_view["zoom"],
        height=650
    )

    fig.update_layout(
        mapbox_style="open-street-map",
        mapbox=dict(
            center=dict(
                lat=selected_view["lat"],
                lon=selected_view["lon"]
            ),
            zoom=selected_view["zoom"]
        ),
        margin=dict(
            l=0,
            r=0,
            t=0,
            b=0
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # -----------------------------
    # Optional table
    # -----------------------------

    st.subheader("Charging Stations in Selected State")

    st.dataframe(
        filtered_map_df[
            [
                "station_name",
                "town",
                "state_clean",
                "max_power_kw",
                "speed_category",
                "reliability_score",
                "reliability_label"
            ]
        ].sort_values(
            "max_power_kw",
            ascending=False
        ),
        use_container_width=True
    )
# -----------------------------
# RELIABILITY INTELLIGENCE
# -----------------------------

elif page == "Reliability Intelligence":
    st.title("🛡️ Reliability Intelligence")

    st.markdown("""
    Reliability score is based on recent verification, data quality level,
    and  days since the charging station was last verified.
    """)

    reliability_view = (
        ocm_df[
            [
                "station_name",
                "state_clean",
                "max_power_kw",
                "reliability_score",
                "reliability_label",
                "days_since_verified",
            ]
        ]
        .sort_values("reliability_score", ascending=False)
    )

    st.subheader("Top Reliable Charging Stations")
    st.dataframe(reliability_view.head(20), use_container_width=True)

    st.subheader("Reliability Label Distribution")
    reliability_dist = ocm_df["reliability_label"].value_counts().reset_index()
    reliability_dist.columns = ["Reliability Label", "Count"]
    st.bar_chart(reliability_dist.set_index("Reliability Label"))

# -----------------------------
# CHARGER RECOMMENDATION
# -----------------------------

elif page == "Charger Recommendation":
    st.title("🎯 Charger Recommendation Engine")

    st.markdown("""
    Find recommended charging stations based on charger power and  reliability score.
    """)

    col1, col2, col3 = st.columns(3)

    with col1:
        rec_state = st.selectbox(
            "Select State",
            sorted(ocm_df["state_clean"].dropna().unique()),
            key="rec_state",
        )

    with col2:
        min_rec_power = st.slider(
            "Minimum Power (kW)",
            0,
            int(ocm_df["max_power_kw"].fillna(0).max()),
            50,
        )

    with col3:
        min_reliability = st.slider("Minimum Reliability Score", 0, 100, 40)

    rec_df = ocm_df[
        (ocm_df["state_clean"] == rec_state)
        & (ocm_df["max_power_kw"].fillna(0) >= min_rec_power)
        & (ocm_df["reliability_score"].fillna(0) >= min_reliability)
    ].copy()

    rec_df["recommendation_score"] = (
        rec_df["max_power_kw"].fillna(0) * 0.6
        + rec_df["reliability_score"].fillna(0) * 0.4
    )

    rec_df = rec_df.sort_values("recommendation_score", ascending=False)

    st.metric("Recommended Stations Found", len(rec_df))

    st.subheader("Recommended Charging Stations")

    if len(rec_df) == 0:
        st.warning("No stations match the selected recommendation filters.")
    else:
        st.dataframe(
            rec_df[
                [
                    "station_name",
                    "state_clean",
                    "max_power_kw",
                    "reliability_score",
                    "reliability_label",
                    "recommendation_score",
                ]
            ].head(15),
            use_container_width=True,
        )

# -----------------------------
# RELIABILITY RISK MODEL
# -----------------------------

elif page == "Reliability Risk Model":
    st.title("🧠 Reliability Risk Model")

    st.markdown("""
    This model estimates charger reliability risk using verification freshness,
    data quality, charger power and  connector availability.

    This is a rule-based risk model, not a production-grade ML failure prediction model.
    """)

    risk_df = ocm_df.copy()

    risk_df["num_connections"] = pd.to_numeric(
        risk_df["num_connections"], errors="coerce"
    ).fillna(0)

    risk_df["reliability_risk_score"] = (
        (risk_df["days_since_verified"].fillna(365) * 0.25)
        + ((100 - risk_df["reliability_score"].fillna(0)) * 0.4)
        + ((50 - risk_df["max_power_kw"].fillna(0).clip(upper=50)) * 0.2)
        + ((2 - risk_df["num_connections"].clip(upper=2)) * 10)
    )

    risk_df["reliability_risk_score"] = (
        risk_df["reliability_risk_score"].clip(lower=0, upper=100).round(2)
    )

    def risk_label(score):
        if score >= 70:
            return "High Risk"
        elif score >= 40:
            return "Medium Risk"
        return "Low Risk"

    risk_df["risk_label"] = risk_df["reliability_risk_score"].apply(risk_label)

    col1, col2, col3 = st.columns(3)

    col1.metric("Stations Scored", len(risk_df))
    col2.metric("High Risk Stations", len(risk_df[risk_df["risk_label"] == "High Risk"]))
    col3.metric("Average Risk Score", round(risk_df["reliability_risk_score"].mean(), 2))

    st.subheader("Highest Reliability Risk Stations")

    st.dataframe(
        risk_df[
            [
                "station_name",
                "state_clean",
                "max_power_kw",
                "reliability_score",
                "days_since_verified",
                "num_connections",
                "reliability_risk_score",
                "risk_label",
            ]
        ]
        .sort_values("reliability_risk_score", ascending=False)
        .head(25),
        use_container_width=True,
    )

    st.subheader("Reliability Risk Distribution")
    risk_dist = risk_df["risk_label"].value_counts().reset_index()
    risk_dist.columns = ["Risk Label", "Count"]
    st.bar_chart(risk_dist.set_index("Risk Label"))

# -----------------------------
# QUEUE SIMULATION ENGINE
# -----------------------------

elif page == "Queue Simulation Engine":
    st.title("⏳ Queue Simulation Engine")

    st.markdown("""
    Simulate estimated waiting time at EV charging stations based on charger capacity,
    arrival demand  and  average charging duration.
    """)

    queue_df = ocm_df.copy()

    queue_df["total_connector_quantity"] = pd.to_numeric(
        queue_df["total_connector_quantity"], errors="coerce"
    ).fillna(1)

    selected_queue_state = st.selectbox(
        "Select State",
        sorted(queue_df["state_clean"].dropna().unique()),
        key="queue_state",
    )

    arrivals_per_hour = st.slider("Estimated EV Arrivals per Hour", 1, 100, 20)
    avg_charge_minutes = st.slider("Average Charging Session Duration", 10, 90, 30)

    queue_state_df = queue_df[queue_df["state_clean"] == selected_queue_state].copy()

    queue_state_df["hourly_capacity"] = queue_state_df["total_connector_quantity"] * (
        60 / avg_charge_minutes
    )

    queue_state_df["queue_pressure_ratio"] = arrivals_per_hour / queue_state_df[
        "hourly_capacity"
    ].replace(0, 1)

    queue_state_df["estimated_wait_minutes"] = (
        (queue_state_df["queue_pressure_ratio"] - 1).clip(lower=0)
        * avg_charge_minutes
    ).round(1)

    def wait_label(wait):
        if wait >= 30:
            return "High Wait"
        elif wait >= 10:
            return "Moderate Wait"
        return "Low Wait"

    queue_state_df["wait_label"] = queue_state_df["estimated_wait_minutes"].apply(
        wait_label
    )

    col1, col2, col3 = st.columns(3)

    col1.metric("Stations Simulated", len(queue_state_df))
    col2.metric("Avg Estimated Wait", round(queue_state_df["estimated_wait_minutes"].mean(), 1))
    col3.metric("High Wait Stations", len(queue_state_df[queue_state_df["wait_label"] == "High Wait"]))

    st.subheader("Estimated Wait Times by Station")

    st.dataframe(
        queue_state_df[
            [
                "station_name",
                "town",
                "state_clean",
                "total_connector_quantity",
                "max_power_kw",
                "hourly_capacity",
                "estimated_wait_minutes",
                "wait_label",
            ]
        ]
        .sort_values("estimated_wait_minutes", ascending=False)
        .head(25),
        use_container_width=True,
    )

    st.subheader("Wait Time Distribution")
    wait_dist = queue_state_df["wait_label"].value_counts().reset_index()
    wait_dist.columns = ["Wait Category", "Count"]
    st.bar_chart(wait_dist.set_index("Wait Category"))

# -----------------------------
# RESERVATION SIMULATION
# -----------------------------

elif page == "Reservation Simulation":

    st.title("📅 Charging Slot Reservation Simulation")

    st.markdown("""
    Simulate checking EV charger slot availability and reserving a charging slot.

    Users can either check immediate availability using **Book Now**, or search for a future charging slot.
    """)

    st.warning(
        "Prototype only: this does not reserve a real charging station. "
        "A production version would require operator APIs, user accounts, payments, live connector availability, and payment/session control."
    )

    # -----------------------------
    # Helper functions
    # -----------------------------

    def generate_access_code():
        return str(random.randint(1000, 9999))

    def infer_demand_period_from_time(reservation_time, booking_mode):
        if booking_mode == "Book Now":
            return "Now / Immediate"

        hour = reservation_time.hour

        if 6 <= hour < 9:
            return "Morning Peak"
        elif 9 <= hour < 15:
            return "Daytime"
        elif 15 <= hour < 18:
            return "Afternoon Peak"
        elif 18 <= hour < 22:
            return "Evening"
        else:
            return "Off-peak"

    def simulate_slot_availability_score(station_reliability, selected_time_period, expected_duration):
        if pd.isna(station_reliability):
            station_reliability = 0

        base_availability = 70

        if station_reliability >= 70:
            base_availability += 15
        elif station_reliability >= 40:
            base_availability += 5
        else:
            base_availability -= 15

        if selected_time_period == "Now / Immediate":
            base_availability -= 5
        elif selected_time_period == "Morning Peak":
            base_availability -= 15
        elif selected_time_period == "Afternoon Peak":
            base_availability -= 20
        elif selected_time_period == "Evening":
            base_availability -= 10
        elif selected_time_period == "Holiday / Long Weekend":
            base_availability -= 30
        else:
            base_availability += 10

        if expected_duration > 60:
            base_availability -= 10
        elif expected_duration <= 30:
            base_availability += 5

        return max(min(base_availability, 100), 0)

    def slot_status_from_score(score):
        if score >= 55:
            return "Available"
        return "Booked"

    def build_simulated_slots(
        base_score,
        booking_mode,
        reservation_date,
        reservation_time,
        expected_duration_min
    ):
        simulated_slots = []

        if booking_mode == "Book Now":
            slot_offsets = [0, 15, 30, 45]
        else:
            slot_offsets = [-30, -15, 0, 15, 30, 45]

        for i, offset in enumerate(slot_offsets):
            slot_datetime = datetime.combine(
                reservation_date,
                reservation_time
            ) + timedelta(minutes=offset)

            slot_score = base_score

            # Simulate some slots being more/less likely to be available.
            if i % 3 == 0:
                slot_score -= 18
            elif i % 3 == 1:
                slot_score += 8
            else:
                slot_score -= 5

            slot_score = max(min(slot_score, 100), 0)
            slot_status = slot_status_from_score(slot_score)

            if slot_status == "Available":
                estimated_wait = 0 if slot_score >= 75 else 5
            else:
                estimated_wait = None

            simulated_slots.append(
                {
                    "slot_date": slot_datetime.date(),
                    "slot_time": slot_datetime.time().replace(second=0, microsecond=0),
                    "slot_status": slot_status,
                    "booking_confidence_score": round(slot_score, 1),
                    "expected_duration_min": expected_duration_min,
                    "estimated_wait_time_min": estimated_wait
                }
            )

        return pd.DataFrame(simulated_slots)

    # -----------------------------
    # Prepare station data
    # -----------------------------

    reservation_df = ocm_df.copy()

    reservation_df["station_name"] = reservation_df["station_name"].fillna("Unknown Station")
    reservation_df["town"] = reservation_df["town"].fillna("")
    reservation_df["state_clean"] = reservation_df["state_clean"].fillna("Unknown")

    reservation_df["max_power_kw"] = pd.to_numeric(
        reservation_df["max_power_kw"],
        errors="coerce"
    )

    reservation_df["reliability_score"] = pd.to_numeric(
        reservation_df["reliability_score"],
        errors="coerce"
    )

    reservation_df["station_display_name"] = (
        reservation_df["station_name"].astype(str)
        + " | "
        + reservation_df["town"].astype(str)
        + " | "
        + reservation_df["state_clean"].astype(str)
    )

    # -----------------------------
    # Station selection
    # -----------------------------

    st.subheader("1. Select Charging Station")

    available_states = sorted(
        reservation_df["state_clean"]
        .dropna()
        .unique()
    )

    valid_states = [
        "New South Wales",
        "Victoria",
        "Queensland",
        "Western Australia",
        "South Australia",
        "Tasmania",
        "Australian Capital Territory",
        "Northern Territory"
    ]

    available_states = [
        state for state in available_states
        if state in valid_states
    ]

    if len(available_states) == 0:
        st.error("No valid state or territory data available for charger selection.")
        st.stop()

    selected_state = st.selectbox(
        "Select state / territory",
        available_states
    )

    state_station_df = reservation_df[
        reservation_df["state_clean"] == selected_state
    ].copy()

    station_options = sorted(
        state_station_df["station_display_name"]
        .dropna()
        .unique()
    )

    station_search = st.text_input(
        "Search charging station within selected state",
        placeholder="Search by station name or town. Example: Tesla, Coolac, Barnawartha"
    )

    if station_search.strip() != "":
        filtered_station_options = [
            station
            for station in station_options
            if station_search.lower() in station.lower()
        ]
    else:
        filtered_station_options = station_options

    if len(filtered_station_options) == 0:
        st.warning(
            "No stations matched your search in this state. Try a different station name or town."
        )
        st.stop()

    selected_station_display = st.selectbox(
        "Select station",
        filtered_station_options
    )

    selected_station_name = selected_station_display.split(" | ")[0]

    selected_station_rows = reservation_df[
        reservation_df["station_display_name"] == selected_station_display
    ].copy()

    if len(selected_station_rows) == 0:
        st.error("Selected station could not be found.")
        st.stop()

    selected_station = selected_station_rows.iloc[0]

    # -----------------------------
    # Booking mode
    # -----------------------------

    st.subheader("2. Choose Booking Mode")

    booking_mode = st.radio(
        "Choose booking type",
        ["Book Now", "Schedule Future Slot"],
        horizontal=True
    )

    now = datetime.now()

    if booking_mode == "Book Now":

        reservation_date = now.date()
        reservation_time = now.time().replace(second=0, microsecond=0)
        expected_duration_min = 30

        selected_time_period = infer_demand_period_from_time(
            reservation_time,
            booking_mode
        )

        selected_ev = "Not specified"
        driver_name = ""
        vehicle_plate = ""

        st.info(
            f"Book Now selected. The app will check simulated availability from the current time: "
            f"{reservation_date} at {reservation_time}."
        )

        st.caption(
            "For Book Now, the app uses a default 30-minute charging session and automatically infers immediate demand conditions."
        )

    else:

        st.subheader("Future Reservation Details")

        col1, col2 = st.columns(2)

        with col1:
            reservation_date = st.date_input(
                "Reservation date"
            )

        with col2:
            reservation_time = st.time_input(
                "Preferred reservation time"
            )

        col3, col4 = st.columns(2)

        with col3:
            expected_duration_min = st.slider(
                "Expected charging duration (minutes)",
                15,
                120,
                45,
                5
            )

        selected_time_period = infer_demand_period_from_time(
            reservation_time,
            booking_mode
        )

        with col4:
            st.metric(
                "Demand Period",
                selected_time_period
            )

        st.caption(
            f"Demand period is automatically estimated as **{selected_time_period}** based on the selected reservation time."
        )

        ev_options = [
            "Tesla Model 3 RWD",
            "Tesla Model Y RWD",
            "BYD Atto 3",
            "BYD Seal",
            "Kia EV6",
            "Hyundai Ioniq 5",
            "MG4 Excite 51",
            "Other EV"
        ]

        selected_ev = st.selectbox(
            "Vehicle",
            ev_options
        )

        driver_name = st.text_input(
            "Driver name",
            placeholder="Example: Benjamin Joseph"
        )

        vehicle_plate = st.text_input(
            "Vehicle plate / reference",
            placeholder="Optional"
        )

    # -----------------------------
    # Station snapshot
    # -----------------------------

    st.subheader("3. Station Snapshot")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Station",
        selected_station_name[:22] + "..." if len(selected_station_name) > 22 else selected_station_name
    )

    col2.metric(
        "Max Power",
        f"{round(selected_station.get('max_power_kw', 0), 1)} kW"
        if pd.notna(selected_station.get("max_power_kw", None))
        else "Unknown"
    )

    col3.metric(
        "Reliability Score",
        round(selected_station.get("reliability_score", 0), 1)
        if pd.notna(selected_station.get("reliability_score", None))
        else "Unknown"
    )

    # -----------------------------
    # Check simulated availability
    # -----------------------------

    st.subheader("4. Check Simulated Availability")

    check_availability = st.button("Check Simulated Availability")

    if check_availability:

        station_reliability = selected_station.get("reliability_score", 0)

        base_score = simulate_slot_availability_score(
            station_reliability,
            selected_time_period,
            expected_duration_min
        )

        slot_df = build_simulated_slots(
            base_score,
            booking_mode,
            reservation_date,
            reservation_time,
            expected_duration_min
        )

        st.session_state["reservation_slot_df"] = slot_df
        st.session_state["reservation_context"] = {
            "booking_mode": booking_mode,
            "selected_station_display": selected_station_display,
            "selected_station_name": selected_station_name,
            "selected_state": selected_state,
            "selected_ev": selected_ev,
            "driver_name": driver_name,
            "vehicle_plate": vehicle_plate,
            "selected_time_period": selected_time_period
        }

    # -----------------------------
    # Show slot options and book
    # -----------------------------

    if "reservation_slot_df" in st.session_state:

        slot_df = st.session_state["reservation_slot_df"]

        st.subheader("5. Simulated Slot Options")

        st.caption(
            "These slots are simulated. In production, this would come from live connector-level availability from operators."
        )

        st.dataframe(
            slot_df[
                [
                    "slot_date",
                    "slot_time",
                    "slot_status",
                    "booking_confidence_score",
                    "expected_duration_min",
                    "estimated_wait_time_min"
                ]
            ],
            use_container_width=True
        )

        available_slot_labels = slot_df.apply(
            lambda row: (
                f"{row['slot_date']} {row['slot_time']} - {row['slot_status']}"
            ),
            axis=1
        ).tolist()

        selected_slot_label = st.selectbox(
            "Select a simulated slot to book",
            available_slot_labels
        )

        selected_slot_index = available_slot_labels.index(selected_slot_label)
        selected_slot = slot_df.iloc[selected_slot_index]

        if selected_slot["slot_status"] == "Booked":
            st.warning(
                "This slot is already booked in the simulation. Please choose an available slot."
            )

        book_selected_slot = st.button("Book Selected Simulated Slot")

        if book_selected_slot:

            if selected_slot["slot_status"] == "Booked":
                st.error(
                    "This simulated slot is booked. Please select an available slot before booking."
                )
                st.stop()

            booking_context = st.session_state.get("reservation_context", {})

            booking_code = generate_access_code()

            st.subheader("6. Simulated Reservation Confirmation")

            reservation_summary = f"""
Reservation Type: Simulated EV Charging Slot
Booking Mode: {booking_context.get("booking_mode", booking_mode)}
Booking Code: EV-{booking_code}

Station: {booking_context.get("selected_station_display", selected_station_display)}
State / Territory: {booking_context.get("selected_state", selected_state)}
Vehicle: {booking_context.get("selected_ev", selected_ev)}
Driver: {booking_context.get("driver_name", driver_name) if str(booking_context.get("driver_name", driver_name)).strip() != "" else "Not provided"}
Vehicle Plate / Reference: {booking_context.get("vehicle_plate", vehicle_plate) if str(booking_context.get("vehicle_plate", vehicle_plate)).strip() != "" else "Not provided"}

Selected Slot Date: {selected_slot["slot_date"]}
Selected Slot Time: {selected_slot["slot_time"]}
Expected Charging Duration: {selected_slot["expected_duration_min"]} minutes
Expected Demand Period: {booking_context.get("selected_time_period", selected_time_period)}

Slot Status: {selected_slot["slot_status"]}
Booking Confidence Score: {selected_slot["booking_confidence_score"]}/100
Estimated Wait Time: {selected_slot["estimated_wait_time_min"]} minutes

Important Note:
This is a simulated reservation only. It does not reserve a real charging station.
A production version would require operator integration, live charger availability, user accounts, and payment/session control.
"""

            st.success(
                f"Simulated booking confirmed. Booking code: EV-{booking_code}"
            )

            st.code(reservation_summary)

            st.download_button(
                "Download Simulated Reservation",
                reservation_summary,
                file_name="simulated_ev_charging_reservation.txt"
            )

            st.markdown("""
            ### How this could work in a production version

            A real reservation system would need:

            - live charger availability from operators
            - connector-level booking support
            - user accounts
            - payment or pre-authorisation
            - cancellation and no-show rules
            - charger access control
            - integration through operator APIs or OCPI
            - live delay handling if the driver arrives late

            This prototype demonstrates the user workflow and decision logic, not real station booking.
            """)
            
# -----------------------------
# CONGESTION RISK ANALYSIS
# -----------------------------

elif page == "Congestion Risk Analysis":
    st.title("🚦 Congestion Risk Analysis")

    st.markdown("""
    Estimate EV charging congestion risk using charger power,
    reliability and  infrastructure availability indicators.
    """)

    congestion_df = ocm_df.copy()
    congestion_df["max_power_kw"] = congestion_df["max_power_kw"].fillna(0)

    state_station_counts = congestion_df.groupby("state_clean").size().to_dict()

    congestion_df["state_station_count"] = congestion_df["state_clean"].map(
        state_station_counts
    )

    congestion_df["congestion_risk_score"] = (
        ((100 - congestion_df["reliability_score"]) * 0.4)
        + ((150 - congestion_df["max_power_kw"].clip(upper=150)) * 0.3)
        + ((100 / congestion_df["state_station_count"].clip(lower=1)) * 30)
    )

    congestion_df["congestion_risk_score"] = (
        congestion_df["congestion_risk_score"].clip(lower=0, upper=100).round(2)
    )

    def congestion_label(score):
        if score >= 70:
            return "High Risk"
        elif score >= 40:
            return "Medium Risk"
        return "Low Risk"

    congestion_df["congestion_label"] = congestion_df["congestion_risk_score"].apply(
        congestion_label
    )

    st.subheader("Highest Congestion Risk Stations")

    risk_view = (
        congestion_df[
            [
                "station_name",
                "state_clean",
                "max_power_kw",
                "reliability_score",
                "congestion_risk_score",
                "congestion_label",
            ]
        ]
        .sort_values("congestion_risk_score", ascending=False)
    )

    st.dataframe(risk_view.head(20), use_container_width=True)

    st.subheader("Congestion Risk Distribution")
    congestion_dist = congestion_df["congestion_label"].value_counts().reset_index()
    congestion_dist.columns = ["Congestion Risk", "Count"]
    st.bar_chart(congestion_dist.set_index("Congestion Risk"))


# -----------------------------
# DYNAMIC PRICING SIMULATOR
# -----------------------------

elif page == "Dynamic Pricing Simulator":
    st.title("💸 Dynamic Pricing Simulator")

    st.markdown("""
    Simulate how EV charging prices could change based on charger speed,
    congestion risk and  reliability.
    """)

    pricing_df = ocm_df.copy()

    base_price = st.slider("Base Price per kWh ($)", 0.20, 1.00, 0.45, 0.05)

    pricing_df["base_price_per_kwh"] = base_price

    pricing_df["speed_premium"] = pricing_df["max_power_kw"].fillna(0).apply(
        lambda x: 0.25 if x >= 150 else 0.10 if x >= 50 else 0.00
    )

    pricing_df["reliability_discount"] = pricing_df["reliability_score"].fillna(0).apply(
        lambda x: 0.05 if x >= 70 else 0.00
    )

    pricing_df["simulated_price_per_kwh"] = (
        pricing_df["base_price_per_kwh"]
        + pricing_df["speed_premium"]
        - pricing_df["reliability_discount"]
    ).round(2)

    st.subheader("Simulated Charging Prices")

    st.dataframe(
        pricing_df[
            [
                "station_name",
                "state_clean",
                "max_power_kw",
                "reliability_score",
                "speed_premium",
                "reliability_discount",
                "simulated_price_per_kwh",
            ]
        ]
        .sort_values("simulated_price_per_kwh", ascending=False)
        .head(25),
        use_container_width=True,
    )

    st.subheader("Average Simulated Price by State")

    price_state = (
        pricing_df.groupby("state_clean")["simulated_price_per_kwh"]
        .mean()
        .reset_index()
        .sort_values("simulated_price_per_kwh", ascending=False)
    )

    st.bar_chart(price_state.set_index("state_clean"))

# -----------------------------
# CHARGING COST SIMULATOR
# -----------------------------

elif page == "Charging Cost Simulator":
    st.title("🔋 Charging Cost Simulator")

    st.markdown("""
    Estimate charging session cost based on battery size, charging need and  simulated electricity price.
    """)

    col1, col2, col3 = st.columns(3)

    with col1:
        battery_size = st.slider("Battery Size (kWh)", 30, 120, 60)

    with col2:
        current_battery = st.slider("Current Battery (%)", 0, 100, 20)

    with col3:
        target_battery = st.slider("Target Battery (%)", 0, 100, 80)

    price_per_kwh = st.slider("Price per kWh ($)", 0.20, 1.20, 0.55, 0.05)

    charge_needed_percent = max(target_battery - current_battery, 0)

    energy_needed_kwh = battery_size * charge_needed_percent / 100
    estimated_cost = energy_needed_kwh * price_per_kwh

    col1, col2, col3 = st.columns(3)

    col1.metric("Energy Needed", f"{round(energy_needed_kwh, 1)} kWh")
    col2.metric("Estimated Cost", f"${round(estimated_cost, 2)}")
    col3.metric("Charge Increase", f"{charge_needed_percent}%")

    if target_battery <= current_battery:
        st.warning("Target battery must be higher than current battery.")
    else:
        st.success(
            f"Estimated cost to charge from {current_battery}% to {target_battery}% is ${round(estimated_cost, 2)}."
        )

# -----------------------------
# AVAILABILITY STRESS TEST
# -----------------------------

elif page == "Availability Stress Test":
    st.title("🧪 Availability Stress Test")

    st.markdown("""
    Simulate how charger availability disruptions could affect EV charging capacity.
    """)

    stress_df = ocm_df.copy()

    stress_df["total_connector_quantity"] = pd.to_numeric(
        stress_df["total_connector_quantity"], errors="coerce"
    ).fillna(1)

    selected_stress_state = st.selectbox(
        "Select State",
        sorted(stress_df["state_clean"].dropna().unique()),
        key="stress_state",
    )

    outage_rate = st.slider("Simulated Charger Outage Rate (%)", 0, 80, 20)

    state_stress_df = stress_df[stress_df["state_clean"] == selected_stress_state].copy()

    current_connectors = state_stress_df["total_connector_quantity"].sum()
    available_connectors = current_connectors * (1 - outage_rate / 100)
    lost_connectors = current_connectors - available_connectors

    col1, col2, col3 = st.columns(3)

    col1.metric("Current Connectors", int(current_connectors))
    col2.metric("Available After Outage", int(available_connectors))
    col3.metric("Connectors Lost", int(lost_connectors))

    if outage_rate >= 50:
        st.error("Severe disruption: charging capacity is heavily reduced.")
    elif outage_rate >= 25:
        st.warning("Moderate disruption: queues may increase significantly.")
    else:
        st.success("Low disruption: network capacity remains relatively stable.")

    st.subheader("Station-Level Availability Simulation")

    state_stress_df["simulated_available_connectors"] = (
        state_stress_df["total_connector_quantity"] * (1 - outage_rate / 100)
    ).round(1)

    st.dataframe(
        state_stress_df[
            [
                "station_name",
                "town",
                "state_clean",
                "total_connector_quantity",
                "simulated_available_connectors",
                "reliability_score",
            ]
        ]
        .sort_values("simulated_available_connectors")
        .head(25),
        use_container_width=True,
    )


elif page == "Fleet Route Upload":

    st.title("🚚 Fleet Route Upload")

    st.markdown("""
    Upload a CSV of fleet routes and  estimate EV charging requirements, route risk,
    charging cost and  charging time across multiple trips.

    This is a high-level fleet planning model, not a live route optimizer.
    For exact route maps and  charger sequencing, use the Real Route Optimizer.
    """)

    st.caption(
        "This page is designed for fleet managers who need to quickly assess many routes at once."
    )

    city_coordinates = {
        "Sydney": [151.2093, -33.8688],
        "Melbourne": [144.9631, -37.8136],
        "Brisbane": [153.0251, -27.4698],
        "Adelaide": [138.6007, -34.9285],
        "Perth": [115.8605, -31.9505],
        "Canberra": [149.1300, -35.2809],
        "Hobart": [147.3272, -42.8821],
        "Darwin": [130.8456, -12.4634],
        "Gold Coast": [153.4000, -28.0167],
        "Newcastle": [151.7817, -32.9283],
        "Wollongong": [150.8931, -34.4278],
        "Geelong": [144.3617, -38.1499]
    }

    ev_profiles = {
        "Tesla Model 3 RWD": {"battery_kwh": 60, "range_km": 513},
        "Tesla Model Y RWD": {"battery_kwh": 60, "range_km": 455},
        "BYD Atto 3": {"battery_kwh": 60.5, "range_km": 420},
        "BYD Seal": {"battery_kwh": 82.5, "range_km": 570},
        "Kia EV6": {"battery_kwh": 77.4, "range_km": 528},
        "Hyundai Ioniq 5": {"battery_kwh": 77.4, "range_km": 507},
        "MG4 Excite 51": {"battery_kwh": 51, "range_km": 350}
    }

    weather_multipliers = {
        "Normal": 1.0,
        "Cold Weather": 0.82,
        "Heavy Rain": 0.88,
        "Extreme Heat": 0.90
    }

    strategy_targets = {
        "Conservative": 80,
        "Fastest Trip": 60,
        "Fewest Stops": 90
    }

    def fleet_haversine_distance(lat1, lon1, lat2, lon2):
        radius_km = 6371

        lat1 = math.radians(lat1)
        lon1 = math.radians(lon1)
        lat2 = math.radians(lat2)
        lon2 = math.radians(lon2)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )

        c = 2 * math.asin(math.sqrt(a))

        return radius_km * c

    st.subheader("CSV Format")

    st.markdown("""
    Your CSV should contain these columns:

    ```csv
    route_id,start_city,destination_city,ev_model,starting_battery_percent,weather,strategy
    R001,Sydney,Melbourne,Tesla Model Y RWD,90,Normal,Conservative
    R002,Sydney,Canberra,BYD Atto 3,80,Cold Weather,Fastest Trip
    R003,Melbourne,Geelong,Kia EV6,75,Heavy Rain,Fewest Stops
    ```
    """)

    sample_fleet_routes = pd.DataFrame(
        [
            {
                "route_id": "R001",
                "start_city": "Sydney",
                "destination_city": "Melbourne",
                "ev_model": "Tesla Model Y RWD",
                "starting_battery_percent": 90,
                "weather": "Normal",
                "strategy": "Conservative"
            },
            {
                "route_id": "R002",
                "start_city": "Sydney",
                "destination_city": "Canberra",
                "ev_model": "BYD Atto 3",
                "starting_battery_percent": 80,
                "weather": "Cold Weather",
                "strategy": "Fastest Trip"
            },
            {
                "route_id": "R003",
                "start_city": "Melbourne",
                "destination_city": "Geelong",
                "ev_model": "Kia EV6",
                "starting_battery_percent": 75,
                "weather": "Heavy Rain",
                "strategy": "Fewest Stops"
            }
        ]
    )

    sample_csv = sample_fleet_routes.to_csv(index=False)

    st.download_button(
        "Download Sample Fleet Route CSV",
        sample_csv,
        file_name="chargesense_sample_fleet_routes.csv",
        mime="text/csv"
    )

    uploaded_file = st.file_uploader(
        "Upload Fleet Route CSV",
        type=["csv"]
    )

    st.subheader("Fleet Planning Assumptions")

    col1, col2, col3 = st.columns(3)

    with col1:
        minimum_arrival_percent = st.slider(
            "Minimum Arrival Battery (%)",
            5,
            50,
            20
        )

    with col2:
        safety_buffer_km = st.slider(
            "Safety Buffer (km)",
            20,
            100,
            50
        )

    with col3:
        electricity_price_per_kwh = st.slider(
            "Charging Price ($/kWh)",
            0.20,
            1.20,
            0.65,
            0.05
        )

    if uploaded_file is not None:

        fleet_df = pd.read_csv(uploaded_file)

        required_columns = [
            "route_id",
            "start_city",
            "destination_city",
            "ev_model",
            "starting_battery_percent",
            "weather",
            "strategy"
        ]

        missing_columns = [
            col for col in required_columns
            if col not in fleet_df.columns
        ]

        if len(missing_columns) > 0:
            st.error(
                "Missing required columns: "
                + ", ".join(missing_columns)
            )
            st.stop()

        results = []

        for _, row in fleet_df.iterrows():

            route_id = row["route_id"]
            start_city = str(row["start_city"]).strip()
            destination_city = str(row["destination_city"]).strip()
            ev_model = str(row["ev_model"]).strip()
            weather = str(row["weather"]).strip()
            strategy = str(row["strategy"]).strip()

            try:
                starting_battery_percent = float(
                    row["starting_battery_percent"]
                )
            except:
                starting_battery_percent = 90

            if start_city not in city_coordinates:
                results.append({
                    "route_id": route_id,
                    "status": "Invalid start city",
                    "start_city": start_city,
                    "destination_city": destination_city
                })
                continue

            if destination_city not in city_coordinates:
                results.append({
                    "route_id": route_id,
                    "status": "Invalid destination city",
                    "start_city": start_city,
                    "destination_city": destination_city
                })
                continue

            if ev_model not in ev_profiles:
                results.append({
                    "route_id": route_id,
                    "status": "Invalid EV model",
                    "start_city": start_city,
                    "destination_city": destination_city
                })
                continue

            if weather not in weather_multipliers:
                weather = "Normal"

            if strategy not in strategy_targets:
                strategy = "Conservative"

            start_coords = city_coordinates[start_city]
            end_coords = city_coordinates[destination_city]

            straight_line_distance = fleet_haversine_distance(
                start_coords[1],
                start_coords[0],
                end_coords[1],
                end_coords[0]
            )

            estimated_route_distance_km = straight_line_distance * 1.25

            estimated_drive_time_hours = (
                estimated_route_distance_km / 85
            )

            battery_kwh = ev_profiles[ev_model]["battery_kwh"]
            base_range_km = ev_profiles[ev_model]["range_km"]

            adjusted_range_km = (
                base_range_km * weather_multipliers[weather]
            )

            target_battery_percent = strategy_targets[strategy]

            usable_start_range_km = adjusted_range_km * (
                starting_battery_percent / 100
            )

            usable_after_charge_range_km = adjusted_range_km * (
                (target_battery_percent - minimum_arrival_percent) / 100
            )

            safe_start_range_km = max(
                usable_start_range_km - safety_buffer_km,
                1
            )

            safe_after_charge_range_km = max(
                usable_after_charge_range_km - safety_buffer_km,
                1
            )

            if estimated_route_distance_km <= safe_start_range_km:
                estimated_stops = 0
            else:
                remaining_distance = (
                    estimated_route_distance_km - safe_start_range_km
                )

                estimated_stops = int(
                    math.ceil(
                        remaining_distance / safe_after_charge_range_km
                    )
                )

            charge_needed_percent = max(
                target_battery_percent - minimum_arrival_percent,
                0
            )

            estimated_energy_per_stop_kwh = (
                battery_kwh * charge_needed_percent / 100
            )

            total_energy_added_kwh = (
                estimated_energy_per_stop_kwh * estimated_stops
            )

            estimated_charging_cost_aud = (
                total_energy_added_kwh * electricity_price_per_kwh
            )

            if strategy == "Fastest Trip":
                assumed_effective_power_kw = 220
            elif strategy == "Conservative":
                assumed_effective_power_kw = 160
            else:
                assumed_effective_power_kw = 140

            estimated_charging_time_min = (
                total_energy_added_kwh
                / assumed_effective_power_kw
            ) * 60

            estimated_total_trip_time_hours = (
                estimated_drive_time_hours
                + estimated_charging_time_min / 60
            )

            if estimated_stops >= 5:
                risk_flag = "High Fleet Charging Risk"
            elif estimated_stops >= 2:
                risk_flag = "Moderate Fleet Charging Risk"
            else:
                risk_flag = "Lower Fleet Charging Risk"

            if starting_battery_percent < 50:
                risk_flag = "High Fleet Charging Risk"

            results.append({
                "route_id": route_id,
                "status": "Processed",
                "start_city": start_city,
                "destination_city": destination_city,
                "ev_model": ev_model,
                "weather": weather,
                "strategy": strategy,
                "starting_battery_percent": starting_battery_percent,
                "estimated_route_distance_km": round(
                    estimated_route_distance_km,
                    1
                ),
                "adjusted_range_km": round(
                    adjusted_range_km,
                    1
                ),
                "estimated_stops": estimated_stops,
                "estimated_energy_added_kwh": round(
                    total_energy_added_kwh,
                    1
                ),
                "estimated_charging_time_min": round(
                    estimated_charging_time_min,
                    1
                ),
                "estimated_charging_cost_aud": round(
                    estimated_charging_cost_aud,
                    2
                ),
                "estimated_total_trip_time_hours": round(
                    estimated_total_trip_time_hours,
                    2
                ),
                "risk_flag": risk_flag
            })

        results_df = pd.DataFrame(results)

        processed_df = results_df[
            results_df["status"] == "Processed"
        ].copy()

        st.subheader("Fleet Route Results")

        if len(processed_df) > 0:

            total_routes = len(processed_df)

            high_risk_routes = len(
                processed_df[
                    processed_df["risk_flag"]
                    == "High Fleet Charging Risk"
                ]
            )

            total_estimated_cost = (
                processed_df["estimated_charging_cost_aud"].sum()
            )

            total_estimated_charging_time = (
                processed_df["estimated_charging_time_min"].sum()
            )

            avg_trip_time = (
                processed_df["estimated_total_trip_time_hours"].mean()
            )

            col1, col2, col3, col4, col5 = st.columns(5)

            col1.metric(
                "Routes Processed",
                total_routes
            )

            col2.metric(
                "High Risk Routes",
                high_risk_routes
            )

            col3.metric(
                "Total Charging Cost",
                f"${round(total_estimated_cost, 2)}"
            )

            col4.metric(
                "Total Charging Time",
                f"{round(total_estimated_charging_time, 1)} min"
            )

            col5.metric(
                "Avg Trip Time",
                f"{round(avg_trip_time, 1)} hrs"
            )

        st.dataframe(
            results_df,
            use_container_width=True
        )

        csv_results = results_df.to_csv(index=False)

        st.download_button(
            "Download Fleet Route Analysis CSV",
            csv_results,
            file_name="chargesense_fleet_route_analysis.csv",
            mime="text/csv"
        )

        if len(processed_df) > 0:

            st.subheader("Fleet Charging Risk Breakdown")

            risk_counts = (
                processed_df["risk_flag"]
                .value_counts()
                .reset_index()
            )

            risk_counts.columns = [
                "risk_flag",
                "route_count"
            ]

            st.dataframe(
                risk_counts,
                use_container_width=True
            )

            st.bar_chart(
                risk_counts.set_index("risk_flag")["route_count"]
            )

            st.subheader("Estimated Charging Cost by Route")

            cost_chart = processed_df.sort_values(
                "estimated_charging_cost_aud",
                ascending=False
            )

            st.bar_chart(
                cost_chart.set_index("route_id")[
                    "estimated_charging_cost_aud"
                ]
            )

            st.subheader("Estimated Stops by Route")

            stops_chart = processed_df.sort_values(
                "estimated_stops",
                ascending=False
            )

            st.bar_chart(
                stops_chart.set_index("route_id")[
                    "estimated_stops"
                ]
            )

            st.subheader("Fleet Planning Recommendations")

            highest_cost_route = processed_df.sort_values(
                "estimated_charging_cost_aud",
                ascending=False
            ).iloc[0]

            highest_stop_route = processed_df.sort_values(
                "estimated_stops",
                ascending=False
            ).iloc[0]

            st.markdown(
                f"""
                **Highest cost route:** Route **{highest_cost_route["route_id"]}**
                from **{highest_cost_route["start_city"]}** to **{highest_cost_route["destination_city"]}**
                has the highest estimated charging cost.

                **Most charging-intensive route:** Route **{highest_stop_route["route_id"]}**
                from **{highest_stop_route["start_city"]}** to **{highest_stop_route["destination_city"]}**
                requires the most estimated charging stops.

                **Fleet action:** Review high-risk routes for longer-range vehicles, depot charging options,
                alternative charging strategies, or route scheduling changes.
                """
            )

    else:

        st.info(
            "Upload a fleet route CSV to generate multi-route charging estimates."
        )

    st.markdown("""
    ### How to interpret this

    **Fleet Route Upload** helps estimate EV charging risk across multiple planned trips.

    It is useful for:
    - fleet transition planning
    - route feasibility checks
    - cost estimation
    - identifying routes that may need longer-range vehicles
    - identifying routes that may need depot charging or schedule changes

    This page uses city-level route estimates. A future version could use exact depot addresses,
    OSRM road routing, live charger availability, depot charging infrastructure and  vehicle telematics.
    """)

elif page == "Operator Performance Dashboard":

    st.title("🏢 Operator Performance Dashboard")

    st.markdown("""
    Benchmark charging operators based on network size, charger speed, ultra-fast coverage,
    reliability indicators, availability estimates and  amenity quality.

    This view helps identify which operators appear strongest from an infrastructure and  user-experience perspective.
    """)

    st.caption(
        "Operator names are estimated from station names using keyword matching. Scores are based on available public metadata, not confirmed operator-provided performance data."
    )

    operator_df = ocm_df.copy()

    operator_df["max_power_kw"] = pd.to_numeric(
        operator_df["max_power_kw"],
        errors="coerce"
    )

    operator_df["reliability_score"] = pd.to_numeric(
        operator_df["reliability_score"],
        errors="coerce"
    )

    def identify_operator(station_name):
        name = str(station_name).lower()

        if "tesla" in name:
            return "Tesla"
        elif "chargefox" in name:
            return "Chargefox"
        elif "evie" in name:
            return "Evie"
        elif "nrma" in name:
            return "NRMA"
        elif "ampol" in name:
            return "Ampol"
        elif "shell" in name:
            return "Shell Recharge"
        elif "bp" in name:
            return "BP Pulse"
        elif "jolt" in name:
            return "JOLT"
        elif "chargepoint" in name:
            return "ChargePoint"
        elif "racv" in name:
            return "RACV"
        elif "woolworths" in name:
            return "Woolworths"
        elif "7-eleven" in name or "7 eleven" in name:
            return "7-Eleven"
        else:
            return "Other / Unknown"

    def operator_availability(row):
        reliability = row.get("reliability_score", 0)

        if reliability >= 70:
            return "Available"
        elif reliability >= 40:
            return "Busy"
        elif reliability > 0:
            return "Unknown"
        else:
            return "Offline"

    def operator_amenity_score(row):
        text = " ".join(
            [
                str(row.get("station_name", "")),
                str(row.get("address", "")),
                str(row.get("town", ""))
            ]
        ).lower()

        high_amenity_keywords = [
            "service centre",
            "service center",
            "shopping centre",
            "shopping center",
            "7-eleven",
            "7 eleven",
            "woolworths",
            "coles",
            "mcdonald",
            "kfc",
            "hungry jack",
            "ampol",
            "bp",
            "shell",
            "caltex",
            "airport"
        ]

        medium_amenity_keywords = [
            "car park",
            "parking",
            "hotel",
            "motel",
            "club",
            "cafe",
            "restaurant",
            "mall",
            "plaza",
            "visitor centre",
            "visitor center"
        ]

        score = 0

        for keyword in high_amenity_keywords:
            if keyword in text:
                score += 30

        for keyword in medium_amenity_keywords:
            if keyword in text:
                score += 15

        return min(score, 100)

    operator_df["operator"] = operator_df["station_name"].apply(
        identify_operator
    )

    operator_df["availability_status"] = operator_df.apply(
        operator_availability,
        axis=1
    )

    availability_weight = {
        "Available": 100,
        "Busy": 30,
        "Unknown": 0,
        "Offline": -200
    }

    operator_df["availability_score"] = (
        operator_df["availability_status"].map(availability_weight)
    )

    operator_df["amenity_score"] = operator_df.apply(
        operator_amenity_score,
        axis=1
    )

    operator_df["is_ultra_fast"] = (
        operator_df["max_power_kw"].fillna(0) >= 250
    )

    operator_summary = (
        operator_df
        .groupby("operator")
        .agg(
            station_count=("station_name", "count"),
            avg_power_kw=("max_power_kw", "mean"),
            max_power_kw=("max_power_kw", "max"),
            avg_reliability=("reliability_score", "mean"),
            avg_availability_score=("availability_score", "mean"),
            avg_amenity_score=("amenity_score", "mean"),
            ultra_fast_sites=("is_ultra_fast", "sum")
        )
        .reset_index()
    )

    operator_summary["ultra_fast_share"] = (
        operator_summary["ultra_fast_sites"]
        / operator_summary["station_count"]
    )

    operator_summary["operator_performance_score"] = (
        operator_summary["station_count"].rank(pct=True) * 25
        + operator_summary["avg_power_kw"].fillna(0).rank(pct=True) * 25
        + operator_summary["avg_reliability"].fillna(0).rank(pct=True) * 20
        + operator_summary["ultra_fast_share"].fillna(0).rank(pct=True) * 20
        + operator_summary["avg_amenity_score"].fillna(0).rank(pct=True) * 10
    )

    operator_summary["operator_performance_score"] = (
        operator_summary["operator_performance_score"]
        .clip(lower=0, upper=100)
        .round(2)
    )

    def operator_label(score):
        if score >= 75:
            return "Strong Network"
        elif score >= 50:
            return "Developing Network"
        return "Limited / Emerging Network"

    operator_summary["operator_label"] = (
        operator_summary["operator_performance_score"]
        .apply(operator_label)
    )

    operator_summary = operator_summary.sort_values(
        "operator_performance_score",
        ascending=False
    )

    top_operator = operator_summary.iloc[0]
    largest_operator = operator_summary.sort_values(
        "station_count",
        ascending=False
    ).iloc[0]

    fastest_operator = operator_summary.sort_values(
        "avg_power_kw",
        ascending=False
    ).iloc[0]

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Top Overall Operator",
        top_operator["operator"]
    )

    col2.metric(
        "Largest Network",
        largest_operator["operator"]
    )

    col3.metric(
        "Highest Avg Power",
        fastest_operator["operator"]
    )

    st.subheader("Operator Performance Ranking")

    st.dataframe(
        operator_summary[
            [
                "operator",
                "station_count",
                "avg_power_kw",
                "max_power_kw",
                "ultra_fast_sites",
                "ultra_fast_share",
                "avg_reliability",
                "avg_availability_score",
                "avg_amenity_score",
                "operator_performance_score",
                "operator_label"
            ]
        ],
        use_container_width=True
    )

    st.subheader("Operator Performance Score")

    score_chart = operator_summary.set_index("operator")[
        "operator_performance_score"
    ]

    st.bar_chart(score_chart)

    st.subheader("Station Count by Operator")

    count_chart = operator_summary.sort_values(
        "station_count",
        ascending=False
    ).set_index("operator")["station_count"]

    st.bar_chart(count_chart)

    st.subheader("Average Charger Power by Operator")

    power_chart = operator_summary.sort_values(
        "avg_power_kw",
        ascending=False
    ).set_index("operator")["avg_power_kw"]

    st.bar_chart(power_chart)

    st.markdown("""
    ### How to interpret this

    **Operator Performance Score** is a benchmark score combining:
    - network size
    - average charger power
    - ultra-fast charger share
    - reliability indicators
    - amenity score

    This is not an official operator ranking. It is a prototype benchmark using public charger metadata.
    """)

elif page == "Model Assumptions":

    st.title("📘 Model Assumptions")

    st.markdown("""
    ### Why this page matters

    EVAtlas uses public EV infrastructure datasets and  scenario-based models.
    Some outputs are analytical estimates, not confirmed real-world measurements.

    ### Key Assumptions

    **1. Reliability Score**  
    Based on recent verification, data quality and  days since last verified.

    **2. Infrastructure Gap Score**  
    Combines charger density, ultra-fast coverage and  average reliability.

    **3. Congestion Risk Score**  
    Uses charger power, reliability and  state-level infrastructure availability as proxy inputs.

    **4. Demand  Forecast Model**  
    Uses estimated EV fleet growth, population share, public charging frequency and  current station count.

    **5. Queue Simulation**  
    Estimates wait time using arrivals per hour, connector count and  average charging session duration.

    **6. Route Intelligence**  
    Uses state-level route corridors, not exact road geometry. Full routing would require a routing API.

    ### Current Limitations

    - No live charger occupancy data
    - No real-time outage feed
    - No confirmed user charging-session history
    - Some location metadata is incomplete or inconsistent
    - Forecasting is scenario-based, not a trained time-series model

    ### Future Improvements

    - Add real charger utilization data
    - Add routing API integration
    - Add operator-level uptime data
    - Add suburb/LGA-level population and  EV registration data
    - Train models on historical failure and  usage records
    """)


elif page == "Fleet & Council Intelligence":

    st.title("🏛️ Fleet & Council Intelligence")

    st.markdown(
        "Strategic EV infrastructure intelligence for councils, fleet managers and infrastructure planners."
    )

    st.markdown(
        "This page combines EV adoption, charger supply, reliability, demand pressure and operator benchmarking to support investment and planning decisions."
    )

    st.caption(
        "This dashboard uses public charger metadata, AAA/BITRE EV registration-derived inputs and scenario-based planning assumptions. "
        "It is a decision-support prototype, not an official infrastructure forecast."
    )

    # -----------------------------
    # Prepare data
    # -----------------------------

    b2b_df = ocm_df.copy()

    b2b_df["state_clean"] = b2b_df["state_clean"].fillna("Unknown")
    b2b_df["station_name"] = b2b_df["station_name"].fillna("Unknown Station")

    if "operator" not in b2b_df.columns:
        b2b_df["operator"] = "Unknown Operator"

    b2b_df["operator"] = b2b_df["operator"].fillna("Unknown Operator")

    b2b_df["max_power_kw"] = pd.to_numeric(
        b2b_df["max_power_kw"],
        errors="coerce"
    ).fillna(0)

    b2b_df["reliability_score"] = pd.to_numeric(
        b2b_df["reliability_score"],
        errors="coerce"
    ).fillna(0)

    # -----------------------------
    # Planning assumptions
    # -----------------------------

    st.subheader("Planning Assumptions")

    col1, col2, col3 = st.columns(3)

    with col1:
        forecast_horizon_years = st.slider(
            "Forecast Horizon (Years)",
            1,
            10,
            3
        )

    with col2:
        public_charges_per_ev_per_month = st.slider(
            "Public Charges per EV per Month",
            1,
            10,
            4
        )

    with col3:
        sessions_per_charger_per_month = st.slider(
            "Sessions per Charger per Month",
            100,
            2000,
            800,
            50
        )

    st.caption(
        "These assumptions are adjustable because this page is designed for scenario testing rather than official forecasting."
    )

    # -----------------------------
    # State-level aggregation
    # -----------------------------

    state_summary = (
        b2b_df
        .groupby("state_clean")
        .agg(
            station_count=("station_name", "count"),
            avg_power_kw=("max_power_kw", "mean"),
            avg_reliability=("reliability_score", "mean"),
            ultra_fast_count=("max_power_kw", lambda x: (x >= 150).sum()),
            high_power_count=("max_power_kw", lambda x: (x >= 50).sum())
        )
        .reset_index()
    )

    state_summary = state_summary[
        state_summary["state_clean"] != "Unknown"
    ].copy()

    # -----------------------------
    # EV market assumptions
    # -----------------------------
    # Replace these later with more granular real EV registrations by state/LGA/postcode if available.

    ev_market_estimates = {
        "New South Wales": 95000,
        "Victoria": 82000,
        "Queensland": 68000,
        "Western Australia": 32000,
        "South Australia": 21000,
        "Australian Capital Territory": 14000,
        "Tasmania": 8000,
        "Northern Territory": 2500,
        "NSW": 95000,
        "VIC": 82000,
        "QLD": 68000,
        "WA": 32000,
        "SA": 21000,
        "ACT": 14000,
        "TAS": 8000,
        "NT": 2500
    }

    state_summary["estimated_evs"] = state_summary["state_clean"].map(
        ev_market_estimates
    ).fillna(10000)

    state_summary["chargers_per_1000_evs"] = (
        state_summary["station_count"]
        / state_summary["estimated_evs"]
        * 1000
    )

    state_summary["ultra_fast_share_%"] = (
        state_summary["ultra_fast_count"]
        / state_summary["station_count"].replace(0, 1)
        * 100
    )

    state_summary["estimated_future_evs"] = (
        state_summary["estimated_evs"]
        * ((1.25) ** forecast_horizon_years)
    ).round(0)

    state_summary["monthly_public_sessions_needed"] = (
        state_summary["estimated_future_evs"]
        * public_charges_per_ev_per_month
    )

    state_summary["estimated_monthly_capacity"] = (
        state_summary["station_count"]
        * sessions_per_charger_per_month
    )

    state_summary["demand_pressure_ratio"] = (
        state_summary["monthly_public_sessions_needed"]
        / state_summary["estimated_monthly_capacity"].replace(0, 1)
    )

    state_summary["additional_chargers_needed"] = (
        (
            state_summary["monthly_public_sessions_needed"]
            - state_summary["estimated_monthly_capacity"]
        )
        / sessions_per_charger_per_month
    ).clip(lower=0).round(0)

    # -----------------------------
    # Investment priority score
    # -----------------------------

    state_summary["supply_gap_score"] = (
        100 - state_summary["chargers_per_1000_evs"].clip(upper=100)
    )

    state_summary["demand_pressure_score"] = (
        state_summary["demand_pressure_ratio"].clip(upper=5)
        / 5
        * 100
    )

    state_summary["reliability_gap_score"] = (
        100 - state_summary["avg_reliability"].clip(upper=100)
    )

    state_summary["ultra_fast_gap_score"] = (
        100 - state_summary["ultra_fast_share_%"].clip(upper=100)
    )

    state_summary["investment_priority_score"] = (
        state_summary["supply_gap_score"] * 0.35
        + state_summary["demand_pressure_score"] * 0.30
        + state_summary["reliability_gap_score"] * 0.20
        + state_summary["ultra_fast_gap_score"] * 0.15
    )

    state_summary["investment_priority_score"] = (
        state_summary["investment_priority_score"]
        .clip(lower=0, upper=100)
        .round(2)
    )

    # -----------------------------
    # Safe top-state definitions
    # -----------------------------

    if len(state_summary) == 0:
        st.error("No valid state-level data available for fleet and council analysis.")
        st.stop()

    top_investment_state = (
        state_summary
        .sort_values("investment_priority_score", ascending=False)
        .iloc[0]
    )

    top_demand_state = (
        state_summary
        .sort_values("demand_pressure_ratio", ascending=False)
        .iloc[0]
    )

    best_reliability_state = (
        state_summary
        .sort_values("avg_reliability", ascending=False)
        .iloc[0]
    )

    weakest_supply_state = (
        state_summary
        .sort_values("chargers_per_1000_evs", ascending=True)
        .iloc[0]
    )

    # -----------------------------
    # Executive summary
    # -----------------------------

    st.subheader("Executive Summary")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Highest Investment Priority",
        top_investment_state["state_clean"],
        f"Score {top_investment_state['investment_priority_score']}"
    )

    col2.metric(
        "Highest Demand Pressure",
        top_demand_state["state_clean"],
        f"{round(top_demand_state['demand_pressure_ratio'], 2)}x"
    )

    col3.metric(
        "Best Avg Reliability",
        best_reliability_state["state_clean"],
        f"{round(best_reliability_state['avg_reliability'], 1)}"
    )

    col4.metric(
        "Weakest Charger Supply",
        weakest_supply_state["state_clean"],
        f"{round(weakest_supply_state['chargers_per_1000_evs'], 2)} / 1k EVs"
    )

    st.info(
        f"{top_investment_state['state_clean']} currently ranks as the highest investment-priority state in this prototype, "
        f"based on charger supply, estimated EV demand growth, reliability and ultra-fast charger coverage."
    )

    # -----------------------------
    # State planning table
    # -----------------------------

    st.subheader("State-Level Fleet & Council Planning Table")

    display_state_summary = state_summary[
        [
            "state_clean",
            "station_count",
            "estimated_evs",
            "estimated_future_evs",
            "chargers_per_1000_evs",
            "avg_power_kw",
            "avg_reliability",
            "ultra_fast_count",
            "ultra_fast_share_%",
            "monthly_public_sessions_needed",
            "estimated_monthly_capacity",
            "demand_pressure_ratio",
            "additional_chargers_needed",
            "investment_priority_score"
        ]
    ].copy()

    st.dataframe(
        display_state_summary
        .sort_values("investment_priority_score", ascending=False)
        .round(2),
        use_container_width=True
    )

    # -----------------------------
    # Visualisations
    # -----------------------------

    st.subheader("Investment Priority by State")

    fig_priority = px.bar(
        state_summary.sort_values("investment_priority_score", ascending=False),
        x="state_clean",
        y="investment_priority_score",
        hover_data=[
            "station_count",
            "estimated_evs",
            "chargers_per_1000_evs",
            "demand_pressure_ratio",
            "avg_reliability",
            "ultra_fast_share_%"
        ],
        title="EV Charging Infrastructure Investment Priority Score"
    )

    st.plotly_chart(
        fig_priority,
        use_container_width=True
    )

    st.subheader("Demand Pressure vs Charger Supply")

    fig_pressure = px.scatter(
        state_summary,
        x="chargers_per_1000_evs",
        y="demand_pressure_ratio",
        size="station_count",
        color="investment_priority_score",
        hover_name="state_clean",
        hover_data=[
            "estimated_evs",
            "estimated_future_evs",
            "additional_chargers_needed",
            "avg_reliability",
            "ultra_fast_share_%"
        ],
        title="Demand Pressure Compared with Charger Supply"
    )

    st.plotly_chart(
        fig_pressure,
        use_container_width=True
    )

    st.subheader("Reliability and Ultra-Fast Coverage")

    fig_reliability = px.scatter(
        state_summary,
        x="avg_reliability",
        y="ultra_fast_share_%",
        size="station_count",
        color="state_clean",
        hover_name="state_clean",
        title="Reliability vs Ultra-Fast Charger Share"
    )

    st.plotly_chart(
        fig_reliability,
        use_container_width=True
    )

    # -----------------------------
    # Operator benchmarking
    # -----------------------------

    st.subheader("Operator Benchmarking for Planning")

    operator_summary = (
        b2b_df
        .groupby("operator")
        .agg(
            station_count=("station_name", "count"),
            avg_power_kw=("max_power_kw", "mean"),
            avg_reliability=("reliability_score", "mean"),
            ultra_fast_count=("max_power_kw", lambda x: (x >= 150).sum())
        )
        .reset_index()
    )

    operator_summary = operator_summary[
        operator_summary["operator"] != "Unknown Operator"
    ].copy()

    if len(operator_summary) > 0:

        operator_summary["ultra_fast_share_%"] = (
            operator_summary["ultra_fast_count"]
            / operator_summary["station_count"].replace(0, 1)
            * 100
        )

        operator_summary["operator_performance_score"] = (
            operator_summary["avg_power_kw"].clip(upper=350) / 350 * 30
            + operator_summary["avg_reliability"].clip(upper=100) / 100 * 45
            + operator_summary["ultra_fast_share_%"].clip(upper=100) / 100 * 25
        ).round(2)

        st.dataframe(
            operator_summary
            .sort_values("operator_performance_score", ascending=False)
            .round(2),
            use_container_width=True
        )

        fig_operator = px.bar(
            operator_summary.sort_values(
                "operator_performance_score",
                ascending=False
            ).head(15),
            x="operator",
            y="operator_performance_score",
            hover_data=[
                "station_count",
                "avg_power_kw",
                "avg_reliability",
                "ultra_fast_share_%"
            ],
            title="Top Operator Performance Scores"
        )

        st.plotly_chart(
            fig_operator,
            use_container_width=True
        )

    else:
        st.info(
            "Operator benchmarking is unavailable because operator names are missing or unknown."
        )

    # -----------------------------
    # Planning interpretation
    # -----------------------------

    st.subheader("Planning Interpretation")

    st.markdown(
        f"""
        **Key planning insight:**  
        In this scenario, **{top_investment_state['state_clean']}** has the highest investment priority score.

        This does not automatically mean it has the fewest chargers. The score combines:
        - charger supply relative to estimated EV adoption
        - future demand pressure
        - average charger reliability
        - ultra-fast charger coverage

        **Demand pressure insight:**  
        **{top_demand_state['state_clean']}** shows the highest demand pressure ratio, meaning estimated future public charging demand may place stronger pressure on existing infrastructure.

        **Fleet/council use case:**  
        A fleet or council could use this view to identify where charging coverage may become constrained, where additional chargers may be needed and where reliability or ultra-fast coverage should be improved.
        """
    )

    # -----------------------------
    # Data limitations
    # -----------------------------

    st.subheader("Data Limitations")

    st.markdown("""
    This dashboard is a prototype and has several important limitations:

    - EV registration figures are currently estimated at state level.
    - It does not yet use live charger utilisation or outage data.
    - It does not include LGA/suburb-level EV adoption.
    - It does not include grid capacity or site feasibility.
    - Demand forecasting is scenario-based, not a production statistical forecast.
    - Operator names and performance depend on available public metadata.

    A production version would require more granular EV registrations, charger utilisation, live status, traffic demand, grid feasibility and customer-specific route/depot data.
    """)

    # -----------------------------
    # Download report
    # -----------------------------

    st.subheader("Download Planning Report")

    planning_report = f"""
Fleet & Council Intelligence Report

Forecast horizon: {forecast_horizon_years} years
Public charges per EV per month: {public_charges_per_ev_per_month}
Sessions per charger per month: {sessions_per_charger_per_month}

Highest Investment Priority:
{top_investment_state['state_clean']} - Score {top_investment_state['investment_priority_score']}

Highest Demand Pressure:
{top_demand_state['state_clean']} - Demand pressure ratio {round(top_demand_state['demand_pressure_ratio'], 2)}x

Best Average Reliability:
{best_reliability_state['state_clean']} - Avg reliability {round(best_reliability_state['avg_reliability'], 1)}

Weakest Charger Supply:
{weakest_supply_state['state_clean']} - {round(weakest_supply_state['chargers_per_1000_evs'], 2)} chargers per 1,000 EVs

Prototype note:
This report uses public charger metadata and scenario-based assumptions.
It is not an official forecast.
"""

    st.code(planning_report)

    st.download_button(
        "Download Fleet & Council Planning Report",
        planning_report,
        file_name="fleet_council_planning_report.txt"
    )

    csv_state_summary = display_state_summary.to_csv(index=False)

    st.download_button(
        "Download State Planning CSV",
        csv_state_summary,
        file_name="fleet_council_state_planning.csv",
        mime="text/csv"
    )

elif page == "Route Comparison Mode":

    st.title("🧭 Route Comparison Mode")

    st.markdown("""
    Compare different EV trip scenarios across weather conditions and  charging strategies.

    This page provides a high-level planning comparison, not a full charger-by-charger route optimizer.
    Use it to understand  how vehicle choice, weather, strategy and  charging price affect total trip planning.
    """)

    city_coordinates = {
        "Sydney": [151.2093, -33.8688],
        "Melbourne": [144.9631, -37.8136],
        "Brisbane": [153.0251, -27.4698],
        "Adelaide": [138.6007, -34.9285],
        "Perth": [115.8605, -31.9505],
        "Canberra": [149.1300, -35.2809],
        "Hobart": [147.3272, -42.8821],
        "Darwin": [130.8456, -12.4634],
        "Gold Coast": [153.4000, -28.0167],
        "Newcastle": [151.7817, -32.9283],
        "Wollongong": [150.8931, -34.4278],
        "Geelong": [144.3617, -38.1499]
    }

    ev_profiles = {
        "Tesla Model 3 RWD": {"battery_kwh": 60, "range_km": 513},
        "Tesla Model Y RWD": {"battery_kwh": 60, "range_km": 455},
        "BYD Atto 3": {"battery_kwh": 60.5, "range_km": 420},
        "BYD Seal": {"battery_kwh": 82.5, "range_km": 570},
        "Kia EV6": {"battery_kwh": 77.4, "range_km": 528},
        "Hyundai Ioniq 5": {"battery_kwh": 77.4, "range_km": 507},
        "MG4 Excite 51": {"battery_kwh": 51, "range_km": 350}
    }

    weather_multipliers = {
        "Normal": 1.0,
        "Cold Weather": 0.82,
        "Heavy Rain": 0.88,
        "Extreme Heat": 0.90
    }

    strategy_targets = {
        "Conservative": 80,
        "Fastest Trip": 60,
        "Fewest Stops": 90
    }

    def haversine_distance_simple(lat1, lon1, lat2, lon2):
        import math

        radius_km = 6371

        lat1 = math.radians(lat1)
        lon1 = math.radians(lon1)
        lat2 = math.radians(lat2)
        lon2 = math.radians(lon2)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )

        c = 2 * math.asin(math.sqrt(a))

        return radius_km * c

    st.subheader("Route Inputs")

    cities = sorted(city_coordinates.keys())

    col1, col2 = st.columns(2)

    with col1:
        start_city = st.selectbox(
            "Start City",
            cities,
            index=cities.index("Sydney")
        )

    with col2:
        destination_city = st.selectbox(
            "Destination City",
            cities,
            index=cities.index("Melbourne")
        )

    if start_city == destination_city:
        st.warning("Start city and  destination city cannot be the same.")
        st.stop()

    start_coords = city_coordinates[start_city]
    end_coords = city_coordinates[destination_city]

    straight_line_distance = haversine_distance_simple(
        start_coords[1],
        start_coords[0],
        end_coords[1],
        end_coords[0]
    )

    estimated_route_distance_km = straight_line_distance * 1.25

    estimated_drive_time_hours = estimated_route_distance_km / 85

    st.caption(
        "This comparison mode estimates route distance using city coordinates and  a road-distance adjustment. "
        "Use Real Route Optimizer for exact OSRM road routing."
    )

    st.subheader("Scenario Settings")

    col1, col2, col3 = st.columns(3)

    with col1:
        selected_ev = st.selectbox(
            "EV Model",
            list(ev_profiles.keys())
        )

    with col2:
        starting_battery_percent = st.slider(
            "Starting Battery (%)",
            20,
            100,
            90
        )

    with col3:
        minimum_arrival_percent = st.slider(
            "Minimum Arrival Battery (%)",
            5,
            50,
            20
        )

    col1, col2 = st.columns(2)

    with col1:
        safety_buffer_km = st.slider(
            "Safety Buffer (km)",
            20,
            100,
            50
        )

    with col2:
        electricity_price_per_kwh = st.slider(
            "Charging Price ($/kWh)",
            0.20,
            1.20,
            0.65,
            0.05
        )

    battery_kwh = ev_profiles[selected_ev]["battery_kwh"]
    base_range_km = ev_profiles[selected_ev]["range_km"]

    st.subheader("Scenario Comparison")

    comparison_rows = []

    for weather_name, weather_multiplier in weather_multipliers.items():

        adjusted_range_km = base_range_km * weather_multiplier

        usable_start_range_km = adjusted_range_km * (
            starting_battery_percent / 100
        )

        for strategy_name, target_battery_percent in strategy_targets.items():

            usable_after_charge_range_km = adjusted_range_km * (
                (target_battery_percent - minimum_arrival_percent) / 100
            )

            safe_start_range_km = max(
                usable_start_range_km - safety_buffer_km,
                1
            )

            safe_after_charge_range_km = max(
                usable_after_charge_range_km - safety_buffer_km,
                1
            )

            if estimated_route_distance_km <= safe_start_range_km:
                estimated_stops = 0
            else:
                remaining_distance = (
                    estimated_route_distance_km - safe_start_range_km
                )

                estimated_stops = int(
                    math.ceil(remaining_distance / safe_after_charge_range_km)
                )

            average_arrival_percent = minimum_arrival_percent

            charge_needed_percent = max(
                target_battery_percent - average_arrival_percent,
                0
            )

            estimated_energy_per_stop_kwh = (
                battery_kwh * charge_needed_percent / 100
            )

            total_energy_added_kwh = (
                estimated_energy_per_stop_kwh * estimated_stops
            )

            estimated_cost_aud = (
                total_energy_added_kwh * electricity_price_per_kwh
            )

            if strategy_name == "Fastest Trip":
                assumed_effective_power_kw = 220
            elif strategy_name == "Conservative":
                assumed_effective_power_kw = 160
            else:
                assumed_effective_power_kw = 140

            estimated_charging_time_min = (
                total_energy_added_kwh / assumed_effective_power_kw
            ) * 60

            total_trip_time_hours = (
                estimated_drive_time_hours
                + estimated_charging_time_min / 60
            )

            comparison_rows.append({
                "weather": weather_name,
                "strategy": strategy_name,
                "adjusted_range_km": round(adjusted_range_km, 1),
                "estimated_stops": estimated_stops,
                "estimated_energy_added_kwh": round(total_energy_added_kwh, 1),
                "estimated_charging_time_min": round(estimated_charging_time_min, 1),
                "estimated_cost_aud": round(estimated_cost_aud, 2),
                "estimated_total_trip_time_hrs": round(total_trip_time_hours, 2)
            })

    comparison_df = pd.DataFrame(comparison_rows)

    best_time_row = comparison_df.sort_values(
        "estimated_total_trip_time_hrs",
        ascending=True
    ).iloc[0]

    cheapest_row = comparison_df.sort_values(
        "estimated_cost_aud",
        ascending=True
    ).iloc[0]

    fewest_stops_row = comparison_df.sort_values(
        "estimated_stops",
        ascending=True
    ).iloc[0]

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

    metric_col1.metric(
        "Estimated Route Distance",
        f"{round(estimated_route_distance_km, 1)} km"
    )

    metric_col2.metric(
        "Fastest Scenario",
        f"{best_time_row['weather']} / {best_time_row['strategy']}"
    )

    metric_col3.metric(
        "Cheapest Scenario",
        f"{cheapest_row['weather']} / {cheapest_row['strategy']}"
    )

    metric_col4.metric(
        "Fewest Stops Scenario",
        f"{fewest_stops_row['weather']} / {fewest_stops_row['strategy']}"
    )

    st.dataframe(
        comparison_df.sort_values(
            "estimated_total_trip_time_hrs",
            ascending=True
        ),
        use_container_width=True
    )

    st.subheader("Total Trip Time by Scenario")

    time_chart = comparison_df.copy()

    time_chart["scenario"] = (
        time_chart["weather"] + " | " + time_chart["strategy"]
    )

    st.bar_chart(
        time_chart.set_index("scenario")["estimated_total_trip_time_hrs"]
    )

    st.subheader("Estimated Charging Cost by Scenario")

    cost_chart = comparison_df.copy()

    cost_chart["scenario"] = (
        cost_chart["weather"] + " | " + cost_chart["strategy"]
    )

    st.bar_chart(
        cost_chart.set_index("scenario")["estimated_cost_aud"]
    )

    st.subheader("Estimated Stops by Scenario")

    stops_chart = comparison_df.copy()

    stops_chart["scenario"] = (
        stops_chart["weather"] + " | " + stops_chart["strategy"]
    )

    st.bar_chart(
        stops_chart.set_index("scenario")["estimated_stops"]
    )

    st.markdown("""
    ### How to interpret this

    **Route Comparison Mode** estimates how different weather and  charging strategies affect a trip.

    - **Normal weather** preserves the vehicle's nominal range.
    - **Cold weather, heavy rain and  extreme heat** reduce estimated usable range.
    - **Fastest Trip** assumes shorter charging sessions and  higher effective charging power.
    - **Conservative** assumes a safer battery target.
    - **Fewest Stops** assumes higher charging targets, which may reduce stop count but increase charging time.

    This is a scenario comparison tool, not a replacement for the full Real Route Optimizer.
    """)

elif page == "Demand  Forecast Model":

    st.title("📊 Demand  Forecast Model")

    st.markdown("""
    Forecast future EV charging pressure using estimated EV fleet growth, charging frequency assumptions,
    and  current charging infrastructure.

    This is a **scenario-based demand  model**, not a production-grade time-series model.
    """)

    st.caption(
        "The forecast uses estimated EV counts, state-level EV growth rates, public charging behaviour assumptions and  current charger infrastructure."
    )

    forecast_df = state_metrics.copy()

    forecast_df["estimated_ev_count"] = pd.to_numeric(
        forecast_df["estimated_ev_count"],
        errors="coerce"
    )

    forecast_df["annual_ev_growth_rate"] = pd.to_numeric(
        forecast_df["annual_ev_growth_rate"],
        errors="coerce"
    )

    forecast_df["total_stations"] = pd.to_numeric(
        forecast_df["total_stations"],
        errors="coerce"
    )

    forecast_df["population"] = pd.to_numeric(
        forecast_df["population"],
        errors="coerce"
    )

    forecast_df = forecast_df.dropna(
        subset=[
            "state_clean",
            "estimated_ev_count",
            "annual_ev_growth_rate",
            "total_stations"
        ]
    )

    st.subheader("Forecast Assumptions")

    national_ev_fleet = st.number_input(
        "Estimated Current Australian EV Fleet",
        min_value=100000,
        max_value=2000000,
        value=410000,
        step=10000
    )

    national_growth_rate = st.slider(
        "National Annual EV Fleet Growth Rate (%)",
        5,
        80,
        30
    )

    forecast_horizon = st.slider(
        "Forecast Horizon (Years)",
        1,
        10,
        3
    )

    public_charges_per_ev_month = st.slider(
        "Average Public Charges per EV per Month",
        1,
        10,
        4
    )

    charger_capacity_sessions_month = st.slider(
        "Estimated Sessions per Charger per Month",
        100,
        2000,
        800,
        step=50
    )

    st.caption(
        "Public charging frequency and  charger capacity are adjustable assumptions because actual charging behaviour varies by vehicle type, location, charger speed and  home charging access."
    )

    forecast_df["state_ev_share"] = (
        forecast_df["estimated_ev_count"]
        / forecast_df["estimated_ev_count"].sum()
    )

    forecast_df["estimated_current_evs"] = (
        forecast_df["state_ev_share"] * national_ev_fleet
    )

    forecast_df["state_growth_rate_used"] = (
        forecast_df["annual_ev_growth_rate"]
        .fillna(national_growth_rate)
        .clip(lower=0, upper=100)
    )

    forecast_df["forecast_evs"] = (
        forecast_df["estimated_current_evs"]
        * (
            1 + forecast_df["state_growth_rate_used"] / 100
        ) ** forecast_horizon
    )

    forecast_df["monthly_public_sessions"] = (
        forecast_df["forecast_evs"]
        * public_charges_per_ev_month
    )

    forecast_df["sessions_per_station_month"] = (
        forecast_df["monthly_public_sessions"]
        / forecast_df["total_stations"].replace(0, np.nan)
    )

    forecast_df["required_stations"] = (
        forecast_df["monthly_public_sessions"]
        / charger_capacity_sessions_month
    )

    forecast_df["additional_stations_needed"] = (
        forecast_df["required_stations"]
        - forecast_df["total_stations"]
    )

    forecast_df["additional_stations_needed"] = (
        forecast_df["additional_stations_needed"]
        .clip(lower=0)
    )

    max_pressure = forecast_df["sessions_per_station_month"].max()

    if max_pressure == 0 or pd.isna(max_pressure):
        forecast_df["demand_pressure_index"] = 0
    else:
        forecast_df["demand_pressure_index"] = (
            forecast_df["sessions_per_station_month"]
            / max_pressure
        ) * 100

    forecast_df["demand_pressure_index"] = (
        forecast_df["demand_pressure_index"]
        .fillna(0)
        .round(2)
    )

    def demand_pressure_label(score):
        if score >= 70:
            return "High Future Pressure"
        elif score >= 40:
            return "Moderate Future Pressure"
        return "Lower Future Pressure"

    forecast_df["demand_pressure_label"] = (
        forecast_df["demand_pressure_index"]
        .apply(demand_pressure_label)
    )

    forecast_df = forecast_df.sort_values(
        "demand_pressure_index",
        ascending=False
    )

    highest_pressure_state = forecast_df.iloc[0]

    forecast_national_evs = forecast_df["forecast_evs"].sum()

    total_additional_stations = forecast_df["additional_stations_needed"].sum()

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Forecast National EV Fleet",
        f"{int(round(forecast_national_evs, 0)):,}"
    )

    col2.metric(
        "Highest Pressure State",
        highest_pressure_state["state_clean"]
    )

    col3.metric(
        "Highest Pressure Index",
        round(highest_pressure_state["demand_pressure_index"], 1)
    )

    col4, col5 = st.columns(2)

    col4.metric(
        "Estimated Additional Stations Needed",
        f"{int(round(total_additional_stations, 0)):,}"
    )

    col5.metric(
        "Forecast Horizon",
        f"{forecast_horizon} years"
    )

    st.subheader("Forecast Demand  Pressure by State")

    st.dataframe(
        forecast_df[
            [
                "state_clean",
                "population",
                "total_stations",
                "estimated_current_evs",
                "state_growth_rate_used",
                "forecast_evs",
                "monthly_public_sessions",
                "sessions_per_station_month",
                "required_stations",
                "additional_stations_needed",
                "demand_pressure_index",
                "demand_pressure_label"
            ]
        ].round(2),
        use_container_width=True
    )

    st.subheader("Demand  Pressure Index")

    pressure_chart = forecast_df.sort_values(
        "demand_pressure_index",
        ascending=False
    )

    st.bar_chart(
        pressure_chart.set_index("state_clean")["demand_pressure_index"]
    )

    st.subheader("Forecast EV Fleet by State")

    ev_chart = forecast_df.sort_values(
        "forecast_evs",
        ascending=False
    )

    st.bar_chart(
        ev_chart.set_index("state_clean")["forecast_evs"]
    )

    st.subheader("Estimated Additional Stations Needed")

    station_gap_chart = forecast_df.sort_values(
        "additional_stations_needed",
        ascending=False
    )

    st.bar_chart(
        station_gap_chart.set_index("state_clean")["additional_stations_needed"]
    )

    st.markdown("""
    ### How to interpret this

    **Forecast EVs** estimates future EV fleet size using current estimated EV counts and  annual growth assumptions.

    **Monthly Public Sessions** estimates public charging demand  based on the assumed number of public charging sessions per EV per month.

    **Sessions per Station per Month** estimates pressure on existing charging infrastructure.

    **Demand  Pressure Index** scales the highest-pressure state to 100 and  compares other states against it.

    **Additional Stations Needed** estimates how many more charging stations may be needed to meet the assumed monthly charging demand  capacity.
    """)

    st.caption(
        "Limitations: This model does not include charger plug count, charger uptime, home charging availability, traffic flows, charger speed mix, or live utilisation. It is intended for scenario planning and  portfolio demonstration."
    )


elif page == "Real Route Optimizer":

    st.title("🛰️ Real Route Optimizer")

    st.markdown(
        "Generate a real driving route and identify high-quality EV charging stations near the route."
    )

    st.markdown(
        "Use **Major City Mode** for quick routes, or **Custom Place Mode** for suburb/place-level routing."
    )

    # -----------------------------
    # Helper functions
    # -----------------------------

    def geocode_place(place_name):
        url = "https://nominatim.openstreetmap.org/search"

        params = {
            "q": place_name,
            "format": "json",
            "limit": 1,
            "countrycodes": "au"
        }

        headers = {
            "User-Agent": "ChargeSenseEVPlatform/1.0"
        }

        try:
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=20
            )
        except requests.exceptions.RequestException as e:
            st.error("Could not connect to geocoding service.")
            st.write(str(e))
            return None

        if response.status_code != 200:
            st.error(f"Geocoding Error {response.status_code}")
            st.write(response.text)
            return None

        results = response.json()

        if len(results) == 0:
            return None

        result = results[0]

        return {
            "display_name": result.get("display_name", place_name),
            "longitude": float(result["lon"]),
            "latitude": float(result["lat"])
        }

    def simulated_availability(row):
        reliability = row.get("reliability_score", 0)

        if pd.isna(reliability):
            reliability = 0

        if reliability >= 70:
            return "Available"
        elif reliability >= 40:
            return "Busy"
        elif reliability > 0:
            return "Unknown"
        else:
            return "Offline"

    def amenity_score(row):
        text = " ".join(
            [
                str(row.get("station_name", "")),
                str(row.get("address", "")),
                str(row.get("town", ""))
            ]
        ).lower()

        high_amenity_keywords = [
            "service centre",
            "service center",
            "shopping centre",
            "shopping center",
            "7-eleven",
            "7 eleven",
            "woolworths",
            "coles",
            "mcdonald",
            "kfc",
            "hungry jack",
            "ampol",
            "bp",
            "shell",
            "caltex",
            "airport"
        ]

        medium_amenity_keywords = [
            "car park",
            "parking",
            "hotel",
            "motel",
            "club",
            "cafe",
            "restaurant",
            "mall",
            "plaza",
            "visitor centre",
            "visitor center"
        ]

        score = 0

        for keyword in high_amenity_keywords:
            if keyword in text:
                score += 30

        for keyword in medium_amenity_keywords:
            if keyword in text:
                score += 15

        return min(score, 100)

    def amenity_label(score):
        if score >= 60:
            return "High Amenity Stop"
        elif score >= 30:
            return "Medium Amenity Stop"
        return "Basic Stop"

    def estimate_wait_time_minutes(row, route_demand_level, trip_time_period):
        base_wait = 0

        availability_status = row.get("availability_status", "Unknown")
        reliability = row.get("reliability_score", 0)
        amenity = row.get("amenity_score", 0)
        charger_power = row.get("max_power_kw", 0)

        if pd.isna(reliability):
            reliability = 0

        if pd.isna(amenity):
            amenity = 0

        if pd.isna(charger_power):
            charger_power = 0

        if availability_status == "Available":
            base_wait += 3
        elif availability_status == "Busy":
            base_wait += 18
        elif availability_status == "Unknown":
            base_wait += 10
        else:
            base_wait += 25

        if route_demand_level == "Low":
            base_wait += 0
        elif route_demand_level == "Medium":
            base_wait += 8
        elif route_demand_level == "High":
            base_wait += 18

        if trip_time_period == "Off-peak":
            base_wait += 0
        elif trip_time_period == "Daytime":
            base_wait += 5
        elif trip_time_period == "Peak":
            base_wait += 12
        elif trip_time_period == "Holiday / Long Weekend":
            base_wait += 25

        if reliability >= 70:
            base_wait -= 4
        elif reliability < 30:
            base_wait += 8

        if amenity >= 60:
            base_wait += 5

        if charger_power >= 250:
            base_wait -= 3
        elif charger_power < 50:
            base_wait += 6

        return round(max(base_wait, 0), 1)

    def get_user_station_feedback(station_name):
        empty_feedback = {
            "user_review_count": 0,
            "avg_user_rating": None,
            "avg_reported_wait_time": None,
            "user_success_rate": None,
            "user_trust_score": None
        }

        if "station_reviews" not in st.session_state:
            return empty_feedback

        if len(st.session_state.station_reviews) == 0:
            return empty_feedback

        reviews_df = pd.DataFrame(st.session_state.station_reviews)

        station_reviews = reviews_df[
            reviews_df["station_name"].astype(str).str.lower()
            == str(station_name).lower()
        ].copy()

        if len(station_reviews) == 0:
            return empty_feedback

        avg_rating = station_reviews["user_rating"].mean()
        avg_wait_time = station_reviews["reported_wait_time_min"].mean()

        success_rate = (
            station_reviews["charger_worked"]
            .map(
                {
                    "Yes": 1,
                    "Partially": 0.5,
                    "No": 0
                }
            )
            .mean()
            * 100
        )

        recommend_rate = (
            station_reviews["would_recommend"]
            .map(
                {
                    "Yes": 1,
                    "Not sure": 0.5,
                    "No": 0
                }
            )
            .mean()
            * 100
        )

        user_trust_score = (
            avg_rating / 5 * 40
            + success_rate * 0.45
            + recommend_rate * 0.15
        )

        user_trust_score = round(
            min(max(user_trust_score, 0), 100),
            2
        )

        return {
            "user_review_count": len(station_reviews),
            "avg_user_rating": round(avg_rating, 2),
            "avg_reported_wait_time": round(avg_wait_time, 1),
            "user_success_rate": round(success_rate, 1),
            "user_trust_score": user_trust_score
        }

    def haversine_distance(lat1, lon1, lat2, lon2):
        radius_km = 6371

        lat1 = math.radians(lat1)
        lon1 = math.radians(lon1)
        lat2 = math.radians(lat2)
        lon2 = math.radians(lon2)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )

        c = 2 * math.asin(math.sqrt(a))

        return radius_km * c

    def min_distance_to_route(charger_lat, charger_lon, route_df):
        distances = route_df.apply(
            lambda row: haversine_distance(
                charger_lat,
                charger_lon,
                row["latitude"],
                row["longitude"]
            ),
            axis=1
        )

        return distances.min()

    # -----------------------------
    # City and EV setup
    # -----------------------------

    city_coordinates = {
        "Sydney": [151.2093, -33.8688],
        "Melbourne": [144.9631, -37.8136],
        "Brisbane": [153.0251, -27.4698],
        "Adelaide": [138.6007, -34.9285],
        "Perth": [115.8605, -31.9505],
        "Canberra": [149.1300, -35.2809],
        "Hobart": [147.3272, -42.8821],
        "Darwin": [130.8456, -12.4634],
        "Gold Coast": [153.4000, -28.0167],
        "Newcastle": [151.7817, -32.9283],
        "Wollongong": [150.8931, -34.4278],
        "Geelong": [144.3617, -38.1499]
    }

    ev_profiles = {
        "Tesla Model 3 RWD": {
            "battery_kwh": 60,
            "range_km": 513
        },
        "Tesla Model Y RWD": {
            "battery_kwh": 60,
            "range_km": 455
        },
        "BYD Atto 3": {
            "battery_kwh": 60.5,
            "range_km": 420
        },
        "BYD Seal": {
            "battery_kwh": 82.5,
            "range_km": 570
        },
        "Kia EV6": {
            "battery_kwh": 77.4,
            "range_km": 528
        },
        "Hyundai Ioniq 5": {
            "battery_kwh": 77.4,
            "range_km": 507
        },
        "MG4 Excite 51": {
            "battery_kwh": 51,
            "range_km": 350
        }
    }

    weather_multipliers = {
        "Normal": 1.00,
        "Cold Weather": 0.82,
        "Heavy Rain": 0.88,
        "Extreme Heat": 0.90
    }

    strategy_targets = {
        "Conservative": 80,
        "Fastest Trip": 60,
        "Fewest Stops": 90
    }

    # -----------------------------
    # Inputs
    # -----------------------------

    route_input_mode = st.radio(
        "Route Input Mode",
        ["Major City", "Custom Place"],
        horizontal=True
    )

    waypoint_inputs = []
    waypoint_coords = []
    waypoint_labels = []

    if route_input_mode == "Major City":
        cities = sorted(city_coordinates.keys())

        col1, col2 = st.columns(2)

        with col1:
            start_city = st.selectbox(
                "Start City",
                cities,
                index=cities.index("Sydney")
            )

        with col2:
            destination_city = st.selectbox(
                "Destination City",
                cities,
                index=cities.index("Melbourne")
            )

        start_coords = city_coordinates[start_city]
        end_coords = city_coordinates[destination_city]

        start_label = start_city
        destination_label = destination_city

    else:
        col1, col2 = st.columns(2)

        with col1:
            start_place = st.text_input(
                "Start Location",
                "Kensington NSW"
            )

        with col2:
            destination_place = st.text_input(
                "Destination",
                "Wollongong NSW"
            )

        if "route_stop_count" not in st.session_state:
            st.session_state.route_stop_count = 1

        add_route_stops = st.checkbox(
            "Add route stops / waypoints",
            value=False
        )

        waypoint_inputs = []

        if add_route_stops:
            st.markdown("#### Route Stops")

            st.caption(
                "Add stops in the order you want the route to follow, similar to Google Maps waypoints."
            )

            for i in range(st.session_state.route_stop_count):
                waypoint_value = st.text_input(
                    f"Stop {i + 1}",
                    "",
                    key=f"route_waypoint_{i}"
                )

                waypoint_inputs.append(waypoint_value)

            col_add, col_clear = st.columns(2)

            with col_add:
                if st.button("Add another stop"):
                    st.session_state.route_stop_count += 1
                    st.rerun()

            with col_clear:
                if st.button("Clear stops"):
                    st.session_state.route_stop_count = 1

                    for key in list(st.session_state.keys()):
                        if key.startswith("route_waypoint_"):
                            del st.session_state[key]

                    st.rerun()

        start_coords = None
        end_coords = None

        start_label = start_place
        destination_label = destination_place

    st.subheader("EV Trip Settings")

    selected_ev = st.selectbox(
        "Select EV Model",
        list(ev_profiles.keys()),
        index=list(ev_profiles.keys()).index("Tesla Model Y RWD")
    )

    battery_kwh = ev_profiles[selected_ev]["battery_kwh"]
    base_range_km = ev_profiles[selected_ev]["range_km"]

    st.info(
        f"{selected_ev}: {battery_kwh} kWh battery, approx. {base_range_km} km driving range."
    )

    charging_strategy = st.selectbox(
        "Charging Strategy",
        ["Conservative", "Fastest Trip", "Fewest Stops"]
    )

    weather_mode = st.selectbox(
        "Weather Conditions",
        ["Normal", "Cold Weather", "Heavy Rain", "Extreme Heat"]
    )

    col1, col2 = st.columns(2)

    with col1:
        max_distance_from_route_km = st.slider(
            "Maximum Distance from Route (km)",
            5,
            50,
            15
        )

    with col2:
        safety_buffer_km = st.slider(
            "Safety Buffer Before Charging (km)",
            10,
            120,
            50
        )

    col1, col2, col3 = st.columns(3)

    with col1:
        starting_battery_percent = st.slider(
            "Starting Battery (%)",
            10,
            100,
            90
        )

    with col2:
        minimum_arrival_percent = st.slider(
            "Minimum Arrival Battery at Stop (%)",
            5,
            50,
            20
        )

    with col3:
        target_battery_percent = strategy_targets[charging_strategy]
        st.metric(
            "Target Battery Strategy",
            f"{target_battery_percent}%"
        )

    st.subheader("Demand & Wait Time Settings")

    col1, col2 = st.columns(2)

    with col1:
        route_demand_level = st.selectbox(
            "Expected Route Demand",
            ["Low", "Medium", "High"],
            index=1
        )

    with col2:
        trip_time_period = st.selectbox(
            "Trip Time Period",
            [
                "Off-peak",
                "Daytime",
                "Peak",
                "Holiday / Long Weekend"
            ],
            index=1
        )

    st.caption(
        "Wait time is currently estimated from demand level, time period, simulated availability, reliability, charger speed and amenity attractiveness. It is not live queue data."
    )

    st.subheader("Cost Settings")

    electricity_price_per_kwh = st.slider(
        "Estimated Public Charging Price ($/kWh)",
        0.20,
        1.20,
        0.65,
        0.05
    )

    generate_route = st.button("Generate Real Route")

    # -----------------------------
    # Route generation
    # -----------------------------

    if generate_route:

        waypoint_coords = []
        waypoint_labels = []

        if route_input_mode == "Custom Place":
            start_geo = geocode_place(start_place)
            destination_geo = geocode_place(destination_place)

            if start_geo is None:
                st.error("Could not find the start location.")
                st.stop()

            if destination_geo is None:
                st.error("Could not find the destination location.")
                st.stop()

            start_coords = [
                start_geo["longitude"],
                start_geo["latitude"]
            ]

            end_coords = [
                destination_geo["longitude"],
                destination_geo["latitude"]
            ]

            start_label = start_geo["display_name"]
            destination_label = destination_geo["display_name"]

            st.info(f"Start matched to: {start_label}")

            cleaned_waypoints = [
                waypoint.strip()
                for waypoint in waypoint_inputs
                if waypoint.strip() != ""
            ]

            for waypoint in cleaned_waypoints:
                waypoint_geo = geocode_place(waypoint)

                if waypoint_geo is None:
                    st.warning(
                        f"Could not find route stop: {waypoint}. This stop will be skipped."
                    )
                else:
                    waypoint_coords.append(
                        [
                            waypoint_geo["longitude"],
                            waypoint_geo["latitude"]
                        ]
                    )

                    waypoint_labels.append(
                        waypoint_geo["display_name"]
                    )

                    st.info(
                        f"Route stop matched to: {waypoint_geo['display_name']}"
                    )

            st.info(f"Destination matched to: {destination_label}")

        if start_coords == end_coords:
            st.warning("Start and destination cannot be the same.")
            st.stop()

        route_points = [
            start_coords
        ]

        if route_input_mode == "Custom Place" and len(waypoint_coords) > 0:
            route_points.extend(waypoint_coords)

        route_points.append(end_coords)

        osrm_coordinate_string = ";".join(
            [
                f"{coords[0]},{coords[1]}"
                for coords in route_points
            ]
        )

        url = (
            f"https://router.project-osrm.org/route/v1/driving/"
            f"{osrm_coordinate_string}"
        )

        params = {
            "overview": "full",
            "geometries": "geojson"
        }

        try:
            response = requests.get(
                url,
                params=params,
                timeout=30
            )
        except requests.exceptions.RequestException as e:
            st.error("Could not connect to OSRM routing service.")
            st.write(str(e))
            st.stop()

        if response.status_code != 200:
            st.error(f"Routing Error {response.status_code}")
            st.write(response.text)
            st.stop()

        route_data = response.json()

        if "routes" not in route_data or len(route_data["routes"]) == 0:
            st.error("No route found.")
            st.stop()

        route = route_data["routes"][0]

        route_coords = route["geometry"]["coordinates"]

        route_df = pd.DataFrame(
            route_coords,
            columns=["longitude", "latitude"]
        )

        distance_km = route["distance"] / 1000
        duration_hours = route["duration"] / 3600

        weather_multiplier = weather_multipliers[weather_mode]
        adjusted_range_km = base_range_km * weather_multiplier

        if route_input_mode == "Custom Place" and len(waypoint_labels) > 0:
            waypoint_summary = " → ".join(waypoint_labels)

            st.success(
                f"Route generated from {start_label} → {waypoint_summary} → {destination_label}"
            )
        else:
            st.success(
                f"Route generated from {start_label} to {destination_label}"
            )

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Route Distance",
            f"{round(distance_km, 1)} km"
        )

        col2.metric(
            "Estimated Drive Time",
            f"{round(duration_hours, 1)} hrs"
        )

        col3.metric(
            "Adjusted EV Range",
            f"{round(adjusted_range_km, 1)} km"
        )

        # -----------------------------
        # Prepare route charger data
        # -----------------------------

        route_map_df = ocm_df.copy()

        route_map_df["latitude"] = pd.to_numeric(
            route_map_df["latitude"],
            errors="coerce"
        )

        route_map_df["longitude"] = pd.to_numeric(
            route_map_df["longitude"],
            errors="coerce"
        )

        route_map_df["max_power_kw"] = pd.to_numeric(
            route_map_df["max_power_kw"],
            errors="coerce"
        )

        route_map_df["reliability_score"] = pd.to_numeric(
            route_map_df["reliability_score"],
            errors="coerce"
        )

        route_map_df = route_map_df.dropna(
            subset=[
                "latitude",
                "longitude"
            ]
        )

        sampled_route_df = route_df.iloc[
            ::max(1, int(len(route_df) / 250))
        ].copy()

        route_map_df["distance_to_route_km"] = route_map_df.apply(
            lambda row: min_distance_to_route(
                row["latitude"],
                row["longitude"],
                sampled_route_df
            ),
            axis=1
        )

        near_route_df = route_map_df[
            route_map_df["distance_to_route_km"] <= max_distance_from_route_km
        ].copy()

        if len(near_route_df) == 0:
            st.warning("No chargers found within the selected route distance.")
            st.stop()

        st.info(
            f"Found {len(near_route_df)} chargers within {max_distance_from_route_km} km of the route."
        )

        near_route_df["availability_status"] = near_route_df.apply(
            simulated_availability,
            axis=1
        )

        availability_weight = {
            "Available": 100,
            "Busy": 30,
            "Unknown": 0,
            "Offline": -200
        }

        near_route_df["availability_score"] = (
            near_route_df["availability_status"].map(availability_weight)
        )

        near_route_df["amenity_score"] = near_route_df.apply(
            amenity_score,
            axis=1
        )

        near_route_df["amenity_label"] = (
            near_route_df["amenity_score"].apply(amenity_label)
        )

        near_route_df["route_score"] = (
            near_route_df["max_power_kw"].fillna(0) * 0.6
            + near_route_df["reliability_score"].fillna(0) * 1.4
        )

        near_route_df["route_recommendation_score"] = (
            near_route_df["route_score"].fillna(0)
            + near_route_df["availability_score"].fillna(0)
            + near_route_df["amenity_score"].fillna(0)
            - near_route_df["distance_to_route_km"].fillna(0) * 10
        )

        recommended_stops = near_route_df.sort_values(
            "route_recommendation_score",
            ascending=False
        ).head(10).copy()

        feedback_metrics = recommended_stops["station_name"].apply(
            get_user_station_feedback
        )

        feedback_df = pd.DataFrame(list(feedback_metrics))

        recommended_stops = recommended_stops.reset_index(drop=True)
        feedback_df = feedback_df.reset_index(drop=True)

        recommended_stops = pd.concat(
            [
                recommended_stops,
                feedback_df
            ],
            axis=1
        )

        recommended_stops["user_feedback_label"] = recommended_stops["user_review_count"].apply(
            lambda x: "User feedback available" if x > 0 else "No session feedback"
        )

        # -----------------------------
        # Corridor risk score
        # -----------------------------

        chargers_near_route = len(near_route_df)
        chargers_per_100_km = chargers_near_route / max(distance_km / 100, 1)
        avg_reliability = near_route_df["reliability_score"].fillna(0).mean()
        avg_availability_score = near_route_df["availability_score"].fillna(0).mean()

        coverage_risk = max(0, 100 - min(chargers_per_100_km * 4, 100))
        reliability_risk = max(0, 100 - avg_reliability)
        availability_risk = max(0, 100 - max(avg_availability_score, 0))

        corridor_risk_score = (
            coverage_risk * 0.35
            + reliability_risk * 0.40
            + availability_risk * 0.25
        )

        corridor_risk_score = round(
            min(max(corridor_risk_score, 0), 100),
            2
        )

        if corridor_risk_score >= 70:
            corridor_risk_label = "High Risk"
        elif corridor_risk_score >= 40:
            corridor_risk_label = "Medium Risk"
        else:
            corridor_risk_label = "Lower Risk"

        st.subheader("Corridor Risk Score")

        st.markdown("""
        The Corridor Risk Score estimates how risky an EV route is based on charging infrastructure along the selected route.

        It considers:

        - how many chargers are near the route
        - average charger reliability
        - estimated availability
        - charger coverage along the route
        - whether the route has enough nearby charging options

        A higher score means the route may have higher charging risk, weaker infrastructure coverage, or lower charger trust.
        """)

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Corridor Risk", corridor_risk_label)
        col2.metric("Risk Score", corridor_risk_score)
        col3.metric("Chargers Near Route", chargers_near_route)
        col4.metric("Chargers / 100 km", round(chargers_per_100_km, 1))

        col5, col6 = st.columns(2)

        col5.metric("Avg Reliability", round(avg_reliability, 1))
        col6.metric("Avg Availability Score", round(avg_availability_score, 1))

        st.caption(
            "Interpretation: A route can have many chargers but still show medium or high corridor risk if reliability, data freshness, or estimated availability is weak."
        )

        st.caption(
            "Corridor risk uses public charger data, reliability indicators, simulated availability and route coverage. It is a planning estimate, not live operational risk."
        )

        # -----------------------------
        # Recommended chargers table
        # -----------------------------

        st.subheader("Recommended Charging Stops Near Route")

        st.caption(
            "Availability status, wait time and queue pressure are estimated from public metadata and scenario assumptions. User review fields are session-based only in this prototype."
        )

        recommended_stops["estimated_wait_time_min"] = recommended_stops.apply(
            lambda row: estimate_wait_time_minutes(
                row,
                route_demand_level,
                trip_time_period
            ),
            axis=1
        )

        st.dataframe(
            recommended_stops[
                [
                    "station_name",
                    "town",
                    "state_clean",
                    "max_power_kw",
                    "reliability_score",
                    "availability_status",
                    "estimated_wait_time_min",
                    "user_review_count",
                    "avg_user_rating",
                    "avg_reported_wait_time",
                    "user_success_rate",
                    "user_trust_score",
                    "user_feedback_label",
                    "availability_score",
                    "amenity_label",
                    "amenity_score",
                    "route_score",
                    "route_recommendation_score",
                    "distance_to_route_km"
                ]
            ],
            use_container_width=True
        )

        # -----------------------------
        # Charging stop sequence
        # -----------------------------

        st.subheader("Suggested Charging Stop Sequence")

        usable_start_range_km = adjusted_range_km * (
            starting_battery_percent / 100
        )

        safe_start_range_km = max(
            usable_start_range_km - safety_buffer_km,
            1
        )

        usable_after_charge_range_km = adjusted_range_km * (
            (target_battery_percent - minimum_arrival_percent) / 100
        )

        safe_after_charge_range_km = max(
            usable_after_charge_range_km - safety_buffer_km,
            1
        )

        charging_sequence = []
        used_station_names = set()
        battery_warning_triggered = False

        current_battery_percent = starting_battery_percent
        previous_distance_km = 0
        stop_number = 1

        if distance_km <= safe_start_range_km:
            charging_sequence = []

        else:
            target_distance = safe_start_range_km

            while target_distance < distance_km:

                route_index = min(
                    int((target_distance / distance_km) * (len(route_df) - 1)),
                    len(route_df) - 1
                )

                target_lat = route_df.iloc[route_index]["latitude"]
                target_lon = route_df.iloc[route_index]["longitude"]

                candidate_stops = near_route_df.copy()

                candidate_stops["distance_to_target_km"] = candidate_stops.apply(
                    lambda row: haversine_distance(
                        row["latitude"],
                        row["longitude"],
                        target_lat,
                        target_lon
                    ),
                    axis=1
                )

                candidate_stops = candidate_stops[
                    ~candidate_stops["station_name"].isin(used_station_names)
                ].copy()

                if len(candidate_stops) == 0:
                    battery_warning_triggered = True
                    break

                best_stop = (
                    candidate_stops
                    .sort_values(
                        [
                            "distance_to_target_km",
                            "route_recommendation_score"
                        ],
                        ascending=[True, False]
                    )
                    .iloc[0]
                )

                used_station_names.add(best_stop["station_name"])

                leg_distance_km = target_distance - previous_distance_km

                battery_used_percent = (
                    leg_distance_km / adjusted_range_km
                ) * 100

                arrival_battery_percent = max(
                    current_battery_percent - battery_used_percent,
                    0
                )

                if arrival_battery_percent < minimum_arrival_percent:
                    battery_warning_triggered = True

                charge_needed_percent = max(
                    target_battery_percent - arrival_battery_percent,
                    0
                )

                departure_battery_percent = min(
                    arrival_battery_percent + charge_needed_percent,
                    100
                )

                energy_needed_kwh = (
                    battery_kwh * charge_needed_percent / 100
                )

                charger_power_kw = max(
                    float(best_stop["max_power_kw"])
                    if pd.notna(best_stop["max_power_kw"])
                    else 1,
                    1
                )

                effective_charger_power_kw = charger_power_kw

                if departure_battery_percent >= 80:
                    effective_charger_power_kw *= 0.55
                elif departure_battery_percent >= 60:
                    effective_charger_power_kw *= 0.75

                effective_charger_power_kw = max(
                    effective_charger_power_kw,
                    25
                )

                estimated_charge_time_min = (
                    energy_needed_kwh / effective_charger_power_kw
                ) * 60

                estimated_wait_time_min = estimate_wait_time_minutes(
                    best_stop,
                    route_demand_level,
                    trip_time_period
                )

                total_stop_time_min = (
                    estimated_wait_time_min + estimated_charge_time_min
                )

                estimated_charge_cost_aud = (
                    energy_needed_kwh * electricity_price_per_kwh
                )

                feedback_info = get_user_station_feedback(
                    best_stop["station_name"]
                )

                charging_sequence.append({
                    "stop_number": stop_number,
                    "target_distance_km": round(target_distance, 1),
                    "station_name": best_stop["station_name"],
                    "town": best_stop.get("town", ""),
                    "state_clean": best_stop.get("state_clean", ""),
                    "max_power_kw": best_stop.get("max_power_kw", 0),
                    "reliability_score": best_stop.get("reliability_score", 0),
                    "availability_status": best_stop.get("availability_status", "Unknown"),
                    "availability_score": best_stop.get("availability_score", 0),
                    "amenity_label": best_stop.get("amenity_label", "Basic Stop"),
                    "amenity_score": best_stop.get("amenity_score", 0),
                    "route_score": best_stop.get("route_score", 0),
                    "arrival_battery_%": round(arrival_battery_percent, 1),
                    "departure_battery_%": round(departure_battery_percent, 1),
                    "estimated_wait_time_min": round(estimated_wait_time_min, 1),
                    "estimated_charge_kwh": round(energy_needed_kwh, 1),
                    "estimated_charge_time_min": round(estimated_charge_time_min, 1),
                    "total_stop_time_min": round(total_stop_time_min, 1),
                    "estimated_charge_cost_aud": round(estimated_charge_cost_aud, 2),
                    "distance_to_target_km": round(best_stop["distance_to_target_km"], 1),
                    "user_review_count": feedback_info["user_review_count"],
                    "avg_user_rating": feedback_info["avg_user_rating"],
                    "avg_reported_wait_time": feedback_info["avg_reported_wait_time"],
                    "user_success_rate": feedback_info["user_success_rate"],
                    "user_trust_score": feedback_info["user_trust_score"]
                })

                current_battery_percent = departure_battery_percent
                previous_distance_km = target_distance
                target_distance += safe_after_charge_range_km
                stop_number += 1

                if stop_number > 20:
                    battery_warning_triggered = True
                    break

        if battery_warning_triggered:
            low_arrival_stops = [
                stop for stop in charging_sequence
                if stop.get("arrival_battery_%", 100) < minimum_arrival_percent
            ]

            if len(low_arrival_stops) > 0:
                affected_stops = ", ".join(
                    [
                        f"Stop {int(stop.get('stop_number', 0))} "
                        f"({stop.get('station_name', 'Unknown Station')}: "
                        f"{round(stop.get('arrival_battery_%', 0), 1)}%)"
                        for stop in low_arrival_stops
                    ]
                )

                st.warning(
                    f"Battery may fall below your selected minimum arrival battery of "
                    f"{minimum_arrival_percent}% at: {affected_stops}. "
                    f"Consider increasing starting battery, reducing the safety buffer, "
                    f"choosing a longer-range EV, or switching to a more conservative charging strategy."
                )

            else:
                st.warning(
                    "The route planner detected a high-risk charging scenario. "
                    "This may be because the route requires too many charging stops, charger spacing is weak, "
                    "or the selected EV/range settings are too restrictive. "
                    "Consider increasing starting battery, using a longer-range EV, reducing the safety buffer, "
                    "or choosing a more conservative charging strategy."
                )

        if len(charging_sequence) == 0:
            st.success(
                "No charging stop required based on selected EV range."
            )

            total_charging_time_min = 0
            total_wait_time_min = 0
            total_stop_time_min = 0
            total_charging_cost_aud = 0
            total_energy_added_kwh = 0
            total_trip_time_hours = duration_hours
            cost_per_100_km = 0

        else:
            sequence_df = pd.DataFrame(charging_sequence)

            total_charging_time_min = sequence_df[
                "estimated_charge_time_min"
            ].sum()

            total_wait_time_min = sequence_df[
                "estimated_wait_time_min"
            ].sum()

            total_stop_time_min = sequence_df[
                "total_stop_time_min"
            ].sum()

            total_charging_cost_aud = sequence_df[
                "estimated_charge_cost_aud"
            ].sum()

            total_energy_added_kwh = sequence_df[
                "estimated_charge_kwh"
            ].sum()

            total_trip_time_hours = (
                duration_hours + total_stop_time_min / 60
            )

            cost_per_100_km = (
                total_charging_cost_aud / distance_km
            ) * 100

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Charging Stops",
                len(sequence_df)
            )

            col2.metric(
                "Total Wait Time",
                f"{round(total_wait_time_min, 1)} min"
            )

            col3.metric(
                "Total Charging Time",
                f"{round(total_charging_time_min, 1)} min"
            )

            col4, col5, col6 = st.columns(3)

            col4.metric(
                "Total Stop Time",
                f"{round(total_stop_time_min, 1)} min"
            )

            col5.metric(
                "Total Trip Time",
                f"{round(total_trip_time_hours, 1)} hrs"
            )

            col6.metric(
                "Charging Cost",
                f"${round(total_charging_cost_aud, 2)}"
            )

            st.metric(
                "Cost / 100 km",
                f"${round(cost_per_100_km, 2)}"
            )

            st.dataframe(
                sequence_df,
                use_container_width=True
            )

            st.subheader("Why These Stops Were Recommended")

            for _, stop in sequence_df.iterrows():

                if pd.notna(stop.get("user_trust_score", None)):
                    user_feedback_text = (
                        f"- User feedback: **{int(stop['user_review_count'])} review(s)**, "
                        f"average rating **{stop['avg_user_rating']}/5**, "
                        f"user trust score **{stop['user_trust_score']}/100**"
                    )
                else:
                    user_feedback_text = "- User feedback: **No session feedback available yet**"

                st.markdown(
                    f"""
                    **Stop {int(stop["stop_number"])}: {stop["station_name"]}**

                    Recommended because:

                    - Charger speed: **{stop["max_power_kw"]} kW**
                    - Availability estimate: **{stop["availability_status"]}**
                    - Estimated wait before charging: **{stop["estimated_wait_time_min"]} minutes**
                    - Estimated charging time: **{stop["estimated_charge_time_min"]} minutes**
                    - Total estimated stop time: **{stop["total_stop_time_min"]} minutes**
                    {user_feedback_text}
                    - Amenity type: **{stop["amenity_label"]}**
                    - Expected arrival battery: **{stop["arrival_battery_%"]}%**
                    - Expected departure battery: **{stop["departure_battery_%"]}%**
                    - Estimated charging cost: **${stop["estimated_charge_cost_aud"]}**
                    - Detour from target point: **{stop["distance_to_target_km"]} km**
                    """
                )

            csv_sequence = sequence_df.to_csv(index=False)

            st.download_button(
                "Download Stop Sequence CSV",
                csv_sequence,
                file_name="chargesense_stop_sequence.csv",
                mime="text/csv"
            )

        # -----------------------------
        # Trip summary
        # -----------------------------

        st.subheader("Trip Plan Summary")

        if len(charging_sequence) == 0:
            charging_stops_count = 0
        else:
            charging_stops_count = len(sequence_df)

        trip_summary = f"""
Route: {start_label} → {destination_label}
Waypoints: {", ".join(waypoint_labels) if route_input_mode == "Custom Place" and len(waypoint_labels) > 0 else "None"}
EV: {selected_ev}
Distance: {round(distance_km, 1)} km
Drive Time: {round(duration_hours, 1)} hrs
Adjusted EV Range: {round(adjusted_range_km, 1)} km
Weather: {weather_mode}
Strategy: {charging_strategy}
Route Demand Level: {route_demand_level}
Trip Time Period: {trip_time_period}
Charging Stops: {charging_stops_count}
Total Wait Time: {round(total_wait_time_min, 1)} min
Total Charging Time: {round(total_charging_time_min, 1)} min
Total Stop Time: {round(total_stop_time_min, 1)} min
Estimated Energy Added: {round(total_energy_added_kwh, 1)} kWh
Estimated Charging Cost: ${round(total_charging_cost_aud, 2)}
Estimated Cost per 100 km: ${round(cost_per_100_km, 2)}
Estimated Total Trip Time: {round(total_trip_time_hours, 1)} hrs
Charging Price Used: ${electricity_price_per_kwh}/kWh
Corridor Risk: {corridor_risk_label}
Corridor Risk Score: {corridor_risk_score}
"""

        st.code(trip_summary)

        st.download_button(
            "Download Trip Plan",
            trip_summary,
            file_name="chargesense_trip_plan.txt"
        )

        # -----------------------------
        # Map
        # -----------------------------

        st.subheader("Route Map with Recommended Chargers")

        recommended_stops["plot_size"] = (
            recommended_stops["max_power_kw"]
            .fillna(1)
            .clip(lower=5, upper=350)
        )

        fig = px.scatter_mapbox(
            recommended_stops,
            lat="latitude",
            lon="longitude",
            hover_name="station_name",
            hover_data=[
                "town",
                "state_clean",
                "max_power_kw",
                "reliability_score",
                "availability_status",
                "estimated_wait_time_min",
                "user_review_count",
                "avg_user_rating",
                "user_trust_score",
                "amenity_label",
                "route_recommendation_score",
                "distance_to_route_km"
            ],
            size="plot_size",
            color="route_recommendation_score",
            zoom=6,
            height=650
        )

        fig.add_scattermapbox(
            lat=route_df["latitude"],
            lon=route_df["longitude"],
            mode="lines",
            line=dict(
                width=4,
                color="blue"
            ),
            name="Driving Route"
        )

        fig.update_layout(
            mapbox_style="open-street-map",
            margin=dict(
                l=0,
                r=0,
                t=0,
                b=0
            )
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )



elif page == "Data Reality & Production Needs":

    st.title("🧾 Data Reality & Production Needs")

    st.markdown("""
    EVAtlas is currently a working prototype that combines public datasets,
    routing APIs, derived metrics and scenario-based assumptions.

    This page explains what is currently based on real public data, what is estimated,
    and what additional data would be required to make the platform more production-ready.
    """)

    # -----------------------------------
    # CURRENT DATA USED
    # -----------------------------------

    st.subheader("Current Data Used")

    current_data = pd.DataFrame(
        [
            {
                "Data Area": "Charger locations",
                "Current Source": "OpenChargeMap / public charger datasets",
                "Current Status": "Real public data",
                "Limitations": "Metadata quality and completeness can vary"
            },
            {
                "Data Area": "Route distance and geometry",
                "Current Source": "OSRM routing API",
                "Current Status": "Real road routing",
                "Limitations": "Does not include live traffic or road closures"
            },
            {
                "Data Area": "Custom place search",
                "Current Source": "Nominatim geocoding",
                "Current Status": "Real geocoding API",
                "Limitations": "Location matching may not always be perfect"
            },
            {
                "Data Area": "EV registrations / market signals",
                "Current Source": "AAA / BITRE-derived inputs",
                "Current Status": "Public / derived data",
                "Limitations": "Currently state-level, not full suburb or LGA detail"
            },
            {
                "Data Area": "Vehicle range and battery specs",
                "Current Source": "Hard-coded EV profile assumptions",
                "Current Status": "Prototype assumptions",
                "Limitations": "Should be replaced with a maintained vehicle database"
            },
            {
                "Data Area": "Weather impact",
                "Current Source": "Scenario multipliers",
                "Current Status": "Estimated",
                "Limitations": "Not connected to live route weather"
            },
            {
                "Data Area": "Availability",
                "Current Source": "Reliability / data freshness proxy",
                "Current Status": "Simulated",
                "Limitations": "Not live charger occupancy"
            },
            {
                "Data Area": "Amenities",
                "Current Source": "Keyword-based station metadata scoring",
                "Current Status": "Estimated",
                "Limitations": "Not confirmed through live POI data"
            },
            {
                "Data Area": "Charging price",
                "Current Source": "User-selected price assumption",
                "Current Status": "Scenario estimate",
                "Limitations": "Not station-specific or operator-specific live pricing"
            }
        ]
    )

    st.dataframe(
        current_data,
        use_container_width=True
    )

    st.caption(
        "This table separates real public data from prototype assumptions and estimated features."
    )

    # -----------------------------------
    # PRODUCTION DATA NEEDED
    # -----------------------------------

    st.subheader("Additional Data Needed for a More Production-Ready Version")

    production_data = pd.DataFrame(
        [
            {
                "Data Needed": "Live charger availability",
                "Why It Matters": "Shows whether chargers are available, occupied, offline, or faulty in real time",
                "Possible Source": "Charging operators, OCPI feeds, roaming platforms"
            },
            {
                "Data Needed": "Station-level pricing",
                "Why It Matters": "Allows exact route cost instead of estimated cost",
                "Possible Source": "Charging operators, OCPI tariff feeds"
            },
            {
                "Data Needed": "Uptime and outage history",
                "Why It Matters": "Improves reliability scoring and corridor risk accuracy",
                "Possible Source": "Charging operators, maintenance records"
            },
            {
                "Data Needed": "Delivered charging power",
                "Why It Matters": "Improves charging time estimates beyond advertised max kW",
                "Possible Source": "Charging sessions, operator telemetry"
            },
            {
                "Data Needed": "Vehicle charging curves",
                "Why It Matters": "Improves charging time estimates by vehicle and battery percentage",
                "Possible Source": "EV databases, manufacturer data, testing datasets"
            },
            {
                "Data Needed": "Live weather and traffic",
                "Why It Matters": "Improves range, travel time and route risk estimates",
                "Possible Source": "Weather APIs, Google Maps, HERE, TomTom"
            },
            {
                "Data Needed": "POI and amenities near chargers",
                "Why It Matters": "Confirms toilets, food, cafes, parking, safety and opening hours",
                "Possible Source": "Google Places, OpenStreetMap POI data"
            },
            {
                "Data Needed": "EV registrations by LGA/postcode",
                "Why It Matters": "Supports local infrastructure planning and site selection",
                "Possible Source": "Government registration datasets, NEVDIS-derived sources"
            },
            {
                "Data Needed": "Traffic volume and corridor demand",
                "Why It Matters": "Supports charger placement and investment prioritisation",
                "Possible Source": "TfNSW traffic counts, transport datasets"
            },
            {
                "Data Needed": "Grid capacity and site feasibility",
                "Why It Matters": "Determines whether chargers can actually be installed at candidate sites",
                "Possible Source": "DNSPs, councils, grid operators"
            },
            {
                "Data Needed": "Fleet depot and route data",
                "Why It Matters": "Enables real fleet electrification planning",
                "Possible Source": "Fleet customers"
            }
        ]
    )

    st.dataframe(
        production_data,
        use_container_width=True
    )

    st.caption(
        "This table identifies the next data layers that could improve commercial accuracy, validation and customer value."
    )

    # -----------------------------------
    # PROTOTYPE VS PRODUCTION READINESS
    # -----------------------------------

    st.subheader("Prototype vs Production Readiness")

    readiness_data = pd.DataFrame(
        [
            {
                "Feature": "Real Route Optimizer",
                "Prototype Status": "Working",
                "Production Gap": "Needs live traffic, live charger status, real pricing and vehicle charging curves"
            },
            {
                "Feature": "Corridor Risk Score",
                "Prototype Status": "Working estimate",
                "Production Gap": "Needs outage history, live status, queue data and station uptime"
            },
            {
                "Feature": "Demand Forecast Model",
                "Prototype Status": "Scenario-based",
                "Production Gap": "Needs granular EV registrations, charger utilisation, and local demand data"
            },
            {
                "Feature": "Fleet Route Upload",
                "Prototype Status": "Working high-level model",
                "Production Gap": "Needs depot addresses, route schedules, telematics, and real operating constraints"
            },
            {
                "Feature": "Operator Performance",
                "Prototype Status": "Public metadata benchmark",
                "Production Gap": "Needs confirmed operator mapping, session success rates, uptime, and delivered power"
            },
            {
                "Feature": "Amenity Score",
                "Prototype Status": "Keyword estimate",
                "Production Gap": "Needs Google Places or OpenStreetMap POI enrichment"
            },
            {
                "Feature": "Availability Layer",
                "Prototype Status": "Simulated",
                "Production Gap": "Needs live operator APIs or OCPI integration"
            },
            {
                "Feature": "Investment Priority Ranking",
                "Prototype Status": "State-level planning estimate",
                "Production Gap": "Needs local EV registrations, traffic demand, land-use data, and grid feasibility"
            }
        ]
    )

    st.dataframe(
        readiness_data,
        use_container_width=True
    )

    # -----------------------------------
    # KEY VALIDATION QUESTION
    # -----------------------------------

    st.subheader("Key Validation Question")

    st.info(
        "The next stage is not simply adding more features. The key question is which missing data layer matters most to the first customer segment: live availability for drivers, route/depot data for fleets, or local demand and site feasibility data for councils."
    )

    st.markdown("""
    ### How this helps the product roadmap

    This page separates the current prototype from a production-grade platform.

    It shows that EVAtlas already demonstrates the workflow using public data and assumptions,
    while also identifying the specific data partnerships and integrations that could improve commercial accuracy.

    For mentorship and customer discovery, this helps frame the next question:

    **Which missing data layer is essential for validation, and which can wait until later?**
    """)

    st.caption(
        "EVAtlas is currently a prototype. The goal is to test the workflow, customer problem, and data value before attempting production-level integrations."
    )

elif page == "Operator Performance":

    st.title("🏢 Operator Performance Dashboard")

    st.markdown("""
    Benchmark charging operators based on network size, charger speed, ultra-fast coverage,
    reliability indicators, availability estimates, and amenity quality.

    This view helps identify which operators appear strongest from an infrastructure and user-experience perspective.
    """)

    st.caption(
        "Operator names are estimated from station names using keyword matching. Scores are based on available public metadata, not confirmed operator-provided performance data."
    )

    operator_df = ocm_df.copy()

    operator_df["max_power_kw"] = pd.to_numeric(
        operator_df["max_power_kw"],
        errors="coerce"
    )

    operator_df["reliability_score"] = pd.to_numeric(
        operator_df["reliability_score"],
        errors="coerce"
    )

    def identify_operator(station_name):
        name = str(station_name).lower()

        if "tesla" in name:
            return "Tesla"
        elif "chargefox" in name:
            return "Chargefox"
        elif "evie" in name:
            return "Evie"
        elif "nrma" in name:
            return "NRMA"
        elif "ampol" in name:
            return "Ampol"
        elif "shell" in name:
            return "Shell Recharge"
        elif "bp" in name:
            return "BP Pulse"
        elif "jolt" in name:
            return "JOLT"
        elif "chargepoint" in name:
            return "ChargePoint"
        elif "racv" in name:
            return "RACV"
        elif "woolworths" in name:
            return "Woolworths"
        elif "7-eleven" in name or "7 eleven" in name:
            return "7-Eleven"
        else:
            return "Other / Unknown"

    def operator_availability(row):
        reliability = row.get("reliability_score", 0)

        if pd.isna(reliability):
            reliability = 0

        if reliability >= 70:
            return "Available"
        elif reliability >= 40:
            return "Busy"
        elif reliability > 0:
            return "Unknown"
        else:
            return "Offline"

    def operator_amenity_score(row):
        text = " ".join(
            [
                str(row.get("station_name", "")),
                str(row.get("address", "")),
                str(row.get("town", ""))
            ]
        ).lower()

        high_amenity_keywords = [
            "service centre",
            "service center",
            "shopping centre",
            "shopping center",
            "7-eleven",
            "7 eleven",
            "woolworths",
            "coles",
            "mcdonald",
            "kfc",
            "hungry jack",
            "ampol",
            "bp",
            "shell",
            "caltex",
            "airport"
        ]

        medium_amenity_keywords = [
            "car park",
            "parking",
            "hotel",
            "motel",
            "club",
            "cafe",
            "restaurant",
            "mall",
            "plaza",
            "visitor centre",
            "visitor center"
        ]

        score = 0

        for keyword in high_amenity_keywords:
            if keyword in text:
                score += 30

        for keyword in medium_amenity_keywords:
            if keyword in text:
                score += 15

        return min(score, 100)

    operator_df["operator"] = operator_df["station_name"].apply(
        identify_operator
    )

    operator_df["availability_status"] = operator_df.apply(
        operator_availability,
        axis=1
    )

    availability_weight = {
        "Available": 100,
        "Busy": 30,
        "Unknown": 0,
        "Offline": -200
    }

    operator_df["availability_score"] = (
        operator_df["availability_status"].map(availability_weight)
    )

    operator_df["amenity_score"] = operator_df.apply(
        operator_amenity_score,
        axis=1
    )

    operator_df["is_ultra_fast"] = (
        operator_df["max_power_kw"].fillna(0) >= 250
    )

    operator_summary = (
        operator_df
        .groupby("operator")
        .agg(
            station_count=("station_name", "count"),
            avg_power_kw=("max_power_kw", "mean"),
            max_power_kw=("max_power_kw", "max"),
            avg_reliability=("reliability_score", "mean"),
            avg_availability_score=("availability_score", "mean"),
            avg_amenity_score=("amenity_score", "mean"),
            ultra_fast_sites=("is_ultra_fast", "sum")
        )
        .reset_index()
    )

    operator_summary["ultra_fast_share"] = (
        operator_summary["ultra_fast_sites"]
        / operator_summary["station_count"]
    )

    operator_summary["operator_performance_score"] = (
        operator_summary["station_count"].rank(pct=True) * 25
        + operator_summary["avg_power_kw"].fillna(0).rank(pct=True) * 25
        + operator_summary["avg_reliability"].fillna(0).rank(pct=True) * 20
        + operator_summary["ultra_fast_share"].fillna(0).rank(pct=True) * 20
        + operator_summary["avg_amenity_score"].fillna(0).rank(pct=True) * 10
    )

    operator_summary["operator_performance_score"] = (
        operator_summary["operator_performance_score"]
        .clip(lower=0, upper=100)
        .round(2)
    )

    def operator_label(score):
        if score >= 75:
            return "Strong Network"
        elif score >= 50:
            return "Developing Network"
        return "Limited / Emerging Network"

    operator_summary["operator_label"] = (
        operator_summary["operator_performance_score"]
        .apply(operator_label)
    )

    operator_summary = operator_summary.sort_values(
        "operator_performance_score",
        ascending=False
    )

    known_operator_summary = operator_summary[
        operator_summary["operator"] != "Other / Unknown"
    ].copy()

    if len(known_operator_summary) > 0:
        top_operator = known_operator_summary.iloc[0]
    else:
        top_operator = operator_summary.iloc[0]

    largest_operator = operator_summary.sort_values(
        "station_count",
        ascending=False
    ).iloc[0]

    fastest_operator = operator_summary.sort_values(
        "avg_power_kw",
        ascending=False
    ).iloc[0]

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Top Known Operator",
        top_operator["operator"]
    )

    col2.metric(
        "Largest Network",
        largest_operator["operator"]
    )

    col3.metric(
        "Highest Avg Power",
        fastest_operator["operator"]
    )

    st.subheader("Operator Performance Ranking")

    st.dataframe(
        operator_summary[
            [
                "operator",
                "station_count",
                "avg_power_kw",
                "max_power_kw",
                "ultra_fast_sites",
                "ultra_fast_share",
                "avg_reliability",
                "avg_availability_score",
                "avg_amenity_score",
                "operator_performance_score",
                "operator_label"
            ]
        ].round(2),
        use_container_width=True
    )

    csv_operator_summary = operator_summary.to_csv(index=False)

    st.download_button(
        "Download Operator Performance CSV",
        csv_operator_summary,
        file_name="chargesense_operator_performance.csv",
        mime="text/csv"
    )

    st.subheader("Operator Performance Score")

    score_chart = operator_summary.set_index("operator")[
        "operator_performance_score"
    ]

    st.bar_chart(score_chart)

    st.subheader("Station Count by Operator")

    count_chart = operator_summary.sort_values(
        "station_count",
        ascending=False
    ).set_index("operator")["station_count"]

    st.bar_chart(count_chart)

    st.subheader("Average Charger Power by Operator")

    power_chart = operator_summary.sort_values(
        "avg_power_kw",
        ascending=False
    ).set_index("operator")["avg_power_kw"]

    st.bar_chart(power_chart)

    st.markdown("""
    ### How to interpret this

    **Operator Performance Score** is a prototype benchmark score combining:
    - network size
    - average charger power
    - ultra-fast charger share
    - reliability indicators
    - amenity score

    This is not an official operator ranking. Operator names are estimated from station names, and the scoring uses public charger metadata rather than confirmed operator uptime or live performance data.
    """)

    st.caption(
        "Future production version: use confirmed operator mapping, live charger status, uptime history, delivered charging power, pricing, and session success rates."
    )

elif page == "Station Feedback":

    st.title("⭐ Station Feedback & Reliability Reviews")

    st.markdown("""
    Submit user feedback about charging stations.

    This prototype uses session-based feedback to show how real driver reviews could improve charger reliability scoring,
    wait-time estimates, and station trust in future versions.
    """)

    st.caption(
        "Prototype note: Reviews are stored only during the current app session. A production version would need a database, user accounts, moderation, and station ID matching."
    )

    # -----------------------------
    # Initialise review storage
    # -----------------------------

    if "station_reviews" not in st.session_state:
        st.session_state.station_reviews = []

    feedback_df = ocm_df.copy()

    feedback_df["station_name"] = feedback_df["station_name"].fillna("Unknown Station")
    feedback_df["town"] = feedback_df["town"].fillna("")
    feedback_df["state_clean"] = feedback_df["state_clean"].fillna("")

    feedback_df["station_display_name"] = (
        feedback_df["station_name"].astype(str)
        + " | "
        + feedback_df["town"].astype(str)
        + " | "
        + feedback_df["state_clean"].astype(str)
    )

    station_options = sorted(
        feedback_df["station_display_name"]
        .dropna()
        .unique()
    )

    st.subheader("Submit Station Feedback")

    station_search = st.text_input(
        "Search charging station",
        placeholder="Search by station name, town, or state. Example: Coolac, Tesla, Barnawartha"
    )

    if station_search.strip() != "":
        filtered_station_options = [
            station
            for station in station_options
            if station_search.lower() in station.lower()
        ]
    else:
        filtered_station_options = station_options

    if len(filtered_station_options) == 0:
        st.warning(
            "No stations matched your search. Try a different station name, town, or operator."
        )
        st.stop()

    selected_station_display = st.selectbox(
        "Select charging station",
        filtered_station_options
    )

    selected_station_name = selected_station_display.split(" | ")[0]

    col1, col2 = st.columns(2)

    with col1:
        user_rating = st.slider(
            "Overall station rating",
            1,
            5,
            4
        )
    with col2:
        charger_worked = st.radio(
            "Did the charger work?",
            ["Yes", "No", "Partially"],
            horizontal=True
        )

    col3, col4 = st.columns(2)

    with col3:
        reported_wait_time = st.slider(
            "How long did you wait before charging? (minutes)",
            0,
            120,
            10
        )

    with col4:
        delivered_speed_kw = st.slider(
            "Approx. delivered charging speed (kW)",
            0,
            350,
            75
        )

    issue_type = st.selectbox(
        "Issue type, if any",
        [
            "No issue",
            "Charger offline",
            "Payment issue",
            "Cable/connector issue",
            "Charging slower than expected",
            "Long queue",
            "App/start session issue",
            "Poor amenities",
            "Other"
        ]
    )

    would_recommend = st.radio(
        "Would you recommend this station to another EV driver?",
        ["Yes", "No", "Not sure"],
        horizontal=True
    )

    user_comment = st.text_area(
        "Optional comment",
        placeholder="Example: Charger worked but wait time was long during peak hours."
    )

    submit_review = st.button("Submit Feedback")

    if submit_review:

        review_record = {
            "station_name": selected_station_name,
            "station_display_name": selected_station_display,
            "user_rating": user_rating,
            "charger_worked": charger_worked,
            "reported_wait_time_min": reported_wait_time,
            "delivered_speed_kw": delivered_speed_kw,
            "issue_type": issue_type,
            "would_recommend": would_recommend,
            "comment": user_comment
        }

        st.session_state.station_reviews.append(review_record)

        st.success("Feedback submitted for this session.")

    # -----------------------------
    # Review summary
    # -----------------------------

    st.subheader("Session Feedback Summary")

    if len(st.session_state.station_reviews) == 0:
        st.info("No station feedback submitted yet in this session.")

    else:
        reviews_df = pd.DataFrame(st.session_state.station_reviews)

        total_reviews = len(reviews_df)

        avg_rating = reviews_df["user_rating"].mean()
        avg_wait_time = reviews_df["reported_wait_time_min"].mean()

        success_rate = (
            reviews_df["charger_worked"]
            .map(
                {
                    "Yes": 1,
                    "Partially": 0.5,
                    "No": 0
                }
            )
            .mean()
            * 100
        )

        recommend_rate = (
            reviews_df["would_recommend"]
            .map(
                {
                    "Yes": 1,
                    "Not sure": 0.5,
                    "No": 0
                }
            )
            .mean()
            * 100
        )

        user_reliability_score = (
            avg_rating / 5 * 40
            + success_rate * 0.45
            + recommend_rate * 0.15
        )

        user_reliability_score = round(
            min(max(user_reliability_score, 0), 100),
            2
        )

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Reviews Submitted", total_reviews)
        col2.metric("Avg User Rating", round(avg_rating, 2))
        col3.metric("Avg Reported Wait", f"{round(avg_wait_time, 1)} min")
        col4.metric("User Reliability Score", user_reliability_score)

        col5, col6 = st.columns(2)

        col5.metric("Charge Success Rate", f"{round(success_rate, 1)}%")
        col6.metric("Recommend Rate", f"{round(recommend_rate, 1)}%")

        st.subheader("Recent Feedback")

        st.dataframe(
            reviews_df,
            use_container_width=True
        )

        csv_reviews = reviews_df.to_csv(index=False)

        st.download_button(
            "Download Session Feedback CSV",
            csv_reviews,
            file_name="chargesense_station_feedback.csv",
            mime="text/csv"
        )

    st.markdown("""
    ### How this improves the product

    Public charger metadata can estimate reliability, but it does not always reflect real driver experience.

    User feedback could help future versions measure:
    - whether chargers actually worked
    - real waiting time
    - delivered charging speed
    - repeated station issues
    - user confidence in specific charging locations

    In a production version, this feedback could be combined with operator data and OCPI feeds to build a stronger station trust score.
    """)

# -----------------------------
# PROJECT INSIGHTS
# -----------------------------

elif page == "Project Insights":
    st.title("💡 Project Insights")

    st.markdown("""
    ### Key Takeaways

    **1. Charger availability is not just about count.**  
    Ultra-fast charger coverage matters more for long-distance travel and  queue reduction.

    **2. Reliability is a major product opportunity.**  
    A charger may exist in the dataset, but stale verification data reduces user trust.

    **3. Reservation systems can reduce queue uncertainty.**  
    Short booking windows with temporary access codes could help manage high-demand  charging sites.

    **4. Public EV datasets need cleaning.**  
    Inconsistent state and  location metadata show why infrastructure data products need strong data quality checks.

    **5. Charging type mix reveals infrastructure maturity.**  
    Regions with more ultra-fast DC chargers are better positioned for long-distance EV adoption and  queue reduction.

    **6. Scenario forecasting helps evaluate future pressure.**  
    Growth simulations can highlight which states may need stronger infrastructure investment as EV adoption rises.

    **7. Charger trust is a product opportunity.**  
    Combining reliability, freshness, power and  connector availability can help drivers choose better stations.

    **8. EVAtlas can evolve into a decision-support tool.**  
    Future versions could support charger investment planning, congestion forecasting,
    live availability and  smart route recommendations.
    """)
