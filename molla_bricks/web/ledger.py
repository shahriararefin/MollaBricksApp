# molla_bricks/web/ledger.py
from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file
from molla_bricks.web import db_controller_instance
from molla_bricks.core.services.ledger_service import LedgerService
from datetime import datetime, timedelta

bp = Blueprint('ledger', __name__, url_prefix='/ledger')

@bp.route('/')
def ledger_book():
    party_name = request.args.get('party_name', default="", type=str)
    start_date = request.args.get('start_date', default=(datetime.now().date() - timedelta(days=30)).strftime('%Y-%m-%d'), type=str)
    end_date = request.args.get('end_date', default=datetime.now().date().strftime('%Y-%m-%d'), type=str)
    party_names = db_controller_instance.execute_query("SELECT DISTINCT party_name FROM ledger_book WHERE party_name IS NOT NULL AND party_name != '' ORDER BY party_name", fetch="all")
    all_parties = [p[0] for p in party_names]
    query = "SELECT id, date, party_name, description, credit, debit FROM ledger_book"
    params = []; where_clauses = []
    if party_name:
        where_clauses.append("party_name = ?"); params.append(party_name)
    where_clauses.append("date BETWEEN ? AND ?"); params.extend([start_date, end_date])
    if where_clauses: query += " WHERE " + " AND ".join(where_clauses)
    query += " ORDER BY date ASC, id ASC" # Statements should be chronological
    transactions = db_controller_instance.execute_query(query, tuple(params), fetch="all")
    
    total_credit = sum(t[4] for t in transactions); total_debit = sum(t[5] for t in transactions); balance = 0.0
    if party_name:
        ob_query = "SELECT SUM(credit) - SUM(debit) FROM ledger_book WHERE party_name = ? AND date < ?"
        opening_balance = db_controller_instance.execute_query(ob_query, (party_name, start_date), fetch="one")[0] or 0.0
        balance = opening_balance + total_credit - total_debit
    else:
        balance_query = "SELECT SUM(credit) - SUM(debit) FROM ledger_book"
        balance = db_controller_instance.execute_query(balance_query, fetch="one")[0] or 0.0

    return render_template('ledger_book.html', 
                           transactions=transactions, all_parties=all_parties, selected_party=party_name,
                           start_date=start_date, end_date=end_date, total_credit=total_credit,
                           total_debit=total_debit, balance=balance, now=datetime.now())

@bp.route('/add', methods=['POST'])
def add_entry():
    party_name = request.form.get('party_name'); description = request.form.get('description'); entry_date = request.form.get('date')
    try:
        credit = float(request.form.get('credit') or 0.0); debit = float(request.form.get('debit') or 0.0)
    except ValueError:
        flash('Credit and Debit must be valid numbers.', 'danger'); return redirect(url_for('ledger.ledger_book'))
    if not party_name:
        flash('Party Name is required.', 'danger'); return redirect(url_for('ledger.ledger_book'))
    if credit > 0 and debit > 0:
        flash('Please enter either a Credit or a Debit, not both.', 'warning'); return redirect(url_for('ledger.ledger_book'))
    query = "INSERT INTO ledger_book (date, party_name, description, credit, debit) VALUES (?, ?, ?, ?, ?)"
    new_id = db_controller_instance.execute_query(query, (entry_date, party_name, description, credit, debit))
    if new_id and credit > 0:
        customer_id_record = db_controller_instance.execute_query("SELECT id FROM customers WHERE name = ?", (party_name,), fetch="one")
        if customer_id_record:
            auto_settle_dues(customer_id_record[0], customer_name, credit, new_id)
            flash('Entry added and dues automatically settled!', 'success')
        else:
            flash('Entry added. Party is not a registered customer, so dues were not auto-settled.', 'info')
    else:
        flash('Ledger entry added successfully!', 'success')
    return redirect(url_for('ledger.ledger_book', party_name=party_name))

@bp.route('/print_statement')
def print_statement():
    party_name = request.args.get('party_name', type=str)
    start_date = request.args.get('start_date', type=str)
    end_date = request.args.get('end_date', type=str)
    
    if not party_name:
        flash("You must select a party to generate a statement.", 'warning')
        return redirect(url_for('ledger.ledger_book'))

    ob_query = "SELECT SUM(credit) - SUM(debit) FROM ledger_book WHERE party_name = ? AND date < ?"
    opening_balance = db_controller_instance.execute_query(ob_query, (party_name, start_date), fetch="one")[0] or 0.0
    
    trans_query = "SELECT date, description, credit, debit FROM ledger_book WHERE party_name = ? AND date BETWEEN ? AND ? ORDER BY date ASC, id ASC"
    transactions = db_controller_instance.execute_query(trans_query, (party_name, start_date, end_date), fetch="all")

    try:
        pdf_path = LedgerService.generate_ledger_pdf(party_name, start_date, end_date, opening_balance, transactions)
        return send_file(pdf_path, as_attachment=True)
    except Exception as e:
        flash(f"Error generating PDF: {e}", 'danger')
        return redirect(url_for('ledger.ledger_book'))

@bp.route('/export_csv')
def export_csv():
    try:
        path, msg = LedgerService.export_to_csv(db_controller_instance)
        if path: return send_file(path, as_attachment=True)
        else: flash(msg, 'warning'); return redirect(url_for('ledger.ledger_book'))
    except Exception as e:
        flash(f"Error exporting CSV: {e}", 'danger')
        return redirect(url_for('ledger.ledger_book'))

def auto_settle_dues(customer_id, customer_name, payment_amount, ledger_entry_id):
    dues_query = "SELECT id, due_amount FROM nagad_khata WHERE customer_id = ? AND due_amount > 0.01 ORDER BY id ASC"; due_records = db_controller_instance.execute_query(dues_query, (customer_id,), fetch="all")
    if not due_records: return
    payment_to_apply = payment_amount; settled_chalans = []
    for chalan_id, chalan_due in due_records:
        if payment_to_apply <= 0: break
        payment_for_this_chalan = min(payment_to_apply, chalan_due); db_controller_instance.execute_query("UPDATE nagad_khata SET paid_amount = paid_amount + ?, due_amount = due_amount - ? WHERE id = ?", (payment_for_this_chalan, payment_for_this_chalan, chalan_id))
        desc = f"Advance applied to Chalan ID: {chalan_id} [AUTO_SETTLED_ID:{chalan_id}]"; db_controller_instance.execute_query("INSERT INTO ledger_book (date, party_name, description, debit, credit) VALUES (?, ?, ?, ?, ?)", (datetime.now().strftime('%Y-%m-%d'), customer_name, desc, payment_for_this_chalan, 0)); payment_to_apply -= payment_for_this_chalan
        settled_chalans.append(f"Chalan ID {chalan_id}")
    if settled_chalans:
        settlement_desc = " | Auto-settled: " + ", ".join(settled_chalans); db_controller_instance.execute_query("UPDATE ledger_book SET description = description || ? WHERE id = ?", (settlement_desc, ledger_entry_id))