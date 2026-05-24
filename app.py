import random
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
    (ocm_df["is_recently_verified"] * 50)
    + (ocm_df["data_quality_level"] * 30)
    - (ocm_df["days_since_verified"].fillna(365) * 0.2)
)

ocm_df["reliability_score"] = (
    ocm_df["reliability_score"].clip(lower=0, upper=100).round(2)
)
# normalize reliability scores
max_rel = ocm_df["reliability_score"].max()

if max_rel > 0:
    ocm_df["reliability_score_normalized"] = (
        ocm_df["reliability_score"] / max_rel
    ) * 100
else:
    ocm_df["reliability_score_normalized"] = 0

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
        avg_reliability_normalized=( "reliability_score_normalized", "mean"),,
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
    + (100 - state_metrics["avg_reliability_normalized"]) * 0.3
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
        "Future Pressure Forecast",
        "Route Intelligence",
        "Dynamic Pricing Simulator",
        "Charging Cost Simulator",
        "Availability Stress Test",
        "EV Adoption Impact",
        "Charger Desert Detector",
        "Peak Surge Simulator",
        "Charging Type Mix",
        "Charger Trust Scorecard",
        "Demand Forecast Model",
        "Model Assumptions",
        "Network Health Dashboard",
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
    future pressure, route intelligence, and charging operations across Australia.

    Features include:
    - Interactive infrastructure mapping
    - Reliability intelligence scoring
    - Charger recommendation engine
    - Reservation simulation
    - Congestion risk analysis
    - Future pressure forecasting
    - Route intelligence
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
                "avg_reliability_normalized",
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
# FUTURE PRESSURE FORECAST
# -----------------------------

elif page == "Future Pressure Forecast":
    st.title("📈 Future Pressure Forecast")

    st.markdown("""
    Simulate how future EV adoption growth could increase pressure on charging infrastructure.
    This is a scenario-based forecast, not a live demand prediction model.
    """)

    demand_growth = st.slider("Projected EV Demand Growth (%)", 0, 200, 50)

    forecast_df = state_metrics.copy().dropna(subset=["population"])

    forecast_df["base_pressure"] = forecast_df["population"] / (
        forecast_df["total_stations"] * forecast_df["avg_power_kw"].fillna(1)
    )

    forecast_df["growth_multiplier"] = 1 + (demand_growth / 100)

    forecast_df["future_pressure_score"] = (
        forecast_df["base_pressure"] * forecast_df["growth_multiplier"]
    ).round(2)

    forecast_df["additional_pressure"] = (
        forecast_df["future_pressure_score"] - forecast_df["base_pressure"]
    ).round(2)

    forecast_df = forecast_df.sort_values("future_pressure_score", ascending=False)

    st.subheader("Future Charging Pressure by State")

    st.dataframe(
        forecast_df[
            [
                "state_clean",
                "population",
                "total_stations",
                "avg_power_kw",
                "chargers_per_million",
                "base_pressure",
                "future_pressure_score",
                "additional_pressure",
            ]
        ],
        use_container_width=True,
    )

    st.subheader("Forecasted Future Pressure Score")
    st.bar_chart(forecast_df.set_index("state_clean")["future_pressure_score"])

    st.subheader("Additional Pressure from Growth Scenario")
    st.bar_chart(forecast_df.set_index("state_clean")["additional_pressure"])

# -----------------------------
# ROUTE INTELLIGENCE
# -----------------------------

