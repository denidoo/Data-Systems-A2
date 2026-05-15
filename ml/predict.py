import joblib
import pandas as pd
from pathlib import Path
from sqlalchemy import text

from database.db_config import engine


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / "models" / "best_model.pkl"


def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "Model file not found. Run `python -m ml.train_model` first."
        )

    return joblib.load(MODEL_PATH)


def build_full_dataset_for_lookup():
    """
    Builds a joined dataset from the PostgreSQL warehouse.

    This is used by the app to populate dropdowns and to find historical
    records for flight/date lookup.
    """

    query = """
        SELECT
            fp.flight_performance_id,

            dd.full_date,
            dd.day,
            dd.month,
            dd.year,

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
            ON fp.time_id = dt.time_id

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

    return pd.read_sql(query, engine)


def get_latest_api_features(flight_number):
    """
    Reads the most recent Aviationstack API row already stored in the warehouse.

    This replaces direct API calls during prediction.
    """

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
        JOIN dim_flight fl
            ON fp.flight_id = fl.flight_id
        WHERE fl.flight_number = :flight_number
        AND fp.api_source = 'Aviationstack'
        ORDER BY fp.api_pull_timestamp DESC
        LIMIT 1;
    """)

    with engine.connect() as conn:
        result = conn.execute(
            query,
            {"flight_number": flight_number.upper()}
        )

        row = result.fetchone()

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
            "api_destination_avg_arrival_delay": 0
        }

    return dict(row._mapping)


def get_historical_flight_features(flight_number, selected_date=None):
    """
    Finds the closest historical record for the selected flight.

    If the selected date exists in the warehouse, it uses that.
    Otherwise, it falls back to the most recent matching flight number.
    """

    if selected_date is not None:
        query = text("""
            SELECT
                fp.*,
                dd.full_date,
                dd.day,
                dd.month,
                dd.year,
                dt.hour,
                dt.minute,
                dt.time_of_day,
                oa.airport_code AS origin_airport_code,
                da.airport_code AS destination_airport_code,
                al.airline_code,
                fl.flight_number,
                fl.flight_type,
                fl.route_category,
                fl.route_distance,
                wc.weather_type,
                wc.temperature,
                wc.wind_speed,
                wc.visibility,
                ac.aircraft_model,
                ac.manufacturer,
                ac.seating_capacity,
                ac.aircraft_category,
                dc.delay_cause_type,
                dc.is_controllable
            FROM fact_flightperformance fp
            LEFT JOIN dim_date dd
                ON fp.date_id = dd.date_id
            LEFT JOIN dim_time dt
                ON fp.time_id = dt.time_id
            LEFT JOIN dim_airport oa
                ON fp.origin_airport_id = oa.airport_id
            LEFT JOIN dim_airport da
                ON fp.destination_airport_id = da.airport_id
            LEFT JOIN dim_airline al
                ON fp.airline_id = al.airline_id
            LEFT JOIN dim_flight fl
                ON fp.flight_id = fl.flight_id
            LEFT JOIN dim_weather_condition wc
                ON fp.weather_id = wc.weather_id
            LEFT JOIN dim_aircraft ac
                ON fp.aircraft_id = ac.aircraft_id
            LEFT JOIN dim_delay_cause dc
                ON fp.delay_cause_id = dc.delay_cause_id
            WHERE fl.flight_number = :flight_number
            AND dd.full_date = :selected_date
            LIMIT 1;
        """)

        params = {
            "flight_number": flight_number.upper(),
            "selected_date": selected_date
        }

    else:
        query = text("""
            SELECT
                fp.*,
                dd.full_date,
                dd.day,
                dd.month,
                dd.year,
                dt.hour,
                dt.minute,
                dt.time_of_day,
                oa.airport_code AS origin_airport_code,
                da.airport_code AS destination_airport_code,
                al.airline_code,
                fl.flight_number,
                fl.flight_type,
                fl.route_category,
                fl.route_distance,
                wc.weather_type,
                wc.temperature,
                wc.wind_speed,
                wc.visibility,
                ac.aircraft_model,
                ac.manufacturer,
                ac.seating_capacity,
                ac.aircraft_category,
                dc.delay_cause_type,
                dc.is_controllable
            FROM fact_flightperformance fp
            LEFT JOIN dim_date dd
                ON fp.date_id = dd.date_id
            LEFT JOIN dim_time dt
                ON fp.time_id = dt.time_id
            LEFT JOIN dim_airport oa
                ON fp.origin_airport_id = oa.airport_id
            LEFT JOIN dim_airport da
                ON fp.destination_airport_id = da.airport_id
            LEFT JOIN dim_airline al
                ON fp.airline_id = al.airline_id
            LEFT JOIN dim_flight fl
                ON fp.flight_id = fl.flight_id
            LEFT JOIN dim_weather_condition wc
                ON fp.weather_id = wc.weather_id
            LEFT JOIN dim_aircraft ac
                ON fp.aircraft_id = ac.aircraft_id
            LEFT JOIN dim_delay_cause dc
                ON fp.delay_cause_id = dc.delay_cause_id
            WHERE fl.flight_number = :flight_number
            ORDER BY dd.full_date DESC
            LIMIT 1;
        """)

        params = {
            "flight_number": flight_number.upper()
        }

    with engine.connect() as conn:
        result = conn.execute(query, params)
        row = result.fetchone()

    if row is None:
        return None

    return dict(row._mapping)


def build_prediction_input(flight_number, selected_date=None):
    """
    Combines historical warehouse features with the latest stored API features.
    """

    historical = get_historical_flight_features(
        flight_number,
        selected_date
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

    input_df = pd.DataFrame([combined])

    return input_df


def clean_model_input(input_df, model):
    """
    Aligns the prediction input with the trained model's expected columns.
    """

    if hasattr(model, "feature_names_in_"):
        expected_columns = list(model.feature_names_in_)

        for column in expected_columns:
            if column not in input_df.columns:
                input_df[column] = 0

        input_df = input_df[expected_columns]

    return input_df


def predict_from_details(flight_number, selected_date=None):
    """
    Main prediction function used by app.py.

    It now reads API values from PostgreSQL instead of calling Aviationstack live.
    """

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

    result = {
        "flight_number": flight_number.upper(),
        "prediction": prediction,
        "prediction_label": "Delayed" if int(prediction) == 1 else "On Time",
        "probability": probability,
        "used_api_data": input_df.iloc[0].get("api_source") == "Aviationstack",
        "api_live_flight_status": input_df.iloc[0].get("api_live_flight_status", "Unknown"),
        "api_departure_delay_minutes": input_df.iloc[0].get("api_departure_delay_minutes", 0),
        "api_arrival_delay_minutes": input_df.iloc[0].get("api_arrival_delay_minutes", 0)
    }

    return result