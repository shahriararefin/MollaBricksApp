# molla_bricks/web/sales.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from molla_bricks.web import db_controller_instance
# --- CORRECT IMPORT ---
from molla_bricks.core.services.nagad_service import NagadService
from datetime import datetime
import os

bp = Blueprint('sales', __name__, url_prefix='/sales')

@bp.route('/')
def nagad_khata():
    query = "SELECT id, date, chalan_no, customer_name, brick_amount, total_amount, paid_amount, due_amount FROM nagad_khata ORDER BY id DESC"
    sales = db_controller_instance.execute_query(query, fetch="all")
    return render_template('nagad_khata.html', sales=sales)

@bp.route('/add')
def add_form():
    customers = db_controller_instance.execute_query("SELECT id, name FROM customers ORDER BY name ASC", fetch="all")
    brick_types = [row[0] for row in db_controller_instance.execute_query("SELECT name FROM brick_types ORDER BY name", fetch="all")]
    marker_id = int(db_controller_instance.get_setting('chalan_reset_marker_id', 0))
    query = "SELECT MAX(CAST(chalan_no AS INTEGER)) FROM nagad_khata WHERE chalan_no GLOB '[0-9]*' AND id > ?"
    result = db_controller_instance.execute_query(query, (marker_id,), fetch="one")
    next_chalan = str(result[0] + 1) if result and result[0] is not None else "1"
    return render_template('add_sale.html', customers=customers, brick_types=brick_types, next_chalan=next_chalan, today=datetime.now().strftime('%Y-%m-%d'))

@bp.route('/add', methods=['POST'])
def add():
    try:
        entry_date = request.form.get('date'); chalan_no = request.form.get('chalan_no'); customer_id = request.form.get('customer_id'); vehicle_no = request.form.get('vehicle_no')
        brick_type = request.form.get('brick_type'); brick_amount = int(request.form.get('brick_amount') or 0); total_amount = float(request.form.get('total_amount') or 0.0)
        paid_amount = float(request.form.get('paid_amount') or 0.0); due_amount = round(total_amount - paid_amount, 2)
        
        check_query = "SELECT id FROM nagad_khata WHERE chalan_no = ? AND id > ?"; marker_id = int(db_controller_instance.get_setting('chalan_reset_marker_id', 0)); exists = db_controller_instance.execute_query(check_query, (chalan_no, marker_id), fetch="one")
        if exists: flash(f"Warning: Chalan No '{chalan_no}' already exists. Please verify.", 'warning')
        
        cust_query = "SELECT name, address FROM customers WHERE id = ?"; customer = db_controller_instance.execute_query(cust_query, (customer_id,), fetch="one")
        customer_name = customer[0] if customer else "N/A"; address = customer[1] if customer else "N/A"
        nagad_query = "INSERT INTO nagad_khata (customer_id, date, chalan_no, customer_name, address, vehicle_no, brick_type, total_amount, paid_amount, due_amount, brick_amount, rate) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        params = (customer_id, entry_date, chalan_no, customer_name, address, vehicle_no, brick_type, total_amount, paid_amount, due_amount, brick_amount, total_amount)
        new_id = db_controller_instance.execute_query(nagad_query, params)
        if new_id:
            db_controller_instance.execute_query("INSERT INTO ledger_book (date, party_name, description, debit, credit) VALUES (?, ?, ?, ?, ?)", (entry_date, customer_name, f"Sale via Chalan: {chalan_no or 'N/A'} [SALE_FROM_CHALAN_ID:{new_id}]", total_amount, 0))
            if paid_amount > 0: db_controller_instance.execute_query("INSERT INTO ledger_book (date, party_name, description, credit, debit) VALUES (?, ?, ?, ?, ?)", (entry_date, customer_name, f"Payment for Chalan: {chalan_no or 'N/A'} [PAID_FOR_CHALAN_ID:{new_id}]", paid_amount, 0))
            if customer_id and due_amount > 0: auto_settle_from_advance(customer_id, customer_name)
            flash('Sale recorded successfully!', 'success'); return redirect(url_for('sales.nagad_khata'))
        else:
            flash('Error saving the entry.', 'danger'); return redirect(url_for('sales.add_form'))
    except Exception as e:
        flash(f'An error occurred: {e}', 'danger'); return redirect(url_for('sales.add_form'))

@bp.route('/delete/<int:sale_id>', methods=['POST'])
def delete_sale(sale_id):
    try:
        db_controller_instance.execute_query("DELETE FROM ledger_book WHERE description LIKE ?", (f"%CHALAN_ID:{sale_id}%",))
        db_controller_instance.execute_query("DELETE FROM nagad_khata WHERE id = ?", (sale_id,))
        flash('Sale and associated ledger entries deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting sale: {e}', 'danger')
    return redirect(url_for('sales.nagad_khata'))

