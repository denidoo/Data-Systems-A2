from database.create_tables import create_tables
from etl.extract import extract_data
from etl.transform import transform_data
from etl.load import load_data


def main():
    print("Running historical ETL pipeline...")

    create_tables()

    raw_data = extract_data()
    processed_data = transform_data(raw_data)
    load_data(processed_data)

    print("Historical ETL pipeline complete.")


if __name__ == "__main__":
    main()