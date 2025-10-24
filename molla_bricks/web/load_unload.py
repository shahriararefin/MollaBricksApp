# molla_bricks/web/load_unload.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from molla_bricks.web import db_controller_instance
from flask_login import login_required
from datetime import datetime, timedelta

bp = Blueprint('load_unload', __name__, url_prefix='/load-unload')

@bp.route('/manage')
@login_required
def management():
    """Renders the Load/Unload management page."""
    
    # --- NEW: Get filter values ---
    chamber_filter = request.args.get('chamber', default="", type=str)
    category_filter = request.args.get('category', default="", type=str)

    fiscal_years_raw = db_controller_instance.execute_query("SELECT name FROM financial_year_end WHERE status = 'Active' ORDER BY name DESC", fetch="all") or []
    fiscal_years = [fy[0] for fy in fiscal_years_raw]

    contractors_raw = db_controller_instance.execute_query("SELECT name, section FROM contractors WHERE section IN ('Loader', 'Unloader') ORDER BY name", fetch="all") or []
    contractors = [f"{name} ({section})" for name, section in contractors_raw]

    # --- MODIFIED: Update query to use filters ---
    query = "SELECT * FROM load_unload"
    params = []
    where_clauses = []

    if chamber_filter:
        where_clauses.append("brick_type LIKE ?") # 'brick_type' stores Chamber
        params.append(f"%{chamber_filter}%")
    if category_filter:
        where_clauses.append("type = ?")
        params.append(category_filter)
    
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
        
    query += " ORDER BY date DESC, id DESC"
    entries = db_controller_instance.execute_query(query, tuple(params), fetch="all") or []
    
    return render_template('load_unload_management.html', 
                           entries=entries,
                           contractors=contractors,
                           fiscal_years=fiscal_years,
                           today=datetime.now().strftime('%Y-%m-%d'),
                           # Pass filters back to template
                           chamber_filter=chamber_filter,
                           category_filter=category_filter)

@bp.route('/add', methods=['POST'])
@login_required
def add_entry():
    date = request.form.get('date')
    ttype = request.form.get('category') # 'Load' or 'Unload'
    contractor_name = request.form.get('contractor_name')
    brick_type = request.form.get('brick_type') # This is 'Chamber'
    quantity = request.form.get('quantity', 0, type=int)
    total_cost = request.form.get('total', 0, type=float)
    fiscal_year = request.form.get('fiscal_year') # Stored in 'chalan_no'
    rate = round(total_cost / quantity, 2) if quantity > 0 else 0

    if not date or not ttype or not contractor_name or not fiscal_year:
        flash('Date, Category, Contractor, and Fiscal Year are required.', 'danger')
        return redirect(url_for('load_unload.management'))

    try:
        query = "INSERT INTO load_unload (date, type, chalan_no, brick_type, quantity, rate, total_cost, contractor_name) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        new_id = db_controller_instance.execute_query(query, (date, ttype, fiscal_year, brick_type, quantity, rate, total_cost, contractor_name))
        
        ledger_desc = f"{ttype} Cost: {quantity} @ {rate} for {contractor_name} [LU_ID:{new_id}]"
        db_controller_instance.execute_query("INSERT INTO ledger_book (date, party_name, description, debit) VALUES (?, ?, ?, ?)", (date, "Load/Unload Expense", ledger_desc, total_cost))
        flash('Load/Unload cost added and recorded in ledger.', 'success')
    except Exception as e:
        flash(f'Error adding entry: {e}', 'danger')
    
    return redirect(url_for('load_unload.management'))

@bp.route('/report')
@login_required
def report():
    today = datetime.now().date()
    start_date = request.args.get('start_date', default=(today - timedelta(days=30)).strftime('%Y-%m-%d'), type=str)
    end_date = request.args.get('end_date', default=today.strftime('%Y-%m-%d'), type=str)
    category_filter = request.args.get('category', default="", type=str)
    fiscal_year = request.args.get('fiscal_year', default="", type=str)

    fiscal_years_raw = db_controller_instance.execute_query("SELECT name FROM financial_year_end ORDER BY name DESC", fetch="all") or []
    fiscal_years = [fy[0] for fy in fiscal_years_raw]
    
    query = "SELECT * FROM load_unload WHERE date BETWEEN ? AND ?"
    params = [start_date, end_date]
    if category_filter:
        query += " AND type = ?"; params.append(category_filter)
    if fiscal_year:
        query += " AND chalan_no = ?"; params.append(fiscal_year)
    query += " ORDER BY date DESC, id DESC"
    entries = db_controller_instance.execute_query(query, tuple(params), fetch="all") or []
    
    total_quantity = sum(e[5] for e in entries)
    total_cost = sum(e[7] for e in entries)

    return render_template('load_unload_report.html', 
                           entries=entries, fiscal_years=fiscal_years, start_date=start_date,
                           end_date=end_date, category_filter=category_filter,
                           selected_fiscal_year=fiscal_year, total_quantity=total_quantity, total_cost=total_cost)

@bp.route('/delete/<int:entry_id>', methods=['POST'])
@login_required
def delete_entry(entry_id):
    try:
        db_controller_instance.execute_query("DELETE FROM ledger_book WHERE description LIKE ?", (f"%[LU_ID:{entry_id}]%",))
        db_controller_instance.execute_query("DELETE FROM load_unload WHERE id = ?", (entry_id,))
        flash('Entry deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting entry: {e}', 'danger')
    return redirect(request.referrer or url_for('load_unload.management'))