from sqlalchemy import text
from database.db_config import engine


CREATE_TABLES_SQL = """
DROP TABLE IF EXISTS fact_flightperformance CASCADE;

DROP TABLE IF EXISTS dim_date CASCADE;
DROP TABLE IF EXISTS dim_time CASCADE;
DROP TABLE IF EXISTS dim_airport CASCADE;
DROP TABLE IF EXISTS dim_airline CASCADE;
DROP TABLE IF EXISTS dim_weather_condition CASCADE;
DROP TABLE IF EXISTS dim_flight CASCADE;
DROP TABLE IF EXISTS dim_aircraft CASCADE;
DROP TABLE IF EXISTS dim_delay_cause CASCADE;

CREATE TABLE dim_date (
    date_id INTEGER PRIMARY KEY,
    full_date DATE NOT NULL,
    day INTEGER,
    month INTEGER,
    year INTEGER
);

CREATE TABLE dim_time (
    time_id INTEGER PRIMARY KEY,
    hour INTEGER,
    minute INTEGER,
    time_of_day VARCHAR(20)
);

CREATE TABLE dim_airport (
    airport_id SERIAL PRIMARY KEY,
    airport_code VARCHAR(10) UNIQUE,
    airport_name VARCHAR(100),
    airport_city VARCHAR(100),
    airport_country VARCHAR(100),
    airport_continent VARCHAR(50),
    airport_elevation INTEGER,
    airport_type VARCHAR(50)
);

CREATE TABLE dim_airline (
    airline_id SERIAL PRIMARY KEY,
    airline_code VARCHAR(10) UNIQUE,
    airline_name VARCHAR(100)
);

CREATE TABLE dim_weather_condition (
    weather_id SERIAL PRIMARY KEY,
    weather_type VARCHAR(50),
    temperature NUMERIC,
    wind_speed NUMERIC,
    visibility NUMERIC
);

CREATE TABLE dim_flight (
    flight_id SERIAL PRIMARY KEY,
    flight_number VARCHAR(20),
    flight_type VARCHAR(50),
    route_category VARCHAR(50),
    route_distance NUMERIC
);

CREATE TABLE dim_aircraft (
    aircraft_id SERIAL PRIMARY KEY,
    tail_number VARCHAR(30),
    aircraft_model VARCHAR(50),
    manufacturer VARCHAR(50),
    seating_capacity INTEGER,
    aircraft_category VARCHAR(50)
);

CREATE TABLE dim_delay_cause (
    delay_cause_id SERIAL PRIMARY KEY,
    delay_cause_type VARCHAR(50),
    delay_cause_detail VARCHAR(150),
    is_controllable BOOLEAN
);

CREATE TABLE fact_flightperformance (
    flight_performance_id SERIAL PRIMARY KEY,

    date_id INTEGER REFERENCES dim_date(date_id),
    time_id INTEGER REFERENCES dim_time(time_id),
    origin_airport_id INTEGER REFERENCES dim_airport(airport_id),
    destination_airport_id INTEGER REFERENCES dim_airport(airport_id),
    airline_id INTEGER REFERENCES dim_airline(airline_id),
    weather_id INTEGER REFERENCES dim_weather_condition(weather_id),
    flight_id INTEGER REFERENCES dim_flight(flight_id),
    aircraft_id INTEGER REFERENCES dim_aircraft(aircraft_id),
    delay_cause_id INTEGER REFERENCES dim_delay_cause(delay_cause_id),

    delay_minutes INTEGER,
    cancellation_flag BOOLEAN,
    passengers INTEGER,

    scheduled_departure_datetime TIMESTAMP,
    actual_departure_datetime TIMESTAMP,
    scheduled_arrival_datetime TIMESTAMP,
    actual_arrival_datetime TIMESTAMP,

    delay_status VARCHAR(20),

    api_source VARCHAR(50),
    api_live_flight_status VARCHAR(50),

    api_departure_delay_minutes FLOAT,
    api_arrival_delay_minutes FLOAT,

    api_origin_live_departures_count INTEGER,
    api_origin_live_arrivals_count INTEGER,
    api_origin_delayed_departures_count INTEGER,
    api_origin_delayed_arrivals_count INTEGER,
    api_origin_avg_departure_delay FLOAT,
    api_origin_avg_arrival_delay FLOAT,

    api_destination_live_departures_count INTEGER,
    api_destination_live_arrivals_count INTEGER,
    api_destination_delayed_departures_count INTEGER,
    api_destination_delayed_arrivals_count INTEGER,
    api_destination_avg_departure_delay FLOAT,
    api_destination_avg_arrival_delay FLOAT
);
"""


def create_tables():
    with engine.begin() as conn:
        conn.execute(text(CREATE_TABLES_SQL))

    print("Tables created successfully.")


def main():
    create_tables()


if __name__ == "__main__":
    main()