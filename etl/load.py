from sqlalchemy import text
from database.db_config import engine


def insert_dataframe_ignore_duplicates(conn, df, table_name, columns, conflict_column):
    for _, row in df.iterrows():
        values = {col: row[col] for col in columns}

        query = text(f"""
            INSERT INTO {table_name} ({", ".join(columns)})
            VALUES ({", ".join([f":{col}" for col in columns])})
            ON CONFLICT ({conflict_column})
            DO NOTHING;
        """)

        conn.execute(query, values)


def load_dimensions(data):
    with engine.begin() as conn:

        insert_dataframe_ignore_duplicates(
            conn,
            data["dim_airline"],
            "dim_airline",
            ["airline_code", "airline_name"],
            "airline_code"
        )

        insert_dataframe_ignore_duplicates(
            conn,
            data["dim_airport"],
            "dim_airport",
            ["airport_code", "airport_name", "city", "state", "country"],
            "airport_code"
        )

        insert_dataframe_ignore_duplicates(
            conn,
            data["dim_date"],
            "dim_date",
            ["full_date", "year", "month", "day", "quarter", "day_of_week", "is_weekend"],
            "full_date"
        )

        insert_dataframe_ignore_duplicates(
            conn,
            data["dim_time"],
            "dim_time",
            ["time_value", "hour", "minute", "time_of_day"],
            "time_value"
        )

        insert_dataframe_ignore_duplicates(
            conn,
            data["dim_flight"],
            "dim_flight",
            ["flight_number"],
            "flight_number"
        )

        insert_dataframe_ignore_duplicates(
            conn,
            data["dim_aircraft"],
            "dim_aircraft",
            ["aircraft_type"],
            "aircraft_type"
        )

        insert_dataframe_ignore_duplicates(
            conn,
            data["dim_weather_condition"],
            "dim_weather_condition",
            ["weather_condition"],
            "weather_condition"
        )

        insert_dataframe_ignore_duplicates(
            conn,
            data["dim_delay_cause"],
            "dim_delay_cause",
            ["delay_cause"],
            "delay_cause"
        )


def load_fact_table(data):
    fact_df = data["fact_flightperformance"]

    query = text("""
        INSERT INTO fact_flightperformance (
            flight_id,
            airline_id,
            origin_airport_id,
            destination_airport_id,
            date_id,
            scheduled_departure_time_id,
            actual_departure_time_id,
            aircraft_id,
            weather_condition_id,
            delay_cause_id,
            delay_minutes,
            is_delayed,
            updated_at
        )
        SELECT
            df.flight_id,
            da.airline_id,
            origin.airport_id,
            destination.airport_id,
            dd.date_id,
            scheduled.time_id,
            actual.time_id,
            dac.aircraft_id,
            dw.weather_condition_id,
            dc.delay_cause_id,
            :delay_minutes,
            :is_delayed,
            CURRENT_TIMESTAMP
        FROM dim_flight df
        JOIN dim_airline da
            ON da.airline_code = :airline_code
        JOIN dim_airport origin
            ON origin.airport_code = :origin_airport
        JOIN dim_airport destination
            ON destination.airport_code = :destination_airport
        JOIN dim_date dd
            ON dd.full_date = :flight_date
        JOIN dim_time scheduled
            ON scheduled.time_value = :scheduled_departure_time
        LEFT JOIN dim_time actual
            ON actual.time_value = :actual_departure_time
        JOIN dim_aircraft dac
            ON dac.aircraft_type = :aircraft_type
        JOIN dim_weather_condition dw
            ON dw.weather_condition = :weather_condition
        JOIN dim_delay_cause dc
            ON dc.delay_cause = :delay_cause
        WHERE df.flight_number = :flight_number

        ON CONFLICT (
            flight_id,
            date_id,
            scheduled_departure_time_id,
            origin_airport_id,
            destination_airport_id
        )
        DO UPDATE SET
            actual_departure_time_id = EXCLUDED.actual_departure_time_id,
            weather_condition_id = EXCLUDED.weather_condition_id,
            delay_cause_id = EXCLUDED.delay_cause_id,
            delay_minutes = EXCLUDED.delay_minutes,
            is_delayed = EXCLUDED.is_delayed,
            updated_at = CURRENT_TIMESTAMP;
    """)

    with engine.begin() as conn:
        for _, row in fact_df.iterrows():
            values = {
                "flight_number": str(row["flight_number"]),
                "airline_code": row["airline"],
                "origin_airport": row["origin_airport"],
                "destination_airport": row["destination_airport"],
                "flight_date": row["flight_date"],
                "scheduled_departure_time": row["scheduled_departure_time"],
                "actual_departure_time": row["actual_departure_time"],
                "aircraft_type": row["aircraft_type"],
                "weather_condition": row["weather_condition"],
                "delay_cause": row["delay_cause"],
                "delay_minutes": int(row["delay_minutes"]),
                "is_delayed": bool(row["is_delayed"])
            }

            conn.execute(query, values)


def load_data(data):
    print("Loading dimension tables...")
    load_dimensions(data)

    print("Loading fact table...")
    load_fact_table(data)

    print("Database load complete.")