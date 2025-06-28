import sqlite3
import json
import os
import sys

# Adjust this path to your actual database file
DATABASE_PATH = "C:/alpha5/data/mother_brain.db"

# Example of the expected position data structure
example_position_data = {
    "id": "some-id",
    "asset_type": "BTC",
    "position_type": "LONG",
    "entry_price": 100.0,
    "liquidation_price": 90.0,
    "travel_percent": 10.0,
    "value": 5000.0,
    "collateral": 1000.0,
    "size": 0.05,
    "leverage": 5.0,
    "wallet_name": "ExampleWallet",
    "last_updated": "2025-06-22T15:50:00",
    "alert_reference_id": None,
    "hedge_buddy_id": None,
    "current_price": 105.0,
    "liquidation_distance": 5.0,
    "heat_index": 0.5,
    "current_heat_index": 0.5,
    "pnl_after_fees_usd": 250.0,
    "status": "ACTIVE"
    # Add more fields if your real data includes them
}

def fetch_db_schema(db_path, table_name):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name});")
    schema_info = cursor.fetchall()
    conn.close()
    return {row[1] for row in schema_info}

def verify_position_schema(data_sample, db_schema_columns):
    data_fields = set(data_sample.keys())

    missing_columns = data_fields - db_schema_columns
    extra_columns = db_schema_columns - data_fields

    print("\n🔍 Schema Validation Results")
    print("=" * 40)
    
    if missing_columns:
        print(f"❌ Columns in your DATA missing from DB schema:\n  {missing_columns}")
    else:
        print("✅ No missing columns found in DB schema.")

    if extra_columns:
        print(f"⚠️ Columns in DB schema not used in DATA:\n  {extra_columns}")
    else:
        print("✅ No unused columns in DB schema.")

    print("=" * 40)
    return missing_columns, extra_columns

if __name__ == "__main__":
    print(f"🔗 Verifying schema for 'positions' table in {DATABASE_PATH}...\n")

    if not os.path.exists(DATABASE_PATH):
        print(f"❌ Database file not found: {DATABASE_PATH}")
        sys.exit(1)

    schema_columns = fetch_db_schema(DATABASE_PATH, "positions")
    missing_cols, extra_cols = verify_position_schema(example_position_data, schema_columns)

    if missing_cols:
        print("\n🛑 Schema mismatch detected! Update your data or schema before proceeding.")
        sys.exit(1)
    else:
        print("\n✅ Schema check passed successfully! Ready for operations.")
