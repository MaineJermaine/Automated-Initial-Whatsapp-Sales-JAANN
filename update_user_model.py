import sqlite3

def upgrade_db():
    try:
        conn = sqlite3.connect('instance/database.db')
        c = conn.cursor()
        
        # Check if column exists
        c.execute("PRAGMA table_info(user)")
        columns = [row[1] for row in c.fetchall()]
        
        if 'last_active_team_chat' not in columns:
            print("Adding last_active_team_chat column to user table...")
            c.execute("ALTER TABLE user ADD COLUMN last_active_team_chat VARCHAR(50)")
            conn.commit()
            print("Column added successfully.")
        else:
            print("Column last_active_team_chat already exists.")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    upgrade_db()
