import pandas as pd


def clean_time(value):
    if pd.isna(value):
        return None

    try:
        value = int(value)
    except ValueError:
        return None

    value = f"{value:04d}"
    hour = int(value[:2])
    minute = int(value[2:])

    if hour >= 24:
        hour = 23
        minute = 59

    return f"{hour:02d}:{minute:02d}:00"


def get_time_of_day(hour):
    if hour is None:
        return "Unknown"
    if 5 <= hour < 12:
        return "Morning"
    if 12 <= hour < 17:
        return "Afternoon"
    if 17 <= hour < 21:
        return "Evening"
    return "Night"


def transform_data(raw_data):
    flights = raw_data["flights"].copy()
    airlines = raw_data["airlines"].copy()
    airports = raw_data["airports"].copy()

    flights.columns = flights.columns.str.lower()
    airlines.columns = airlines.columns.str.lower()
    airports.columns = airports.columns.str.lower()

    # Limit data size if needed while testing
    flights = flights.head(100000)

    flights["flight_date"] = pd.to_datetime(
        flights[["year", "month", "day"]]
    )

    flights["scheduled_departure_time"] = flights["scheduled_departure"].apply(clean_time)
    flights["actual_departure_time"] = flights["departure_time"].apply(clean_time)

    flights["is_delayed"] = flights["departure_delay"].fillna(0) > 15
    flights["delay_minutes"] = flights["departure_delay"].fillna(0).astype(int)

    dim_airline = airlines.rename(columns={
        "iata_code": "airline_code",
        "airline": "airline_name"
    })[["airline_code", "airline_name"]].drop_duplicates()

    dim_airport = airports.rename(columns={
        "iata_code": "airport_code",
        "airport": "airport_name"
    })

    airport_cols = ["airport_code", "airport_name", "city", "state", "country"]
    for col in airport_cols:
        if col not in dim_airport.columns:
            dim_airport[col] = None

    dim_airport = dim_airport[airport_cols].drop_duplicates()

    dim_date = flights[["flight_date"]].drop_duplicates()
    dim_date = dim_date.rename(columns={"flight_date": "full_date"})
    dim_date["year"] = dim_date["full_date"].dt.year
    dim_date["month"] = dim_date["full_date"].dt.month
    dim_date["day"] = dim_date["full_date"].dt.day
    dim_date["quarter"] = dim_date["full_date"].dt.quarter
    dim_date["day_of_week"] = dim_date["full_date"].dt.dayofweek
    dim_date["is_weekend"] = dim_date["day_of_week"].isin([5, 6])

    scheduled_times = flights[["scheduled_departure_time"]].rename(
        columns={"scheduled_departure_time": "time_value"}
    )

    actual_times = flights[["actual_departure_time"]].rename(
        columns={"actual_departure_time": "time_value"}
    )

    dim_time = pd.concat([scheduled_times, actual_times])
    dim_time = dim_time.dropna().drop_duplicates()

    dim_time["time_value"] = pd.to_datetime(dim_time["time_value"]).dt.time
    dim_time["hour"] = dim_time["time_value"].apply(lambda x: x.hour)
    dim_time["minute"] = dim_time["time_value"].apply(lambda x: x.minute)
    dim_time["time_of_day"] = dim_time["hour"].apply(get_time_of_day)

    dim_flight = flights[["flight_number"]].dropna().drop_duplicates()
    dim_flight["flight_number"] = dim_flight["flight_number"].astype(str)

    dim_aircraft = pd.DataFrame({
        "aircraft_type": ["Unknown"]
    })

    dim_weather_condition = pd.DataFrame({
        "weather_condition": ["Unknown"]
    })

    dim_delay_cause = pd.DataFrame({
        "delay_cause": ["None", "Carrier", "Weather", "NAS", "Security", "Late Aircraft"]
    })

    fact_flightperformance = flights[[
        "flight_number",
        "airline",
        "origin_airport",
        "destination_airport",
        "flight_date",
        "scheduled_departure_time",
        "actual_departure_time",
        "delay_minutes",
        "is_delayed"
    ]].copy()

    fact_flightperformance["aircraft_type"] = "Unknown"
    fact_flightperformance["weather_condition"] = "Unknown"
    fact_flightperformance["delay_cause"] = "None"

    fact_flightperformance["flight_number"] = fact_flightperformance["flight_number"].astype(str)

    print("Transform complete.")

    return {
        "dim_airline": dim_airline,
        "dim_airport": dim_airport,
        "dim_date": dim_date,
        "dim_time": dim_time,
        "dim_flight": dim_flight,
        "dim_aircraft": dim_aircraft,
        "dim_weather_condition": dim_weather_condition,
        "dim_delay_cause": dim_delay_cause,
        "fact_flightperformance": fact_flightperformance
    }