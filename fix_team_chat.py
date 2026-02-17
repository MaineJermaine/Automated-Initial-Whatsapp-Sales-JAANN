from app import app, db, TeamMessage
from sqlalchemy import text

with app.app_context():
    try:
        # Check if table exists
        db.session.execute(text('SELECT 1 FROM team_message LIMIT 1'))
        print("Table team_message already exists.")
    except Exception:
        print("Creating table team_message...")
        db.create_all()
        print("Table created.")
