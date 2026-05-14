import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

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
        """))

    print("Database sequences fixed.")


if __name__ == "__main__":
    fix_sequences()