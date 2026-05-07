import pandas as pd
from pathlib import Path


RAW_DIR = Path("data/raw")
MANUAL_DIR = Path("data/manual_uploads")

RAW_FLIGHTS_PATH = RAW_DIR / "flights.csv"
RAW_AIRLINES_PATH = RAW_DIR / "airlines.csv"
RAW_AIRPORTS_PATH = RAW_DIR / "airports.csv"
MANUAL_FLIGHTS_PATH = MANUAL_DIR / "manual_flights.csv"


def get_first_existing_column(df, possible_columns):
    for column in possible_columns:
        if column in df.columns:
            return column
    return None


def normalise_columns(df):
    df = df.copy()
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )
    return df


def extract():
    if not RAW_FLIGHTS_PATH.exists():
        raise FileNotFoundError(
            f"Missing raw flight dataset: {RAW_FLIGHTS_PATH}. "
            "Place flights.csv inside data/raw/."
        )

    flights = pd.read_csv(RAW_FLIGHTS_PATH, low_memory=False)
    print(f"Main flight file loaded: {len(flights)} rows")

    if MANUAL_FLIGHTS_PATH.exists():
        manual_flights = pd.read_csv(MANUAL_FLIGHTS_PATH, low_memory=False)
        flights = pd.concat([flights, manual_flights], ignore_index=True)
        print(f"Manual flight file added: {len(manual_flights)} rows")

    print(f"Extract complete. Total rows loaded: {len(flights)}")
    return flights


def extract_airlines_lookup():
    if RAW_AIRLINES_PATH.exists():
        airlines = pd.read_csv(RAW_AIRLINES_PATH)
        airlines = normalise_columns(airlines)

        code_col = get_first_existing_column(
            airlines,
            ["iata_code", "airline_code", "carrier", "code"]
        )

        name_col = get_first_existing_column(
            airlines,
            ["airline", "airline_name", "name"]
        )

        if code_col and name_col:
            airlines = airlines[[code_col, name_col]].drop_duplicates()
            airlines = airlines.rename(columns={
                code_col: "airline_code",
                name_col: "airline_name"
            })
            airlines["airline_code"] = airlines["airline_code"].astype(str).str.strip()
            airlines["airline_name"] = airlines["airline_name"].astype(str).str.strip()
            return airlines

    return pd.DataFrame(columns=["airline_code", "airline_name"])


def extract_airports_lookup():
    if RAW_AIRPORTS_PATH.exists():
        airports = pd.read_csv(RAW_AIRPORTS_PATH)
        airports = normalise_columns(airports)

        code_col = get_first_existing_column(
            airports,
            ["iata_code", "airport_code", "origin", "code"]
        )

        name_col = get_first_existing_column(
            airports,
            ["airport", "airport_name", "name"]
        )

        city_col = get_first_existing_column(
            airports,
            ["city", "airport_city"]
        )

        country_col = get_first_existing_column(
            airports,
            ["country", "airport_country"]
        )

        if code_col:
            result = pd.DataFrame()
            result["airport_code"] = airports[code_col].astype(str).str.strip()
            result["airport_name"] = airports[name_col].astype(str).str.strip() if name_col else result["airport_code"]
            result["airport_city"] = airports[city_col].astype(str).str.strip() if city_col else "Unknown"
            result["airport_country"] = airports[country_col].astype(str).str.strip() if country_col else "United States"
            result["airport_continent"] = "North America"
            result["airport_elevation"] = 0
            result["airport_type"] = "Unknown"

            return result.drop_duplicates()

    return pd.DataFrame(columns=[
        "airport_code",
        "airport_name",
        "airport_city",
        "airport_country",
        "airport_continent",
        "airport_elevation",
        "airport_type"
    ])