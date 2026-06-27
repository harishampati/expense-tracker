import os
import sqlite3
import csv
import io
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, g, jsonify, Response
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "expenseiq_super_secret_2026"

if os.environ.get("RAILWAY_ENVIRONMENT"):
    DATABASE = "/tmp/database.db"
else:
    DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")

# ── Flask-Login setup ──────────────────────────────────
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access your expenses."
login_manager.login_message_category = "danger"


class User(UserMixin):
    def __init__(self, id, username, email):
        self.id = id
        self.username = username
        self.email = email


@login_manager.user_loader
def load_user(user_id):
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    db.close()
    if user:
        return User(user["id"], user["username"], user["email"])
    return None


# ── Database ───────────────────────────────────────────

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DATABASE)
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT    NOT NULL UNIQUE,
            email    TEXT    NOT NULL UNIQUE,
            password TEXT    NOT NULL,
            budget   REAL    DEFAULT 0
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id  INTEGER NOT NULL,
            title    TEXT    NOT NULL,
            category TEXT    NOT NULL,
            amount   REAL    NOT NULL,
            date     TEXT    NOT NULL,
            note     TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    db.commit()
    db.close()


init_db()


# ── Auth Routes ────────────────────────────────────────

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        confirm  = request.form.get("confirm", "").strip()

        errors = []
        if not username: errors.append("Username is required.")
        if not email:    errors.append("Email is required.")
        if not password: errors.append("Password is required.")
        if password != confirm: errors.append("Passwords do not match.")
        if len(password) < 6:  errors.append("Password must be at least 6 characters.")

        if not errors:
            db = get_db()
            existing = db.execute(
                "SELECT id FROM users WHERE username=? OR email=?", (username, email)
            ).fetchone()
            if existing:
                errors.append("Username or email already taken.")

        if errors:
            for e in errors: flash(e, "danger")
            return render_template("register.html", form=request.form)

        db = get_db()
        db.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username, email, generate_password_hash(password))
        )
        db.commit()
        flash("Account created! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html", form={})


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()

        if not user or not check_password_hash(user["password"], password):
            flash("Invalid username or password.", "danger")
            return render_template("login.html", form=request.form)

        login_user(User(user["id"], user["username"], user["email"]))
        flash(f"Welcome back, {user['username']}!", "success")
        return redirect(url_for("index"))

    return render_template("login.html", form={})


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# ── Dashboard ──────────────────────────────────────────

@app.route("/")
@login_required
def index():
    db = get_db()
    search = request.args.get("search", "").strip()
    month  = request.args.get("month", "").strip()

    query  = "SELECT * FROM expenses WHERE user_id=?"
    params = [current_user.id]

    if search:
        query += " AND (title LIKE ? OR category LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if month:
        query += " AND strftime('%Y-%m', date) = ?"
        params.append(month)

    query += " ORDER BY date DESC"
    expenses = db.execute(query, params).fetchall()
    total    = db.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE user_id=?",
                          (current_user.id,)).fetchone()[0]

    # Monthly total for current month
    this_month = datetime.now().strftime("%Y-%m")
    month_total = db.execute(
        "SELECT COALESCE(SUM(amount),0) FROM expenses WHERE user_id=? AND strftime('%Y-%m',date)=?",
        (current_user.id, this_month)
    ).fetchone()[0]

    # Budget
    budget = db.execute("SELECT budget FROM users WHERE id=?", (current_user.id,)).fetchone()["budget"]

    return render_template("index.html",
        expenses=expenses, total=total,
        month_total=month_total, budget=budget,
        search=search, month=month
    )


# ── Charts API ─────────────────────────────────────────

@app.route("/api/chart/category")
@login_required
def chart_category():
    db = get_db()
    rows = db.execute(
        "SELECT category, SUM(amount) as total FROM expenses WHERE user_id=? GROUP BY category ORDER BY total DESC",
        (current_user.id,)
    ).fetchall()
    return jsonify({
        "labels": [r["category"] for r in rows],
        "data":   [r["total"] for r in rows]
    })


