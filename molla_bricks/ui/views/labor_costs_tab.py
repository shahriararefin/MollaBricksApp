# molla_bricks/ui/views/labor_costs_tab.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, timedelta
from molla_bricks.ui.custom_calendar import CalendarPopup

class RecordPaymentWindow(tk.Toplevel):
    """A dedicated window to record a payment with full details."""
    def __init__(self, parent, db_controller, payee_id, payee_name, payee_type, callback):
        super().__init__(parent)
        self.transient(parent); self.title(f"Record Payment for {payee_name}"); self.db_controller = db_controller
        self.payee_id = payee_id; self.payee_name = payee_name; self.payee_type = payee_type; self.callback = callback
        self.date_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d')); self.amount_var = tk.DoubleVar(); self.notes_var = tk.StringVar()
        self.create_widgets(); self.grab_set(); self.wait_window()

    def create_widgets(self):
        form_frame = ttk.Frame(self, padding=20); form_frame.pack(expand=True, fill="both")
        ttk.Label(form_frame, text=f"Paying: {self.payee_name}", font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 10))
        ttk.Label(form_frame, text="Payment Date:").grid(row=1, column=0, sticky="w", pady=5); date_entry_frame = ttk.Frame(form_frame); date_entry_frame.grid(row=1, column=1, sticky="ew", pady=5)
        ttk.Entry(date_entry_frame, textvariable=self.date_var).pack(side="left"); ttk.Button(date_entry_frame, text="📅", width=3, command=lambda: CalendarPopup(self, self.date_var)).pack(side="left", padx=5)
        ttk.Label(form_frame, text="Amount Paid:").grid(row=2, column=0, sticky="w", pady=5); ttk.Entry(form_frame, textvariable=self.amount_var).grid(row=2, column=1, sticky="ew", pady=5)
        ttk.Label(form_frame, text="Notes/Description:").grid(row=3, column=0, sticky="w", pady=5); ttk.Entry(form_frame, textvariable=self.notes_var).grid(row=3, column=1, sticky="ew", pady=5)
        ttk.Button(form_frame, text="Save Payment", command=self.save_payment, style="Accent.TButton").grid(row=4, column=1, sticky="e", pady=10)

    def save_payment(self):
        payment_date = self.date_var.get(); notes = self.notes_var.get()
        try:
            amount = round(self.amount_var.get(), 2)
            if not amount > 0: messagebox.showerror("Input Error", "Payment amount must be greater than zero.", parent=self); return
        except tk.TclError: messagebox.showerror("Input Error", "Please enter a valid number for the amount.", parent=self); return
        
        if self.payee_type == "Staff":
            new_id = self.db_controller.execute_query("INSERT INTO salary_payments (staff_id, payment_date, paid_amount, notes) VALUES (?, ?, ?, ?)", (self.payee_id, payment_date, amount, notes))
            ledger_desc = f"Salary: {notes or 'Payment'} to {self.payee_name} [SALARY_PAYMENT_ID:{new_id}]"
        else: # Contractor
            new_id = self.db_controller.execute_query("INSERT INTO contractor_payments (contractor_id, payment_date, amount, description) VALUES (?, ?, ?, ?)", (self.payee_id, payment_date, amount, notes))
            ledger_desc = f"Contractor: {notes or 'Work Pmt'} to {self.payee_name} [CON_PAY_ID:{new_id}]"
        
        self.db_controller.execute_query("INSERT INTO ledger_book (date, party_name, description, debit) VALUES (?, ?, ?, ?)", (payment_date, self.payee_name, ledger_desc, amount))
        messagebox.showinfo("Success", "Payment saved and recorded in ledger.", parent=self.master)
        if self.callback: self.callback()
        self.destroy()

