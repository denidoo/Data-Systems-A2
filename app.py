import streamlit as st
import pandas as pd

from ml.predict import predict_from_details, build_full_dataset_for_lookup


st.set_page_config(
    page_title="FlightInsight",
    page_icon="✈️",
    layout="wide"
)

st.title("FlightInsight")
st.subheader("Flight Delay Prediction System")


@st.cache_data(ttl=60)
def load_available_flights():
    df = build_full_dataset_for_lookup()

    # Convert to string and clean
    df["flight_number"] = (
        df["flight_number"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    # Remove invalid flight numbers
    df = df[
        df["flight_number"].str.match(
            r"^[A-Z]{2,3}[0-9]{1,4}$",
            na=False
        )
    ]

    available_flights = (
        df[
            [
                "flight_number",
                "airline_code",
                "origin_airport_code",
                "destination_airport_code",
                "full_date",
            ]
        ]
        .dropna(subset=["flight_number"])
        .drop_duplicates()
        .sort_values("flight_number")
    )

    return available_flights

def safe_get(df, column, default="Unknown"):
    if column in df.columns:
        value = df[column].iloc[0]
        if pd.notna(value):
            return value
    return default


try:
    available_flights = load_available_flights()

    st.sidebar.header("Prediction Input")

    flight_options = available_flights["flight_number"].unique().tolist()

    selected_flight = st.sidebar.selectbox(
        "Select Flight Number",
        flight_options
    )

    selected_date = st.sidebar.date_input(
        "Enter Flight Date"
    )

    predict_button = st.sidebar.button("Predict Delay")

    st.sidebar.markdown("---")
    st.sidebar.caption(
        "Prediction uses historical flight data and available live API features."
    )

    if predict_button:
        try:
            with st.spinner("Running prediction..."):
                result, input_df = predict_from_details(
                    flight_number=selected_flight,
                    flight_date=selected_date,
                )

            st.markdown("## Prediction Result")

            col1, col2 = st.columns(2)

            prediction_label = result.get(
                "prediction_label",
                result.get("status", "Unknown")
            )

            probability = result.get(
                "probability",
                result.get("delayed_probability", None)
            )

            with col1:
                st.metric("Predicted Status", prediction_label)

            with col2:
                if probability is not None:
                    st.metric("Prediction Confidence", f"{probability:.2%}")
                else:
                    st.metric("Prediction Confidence", "Unavailable")

            st.markdown("## Flight Details")

            details_col1, details_col2, details_col3 = st.columns(3)

            with details_col1:
                st.write("**Flight Number:**", selected_flight)
                st.write("**Selected Flight Date:**", selected_date)
                st.write("**Airline:**", safe_get(input_df, "airline_code"))
                st.write("**Flight Type:**", safe_get(input_df, "flight_type"))

            with details_col2:
                st.write("**Origin Airport:**", safe_get(input_df, "origin_airport_code"))
                st.write("**Destination Airport:**", safe_get(input_df, "destination_airport_code"))
                st.write("**Route Category:**", safe_get(input_df, "route_category"))

            with details_col3:
                scheduled_hour = safe_get(input_df, "hour", None)

                if scheduled_hour is not None:
                    st.write("**Scheduled Hour:**", int(scheduled_hour))
                else:
                    st.write("**Scheduled Hour:**", "Unknown")

                st.write("**Weather Type:**", safe_get(input_df, "weather_type"))
                st.write("**Aircraft Category:**", safe_get(input_df, "aircraft_category"))

            if result.get("used_api_data") is True:
                st.markdown("## Live API Details")
                st.write("**API Source:** Aviationstack")
                st.write("**Live Flight Status:**", result.get("api_live_flight_status", "Unknown"))
                st.write("**API Departure Delay Minutes:**", result.get("api_departure_delay_minutes", 0))
                st.write("**API Arrival Delay Minutes:**", result.get("api_arrival_delay_minutes", 0))

            st.markdown("## Historical Trends")

            selected_records = available_flights[
                available_flights["flight_number"] == str(selected_flight)
            ]

            st.write("Matching historical records for this flight number in the database:")

            st.dataframe(
                selected_records,
                use_container_width=True,
            )

            with st.expander("Show model input features"):
                st.dataframe(input_df.T)

        except ValueError as e:
            st.warning(str(e))
            st.info(
                "This flight number/date combination is not available in the historical database. "
                "Try selecting a flight from the available records table."
            )

        except Exception as e:
            st.error("An error occurred while running the prediction.")
            st.exception(e)

    else:
        st.info("Select a flight number from the sidebar, then click Predict Delay.")

        st.markdown("## Available Flight Records")

        st.dataframe(
            available_flights.head(50),
            use_container_width=True,
        )

except Exception as e:
    st.error("An error occurred while loading the app.")
    st.exception(e)