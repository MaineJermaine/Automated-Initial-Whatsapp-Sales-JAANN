from flask import Flask, render_template, request, redirect, url_for, jsonify, make_response, session, has_request_context
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_

app = Flask(__name__)
# Database Configuration - use ENV var if available for Render/Cloud deployment
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Upload Folder Configuration
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', 'static/uploads')
# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
app.secret_key = os.environ.get('SECRET_KEY', 'secure_admin_key_2026')

# --- 1. MODELS (All models must be defined before create_all) ---

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), default='Admin')
    bio = db.Column(db.Text, default='')
    profile_picture = db.Column(db.String(200), default='https://ui-avatars.com/api/?name=Admin&background=random')
    role = db.Column(db.String(20), default='agent') # super_admin, agent
    preferences = db.Column(db.Text, default='{}') # Stores dashboard layout/stats as JSON
    last_active = db.Column(db.String(50))
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    team_role = db.Column(db.String(20)) # leader, vice_leader, member
    last_active_team_chat = db.Column(db.String(50)) # Timestamp of last time user viewed team chat

    @property
    def is_online(self):
        return self.status_display == "Active"

    @property
    def status_display(self):
        if not self.last_active:
            return "Inactive"
        try:
            from datetime import datetime
            last = datetime.strptime(self.last_active, '%Y-%m-%d %H:%M:%S')
            now = datetime.now()
            diff = now - last
            minutes = divmod(diff.total_seconds(), 60)[0]
            
            if minutes < 5:
                return "Active"
            elif minutes < 60:
                return f"Last active {int(minutes)} mins ago"
            elif minutes < 1440:
                return f"Last active {int(minutes // 60)} hours ago"
            else:
                return f"Last active {int(minutes // 1440)} days ago"
        except:
            return "Inactive"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class PromotionRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    target_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending') # pending, approved, rejected
    approvals = db.Column(db.Text, default='[]') # JSON list of user_ids who approved
    created_at = db.Column(db.String(50))
    target_role = db.Column(db.String(20), default='super_admin')
    
    target_user = db.relationship('User', foreign_keys=[target_user_id], backref='promotion_requests')
    requester = db.relationship('User', foreign_keys=[requester_id], backref='sent_promotion_requests')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    profile_picture = db.Column(db.String(255), default='https://ui-avatars.com/api/?name=Team&background=random')
    description = db.Column(db.Text, default='')
    role = db.Column(db.String(50)) # e.g., "Corporate Sales", "Customer Support"
    department = db.Column(db.String(50))
    team_score = db.Column(db.Integer, default=0)
    team_tag = db.Column(db.String(50))
    created_at = db.Column(db.String(50))
    
    # Relationship to members
    members = db.relationship('User', backref='team_obj', foreign_keys='User.team_id', lazy=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class TeamRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True) # nullable if it's a request to leave? No, leave is automatic. 
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(20)) # join, move, invite
    status = db.Column(db.String(20), default='pending') # pending, approved, rejected
    created_at = db.Column(db.String(50))
    
    target_user = db.relationship('User', foreign_keys=[user_id], backref='team_requests')
    target_team = db.relationship('Team', backref='team_requests')
    requester = db.relationship('User', foreign_keys=[requester_id], backref='initiated_team_requests')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class Rule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    keywords = db.Column(db.String(200), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    operation = db.Column(db.String(10), nullable=False, default='+') 
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.String(50))
    created_by = db.Column(db.String(100))
    updated_at = db.Column(db.String(50))
    updated_by = db.Column(db.String(100))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class Inquiry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer = db.Column(db.String(100), nullable=False)
    assigned_rep = db.Column(db.String(50))
    inquiry_type = db.Column(db.String(50))
    status = db.Column(db.String(20), default='New')
    description = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_at = db.Column(db.String(50))
    created_by = db.Column(db.String(100))
    updated_at = db.Column(db.String(50))
    updated_by = db.Column(db.String(100))
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=True)
    
    messages = db.relationship('Message', backref='inquiry', cascade="all, delete-orphan")
    linked_customer = db.relationship('Customer', backref='inquiries')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

def calculate_team_score(team_id):
    """
    Calculate team score based on:
    - Inquiries assigned to team members (status + type points)
    - Chat sessions assigned to team members (6 base + lead score/10)
    """
    import math
    
    team = Team.query.get(team_id)
    if not team:
        return 0
    
    total_score = 0
    
    # Get all team member usernames
    team_members = User.query.filter_by(team_id=team_id).all()
    member_usernames = [m.username for m in team_members]
    member_ids = [m.id for m in team_members]
    
    if not member_usernames:
        return 0
    
    # 1. Calculate score from inquiries
    inquiries = Inquiry.query.filter(Inquiry.assigned_rep.in_(member_usernames)).all()
    
    for inquiry in inquiries:
        # Status points
        status_points = {
            'New': 1,
            'In Progress': 3,
            'Urgent': 5,
            'Resolved': 0
        }.get(inquiry.status, 0)
        
        # Type points
        type_points = {
            'Sales': 4,
            'Support': 2,
            'Product': 3
        }.get(inquiry.inquiry_type, 0)
        
        total_score += status_points + type_points
    
    # 2. Calculate score from chat sessions
    chat_sessions = ChatSession.query.filter(ChatSession.assigned_agent_id.in_(member_ids)).all()
    
    for chat in chat_sessions:
        # Base 6 points per chat
        chat_score = 6
        
        # Check if it's a lead and add lead score / 10 (rounded up)
        if hasattr(chat, 'is_lead') and chat.is_lead:
            lead_score = getattr(chat, 'calculated_score', 0)
            if lead_score > 0:
                chat_score += math.ceil(lead_score / 10)
        else:
            # Calculate if it's a lead using the existing logic
            session_score = calculate_session_score(chat)
            if session_score > 0:
                chat_score += math.ceil(session_score / 10)
        
        total_score += chat_score
    
    return total_score

def calculate_agent_score(user_id):
    """
    Calculate individual agent score based on:
    - Inquiries assigned to the agent (status + type points)
    - Chat sessions assigned to the agent (6 base + lead score/10)
    """
    import math
    
    user = User.query.get(user_id)
    if not user:
        return 0
    
    total_score = 0
    
    # 1. Calculate score from inquiries assigned to this agent
    inquiries = Inquiry.query.filter_by(assigned_rep=user.username).all()
    
    for inquiry in inquiries:
        # Status points
        status_points = {
            'New': 1,
            'In Progress': 3,
            'Urgent': 5,
            'Resolved': 0
        }.get(inquiry.status, 0)
        
        # Type points
        type_points = {
            'Sales': 4,
            'Support': 2,
            'Product': 3
        }.get(inquiry.inquiry_type, 0)
        
        total_score += status_points + type_points
    
    # 2. Calculate score from chat sessions assigned to this agent
    chat_sessions = ChatSession.query.filter_by(assigned_agent_id=user.id).all()
    
    for chat in chat_sessions:
        # Base 6 points per chat
        chat_score = 6
        
        # Check if it's a lead and add lead score / 10 (rounded up)
        session_score = calculate_session_score(chat)
        if session_score > 0:
            chat_score += math.ceil(session_score / 10)
        
        total_score += chat_score
    
    return total_score

@app.before_request
def inject_sidebar_counts():
    if not session.get('logged_in'):
        return

    user_id = session.get('user_id')
    if not user_id:
        return

    # Using g to store temporary globals for templates
    from flask import g
    user = User.query.get(user_id)
    if not user:
        return

    # 1. Pending Join Requests (Leader only)
    g.team_pending_requests_count = 0
    if user.team_id and user.team_role == 'leader':
        g.team_pending_requests_count = TeamRequest.query.filter_by(
            team_id=user.team_id, status='pending', type='join'
        ).count()

    # 2. Unread Team Messages
    g.unread_team_messages = False
    if user.team_id:
        last_read = user.last_active_team_chat
        
        query = TeamMessage.query.filter_by(team_id=user.team_id)
        if last_read:
             query = query.filter(TeamMessage.created_at > last_read)
        
        # Don't count own messages
        query = query.filter(TeamMessage.user_id != user.id)
        
        unread_count = query.count()
        if unread_count > 0:
            g.unread_team_messages = True

@app.context_processor
def context_processor():
    # Make g variables available in templates without 'g.' prefix if desired, 
    # but normally context_processor returns a dict.
    # Let's return them explicitly.
    from flask import g
    return dict(
        team_pending_requests_count=getattr(g, 'team_pending_requests_count', 0),
        unread_team_messages=getattr(g, 'unread_team_messages', False)
    )

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inquiry_id = db.Column(db.Integer, db.ForeignKey('inquiry.id'), nullable=False)
    sender = db.Column(db.String(50))
    text = db.Column(db.Text)
    time = db.Column(db.String(50))
    is_agent = db.Column(db.Boolean, default=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class TeamMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.String(50)) 
    
    user = db.relationship('User', backref='team_messages')
    team = db.relationship('Team', backref='messages')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

