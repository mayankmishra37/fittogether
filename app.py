from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from models import db, User, DailyLog, UserProfile, ActivityLog
from datetime import date, datetime, timedelta
from functools import wraps
from sqlalchemy import extract
from werkzeug.utils import secure_filename
import os
from sqlalchemy import or_

# ---------------- APP SETUP ----------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key")

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# PROFILE PHOTO CONFIG
UPLOAD_FOLDER = "static/uploads/profiles"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db.init_app(app)

with app.app_context():
    db.create_all()

# ---------------- LOGIN REQUIRED ----------------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# =====================================================
# 🧠 AI COACH LOGIC
# =====================================================
def ai_coach_advice(user, profile, log):
    advice = []

    if log.steps < profile.target_steps:
        advice.append(f"Walk {profile.target_steps - log.steps} more steps today.")
    else:
        advice.append("Great job! You completed your step goal today.")

    net = log.calories_consumed - log.calories_burned

    if profile.goal == "lose":
        advice.append(
            "You exceeded your calorie limit. Prefer light meals and cardio."
            if net > profile.target_calories else
            "You are on track with calories for weight loss."
        )
    elif profile.goal == "gain":
        advice.append(
            "Increase calories with protein-rich foods."
            if net < profile.target_calories else
            "Good calorie intake for muscle gain."
        )
    else:
        advice.append("Maintain balanced meals and regular activity.")

    advice.append("Stay consistent. Small daily efforts give big results 💪")
    return advice

# =====================================================
# 🤖 AI COACH ROUTE
# =====================================================
@app.route('/ai-coach')
@login_required
def ai_coach():
    user = User.query.get(session['user_id'])
    profile = user.profile
    today = date.today()

    log = DailyLog.query.filter_by(user_id=user.id, log_date=today).first()
    if not log:
        log = DailyLog(
            user_id=user.id,
            log_date=today,
            steps=0,
            calories_burned=0,
            calories_consumed=0
        )
        db.session.add(log)
        db.session.commit()

    msg = request.args.get("message", "").lower().strip()

    greetings = ["hi", "hello", "hey"]
    endings = ["bye", "thanks", "thank you", "ok", "done"]

    if msg == "" or msg in greetings:
        return jsonify({"advice": [
            "Hi! I’m your FitTogether AI Coach 👋",
            "I can help with fitness, food, calories, and workouts.",
            "What would you like to work on today?"
        ]})

    if msg in endings:
        return jsonify({"advice": [
            "You’re welcome 😊",
            "Take care of your health and come back anytime 💚"
        ]})

    allowed = [
    "diet", "food", "eat", "workout", "exercise",
    "steps", "calories", "fitness", "health",
    "habit", "habits", "daily"
]


    if not any(w in msg for w in allowed):
        return jsonify({"advice": [
            "I can only help with fitness-related topics 😊",
            "Try asking about diet, calories, or workouts."
        ]})

    if "habit" in msg or "daily" in msg:
        return jsonify({
            "advice": [
                "Healthy daily habits include regular walks, balanced meals, and proper sleep.",
                "Consistency matters more than intensity.",
                "Would you like tips on workouts or diet?"
            ]
        })

    return jsonify({"advice": ai_coach_advice(user, profile, log)})

# =====================================================
# 🚨 SMART NOTIFICATIONS
# =====================================================
def get_smart_notifications(profile, log):
    alerts = []
    net = log.calories_consumed - log.calories_burned

    if net > profile.target_calories:
        alerts.append(f"You’re {net - profile.target_calories} calories above target.")

    if log.steps < profile.target_steps:
        alerts.append(f"You’re {profile.target_steps - log.steps} steps below today’s goal.")

    return alerts

# =====================================================
# 🔥 STREAK SYSTEM
# =====================================================
def calculate_streak(user_id):
    streak = 0
    today = date.today()

    for i in range(365):
        d = today - timedelta(days=i)
        log = DailyLog.query.filter_by(user_id=user_id, log_date=d).first()
        if log and (log.steps > 0 or log.calories_consumed > 0):
            streak += 1
        else:
            break

    return streak

# ---------------- HOME ----------------
@app.route('/')
def home():
    return render_template('home.html')

