# molla_bricks/web/language.py
from flask import Blueprint, redirect, url_for, session, request

bp = Blueprint('language', __name__)

@bp.route('/lang/<lang_code>')
def set_language(lang_code):
    """Sets the user's language in the session."""
    if lang_code in ('en', 'bn'):
        session['lang'] = lang_code
    return redirect(request.referrer or url_for('dashboard.index'))

# --- NEW: Route to change the theme ---
@bp.route('/theme/<theme_name>')
def set_theme(theme_name):
    """Sets the user's theme in the session."""
    if theme_name in ('superhero', 'litera'): # 'superhero' = Dark, 'litera' = Light
        session['theme'] = theme_name
    return redirect(request.referrer or url_for('dashboard.index'))