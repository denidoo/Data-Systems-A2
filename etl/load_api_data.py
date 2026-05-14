import os
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from api.aviation_stack_api import (
    get_live_flight_status,
    get_airport_live_flight_summary
)

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)


def get_or_create_api_snapshot(conn, request_type="flight_prediction"):
    result = conn.execute(
        text("""
            INSERT INTO dim_api_snapshot (
                api_provider,
                snapshot_timestamp,
                request_type
            )
            VALUES (
                'Aviationstack',
                :snapshot_timestamp,
                :request_type
            )
            RETURNING api_snapshot_id;
        """),
        {
            "snapshot_timestamp": datetime.now(),
            "request_type": request_type
        }
    )

    return result.scalar()


def get_id(conn, table, id_col, lookup_col, lookup_value):
    result = conn.execute(
        text(f"""
            SELECT {id_col}
            FROM {table}
            WHERE {lookup_col} = :lookup_value
            LIMIT 1;
        """),
        {"lookup_value": lookup_value}
    ).scalar()

    return result


def get_or_create_date_id(conn, selected_datetime):
    date_id = int(selected_datetime.strftime("%Y%m%d"))

    conn.execute(
        text("""
            INSERT INTO dim_date (
                date_id,
                full_date,
                day,
                month,
                year
            )
            VALUES (
                :date_id,
                :full_date,
                :day,
                :month,
                :year
            )
            ON CONFLICT (date_id) DO NOTHING;
        """),
        {
            "date_id": date_id,
            "full_date": selected_datetime.date(),
            "day": selected_datetime.day,
            "month": selected_datetime.month,
            "year": selected_datetime.year
        }
    )

    return date_id


def get_or_create_time_id(conn, selected_datetime):
    hour = selected_datetime.hour
    minute = selected_datetime.minute
    time_id = hour * 100 + minute

    if 5 <= hour < 12:
        time_of_day = "Morning"
    elif 12 <= hour < 17:
        time_of_day = "Afternoon"
    elif 17 <= hour < 21:
        time_of_day = "Evening"
    else:
        time_of_day = "Night"

    conn.execute(
        text("""
            INSERT INTO dim_time (
                time_id,
                hour,
                minute,
                time_of_day
            )
            VALUES (
                :time_id,
                :hour,
                :minute,
                :time_of_day
            )
            ON CONFLICT (time_id) DO NOTHING;
        """),
        {
            "time_id": time_id,
            "hour": hour,
            "minute": minute,
            "time_of_day": time_of_day
        }
    )

    return time_id

def get_or_create_airline_id(conn, airline_code, airline_name=None):
    airline_id = get_id(
        conn,
        "dim_airline",
        "airline_id",
        "airline_code",
        airline_code
    )

    if airline_id is not None:
        return airline_id

    result = conn.execute(
        text("""
            INSERT INTO dim_airline (
                airline_code,
                airline_name
            )
            VALUES (
                :airline_code,
                :airline_name
            )
            RETURNING airline_id;
        """),
        {
            "airline_code": airline_code,
            "airline_name": airline_name or airline_code
        }
    )

    return result.scalar()


def get_or_create_airport_id(conn, airport_code, airport_name=None):
    airport_id = get_id(
        conn,
        "dim_airport",
        "airport_id",
        "airport_code",
        airport_code
    )

    if airport_id is not None:
        return airport_id

    result = conn.execute(
        text("""
            INSERT INTO dim_airport (
                airport_code,
                airport_name
            )
            VALUES (
                :airport_code,
                :airport_name
            )
            RETURNING airport_id;
        """),
        {
            "airport_code": airport_code,
            "airport_name": airport_name or airport_code
        }
    )

    return result.scalar()


def get_or_create_flight_id(conn, flight_number):
    flight_id = get_id(
        conn,
        "dim_flight",
        "flight_id",
        "flight_number",
        flight_number
    )

    if flight_id is not None:
        return flight_id

    result = conn.execute(
        text("""
            INSERT INTO dim_flight (
                flight_number
            )
            VALUES (
                :flight_number
            )
            RETURNING flight_id;
        """),
        {
            "flight_number": flight_number
        }
    )

    return result.scalar()

