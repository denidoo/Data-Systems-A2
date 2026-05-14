import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
APP_FILE = PROJECT_ROOT / "app.py"


def run_command(command, step_name):
    print(f"\n--- {step_name} ---")

    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        shell=True
    )

    if result.returncode != 0:
        print(f"\nError: {step_name} failed.")
        sys.exit(result.returncode)


def main():
    if not APP_FILE.exists():
        print("Error: app.py was not found in the project root.")
        return

    print("Starting full FlightInsight setup...")

    run_command(
        f'"{sys.executable}" -m etl.etl_run',
        "Running full ETL pipeline"
    )

    run_command(
        f'"{sys.executable}" -m ml.train_model',
        "Training machine learning model"
    )

    print("\nSetup complete. Opening FlightInsight app...")

    run_command(
        f'"{sys.executable}" -m streamlit run "{APP_FILE}"',
        "Opening Streamlit app"
    )


if __name__ == "__main__":
    main()