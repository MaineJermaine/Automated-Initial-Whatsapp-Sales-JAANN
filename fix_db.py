from app import app, db
from sqlalchemy import text

with app.app_context():
    # This manually adds the missing column to your existing SQLite table
    db.session.execute(text('ALTER TABLE rule ADD COLUMN operation VARCHAR(10) DEFAULT "+" NOT NULL'))
    db.session.commit()
    print("Column added successfully!")