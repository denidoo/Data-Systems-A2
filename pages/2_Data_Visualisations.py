import streamlit as st
import pandas as pd
import plotly.express as px

from ml.predict import build_full_dataset_for_lookup


st.set_page_config(
    page_title="FlightInsight Data Visualisations",
    page_icon="📊",
    layout="wide"
)

st.title("FlightInsight Data Visualisations")
st.write("This page shows visual insights from the flight delay database.")


# -----------------------------
# Load data
# -----------------------------
@st.cache_data
def load_data():
    df = build_full_dataset_for_lookup()

    df["flight_number"] = df["flight_number"].astype(str)

    # Standardise delay column names
    if "departure_delay" not in df.columns:
        if "departure_delay_minutes" in df.columns:
            df["departure_delay"] = df["departure_delay_minutes"]
        else:
            df["departure_delay"] = 0

    if "arrival_delay" not in df.columns:
        if "arrival_delay_minutes" in df.columns:
            df["arrival_delay"] = df["arrival_delay_minutes"]
        else:
            df["arrival_delay"] = 0

    # Standardise delayed flag
    if "is_delayed" not in df.columns:
        df["is_delayed"] = df["departure_delay"] > 15

    # Standardise hour column
    if "departure_hour" not in df.columns:
        if "hour" in df.columns:
            df["departure_hour"] = df["hour"]
        else:
            df["departure_hour"] = 0

    # Standardise airport display columns
    if "origin_airport" not in df.columns:
        if "origin_airport_code" in df.columns:
            df["origin_airport"] = df["origin_airport_code"]
        else:
            df["origin_airport"] = "Unknown"

    if "destination_airport" not in df.columns:
        if "destination_airport_code" in df.columns:
            df["destination_airport"] = df["destination_airport_code"]
        else:
            df["destination_airport"] = "Unknown"

    # Standardise airline display column
    if "airline_name" not in df.columns:
        if "airline_code" in df.columns:
            df["airline_name"] = df["airline_code"]
        else:
            df["airline_name"] = "Unknown"

    # Ensure year/month exist
    if "year" not in df.columns:
        if "full_date" in df.columns:
            df["full_date"] = pd.to_datetime(df["full_date"], errors="coerce")
            df["year"] = df["full_date"].dt.year
        else:
            df["year"] = "Unknown"

    if "month" not in df.columns:
        if "full_date" in df.columns:
            df["full_date"] = pd.to_datetime(df["full_date"], errors="coerce")
            df["month"] = df["full_date"].dt.month
        else:
            df["month"] = 0

    # Ensure flight id exists for counting
    if "flight_performance_id" not in df.columns:
        df["flight_performance_id"] = range(1, len(df) + 1)

    return df


df = load_data()

if df.empty:
    st.warning("No data found in the database.")
    st.stop()


# -----------------------------
# Filters
# -----------------------------
st.sidebar.header("Filters")

year_options = sorted(df["year"].dropna().unique())

selected_year = st.sidebar.multiselect(
    "Select year",
    options=year_options,
    default=year_options
)

airline_options = sorted(df["airline_name"].dropna().unique())

default_airlines = airline_options[:5] if len(airline_options) > 5 else airline_options

selected_airlines = st.sidebar.multiselect(
    "Select airline",
    options=airline_options,
    default=default_airlines
)

filtered_df = df[
    (df["year"].isin(selected_year)) &
    (df["airline_name"].isin(selected_airlines))
].copy()

if filtered_df.empty:
    st.warning("No records match the selected filters.")
    st.stop()


# -----------------------------
# Summary metrics
# -----------------------------
st.subheader("Summary Metrics")

col1, col2, col3, col4 = st.columns(4)

total_flights = len(filtered_df)
delayed_flights = int(filtered_df["is_delayed"].sum())
delay_rate = delayed_flights / total_flights * 100 if total_flights > 0 else 0
avg_departure_delay = filtered_df["departure_delay"].mean()

