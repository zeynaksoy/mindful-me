from app import db

from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app
from itsdangerous import URLSafeTimedSerializer as Serializer

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(256))
    avatar_file = db.Column(db.String(120), nullable=False, default='default.png')
    streak_count = db.Column(db.Integer, default=0)
    last_entry_date = db.Column(db.Date, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_reset_password_token(self):
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id})

    @staticmethod
    def verify_reset_password_token(token, expires_in=1800):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token, max_age=expires_in).get('user_id')
        except:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return f'<User {self.username}>'

class MoodEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mood = db.Column(db.String(20), nullable=False)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=db.func.now())
    ai_analysis = db.Column(db.String(255), nullable=True)
    ai_advice = db.Column(db.Text, nullable=True)
    ai_sentiment = db.Column(db.String(50), nullable=True)
    ai_score = db.Column(db.Integer, nullable=True)
    ai_keywords = db.Column(db.String(255), nullable=True)
    sleep_hours = db.Column(db.Float, nullable=True)
    stress_level = db.Column(db.Integer, nullable=True)
    activities = db.Column(db.String(255), nullable=True)
    
    # Yeni eklenen uyku ve alışkanlık alanları
    bedtime = db.Column(db.Time, nullable=True)
    wakeup_time = db.Column(db.Time, nullable=True)
    sleep_quality = db.Column(db.Integer, nullable=True) # 1-5
    dream_note = db.Column(db.Text, nullable=True)
    caffeine_intake = db.Column(db.Integer, nullable=True)
    screen_time = db.Column(db.Integer, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'mood': self.mood,
            'text': self.text,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'sleep_hours': self.sleep_hours,
            'stress_level': self.stress_level,
            'activities': self.activities,
            'ai_analysis': {
                'sentiment': self.ai_sentiment,
                'score': self.ai_score,
                'keywords': self.ai_keywords,
                'advice': self.ai_advice
            }
        }

    def __repr__(self):
        return f'<MoodEntry {self.mood} at {self.timestamp}>'
