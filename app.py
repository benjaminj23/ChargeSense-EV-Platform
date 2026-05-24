import random
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

# -----------------------------------
# PAGE CONFIG
# -----------------------------------

st.set_page_config(
    page_title="ChargeSense",
    layout="wide"
)

# -----------------------------------
# LOAD DATA
# -----------------------------------

@st.cache_data
def load_data():
    nsw_df = pd.read_csv("ev_chargers_nsw_enriched.csv")
    ocm_df = pd.read_csv("openchargemap_au_enriched.csv")
    return nsw_df, ocm_df

nsw_df, ocm_df = load_data()

# -----------------------------------
# DATA PREP
# -----------------------------------
state_population = {
    "New South Wales": 8500000,
    "Victoria": 6900000,
    "Queensland": 5600000,
    "Western Australia": 3000000,
    "South Australia": 1900000,
    "Tasmania": 575000,
    "ACT": 470000,
    "Northern Territory": 260000
}
ocm_df["population"] = (
    ocm_df["state_clean"]
    .map(state_population)
)
state_metrics = (
    ocm_df.groupby("state_clean")
    .agg(
        total_stations=("station_name", "count"),
        avg_power_kw=("max_power_kw", "mean"),
        avg_reliability=("reliability_score", "mean"),
        ultra_fast_sites=(
            "speed_category",
            lambda x: (x == "Ultra-fast DC").sum()
        ),
        population=("population", "first")
    )
    .reset_index()
)

state_metrics["chargers_per_million"] = (
    state_metrics["total_stations"]
    / state_metrics["population"]
) * 1_000_000

state_metrics["ultra_fast_ratio"] = (
    state_metrics["ultra_fast_sites"]
    / state_metrics["total_stations"]
)

state_metrics["infrastructure_gap_score"] = (
    (
        100
        - state_metrics["chargers_per_million"]
        .clip(upper=100)
    ) * 0.4
    +
    (
        100
        - state_metrics["avg_reliability"]
    ) * 0.3
    +
    (
        1
        - state_metrics["ultra_fast_ratio"]
    ) * 100 * 0.3
)

state_metrics["infrastructure_gap_score"] = (
    state_metrics["infrastructure_gap_score"]
    .clip(lower=0, upper=100)
    .round(2)
)

ocm_df["max_power_kw"] = pd.to_numeric(
    ocm_df["max_power_kw"],
    errors="coerce"
)

ocm_df["date_last_verified"] = pd.to_datetime(
    ocm_df["date_last_verified"],
    errors="coerce"
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
    ocm_df["data_quality_level"],
    errors="coerce"
).fillna(0)

ocm_df["reliability_score"] = (
    (ocm_df["is_recently_verified"] * 50)
    + (ocm_df["data_quality_level"] * 30)
    - (ocm_df["days_since_verified"].fillna(365) * 0.2)
)

ocm_df["reliability_score"] = (
    ocm_df["reliability_score"]
    .clip(lower=0, upper=100)
    .round(2)
)

def reliability_label(score):
    if score >= 70:
        return "High"
    elif score >= 40:
        return "Medium"
    elif score > 0:
        return "Low"
    return "Unknown / Stale"

ocm_df["reliability_label"] = ocm_df["reliability_score"].apply(reliability_label)

# -----------------------------------
# SIDEBAR
# -----------------------------------

st.sidebar.title("⚡ ChargeSense")

page = st.sidebar.radio(
    "Navigate",
    [
        "Home",
        "Infrastructure Overview",
        "Interactive Map",
        "Reliability Intelligence",
        "Charger Recommendation",
        "Reservation Simulation",
        "Congestion Risk Analysis",
        "Charging Type Mix",
        "Infrastructure Gap Analysis",
        "Future Pressure Forecast",
        "Project Insights"
    ]
)

# -----------------------------------
# HOME
# -----------------------------------

