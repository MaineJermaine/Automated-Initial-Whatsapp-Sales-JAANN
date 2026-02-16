from flask import Flask, render_template, request, redirect, url_for, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- 1. MODELS (All models must be defined before create_all) ---

class Rule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    keywords = db.Column(db.String(200), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    operation = db.Column(db.String(10), nullable=False, default='+') 
    active = db.Column(db.Boolean, default=True)

class Inquiry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer = db.Column(db.String(100), nullable=False)
    assigned_rep = db.Column(db.String(50))
    inquiry_type = db.Column(db.String(50))
    status = db.Column(db.String(20), default='New')
    description = db.Column(db.Text)
    notes = db.Column(db.Text)
    messages = db.relationship('Message', backref='inquiry', cascade="all, delete-orphan")

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inquiry_id = db.Column(db.Integer, db.ForeignKey('inquiry.id'), nullable=False)
    sender = db.Column(db.String(50))
    text = db.Column(db.Text)
    time = db.Column(db.String(50))
    is_agent = db.Column(db.Boolean, default=False)

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

class AutoReplyTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    keywords = db.Column(db.Text)  # Stored as comma-separated string
    usage_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.String(50))

class FAQ(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(200), nullable=False)
    answer = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    click_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.String(50))

class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), nullable=False, default='normal')  # low, normal, high, urgent
    created_at = db.Column(db.String(50))

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
    chat_messages = db.relationship('ChatMessage', backref='session', cascade="all, delete-orphan", order_by='ChatMessage.id')
    linked_customer = db.relationship('Customer', backref='chat_sessions')
    linked_inquiry = db.relationship('Inquiry', backref='chat_sessions')

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_session.id'), nullable=False)
    sender_type = db.Column(db.String(20), nullable=False)  # customer, bot, agent, system
    sender_name = db.Column(db.String(100))
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.String(50))

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(30), nullable=False)  # announcement, customer, inquiry, rule
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    icon = db.Column(db.String(10), default='🔔')
    created_by = db.Column(db.String(100), default='System')
    created_at = db.Column(db.String(50))
    is_read = db.Column(db.Boolean, default=False)

# Helper to create notifications
def create_notification(notif_type, title, message, icon='🔔', created_by='JAANN AZRI 252499L'):
    from datetime import datetime
    notif = Notification(
        type=notif_type,
        title=title,
        message=message,
        icon=icon,
        created_by=created_by,
        created_at=datetime.now().strftime('%Y-%m-%d %H:%M')
    )
    db.session.add(notif)
    db.session.commit()
    return notif

# Create tables logic
with app.app_context():
    db.create_all()

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

    return render_template('admin_dashboard_main_hub.html', 
                           all_rules=all_rules, 
                           all_inquiries=all_inquiries,
                           all_announcements=all_announcements,
                           latest_chats=latest_chats,
                           high_value_leads=high_value_leads)

