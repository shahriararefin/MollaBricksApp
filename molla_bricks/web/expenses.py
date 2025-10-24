# molla_bricks/web/expenses.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from molla_bricks.web import db_controller_instance
from datetime import datetime, timedelta

bp = Blueprint('expenses', __name__, url_prefix='/expenses')

@bp.route('/')
def index():
    """Renders the Daily Expenses page."""
    today = datetime.now().date()
    start_date = request.args.get('start_date', default=(today - timedelta(days=30)).strftime('%Y-%m-%d'), type=str)
    end_date = request.args.get('end_date', default=today.strftime('%Y-%m-%d'), type=str)

    categories = [row[0] for row in db_controller_instance.execute_query("SELECT name FROM expense_categories ORDER BY name", fetch="all")]
    
    query = "SELECT id, expense_date, category, description, amount FROM daily_expenses WHERE expense_date BETWEEN ? AND ? ORDER BY expense_date DESC"
    transactions = db_controller_instance.execute_query(query, (start_date, end_date), fetch="all")
    
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
    expense_date = request.form.get('date'); category = request.form.get('category'); description = request.form.get('description')
    try:
        amount = float(request.form.get('amount') or 0.0)
        if amount <= 0: raise ValueError("Amount must be greater than zero")
    except ValueError as e:
        flash(f'Invalid amount. {e}', 'danger'); return redirect(url_for('expenses.index'))

    if not category or not description:
        flash('Category and Description are required.', 'danger'); return redirect(url_for('expenses.index'))

    expense_query = "INSERT INTO daily_expenses (expense_date, category, description, amount) VALUES (?, ?, ?, ?)"
    new_id = db_controller_instance.execute_query(expense_query, (expense_date, category, description, amount))
    
    ledger_desc = f"{description} [EXPENSE_ID:{new_id}]"
    ledger_query = "INSERT INTO ledger_book (date, party_name, description, debit) VALUES (?, ?, ?, ?)"
    db_controller_instance.execute_query(ledger_query, (expense_date, category, ledger_desc, amount))
    
    flash('Expense recorded and added to ledger successfully!', 'success')
    return redirect(url_for('expenses.index'))

# --- NEW: Route to show the edit form ---
@bp.route('/edit/<int:expense_id>')
def edit_form(expense_id):
    query = "SELECT id, expense_date, category, description, amount FROM daily_expenses WHERE id = ?"
    expense = db_controller_instance.execute_query(query, (expense_id,), fetch="one")
    if not expense:
        flash("Expense not found.", 'danger'); return redirect(url_for('expenses.index'))
    
    categories = [row[0] for row in db_controller_instance.execute_query("SELECT name FROM expense_categories ORDER BY name", fetch="all")]
    
    # Convert tuple to a dictionary for easier template access
    expense_dict = {
        'id': expense[0],
        'date': expense[1],
        'category': expense[2],
        'description': expense[3],
        'amount': expense[4]
    }
    return render_template('edit_expense.html', expense=expense_dict, categories=categories)

# --- NEW: Route to process the edit ---
@bp.route('/edit', methods=['POST'])
def edit_expense():
    expense_id = request.form.get('expense_id', type=int)
    expense_date = request.form.get('date')
    category = request.form.get('category')
    description = request.form.get('description')
    try:
        amount = float(request.form.get('amount') or 0.0)
        if amount <= 0: raise ValueError("Amount must be greater than zero")
    except ValueError as e:
        flash(f'Invalid amount. {e}', 'danger'); return redirect(url_for('expenses.edit_form', expense_id=expense_id))
        
    try:
        # Update the expense entry
        query = "UPDATE daily_expenses SET expense_date = ?, category = ?, description = ?, amount = ? WHERE id = ?"
        db_controller_instance.execute_query(query, (expense_date, category, description, amount, expense_id))
        
        # Update the corresponding ledger entry
        ledger_desc = f"{description} [EXPENSE_ID:{expense_id}]"
        ledger_query = "UPDATE ledger_book SET date = ?, party_name = ?, description = ?, debit = ? WHERE description LIKE ?"
        db_controller_instance.execute_query(ledger_query, (expense_date, category, ledger_desc, amount, f"%[EXPENSE_ID:{expense_id}]%"))
        
        flash('Expense updated successfully!', 'success')
    except Exception as e:
        flash(f'Error updating expense: {e}', 'danger')
        
    return redirect(url_for('expenses.index'))

# --- NEW: Route to delete an expense ---
@bp.route('/delete/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    try:
        # Delete the ledger entry first
        db_controller_instance.execute_query("DELETE FROM ledger_book WHERE description LIKE ?", (f"%[EXPENSE_ID:{expense_id}]%",))
        # Delete the expense entry
        db_controller_instance.execute_query("DELETE FROM daily_expenses WHERE id = ?", (expense_id,))
        flash('Expense and associated ledger entry deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting expense: {e}', 'danger')
    return redirect(url_for('expenses.index'))