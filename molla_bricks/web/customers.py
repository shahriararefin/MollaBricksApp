# molla_bricks/web/customers.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from molla_bricks.web import db_controller_instance # Import our shared DB instance
import logging

# Create a Blueprint. 'customers' is the name we'll use in url_for()
bp = Blueprint('customers', __name__, url_prefix='/customers')

@bp.route('/')
def index():
    query = "SELECT id, name, address, phone FROM customers ORDER BY name ASC"
    customers = db_controller_instance.execute_query(query, fetch="all")
    return render_template('index.html', customers=customers)

@bp.route('/customers/add')
def add_form():
    return render_template('add_customer.html')

@bp.route('/customers/add', methods=['POST'])
def add():
    name = request.form.get('name')
    address = request.form.get('address')
    phone = request.form.get('phone')
    if not name:
        flash('Customer name is required.', 'danger')
        return redirect(url_for('customers.add_form'))
    query = "INSERT INTO customers (name, address, phone) VALUES (?, ?, ?)"
    try:
        db_controller_instance.execute_query(query, (name, address, phone))
        flash('Customer added successfully!', 'success')
        return redirect(url_for('customers.index'))
    except Exception as e:
        flash(f'Error adding customer: {e}', 'danger')
        return redirect(url_for('customers.add_form'))

@bp.route('/customers/edit/<int:customer_id>')
def edit_form(customer_id):
    query = "SELECT id, name, address, phone FROM customers WHERE id = ?"
    customer = db_controller_instance.execute_query(query, (customer_id,), fetch="one")
    if customer:
        return render_template('edit_customer.html', customer=customer)
    else:
        flash('Customer not found.', 'danger')
        return redirect(url_for('customers.index'))

@bp.route('/customers/edit', methods=['POST'])
def edit():
    customer_id = request.form.get('customer_id'); name = request.form.get('name'); address = request.form.get('address'); phone = request.form.get('phone')
    if not name:
        flash('Customer name is required.', 'danger')
        return redirect(url_for('customers.edit_form', customer_id=customer_id))
    query = "UPDATE customers SET name = ?, address = ?, phone = ? WHERE id = ?"
    try:
        db_controller_instance.execute_query(query, (name, address, phone, customer_id))
        flash('Customer updated successfully!', 'success')
        return redirect(url_for('customers.index'))
    except Exception as e:
        flash(f'Error updating customer: {e}', 'danger')
        return redirect(url_for('customers.edit_form', customer_id=customer_id))

@bp.route('/customers/delete/<int:customer_id>')
def delete(customer_id):
    try:
        query = "DELETE FROM customers WHERE id = ?"
        db_controller_instance.execute_query(query, (customer_id,))
        flash('Customer deleted successfully.', 'success')
    except Exception as e:
        logging.error(f"Error deleting customer: {e}")
        flash('Error: This customer cannot be deleted, they may have sales records.', 'danger')
    return redirect(url_for('customers.index'))