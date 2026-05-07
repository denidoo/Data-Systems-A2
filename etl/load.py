from sqlalchemy import text

from db_config import engine


def clear_database():
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM fact_flightperformance;"))
        conn.execute(text("DELETE FROM dim_delay_cause;"))
        conn.execute(text("DELETE FROM dim_aircraft;"))
        conn.execute(text("DELETE FROM dim_flight;"))
        conn.execute(text("DELETE FROM dim_weather_condition;"))
        conn.execute(text("DELETE FROM dim_airline;"))
        conn.execute(text("DELETE FROM dim_airport;"))
        conn.execute(text("DELETE FROM dim_time;"))
        conn.execute(text("DELETE FROM dim_date;"))

        conn.execute(text("ALTER SEQUENCE dim_airport_airport_id_seq RESTART WITH 1;"))
        conn.execute(text("ALTER SEQUENCE dim_airline_airline_id_seq RESTART WITH 1;"))
        conn.execute(text("ALTER SEQUENCE dim_weather_condition_weather_id_seq RESTART WITH 1;"))
        conn.execute(text("ALTER SEQUENCE dim_flight_flight_id_seq RESTART WITH 1;"))
        conn.execute(text("ALTER SEQUENCE dim_aircraft_aircraft_id_seq RESTART WITH 1;"))
        conn.execute(text("ALTER SEQUENCE dim_delay_cause_delay_cause_id_seq RESTART WITH 1;"))
        conn.execute(text("ALTER SEQUENCE fact_flightperformance_flight_performance_id_seq RESTART WITH 1;"))

    print("Existing database rows cleared.")


def load(dimensions, fact_table):
    clear_database()

    dimensions["dim_date"].to_sql("dim_date", engine, if_exists="append", index=False)
    dimensions["dim_time"].to_sql("dim_time", engine, if_exists="append", index=False)
    dimensions["dim_airport"].to_sql("dim_airport", engine, if_exists="append", index=False)
    dimensions["dim_airline"].to_sql("dim_airline", engine, if_exists="append", index=False)
    dimensions["dim_weather_condition"].to_sql("dim_weather_condition", engine, if_exists="append", index=False)
    dimensions["dim_flight"].to_sql("dim_flight", engine, if_exists="append", index=False)
    dimensions["dim_aircraft"].to_sql("dim_aircraft", engine, if_exists="append", index=False)
    dimensions["dim_delay_cause"].to_sql("dim_delay_cause", engine, if_exists="append", index=False)

    fact_table.to_sql("fact_flightperformance", engine, if_exists="append", index=False)

    print("Load complete. Data inserted into PostgreSQL.")