from etl.extract import extract
from etl.transform import transform, build_dimensions, build_fact_table
from etl.load import load


def main():
    raw_df = extract()
    transformed_df = transform(raw_df)
    dimensions = build_dimensions(transformed_df)
    fact_table = build_fact_table(transformed_df, dimensions)
    load(dimensions, fact_table)

    print("ETL process completed successfully.")


if __name__ == "__main__":
    main()