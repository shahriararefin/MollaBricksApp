# molla_bricks/web/salary.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from molla_bricks.web import db_controller_instance
from datetime import datetime

bp = Blueprint('salary', __name__, url_prefix='/salary')

@bp.route('/')
def index():
    """Renders the main personnel management page."""
    staff_query = "SELECT id, name, monthly_salary FROM staff ORDER BY name ASC"
    staff = db_controller_instance.execute_query(staff_query, fetch="all")
    
    contractor_query = "SELECT id, name, section, phone FROM contractors ORDER BY section, name"
    contractors = db_controller_instance.execute_query(contractor_query, fetch="all")
    
    return render_template('manage_personnel.html', staff_list=staff, contractor_list=contractors)

@bp.route('/add_staff', methods=['POST'])
def add_staff():
    name = request.form.get('name')
    salary = request.form.get('salary', type=float)
    
    if not name or not salary or salary <= 0:
        flash('Staff name and a valid salary are required.', 'danger')
        return redirect(url_for('salary.index'))
    
    try:
        db_controller_instance.execute_query("INSERT INTO staff (name, monthly_salary) VALUES (?, ?)", (name, salary))
        flash('Monthly staff member added successfully.', 'success')
    except Exception as e:
        flash(f'Error adding staff: {e}', 'danger')
    
    return redirect(url_for('salary.index'))

@bp.route('/add_contractor', methods=['POST'])
def add_contractor():
    name = request.form.get('name')
    section = request.form.get('section')
    phone = request.form.get('phone')
    
    if not name or not section:
        flash('Contractor name and section are required.', 'danger')
        return redirect(url_for('salary.index'))

    try:
        db_controller_instance.execute_query("INSERT INTO contractors (name, section, phone) VALUES (?, ?, ?)", (name, section, phone))
        flash('Contractor added successfully.', 'success')
    except Exception as e:
        flash(f'Error adding contractor: {e}', 'danger')

    return redirect(url_for('salary.index'))

@bp.route('/pay/<person_type>/<int:person_id>')
def pay_form(person_type, person_id):
    """Shows the payment form for a specific person."""
    if person_type == 'staff':
        record = db_controller_instance.execute_query("SELECT name FROM staff WHERE id = ?", (person_id,), fetch="one")
        name = record[0]
    else: # contractor
        record = db_controller_instance.execute_query("SELECT name, section FROM contractors WHERE id = ?", (person_id,), fetch="one")
        name = f"{record[0]} ({record[1]})"

    if not record:
        flash("Personnel not found.", 'danger')
        return redirect(url_for('salary.index'))

    return render_template('record_payment.html', 
                           person_id=person_id, 
                           name=name, 
                           person_type=person_type, 
                           today=datetime.now().strftime('%Y-%m-%d'))

@bp.route('/pay', methods=['POST'])
def record_payment():
    """Handles the submission of the payment form."""
    person_id = request.form.get('person_id', type=int)
    person_type = request.form.get('person_type')
    payee_name = request.form.get('payee_name')
    payment_date = request.form.get('date')
    notes = request.form.get('notes')
    try:
        amount = float(request.form.get('amount') or 0.0)
        if amount <= 0:
            raise ValueError("Payment must be greater than zero")
    except ValueError as e:
        flash(f'Invalid amount. {e}', 'danger')
        return redirect(url_for('salary.pay_form', person_type=person_type, person_id=person_id))

    try:
        if person_type == "staff":
            new_id = db_controller_instance.execute_query("INSERT INTO salary_payments (staff_id, payment_date, paid_amount, notes) VALUES (?, ?, ?, ?)", (person_id, payment_date, amount, notes))
            ledger_desc = f"Salary: {notes or 'Payment'} to {payee_name} [SALARY_PAYMENT_ID:{new_id}]"
        else: # contractor
            new_id = db_controller_instance.execute_query("INSERT INTO contractor_payments (contractor_id, payment_date, amount, description) VALUES (?, ?, ?, ?)", (person_id, payment_date, amount, notes))
            ledger_desc = f"Contractor: {notes or 'Work Pmt'} to {payee_name} [CON_PAY_ID:{new_id}]"
        
        db_controller_instance.execute_query("INSERT INTO ledger_book (date, party_name, description, debit) VALUES (?, ?, ?, ?)", (payment_date, payee_name, ledger_desc, amount))
        flash('Payment saved and recorded in ledger.', 'success')
        return redirect(url_for('salary.index'))

    except Exception as e:
        flash(f'Error saving payment: {e}', 'danger')
        return redirect(url_for('salary.pay_form', person_type=person_type, person_id=person_id))