@bp.route('/edit/<int:sale_id>')
def edit_sale_form(sale_id):
    query = "SELECT * FROM nagad_khata WHERE id = ?"; sale_record = db_controller_instance.execute_query(query, (sale_id,), fetch="one")
    if not sale_record: flash('Sale not found.', 'danger'); return redirect(url_for('sales.nagad_khata'))
    columns = ["id", "customer_id", "date", "chalan_no", "customer_name", "address", "vehicle_no", "brick_type", "brick_amount", "rate", "total_amount", "paid_amount", "due_amount", "timestamp"]; sale = dict(zip(columns, sale_record))
    brick_types = [row[0] for row in db_controller_instance.execute_query("SELECT name FROM brick_types ORDER BY name", fetch="all")]
    return render_template('edit_sale.html', sale=sale, brick_types=brick_types)

@bp.route('/edit', methods=['POST'])
def edit_sale():
    try:
        sale_id = request.form.get('sale_id'); total_amount = float(request.form.get('total_amount') or 0.0); paid_amount = float(request.form.get('paid_amount') or 0.0); due_amount = round(total_amount - paid_amount, 2)
        query = "UPDATE nagad_khata SET date = ?, chalan_no = ?, vehicle_no = ?, brick_type = ?, brick_amount = ?, total_amount = ?, paid_amount = ?, due_amount = ? WHERE id = ?"
        params = (request.form.get('date'), request.form.get('chalan_no'), request.form.get('vehicle_no'), request.form.get('brick_type'), int(request.form.get('brick_amount') or 0), total_amount, paid_amount, due_amount, sale_id)
        db_controller_instance.execute_query(query, params); flash('Sale updated successfully. Please manually verify ledger entries.', 'info'); return redirect(url_for('sales.nagad_khata'))
    except Exception as e:
        flash(f'An error occurred: {e}', 'danger'); return redirect(url_for('sales.edit_sale_form', sale_id=sale_id))

@bp.route('/print_chalan/<int:sale_id>')
def print_chalan(sale_id):
    query = "SELECT * FROM nagad_khata WHERE id = ?"
    record = db_controller_instance.execute_query(query, (sale_id,), fetch="one")
    if not record:
        flash("Sale not found.", 'danger')
        return redirect(url_for('sales.nagad_khata'))
    
    columns = ["id", "customer_id", "date", "chalan_no", "customer_name", "address", "vehicle_no", "brick_type", "brick_amount", "rate", "total_amount", "paid_amount", "due_amount", "timestamp"]
    chalan_data = dict(zip(columns, record))
    
    try:
        pdf_path = NagadService.generate_chalan_pdf(chalan_data)
        # Send the file from the server to the user's browser
        return send_file(pdf_path, as_attachment=True)
    except Exception as e:
        flash(f"Error generating PDF: {e}", 'danger')
        return redirect(url_for('sales.nagad_khata'))

# Helper function
def auto_settle_from_advance(customer_id, customer_name):
    balance_query = "SELECT SUM(credit) - SUM(debit) FROM ledger_book WHERE party_name = ?"; balance = db_controller_instance.execute_query(balance_query, (customer_name,), fetch="one")[0] or 0.0
    if balance > 0:
        dues_query = "SELECT id, due_amount FROM nagad_khata WHERE customer_id = ? AND due_amount > 0.01 ORDER BY id ASC"; due_records = db_controller_instance.execute_query(dues_query, (customer_id,), fetch="all")
        if not due_records: return
        payment_to_apply = balance
        for chalan_id, chalan_due in due_records:
            if payment_to_apply <= 0: break
            payment_for_this_chalan = min(payment_to_apply, chalan_due); db_controller_instance.execute_query("UPDATE nagad_khata SET paid_amount = paid_amount + ?, due_amount = due_amount - ? WHERE id = ?", (payment_for_this_chalan, payment_for_this_chalan, chalan_id))
            desc = f"Advance applied to Chalan ID: {chalan_id} [AUTO_SETTLED_ID:{chalan_id}]"; db_controller_instance.execute_query("INSERT INTO ledger_book (date, party_name, description, debit, credit) VALUES (?, ?, ?, ?, ?)", (datetime.now().strftime('%Y-%m-%d'), customer_name, desc, payment_for_this_chalan, 0)); payment_to_apply -= payment_for_this_chalan