import streamlit as st
import pandas as pd
import plotly.express as px
from db_config import get_connection


st.set_page_config(
    page_title="FlightInsight Data Visualisations",
    page_icon="📊",
    layout="wide"
)

st.title("FlightInsight Data Visualisations")
st.write("This page shows visual insights from the flight delay database.")


# -----------------------------
# Load data from PostgreSQL
# -----------------------------
@st.cache_data
def load_flight_data():
    conn = get_connection()

    query = """
        SELECT
            f.flight_performance_id,
            d.year,
            d.month,
            d.day,
            a.airline_name,
            o.airport_name AS origin_airport,
            dest.airport_name AS destination_airport,
            t.hour AS departure_hour,
            f.departure_delay,
            f.arrival_delay,
            f.is_delayed
        FROM fact_flightperformance f
        LEFT JOIN dim_date d 
            ON f.date_id = d.date_id
        LEFT JOIN dim_airline a 
            ON f.airline_id = a.airline_id
        LEFT JOIN dim_airport o 
            ON f.origin_airport_id = o.airport_id
        LEFT JOIN dim_airport dest 
            ON f.destination_airport_id = dest.airport_id
        LEFT JOIN dim_time t 
            ON f.scheduled_departure_time_id = t.time_id;
    """

    df = pd.read_sql(query, conn)
    conn.close()

    return df


df = load_flight_data()


if df.empty:
    st.warning("No data found in the database.")
    st.stop()


# -----------------------------
# Filters
# -----------------------------
st.sidebar.header("Filters")

selected_year = st.sidebar.multiselect(
    "Select year",
    options=sorted(df["year"].dropna().unique()),
    default=sorted(df["year"].dropna().unique())
)

selected_airlines = st.sidebar.multiselect(
    "Select airline",
    options=sorted(df["airline_name"].dropna().unique()),
    default=sorted(df["airline_name"].dropna().unique())[:5]
)

filtered_df = df[
    (df["year"].isin(selected_year)) &
    (df["airline_name"].isin(selected_airlines))
]


# -----------------------------
# Summary metrics
# -----------------------------
st.subheader("Summary Metrics")

col1, col2, col3, col4 = st.columns(4)

total_flights = len(filtered_df)
delayed_flights = filtered_df["is_delayed"].sum()
delay_rate = delayed_flights / total_flights * 100 if total_flights > 0 else 0
avg_departure_delay = filtered_df["departure_delay"].mean()

col1.metric("Total Flights", f"{total_flights:,}")
col2.metric("Delayed Flights", f"{int(delayed_flights):,}")
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
    monthly_delay,
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
    hourly_delay,
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
    filtered_df["origin_airport"] + " → " + filtered_df["destination_airport"]
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
    st.dataframe(filtered_df)