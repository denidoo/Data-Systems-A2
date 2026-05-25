import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import text

from api.aviation_stack_api import get_live_flights
from database.create_tables import create_tables
from database.db_config import engine

load_dotenv()

AVIATIONSTACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY")


def clean_api_time(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).time()
    except ValueError:
        return None


def fetch_api_flights(limit=2000):
    if not AVIATIONSTACK_API_KEY:
        raise ValueError("AVIATIONSTACK_API_KEY is missing from .env")

    url = "http://api.aviationstack.com/v1/flights"

    params = {
        "access_key": AVIATIONSTACK_API_KEY,
        "limit": limit
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    payload = response.json()

    return payload.get("data", [])


def ensure_dimension_values(conn, record):
    conn.execute(text("""
        INSERT INTO dim_airline (airline_code, airline_name)
        VALUES (:airline_code, :airline_name)
        ON CONFLICT (airline_code) DO NOTHING;
    """), record)

    conn.execute(text("""
        INSERT INTO dim_airport (airport_code, airport_name, city, state, country)
        VALUES (:origin_airport_code, :origin_airport_name, NULL, NULL, NULL)
        ON CONFLICT (airport_code) DO NOTHING;
    """), record)

    conn.execute(text("""
        INSERT INTO dim_airport (airport_code, airport_name, city, state, country)
        VALUES (:destination_airport_code, :destination_airport_name, NULL, NULL, NULL)
        ON CONFLICT (airport_code) DO NOTHING;
    """), record)

    conn.execute(text("""
        INSERT INTO dim_flight (flight_number)
        VALUES (:flight_number)
        ON CONFLICT (flight_number) DO NOTHING;
    """), record)

    conn.execute(text("""
        INSERT INTO dim_aircraft (aircraft_type)
        VALUES (:aircraft_type)
        ON CONFLICT (aircraft_type) DO NOTHING;
    """), record)

    conn.execute(text("""
        INSERT INTO dim_weather_condition (weather_condition)
        VALUES (:weather_condition)
        ON CONFLICT (weather_condition) DO NOTHING;
    """), record)

    conn.execute(text("""
        INSERT INTO dim_delay_cause (delay_cause)
        VALUES (:delay_cause)
        ON CONFLICT (delay_cause) DO NOTHING;
    """), record)

    conn.execute(text("""
        INSERT INTO dim_date (
            full_date,
            year,
            month,
            day,
            quarter,
            day_of_week,
            is_weekend
        )
        VALUES (
            :flight_date,
            EXTRACT(YEAR FROM CAST(:flight_date AS DATE)),
            EXTRACT(MONTH FROM CAST(:flight_date AS DATE)),
            EXTRACT(DAY FROM CAST(:flight_date AS DATE)),
            EXTRACT(QUARTER FROM CAST(:flight_date AS DATE)),
            EXTRACT(DOW FROM CAST(:flight_date AS DATE)),
            CASE 
                WHEN EXTRACT(DOW FROM CAST(:flight_date AS DATE)) IN (0, 6) THEN TRUE 
                ELSE FALSE 
            END
        )
        ON CONFLICT (full_date) DO NOTHING;
    """), record)

    for key in ["scheduled_departure_time", "actual_departure_time"]:
        if record[key] is not None:
            conn.execute(text("""
                INSERT INTO dim_time (
                    time_value,
                    hour,
                    minute,
                    time_of_day
                )
                VALUES (
                    :time_value,
                    EXTRACT(HOUR FROM CAST(:time_value AS TIME)),
                    EXTRACT(MINUTE FROM CAST(:time_value AS TIME)),
                    CASE
                        WHEN EXTRACT(HOUR FROM CAST(:time_value AS TIME)) BETWEEN 5 AND 11 THEN 'Morning'
                        WHEN EXTRACT(HOUR FROM CAST(:time_value AS TIME)) BETWEEN 12 AND 16 THEN 'Afternoon'
                        WHEN EXTRACT(HOUR FROM CAST(:time_value AS TIME)) BETWEEN 17 AND 20 THEN 'Evening'
                        ELSE 'Night'
                    END
                )
                ON CONFLICT (time_value) DO NOTHING;
            """), {"time_value": record[key]})


def upsert_api_fact_record(conn, record):
    query = text("""
        INSERT INTO fact_flightperformance (
            flight_id,
            airline_id,
            origin_airport_id,
            destination_airport_id,
            date_id,
            scheduled_departure_time_id,
            actual_departure_time_id,
            aircraft_id,
            weather_condition_id,
            delay_cause_id,
            delay_minutes,
            is_delayed,
            updated_at
        )
        SELECT
            df.flight_id,
            da.airline_id,
            origin.airport_id,
            destination.airport_id,
            dd.date_id,
            scheduled.time_id,
            actual.time_id,
            dac.aircraft_id,
            dw.weather_condition_id,
            dc.delay_cause_id,
            :delay_minutes,
            :is_delayed,
            CURRENT_TIMESTAMP
        FROM dim_flight df
        JOIN dim_airline da
            ON da.airline_code = :airline_code
        JOIN dim_airport origin
            ON origin.airport_code = :origin_airport_code
        JOIN dim_airport destination
            ON destination.airport_code = :destination_airport_code
        JOIN dim_date dd
            ON dd.full_date = :flight_date
        JOIN dim_time scheduled
            ON scheduled.time_value = :scheduled_departure_time
        LEFT JOIN dim_time actual
            ON actual.time_value = :actual_departure_time
        JOIN dim_aircraft dac
            ON dac.aircraft_type = :aircraft_type
        JOIN dim_weather_condition dw
            ON dw.weather_condition = :weather_condition
        JOIN dim_delay_cause dc
            ON dc.delay_cause = :delay_cause
        WHERE df.flight_number = :flight_number

        ON CONFLICT (
            flight_id,
            date_id,
            scheduled_departure_time_id,
            origin_airport_id,
            destination_airport_id
        )
        DO UPDATE SET
            actual_departure_time_id = EXCLUDED.actual_departure_time_id,
            weather_condition_id = EXCLUDED.weather_condition_id,
            delay_cause_id = EXCLUDED.delay_cause_id,
            delay_minutes = EXCLUDED.delay_minutes,
            is_delayed = EXCLUDED.is_delayed,
            updated_at = CURRENT_TIMESTAMP;
    """)

    conn.execute(query, record)


def parse_api_record(item):
    flight_number = item.get("flight_number")
    airline_code = item.get("airline_code")
    airline_name = item.get("airline_name")

    origin_airport_code = item.get("origin_airport_code")
    origin_airport_name = item.get("origin_airport_name")

    destination_airport_code = item.get("destination_airport_code")
    destination_airport_name = item.get("destination_airport_name")

    scheduled_raw = item.get("scheduled_departure_datetime")
    actual_raw = item.get("actual_departure_datetime")

    if not flight_number or not airline_code or not origin_airport_code or not destination_airport_code:
        return None

    if not scheduled_raw:
        return None

    scheduled_dt = datetime.fromisoformat(scheduled_raw.replace("Z", "+00:00"))
    flight_date = scheduled_dt.date()

    scheduled_departure_time = clean_api_time(scheduled_raw)
    actual_departure_time = clean_api_time(actual_raw)

    delay_minutes = item.get("departure_delay_minutes_live") or 0
    is_delayed = delay_minutes > 15

    return {
        "flight_number": flight_number,
        "airline_code": airline_code,
        "airline_name": airline_name or "Unknown",
        "origin_airport_code": origin_airport_code,
        "origin_airport_name": origin_airport_name or "Unknown",
        "destination_airport_code": destination_airport_code,
        "destination_airport_name": destination_airport_name or "Unknown",
        "flight_date": flight_date,
        "scheduled_departure_time": scheduled_departure_time,
        "actual_departure_time": actual_departure_time,
        "aircraft_type": "Unknown",
        "weather_condition": "Unknown",
        "delay_cause": "None",
        "delay_minutes": int(delay_minutes),
        "is_delayed": bool(is_delayed),
    }


def main():
    print("Updating FlightInsight database from API...")

    create_tables()

    api_items = get_live_flights(max_rows=2000, page_size=100)

    inserted_count = 0
    skipped_count = 0

    with engine.begin() as conn:
        for item in api_items:
            record = parse_api_record(item)

            if record is None:
                skipped_count += 1

                continue

            ensure_dimension_values(conn, record)
            upsert_api_fact_record(conn, record)

            inserted_count += 1

    print(f"API update complete.")
    print(f"Records inserted/updated: {inserted_count}")
    print(f"Records skipped: {skipped_count}")


if __name__ == "__main__":
    main()