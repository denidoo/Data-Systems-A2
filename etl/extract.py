from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"


def extract_data():
    flights_path = RAW_DATA_DIR / "flights.csv"
    airlines_path = RAW_DATA_DIR / "airlines.csv"
    airports_path = RAW_DATA_DIR / "airports.csv"

    if not flights_path.exists():
        raise FileNotFoundError(f"Missing file: {flights_path}")

    if not airlines_path.exists():
        raise FileNotFoundError(f"Missing file: {airlines_path}")

    if not airports_path.exists():
        raise FileNotFoundError(f"Missing file: {airports_path}")

    flights = pd.read_csv(flights_path, low_memory=False)
    airlines = pd.read_csv(airlines_path)
    airports = pd.read_csv(airports_path)

    print(f"Flights loaded: {len(flights)} rows")
    print(f"Airlines loaded: {len(airlines)} rows")
    print(f"Airports loaded: {len(airports)} rows")

    return {
        "flights": flights,
        "airlines": airlines,
        "airports": airports
    }