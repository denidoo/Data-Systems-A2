import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
APP_FILE = PROJECT_ROOT / "app.py"


def run_command(command):
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        shell=True
    )
    return result.returncode == 0


def main():
    if not APP_FILE.exists():
        print("Error: app.py was not found in the project root.")
        return

    print("Starting FlightInsight...")

    command = f'"{sys.executable}" -m streamlit run "{APP_FILE}"'

    success = run_command(command)

    if not success:
        print("Failed to start Streamlit app.")


if __name__ == "__main__":
    main()