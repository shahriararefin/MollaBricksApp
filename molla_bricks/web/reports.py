# molla_bricks/web/reports.py
from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file
from molla_bricks.web import db_controller_instance
from molla_bricks.core.services.ledger_service import LedgerService
from flask_login import login_required
from datetime import datetime, timedelta

bp = Blueprint('reports', __name__, url_prefix='/reports')

@bp.route('/brick-statement')
@login_required
def brick_statement():
    today = datetime.now().date()
    start_date = request.args.get('start_date', default=(today - timedelta(days=30)).strftime('%Y-%m-%d'), type=str)
    end_date = request.args.get('end_date', default=today.strftime('%Y-%m-%d'), type=str)
    brick_type = request.args.get('brick_type', default="", type=str)
    brick_types = [row[0] for row in db_controller_instance.execute_query("SELECT name FROM brick_types ORDER BY name", fetch="all")]
    query = "SELECT brick_type, SUM(brick_amount) FROM nagad_khata WHERE date BETWEEN ? AND ?"
    params = [start_date, end_date]
    if brick_type:
        query += " AND brick_type = ?"; params.append(brick_type)
    query += " GROUP BY brick_type ORDER BY brick_type"; records = db_controller_instance.execute_query(query, tuple(params), fetch="all") or []
    total_quantity = sum(r[1] for r in records)
    return render_template('brick_statement.html', records=records, brick_types=brick_types, start_date=start_date, end_date=end_date, selected_brick_type=brick_type, total_quantity=total_quantity)

@bp.route('/coal-statement')
@login_required
def coal_statement():
    """Renders the Coal Statement page."""
    today = datetime.now().date()
    start_date = request.args.get('start_date', default=(today - timedelta(days=30)).strftime('%Y-%m-%d'), type=str)
    end_date = request.args.get('end_date', default=today.strftime('%Y-%m-%d'), type=str)
    sector = request.args.get('sector', default="", type=str)

    sectors = db_controller_instance.execute_query("SELECT name FROM coal_sectors ORDER BY name", fetch="all") or []

    query = "SELECT * FROM coal_purchases WHERE date BETWEEN ? AND ?"
    params = [start_date, end_date]
    if sector:
        query += " AND sector = ?"; params.append(sector)
    query += " ORDER BY date DESC"
    
    entries = db_controller_instance.execute_query(query, tuple(params), fetch="all") or []
    
    total_quantity = sum(e[6] for e in entries) # sum(quantity)
    total_amount = sum(e[8] for e in entries) # sum(total)

    return render_template('coal_statement.html', 
                           entries=entries,
                           start_date=start_date,
                           end_date=end_date,
                           sectors=[s[0] for s in sectors],
                           selected_sector=sector,
                           total_quantity=total_quantity,
                           total_amount=total_amount)

# --- NEW: Route to print the coal statement ---
@bp.route('/print-coal-statement')
@login_required
def print_coal_statement():
    start_date = request.args.get('start_date', default="", type=str)
    end_date = request.args.get('end_date', default="", type=str)
    sector = request.args.get('sector', default="", type=str)

    query = "SELECT * FROM coal_purchases WHERE date BETWEEN ? AND ?"
    params = [start_date, end_date]
    if sector:
        query += " AND sector = ?"; params.append(sector)
    query += " ORDER BY date ASC"
    
    entries = db_controller_instance.execute_query(query, tuple(params), fetch="all") or []
    if not entries:
        flash("No data found for this period to print.", 'warning')
        return redirect(url_for('reports.coal_statement'))
        
    total_quantity = sum(e[6] for e in entries)
    total_amount = sum(e[8] for e in entries)
    totals = {'quantity': total_quantity, 'amount': total_amount}

    try:
        pdf_path = LedgerService.generate_coal_statement_pdf(start_date, end_date, sector, entries, totals)
        return send_file(pdf_path, as_attachment=True)
    except Exception as e:
        flash(f"Error generating PDF: {e}", 'danger')
        return redirect(url_for('reports.coal_statement'))


# --- Other Report Placeholders ---
@bp.route('/owner-cash-report')
@login_required
def owner_cash_report():
    flash("Owner Cash Report page is under construction.", "info"); return render_template('placeholder_page.html', title="Owner Cash Report")
@bp.route('/cash-book')
@login_required
def cash_book():
    flash("Cash book page is under construction.", "info"); return render_template('placeholder_page.html', title="Cash book")
@bp.route('/bank-book')
@login_required
def bank_book():
    flash("Bank book page is under construction.", "info"); return render_template('placeholder_page.html', title="Bank book")
@bp.route('/income-report')
@login_required
def income_report():
    flash("Income report page is under construction.", "info"); return render_template('placeholder_page.html', title="Income report")
@bp.route('/expense-report')
@login_required
def expense_report():
    flash("Expense report page is under construction.", "info"); return render_template('placeholder_page.html', title="Expense report")
@bp.route('/profit-and-loss')
@login_required
def profit_and_loss_report():
    flash("Profit and loss report page is under construction.", "info"); return render_template('placeholder_page.html', title="Profit and loss report")
@bp.route('/summary-report')
@login_required
def summary_report():
    flash("Summary report page is under construction.", "info"); return render_template('placeholder_page.html', title="Summary report")
@bp.route('/closing-report')
@login_required
def closing_report():
    flash("Closing report page is under construction.", "info"); return render_template('placeholder_page.html', title="Closing report")
@bp.route('/income-due-report')
@login_required
def income_due_report():
    flash("Income Due Report page is under construction.", "info"); return render_template('placeholder_page.html', title="Income Due Report")
@bp.route('/expense-due-report')
@login_required
def expense_due_report():
    flash("Expense Due Report page is under construction.", "info"); return render_template('placeholder_page.html', title="Expense Due Report")