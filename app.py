from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
# Move all configurations to the top
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Database Model ---
class Rule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    keywords = db.Column(db.String(200), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    operation = db.Column(db.String(10), nullable=False, default='+') 
    active = db.Column(db.Boolean, default=True)

# Create tables if they don't exist
with app.app_context():
    db.create_all()

# --- ROUTES ---

# 1. Main Dashboard
# Update this in your app.py
@app.route('/')
@app.route('/dashboard')
def dashboard():
    # Fetch all rules so the search bar knows they exist immediately
    all_rules = Rule.query.all() 
    return render_template('admin_dashboard_main_hub.html', all_rules=all_rules)

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

# 6. Lead Scoring (Main Page)
@app.route('/scoring')
def lead_scoring():
    # We query the rules here so they show up on the merged page
    rules = Rule.query.all()
    return render_template('lead-scoring.html', rules=rules)

# 7. Add Rule Configuration
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
        return redirect(url_for('lead_scoring')) # Updated to lead_scoring
    return render_template('rule_form.html', rule=None, title="New Rule Configuration")

# 8. Edit Rule
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
        return redirect(url_for('lead_scoring')) # Updated to lead_scoring
    return render_template('rule_form.html', rule=rule, title="Edit Rule Configuration")

# 9. Delete Rule
@app.route('/delete_rule/<int:id>')
def delete_rule(id):
    rule = Rule.query.get_or_404(id)
    db.session.delete(rule)
    db.session.commit()
    return redirect(url_for('lead_scoring'))

# 10. AJAX Toggle
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