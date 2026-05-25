import joblib
import pandas as pd
from pathlib import Path
from sqlalchemy import text

from database.db_config import engine


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = PROJECT_ROOT / "models" / "flight_delay_model.pkl"


def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model file not found at {MODEL_PATH}. "
            "Run `python -m ml.train_model` first."
        )

    return joblib.load(MODEL_PATH)


def build_full_dataset_for_lookup():
    query = """
        SELECT
            fp.flight_performance_id,

            dd.full_date,
            dd.day,
            dd.month,
            dd.year,
            dd.day_of_week,
            dd.is_weekend,

            dt.hour,
            dt.minute,
            dt.time_of_day,

            oa.airport_code AS origin_airport_code,
            oa.airport_name AS origin_airport_name,

            da.airport_code AS destination_airport_code,
            da.airport_name AS destination_airport_name,

            al.airline_code,
            al.airline_name,

            wc.weather_type,
            wc.temperature,
            wc.wind_speed,
            wc.visibility,

            fl.flight_number,
            fl.flight_type,
            fl.route_category,
            fl.route_distance,

            ac.aircraft_model,
            ac.manufacturer,
            ac.seating_capacity,
            ac.aircraft_category,

            dc.delay_cause_type,
            dc.delay_cause_detail,
            dc.is_controllable,

            fp.delay_minutes,
            fp.cancellation_flag,
            fp.passengers,
            fp.scheduled_departure_datetime,
            fp.actual_departure_datetime,
            fp.scheduled_arrival_datetime,
            fp.actual_arrival_datetime,
            fp.delay_status,

            fp.api_source,
            fp.api_pull_timestamp,
            fp.api_live_flight_status,
            fp.api_departure_delay_minutes,
            fp.api_arrival_delay_minutes,
            fp.api_origin_live_departures_count,
            fp.api_origin_live_arrivals_count,
            fp.api_origin_delayed_departures_count,
            fp.api_origin_delayed_arrivals_count,
            fp.api_origin_avg_departure_delay,
            fp.api_origin_avg_arrival_delay,
            fp.api_destination_live_departures_count,
            fp.api_destination_live_arrivals_count,
            fp.api_destination_delayed_departures_count,
            fp.api_destination_delayed_arrivals_count,
            fp.api_destination_avg_departure_delay,
            fp.api_destination_avg_arrival_delay

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

        LEFT JOIN dim_weather_condition wc
            ON fp.weather_id = wc.weather_id

        LEFT JOIN dim_flight fl
            ON fp.flight_id = fl.flight_id

        LEFT JOIN dim_aircraft ac
            ON fp.aircraft_id = ac.aircraft_id

        LEFT JOIN dim_delay_cause dc
            ON fp.delay_cause_id = dc.delay_cause_id;
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


def get_latest_api_features(flight_number):
    query = text("""
        SELECT
            fp.api_source,
            fp.api_pull_timestamp,
            fp.api_live_flight_status,
            fp.api_departure_delay_minutes,
            fp.api_arrival_delay_minutes,
            fp.api_origin_live_departures_count,
            fp.api_origin_live_arrivals_count,
            fp.api_origin_delayed_departures_count,
            fp.api_origin_delayed_arrivals_count,
            fp.api_origin_avg_departure_delay,
            fp.api_origin_avg_arrival_delay,
            fp.api_destination_live_departures_count,
            fp.api_destination_live_arrivals_count,
            fp.api_destination_delayed_departures_count,
            fp.api_destination_delayed_arrivals_count,
            fp.api_destination_avg_departure_delay,
            fp.api_destination_avg_arrival_delay

        FROM fact_flightperformance fp

        LEFT JOIN dim_flight fl
            ON fp.flight_id = fl.flight_id

        WHERE UPPER(fl.flight_number) = :flight_number

        ORDER BY fp.api_pull_timestamp DESC NULLS LAST
        LIMIT 1;
    """)

    with engine.connect() as conn:
        row = conn.execute(
            query,
            {"flight_number": flight_number.upper()}
        ).fetchone()

    if row is None:
        return {
            "api_source": "None",
            "api_live_flight_status": "Unknown",
            "api_departure_delay_minutes": 0,
            "api_arrival_delay_minutes": 0,
            "api_origin_live_departures_count": 0,
            "api_origin_live_arrivals_count": 0,
            "api_origin_delayed_departures_count": 0,
            "api_origin_delayed_arrivals_count": 0,
            "api_origin_avg_departure_delay": 0,
            "api_origin_avg_arrival_delay": 0,
            "api_destination_live_departures_count": 0,
            "api_destination_live_arrivals_count": 0,
            "api_destination_delayed_departures_count": 0,
            "api_destination_delayed_arrivals_count": 0,
            "api_destination_avg_departure_delay": 0,
            "api_destination_avg_arrival_delay": 0,
        }

    return dict(row._mapping)


def get_historical_flight_features(flight_number, selected_date=None):
    query = text("""
        SELECT
            fp.flight_performance_id,

            dd.full_date,
            dd.day,
            dd.month,
            dd.year,
            dd.day_of_week,
            dd.is_weekend,

            dt.hour,
            dt.minute,
            dt.time_of_day,

            oa.airport_code AS origin_airport_code,
            da.airport_code AS destination_airport_code,

            al.airline_code,

            wc.weather_type,
            wc.temperature,
            wc.wind_speed,
            wc.visibility,

            fl.flight_number,
            fl.flight_type,
            fl.route_category,
            fl.route_distance,

            ac.aircraft_model,
            ac.manufacturer,
            ac.seating_capacity,
            ac.aircraft_category,

            dc.delay_cause_type,
            dc.delay_cause_detail,
            dc.is_controllable,

            fp.delay_minutes,
            fp.cancellation_flag,
            fp.passengers,
            fp.scheduled_departure_datetime,
            fp.actual_departure_datetime,
            fp.scheduled_arrival_datetime,
            fp.actual_arrival_datetime,
            fp.delay_status

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

        LEFT JOIN dim_weather_condition wc
            ON fp.weather_id = wc.weather_id

        LEFT JOIN dim_flight fl
            ON fp.flight_id = fl.flight_id

        LEFT JOIN dim_aircraft ac
            ON fp.aircraft_id = ac.aircraft_id

        LEFT JOIN dim_delay_cause dc
            ON fp.delay_cause_id = dc.delay_cause_id

        WHERE UPPER(fl.flight_number) = :flight_number

        ORDER BY dd.full_date DESC NULLS LAST
        LIMIT 1;
    """)

    with engine.connect() as conn:
        row = conn.execute(
            query,
            {"flight_number": flight_number.upper()}
        ).fetchone()

    if row is None:
        return None

    historical = dict(row._mapping)

    if selected_date is not None:
        selected_date = pd.to_datetime(selected_date)

        historical["full_date"] = selected_date
        historical["day"] = selected_date.day
        historical["month"] = selected_date.month
        historical["year"] = selected_date.year
        historical["quarter"] = selected_date.quarter
        historical["day_of_week"] = selected_date.dayofweek
        historical["is_weekend"] = selected_date.dayofweek in [5, 6]
    else:
        historical["quarter"] = (
            ((int(historical["month"]) - 1) // 3) + 1
            if historical.get("month") is not None
            else 1
        )

    return historical


def build_prediction_input(flight_number, selected_date=None):
    historical = get_historical_flight_features(
        flight_number=flight_number,
        selected_date=selected_date
    )

    if historical is None:
        raise ValueError(
            f"No historical data found for flight number {flight_number}."
        )

    api_features = get_latest_api_features(flight_number)

    combined = {
        **historical,
        **api_features
    }

    return pd.DataFrame([combined])


def clean_model_input(input_df, model):
    if hasattr(model, "feature_names_in_"):
        expected_columns = list(model.feature_names_in_)

        for column in expected_columns:
            if column not in input_df.columns:
                input_df[column] = 0

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
        "used_api_data": input_df.iloc[0].get("api_source") not in [None, "None"],
        "api_live_flight_status": input_df.iloc[0].get(
            "api_live_flight_status",
            "Unknown"
        ),
        "api_departure_delay_minutes": input_df.iloc[0].get(
            "api_departure_delay_minutes",
            0
        ),
        "api_arrival_delay_minutes": input_df.iloc[0].get(
            "api_arrival_delay_minutes",
            0
        ),
    }