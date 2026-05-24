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
elif page == "Congestion Risk Analysis":

    st.title("🚦 Congestion Risk Analysis")

    st.markdown("""
    Estimate EV charging congestion risk using charger power,
    reliability, and infrastructure availability indicators.
    """)

    congestion_df = ocm_df.copy()

    congestion_df["max_power_kw"] = (
        congestion_df["max_power_kw"]
        .fillna(0)
    )

    # Higher congestion risk:
    # - lower charger power
    # - lower reliability
    # - fewer stations

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
        (
            100
            - congestion_df["reliability_score"]
        ) * 0.4
        +
        (
            150
            - congestion_df["max_power_kw"]
            .clip(upper=150)
        ) * 0.3
        +
        (
            100
            / congestion_df["state_station_count"]
            .clip(lower=1)
        ) * 30
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
        else:
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
        .sort_values(
            "congestion_risk_score",
            ascending=False
        )
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

    **5. ChargeSense can evolve into a decision-support tool.**  
    Future versions could support charger investment planning, congestion forecasting, and smart route recommendations.
    """)