class LaborCostsTab(ttk.Frame):
    def __init__(self, parent, db_controller):
        super().__init__(parent)
        self.db_controller = db_controller
        self.notebook = ttk.Notebook(self); self.notebook.pack(expand=True, fill="both", padx=10, pady=10)
        
        self.monthly_payments_frame = MonthlyPaymentsFrame(self.notebook, self.db_controller)
        self.contractor_payments_frame = ContractorPaymentsFrame(self.notebook, self.db_controller)
        self.manage_personnel_frame = ManagePersonnelFrame(self.notebook, self.db_controller)
        
        self.notebook.add(self.monthly_payments_frame, text="Monthly Salary Payments")
        self.notebook.add(self.contractor_payments_frame, text="Contractor Payments")
        self.notebook.add(self.manage_personnel_frame, text="Manage Personnel")
        
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def on_tab_changed(self, event=None):
        selected_tab = self.notebook.index(self.notebook.select())
        if selected_tab == 0: self.monthly_payments_frame.refresh_data()
        elif selected_tab == 1: self.contractor_payments_frame.refresh_data()
        elif selected_tab == 2: self.manage_personnel_frame.refresh_data()

    def refresh_data(self): self.on_tab_changed()

class MonthlyPaymentsFrame(ttk.Frame):
    def __init__(self, parent, db_controller):
        super().__init__(parent, padding=15); self.db_controller = db_controller; self.staff_map = {}
        self.filter_staff_var = tk.StringVar(); self.filter_month_var = tk.StringVar(value=datetime.now().strftime("%B")); self.filter_year_var = tk.StringVar(value=datetime.now().strftime("%Y"))
        self.summary_salary_var = tk.StringVar(value="Monthly Salary: 0.00"); self.summary_paid_var = tk.StringVar(value="Total Paid: 0.00"); self.summary_due_var = tk.StringVar(value="Amount Due: 0.00")
        self.create_widgets()

    def create_widgets(self):
        left_frame = ttk.Frame(self); left_frame.grid(row=0, column=0, padx=(0, 10), sticky="ns"); right_frame = ttk.Frame(self); right_frame.grid(row=0, column=1, sticky="nsew"); self.grid_columnconfigure(1, weight=1)
        summary_frame = ttk.LabelFrame(left_frame, text="Monthly Summary", padding=15); summary_frame.pack(fill="x", pady=10, anchor="n")
        ttk.Label(summary_frame, textvariable=self.summary_salary_var, font=("Arial", 11, "bold")).pack(anchor="w"); ttk.Label(summary_frame, textvariable=self.summary_paid_var, font=("Arial", 11, "bold"), foreground="green").pack(anchor="w"); ttk.Label(summary_frame, textvariable=self.summary_due_var, font=("Arial", 11, "bold"), foreground="red").pack(anchor="w")
        filter_frame = ttk.LabelFrame(right_frame, text="Filter View", padding=10); filter_frame.pack(fill="x")
        months = [datetime(2000, m, 1).strftime('%B') for m in range(1, 13)]
        ttk.Label(filter_frame, text="Staff:").pack(side="left", padx=5); self.filter_staff_combo = ttk.Combobox(filter_frame, textvariable=self.filter_staff_var, state="readonly", width=20); self.filter_staff_combo.pack(side="left", padx=5); self.filter_staff_combo.bind("<<ComboboxSelected>>", self.refresh_payment_history)
        ttk.Label(filter_frame, text="Month:").pack(side="left", padx=5); self.month_combo = ttk.Combobox(filter_frame, textvariable=self.filter_month_var, values=months, state="readonly", width=12); self.month_combo.pack(side="left", padx=5)
        ttk.Label(filter_frame, text="Year:").pack(side="left", padx=5); self.year_entry = ttk.Entry(filter_frame, textvariable=self.filter_year_var, width=6); self.year_entry.pack(side="left", padx=5)
        ttk.Button(filter_frame, text="Filter", command=self.refresh_payment_history).pack(side="left", padx=5); ttk.Button(filter_frame, text="Show All Time", command=self.show_all_time).pack(side="left", padx=5)
        history_frame = ttk.LabelFrame(right_frame, text="Payment History", padding=10); history_frame.pack(fill="both", expand=True, pady=10)
        columns = ("id", "date", "name", "amount", "notes"); self.tree = ttk.Treeview(history_frame, columns=columns, show="headings"); self.tree.heading("id", text="ID"); self.tree.column("id", width=40); self.tree.heading("date", text="Payment Date"); self.tree.column("date", width=100); self.tree.heading("name", text="Staff Name"); self.tree.column("name", width=150); self.tree.heading("amount", text="Amount Paid"); self.tree.column("amount", width=100, anchor="e"); self.tree.heading("notes", text="Notes"); self.tree.column("notes", width=250); self.tree.pack(fill="both", expand=True)

    def refresh_data(self): self.refresh_staff_dropdown()
    def show_all_time(self): self.month_combo.set(""); self.year_entry.delete(0, tk.END); self.refresh_payment_history()
    def refresh_staff_dropdown(self):
        records = self.db_controller.execute_query("SELECT id, name FROM staff ORDER BY name", fetch="all"); self.staff_map = {name: id for id, name in records}; staff_names = list(self.staff_map.keys())
        self.filter_staff_combo['values'] = staff_names
        if staff_names and not self.filter_staff_var.get() in staff_names: self.filter_staff_var.set(staff_names[0])
        self.refresh_payment_history()
    def refresh_payment_history(self, event=None):
        for item in self.tree.get_children(): self.tree.delete(item)
        staff_filter = self.filter_staff_var.get(); month_filter = self.filter_month_var.get(); year_filter = self.filter_year_var.get();
        if not staff_filter: self.update_summary(); return
        query = "SELECT p.id, p.payment_date, s.name, p.paid_amount, p.notes FROM salary_payments p JOIN staff s ON p.staff_id = s.id WHERE s.name = ?"; params = [staff_filter]
        if month_filter and year_filter:
            month_num = datetime.strptime(month_filter, "%B").month; month_year_str = f"{year_filter}-{month_num:02d}"; query += " AND STRFTIME('%Y-%m', p.payment_date) = ?"; params.append(month_year_str)
        query += " ORDER BY p.payment_date DESC"; records = self.db_controller.execute_query(query, tuple(params), fetch="all")
        if records:
            for row in records: self.tree.insert("", "end", values=row)
        self.update_summary()
    def update_summary(self):
        staff_name = self.filter_staff_var.get(); month_filter = self.filter_month_var.get(); year_filter = self.filter_year_var.get()
        if not staff_name: self.summary_salary_var.set("Select a staff member"); self.summary_paid_var.set(""); self.summary_due_var.set(""); return
        staff_record = self.db_controller.execute_query("SELECT monthly_salary FROM staff WHERE name = ?", (staff_name,), fetch="one"); monthly_salary = staff_record[0] if staff_record else 0
        self.summary_salary_var.set(f"Monthly Salary: {monthly_salary:,.2f}")
        if month_filter and year_filter:
            month_num = datetime.strptime(month_filter, "%B").month; month_year_str = f"{year_filter}-{month_num:02d}"; staff_id = self.staff_map[staff_name]
            paid_query = "SELECT SUM(paid_amount) FROM salary_payments WHERE staff_id = ? AND STRFTIME('%Y-%m', payment_date) = ?"; paid_record = self.db_controller.execute_query(paid_query, (staff_id, month_year_str), fetch="one"); total_paid = paid_record[0] or 0
            self.summary_paid_var.set(f"Total Paid this Month: {total_paid:,.2f}"); self.summary_due_var.set(f"Amount Due for Month: {monthly_salary - total_paid:,.2f}")
        else:
            self.summary_paid_var.set("Filter by month/year to see summary"); self.summary_due_var.set("")