@app.route('/api/dashboard/stats')
def dashboard_stats():
    """Returns all stat values and graph data for the customizable dashboard."""
    total_customers = Customer.query.count()
    active_inquiries = Inquiry.query.filter(Inquiry.status != 'Resolved').count()
    total_inquiries = Inquiry.query.count()
    total_rules = Rule.query.count()
    active_rules = Rule.query.filter_by(active=True).count()
    total_templates = AutoReplyTemplate.query.count()
    total_faqs = FAQ.query.count()
    total_announcements = Announcement.query.count()

    return jsonify({
        "solid_stats": [
            {"key": "total_customers", "label": "Total Customers", "value": total_customers, "icon": "👥", "color": "#3F88C5"},
            {"key": "active_inquiries", "label": "Active Inquiries", "value": active_inquiries, "icon": "📩", "color": "#E94F37"},
            {"key": "total_inquiries", "label": "Total Inquiries", "value": total_inquiries, "icon": "📋", "color": "#44BBA4"},
            {"key": "scoring_rules", "label": "Scoring Rules", "value": f"{active_rules} / {total_rules}", "icon": "⚡", "color": "#a855f7"},
            {"key": "templates_count", "label": "Reply Templates", "value": total_templates, "icon": "💬", "color": "#f59e0b"},
            {"key": "faq_count", "label": "FAQs Published", "value": total_faqs, "icon": "❓", "color": "#06b6d4"},
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
                "labels": ["New", "In Progress", "Resolved", "Urgent"],
                "datasets": [{"label": "Inquiries", "data": [18, 12, 35, 5], "backgroundColor": ["#44BBA4","#f59e0b","#3F88C5","#E94F37"]}]
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
    per_page = 12
    
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
        tags_inventory=tags_inventory,
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
    
    return render_template('customer_details.html', c=customer, tag_colors=tag_colors)

@app.route('/customer/<int:id>/edit', methods=['GET', 'POST'])
def edit_customer(id):
    customer = Customer.query.get_or_404(id)
    
    if request.method == 'POST':
        customer.name = request.form.get('name')
        customer.email = request.form.get('email')
        customer.phone = request.form.get('phone')
        customer.location = request.form.get('location')
        customer.notes = request.form.get('notes', '')
        
        # Handle tags
        selected_tags = request.form.getlist('tags')
        new_tag = request.form.get('new_tag', '').strip()
        if new_tag:
            selected_tags.append(new_tag)
        customer.tags = ','.join(selected_tags) if selected_tags else ''
        
        db.session.commit()
        
        create_notification(
            'customer',
            'Customer Updated',
            f'Customer "{customer.name}" was updated by JAANN AZRI 252499L.',
            icon='✏️'
        )
        
        return redirect(url_for('customer_profile', id=id))
    
    # GET request - show edit form
    tag_colors = {
        'VIP': '#f59e0b',
        'New': '#10b981',
        'Returning': '#3b82f6',
        'Hot Lead': '#ef4444',
        'Cold Lead': '#6b7280',
        'Premium': '#8b5cf6',
        'Enterprise': '#ec4899'
    }
    
    # Get all unique tags for the tag picker
    all_customers = Customer.query.all()
    tags_inventory = {}
    for c in all_customers:
        if c.tags:
            for tag in c.tags.split(','):
                tag = tag.strip()
                if tag and tag not in tags_inventory:
                    tags_inventory[tag] = tag_colors.get(tag, '#94a3b8')
    
    return render_template('edit_customer.html', c=customer, tags_inventory=tags_inventory, tag_colors=tag_colors)

@app.route('/customer/<int:id>/delete', methods=['POST'])
def delete_customer(id):
    customer = Customer.query.get_or_404(id)
    db.session.delete(customer)
    db.session.commit()
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
        status="Active",  # Default for new customers
        tags="New"        # Default tag
    )
    
    db.session.add(new_cust)
    db.session.commit()
    
    create_notification(
        'customer',
        'New Customer Added',
        f'Customer "{new_cust.name}" was added by JAANN AZRI 252499L.',
        icon='👤'
    )
    
    return jsonify({"ok": True})

@app.route('/api/customer/<int:id>/notes', methods=['PUT'])
def api_update_customer_notes(id):
    customer = Customer.query.get_or_404(id)
    data = request.get_json()
    
    customer.notes = data.get('notes', '')
    db.session.commit()
    
    create_notification(
        'customer',
        'Customer Notes Updated',
        f'Notes for "{customer.name}" were updated by JAANN AZRI 252499L.',
        icon='📝'
    )
    
    return jsonify({"success": True, "message": "Notes saved successfully"})

@app.route('/history')
def history():
    view = request.args.get('view', 'active')  # active or archived
    if view == 'archived':
        sessions = ChatSession.query.filter_by(archived=True).order_by(ChatSession.pinned.desc(), ChatSession.id.desc()).all()
    else:
        sessions = ChatSession.query.filter_by(archived=False).order_by(ChatSession.pinned.desc(), ChatSession.id.desc()).all()
    
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
    
    return render_template('chat-history.html',
                           sessions=sessions,
                           customers=customers_list,
                           inquiries=inquiries_list,
                           rule_keywords=keywords,
                           current_view=view)

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
    session = ChatSession.query.get_or_404(session_id)
    messages = [{
        'id': m.id,
        'sender_type': m.sender_type,
        'sender_name': m.sender_name,
        'text': m.text,
        'timestamp': m.timestamp
    } for m in session.chat_messages]
    return jsonify({
        'session': {
            'id': session.id,
            'visitor_name': session.visitor_name,
            'visitor_email': session.visitor_email,
            'status': session.status,
            'linked_customer_id': session.linked_customer_id,
            'linked_inquiry_id': session.linked_inquiry_id,
            'tags': session.tags or '',
            'archived': session.archived,
            'pinned': session.pinned,
        },
        'messages': messages
    })

@app.route('/api/chat/session/<int:session_id>/send', methods=['POST'])
def api_chat_send(session_id):
    session = ChatSession.query.get_or_404(session_id)
    data = request.get_json()
    from datetime import datetime
    
    new_msg = ChatMessage(
        session_id=session_id,
        sender_type='agent',
        sender_name='Admin',
        text=data.get('text', ''),
        timestamp=datetime.now().strftime('%I:%M %p')
    )
    db.session.add(new_msg)
    session.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M')
    db.session.commit()
    
    return jsonify({'ok': True, 'message': {
        'id': new_msg.id,
        'sender_type': new_msg.sender_type,
        'sender_name': new_msg.sender_name,
        'text': new_msg.text,
        'timestamp': new_msg.timestamp
    }})

@app.route('/api/chat/session/<int:session_id>/takeover', methods=['POST'])
def api_chat_takeover(session_id):
    session = ChatSession.query.get_or_404(session_id)
    from datetime import datetime
    
    if session.status == 'agent_active':
        return jsonify({'ok': False, 'error': 'Chat already taken over.'}), 400
    
    session.status = 'agent_active'
    session.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    # Add system message
    system_msg = ChatMessage(
        session_id=session_id,
        sender_type='system',
        sender_name='System',
        text='🟢 An agent has taken over this conversation.',
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

@app.route('/api/chat/message/<int:message_id>/delete', methods=['POST'])
def api_chat_delete_message(message_id):
    msg = ChatMessage.query.get_or_404(message_id)
    # Only allow deleting agent and customer messages
    if msg.sender_type not in ('agent', 'customer'):
        return jsonify({'ok': False, 'error': 'Cannot delete system/bot messages.'}), 400
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
    return render_template('inquiry_detail.html', inquiry=inquiry)

# API to fetch messages for the chat
@app.route('/api/inquiry/<int:id>/messages')
def get_messages(id):
    inquiry = Inquiry.query.get_or_404(id)
    messages = [{'sender': m.sender, 'text': m.text, 'time': m.time, 'is_agent': m.is_agent} for m in inquiry.messages]
    return jsonify(messages)

# API to send a new message
@app.route('/api/inquiry/<int:id>/message', methods=['POST'])
def send_message(id):
    data = request.get_json()
    new_msg = Message(
        inquiry_id=id,
        sender="Admin", # Or use data.get('sender')
        text=data.get('text'),
        time="Just now", # You can use datetime.now() for real timestamps
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
            active=True if request.form.get('active') else False
        )
        db.session.add(new_rule)
        db.session.commit()
        
        create_notification(
            'rule',
            'New Scoring Rule Created',
            f'Rule "{new_rule.name}" was created by JAANN AZRI 252499L.',
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
        db.session.commit()
        
        create_notification(
            'rule',
            'Scoring Rule Updated',
            f'Rule "{rule.name}" was updated by JAANN AZRI 252499L.',
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
            created_at="Just now" # You can use datetime.now()
        )
        db.session.add(new_template)
        db.session.commit()
        
        create_notification(
            'template',
            'New Auto-Reply Template Created',
            f'Template "{new_template.title}" was created by JAANN AZRI 252499L.',
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
    db.session.commit()
    
    create_notification(
        'template',
        'Auto-Reply Template Updated',
        f'Template "{template.title}" was updated by JAANN AZRI 252499L.',
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
            created_at="Just now"
        )
        db.session.add(new_faq)
        db.session.commit()
        
        create_notification(
            'template',
            'New FAQ Created',
            f'FAQ "{new_faq.question}" was created by JAANN AZRI 252499L.',
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
    db.session.commit()
    
    create_notification(
        'template',
        'FAQ Updated',
        f'FAQ "{faq.question}" was updated by JAANN AZRI 252499L.',
        icon='✏️'
    )
    
    return jsonify(faq_to_dict(faq))

@app.route('/api/faqs/<int:id>/click', methods=['POST'])
def increment_faq_click(id):
    faq = FAQ.query.get_or_404(id)
    faq.click_count += 1
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
            
    if matched_replies:
        db.session.commit()
        return jsonify({
            "source": "template",
            "replies": matched_replies
        })
    
    # 2. Fallback to AI (Mocked for now)
    return jsonify({
        "source": "ai",
        "replies": ["I see you're asking about that. Our AI agent is currently processing your request... (Integration Placeholder)"]
    })

# --- 3. INQUIRY REPOSITORY API ---

@app.route('/api/inquiries')
def get_inquiries():
    search = request.args.get('search', '').lower()
    status_filters = request.args.getlist('status[]')
    
    query = Inquiry.query
    if search:
        query = query.filter(Inquiry.customer.ilike(f'%{search}%'))
    if status_filters:
        query = query.filter(Inquiry.status.in_(status_filters))
        
    inquiries = query.all()
    return jsonify([
        {'id': i.id, 'customer': i.customer, 'inquiry_type': i.inquiry_type, 
         'status': i.status, 'assigned_rep': i.assigned_rep} for i in inquiries
    ])

@app.route('/inquiry/new')
def inquiry_new():
    return render_template('inquiry_new.html')

@app.route('/api/inquiry/create', methods=['POST'])
def api_create_inquiry():
    data = request.get_json()
    new_inquiry = Inquiry(
        customer=data.get('customer'),
        assigned_rep=data.get('assigned_rep'),
        inquiry_type=data.get('inquiry_type'),
        status=data.get('status', 'New'),
        description=data.get('description', ''),
        notes=data.get('notes', '')
    )
    db.session.add(new_inquiry)
    db.session.commit()
    
    create_notification(
        'inquiry',
        'New Inquiry Created',
        f'Inquiry for "{new_inquiry.customer}" was created by JAANN AZRI 252499L.',
        icon='📋'
    )
    
    return jsonify({"ok": True, "id": new_inquiry.id})

# Helper functions to serialize objects
def template_to_dict(t):
    return {
        'id': t.id,
        'title': t.title,
        'message': t.message,
        'category': t.category,
        'keywords': t.keywords.split(',') if t.keywords else [],
        'usageCount': t.usage_count,
        'createdAt': t.created_at
    }

def faq_to_dict(f):
    return {
        'id': f.id,
        'question': f.question,
        'answer': f.answer,
        'category': f.category,
        'clickCount': f.click_count,
        'createdAt': f.created_at
    }

# --- 4. ANNOUNCEMENT CRUD API ---

@app.route('/api/announcements', methods=['GET'])
def get_announcements():
    announcements = Announcement.query.order_by(Announcement.id.desc()).all()
    return jsonify([announcement_to_dict(a) for a in announcements])

@app.route('/api/announcements', methods=['POST'])
def create_announcement():
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
        f'Announcement by JAANN AZRI 252499L: {new_announcement.content[:100]}',
        icon='📢'
    )
    
    return jsonify(announcement_to_dict(new_announcement)), 201

@app.route('/api/announcements/<int:id>', methods=['PUT'])
def update_announcement(id):
    announcement = Announcement.query.get_or_404(id)
    data = request.get_json()
    announcement.title = data.get('title', announcement.title)
    announcement.content = data.get('content', announcement.content)
    announcement.priority = data.get('priority', announcement.priority)
    db.session.commit()
    
    create_notification(
        'announcement',
        'Announcement Updated',
        f'Announcement "{announcement.title}" was updated by JAANN AZRI 252499L.',
        icon='✏️'
    )
    
    return jsonify(announcement_to_dict(announcement))

@app.route('/api/announcements/<int:id>', methods=['DELETE'])
def delete_announcement(id):
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

# --- 5. NOTIFICATIONS API ---

@app.route('/api/notifications')
def get_notifications():
    from datetime import datetime, timedelta
    # Get notifications from the past week
    one_week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M')
    notifications = Notification.query.filter(
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
    data = request.get_json()
    notif_ids = data.get('ids', [])
    
    if notif_ids == 'all':
        Notification.query.filter_by(is_read=False).update({'is_read': True})
    else:
        for nid in notif_ids:
            notif = Notification.query.get(nid)
            if notif:
                notif.is_read = True
    
    db.session.commit()
    return jsonify({'ok': True})

# --- Error Handlers ---
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# --- START SERVER (This must always be at the very bottom!) ---
if __name__ == '__main__':
    app.run(debug=True, port=5000)