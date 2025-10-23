# molla_bricks/web/__init__.py
from flask import Flask
from molla_bricks.core.db.db_controller import DBController

db_controller_instance = DBController()

def create_app():
    app = Flask(__name__, template_folder='../../templates')
    app.secret_key = 'your_super_secret_key_for_sessions'

    from . import customers
    from . import sales
    from . import api
    from . import dues
    from . import ledger
    from . import salary 
    from . import expenses

    app.register_blueprint(customers.bp)
    app.register_blueprint(sales.bp)
    app.register_blueprint(api.bp)
    app.register_blueprint(dues.bp)
    app.register_blueprint(ledger.bp)
    app.register_blueprint(salary.bp) 
    app.register_blueprint(expenses.bp)

    return app