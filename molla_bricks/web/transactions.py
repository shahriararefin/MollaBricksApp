# molla_bricks/web/transactions.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from molla_bricks.web import db_controller_instance
from flask_login import login_required

bp = Blueprint('transactions', __name__, url_prefix='/transactions')

@bp.route('/opening-balance')
@login_required
def opening_balance():
    """Placeholder for Opening Balance page."""
    flash("Opening Balance page is under construction.", "info")
    return redirect(url_for('dashboard.index'))

@bp.route('/payment')
@login_required
def payment():
    """Placeholder for Payment page."""
    flash("Payment page is under construction.", "info")
    return redirect(url_for('dashboard.index'))

@bp.route('/collection')
@login_required
def collection():
    """Placeholder for Collection page."""
    flash("Collection page is under construction.", "info")
    return redirect(url_for('dashboard.index'))

@bp.route('/receipt')
@login_required
def receipt():
    """Placeholder for Receipt page."""
    flash("Receipt page is under construction.", "info")
    return redirect(url_for('dashboard.index'))