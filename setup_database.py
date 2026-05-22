from database.create_tables import create_tables


def main():
    print("Setting up FlightInsight database...")
    create_tables()
    print("Database setup complete.")


if __name__ == "__main__":
    main()