@app.route("/api/chart/monthly")
@login_required
def chart_monthly():
    db = get_db()
    rows = db.execute(
        """SELECT strftime('%Y-%m', date) as month, SUM(amount) as total
           FROM expenses WHERE user_id=?
           GROUP BY month ORDER BY month ASC LIMIT 12""",
        (current_user.id,)
    ).fetchall()
    return jsonify({
        "labels": [r["month"] for r in rows],
        "data":   [r["total"] for r in rows]
    })


# ── Add / Edit / Delete ────────────────────────────────

@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        title    = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        amount   = request.form.get("amount", "").strip()
        date     = request.form.get("date", "").strip()
        note     = request.form.get("note", "").strip()

        errors = []
        if not title:    errors.append("Title is required.")
        if not category: errors.append("Category is required.")
        if not date:     errors.append("Date is required.")
        if not amount:
            errors.append("Amount is required.")
        else:
            try:
                amount = float(amount)
                if amount <= 0: errors.append("Amount must be greater than zero.")
            except ValueError:
                errors.append("Amount must be a valid number.")

        if errors:
            for e in errors: flash(e, "danger")
            return render_template("add.html", form=request.form)

        db = get_db()
        db.execute(
            "INSERT INTO expenses (user_id, title, category, amount, date, note) VALUES (?,?,?,?,?,?)",
            (current_user.id, title, category, amount, date, note)
        )
        db.commit()
        flash("Expense added!", "success")
        return redirect(url_for("index"))

    return render_template("add.html", form={"date": datetime.now().strftime("%Y-%m-%d")})


@app.route("/edit/<int:expense_id>", methods=["GET", "POST"])
@login_required
def edit(expense_id):
    db = get_db()
    expense = db.execute(
        "SELECT * FROM expenses WHERE id=? AND user_id=?", (expense_id, current_user.id)
    ).fetchone()

    if not expense:
        flash("Expense not found.", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":
        title    = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        amount   = request.form.get("amount", "").strip()
        date     = request.form.get("date", "").strip()
        note     = request.form.get("note", "").strip()

        errors = []
        if not title:    errors.append("Title is required.")
        if not category: errors.append("Category is required.")
        if not date:     errors.append("Date is required.")
        if not amount:
            errors.append("Amount is required.")
        else:
            try:
                amount = float(amount)
                if amount <= 0: errors.append("Amount must be greater than zero.")
            except ValueError:
                errors.append("Amount must be a valid number.")

        if errors:
            for e in errors: flash(e, "danger")
            return render_template("edit.html", expense=expense, form=request.form)

        db.execute(
            "UPDATE expenses SET title=?, category=?, amount=?, date=?, note=? WHERE id=? AND user_id=?",
            (title, category, amount, date, note, expense_id, current_user.id)
        )
        db.commit()
        flash("Expense updated!", "success")
        return redirect(url_for("index"))

    return render_template("edit.html", expense=expense, form=expense)


@app.route("/delete/<int:expense_id>", methods=["POST"])
@login_required
def delete(expense_id):
    db = get_db()
    expense = db.execute(
        "SELECT id FROM expenses WHERE id=? AND user_id=?", (expense_id, current_user.id)
    ).fetchone()
    if expense:
        db.execute("DELETE FROM expenses WHERE id=?", (expense_id,))
        db.commit()
        flash("Expense deleted.", "success")
    return redirect(url_for("index"))


# ── Budget ─────────────────────────────────────────────

@app.route("/budget", methods=["POST"])
@login_required
def set_budget():
    try:
        budget = float(request.form.get("budget", 0))
        db = get_db()
        db.execute("UPDATE users SET budget=? WHERE id=?", (budget, current_user.id))
        db.commit()
        flash("Budget updated!", "success")
    except ValueError:
        flash("Invalid budget amount.", "danger")
    return redirect(url_for("index"))


# ── Export CSV ─────────────────────────────────────────

@app.route("/export")
@login_required
def export():
    db = get_db()
    expenses = db.execute(
        "SELECT title, category, amount, date, note FROM expenses WHERE user_id=? ORDER BY date DESC",
        (current_user.id,)
    ).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Title", "Category", "Amount", "Date", "Note"])
    for e in expenses:
        writer.writerow([e["title"], e["category"], e["amount"], e["date"], e["note"] or ""])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=expenses.csv"}
    )


# ── Entry point ────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=False, host="0.0.0.0", port=port)
