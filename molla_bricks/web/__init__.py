# molla_bricks/web/__init__.py
from flask import Flask
from molla_bricks.core.db.db_controller import DBController

# Create a single, shared database instance
db_controller_instance = DBController()

def create_app():
    """Create and configure the Flask app."""
    app = Flask(__name__, template_folder='../../templates')
    app.secret_key = 'your_super_secret_key_for_sessions'

    # Import and register the Blueprints (our route files)
    from . import customers
    from . import sales
    from . import api

    app.register_blueprint(customers.bp)
    app.register_blueprint(sales.bp)
    app.register_blueprint(api.bp)

    return app