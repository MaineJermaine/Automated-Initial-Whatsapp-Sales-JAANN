from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)

# 1. Main Dashboard
@app.route('/')
@app.route('/dashboard')
def dashboard():
    return render_template('admin_dashboard_main_hub.html')

# 2. Customer List
@app.route('/customers')
def customers():
    return render_template('customer-list.html')

# 3. Chat History
@app.route('/history')
def history():
    return render_template('chat-history.html')

# 4. Templates
@app.route('/templates-manager')
def templates_manager():
    return render_template('auto_reply_template_manager.html')

# 5. Inquiry Repository
@app.route('/repository')
def repository():
    return render_template('inquiry-repository.html')

# 6. Lead Scoring
@app.route('/scoring')
def lead_scoring():
    return render_template('lead-scoring.html')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Database Model ---
class Rule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    keywords = db.Column(db.String(200), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    # New column to store the math operation (+, -, *, /)
    operation = db.Column(db.String(10), nullable=False, default='+') 
    active = db.Column(db.Boolean, default=True)

# Create tables if they don't exist
with app.app_context():
    db.create_all()

# --- Helper Function: Math Logic ---
def calculate_new_score(current_lead_score, rule_value, operation):
    """
    Calculates the new score based on the operation.
    This function is ready to be used when you process your leads.
    """
    if operation == '+':
        return current_lead_score + rule_value
    elif operation == '-':
        return current_lead_score - rule_value
    elif operation == '*':
        return current_lead_score * rule_value
    elif operation == '/':
        # Prevent division by zero
        return current_lead_score / rule_value if rule_value != 0 else current_lead_score
    return current_lead_score

# --- Routes ---

# 1. Main Dashboard (List Rules)
@app.route('/')
def index():
    # Fetch all rules from database
    rules = Rule.query.all()
    return render_template('lead-scoring.html', rules=rules)

# 2. Add Rule Page
@app.route('/add_rule', methods=['GET', 'POST'])
def add_rule():
    if request.method == 'POST':
        # Logic to SAVE the new rule
        new_rule = Rule(
            name=request.form.get('name'),
            keywords=request.form.get('keywords'),
            score=int(request.form.get('score')),
            operation=request.form.get('operation'), # Capture operation
            active=True if request.form.get('active') else False
        )
        db.session.add(new_rule)
        db.session.commit()
        return redirect(url_for('index'))
    
    # Logic to DISPLAY the page (GET request)
    return render_template('rule_form.html', rule=None, title="New Rule Configuration")

# 3. Edit Rule Page
@app.route('/edit_rule/<int:id>', methods=['GET', 'POST'])
def edit_rule(id):
    # Find the rule or return 404
    rule = Rule.query.get_or_404(id)

    if request.method == 'POST':
        # Logic to UPDATE the existing rule
        rule.name = request.form.get('name')
        rule.keywords = request.form.get('keywords')
        rule.score = int(request.form.get('score'))
        rule.operation = request.form.get('operation') # Update operation
        rule.active = True if request.form.get('active') else False
        
        db.session.commit()
        return redirect(url_for('index'))

    # Logic to DISPLAY the page with EXISTING DATA (GET request)
    # We pass the 'rule' object to the template so it can pre-fill the inputs
    return render_template('rule_form.html', rule=rule, title="Edit Rule Configuration")

# 4. Delete Rule
@app.route('/delete_rule/<int:id>')
def delete_rule(id):
    rule = Rule.query.get_or_404(id)
    db.session.delete(rule)
    db.session.commit()
    return redirect(url_for('index'))

# 5. AJAX Toggle Status (Kept this for the main page switch)
@app.route('/toggle_status/<int:id>', methods=['POST'])
def toggle_status(id):
    rule = Rule.query.get_or_404(id)
    data = request.get_json()
    rule.active = data['active']
    db.session.commit()
    return jsonify({'success': True})

# --- Error Handlers ---
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


if __name__ == '__main__':
    app.run(debug=True, port=5000)