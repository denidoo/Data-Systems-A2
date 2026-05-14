import streamlit as st
import pandas as pd
from sqlalchemy import text
from database.db_config import engine


st.title("FlightInsight Database Admin")

st.write(
    "Use this page to upload CSV files or manually add rows into the PostgreSQL database."
)


TABLES = [
    "dim_date",
    "dim_time",
    "dim_airport",
    "dim_airline",
    "dim_weather_condition",
    "dim_flight",
    "dim_aircraft",
    "dim_delay_cause",
    "dim_api_snapshot",
    "fact_flightperformance",
    "fact_liveflightstatus"
]


# ------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------

def load_table(table_name):
    query = f"SELECT * FROM {table_name};"
    return pd.read_sql(query, engine)


def insert_row(table_name, data):
    columns = ", ".join(data.keys())
    placeholders = ", ".join([f":{key}" for key in data.keys()])

    query = text(f"""
        INSERT INTO {table_name} ({columns})
        VALUES ({placeholders})
    """)

    with engine.begin() as conn:
        conn.execute(query, data)


def upload_csv_to_table(table_name, uploaded_file):
    df = pd.read_csv(uploaded_file)
    df.to_sql(table_name, engine, if_exists="append", index=False)
    return df


# ------------------------------------------------------------
# SIDEBAR NAVIGATION
# ------------------------------------------------------------

page = st.sidebar.radio(
    "Select Admin Action",
    [
        "View Tables",
        "Upload CSV",
        "Add Date",
        "Add Time",
        "Add Airport",
        "Add Airline",
        "Add Weather",
        "Add Flight",
        "Add Aircraft",
        "Add Delay Cause",
        "Add Flight Performance"
    ]
)


# ------------------------------------------------------------
# VIEW TABLES
# ------------------------------------------------------------

if page == "View Tables":
    st.subheader("View Database Tables")

    selected_table = st.selectbox("Select table", TABLES)

    try:
        df = load_table(selected_table)
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error("Could not load table.")
        st.write(e)


# ------------------------------------------------------------
# CSV UPLOAD
# ------------------------------------------------------------

elif page == "Upload CSV":
    st.subheader("Upload CSV to Table")

    st.warning(
        "Only upload processed CSV files here. "
        "Do not upload raw flights.csv directly into fact_flightperformance. "
        "Raw flight datasets should be placed in data/raw/flights.csv and loaded using etl_load_data.py."
    )

    selected_table = st.selectbox("Select destination table", TABLES)

    uploaded_file = st.file_uploader(
        "Upload CSV file",
        type=["csv"]
    )

    if uploaded_file is not None:
        preview_df = pd.read_csv(uploaded_file)

        st.write("CSV Preview")
        st.dataframe(preview_df.head(), use_container_width=True)

        if st.button("Load CSV into Database"):
            try:
                uploaded_file.seek(0)
                uploaded_df = upload_csv_to_table(selected_table, uploaded_file)
                st.success(f"Loaded {len(uploaded_df)} rows into {selected_table}.")
            except Exception as e:
                st.error("Upload failed. Check that CSV columns match the table columns.")
                st.write(e)


# ------------------------------------------------------------
# ADD DATE
# ------------------------------------------------------------

elif page == "Add Date":
    st.subheader("Add Date Row")

    full_date = st.date_input("Full Date")

    date_id = int(full_date.strftime("%Y%m%d"))

    if st.button("Add Date"):
        data = {
            "date_id": date_id,
            "full_date": full_date,
            "day": full_date.day,
            "month": full_date.month,
            "year": full_date.year
        }

        try:
            insert_row("dim_date", data)
            st.success("Date added.")
        except Exception as e:
            st.error("Insert failed.")
            st.write(e)


# ------------------------------------------------------------
# ADD TIME
# ------------------------------------------------------------

elif page == "Add Time":
    st.subheader("Add Time Row")

    hour = st.number_input("Hour", min_value=0, max_value=23, value=8)
    minute = st.number_input("Minute", min_value=0, max_value=59, value=0)

    time_id = int(hour * 100 + minute)

    if hour <= 5:
        time_of_day = "Night"
    elif hour <= 11:
        time_of_day = "Morning"
    elif hour <= 17:
        time_of_day = "Afternoon"
    else:
        time_of_day = "Evening"

    st.write(f"Time ID: {time_id}")
    st.write(f"Time of Day: {time_of_day}")

    if st.button("Add Time"):
        data = {
            "time_id": time_id,
            "hour": hour,
            "minute": minute,
            "time_of_day": time_of_day
        }

        try:
            insert_row("dim_time", data)
            st.success("Time added.")
        except Exception as e:
            st.error("Insert failed.")
            st.write(e)


