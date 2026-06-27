import os
import sqlite3
import csv
import io
import traceback
import logging
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, flash, g, jsonify, Response
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "expenseiq_pro_secret_2026"

logging.basicConfig(filename=os.path.join(os.path.dirname(os.path.abspath(__file__)), "error.log"), level=logging.ERROR)

@app.errorhandler(500)
def handle_500(e):
    tb = traceback.format_exc()
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "error.log"), "a") as f:
        f.write(f"\n--- 500 on {request.url} ---\n{tb}\n")
    return render_template("error.html"), 500

if os.environ.get("RAILWAY_ENVIRONMENT"):
    DATABASE = "/tmp/database.db"
else:
    DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to continue."
login_manager.login_message_category = "danger"

CATEGORIES = ["Food", "Transport", "Housing", "Health", "Entertainment", "Shopping", "Education", "Other"]
INCOME_CATEGORIES = ["Salary", "Freelance", "Investment", "Gift", "Other Income"]

class User(UserMixin):
    def __init__(self, id, username, email):
        self.id = id
        self.username = username
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    db.close()
    if user:
        return User(user["id"], user["username"], user["email"])
    return None

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
    db.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        balance REAL DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        account_id INTEGER,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        amount REAL NOT NULL,
        type TEXT NOT NULL DEFAULT 'expense',
        date TEXT NOT NULL,
        note TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        amount REAL NOT NULL,
        month TEXT NOT NULL,
        UNIQUE(user_id, category, month)
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS recurring (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        amount REAL NOT NULL,
        type TEXT NOT NULL DEFAULT 'expense',
        frequency TEXT NOT NULL,
        next_date TEXT NOT NULL,
        account_id INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")
    db.commit()
    db.close()

init_db()

# ── Auth ───────────────────────────────────────────────

@app.route("/register", methods=["GET","POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username","").strip()
        email    = request.form.get("email","").strip()
        password = request.form.get("password","").strip()
        confirm  = request.form.get("confirm","").strip()
        errors = []
        if not username: errors.append("Username is required.")
        if not email:    errors.append("Email is required.")
        if len(password) < 6: errors.append("Password must be at least 6 characters.")
        if password != confirm: errors.append("Passwords do not match.")
        if not errors:
            db = get_db()
            if db.execute("SELECT id FROM users WHERE username=? OR email=?", (username,email)).fetchone():
                errors.append("Username or email already taken.")
        if errors:
            for e in errors: flash(e, "danger")
            return render_template("register.html", form=request.form)
        db = get_db()
        db.execute("INSERT INTO users (username,email,password) VALUES (?,?,?)",
                   (username, email, generate_password_hash(password)))
        db.commit()
        flash("Account created! Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html", form={})

@app.route("/login", methods=["GET","POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","").strip()
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username=? OR email=?", (username, username)).fetchone()
        if not user or not check_password_hash(user["password"], password):
            flash("Invalid username or password.", "danger")
            return render_template("login.html", form=request.form)
        login_user(User(user["id"], user["username"], user["email"]))
        return redirect(url_for("index"))
    return render_template("login.html", form={})

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# ── Dashboard ──────────────────────────────────────────

@app.route("/")
@login_required
def index():
    db = get_db()
    uid = current_user.id
    this_month = datetime.now().strftime("%Y-%m")

    transactions = db.execute(
        "SELECT t.*, a.name as account_name FROM transactions t LEFT JOIN accounts a ON t.account_id=a.id WHERE t.user_id=? ORDER BY t.date DESC LIMIT 10",
        (uid,)
    ).fetchall()

    total_income = db.execute(
        "SELECT COALESCE(SUM(amount),0) FROM transactions WHERE user_id=? AND type='income'", (uid,)
    ).fetchone()[0]
    total_expense = db.execute(
        "SELECT COALESCE(SUM(amount),0) FROM transactions WHERE user_id=? AND type='expense'", (uid,)
    ).fetchone()[0]
    month_income = db.execute(
        "SELECT COALESCE(SUM(amount),0) FROM transactions WHERE user_id=? AND type='income' AND strftime('%Y-%m',date)=?",
        (uid, this_month)
    ).fetchone()[0]
    month_expense = db.execute(
        "SELECT COALESCE(SUM(amount),0) FROM transactions WHERE user_id=? AND type='expense' AND strftime('%Y-%m',date)=?",
        (uid, this_month)
    ).fetchone()[0]

    accounts = db.execute("SELECT * FROM accounts WHERE user_id=?", (uid,)).fetchall()
    total_balance = sum(a["balance"] for a in accounts)

    budgets = db.execute("SELECT * FROM budgets WHERE user_id=? AND month=?", (uid, this_month)).fetchall()
    budget_data = []
    for b in budgets:
        spent = db.execute(
            "SELECT COALESCE(SUM(amount),0) FROM transactions WHERE user_id=? AND category=? AND type='expense' AND strftime('%Y-%m',date)=?",
            (uid, b["category"], this_month)
        ).fetchone()[0]
        pct = min(int(spent / b["amount"] * 100), 100) if b["amount"] > 0 else 0
        budget_data.append({"category": b["category"], "budget": b["amount"], "spent": spent, "pct": pct})

    recurring = db.execute("SELECT * FROM recurring WHERE user_id=? ORDER BY next_date ASC LIMIT 5", (uid,)).fetchall()

    return render_template("index.html",
        transactions=transactions,
        total_income=total_income, total_expense=total_expense,
        month_income=month_income, month_expense=month_expense,
        total_balance=total_balance, accounts=accounts,
        budget_data=budget_data, recurring=recurring,
        this_month=this_month
    )

# ── Transactions ───────────────────────────────────────

@app.route("/transactions")
@login_required
def transactions():
    db = get_db()
    uid = current_user.id
    search   = request.args.get("search","").strip()
    ftype    = request.args.get("type","").strip()
    fcategory= request.args.get("category","").strip()

    query  = "SELECT t.*, a.name as account_name FROM transactions t LEFT JOIN accounts a ON t.account_id=a.id WHERE t.user_id=?"
    params = [uid]
    if search:
        query += " AND (t.title LIKE ? OR t.category LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if ftype:
        query += " AND t.type=?"
        params.append(ftype)
    if fcategory:
        query += " AND t.category=?"
        params.append(fcategory)
    query += " ORDER BY t.date DESC"

    rows  = db.execute(query, params).fetchall()
    accounts = db.execute("SELECT * FROM accounts WHERE user_id=?", (uid,)).fetchall()
    return render_template("transactions.html",
        transactions=rows, accounts=accounts,
        search=search, ftype=ftype, fcategory=fcategory,
        categories=CATEGORIES, income_categories=INCOME_CATEGORIES
    )

@app.route("/add", methods=["GET","POST"])
@login_required
def add():
    db = get_db()
    uid = current_user.id
    accounts = db.execute("SELECT * FROM accounts WHERE user_id=?", (uid,)).fetchall()

    if request.method == "POST":
        title      = request.form.get("title","").strip()
        category   = request.form.get("category","").strip()
        amount     = request.form.get("amount","").strip()
        ttype      = request.form.get("type","expense")
        date_val   = request.form.get("date","").strip()
        note       = request.form.get("note","").strip()
        account_id = request.form.get("account_id","").strip() or None

        errors = []
        if not title:    errors.append("Title is required.")
        if not category: errors.append("Category is required.")
        if not date_val: errors.append("Date is required.")
        if not amount:
            errors.append("Amount is required.")
        else:
            try:
                amount = float(amount)
                if amount <= 0: errors.append("Amount must be greater than zero.")
            except ValueError:
                errors.append("Invalid amount.")

        if errors:
            for e in errors: flash(e, "danger")
            return render_template("add.html", form=request.form, accounts=accounts,
                                   categories=CATEGORIES, income_categories=INCOME_CATEGORIES)

        db.execute("INSERT INTO transactions (user_id,account_id,title,category,amount,type,date,note) VALUES (?,?,?,?,?,?,?,?)",
                   (uid, account_id, title, category, amount, ttype, date_val, note))
        if account_id:
            if ttype == "income":
                db.execute("UPDATE accounts SET balance=balance+? WHERE id=? AND user_id=?", (amount, account_id, uid))
            else:
                db.execute("UPDATE accounts SET balance=balance-? WHERE id=? AND user_id=?", (amount, account_id, uid))
        db.commit()
        flash("Transaction added!", "success")
        return redirect(url_for("index"))

    return render_template("add.html", form={"date": date.today().strftime("%Y-%m-%d")},
                           accounts=accounts, categories=CATEGORIES, income_categories=INCOME_CATEGORIES)

@app.route("/edit/<int:tid>", methods=["GET","POST"])
@login_required
def edit(tid):
    db = get_db()
    uid = current_user.id
    tx = db.execute("SELECT * FROM transactions WHERE id=? AND user_id=?", (tid, uid)).fetchone()
    if not tx:
        flash("Not found.", "danger")
        return redirect(url_for("transactions"))

    accounts = db.execute("SELECT * FROM accounts WHERE user_id=?", (uid,)).fetchall()

    if request.method == "POST":
        title      = request.form.get("title","").strip()
        category   = request.form.get("category","").strip()
        amount     = request.form.get("amount","").strip()
        ttype      = request.form.get("type","expense")
        date_val   = request.form.get("date","").strip()
        note       = request.form.get("note","").strip()
        account_id = request.form.get("account_id","").strip() or None

        errors = []
        if not title:    errors.append("Title is required.")
        if not category: errors.append("Category is required.")
        if not date_val: errors.append("Date is required.")
        if not amount:
            errors.append("Amount is required.")
        else:
            try:
                amount = float(amount)
                if amount <= 0: errors.append("Amount must be > 0.")
            except ValueError:
                errors.append("Invalid amount.")

        if errors:
            for e in errors: flash(e, "danger")
            return render_template("edit.html", tx=tx, form=request.form, accounts=accounts,
                                   categories=CATEGORIES, income_categories=INCOME_CATEGORIES)

        # reverse old account balance effect
        if tx["account_id"]:
            if tx["type"] == "income":
                db.execute("UPDATE accounts SET balance=balance-? WHERE id=? AND user_id=?", (tx["amount"], tx["account_id"], uid))
            else:
                db.execute("UPDATE accounts SET balance=balance+? WHERE id=? AND user_id=?", (tx["amount"], tx["account_id"], uid))

        db.execute("UPDATE transactions SET title=?,category=?,amount=?,type=?,date=?,note=?,account_id=? WHERE id=? AND user_id=?",
                   (title, category, amount, ttype, date_val, note, account_id, tid, uid))

        if account_id:
            if ttype == "income":
                db.execute("UPDATE accounts SET balance=balance+? WHERE id=? AND user_id=?", (amount, account_id, uid))
            else:
                db.execute("UPDATE accounts SET balance=balance-? WHERE id=? AND user_id=?", (amount, account_id, uid))

        db.commit()
        flash("Transaction updated!", "success")
        return redirect(url_for("transactions"))

    return render_template("edit.html", tx=tx, form=tx, accounts=accounts,
                           categories=CATEGORIES, income_categories=INCOME_CATEGORIES)

@app.route("/delete/<int:tid>", methods=["POST"])
@login_required
def delete(tid):
    db = get_db()
    uid = current_user.id
    tx = db.execute("SELECT * FROM transactions WHERE id=? AND user_id=?", (tid, uid)).fetchone()
    if tx:
        if tx["account_id"]:
            if tx["type"] == "income":
                db.execute("UPDATE accounts SET balance=balance-? WHERE id=? AND user_id=?", (tx["amount"], tx["account_id"], uid))
            else:
                db.execute("UPDATE accounts SET balance=balance+? WHERE id=? AND user_id=?", (tx["amount"], tx["account_id"], uid))
        db.execute("DELETE FROM transactions WHERE id=?", (tid,))
        db.commit()
        flash("Deleted.", "success")
    return redirect(url_for("transactions"))

# ── Accounts ───────────────────────────────────────────

@app.route("/accounts", methods=["GET","POST"])
@login_required
def accounts():
    db = get_db()
    uid = current_user.id
    if request.method == "POST":
        name    = request.form.get("name","").strip()
        atype   = request.form.get("type","Bank")
        balance = float(request.form.get("balance",0) or 0)
        if name:
            db.execute("INSERT INTO accounts (user_id,name,type,balance) VALUES (?,?,?,?)", (uid,name,atype,balance))
            db.commit()
            flash("Account added!", "success")
        return redirect(url_for("accounts"))

    rows = db.execute("SELECT * FROM accounts WHERE user_id=?", (uid,)).fetchall()
    return render_template("accounts.html", accounts=rows)

@app.route("/accounts/delete/<int:aid>", methods=["POST"])
@login_required
def delete_account(aid):
    db = get_db()
    db.execute("DELETE FROM accounts WHERE id=? AND user_id=?", (aid, current_user.id))
    db.commit()
    flash("Account removed.", "success")
    return redirect(url_for("accounts"))

# ── Budgets ────────────────────────────────────────────

@app.route("/budgets", methods=["GET","POST"])
@login_required
def budgets():
    db = get_db()
    uid = current_user.id
    this_month = datetime.now().strftime("%Y-%m")

    if request.method == "POST":
        category = request.form.get("category","")
        amount   = float(request.form.get("amount",0) or 0)
        if category and amount > 0:
            db.execute("INSERT OR REPLACE INTO budgets (user_id,category,amount,month) VALUES (?,?,?,?)",
                       (uid, category, amount, this_month))
            db.commit()
            flash("Budget set!", "success")
        return redirect(url_for("budgets"))

    rows = db.execute("SELECT * FROM budgets WHERE user_id=? AND month=?", (uid, this_month)).fetchall()
    budget_data = []
    for b in rows:
        spent = db.execute(
            "SELECT COALESCE(SUM(amount),0) FROM transactions WHERE user_id=? AND category=? AND type='expense' AND strftime('%Y-%m',date)=?",
            (uid, b["category"], this_month)
        ).fetchone()[0]
        pct = min(int(spent / b["amount"] * 100), 100) if b["amount"] > 0 else 0
        budget_data.append({"id": b["id"], "category": b["category"], "budget": b["amount"], "spent": spent, "pct": pct})

    return render_template("budgets.html", budget_data=budget_data, categories=CATEGORIES, this_month=this_month)

@app.route("/budgets/delete/<int:bid>", methods=["POST"])
@login_required
def delete_budget(bid):
    db = get_db()
    db.execute("DELETE FROM budgets WHERE id=? AND user_id=?", (bid, current_user.id))
    db.commit()
    flash("Budget removed.", "success")
    return redirect(url_for("budgets"))

# ── Recurring ──────────────────────────────────────────

@app.route("/recurring", methods=["GET","POST"])
@login_required
def recurring():
    db = get_db()
    uid = current_user.id
    accounts = db.execute("SELECT * FROM accounts WHERE user_id=?", (uid,)).fetchall()

    if request.method == "POST":
        title      = request.form.get("title","").strip()
        category   = request.form.get("category","")
        amount     = float(request.form.get("amount",0) or 0)
        rtype      = request.form.get("type","expense")
        frequency  = request.form.get("frequency","monthly")
        next_date  = request.form.get("next_date","")
        account_id = request.form.get("account_id","") or None
        if title and amount > 0 and next_date:
            db.execute("INSERT INTO recurring (user_id,title,category,amount,type,frequency,next_date,account_id) VALUES (?,?,?,?,?,?,?,?)",
                       (uid, title, category, amount, rtype, frequency, next_date, account_id))
            db.commit()
            flash("Recurring transaction added!", "success")
        return redirect(url_for("recurring"))

    rows = db.execute("SELECT * FROM recurring WHERE user_id=? ORDER BY next_date ASC", (uid,)).fetchall()
    return render_template("recurring.html", recurring=rows, accounts=accounts,
                           categories=CATEGORIES, income_categories=INCOME_CATEGORIES)

@app.route("/recurring/delete/<int:rid>", methods=["POST"])
@login_required
def delete_recurring(rid):
    db = get_db()
    db.execute("DELETE FROM recurring WHERE id=? AND user_id=?", (rid, current_user.id))
    db.commit()
    flash("Removed.", "success")
    return redirect(url_for("recurring"))

# ── Reports ────────────────────────────────────────────

@app.route("/reports")
@login_required
def reports():
    db = get_db()
    uid = current_user.id
    selected_month = request.args.get("month", datetime.now().strftime("%Y-%m"))

    income   = db.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE user_id=? AND type='income' AND strftime('%Y-%m',date)=?", (uid, selected_month)).fetchone()[0]
    expenses = db.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE user_id=? AND type='expense' AND strftime('%Y-%m',date)=?", (uid, selected_month)).fetchone()[0]
    savings  = income - expenses
    tx_count = db.execute("SELECT COUNT(*) FROM transactions WHERE user_id=? AND strftime('%Y-%m',date)=?", (uid, selected_month)).fetchone()[0]

    by_cat_rows = db.execute(
        "SELECT category, SUM(amount) as total FROM transactions WHERE user_id=? AND type='expense' AND strftime('%Y-%m',date)=? GROUP BY category ORDER BY total DESC",
        (uid, selected_month)
    ).fetchall()

    category_rows = []
    for r in by_cat_rows:
        pct = round(r["total"] / expenses * 100) if expenses > 0 else 0
        category_rows.append({"category": r["category"], "total": r["total"], "pct": pct})

    chart_data = {
        "labels": [r["category"] for r in category_rows],
        "values": [r["total"] for r in category_rows]
    }

    month_txs = db.execute(
        "SELECT t.*, a.name as account_name FROM transactions t LEFT JOIN accounts a ON t.account_id=a.id WHERE t.user_id=? AND strftime('%Y-%m',t.date)=? ORDER BY t.date DESC",
        (uid, selected_month)
    ).fetchall()

    return render_template("reports.html",
        selected_month=selected_month, income=income, expenses=expenses,
        savings=savings, tx_count=tx_count,
        category_rows=category_rows, chart_data=chart_data, month_txs=month_txs
    )

# ── Chart APIs ─────────────────────────────────────────

@app.route("/api/chart/category")
@login_required
def chart_category():
    db = get_db()
    rows = db.execute(
        "SELECT category, SUM(amount) as total FROM transactions WHERE user_id=? AND type='expense' GROUP BY category ORDER BY total DESC",
        (current_user.id,)
    ).fetchall()
    return jsonify({"labels": [r["category"] for r in rows], "data": [r["total"] for r in rows]})

@app.route("/api/chart/monthly")
@login_required
def chart_monthly():
    db = get_db()
    rows = db.execute(
        "SELECT strftime('%Y-%m',date) as month, SUM(CASE WHEN type='income' THEN amount ELSE 0 END) as income, SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) as expense FROM transactions WHERE user_id=? GROUP BY month ORDER BY month ASC LIMIT 12",
        (current_user.id,)
    ).fetchall()
    return jsonify({
        "labels":   [r["month"] for r in rows],
        "income":   [r["income"] for r in rows],
        "expense":  [r["expense"] for r in rows]
    })

# ── Export ─────────────────────────────────────────────

@app.route("/export")
@login_required
def export():
    db = get_db()
    rows = db.execute(
        "SELECT title,category,amount,type,date,note FROM transactions WHERE user_id=? ORDER BY date DESC",
        (current_user.id,)
    ).fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Title","Category","Amount","Type","Date","Note"])
    for r in rows:
        writer.writerow([r["title"],r["category"],r["amount"],r["type"],r["date"],r["note"] or ""])
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=expenseiq_export.csv"})

# ── Entry point ────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(debug=False, host="0.0.0.0", port=port)
