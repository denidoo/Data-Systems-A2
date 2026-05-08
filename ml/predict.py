import joblib
import pandas as pd
from pathlib import Path


PROCESSED_DIR = Path("data/processed")
MODEL_PATH = Path("ml/models/best_flight_delay_model.pkl")


def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"No trained model found at {MODEL_PATH}. Run this first: python -m ml.model"
        )

    return joblib.load(MODEL_PATH)


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


def build_full_dataset_for_lookup():
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
    df["target_delayed"] = (df["delay_status"] == "Delayed").astype(int)

    return df


def get_historical_rate(df, column_name, value, default_rate):
    if column_name not in df.columns:
        return default_rate

    matching_rows = df[df[column_name].astype(str) == str(value)]

    if matching_rows.empty:
        return default_rate

    return matching_rows["target_delayed"].mean()


def get_route_delay_rate(df, origin_airport_code, destination_airport_code, default_rate):
    if "origin_airport_code" not in df.columns or "destination_airport_code" not in df.columns:
        return default_rate

    matching_rows = df[
        (df["origin_airport_code"].astype(str) == str(origin_airport_code)) &
        (df["destination_airport_code"].astype(str) == str(destination_airport_code))
    ]

    if matching_rows.empty:
        return default_rate

    return matching_rows["target_delayed"].mean()


def find_flight_record(flight_number, flight_date=None):
    df = build_full_dataset_for_lookup()

    if "flight_number" not in df.columns:
        raise ValueError("Column 'flight_number' does not exist in your processed flight data.")

    flight_matches = df[df["flight_number"].astype(str) == str(flight_number)]

    if flight_date is not None:
        flight_date = pd.to_datetime(flight_date, errors="coerce")

        if pd.notna(flight_date):
            same_month_day = (
                (flight_matches["full_date"].dt.month == flight_date.month) &
                (flight_matches["full_date"].dt.day == flight_date.day)
            )

            exact_date_matches = flight_matches[flight_matches["full_date"] == flight_date]

            if not exact_date_matches.empty:
                flight_matches = exact_date_matches
            elif not flight_matches[same_month_day].empty:
                flight_matches = flight_matches[same_month_day]

    if flight_matches.empty:
        raise ValueError(
            f"No matching flight found for flight number {flight_number}. "
            "Add this flight to your processed data first, or update predict_from_details() manually."
        )

    return flight_matches.iloc[0], df


def add_engineered_features(input_df, historical_df):
    input_df = input_df.copy()

    numeric_defaults = {
        "day": 1,
        "month": 1,
        "year": 2024,
        "hour": 12,
        "minute": 0,
        "temperature": 20,
        "wind_speed": 0,
        "visibility": 10,
        "route_distance": 0,
        "seating_capacity": 150,
        "day_of_week": 0,
    }

    for col, default in numeric_defaults.items():
        if col not in input_df.columns:
            input_df[col] = default

        input_df[col] = pd.to_numeric(input_df[col], errors="coerce").fillna(default)

    categorical_defaults = {
        "time_of_day": "Unknown",
        "airline_code": "Unknown",
        "origin_airport_code": "Unknown",
        "destination_airport_code": "Unknown",
        "weather_type": "Unknown",
        "flight_type": "Unknown",
        "route_category": "Unknown",
        "aircraft_category": "Unknown",
    }

    for col, default in categorical_defaults.items():
        if col not in input_df.columns:
            input_df[col] = default

        input_df[col] = input_df[col].fillna(default).astype(str)

    input_df["is_weekend"] = input_df["day_of_week"].isin([5, 6]).astype(int)

    input_df["is_night_flight"] = input_df["hour"].between(0, 5).astype(int)
    input_df["is_morning"] = input_df["hour"].between(6, 11).astype(int)
    input_df["is_afternoon"] = input_df["hour"].between(12, 17).astype(int)
    input_df["is_evening"] = input_df["hour"].between(18, 23).astype(int)
    input_df["is_peak_hour"] = input_df["hour"].isin([7, 8, 9, 16, 17, 18, 19]).astype(int)

    input_df["is_winter"] = input_df["month"].isin([12, 1, 2]).astype(int)
    input_df["is_summer"] = input_df["month"].isin([6, 7, 8]).astype(int)
    input_df["is_holiday_season"] = input_df["month"].isin([12, 1]).astype(int)

    input_df["low_visibility"] = (input_df["visibility"] < 5).astype(int)
    input_df["high_wind"] = (input_df["wind_speed"] > 20).astype(int)

    input_df["bad_weather"] = input_df["weather_type"].isin(
        ["Rain", "Storm", "Snow", "Fog", "Thunderstorm"]
    ).astype(int)

    input_df["short_route"] = (input_df["route_distance"] < 500).astype(int)
    input_df["medium_route"] = input_df["route_distance"].between(500, 1500).astype(int)
    input_df["long_route"] = (input_df["route_distance"] > 1500).astype(int)

    default_delay_rate = historical_df["target_delayed"].mean()

    input_df["airline_delay_rate"] = input_df["airline_code"].apply(
        lambda x: get_historical_rate(historical_df, "airline_code", x, default_delay_rate)
    )

    input_df["origin_delay_rate"] = input_df["origin_airport_code"].apply(
        lambda x: get_historical_rate(historical_df, "origin_airport_code", x, default_delay_rate)
    )

    input_df["destination_delay_rate"] = input_df["destination_airport_code"].apply(
        lambda x: get_historical_rate(historical_df, "destination_airport_code", x, default_delay_rate)
    )

    input_df["aircraft_delay_rate"] = input_df["aircraft_category"].apply(
        lambda x: get_historical_rate(historical_df, "aircraft_category", x, default_delay_rate)
    )

    input_df["weather_delay_rate"] = input_df["weather_type"].apply(
        lambda x: get_historical_rate(historical_df, "weather_type", x, default_delay_rate)
    )

    input_df["route_delay_rate"] = input_df.apply(
        lambda row: get_route_delay_rate(
            historical_df,
            row["origin_airport_code"],
            row["destination_airport_code"],
            default_delay_rate
        ),
        axis=1
    )

    return input_df