elif page == "Route Intelligence":
    st.title("🛣️ Route Intelligence")

    st.markdown("""
    Select a start city and destination city to find recommended EV charging stops.
    This prototype recommends chargers based on route-relevant states, charger power, and reliability.
    """)

    city_state_map = {
        "Sydney": "New South Wales",
        "Melbourne": "Victoria",
        "Brisbane": "Queensland",
        "Canberra": "ACT",
        "Adelaide": "South Australia",
        "Perth": "Western Australia",
        "Hobart": "Tasmania",
        "Darwin": "Northern Territory",
        "Gold Coast": "Queensland",
        "Newcastle": "New South Wales",
        "Wollongong": "New South Wales",
        "Geelong": "Victoria",
    }

    cities = sorted(city_state_map.keys())

    col1, col2 = st.columns(2)

    with col1:
        start_city = st.selectbox("Start City", cities, index=cities.index("Sydney"))

    with col2:
        destination_city = st.selectbox(
            "Destination City", cities, index=cities.index("Melbourne")
        )

    start_state = city_state_map[start_city]
    destination_state = city_state_map[destination_city]

    route_states = list(set([start_state, destination_state]))

    st.info(
        f"Route corridor: {start_city} ({start_state}) → {destination_city} ({destination_state})"
    )

    route_df = ocm_df[ocm_df["state_clean"].isin(route_states)].copy()

    route_df["route_score"] = (
        route_df["max_power_kw"].fillna(0) * 0.6
        + route_df["reliability_score"].fillna(0) * 0.4
    )

    route_df = route_df.sort_values("route_score", ascending=False)

    st.metric("Recommended Stops Found", len(route_df))

    st.subheader("Top Recommended Charging Stops")

    if len(route_df) == 0:
        st.warning("No charging stops found for this city pair.")
    else:
        st.dataframe(
            route_df[
                [
                    "station_name",
                    "town",
                    "state_clean",
                    "max_power_kw",
                    "reliability_score",
                    "reliability_label",
                    "route_score",
                ]
            ].head(20),
            use_container_width=True,
        )

    st.subheader("Route Charging Map")

    map_route_df = route_df.copy()

    map_route_df["latitude"] = pd.to_numeric(
        map_route_df["latitude"], errors="coerce"
    )
    map_route_df["longitude"] = pd.to_numeric(
        map_route_df["longitude"], errors="coerce"
    )

    map_route_df = map_route_df.dropna(subset=["latitude", "longitude"])

    map_route_df["plot_size"] = map_route_df["max_power_kw"].fillna(1).clip(
        lower=5, upper=350
    )

    if len(map_route_df) == 0:
        st.warning("No mappable charging stops found for this route.")
    else:
        fig = px.scatter_mapbox(
            map_route_df.head(150),
            lat="latitude",
            lon="longitude",
            hover_name="station_name",
            hover_data={
                "town": True,
                "state_clean": True,
                "max_power_kw": True,
                "reliability_score": True,
                "route_score": True,
                "latitude": False,
                "longitude": False,
                "plot_size": False,
            },
            color="route_score",
            size="plot_size",
            zoom=4,
            height=650,
        )

        fig.update_layout(
            mapbox_style="open-street-map",
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
        )

        st.plotly_chart(fig, use_container_width=True)

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
# EV ADOPTION IMPACT
# -----------------------------

elif page == "EV Adoption Impact":
    st.title("🚗 EV Adoption Impact Simulator")

    st.markdown("""
    Simulate how rising EV adoption could affect charger demand pressure by state.
    """)

    selected_adoption_state = st.selectbox(
        "Select State",
        sorted(state_metrics["state_clean"].dropna().unique()),
        key="adoption_state",
    )

    ev_adoption_rate = st.slider("Estimated EV Adoption Rate (% of population)", 1, 30, 5)

    avg_charges_per_ev_month = st.slider(
        "Average Public Charges per EV per Month", 1, 20, 4
    )

    adoption_row = state_metrics[
        state_metrics["state_clean"] == selected_adoption_state
    ].iloc[0]

    estimated_evs = adoption_row["population"] * ev_adoption_rate / 100

    monthly_public_charging_sessions = estimated_evs * avg_charges_per_ev_month

    sessions_per_station_month = (
        monthly_public_charging_sessions / adoption_row["total_stations"]
    )

    col1, col2, col3 = st.columns(3)

    col1.metric("Estimated EVs", f"{int(estimated_evs):,}")
    col2.metric(
        "Monthly Public Charging Sessions",
        f"{int(monthly_public_charging_sessions):,}",
    )
    col3.metric("Sessions per Station / Month", f"{round(sessions_per_station_month, 1)}")

    if sessions_per_station_month > 1000:
        st.error("High pressure: current charging infrastructure may struggle.")
    elif sessions_per_station_month > 500:
        st.warning("Moderate pressure: infrastructure expansion may be needed.")
    else:
        st.success("Lower pressure: current infrastructure appears manageable.")

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
        + (100 - desert_df["avg_reliability_normalized"]) * 0.2
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
                "avg_reliability_normalized",
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

# -----------------------------
# CHARGING TYPE MIX
# -----------------------------

elif page == "Charging Type Mix":
    st.title("🔌 Charging Type Mix")

    st.markdown("""
    Analyze the mix of charger speed categories across Australian states.
    """)

    selected_state_mix = st.selectbox(
        "Select State",
        sorted(ocm_df["state_clean"].dropna().unique()),
        key="mix_state",
    )

    mix_df = ocm_df[ocm_df["state_clean"] == selected_state_mix]

    speed_mix = mix_df["speed_category"].fillna("Unknown").value_counts().reset_index()
    speed_mix.columns = ["Speed Category", "Count"]

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Stations", len(mix_df))
    col2.metric("Ultra-fast Sites", len(mix_df[mix_df["speed_category"] == "Ultra-fast DC"]))
    col3.metric("Average Power (kW)", round(mix_df["max_power_kw"].mean(), 1))

    st.subheader("Charging Speed Category Mix")
    st.bar_chart(speed_mix.set_index("Speed Category"))

    st.subheader("Station Details")

    st.dataframe(
        mix_df[
            [
                "station_name",
                "town",
                "state_clean",
                "max_power_kw",
                "speed_category",
                "reliability_score",
            ]
        ].head(30),
        use_container_width=True,
    )

