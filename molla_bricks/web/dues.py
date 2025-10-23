# molla_bricks/web/dues.py
from flask import Blueprint, render_template, request, flash
from molla_bricks.web import db_controller_instance

bp = Blueprint('dues', __name__, url_prefix='/dues')

@bp.route('/')
def baki_khata():
    """Renders the Baki Khata (Dues) page."""
    
    # Get filter criteria from URL (e.g., /dues?customer_id=5)
    customer_id = request.args.get('customer_id', type=int)

    # Fetch customers who have outstanding dues for the filter dropdown
    cust_query = """
        SELECT c.id, c.name FROM customers c 
        JOIN nagad_khata n ON c.id = n.customer_id 
        WHERE n.due_amount > 0.01 
        GROUP BY c.id ORDER BY c.name
    """
    customers_with_dues = db_controller_instance.execute_query(cust_query, fetch="all")

    # Fetch the actual due records
    query = """
        SELECT id, date, chalan_no, customer_name, total_amount, paid_amount, due_amount 
        FROM nagad_khata 
        WHERE due_amount > 0.01
    """
    params = []
    
    if customer_id:
        query += " AND customer_id = ?"
        params.append(customer_id)
        
    query += " ORDER BY id ASC" # Show oldest dues first
    
    due_records = db_controller_instance.execute_query(query, tuple(params), fetch="all")
    
    # Calculate total due for the filtered view
    total_due = sum(row[6] for row in due_records)
    
    return render_template('baki_khata.html', 
                           dues=due_records, 
                           customers=customers_with_dues, 
                           total_due=total_due,
                           selected_customer_id=customer_id)