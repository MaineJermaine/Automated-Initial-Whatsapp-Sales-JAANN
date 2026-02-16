from app import db, User

class PromotionRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    target_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending') # pending, approved, rejected
    approvals = db.Column(db.Text, default='[]') # JSON list of user_ids who approved
    created_at = db.Column(db.String(50))
    
    target_user = db.relationship('User', foreign_keys=[target_user_id], backref='promotion_requests')
    requester = db.relationship('User', foreign_keys=[requester_id], backref='sent_promotion_requests')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