# -----------------------------
# CHARGER TRUST SCORECARD
# -----------------------------

elif page == "Charger Trust Scorecard":
    st.title("⭐ Charger Trust Scorecard")

    st.markdown("""
    Compare charging stations using a combined trust score based on reliability,
    charger speed, connector availability, and data freshness.
    """)

    trust_df = ocm_df.copy()

    trust_df["max_power_kw"] = pd.to_numeric(
        trust_df["max_power_kw"], errors="coerce"
    ).fillna(0)

    trust_df["total_connector_quantity"] = pd.to_numeric(
        trust_df["total_connector_quantity"], errors="coerce"
    ).fillna(1)

    trust_df["power_score"] = trust_df["max_power_kw"].clip(upper=350) / 350 * 100

    trust_df["connector_score"] = (
        trust_df["total_connector_quantity"].clip(upper=8) / 8 * 100
    )

    trust_df["freshness_score"] = (
        100
        - trust_df["days_since_verified"].fillna(365).clip(upper=365) / 365 * 100
    )

    trust_df["trust_score"] = (
        trust_df["reliability_score"].fillna(0) * 0.4
        + trust_df["power_score"] * 0.25
        + trust_df["connector_score"] * 0.2
        + trust_df["freshness_score"] * 0.15
    ).round(2)

    selected_trust_state = st.selectbox(
        "Select State",
        sorted(trust_df["state_clean"].dropna().unique()),
        key="trust_state",
    )

    trust_state_df = trust_df[
        trust_df["state_clean"] == selected_trust_state
    ].sort_values("trust_score", ascending=False)

    col1, col2, col3 = st.columns(3)

    col1.metric("Stations Scored", len(trust_state_df))
    col2.metric("Average Trust Score", round(trust_state_df["trust_score"].mean(), 1))
    col3.metric("Top Trust Score", round(trust_state_df["trust_score"].max(), 1))

    st.subheader("Top Trusted Charging Stations")

    st.dataframe(
        trust_state_df[
            [
                "station_name",
                "town",
                "state_clean",
                "max_power_kw",
                "total_connector_quantity",
                "reliability_score",
                "days_since_verified",
                "trust_score",
            ]
        ].head(25),
        use_container_width=True,
    )

    st.subheader("Trust Score Distribution")

    st.bar_chart(
        trust_state_df.head(20).set_index("station_name")["trust_score"]
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

elif page == "Network Health Dashboard":

    st.title("🛰️ Network Health Dashboard")

    st.markdown("""
    Simulate real-time EV charging network health monitoring using reliability,
    freshness, congestion, and availability indicators.
    """)

    health_df = ocm_df.copy()

    health_df["health_score"] = (
        health_df["reliability_score"].fillna(0) * 0.5
        + (100 - health_df["days_since_verified"].fillna(365).clip(upper=365) / 365 * 100) * 0.3
        + health_df["max_power_kw"].fillna(0).clip(upper=350) / 350 * 100 * 0.2
    )

    health_df["health_score"] = (
        health_df["health_score"]
        .clip(lower=0, upper=100)
        .round(2)
    )

    def health_status(score):
        if score >= 70:
            return "Healthy"
        elif score >= 40:
            return "Degraded"
        return "Critical"

    health_df["health_status"] = (
        health_df["health_score"]
        .apply(health_status)
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Total Stations",
        len(health_df)
    )

    col2.metric(
        "Healthy",
        len(health_df[health_df["health_status"] == "Healthy"])
    )

    col3.metric(
        "Degraded",
        len(health_df[health_df["health_status"] == "Degraded"])
    )

    col4.metric(
        "Critical",
        len(health_df[health_df["health_status"] == "Critical"])
    )

    st.subheader("Network Health Status Distribution")

    health_dist = (
        health_df["health_status"]
        .value_counts()
        .reset_index()
    )

    health_dist.columns = ["Health Status", "Count"]

    st.bar_chart(
        health_dist.set_index("Health Status")
    )

    st.subheader("Critical Stations")

    critical_df = (
        health_df[
            health_df["health_status"] == "Critical"
        ]
        .sort_values("health_score")
    )

    st.dataframe(
        critical_df[
            [
                "station_name",
                "town",
                "state_clean",
                "max_power_kw",
                "reliability_score",
                "days_since_verified",
                "health_score",
                "health_status"
            ]
        ]
        .head(25),
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
