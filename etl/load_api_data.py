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


def create_api_tables():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dim_api_snapshot (
                api_snapshot_id SERIAL PRIMARY KEY,
                api_provider VARCHAR(50),
                snapshot_timestamp TIMESTAMP,
                request_type VARCHAR(50)
            );
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS fact_live_flight_status (
                live_status_id SERIAL PRIMARY KEY,

                api_snapshot_id INT REFERENCES dim_api_snapshot(api_snapshot_id),

                flight_number VARCHAR(20),
                origin_airport_code VARCHAR(10),
                destination_airport_code VARCHAR(10),

                live_flight_status VARCHAR(50),

                departure_delay_minutes_live FLOAT,
                arrival_delay_minutes_live FLOAT,

                origin_live_departures_count INT,
                origin_live_arrivals_count INT,
                origin_delayed_departures_count INT,
                origin_delayed_arrivals_count INT,
                origin_avg_departure_delay FLOAT,
                origin_avg_arrival_delay FLOAT,

                destination_live_departures_count INT,
                destination_live_arrivals_count INT,
                destination_delayed_departures_count INT,
                destination_delayed_arrivals_count INT,
                destination_avg_departure_delay FLOAT,
                destination_avg_arrival_delay FLOAT
            );
        """))


def insert_api_snapshot(request_type="flight_prediction"):
    with engine.begin() as conn:
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


def insert_live_flight_status(
    flight_number,
    origin_airport_code,
    destination_airport_code
):
    api_snapshot_id = insert_api_snapshot()

    flight_status = get_live_flight_status(flight_number)

    origin_summary = get_airport_live_flight_summary(origin_airport_code)
    destination_summary = get_airport_live_flight_summary(destination_airport_code)

    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO fact_live_flight_status (
                    api_snapshot_id,

                    flight_number,
                    origin_airport_code,
                    destination_airport_code,

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

                    :flight_number,
                    :origin_airport_code,
                    :destination_airport_code,

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

                "flight_number": flight_number,
                "origin_airport_code": origin_airport_code,
                "destination_airport_code": destination_airport_code,

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


if __name__ == "__main__":
    create_api_tables()

    insert_live_flight_status(
        flight_number="QF1",
        origin_airport_code="SYD",
        destination_airport_code="SIN"
    )

    print("API data loaded into PostgreSQL.")