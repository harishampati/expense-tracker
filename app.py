import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, g

app = Flask(__name__)
app.secret_key = "expense_tracker_secret_key"

DATABASE = "database.db"


# ---------- Database helpers ----------

def get_db():
    """Open a database connection for the current request."""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row  # rows behave like dicts
    return g.db


@app.teardown_appcontext
def close_db(error):
    """Close the database connection at the end of each request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create the expenses table if it doesn't already exist."""
    db = sqlite3.connect(DATABASE)
    db.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            title    TEXT    NOT NULL,
            category TEXT    NOT NULL,
            amount   REAL    NOT NULL,
            date     TEXT    NOT NULL
        )
    """)
    db.commit()
    db.close()


# ---------- Routes ----------

@app.route("/")
def index():
    """Dashboard: list all expenses with optional search, show total."""
    db = get_db()
    search = request.args.get("search", "").strip()

    if search:
        rows = db.execute(
            """SELECT * FROM expenses
               WHERE title LIKE ? OR category LIKE ?
               ORDER BY date DESC""",
            (f"%{search}%", f"%{search}%"),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM expenses ORDER BY date DESC"
        ).fetchall()

    total = db.execute("SELECT COALESCE(SUM(amount), 0) FROM expenses").fetchone()[0]

    return render_template("index.html", expenses=rows, total=total, search=search)


@app.route("/add", methods=["GET", "POST"])
def add():
    """Show the add-expense form and handle submission."""
    if request.method == "POST":
        title    = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        amount   = request.form.get("amount", "").strip()
        date     = request.form.get("date", "").strip()

        # Basic validation
        errors = []
        if not title:
            errors.append("Title is required.")
        if not category:
            errors.append("Category is required.")
        if not amount:
            errors.append("Amount is required.")
        else:
            try:
                amount = float(amount)
                if amount <= 0:
                    errors.append("Amount must be greater than zero.")
            except ValueError:
                errors.append("Amount must be a valid number.")
        if not date:
            errors.append("Date is required.")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("add.html", form=request.form)

        db = get_db()
        db.execute(
            "INSERT INTO expenses (title, category, amount, date) VALUES (?, ?, ?, ?)",
            (title, category, amount, date),
        )
        db.commit()
        flash("Expense added successfully!", "success")
        return redirect(url_for("index"))

    return render_template("add.html", form={})


@app.route("/edit/<int:expense_id>", methods=["GET", "POST"])
def edit(expense_id):
    """Show the edit form pre-filled with existing data, handle updates."""
    db = get_db()
    expense = db.execute(
        "SELECT * FROM expenses WHERE id = ?", (expense_id,)
    ).fetchone()

    if expense is None:
        flash("Expense not found.", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":
        title    = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        amount   = request.form.get("amount", "").strip()
        date     = request.form.get("date", "").strip()

        errors = []
        if not title:
            errors.append("Title is required.")
        if not category:
            errors.append("Category is required.")
        if not amount:
            errors.append("Amount is required.")
        else:
            try:
                amount = float(amount)
                if amount <= 0:
                    errors.append("Amount must be greater than zero.")
            except ValueError:
                errors.append("Amount must be a valid number.")
        if not date:
            errors.append("Date is required.")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("edit.html", expense=expense, form=request.form)

        db.execute(
            "UPDATE expenses SET title=?, category=?, amount=?, date=? WHERE id=?",
            (title, category, amount, date, expense_id),
        )
        db.commit()
        flash("Expense updated successfully!", "success")
        return redirect(url_for("index"))

    return render_template("edit.html", expense=expense, form=expense)


@app.route("/delete/<int:expense_id>", methods=["POST"])
def delete(expense_id):
    """Delete an expense by ID."""
    db = get_db()
    expense = db.execute(
        "SELECT id FROM expenses WHERE id = ?", (expense_id,)
    ).fetchone()

    if expense is None:
        flash("Expense not found.", "danger")
    else:
        db.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        db.commit()
        flash("Expense deleted successfully!", "success")

    return redirect(url_for("index"))


# ---------- Entry point ----------

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=False, host="0.0.0.0", port=port)
