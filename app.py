from flask import Flask, render_template_string, redirect, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'taskora_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# ---------------- DATABASE ----------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    plan = db.Column(db.String(20), default="Free")
    streak = db.Column(db.Integer, default=0)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200))
    due_date = db.Column(db.String(50))
    due_time = db.Column(db.String(20))
    priority = db.Column(db.String(20))
    category = db.Column(db.String(50))
    focus_minutes = db.Column(db.Integer)
    status = db.Column(db.String(20), default="Pending")
    created_date = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------- HOME ----------------

@app.route('/')
def home():
    return render_template_string("""
    <h1>🚀 Taskora</h1>
    <p>Smart Productivity System</p>
    <a href="/login">Login</a> |
    <a href="/register">Register</a>
    """)

# ---------------- REGISTER ----------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hashed_password = generate_password_hash(request.form['password'])
        user = User(username=request.form['username'], password=hashed_password)
        db.session.add(user)
        db.session.commit()
        return redirect('/login')

    return render_template_string("""
    <h2>Register</h2>
    <form method="POST">
        <input name="username" required placeholder="Username"><br><br>
        <input name="password" type="password" required placeholder="Password"><br><br>
        <button>Register</button>
    </form>
    """)

# ---------------- LOGIN ----------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect('/dashboard')

    return render_template_string("""
    <h2>Login</h2>
    <form method="POST">
        <input name="username" required><br><br>
        <input name="password" type="password" required><br><br>
        <button>Login</button>
    </form>
    """)

# ---------------- DASHBOARD ----------------

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():

    tasks = Task.query.filter_by(user_id=current_user.id).all()

    if request.method == 'POST':
        if current_user.plan == "Free" and len(tasks) >= 5:
            return "<h3>Free plan allows only 5 tasks. Upgrade.</h3><a href='/subscribe'>Upgrade</a>"

        task = Task(
            content=request.form['task'],
            due_date=request.form['due_date'],
            due_time=request.form['due_time'],
            priority=request.form['priority'],
            category=request.form['category'],
            focus_minutes=int(request.form['focus_minutes']),
            created_date=str(datetime.today().date()),
            user_id=current_user.id
        )
        db.session.add(task)
        db.session.commit()

    tasks = Task.query.filter_by(user_id=current_user.id).all()

    total_tasks = len(tasks)
    completed_tasks = len([t for t in tasks if t.status == "Completed"])
    total_focus = sum([t.focus_minutes or 0 for t in tasks])

    completion_rate = 0
    if total_tasks > 0:
        completion_rate = round((completed_tasks / total_tasks) * 100, 2)

    return render_template_string("""
    <h2>Welcome {{ current_user.username }}</h2>

    <p><b>Plan:</b> {{ current_user.plan }}</p>
    {% if current_user.plan == "Free" %}
        <a href="/subscribe">Upgrade</a>
    {% endif %}

    <h3>Productivity Summary</h3>
    Total Tasks: {{ total_tasks }}<br>
    Completed: {{ completed_tasks }}<br>
    Completion Rate: {{ completion_rate }}%<br>
    Focus Minutes: {{ total_focus }}<br>

    {% if current_user.plan != "Free" %}
        🔥 Streak: {{ current_user.streak }}
    {% endif %}

    <hr>

    <form method="POST">
        <input name="task" required placeholder="Task"><br><br>
        <input type="date" name="due_date"><br><br>
        <input type="time" name="due_time"><br><br>

        <select name="priority">
            <option>Low</option>
            <option>Medium</option>
            <option>High</option>
        </select><br><br>

        <input name="category" placeholder="Category"><br><br>
        <input type="number" name="focus_minutes" placeholder="Focus Minutes"><br><br>

        <button>Add Task</button>
    </form>

    <hr>

    {% for task in tasks %}
        <b>{{ task.content }}</b> |
        {{ task.priority }} |
        {{ task.category }} |
        {{ task.status }}

        {% if task.status == "Pending" %}
            <a href="/complete/{{ task.id }}">Complete</a>
        {% endif %}

        | <a href="/delete/{{ task.id }}">Delete</a>
        <br><br>
    {% endfor %}

    <a href="/logout">Logout</a>
    """,
    tasks=tasks,
    total_tasks=total_tasks,
    completed_tasks=completed_tasks,
    total_focus=total_focus,
    completion_rate=completion_rate)

# ---------------- COMPLETE ----------------

@app.route('/complete/<int:id>')
@login_required
def complete(id):
    task = Task.query.get(id)
    task.status = "Completed"

    if current_user.plan != "Free":
        current_user.streak += 1

    db.session.commit()
    return redirect('/dashboard')

# ---------------- DELETE ----------------

@app.route('/delete/<int:id>')
@login_required
def delete(id):
    task = Task.query.get(id)
    db.session.delete(task)
    db.session.commit()
    return redirect('/dashboard')

# ---------------- SUBSCRIBE ----------------

@app.route('/subscribe')
@login_required
def subscribe():
    return """
    <h2>Upgrade to Taskora 💎</h2>

    <h3>Premium ₹49/month</h3>
    <h3>Lifetime ₹499</h3>

    <p>Pay via UPI:</p>
    <b>7970583321@upi</b>

    <br><br>

    <a href="upi://pay?pa=7970583321@upi&pn=Taskora&am=49&cu=INR">
        Pay ₹49 Now
    </a>

    <p>After payment, contact admin to activate.</p>

    <a href="/dashboard">Back</a>
    """

# ---------------- LOGOUT ----------------

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')

# ---------------- RUN ----------------

import os

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))


