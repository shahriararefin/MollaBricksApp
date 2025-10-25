# molla_bricks/web/dashboard.py
from flask import Blueprint, render_template, request
from molla_bricks.web import db_controller_instance
from flask_login import login_required
from datetime import datetime, timedelta

bp = Blueprint('dashboard', __name__, url_prefix='/')

def _get_date_range(period_str):
    """Helper function to get start/end dates from a string."""
    today = datetime.now().date()
    if period_str == "Today":
        return today.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')
    if period_str == "This Week":
        start_week = today - timedelta(days=today.weekday())
        return start_week.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')
    if period_str == "This Year":
        return today.replace(day=1, month=1).strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')
    if period_str == "All Time":
        return "1970-01-01", today.strftime('%Y-%m-%d')
    
    # Default is "This Month"
    return today.replace(day=1).strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')

def _safe_sum_query(query, params=()):
    """ Helper function to safely run a SUM query and return 0 if None. """
    result = db_controller_instance.execute_query(query, params, fetch="one")
    # This is the fix: check if result is None before trying to access result[0]
    return (result[0] or 0) if result else 0

@bp.route('/')
@login_required
def index():
    """Renders the main dashboard homepage."""
    
    period = request.args.get('period', 'This Month')
    start_date, end_date = _get_date_range(period)
    
    # --- Build WHERE clause for date filtering ---
    date_filter = f"WHERE date BETWEEN '{start_date}' AND '{end_date}'"
    date_filter_sales = f"WHERE sale_date BETWEEN '{start_date}' AND '{end_date}'"
    date_filter_expenses = f"WHERE date(expense_date) BETWEEN '{start_date}' AND '{end_date}'"
    date_filter_salary = f"WHERE date(payment_date) BETWEEN '{start_date}' AND '{end_date}'"
    date_filter_lu = f"WHERE date BETWEEN '{start_date}' AND '{end_date}'"
    
    if period == "All Time":
        date_filter = date_filter_sales = date_filter_expenses = date_filter_salary = date_filter_lu = ""

    # --- 1. Income Stats (Points to new sales_invoices table) ---
    total_income = _safe_sum_query(f"SELECT SUM(total) FROM sales_invoices {date_filter_sales}")
    total_paid = _safe_sum_query(f"SELECT SUM(paid) FROM sales_invoices {date_filter_sales}")
    total_outstanding = _safe_sum_query("SELECT SUM(due) FROM sales_invoices") # Always show all outstanding

    # --- 2. Cost Stats (All queries are now safe) ---
    exp_daily = _safe_sum_query(f"SELECT SUM(amount) FROM daily_expenses {date_filter_expenses}")
    exp_salary = _safe_sum_query(f"SELECT SUM(paid_amount) FROM salary_payments {date_filter_salary}")
    exp_contractor = _safe_sum_query(f"SELECT SUM(amount) FROM contractor_payments {date_filter_salary}")
    exp_load_unload = _safe_sum_query(f"SELECT SUM(total_cost) FROM load_unload {date_filter_lu}")
    exp_coal = _safe_sum_query(f"SELECT SUM(coal_cost) FROM round_entries {date_filter}")
    
    total_costs = exp_daily + exp_salary + exp_contractor + exp_load_unload + exp_coal
    
    # --- 3. Production Stats (Points to new sales_items table) ---
    prod_query = f"SELECT si.product_name, SUM(si.quantity) FROM sales_items si JOIN sales_invoices s ON si.invoice_id = s.id {date_filter_sales} GROUP BY si.product_name"
    prod_data = db_controller_instance.execute_query(prod_query, fetch="all") or []
    production_stats = {row[0]: row[1] for row in prod_data}

    # --- 4. Round Stats (Safe query) ---
    round_query = f"SELECT COUNT(id), MIN(date) FROM round_entries WHERE firing_status = 'Firing' {date_filter.replace('WHERE', 'AND') if date_filter else ''}"
    round_stats = db_controller_instance.execute_query(round_query, fetch="one")
    
    summary = {
        'total_income': total_income,
        'total_outstanding': total_outstanding,
        'balance': total_paid - total_costs, # Simple balance calculation
        'total_costs': total_costs,
        'cost_load': _safe_sum_query(f"SELECT SUM(total_cost) FROM load_unload {date_filter_lu} {'AND' if date_filter_lu else 'WHERE'} type = 'Load'"),
        'cost_unload': _safe_sum_query(f"SELECT SUM(total_cost) FROM load_unload {date_filter_lu} {'AND' if date_filter_lu else 'WHERE'} type = 'Unload'"),
        'cost_coal': exp_coal,
        'cost_firing': exp_salary + exp_contractor, # Combined labor costs
        'cost_soil': 0, # Placeholder
        'cost_oil': 0, # Placeholder
        'cost_electricity': 0, # Placeholder
        # Match product names from db
        'prod_first_class': production_stats.get('1st Class', 0) + production_stats.get('Class 1', 0),
        'prod_second_class': production_stats.get('2nd Class', 0) + production_stats.get('Class 2', 0),
        'prod_picket': production_stats.get('Picket', 0),
        'prod_adla': production_stats.get('Adla', 0), # Placeholder name
        'round_count': (round_stats[0] or 0) if round_stats else 0,
        'round_date': round_stats[1] if round_stats and round_stats[1] else 'N/A',
        'period': period,
        'filter_date': (datetime.strptime(start_date, '%Y-%m-%d') if period != 'All Time' else datetime.now()).strftime('%m/%d/%Y')
    }
    
    return render_template('dashboard.html', summary=summary, alerts=_get_alerts())

def _get_alerts():
    alerts = []
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    # FIXED: Point to sales_invoices
    overdue_query = "SELECT COUNT(id) FROM sales_invoices WHERE due > 0.01 AND sale_date <= ?"
    overdue_count_result = db_controller_instance.execute_query(overdue_query, (thirty_days_ago,), fetch="one")
    overdue_count = (overdue_count_result[0] or 0) if overdue_count_result else 0
    if overdue_count > 0:
        alerts.append({'type': 'warning', 'text': f"You have {overdue_count} unpaid due(s) older than 30 days."})
    
    today = datetime.now().date()
    if today.day > 5:
        last_month_date = today.replace(day=1) - timedelta(days=1)
        last_month_str = last_month_date.strftime('%Y-%m')
        paid_staff_ids = {row[0] for row in db_controller_instance.execute_query("SELECT DISTINCT staff_id FROM salary_payments WHERE STRFTIME('%Y-%m', payment_date) = ?", (last_month_str,), fetch="all") or []}
        all_staff_ids = {row[0] for row in db_controller_instance.execute_query("SELECT id FROM staff", fetch="all") or []}
        if all_staff_ids - paid_staff_ids:
            alerts.append({'type': 'info', 'text': f"Reminder: Salaries for {last_month_date.strftime('%B')} may be due."})

    if not alerts:
        alerts.append({'type': 'success', 'text': 'No critical alerts. System is normal.'})
    
    return alerts