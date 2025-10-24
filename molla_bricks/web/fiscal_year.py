# molla_bricks/web/fiscal_year.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from molla_bricks.web import db_controller_instance
from flask_login import login_required
from datetime import datetime

bp = Blueprint('fiscal_year', __name__, url_prefix='/fiscal-year')

@bp.route('/manage')
@login_required
def management():
    """Renders the 'Fiscal year management' page."""
    name_filter = request.args.get('name', default="", type=str)
    status_filter = request.args.get('status', default="", type=str)
    
    query = "SELECT id, name, start_date, end_date, status FROM financial_year_end"
    params = []
    where_clauses = []

    if name_filter:
        where_clauses.append("name LIKE ?")
        params.append(f"%{name_filter}%")
    if status_filter:
        where_clauses.append("status = ?")
        params.append(status_filter)

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
    
    query += " ORDER BY start_date DESC"
    
    records = db_controller_instance.execute_query(query, tuple(params), fetch="all")
    
    return render_template('fiscal_year_management.html', 
                           records=records, 
                           name_filter=name_filter, 
                           status_filter=status_filter,
                           today=datetime.now().strftime('%Y-%m-%d'))

@bp.route('/add', methods=['POST'])
@login_required
def add():
    name = request.form.get('name')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    status = request.form.get('status') # <-- FIXED

    if not name or not start_date or not status:
        flash("Name, Start Date, and Status are required.", 'danger')
        return redirect(url_for('fiscal_year.management'))
        
    try:
        query = "INSERT OR IGNORE INTO financial_year_end (name, status, start_date, end_date) VALUES (?, ?, ?, ?)"
        rows_affected = db_controller_instance.execute_query(query, (name, status, start_date, end_date if end_date else None))
        
        if rows_affected > 0:
            flash("Fiscal year added successfully.", 'success')
        else:
            flash(f"Error: A fiscal year with the name '{name}' already exists.", 'danger')
            
    except Exception as e:
        flash(f"Error: {e}", 'danger')
        
    return redirect(url_for('fiscal_year.management'))

# --- NEW: Route to handle editing a fiscal year ---
@bp.route('/edit', methods=['POST'])
@login_required
def edit():
    try:
        year_id = request.form.get('id')
        name = request.form.get('name')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        status = request.form.get('status')

        if not all([year_id, name, start_date, status]):
            flash("Name, Start Date, and Status are required.", 'danger')
            return redirect(url_for('fiscal_year.management'))

        query = "UPDATE financial_year_end SET name = ?, start_date = ?, end_date = ?, status = ? WHERE id = ?"
        db_controller_instance.execute_query(query, (name, start_date, end_date if end_date else None, status, year_id))
        flash("Fiscal year updated successfully.", 'success')
    except Exception as e:
        flash(f"Error: {e}", 'danger')
    
    return redirect(url_for('fiscal_year.management'))

# --- NEW: Route to delete a fiscal year ---
@bp.route('/delete/<int:year_id>', methods=['POST'])
@login_required
def delete(year_id):
    try:
        # We should add a check here later if other tables depend on this
        db_controller_instance.execute_query("DELETE FROM financial_year_end WHERE id = ?", (year_id,))
        flash("Fiscal year deleted.", 'success')
    except Exception as e:
        flash(f"Error: {e}. It may be in use.", 'danger')
    return redirect(url_for('fiscal_year.management'))

@bp.route('/financial-year-end')
@login_required
def financial_year_end():
    fiscal_years = db_controller_instance.execute_query("SELECT id, name FROM financial_year_end WHERE status = 'Active' ORDER BY name DESC", fetch="all")
    fiscal_year_id = request.args.get('fiscal_year_id', type=int)
    record = None
    if fiscal_year_id:
        query = "SELECT * FROM financial_year_end WHERE id = ?"
        record = db_controller_instance.execute_query(query, (fiscal_year_id,), fetch="one")
    return render_template('financial_year_end.html', 
                           record=record,
                           fiscal_years=fiscal_years,
                           selected_fiscal_year_id=fiscal_year_id)