if page == "Home":

    st.title("⚡ ChargeSense")
    st.subheader("EV Infrastructure Intelligence Platform")

    st.markdown("""
    ChargeSense is an EV Infrastructure Intelligence Platform designed to analyze
    charging reliability, infrastructure quality, congestion risk, and charging accessibility
    across Australia.

    Features include:
    - Interactive infrastructure mapping
    - Reliability intelligence scoring
    - Charger recommendation engine
    - Reservation simulation
    - Congestion risk analysis
    - Operator fragmentation analysis
    - National EV infrastructure analytics
    """)

    st.success("Platform loaded successfully")

    st.divider()

    st.caption(
        "Built using Python, Streamlit, OpenChargeMap API data, and NSW EV infrastructure data."
    )

    st.link_button(
        "View GitHub Repository",
        "YOUR_GITHUB_LINK"
    )

# -----------------------------------
# INFRASTRUCTURE OVERVIEW
# -----------------------------------

elif page == "Infrastructure Overview":

    st.title("📊 Infrastructure Overview")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Stations", len(ocm_df))

    col2.metric(
        "Ultra-fast Chargers",
        len(ocm_df[ocm_df["max_power_kw"] >= 150])
    )

    col3.metric(
        "Average Charger Power",
        round(ocm_df["max_power_kw"].mean(), 1)
    )

    col4.metric(
        "States Covered",
        ocm_df["state_clean"].nunique()
    )

    st.divider()

    state_summary = (
        ocm_df.groupby("state_clean")
        .size()
        .reset_index(name="stations")
        .sort_values("stations", ascending=False)
    )

    st.subheader("EV Charging Stations by State")
    st.bar_chart(state_summary.set_index("state_clean"))

# -----------------------------------
# INTERACTIVE MAP
# -----------------------------------

elif page == "Interactive Map":

    st.title("🗺️ Interactive Charger Map")

    st.markdown(
        "Explore EV charging stations across Australia using OpenChargeMap data."
    )

    col1, col2 = st.columns(2)

    with col1:
        selected_state = st.selectbox(
            "Select State",
            sorted(ocm_df["state_clean"].dropna().unique())
        )

    with col2:
        max_power_available = int(ocm_df["max_power_kw"].fillna(0).max())

        min_power = st.slider(
            "Minimum Charger Power (kW)",
            0,
            max_power_available,
            0
        )

    map_df = ocm_df[
        (ocm_df["state_clean"] == selected_state)
        & (ocm_df["max_power_kw"].fillna(0) >= min_power)
    ].copy()

    map_df["latitude"] = pd.to_numeric(
        map_df["latitude"],
        errors="coerce"
    )

    map_df["longitude"] = pd.to_numeric(
        map_df["longitude"],
        errors="coerce"
    )

    map_df = map_df.dropna(subset=["latitude", "longitude"])

    map_df["plot_size"] = (
        map_df["max_power_kw"]
        .fillna(1)
        .clip(lower=5, upper=350)
    )

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
                "plot_size": False
            },
            color="speed_category",
            size="plot_size",
            zoom=5,
            height=650
        )

        fig.update_layout(
            mapbox_style="open-street-map",
            margin={"r": 0, "t": 0, "l": 0, "b": 0}
        )

        st.plotly_chart(fig, use_container_width=True)

# -----------------------------------
# RELIABILITY INTELLIGENCE
# -----------------------------------

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
                "days_since_verified"
            ]
        ]
        .sort_values("reliability_score", ascending=False)
    )

    st.subheader("Top Reliable Charging Stations")

    st.dataframe(
        reliability_view.head(20),
        use_container_width=True
    )

    st.subheader("Reliability Label Distribution")

    reliability_dist = (
        ocm_df["reliability_label"]
        .value_counts()
        .reset_index()
    )

    reliability_dist.columns = ["Reliability Label", "Count"]

    st.bar_chart(
        reliability_dist.set_index("Reliability Label")
    )

