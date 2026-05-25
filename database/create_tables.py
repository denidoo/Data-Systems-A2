from sqlalchemy import text
from database.db_config import engine


def create_tables():
    with engine.begin() as conn:

        # =============================
        # Dimension tables
        # =============================

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dim_airline (
                airline_id SERIAL PRIMARY KEY,
                airline_code VARCHAR(10),
                airline_name VARCHAR(255)
            );
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dim_airport (
                airport_id SERIAL PRIMARY KEY,
                airport_code VARCHAR(10),
                airport_name VARCHAR(255),
                city VARCHAR(100),
                state VARCHAR(100),
                country VARCHAR(100)
            );
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dim_date (
                date_id SERIAL PRIMARY KEY,
                full_date DATE,
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
                time_value TIME,
                hour INTEGER,
                minute INTEGER,
                time_of_day VARCHAR(50)
            );
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dim_aircraft (
                aircraft_id SERIAL PRIMARY KEY,
                aircraft_type VARCHAR(100)
            );
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dim_weather_condition (
                weather_condition_id SERIAL PRIMARY KEY,
                weather_condition VARCHAR(100)
            );
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dim_delay_cause (
                delay_cause_id SERIAL PRIMARY KEY,
                delay_cause VARCHAR(100)
            );
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dim_flight (
                flight_id SERIAL PRIMARY KEY,
                flight_number VARCHAR(20)
            );
        """))

        # =============================
        # Fact table
        # =============================

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
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # =============================
        # Upgrade old existing tables
        # =============================

        conn.execute(text("ALTER TABLE dim_airport ADD COLUMN IF NOT EXISTS city VARCHAR(100);"))
        conn.execute(text("ALTER TABLE dim_airport ADD COLUMN IF NOT EXISTS state VARCHAR(100);"))
        conn.execute(text("ALTER TABLE dim_airport ADD COLUMN IF NOT EXISTS country VARCHAR(100);"))

        conn.execute(text("ALTER TABLE dim_date ADD COLUMN IF NOT EXISTS quarter INTEGER;"))
        conn.execute(text("ALTER TABLE dim_date ADD COLUMN IF NOT EXISTS day_of_week INTEGER;"))
        conn.execute(text("ALTER TABLE dim_date ADD COLUMN IF NOT EXISTS is_weekend BOOLEAN;"))

        # =============================
        # Unique constraints for upserts
        # =============================

        add_unique_constraint(
            conn,
            "dim_airline_airline_code_unique",
            "dim_airline",
            "airline_code"
        )

        add_unique_constraint(
            conn,
            "dim_airport_airport_code_unique",
            "dim_airport",
            "airport_code"
        )

        add_unique_constraint(
            conn,
            "dim_date_full_date_unique",
            "dim_date",
            "full_date"
        )

        add_unique_constraint(
            conn,
            "dim_time_time_value_unique",
            "dim_time",
            "time_value"
        )

        add_unique_constraint(
            conn,
            "dim_aircraft_aircraft_type_unique",
            "dim_aircraft",
            "aircraft_type"
        )

        add_unique_constraint(
            conn,
            "dim_weather_condition_weather_condition_unique",
            "dim_weather_condition",
            "weather_condition"
        )

        add_unique_constraint(
            conn,
            "dim_delay_cause_delay_cause_unique",
            "dim_delay_cause",
            "delay_cause"
        )

        add_unique_constraint(
            conn,
            "dim_flight_flight_number_unique",
            "dim_flight",
            "flight_number"
        )

        add_fact_unique_constraint(conn)

    print("Tables checked/created/upgraded successfully.")


def add_unique_constraint(conn, constraint_name, table_name, column_name):
    conn.execute(text(f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = '{constraint_name}'
            ) THEN
                ALTER TABLE {table_name}
                ADD CONSTRAINT {constraint_name}
                UNIQUE ({column_name});
            END IF;
        END $$;
    """))


def add_fact_unique_constraint(conn):
    conn.execute(text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'fact_flightperformance_unique_record'
            ) THEN
                ALTER TABLE fact_flightperformance
                ADD CONSTRAINT fact_flightperformance_unique_record
                UNIQUE (
                    flight_id,
                    date_id,
                    scheduled_departure_time_id,
                    origin_airport_id,
                    destination_airport_id
                );
            END IF;
        END $$;
    """))


if __name__ == "__main__":
    create_tables()