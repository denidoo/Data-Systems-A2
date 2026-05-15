from sqlalchemy import text
from database.db_config import engine


def fix_sequences():
    with engine.begin() as conn:
        conn.execute(text("""
            SELECT setval(
                'dim_airline_airline_id_seq',
                COALESCE((SELECT MAX(airline_id) FROM dim_airline), 1),
                true
            );

            SELECT setval(
                'dim_airport_airport_id_seq',
                COALESCE((SELECT MAX(airport_id) FROM dim_airport), 1),
                true
            );

            SELECT setval(
                'dim_flight_flight_id_seq',
                COALESCE((SELECT MAX(flight_id) FROM dim_flight), 1),
                true
            );

            SELECT setval(
                'dim_weather_condition_weather_id_seq',
                COALESCE((SELECT MAX(weather_id) FROM dim_weather_condition), 1),
                true
            );

            SELECT setval(
                'dim_aircraft_aircraft_id_seq',
                COALESCE((SELECT MAX(aircraft_id) FROM dim_aircraft), 1),
                true
            );

            SELECT setval(
                'dim_delay_cause_delay_cause_id_seq',
                COALESCE((SELECT MAX(delay_cause_id) FROM dim_delay_cause), 1),
                true
            );

            SELECT setval(
                'fact_flightperformance_flight_performance_id_seq',
                COALESCE((SELECT MAX(flight_performance_id) FROM fact_flightperformance), 1),
                true
            );
        """))

    print("Database sequences fixed.")


if __name__ == "__main__":
    fix_sequences()