# Add this to your models in app.py
class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True)
    phone = db.Column(db.String(20))
    location = db.Column(db.String(100))
    assigned_staff = db.Column(db.String(100))
    status = db.Column(db.String(50), default="Active")
    tags = db.Column(db.String(200)) # Stored as "VIP,New,Returning"
    notes = db.Column(db.Text)
    last_contact = db.Column(db.String(50))
    created_at = db.Column(db.String(50))
    created_by = db.Column(db.String(100))
    updated_at = db.Column(db.String(50))
    updated_by = db.Column(db.String(100))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class AutoReplyTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    usage_count = db.Column(db.Integer, default=0)
    keywords = db.Column(db.Text)  # Stored as comma-separated string
    created_at = db.Column(db.String(50))
    created_by = db.Column(db.String(100))
    updated_at = db.Column(db.String(50))
    updated_by = db.Column(db.String(100))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class FAQ(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(200), nullable=False)
    answer = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    click_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.String(50))
    created_by = db.Column(db.String(100))
    updated_at = db.Column(db.String(50))
    updated_by = db.Column(db.String(100))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class FAQLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    faq_id = db.Column(db.Integer, db.ForeignKey('faq.id'))
    clicked_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), nullable=False, default='normal')  # low, normal, high, urgent
    created_at = db.Column(db.String(50))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class ChatSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visitor_name = db.Column(db.String(100), nullable=False)
    visitor_email = db.Column(db.String(120))
    status = db.Column(db.String(20), default='bot')  # bot, agent_active, closed
    linked_customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=True)
    linked_inquiry_id = db.Column(db.Integer, db.ForeignKey('inquiry.id'), nullable=True)
    created_at = db.Column(db.String(50))
    updated_at = db.Column(db.String(50))
    tags = db.Column(db.String(200), default='')  # comma-separated: impt,waiting,completed
    archived = db.Column(db.Boolean, default=False)
    pinned = db.Column(db.Boolean, default=False)
    assigned_agent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    requested_agent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    transfer_status = db.Column(db.String(20), default='none')  # none, pending
    chat_messages = db.relationship('ChatMessage', backref='session', cascade="all, delete-orphan", order_by='ChatMessage.id')
    linked_customer = db.relationship('Customer', backref='chat_sessions')
    linked_inquiry = db.relationship('Inquiry', backref='chat_sessions')
    assigned_agent = db.relationship('User', foreign_keys=[assigned_agent_id], backref='assigned_chats')
    requested_agent = db.relationship('User', foreign_keys=[requested_agent_id], backref='requested_chats')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_session.id'), nullable=False)
    sender_type = db.Column(db.String(20), nullable=False)  # customer, bot, agent, system
    sender_name = db.Column(db.String(100))
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.String(50))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(30), nullable=False)  # announcement, customer, inquiry, rule
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    icon = db.Column(db.String(10), default='🔔')
    created_by = db.Column(db.String(100), default='System')
    created_at = db.Column(db.String(50))
    is_read = db.Column(db.Boolean, default=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

# Helper to create notifications
# Helper to create notifications
def create_notification(notif_type, title, message, icon='🔔', created_by=None, target_user_id=None, target_roles=None):
    if created_by is None:
        created_by = session.get('user_name', 'System') if has_request_context() else 'System'
    
    from datetime import datetime
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    u_ids = []
    if target_user_id:
        u_ids = [target_user_id]
    elif target_roles:
        # Target specific roles
        users = User.query.filter(User.role.in_(target_roles)).all()
        u_ids = [u.id for u in users]
    else:
        # Broadcast to all registered users
        u_ids = [u.id for u in User.query.all()]
        
    for uid in u_ids:
        # Avoid duplicate notifications if logic overlaps, though set() would require hashable items
        notif = Notification(
            user_id=uid,
            type=notif_type,
            title=title,
            message=message,
            icon=icon,
            created_by=created_by,
            created_at=now
        )
        db.session.add(notif)
    
    db.session.commit()

@app.context_processor
def inject_user_preferences():
    theme = 'light'
    if has_request_context() and 'user_id' in session:
        user_id = session.get('user_id')
        # Avoid database call on static files if possible, but for now simple query
        user = User.query.get(user_id)
        if user and user.preferences:
            try:
                import json
                prefs = json.loads(user.preferences)
                theme = prefs.get('theme', 'light')
            except:
                pass
    return dict(current_theme=theme)

@app.template_filter('from_json')
def from_json_filter(s):
    import json
    try:
        if not s: return []
        return json.loads(s)
    except:
        return []

# Create tables logic
def seed_admin():
    if not User.query.filter_by(username='252499L').first():
        admin = User(
            username='252499L', 
            password=generate_password_hash('fjr1300A15'), 
            name='Admin User', 
            bio='System Administrator',
            role='ultra_admin'
        )
        db.session.add(admin)
        db.session.commit()
    
    # Create the second user account if it doesn't exist
    if not User.query.filter_by(username='252435M').first():
        new_user = User(
            username='252435M',
            password=generate_password_hash('akshaya')
            # name, bio, profile_picture will use defaults
        )
        db.session.add(new_user)
        db.session.commit()

with app.app_context():
    db.create_all()
    seed_admin()

def seed_chat_data():
    """Seed sample chat conversations if none exist."""
    if ChatSession.query.count() > 0:
        return

    from datetime import datetime
    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    # Chat 1 – Ananya asking about pricing (keyword: "pricing")
    s1 = ChatSession(visitor_name='Ananya Ravikumar', visitor_email='ananya.r@gmail.com',
                     status='bot', created_at=now, updated_at=now)
    db.session.add(s1)
    db.session.flush()
    for msg in [
        ('bot', 'Chatbot', 'Hello! 👋 Welcome to our support. How can I help you today?', '12:01 PM'),
        ('customer', 'Ananya Ravikumar', "Hi! I'm interested in the pricing for the premium plan.", '12:02 PM'),
        ('bot', 'Chatbot', "Great question! Our Premium plan starts at $49/month. Would you like more details?", '12:02 PM'),
        ('customer', 'Ananya Ravikumar', "Yes, what features are included? I want to compare it with the enterprise option.", '12:03 PM'),
        ('bot', 'Chatbot', "The Premium plan includes unlimited users, priority support, and advanced analytics. For enterprise pricing, I'd recommend speaking with our sales team.", '12:03 PM'),
        ('customer', 'Ananya Ravikumar', "That sounds good. Can I get a demo scheduled?", '12:05 PM'),
        ('bot', 'Chatbot', "Absolutely! I can help you schedule a demo. Could you share your preferred date and time?", '12:05 PM'),
    ]:
        db.session.add(ChatMessage(session_id=s1.id, sender_type=msg[0], sender_name=msg[1], text=msg[2], timestamp=msg[3]))

    # Chat 2 – Marcus with a complaint
    s2 = ChatSession(visitor_name='Marcus Chen', visitor_email='marcus.chen@outlook.com',
                     status='bot', created_at=now, updated_at=now)
    db.session.add(s2)
    db.session.flush()
    for msg in [
        ('bot', 'Chatbot', 'Hello! How can I assist you today?', '11:30 AM'),
        ('customer', 'Marcus Chen', "I have an issue with my recent invoice. I was overcharged.", '11:31 AM'),
        ('bot', 'Chatbot', "I'm sorry to hear that. Could you provide your invoice number so I can look into it?", '11:31 AM'),
        ('customer', 'Marcus Chen', "It's INV-2024-0892. I was charged twice for the same service.", '11:32 AM'),
        ('bot', 'Chatbot', "Thank you for providing that. Let me check our records... I can see the duplicate charge. Let me connect you with our billing team for a refund.", '11:33 AM'),
        ('customer', 'Marcus Chen', "Thanks. I'd also like to upgrade my subscription while we're at it.", '11:34 AM'),
    ]:
        db.session.add(ChatMessage(session_id=s2.id, sender_type=msg[0], sender_name=msg[1], text=msg[2], timestamp=msg[3]))

    # Chat 3 – Priya asking about integration (keyword: "integration")
    s3 = ChatSession(visitor_name='Priya Sharma', visitor_email='priya.sharma@techcorp.io',
                     status='bot', created_at=now, updated_at=now)
    db.session.add(s3)
    db.session.flush()
    for msg in [
        ('bot', 'Chatbot', 'Welcome! How can I help you today?', '10:15 AM'),
        ('customer', 'Priya Sharma', "Hi, I need help with API integration for our platform.", '10:16 AM'),
        ('bot', 'Chatbot', "Of course! We support REST APIs with full documentation. What platform are you integrating with?", '10:16 AM'),
        ('customer', 'Priya Sharma', "We use Salesforce. Do you have a direct integration?", '10:17 AM'),
        ('bot', 'Chatbot', "Yes! We have a native Salesforce integration. I can share the setup guide with you.", '10:17 AM'),
        ('customer', 'Priya Sharma', "That would be great. Also, what about the pricing for the API access?", '10:19 AM'),
        ('bot', 'Chatbot', "API access is included in our Professional and Enterprise plans. Would you like to discuss pricing options?", '10:19 AM'),
        ('customer', 'Priya Sharma', "Yes please. We're looking at an enterprise deal for 200+ users.", '10:20 AM'),
    ]:
        db.session.add(ChatMessage(session_id=s3.id, sender_type=msg[0], sender_name=msg[1], text=msg[2], timestamp=msg[3]))

    # Chat 4 – Jake just browsing (short chat)
    s4 = ChatSession(visitor_name='Jake Thompson', visitor_email='jake.t@email.com',
                     status='bot', created_at=now, updated_at=now)
    db.session.add(s4)
    db.session.flush()
    for msg in [
        ('bot', 'Chatbot', 'Hello! Welcome. How can I assist you?', '9:45 AM'),
        ('customer', 'Jake Thompson', "Just browsing for now. What products do you offer?", '9:46 AM'),
        ('bot', 'Chatbot', "We offer CRM solutions, marketing automation, and analytics tools. Would you like to learn more about any of these?", '9:46 AM'),
        ('customer', 'Jake Thompson', "Maybe later. Thanks!", '9:47 AM'),
    ]:
        db.session.add(ChatMessage(session_id=s4.id, sender_type=msg[0], sender_name=msg[1], text=msg[2], timestamp=msg[3]))

    # Chat 5 – Sara interested in a demo and partnership (keywords: "demo", "partnership")
    s5 = ChatSession(visitor_name='Sara Williams', visitor_email='sara.w@innovate.co',
                     status='bot', created_at=now, updated_at=now)
    db.session.add(s5)
    db.session.flush()
    for msg in [
        ('bot', 'Chatbot', 'Hi there! 👋 How can I help you today?', '2:00 PM'),
        ('customer', 'Sara Williams', "Hello! I'd like to schedule a demo of your platform.", '2:01 PM'),
        ('bot', 'Chatbot', "We'd love to show you around! Are you looking at this for your team or organization?", '2:01 PM'),
        ('customer', 'Sara Williams', "For our organization. We're also interested in a potential partnership opportunity.", '2:02 PM'),
        ('bot', 'Chatbot', "That's exciting! Partnership inquiries are handled by our business development team. Let me get someone who can help.", '2:03 PM'),
        ('customer', 'Sara Williams', "Great. We have about 500 employees and need an enterprise solution with custom pricing.", '2:04 PM'),
        ('bot', 'Chatbot', "Understood! For enterprise deals of that scale, I'll connect you with a dedicated account manager. Please hold.", '2:04 PM'),
    ]:
        db.session.add(ChatMessage(session_id=s5.id, sender_type=msg[0], sender_name=msg[1], text=msg[2], timestamp=msg[3]))

    db.session.commit()

with app.app_context():
    seed_chat_data()

@app.context_processor
def inject_pending_counts():
    if not session.get('logged_in'): 
        return {}
    
    import json
    # Pending promotions for the UI (notifications badge)
    pending_count = PromotionRequest.query.filter_by(status='pending').count()
    
    # Check if the current user has a pending promotion request (Requirement: account itself able to see pending promotion)
    my_id = session.get('user_id')
    if my_id:
        try:
            my_id = int(my_id)
        except:
            pass
            
    my_user = User.query.get(my_id) if my_id else None
    
    # Check if the current user has a pending promotion request
    my_promotion = PromotionRequest.query.filter_by(target_user_id=my_id, status='pending').first() if my_id else None
    
    my_promotion_data = None
    if my_promotion:
        # Calculate how many have approved
        approvals = json.loads(my_promotion.approvals)
        # Total super admins needed
        sa_count = User.query.filter_by(role='super_admin').count()
        my_promotion_data = {
            'role': my_promotion.target_role.replace('_', ' ').title(),
            'approvals': len(approvals),
            'total_needed': sa_count
        }

    # Team request counts for leaders
    team_pending_requests_count = 0
    if my_user and my_user.team_id and my_user.team_role in ['leader', 'vice_leader']:
        team_pending_requests_count = TeamRequest.query.filter_by(team_id=my_user.team_id, status='pending').count()

    # Chat transfer requests for the current user (Assigned TO me, requested by someone else)
    transfer_request_count = ChatSession.query.filter_by(assigned_agent_id=my_id, transfer_status='pending').count() if my_id else 0

    return dict(
        pending_promotion_count=pending_count, 
        my_promotion=my_promotion_data,
        team_pending_requests_count=team_pending_requests_count,
        transfer_request_count=transfer_request_count,
        my_team_id=my_user.team_id if my_user else None,
        my_team_role=my_user.team_role if my_user else None,
        my_user=my_user
    )

@app.context_processor
def inject_search_data():
    # 1. Fetch all data from your SQLite tables
    customers = Customer.query.all()
    inquiries = Inquiry.query.all()
    rules = Rule.query.all()
    templates = AutoReplyTemplate.query.all()
    faqs = FAQ.query.all()
    
    # 2. Format them into a list the Search Bar understands
    search_seed = []
    
    for c in customers:
        search_seed.append({"display": c.name, "category": "Customer", "page": "/customers"})
        
    for i in inquiries:
        # We search by the customer name inside the inquiry
        search_seed.append({"display": f"Inquiry: {i.customer}", "category": "Inquiry", "page": f"/inquiry/{i.id}"})
        
    for r in rules:
        search_seed.append({"display": r.name, "category": "Rule", "page": "/scoring"})
    
    for t in templates:
        search_seed.append({"display": t.title, "category": "Template", "page": "/templates-manager"})
    
    for f in faqs:
        search_seed.append({"display": f.question, "category": "FAQ", "page": "/templates-manager"})
        
    return dict(search_seed=search_seed)

def get_tags_inventory():
    tag_colors = {
        'VIP': '#f59e0b',
        'New': '#10b981',
        'Returning': '#3b82f6',
        'Hot Lead': '#ef4444',
        'Cold Lead': '#6b7280',
        'Premium': '#8b5cf6',
        'Enterprise': '#ec4899'
    }

    # Start with defaults so inventory is never empty
    tags_inventory = dict(tag_colors)

    customers = Customer.query.all()

    for c in customers:
        if c.tags:
            for tag in c.tags.split(','):
                tag = tag.strip()
                if tag:
                    # Preserve default color if present, otherwise add with gray
                    tags_inventory.setdefault(tag, tag_colors.get(tag, '#94a3b8'))

    return tags_inventory

# --- 2. ROUTES ---

def calculate_session_score(session):
    score = 0
    # Consolidate visitor messages
    visitor_text = " ".join([m.text.lower() for m in session.chat_messages if m.sender_type == 'customer'])
    
    active_rules = Rule.query.filter_by(active=True).all()
    
    for rule in active_rules:
        # Check rule match
        keywords = [k.strip().lower() for k in rule.keywords.split(',') if k.strip()]
        if not keywords: continue
        
        # If ANY keyword in visitor text
        if any(k in visitor_text for k in keywords):
            try:
                val = int(rule.score)
                op = rule.operation
                # Robustly handle symbol ('+') vs verbose ('Add (+)') formats
                if '+' in op: score += val
                elif '-' in op: score -= val
                elif '*' in op: score *= val
                elif '/' in op: 
                    if val != 0: score /= val
            except:
                pass
    return score

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user:
            # Support both hashed and legacy plain text passwords during transition
            is_valid = False
            try:
                if check_password_hash(user.password, password):
                    is_valid = True
            except:
                pass # Not a hash
            
            if not is_valid and user.password == password:
                is_valid = True
                # Optional: Upgrade to hash on successful login? 
                # user.password = generate_password_hash(password)
                # db.session.commit()

            if is_valid:
                session['logged_in'] = True
                session['user_id'] = user.id
                session['user_name'] = user.name
                session['user_pic'] = user.profile_picture
                session['user_role'] = user.role or 'agent'
                session['user_username'] = user.username
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', error="Invalid credentials")
        else:
            return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/logout')
def logout():
    # Set user as inactive before clearing session
    if session.get('user_id'):
        user = User.query.get(session.get('user_id'))
        if user:
            user.last_active = None
            db.session.commit()
            
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin/create-account', methods=['GET', 'POST'])
def admin_create_account():
    # Only 252499L or someone with super_admin role can access
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    current_user = User.query.get(session.get('user_id'))
    # Allow 'admin' role to view the page, but creation will be restricted
    if current_user.username != '252499L' and current_user.role not in ['super_admin', 'admin']:
        return render_template('404.html'), 404

    if request.method == 'POST':
        # Only super_admin or ultra_admin can create accounts
        if current_user.role not in ['super_admin', 'ultra_admin']:
             return render_template('403.html'), 403
             
        username = request.form.get('username')
        password = request.form.get('password')
        name = request.form.get('name')
        bio = request.form.get('bio')
        role = request.form.get('role', 'agent')
        
        # Prepare context variables for possible re-rendering
        all_users = User.query.all()
        all_teams = Team.query.all()
        promotion_requests = []
        total_super_admins = 0
        if current_user.role in ['super_admin', 'ultra_admin']:
            promotion_requests = PromotionRequest.query.filter_by(status='pending').all()
            total_super_admins = User.query.filter_by(role='super_admin').count()

        # Check if username exists
        if User.query.filter_by(username=username).first():
            return render_template('create_account.html', 
                                   error="Username already exists",
                                   users=all_users,
                                   teams=all_teams,
                                   promotion_requests=promotion_requests,
                                   total_super_admins=total_super_admins)

        # Handle profile picture
        profile_pic_filename = None
        file = request.files.get('profile_picture')
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            unique_filename = f"profile_{username}_{int(datetime.now().timestamp())}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
            profile_pic_filename = unique_filename

        # Create user
        new_user = User(
            username=username,
            password=generate_password_hash(password),
            name=name,
            bio=bio,
            role=role
        )
        if profile_pic_filename:
            new_user.profile_picture = profile_pic_filename
        
        db.session.add(new_user)
        db.session.commit()
        
        # Notification logic
        notify_roles = ['super_admin', 'ultra_admin']
        create_notification(
            'account', 
            'New Account Created', 
            f"{current_user.role.replace('_', ' ').title()} {current_user.name} created a new account for {username} ({role}).", 
            target_roles=notify_roles
        )
        
        return render_template('create_account.html', 
                               success=f"Account for {username} created successfully!", 
                               users=User.query.all(),
                               teams=all_teams,
                               promotion_requests=promotion_requests,
                               total_super_admins=total_super_admins)



    # Fetch pending promotion requests for super_admins
    promotion_requests = []
    total_super_admins = 0
    if current_user.role in ['super_admin', 'ultra_admin']:
        promotion_requests = PromotionRequest.query.filter_by(status='pending').all()
        total_super_admins = User.query.filter_by(role='super_admin').count()

    return render_template('create_account.html', 
                           users=User.query.all(), 
                           teams=Team.query.all(),
                           promotion_requests=promotion_requests, 
                           total_super_admins=total_super_admins,
                           me=current_user)

@app.route('/admin/delete-account/<int:user_id>', methods=['POST'])
def admin_delete_account(user_id):
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    current_user = User.query.get(session.get('user_id'))
    if current_user.role not in ['ultra_admin', 'super_admin', 'admin']:
        return jsonify({'error': 'Forbidden'}), 403

    user_to_delete = User.query.get_or_404(user_id)
    
    # Ultra Admin can delete their own account BUT only if they already transferred the role
    if user_to_delete.id == current_user.id:
        if current_user.role == 'ultra_admin':
            # Check if there is another ultra_admin (meaning they transferred the role)
            # Actually, the logic should be: if role is ultra_admin and count is 1, they CANNOT delete.
            ultra_admin_count = User.query.filter_by(role='ultra_admin').count()
            if ultra_admin_count == 1:
                return jsonify({'error': 'Ultra Admin must transfer role to another account before deleting their own account'}), 400
        else:
            return jsonify({'error': 'You cannot delete your own account'}), 400
    
    # Prevent deletion of primary admin (if not ultra admin)
    if user_to_delete.username == '252499L' and current_user.role != 'ultra_admin':
        return jsonify({'error': 'Primary admin account cannot be deleted'}), 400

    # Role-specific deletion rules
    if current_user.role == 'ultra_admin':
        # Ultra Admin can delete ANYTHING except themselves (without transfer)
        pass
    elif current_user.role == 'super_admin':
        # Super admin cannot delete other super admins or ultra admin
        if user_to_delete.role in ['super_admin', 'ultra_admin']:
            return jsonify({'error': 'Super Admins cannot delete other Super Admins or the Ultra Admin'}), 403
            
    elif current_user.role == 'admin':
        # Admin can ONLY delete agents (cannot delete admins, super_admins, ultra_admins)
        if user_to_delete.role in ['super_admin', 'admin', 'ultra_admin']:
             return jsonify({'error': 'Admins cannot delete Super Admins, Ultra Admins or other Admins'}), 403

    db.session.delete(user_to_delete)
    db.session.commit()
    
    # Notification logic
    notify_roles = ['super_admin'] if current_user.role in ['super_admin', 'ultra_admin'] else ['super_admin', 'admin']
    create_notification(
        'account', 
        'Account Deleted', 
        f"{current_user.name} ({current_user.role}) deleted the account of {user_to_delete.username}.", 
        target_roles=notify_roles
    )
    
    return jsonify({'success': True})

@app.route('/api/admin/user/<int:user_id>')
def api_admin_get_user(user_id):
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = User.query.get_or_404(user_id)
    
    # Calculate agent score
    agent_score = calculate_agent_score(user.id)
    
    return jsonify({
        'id': user.id,
        'username': user.username,
        'name': user.name,
        'role': user.role,
        'bio': user.bio,
        'profile_picture': user.profile_picture,
        'team_id': user.team_id,
        'team_role': user.team_role,
        'team_name': user.team_obj.name if user.team_obj else None,
        'team_pic': user.team_obj.profile_picture if user.team_obj else None,
        'team_tag': user.team_obj.team_tag if user.team_obj else None,
        'agent_score': agent_score
    })

@app.route('/admin/edit-account/<int:user_id>', methods=['POST'])
def admin_edit_account(user_id):
    if not session.get('logged_in') or session.get('user_role') not in ['ultra_admin', 'super_admin', 'admin']:
        return redirect(url_for('login'))
    
    current_user_role = session.get('user_role')
    user = User.query.get_or_404(user_id)
    
    # Admin Permission Check: Admins can only edit agents
    if current_user_role == 'admin' and user.role != 'agent':
        # Flash message usage would be better, but simple 403 string for now
        return "Forbidden: Admins can only edit Agent accounts", 403

    user.name = request.form.get('name')
    
    # Notification Setup
    changes_summary = []
    
    if user.name != request.form.get('name'):
        changes_summary.append("name")
    
    # Only Super Admin can change roles
    new_role = request.form.get('role')
    
    if (current_user_role in ['super_admin', 'ultra_admin']) and new_role and new_role != user.role:
        # Check for Promotion Request logic
        if new_role in ['super_admin', 'ultra_admin']:
            # Promotions/Transfers need approval from ALL Super Admins
            # (Ultra Admin also needs approval from Super Admins for a transfer)
            
            # Special check for Ultra Admin: only ONE allowed
            if new_role == 'ultra_admin':
                if current_user_role != 'ultra_admin':
                    return "Forbidden: Only an Ultra Admin can promote someone else to Ultra Admin.", 403
                
                # Check for existing pending ultra_admin requests
                existing_ultra_req = PromotionRequest.query.filter_by(target_role='ultra_admin', status='pending').first()
                if existing_ultra_req:
                    return render_template('create_account.html', 
                                           error="A transfer of Ultra Admin role is already in progress.", 
                                           users=User.query.all(),
                                           teams=Team.query.all(),
                                           promotion_requests=PromotionRequest.query.filter_by(status='pending').all())

            # Get all super admins
            super_admins = User.query.filter_by(role='super_admin').all()
            
            # If there are OTHER super admins, we need approval
            # Note: Approvals are needed for ANY promotion to super_admin or ultra_admin
            if len(super_admins) > 0:
                # Need approval process
                # Check if request already exists
                existing_req = PromotionRequest.query.filter_by(target_user_id=user.id, status='pending').first()
                if not existing_req:
                    # Create request
                    req = PromotionRequest(
                        target_user_id=user.id,
                        requester_id=session.get('user_id'),
                        target_role=new_role,
                        status='pending',
                        approvals=json.dumps([session.get('user_id')]), # Using json dumps for list
                        created_at=datetime.now().strftime('%Y-%m-%d %H:%M')
                    )
                    db.session.add(req)
                    
                    # Notify ALL super admins
                    notif_title = 'Ultra Admin Transfer' if new_role == 'ultra_admin' else 'Promotion - Approval Needed'
                    notif_msg = f"Ultra Admin {session.get('user_name')} requested to transfer role to {user.name}." if new_role == 'ultra_admin' else f"{session.get('user_name')} requested to promote {user.name} to Super Admin."
                    
                    create_notification(
                        'account', 
                        notif_title, 
                        notif_msg, 
                        target_roles=['super_admin']
                    )
                    
                    db.session.commit()
                    return render_template('create_account.html', 
                                           info=f"Promotion request created for {user.name}. Waiting for approval from Super Admins.", 
                                           users=User.query.all(),
                                           teams=Team.query.all(),
                                           promotion_requests=PromotionRequest.query.filter_by(status='pending').all())
                else:
                    return render_template('create_account.html', 
                                           error=f"A request for {user.name} is already pending.", 
                                           users=User.query.all(),
                                           teams=Team.query.all(),
                                           promotion_requests=PromotionRequest.query.filter_by(status='pending').all())
            else:
                 changes_summary.append(f"role to {new_role}")
                 user.role = new_role
        else:
             changes_summary.append(f"role to {new_role}")
             user.role = new_role
    
    user.bio = request.form.get('bio')
    
    new_password = request.form.get('password')
    if new_password:
        user.password = generate_password_hash(new_password)
        changes_summary.append("password")
        
    file = request.files.get('profile_picture')
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        unique_filename = f"profile_{user.username}_{int(datetime.now().timestamp())}_{filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
        user.profile_picture = unique_filename
        changes_summary.append("profile picture")
        
    db.session.commit()
    
    # Send Notification if there were changes
    # Note: We simply notify that an update occurred
    if True: # Notify on any edit save
        notify_roles = ['super_admin'] if current_user_role in ['ultra_admin', 'super_admin'] else ['super_admin', 'admin']
        create_notification(
            'account',
            'Account Updated',
            f"{session.get('user_name')} updated account details for {user.username}.",
            target_roles=notify_roles
        )

    return redirect(url_for('admin_create_account'))

@app.route('/admin/approve-promotion/<int:req_id>', methods=['POST'])
def approve_promotion(req_id):
    if not session.get('logged_in') or session.get('user_role') != 'super_admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    req = PromotionRequest.query.get_or_404(req_id)
    current_uid = session.get('user_id')
    import json
    
    approvals = json.loads(req.approvals)
    if current_uid not in approvals:
        approvals.append(current_uid)
        req.approvals = json.dumps(approvals)
        
        # Get all current super admins
        all_super_admins = User.query.filter_by(role='super_admin').all()
        all_sa_ids = set([u.id for u in all_super_admins])
        approved_ids = set(approvals)
        
        # Check if ALL current super admins have approved
        if all_sa_ids.issubset(approved_ids):
            # Promote!
            req.status = 'approved'
            old_role = req.target_user.role
            new_role = req.target_role or 'super_admin'
            
            # If target role is ultra_admin, demote the current ultra_admin
            if new_role == 'ultra_admin':
                 current_ua = User.query.filter_by(role='ultra_admin').first()
                 if current_ua:
                     current_ua.role = 'super_admin'
            
            req.target_user.role = new_role
            
            # Notify everyone
            create_notification(
                'account',
                'Promotion Approved',
                f"{req.target_user.name} has been promoted to {new_role.replace('_', ' ').title()}!",
                target_roles=['super_admin', 'admin']
            )
            
            # Nofity the account itself (Requirement: Account notified of promotion with congratulations)
            create_notification(
                'account',
                '🎉 Congratulations!',
                f"You have been successfully promoted to {new_role.replace('_', ' ').title()}! Check your new permissions.",
                target_user_id=req.target_user.id,
                icon='🎊'
            )
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Approval recorded'})
    
    return jsonify({'success': True, 'message': 'Already approved'})

@app.route('/admin/reject-promotion/<int:req_id>', methods=['POST'])
def reject_promotion(req_id):
    if not session.get('logged_in') or session.get('user_role') != 'super_admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    req = PromotionRequest.query.get_or_404(req_id)
    req.status = 'rejected'
    db.session.commit()
    
    create_notification(
        'account',
        'Promotion Rejected',
        f"Promotion request for {req.target_user.name} was rejected.",
        target_roles=['super_admin']
    )
    
    return jsonify({'success': True})

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    user_id = session.get('user_id')
    if not user_id:
        session.clear()
        return redirect(url_for('login'))
        
    user = User.query.get(user_id)
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        user.name = request.form.get('name')
        user.bio = request.form.get('bio')
        
        # Password change
        new_pass = request.form.get('new_password')
        confirm_pass = request.form.get('confirm_password')
        if new_pass:
            if new_pass == confirm_pass:
                user.password = generate_password_hash(new_pass)
            else:
                return render_template('edit_profile.html', user=user, error="Passwords do not match")
        
        # Profile Picture
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                # Save to specific folder
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                user.profile_picture = filename # Store filename only
                
        db.session.commit()
        
        # Update session data
        session['user_name'] = user.name
        session['user_pic'] = user.profile_picture
        
        return redirect(url_for('profile'))
    
    # Calculate individual agent score
    agent_score = calculate_agent_score(user.id)
        
    return render_template('edit_profile.html', user=user, agent_score=agent_score)

@app.before_request
def require_login():
    allowed_routes = ['login', 'static']
    if request.endpoint and request.endpoint not in allowed_routes and not session.get('logged_in'):
        # For API endpoints, return JSON error instead of redirect
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Unauthorized'}), 401
        return redirect(url_for('login'))
    
    if session.get('logged_in') and session.get('user_id'):
        user = User.query.get(session.get('user_id'))
        if user:
            # Update last active
            try:
                user.last_active = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                db.session.commit()
            except:
                pass
                
            session['user_role'] = user.role
            session['team_id'] = user.team_id
            session['user_name'] = user.name
            session['user_pic'] = user.profile_picture

@app.route('/')
@app.route('/dashboard')
def dashboard():
    all_rules = Rule.query.all()
    all_inquiries = Inquiry.query.all()
    all_announcements = Announcement.query.order_by(Announcement.id.desc()).all()
    
    # Latest Chats
    latest_chats = ChatSession.query.filter_by(archived=False).order_by(ChatSession.updated_at.desc()).limit(5).all()
    
    # High Value Leads
    all_sessions = ChatSession.query.all()
    scored_sessions = []
    for s in all_sessions:
        score = calculate_session_score(s)
        s.calculated_score = score # Attach for template
        scored_sessions.append(s)
        
    scored_sessions.sort(key=lambda x: x.calculated_score, reverse=True)
    high_value_leads = scored_sessions[:3] # User asked for High Value sections... template says Top 3
    
    # Filter for actively scored leads only
    active_leads = [s for s in scored_sessions if s.calculated_score > 0]

    return render_template('admin_dashboard_main_hub.html', 
                           all_rules=all_rules, 
                           all_inquiries=all_inquiries,
                           all_announcements=all_announcements,
                           latest_chats=latest_chats,
                           high_value_leads=high_value_leads,
                           all_leads=active_leads)

@app.route('/api/dashboard/stats')
def dashboard_stats():
    """Returns all stat values and graph data for the customizable dashboard."""
    from datetime import datetime, timedelta
    now_dt = datetime.utcnow()
    seven_days_ago = now_dt - timedelta(days=7)

    faq_clicks_7d = FAQLog.query.filter(FAQLog.clicked_at >= seven_days_ago).count()

    total_customers = Customer.query.count()
    active_inquiries = Inquiry.query.filter(Inquiry.status != 'Resolved').count()
    total_inquiries = Inquiry.query.count()
    total_rules = Rule.query.count()
    active_rules = Rule.query.filter_by(active=True).count()
    total_templates = AutoReplyTemplate.query.count()
    total_faqs = FAQ.query.count()
    total_announcements = Announcement.query.count()

    # --- Fetch Real Inquiry Status Data ---
    inq_status_counts = db.session.query(Inquiry.status, db.func.count(Inquiry.id)).group_by(Inquiry.status).all()
    
    inq_labels = []
    inq_data = []
    inq_colors = []
    
    # Color mapping matching the previous design
    status_colors = {
        "New": "#44BBA4",       # Teal
        "In Progress": "#f59e0b", # Orange
        "Resolved": "#3F88C5",  # Blue
        "Urgent": "#E94F37"     # Red
    }
    
    for status, count in inq_status_counts:
        status_label = status if status else "Unknown"
        inq_labels.append(status_label)
        inq_data.append(count)
        inq_colors.append(status_colors.get(status_label, "#94a3b8")) # Gray if unknown status

    # Handle empty case
    if not inq_data:
        inq_labels = ["No Data"]
        inq_data = [0]
        inq_colors = ["#e2e8f0"]

    return jsonify({
        "solid_stats": [
            {"key": "total_customers", "label": "Total Customers", "value": total_customers, "icon": "👥", "color": "#3F88C5"},
            {"key": "active_inquiries", "label": "Active Inquiries", "value": active_inquiries, "icon": "📩", "color": "#E94F37"},
            {"key": "total_inquiries", "label": "Total Inquiries", "value": total_inquiries, "icon": "📋", "color": "#44BBA4"},
            {"key": "scoring_rules", "label": "Scoring Rules", "value": f"{active_rules} / {total_rules}", "icon": "⚡", "color": "#a855f7"},
            {"key": "templates_count", "label": "Reply Templates", "value": total_templates, "icon": "💬", "color": "#f59e0b"},
            {"key": "faq_count", "label": "FAQs Published", "value": total_faqs, "icon": "❓", "color": "#06b6d4"},
            {"key": "faq_clicks_7d", "label": "FAQ Clicks (7d)", "value": faq_clicks_7d, "icon": "📊", "color": "#f43f5e"},
            {"key": "conversion_rate", "label": "Conversion Rate", "value": "24.8%", "icon": "📈", "color": "#10b981"},
            {"key": "avg_response", "label": "Avg Response Time", "value": "2.4 min", "icon": "⏱️", "color": "#ec4899"},
        ],
        "graphs": [
            {
                "key": "leads_7d",
                "label": "Leads (Past 7 Days)",
                "type": "line",
                "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                "datasets": [{"label": "Leads", "data": [12, 19, 15, 25, 22, 30, 28], "borderColor": "#3F88C5", "backgroundColor": "rgba(63,136,197,0.1)"}]
            },
            {
                "key": "inquiry_status",
                "label": "Inquiry Status Breakdown",
                "type": "doughnut",
                "labels": inq_labels,
                "datasets": [{"label": "Inquiries", "data": inq_data, "backgroundColor": inq_colors}]
            },
            {
                "key": "customer_growth",
                "label": "Customer Growth (6 Months)",
                "type": "bar",
                "labels": ["Sep", "Oct", "Nov", "Dec", "Jan", "Feb"],
                "datasets": [{"label": "New Customers", "data": [8, 14, 11, 19, 23, 17], "backgroundColor": "#a855f7"}]
            },
            {
                "key": "response_time",
                "label": "Avg Response Time (7 Days)",
                "type": "line",
                "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                "datasets": [{"label": "Minutes", "data": [3.2, 2.8, 4.1, 2.1, 1.9, 3.5, 2.4], "borderColor": "#ec4899", "backgroundColor": "rgba(236,72,153,0.1)"}]
            }
        ]
    })

@app.route('/customers')
def customers():
    # Tag color mapping
    tag_colors = {
        'VIP': '#f59e0b',
        'New': '#10b981',
        'Returning': '#3b82f6',
        'Hot Lead': '#ef4444',
        'Cold Lead': '#6b7280',
        'Premium': '#8b5cf6',
        'Enterprise': '#ec4899'
    }
    
    # Get all unique tags from customers for the filter
    all_customers_for_tags = Customer.query.all()
    tags_inventory = {}
    for c in all_customers_for_tags:
        if c.tags:
            for tag in c.tags.split(','):
                tag = tag.strip()
                if tag and tag not in tags_inventory:
                    tags_inventory[tag] = tag_colors.get(tag, '#94a3b8')
    
    # Get filter parameters
    selected_tags = request.args.getlist('tags')
    last_contact_filter = request.args.get('last_contact', '')
    page = request.args.get('page', 1, type=int)
    per_page = 8
    
    # Build query
    query = Customer.query
    
    # Filter by tags
    if selected_tags:
        # Filter customers that have at least one of the selected tags
        tag_filters = []
        for tag in selected_tags:
            tag_filters.append(Customer.tags.like(f'%{tag}%'))
        query = query.filter(or_(*tag_filters))
    
    # Filter by last contact date
    if last_contact_filter:
        query = query.filter(Customer.last_contact == last_contact_filter)
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    customers_list = pagination.items
    
    # Get all customers for the directory table (unpaginated)
    all_customers = Customer.query.all()
    
    return render_template(
        'customer-list.html',
        customers=customers_list,
        pagination=pagination,
        tags_inventory=get_tags_inventory(),
        tag_colors=tag_colors,
        selected_tags=selected_tags,
        last_contact_filter=last_contact_filter,
        all_customers=all_customers
    )

@app.route('/customer/<int:id>')
def customer_profile(id):
    # Fetch customer from database.db
    customer = Customer.query.get_or_404(id)
    
    # Tag color mapping (same as in customers route)
    tag_colors = {
        'VIP': '#f59e0b',
        'New': '#10b981',
        'Returning': '#3b82f6',
        'Hot Lead': '#ef4444',
        'Cold Lead': '#6b7280',
        'Premium': '#8b5cf6',
        'Enterprise': '#ec4899'
    }
    
    users = User.query.all()
    
    # Calculate total lead score across all linked chat sessions
    total_lead_score = 0
    for s in customer.chat_sessions:
        total_lead_score += calculate_session_score(s)
        
    return render_template('customer_details.html', c=customer, tags_inventory=get_tags_inventory(), tag_colors=tag_colors, users=users, total_lead_score=total_lead_score)

@app.route('/api/customer/<int:id>')
def api_get_customer(id):
    customer = Customer.query.get_or_404(id)
    return jsonify({
        'id': customer.id,
        'name': customer.name,
        'email': customer.email,
        'phone': customer.phone,
        'location': customer.location,
        'notes': customer.notes,
        'tags': customer.tags,
        'assigned_staff': customer.assigned_staff or "Jayden Ng",
        'created_at': customer.created_at,
        'updated_at': customer.updated_at
    })

from flask import flash

@app.route('/customer/<int:id>/edit', methods=['GET','POST'])
def edit_customer(id):

    c = Customer.query.get_or_404(id)

    tag_colors = {
        'VIP': '#f59e0b',
        'New': '#10b981',
        'Returning': '#3b82f6',
        'Hot Lead': '#ef4444',
        'Cold Lead': '#6b7280',
        'Premium': '#8b5cf6',
        'Enterprise': '#ec4899'
    }

    if request.method == 'POST':
        c.name = request.form.get("name")
        c.email = request.form.get("email")
        c.phone = request.form.get("phone")
        c.location = request.form.get("location")
        c.notes = request.form.get("notes")

        tags = request.form.getlist("tags")
        new_tag = request.form.get("new_tag")

        if new_tag:
            tags.append(new_tag)

        c.tags = ",".join(tags)

        db.session.commit()
        flash("Customer updated successfully!", "success")

        return redirect(url_for('customer_profile', id=c.id))

    return render_template(
        'edit_customer.html',
        c=c,
        tags_inventory=get_tags_inventory(),
        tag_colors=tag_colors
    )

@app.route('/customer/<int:id>/delete', methods=['POST'])
def delete_customer(id):
    customer = Customer.query.get_or_404(id)
    db.session.delete(customer)
    db.session.commit()
    flash("Customer deleted successfully!", "danger")
    return redirect(url_for('customers'))

@app.route('/export_customers')
def export_customers():
    """Export all customers as CSV"""
    import csv
    from io import StringIO
    
    customers_list = Customer.query.all()
    
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['ID', 'Name', 'Email', 'Phone', 'Location', 'Tags', 'Status', 'Last Contact'])
    
    for c in customers_list:
        writer.writerow([
            c.id,
            c.name,
            c.email or '',
            c.phone or '',
            c.location or '',
            c.tags or '',
            c.status or '',
            c.last_contact or ''
        ])
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=customers.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route('/api/customer/create', methods=['POST'])
def api_create_customer():
    data = request.get_json()
    
    # Check if email already exists (safety check from your friend's logic)
    existing = Customer.query.filter_by(email=data.get('email')).first()
    if existing:
        return jsonify({"error": "A customer with this email already exists"}), 400

    new_cust = Customer(
        name=data.get('name'),
        email=data.get('email'),
        phone=data.get('phone'),
        location=data.get('location'),
        status="Active",  # Default for new customers
        tags=data.get('tags', 'New'),
        created_at=datetime.now().strftime('%Y-%m-%d %H:%M'),
        created_by=session.get('user_name', 'Admin'),
        updated_at=datetime.now().strftime('%Y-%m-%d %H:%M'),
        updated_by=session.get('user_name', 'Admin')
    )
    
    db.session.add(new_cust)
    db.session.commit()
    
    # Create a corresponding ChatSession so the new customer appears in Chat History
    try:
        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        chat = ChatSession(
            visitor_name=new_cust.name,
            visitor_email=new_cust.email,
            status='bot',
            linked_customer_id=new_cust.id,
            created_at=now,
            updated_at=now
        )
        db.session.add(chat)
        db.session.flush()  # ensure chat.id available

        # Add an initial system message to the chat history
        sys_msg = ChatMessage(
            session_id=chat.id,
            sender_type='system',
            sender_name='System',
            text=f'Customer record created for {new_cust.name} in CRM.',
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        db.session.add(sys_msg)
        db.session.commit()
    except Exception:
        db.session.rollback()
        # don't block customer creation on chat seeding failure

    flash("Customer created successfully!", "success")

    create_notification(
        'customer',
        'New Customer Added',
        f'Customer "{new_cust.name}" was added by {session.get("user_name", "Admin")}.',
        icon='👤'
    )
    
    return jsonify({"ok": True, "id": new_cust.id, "name": new_cust.name})

@app.route('/api/customer/<int:id>/notes', methods=['PUT'])
def api_update_customer_notes(id):
    customer = Customer.query.get_or_404(id)
    data = request.get_json()
    
    customer.notes = data.get('notes', '')
    customer.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M')
    customer.updated_by = session.get('user_name', 'Admin')
    db.session.commit()
    
    create_notification(
        'customer',
        'Customer Notes Updated',
        f'Notes for "{customer.name}" were updated by {session.get("user_name", "Admin")}.',
        icon='📝'
    )
    
    return jsonify({"success": True, "message": "Notes saved successfully"})

@app.route('/history')
def history():
    view = request.args.get('view', 'active')  # active or archived
    search_query = request.args.get('search', '').strip()
    
    # Base query
    if view == 'archived':
        base_query = ChatSession.query.filter_by(archived=True)
    else:
        base_query = ChatSession.query.filter_by(archived=False)
    
    # If search query exists, filter by message content or visitor name
    if search_query:
        # Find session IDs that have messages containing the search query
        matching_message_sessions = db.session.query(ChatMessage.session_id).filter(
            ChatMessage.text.ilike(f'%{search_query}%')
        ).distinct().all()
        matching_session_ids = [s[0] for s in matching_message_sessions]
        
        # Filter sessions by either visitor name OR session ID in matching messages
        sessions = base_query.filter(
            or_(
                ChatSession.visitor_name.ilike(f'%{search_query}%'),
                ChatSession.id.in_(matching_session_ids)
            )
        ).order_by(ChatSession.pinned.desc(), ChatSession.id.desc()).all()
    else:
        sessions = base_query.order_by(ChatSession.pinned.desc(), ChatSession.id.desc()).all()
    
    customers_list = Customer.query.all()
    inquiries_list = Inquiry.query.all()
    rules = Rule.query.filter_by(active=True).all()
    
    # Pre-calculate lead status for persistent UI
    for s in sessions:
        score = calculate_session_score(s)
        s.is_lead = (score > 0)
        s.calculated_score = score
    
    # Collect all keywords from active rules
    keywords = []
    for r in rules:
        for kw in r.keywords.split(','):
            kw = kw.strip()
            if kw:
                keywords.append(kw.lower())
    
    # Get current user role for permissions
    user_role = session.get('user_role', 'agent')
    
    # Also get all agents for super admin transfer functionality
    users_list = User.query.all()
    
    return render_template('chat-history.html',
                           sessions=sessions,
                           customers=customers_list,
                           inquiries=inquiries_list,
                           users=users_list,
                           rule_keywords=keywords,
                           current_view=view,
                           user_role=user_role)

@app.route('/visitor-profile/<int:session_id>')
def visitor_profile(session_id):
    chat_session = ChatSession.query.get_or_404(session_id)
    # Generate a consistent mock phone number for the external profile demo
    # The format will be: +60 12-XXX XXXX
    mock_phone = f"+60 12-{ (session_id * 12345 % 900) + 100 } { (session_id * 6789) % 9000 + 1000 }"
    return render_template('visitor_profile.html', session=chat_session, visitor_phone=mock_phone)

@app.route('/api/chat/session/<int:session_id>/profile')
def api_visitor_profile(session_id):
    chat_session = ChatSession.query.get_or_404(session_id)
    mock_phone = f"+60 12-{ (session_id * 12345 % 900) + 100 } { (session_id * 6789) % 9000 + 1000 }"
    
    customer_data = None
    if chat_session.linked_customer_id:
        c = chat_session.linked_customer
        customer_data = {
            'id': c.id,
            'name': c.name,
            'email': c.email,
            'phone': c.phone,
            'location': c.location,
            'notes': c.notes,
            'tags': c.tags,
            'assigned_staff': c.assigned_staff or "Jayden Ng"
        }

    return jsonify({
        'session': {
            'id': chat_session.id,
            'visitor_name': chat_session.visitor_name,
            'visitor_email': chat_session.visitor_email,
            'visitor_phone': mock_phone,
            'linked_customer_id': chat_session.linked_customer_id,
            'linked_inquiry_id': chat_session.linked_inquiry_id,
            'updated_at': chat_session.updated_at,
            'discovery_channel': 'Direct Visit'
        },
        'customer': customer_data
    })

@app.route('/api/chat/session/<int:session_id>/become-customer', methods=['POST'])
def api_promote_to_customer(session_id):
    chat_session = ChatSession.query.get_or_404(session_id)
    
    # Check if already a customer
    if chat_session.linked_customer_id:
        return jsonify({'ok': False, 'error': 'This visitor is already linked to a customer record.'}), 400

    # Promote visitor to customer status with the mock phone number for consistency
    mock_phone = f"+60 12-{ (session_id * 12345 % 900) + 100 } { (session_id * 6789) % 9000 + 1000 }"
    new_customer = Customer(
        name=chat_session.visitor_name,
        email=chat_session.visitor_email,
        phone=mock_phone,
        status="Active",
        assigned_staff=session.get('user_name', 'Admin')
    )
    db.session.add(new_customer)
    db.session.commit() # Save to get the new ID
    
    # Update the chat session to reflect the new internal customer link
    chat_session.linked_customer_id = new_customer.id
    db.session.commit()
    
    return jsonify({'ok': True, 'customer_id': new_customer.id})

# --- CHAT API ENDPOINTS ---

@app.route('/api/chat/sessions')
def api_chat_sessions():
    sessions = ChatSession.query.filter_by(archived=False).order_by(ChatSession.pinned.desc(), ChatSession.id.desc()).all()
    result = []
    for s in sessions:
        last_msg = s.chat_messages[-1] if s.chat_messages else None
        result.append({
            'id': s.id,
            'visitor_name': s.visitor_name,
            'visitor_email': s.visitor_email,
            'status': s.status,
            'linked_customer_id': s.linked_customer_id,
            'linked_inquiry_id': s.linked_inquiry_id,
            'updated_at': s.updated_at,
            'tags': s.tags or '',
            'archived': s.archived,
            'pinned': s.pinned,
            'last_message': last_msg.text[:60] + '...' if last_msg and len(last_msg.text) > 60 else (last_msg.text if last_msg else ''),
            'last_time': last_msg.timestamp if last_msg else '',
            'message_count': len(s.chat_messages)
        })
    return jsonify(result)

@app.route('/api/chat/session/<int:session_id>/messages')
def api_chat_messages(session_id):
    from flask import session as flask_session
    chat_session = ChatSession.query.get_or_404(session_id)
    messages = []
    for m in chat_session.chat_messages:
        pic = None
        if m.sender_type == 'agent':
            agent = User.query.filter_by(name=m.sender_name).first()
            if agent:
                pic = agent.profile_picture
        
        messages.append({
            'id': m.id,
            'sender_type': m.sender_type,
            'sender_name': m.sender_name,
            'text': m.text,
            'timestamp': m.timestamp,
            'pic': pic
        })
    return jsonify({
        'session': {
            'id': chat_session.id,
            'visitor_name': chat_session.visitor_name,
            'visitor_email': chat_session.visitor_email,
            'visitor_phone': f"+60 12-{ (session_id * 12345 % 900) + 100 } { (session_id * 6789) % 9000 + 1000 }",
            'status': chat_session.status,
            'linked_customer_id': chat_session.linked_customer_id,
            'linked_inquiry_id': chat_session.linked_inquiry_id,
            'tags': chat_session.tags or '',
            'archived': chat_session.archived,
            'pinned': chat_session.pinned,
            'assigned_agent_id': chat_session.assigned_agent_id,
            'assigned_agent_name': chat_session.assigned_agent.name if chat_session.assigned_agent else None,
            'assigned_agent_pic': chat_session.assigned_agent.profile_picture if chat_session.assigned_agent else None,
            'requested_agent_id': chat_session.requested_agent_id,
            'requested_agent_name': chat_session.requested_agent.name if chat_session.requested_agent else None,
            'transfer_status': chat_session.transfer_status,
            'linked_customer_id': chat_session.linked_customer_id,
            'current_user_id': flask_session.get('user_id')
        },
        'messages': messages
    })

@app.route('/api/chat/session/<int:session_id>/send', methods=['POST'])
def api_chat_send(session_id):
    chat_session = ChatSession.query.get_or_404(session_id)
    data = request.get_json()
    from datetime import datetime
    from flask import session as flask_session
    
    if chat_session.assigned_agent_id and chat_session.assigned_agent_id != flask_session.get('user_id'):
        return jsonify({'ok': False, 'error': 'Only the assigned agent can chat here.'}), 403
    
    new_msg = ChatMessage(
        session_id=session_id,
        sender_type='agent',
        sender_name=flask_session.get('user_name', 'Admin'),
        text=data.get('text', ''),
        timestamp=datetime.now().strftime('%I:%M %p')
    )
    if not chat_session.assigned_agent_id:
        chat_session.assigned_agent_id = flask_session.get('user_id')
        chat_session.status = 'agent_active'
    db.session.add(new_msg)
    chat_session.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M')
    db.session.commit()
    
    agent = User.query.get(flask_session.get('user_id'))
    agent_pic = agent.profile_picture if agent else None

    return jsonify({'ok': True, 'message': {
        'id': new_msg.id,
        'sender_type': new_msg.sender_type,
        'sender_name': new_msg.sender_name,
        'text': new_msg.text,
        'timestamp': new_msg.timestamp,
        'pic': agent_pic
    }})

@app.route('/api/chat/session/<int:session_id>/takeover', methods=['POST'])
def api_chat_takeover(session_id):
    chat_session = ChatSession.query.get_or_404(session_id)
    from datetime import datetime
    from flask import session as flask_session
    
    if chat_session.assigned_agent_id:
        return jsonify({'ok': False, 'error': f'Chat already assigned to {chat_session.assigned_agent.username}.'}), 400
    
    chat_session.assigned_agent_id = flask_session.get('user_id')
    chat_session.status = 'agent_active'
    chat_session.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    # Add system message
    system_msg = ChatMessage(
        session_id=session_id,
        sender_type='system',
        sender_name='System',
        text=f'🟢 {flask_session.get("user_name", "An agent")} has taken over this conversation.',
        timestamp=datetime.now().strftime('%I:%M %p')
    )
    db.session.add(system_msg)
    db.session.commit()
    
    return jsonify({'ok': True, 'message': {
        'id': system_msg.id,
        'sender_type': system_msg.sender_type,
        'sender_name': system_msg.sender_name,
        'text': system_msg.text,
        'timestamp': system_msg.timestamp
    }})

@app.route('/api/chat/session/<int:session_id>/request-transfer', methods=['POST'])
def api_chat_request_transfer(session_id):
    chat_session = ChatSession.query.get_or_404(session_id)
    from flask import session as flask_session
    if not chat_session.assigned_agent_id:
        return jsonify({'ok': False, 'error': 'Chat is not assigned to anyone.'}), 400
    
    chat_session.requested_agent_id = flask_session.get('user_id')
    chat_session.transfer_status = 'pending'
    db.session.commit()
    
    create_notification(
        'chat',
        'Chat Transfer Requested',
        f'Agent {flask_session.get("user_name")} wants to take over chat with {chat_session.visitor_name}.',
        target_user_id=chat_session.assigned_agent_id,
        icon='🔄'
    )
    
    return jsonify({'ok': True})

@app.route('/api/chat/session/<int:session_id>/handle-transfer', methods=['POST'])
def api_chat_handle_transfer(session_id):
    chat_session = ChatSession.query.get_or_404(session_id)
    from flask import session as flask_session
    data = request.get_json()
    action = data.get('action') # 'accept' or 'reject'
    
    if chat_session.assigned_agent_id != flask_session.get('user_id'):
        return jsonify({'ok': False, 'error': 'Only the owner can handle transfers.'}), 403
        
    if action == 'accept':
        from datetime import datetime
        old_agent_name = flask_session.get('user_name')
        new_agent_id = chat_session.requested_agent_id
        new_agent = User.query.get(new_agent_id)
        
        chat_session.assigned_agent_id = new_agent_id
        chat_session.requested_agent_id = None
        chat_session.transfer_status = 'none'
        
        # Add system message
        sys_msg = ChatMessage(
            session_id=session_id,
            sender_type='system',
            sender_name='System',
            text=f'🔄 Agent {old_agent_name} transferred this chat over to Agent {new_agent.name if new_agent else "another agent"}.',
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        db.session.add(sys_msg)
        db.session.commit()
    else:
        chat_session.requested_agent_id = None
        chat_session.transfer_status = 'none'
        db.session.commit()
        
    return jsonify({'ok': True})

@app.route('/api/chat/session/<int:session_id>/admin-transfer', methods=['POST'])
def api_chat_admin_transfer(session_id):
    from flask import session as flask_session
    from datetime import datetime
    
    # Check if user is admin/super admin/ultra admin for force actions
    user_role = flask_session.get('user_role', 'agent')
    if user_role not in ['super_admin', 'ultra_admin']:
        return jsonify({'ok': False, 'error': 'Only admins can forcefully transfer chats.'}), 403
        
    chat_session = ChatSession.query.get_or_404(session_id)
    data = request.get_json()
    new_agent_id = data.get('target_user_id')
    
    if not new_agent_id:
        return jsonify({'ok': False, 'error': 'No target agent provided.'}), 400
        
    new_agent = User.query.get(new_agent_id)
    if not new_agent:
        return jsonify({'ok': False, 'error': 'Target agent not found.'}), 404
        
    old_agent_name = "None"
    if chat_session.assigned_agent_id:
        old_agent = User.query.get(chat_session.assigned_agent_id)
        if old_agent:
            old_agent_name = old_agent.name
            
    chat_session.assigned_agent_id = new_agent_id
    chat_session.requested_agent_id = None
    chat_session.transfer_status = 'none'
    chat_session.status = 'agent_active' # Ensure it's in agent mode
    chat_session.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    # Add system message
    role_name = user_role.replace('_', ' ').title()
    sys_msg = ChatMessage(
        session_id=session_id,
        sender_type='system',
        sender_name='System',
        text=f'🛡️ {role_name} {flask_session.get("user_name")} forcefully transferred this chat from {old_agent_name} to {new_agent.name}.',
        timestamp=datetime.now().strftime('%I:%M %p')
    )
    db.session.add(sys_msg)
    db.session.commit()
    
    return jsonify({'ok': True})

@app.route('/api/chat/session/<int:session_id>/force-takeover', methods=['POST'])
def api_chat_force_takeover(session_id):
    from flask import session as flask_session
    from datetime import datetime
    
    # Check if user is super admin or ultra admin
    user_role = flask_session.get('user_role', 'agent')
    if user_role not in ['super_admin', 'ultra_admin']:
        return jsonify({'ok': False, 'error': 'Only admins can force take over chats.'}), 403
    
    chat_session = ChatSession.query.get_or_404(session_id)
    old_agent_name = None
    
    if chat_session.assigned_agent_id:
        old_agent = User.query.get(chat_session.assigned_agent_id)
        old_agent_name = old_agent.name if old_agent else 'previous agent'
    
    # Force transfer
    chat_session.assigned_agent_id = flask_session.get('user_id')
    chat_session.status = 'agent_active'
    chat_session.requested_agent_id = None
    chat_session.transfer_status = 'none'
    chat_session.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    # Add system message
    role_name = user_role.replace('_', ' ').title()
    if old_agent_name:
        message_text = f'⚡ {role_name} {flask_session.get("user_name", "Admin")} has forcefully taken over this conversation from {old_agent_name}.'
    else:
        message_text = f'⚡ {role_name} {flask_session.get("user_name", "Admin")} has taken over this conversation.'
    
    system_msg = ChatMessage(
        session_id=session_id,
        sender_type='system',
        sender_name='System',
        text=message_text,
        timestamp=datetime.now().strftime('%I:%M %p')
    )
    db.session.add(system_msg)
    db.session.commit()
    
    return jsonify({'ok': True})

@app.route('/api/chat/session/<int:session_id>/link-customer', methods=['POST'])
def api_chat_link_customer(session_id):
    session = ChatSession.query.get_or_404(session_id)
    data = request.get_json()
    customer_id = data.get('customer_id')
    
    if customer_id:
        customer = Customer.query.get_or_404(customer_id)
        session.linked_customer_id = customer.id
    else:
        session.linked_customer_id = None
    
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/chat/session/<int:session_id>/link-inquiry', methods=['POST'])
def api_chat_link_inquiry(session_id):
    session = ChatSession.query.get_or_404(session_id)
    data = request.get_json()
    inquiry_id = data.get('inquiry_id')
    
    if inquiry_id:
        inquiry = Inquiry.query.get_or_404(inquiry_id)
        session.linked_inquiry_id = inquiry.id
    else:
        session.linked_inquiry_id = None
    
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/inquiry/<int:inquiry_id>/unlink-chats', methods=['POST'])
def api_inquiry_unlink_chats(inquiry_id):
    inquiry = Inquiry.query.get_or_404(inquiry_id)
    # Find all sessions linked to this inquiry
    sessions = ChatSession.query.filter_by(linked_inquiry_id=inquiry.id).all()
    for s in sessions:
        s.linked_inquiry_id = None
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/chat/message/<int:message_id>/edit', methods=['POST'])
def api_chat_edit_message(message_id):
    msg = ChatMessage.query.get_or_404(message_id)
    # Allow editing agent and bot messages
    if msg.sender_type not in ('agent', 'bot'):
        return jsonify({'ok': False, 'error': 'Cannot edit customer/system messages.'}), 400
    
    data = request.get_json()
    new_text = data.get('text')
    if not new_text or not new_text.strip():
        return jsonify({'ok': False, 'error': 'Text cannot be empty.'}), 400

    msg.text = new_text.strip()
    db.session.commit()
    return jsonify({'ok': True, 'text': msg.text})

@app.route('/api/chat/message/<int:message_id>/delete', methods=['POST'])
def api_chat_delete_message(message_id):
    msg = ChatMessage.query.get_or_404(message_id)
    # Only allow deleting agent, customer, and bot messages
    if msg.sender_type not in ('agent', 'customer', 'bot'):
        return jsonify({'ok': False, 'error': 'Cannot delete system messages.'}), 400
    db.session.delete(msg)
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/chat/session/<int:session_id>/delete', methods=['POST'])
def api_chat_delete_session(session_id):
    session = ChatSession.query.get_or_404(session_id)
    db.session.delete(session)
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/chat/session/<int:session_id>/archive', methods=['POST'])
def api_chat_archive(session_id):
    session = ChatSession.query.get_or_404(session_id)
    data = request.get_json()
    session.archived = data.get('archived', True)
    db.session.commit()
    return jsonify({'ok': True, 'archived': session.archived})

@app.route('/api/chat/session/<int:session_id>/tags', methods=['POST'])
def api_chat_update_tags(session_id):
    session = ChatSession.query.get_or_404(session_id)
    data = request.get_json()
    session.tags = data.get('tags', '')
    db.session.commit()
    return jsonify({'ok': True, 'tags': session.tags})

@app.route('/api/chat/session/<int:session_id>/pin', methods=['POST'])
def api_chat_pin(session_id):
    session = ChatSession.query.get_or_404(session_id)
    data = request.get_json()
    session.pinned = data.get('pinned', not session.pinned)
    db.session.commit()
    return jsonify({'ok': True, 'pinned': session.pinned})

@app.route('/my-team')
def my_team():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    team = None
    members = []
    
    all_teams = []
    my_requests = []
    
    if user.team_id:
        # Mark chat as read
        user.last_active_team_chat = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        db.session.commit()

        team = Team.query.get(user.team_id)
        if team:
            members = User.query.filter_by(team_id=team.id).all()
            # Sort: leader=0, vice=1, others=2
            members.sort(key=lambda x: 0 if x.team_role == 'leader' else (1 if x.team_role == 'vice_leader' else 2))
        
        # If leader or vice leader, fetch pending join requests
        if user.team_role in ['leader', 'vice_leader']:
             pending_join_requests = TeamRequest.query.filter_by(team_id=team.id, status='pending', type='join').all()
        else:
             pending_join_requests = []
    else:
        pending_join_requests = []
        # Fetch available teams and user's requests
        all_teams = Team.query.all()
        # Calculate dynamic scores for all teams
        for t in all_teams:
            t.dynamic_score = calculate_team_score(t.id)
            
        # Create a set of requested team IDs for easy lookup in template
        pending_reqs = TeamRequest.query.filter_by(user_id=user.id, status='pending').all()
        my_requests = [r.team_id for r in pending_reqs]
    
    # Calculate team score if user has a team
    calculated_team_score = calculate_team_score(team.id) if team else 0

    return render_template('my_team.html', team=team, members=members, user=user, all_teams=all_teams, my_requests=my_requests, pending_join_requests=pending_join_requests, calculated_team_score=calculated_team_score)

@app.route('/templates-manager')
def templates_manager():
    return render_template('auto_reply_template_manager.html')

@app.route('/repository')
def repository():
    return render_template('inquiry-repository.html')

@app.route('/scoring')
def lead_scoring():
    rules = Rule.query.all()
    # Use the global context processor's search_seed instead of overriding it
    return render_template('lead-scoring.html', rules=rules)

# Route to show the Detail/Chat page
@app.route('/inquiry/<int:id>')
def inquiry_detail(id):
    inquiry = Inquiry.query.get_or_404(id)
    assigned_user = User.query.filter_by(username=inquiry.assigned_rep).first()
    if not assigned_user and inquiry.assigned_rep:
        assigned_user = User.query.filter_by(name=inquiry.assigned_rep).first()
    users = User.query.all()
    return render_template('inquiry_detail.html', inquiry=inquiry, users=users, assigned_user=assigned_user)

@app.route('/inquiry/<int:id>/delete', methods=['POST'])
def delete_inquiry(id):
    inquiry = Inquiry.query.get_or_404(id)
    db.session.delete(inquiry)
    db.session.commit()
    flash("Customer deleted successfully!", "danger")
    return jsonify({'ok': True})

# API to fetch messages for the chat
@app.route('/api/inquiry/<int:id>/messages')
def get_messages(id):
    inquiry = Inquiry.query.get_or_404(id)
    
    # If linked to a chat session, return THOSE messages
    if inquiry.chat_sessions:
        session = inquiry.chat_sessions[0]
        messages = []
        for m in session.chat_messages:
            messages.append({
                'sender': m.sender_name or m.sender_type,
                'text': m.text,
                'time': m.timestamp,
                'is_agent': m.sender_type in ['agent', 'bot', 'system']
            })
        return jsonify(messages)
    
    # Fallback to old behavior (though UI hides it)
    messages = [{'sender': m.sender, 'text': m.text, 'time': m.time, 'is_agent': m.is_agent} for m in inquiry.messages]
    return jsonify(messages)

@app.route('/api/inquiry/<int:id>/message', methods=['POST'])
def send_message(id):
    inquiry = Inquiry.query.get_or_404(id)
    data = request.get_json()
    from datetime import datetime
    
    if inquiry.chat_sessions:
        session = inquiry.chat_sessions[0]
        new_msg = ChatMessage(
            session_id=session.id,
            sender_type='agent',
            sender_name='Admin',
            text=data.get('text'),
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        db.session.add(new_msg)
        session.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M')
    else:
        new_msg = Message(
            inquiry_id=id,
            sender="Admin",
            text=data.get('text'),
            time=datetime.now().strftime('%I:%M %p'),
            is_agent=True
        )
        db.session.add(new_msg)
        
    db.session.commit()
    return jsonify({"ok": True})

# Lead Scoring Logic (Add/Edit/Delete)
@app.route('/add_rule', methods=['GET', 'POST'])
def add_rule():
    if request.method == 'POST':
        new_rule = Rule(
            name=request.form.get('name'),
            keywords=request.form.get('keywords'),
            score=int(request.form.get('score')),
            operation=request.form.get('operation'),
            active=True if request.form.get('active') else False,
            created_at=datetime.now().strftime('%Y-%m-%d %H:%M'),
            created_by=session.get('user_name', 'Admin'),
            updated_at=datetime.now().strftime('%Y-%m-%d %H:%M'),
            updated_by=session.get('user_name', 'Admin')
        )
        db.session.add(new_rule)
        db.session.commit()
        
        create_notification(
            'rule',
            'New Scoring Rule Created',
            f'Rule "{new_rule.name}" was created by {session.get("user_name", "Admin")}.',
            icon='⚙️'
        )
        
        return redirect(url_for('lead_scoring'))
    return render_template('rule_form.html', rule=None, title="New Rule Configuration")

@app.route('/edit_rule/<int:id>', methods=['GET', 'POST'])
def edit_rule(id):
    rule = Rule.query.get_or_404(id)
    if request.method == 'POST':
        rule.name = request.form.get('name')
        rule.keywords = request.form.get('keywords')
        rule.score = int(request.form.get('score'))
        rule.operation = request.form.get('operation')
        rule.active = True if request.form.get('active') else False
        rule.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M')
        rule.updated_by = session.get('user_name', 'Admin')
        db.session.commit()
        
        create_notification(
            'rule',
            'Scoring Rule Updated',
            f'Rule "{rule.name}" was updated by {session.get("user_name", "Admin")}.',
            icon='✏️'
        )
        
        return redirect(url_for('lead_scoring'))
    return render_template('rule_form.html', rule=rule, title="Edit Rule Configuration")

@app.route('/delete_rule/<int:id>')
def delete_rule(id):
    rule = Rule.query.get_or_404(id)
    db.session.delete(rule)
    db.session.commit()
    return redirect(url_for('lead_scoring'))

@app.route('/toggle_status/<int:id>', methods=['POST'])
def toggle_status(id):
    rule = Rule.query.get_or_404(id)
    data = request.get_json()
    rule.active = data['active']
    rule.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M')
    rule.updated_by = session.get('user_name', 'Admin')
    db.session.commit()
    return jsonify({'success': True})

# 1. Template API
@app.route('/api/templates', methods=['GET', 'POST'])
def handle_templates():
    if request.method == 'POST':
        data = request.get_json()
        new_template = AutoReplyTemplate(
            title=data['title'],
            message=data['message'],
            category=data['category'],
            keywords=','.join(data['keywords']), # Convert list to string
            created_at=datetime.now().strftime('%Y-%m-%d %H:%M'),
            created_by=session.get('user_name', 'Admin'),
            updated_at=datetime.now().strftime('%Y-%m-%d %H:%M'),
            updated_by=session.get('user_name', 'Admin')
        )
        db.session.add(new_template)
        db.session.commit()
        
        create_notification(
            'template',
            'New Auto-Reply Template Created',
            f'Template "{new_template.title}" was created by {session.get("user_name", "Admin")}.',
            icon='💬'
        )
        
        return jsonify(template_to_dict(new_template))
    
    templates = AutoReplyTemplate.query.all()
    return jsonify([template_to_dict(t) for t in templates])

@app.route('/api/templates/<int:id>', methods=['PUT', 'DELETE'])
def handle_single_template(id):
    template = AutoReplyTemplate.query.get_or_404(id)
    if request.method == 'DELETE':
        db.session.delete(template)
        db.session.commit()
        return jsonify({"success": True})
    
    data = request.get_json()
    template.title = data['title']
    template.message = data['message']
    template.category = data['category']
    template.keywords = ','.join(data['keywords'])
    template.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M')
    template.updated_by = session.get('user_name', 'Admin')
    db.session.commit()
    
    create_notification(
        'template',
        'Auto-Reply Template Updated',
        f'Template "{template.title}" was updated by {session.get("user_name", "Admin")}.',
        icon='✏️'
    )
    
    return jsonify(template_to_dict(template))

# 2. FAQ API
@app.route('/api/faqs', methods=['GET', 'POST'])
def handle_faqs():
    if request.method == 'POST':
        data = request.get_json()
        new_faq = FAQ(
            question=data['question'],
            answer=data['answer'],
            category=data['category'],
            created_at=datetime.now().strftime('%Y-%m-%d %H:%M'),
            created_by=session.get('user_name', 'Admin'),
            updated_at=datetime.now().strftime('%Y-%m-%d %H:%M'),
            updated_by=session.get('user_name', 'Admin')
        )
        db.session.add(new_faq)
        db.session.commit()
        
        create_notification(
            'template',
            'New FAQ Created',
            f'FAQ "{new_faq.question}" was created by {session.get("user_name", "Admin")}.',
            icon='❓'
        )
        
        return jsonify(faq_to_dict(new_faq))
    
    faqs = FAQ.query.all()
    return jsonify([faq_to_dict(f) for f in faqs])

@app.route('/api/faqs/<int:id>', methods=['PUT', 'DELETE'])
def handle_single_faq(id):
    faq = FAQ.query.get_or_404(id)
    if request.method == 'DELETE':
        db.session.delete(faq)
        db.session.commit()
        return jsonify({"success": True})
    
    data = request.get_json()
    faq.question = data['question']
    faq.answer = data['answer']
    faq.category = data['category']
    faq.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M')
    faq.updated_by = session.get('user_name', 'Admin')
    db.session.commit()
    
    create_notification(
        'template',
        'FAQ Updated',
        f'FAQ "{faq.question}" was updated by {session.get("user_name", "Admin")}.',
        icon='✏️'
    )
    
    return jsonify(faq_to_dict(faq))

@app.route('/api/faqs/<int:id>/click', methods=['POST'])
def increment_faq_click(id):
    faq = FAQ.query.get_or_404(id)
    faq.click_count += 1
    
    # Log the click for temporal stats
    click_log = FAQLog(faq_id=id)
    db.session.add(click_log)
    
    db.session.commit()
    return jsonify(faq_to_dict(faq))

# 3. Auto-Reply Logic API
@app.route('/api/auto-reply', methods=['POST'])
def auto_reply():
    data = request.get_json()
    user_msg = data.get('message', '').lower()
    
    # 1. Search for Keyword Match in Templates
    templates = AutoReplyTemplate.query.all()
    matched_replies = []
    
    for t in templates:
        keywords = t.keywords.lower().split(',')
        if any(k.strip() in user_msg for k in keywords if k.strip()):
            matched_replies.append(t.message)
            t.usage_count += 1 # Increment usage
            
    # 2. Search for Match in FAQs
    if not matched_replies:
        faqs = FAQ.query.all()
        for f in faqs:
            question_words = f.question.lower().split()
            if any(word in user_msg for word in question_words):
                matched_replies.append(f.answer)
                f.click_count += 1 # Increment click count
    
    if matched_replies:
        db.session.commit()
        source = "template" if any(t.message in matched_replies for t in templates) else "faq"
        return jsonify({
            "source": source,
            "replies": matched_replies
        })
    
    # 3. Fallback to AI (Mocked for now)
    return jsonify({
        "source": "ai",
        "replies": ["I see you're asking about that. Our AI agent is currently processing your request... (Integration Placeholder)"]
    })

# --- 3. INQUIRY REPOSITORY API ---

@app.route('/api/inquiries')
def get_inquiries():
    search = request.args.get('search', '').lower()
    inq_id = request.args.get('id', '')
    
    # Support both single and multiple filters
    status_filter = request.args.get('status', '')
    status_list = request.args.getlist('status[]')
    
    type_filter = request.args.get('type', '')
    type_list = request.args.getlist('type[]')
    
    # We join with User to get the current display name based on username
    query = db.session.query(Inquiry, User).outerjoin(User, Inquiry.assigned_rep == User.username)
    
    if inq_id:
        query = query.filter(Inquiry.id == inq_id)
    if search:
        query = query.filter(or_(
            Inquiry.customer.ilike(f'%{search}%'),
            User.name.ilike(f'%{search}%'),
            User.username.ilike(f'%{search}%'),
            Inquiry.assigned_rep.ilike(f'%{search}%')
        ))
    
    # Apply status filter
    if status_filter:
        query = query.filter(Inquiry.status == status_filter)
    elif status_list:
        query = query.filter(Inquiry.status.in_(status_list))
        
    # Apply type filter
    if type_filter:
        query = query.filter(Inquiry.inquiry_type == type_filter)
    elif type_list:
        query = query.filter(Inquiry.inquiry_type.in_(type_list))
        
    results = query.all()
    
    data = []
    for inquiry, user in results:
        # Format: "[display name] @[username]"
        user_display = "Unassigned"
        if user:
            user_display = f"{user.name} @{user.username}"
        elif inquiry.assigned_rep:
            # Try to find user by name if username match failed (for old data)
            alt_user = User.query.filter_by(name=inquiry.assigned_rep).first()
            if alt_user:
                user_display = f"{alt_user.name} @{alt_user.username}"
            else:
                user_display = inquiry.assigned_rep

        rep_pic = None
        rep_id = None
        
        if user:
            rep_pic = user.profile_picture
            rep_id = user.id
        elif inquiry.assigned_rep:
            # Try to find user by name if username match failed (for old data)
            alt_user = User.query.filter_by(name=inquiry.assigned_rep).first()
            if alt_user:
                rep_pic = alt_user.profile_picture
                rep_id = alt_user.id

        data.append({
            'id': inquiry.id,
            'customer': inquiry.customer,
            'customer_id': inquiry.customer_id,
            'inquiry_type': inquiry.inquiry_type,
            'status': inquiry.status,
            'assigned_rep': user_display,
            'rep_username': inquiry.assigned_rep,
            'rep_id': rep_id,
            'rep_pic': rep_pic,
            'created_at': inquiry.created_at,
            'created_by': inquiry.created_by,
            'updated_at': inquiry.updated_at,
            'updated_by': inquiry.updated_by
        })
    
    return jsonify(data)

@app.route('/inquiry/new')
def inquiry_new():
    users = User.query.all()
    return render_template('inquiry_new.html', users=users)

@app.route('/api/inquiry/create', methods=['POST'])
def api_create_inquiry():
    data = request.get_json()
    new_inquiry = Inquiry(
        customer=data.get('customer'),
        customer_id=data.get('customer_id'),
        assigned_rep=data.get('assigned_rep'),
        inquiry_type=data.get('inquiry_type'),
        status=data.get('status', 'New'),
        description=data.get('description', ''),
        notes=data.get('notes', ''),
        created_at=datetime.now().strftime('%Y-%m-%d %H:%M'),
        created_by=session.get('user_name', 'Admin'),
        updated_at=datetime.now().strftime('%Y-%m-%d %H:%M'),
        updated_by=session.get('user_name', 'Admin')
    )
    db.session.add(new_inquiry)
    db.session.commit()
    
    # Handle immediate linking to chat
    linked_session_id = data.get('linked_session_id')
    if linked_session_id:
        chat = ChatSession.query.get(linked_session_id)
        if chat:
            chat.linked_inquiry_id = new_inquiry.id
            db.session.commit()
    
    create_notification(
        'inquiry',
        'New Inquiry Created',
        f'Inquiry for "{new_inquiry.customer}" was created by {session.get("user_name", "Admin")}.',
        icon='📋'
    )
    
    return jsonify({"ok": True, "id": new_inquiry.id})

@app.route('/api/inquiry/<int:id>/update', methods=['PUT'])
def api_update_inquiry(id):
    inquiry = Inquiry.query.get_or_404(id)
    data = request.get_json()
    
    inquiry.status = data.get('status', inquiry.status)
    inquiry.assigned_rep = data.get('assigned_rep', inquiry.assigned_rep)
    inquiry.description = data.get('description', inquiry.description)
    
    # Handle internal notes - if inquiry has a linked customer, update customer notes instead
    if 'notes' in data:
        if inquiry.customer_id:
            # Update linked customer's notes
            customer = Customer.query.get(inquiry.customer_id)
            if customer:
                customer.notes = data.get('notes')
                customer.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M')
                customer.updated_by = session.get('user_name', 'Admin')
        else:
            # No linked customer, update inquiry notes directly
            inquiry.notes = data.get('notes', inquiry.notes)
    
    inquiry.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M')
    inquiry.updated_by = session.get('user_name', 'Admin')
    db.session.commit()
    
    create_notification(
        'inquiry',
        'Inquiry Updated',
        f'Inquiry for "{inquiry.customer}" was updated by {session.get("user_name", "Admin")}.',
        icon='✏️'
    )
    
    return jsonify({"ok": True, "id": inquiry.id})

@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/api/inquiry/<int:id>/link-customer', methods=['POST'])
def api_link_inquiry_customer(id):
    inquiry = Inquiry.query.get_or_404(id)
    data = request.get_json()
    inquiry.customer_id = data.get('customer_id')
    inquiry.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M')
    inquiry.updated_by = session.get('user_name', 'Admin')
    db.session.commit()
    return jsonify({"ok": True})

# Helper functions to serialize objects
def template_to_dict(t):
    return {
        'id': t.id,
        'title': t.title,
        'message': t.message,
        'category': t.category,
        'keywords': t.keywords.split(',') if t.keywords else [],
        'usageCount': t.usage_count,
        'created_at': t.created_at,
        'created_by': t.created_by,
        'updated_at': t.updated_at,
        'updated_by': t.updated_by
    }

def faq_to_dict(f):
    return {
        'id': f.id,
        'question': f.question,
        'answer': f.answer,
        'category': f.category,
        'clickCount': f.click_count,
        'created_at': f.created_at,
        'created_by': f.created_by,
        'updated_at': f.updated_at,
        'updated_by': f.updated_by
    }

# --- 4. ANNOUNCEMENT CRUD API ---

@app.route('/api/announcements', methods=['GET'])
def get_announcements():
    announcements = Announcement.query.order_by(Announcement.id.desc()).all()
    return jsonify([announcement_to_dict(a) for a in announcements])

@app.route('/api/announcements', methods=['POST'])
def create_announcement():
    if session.get('user_role') not in ['ultra_admin', 'super_admin', 'admin']:
        return jsonify({'error': 'Forbidden: Only admins can create announcements'}), 403
        
    data = request.get_json()
    from datetime import datetime
    new_announcement = Announcement(
        title=data.get('title'),
        content=data.get('content'),
        priority=data.get('priority', 'normal'),
        created_at=datetime.now().strftime('%Y-%m-%d %H:%M')
    )
    db.session.add(new_announcement)
    db.session.commit()
    
    create_notification(
        'announcement',
        f'📢 {new_announcement.title}',
        f'Announcement by {session.get("user_name", "Admin")}: {new_announcement.content[:100]}',
        icon='📢'
    )
    
    return jsonify(announcement_to_dict(new_announcement)), 201

@app.route('/api/announcements/<int:id>', methods=['PUT'])
def update_announcement(id):
    if session.get('user_role') not in ['ultra_admin', 'super_admin', 'admin']:
        return jsonify({'error': 'Forbidden: Only admins can edit announcements'}), 403

    announcement = Announcement.query.get_or_404(id)
    data = request.get_json()
    announcement.title = data.get('title', announcement.title)
    announcement.content = data.get('content', announcement.content)
    announcement.priority = data.get('priority', announcement.priority)
    db.session.commit()
    
    create_notification(
        'announcement',
        'Announcement Updated',
        f'Announcement "{announcement.title}" was updated by {session.get("user_name", "Admin")}.',
        icon='✏️'
    )
    
    return jsonify(announcement_to_dict(announcement))

@app.route('/api/announcements/<int:id>', methods=['DELETE'])
def delete_announcement(id):
    if session.get('user_role') not in ['ultra_admin', 'super_admin', 'admin']:
        return jsonify({'error': 'Forbidden: Only admins can delete announcements'}), 403

    announcement = Announcement.query.get_or_404(id)
    db.session.delete(announcement)
    db.session.commit()
    return jsonify({"success": True})

def announcement_to_dict(a):
    return {
        'id': a.id,
        'title': a.title,
        'content': a.content,
        'priority': a.priority,
        'createdAt': a.created_at
    }

# --- 5. TEAM MANAGEMENT API ---

@app.route('/api/teams', methods=['GET'])
def get_teams():
    teams = Team.query.all()
    result = []
    for t in teams:
        pic_url = t.profile_picture
        if pic_url and not pic_url.startswith('http'):
            pic_url = url_for('static', filename='uploads/' + pic_url)
        elif not pic_url:
            pic_url = f"https://ui-avatars.com/api/?name={t.name}&background=random"
            
        result.append({
            'id': t.id,
            'name': t.name,
            'profile_picture': pic_url,
            'description': t.description,
            'role': t.role,
            'department': t.department,
            'team_score': calculate_team_score(t.id),
            'team_tag': t.team_tag,
            'member_count': len(t.members)
        })
    return jsonify({'teams': result})

@app.route('/api/teams/create', methods=['POST'])
def create_team():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    current_user = User.query.get(session.get('user_id'))
    if current_user.role not in ['ultra_admin', 'super_admin']:
        return jsonify({'error': 'Only Super Admins and Ultra Admins can create teams.'}), 403
        
    leader_id = request.form.get('leader_id')
    
    if current_user.team_id and not leader_id:
        return jsonify({'error': 'You are already in a team. You must assign another user as the leader for this new team.'}), 400
        
    # Handling form data for file upload
    name = request.form.get('name')
    if not name:
        return jsonify({'error': 'Team name is required.'}), 400
        
    if Team.query.filter_by(name=name).first():
        return jsonify({'error': 'A team with this name already exists.'}), 400
        
    new_team = Team(
        name=name,
        description=request.form.get('description', ''),
        role=request.form.get('role', ''),
        department=request.form.get('department', ''),
        team_tag=request.form.get('team_tag', ''),
        created_at=datetime.now().strftime('%Y-%m-%d %H:%M')
    )
    
    # Handle Profile Picture Upload
    if 'profile_picture' in request.files:
        file = request.files['profile_picture']
        if file and file.filename != '':
            import os
            from werkzeug.utils import secure_filename
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = f"team_{timestamp}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            new_team.profile_picture = filename

    db.session.add(new_team)
    db.session.flush() # Get the ID
    
    # Assignment of leadership
    if leader_id:
        target_leader = User.query.get(leader_id)
        if target_leader:
            if target_leader.team_id:
                return jsonify({'error': f'User {target_leader.name} is already in a team and cannot be assigned as the leader.'}), 400
            target_leader.team_id = new_team.id
            target_leader.team_role = 'leader'
    else:
        # Creator becomes leader
        current_user.team_id = new_team.id
        current_user.team_role = 'leader'
    
    db.session.commit()
    
    create_notification(
        'account',
        'New Team Created',
        f'Team {new_team.name} has been created by {current_user.username}.',
        target_roles=['super_admin', 'admin']
    )
    
    return jsonify({'success': True, 'team_id': new_team.id})

@app.route('/api/teams/request-action', methods=['POST'])
def team_request_action():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.get_json()
    action_type = data.get('type') # join, move, invite
    target_user_id = int(data.get('user_id'))
    target_team_id = data.get('team_id')
    if target_team_id and target_team_id != 'none':
        target_team_id = int(target_team_id)
    
    current_user = User.query.get(session.get('user_id'))
    target_user = User.query.get(target_user_id)
    
    # Leadership Integrity Check for Removal
    if (not target_team_id or str(target_team_id).lower() == 'none') and target_user.team_id:
        if target_user.team_role == 'leader':
            others_count = User.query.filter(User.team_id == target_user.team_id, User.id != target_user.id).count()
            if others_count > 0:
                return jsonify({'error': f'Leadership Integrity: {target_user.name} is the team leader. You cannot remove the leader while there are other members in the team. Please transfer leadership first.'}), 400

    # Handle removal (no team)
    if not target_team_id or str(target_team_id).lower() == 'none':
        if current_user.role == 'ultra_admin' or (current_user.role == 'super_admin' and target_user.role in ['admin', 'agent']) or (current_user.role == 'admin' and target_user.id == current_user.id):
             target_user.team_id = None
             target_user.team_role = None
             db.session.commit()
             return jsonify({'success': True, 'message': 'User removed from team.'})
        return jsonify({'error': 'Permission denied for team removal.'}), 403

    target_team = Team.query.get(target_team_id)
    if not target_team:
        return jsonify({'error': 'Target team not found.'}), 404

    # Leadership Integrity Check for Moving
    if target_user.team_id and target_user.team_role == 'leader' and target_user.team_id != target_team_id:
        others_count = User.query.filter(User.team_id == target_user.team_id, User.id != target_user.id).count()
        if others_count > 0:
             return jsonify({'error': f'Leadership Integrity: {target_user.name} is the team leader. You cannot move the leader to a new team while there are other members present. Please transfer leadership first.'}), 400

    # Permission Checks
    can_perform = False
    needs_approval = True
    
    if action_type == 'join':
        # Agents can request to join
        if current_user.role == 'agent' or current_user.role == 'admin':
            can_perform = True
        # Super Admins joining themselves requires leader permission
        elif current_user.role == 'super_admin' and target_user_id == current_user.id:
            can_perform = True
        # Ultra Admin joining themselves require no permission
        elif current_user.role == 'ultra_admin' and target_user_id == current_user.id:
            can_perform = True
            needs_approval = False
            
    elif action_type == 'move':
        # Ultra Admins can move anyone
        if current_user.role == 'ultra_admin':
            can_perform = True
            needs_approval = False
        # Super Admins can move admins or agents
        elif current_user.role == 'super_admin' and target_user.role in ['admin', 'agent']:
            can_perform = True
            needs_approval = False
        # Admins can request to move any agent
        elif current_user.role == 'admin' and target_user.role == 'agent':
            can_perform = True
            
    elif action_type == 'invite':
        # Leaders and Vice Leaders can invite
        if current_user.team_id == target_team_id and current_user.team_role in ['leader', 'vice_leader']:
            can_perform = True

    if not can_perform:
        return jsonify({'error': 'Forbidden: You do not have permission for this action.'}), 403

    if not needs_approval:
        target_user.team_id = target_team_id
        target_user.team_role = 'member'
        db.session.commit()
        return jsonify({'success': True, 'message': 'Action completed successfully.'})
    
    # Create request
    new_req = TeamRequest(
        user_id=target_user_id,
        team_id=target_team_id,
        requester_id=current_user.id,
        type=action_type,
        created_at=datetime.now().strftime('%Y-%m-%d %H:%M')
    )
    db.session.add(new_req)
    db.session.commit()
    
    # Notify team leader
    leaders = User.query.filter_by(team_id=target_team_id, team_role='leader').all()
    for leader in leaders:
        create_notification(
            'account',
            'Team Request',
            f'{current_user.username} requested {action_type} for {target_user.username}.',
            target_user_id=leader.id
        )
        
    return jsonify({'success': True, 'message': 'Request sent successfully.'})

@app.route('/api/teams/handle-request', methods=['POST'])
def handle_team_request():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.get_json()
    req_id = data.get('request_id')
    # JS sends 'action' (approve/reject), DB/logic expects 'status' (approved/rejected)
    action = data.get('action') 
    
    if action == 'approve':
        status = 'approved'
    elif action == 'reject':
        status = 'rejected'
    else:
        status = data.get('status') # Fallback
    
    if not status:
         return jsonify({'error': 'Missing action or status'}), 400

    req = TeamRequest.query.get_or_404(req_id)
    current_user = User.query.get(session.get('user_id'))
    
    # Only team leader can approve/reject
    if current_user.team_id != req.team_id or current_user.team_role != 'leader':
        return jsonify({'error': 'Forbidden: Only the team leader can handle requests.'}), 403
        
    req.status = status
    if status == 'approved':
        # Add user to the team
        target_user = User.query.get(req.user_id)
        target_user.team_id = req.team_id
        target_user.team_role = 'member'
        
        # Remove any other pending requests from this user? or just this one is done.
        
    db.session.commit()
    
    # Notify requester and user
    try:
        create_notification(
            'account',
            f'Team Request {status.title()}',
            f'Request for {req.target_user.username} to join {req.target_team.name} was {status}.',
            target_user_id=req.requester_id
        )
    except Exception as e:
        print(f"Notification error: {e}")
    
    return jsonify({'success': True})

@app.route('/api/teams/leave', methods=['POST'])
def leave_team():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    current_user = User.query.get(session.get('user_id'))
    if not current_user.team_id:
        return jsonify({'error': 'You are not in a team.'}), 400
        
    # If the user is the ONLY leader, they might need to assign another one or team must have at least one leader.
    # The prompt says: "A team MUST have atleast one leader."
    if current_user.team_role == 'leader':
        # Absolute Rule: Leaders must manually transfer leadership if there are other members
        others_count = User.query.filter(User.team_id == current_user.team_id, User.id != current_user.id).count()
        if others_count > 0:
            return jsonify({'error': 'Leadership Integrity: You are the team leader. You must transfer your leadership to another member before leaving the team.'}), 400

    current_user.team_id = None
    current_user.team_role = None
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/teams/kick', methods=['POST'])
def kick_member():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.get_json()
    username = data.get('username')
    
    current_user = User.query.get(session.get('user_id'))
    target_user = User.query.filter_by(username=username).first_or_404()
    
    if current_user.team_id != target_user.team_id:
        return jsonify({'error': 'User is not in your team.'}), 400
        
    # Hierarchy: Leaders, Vice Leaders (for members), and all Admins can kick
    is_leader = (current_user.team_id == target_user.team_id and current_user.team_role == 'leader')
    is_vice = (current_user.team_id == target_user.team_id and current_user.team_role == 'vice_leader')
    is_any_admin = current_user.role in ['ultra_admin', 'super_admin', 'admin']
    
    # Vice leaders can only kick members
    if is_vice and target_user.team_role != 'member':
        return jsonify({'error': 'Vice leaders can only kick regular members.'}), 403
        
    if not is_leader and not is_vice and not is_any_admin:
        return jsonify({'error': 'Only leaders, vice leaders (for members), or admins can kick members.'}), 403
        
    # Leaders can only kick agents (non-admin accounts)
    if is_leader and not is_any_admin and target_user.role != 'agent':
        return jsonify({'error': 'Leaders can only kick regular agents.'}), 403

    # Leadership Integrity Check for Kick (if kicking a leader)
    if target_user.team_role == 'leader':
        others_count = User.query.filter(User.team_id == target_user.team_id, User.id != target_user.id).count()
        if others_count > 0:
            return jsonify({'error': f'Leadership Integrity: {target_user.name} is the team leader. You cannot kick the leader while there are other members in the team. Please transfer leadership first.'}), 400

    target_user.team_id = None
    target_user.team_role = None
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/teams/my-requests', methods=['GET'])
def get_my_team_requests():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    current_user = User.query.get(session.get('user_id'))
    if not current_user.team_id or current_user.team_role not in ['leader', 'vice_leader']:
        return jsonify({'requests': []})
        
    requests = TeamRequest.query.filter_by(team_id=current_user.team_id, status='pending').all()
    result = []
    for r in requests:
        result.append({
            'id': r.id,
            'user_id': r.user_id,
            'user_name': r.target_user.username if r.target_user else 'Unknown',
            'type': r.type,
            'created_at': r.created_at
        })
    return jsonify({'requests': result})

@app.route('/api/teams/<int:team_id>/details', methods=['GET'])
def get_team_details(team_id):
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    team = Team.query.get_or_404(team_id)
    members = User.query.filter_by(team_id=team.id).all()
    
    member_list = []
    for m in members:
        member_list.append({
            'id': m.id,
            'name': m.name,
            'username': m.username,
            'role': m.role, # system role
            'team_role': m.team_role or 'member',
            'pic': m.profile_picture
        })
        
    pic_url = team.profile_picture

    return jsonify({
        'team': {
            'id': team.id,
            'name': team.name,
            'profile_picture': pic_url,
            'description': team.description,
            'role': team.role,
            'department': team.department,
            'team_score': calculate_team_score(team.id),
            'team_tag': team.team_tag
        },
        'members': member_list
    })

@app.route('/api/teams/<int:team_id>/delete', methods=['POST'])
def delete_team(team_id):
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    current_user = User.query.get(session.get('user_id'))
    team = Team.query.get_or_404(team_id)
    
    # Permission: Ultra/Super Admin OR Team Leader
    is_admin = current_user.role in ['ultra_admin', 'super_admin']
    is_leader = current_user.team_id == team.id and current_user.team_role == 'leader'
    
    if not is_admin and not is_leader:
        return jsonify({'error': 'Forbidden: Only admins or team leaders can delete this team.'}), 403
        
    # Unassign all members
    User.query.filter_by(team_id=team.id).update({'team_id': None, 'team_role': None})
    
    # Delete requests
    TeamRequest.query.filter_by(team_id=team.id).delete()
    
    db.session.delete(team)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/teams/<int:team_id>/update', methods=['POST'])
def update_team(team_id):
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    current_user = User.query.get(session.get('user_id'))
    team = Team.query.get_or_404(team_id)
    
    if not (current_user.role in ['ultra_admin', 'super_admin'] or (current_user.team_id == team.id and current_user.team_role == 'leader')):
        return jsonify({'error': 'Forbidden'}), 403
        
    team.name = request.form.get('name', team.name)
    team.description = request.form.get('description', team.description)
    team.role = request.form.get('role', team.role)
    team.department = request.form.get('department', team.department)
    team.team_tag = request.form.get('team_tag', team.team_tag)
    # Team score is now calculated automatically, not manually edited
    
    # Handle Profile Picture Upload
    if 'profile_picture' in request.files:
        file = request.files['profile_picture']
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = f"team_{timestamp}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            team.profile_picture = filename
        
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/teams/member-action', methods=['POST'])
def team_member_action():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.get_json()
    action = data.get('action') # promote_vice, transfer_leader, demote
    target_username = data.get('username')
    
    current_user = User.query.get(session.get('user_id'))
    target_user = User.query.filter_by(username=target_username).first_or_404()
    
    if current_user.team_id != target_user.team_id and current_user.role not in ['ultra_admin', 'super_admin']:
        return jsonify({'error': 'User is not in your team.'}), 400
        
    # Hierarchy Check
    is_ultra_super = current_user.role in ['ultra_admin', 'super_admin']
    is_any_admin = is_ultra_super or current_user.role == 'admin'
    is_leader = (current_user.team_role == 'leader' or is_ultra_super)
    
    # Transfer Leadership is restricted to Leader/Ultra/Super only
    if action == 'transfer_leader' and not is_leader:
        return jsonify({'error': 'Forbidden: Only leaders or ultra/super admins can transfer leadership.'}), 403

    # Promote/Demote allowed for Leader or Any Admin
    if not is_leader and not is_any_admin:
        return jsonify({'error': 'Forbidden: Only leaders or admins can perform this action.'}), 403

    if action == 'promote_vice':
        if target_user.team_role == 'leader':
             return jsonify({'error': 'Cannot demote the team leader directly. Please transfer leadership to another member first.'}), 400
        target_user.team_role = 'vice_leader'
    elif action == 'demote':
        if target_user.team_role == 'leader':
             return jsonify({'error': 'Cannot demote the team leader directly. Please transfer leadership to another member first.'}), 400
        target_user.team_role = 'member'
    elif action == 'transfer_leader': 
        # Logic for performing transfer
        # 1. Find the current leader(s)
        current_leader = User.query.filter_by(team_id=target_user.team_id, team_role='leader').first()
        
        if current_leader:
            current_leader.team_role = 'vice_leader'
        
        target_user.team_role = 'leader'
        
    db.session.commit()
    return jsonify({'success': True})


 # --- 6. NOTIFICATIONS API ---

@app.route('/api/teams/<int:team_id>/chat', methods=['GET', 'POST'])
def api_team_chat(team_id):
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    # Must be in team or super/ultra admin
    if user.team_id != team_id and user.role not in ['ultra_admin', 'super_admin']:
         return jsonify({'error': 'Forbidden'}), 403

    if request.method == 'GET':
        since_id = request.args.get('since', 0, type=int)
        
        query = TeamMessage.query.filter_by(team_id=team_id)
        if since_id > 0:
            query = query.filter(TeamMessage.id > since_id)
        
        # If fetching initial history (since=0), limit to last 50
        if since_id == 0:
            total = query.count()
            if total > 50:
                # We need to slice the query. SQLAlchemy slice/offset
                # Wait, simpler: order by desc limit 50 then reverse?
                # Or just fetch all if not too many. Let's do fetch all but verify count.
                # If > 50, fetch latest 50.
                pass 
                # Actually, simpler logic:
                # If since_id is 0, we want the most recent messages.
                # query.order_by(TeamMessage.created_at.desc()).limit(50) -> reverse
                # But IDs are sequential usually.
        
        # Implementing simple logic: if since_id > 0, get ones > since_id.
        # If since_id == 0, get ALL (or last 100). Let's do ALL for now, simpler.
        messages = query.all()
        
        result = []
        for m in messages:
            # Need user link. The model has backref 'user'.
            result.append({
                'id': m.id,
                'user_id': m.user_id,
                'name': m.user.name if m.user else 'Unknown',
                'pic': m.user.profile_picture if m.user else None,
                'message': m.message,
                'created_at': m.created_at
            })
        
        return jsonify({'messages': result})

    elif request.method == 'POST':
        data = request.get_json()
        msg_text = data.get('message')
        if not msg_text:
            return jsonify({'error': 'Message required'}), 400
        
        import datetime
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        new_msg = TeamMessage(
            team_id=team_id,
            user_id=user_id,
            message=msg_text,
            created_at=now
        )
        db.session.add(new_msg)
        db.session.commit()
        
        return jsonify({'success': True})

@app.route('/api/teams/message/<int:message_id>/edit', methods=['POST'])
def api_team_edit_message(message_id):
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = session.get('user_id')
    msg = TeamMessage.query.get_or_404(message_id)
    user = User.query.get(user_id)
    
    # Hierarchy: ONLY Owners can edit their own messages
    is_owner = msg.user_id == user_id
    
    if not is_owner:
        return jsonify({'error': 'Forbidden: You can only edit your own messages.'}), 403
        
    data = request.get_json()
    new_text = data.get('message')
    if not new_text or not new_text.strip():
        return jsonify({'error': 'Message cannot be empty.'}), 400

    msg.message = new_text.strip()
    db.session.commit()
    return jsonify({'success': True, 'message': msg.message})

@app.route('/api/teams/message/<int:message_id>/delete', methods=['POST'])
def api_team_delete_message(message_id):
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    user_id = session.get('user_id')
    msg = TeamMessage.query.get_or_404(message_id)
    user = User.query.get(user_id)
    
    # Hierarchy: Owners and ALL Admins (Ultra, Super, Regular) can delete
    is_any_admin = user.role in ['ultra_admin', 'super_admin', 'admin']
    is_owner = msg.user_id == user_id
    
    if not (is_any_admin or is_owner):
        return jsonify({'error': 'Forbidden: Only owners and admins can delete messages.'}), 403
        
    db.session.delete(msg)
    db.session.commit()
    return jsonify({'success': True, 'id': msg.id})



@app.route('/api/notifications')
def get_notifications():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'notifications': [], 'unread_count': 0})
        
    from datetime import datetime, timedelta
    # Get notifications from the past week for THIS user
    one_week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M')
    notifications = Notification.query.filter(
        Notification.user_id == user_id,
        Notification.created_at >= one_week_ago
    ).order_by(Notification.id.desc()).all()
    
    result = []
    for n in notifications:
        result.append({
            'id': n.id,
            'type': n.type,
            'title': n.title,
            'message': n.message,
            'icon': n.icon,
            'created_by': n.created_by,
            'created_at': n.created_at,
            'is_read': n.is_read
        })
    
    unread_count = sum(1 for n in notifications if not n.is_read)
    return jsonify({'notifications': result, 'unread_count': unread_count})

@app.route('/api/notifications/read', methods=['POST'])
def mark_notifications_read():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.get_json()
    notif_ids = data.get('ids', [])
    
    if notif_ids == 'all':
        Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
    else:
        for nid in notif_ids:
            notif = Notification.query.filter_by(id=nid, user_id=user_id).first()
            if notif:
                notif.is_read = True
    
    db.session.commit()
    return jsonify({'ok': True})

# --- 6. USER PREFERENCES API ---

@app.route('/api/user/preferences', methods=['GET', 'POST'])
def handle_preferences():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    import json
    if request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid data'}), 400
        
        try:
            prefs = json.loads(user.preferences) if user.preferences else {}
        except:
            prefs = {}
        
        prefs.update(data)
        user.preferences = json.dumps(prefs)
        db.session.commit()
        return jsonify({'success': True})
    
    # GET method
    try:
        prefs = json.loads(user.preferences) if user.preferences else {}
    except:
        prefs = {}
    return jsonify(prefs)

# --- Error Handlers ---
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# --- GLOBAL SEARCH API ---
@app.route('/api/global-search')
def global_search():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])

    results = []

    # 1. Teams (Team Name)
    teams = Team.query.filter(Team.name.ilike(f'%{query}%')).limit(3).all()
    for t in teams:
        results.append({
            'category': 'Team',
            'display': t.name,
            'url': '/admin/create-account' # Teams are also managed here
        })

    # 3. Chats (Visitor Name)
    chats = ChatSession.query.filter(ChatSession.visitor_name.ilike(f'%{query}%')).limit(3).all()
    for c in chats:
        results.append({
            'category': 'Chat',
            'display': f"{c.visitor_name} (#{c.id})",
            'url': f"/history?session={c.id}"
        })

    # 4. Announcements (Title or Content)
    anns = Announcement.query.filter(
        or_(Announcement.title.ilike(f'%{query}%'), Announcement.content.ilike(f'%{query}%'))
    ).limit(3).all()
    for a in anns:
        results.append({
            'category': 'Announcement',
            'display': a.title,
            'url': '/dashboard' # Announcements are on the dashboard
        })
    
    # 5. Customers (Name or Email) - Added for completeness as the UI says "Search leads, rules, or customers..."
    customers = Customer.query.filter(
         or_(Customer.name.ilike(f'%{query}%'), Customer.email.ilike(f'%{query}%'))
    ).limit(3).all()
    for c in customers:
        results.append({
            'category': 'Customer',
            'display': c.name,
            'url': f"/customer/{c.id}"
        })

    # 6. Inquiries (ID, Customer, Type, Description)
    inq_filters = [
        Inquiry.customer.ilike(f'%{query}%'),
        Inquiry.inquiry_type.ilike(f'%{query}%'),
        Inquiry.description.ilike(f'%{query}%')
    ]
    # Check if query is numeric for ID search
    if query.isdigit():
        inq_filters.append(Inquiry.id == int(query))
        
    inquiries = Inquiry.query.filter(or_(*inq_filters)).limit(3).all()
    for i in inquiries:
        results.append({
            'category': 'Inquiry',
            'display': f"#{i.id} - {i.customer} ({i.inquiry_type})",
            'url': f"/inquiry/{i.id}"
        })

    return jsonify(results)

# --- START SERVER (This must always be at the very bottom!) ---
if __name__ == '__main__':
    app.run(debug=True, port=5000)