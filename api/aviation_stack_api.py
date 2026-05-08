import os
import requests


BASE_URL = "https://api.aviationstack.com/v1"


def _get(endpoint, params=None):
    api_key = os.getenv("AVIATIONSTACK_API_KEY")

    if not api_key:
        raise ValueError("Missing AVIATIONSTACK_API_KEY environment variable.")

    if params is None:
        params = {}

    params["access_key"] = api_key

    response = requests.get(
        f"{BASE_URL}{endpoint}",
        params=params,
        timeout=15
    )

    response.raise_for_status()
    return response.json()


def get_live_flight_status(flight_number):
    """
    Gets real-time Aviationstack flight data.
    Example flight numbers: QF1, EK412, BA15, AA100.
    """

    try:
        data = _get(
            "/flights",
            params={
                "flight_iata": flight_number
            }
        )
    except Exception:
        return {
            "live_flight_status": "Unknown",
            "departure_delay_minutes_live": 0,
            "arrival_delay_minutes_live": 0,
        }

    flights = data.get("data", [])

    if not flights:
        return {
            "live_flight_status": "Unknown",
            "departure_delay_minutes_live": 0,
            "arrival_delay_minutes_live": 0,
        }

    flight = flights[0]

    status = flight.get("flight_status", "Unknown")

    departure = flight.get("departure", {}) or {}
    arrival = flight.get("arrival", {}) or {}

    departure_delay = departure.get("delay", 0) or 0
    arrival_delay = arrival.get("delay", 0) or 0

    return {
        "live_flight_status": status,
        "departure_delay_minutes_live": departure_delay,
        "arrival_delay_minutes_live": arrival_delay,
    }


def get_airport_live_flight_summary(iata_code):
    """
    Creates simple airport congestion features using live flights at an airport.
    This is not a direct airport delay API. It estimates congestion from live departures/arrivals.
    """

    try:
        departures_data = _get(
            "/flights",
            params={
                "dep_iata": iata_code,
                "limit": 100
            }
        )

        arrivals_data = _get(
            "/flights",
            params={
                "arr_iata": iata_code,
                "limit": 100
            }
        )

    except Exception:
        return {
            "airport_live_departures_count": 0,
            "airport_live_arrivals_count": 0,
            "airport_delayed_departures_count": 0,
            "airport_delayed_arrivals_count": 0,
            "airport_avg_departure_delay": 0,
            "airport_avg_arrival_delay": 0,
        }

    departures = departures_data.get("data", [])
    arrivals = arrivals_data.get("data", [])

    departure_delays = [
        flight.get("departure", {}).get("delay", 0) or 0
        for flight in departures
    ]

    arrival_delays = [
        flight.get("arrival", {}).get("delay", 0) or 0
        for flight in arrivals
    ]

    delayed_departures = sum(delay > 0 for delay in departure_delays)
    delayed_arrivals = sum(delay > 0 for delay in arrival_delays)

    avg_departure_delay = (
        sum(departure_delays) / len(departure_delays)
        if departure_delays else 0
    )

    avg_arrival_delay = (
        sum(arrival_delays) / len(arrival_delays)
        if arrival_delays else 0
    )

    return {
        "airport_live_departures_count": len(departures),
        "airport_live_arrivals_count": len(arrivals),
        "airport_delayed_departures_count": delayed_departures,
        "airport_delayed_arrivals_count": delayed_arrivals,
        "airport_avg_departure_delay": avg_departure_delay,
        "airport_avg_arrival_delay": avg_arrival_delay,
    }