import random
import requests
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
    "Queensland": 5600000,
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
# -----------------------------
# SIDEBAR
# -----------------------------

st.sidebar.title("⚡ ChargeSense")

page = st.sidebar.radio(
    "Navigate",
    [
        "Home",
        "Infrastructure Overview",
        "Infrastructure Gap Analysis",
        "Interactive Map",
        "Reliability Intelligence",
        "Charger Recommendation",
        "Reliability Risk Model",
        "Queue Simulation Engine",
        "Reservation Simulation",
        "Congestion Risk Analysis",
        "Dynamic Pricing Simulator",
        "Charging Cost Simulator",
        "Availability Stress Test",
        "Demand Forecast Model",
        "Model Assumptions",
        "Real Route Optimizer",
        "Project Insights",
    ],
)

# -----------------------------
# HOME
# -----------------------------

if page == "Home":
    st.title("⚡ ChargeSense")
    st.subheader("EV Infrastructure Intelligence Platform")

    st.markdown("""
    ChargeSense is an EV Infrastructure Intelligence Platform designed to analyze
    charging reliability, infrastructure quality, congestion risk, charging accessibility,
    future pressure and charging operations across Australia.

    Features include:
    - Interactive infrastructure mapping
    - Reliability intelligence scoring
    - Charger recommendation engine
    - Reservation simulation
    - Congestion risk analysis
    - Queue simulation
    - Charging cost simulation
    - Infrastructure investment-style analytics
    """)

    st.success("Platform loaded successfully")

    st.divider()

    st.caption(
        "Built using Python, Streamlit, OpenChargeMap API data, and NSW EV infrastructure data."
    )

    st.link_button("View GitHub Repository", "YOUR_GITHUB_LINK")

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
    charger density, ultra-fast charger availability, and reliability.
    """)

    gap_view = (
        state_metrics[
            [
                "state_clean",
                "population",
                "total_stations",
                "chargers_per_million",
                "ultra_fast_sites",
                "ultra_fast_ratio",
                "avg_reliability",
                "infrastructure_gap_score",
            ]
        ]
        .dropna(subset=["population"])
        .sort_values("infrastructure_gap_score", ascending=False)
    )

    col1, col2, col3 = st.columns(3)
    highest_gap = gap_view.iloc[0]

    col1.metric("Highest Gap State", highest_gap["state_clean"])
    col2.metric("Gap Score", round(highest_gap["infrastructure_gap_score"], 1))
    col3.metric("Chargers / Million", round(highest_gap["chargers_per_million"], 1))

    st.subheader("Infrastructure Gap Ranking")
    st.dataframe(gap_view, use_container_width=True)

    st.subheader("Infrastructure Gap Score by State")
    st.bar_chart(gap_view.set_index("state_clean")["infrastructure_gap_score"])

    st.subheader("Chargers per Million People")
    st.bar_chart(gap_view.set_index("state_clean")["chargers_per_million"])

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
    and days since the charging station was last verified.
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
    Find recommended charging stations based on charger power and reliability score.
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
    data quality, charger power, and connector availability.

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
    arrival demand, and average charging duration.
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
        - Future versions could include no-show penalties and queue priority rules.
        """)

# -----------------------------
# CONGESTION RISK ANALYSIS
# -----------------------------

