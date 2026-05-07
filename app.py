import streamlit as st
import pandas as pd

from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier

from database.db_config import engine


st.set_page_config(
    page_title="FlightInsight",
    layout="centered"
)

st.title("Flight Delay Predictor")

st.write("Enter a flight number and departure date to predict whether the flight is likely to be delayed.")

def load_flight_data():
    query = """
        SELECT
            f.flight_performance_id,
            d.full_date,
            t.hour,
            t.minute,
            t.time_of_day,
            fl.flight_number,
            fl.flight_type,
            fl.route_category,
            fl.route_distance,
            al.airline_name,
            al.airline_code,
            oa.airport_code AS origin_airport,
            da.airport_code AS destination_airport,
            w.weather_type,
            w.temperature,
            w.wind_speed,
            w.visibility,
            ac.aircraft_model,
            ac.manufacturer,
            ac.seating_capacity,
            ac.aircraft_category,
            dc.delay_cause_type,
            dc.is_controllable,
            f.delay_minutes,
            f.cancellation_flag,
            f.passengers,
            f.scheduled_departure_datetime,
            f.actual_departure_datetime,
            f.scheduled_arrival_datetime,
            f.actual_arrival_datetime,
            f.delay_status
        FROM fact_flightperformance f
        JOIN dim_date d ON f.date_id = d.date_id
        JOIN dim_time t ON f.time_id = t.time_id
        JOIN dim_flight fl ON f.flight_id = fl.flight_id
        JOIN dim_airline al ON f.airline_id = al.airline_id
        JOIN dim_airport oa ON f.origin_airport_id = oa.airport_id
        JOIN dim_airport da ON f.destination_airport_id = da.airport_id
        JOIN dim_weather_condition w ON f.weather_id = w.weather_id
        JOIN dim_aircraft ac ON f.aircraft_id = ac.aircraft_id
        JOIN dim_delay_cause dc ON f.delay_cause_id = dc.delay_cause_id;
    """

    return pd.read_sql(query, engine)


try:
    df = load_flight_data()
except Exception as e:
    st.error("Could not connect to PostgreSQL or load flight data.")
    st.write(e)
    st.stop()


if df.empty:
    st.error("No data found in the PostgreSQL database. Run create_tables.py and etl_load_data.py first.")
    st.stop()


df["full_date"] = pd.to_datetime(df["full_date"])
df["month"] = df["full_date"].dt.month
df["day_of_week"] = df["full_date"].dt.dayofweek
df["full_date"] = pd.to_datetime(df["full_date"]).dt.strftime("%Y-%m-%d")


categorical_columns = [
    "flight_number",
    "flight_type",
    "route_category",
    "airline_name",
    "airline_code",
    "origin_airport",
    "destination_airport",
    "weather_type",
    "aircraft_model",
    "manufacturer",
    "aircraft_category",
    "delay_cause_type",
    "time_of_day"
]


features = [
    "flight_number",
    "flight_type",
    "route_category",
    "route_distance",
    "airline_name",
    "airline_code",
    "origin_airport",
    "destination_airport",
    "weather_type",
    "temperature",
    "wind_speed",
    "visibility",
    "aircraft_model",
    "manufacturer",
    "seating_capacity",
    "aircraft_category",
    "delay_cause_type",
    "is_controllable",
    "passengers",
    "hour",
    "minute",
    "time_of_day",
    "month",
    "day_of_week"
]


model_df = df.copy()

label_encoders = {}

for column in categorical_columns:
    encoder = LabelEncoder()
    model_df[column] = encoder.fit_transform(model_df[column].astype(str))
    label_encoders[column] = encoder


target_encoder = LabelEncoder()
model_df["delay_status"] = target_encoder.fit_transform(model_df["delay_status"].astype(str))


X = model_df[features]
y = model_df["delay_status"]


model = RandomForestClassifier(
    n_estimators=100,
    random_state=42
)

model.fit(X, y)


with st.form("prediction_form"):

    input_flight_number = st.text_input(
        "Flight Number",
        placeholder="Example: AA1234"
    )

    input_departure_date = st.date_input(
        "Departure Date"
    )

    submitted = st.form_submit_button("Predict")


if submitted:

    selected_date = pd.to_datetime(input_departure_date)
    clean_flight_number = input_flight_number.strip().upper()

    historical_flights = df[
        df["flight_number"].astype(str).str.upper() == clean_flight_number
    ]

    if historical_flights.empty:
        st.error("No historical records found for that flight number. The model needs past examples of this flight before it can predict it.")
        st.stop()

    # Use the most recent historical record as the base flight profile
    flight_record = historical_flights.sort_values("full_date").iloc[-1].copy()

    # Replace date-based fields with the user-selected date
    flight_record["month"] = selected_date.month
    flight_record["day_of_week"] = selected_date.dayofweek

    prediction_input = pd.DataFrame([flight_record])
    prediction_input = prediction_input[features]

    # Encode categorical values safely
    for column in categorical_columns:
        prediction_input[column] = prediction_input[column].astype(str)

        known_classes = set(label_encoders[column].classes_)

        if prediction_input[column].iloc[0] not in known_classes:
            st.error(f"The value '{prediction_input[column].iloc[0]}' in column '{column}' was not seen during training.")
            st.stop()

        prediction_input[column] = label_encoders[column].transform(prediction_input[column])

    prediction = model.predict(prediction_input)[0]
    prediction_label = target_encoder.inverse_transform([prediction])[0]

    prediction_probability = model.predict_proba(prediction_input)[0]
    confidence = max(prediction_probability) * 100

    if prediction_label == "Delayed":
        st.error(f"Predicted Status: {prediction_label}")
    else:
        st.success(f"Predicted Status: {prediction_label}")

    st.write(f"**Model Confidence:** {confidence:.1f}%")

    st.write("### Prediction Factors Used")
    st.write(f"**Flight Number:** {flight_record['flight_number']}")
    st.write(f"**Selected Date:** {selected_date.strftime('%Y-%m-%d')}")
    st.write(f"**Month:** {selected_date.month}")
    st.write(f"**Day of Week:** {selected_date.day_name()}")
    st.write(f"**Airline:** {flight_record['airline_name']}")
    st.write(f"**Route:** {flight_record['origin_airport']} → {flight_record['destination_airport']}")
    st.write(f"**Departure Time:** {flight_record['hour']:02d}:{flight_record['minute']:02d}")
    st.write(f"**Time of Day:** {flight_record['time_of_day']}")
    st.write(f"**Aircraft:** {flight_record['aircraft_model']}")
    st.write(f"**Historical Weather Type:** {flight_record['weather_type']}")
    st.write(f"**Historical Delay Cause:** {flight_record['delay_cause_type']}")