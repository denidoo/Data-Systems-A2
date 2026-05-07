import pandas as pd
from pathlib import Path


PROCESSED_DIR = Path("data/processed")


def load_processed_tables():
    fact = pd.read_csv(PROCESSED_DIR / "fact_flightperformance.csv")
    dim_date = pd.read_csv(PROCESSED_DIR / "dim_date.csv")
    dim_time = pd.read_csv(PROCESSED_DIR / "dim_time.csv")
    dim_airport = pd.read_csv(PROCESSED_DIR / "dim_airport.csv")
    dim_airline = pd.read_csv(PROCESSED_DIR / "dim_airline.csv")
    dim_weather = pd.read_csv(PROCESSED_DIR / "dim_weather_condition.csv")
    dim_flight = pd.read_csv(PROCESSED_DIR / "dim_flight.csv")
    dim_aircraft = pd.read_csv(PROCESSED_DIR / "dim_aircraft.csv")

    return {
        "fact": fact,
        "dim_date": dim_date,
        "dim_time": dim_time,
        "dim_airport": dim_airport,
        "dim_airline": dim_airline,
        "dim_weather": dim_weather,
        "dim_flight": dim_flight,
        "dim_aircraft": dim_aircraft,
    }


def build_training_dataset():
    tables = load_processed_tables()

    fact = tables["fact"]
    dim_date = tables["dim_date"]
    dim_time = tables["dim_time"]
    dim_airline = tables["dim_airline"]
    dim_weather = tables["dim_weather"]
    dim_flight = tables["dim_flight"]
    dim_aircraft = tables["dim_aircraft"]

    dim_airport = tables["dim_airport"]

    origin_airport = dim_airport.add_prefix("origin_")
    destination_airport = dim_airport.add_prefix("destination_")

    df = fact.merge(dim_date, on="date_id", how="left")
    df = df.merge(dim_time, on="time_id", how="left")
    df = df.merge(dim_airline, on="airline_id", how="left")
    df = df.merge(dim_weather, on="weather_id", how="left")
    df = df.merge(dim_flight, on="flight_id", how="left")
    df = df.merge(dim_aircraft, on="aircraft_id", how="left")

    df = df.merge(
        origin_airport,
        left_on="origin_airport_id",
        right_on="origin_airport_id",
        how="left"
    )

    df = df.merge(
        destination_airport,
        left_on="destination_airport_id",
        right_on="destination_airport_id",
        how="left"
    )

    df["full_date"] = pd.to_datetime(df["full_date"], errors="coerce")
    df["day_of_week"] = df["full_date"].dt.dayofweek
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    df["is_night_flight"] = df["hour"].between(0, 5).astype(int)

    df["target_delayed"] = (df["delay_status"] == "Delayed").astype(int)

    return df


def get_feature_columns():
    numeric_features = [
        "day",
        "month",
        "year",
        "day_of_week",
        "is_weekend",
        "hour",
        "minute",
        "is_night_flight",
        "temperature",
        "wind_speed",
        "visibility",
        "route_distance",
        "seating_capacity"
    ]

    categorical_features = [
        "time_of_day",
        "airline_code",
        "origin_airport_code",
        "destination_airport_code",
        "weather_type",
        "flight_type",
        "route_category",
        "aircraft_category"
    ]

    return numeric_features, categorical_features


def prepare_features(df):
    numeric_features, categorical_features = get_feature_columns()

    required_columns = numeric_features + categorical_features + ["target_delayed"]

    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        raise ValueError(f"Missing columns for ML training: {missing_columns}")

    X = df[numeric_features + categorical_features].copy()
    y = df["target_delayed"].copy()

    for col in numeric_features:
        X[col] = pd.to_numeric(X[col], errors="coerce").fillna(0)

    for col in categorical_features:
        X[col] = X[col].fillna("Unknown").astype(str)

    return X, y