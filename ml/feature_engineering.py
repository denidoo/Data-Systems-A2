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

    # Date-based features
    df["full_date"] = pd.to_datetime(df["full_date"], errors="coerce")
    df["day_of_week"] = df["full_date"].dt.dayofweek
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)

    # Time-based features
    df["is_night_flight"] = df["hour"].between(0, 5).astype(int)
    df["is_morning"] = df["hour"].between(6, 11).astype(int)
    df["is_afternoon"] = df["hour"].between(12, 17).astype(int)
    df["is_evening"] = df["hour"].between(18, 23).astype(int)
    df["is_peak_hour"] = df["hour"].isin([7, 8, 9, 16, 17, 18, 19]).astype(int)

    # Seasonal features
    df["is_winter"] = df["month"].isin([12, 1, 2]).astype(int)
    df["is_summer"] = df["month"].isin([6, 7, 8]).astype(int)
    df["is_holiday_season"] = df["month"].isin([12, 1]).astype(int)

    # Weather severity features
    df["low_visibility"] = (pd.to_numeric(df["visibility"], errors="coerce") < 5).astype(int)
    df["high_wind"] = (pd.to_numeric(df["wind_speed"], errors="coerce") > 20).astype(int)

    df["bad_weather"] = df["weather_type"].isin(
        ["Rain", "Storm", "Snow", "Fog", "Thunderstorm"]
    ).astype(int)

    # Distance category features
    df["route_distance"] = pd.to_numeric(df["route_distance"], errors="coerce")

    df["short_route"] = (df["route_distance"] < 500).astype(int)
    df["medium_route"] = df["route_distance"].between(500, 1500).astype(int)
    df["long_route"] = (df["route_distance"] > 1500).astype(int)

    # Target variable
    df["target_delayed"] = (df["delay_status"] == "Delayed").astype(int)

    # Historical delay-rate features
    df["airline_delay_rate"] = df.groupby("airline_code")["target_delayed"].transform("mean")

    df["origin_delay_rate"] = df.groupby(
        "origin_airport_code"
    )["target_delayed"].transform("mean")

    df["destination_delay_rate"] = df.groupby(
        "destination_airport_code"
    )["target_delayed"].transform("mean")

    df["route_delay_rate"] = df.groupby(
        ["origin_airport_code", "destination_airport_code"]
    )["target_delayed"].transform("mean")

    df["aircraft_delay_rate"] = df.groupby(
        "aircraft_category"
    )["target_delayed"].transform("mean")

    df["weather_delay_rate"] = df.groupby(
        "weather_type"
    )["target_delayed"].transform("mean")

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
        "is_morning",
        "is_afternoon",
        "is_evening",
        "is_peak_hour",

        "is_winter",
        "is_summer",
        "is_holiday_season",

        "temperature",
        "wind_speed",
        "visibility",
        "low_visibility",
        "high_wind",
        "bad_weather",

        "route_distance",
        "short_route",
        "medium_route",
        "long_route",

        "seating_capacity",

        "airline_delay_rate",
        "origin_delay_rate",
        "destination_delay_rate",
        "route_delay_rate",
        "aircraft_delay_rate",
        "weather_delay_rate",
    ]

    categorical_features = [
        "time_of_day",
        "airline_code",
        "origin_airport_code",
        "destination_airport_code",
        "weather_type",
        "flight_type",
        "route_category",
        "aircraft_category",
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