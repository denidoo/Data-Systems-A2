import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent

APP_FILE = PROJECT_ROOT / "app.py"
MODEL_FILE = PROJECT_ROOT / "ml" / "models" / "best_flight_delay_model.pkl"


def run_command(command):
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        shell=True
    )

    return result.returncode == 0


def install_requirements():
    requirements_file = PROJECT_ROOT / "requirements.txt"

    if requirements_file.exists():
        print("\nInstalling requirements...")

        command = f'"{sys.executable}" -m pip install -r "{requirements_file}"'

        success = run_command(command)

        if not success:
            print("Failed to install requirements.")
            return False

    return True


def train_model_if_needed():
    if MODEL_FILE.exists():
        print("\nExisting trained model found.")
        return True

    print("\nNo trained model found.")
    print("Training ML model...")

    command = f'"{sys.executable}" -m ml.model'

    success = run_command(command)

    if not success:
        print("Failed to train ML model.")
        return False

    return True


def start_streamlit():
    print("\nStarting FlightInsight Streamlit app...")

    command = (
        f'"{sys.executable}" -m streamlit run "{APP_FILE}" '
        f'--server.headless true '
        f'--browser.gatherUsageStats false'
    )

    success = run_command(command)

    if not success:
        print("Failed to start Streamlit app.")

    return success


def main():
    print("===================================")
    print("       FlightInsight Startup      ")
    print("===================================")

    if not APP_FILE.exists():
        print("\nError: app.py was not found.")
        return

    requirements_success = install_requirements()

    if not requirements_success:
        return

    model_success = train_model_if_needed()

    if not model_success:
        return

    start_streamlit()


if __name__ == "__main__":
    main()