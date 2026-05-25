import pandas as pd
import streamlit as st

from ml.predict import predict_from_details, build_full_dataset_for_lookup


st.set_page_config(
    page_title="FlightInsight",
    page_icon="✈️",
    layout="wide"
)


@st.cache_data(ttl=60)
def load_available_flights():
    df = build_full_dataset_for_lookup()

    df["flight_number"] = (
        df["flight_number"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    df = df[
        df["flight_number"].str.match(
            r"^[A-Z]{2,3}[0-9]{1,4}$",
            na=False
        )
    ]

    required_columns = [
        "flight_number",
        "airline_code",
        "origin_airport_code",
        "destination_airport_code",
        "full_date",
    ]

    for col in required_columns:
        if col not in df.columns:
            df[col] = None

    available_flights = (
        df[required_columns]
        .dropna(subset=["flight_number"])
        .drop_duplicates()
        .sort_values("flight_number")
        .reset_index(drop=True)
    )

    return available_flights


st.title("FlightInsight")
st.subheader("Flight Delay Prediction System")

try:
    available_flights = load_available_flights()

    if available_flights.empty:
        st.error("No valid flight numbers were found in the database.")
        st.stop()

    st.sidebar.header("Prediction Input")

    flight_options = available_flights["flight_number"].tolist()

    selected_flight = st.sidebar.selectbox(
        "Select Flight Number",
        flight_options
    )

    selected_date = st.sidebar.date_input(
        "Enter Flight Date"
    )

    predict_button = st.sidebar.button("Predict Delay")

    st.sidebar.divider()
    st.sidebar.caption(
        "Prediction uses historical flight data and available live API features."
    )

    if predict_button:
        try:
            result = predict_from_details(
                flight_number=selected_flight,
                selected_date=selected_date
            )

            st.success("Prediction complete.")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "Flight Number",
                    result.get("flight_number", selected_flight)
                )

            with col2:
                st.metric(
                    "Prediction",
                    result.get("prediction_label", "Unknown")
                )

            with col3:
                probability = result.get("probability")

                if probability is not None:
                    st.metric(
                        "Confidence",
                        f"{probability * 100:.1f}%"
                    )
                else:
                    st.metric("Confidence", "Not available")

            st.subheader("Prediction Details")

            st.write(
                f"Selected date: **{pd.to_datetime(selected_date).strftime('%Y-%m-%d')}**"
            )

            st.write(
                f"Live API data used: **{result.get('used_api_data', False)}**"
            )

            st.write(
                f"API flight status: **{result.get('api_live_flight_status', 'Not used')}**"
            )

            st.write(
                f"API departure delay: **{result.get('api_departure_delay_minutes', 0)} minutes**"
            )

            st.write(
                f"API arrival delay: **{result.get('api_arrival_delay_minutes', 0)} minutes**"
            )

        except ValueError as e:
            st.warning(str(e))
            st.info(
                "This flight number/date combination is not available in the historical database. "
                "Try selecting a flight from the available records table."
            )

        except Exception as e:
            st.error("An error occurred while running the prediction.")
            st.exception(e)

    st.subheader("Available Flight Records")
    st.dataframe(
        available_flights,
        use_container_width=True
    )

except Exception as e:
    st.error("An error occurred while loading the app.")
    st.exception(e)