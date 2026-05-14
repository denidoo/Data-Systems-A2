import streamlit as st
import subprocess
import sys
from pathlib import Path
import pandas as pd

from database.db_config import get_connection


st.set_page_config(
    page_title="FlightInsight Admin",
    page_icon="🛠️",
    layout="wide"
)

st.title("FlightInsight Admin Panel")


# =====================================================
# Helper Functions
# =====================================================

def run_command(command):
    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    return result


@st.cache_data
def load_database_summary():
    conn = get_connection()

    queries = {
        "Flights": "SELECT COUNT(*) FROM fact_flightperformance;",
        "Airlines": "SELECT COUNT(*) FROM dim_airline;",
        "Airports": "SELECT COUNT(*) FROM dim_airport;",
        "Dates": "SELECT COUNT(*) FROM dim_date;"
    }

    results = {}

    for key, query in queries.items():
        results[key] = pd.read_sql(query, conn).iloc[0, 0]

    conn.close()

    return results


# =====================================================
# Database Overview
# =====================================================

st.header("Database Overview")

try:
    summary = load_database_summary()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Flights", f"{summary['Flights']:,}")
    col2.metric("Airlines", f"{summary['Airlines']:,}")
    col3.metric("Airports", f"{summary['Airports']:,}")
    col4.metric("Dates", f"{summary['Dates']:,}")

except Exception as e:
    st.error("Could not load database summary.")
    st.exception(e)


# =====================================================
# Upload Raw Dataset Files
# =====================================================

st.header("Upload Raw Dataset")

uploaded_files = st.file_uploader(
    "Upload CSV files",
    type=["csv"],
    accept_multiple_files=True
)

if uploaded_files:
    raw_data_path = Path("data/raw")
    raw_data_path.mkdir(parents=True, exist_ok=True)

    for uploaded_file in uploaded_files:
        save_path = raw_data_path / uploaded_file.name

        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

    st.success("Files uploaded successfully.")


# =====================================================
# ETL Controls
# =====================================================

st.header("ETL Pipeline")

col1, col2 = st.columns(2)

with col1:

    if st.button("Create Database Tables"):

        with st.spinner("Creating tables..."):

            result = run_command(
                [sys.executable, "create_tables.py"]
            )

        st.code(result.stdout)

        if result.returncode == 0:
            st.success("Tables created successfully.")
        else:
            st.error("Table creation failed.")
            st.code(result.stderr)

with col2:

    if st.button("Run ETL Pipeline"):

        with st.spinner("Running ETL pipeline..."):

            result = run_command(
                [sys.executable, "-m", "etl.etl_run"]
            )

        st.code(result.stdout)

        if result.returncode == 0:
            st.success("ETL completed successfully.")
        else:
            st.error("ETL failed.")
            st.code(result.stderr)


# =====================================================
# Machine Learning Controls
# =====================================================

st.header("Machine Learning")

if st.button("Retrain Prediction Model"):

    with st.spinner("Training model..."):

        result = run_command(
            [sys.executable, "-m", "ml.train_model"]
        )

    st.code(result.stdout)

    if result.returncode == 0:
        st.success("Model trained successfully.")
    else:
        st.error("Model training failed.")
        st.code(result.stderr)


# =====================================================
# Database Table Viewer
# =====================================================

st.header("Database Table Viewer")

table_option = st.selectbox(
    "Select Table",
    [
        "fact_flightperformance",
        "dim_airline",
        "dim_airport",
        "dim_date",
        "dim_time",
        "dim_aircraft",
        "dim_weather_condition",
        "dim_delay_cause"
    ]
)

if st.button("Load Table Data"):

    try:
        conn = get_connection()

        query = f"""
            SELECT *
            FROM {table_option}
            LIMIT 100;
        """

        df = pd.read_sql(query, conn)

        conn.close()

        st.dataframe(
            df,
            use_container_width=True
        )

    except Exception as e:
        st.error("Could not load table data.")
        st.exception(e)


# =====================================================
# Danger Zone
# =====================================================

st.header("Danger Zone")

st.warning(
    "These actions can overwrite or remove data."
)

if st.button("Clear Processed CSV Files"):

    processed_path = Path("data/processed")

    deleted_files = 0

    if processed_path.exists():

        for file in processed_path.glob("*.csv"):
            file.unlink()
            deleted_files += 1

    st.success(f"Deleted {deleted_files} processed CSV files.")