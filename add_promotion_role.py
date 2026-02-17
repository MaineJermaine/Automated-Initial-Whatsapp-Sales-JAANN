import sqlite3
import os

def add_promotion_type():
    db_path = 'instance/database.db'
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if target_role column exists
        cursor.execute("PRAGMA table_info(promotion_request)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'target_role' not in columns:
            cursor.execute("ALTER TABLE promotion_request ADD COLUMN target_role TEXT DEFAULT 'super_admin'")
            conn.commit()
            print("Column 'target_role' added successfully to 'promotion_request' table.")
        else:
            print("Column 'target_role' already exists.")
            
    except sqlite3.OperationalError as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_promotion_type()