elif page == "Congestion Risk Analysis":
    st.title("🚦 Congestion Risk Analysis")

    st.markdown("""
    Estimate EV charging congestion risk using charger power,
    reliability, and infrastructure availability indicators.
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
    congestion risk, and reliability.
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
    Estimate charging session cost based on battery size, charging need, and simulated electricity price.
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


# -----------------------------
# CHARGER DESERT DETECTOR
# -----------------------------

elif page == "Charger Desert Detector":
    st.title("🏜️ Charger Desert Detector")

    st.markdown("""
    Identify regions that may be underserved by EV charging infrastructure.
    This version uses charger density, ultra-fast coverage, and reliability as proxy indicators.
    """)

    st.caption(
        "Note: Desert scores use available public dataset quality, charger density, ultra-fast coverage, and reliability proxies. Scores indicate relative undersupply risk, not confirmed infrastructure failure."
    )

    desert_df = state_metrics.copy().dropna(subset=["population"])

    desert_df["desert_score"] = (
        (100 - desert_df["chargers_per_million"].clip(upper=100)) * 0.5
        + (1 - desert_df["ultra_fast_ratio"]) * 100 * 0.3
        + (100 - desert_df["avg_reliability"]) * 0.2
    )

    desert_df["desert_score"] = (
        desert_df["desert_score"].clip(lower=0, upper=100).round(2)
    )

    def desert_label(score):
        if score >= 70:
            return "High Undersupply"
        elif score >= 40:
            return "Moderate Undersupply"
        return "Lower Undersupply"

    desert_df["desert_label"] = desert_df["desert_score"].apply(desert_label)

    desert_df = desert_df.sort_values("desert_score", ascending=False)

    col1, col2, col3 = st.columns(3)

    col1.metric("Highest Desert Risk", desert_df.iloc[0]["state_clean"])
    col2.metric("Desert Score", round(desert_df.iloc[0]["desert_score"], 1))
    col3.metric("Chargers / Million", round(desert_df.iloc[0]["chargers_per_million"], 1))

    st.subheader("Charger Desert Ranking")

    st.dataframe(
        desert_df[
            [
                "state_clean",
                "population",
                "total_stations",
                "chargers_per_million",
                "ultra_fast_ratio",
                "avg_reliability",
                "desert_score",
                "desert_label",
            ]
        ],
        use_container_width=True,
    )

    st.subheader("Charger Desert Score by State")
    st.bar_chart(desert_df.set_index("state_clean")["desert_score"])

# -----------------------------
# PEAK SURGE SIMULATOR
# -----------------------------

elif page == "Peak Surge Simulator":
    st.title("🏖️ Peak Holiday Surge Simulator")

    st.markdown("""
    Simulate how holiday or long-weekend travel surges could increase charging pressure.
    """)

    surge_df = ocm_df.copy()

    selected_surge_state = st.selectbox(
        "Select State",
        sorted(surge_df["state_clean"].dropna().unique()),
        key="surge_state",
    )

    travel_surge = st.slider("Travel Demand Surge (%)", 0, 300, 100)

    avg_session_minutes = st.slider("Average Charging Session Duration", 10, 90, 35)

    surge_state_df = surge_df[surge_df["state_clean"] == selected_surge_state].copy()

    surge_state_df["total_connector_quantity"] = pd.to_numeric(
        surge_state_df["total_connector_quantity"], errors="coerce"
    ).fillna(1)

    surge_state_df["hourly_capacity"] = surge_state_df["total_connector_quantity"] * (
        60 / avg_session_minutes
    )

    base_arrivals = 10

    surge_state_df["surge_arrivals_per_hour"] = base_arrivals * (
        1 + travel_surge / 100
    )

    surge_state_df["surge_pressure_ratio"] = (
        surge_state_df["surge_arrivals_per_hour"]
        / surge_state_df["hourly_capacity"].replace(0, 1)
    )

    surge_state_df["estimated_surge_wait"] = (
        (surge_state_df["surge_pressure_ratio"] - 1).clip(lower=0)
        * avg_session_minutes
    ).round(1)

    col1, col2, col3 = st.columns(3)

    col1.metric("Stations Simulated", len(surge_state_df))
    col2.metric("Avg Surge Wait", round(surge_state_df["estimated_surge_wait"].mean(), 1))
    col3.metric("Max Surge Wait", round(surge_state_df["estimated_surge_wait"].max(), 1))

    st.subheader("Stations Most Exposed to Holiday Surge")

    st.dataframe(
        surge_state_df[
            [
                "station_name",
                "town",
                "state_clean",
                "total_connector_quantity",
                "hourly_capacity",
                "surge_arrivals_per_hour",
                "estimated_surge_wait",
                "reliability_score",
            ]
        ]
        .sort_values("estimated_surge_wait", ascending=False)
        .head(25),
        use_container_width=True,
    )

    st.subheader("Holiday Surge Wait Distribution")

    st.bar_chart(
        surge_state_df.sort_values("estimated_surge_wait", ascending=False)
        .head(20)
        .set_index("station_name")["estimated_surge_wait"]
    )

elif page == "Demand Forecast Model":

    st.title("📊 Demand Forecast Model")

    st.markdown("""
    Forecast future EV charging pressure using estimated EV fleet growth,
    charging frequency assumptions, and current charging infrastructure.
    
    This is a scenario-based demand model, not a production-grade time-series model.
    """)

    current_ev_fleet = st.number_input(
        "Estimated Current Australian EV Fleet",
        min_value=100000,
        max_value=2000000,
        value=410000,
        step=10000
    )

    annual_growth_rate = st.slider(
        "Annual EV Fleet Growth Rate (%)",
        5,
        80,
        30
    )

    forecast_years = st.slider(
        "Forecast Horizon (Years)",
        1,
        5,
        3
    )

    public_charges_per_ev_month = st.slider(
        "Average Public Charges per EV per Month",
        1,
        20,
        4
    )

    forecast_df = state_metrics.copy()
    forecast_df = forecast_df.dropna(subset=["population"])

    total_population = forecast_df["population"].sum()

    forecast_df["population_share"] = (
        forecast_df["population"] / total_population
    )

    forecast_df["estimated_current_evs"] = (
        current_ev_fleet * forecast_df["population_share"]
    )

    forecast_df["forecast_evs"] = (
        forecast_df["estimated_current_evs"]
        * ((1 + annual_growth_rate / 100) ** forecast_years)
    )

    forecast_df["monthly_public_sessions"] = (
        forecast_df["forecast_evs"]
        * public_charges_per_ev_month
    )

    forecast_df["sessions_per_station_month"] = (
        forecast_df["monthly_public_sessions"]
        / forecast_df["total_stations"]
    )

    forecast_df["demand_pressure_index"] = (
        forecast_df["sessions_per_station_month"]
        / forecast_df["sessions_per_station_month"].max()
        * 100
    ).round(2)

    def demand_label(score):
        if score >= 70:
            return "High Future Pressure"
        elif score >= 40:
            return "Moderate Future Pressure"
        return "Lower Future Pressure"

    forecast_df["demand_pressure_label"] = (
        forecast_df["demand_pressure_index"]
        .apply(demand_label)
    )

    forecast_df = forecast_df.sort_values(
        "demand_pressure_index",
        ascending=False
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Forecast National EV Fleet",
        f"{int(forecast_df['forecast_evs'].sum()):,}"
    )

    col2.metric(
        "Highest Pressure State",
        forecast_df.iloc[0]["state_clean"]
    )

    col3.metric(
        "Highest Pressure Index",
        round(forecast_df.iloc[0]["demand_pressure_index"], 1)
    )

    st.subheader("Forecast Demand Pressure by State")

    st.dataframe(
        forecast_df[
            [
                "state_clean",
                "population",
                "total_stations",
                "estimated_current_evs",
                "forecast_evs",
                "monthly_public_sessions",
                "sessions_per_station_month",
                "demand_pressure_index",
                "demand_pressure_label"
            ]
        ],
        use_container_width=True
    )

    st.subheader("Demand Pressure Index")

    st.bar_chart(
        forecast_df.set_index("state_clean")["demand_pressure_index"]
    )

    st.subheader("Forecast EV Fleet by State")

    st.bar_chart(
        forecast_df.set_index("state_clean")["forecast_evs"]
    )

elif page == "Model Assumptions":

    st.title("📘 Model Assumptions")

    st.markdown("""
    ### Why this page matters

    ChargeSense uses public EV infrastructure datasets and scenario-based models.
    Some outputs are analytical estimates, not confirmed real-world measurements.

    ### Key Assumptions

    **1. Reliability Score**  
    Based on recent verification, data quality, and days since last verified.

    **2. Infrastructure Gap Score**  
    Combines charger density, ultra-fast coverage, and average reliability.

    **3. Congestion Risk Score**  
    Uses charger power, reliability, and state-level infrastructure availability as proxy inputs.

    **4. Demand Forecast Model**  
    Uses estimated EV fleet growth, population share, public charging frequency, and current station count.

    **5. Queue Simulation**  
    Estimates wait time using arrivals per hour, connector count, and average charging session duration.

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
    - Add suburb/LGA-level population and EV registration data
    - Train models on historical failure and usage records
    """)

elif page == "Real Route Optimizer":

    st.title("🛰️ Real Route Optimizer")

    st.markdown("""
    Generate a real driving route and identify high-quality EV charging stations near the route.

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

    route_input_mode = st.radio(
        "Route Input Mode",
        [
            "Major City",
            "Custom Place"
        ],
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
        charge_to_percent = st.slider(
            "Target Battery After Charging (%)",
            50,
            100,
            80
        )

    if st.button("Generate Real Route"):

        if charge_to_percent <= charge_from_percent:
            st.warning("Target battery must be higher than minimum arrival battery.")
            st.stop()

        if route_input_mode == "Major City":

            if start_label == destination_label:
                st.warning("Start city and destination city cannot be the same.")
                st.stop()

        else:

            if start_place.strip() == "" or destination_place.strip() == "":
                st.warning("Please enter both a start location and destination.")
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
                "Selected EV Range",
                f"{ev_range_km} km"
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
                near_route_df["route_score"]
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

            st.subheader("Recommended Charging Stops Near Route")

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
                        "route_score",
                        "route_recommendation_score",
                        "distance_to_route_km"
                    ]
                ],
                use_container_width=True
            )

            st.subheader("Suggested Charging Stop Sequence")

            usable_start_range_km = ev_range_km * (starting_battery_percent / 100)

            usable_after_charge_range_km = ev_range_km * ((charge_to_percent - charge_from_percent) / 100)

            safe_start_range_km = max(usable_start_range_km - safety_buffer_km, 1)

            safe_after_charge_range_km = max( usable_after_charge_range_km - safety_buffer_km, 1)

            route_stop_targets = []
            distance_covered = safe_start_range_km
            while distance_covered < distance_km:
                 route_stop_targets.append(distance_covered)
                 distance_covered += safe_after_charge_range_km
    
            sequence_stops = []
            used_station_names = set()

            current_battery_percent = starting_battery_percent
            previous_distance_km = 0

            for target_distance in route_stop_targets:

                leg_distance_km = target_distance - previous_distance_km

                battery_used_percent = (
                    leg_distance_km / ev_range_km
                ) * 100

                arrival_battery_percent = max(
                    current_battery_percent - battery_used_percent,
                    0
                )

                if arrival_battery_percent < charge_from_percent:
                    st.warning(
                        f"Battery may drop below the selected minimum arrival battery before stop "
                        f"{len(sequence_stops) + 1}. Consider increasing starting battery, reducing safety buffer, "
                        f"or choosing a longer-range EV."
                    )

                charge_needed_percent = max(
                    charge_to_percent - arrival_battery_percent,
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

                candidate_stops = recommended_stops.copy()

                candidate_stops["distance_to_target_km"] = (
                    candidate_stops.apply(
                        lambda row: haversine_distance(
                            row["latitude"],
                            row["longitude"],
                            target_point["latitude"],
                            target_point["longitude"]
                        ),
                        axis=1
                    )
                )

                candidate_stops = candidate_stops[
                    ~candidate_stops["station_name"].isin(used_station_names)
                ]

                if len(candidate_stops) == 0:
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

                charger_power_kw = max(
                    float(best_stop["max_power_kw"])
                    if pd.notna(best_stop["max_power_kw"])
                    else 1,
                    1
                )

                estimated_charge_time_min = (
                    energy_needed_kwh / charger_power_kw
                ) * 60

                departure_battery_percent = min(
                    arrival_battery_percent + charge_needed_percent,
                    100
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
                    "route_score": best_stop["route_score"],
                    "arrival_battery_%": round(arrival_battery_percent, 1),
                    "departure_battery_%": round(departure_battery_percent, 1),
                    "estimated_charge_kwh": round(energy_needed_kwh, 1),
                    "estimated_charge_time_min": round(estimated_charge_time_min, 1),
                    "distance_to_target_km": round(
                        best_stop["distance_to_target_km"],
                        1
                    )
                })

            if len(sequence_stops) == 0:

                st.success(
                    "No charging stop required based on selected EV range."
                )

            else:

                sequence_df = pd.DataFrame(sequence_stops)

                st.dataframe(
                    sequence_df,
                    use_container_width=True
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
                    "route_score": True,
                    "route_recommendation_score": True,
                    "distance_to_route_km": True,
                    "latitude": False,
                    "longitude": False,
                    "plot_size": False
                },
                color="route_recommendation_score",
                size="plot_size",
                zoom=4,
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
    Ultra-fast charger coverage matters more for long-distance travel and queue reduction.

    **2. Reliability is a major product opportunity.**  
    A charger may exist in the dataset, but stale verification data reduces user trust.

    **3. Reservation systems can reduce queue uncertainty.**  
    Short booking windows with temporary access codes could help manage high-demand charging sites.

    **4. Public EV datasets need cleaning.**  
    Inconsistent state and location metadata show why infrastructure data products need strong data quality checks.

    **5. Charging type mix reveals infrastructure maturity.**  
    Regions with more ultra-fast DC chargers are better positioned for long-distance EV adoption and queue reduction.

    **6. Scenario forecasting helps evaluate future pressure.**  
    Growth simulations can highlight which states may need stronger infrastructure investment as EV adoption rises.

    **7. Charger trust is a product opportunity.**  
    Combining reliability, freshness, power, and connector availability can help drivers choose better stations.

    **8. ChargeSense can evolve into a decision-support tool.**  
    Future versions could support charger investment planning, congestion forecasting,
    live availability, and smart route recommendations.
    """)
