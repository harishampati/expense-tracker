ExpenseIQ - Personal Finance Tracker

A full-featured personal finance web app built with Python and Flask. Track income and expenses, manage multiple accounts, and get a clear picture of your spending.

## Features

- User accounts - register, log in, and keep your data private
- Multiple accounts - manage different wallets, bank accounts, or cash pots
- Expense and income tracking - log transactions with categories, dates, and notes
- Dashboard - see your total balance and recent transactions at a glance
- CSV export - download your transaction history as a spreadsheet
- Responsive design - works on desktop and mobile
- One-click launcher - Start Expense Tracker.bat opens the app instantly on Windows

## Tech Stack

- Backend: Python 3, Flask
- Auth: Flask-Login, Werkzeug
- Database: SQLite
- Frontend: HTML, Jinja2, Bootstrap
- Deployment: Railway (Procfile included)

## Project Structure

expense-tracker/
- app.py                     - All routes, models, and database logic
- requirements.txt           - Python dependencies
- Procfile                   - Railway deployment config
- launch_app.pyw             - Silent Windows launcher
- Start Expense Tracker.bat  - One-click Windows startup script
- templates/                 - Jinja2 HTML templates
- static/                    - CSS and static assets

## Setup and Run

1. Clone the repository
   git clone https://github.com/harishampati/expense-tracker.git
   cd expense-tracker

2. Create a virtual environment
   python -m venv venv
   venv\Scripts\activate       (Windows)
   source venv/bin/activate    (macOS / Linux)

3. Install dependencies
   pip install -r requirements.txt

4. Run the app
   python app.py

Then open http://127.0.0.1:5000 in your browser.
On Windows you can also double-click Start Expense Tracker.bat to launch it instantly.

## Expense Categories

Food, Transport, Housing, Health, Entertainment, Shopping, Education, Other

## Income Categories

Salary, Freelance, Investment, Gift, Other Income

## Deployment

The project includes a Procfile for one-command deployment to Railway (https://railway.app).
The app automatically detects the Railway environment and stores the SQLite database in the correct persistent volume.

## License

MIT - free to use and modify.
