import pandas as pd

from database.db_config import engine


# ------------------------------------------------------------
# FLIGHTS
# ------------------------------------------------------------

def get_flight_options():
    query = """
        SELECT DISTINCT
            flight_number
        FROM dim_flight
        ORDER BY flight_number;
    """

    return pd.read_sql(query, engine)


def get_flight_route_details(flight_number):
    query = """
        SELECT
            flight_number,
            flight_type,
            route_category,
            route_distance
        FROM dim_flight
        WHERE flight_number = %(flight_number)s
        LIMIT 1;
    """

    df = pd.read_sql(
        query,
        engine,
        params={"flight_number": flight_number}
    )

    if df.empty:
        return None

    return df.iloc[0].to_dict()


# ------------------------------------------------------------
# AIRLINES
# ------------------------------------------------------------

def get_airline_options():
    query = """
        SELECT
            airline_id,
            airline_code,
            airline_name
        FROM dim_airline
        ORDER BY airline_code;
    """

    return pd.read_sql(query, engine)


# ------------------------------------------------------------
# AIRPORTS
# ------------------------------------------------------------

def get_airport_options():
    query = """
        SELECT
            airport_id,
            airport_code,
            airport_name,
            airport_city,
            airport_country,
            latitude,
            longitude
        FROM dim_airport
        ORDER BY airport_code;
    """

    return pd.read_sql(query, engine)


def get_airport_by_code(airport_code):
    query = """
        SELECT
            airport_id,
            airport_code,
            airport_name,
            airport_city,
            airport_country,
            latitude,
            longitude
        FROM dim_airport
        WHERE airport_code = %(airport_code)s
        LIMIT 1;
    """

    df = pd.read_sql(
        query,
        engine,
        params={"airport_code": airport_code}
    )

    if df.empty:
        return None

    return df.iloc[0].to_dict()