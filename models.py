from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


# ================= USER =================
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    # Profile photo
    profile_image = db.Column(db.String(200), default="default.png")

    quiz_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    profile = db.relationship(
        'UserProfile',
        backref='user',
        uselist=False,
        cascade="all, delete-orphan"
    )

    daily_logs = db.relationship(
        'DailyLog',
        backref='user',
        cascade="all, delete-orphan"
    )

    activities = db.relationship(
        'ActivityLog',
        backref='user',
        cascade="all, delete-orphan"
    )

    # Password helpers
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.email}>"


# ================= USER PROFILE =================
class UserProfile(db.Model):
    __tablename__ = 'user_profiles'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        unique=True,
        nullable=False
    )

    age = db.Column(db.Integer, nullable=False)
    height_cm = db.Column(db.Integer, nullable=False)
    weight_kg = db.Column(db.Integer, nullable=False)

    goal = db.Column(db.String(20), nullable=False)
    target_steps = db.Column(db.Integer, nullable=False)
    target_calories = db.Column(db.Integer, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # -------- PERSONALIZATION LOGIC --------
    @staticmethod
    def calculate_targets(weight, goal):
        base_calories = weight * 30

        if goal == "lose":
            return 10000, base_calories - 300
        elif goal == "gain":
            return 7000, base_calories + 400
        else:  # maintain
            return 8000, base_calories

    def __repr__(self):
        return f"<UserProfile user_id={self.user_id} goal={self.goal}>"


# ================= DAILY LOG =================
class DailyLog(db.Model):
    __tablename__ = 'daily_logs'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False
    )

    log_date = db.Column(
        db.Date,
        default=date.today,
        nullable=False
    )

    steps = db.Column(db.Integer, default=0)
    calories_consumed = db.Column(db.Integer, default=0)
    calories_burned = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<DailyLog user={self.user_id} date={self.log_date}>"


# ================= ACTIVITY LOG =================
class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False
    )

    activity_type = db.Column(db.String(50), nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    calories = db.Column(db.Integer, nullable=False)

    log_date = db.Column(db.Date, default=date.today)

    def __repr__(self):
        return f"<ActivityLog user={self.user_id} {self.activity_type}>"
