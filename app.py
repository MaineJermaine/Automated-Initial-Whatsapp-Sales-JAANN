from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy

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

# Create tables logic
with app.app_context():
    db.create_all()

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

@app.route('/')
@app.route('/dashboard')
def dashboard():
    all_rules = Rule.query.all()
    # ADD THIS LINE: Fetch all inquiries too
    all_inquiries = Inquiry.query.all() 
    return render_template('admin_dashboard_main_hub.html', 
                           all_rules=all_rules, 
                           all_inquiries=all_inquiries)

@app.route('/customers')
def customers():
    query = request.args.get('q', '')
    if query:
        # Search by name or email
        customers_list = Customer.query.filter(
            (Customer.name.ilike(f'%{query}%')) | 
            (Customer.email.ilike(f'%{query}%'))
        ).all()
    else:
        customers_list = Customer.query.all()
    
    return render_template('customer-list.html', customers=customers_list, query=query)

@app.route('/customer/<int:id>')
def customer_profile(id):
    # Fetch customer from database.db
    customer = Customer.query.get_or_404(id)
    return render_template('customer_details.html', c=customer)

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
    
    return jsonify({"ok": True})

@app.route('/api/customer/<int:id>/notes', methods=['PUT'])
def api_update_customer_notes(id):
    customer = Customer.query.get_or_404(id)
    data = request.get_json()
    
    customer.notes = data.get('notes', '')
    db.session.commit()
    
    return jsonify({"success": True, "message": "Notes saved successfully"})

@app.route('/history')
def history():
    return render_template('chat-history.html')

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

# --- Error Handlers ---
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# --- START SERVER (This must always be at the very bottom!) ---
if __name__ == '__main__':
    app.run(debug=True, port=5000)