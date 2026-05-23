import streamlit as st
import pandas as pd
import plotly.express as px

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
    else:
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
        "Reservation Simulation"
    ]
)

# -----------------------------------
# HOME
# -----------------------------------

if page == "Home":

    st.title("⚡ ChargeSense")
    st.subheader("EV Infrastructure Intelligence Platform")

    st.markdown("""
    Explore EV charging infrastructure, congestion risk, reliability intelligence,
    and reservation simulation using public EV charging data.
    """)

    st.success("Platform loaded successfully")

# -----------------------------------
# INFRASTRUCTURE OVERVIEW
# -----------------------------------

elif page == "Infrastructure Overview":

    st.title("Infrastructure Overview")

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

    st.title("Interactive Charger Map")

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

    map_df = map_df.dropna(subset=["latitude", "longitude"])

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

    st.title("Reliability Intelligence")

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
# RESERVATION SIMULATION
# -----------------------------------

elif page == "Reservation Simulation":

    st.title("Reservation Simulation")

    st.markdown("""
    Simulate a short reservation window for high-priority EV charging stations.
    This is a prototype of the booking/passcode concept.
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

    if st.button("Simulate Reservation"):

        st.success(f"Reservation confirmed for {selected_station}")
        st.info(f"Access window: {reservation_minutes} minutes")
        st.code("PASSCODE: CHARGE2026")
