import sqlite3
import os

db_path = 'instance/database.db'
if not os.path.exists(db_path):
    db_path = 'database.db' # Fallback for local dev

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print(f"Updating database at {db_path}...")

# 1. Create Team table
cursor.execute('''
CREATE TABLE IF NOT EXISTS team (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    profile_picture TEXT,
    description TEXT,
    role TEXT,
    department TEXT,
    team_score INTEGER DEFAULT 0,
    team_tag TEXT,
    created_at TEXT
)
''')

# 2. Create TeamRequest table
cursor.execute('''
CREATE TABLE IF NOT EXISTS team_request (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    team_id INTEGER,
    requester_id INTEGER NOT NULL,
    type TEXT,
    status TEXT DEFAULT 'pending',
    created_at TEXT,
    FOREIGN KEY(user_id) REFERENCES user(id),
    FOREIGN KEY(team_id) REFERENCES team(id),
    FOREIGN KEY(requester_id) REFERENCES user(id)
)
''')

# 3. Add columns to User table
try:
    cursor.execute('ALTER TABLE user ADD COLUMN team_id INTEGER REFERENCES team(id)')
    print("Added team_id to user table.")
except sqlite3.OperationalError:
    print("team_id already exists in user table.")

try:
    cursor.execute('ALTER TABLE user ADD COLUMN team_role TEXT')
    print("Added team_role to user table.")
except sqlite3.OperationalError:
    print("team_role already exists in user table.")

# 4. Initialize JAANN team
from datetime import datetime
now = datetime.now().strftime('%Y-%m-%d %H:%M')

cursor.execute('SELECT id FROM team WHERE name = "JAANN"')
team = cursor.fetchone()

if not team:
    cursor.execute('''
    INSERT INTO team (name, profile_picture, description, role, department, team_score, team_tag, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        "JAANN",
        "https://ui-avatars.com/api/?name=JAANN&background=6366f1&color=fff",
        "The primary administrative team overseeing system operations.",
        "System Administration",
        "IT & Operations",
        100,
        "CORE",
        now
    ))
    team_id = cursor.lastrowid
    print(f"Created JAANN team with ID {team_id}.")
else:
    team_id = team[0]
    print(f"JAANN team already exists with ID {team_id}.")

# 5. Assign primary account (252499L) as leader
cursor.execute('SELECT id FROM user WHERE username = "252499L"')
user = cursor.fetchone()
if user:
    user_id = user[0]
    cursor.execute('UPDATE user SET team_id = ?, team_role = "leader" WHERE id = ?', (team_id, user_id))
    print(f"Assigned user 252499L as leader of JAANN.")
else:
    print("User 252499L not found, skipping leader assignment.")

conn.commit()
conn.close()
print("Database update complete.")
