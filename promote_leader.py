
from app import app, db, User, Team

def update_leader():
    with app.app_context():
        # Find the user
        user = User.query.filter_by(username='252499L').first()
        if not user:
            print("User 252499L not found.")
            return

        # Find the team
        team = Team.query.filter_by(name='JAANN').first()
        # If not found by name, it might be the team_tag? Let's check.
        if not team:
            team = Team.query.filter_by(team_tag='JAANN').first()

        if not team:
            print("Team JAANN not found.")
            return

        # Update user
        user.team_id = team.id
        user.team_role = 'leader'
        
        # Verify if there is already a leader?
        existing_leader = User.query.filter_by(team_id=team.id, team_role='leader').first()
        if existing_leader and existing_leader.id != user.id:
            print(f"Warning: There is already a leader: {existing_leader.username}. Demoting them to member.")
            existing_leader.team_role = 'member'

        db.session.commit()
        print(f"Successfully promoted {user.username} to leader of {team.name}")

if __name__ == "__main__":
    update_leader()
