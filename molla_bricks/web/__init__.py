# molla_bricks/web/__init__.py
from flask import Flask, session, request
from molla_bricks.core.db.db_controller import DBController
from flask_login import LoginManager
from flask_babel import Babel

db_controller_instance = DBController()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'You must be logged in to access this page.'
login_manager.login_message_category = 'danger'
babel = Babel()

@login_manager.user_loader
def load_user(user_id):
    from .models import User
    return User.get(user_id)

def create_app():
    app = Flask(__name__, template_folder='../../templates', static_folder='static')
    app.secret_key = 'your_super_secret_key_for_sessions'
    
    login_manager.init_app(app)
    babel.init_app(app)

    def get_locale():
        lang = session.get('lang');
        if lang: return lang
        return request.accept_languages.best_match(['en', 'bn'])
    
    babel.locale_selector = get_locale

    # --- MODIFIED: Removed 'sales', added 'income' ---
    from . import auth, dashboard, customers, api, dues, ledger, salary, expenses, insights, language, categories, brick_types, pot, round, load_unload, fiscal_year, owner, accounts, reports, transactions
    from . import income  # <-- ADDED

    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp) 
    app.register_blueprint(customers.bp)
    # app.register_blueprint(sales.bp) # <-- REMOVED
    app.register_blueprint(api.bp)
    app.register_blueprint(dues.bp)
    app.register_blueprint(ledger.bp)
    app.register_blueprint(salary.bp)
    app.register_blueprint(expenses.bp)
    app.register_blueprint(insights.bp)
    app.register_blueprint(language.bp)
    app.register_blueprint(categories.bp)
    app.register_blueprint(brick_types.bp)
    app.register_blueprint(pot.bp)
    app.register_blueprint(round.bp)
    app.register_blueprint(load_unload.bp)
    app.register_blueprint(fiscal_year.bp)
    app.register_blueprint(owner.bp)
    app.register_blueprint(accounts.bp)
    app.register_blueprint(reports.bp)
    app.register_blueprint(transactions.bp)
    app.register_blueprint(income.bp) # <-- ADDED

    return app