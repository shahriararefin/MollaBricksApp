# molla_bricks/web/api.py
from flask import Blueprint, jsonify
from molla_bricks.web import db_controller_instance
from flask_login import login_required # <-- ADDED

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/customer_balance/<int:customer_id>')
@login_required # <-- ADDED
def get_customer_balance(customer_id):
    cust_query = "SELECT name FROM customers WHERE id = ?"; customer = db_controller_instance.execute_query(cust_query, (customer_id,), fetch="one")
    if not customer:
        return jsonify({'error': 'Customer not found'}), 404
    balance_query = "SELECT SUM(credit) - SUM(debit) FROM ledger_book WHERE party_name = ?"; balance = db_controller_instance.execute_query(balance_query, (customer[0],), fetch="one")[0] or 0.0
    return jsonify({ 'balance': balance, 'balance_str': f"{balance:,.2f} BDT" })