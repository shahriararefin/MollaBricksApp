# molla_bricks/web/accounts.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from molla_bricks.web import db_controller_instance
from flask_login import login_required

bp = Blueprint('accounts', __name__, url_prefix='/accounts')

# --- Chart of Head (Unchanged) ---
@bp.route('/chart-of-head')
@login_required
def chart_of_head():
    records = db_controller_instance.execute_query("SELECT * FROM chart_of_accounts ORDER BY type, name", fetch="all") or []
    return render_template('chart_of_accounts.html', records=records)

@bp.route('/chart-of-head/add', methods=['POST'])
@login_required
def add_head():
    name = request.form.get('name'); ttype = request.form.get('type')
    if not name or not ttype: flash("Name and Type are required.", 'danger')
    else:
        try:
            db_controller_instance.execute_query("INSERT INTO chart_of_accounts (name, type) VALUES (?, ?)", (name, ttype))
            flash("Account head added.", 'success')
        except Exception as e: flash(f"Error: {e}", 'danger')
    return redirect(url_for('accounts.chart_of_head'))

# --- Transaction Placeholders (Unchanged) ---
@bp.route('/transactions')
@login_required
def transactions():
    flash("Transaction page is under construction.", 'info'); return redirect(url_for('dashboard.index'))
@bp.route('/transactions/opening-balance')
@login_required
def opening_balance():
    flash("Opening Balance page is under construction.", 'info'); return redirect(url_for('dashboard.index'))
@bp.route('/transactions/payment')
@login_required
def payment():
    flash("Payment page is under construction.", 'info'); return redirect(url_for('dashboard.index'))
@bp.route('/transactions/collection')
@login_required
def collection():
    flash("Collection page is under construction.", 'info'); return redirect(url_for('dashboard.index'))
@bp.route('/transactions/receipt')
@login_required
def receipt():
    flash("Receipt page is under construction.", 'info'); return redirect(url_for('dashboard.index'))

# --- Bank Accounts (Unchanged) ---
@bp.route('/bank')
@login_required
def bank():
    records = db_controller_instance.execute_query("SELECT * FROM bank_accounts ORDER BY bank_name, account_name", fetch="all") or []
    return render_template('bank_accounts.html', records=records)

@bp.route('/bank/add', methods=['POST'])
@login_required
def add_bank():
    bank_name = request.form.get('bank_name'); account_name = request.form.get('account_name'); account_number = request.form.get('account_number')
    if not bank_name or not account_name: flash("Bank Name and Account Name are required.", 'danger')
    else:
        try:
            db_controller_instance.execute_query("INSERT INTO bank_accounts (bank_name, account_name, account_number, branch) VALUES (?, ?, ?, ?)", (bank_name, account_name, account_number, request.form.get('branch')))
            flash("Bank account added.", 'success')
        except Exception as e: flash(f"Error: {e}", 'danger')
    return redirect(url_for('accounts.bank'))

# --- MODIFIED: Mobile Bank Section ---
@bp.route('/mobile-bank')
@login_required
def mobile_bank():
    """Renders the Mobile Bank Accounts page with filters."""
    provider_name = request.args.get('provider_name', default="", type=str)
    account_name = request.args.get('account_name', default="", type=str)
    account_number = request.args.get('account_number', default="", type=str)
    
    query = "SELECT * FROM mobile_bank_accounts"
    params = []
    where_clauses = []
    
    if provider_name:
        where_clauses.append("provider_name LIKE ?")
        params.append(f"%{provider_name}%")
    if account_name:
        where_clauses.append("account_name LIKE ?")
        params.append(f"%{account_name}%")
    if account_number:
        where_clauses.append("account_number LIKE ?")
        params.append(f"%{account_number}%")

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
    
    query += " ORDER BY provider_name, account_name"
    records = db_controller_instance.execute_query(query, tuple(params), fetch="all") or []
    
    return render_template('mobile_bank_accounts.html', 
                           records=records,
                           provider_name=provider_name,
                           account_name=account_name,
                           account_number=account_number)

@bp.route('/mobile-bank/add', methods=['POST'])
@login_required
def add_mobile_bank():
    provider_name = request.form.get('provider_name')
    account_name = request.form.get('account_name')
    account_number = request.form.get('account_number')
    if not provider_name or not account_name:
        flash("Provider Name and Account Name are required.", 'danger')
    else:
        try:
            db_controller_instance.execute_query("INSERT INTO mobile_bank_accounts (provider_name, account_name, account_number) VALUES (?, ?, ?)", 
                                                 (provider_name, account_name, account_number))
            flash("Mobile bank account added.", 'success')
        except Exception as e:
            flash(f"Error: {e}", 'danger')
    return redirect(url_for('accounts.mobile_bank'))

@bp.route('/mobile-bank/edit', methods=['POST'])
@login_required
def edit_mobile_bank():
    account_id = request.form.get('id')
    provider_name = request.form.get('provider_name')
    account_name = request.form.get('account_name')
    account_number = request.form.get('account_number')

    if not provider_name or not account_name:
        flash("Provider Name and Account Name are required.", 'danger')
    else:
        try:
            query = "UPDATE mobile_bank_accounts SET provider_name = ?, account_name = ?, account_number = ? WHERE id = ?"
            db_controller_instance.execute_query(query, (provider_name, account_name, account_number, account_id))
            flash("Mobile bank account updated.", 'success')
        except Exception as e:
            flash(f"Error: {e}", 'danger')
    return redirect(url_for('accounts.mobile_bank'))

@bp.route('/mobile-bank/delete/<int:account_id>', methods=['POST'])
@login_required
def delete_mobile_bank(account_id):
    try:
        # We should add a check here later if transactions are linked
        db_controller_instance.execute_query("DELETE FROM mobile_bank_accounts WHERE id = ?", (account_id,))
        flash('Mobile bank account deleted.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    return redirect(url_for('accounts.mobile_bank'))