# -----------------------------------
# CHARGER RECOMMENDATION
# -----------------------------------

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
            key="rec_state"
        )

    with col2:
        min_rec_power = st.slider(
            "Minimum Power (kW)",
            0,
            int(ocm_df["max_power_kw"].fillna(0).max()),
            50
        )

    with col3:
        min_reliability = st.slider(
            "Minimum Reliability Score",
            0,
            100,
            40
        )

    rec_df = ocm_df[
        (ocm_df["state_clean"] == rec_state)
        & (ocm_df["max_power_kw"].fillna(0) >= min_rec_power)
        & (ocm_df["reliability_score"].fillna(0) >= min_reliability)
    ].copy()

    rec_df["recommendation_score"] = (
        rec_df["max_power_kw"].fillna(0) * 0.6
        + rec_df["reliability_score"].fillna(0) * 0.4
    )

    rec_df = rec_df.sort_values(
        "recommendation_score",
        ascending=False
    )

    st.metric(
        "Recommended Stations Found",
        len(rec_df)
    )

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
                    "recommendation_score"
                ]
            ].head(15),
            use_container_width=True
        )

# -----------------------------------
# RESERVATION SIMULATION
# -----------------------------------

elif page == "Reservation Simulation":

    st.title("🔐 Reservation Simulation")

    st.markdown("""
    Simulate a short reservation window for high-priority EV charging stations.
    This is a prototype of the booking/access-code concept.
    """)

    top_sites = (
        nsw_df[
            [
                "Station_name",
                "Operator",
                "reservation_need_index"
            ]
        ]
        .dropna(subset=["Station_name"])
        .sort_values("reservation_need_index", ascending=False)
    )

    selected_station = st.selectbox(
        "Select Charging Station",
        top_sites["Station_name"].unique()
    )

    reservation_minutes = st.slider(
        "Reservation Duration (minutes)",
        15,
        60,
        20
    )

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

# -----------------------------------
# CONGESTION RISK ANALYSIS
# -----------------------------------

elif page == "Congestion Risk Analysis":

    st.title("🚦 Congestion Risk Analysis")

    st.markdown("""
    Estimate EV charging congestion risk using charger power,
    reliability, and infrastructure availability indicators.
    """)

    congestion_df = ocm_df.copy()

    congestion_df["max_power_kw"] = congestion_df["max_power_kw"].fillna(0)

    state_station_counts = (
        congestion_df.groupby("state_clean")
        .size()
        .to_dict()
    )

    congestion_df["state_station_count"] = (
        congestion_df["state_clean"]
        .map(state_station_counts)
    )

    congestion_df["congestion_risk_score"] = (
        ((100 - congestion_df["reliability_score"]) * 0.4)
        + ((150 - congestion_df["max_power_kw"].clip(upper=150)) * 0.3)
        + ((100 / congestion_df["state_station_count"].clip(lower=1)) * 30)
    )

    congestion_df["congestion_risk_score"] = (
        congestion_df["congestion_risk_score"]
        .clip(lower=0, upper=100)
        .round(2)
    )

    def congestion_label(score):
        if score >= 70:
            return "High Risk"
        elif score >= 40:
            return "Medium Risk"
        return "Low Risk"

    congestion_df["congestion_label"] = (
        congestion_df["congestion_risk_score"]
        .apply(congestion_label)
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
                "congestion_label"
            ]
        ]
        .sort_values("congestion_risk_score", ascending=False)
    )

    st.dataframe(
        risk_view.head(20),
        use_container_width=True
    )

    st.subheader("Congestion Risk Distribution")

    congestion_dist = (
        congestion_df["congestion_label"]
        .value_counts()
        .reset_index()
    )

    congestion_dist.columns = [
        "Congestion Risk",
        "Count"
    ]

    st.bar_chart(
        congestion_dist.set_index("Congestion Risk")
    )

