# Expense Tracker

A simple, clean web application for tracking personal expenses — built with Python, Flask, SQLite, and Bootstrap 5.

## Features

- Dashboard with a full list of expenses and total amount spent
- Add, edit, and delete expenses
- Search expenses by title or category
- Flash messages for user feedback
- Fully responsive layout (mobile-friendly)

## Tech Stack

| Layer     | Technology          |
|-----------|---------------------|
| Backend   | Python 3, Flask     |
| Database  | SQLite (built-in)   |
| Frontend  | HTML, Bootstrap 5   |
| Templating| Jinja2              |

## Project Structure

```
expense_tracker/
├── app.py              # Flask application & routes
├── database.db         # SQLite database (auto-created on first run)
├── requirements.txt    # Python dependencies
├── README.md
├── templates/
│   ├── base.html       # Shared layout (navbar, flash messages, footer)
│   ├── index.html      # Dashboard
│   ├── add.html        # Add expense form
│   └── edit.html       # Edit expense form
└── static/
    └── style.css       # Custom styles
```

## Setup & Run

### 1. Clone or download the project

```bash
cd expense_tracker
```

### 2. (Optional) Create a virtual environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the application

```bash
python app.py
```

### 5. Open in your browser

```
http://127.0.0.1:5000
```

The SQLite database (`database.db`) is created automatically on first run — no setup required.

## Expense Fields

| Field    | Type   | Description               |
|----------|--------|---------------------------|
| Title    | Text   | Short description          |
| Category | Select | Food, Transport, Health… |
| Amount   | Number | Cost in dollars            |
| Date     | Date   | When the expense occurred  |

## Notes

- No external database required — SQLite is part of Python's standard library.
- Debug mode is enabled by default (`debug=True`). Disable it in production.
