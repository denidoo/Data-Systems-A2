import subprocess
import sys


def run_command(command):
    print(f"\nRunning: {command}\n")

    result = subprocess.run(command, shell=True)

    if result.returncode != 0:
        print(f"\nCommand failed: {command}")
        sys.exit(result.returncode)


def main():
    run_command("python create_tables.py")
    run_command("python etl_load_data.py")
    run_command("python -m streamlit run app.py")


if __name__ == "__main__":
    main()