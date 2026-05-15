import os
import requests
from dotenv import load_dotenv

load_dotenv()

AVIATIONSTACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY")
BASE_URL = "http://api.aviationstack.com/v1/flights"


def _safe_get(data, *keys, default=None):
    current = data

    for key in keys:
        if not isinstance(current, dict):
            return default

        current = current.get(key)

        if current is None:
            return default

    return current


def get_live_flights(max_rows=500, page_size=100):
    """
    Pulls multiple live flight records from Aviationstack.

    max_rows controls the total number of API flight rows to request.
    page_size controls how many rows are requested per API call.
    """

    if not AVIATIONSTACK_API_KEY:
        raise ValueError("AVIATIONSTACK_API_KEY is missing from your .env file.")

    all_flights = []
    offset = 0

    while len(all_flights) < max_rows:
        remaining = max_rows - len(all_flights)
        limit = min(page_size, remaining)

        params = {
            "access_key": AVIATIONSTACK_API_KEY,
            "limit": limit,
            "offset": offset
        }

        response = requests.get(BASE_URL, params=params, timeout=30)
        response.raise_for_status()

        payload = response.json()
        rows = payload.get("data", [])

        if not rows:
            break

        for row in rows:
            normalised = normalise_flight(row)

            if normalised is not None:
                all_flights.append(normalised)

        offset += limit

    return all_flights


def normalise_flight(row):
    flight_number = _safe_get(row, "flight", "iata")
    airline_code = _safe_get(row, "airline", "iata")
    airline_name = _safe_get(row, "airline", "name")

    origin_airport_code = _safe_get(row, "departure", "iata")
    origin_airport_name = _safe_get(row, "departure", "airport")

    destination_airport_code = _safe_get(row, "arrival", "iata")
    destination_airport_name = _safe_get(row, "arrival", "airport")

    if not flight_number or not airline_code or not origin_airport_code or not destination_airport_code:
        return None

    departure_delay = _safe_get(row, "departure", "delay", default=0) or 0
    arrival_delay = _safe_get(row, "arrival", "delay", default=0) or 0

    scheduled_departure = _safe_get(row, "departure", "scheduled")
    actual_departure = _safe_get(row, "departure", "actual")

    scheduled_arrival = _safe_get(row, "arrival", "scheduled")
    actual_arrival = _safe_get(row, "arrival", "actual")

    return {
        "flight_number": flight_number,
        "airline_code": airline_code,
        "airline_name": airline_name or airline_code,

        "origin_airport_code": origin_airport_code,
        "origin_airport_name": origin_airport_name or origin_airport_code,

        "destination_airport_code": destination_airport_code,
        "destination_airport_name": destination_airport_name or destination_airport_code,

        "live_flight_status": row.get("flight_status"),

        "departure_delay_minutes_live": departure_delay,
        "arrival_delay_minutes_live": arrival_delay,

        "scheduled_departure_datetime": scheduled_departure,
        "actual_departure_datetime": actual_departure,
        "scheduled_arrival_datetime": scheduled_arrival,
        "actual_arrival_datetime": actual_arrival,

        "flight_type": "Unknown",
        "route_category": "Unknown",
        "route_distance": None
    }