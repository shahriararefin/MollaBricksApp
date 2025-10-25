# molla_bricks/web/income.py
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from molla_bricks.web import db_controller_instance
from flask_login import login_required
from datetime import datetime

bp = Blueprint('income', __name__, url_prefix='/income')

@bp.route('/manage')
@login_required
def manage_income():
    """Renders the 'Manage income' page (the sales list)."""
    
    # Fetch all invoices to display in the list
    query = """
        SELECT inv.id, inv.invoice_no, inv.sale_date, inv.party_name, inv.total, inv.paid, inv.due, inv.status
        FROM sales_invoices inv
        ORDER BY inv.sale_date DESC, inv.id DESC
    """
    invoices = db_controller_instance.execute_query(query, fetch="all") or []
    
    return render_template('manage_income.html', invoices=invoices)

@bp.route('/add')
@login_required
def add_income_form():
    """Renders the 'Add income' (new invoice) page."""
    
    # Fetch data for dropdowns
    customers = db_controller_instance.execute_query("SELECT id, name FROM customers ORDER BY name ASC", fetch="all")
    # We use the 'brick_types' table, which you call 'Class' or 'Products'
    products = db_controller_instance.execute_query("SELECT id, name, product_code, unit FROM brick_types WHERE status = 'Active' ORDER BY name", fetch="all") or []

    # Generate a unique invoice number
    today_str = datetime.now().strftime('%Y%m%d')
    last_invoice = db_controller_instance.execute_query("SELECT MAX(id) FROM sales_invoices", fetch="one")
    next_id = (last_invoice[0] or 0) + 1
    invoice_no = f"SALE-{today_str}-{next_id:04d}"

    return render_template('add_income.html', 
                           customers=customers, 
                           products=products,
                           invoice_no=invoice_no,
                           today=datetime.now().strftime('%Y-%m-%d'))

@bp.route('/add', methods=['POST'])
@login_required
def add_income_submit():
    """Handles the submission of the new income form."""
    try:
        # --- 1. Get Main Invoice Data ---
        invoice_no = request.form.get('invoice_no')
        sale_date = request.form.get('sale_date')
        party_id = request.form.get('party_id')
        vehicle_no = request.form.get('vehicle_no')
        status = request.form.get('transaction_status')
        notes = request.form.get('notes')
        
        # Get customer name from party_id
        party_name = "N/A"
        if party_id:
            party_name = db_controller_instance.execute_query("SELECT name FROM customers WHERE id = ?", (party_id,), fetch="one")[0]

        # --- 2. Get all the product rows ---
        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')
        rates = request.form.getlist('rate[]')
        subtotals = request.form.getlist('subtotal[]')

        if not product_ids:
            flash("You must add at least one product.", 'danger')
            return redirect(url_for('income.add_income_form'))

        # --- 3. Calculate Totals ---
        total_amount = sum(float(s) for s in subtotals)
        # For now, let's assume 'Paid' is the full amount if status is 'Paid'
        paid_amount = total_amount if status == 'Paid' else 0.0
        due_amount = total_amount - paid_amount

        # --- 4. Save to Database ---
        
        # Start a transaction
        db_controller_instance.execute_query("BEGIN TRANSACTION;")

        # Insert into sales_invoices
        invoice_query = """
            INSERT INTO sales_invoices (invoice_no, sale_date, party_id, party_name, vehicle_no, total, paid, due, notes, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        invoice_id = db_controller_instance.execute_query(invoice_query, (
            invoice_no, sale_date, party_id, party_name, vehicle_no, total_amount, paid_amount, due_amount, notes, status
        ))

        # Insert into sales_items
        item_query = "INSERT INTO sales_items (invoice_id, product_id, product_name, quantity, rate, subtotal) VALUES (?, ?, ?, ?, ?, ?)"
        total_brick_amount = 0
        
        for i in range(len(product_ids)):
            prod_id = int(product_ids[i])
            prod_name = db_controller_instance.execute_query("SELECT name FROM brick_types WHERE id = ?", (prod_id,), fetch="one")[0]
            qty = int(quantities[i])
            rate = float(rates[i])
            sub = float(subtotals[i])
            total_brick_amount += qty
            
            db_controller_instance.execute_query(item_query, (invoice_id, prod_id, prod_name, qty, rate, sub))

        # --- 5. Add to Ledger (using new logic) ---
        ledger_desc = f"Sale via Invoice: {invoice_no} ({total_brick_amount} pcs) [SALE_INVOICE_ID:{invoice_id}]"
        db_controller_instance.execute_query(
            "INSERT INTO ledger_book (date, party_name, description, debit) VALUES (?, ?, ?, ?)",
            (sale_date, party_name, ledger_desc, total_amount)
        )
        if paid_amount > 0:
            ledger_desc_paid = f"Payment for Invoice: {invoice_no} [PAID_FOR_INVOICE_ID:{invoice_id}]"
            db_controller_instance.execute_query(
                "INSERT INTO ledger_book (date, party_name, description, credit) VALUES (?, ?, ?, ?)",
                (sale_date, party_name, ledger_desc_paid, paid_amount)
            )

        # Commit the transaction
        db_controller_instance.execute_query("COMMIT;")
        flash('Income added successfully!', 'success')
        return redirect(url_for('income.manage_income'))

    except Exception as e:
        db_controller_instance.execute_query("ROLLBACK;") # Roll back all changes on error
        flash(f'An error occurred: {e}', 'danger')
        return redirect(url_for('income.add_income_form'))