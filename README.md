# FlightInsight

FlightInsight is a Streamlit and PostgreSQL application for storing, processing, and predicting flight delay data.

The project uses:

- Python
- pandas
- PostgreSQL
- SQLAlchemy
- Streamlit
- scikit-learn

---

## Project Structure

FlightInsight/
│
├── app.py
├── admin_data_entry.py
├── create_tables.py
├── db_config.py
├── etl_load_data.py
├── requirements.txt
├── README.md
│
└── data/
    ├── raw/
    │   ├── flights.csv
    │   ├── airlines.csv
    │   └── airports.csv
    │
    ├── processed/
    │   ├── dim_date.csv
    │   ├── dim_time.csv
    │   ├── dim_airport.csv
    │   ├── dim_airline.csv
    │   ├── dim_weather_condition.csv
    │   ├── dim_flight.csv
    │   ├── dim_aircraft.csv
    │   ├── dim_delay_cause.csv
    │   └── fact_flightperformance.csv
    │
    └── manual_uploads/

---

## Run App Procedure

In order to run this program for the first time, complete the following steps with your terminal:
1. "python -m pip install -r requirements.txt"
2. "python run_app.py"
3. If access to the admin site is required for manual data entry or viewing, click into the admin data entry page on the left sidebar of app.

If app has been run recently and database and ML models do not need updating, use "python -m streamlit run start_app.py" to start app.
