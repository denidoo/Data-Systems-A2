from database.create_tables import create_tables
from database.fix_sequences import fix_sequences

from etl.extract import extract
from etl.transform import (
    transform,
    build_dimensions,
    build_fact_table
)
from etl.load import load
from etl.load_api_data import insert_live_flight_status


def main(load_api=True):
    print("Creating database tables...")
    create_tables()

    print("Starting main ETL process...")

    raw_df = extract()
    transformed_df = transform(raw_df)

    dimensions = build_dimensions(transformed_df)

    fact_table = build_fact_table(
        transformed_df,
        dimensions
    )

    load(dimensions, fact_table)

    fix_sequences()

    print("Main warehouse ETL completed.")

    if load_api:
        print("Loading live API data...")

        insert_live_flight_status(
            flight_number="QF1",
            airline_code="QF",
            origin_airport_code="SYD",
            destination_airport_code="SIN"
        )

        print("Live API ETL completed.")


if __name__ == "__main__":
    main(load_api=True)