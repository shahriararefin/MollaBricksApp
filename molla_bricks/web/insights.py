# molla_bricks/web/insights.py
from flask import Blueprint, render_template
from molla_bricks.web import db_controller_instance
from flask_login import login_required # <-- ADDED

bp = Blueprint('insights', __name__, url_prefix='/insights')

@bp.route('/')
@login_required # <-- ADDED
def index():
    valuable_query = "SELECT customer_name, SUM(total_amount) as total_spent FROM nagad_khata WHERE customer_id IS NOT NULL GROUP BY customer_id, customer_name ORDER BY total_spent DESC LIMIT 10"
    valuable_customers = db_controller_instance.execute_query(valuable_query, fetch="all")
    frequent_query = "SELECT customer_name, COUNT(id) as visit_count FROM nagad_khata WHERE customer_id IS NOT NULL GROUP BY customer_id, customer_name ORDER BY visit_count DESC LIMIT 10"
    frequent_customers = db_controller_instance.execute_query(frequent_query, fetch="all")
    return render_template('insights.html', valuable_customers=valuable_customers, frequent_customers=frequent_customers)