class ContractorPaymentsFrame(ttk.Frame):
    def __init__(self, parent, db_controller):
        super().__init__(parent, padding=15); self.db_controller = db_controller; self.contractor_map = {}
        self.filter_contractor_var = tk.StringVar(); self.filter_start_date_var = tk.StringVar(value=(datetime.now().date()-timedelta(days=30)).strftime('%Y-%m-%d')); self.filter_end_date_var = tk.StringVar(value=datetime.now().date().strftime('%Y-%m-%d'))
        self.summary_total_var = tk.StringVar(value="Total Paid in Period: 0.00")
        self.create_widgets()
    def create_widgets(self):
        filter_frame = ttk.LabelFrame(self, text="Filter Contractor Payments", padding=10); filter_frame.pack(fill="x")
        ttk.Label(filter_frame, text="Contractor:").pack(side="left", padx=5); self.filter_contractor_combo = ttk.Combobox(filter_frame, textvariable=self.filter_contractor_var, state="readonly", width=30); self.filter_contractor_combo.pack(side="left", padx=5); self.filter_contractor_combo.bind("<<ComboboxSelected>>", self.refresh_payment_history)
        ttk.Label(filter_frame, text="From:").pack(side="left", padx=5); start_date_entry = ttk.Entry(filter_frame, textvariable=self.filter_start_date_var, width=12); start_date_entry.pack(side="left"); ttk.Button(filter_frame, text="📅", width=3, command=lambda: CalendarPopup(self, self.filter_start_date_var)).pack(side="left")
        ttk.Label(filter_frame, text="To:").pack(side="left", padx=5); end_date_entry = ttk.Entry(filter_frame, textvariable=self.filter_end_date_var, width=12); end_date_entry.pack(side="left"); ttk.Button(filter_frame, text="📅", width=3, command=lambda: CalendarPopup(self, self.filter_end_date_var)).pack(side="left")
        ttk.Button(filter_frame, text="Filter", command=self.refresh_payment_history).pack(side="left", padx=5)
        history_frame = ttk.LabelFrame(self, text="Payment History", padding=10); history_frame.pack(fill="both", expand=True, pady=10)
        ttk.Label(history_frame, textvariable=self.summary_total_var, font=("Arial", 12, "bold")).pack(anchor="e", pady=(0,5))
        columns = ("id", "date", "name", "section", "amount", "description"); self.tree = ttk.Treeview(history_frame, columns=columns, show="headings");
        for col in columns: self.tree.heading(col, text=col.title()); self.tree.column(col, width=120)
        self.tree.pack(fill="both", expand=True)
    def refresh_data(self): self.refresh_contractor_dropdown()
    def refresh_contractor_dropdown(self):
        records = self.db_controller.execute_query("SELECT id, name, section FROM contractors ORDER BY name", fetch="all"); self.contractor_map = {f"{name} ({section})": id for id, name, section in records}; names = list(self.contractor_map.keys())
        self.filter_contractor_combo['values'] = ["-- Show All --"] + names
        if not self.filter_contractor_var.get() in names: self.filter_contractor_var.set("-- Show All --")
        self.refresh_payment_history()
    def refresh_payment_history(self, event=None):
        for item in self.tree.get_children(): self.tree.delete(item)
        start_date = self.filter_start_date_var.get(); end_date = self.filter_end_date_var.get()
        query = "SELECT p.id, p.payment_date, c.name, c.section, p.amount, p.description FROM contractor_payments p JOIN contractors c ON p.contractor_id = c.id WHERE p.payment_date BETWEEN ? AND ?"
        params = [start_date, end_date]
        contractor_filter = self.filter_contractor_var.get()
        if contractor_filter and contractor_filter != "-- Show All --":
            query += " AND p.contractor_id = ?"
            params.append(self.contractor_map[contractor_filter])
        query += " ORDER BY p.payment_date DESC"; records = self.db_controller.execute_query(query, tuple(params), fetch="all")
        total_paid = 0
        if records:
            for row in records: self.tree.insert("", "end", values=row); total_paid += row[4]
        self.summary_total_var.set(f"Total Paid in Period: {total_paid:,.2f} BDT")

