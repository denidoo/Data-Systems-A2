from sqlalchemy import text
from database.db_config import engine


def create_tables():
    with engine.begin() as conn:

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dim_airline (
                airline_id SERIAL PRIMARY KEY,
                airline_code VARCHAR(10) UNIQUE NOT NULL,
                airline_name VARCHAR(255) NOT NULL
            );
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dim_airport (
                airport_id SERIAL PRIMARY KEY,
                airport_code VARCHAR(10) UNIQUE NOT NULL,
                airport_name VARCHAR(255),
                city VARCHAR(100),
                state VARCHAR(100),
                country VARCHAR(100)
            );
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dim_date (
                date_id SERIAL PRIMARY KEY,
                full_date DATE UNIQUE NOT NULL,
                year INTEGER,
                month INTEGER,
                day INTEGER,
                quarter INTEGER,
                day_of_week INTEGER,
                is_weekend BOOLEAN
            );
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dim_time (
                time_id SERIAL PRIMARY KEY,
                time_value TIME UNIQUE NOT NULL,
                hour INTEGER,
                minute INTEGER,
                time_of_day VARCHAR(50)
            );
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dim_aircraft (
                aircraft_id SERIAL PRIMARY KEY,
                aircraft_type VARCHAR(100) UNIQUE NOT NULL
            );
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dim_weather_condition (
                weather_condition_id SERIAL PRIMARY KEY,
                weather_condition VARCHAR(100) UNIQUE NOT NULL
            );
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dim_delay_cause (
                delay_cause_id SERIAL PRIMARY KEY,
                delay_cause VARCHAR(100) UNIQUE NOT NULL
            );
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dim_flight (
                flight_id SERIAL PRIMARY KEY,
                flight_number VARCHAR(20) UNIQUE NOT NULL
            );
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS fact_flightperformance (
                flight_performance_id SERIAL PRIMARY KEY,

                flight_id INTEGER REFERENCES dim_flight(flight_id),
                airline_id INTEGER REFERENCES dim_airline(airline_id),
                origin_airport_id INTEGER REFERENCES dim_airport(airport_id),
                destination_airport_id INTEGER REFERENCES dim_airport(airport_id),
                date_id INTEGER REFERENCES dim_date(date_id),
                scheduled_departure_time_id INTEGER REFERENCES dim_time(time_id),
                actual_departure_time_id INTEGER REFERENCES dim_time(time_id),
                aircraft_id INTEGER REFERENCES dim_aircraft(aircraft_id),
                weather_condition_id INTEGER REFERENCES dim_weather_condition(weather_condition_id),
                delay_cause_id INTEGER REFERENCES dim_delay_cause(delay_cause_id),

                delay_minutes INTEGER DEFAULT 0,
                is_delayed BOOLEAN DEFAULT FALSE,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                UNIQUE (
                    flight_id,
                    date_id,
                    scheduled_departure_time_id,
                    origin_airport_id,
                    destination_airport_id
                )
            );
        """))

    print("Tables checked/created successfully.")


if __name__ == "__main__":
    create_tables()