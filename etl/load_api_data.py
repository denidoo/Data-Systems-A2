from datetime import datetime
from sqlalchemy import text

from database.db_config import engine

from api.aviation_stack_api import (
    get_live_flight_status,
    get_airport_live_flight_summary
)


def clean_code(value):
    if value is None:
        return None

    return str(value).strip().upper()


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


def get_or_create_airline_id(conn, airline_code, airline_name=None):
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


def get_or_create_airport_id(
    conn,
    airport_code,
    airport_name=None,
    airport_city="Unknown",
    airport_country="Unknown",
    airport_continent="Unknown",
    airport_elevation=None,
    airport_type="Unknown"
):
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
                SET
                    airport_name = COALESCE(:airport_name, airport_name),
                    airport_city = COALESCE(:airport_city, airport_city),
                    airport_country = COALESCE(:airport_country, airport_country),
                    airport_continent = COALESCE(:airport_continent, airport_continent),
                    airport_elevation = COALESCE(:airport_elevation, airport_elevation),
                    airport_type = COALESCE(:airport_type, airport_type)
                WHERE airport_id = :airport_id;
            """),
            {
                "airport_id": airport_id,
                "airport_name": airport_name,
                "airport_city": airport_city,
                "airport_country": airport_country,
                "airport_continent": airport_continent,
                "airport_elevation": airport_elevation,
                "airport_type": airport_type
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
                :airport_city,
                :airport_country,
                :airport_continent,
                :airport_elevation,
                :airport_type
            )
            RETURNING airport_id;
        """),
        {
            "airport_code": airport_code,
            "airport_name": airport_name or airport_code,
            "airport_city": airport_city,
            "airport_country": airport_country,
            "airport_continent": airport_continent,
            "airport_elevation": airport_elevation,
            "airport_type": airport_type
        }
    )

    return result.scalar()


