# manage_learning_db.py
"""
Script to populate, clear, or view learning database with realistic test data.
"""

import random
import uuid
from datetime import datetime, timedelta, timezone

from learning_database.learning_data_locker import LearningDataLocker

# Initialize database instance
locker = LearningDataLocker.get_instance()


def generate_random_position_event():
    return {
        "event_id": str(uuid.uuid4()),
        "position_id": f"POS-{random.randint(1000, 9999)}",
        "trader_name": random.choice(["TraderJoe", "CryptoKing", "RiskyBiz"]),
        "ts": (datetime.now(timezone.utc) - timedelta(minutes=random.randint(0, 1440))).isoformat(),
        "state": random.choice(["ENRICH", "CLOSE", "LIQUIDATE", "IMPORT", "MANUAL_EDIT"]),
        "travel_percent": round(random.uniform(-20, 20), 2),
        "liquidation_distance": round(random.uniform(0, 10), 2),
        "heat_index": round(random.uniform(0, 100), 2),
        "value": round(random.uniform(10, 1000), 2),
        "leverage": round(random.uniform(1, 10), 2),
        "pnl_after_fees": round(random.uniform(-100, 100), 2),
        "is_hedged": random.choice([0, 1]),
        "alert_level": random.choice(["", "LOW", "MEDIUM", "HIGH"]),
    }


def populate_test_data(record_count=100):
    cursor = locker.db.get_cursor()

    for _ in range(record_count):
        event = generate_random_position_event()
        cursor.execute(
            """
            INSERT INTO position_events (
                event_id, position_id, trader_name, ts, state, travel_percent,
                liquidation_distance, heat_index, value, leverage, pnl_after_fees,
                is_hedged, alert_level
            ) VALUES (
                :event_id, :position_id, :trader_name, :ts, :state, :travel_percent,
                :liquidation_distance, :heat_index, :value, :leverage, :pnl_after_fees,
                :is_hedged, :alert_level
            )
            """,
            event,
        )

    locker.db.commit()
    print("✅ Learning database populated with test data!")


def clear_learning_db():
    cursor = locker.db.get_cursor()
    tables = locker.db.list_tables()
    for table in tables:
        cursor.execute(f"DELETE FROM {table}")
    locker.db.commit()
    print("🧹 Learning database cleared successfully!")


def view_database_contents():
    cursor = locker.db.get_cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [table[0] for table in cursor.fetchall()]

    print("\n📋 Tables available in the learning database:")
    for idx, table_name in enumerate(tables, start=1):
        print(f"[{idx}] {table_name}")

    table_choice = input("\nEnter the number of the table to view its contents: ").strip()

    if table_choice.isdigit() and 1 <= int(table_choice) <= len(tables):
        selected_table = tables[int(table_choice) - 1]
        cursor.execute(f"SELECT * FROM {selected_table}")
        rows = cursor.fetchall()

        if not rows:
            print(f"⚠️ Table '{selected_table}' is empty.")
            return

        print(f"\n🔍 Contents of '{selected_table}':")
        for row in rows:
            print(row)
    else:
        print("❌ Invalid selection.")


def main():
    print("🛠️ Learning Database Management")
    print("----------------------------------")
    print("[1] 🚀 Populate test data")
    print("[2] 🧹 Clear database")
    print("[3] 📋 View database contents")
    print("[4] ❌ Exit")

    choice = input("\nEnter your choice (1-4): ").strip()

    if choice == "1":
        count_input = input("Enter number of records to insert (default 100): ").strip()
        count = int(count_input) if count_input.isdigit() else 100
        populate_test_data(count)
    elif choice == "2":
        confirm = input("Are you sure you want to clear the database? (y/N): ").lower()
        if confirm == "y":
            clear_learning_db()
        else:
            print("❌ Operation canceled.")
    elif choice == "3":
        view_database_contents()
    else:
        print("👋 Exiting.")


if __name__ == "__main__":
    main()