def get_model_feature_columns():
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

    return numeric_features + categorical_features


def predict_delay(input_df):
    model = load_model()

    required_columns = get_model_feature_columns()
    missing_columns = [col for col in required_columns if col not in input_df.columns]

    if missing_columns:
        raise ValueError(f"Missing columns before prediction: {missing_columns}")

    input_df = input_df[required_columns].copy()

    prediction = model.predict(input_df)[0]

    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(input_df)[0]
        delayed_probability = probabilities[1]
    else:
        delayed_probability = None

    if prediction == 1:
        status = "Delayed"
    else:
        status = "Not Delayed"

    return {
        "prediction": int(prediction),
        "status": status,
        "delayed_probability": delayed_probability
    }


def predict_from_details(flight_number, flight_date=None):
    flight_record, historical_df = find_flight_record(flight_number, flight_date)

    input_data = {
        "day": flight_record.get("day", 1),
        "month": flight_record.get("month", 1),
        "year": flight_record.get("year", 2024),
        "day_of_week": flight_record.get("full_date", pd.Timestamp("2024-01-01")).dayofweek
        if pd.notna(flight_record.get("full_date", pd.NaT)) else 0,

        "hour": flight_record.get("hour", 12),
        "minute": flight_record.get("minute", 0),
        "time_of_day": flight_record.get("time_of_day", "Unknown"),

        "airline_code": flight_record.get("airline_code", "Unknown"),
        "origin_airport_code": flight_record.get("origin_airport_code", "Unknown"),
        "destination_airport_code": flight_record.get("destination_airport_code", "Unknown"),

        "weather_type": flight_record.get("weather_type", "Unknown"),
        "temperature": flight_record.get("temperature", 20),
        "wind_speed": flight_record.get("wind_speed", 0),
        "visibility": flight_record.get("visibility", 10),

        "flight_type": flight_record.get("flight_type", "Unknown"),
        "route_category": flight_record.get("route_category", "Unknown"),
        "route_distance": flight_record.get("route_distance", 0),

        "aircraft_category": flight_record.get("aircraft_category", "Unknown"),
        "seating_capacity": flight_record.get("seating_capacity", 150),
    }

    input_df = pd.DataFrame([input_data])
    input_df = add_engineered_features(input_df, historical_df)

    result = predict_delay(input_df)

    return result, input_df


if __name__ == "__main__":
    historical_df = build_full_dataset_for_lookup()

    print("\nAvailable flight numbers:")
    print(historical_df["flight_number"].dropna().astype(str).head(20).to_list())

    test_flight_number = historical_df["flight_number"].dropna().astype(str).iloc[0]
    test_flight_date = None

    print(f"\nTesting prediction for flight number: {test_flight_number}")

    result, input_df = predict_from_details(
        flight_number=test_flight_number,
        flight_date=test_flight_date
    )

    print("\nPrediction Input:")
    print(input_df.T)

    print("\nPrediction Result:")
    print(f"Status: {result['status']}")

    if result["delayed_probability"] is not None:
        print(f"Delayed Probability: {result['delayed_probability']:.2%}")