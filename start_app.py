import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
APP_FILE = PROJECT_ROOT / "app.py"


def main():
    if not APP_FILE.exists():
        print("Error: app.py was not found in the project root.")
        return

    print("Opening FlightInsight app without updating database or models...")

    command = f'"{sys.executable}" -m streamlit run "{APP_FILE}"'

    subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        shell=True
    )


if __name__ == "__main__":
    main()