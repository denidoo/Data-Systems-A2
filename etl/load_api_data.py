from datetime import datetime
from sqlalchemy import text

from database.db_config import engine
from api.aviation_stack_api import get_live_flights


def clean_code(value):
    if value is None:
        return None

    return str(value).strip().upper()


def parse_datetime(value):
    if value is None:
        return datetime.now()

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return datetime.now()


def get_id(conn, table_name, id_column, lookup_column, lookup_value):
    result = conn.execute(
        text(f"""
            SELECT {id_column}
            FROM {table_name}
            WHERE {lookup_column} = :lookup_value
            LIMIT 1;
        """),
        {"lookup_value": lookup_value}
    )

    return result.scalar()


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


def get_or_create_airline_id(conn, airline_code, airline_name):
    airline_code = clean_code(airline_code)

    airline_id = get_id(
        conn,
        "dim_airline",
        "airline_id",
        "airline_code",
        airline_code
    )

    if airline_id is not None:
        conn.execute(
            text("""
                UPDATE dim_airline
                SET airline_name = COALESCE(:airline_name, airline_name)
                WHERE airline_id = :airline_id;
            """),
            {
                "airline_id": airline_id,
                "airline_name": airline_name
            }
        )

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


def get_or_create_airport_id(conn, airport_code, airport_name):
    airport_code = clean_code(airport_code)

    airport_id = get_id(
        conn,
        "dim_airport",
        "airport_id",
        "airport_code",
        airport_code
    )

    if airport_id is not None:
        conn.execute(
            text("""
                UPDATE dim_airport
                SET airport_name = COALESCE(:airport_name, airport_name)
                WHERE airport_id = :airport_id;
            """),
            {
                "airport_id": airport_id,
                "airport_name": airport_name
            }
        )

        return airport_id

    result = conn.execute(
        text("""
            INSERT INTO dim_airport (
                airport_code,
                airport_name,
                airport_city,
                airport_country,
                airport_continent,
                airport_elevation,
                airport_type
            )
            VALUES (
                :airport_code,
                :airport_name,
                'Unknown',
                'Unknown',
                'Unknown',
                NULL,
                'Unknown'
            )
            RETURNING airport_id;
        """),
        {
            "airport_code": airport_code,
            "airport_name": airport_name or airport_code
        }
    )

    return result.scalar()


def get_or_create_flight_id(conn, flight_number, flight_type, route_category, route_distance):
    flight_number = clean_code(flight_number)

    result = conn.execute(
        text("""
            SELECT flight_id
            FROM dim_flight
            WHERE flight_number = :flight_number
            LIMIT 1;
        """),
        {"flight_number": flight_number}
    )

    flight_id = result.scalar()

    if flight_id is not None:
        return flight_id

    result = conn.execute(
        text("""
            INSERT INTO dim_flight (
                flight_number,
                flight_type,
                route_category,
                route_distance
            )
            VALUES (
                :flight_number,
                :flight_type,
                :route_category,
                :route_distance
            )
            RETURNING flight_id;
        """),
        {
            "flight_number": flight_number,
            "flight_type": flight_type or "Unknown",
            "route_category": route_category or "Unknown",
            "route_distance": route_distance
        }
    )

    return result.scalar()


def get_default_weather_id(conn):
    weather_id = get_id(
        conn,
        "dim_weather_condition",
        "weather_id",
        "weather_type",
        "Unknown"
    )

    if weather_id is not None:
        return weather_id

    result = conn.execute(
        text("""
            INSERT INTO dim_weather_condition (
                weather_type,
                temperature,
                wind_speed,
                visibility
            )
            VALUES (
                'Unknown',
                NULL,
                NULL,
                NULL
            )
            RETURNING weather_id;
        """)
    )

    return result.scalar()


def get_default_aircraft_id(conn):
    result = conn.execute(
        text("""
            SELECT aircraft_id
            FROM dim_aircraft
            WHERE aircraft_model = 'Unknown'
            LIMIT 1;
        """)
    )

    aircraft_id = result.scalar()

    if aircraft_id is not None:
        return aircraft_id

    result = conn.execute(
        text("""
            INSERT INTO dim_aircraft (
                tail_number,
                aircraft_model,
                manufacturer,
                seating_capacity,
                aircraft_category
            )
            VALUES (
                'UNKNOWN',
                'Unknown',
                'Unknown',
                NULL,
                'Unknown'
            )
            RETURNING aircraft_id;
        """)
    )

    return result.scalar()


