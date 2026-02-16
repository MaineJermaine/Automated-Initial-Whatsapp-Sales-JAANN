import sqlite3

def add_column():
    conn = sqlite3.connect('instance/database.db')
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables:", tables)

    try:
        cursor.execute("ALTER TABLE user ADD COLUMN last_active TEXT")
        conn.commit()
        print("Column 'last_active' added successfully.")
    except sqlite3.OperationalError as e:
        print(f"Error (possibly column exists): {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_column()
