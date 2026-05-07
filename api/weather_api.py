import requests
import pandas as pd


def get_historical_weather(latitude, longitude, flight_date):
    """
    Fetch historical hourly weather data for a specific airport location and date.

    Parameters:
        latitude: airport latitude
        longitude: airport longitude
        flight_date: date in YYYY-MM-DD format

    Returns:
        pandas DataFrame containing hourly weather data
    """

    url = "https://archive-api.open-meteo.com/v1/archive"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": flight_date,
        "end_date": flight_date,
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "rain",
            "snowfall",
            "weather_code",
            "wind_speed_10m",
            "wind_gusts_10m"
        ],
        "timezone": "auto"
    }

    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()

        if "hourly" not in data:
            raise ValueError("No hourly weather data returned from API.")

        weather_df = pd.DataFrame(data["hourly"])

        if weather_df.empty:
            raise ValueError("Weather API returned an empty dataset.")

        return weather_df

    except requests.exceptions.RequestException as error:
        raise RuntimeError(f"Weather API request failed: {error}")


def get_weather_for_hour(latitude, longitude, flight_date, scheduled_hour):
    """
    Gets the weather closest to the scheduled flight departure hour.

    Parameters:
        latitude: airport latitude
        longitude: airport longitude
        flight_date: date in YYYY-MM-DD format
        scheduled_hour: hour of scheduled departure, from 0 to 23

    Returns:
        dictionary of weather features
    """

    weather_df = get_historical_weather(
        latitude=latitude,
        longitude=longitude,
        flight_date=flight_date
    )

    weather_df["time"] = pd.to_datetime(weather_df["time"])
    weather_df["hour"] = weather_df["time"].dt.hour

    scheduled_hour = int(scheduled_hour)

    closest_row = weather_df.iloc[
        (weather_df["hour"] - scheduled_hour).abs().argsort()[:1]
    ]

    row = closest_row.iloc[0]

    return {
        "temperature_2m": float(row.get("temperature_2m", 0)),
        "relative_humidity_2m": float(row.get("relative_humidity_2m", 0)),
        "precipitation": float(row.get("precipitation", 0)),
        "rain": float(row.get("rain", 0)),
        "snowfall": float(row.get("snowfall", 0)),
        "weather_code": float(row.get("weather_code", 0)),
        "wind_speed_10m": float(row.get("wind_speed_10m", 0)),
        "wind_gusts_10m": float(row.get("wind_gusts_10m", 0))
    }


def get_default_weather_features():
    """
    Returns fallback weather values if the API fails.
    This prevents the app from crashing during prediction.
    """

    return {
        "temperature_2m": 0.0,
        "relative_humidity_2m": 0.0,
        "precipitation": 0.0,
        "rain": 0.0,
        "snowfall": 0.0,
        "weather_code": 0.0,
        "wind_speed_10m": 0.0,
        "wind_gusts_10m": 0.0
    }


def safe_get_weather_for_hour(latitude, longitude, flight_date, scheduled_hour):
    """
    Safe wrapper for weather API.

    If the API fails, fallback values are returned instead of stopping the app.
    """

    try:
        return get_weather_for_hour(
            latitude=latitude,
            longitude=longitude,
            flight_date=flight_date,
            scheduled_hour=scheduled_hour
        )

    except Exception as error:
        print(f"Weather API failed. Using default weather values. Error: {error}")
        return get_default_weather_features()


if __name__ == "__main__":
    test_weather = safe_get_weather_for_hour(
        latitude=40.6413,
        longitude=-73.7781,
        flight_date="2024-01-15",
        scheduled_hour=14
    )

    print(test_weather)