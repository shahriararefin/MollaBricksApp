# molla_bricks/web/pot.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from molla_bricks.web import db_controller_instance
from flask_login import login_required
from datetime import datetime, timedelta

bp = Blueprint('pot', __name__, url_prefix='/pot')

@bp.route('/manage')
@login_required
def manage_pot():
    """Renders the Pot Management page."""
    query = "SELECT * FROM pot_entries ORDER BY date DESC, id DESC"
    entries = db_controller_instance.execute_query(query, fetch="all")
    return render_template('pot_management.html', 
                           entries=entries,
                           today=datetime.now().strftime('%Y-%m-%d'))

@bp.route('/add', methods=['POST'])
@login_required
def add_entry():
    date = request.form.get('date'); pot_name = request.form.get('pot_name'); mill_number = request.form.get('mill_number', type=int)
    quantity = request.form.get('quantity_shaped', 0, type=int); status = request.form.get('status'); notes = request.form.get('notes')
    if not date or not pot_name or not status:
        flash('Date, Pot Name, and Status are required.', 'danger'); return redirect(url_for('pot.manage_pot'))
    try:
        query = "INSERT INTO pot_entries (date, pot_name, mill_number, quantity_shaped, status, notes) VALUES (?, ?, ?, ?, ?, ?)"
        db_controller_instance.execute_query(query, (date, pot_name, mill_number, quantity, status, notes))
        flash('Pot entry added successfully.', 'success')
    except Exception as e:
        flash(f'Error adding entry: {e}', 'danger')
    return redirect(url_for('pot.manage_pot'))

# --- MODIFIED: This function now fetches data for the report ---
@bp.route('/report')
@login_required
def pot_report():
    """Renders the Pot Report page with filters."""
    today = datetime.now().date()
    start_date = request.args.get('start_date', default=(today - timedelta(days=30)).strftime('%Y-%m-%d'), type=str)
    end_date = request.args.get('end_date', default=today.strftime('%Y-%m-%d'), type=str)
    status_filter = request.args.get('status', default="", type=str)

    query = "SELECT * FROM pot_entries WHERE date BETWEEN ? AND ?"
    params = [start_date, end_date]

    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)
        
    query += " ORDER BY date DESC, id DESC"
    entries = db_controller_instance.execute_query(query, tuple(params), fetch="all")
    
    total_bricks = sum(e[4] for e in entries) # Sum of 'quantity_shaped'

    return render_template('pot_report.html', 
                           entries=entries,
                           start_date=start_date,
                           end_date=end_date,
                           status_filter=status_filter,
                           total_bricks=total_bricks)

@bp.route('/delete/<int:entry_id>', methods=['POST'])
@login_required
def delete_entry(entry_id):
    try:
        db_controller_instance.execute_query("DELETE FROM pot_entries WHERE id = ?", (entry_id,))
        flash('Entry deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting entry: {e}', 'danger')
    return redirect(url_for('pot.manage_pot'))