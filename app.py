from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, template_folder="templates")

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
db_path = os.path.join(INSTANCE_DIR, "todo.db")

APP_ENV = os.environ.get("ENV") or os.environ.get("FLASK_ENV") or "development"
IS_PRODUCTION = APP_ENV.lower() == "production"

# Only create the local instance dir in development (Vercel FS is read-only)
if not IS_PRODUCTION:
    os.makedirs(INSTANCE_DIR, exist_ok=True)


def get_secret_key():
    """Return SECRET_KEY from env. In production this is required; in dev a random fallback is used."""
    secret_key = os.environ.get("SECRET_KEY", "").strip()
    if not secret_key:
        if IS_PRODUCTION:
            raise RuntimeError("SECRET_KEY must be set as an environment variable in production.")
        import secrets
        return secrets.token_hex(32)   # random key for local dev only
    return secret_key


def get_database_uri():
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if database_url:
        # Heroku/older providers may return 'postgres://' which SQLAlchemy 1.4+ rejects
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        return database_url
    # Local development fallback — SQLite
    return "sqlite:///" + db_path


def parse_due_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


app.config["SQLALCHEMY_DATABASE_URI"] = get_database_uri()
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = get_secret_key()
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = IS_PRODUCTION

db = SQLAlchemy(app)

# Create tables automatically on first startup (works for both SQLite and Postgres).
# flask-migrate is not used here because there is no CLI available in serverless environments.
with app.app_context():
    db.create_all()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    todos = db.relationship("Todo", backref="user", cascade="all, delete-orphan", passive_deletes=True)

    def __repr__(self):
        return f"{self.id} - {self.username}"


class Todo(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    desc = db.Column(db.String(500), nullable=False)
    time = db.Column(db.DateTime, default=datetime.utcnow)
    completed = db.Column(db.Boolean, nullable=False, default=False)
    due_date = db.Column(db.Date, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)

    def __repr__(self):
        return f"{self.sno} - {self.title}"


def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped


@app.route("/", methods=['GET', 'POST'])
@login_required
def index():
    current_user = get_current_user()
    if request.method == 'POST':
        todo_title = request.form['title']
        desc_todo = request.form['desc']
        due_date = parse_due_date(request.form.get("due_date", ""))
        data = Todo(
            title=todo_title,
            desc=desc_todo,
            user_id=current_user.id,
            due_date=due_date
        )
        db.session.add(data)
        db.session.commit()

    alltodo = Todo.query.filter_by(user_id=current_user.id).order_by(Todo.time.desc()).all()
    return render_template("index.html", alltodo=alltodo, current_user=current_user)


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("index"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not email or not password:
            error = "All fields are required."
        elif password != confirm_password:
            error = "Passwords do not match."
        elif User.query.filter_by(username=username).first():
            error = "Username already exists."
        elif User.query.filter_by(email=email).first():
            error = "Email already exists."
        else:
            password_hash = generate_password_hash(password)
            user = User(username=username, email=email, password_hash=password_hash)
            db.session.add(user)
            db.session.commit()
            session["user_id"] = user.id
            return redirect(url_for("index"))

    return render_template("register.html", error=error, current_user=None)


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("index"))

    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            error = "Invalid email or password."
        else:
            session["user_id"] = user.id
            return redirect(url_for("index"))

    return render_template("login.html", error=error, current_user=None)


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("login"))


@app.route("/update/<int:sno>", methods=['GET', 'POST'])
@login_required
def update(sno):
    current_user = get_current_user()
    todo = Todo.query.filter_by(sno=sno, user_id=current_user.id).first()
    if not todo:
        return redirect(url_for("index"))

    if request.method == 'POST':
        todo.title = request.form['title']
        todo.desc = request.form['desc']
        todo.due_date = parse_due_date(request.form.get("due_date", ""))
        todo.completed = request.form.get("completed") == "on"
        db.session.commit()
        return redirect(url_for("index"))

    return render_template('update.html', todo=todo, current_user=current_user)


@app.route("/delete/<int:sno>")
@login_required
def delete(sno):
    current_user = get_current_user()
    todo = Todo.query.filter_by(sno=sno, user_id=current_user.id).first()
    if not todo:
        return redirect(url_for("index"))
    db.session.delete(todo)
    db.session.commit()
    return redirect(url_for("index"))


@app.route("/toggle/<int:sno>", methods=["POST"])
@login_required
def toggle(sno):
    current_user = get_current_user()
    todo = Todo.query.filter_by(sno=sno, user_id=current_user.id).first()
    if not todo:
        return redirect(url_for("index"))
    todo.completed = not todo.completed
    db.session.commit()
    return redirect(url_for("index"))


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html", current_user=get_current_user()), 404


@app.errorhandler(500)
def server_error(_error):
    return render_template("500.html", current_user=get_current_user()), 500


if __name__ == "__main__" and not IS_PRODUCTION:
    app.run(debug=True)
