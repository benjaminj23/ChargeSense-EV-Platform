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

st.set_page_config(page_title="ChargeSense", layout="wide")


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
ocm_df["max_power_kw"] = pd.to_numeric(ocm_df["max_power_kw"], errors="coerce")
ocm_df["date_last_verified"] = pd.to_datetime(
    ocm_df["date_last_verified"], errors="coerce"
)

latest_date = ocm_df["date_last_verified"].max()

ocm_df["days_since_verified"] = (
    latest_date - ocm_df["date_last_verified"]
).dt.days

ocm_df["is_recently_verified"] = (
    ocm_df["is_recently_verified"]
    .astype(str)
    .str.lower()
    .map({"true": 1, "false": 0, "1": 1, "0": 0})
    .fillna(0)
)

ocm_df["data_quality_level"] = pd.to_numeric(
    ocm_df["data_quality_level"], errors="coerce"
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


ocm_df["reliability_label"] = ocm_df["reliability_score"].apply(reliability_label)

state_population = {
    "New South Wales": 8500000,
    "Victoria": 6900000,
    "Queensland ": 5600000,
    "Western Australia": 3000000,
    "South Australia": 1900000,
    "Tasmania": 575000,
    "ACT": 470000,
    "Northern Territory": 260000,
}

ocm_df["population"] = ocm_df["state_clean"].map(state_population)

state_metrics = (
    ocm_df.groupby("state_clean")
    .agg(
        total_stations=("station_name", "count"),
        avg_power_kw=("max_power_kw", "mean"),
        avg_reliability=( "reliability_score", "mean"),
        ultra_fast_sites=("speed_category", lambda x: (x == "Ultra-fast DC").sum()),
        population=("population", "first"),
    )
    .reset_index()
)

state_metrics["chargers_per_million"] = (
    state_metrics["total_stations"] / state_metrics["population"]
) * 1_000_000

state_metrics["ultra_fast_ratio"] = (
    state_metrics["ultra_fast_sites"] / state_metrics["total_stations"]
)

state_metrics["infrastructure_gap_score"] = (
    (100 - state_metrics["chargers_per_million"].clip(upper=100)) * 0.4
    + (100 - state_metrics["avg_reliability"]) * 0.3
    + (1 - state_metrics["ultra_fast_ratio"]) * 100 * 0.3
)

state_metrics["infrastructure_gap_score"] = (
    state_metrics["infrastructure_gap_score"].clip(lower=0, upper=100).round(2)
)
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

state_metrics["chargers_per_1000_evs"] = (
    state_metrics["total_stations"]
    / state_metrics["estimated_ev_count"]
) * 1000

state_metrics["chargers_per_1000_evs"] = (
    state_metrics["chargers_per_1000_evs"]
    .round(2)
)
# -----------------------------
# SIDEBAR
# -----------------------------

st.sidebar.title("⚡ ChargeSense")


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
            "Reservation Simulation"
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
            "Model Assumptions",
            "Project Insights"
        ]
    )

# -----------------------------
# HOME
# -----------------------------

