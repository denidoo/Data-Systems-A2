import pandas as pd
import numpy as np
from pathlib import Path
from sqlalchemy import text
from db_config import engine


RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
MANUAL_DIR = Path("data/manual_uploads")

RAW_FLIGHTS_PATH = RAW_DIR / "flights.csv"
RAW_AIRLINES_PATH = RAW_DIR / "airlines.csv"
RAW_AIRPORTS_PATH = RAW_DIR / "airports.csv"
MANUAL_FLIGHTS_PATH = MANUAL_DIR / "manual_flights.csv"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------

def get_first_existing_column(df, possible_columns):
    for column in possible_columns:
        if column in df.columns:
            return column
    return None


def classify_time_of_day(hour):
    if 0 <= hour <= 5:
        return "Night"
    elif 6 <= hour <= 11:
        return "Morning"
    elif 12 <= hour <= 17:
        return "Afternoon"
    else:
        return "Evening"


def classify_route(distance):
    if distance < 800:
        return "Short-haul"
    elif distance < 2500:
        return "Medium-haul"
    else:
        return "Long-haul"


def classify_delay_cause(row):
    delay_columns = {
        "carrier_delay": "Airline",
        "weather_delay": "Weather",
        "nas_delay": "ATC",
        "security_delay": "Security",
        "late_aircraft_delay": "Late Aircraft"
    }

    available = {
        col: label
        for col, label in delay_columns.items()
        if col in row.index
    }

    if not available:
        return "Unknown"

    max_column = None
    max_value = 0

    for col in available:
        value = row[col]
        if pd.notna(value) and value > max_value:
            max_value = value
            max_column = col

    if max_column is None or max_value <= 0:
        return "None"

    return available[max_column]