class ManagePersonnelFrame(ttk.Frame):
    def __init__(self, parent, db_controller):
        super().__init__(parent, padding=15); self.db_controller = db_controller
        self.staff_name_var = tk.StringVar(); self.salary_var = tk.DoubleVar(); self.contractor_name_var = tk.StringVar(); self.section_var = tk.StringVar(); self.phone_var = tk.StringVar()
        self.create_widgets()
    def create_widgets(self):
        container = ttk.Frame(self); container.pack(fill="both", expand=True); container.grid_columnconfigure(1, weight=1); container.grid_rowconfigure(1, weight=1)
        staff_form = ttk.LabelFrame(container, text="Manage Monthly Staff", padding=15); staff_form.grid(row=0, column=0, sticky="ew", padx=5, pady=(0,10)); ttk.Label(staff_form, text="Name:").grid(row=0, column=0); ttk.Entry(staff_form, textvariable=self.staff_name_var).grid(row=0, column=1, padx=5, pady=2, sticky="ew"); ttk.Label(staff_form, text="Salary:").grid(row=1, column=0); ttk.Entry(staff_form, textvariable=self.salary_var).grid(row=1, column=1, padx=5, pady=2, sticky="ew"); ttk.Button(staff_form, text="Add Staff", command=self.add_staff).grid(row=2, column=1, sticky="e", pady=5); staff_list = ttk.LabelFrame(container, text="Staff List", padding=10); staff_list.grid(row=1, column=0, sticky="nsew", padx=5, pady=10); self.staff_tree = self.create_personnel_tree(staff_list, ("id", "name", "salary"), ("ID", "Name", "Monthly Salary"), self.delete_staff, "Staff"); staff_form.grid_columnconfigure(1, weight=1)
        contractor_form = ttk.LabelFrame(container, text="Manage Contractors (Sardars)", padding=15); contractor_form.grid(row=0, column=1, sticky="ew", padx=5); ttk.Label(contractor_form, text="Name:").grid(row=0, column=0); ttk.Entry(contractor_form, textvariable=self.contractor_name_var).grid(row=0, column=1, padx=5, pady=2, sticky="ew"); ttk.Label(contractor_form, text="Section:").grid(row=1, column=0); ttk.Combobox(contractor_form, textvariable=self.section_var, state="readonly", values=["Mill Sardar", "Loader", "Unloader", "Burner", "Other"]).grid(row=1, column=1, padx=5, pady=2, sticky="ew"); ttk.Label(contractor_form, text="Phone:").grid(row=2, column=0); ttk.Entry(contractor_form, textvariable=self.phone_var).grid(row=2, column=1, padx=5, pady=2, sticky="ew"); ttk.Button(contractor_form, text="Add Contractor", command=self.add_contractor).grid(row=3, column=1, sticky="e", pady=5); contractor_list_frame = ttk.LabelFrame(container, text="Contractor List", padding=10); contractor_list_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=10); self.contractor_tree = self.create_personnel_tree(contractor_list_frame, ("id", "name", "section", "phone"), ("ID", "Name", "Section", "Phone"), self.delete_contractor, "Contractor"); contractor_form.grid_columnconfigure(1, weight=1)
    def create_personnel_tree(self, parent, columns, headings, delete_cmd, payee_type):
        parent.grid_rowconfigure(0, weight=1); parent.grid_columnconfigure(0, weight=1)
        tree = ttk.Treeview(parent, columns=columns, show="headings"); tree.grid(row=0, column=0, columnspan=2, sticky="nsew"); scrollbar = ttk.Scrollbar(parent, orient="vertical", command=tree.yview); tree.configure(yscrollcommand=scrollbar.set); scrollbar.grid(row=0, column=1, sticky="ns")
        btn_frame = ttk.Frame(parent); btn_frame.grid(row=1, column=0, columnspan=2, pady=5, sticky="e")
        ttk.Button(btn_frame, text="Record Payment", command=lambda: self.record_payment(payee_type)).pack(side="left", padx=5)
        if payee_type == "Staff": ttk.Button(btn_frame, text="Edit Salary", command=self.edit_staff).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Delete Selected", command=delete_cmd).pack(side="left")
        return tree
    def record_payment(self, payee_type):
        tree = self.staff_tree if payee_type == "Staff" else self.contractor_tree; item = tree.focus()
        if not item: messagebox.showwarning("Error", f"Please select a {payee_type.lower()} from the list.", parent=self); return
        item_id, name, *_ = tree.item(item, "values"); RecordPaymentWindow(self, self.db_controller, item_id, name, payee_type, self.refresh_data)
    def edit_staff(self):
        item = self.staff_tree.focus();
        if not item: messagebox.showwarning("Error", "Please select a staff member to edit.", parent=self); return
        item_id, name, salary = self.staff_tree.item(item, "values"); new_salary = simpledialog.askfloat("Edit Salary", f"Enter new monthly salary for {name}:", initialvalue=salary, parent=self)
        if new_salary is not None: self.db_controller.execute_query("UPDATE staff SET monthly_salary = ? WHERE id = ?", (new_salary, item_id)); self.refresh_data()
    def refresh_data(self): self.refresh_staff_list(); self.refresh_contractor_list()
    def refresh_staff_list(self):
        for i in self.staff_tree.get_children(): self.staff_tree.delete(i)
        for row in self.db_controller.execute_query("SELECT id, name, monthly_salary FROM staff ORDER BY name", fetch="all"): self.staff_tree.insert("", "end", values=row)
    def refresh_contractor_list(self):
        for i in self.contractor_tree.get_children(): self.contractor_tree.delete(i)
        for row in self.db_controller.execute_query("SELECT * FROM contractors ORDER BY section, name", fetch="all"): self.contractor_tree.insert("", "end", values=row)
    def add_staff(self):
        name = self.staff_name_var.get(); salary = self.salary_var.get()
        if not name or not salary > 0: messagebox.showerror("Error", "Name and a valid salary are required.", parent=self); return
        try: self.db_controller.execute_query("INSERT INTO staff (name, monthly_salary) VALUES (?, ?)", (name, salary)); self.refresh_staff_list(); self.staff_name_var.set(""); self.salary_var.set(0.0)
        except Exception as e: messagebox.showerror("Error", f"Could not add staff.\n{e}", parent=self)
    def add_contractor(self):
        name = self.contractor_name_var.get(); section = self.section_var.get(); phone = self.phone_var.get()
        if not name or not section: messagebox.showerror("Error", "Name and Section are required.", parent=self); return
        try: self.db_controller.execute_query("INSERT INTO contractors (name, section, phone) VALUES (?, ?, ?)", (name, section, phone)); self.refresh_contractor_list(); self.contractor_name_var.set(""); self.section_var.set(""); self.phone_var.set("")
        except Exception as e: messagebox.showerror("Error", f"Could not add contractor.\n{e}", parent=self)
    def delete_staff(self):
        item = self.staff_tree.focus();
        if not item: messagebox.showwarning("Error", "Please select a staff member to delete.", parent=self); return
        item_id, name, _ = self.staff_tree.item(item, "values")
        if messagebox.askyesno("Confirm", f"Are you sure you want to delete {name}? ALL their payment records will be permanently deleted!"):
            payment_ids = self.db_controller.execute_query("SELECT id FROM salary_payments WHERE staff_id = ?", (item_id,), fetch="all") or []
            for pid_tuple in payment_ids: self.db_controller.execute_query("DELETE FROM ledger_book WHERE description LIKE ?", (f"%[SALARY_PAYMENT_ID:{pid_tuple[0]}]%",))
            self.db_controller.execute_query("DELETE FROM staff WHERE id = ?", (item_id,)); self.refresh_data()
    def delete_contractor(self):
        item = self.contractor_tree.focus();
        if not item: messagebox.showwarning("Error", "Please select a contractor to delete.", parent=self); return
        item_id, name, section, _ = self.contractor_tree.item(item, "values")
        if messagebox.askyesno("Confirm", f"Are you sure you want to delete {name} ({section})? ALL their payment records will be deleted!"):
            payment_ids = self.db_controller.execute_query("SELECT id FROM contractor_payments WHERE contractor_id = ?", (item_id,), fetch="all") or []
            for pid_tuple in payment_ids: self.db_controller.execute_query("DELETE FROM ledger_book WHERE description LIKE ?", (f"%[CON_PAY_ID:{pid_tuple[0]}]%",))
            self.db_controller.execute_query("DELETE FROM contractors WHERE id = ?", (item_id,)); self.refresh_data()