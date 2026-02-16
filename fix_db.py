import sqlite3
import os

db_path = 'instance/database.db'

def fix_database():
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # List of tables and columns to ensure exist
    # format: (table_name, column_definition)
    changes = [
        ('inquiry', 'customer_id INTEGER'),
        ('chat_session', 'linked_customer_id INTEGER'),
        ('chat_session', 'linked_inquiry_id INTEGER'),
        ('customer', 'created_at TEXT'),
        ('customer', 'created_by TEXT'),
        ('customer', 'updated_at TEXT'),
        ('customer', 'updated_by TEXT')
    ]

    for table, col_def in changes:
        col_name = col_def.split()[0]
        try:
            # Check if column exists
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [c[1] for c in cursor.fetchall()]
            
            if col_name not in columns:
                print(f"Adding column {col_name} to {table}...")
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
                print(f"Successfully added {col_name} to {table}.")
            else:
                print(f"Column {col_name} already exists in {table}.")
        except Exception as e:
            print(f"Error updating {table}.{col_name}: {e}")

    conn.commit()
    conn.close()
    print("Database check and update complete.")

if __name__ == "__main__":
    fix_database()