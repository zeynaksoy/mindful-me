from app import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    avatar_file = db.Column(db.String(120), nullable=False, default='default.png')

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