col1.metric("Total Flights", f"{total_flights:,}")
col2.metric("Delayed Flights", f"{delayed_flights:,}")
col3.metric("Delay Rate", f"{delay_rate:.1f}%")
col4.metric("Avg Departure Delay", f"{avg_departure_delay:.1f} mins")


# -----------------------------
# Chart 1: Delay rate by airline
# -----------------------------
st.subheader("Delay Rate by Airline")

airline_delay = (
    filtered_df.groupby("airline_name")
    .agg(
        total_flights=("flight_performance_id", "count"),
        delayed_flights=("is_delayed", "sum")
    )
    .reset_index()
)

airline_delay["delay_rate"] = (
    airline_delay["delayed_flights"] / airline_delay["total_flights"] * 100
)

fig_airline = px.bar(
    airline_delay.sort_values("delay_rate", ascending=False),
    x="airline_name",
    y="delay_rate",
    title="Percentage of Flights Delayed by Airline",
    labels={
        "airline_name": "Airline",
        "delay_rate": "Delay Rate (%)"
    }
)

st.plotly_chart(fig_airline, use_container_width=True)


# -----------------------------
# Chart 2: Delay trend by month
# -----------------------------
st.subheader("Monthly Delay Trend")

monthly_delay = (
    filtered_df.groupby("month")
    .agg(
        total_flights=("flight_performance_id", "count"),
        delayed_flights=("is_delayed", "sum"),
        avg_departure_delay=("departure_delay", "mean")
    )
    .reset_index()
)

monthly_delay["delay_rate"] = (
    monthly_delay["delayed_flights"] / monthly_delay["total_flights"] * 100
)

fig_month = px.line(
    monthly_delay.sort_values("month"),
    x="month",
    y="delay_rate",
    markers=True,
    title="Delay Rate by Month",
    labels={
        "month": "Month",
        "delay_rate": "Delay Rate (%)"
    }
)

st.plotly_chart(fig_month, use_container_width=True)


# -----------------------------
# Chart 3: Average delay by departure hour
# -----------------------------
st.subheader("Average Departure Delay by Hour")

hourly_delay = (
    filtered_df.groupby("departure_hour")
    .agg(avg_departure_delay=("departure_delay", "mean"))
    .reset_index()
)

fig_hour = px.bar(
    hourly_delay.sort_values("departure_hour"),
    x="departure_hour",
    y="avg_departure_delay",
    title="Average Departure Delay by Scheduled Departure Hour",
    labels={
        "departure_hour": "Departure Hour",
        "avg_departure_delay": "Average Departure Delay (mins)"
    }
)

st.plotly_chart(fig_hour, use_container_width=True)


# -----------------------------
# Chart 4: Top delayed routes
# -----------------------------
st.subheader("Top Delayed Routes")

filtered_df["route"] = (
    filtered_df["origin_airport"].astype(str)
    + " → "
    + filtered_df["destination_airport"].astype(str)
)

route_delay = (
    filtered_df.groupby("route")
    .agg(
        total_flights=("flight_performance_id", "count"),
        avg_departure_delay=("departure_delay", "mean")
    )
    .reset_index()
)

route_delay = route_delay[route_delay["total_flights"] >= 10]

if route_delay.empty:
    st.info("Not enough repeated routes to show top delayed routes.")
else:
    fig_route = px.bar(
        route_delay.sort_values("avg_departure_delay", ascending=False).head(10),
        x="avg_departure_delay",
        y="route",
        orientation="h",
        title="Top 10 Routes by Average Departure Delay",
        labels={
            "avg_departure_delay": "Average Departure Delay (mins)",
            "route": "Route"
        }
    )

    st.plotly_chart(fig_route, use_container_width=True)


# -----------------------------
# Raw data preview
# -----------------------------
with st.expander("View filtered data"):
    st.dataframe(filtered_df, use_container_width=True)

with st.expander("Show available columns"):
    st.write(df.columns.tolist())