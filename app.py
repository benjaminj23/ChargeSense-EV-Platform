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
        min_power = st.slider(
            "Minimum Charger Power (kW)",
            0,
            int(ocm_df["max_power_kw"].fillna(0).max()),
            0
        )

    map_df = ocm_df[
        (ocm_df["state_clean"] == selected_state)
        &
        (ocm_df["max_power_kw"].fillna(0) >= min_power)
    ].copy()

    map_df = map_df.dropna(
        subset=["latitude", "longitude"]
    )

    map_df["max_power_kw"] = (
        pd.to_numeric(
            map_df["max_power_kw"],
            errors="coerce"
        )
        .fillna(1)
    )

    map_df["plot_size"] = (
        map_df["max_power_kw"]
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
            margin={"r":0,"t":0,"l":0,"b":0}
        )

        st.plotly_chart(fig, use_container_width=True)
