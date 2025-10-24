# molla_bricks/web/salary.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from molla_bricks.web import db_controller_instance
from datetime import datetime
from flask_login import login_required # <-- ADDED

bp = Blueprint('salary', __name__, url_prefix='/salary')

@bp.route('/')
@login_required # <-- ADDED
def index():
    staff = db_controller_instance.execute_query("SELECT id, name, monthly_salary FROM staff ORDER BY name ASC", fetch="all")
    contractors = db_controller_instance.execute_query("SELECT id, name, section, phone FROM contractors ORDER BY section, name", fetch="all")
    return render_template('manage_personnel.html', staff_list=staff, contractor_list=contractors)

@bp.route('/add_staff', methods=['POST'])
@login_required # <-- ADDED
def add_staff():
    name = request.form.get('name'); salary = request.form.get('salary', type=float)
    if not name or not salary or salary <= 0:
        flash('Staff name and a valid salary are required.', 'danger'); return redirect(url_for('salary.index'))
    try:
        db_controller_instance.execute_query("INSERT INTO staff (name, monthly_salary) VALUES (?, ?)", (name, salary))
        flash('Monthly staff member added successfully.', 'success')
    except Exception as e: flash(f'Error adding staff: {e}', 'danger')
    return redirect(url_for('salary.index'))

@bp.route('/add_contractor', methods=['POST'])
@login_required # <-- ADDED
def add_contractor():
    name = request.form.get('name'); section = request.form.get('section'); phone = request.form.get('phone')
    if not name or not section:
        flash('Contractor name and section are required.', 'danger'); return redirect(url_for('salary.index'))
    try:
        db_controller_instance.execute_query("INSERT INTO contractors (name, section, phone) VALUES (?, ?, ?)", (name, section, phone))
        flash('Contractor added successfully.', 'success')
    except Exception as e: flash(f'Error adding contractor: {e}', 'danger')
    return redirect(url_for('salary.index'))

@bp.route('/pay/<person_type>/<int:person_id>')
@login_required # <-- ADDED
def pay_form(person_type, person_id):
    if person_type == 'staff':
        record = db_controller_instance.execute_query("SELECT name FROM staff WHERE id = ?", (person_id,), fetch="one"); name = record[0]
    else:
        record = db_controller_instance.execute_query("SELECT name, section FROM contractors WHERE id = ?", (person_id,), fetch="one"); name = f"{record[0]} ({record[1]})"
    if not record: flash("Personnel not found.", 'danger'); return redirect(url_for('salary.index'))
    return render_template('record_payment.html', person_id=person_id, name=name, person_type=person_type, today=datetime.now().strftime('%Y-%m-%d'))

@bp.route('/pay', methods=['POST'])
@login_required # <-- ADDED
def record_payment():
    person_id = request.form.get('person_id', type=int); person_type = request.form.get('person_type'); payee_name = request.form.get('payee_name')
    payment_date = request.form.get('date'); notes = request.form.get('notes')
    try:
        amount = float(request.form.get('amount') or 0.0)
        if amount <= 0: raise ValueError("Payment must be greater than zero")
    except ValueError as e:
        flash(f'Invalid amount. {e}', 'danger'); return redirect(url_for('salary.pay_form', person_type=person_type, person_id=person_id))
    try:
        if person_type == "staff":
            new_id = db_controller_instance.execute_query("INSERT INTO salary_payments (staff_id, payment_date, paid_amount, notes) VALUES (?, ?, ?, ?)", (person_id, payment_date, amount, notes))
            ledger_desc = f"Salary: {notes or 'Payment'} to {payee_name} [SALARY_PAYMENT_ID:{new_id}]"
        else:
            new_id = db_controller_instance.execute_query("INSERT INTO contractor_payments (contractor_id, payment_date, amount, description) VALUES (?, ?, ?, ?)", (person_id, payment_date, amount, notes))
            ledger_desc = f"Contractor: {notes or 'Work Pmt'} to {payee_name} [CON_PAY_ID:{new_id}]"
        db_controller_instance.execute_query("INSERT INTO ledger_book (date, party_name, description, debit) VALUES (?, ?, ?, ?)", (payment_date, payee_name, ledger_desc, amount))
        flash('Payment saved and recorded in ledger.', 'success')
    except Exception as e: flash(f'Error saving payment: {e}', 'danger')
    return redirect(url_for('salary.index'))

@bp.route('/edit/<person_type>/<int:person_id>')
@login_required # <-- ADDED
def edit_form(person_type, person_id):
    if person_type == 'staff':
        record = db_controller_instance.execute_query("SELECT id, name, monthly_salary FROM staff WHERE id = ?", (person_id,), fetch="one")
        person = {'id': record[0], 'name': record[1], 'detail': record[2]}
    else:
        record = db_controller_instance.execute_query("SELECT id, name, section, phone FROM contractors WHERE id = ?", (person_id,), fetch="one")
        person = {'id': record[0], 'name': record[1], 'detail': record[2], 'phone': record[3]}
    return render_template('edit_personnel.html', person=person, person_type=person_type)

@bp.route('/edit', methods=['POST'])
@login_required # <-- ADDED
def edit_personnel():
    person_id = request.form.get('person_id', type=int); person_type = request.form.get('person_type')
    name = request.form.get('name'); detail = request.form.get('detail')
    if not name or not detail:
        flash("Name and Detail (Salary/Section) are required.", 'danger'); return redirect(url_for('salary.edit_form', person_type=person_type, person_id=person_id))
    try:
        if person_type == 'staff':
            salary = float(detail)
            db_controller_instance.execute_query("UPDATE staff SET name = ?, monthly_salary = ? WHERE id = ?", (name, salary, person_id))
        else:
            phone = request.form.get('phone')
            db_controller_instance.execute_query("UPDATE contractors SET name = ?, section = ?, phone = ? WHERE id = ?", (name, detail, phone, person_id))
        flash(f"{person_type.title()} updated successfully.", 'success')
    except Exception as e: flash(f"Error updating: {e}", 'danger')
    return redirect(url_for('salary.index'))

@bp.route('/delete/<person_type>/<int:person_id>', methods=['POST'])
@login_required # <-- ADDED
def delete_personnel(person_type, person_id):
    try:
        if person_type == 'staff':
            payment_ids = db_controller_instance.execute_query("SELECT id FROM salary_payments WHERE staff_id = ?", (person_id,), fetch="all") or []
            for pid_tuple in payment_ids: db_controller_instance.execute_query("DELETE FROM ledger_book WHERE description LIKE ?", (f"%[SALARY_PAYMENT_ID:{pid_tuple[0]}]%",))
            db_controller_instance.execute_query("DELETE FROM staff WHERE id = ?", (person_id,))
        else:
            payment_ids = db_controller_instance.execute_query("SELECT id FROM contractor_payments WHERE contractor_id = ?", (person_id,), fetch="all") or []
            for pid_tuple in payment_ids: db_controller_instance.execute_query("DELETE FROM ledger_book WHERE description LIKE ?", (f"%[CON_PAY_ID:{pid_tuple[0]}]%",))
            db_controller_instance.execute_query("DELETE FROM contractors WHERE id = ?", (person_id,))
        flash(f"{person_type.title()} deleted successfully.", 'success')
    except Exception as e: flash(f"Error deleting: {e}", 'danger')
    return redirect(url_for('salary.index'))