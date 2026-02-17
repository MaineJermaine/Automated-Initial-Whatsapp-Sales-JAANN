import sqlite3
import os

def promote_primary_admin():
    db_path = 'instance/database.db'
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("UPDATE user SET role='ultra_admin' WHERE username='252499L'")
        conn.commit()
        if cursor.rowcount > 0:
            print("Primary admin '252499L' promoted to Ultra Admin successfully.")
        else:
            print("Primary admin '252499L' not found.")
            
    except sqlite3.OperationalError as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    promote_primary_admin()