def get_or_create_flight_id(
    conn,
    flight_number,
    flight_type="Unknown",
    route_category="Unknown",
    route_distance=None
):
    flight_number = clean_code(flight_number)

    flight_id = get_id(
        conn,
        "dim_flight",
        "flight_id",
        "flight_number",
        flight_number
    )

    if flight_id is not None:
        conn.execute(
            text("""
                UPDATE dim_flight
                SET
                    flight_type = COALESCE(:flight_type, flight_type),
                    route_category = COALESCE(:route_category, route_category),
                    route_distance = COALESCE(:route_distance, route_distance)
                WHERE flight_id = :flight_id;
            """),
            {
                "flight_id": flight_id,
                "flight_type": flight_type,
                "route_category": route_category,
                "route_distance": route_distance
            }
        )

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
            "flight_type": flight_type,
            "route_category": route_category,
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
                'Live flight status inserted from Aviationstack API',
                FALSE
            )
            RETURNING delay_cause_id;
        """)
    )

    return result.scalar()


def extract_api_dimension_values(
    flight_status,
    flight_number,
    airline_code,
    origin_airport_code,
    destination_airport_code
):
    airline_name = (
        flight_status.get("airline_name")
        or flight_status.get("airline")
        or airline_code
    )

    origin_airport_name = (
        flight_status.get("origin_airport_name")
        or flight_status.get("departure_airport")
        or origin_airport_code
    )

    destination_airport_name = (
        flight_status.get("destination_airport_name")
        or flight_status.get("arrival_airport")
        or destination_airport_code
    )

    flight_type = flight_status.get("flight_type") or "Unknown"
    route_category = flight_status.get("route_category") or "Unknown"
    route_distance = flight_status.get("route_distance")

    return {
        "airline_name": airline_name,
        "origin_airport_name": origin_airport_name,
        "destination_airport_name": destination_airport_name,
        "flight_type": flight_type,
        "route_category": route_category,
        "route_distance": route_distance
    }


def insert_live_flight_status(
    flight_number,
    airline_code,
    origin_airport_code,
    destination_airport_code,
    selected_datetime=None
):
    flight_number = clean_code(flight_number)
    airline_code = clean_code(airline_code)
    origin_airport_code = clean_code(origin_airport_code)
    destination_airport_code = clean_code(destination_airport_code)

    if selected_datetime is None:
        selected_datetime = datetime.now()

    flight_status = get_live_flight_status(flight_number)
    origin_summary = get_airport_live_flight_summary(origin_airport_code)
    destination_summary = get_airport_live_flight_summary(destination_airport_code)

    dim_values = extract_api_dimension_values(
        flight_status,
        flight_number,
        airline_code,
        origin_airport_code,
        destination_airport_code
    )

    api_departure_delay = flight_status.get("departure_delay_minutes_live", 0)
    api_arrival_delay = flight_status.get("arrival_delay_minutes_live", 0)

    delay_minutes = api_departure_delay or 0
    delay_status = "Delayed" if delay_minutes > 15 else "On Time"

    with engine.begin() as conn:
        airline_id = get_or_create_airline_id(
            conn,
            airline_code=airline_code,
            airline_name=dim_values["airline_name"]
        )

        origin_airport_id = get_or_create_airport_id(
            conn,
            airport_code=origin_airport_code,
            airport_name=dim_values["origin_airport_name"]
        )

        destination_airport_id = get_or_create_airport_id(
            conn,
            airport_code=destination_airport_code,
            airport_name=dim_values["destination_airport_name"]
        )

        flight_id = get_or_create_flight_id(
            conn,
            flight_number=flight_number,
            flight_type=dim_values["flight_type"],
            route_category=dim_values["route_category"],
            route_distance=dim_values["route_distance"]
        )

        date_id = get_or_create_date_id(conn, selected_datetime)
        time_id = get_or_create_time_id(conn, selected_datetime)

        weather_id = get_default_weather_id(conn)
        aircraft_id = get_default_aircraft_id(conn)
        delay_cause_id = get_default_delay_cause_id(conn)

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
                    api_live_flight_status,
                    api_departure_delay_minutes,
                    api_arrival_delay_minutes,

                    api_origin_live_departures_count,
                    api_origin_live_arrivals_count,
                    api_origin_delayed_departures_count,
                    api_origin_delayed_arrivals_count,
                    api_origin_avg_departure_delay,
                    api_origin_avg_arrival_delay,

                    api_destination_live_departures_count,
                    api_destination_live_arrivals_count,
                    api_destination_delayed_departures_count,
                    api_destination_delayed_arrivals_count,
                    api_destination_avg_departure_delay,
                    api_destination_avg_arrival_delay
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

                    :api_source,
                    :api_live_flight_status,
                    :api_departure_delay_minutes,
                    :api_arrival_delay_minutes,

                    :api_origin_live_departures_count,
                    :api_origin_live_arrivals_count,
                    :api_origin_delayed_departures_count,
                    :api_origin_delayed_arrivals_count,
                    :api_origin_avg_departure_delay,
                    :api_origin_avg_arrival_delay,

                    :api_destination_live_departures_count,
                    :api_destination_live_arrivals_count,
                    :api_destination_delayed_departures_count,
                    :api_destination_delayed_arrivals_count,
                    :api_destination_avg_departure_delay,
                    :api_destination_avg_arrival_delay
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
                "scheduled_departure_datetime": selected_datetime,
                "actual_departure_datetime": selected_datetime,
                "scheduled_arrival_datetime": selected_datetime,
                "actual_arrival_datetime": selected_datetime,
                "delay_status": delay_status,

                "api_source": "Aviationstack",
                "api_live_flight_status": flight_status.get("live_flight_status"),
                "api_departure_delay_minutes": api_departure_delay,
                "api_arrival_delay_minutes": api_arrival_delay,

                "api_origin_live_departures_count": origin_summary.get("airport_live_departures_count", 0),
                "api_origin_live_arrivals_count": origin_summary.get("airport_live_arrivals_count", 0),
                "api_origin_delayed_departures_count": origin_summary.get("airport_delayed_departures_count", 0),
                "api_origin_delayed_arrivals_count": origin_summary.get("airport_delayed_arrivals_count", 0),
                "api_origin_avg_departure_delay": origin_summary.get("airport_avg_departure_delay", 0),
                "api_origin_avg_arrival_delay": origin_summary.get("airport_avg_arrival_delay", 0),

                "api_destination_live_departures_count": destination_summary.get("airport_live_departures_count", 0),
                "api_destination_live_arrivals_count": destination_summary.get("airport_live_arrivals_count", 0),
                "api_destination_delayed_departures_count": destination_summary.get("airport_delayed_departures_count", 0),
                "api_destination_delayed_arrivals_count": destination_summary.get("airport_delayed_arrivals_count", 0),
                "api_destination_avg_departure_delay": destination_summary.get("airport_avg_departure_delay", 0),
                "api_destination_avg_arrival_delay": destination_summary.get("airport_avg_arrival_delay", 0)
            }
        )

    print("API data inserted into fact_flightperformance and dimension tables updated.")


if __name__ == "__main__":
    insert_live_flight_status(
        flight_number="QF1",
        airline_code="QF",
        origin_airport_code="SYD",
        destination_airport_code="SIN"
    )