import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from sqlalchemy import text

from database.db_config import engine


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
    return subprocess.run(
        command,
        capture_output=True,
        text=True
    )


@st.cache_data(ttl=60)
def load_database_summary():
    queries = {
        "Flights": "SELECT COUNT(*) FROM fact_flightperformance;",
        "Airlines": "SELECT COUNT(*) FROM dim_airline;",
        "Airports": "SELECT COUNT(*) FROM dim_airport;",
        "Dates": "SELECT COUNT(*) FROM dim_date;"
    }

    results = {}

    with engine.connect() as conn:
        for key, query in queries.items():
            results[key] = pd.read_sql(text(query), conn).iloc[0, 0]

    return results


def load_file(uploaded_file):
    file_name = uploaded_file.name.lower()

    if file_name.endswith(".csv"):
        encodings = ["utf-8", "utf-8-sig", "latin1", "cp1252"]

        for encoding in encodings:
            try:
                uploaded_file.seek(0)
                return pd.read_csv(uploaded_file, encoding=encoding)
            except UnicodeDecodeError:
                continue

        raise ValueError("Could not read CSV file. Try saving it as UTF-8 CSV.")

    if file_name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded_file)

    raise ValueError("Only CSV or Excel files are supported.")


def upload_dataframe_to_table(df, table_name):
    with engine.begin() as conn:
        df.to_sql(
            table_name,
            con=conn,
            if_exists="append",
            index=False,
            method="multi"
        )


def load_table_preview(table_name):
    allowed_tables = [
        "fact_flightperformance",
        "dim_airline",
        "dim_airport",
        "dim_date",
        "dim_time",
        "dim_flight",
        "dim_aircraft",
        "dim_weather_condition",
        "dim_delay_cause"
    ]

    if table_name not in allowed_tables:
        raise ValueError("Invalid table selected.")

    query = text(f"""
        SELECT *
        FROM {table_name}
        LIMIT 100;
    """)

    with engine.connect() as conn:
        return pd.read_sql(query, conn)


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
# Upload Data
# =====================================================

st.header("Upload Data to Database")

TABLES = {
    "Dim Airline": "dim_airline",
    "Dim Airport": "dim_airport",
    "Dim Aircraft": "dim_aircraft",
    "Dim Date": "dim_date",
    "Dim Time": "dim_time",
    "Dim Flight": "dim_flight",
    "Dim Weather Condition": "dim_weather_condition",
    "Dim Delay Cause": "dim_delay_cause",
    "Fact Flight Performance": "fact_flightperformance",
}

selected_label = st.selectbox(
    "Choose table to upload into",
    list(TABLES.keys())
)

selected_table = TABLES[selected_label]

uploaded_file = st.file_uploader(
    "Upload CSV or Excel file",
    type=["csv", "xlsx", "xls"]
)

if uploaded_file is not None:
    try:
        df = load_file(uploaded_file)

        st.subheader("Preview")
        st.dataframe(df.head(20), use_container_width=True)

        st.write(f"Rows detected: `{len(df)}`")
        st.write(f"Target table: `{selected_table}`")

        if st.button("Load file into selected table"):
            try:
                upload_dataframe_to_table(df, selected_table)
                st.cache_data.clear()
                st.success(f"Successfully loaded {len(df)} rows into {selected_table}.")
            except Exception as e:
                st.error("Database load failed.")
                st.exception(e)

    except Exception as e:
        st.error("Upload failed.")
        st.exception(e)


# =====================================================
# ETL Controls
# =====================================================

st.header("ETL Pipeline")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("Create Database Tables"):
        with st.spinner("Creating tables..."):
            result = run_command([sys.executable, "create_tables.py"])

        st.code(result.stdout)

        if result.returncode == 0:
            st.cache_data.clear()
            st.success("Tables checked/created successfully.")
        else:
            st.error("Table creation failed.")
            st.code(result.stderr)

with col2:
    if st.button("Run Historical ETL Pipeline"):
        with st.spinner("Running ETL pipeline..."):
            result = run_command([sys.executable, "-m", "etl.etl_run"])

        st.code(result.stdout)

        if result.returncode == 0:
            st.cache_data.clear()
            st.success("ETL completed successfully.")
        else:
            st.error("ETL failed.")
            st.code(result.stderr)

with col3:
    if st.button("Update Data from API"):
        with st.spinner("Updating database from API..."):
            result = run_command([sys.executable, "update_from_api.py"])

        st.code(result.stdout)

        if result.returncode == 0:
            st.cache_data.clear()
            st.success("API update completed successfully.")
        else:
            st.error("API update failed.")
            st.code(result.stderr)


# =====================================================
# Machine Learning Controls
# =====================================================

st.header("Machine Learning")

if st.button("Retrain Prediction Model"):
    with st.spinner("Training model..."):
        result = run_command([sys.executable, "-m", "ml.train_model"])

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
        "dim_flight",
        "dim_aircraft",
        "dim_weather_condition",
        "dim_delay_cause"
    ]
)

if st.button("Load Table Data"):
    try:
        df = load_table_preview(table_option)

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

st.warning("These actions do not delete database tables, but they can remove local files.")

if st.button("Clear Processed CSV Files"):
    processed_path = Path("data/processed")
    deleted_files = 0

    if processed_path.exists():
        for file in processed_path.glob("*.csv"):
            file.unlink()
            deleted_files += 1

    st.success(f"Deleted {deleted_files} processed CSV files.")