# ---------------- SIGNUP ----------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')

        if not username or not email or not password or not confirm:
            flash("All fields are required", "danger")
            return redirect(url_for('signup'))

        if password != confirm:
            flash("Passwords do not match", "danger")
            return redirect(url_for('signup'))

        if len(password) < 6:
            flash("Password must be at least 6 characters", "warning")
            return redirect(url_for('signup'))

        if User.query.filter_by(username=username).first():
            flash("Username already exists", "danger")
            return redirect(url_for('signup'))

        if User.query.filter_by(email=email).first():
            flash("Email already exists", "danger")
            return redirect(url_for('signup'))

        user = User(username=username, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        # ✅ AUTO LOGIN
        session['user_id'] = user.id
        flash("Account created successfully! Complete your setup.", "success")
        return redirect(url_for('quiz'))

    return render_template('signup.html')



# ---------------- LOGIN ----------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form.get('email', '').strip()
        password = request.form.get('password')

        if not identifier or not password:
            flash("All fields are required", "warning")
            return redirect(url_for('login'))

        # ✅ Allow login with EMAIL OR USERNAME
        user = User.query.filter(
            (User.email == identifier) | (User.username == identifier)
        ).first()

        if not user or not user.check_password(password):
            flash("Invalid username/email or password", "danger")
            return redirect(url_for('login'))

        # ✅ LOGIN SUCCESS → DIRECT DASHBOARD
        session['user_id'] = user.id
        flash("Welcome back!", "success")
        return redirect(url_for('dashboard'))

    return render_template('login.html')



# ---------------- QUIZ ----------------
@app.route('/quiz', methods=['GET', 'POST'])
@login_required
def quiz():
    user = User.query.get(session['user_id'])

    # If profile already completed → skip quiz
    if user.quiz_completed and user.profile:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            age = int(request.form.get('age'))
            height = int(request.form.get('height'))
            weight = int(request.form.get('weight'))
            goal = request.form.get('goal')
        except (TypeError, ValueError):
            flash("Please enter valid numbers", "danger")
            return redirect(url_for('quiz'))

        # ✅ VALIDATION FIRST
        if age <= 0 or height <= 0 or weight <= 0:
            flash("Invalid input values", "danger")
            return redirect(url_for('quiz'))

        if goal not in ["lose", "maintain", "gain"]:
            flash("Please select a valid goal", "danger")
            return redirect(url_for('quiz'))

        # Calculate targets
        steps, calories = UserProfile.calculate_targets(weight, goal)

        # Create profile
        profile = UserProfile(
            user_id=user.id,
            age=age,
            height_cm=height,
            weight_kg=weight,
            goal=goal,
            target_steps=steps,
            target_calories=calories
        )

        db.session.add(profile)
        user.quiz_completed = True
        db.session.commit()

        # ✅ IMPORTANT: go to fitness plan
        return redirect(url_for('fitness_plan'))

    return render_template('quiz.html')

# ---------------- FITNESS PLAN ----------------
@app.route('/fitness-plan')
@login_required
def fitness_plan():
    user = User.query.get(session['user_id'])
    profile = user.profile
    return render_template('fitness_plan.html', user=user, profile=profile)



# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
@login_required
def dashboard():
    user = User.query.get(session['user_id'])
    profile = user.profile
    today = date.today()

    log = DailyLog.query.filter_by(user_id=user.id, log_date=today).first()
    if not log:
        log = DailyLog(
            user_id=user.id,
            log_date=today,
            steps=0,
            calories_burned=0,
            calories_consumed=0
        )
        db.session.add(log)
        db.session.commit()

    activities = ActivityLog.query.filter_by(user_id=user.id, log_date=today).all()

    calories_consumed = log.calories_consumed
    calories_burned = log.calories_burned
    remaining_calories = profile.target_calories - calories_consumed + calories_burned

    return render_template(
        'dashboard.html',
        user=user,
        profile=profile,
        log=log,
        activities=[{
            "type": a.activity_type,
            "duration": a.duration,
            "calories": a.calories
        } for a in activities],
        calories_consumed=calories_consumed,
        calories_burned=calories_burned,
        remaining_calories=remaining_calories,
        alerts=get_smart_notifications(profile, log),
        streak=calculate_streak(user.id)
    )

# ---------------- ACTIVITY ----------------
@app.route('/activity', methods=['GET', 'POST'])
@login_required
def activity():
    user = User.query.get(session['user_id'])
    today = date.today()

    log = DailyLog.query.filter_by(user_id=user.id, log_date=today).first()
    if not log:
        log = DailyLog(
            user_id=user.id,
            log_date=today,
            steps=0,
            calories_burned=0,
            calories_consumed=0
        )
        db.session.add(log)
        db.session.commit()

    if request.method == 'POST':
        activity = ActivityLog(
            user_id=user.id,
            activity_type=request.form.get('activity_type'),
            duration=int(request.form.get('duration', 0)),
            calories=int(request.form.get('calories', 0)),
            log_date=today
        )
        db.session.add(activity)

        log.steps += activity.duration
        log.calories_burned += activity.calories

        db.session.commit()
        flash("Activity added successfully", "success")
        return redirect(url_for('activity'))

    return render_template('activity.html', log=log)

# ---------------- FOOD ----------------
@app.route('/food', methods=['GET', 'POST'])
@login_required
def food():
    user = User.query.get(session['user_id'])
    profile = user.profile
    today = date.today()

    log = DailyLog.query.filter_by(user_id=user.id, log_date=today).first()
    if not log:
        log = DailyLog(
            user_id=user.id,
            log_date=today,
            steps=0,
            calories_burned=0,
            calories_consumed=0
        )
        db.session.add(log)
        db.session.commit()

    if request.method == 'POST':
        log.calories_consumed += int(request.form.get('calories', 0))
        db.session.commit()
        flash("Meal logged successfully", "success")
        return redirect(url_for('food'))

    return render_template('food.html', log=log, profile=profile)

# ---------------- PROFILE ----------------
@app.route('/profile')
@login_required
def profile():
    user = User.query.get(session['user_id'])
    return render_template('profile.html', user=user, profile=user.profile)

# ---------------- UPLOAD PROFILE PHOTO ----------------
@app.route('/upload-profile-photo', methods=['POST'])
@login_required
def upload_profile_photo():
    file = request.files.get('profile_photo')

    if not file or file.filename == "":
        flash("No file selected", "warning")
        return redirect(url_for('profile'))

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    user = User.query.get(session['user_id'])
    user.profile_image = filename
    db.session.commit()

    flash("Profile photo updated", "success")
    return redirect(url_for('profile'))

# ---------------- UPDATE PROFILE ----------------
@app.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    user = User.query.get(session['user_id'])

    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()

    if not username or not email:
        flash("Username and email are required", "danger")
        return redirect(url_for('profile'))

    exists = User.query.filter(User.email == email, User.id != user.id).first()
    if exists:
        flash("Email already exists", "danger")
        return redirect(url_for('profile'))

    user.username = username
    user.email = email
    db.session.commit()

    flash("Profile updated successfully", "success")
    return redirect(url_for('profile'))

# ---------------- CHANGE PASSWORD ----------------
@app.route('/change-password', methods=['POST'])
@login_required
def change_password():
    user = User.query.get(session['user_id'])

    current = request.form.get('current_password', '')
    new = request.form.get('new_password', '')

    if not user.check_password(current):
        flash("Current password is incorrect", "danger")
        return redirect(url_for('profile'))

    if len(new) < 6:
        flash("Password must be at least 6 characters", "warning")
        return redirect(url_for('profile'))

    user.set_password(new)
    db.session.commit()

    flash("Password updated successfully", "success")
    return redirect(url_for('profile'))

# ---------------- GROWTH ----------------
@app.route('/growth')
@login_required
def growth():
    user = User.query.get(session['user_id'])
    profile = user.profile
    today = date.today()

    period = request.args.get('period')
    logs = []

    if period:
        if len(period) == 10:
            selected = datetime.strptime(period, "%Y-%m-%d").date()
            logs = DailyLog.query.filter_by(user_id=user.id, log_date=selected).all()
        elif len(period) == 7:
            year, month = map(int, period.split('-'))
            logs = DailyLog.query.filter(
                DailyLog.user_id == user.id,
                extract('year', DailyLog.log_date) == year,
                extract('month', DailyLog.log_date) == month
            ).all()
    else:
        start = today - timedelta(days=6)
        logs = DailyLog.query.filter(
            DailyLog.user_id == user.id,
            DailyLog.log_date >= start
        ).all()

    calories_consumed = sum(l.calories_consumed for l in logs)
    calories_burned = sum(l.calories_burned for l in logs)

    return render_template(
        'growth.html',
        user=user,
        profile=profile,
        calories_consumed=calories_consumed,
        calories_burned=calories_burned,
        selected_period=period
    )

# ---------------- LOGOUT ----------------
@app.route('/logout')
@login_required
def logout():
    session.clear()
    return redirect(url_for('home'))
    flash("Logged out successfully", "success")
    return redirect(url_for('home'))            


if __name__ == "__main__":
    app.run()
