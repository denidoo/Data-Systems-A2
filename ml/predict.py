import joblib
import pandas as pd
from pathlib import Path

from api.weather_api import safe_get_weather_for_hour


MODEL_PATH = Path("ml/models/delay_model.pkl")


def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found at {MODEL_PATH}. "
            "Run: python -m ml.train_model"
        )

    return joblib.load(MODEL_PATH)


def build_prediction_input(
    flight_date,
    scheduled_hour,
    scheduled_minute,
    airline_code,
    origin_airport_code,
    destination_airport_code,
    flight_type="Domestic",
    route_category="Unknown",
    route_distance=0,
    aircraft_category="Unknown",
    seating_capacity=0,
    latitude=None,
    longitude=None
):
    flight_date = pd.to_datetime(flight_date)

    weather = {
        "temperature": 0,
        "wind_speed": 0,
        "visibility": 0
    }

    if latitude is not None and longitude is not None:
        weather_api_result = safe_get_weather_for_hour(
            latitude=latitude,
            longitude=longitude,
            flight_date=flight_date.strftime("%Y-%m-%d"),
            scheduled_hour=scheduled_hour
        )

        weather["temperature"] = weather_api_result.get("temperature_2m", 0)
        weather["wind_speed"] = weather_api_result.get("wind_speed_10m", 0)
        weather["visibility"] = 0

    input_data = {
        "day": flight_date.day,
        "month": flight_date.month,
        "year": flight_date.year,
        "day_of_week": flight_date.dayofweek,
        "is_weekend": int(flight_date.dayofweek in [5, 6]),
        "hour": int(scheduled_hour),
        "minute": int(scheduled_minute),
        "is_night_flight": int(0 <= int(scheduled_hour) <= 5),

        "temperature": weather["temperature"],
        "wind_speed": weather["wind_speed"],
        "visibility": weather["visibility"],

        "route_distance": route_distance,
        "seating_capacity": seating_capacity,

        "time_of_day": classify_time_of_day(int(scheduled_hour)),
        "airline_code": airline_code,
        "origin_airport_code": origin_airport_code,
        "destination_airport_code": destination_airport_code,
        "weather_type": classify_weather_type(weather),
        "flight_type": flight_type,
        "route_category": route_category,
        "aircraft_category": aircraft_category
    }

    return pd.DataFrame([input_data])


def classify_time_of_day(hour):
    if 0 <= hour <= 5:
        return "Night"
    elif 6 <= hour <= 11:
        return "Morning"
    elif 12 <= hour <= 17:
        return "Afternoon"
    else:
        return "Evening"


def classify_weather_type(weather):
    if weather.get("wind_speed", 0) > 35:
        return "Poor Weather"

    if weather.get("temperature", 0) < -5:
        return "Poor Weather"

    return "Unknown"


def predict_delay(input_df):
    model = load_model()

    prediction = model.predict(input_df)[0]

    probability = None

    if hasattr(model, "predict_proba"):
        probability = model.predict_proba(input_df)[0][1]

    result = {
        "prediction": int(prediction),
        "prediction_label": "Delayed" if prediction == 1 else "On Time",
        "delay_probability": probability
    }

    return result


def predict_from_details(
    flight_date,
    scheduled_hour,
    scheduled_minute,
    airline_code,
    origin_airport_code,
    destination_airport_code,
    flight_type="Domestic",
    route_category="Unknown",
    route_distance=0,
    aircraft_category="Unknown",
    seating_capacity=0,
    latitude=None,
    longitude=None
):
    input_df = build_prediction_input(
        flight_date=flight_date,
        scheduled_hour=scheduled_hour,
        scheduled_minute=scheduled_minute,
        airline_code=airline_code,
        origin_airport_code=origin_airport_code,
        destination_airport_code=destination_airport_code,
        flight_type=flight_type,
        route_category=route_category,
        route_distance=route_distance,
        aircraft_category=aircraft_category,
        seating_capacity=seating_capacity,
        latitude=latitude,
        longitude=longitude
    )

    result = predict_delay(input_df)

    return result, input_df


if __name__ == "__main__":
    result, input_df = predict_from_details(
        flight_date="2024-01-15",
        scheduled_hour=14,
        scheduled_minute=30,
        airline_code="AA",
        origin_airport_code="JFK",
        destination_airport_code="LAX",
        route_distance=2475,
        route_category="Medium-haul",
        latitude=40.6413,
        longitude=-73.7781
    )

    print(input_df)
    print(result)