def insert_live_flight_status(
    flight_number,
    airline_code,
    origin_airport_code,
    destination_airport_code,
    selected_datetime=None
):
    if selected_datetime is None:
        selected_datetime = datetime.now()

    flight_status = get_live_flight_status(flight_number)
    origin_summary = get_airport_live_flight_summary(origin_airport_code)
    destination_summary = get_airport_live_flight_summary(destination_airport_code)

    with engine.begin() as conn:
        api_snapshot_id = get_or_create_api_snapshot(conn)

        airline_id = get_or_create_airline_id(
            conn,
            airline_code=airline_code
        )

        origin_airport_id = get_or_create_airport_id(
            conn,
            airport_code=origin_airport_code
        )

        destination_airport_id = get_or_create_airport_id(
            conn,
            airport_code=destination_airport_code
        )

        flight_id = get_or_create_flight_id(
            conn,
            flight_number=flight_number
        )

        date_id = get_or_create_date_id(conn, selected_datetime)
        time_id = get_or_create_time_id(conn, selected_datetime)

        missing = {
            "flight_id": flight_id,
            "airline_id": airline_id,
            "origin_airport_id": origin_airport_id,
            "destination_airport_id": destination_airport_id,
        }

        missing_values = [key for key, value in missing.items() if value is None]

        if missing_values:
            raise ValueError(
                f"Could not insert API data because these dimension IDs were missing: {missing_values}"
            )

        conn.execute(
            text("""
                INSERT INTO fact_liveflightstatus (
                    api_snapshot_id,
                    flight_id,
                    origin_airport_id,
                    destination_airport_id,
                    airline_id,
                    date_id,
                    time_id,
                    live_flight_status,
                    departure_delay_minutes_live,
                    arrival_delay_minutes_live,
                    origin_live_departures_count,
                    origin_live_arrivals_count,
                    origin_delayed_departures_count,
                    origin_delayed_arrivals_count,
                    origin_avg_departure_delay,
                    origin_avg_arrival_delay,
                    destination_live_departures_count,
                    destination_live_arrivals_count,
                    destination_delayed_departures_count,
                    destination_delayed_arrivals_count,
                    destination_avg_departure_delay,
                    destination_avg_arrival_delay
                )
                VALUES (
                    :api_snapshot_id,
                    :flight_id,
                    :origin_airport_id,
                    :destination_airport_id,
                    :airline_id,
                    :date_id,
                    :time_id,
                    :live_flight_status,
                    :departure_delay_minutes_live,
                    :arrival_delay_minutes_live,
                    :origin_live_departures_count,
                    :origin_live_arrivals_count,
                    :origin_delayed_departures_count,
                    :origin_delayed_arrivals_count,
                    :origin_avg_departure_delay,
                    :origin_avg_arrival_delay,
                    :destination_live_departures_count,
                    :destination_live_arrivals_count,
                    :destination_delayed_departures_count,
                    :destination_delayed_arrivals_count,
                    :destination_avg_departure_delay,
                    :destination_avg_arrival_delay
                );
            """),
            {
                "api_snapshot_id": api_snapshot_id,
                "flight_id": flight_id,
                "origin_airport_id": origin_airport_id,
                "destination_airport_id": destination_airport_id,
                "airline_id": airline_id,
                "date_id": date_id,
                "time_id": time_id,
                "live_flight_status": flight_status["live_flight_status"],
                "departure_delay_minutes_live": flight_status["departure_delay_minutes_live"],
                "arrival_delay_minutes_live": flight_status["arrival_delay_minutes_live"],
                "origin_live_departures_count": origin_summary["airport_live_departures_count"],
                "origin_live_arrivals_count": origin_summary["airport_live_arrivals_count"],
                "origin_delayed_departures_count": origin_summary["airport_delayed_departures_count"],
                "origin_delayed_arrivals_count": origin_summary["airport_delayed_arrivals_count"],
                "origin_avg_departure_delay": origin_summary["airport_avg_departure_delay"],
                "origin_avg_arrival_delay": origin_summary["airport_avg_arrival_delay"],
                "destination_live_departures_count": destination_summary["airport_live_departures_count"],
                "destination_live_arrivals_count": destination_summary["airport_live_arrivals_count"],
                "destination_delayed_departures_count": destination_summary["airport_delayed_departures_count"],
                "destination_delayed_arrivals_count": destination_summary["airport_delayed_arrivals_count"],
                "destination_avg_departure_delay": destination_summary["airport_avg_departure_delay"],
                "destination_avg_arrival_delay": destination_summary["airport_avg_arrival_delay"],
            }
        )

    print("API data inserted into Fact_LiveFlightStatus using dimension foreign keys.")


if __name__ == "__main__":
    insert_live_flight_status(
        flight_number="QF1",
        airline_code="QF",
        origin_airport_code="SYD",
        destination_airport_code="SIN"
    )