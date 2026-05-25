import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
APP_FILE = PROJECT_ROOT / "App.py"


def main():
    if not APP_FILE.exists():
        print("Error: app.py was not found in the project root.")
        return

    print("Starting FlightInsight...")

    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(APP_FILE)],
        cwd=PROJECT_ROOT
    )


if __name__ == "__main__":
    main()