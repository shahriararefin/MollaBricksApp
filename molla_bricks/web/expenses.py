# molla_bricks/web/expenses.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from molla_bricks.web import db_controller_instance
from datetime import datetime, timedelta

bp = Blueprint('expenses', __name__, url_prefix='/expenses')

@bp.route('/')
def index():
    """Renders the Daily Expenses page."""
    
    # Get filters
    today = datetime.now().date()
    start_date = request.args.get('start_date', default=(today - timedelta(days=30)).strftime('%Y-%m-%d'), type=str)
    end_date = request.args.get('end_date', default=today.strftime('%Y-%m-%d'), type=str)

    # Fetch expense categories for the dropdown
    categories = [row[0] for row in db_controller_instance.execute_query("SELECT name FROM expense_categories ORDER BY name", fetch="all")]
    
    # Fetch expense records for the table
    query = "SELECT id, expense_date, category, description, amount FROM daily_expenses WHERE expense_date BETWEEN ? AND ? ORDER BY expense_date DESC"
    transactions = db_controller_instance.execute_query(query, (start_date, end_date), fetch="all")
    
    # Calculate summary
    total_expenses = sum(t[4] for t in transactions)
    
    return render_template('daily_expenses.html', 
                           transactions=transactions, 
                           categories=categories,
                           start_date=start_date,
                           end_date=end_date,
                           total_expenses=total_expenses,
                           today=today.strftime('%Y-%m-%d'))

@bp.route('/add', methods=['POST'])
def add_expense():
    """Handles the submission of a new expense."""
    expense_date = request.form.get('date')
    category = request.form.get('category')
    description = request.form.get('description')
    try:
        amount = float(request.form.get('amount') or 0.0)
        if amount <= 0:
            raise ValueError("Amount must be greater than zero")
    except ValueError as e:
        flash(f'Invalid amount. {e}', 'danger')
        return redirect(url_for('expenses.index'))

    if not category or not description:
        flash('Category and Description are required.', 'danger')
        return redirect(url_for('expenses.index'))

    # Insert into daily_expenses table
    expense_query = "INSERT INTO daily_expenses (expense_date, category, description, amount) VALUES (?, ?, ?, ?)"
    new_id = db_controller_instance.execute_query(expense_query, (expense_date, category, description, amount))
    
    # Also insert into the main Ledger Book
    ledger_desc = f"{description} [EXPENSE_ID:{new_id}]"
    ledger_query = "INSERT INTO ledger_book (date, party_name, description, debit) VALUES (?, ?, ?, ?)"
    db_controller_instance.execute_query(ledger_query, (expense_date, category, ledger_desc, amount))
    
    flash('Expense recorded and added to ledger successfully!', 'success')
    return redirect(url_for('expenses.index'))