# molla_bricks/web/owner.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from molla_bricks.web import db_controller_instance
from flask_login import login_required
from datetime import datetime

bp = Blueprint('owner', __name__, url_prefix='/owner')

@bp.route('/')
@login_required
def index():
    """Renders the Manage Owner page."""
    records = db_controller_instance.execute_query("SELECT * FROM owners ORDER BY name", fetch="all")
    return render_template('manage_owners.html', records=records or [])

@bp.route('/cash')
@login_required
def cash_management():
    """Renders the Owner's Cash Management page."""
    # Fetch owners for the modal dropdown
    owners = db_controller_instance.execute_query("SELECT id, name FROM owners WHERE status = 'Active' ORDER BY name", fetch="all") or []
    
    # Fetch transactions for the table
    date_filter = request.args.get('date', default="", type=str)
    
    query = """
        SELECT o.date, own.name, o.voucher_no, o.description, o.amount, o.type, o.id
        FROM owner_cash o
        LEFT JOIN owners own ON o.owner_id = own.id
    """
    params = []
    if date_filter:
        query += " WHERE o.date = ?"
        params.append(date_filter)
        
    query += " ORDER BY o.date DESC, o.id DESC"
    
    entries = db_controller_instance.execute_query(query, tuple(params), fetch="all") or []
    
    return render_template('owner_cash_management.html', 
                           entries=entries, 
                           owners=owners,
                           date_filter=date_filter,
                           today=datetime.now().strftime('%Y-%m-%d'))

@bp.route('/cash/add', methods=['POST'])
@login_required
def add_cash_entry():
    voucher_no = request.form.get('voucher_no')
    date = request.form.get('date')
    owner_id = request.form.get('owner_id', type=int)
    payment_method = request.form.get('payment_method')
    account = request.form.get('account')
    amount = request.form.get('amount', type=float)
    remarks = request.form.get('remarks')
    
    # Determine if it's a 'Deposit' (owner provided) or 'Withdrawal' (owner accepted)
    # This logic may need to be adjusted based on 'account'
    trans_type = "Deposit" if payment_method == "Cash" else "Withdrawal" 

    if not voucher_no or not date or not owner_id or not amount:
        flash("Voucher, Date, Owner, and Amount are required.", 'danger')
        return redirect(url_for('owner.cash_management'))
        
    try:
        query = """
            INSERT INTO owner_cash (date, type, description, amount, voucher_no, owner_id, payment_method, account)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        db_controller_instance.execute_query(query, (date, trans_type, remarks, amount, voucher_no, owner_id, payment_method, account))
        flash("Owner's cash entry added successfully.", 'success')
    except Exception as e:
        flash(f"Error: {e}", 'danger')
        
    return redirect(url_for('owner.cash_management'))

@bp.route('/cash/delete/<int:entry_id>', methods=['POST'])
@login_required
def delete_cash_entry(entry_id):
    try:
        db_controller_instance.execute_query("DELETE FROM owner_cash WHERE id = ?", (entry_id,))
        flash('Entry deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting entry: {e}', 'danger')
    return redirect(url_for('owner.cash_management'))