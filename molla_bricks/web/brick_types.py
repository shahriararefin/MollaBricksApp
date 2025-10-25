# molla_bricks/web/brick_types.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from molla_bricks.web import db_controller_instance
from flask_login import login_required, current_user

bp = Blueprint('brick_types', __name__, url_prefix='/brick-types')

@bp.route('/')
@login_required
def index():
    name = request.args.get('name', default="", type=str)
    code = request.args.get('code', default="", type=str)
    category = request.args.get('category', default="", type=str)
    status = request.args.get('status', default="", type=str)

    categories_raw = db_controller_instance.execute_query("SELECT name FROM expense_categories ORDER BY name", fetch="all") or []
    categories_list = [c[0] for c in categories_raw]

    query = "SELECT * FROM brick_types"
    params = []; where_clauses = []
    if name: where_clauses.append("name LIKE ?"); params.append(f"%{name}%")
    if code: where_clauses.append("product_code LIKE ?"); params.append(f"%{code}%")
    if category: where_clauses.append("category = ?"); params.append(category)
    if status: where_clauses.append("status = ?"); params.append(status)
    if where_clauses: query += " WHERE " + " AND ".join(where_clauses)
    query += " ORDER BY name"
    
    types = db_controller_instance.execute_query(query, tuple(params), fetch="all")
    
    return render_template('manage_brick_types.html', 
                           brick_types=types or [], categories=categories_list,
                           filter_name=name, filter_code=code, filter_category=category, filter_status=status)

@bp.route('/add', methods=['POST'])
@login_required
def add_type():
    name = request.form.get('name'); product_code = request.form.get('product_code')
    category = request.form.get('category'); unit = request.form.get('unit')
    
    if not name or not product_code or not category or not unit:
        flash('Name, Code, Category, and Unit are required.', 'danger')
        return redirect(url_for('brick_types.index'))
    try:
        query = "INSERT INTO brick_types (name, product_code, category, unit, status, made_by) VALUES (?, ?, ?, ?, ?, ?)"
        params = (name, product_code, category, unit, 'Active', current_user.username)
        db_controller_instance.execute_query(query, params)
        flash('Product/Class added successfully.', 'success')
    except Exception as e:
        flash(f"Error: {e}", 'danger')
    return redirect(url_for('brick_types.index'))

@bp.route('/edit', methods=['POST'])
@login_required
def edit_type():
    type_id = request.form.get('id'); name = request.form.get('name'); product_code = request.form.get('product_code')
    category = request.form.get('category'); unit = request.form.get('unit'); status = request.form.get('status')
    if not all([type_id, name, product_code, category, unit, status]):
        flash('All fields are required.', 'danger'); return redirect(url_for('brick_types.index'))
    try:
        query = "UPDATE brick_types SET name = ?, product_code = ?, category = ?, unit = ?, status = ? WHERE id = ?"
        db_controller_instance.execute_query(query, (name, product_code, category, unit, status, type_id))
        flash('Product/Class updated successfully.', 'success')
    except Exception as e:
        flash(f"Error: {e}", 'danger')
    return redirect(url_for('brick_types.index'))

@bp.route('/delete/<int:type_id>', methods=['POST'])
@login_required
def delete_type(type_id):
    try:
        db_controller_instance.execute_query("DELETE FROM brick_types WHERE id = ?", (type_id,))
        flash('Product/Class deleted successfully.', 'success')
    except Exception as e:
        flash('Error: This class may be in use in sales records and cannot be deleted.', 'danger')
    return redirect(url_for('brick_types.index'))