from app import app, db, Customer, Inquiry, Rule, Message
import random

def seed_data():
    with app.app_context():
        # 1. Clear existing data so we don't get duplicates
        db.drop_all()
        db.create_all()

        print("Creating fresh database...")

        # --- SEED CUSTOMERS ---
        first_names = ["Alice", "Bob", "Charlie", "Diana", "Ethan", "Fiona", "George", "Hannah"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Garcia"]
        tags_options = ["VIP", "Returning", "New", "Student", "High Value", "Prospect"]
        locations = ["Singapore", "Kuala Lumpur", "New York", "London", "Sydney"]

        customers = []
        for i in range(12):  # Create 12 fake customers
            f = random.choice(first_names)
            l = random.choice(last_names)
            name = f"{f} {l}"
            c = Customer(
                name=name,
                email=f"{f.lower()}.{l.lower()}@example.com",
                phone=f"+65 {random.randint(80000000, 99999999)}",
                location=random.choice(locations),
                assigned_staff=random.choice(["Karina", "Winter", "Giselle"]),
                status=random.choice(["Active", "Pending", "Inactive"]),
                tags=",".join(random.sample(tags_options, random.randint(1, 3))),
                notes="Met at the regional conference last month."
            )
            db.session.add(c)
            customers.append(c)

        # --- SEED RULES (Lead Scoring) ---
        rules = [
            Rule(name="VIP Customer", keywords="VIP, CEO, Director", score=50, operation="+"),
            Rule(name="Budget Alert", keywords="cheap, discount, free", score=20, operation="-"),
            Rule(name="Urgent Inquiry", keywords="asap, immediately, urgent", score=30, operation="+"),
        ]
        for r in rules:
            db.session.add(r)

        # --- SEED INQUIRIES & MESSAGES ---
        for i in range(5):
            cust = random.choice(customers)
            inq = Inquiry(
                customer=cust.name,
                assigned_rep=cust.assigned_staff,
                inquiry_type=random.choice(["Sales", "Support", "Product"]),
                status=random.choice(["New", "In Progress", "Urgent"]),
                description="User is asking about pricing tiers and API integration limits."
            )
            db.session.add(inq)
            db.session.flush() # Gets the ID for the inquiry

            # Add a welcome message to each inquiry
            msg = Message(
                inquiry_id=inq.id,
                sender="System",
                text=f"Welcome {cust.name}! How can we help you today?",
                time="10:00 AM",
                is_agent=True
            )
            db.session.add(msg)

        db.session.commit()
        print("Database Seeded Successfully! 🚀")

if __name__ == "__main__":
    seed_data()