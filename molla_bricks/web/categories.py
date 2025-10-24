# molla_bricks/web/categories.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from molla_bricks.web import db_controller_instance
from flask_login import login_required

bp = Blueprint('categories', __name__, url_prefix='/categories')

@bp.route('/')
@login_required
def index():
    categories = db_controller_instance.execute_query("SELECT * FROM expense_categories ORDER BY name", fetch="all")
    return render_template('manage_categories.html', categories=categories)

@bp.route('/add', methods=['POST'])
@login_required
def add_category():
    name = request.form.get('name')
    if not name:
        flash('Category name is required.', 'danger')
        return redirect(url_for('categories.index'))
    try:
        db_controller_instance.execute_query("INSERT INTO expense_categories (name) VALUES (?)", (name,))
        flash('Category added successfully.', 'success')
    except Exception as e:
        flash(f"Error: {e}", 'danger')
    return redirect(url_for('categories.index'))

@bp.route('/edit', methods=['POST'])
@login_required
def edit_category():
    category_id = request.form.get('id')
    name = request.form.get('name')
    if not name:
        flash('Category name is required.', 'danger')
        return redirect(url_for('categories.index'))
    try:
        db_controller_instance.execute_query("UPDATE expense_categories SET name = ? WHERE id = ?", (name, category_id))
        flash('Category updated successfully.', 'success')
    except Exception as e:
        flash(f"Error: {e}", 'danger')
    return redirect(url_for('categories.index'))

@bp.route('/delete/<int:category_id>', methods=['POST'])
@login_required
def delete_category(category_id):
    try:
        db_controller_instance.execute_query("DELETE FROM expense_categories WHERE id = ?", (category_id,))
        flash('Category deleted successfully.', 'success')
    except Exception as e:
        flash('Error: This category may be in use and cannot be deleted.', 'danger')
    return redirect(url_for('categories.index'))