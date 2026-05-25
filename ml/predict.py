import joblib
import pandas as pd
from pathlib import Path
from sqlalchemy import inspect, text

from database.db_config import engine


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = PROJECT_ROOT / "models" / "flight_delay_model.pkl"


def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found at {MODEL_PATH}. Run: python -m ml.train_model"
        )
    return joblib.load(MODEL_PATH)


def get_columns(table_name):
    inspector = inspect(engine)
    return [col["name"] for col in inspector.get_columns(table_name)]


def first_existing(columns, options):
    for option in options:
        if option in columns:
            return option
    return None


def build_full_dataset_for_lookup():
    fact_cols = get_columns("fact_flightperformance")
    date_cols = get_columns("dim_date")
    time_cols = get_columns("dim_time")
    airport_cols = get_columns("dim_airport")
    airline_cols = get_columns("dim_airline")
    flight_cols = get_columns("dim_flight")
    aircraft_cols = get_columns("dim_aircraft")
    delay_cols = get_columns("dim_delay_cause")

    weather_cols = []
    try:
        weather_cols = get_columns("dim_weather_condition")
    except Exception:
        pass

    weather_pk = first_existing(weather_cols, ["weather_condition_id", "weather_id"])

    select_parts = [
        "fp.flight_performance_id",
        "fp.delay_minutes",
        "fp.is_delayed",
        "fp.created_at",
        "fp.updated_at",
    ]

    # Date fields
    for col in ["full_date", "day", "month", "year", "day_of_week", "is_weekend"]:
        if col in date_cols:
            select_parts.append(f"dd.{col}")

    # Time fields
    for col in ["hour", "minute", "time_of_day"]:
        if col in time_cols:
            select_parts.append(f"dt.{col}")

    # Airports
    if "airport_code" in airport_cols:
        select_parts.append("oa.airport_code AS origin_airport_code")
        select_parts.append("da.airport_code AS destination_airport_code")

    if "airport_name" in airport_cols:
        select_parts.append("oa.airport_name AS origin_airport_name")
        select_parts.append("da.airport_name AS destination_airport_name")

    # Airline
    for col in ["airline_code", "airline_name"]:
        if col in airline_cols:
            select_parts.append(f"al.{col}")

    # Flight
    for col in ["flight_number", "flight_type", "route_category", "route_distance"]:
        if col in flight_cols:
            select_parts.append(f"fl.{col}")

    # Aircraft
    for col in ["aircraft_model", "manufacturer", "seating_capacity", "aircraft_category"]:
        if col in aircraft_cols:
            select_parts.append(f"ac.{col}")

    # Weather
    for col in ["weather_type", "temperature", "wind_speed", "visibility"]:
        if col in weather_cols:
            select_parts.append(f"wc.{col}")

    # Delay cause
    for col in ["delay_cause_type", "delay_cause_detail", "is_controllable"]:
        if col in delay_cols:
            select_parts.append(f"dc.{col}")

    query = f"""
        SELECT
            {", ".join(select_parts)}
        FROM fact_flightperformance fp

        LEFT JOIN dim_date dd
            ON fp.date_id = dd.date_id

        LEFT JOIN dim_time dt
            ON fp.scheduled_departure_time_id = dt.time_id

        LEFT JOIN dim_airport oa
            ON fp.origin_airport_id = oa.airport_id

        LEFT JOIN dim_airport da
            ON fp.destination_airport_id = da.airport_id

        LEFT JOIN dim_airline al
            ON fp.airline_id = al.airline_id

        LEFT JOIN dim_flight fl
            ON fp.flight_id = fl.flight_id

        LEFT JOIN dim_aircraft ac
            ON fp.aircraft_id = ac.aircraft_id

        LEFT JOIN dim_delay_cause dc
            ON fp.delay_cause_id = dc.delay_cause_id

        {"LEFT JOIN dim_weather_condition wc ON fp.weather_condition_id = wc." + weather_pk if weather_pk else ""}
    """

    df = pd.read_sql(query, engine)

    if "month" in df.columns:
        df["quarter"] = df["month"].apply(
            lambda x: ((int(x) - 1) // 3) + 1 if pd.notna(x) else 1
        )

    return df


def load_available_flights():
    df = build_full_dataset_for_lookup()

    if "flight_number" not in df.columns:
        return pd.DataFrame(columns=["flight_number"])

    return (
        df[["flight_number"]]
        .dropna()
        .drop_duplicates()
        .sort_values("flight_number")
        .reset_index(drop=True)
    )


def get_historical_flight_features(flight_number, selected_date=None):
    df = build_full_dataset_for_lookup()

    if "flight_number" not in df.columns:
        raise ValueError("flight_number column was not found after joining dim_flight.")

    match = df[df["flight_number"].astype(str).str.upper() == flight_number.upper()]

    if match.empty:
        return None

    row = match.iloc[0].to_dict()

    if selected_date is not None:
        selected_date = pd.to_datetime(selected_date)

        row["full_date"] = selected_date
        row["day"] = selected_date.day
        row["month"] = selected_date.month
        row["year"] = selected_date.year
        row["quarter"] = selected_date.quarter
        row["day_of_week"] = selected_date.dayofweek
        row["is_weekend"] = selected_date.dayofweek in [5, 6]

    return row


def build_prediction_input(flight_number, selected_date=None):
    row = get_historical_flight_features(flight_number, selected_date)

    if row is None:
        raise ValueError(f"No historical data found for flight number {flight_number}.")

    return pd.DataFrame([row])


def clean_model_input(input_df, model):
    input_df = input_df.copy()

    expected_columns = (
        list(model.feature_names_in_)
        if hasattr(model, "feature_names_in_")
        else list(input_df.columns)
    )

    # Try to detect categorical and numeric columns from the trained pipeline
    categorical_columns = []
    numeric_columns = []

    try:
        preprocessor = model.named_steps["preprocessor"]

        for name, transformer, columns in preprocessor.transformers_:
            if name.lower() in ["cat", "categorical", "categorical_features"]:
                categorical_columns.extend(list(columns))
            elif name.lower() in ["num", "numeric", "numeric_features"]:
                numeric_columns.extend(list(columns))
    except Exception:
        pass

    # Add missing expected columns using safe defaults
    for column in expected_columns:
        if column not in input_df.columns:
            if column in categorical_columns:
                input_df[column] = "Unknown"
            else:
                input_df[column] = 0

    # Clean categorical columns
    for column in input_df.columns:
        if column in categorical_columns or input_df[column].dtype == "object":
            input_df[column] = (
                input_df[column]
                .fillna("Unknown")
                .astype(str)
            )

    # Clean datetime columns
    for column in input_df.columns:
        if "date" in column.lower() or "time" in column.lower():
            input_df[column] = input_df[column].astype(str).fillna("Unknown")

    # Clean boolean columns
    for column in input_df.columns:
        if input_df[column].dtype == "bool":
            input_df[column] = input_df[column].astype(int)

    # Clean numeric columns
    for column in numeric_columns:
        if column in input_df.columns:
            input_df[column] = pd.to_numeric(input_df[column], errors="coerce").fillna(0)

    # Keep only the columns the model was trained on
    input_df = input_df[expected_columns]

    return input_df

def predict_from_details(flight_number, selected_date=None, flight_date=None):
    if selected_date is None and flight_date is not None:
        selected_date = flight_date

    model = load_model()

    input_df = build_prediction_input(
        flight_number=flight_number,
        selected_date=selected_date
    )

    model_input = clean_model_input(input_df, model)

    prediction = model.predict(model_input)[0]

    probability = None
    if hasattr(model, "predict_proba"):
        probability = model.predict_proba(model_input)[0].max()

    return {
        "flight_number": flight_number.upper(),
        "prediction": int(prediction),
        "prediction_label": "Delayed" if int(prediction) == 1 else "On Time",
        "probability": probability,
        "used_api_data": False,
        "api_live_flight_status": "Not used",
        "api_departure_delay_minutes": 0,
        "api_arrival_delay_minutes": 0,
    }