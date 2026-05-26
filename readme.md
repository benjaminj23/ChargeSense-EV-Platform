# ChargeSense: EV Infrastructure Intelligence and Route Planning Platform

ChargeSense is a data-driven EV infrastructure intelligence and route planning prototype for Australia. It combines public EV charger data, EV registration-based market signals, route optimization, demand forecasting, reliability scoring and fleet/council planning analytics into one interactive Streamlit platform.

The project was built as a portfolio and product analytics case study to explore how data science, geospatial analytics and product thinking can support EV charging decisions for drivers, fleets, councils, infrastructure planners and charging operators.

---

## Live App

[Open ChargeSense](YOUR_STREAMLIT_APP_LINK_HERE)

---

## Key Features

- EV infrastructure overview across Australia
- Interactive charger map
- Infrastructure gap analysis
- Chargers per 1,000 EVs
- Investment priority ranking
- Demand forecast model
- Reliability intelligence
- Charger recommendation engine
- Real route optimizer using OSRM
- Custom suburb/place route planning
- Weather-adjusted EV range
- Battery-aware charging stop sequencing
- Charging cost estimation
- Corridor risk score
- Amenities/rest-stop score
- Simulated charger availability layer
- Operator performance dashboard
- Route comparison mode
- Fleet & Council Intelligence dashboard
- Fleet route CSV upload
- Downloadable trip plans and CSV reports

---

## Main Pages

### Real Route Optimizer

Plans EV routes using real road routing, EV model profiles, weather-adjusted range, charging strategies, charger recommendations, estimated charging time, estimated cost, corridor risk scoring and downloadable trip plans.

### Infrastructure Gap Analysis

Compares states by charger density, chargers per 1,000 EVs, ultra-fast charger share, reliability, EV growth and investment priority.

### Demand Forecast Model

Forecasts future EV charging pressure using EV fleet growth, public charging assumptions, charger capacity assumptions and current infrastructure levels.

### Fleet & Council Intelligence

A B2B planning dashboard for councils, fleets and infrastructure planners. It combines investment ranking, demand forecasting, additional station estimates and operator benchmarking.

### Fleet Route Upload

Allows fleet managers to upload multiple routes as a CSV and estimate charging stops, charging cost, charging time, trip time and fleet charging risk.

### Operator Performance Dashboard

Benchmarks charging operators using public metadata such as station count, average charger power, ultra-fast share, reliability and operator performance score.

### Route Comparison Mode

Compares different route planning scenarios across weather conditions and charging strategies, including estimated stops, charging time, charging cost and total trip time.

---

## Data Sources

- OpenChargeMap public EV charger metadata
- NSW EV charger data
- AAA / BITRE EV registration-derived inputs
- OSRM routing API
- Nominatim geocoding
- Public population and infrastructure assumptions

The project uses these sources to estimate charger coverage, reliability, demand pressure, investment priority and route-level charging risk.

---

## Methodology

### Reliability Score

Reliability is estimated from public charger metadata such as verification status, data freshness and available quality indicators. It is not confirmed live uptime.

### Simulated Availability

Availability status is simulated from reliability indicators and data freshness. Future versions could replace this with live operator APIs or OCPI feeds.

### Amenity Score

Amenity/rest-stop quality is estimated from station names, addresses and town fields using keywords such as service centre, shopping centre, 7-Eleven, Woolworths, Coles, McDonald's, Ampol, BP, Shell, cafe, restaurant and parking.

### Investment Priority Score

The investment priority score combines low chargers per EV, EV growth, weaker reliability and low ultra-fast charger coverage.

### Corridor Risk Score

Corridor risk estimates how risky an EV route is based on chargers near the route, chargers per 100 km, average reliability and estimated availability.

### Demand Forecast

The demand forecast model estimates future EV charging pressure using EV fleet growth, public charging session assumptions and charger capacity assumptions.

---

## Technology Stack

- Python
- Streamlit
- Pandas
- NumPy
- Plotly
- OSRM Routing API
- Nominatim Geocoding
- OpenStreetMap
- GitHub
- Streamlit Cloud

---

## Current limitations

ChargeSense currently uses public and derived data, so some features are prototype estimates:

Charger availability is simulated, not live.
Reliability is estimated from public metadata and data freshness.
Amenity score is keyword-based, not confirmed through a live POI API.
Operator names are estimated from station names.
Demand forecasts are scenario-based, not production statistical forecasts.
Fleet route upload uses city-level estimates, not depot-to-depot road routing.
Route Comparison Mode uses approximate distance estimates.
Real Route Optimizer uses OSRM routing but does not include live traffic.
No OCPI integration yet.
No user accounts, payments, or live charging session control.
Real data needed later

For a production version, ChargeSense would need:

Live charger availability from charging operators
OCPI feeds for charger status, pricing, roaming, and session data
Confirmed charger uptime and outage history
Real pricing data by operator and station
Real amenities/POI data from Google Places or OpenStreetMap
EV registrations by postcode, suburb, or LGA
LGA/suburb population and boundary data
Traffic and corridor demand data
Fleet depot locations and route schedules
Fleet vehicle telematics or usage patterns
Grid capacity or site feasibility data for infrastructure planning


---

## Screenshots

Add screenshots in an `images/` folder and update the paths below.



```text
images/home.png
images/real-route-optimizer.png
images/corridor-risk-score.png
images/fleet-council-intelligence.png
images/operator-performance-dashboard.png
images/demand-forecast-model.png
images/fleet-route-upload.png
