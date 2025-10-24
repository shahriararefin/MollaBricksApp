# molla_bricks/web/round.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from molla_bricks.web import db_controller_instance
from flask_login import login_required
from datetime import datetime

bp = Blueprint('round', __name__, url_prefix='/round')

@bp.route('/')
@login_required
def index():
    """Renders the Round Management page."""
    
    # Fetch all pot entries that are "Ready for Firing"
    pot_query = "SELECT id, pot_name, quantity_shaped FROM pot_entries WHERE status = 'Ready for Firing'"
    # --- FIXED: Added 'or []' to prevent error on None ---
    available_pots = db_controller_instance.execute_query(pot_query, fetch="all") or []
    
    # Fetch all round entries
    round_query = """
        SELECT r.id, r.date, r.round_name, p.pot_name, r.bricks_loaded, r.coal_cost, r.firing_status, r.notes
        FROM round_entries r
        LEFT JOIN pot_entries p ON r.pot_id = p.id
        ORDER BY r.date DESC, r.id DESC
    """
    # --- FIXED: Added 'or []' to prevent error on None ---
    entries = db_controller_instance.execute_query(round_query, fetch="all") or []
    
    return render_template('manage_rounds.html', 
                           entries=entries,
                           available_pots=available_pots,
                           today=datetime.now().strftime('%Y-%m-%d'))

@bp.route('/add', methods=['POST'])
@login_required
def add_entry():
    date = request.form.get('date')
    round_name = request.form.get('round_name')
    pot_id = request.form.get('pot_id', type=int)
    bricks_loaded = request.form.get('bricks_loaded', 0, type=int)
    coal_cost = request.form.get('coal_cost', 0, type=float)
    firing_status = request.form.get('firing_status')
    notes = request.form.get('notes')

    if not date or not round_name or not pot_id:
        flash('Date, Round Name, and Linked Pot are required.', 'danger')
        return redirect(url_for('round.index'))

    try:
        query = """
            INSERT INTO round_entries (date, round_name, pot_id, bricks_loaded, coal_cost, firing_status, notes) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        new_round_id = db_controller_instance.execute_query(query, (date, round_name, pot_id, bricks_loaded, coal_cost, firing_status, notes))
        
        db_controller_instance.execute_query("UPDATE pot_entries SET status = 'Firing' WHERE id = ?", (pot_id,))
        
        if coal_cost > 0:
            ledger_desc = f"Coal cost for Round: {round_name} [ROUND_ID:{new_round_id}]"
            db_controller_instance.execute_query("INSERT INTO ledger_book (date, party_name, description, debit) VALUES (?, ?, ?, ?)", (date, "Coal Expense", ledger_desc, coal_cost))

        flash('Firing round started and coal cost recorded in ledger.', 'success')
    except Exception as e:
        flash(f'Error adding entry: {e}', 'danger')
    
    return redirect(url_for('round.index'))

@bp.route('/delete/<int:entry_id>', methods=['POST'])
@login_required
def delete_entry(entry_id):
    try:
        db_controller_instance.execute_query("DELETE FROM ledger_book WHERE description LIKE ?", (f"%[ROUND_ID:{entry_id}]%",))
        pot_id = db_controller_instance.execute_query("SELECT pot_id FROM round_entries WHERE id = ?", (entry_id,), fetch="one")
        if pot_id:
            db_controller_instance.execute_query("UPDATE pot_entries SET status = 'Ready for Firing' WHERE id = ?", (pot_id[0],))
        
        db_controller_instance.execute_query("DELETE FROM round_entries WHERE id = ?", (entry_id,))
        flash('Round deleted, pot status reverted, and ledger entry removed.', 'success')
    except Exception as e:
        flash(f'Error deleting entry: {e}', 'danger')
    return redirect(url_for('round.index'))