def get_default_delay_cause_id(conn):
    delay_cause_id = get_id(
        conn,
        "dim_delay_cause",
        "delay_cause_id",
        "delay_cause_type",
        "API / Live Status"
    )

    if delay_cause_id is not None:
        return delay_cause_id

    result = conn.execute(
        text("""
            INSERT INTO dim_delay_cause (
                delay_cause_type,
                delay_cause_detail,
                is_controllable
            )
            VALUES (
                'API / Live Status',
                'Live flight data inserted from Aviationstack API',
                FALSE
            )
            RETURNING delay_cause_id;
        """)
    )

    return result.scalar()


def insert_api_flight(conn, flight):
    scheduled_departure = parse_datetime(
        flight.get("scheduled_departure_datetime")
    )

    date_id = get_or_create_date_id(conn, scheduled_departure)
    time_id = get_or_create_time_id(conn, scheduled_departure)

    airline_id = get_or_create_airline_id(
        conn,
        flight["airline_code"],
        flight.get("airline_name")
    )

    origin_airport_id = get_or_create_airport_id(
        conn,
        flight["origin_airport_code"],
        flight.get("origin_airport_name")
    )

    destination_airport_id = get_or_create_airport_id(
        conn,
        flight["destination_airport_code"],
        flight.get("destination_airport_name")
    )

    flight_id = get_or_create_flight_id(
        conn,
        flight["flight_number"],
        flight.get("flight_type"),
        flight.get("route_category"),
        flight.get("route_distance")
    )

    weather_id = get_default_weather_id(conn)
    aircraft_id = get_default_aircraft_id(conn)
    delay_cause_id = get_default_delay_cause_id(conn)

    delay_minutes = int(flight.get("departure_delay_minutes_live") or 0)
    delay_status = "Delayed" if delay_minutes > 15 else "On Time"

    actual_departure = parse_datetime(
        flight.get("actual_departure_datetime")
    )

    scheduled_arrival = parse_datetime(
        flight.get("scheduled_arrival_datetime")
    )

    actual_arrival = parse_datetime(
        flight.get("actual_arrival_datetime")
    )

    conn.execute(
        text("""
            INSERT INTO fact_flightperformance (
                date_id,
                time_id,
                origin_airport_id,
                destination_airport_id,
                airline_id,
                weather_id,
                flight_id,
                aircraft_id,
                delay_cause_id,

                delay_minutes,
                cancellation_flag,
                passengers,

                scheduled_departure_datetime,
                actual_departure_datetime,
                scheduled_arrival_datetime,
                actual_arrival_datetime,

                delay_status,

                api_source,
                api_pull_timestamp,
                api_live_flight_status,
                api_departure_delay_minutes,
                api_arrival_delay_minutes
            )
            VALUES (
                :date_id,
                :time_id,
                :origin_airport_id,
                :destination_airport_id,
                :airline_id,
                :weather_id,
                :flight_id,
                :aircraft_id,
                :delay_cause_id,

                :delay_minutes,
                FALSE,
                0,

                :scheduled_departure_datetime,
                :actual_departure_datetime,
                :scheduled_arrival_datetime,
                :actual_arrival_datetime,

                :delay_status,

                'Aviationstack',
                :api_pull_timestamp,
                :api_live_flight_status,
                :api_departure_delay_minutes,
                :api_arrival_delay_minutes
            );
        """),
        {
            "date_id": date_id,
            "time_id": time_id,
            "origin_airport_id": origin_airport_id,
            "destination_airport_id": destination_airport_id,
            "airline_id": airline_id,
            "weather_id": weather_id,
            "flight_id": flight_id,
            "aircraft_id": aircraft_id,
            "delay_cause_id": delay_cause_id,

            "delay_minutes": delay_minutes,
            "scheduled_departure_datetime": scheduled_departure,
            "actual_departure_datetime": actual_departure,
            "scheduled_arrival_datetime": scheduled_arrival,
            "actual_arrival_datetime": actual_arrival,

            "delay_status": delay_status,

            "api_pull_timestamp": datetime.now(),
            "api_live_flight_status": flight.get("live_flight_status"),
            "api_departure_delay_minutes": flight.get("departure_delay_minutes_live", 0),
            "api_arrival_delay_minutes": flight.get("arrival_delay_minutes_live", 0)
        }
    )


def load_live_flights_from_api(max_rows=500, page_size=100):
    flights = get_live_flights(
        max_rows=max_rows,
        page_size=page_size
    )

    inserted_count = 0
    skipped_count = 0

    with engine.begin() as conn:
        for flight in flights:
            try:
                insert_api_flight(conn, flight)
                inserted_count += 1
            except Exception as e:
                skipped_count += 1
                print(f"Skipped flight {flight.get('flight_number')}: {e}")

    print(f"API load complete. Inserted {inserted_count} rows. Skipped {skipped_count} rows.")


if __name__ == "__main__":
    load_live_flights_from_api(
        max_rows=500,
        page_size=100
    )