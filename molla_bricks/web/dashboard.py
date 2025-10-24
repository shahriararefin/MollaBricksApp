# molla_bricks/web/dashboard.py
from flask import Blueprint, render_template, request # <-- ADDED 'request' HERE
from molla_bricks.web import db_controller_instance
from datetime import datetime, timedelta

bp = Blueprint('dashboard', __name__, url_prefix='/')

@bp.route('/')
def index():
    """Renders the main dashboard homepage."""
    
    # Get filter period from URL, default to 'This Month'
    period = request.args.get('period', 'This Month')
    start_date, end_date = _get_date_range(period)
    
    # --- 1. Get Financial Card Data ---
    nagad_where, expense_where, salary_where, params = ("", "", "", ())
    if start_date and end_date:
        nagad_where = "WHERE date(timestamp) BETWEEN ? AND ?"
        expense_where = "WHERE date(expense_date) BETWEEN ? AND ?"
        salary_where = "WHERE date(payment_date) BETWEEN ? AND ?"
        params = (start_date, end_date)

    revenue = db_controller_instance.execute_query(f"SELECT SUM(total_amount) FROM nagad_khata {nagad_where}", params, fetch="one")[0] or 0
    total_dues = db_controller_instance.execute_query(f"SELECT SUM(due_amount) FROM nagad_khata {nagad_where}", params, fetch="one")[0] or 0
    salary_expense = db_controller_instance.execute_query(f"SELECT SUM(paid_amount) FROM salary_payments {salary_where}", params, fetch="one")[0] or 0
    contractor_expense = db_controller_instance.execute_query(f"SELECT SUM(amount) FROM contractor_payments {salary_where}", params, fetch="one")[0] or 0
    daily_expense = db_controller_instance.execute_query(f"SELECT SUM(amount) FROM daily_expenses {expense_where}", params, fetch="one")[0] or 0

    total_expenses = salary_expense + contractor_expense + daily_expense
    net_profit = revenue - total_expenses
    
    summary_data = {
        'revenue': revenue,
        'total_dues': total_dues,
        'total_expenses': total_expenses,
        'net_profit': net_profit,
        'period': period
    }

    # --- 2. Get Alerts ---
    alerts = _get_alerts()
    
    return render_template('dashboard.html', summary=summary_data, alerts=alerts)

def _get_date_range(period):
    today = datetime.now().date()
    if period == "Today": return today.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')
    elif period == "This Week": return (today - timedelta(days=today.weekday())).strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')
    elif period == "This Month": return today.replace(day=1).strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')
    elif period == "This Year": return today.replace(month=1, day=1).strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')
    else: return None, None # All Time

def _get_alerts():
    alerts = []
    # Check for overdue dues
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    overdue_query = "SELECT COUNT(id) FROM nagad_khata WHERE due_amount > 0.01 AND date <= ?"
    overdue_count = db_controller_instance.execute_query(overdue_query, (thirty_days_ago,), fetch="one")[0] or 0
    if overdue_count > 0:
        alerts.append({'type': 'warning', 'text': f"You have {overdue_count} unpaid due(s) older than 30 days."})

    # Check for salary reminders
    today = datetime.now().date()
    if today.day > 5: # Only check after the 5th
        last_month_date = today.replace(day=1) - timedelta(days=1)
        last_month_str = last_month_date.strftime('%Y-%m')
        paid_staff_ids = {row[0] for row in db_controller_instance.execute_query("SELECT DISTINCT staff_id FROM salary_payments WHERE STRFTIME('%Y-%m', payment_date) = ?", (last_month_str,), fetch="all")}
        all_staff_ids = {row[0] for row in db_controller_instance.execute_query("SELECT id FROM staff", fetch="all")}
        if all_staff_ids - paid_staff_ids: # If any staff hasn't been paid
            alerts.append({'type': 'info', 'text': f"Reminder: Salaries for {last_month_date.strftime('%B')} may be due."})

    if not alerts:
        alerts.append({'type': 'success', 'text': 'No critical alerts. System is normal.'})
    
    return alerts