# ------------------------------------------------------------
# ADD AIRPORT
# ------------------------------------------------------------

elif page == "Add Airport":
    st.subheader("Add Airport Row")

    airport_code = st.text_input("Airport Code", placeholder="SYD")
    airport_name = st.text_input("Airport Name", placeholder="Sydney Kingsford Smith Airport")
    airport_city = st.text_input("City", placeholder="Sydney")
    airport_country = st.text_input("Country", placeholder="Australia")
    airport_continent = st.text_input("Continent", placeholder="Oceania")
    airport_elevation = st.number_input("Elevation", value=0)
    airport_type = st.selectbox("Airport Type", ["Domestic", "International", "Regional", "Unknown"])

    if st.button("Add Airport"):
        data = {
            "airport_code": airport_code.upper(),
            "airport_name": airport_name,
            "airport_city": airport_city,
            "airport_country": airport_country,
            "airport_continent": airport_continent,
            "airport_elevation": airport_elevation,
            "airport_type": airport_type
        }

        try:
            insert_row("dim_airport", data)
            st.success("Airport added.")
        except Exception as e:
            st.error("Insert failed.")
            st.write(e)


# ------------------------------------------------------------
# ADD AIRLINE
# ------------------------------------------------------------

elif page == "Add Airline":
    st.subheader("Add Airline Row")

    airline_code = st.text_input("Airline Code", placeholder="QF")
    airline_name = st.text_input("Airline Name", placeholder="Qantas")

    if st.button("Add Airline"):
        data = {
            "airline_code": airline_code.upper(),
            "airline_name": airline_name
        }

        try:
            insert_row("dim_airline", data)
            st.success("Airline added.")
        except Exception as e:
            st.error("Insert failed.")
            st.write(e)


# ------------------------------------------------------------
# ADD WEATHER
# ------------------------------------------------------------

elif page == "Add Weather":
    st.subheader("Add Weather Row")

    weather_type = st.selectbox(
        "Weather Type",
        ["Clear", "Rain", "Fog", "Thunderstorm", "Windy", "Weather Delay", "Unknown"]
    )

    temperature = st.number_input("Temperature", value=20.0)
    wind_speed = st.number_input("Wind Speed", value=10.0)
    visibility = st.number_input("Visibility", value=10.0)

    if st.button("Add Weather"):
        data = {
            "weather_type": weather_type,
            "temperature": temperature,
            "wind_speed": wind_speed,
            "visibility": visibility
        }

        try:
            insert_row("dim_weather_condition", data)
            st.success("Weather row added.")
        except Exception as e:
            st.error("Insert failed.")
            st.write(e)


# ------------------------------------------------------------
# ADD FLIGHT
# ------------------------------------------------------------

elif page == "Add Flight":
    st.subheader("Add Flight Row")

    flight_number = st.text_input("Flight Number", placeholder="QF402")
    flight_type = st.selectbox("Flight Type", ["Domestic", "International"])
    route_category = st.selectbox("Route Category", ["Short-haul", "Medium-haul", "Long-haul", "Unknown"])
    route_distance = st.number_input("Route Distance", value=700.0)

    if st.button("Add Flight"):
        data = {
            "flight_number": flight_number.upper(),
            "flight_type": flight_type,
            "route_category": route_category,
            "route_distance": route_distance
        }

        try:
            insert_row("dim_flight", data)
            st.success("Flight added.")
        except Exception as e:
            st.error("Insert failed.")
            st.write(e)


# ------------------------------------------------------------
# ADD AIRCRAFT
# ------------------------------------------------------------

elif page == "Add Aircraft":
    st.subheader("Add Aircraft Row")

    tail_number = st.text_input("Tail Number", placeholder="VH-VXA")
    aircraft_model = st.text_input("Aircraft Model", placeholder="A320")
    manufacturer = st.text_input("Manufacturer", placeholder="Airbus")
    seating_capacity = st.number_input("Seating Capacity", value=180)
    aircraft_category = st.selectbox("Aircraft Category", ["Narrow-body", "Wide-body", "Regional", "Unknown"])

    if st.button("Add Aircraft"):
        data = {
            "tail_number": tail_number.upper(),
            "aircraft_model": aircraft_model,
            "manufacturer": manufacturer,
            "seating_capacity": seating_capacity,
            "aircraft_category": aircraft_category
        }

        try:
            insert_row("dim_aircraft", data)
            st.success("Aircraft added.")
        except Exception as e:
            st.error("Insert failed.")
            st.write(e)


# ------------------------------------------------------------
# ADD DELAY CAUSE
# ------------------------------------------------------------

