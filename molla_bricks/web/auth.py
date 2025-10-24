# molla_bricks/web/auth.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from molla_bricks.web import db_controller_instance
from molla_bricks.web.models import User

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index')) # Already logged in

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # We use your existing verify_user method from the desktop app
        if db_controller_instance.verify_user(username, password):
            user = User.get_by_username(username)
            login_user(user) # This creates the session
            return redirect(url_for('dashboard.index')) # Redirect to dashboard
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')

@bp.route('/logout')
@login_required # You must be logged in to log out
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))