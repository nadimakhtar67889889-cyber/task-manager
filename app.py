from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'super-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ================= MODELS =================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    is_premium = db.Column(db.Boolean, default=False)
    
    # Premium Feature: Streak Tracking
    current_streak = db.Column(db.Integer, default=0)
    last_login_date = db.Column(db.Date, nullable=True)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    priority = db.Column(db.String(50), default='Normal') # High, Normal, Low
    category = db.Column(db.String(100), nullable=True)
    is_completed = db.Column(db.Boolean, default=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ================= ROUTES =================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists.')
            return redirect(url_for('register'))
            
        hashed_pw = generate_password_hash(password, method='sha256')
        new_user = User(username=username, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            
            # Premium Feature: Update Streak on Login
            today = date.today()
            if user.last_login_date == today - timedelta(days=1):
                user.current_streak += 1
            elif user.last_login_date != today:
                user.current_streak = 1 # Reset if they missed a day
            user.last_login_date = today
            db.session.commit()
            
            return redirect(url_for('dashboard'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    query = Task.query.filter_by(user_id=current_user.id)
    
    # Premium Feature: Smart Focus & Search/Filter
    if current_user.is_premium:
        search_query = request.args.get('search')
        focus_mode = request.args.get('focus')
        
        if search_query:
            query = query.filter(Task.title.contains(search_query))
        if focus_mode == 'true':
            query = query.filter_by(priority='High')

    tasks = query.all()
    
    # Premium Feature: Analytics
    total_tasks = len(tasks)
    completed_tasks = len([t for t in tasks if t.is_completed])
    completion_rate = round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0

    return render_template('dashboard.html', 
                           tasks=tasks, 
                           completion_rate=completion_rate)

@app.route('/add_task', methods=['POST'])
@login_required
def add_task():
    # FREE TIER LIMIT: Max 5 active tasks
    active_tasks_count = Task.query.filter_by(user_id=current_user.id, is_completed=False).count()
    
    if not current_user.is_premium and active_tasks_count >= 5:
        flash('Free limit reached (5 active tasks). Upgrade to Premium to add more!', 'warning')
        return redirect(url_for('subscribe'))
        
    title = request.form.get('title')
    priority = request.form.get('priority', 'Normal')
    category = request.form.get('category', 'General')
    
    new_task = Task(title=title, priority=priority, category=category, user_id=current_user.id)
    db.session.add(new_task)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/complete_task/<int:task_id>')
@login_required
def complete_task(task_id):
    task = Task.query.get(task_id)
    if task and task.user_id == current_user.id:
        task.is_completed = not task.is_completed # Toggle completion
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/subscribe', methods=['GET', 'POST'])
@login_required
def subscribe():
    # Mock payment/upgrade route
    if request.method == 'POST':
        current_user.is_premium = True
        db.session.commit()
        flash('Welcome to Premium! 💎', 'success')
        return redirect(url_for('dashboard'))
    return render_template('subscribe.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # Use port 5000 for local, Render will dynamically assign via environment variables
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)