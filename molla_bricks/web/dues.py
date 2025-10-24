# molla_bricks/web/dues.py
from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file
from molla_bricks.web import db_controller_instance
from molla_bricks.core.services.nagad_service import NagadService
from flask_login import login_required

bp = Blueprint('dues', __name__, url_prefix='/dues')

@bp.route('/')
@login_required
def baki_khata():
    """Renders the Baki Khata (Dues) page."""
    customer_id = request.args.get('customer_id', type=int)

    cust_query = """
        SELECT c.id, c.name FROM customers c 
        JOIN nagad_khata n ON c.id = n.customer_id 
        WHERE n.due_amount > 0.01 
        GROUP BY c.id ORDER BY c.name
    """
    customers_with_dues = db_controller_instance.execute_query(cust_query, fetch="all")

    query = """
        SELECT id, date, chalan_no, customer_name, total_amount, paid_amount, due_amount 
        FROM nagad_khata 
        WHERE due_amount > 0.01
    """
    params = []
    
    if customer_id:
        query += " AND customer_id = ?"
        params.append(customer_id)
        
    query += " ORDER BY id ASC"
    
    due_records = db_controller_instance.execute_query(query, tuple(params), fetch="all")
    total_due = sum(row[6] for row in due_records)
    
    return render_template('baki_khata.html', 
                           dues=due_records, 
                           customers=customers_with_dues, 
                           total_due=total_due,
                           selected_customer_id=customer_id)

# --- NEW: Route to print the dues report ---
@bp.route('/print_report')
@login_required
def print_report():
    customer_id = request.args.get('customer_id', type=int)
    
    query = """
        SELECT id, date, chalan_no, customer_name, total_amount, paid_amount, due_amount 
        FROM nagad_khata 
        WHERE due_amount > 0.01
    """
    params = []
    customer_name = "All Customers"

    if customer_id:
        query += " AND customer_id = ?"
        params.append(customer_id)
        # Get the customer's name for the report title
        name_record = db_controller_instance.execute_query("SELECT name FROM customers WHERE id = ?", (customer_id,), fetch="one")
        if name_record:
            customer_name = name_record[0]

    query += " ORDER BY id ASC"
    transactions = db_controller_instance.execute_query(query, tuple(params), fetch="all")
    
    if not transactions:
        flash("No dues found to print.", 'warning')
        return redirect(url_for('dues.baki_khata'))

    total_due = sum(row[6] for row in transactions)
    summary = {"customer_name": customer_name, "total_due": total_due}
    
    try:
        # We use the generate_due_report_pdf function that already exists in your NagadService
        pdf_path = NagadService.generate_due_report_pdf(transactions, summary)
        return send_file(pdf_path, as_attachment=True)
    except Exception as e:
        flash(f"Error generating PDF: {e}", 'danger')
        return redirect(url_for('dues.baki_khata'))