elif page == "Add Delay Cause":
    st.subheader("Add Delay Cause Row")

    delay_cause_type = st.selectbox(
        "Delay Cause Type",
        ["None", "Airline", "Weather", "ATC", "Security", "Late Aircraft", "Technical", "Unknown"]
    )

    delay_cause_detail = st.text_input("Delay Cause Detail", placeholder="Air traffic congestion")
    is_controllable = st.checkbox("Is Controllable?")

    if st.button("Add Delay Cause"):
        data = {
            "delay_cause_type": delay_cause_type,
            "delay_cause_detail": delay_cause_detail,
            "is_controllable": is_controllable
        }

        try:
            insert_row("dim_delay_cause", data)
            st.success("Delay cause added.")
        except Exception as e:
            st.error("Insert failed.")
            st.write(e)


# ------------------------------------------------------------
# ADD FACT FLIGHT PERFORMANCE
# ------------------------------------------------------------

elif page == "Add Flight Performance":
    st.subheader("Add Flight Performance Row")

    try:
        dates = load_table("dim_date")
        times = load_table("dim_time")
        airports = load_table("dim_airport")
        airlines = load_table("dim_airline")
        weather = load_table("dim_weather_condition")
        flights = load_table("dim_flight")
        aircraft = load_table("dim_aircraft")
        delay_causes = load_table("dim_delay_cause")

        date_id = st.selectbox("Date", dates["date_id"])
        time_id = st.selectbox("Time", times["time_id"])

        origin_airport_id = st.selectbox(
            "Origin Airport",
            airports["airport_id"],
            format_func=lambda x: airports.loc[airports["airport_id"] == x, "airport_code"].iloc[0]
        )

        destination_airport_id = st.selectbox(
            "Destination Airport",
            airports["airport_id"],
            format_func=lambda x: airports.loc[airports["airport_id"] == x, "airport_code"].iloc[0]
        )

        airline_id = st.selectbox(
            "Airline",
            airlines["airline_id"],
            format_func=lambda x: airlines.loc[airlines["airline_id"] == x, "airline_name"].iloc[0]
        )

        weather_id = st.selectbox(
            "Weather",
            weather["weather_id"],
            format_func=lambda x: weather.loc[weather["weather_id"] == x, "weather_type"].iloc[0]
        )

        flight_id = st.selectbox(
            "Flight",
            flights["flight_id"],
            format_func=lambda x: flights.loc[flights["flight_id"] == x, "flight_number"].iloc[0]
        )

        aircraft_id = st.selectbox(
            "Aircraft",
            aircraft["aircraft_id"],
            format_func=lambda x: aircraft.loc[aircraft["aircraft_id"] == x, "aircraft_model"].iloc[0]
        )

        delay_cause_id = st.selectbox(
            "Delay Cause",
            delay_causes["delay_cause_id"],
            format_func=lambda x: delay_causes.loc[delay_causes["delay_cause_id"] == x, "delay_cause_type"].iloc[0]
        )

        delay_minutes = st.number_input("Delay Minutes", value=0)
        cancellation_flag = st.checkbox("Cancelled?")
        passengers = st.number_input("Passengers", value=0)

        scheduled_departure_datetime = st.text_input(
            "Scheduled Departure Datetime",
            placeholder="2024-05-01 08:00:00"
        )

        actual_departure_datetime = st.text_input(
            "Actual Departure Datetime",
            placeholder="2024-05-01 08:15:00"
        )

        scheduled_arrival_datetime = st.text_input(
            "Scheduled Arrival Datetime",
            placeholder="2024-05-01 09:30:00"
        )

        actual_arrival_datetime = st.text_input(
            "Actual Arrival Datetime",
            placeholder="2024-05-01 09:45:00"
        )

        delay_status = "Delayed" if delay_minutes > 15 else "On Time"
        st.write(f"Delay Status: **{delay_status}**")

        if st.button("Add Flight Performance"):
            data = {
                "date_id": date_id,
                "time_id": time_id,
                "origin_airport_id": origin_airport_id,
                "destination_airport_id": destination_airport_id,
                "airline_id": airline_id,
                "weather_id": weather_id,
                "flight_id": flight_id,
                "aircraft_id": aircraft_id,
                "delay_cause_id": delay_cause_id,
                "delay_minutes": delay_minutes,
                "cancellation_flag": cancellation_flag,
                "passengers": passengers,
                "scheduled_departure_datetime": scheduled_departure_datetime,
                "actual_departure_datetime": actual_departure_datetime,
                "scheduled_arrival_datetime": scheduled_arrival_datetime,
                "actual_arrival_datetime": actual_arrival_datetime,
                "delay_status": delay_status
            }

            try:
                insert_row("fact_flightperformance", data)
                st.success("Flight performance row added.")
            except Exception as e:
                st.error("Insert failed.")
                st.write(e)

    except Exception as e:
        st.error("Could not load dimension tables. Add dimension rows first.")
        st.write(e)