elif page == "Charging Type Mix":

    st.title("🔌 Charging Type Mix")

    st.markdown("""
    Analyze the mix of charger speed categories across Australian states.
    This helps identify whether regions are relying mainly on slower AC infrastructure
    or building stronger fast and ultra-fast charging capacity.
    """)

    selected_state_mix = st.selectbox(
        "Select State",
        sorted(ocm_df["state_clean"].dropna().unique()),
        key="mix_state"
    )

    mix_df = ocm_df[
        ocm_df["state_clean"] == selected_state_mix
    ]

    speed_mix = (
        mix_df["speed_category"]
        .fillna("Unknown")
        .value_counts()
        .reset_index()
    )

    speed_mix.columns = ["Speed Category", "Count"]

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Total Stations",
        len(mix_df)
    )

    col2.metric(
        "Ultra-fast Sites",
        len(mix_df[mix_df["speed_category"] == "Ultra-fast DC"])
    )

    col3.metric(
        "Average Power (kW)",
        round(mix_df["max_power_kw"].mean(), 1)
    )

    st.subheader("Charging Speed Category Mix")

    st.bar_chart(
        speed_mix.set_index("Speed Category")
    )

    st.subheader("Station Details")

    st.dataframe(
        mix_df[
            [
                "station_name",
                "town",
                "state_clean",
                "max_power_kw",
                "speed_category",
                "reliability_score"
            ]
        ].head(30),
        use_container_width=True
    )
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
                "infrastructure_gap_score"
            ]
        ]
        .sort_values("infrastructure_gap_score", ascending=False)
    )

    col1, col2, col3 = st.columns(3)

    highest_gap = gap_view.iloc[0]

    col1.metric(
        "Highest Gap State",
        highest_gap["state_clean"]
    )

    col2.metric(
        "Gap Score",
        round(highest_gap["infrastructure_gap_score"], 1)
    )

    col3.metric(
        "Chargers / Million",
        round(highest_gap["chargers_per_million"], 1)
    )

    st.subheader("Infrastructure Gap Ranking")

    st.dataframe(
        gap_view,
        use_container_width=True
    )

    st.subheader("Infrastructure Gap Score by State")

    st.bar_chart(
        gap_view.set_index("state_clean")["infrastructure_gap_score"]
    )

    st.subheader("Chargers per Million People")

    st.bar_chart(
        gap_view.set_index("state_clean")["chargers_per_million"]
    )
elif page == "Future Pressure Forecast":

    st.title("📈 Future Pressure Forecast")

    st.markdown("""
    Simulate how future EV adoption growth could increase pressure on charging infrastructure.
    This is a scenario-based forecast, not a live demand prediction model.
    """)

    demand_growth = st.slider(
        "Projected EV Demand Growth (%)",
        0,
        200,
        50
    )

    forecast_df = state_metrics.copy()

    forecast_df["future_demand_index"] = (
        forecast_df["population"]
        * (1 + demand_growth / 100)
    )

    forecast_df["future_pressure_score"] = (
        forecast_df["future_demand_index"]
        / (
            forecast_df["total_stations"]
            * forecast_df["avg_power_kw"].fillna(1)
        )
    )

    forecast_df["future_pressure_score"] = (
        forecast_df["future_pressure_score"]
        / forecast_df["future_pressure_score"].max()
        * 100
    ).round(2)

    forecast_df = forecast_df.sort_values(
        "future_pressure_score",
        ascending=False
    )

    st.subheader("Future Charging Pressure by State")

    st.dataframe(
        forecast_df[
            [
                "state_clean",
                "population",
                "total_stations",
                "avg_power_kw",
                "chargers_per_million",
                "future_pressure_score"
            ]
        ],
        use_container_width=True
    )

    st.subheader("Forecasted Future Pressure Score")

    st.bar_chart(
        forecast_df.set_index("state_clean")["future_pressure_score"]
    )
# -----------------------------------
# PROJECT INSIGHTS
# -----------------------------------

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

    **6. ChargeSense can evolve into a decision-support tool.**  
    Future versions could support charger investment planning, congestion forecasting,
    live availability, and smart route recommendations.
    """)
