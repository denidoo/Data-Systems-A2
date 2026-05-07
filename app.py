import streamlit as st

from database.db_queries import (
    get_flight_options,
    get_airline_options,
    get_airport_options,
    get_flight_route_details
)

from ml.predict import predict_from_details


# ------------------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------------------

st.set_page_config(
    page_title="FlightInsight",
    page_icon="✈️",
    layout="wide"
)


# ------------------------------------------------------------
# CACHED DATA LOADING
# ------------------------------------------------------------

@st.cache_data(ttl=3600)
def load_flight_options():
    return get_flight_options()


@st.cache_data(ttl=3600)
def load_airline_options():
    return get_airline_options()


@st.cache_data(ttl=3600)
def load_airport_options():
    return get_airport_options()


@st.cache_data(ttl=3600)
def load_flight_route_details(flight_number):
    return get_flight_route_details(flight_number)


# ------------------------------------------------------------
# MAIN UI
# ------------------------------------------------------------

st.title("FlightInsight")
st.subheader("Flight Delay Prediction System")

st.write(
    "Enter flight details below to predict whether a flight is likely to be delayed."
)


# ------------------------------------------------------------
# LOAD DATABASE DATA
# ------------------------------------------------------------

try:
    flight_options = load_flight_options()
    airline_options = load_airline_options()
    airport_options = load_airport_options()

except Exception as error:
    st.error("Could not load data from the database.")
    st.exception(error)
    st.stop()


if flight_options.empty:
    st.warning("No flights found. Run the ETL pipeline first.")
    st.stop()

if airline_options.empty:
    st.warning("No airlines found. Run the ETL pipeline first.")
    st.stop()

if airport_options.empty:
    st.warning("No airports found. Run the ETL pipeline first.")
    st.stop()


# ------------------------------------------------------------
# INPUT FORM
# ------------------------------------------------------------

with st.form("prediction_form"):
    col1, col2 = st.columns(2)

    with col1:
        flight_number = st.selectbox(
            "Flight Number",
            flight_options["flight_number"].tolist()
        )

        flight_date = st.date_input("Departure Date")

        scheduled_time = st.time_input("Scheduled Departure Time")

    with col2:
        airline_code = st.selectbox(
            "Airline",
            airline_options["airline_code"].tolist()
        )

        origin_airport_code = st.selectbox(
            "Origin Airport",
            airport_options["airport_code"].tolist()
        )

        destination_airport_code = st.selectbox(
            "Destination Airport",
            airport_options["airport_code"].tolist()
        )

    submitted = st.form_submit_button("Predict Delay")


# ------------------------------------------------------------
# PREDICTION
# ------------------------------------------------------------

if submitted:
    route_details = load_flight_route_details(flight_number)

    if route_details is None:
        st.error("Flight route details were not found in the database.")
        st.stop()

    origin_airport_df = airport_options[
        airport_options["airport_code"] == origin_airport_code
    ]

    if origin_airport_df.empty:
        st.error("Origin airport details were not found.")
        st.stop()

    origin_airport = origin_airport_df.iloc[0]

    latitude = origin_airport.get("latitude", None)
    longitude = origin_airport.get("longitude", None)

    try:
        result, input_df = predict_from_details(
            flight_date=flight_date,
            scheduled_hour=scheduled_time.hour,
            scheduled_minute=scheduled_time.minute,
            airline_code=airline_code,
            origin_airport_code=origin_airport_code,
            destination_airport_code=destination_airport_code,
            flight_type=route_details.get("flight_type", "Domestic"),
            route_category=route_details.get("route_category", "Unknown"),
            route_distance=route_details.get("route_distance", 0),
            aircraft_category="Unknown",
            seating_capacity=0,
            latitude=latitude,
            longitude=longitude
        )

        st.divider()

        if result["prediction_label"] == "Delayed":
            st.error("Prediction: Flight is likely to be delayed")
        else:
            st.success("Prediction: Flight is likely to be on time")

        if result["delay_probability"] is not None:
            st.metric(
                label="Delay Probability",
                value=f"{result['delay_probability']:.2%}"
            )

        with st.expander("View prediction input features"):
            st.dataframe(input_df, use_container_width=True)

    except FileNotFoundError:
        st.error(
            "Model file not found. Run the model training script first:\n\n"
            "`python -m ml.train_model`"
        )

    except Exception as error:
        st.error("Prediction failed.")
        st.exception(error)


# ------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------

st.sidebar.title("FlightInsight Menu")

st.sidebar.write("This app predicts flight delay risk using:")
st.sidebar.write("- Historical flight data")
st.sidebar.write("- Airline and airport data")
st.sidebar.write("- Route information")
st.sidebar.write("- Real weather API data")

st.sidebar.divider()

if st.sidebar.button("Refresh Cached Data"):
    st.cache_data.clear()
    st.rerun()