def make_datetime(date_value, time_value):
    if pd.isna(date_value):
        return pd.NaT

    try:
        time_value = int(time_value)
    except Exception:
        time_value = 0

    hour = min(max(time_value // 100, 0), 23)
    minute = min(max(time_value % 100, 0), 59)

    return (
        pd.to_datetime(date_value)
        + pd.to_timedelta(hour, unit="h")
        + pd.to_timedelta(minute, unit="m")
    )


def normalise_columns(df):
    df = df.copy()
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )
    return df


# ------------------------------------------------------------
# EXTRACT
# ------------------------------------------------------------

def extract():
    if not RAW_FLIGHTS_PATH.exists():
        raise FileNotFoundError(
            f"Missing raw flight dataset: {RAW_FLIGHTS_PATH}. "
            "Place your main flights.csv file inside data/raw/."
        )

    flights = pd.read_csv(RAW_FLIGHTS_PATH, low_memory=False, nrows=200000)
    print(f"Main flight file loaded: {len(flights)} rows")

    if MANUAL_FLIGHTS_PATH.exists():
        manual_flights = pd.read_csv(MANUAL_FLIGHTS_PATH, low_memory=False)
        flights = pd.concat([flights, manual_flights], ignore_index=True)
        print(f"Manual flight file added: {len(manual_flights)} rows")

    print(f"Extract complete. Total rows loaded: {len(flights)}")
    return flights


def extract_airlines_lookup():
    if RAW_AIRLINES_PATH.exists():
        airlines = pd.read_csv(RAW_AIRLINES_PATH)
        airlines = normalise_columns(airlines)

        code_col = get_first_existing_column(
            airlines,
            ["iata_code", "airline_code", "carrier", "code"]
        )

        name_col = get_first_existing_column(
            airlines,
            ["airline", "airline_name", "name"]
        )

        if code_col and name_col:
            airlines = airlines[[code_col, name_col]].drop_duplicates()
            airlines = airlines.rename(columns={
                code_col: "airline_code",
                name_col: "airline_name"
            })
            airlines["airline_code"] = airlines["airline_code"].astype(str).str.strip()
            airlines["airline_name"] = airlines["airline_name"].astype(str).str.strip()
            return airlines

    return pd.DataFrame(columns=["airline_code", "airline_name"])


def extract_airports_lookup():
    if RAW_AIRPORTS_PATH.exists():
        airports = pd.read_csv(RAW_AIRPORTS_PATH)
        airports = normalise_columns(airports)

        code_col = get_first_existing_column(
            airports,
            ["iata_code", "airport_code", "origin", "code"]
        )

        name_col = get_first_existing_column(
            airports,
            ["airport", "airport_name", "name"]
        )

        city_col = get_first_existing_column(
            airports,
            ["city", "airport_city"]
        )

        country_col = get_first_existing_column(
            airports,
            ["country", "airport_country"]
        )

        if code_col:
            result = pd.DataFrame()
            result["airport_code"] = airports[code_col].astype(str).str.strip()
            result["airport_name"] = airports[name_col].astype(str).str.strip() if name_col else result["airport_code"]
            result["airport_city"] = airports[city_col].astype(str).str.strip() if city_col else "Unknown"
            result["airport_country"] = airports[country_col].astype(str).str.strip() if country_col else "United States"
            result["airport_continent"] = "North America"
            result["airport_elevation"] = 0
            result["airport_type"] = "Unknown"

            return result.drop_duplicates()

    return pd.DataFrame(columns=[
        "airport_code",
        "airport_name",
        "airport_city",
        "airport_country",
        "airport_continent",
        "airport_elevation",
        "airport_type"
    ])


# ------------------------------------------------------------
# TRANSFORM
# ------------------------------------------------------------

def transform(raw_df):
    df = normalise_columns(raw_df)

    carrier_col = get_first_existing_column(df, [
        "op_carrier",
        "op_unique_carrier",
        "mkt_unique_carrier",
        "carrier",
        "airline"
    ])

    flight_number_col = get_first_existing_column(df, [
        "op_carrier_fl_num",
        "flight_number"
    ])

    date_col = get_first_existing_column(df, [
        "fl_date",
        "date",
        "flight_date"
    ])

    origin_col = get_first_existing_column(df, [
        "origin",
        "origin_airport"
    ])

    dest_col = get_first_existing_column(df, [
        "dest",
        "destination",
        "destination_airport"
    ])

    dep_time_col = get_first_existing_column(df, [
        "crs_dep_time",
        "scheduled_departure",
        "scheduled_departure_time"
    ])

    arr_delay_col = get_first_existing_column(df, [
        "arr_delay",
        "arrival_delay"
    ])

    cancelled_col = get_first_existing_column(df, [
        "cancelled",
        "cancellation_flag"
    ])

    missing = []

    required_map = {
        "carrier/airline column": carrier_col,
        "flight number column": flight_number_col,
        "origin column": origin_col,
        "destination column": dest_col,
        "scheduled departure time column": dep_time_col,
        "arrival delay column": arr_delay_col,
        "cancelled column": cancelled_col
    }

    for label, value in required_map.items():
        if value is None:
            missing.append(label)

    if missing:
        raise ValueError(f"Missing required columns in CSV: {missing}")

    if date_col:
        df["fl_date"] = pd.to_datetime(df[date_col], errors="coerce")
    else:
        if all(col in df.columns for col in ["year", "month", "day"]):
            df["fl_date"] = pd.to_datetime(
                df[["year", "month", "day"]],
                errors="coerce"
            )
        else:
            raise ValueError("Missing required date information. Expected fl_date/date/flight_date or year/month/day columns.")
        
    df = df.dropna(subset=["fl_date"])

    df["airline_code"] = df[carrier_col].astype(str).str.strip().str.upper()

    df["flight_number"] = (
        df["airline_code"]
        + df[flight_number_col].astype(str).str.strip()
    )

    df["origin"] = df[origin_col].astype(str).str.strip().str.upper()
    df["dest"] = df[dest_col].astype(str).str.strip().str.upper()

    df["arr_delay"] = pd.to_numeric(df[arr_delay_col], errors="coerce").fillna(0)

    dep_delay_col = get_first_existing_column(df, [
        "dep_delay",
        "departure_delay"
    ])

    if dep_delay_col:
        df["dep_delay"] = pd.to_numeric(df[dep_delay_col], errors="coerce").fillna(0)
    else:
        df["dep_delay"] = 0

    df["cancelled"] = pd.to_numeric(df[cancelled_col], errors="coerce").fillna(0)

    df["delay_minutes"] = df["arr_delay"].astype(int)
    df["delay_status"] = np.where(df["delay_minutes"] > 15, "Delayed", "On Time")
    df["cancellation_flag"] = df["cancelled"].astype(bool)

    df["date_id"] = df["fl_date"].dt.strftime("%Y%m%d").astype(int)

    df["crs_dep_time"] = pd.to_numeric(df[dep_time_col], errors="coerce").fillna(0).astype(int)
    df["hour"] = (df["crs_dep_time"] // 100).clip(0, 23)
    df["minute"] = (df["crs_dep_time"] % 100).clip(0, 59)
    df["time_id"] = df["hour"] * 100 + df["minute"]
    df["time_of_day"] = df["hour"].apply(classify_time_of_day)

    distance_col = get_first_existing_column(df, [
        "distance",
        "route_distance"
    ])

    if distance_col:
        df["route_distance"] = pd.to_numeric(df[distance_col], errors="coerce").fillna(0)
    else:
        df["route_distance"] = 0

    df["route_category"] = df["route_distance"].apply(classify_route)
    df["flight_type"] = "Domestic"

    df["scheduled_departure_datetime"] = df.apply(
        lambda row: make_datetime(row["fl_date"], row["crs_dep_time"]),
        axis=1
    )

    df["actual_departure_datetime"] = (
        df["scheduled_departure_datetime"]
        + pd.to_timedelta(df["dep_delay"], unit="m")
    )

    arr_time_col = get_first_existing_column(df, [
        "crs_arr_time",
        "scheduled_arrival",
        "scheduled_arrival_time"
    ])

    if arr_time_col:
        df["scheduled_arrival_datetime"] = df.apply(
            lambda row: make_datetime(row["fl_date"], row[arr_time_col]),
            axis=1
        )
    else:
        df["scheduled_arrival_datetime"] = df["scheduled_departure_datetime"]

    df["actual_arrival_datetime"] = (
        df["scheduled_arrival_datetime"]
        + pd.to_timedelta(df["arr_delay"], unit="m")
    )

    df["delay_cause_type"] = df.apply(classify_delay_cause, axis=1)
    df["delay_cause_detail"] = df["delay_cause_type"]

    df["is_controllable"] = df["delay_cause_type"].isin([
        "Airline",
        "Late Aircraft",
        "Technical"
    ])

    df["weather_type"] = np.where(
        df["delay_cause_type"] == "Weather",
        "Weather Delay",
        "Unknown"
    )

    df["temperature"] = 0
    df["wind_speed"] = 0
    df["visibility"] = 0

    tail_col = get_first_existing_column(df, [
        "tail_num",
        "tail_number"
    ])

    if tail_col:
        df["tail_number"] = df[tail_col].astype(str).str.strip()
    else:
        df["tail_number"] = "Unknown"

    df["aircraft_model"] = "Unknown"
    df["manufacturer"] = "Unknown"
    df["seating_capacity"] = 0
    df["aircraft_category"] = "Unknown"

    df["passengers"] = 0

    print("Transform complete.")
    return df


# ------------------------------------------------------------
# BUILD DIMENSIONS
# ------------------------------------------------------------

def build_dimensions(df):
    airlines_lookup = extract_airlines_lookup()
    airports_lookup = extract_airports_lookup()

    dim_date = df[["date_id", "fl_date"]].drop_duplicates().copy()
    dim_date["day"] = dim_date["fl_date"].dt.day
    dim_date["month"] = dim_date["fl_date"].dt.month
    dim_date["year"] = dim_date["fl_date"].dt.year
    dim_date = dim_date.rename(columns={"fl_date": "full_date"})
    dim_date = dim_date[["date_id", "full_date", "day", "month", "year"]]

    dim_time = df[["time_id", "hour", "minute", "time_of_day"]].drop_duplicates().copy()

    dim_airline = df[["airline_code"]].drop_duplicates().copy()

    if not airlines_lookup.empty:
        dim_airline = dim_airline.merge(
            airlines_lookup,
            on="airline_code",
            how="left"
        )
        dim_airline["airline_name"] = dim_airline["airline_name"].fillna(dim_airline["airline_code"])
    else:
        dim_airline["airline_name"] = dim_airline["airline_code"]

    dim_airline = dim_airline.sort_values("airline_code").reset_index(drop=True)
    dim_airline["airline_id"] = dim_airline.index + 1
    dim_airline = dim_airline[["airline_id", "airline_code", "airline_name"]]

    airports = pd.concat([
        df[["origin"]].rename(columns={"origin": "airport_code"}),
        df[["dest"]].rename(columns={"dest": "airport_code"})
    ]).drop_duplicates()

    if not airports_lookup.empty:
        dim_airport = airports.merge(
            airports_lookup,
            on="airport_code",
            how="left"
        )
    else:
        dim_airport = airports.copy()
        dim_airport["airport_name"] = dim_airport["airport_code"]
        dim_airport["airport_city"] = "Unknown"
        dim_airport["airport_country"] = "United States"
        dim_airport["airport_continent"] = "North America"
        dim_airport["airport_elevation"] = 0
        dim_airport["airport_type"] = "Unknown"

    dim_airport["airport_name"] = dim_airport["airport_name"].fillna(dim_airport["airport_code"])
    dim_airport["airport_city"] = dim_airport["airport_city"].fillna("Unknown")
    dim_airport["airport_country"] = dim_airport["airport_country"].fillna("United States")
    dim_airport["airport_continent"] = dim_airport["airport_continent"].fillna("North America")
    dim_airport["airport_elevation"] = dim_airport["airport_elevation"].fillna(0)
    dim_airport["airport_type"] = dim_airport["airport_type"].fillna("Unknown")

    dim_airport = dim_airport.sort_values("airport_code").reset_index(drop=True)
    dim_airport["airport_id"] = dim_airport.index + 1

    dim_airport = dim_airport[[
        "airport_id",
        "airport_code",
        "airport_name",
        "airport_city",
        "airport_country",
        "airport_continent",
        "airport_elevation",
        "airport_type"
    ]]

    dim_weather = df[[
        "weather_type",
        "temperature",
        "wind_speed",
        "visibility"
    ]].drop_duplicates().reset_index(drop=True)

    dim_weather["weather_id"] = dim_weather.index + 1

    dim_weather = dim_weather[[
        "weather_id",
        "weather_type",
        "temperature",
        "wind_speed",
        "visibility"
    ]]

    dim_flight = df[[
        "flight_number",
        "flight_type",
        "route_category",
        "route_distance"
    ]].drop_duplicates().reset_index(drop=True)

    dim_flight["flight_id"] = dim_flight.index + 1

    dim_flight = dim_flight[[
        "flight_id",
        "flight_number",
        "flight_type",
        "route_category",
        "route_distance"
    ]]

    dim_aircraft = df[[
        "tail_number",
        "aircraft_model",
        "manufacturer",
        "seating_capacity",
        "aircraft_category"
    ]].drop_duplicates().reset_index(drop=True)

    dim_aircraft["aircraft_id"] = dim_aircraft.index + 1

    dim_aircraft = dim_aircraft[[
        "aircraft_id",
        "tail_number",
        "aircraft_model",
        "manufacturer",
        "seating_capacity",
        "aircraft_category"
    ]]

    dim_delay_cause = df[[
        "delay_cause_type",
        "delay_cause_detail",
        "is_controllable"
    ]].drop_duplicates().reset_index(drop=True)

    dim_delay_cause["delay_cause_id"] = dim_delay_cause.index + 1

    dim_delay_cause = dim_delay_cause[[
        "delay_cause_id",
        "delay_cause_type",
        "delay_cause_detail",
        "is_controllable"
    ]]

    dimensions = {
        "dim_date": dim_date,
        "dim_time": dim_time,
        "dim_airline": dim_airline,
        "dim_airport": dim_airport,
        "dim_weather_condition": dim_weather,
        "dim_flight": dim_flight,
        "dim_aircraft": dim_aircraft,
        "dim_delay_cause": dim_delay_cause
    }

    for table_name, table_df in dimensions.items():
        table_df.to_csv(PROCESSED_DIR / f"{table_name}.csv", index=False)

    print("Dimension tables created and saved to data/processed/.")
    return dimensions


# ------------------------------------------------------------
# BUILD FACT TABLE
# ------------------------------------------------------------

def build_fact_table(df, dimensions):
    airline_map = dict(zip(
        dimensions["dim_airline"]["airline_code"],
        dimensions["dim_airline"]["airline_id"]
    ))

    airport_map = dict(zip(
        dimensions["dim_airport"]["airport_code"],
        dimensions["dim_airport"]["airport_id"]
    ))

    weather_map = dict(zip(
        dimensions["dim_weather_condition"]["weather_type"],
        dimensions["dim_weather_condition"]["weather_id"]
    ))

    flight_map = dict(zip(
        dimensions["dim_flight"]["flight_number"],
        dimensions["dim_flight"]["flight_id"]
    ))

    aircraft_map = dict(zip(
        dimensions["dim_aircraft"]["tail_number"],
        dimensions["dim_aircraft"]["aircraft_id"]
    ))

    delay_map = dict(zip(
        dimensions["dim_delay_cause"]["delay_cause_type"],
        dimensions["dim_delay_cause"]["delay_cause_id"]
    ))

    fact = pd.DataFrame()

    fact["date_id"] = df["date_id"]
    fact["time_id"] = df["time_id"]
    fact["origin_airport_id"] = df["origin"].map(airport_map)
    fact["destination_airport_id"] = df["dest"].map(airport_map)
    fact["airline_id"] = df["airline_code"].map(airline_map)
    fact["weather_id"] = df["weather_type"].map(weather_map)
    fact["flight_id"] = df["flight_number"].map(flight_map)
    fact["aircraft_id"] = df["tail_number"].map(aircraft_map)
    fact["delay_cause_id"] = df["delay_cause_type"].map(delay_map)
    fact["delay_minutes"] = df["delay_minutes"]
    fact["cancellation_flag"] = df["cancellation_flag"]
    fact["passengers"] = df["passengers"]
    fact["scheduled_departure_datetime"] = df["scheduled_departure_datetime"]
    fact["actual_departure_datetime"] = df["actual_departure_datetime"]
    fact["scheduled_arrival_datetime"] = df["scheduled_arrival_datetime"]
    fact["actual_arrival_datetime"] = df["actual_arrival_datetime"]
    fact["delay_status"] = df["delay_status"]

    fact = fact.dropna(subset=[
        "date_id",
        "time_id",
        "origin_airport_id",
        "destination_airport_id",
        "airline_id",
        "weather_id",
        "flight_id",
        "aircraft_id",
        "delay_cause_id"
    ])

    fact.to_csv(PROCESSED_DIR / "fact_flightperformance.csv", index=False)

    print("Fact table created and saved to data/processed/.")
    return fact


# ------------------------------------------------------------
# LOAD
# ------------------------------------------------------------

def clear_database():
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM fact_flightperformance;"))
        conn.execute(text("DELETE FROM dim_delay_cause;"))
        conn.execute(text("DELETE FROM dim_aircraft;"))
        conn.execute(text("DELETE FROM dim_flight;"))
        conn.execute(text("DELETE FROM dim_weather_condition;"))
        conn.execute(text("DELETE FROM dim_airline;"))
        conn.execute(text("DELETE FROM dim_airport;"))
        conn.execute(text("DELETE FROM dim_time;"))
        conn.execute(text("DELETE FROM dim_date;"))

        conn.execute(text("ALTER SEQUENCE dim_airport_airport_id_seq RESTART WITH 1;"))
        conn.execute(text("ALTER SEQUENCE dim_airline_airline_id_seq RESTART WITH 1;"))
        conn.execute(text("ALTER SEQUENCE dim_weather_condition_weather_id_seq RESTART WITH 1;"))
        conn.execute(text("ALTER SEQUENCE dim_flight_flight_id_seq RESTART WITH 1;"))
        conn.execute(text("ALTER SEQUENCE dim_aircraft_aircraft_id_seq RESTART WITH 1;"))
        conn.execute(text("ALTER SEQUENCE dim_delay_cause_delay_cause_id_seq RESTART WITH 1;"))
        conn.execute(text("ALTER SEQUENCE fact_flightperformance_flight_performance_id_seq RESTART WITH 1;"))

    print("Existing database rows cleared.")


def load(dimensions, fact_table):
    clear_database()

    dimensions["dim_date"].to_sql("dim_date", engine, if_exists="append", index=False)
    dimensions["dim_time"].to_sql("dim_time", engine, if_exists="append", index=False)
    dimensions["dim_airport"].to_sql("dim_airport", engine, if_exists="append", index=False)
    dimensions["dim_airline"].to_sql("dim_airline", engine, if_exists="append", index=False)
    dimensions["dim_weather_condition"].to_sql("dim_weather_condition", engine, if_exists="append", index=False)
    dimensions["dim_flight"].to_sql("dim_flight", engine, if_exists="append", index=False)
    dimensions["dim_aircraft"].to_sql("dim_aircraft", engine, if_exists="append", index=False)
    dimensions["dim_delay_cause"].to_sql("dim_delay_cause", engine, if_exists="append", index=False)

    fact_table.to_sql("fact_flightperformance", engine, if_exists="append", index=False)

    print("Load complete. Data inserted into PostgreSQL.")


def main():
    raw_df = extract()
    transformed_df = transform(raw_df)
    dimensions = build_dimensions(transformed_df)
    fact_table = build_fact_table(transformed_df, dimensions)
    load(dimensions, fact_table)

    print("ETL process completed successfully.")


if __name__ == "__main__":
    main()