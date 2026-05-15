from sqlalchemy import text
from database.db_config import engine


with engine.connect() as conn:
    rows = conn.execute(text("""
        SELECT
            fp.flight_performance_id,
            al.airline_code,
            al.airline_name,
            fl.flight_number,
            oa.airport_code AS origin_airport,
            da.airport_code AS destination_airport,
            fp.delay_minutes,
            fp.delay_status,
            fp.api_source,
            fp.api_live_flight_status,
            fp.api_departure_delay_minutes,
            fp.api_arrival_delay_minutes,
            fp.api_origin_live_departures_count,
            fp.api_destination_live_arrivals_count
        FROM fact_flightperformance fp
        LEFT JOIN dim_airline al
            ON fp.airline_id = al.airline_id
        LEFT JOIN dim_flight fl
            ON fp.flight_id = fl.flight_id
        LEFT JOIN dim_airport oa
            ON fp.origin_airport_id = oa.airport_id
        LEFT JOIN dim_airport da
            ON fp.destination_airport_id = da.airport_id
        WHERE fp.api_source = 'Aviationstack'
        ORDER BY fp.flight_performance_id DESC
        LIMIT 10;
    """)).fetchall()

if not rows:
    print("No Aviationstack API rows found in fact_flightperformance.")
else:
    for row in rows:
        print(row)