if page == "Home":

    st.title("⚡ ChargeSense")

    st.subheader("EV Infrastructure Intelligence & Route Planning Platform")

    st.markdown("""
    ChargeSense is a prototype platform for EV route planning and  EV infrastructure intelligence in Australia.

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

    st.markdown("Explore EV charging stations across Australia using OpenChargeMap data.")

    col1, col2 = st.columns(2)

    with col1:
        selected_state = st.selectbox(
            "Select State", sorted(ocm_df["state_clean"].dropna().unique())
        )

    with col2:
        max_power_available = int(ocm_df["max_power_kw"].fillna(0).max())
        min_power = st.slider("Minimum Charger Power (kW)", 0, max_power_available, 0)

    map_df = ocm_df[
        (ocm_df["state_clean"] == selected_state)
        & (ocm_df["max_power_kw"].fillna(0) >= min_power)
    ].copy()

    map_df["latitude"] = pd.to_numeric(map_df["latitude"], errors="coerce")
    map_df["longitude"] = pd.to_numeric(map_df["longitude"], errors="coerce")
    map_df = map_df.dropna(subset=["latitude", "longitude"])

    map_df["plot_size"] = map_df["max_power_kw"].fillna(1).clip(lower=5, upper=350)

    st.write(f"Showing {len(map_df)} charging stations")

    if len(map_df) == 0:
        st.warning("No stations match the selected filters.")
    else:
        fig = px.scatter_mapbox(
            map_df,
            lat="latitude",
            lon="longitude",
            hover_name="station_name",
            hover_data={
                "state_clean": True,
                "max_power_kw": True,
                "speed_category": True,
                "reliability_score": True,
                "reliability_label": True,
                "latitude": False,
                "longitude": False,
                "plot_size": False,
            },
            color="speed_category",
            size="plot_size",
            zoom=5,
            height=650,
        )

        fig.update_layout(
            mapbox_style="open-street-map",
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
        )

        st.plotly_chart(fig, use_container_width=True)

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
    st.title("🔐 Reservation Simulation")

    st.markdown("""
    Simulate a short reservation window for high-priority EV charging stations.
    This is a prototype of the booking/access-code concept.
    """)

    top_sites = (
        nsw_df[["Station_name", "Operator", "reservation_need_index"]]
        .dropna(subset=["Station_name"])
        .sort_values("reservation_need_index", ascending=False)
    )

    selected_station = st.selectbox(
        "Select Charging Station", top_sites["Station_name"].unique()
    )

    selected_row = top_sites[top_sites["Station_name"] == selected_station].iloc[0]

    reservation_score = selected_row["reservation_need_index"]
    operator = selected_row["Operator"]

    col1, col2 = st.columns(2)

    col1.metric("Operator", operator)
    col2.metric("Reservation Need Score", round(reservation_score, 2))

    if reservation_score >= 13:
        st.warning(
            "High reservation priority: limited high-speed charging capacity may create queue pressure."
        )
    elif reservation_score >= 10:
        st.info("Medium reservation priority: booking may help reduce uncertainty.")
    else:
        st.success("Lower reservation priority: queue pressure is likely manageable.")

    reservation_minutes = st.slider("Reservation Duration (minutes)", 15, 60, 20)

    def generate_access_code():
        return str(random.randint(1000, 9999))

    if st.button("Simulate Reservation"):
        booking_time = datetime.now()
        expiry_time = booking_time + timedelta(minutes=reservation_minutes)
        access_code = generate_access_code()

        st.success(f"Reservation confirmed for {selected_station}")
        st.info(f"Access window: {reservation_minutes} minutes")

        st.write("Booking time:", booking_time.strftime("%Y-%m-%d %H:%M:%S"))
        st.write("Expiry time:", expiry_time.strftime("%Y-%m-%d %H:%M:%S"))

        st.code(f"ACCESS CODE: {access_code}")

        st.markdown("""
        ### Reservation Rules

        - Access code is valid only during the reservation window.
        - If the driver does not arrive before expiry, the charger is released.
        - Future versions could include no-show penalties and  queue priority rules.
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

    ChargeSense uses public EV infrastructure datasets and  scenario-based models.
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

    st.markdown("""
    Strategic EV infrastructure intelligence for councils, fleet managers and  infrastructure planners.

    This page combines EV adoption, charger supply, reliability, demand  pressure and  operator benchmarking
    to support investment and  planning decisions.
    """)

    st.caption(
        "This dashboard uses public charger metadata, AAA/BITRE EV registration-derived inputs and  scenario-based planning assumptions. It is a decision-support prototype, not an official infrastructure forecast."
    )

    # -----------------------------------
    # PREPARE B2B STATE DATA
    # -----------------------------------

    b2b_df = state_metrics.copy()

    numeric_cols = [
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
        "investment_priority_score"
    ]

    for col in numeric_cols:
        if col in b2b_df.columns:
            b2b_df[col] = pd.to_numeric(
                b2b_df[col],
                errors="coerce"
            )

    b2b_df = b2b_df.dropna(
        subset=[
            "state_clean",
            "estimated_ev_count",
            "total_stations"
        ]
    )

    # -----------------------------------
    # DEMand  FORECAST ASSUMPTIONS
    # -----------------------------------

    st.subheader("Planning Assumptions")

    col1, col2, col3 = st.columns(3)

    with col1:
        forecast_horizon = st.slider(
            "Forecast Horizon (Years)",
            1,
            10,
            3
        )

    with col2:
        public_charges_per_ev_month = st.slider(
            "Public Charges per EV per Month",
            1,
            10,
            4
        )

    with col3:
        charger_capacity_sessions_month = st.slider(
            "Sessions per Charger per Month",
            100,
            2000,
            800,
            step=50
        )

    # -----------------------------------
    # FORECAST PRESSURE
    # -----------------------------------

    b2b_df["state_growth_rate_used"] = (
        b2b_df["annual_ev_growth_rate"]
        .fillna(0)
        .clip(lower=0, upper=100)
    )

    b2b_df["forecast_evs"] = (
        b2b_df["estimated_ev_count"]
        * (
            1 + b2b_df["state_growth_rate_used"] / 100
        ) ** forecast_horizon
    )

    b2b_df["monthly_public_sessions"] = (
        b2b_df["forecast_evs"]
        * public_charges_per_ev_month
    )

    b2b_df["sessions_per_station_month"] = (
        b2b_df["monthly_public_sessions"]
        / b2b_df["total_stations"].replace(0, np.nan)
    )

    b2b_df["required_stations"] = (
        b2b_df["monthly_public_sessions"]
        / charger_capacity_sessions_month
    )

    b2b_df["additional_stations_needed"] = (
        b2b_df["required_stations"]
        - b2b_df["total_stations"]
    )

    b2b_df["additional_stations_needed"] = (
        b2b_df["additional_stations_needed"]
        .clip(lower=0)
        .fillna(0)
    )

    max_sessions_pressure = b2b_df["sessions_per_station_month"].max()

    if pd.isna(max_sessions_pressure) or max_sessions_pressure == 0:
        b2b_df["demand _pressure_index"] = 0
    else:
        b2b_df["demand _pressure_index"] = (
            b2b_df["sessions_per_station_month"]
            / max_sessions_pressure
            * 100
        )

    b2b_df["demand _pressure_index"] = (
        b2b_df["demand _pressure_index"]
        .fillna(0)
        .round(2)
    )

    def b2b_priority_label(score):
        high_threshold = b2b_df["investment_priority_score"].quantile(0.67)
        medium_threshold = b2b_df["investment_priority_score"].quantile(0.33)

        if score >= high_threshold:
            return "High Priority"
        elif score >= medium_threshold:
            return "Medium Priority"
        return "Lower Priority"

    b2b_df["investment_priority_label"] = (
        b2b_df["investment_priority_score"]
        .apply(b2b_priority_label)
    )

    # -----------------------------------
    # OPERATOR SUMMARY
    # -----------------------------------

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

    operator_df["operator"] = operator_df["station_name"].apply(
        identify_operator
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
            ultra_fast_sites=("is_ultra_fast", "sum")
        )
        .reset_index()
    )

    operator_summary["ultra_fast_share"] = (
        operator_summary["ultra_fast_sites"]
        / operator_summary["station_count"]
    )

    operator_summary["operator_performance_score"] = (
        operator_summary["station_count"].rank(pct=True) * 30
        + operator_summary["avg_power_kw"].fillna(0).rank(pct=True) * 30
        + operator_summary["avg_reliability"].fillna(0).rank(pct=True) * 20
        + operator_summary["ultra_fast_share"].fillna(0).rank(pct=True) * 20
    )

    operator_summary["operator_performance_score"] = (
        operator_summary["operator_performance_score"]
        .clip(lower=0, upper=100)
        .round(2)
    )

    operator_summary = operator_summary.sort_values(
        "operator_performance_score",
        ascending=False
    )

    known_operator_summary = operator_summary[
        operator_summary["operator"] != "Other / Unknown"
    ].copy()

    if len(known_operator_summary) > 0:
        best_operator = known_operator_summary.iloc[0]
    else:
        best_operator = operator_summary.iloc[0]

    # -----------------------------------
    # EXECUTIVE SUMMARY KPIS
    # -----------------------------------

    st.subheader("Executive Summary")

    top_demand_state = b2b_df.sort_values(
    "demand_pressure_index",
    ascending=False
    ).iloc[0]

    top_demand_state = b2b_df.sort_values(
        "demand _pressure_index",
        ascending=False
    ).iloc[0]

    weakest_charger_supply_state = b2b_df.sort_values(
        "chargers_per_1000_evs",
        ascending=True
    ).iloc[0]

    total_additional_stations = b2b_df["additional_stations_needed"].sum()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Top Investment Priority",
        top_investment_state["state_clean"]
    )

    col2.metric(
        "Highest Demand  Pressure",
        top_demand_state["state_clean"]
    )

    col3.metric(
        "Lowest Chargers / 1,000 EVs",
        weakest_charger_supply_state["state_clean"]
    )

    col4.metric(
        "Best Known Operator",
        best_operator["operator"]
    )

    col5, col6, col7 = st.columns(3)

    col5.metric(
        "Estimated Additional Stations Needed",
        f"{int(round(total_additional_stations, 0)):,}"
    )

    col6.metric(
        "National Forecast EVs",
        f"{int(round(b2b_df['forecast_evs'].sum(), 0)):,}"
    )

    col7.metric(
        "Planning Horizon",
        f"{forecast_horizon} years"
    )

    # -----------------------------------
    # DECISION RECOMMENDATIONS
    # -----------------------------------

    st.subheader("Planning Recommendations")

    priority_states = b2b_df.sort_values(
        "investment_priority_score",
        ascending=False
    ).head(3)

    demand_states = b2b_df.sort_values(
        "demand _pressure_index",
        ascending=False
    ).head(3)

    low_supply_states = b2b_df.sort_values(
        "chargers_per_1000_evs",
        ascending=True
    ).head(3)

    st.markdown(
        f"""
        **Investment focus:** Prioritise **{top_investment_state["state_clean"]}** based on the combined investment priority score.

        **Demand  pressure:** **{top_demand_state["state_clean"]}** shows the highest forecast charging pressure under the current assumptions.

        **Charger supply gap:** **{weakest_charger_supply_state["state_clean"]}** has the lowest chargers per 1,000 EVs, suggesting tighter charging supply relative to EV adoption.

        **Operator benchmark:** **{best_operator["operator"]}** currently ranks highest among known operators based on public metadata.
        """
    )

    # -----------------------------------
    # STATE INVESTMENT TABLE
    # -----------------------------------

    st.subheader("State Investment Ranking")

    investment_table = (
        b2b_df[
            [
                "state_clean",
                "estimated_ev_count",
                "annual_ev_growth_rate",
                "forecast_evs",
                "total_stations",
                "chargers_per_1000_evs",
                "avg_reliability",
                "ultra_fast_ratio",
                "investment_priority_score",
                "investment_priority_label",
                "additional_stations_needed",
                "demand _pressure_index"
            ]
        ]
        .sort_values("investment_priority_score", ascending=False)
        .round(2)
    )

    st.dataframe(
        investment_table,
        use_container_width=True
    )

    csv_investment = investment_table.to_csv(index=False)

    st.download_button(
        "Download State Investment Report CSV",
        csv_investment,
        file_name="chargesense_state_investment_report.csv",
        mime="text/csv"
    )

    # -----------------------------------
    # DEMand  FORECAST SUMMARY
    # -----------------------------------

    st.subheader("Demand  Forecast Summary")

    forecast_summary = (
        b2b_df[
            [
                "state_clean",
                "estimated_ev_count",
                "forecast_evs",
                "monthly_public_sessions",
                "sessions_per_station_month",
                "required_stations",
                "additional_stations_needed",
                "demand _pressure_index"
            ]
        ]
        .sort_values("demand _pressure_index", ascending=False)
        .round(2)
    )

    st.dataframe(
        forecast_summary,
        use_container_width=True
    )

    csv_forecast = forecast_summary.to_csv(index=False)

    st.download_button(
        "Download Demand  Forecast Report CSV",
        csv_forecast,
        file_name="chargesense_demand _forecast_report.csv",
        mime="text/csv"
    )

    # -----------------------------------
    # OPERATOR BENCHMARK SUMMARY
    # -----------------------------------

    st.subheader("Operator Benchmark Summary")

    operator_benchmark_table = (
        operator_summary[
            [
                "operator",
                "station_count",
                "avg_power_kw",
                "max_power_kw",
                "ultra_fast_sites",
                "ultra_fast_share",
                "avg_reliability",
                "operator_performance_score"
            ]
        ]
        .sort_values("operator_performance_score", ascending=False)
        .round(2)
    )

    st.dataframe(
        operator_benchmark_table,
        use_container_width=True
    )

    csv_operator = operator_benchmark_table.to_csv(index=False)

    st.download_button(
        "Download Operator Benchmark Report CSV",
        csv_operator,
        file_name="chargesense_operator_benchmark_report.csv",
        mime="text/csv"
    )

    # -----------------------------------
    # CHARTS
    # -----------------------------------

    st.subheader("Investment Priority Score by State")

    investment_chart = b2b_df.sort_values(
        "investment_priority_score",
        ascending=False
    )

    st.bar_chart(
        investment_chart.set_index("state_clean")["investment_priority_score"]
    )

    st.subheader("Additional Stations Needed by State")

    additional_station_chart = b2b_df.sort_values(
        "additional_stations_needed",
        ascending=False
    )

    st.bar_chart(
        additional_station_chart.set_index("state_clean")["additional_stations_needed"]
    )

    st.subheader("Demand  Pressure Index by State")

    demand_chart = b2b_df.sort_values(
        "demand _pressure_index",
        ascending=False
    )

    st.bar_chart(
        demand_chart.set_index("state_clean")["demand _pressure_index"]
    )

    st.subheader("Operator Performance Score")

    operator_chart = operator_summary.sort_values(
        "operator_performance_score",
        ascending=False
    )

    st.bar_chart(
        operator_chart.set_index("operator")["operator_performance_score"]
    )

    # -----------------------------------
    # INTERPRETATION
    # -----------------------------------

    st.markdown("""
    ### How to interpret this page

    **Fleet managers** can use this page to understand  charging risk, expected charging demand  and  operator network strength.

    **Councils** can use this page to identify states or regions where public charging infrastructure may need stronger investment.

    **Charging investors/operators** can use this page to compare demand  pressure, infrastructure gaps and  operator performance.

    The current model is state-level. A future B2B version could extend this to LGA, suburb, corridor, or depot-level planning using richer geographic and  fleet data.
    """)

    st.caption(
        "This page is designed as a B2B planning prototype. It does not use live charger occupancy, confirmed operator uptime, or private fleet telematics."
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
        forecast_df["demand _pressure_index"] = 0
    else:
        forecast_df["demand _pressure_index"] = (
            forecast_df["sessions_per_station_month"]
            / max_pressure
        ) * 100

    forecast_df["demand _pressure_index"] = (
        forecast_df["demand _pressure_index"]
        .fillna(0)
        .round(2)
    )

    def demand _pressure_label(score):
        if score >= 70:
            return "High Future Pressure"
        elif score >= 40:
            return "Moderate Future Pressure"
        return "Lower Future Pressure"

    forecast_df["demand _pressure_label"] = (
        forecast_df["demand _pressure_index"]
        .apply(demand _pressure_label)
    )

    forecast_df = forecast_df.sort_values(
        "demand _pressure_index",
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
        round(highest_pressure_state["demand _pressure_index"], 1)
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
                "demand _pressure_index",
                "demand _pressure_label"
            ]
        ].round(2),
        use_container_width=True
    )

    st.subheader("Demand  Pressure Index")

    pressure_chart = forecast_df.sort_values(
        "demand _pressure_index",
        ascending=False
    )

    st.bar_chart(
        pressure_chart.set_index("state_clean")["demand _pressure_index"]
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

    st.markdown("""
    Generate a real driving route and  identify high-quality EV charging stations near the route.

    Use **Major City Mode** for quick routes, or **Custom Place Mode** for suburb/place-level routing.
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

        if reliability >= 70:
            return "Available"
        elif reliability >= 40:
            return "Busy"
        elif reliability > 0:
            return "Unknown"
        else:
            return "Offline"

    def calculate_amenity_score(row):
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
        else:
            return "Basic Stop"

    route_input_mode = st.radio(
        "Route Input Mode",
        ["Major City", "Custom Place"],
        horizontal=True
    )

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

        start_label = start_city
        destination_label = destination_city
        start_coords = city_coordinates[start_city]
        end_coords = city_coordinates[destination_city]

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

        start_label = start_place
        destination_label = destination_place
        start_coords = None
        end_coords = None

    st.subheader("EV Trip Settings")

    selected_ev = st.selectbox(
        "Select EV Model",
        list(ev_profiles.keys())
    )

    battery_kwh = ev_profiles[selected_ev]["battery_kwh"]
    ev_range_km = ev_profiles[selected_ev]["range_km"]

    st.info(
        f"{selected_ev}: {battery_kwh} kWh battery, approx. {ev_range_km} km driving range."
    )

    charging_strategy = st.selectbox(
        "Charging Strategy",
        ["Conservative", "Fastest Trip", "Fewest Stops"]
    )

    if charging_strategy == "Conservative":
        dynamic_charge_to_percent = 80
    elif charging_strategy == "Fastest Trip":
        dynamic_charge_to_percent = 60
    else:
        dynamic_charge_to_percent = 90

    weather_mode = st.selectbox(
        "Weather Conditions",
        [
            "Normal",
            "Cold Weather",
            "Heavy Rain",
            "Extreme Heat"
        ]
    )

    weather_range_multiplier = 1.0

    if weather_mode == "Cold Weather":
        weather_range_multiplier = 0.82
    elif weather_mode == "Heavy Rain":
        weather_range_multiplier = 0.88
    elif weather_mode == "Extreme Heat":
        weather_range_multiplier = 0.90

    adjusted_ev_range_km = ev_range_km * weather_range_multiplier

    col1, col2 = st.columns(2)

    with col1:
        route_buffer_km = st.slider(
            "Maximum Distance from Route (km)",
            5,
            50,
            15
        )

    with col2:
        safety_buffer_km = st.slider(
            "Safety Buffer Before Charging (km)",
            20,
            100,
            50
        )

    col1, col2, col3 = st.columns(3)

    with col1:
        starting_battery_percent = st.slider(
            "Starting Battery (%)",
            20,
            100,
            90
        )

    with col2:
        charge_from_percent = st.slider(
            "Minimum Arrival Battery at Stop (%)",
            5,
            50,
            20
        )

    with col3:
        st.metric(
            "Target Battery Strategy",
            f"{dynamic_charge_to_percent}%"
        )

    st.subheader("Cost Settings")

    electricity_price_per_kwh = st.slider(
        "Estimated Public Charging Price ($/kWh)",
        0.20,
        1.20,
        0.65,
        0.05
    )

    if st.button("Generate Real Route"):

        if dynamic_charge_to_percent <= charge_from_percent:
            st.warning("Charging strategy target must be higher than minimum arrival battery.")
            st.stop()

        if route_input_mode == "Major City":

            if start_label == destination_label:
                st.warning("Start city and  destination city cannot be the same.")
                st.stop()

        else:

            if start_place.strip() == "" or destination_place.strip() == "":
                st.warning("Please enter both a start location and  destination.")
                st.stop()

            with st.spinner("Finding locations..."):
                start_geo = geocode_place(start_place)
                destination_geo = geocode_place(destination_place)

            if start_geo is None:
                st.error(f"Could not find start location: {start_place}")
                st.stop()

            if destination_geo is None:
                st.error(f"Could not find destination: {destination_place}")
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
            st.info(f"Destination matched to: {destination_label}")

        with st.spinner("Calculating route..."):

            url = (
                f"https://router.project-osrm.org/route/v1/driving/"
                f"{start_coords[0]},{start_coords[1]};"
                f"{end_coords[0]},{end_coords[1]}"
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
                st.error(f"OSRM Error {response.status_code}")
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

            st.success(
                f"Route generated from {start_label} to {destination_label}"
            )

            metric_col1, metric_col2, metric_col3 = st.columns(3)

            metric_col1.metric(
                "Route Distance",
                f"{round(distance_km, 1)} km"
            )

            metric_col2.metric(
                "Estimated Drive Time",
                f"{round(duration_hours, 1)} hrs"
            )

            metric_col3.metric(
                "Adjusted EV Range",
                f"{round(adjusted_ev_range_km, 1)} km"
            )

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

            route_map_df = route_map_df.dropna(
                subset=["latitude", "longitude"]
            )

            route_map_df["route_score"] = (
                route_map_df["max_power_kw"].fillna(0) * 0.6
                + route_map_df["reliability_score"].fillna(0) * 0.4
            )

            route_map_df["availability_status"] = (
                route_map_df.apply(simulated_availability, axis=1)
            )

            availability_weight = {
                "Available": 100,
                "Busy": 30,
                "Unknown": 0,
                "Offline": -200
            }

            route_map_df["availability_score"] = (
                route_map_df["availability_status"].map(availability_weight)
            )

            route_map_df["amenity_score"] = (
                route_map_df.apply(calculate_amenity_score, axis=1)
            )

            route_map_df["amenity_label"] = (
                route_map_df["amenity_score"].apply(amenity_label)
            )

            sampled_route = route_df.iloc[
                ::max(1, len(route_df) // 100)
            ].copy()

            def nearest_route_distance(row):
                distances = sampled_route.apply(
                    lambda point: haversine_distance(
                        row["latitude"],
                        row["longitude"],
                        point["latitude"],
                        point["longitude"]
                    ),
                    axis=1
                )

                return distances.min()

            route_map_df["distance_to_route_km"] = route_map_df.apply(
                nearest_route_distance,
                axis=1
            )

            near_route_df = route_map_df[
                route_map_df["distance_to_route_km"] <= route_buffer_km
            ].copy()

            near_route_df["route_recommendation_score"] = (
                near_route_df["route_score"].fillna(0)
                + near_route_df["availability_score"].fillna(0)
                + (near_route_df["amenity_score"].fillna(0) * 0.5)
                - (near_route_df["distance_to_route_km"] * 10)
            )

            recommended_stops = (
                near_route_df
                .sort_values("route_recommendation_score", ascending=False)
                .head(30)
            )

            st.info(
                f"Found {len(near_route_df)} chargers within "
                f"{route_buffer_km} km of the route."
            )

            st.subheader("Corridor Risk Score")

            st.markdown("""
            The **Corridor Risk Score** estimates how risky an EV route is based on charging infrastructure along the selected route.

            It considers:
            - how many chargers are near the route
            - average charger reliability
            - estimated availability
            - charger coverage along the route
            - whether the route has enough nearby charging options

            A higher score means the route may have higher charging risk, weaker infrastructure coverage, or lower charger trust.
            """)

            corridor_charger_count = len(near_route_df)

            avg_corridor_reliability = (
                near_route_df["reliability_score"]
                .fillna(0)
                .mean()
            )

            avg_corridor_availability = (
                near_route_df["availability_score"]
                .fillna(0)
                .mean()
            )

            chargers_per_100km = (
                corridor_charger_count / distance_km
            ) * 100

            corridor_risk_score = (
                (100 - min(chargers_per_100km * 10, 100)) * 0.4
                + (100 - avg_corridor_reliability) * 0.35
                + (100 - max(avg_corridor_availability, 0)) * 0.25
            )

            corridor_risk_score = round(
                max(0, min(corridor_risk_score, 100)),
                2
            )

            if corridor_risk_score >= 70:
                corridor_risk_label = "High Risk"
            elif corridor_risk_score >= 40:
                corridor_risk_label = "Medium Risk"
            else:
                corridor_risk_label = "Low Risk"

            risk_col1, risk_col2, risk_col3, risk_col4 = st.columns(4)

            risk_col1.metric(
                "Corridor Risk",
                corridor_risk_label
            )

            risk_col2.metric(
                "Risk Score",
                corridor_risk_score
            )

            risk_col3.metric(
                "Chargers Near Route",
                corridor_charger_count
            )

            risk_col4.metric(
                "Chargers / 100 km",
                round(chargers_per_100km, 1)
            )

            risk_col5, risk_col6 = st.columns(2)

            risk_col5.metric(
                "Avg Reliability",
                round(avg_corridor_reliability, 1)
            )

            risk_col6.metric(
                "Avg Availability Score",
                round(avg_corridor_availability, 1)
            )

            st.caption(
                "Interpretation: A route can have many chargers but still show medium or high corridor risk if reliability, data freshness, or estimated availability is weak."
            )

            st.caption(
                "Corridor risk uses public charger data, reliability indicators and  simulated availability. It is a planning estimate, not live operational risk."
            )

            st.subheader("Recommended Charging Stops Near Route")

            st.caption(
                "Availability status is currently simulated from reliability indicators and  data freshness. Future versions can replace this with live operator API data."
            )

            if len(recommended_stops) == 0:
                st.warning("No chargers found within the selected route buffer.")
                st.stop()

            st.dataframe(
                recommended_stops[
                    [
                        "station_name",
                        "town",
                        "state_clean",
                        "max_power_kw",
                        "reliability_score",
                        "availability_status",
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

            st.subheader("Suggested Charging Stop Sequence")

            usable_start_range_km = adjusted_ev_range_km * (
                starting_battery_percent / 100
            )

            usable_after_charge_range_km = adjusted_ev_range_km * (
                (dynamic_charge_to_percent - charge_from_percent) / 100
            )

            safe_start_range_km = max(
                usable_start_range_km - safety_buffer_km,
                1
            )

            safe_after_charge_range_km = max(
                usable_after_charge_range_km - safety_buffer_km,
                1
            )

            route_stop_targets = []

            distance_covered = safe_start_range_km

            while distance_covered < distance_km:
                route_stop_targets.append(distance_covered)
                distance_covered += safe_after_charge_range_km

            sequence_stops = []
            used_station_names = set()

            current_battery_percent = starting_battery_percent
            previous_distance_km = 0
            battery_warning_triggered = False

            for target_distance in route_stop_targets:

                leg_distance_km = target_distance - previous_distance_km

                battery_used_percent = (
                    leg_distance_km / adjusted_ev_range_km
                ) * 100

                arrival_battery_percent = max(
                    current_battery_percent - battery_used_percent,
                    0
                )

                if arrival_battery_percent < charge_from_percent:
                    battery_warning_triggered = True

                charge_needed_percent = max(
                    dynamic_charge_to_percent - arrival_battery_percent,
                    0
                )

                energy_needed_kwh = (
                    battery_kwh
                    * charge_needed_percent
                    / 100
                )

                target_ratio = target_distance / distance_km

                target_index = int(
                    target_ratio * len(route_df)
                )

                target_index = min(
                    max(target_index, 0),
                    len(route_df) - 1
                )

                target_point = route_df.iloc[target_index]

                cand idate_stops = recommended_stops.copy()

                cand idate_stops["distance_to_target_km"] = (
                    cand idate_stops.apply(
                        lambda row: haversine_distance(
                            row["latitude"],
                            row["longitude"],
                            target_point["latitude"],
                            target_point["longitude"]
                        ),
                        axis=1
                    )
                )

                cand idate_stops = cand idate_stops[
                    ~cand idate_stops["station_name"].isin(used_station_names)
                ]

                if len(cand idate_stops) == 0:
                    break

                best_stop = (
                    cand idate_stops
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

                charger_power_kw = max(
                    float(best_stop["max_power_kw"])
                    if pd.notna(best_stop["max_power_kw"])
                    else 1,
                    1
                )

                departure_battery_percent = min(
                    arrival_battery_percent + charge_needed_percent,
                    100
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

                estimated_charge_cost_aud = (
                    energy_needed_kwh * electricity_price_per_kwh
                )

                current_battery_percent = departure_battery_percent
                previous_distance_km = target_distance

                sequence_stops.append({
                    "stop_number": len(sequence_stops) + 1,
                    "target_distance_km": round(target_distance, 1),
                    "station_name": best_stop["station_name"],
                    "town": best_stop["town"],
                    "state_clean": best_stop["state_clean"],
                    "max_power_kw": best_stop["max_power_kw"],
                    "reliability_score": best_stop["reliability_score"],
                    "availability_status": best_stop["availability_status"],
                    "availability_score": best_stop["availability_score"],
                    "amenity_label": best_stop["amenity_label"],
                    "amenity_score": best_stop["amenity_score"],
                    "route_score": best_stop["route_score"],
                    "arrival_battery_%": round(arrival_battery_percent, 1),
                    "departure_battery_%": round(departure_battery_percent, 1),
                    "estimated_charge_kwh": round(energy_needed_kwh, 1),
                    "estimated_charge_time_min": round(estimated_charge_time_min, 1),
                    "estimated_charge_cost_aud": round(estimated_charge_cost_aud, 2),
                    "distance_to_target_km": round(
                        best_stop["distance_to_target_km"],
                        1
                    )
                })

            if battery_warning_triggered:
                st.warning(
                    "Battery may drop below the selected minimum arrival battery on one or more legs. "
                    "Consider increasing starting battery, using a longer-range EV, reducing the safety buffer, "
                    "or choosing a different charging strategy."
                )

            if len(sequence_stops) == 0:

                st.success(
                    "No charging stop required based on selected EV range."
                )

                total_charging_time_min = 0
                total_trip_time_hours = duration_hours
                total_charging_cost_aud = 0
                cost_per_100km = 0

            else:

                sequence_df = pd.DataFrame(sequence_stops)

                total_charging_time_min = (
                    sequence_df["estimated_charge_time_min"].sum()
                )

                total_trip_time_hours = (
                    duration_hours + (total_charging_time_min / 60)
                )

                total_charging_cost_aud = (
                    sequence_df["estimated_charge_cost_aud"].sum()
                )

                cost_per_100km = (
                    total_charging_cost_aud / distance_km
                ) * 100

                summary_col1, summary_col2, summary_col3, summary_col4, summary_col5 = st.columns(5)

                summary_col1.metric(
                    "Charging Stops",
                    len(sequence_df)
                )

                summary_col2.metric(
                    "Total Charging Time",
                    f"{round(total_charging_time_min, 1)} min"
                )

                summary_col3.metric(
                    "Total Trip Time",
                    f"{round(total_trip_time_hours, 1)} hrs"
                )

                summary_col4.metric(
                    "Charging Cost",
                    f"${round(total_charging_cost_aud, 2)}"
                )

                summary_col5.metric(
                    "Cost / 100 km",
                    f"${round(cost_per_100km, 2)}"
                )

                st.dataframe(
                    sequence_df,
                    use_container_width=True
                )

                st.subheader("Why These Stops Were Recommended")
                for _, stop in sequence_df.iterrows():
                    st.markdown(
                    f"""
                    **Stop {int(stop["stop_number"])}: {stop["station_name"]}**

                    Recommended because:
                    - Charger speed: **{stop["max_power_kw"]} kW**
                    - Availability estimate: **{stop["availability_status"]}**
                    - Amenity type: **{stop["amenity_label"]}**
                    - Expected arrival battery: **{stop["arrival_battery_%"]}%**
                    - Expected departure battery: **{stop["departure_battery_%"]}%**
                    - Estimated charging time: **{stop["estimated_charge_time_min"]} minutes**
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

            st.subheader("Trip Plan Summary")

            if len(sequence_stops) > 0:
                charging_stops_count = len(sequence_df)
                charging_time_summary = round(total_charging_time_min, 1)
                total_trip_time_summary = round(total_trip_time_hours, 1)
                charging_cost_summary = round(total_charging_cost_aud, 2)
                cost_per_100km_summary = round(cost_per_100km, 2)
            else:
                charging_stops_count = 0
                charging_time_summary = 0
                total_trip_time_summary = round(duration_hours, 1)
                charging_cost_summary = 0
                cost_per_100km_summary = 0

            trip_summary = f"""
Route: {start_label} → {destination_label}
EV: {selected_ev}
Distance: {round(distance_km, 1)} km
Drive Time: {round(duration_hours, 1)} hrs
Adjusted EV Range: {round(adjusted_ev_range_km, 1)} km
Weather: {weather_mode}
Strategy: {charging_strategy}
Charging Stops: {charging_stops_count}
Total Charging Time: {charging_time_summary} min
Estimated Charging Cost: ${charging_cost_summary}
Estimated Cost per 100 km: ${cost_per_100km_summary}
Estimated Total Trip Time: {total_trip_time_summary} hrs
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
                hover_data={
                    "town": True,
                    "state_clean": True,
                    "max_power_kw": True,
                    "reliability_score": True,
                    "availability_status": True,
                    "availability_score": True,
                    "amenity_label": True,
                    "amenity_score": True,
                    "route_score": True,
                    "route_recommendation_score": True,
                    "distance_to_route_km": True,
                    "latitude": False,
                    "longitude": False,
                    "plot_size": False
                },
                color="route_recommendation_score",
                size="plot_size",
                center={
                    "lat": route_df["latitude"].mean(),
                    "lon": route_df["longitude"].mean()
                },
                zoom=6,
                height=700
            )

            fig.add_scattermapbox(
                lat=route_df["latitude"],
                lon=route_df["longitude"],
                mode="lines",
                line=dict(width=4),
                name="Driving Route"
            )

            fig.update_layout(
                mapbox_style="open-street-map",
                margin={
                    "r": 0,
                    "t": 0,
                    "l": 0,
                    "b": 0
                }
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

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

    **8. ChargeSense can evolve into a decision-support tool.**  
    Future versions could support charger investment planning, congestion forecasting,
    live availability and  smart route recommendations.
    """)
