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


@st.cache_data
def load_available_flights():
    df = build_full_dataset_for_lookup()

    df["flight_number"] = df["flight_number"].astype(str)

    available_flights = (
        df[[
            "flight_number",
            "airline_code",
            "origin_airport_code",
            "destination_airport_code",
            "full_date"
        ]]
        .dropna(subset=["flight_number"])
        .drop_duplicates()
        .sort_values("flight_number")
    )

    return available_flights


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
    st.sidebar.caption("Prediction uses historical data plus live Aviationstack API data.")

    if predict_button:
        with st.spinner("Running prediction and fetching live aviation data..."):
            result, input_df = predict_from_details(
                flight_number=selected_flight,
                flight_date=selected_date
            )

        st.markdown("## Prediction Result")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Predicted Status", result["status"])

        with col2:
            if result["delayed_probability"] is not None:
                st.metric(
                    "Delay Probability",
                    f"{result['delayed_probability']:.2%}"
                )
            else:
                st.metric("Delay Probability", "Unavailable")

        with col3:
            st.metric(
                "Live Flight Status",
                input_df["live_flight_status"].iloc[0]
            )

        st.markdown("## Flight Details")

        details_col1, details_col2, details_col3 = st.columns(3)

        with details_col1:
            st.write("**Flight Number:**", selected_flight)
            st.write("**Selected Flight Date:**", selected_date)
            st.write("**Airline:**", input_df["airline_code"].iloc[0])
            st.write("**Flight Type:**", input_df["flight_type"].iloc[0])

        with details_col2:
            st.write("**Origin Airport:**", input_df["origin_airport_code"].iloc[0])
            st.write("**Destination Airport:**", input_df["destination_airport_code"].iloc[0])
            st.write("**Route Category:**", input_df["route_category"].iloc[0])

        with details_col3:
            st.write("**Scheduled Hour:**", int(input_df["hour"].iloc[0]))
            st.write("**Weather Type:**", input_df["weather_type"].iloc[0])
            st.write("**Aircraft Category:**", input_df["aircraft_category"].iloc[0])

        st.markdown("## Live Aviationstack Data")

        live_col1, live_col2 = st.columns(2)

        with live_col1:
            st.markdown("### Flight-Level Live Data")
            st.metric(
                "Live Departure Delay",
                f"{input_df['departure_delay_minutes_live'].iloc[0]:.0f} min"
            )
            st.metric(
                "Live Arrival Delay",
                f"{input_df['arrival_delay_minutes_live'].iloc[0]:.0f} min"
            )

        with live_col2:
            st.markdown("### Current Flight Status")
            st.write("**Status:**", input_df["live_flight_status"].iloc[0])

        st.markdown("## Origin Airport Live Activity")

        origin_col1, origin_col2, origin_col3 = st.columns(3)

        with origin_col1:
            st.metric(
                "Live Departures",
                int(input_df["origin_live_departures_count"].iloc[0])
            )
            st.metric(
                "Live Arrivals",
                int(input_df["origin_live_arrivals_count"].iloc[0])
            )

        with origin_col2:
            st.metric(
                "Delayed Departures",
                int(input_df["origin_delayed_departures_count"].iloc[0])
            )
            st.metric(
                "Delayed Arrivals",
                int(input_df["origin_delayed_arrivals_count"].iloc[0])
            )

        with origin_col3:
            st.metric(
                "Avg Departure Delay",
                f"{input_df['origin_avg_departure_delay'].iloc[0]:.1f} min"
            )
            st.metric(
                "Avg Arrival Delay",
                f"{input_df['origin_avg_arrival_delay'].iloc[0]:.1f} min"
            )

        st.markdown("## Destination Airport Live Activity")

        destination_col1, destination_col2, destination_col3 = st.columns(3)

        with destination_col1:
            st.metric(
                "Live Departures",
                int(input_df["destination_live_departures_count"].iloc[0])
            )
            st.metric(
                "Live Arrivals",
                int(input_df["destination_live_arrivals_count"].iloc[0])
            )

        with destination_col2:
            st.metric(
                "Delayed Departures",
                int(input_df["destination_delayed_departures_count"].iloc[0])
            )
            st.metric(
                "Delayed Arrivals",
                int(input_df["destination_delayed_arrivals_count"].iloc[0])
            )

        with destination_col3:
            st.metric(
                "Avg Departure Delay",
                f"{input_df['destination_avg_departure_delay'].iloc[0]:.1f} min"
            )
            st.metric(
                "Avg Arrival Delay",
                f"{input_df['destination_avg_arrival_delay'].iloc[0]:.1f} min"
            )

        st.markdown("## Model Input Features")

        with st.expander("Show full prediction input data"):
            st.dataframe(input_df.T)

    else:
        st.info("Select a flight number from the sidebar, then click Predict Delay.")

        st.markdown("## Available Flight Records")

        st.dataframe(
            available_flights.head(50),
            use_container_width=True
        )

except Exception as e:
    st.error("An error occurred while running the app.")
    st.exception(e)