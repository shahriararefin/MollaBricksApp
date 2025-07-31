# molla_bricks/ui/views/nagad_khata/nagad_khata_tab.py
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import os, subprocess, sys, re
from molla_bricks.ui.custom_calendar import CalendarPopup
from molla_bricks.core.services.nagad_service import NagadService
from .customer_selection_window import CustomerSelectionWindow

# The EditNagadWindow class is unchanged and correct.
class EditNagadWindow(tk.Toplevel):
    def __init__(self, parent, db_controller, item_id, callback):
        super().__init__(parent); self.transient(parent); self.title("Edit Nagad Entry"); self.db_controller = db_controller; self.item_id = item_id; self.callback = callback
        query = "SELECT date, chalan_no, customer_id, customer_name, address, vehicle_no, brick_type, total_amount, paid_amount, brick_amount FROM nagad_khata WHERE id = ?"
        record = self.db_controller.execute_query(query, (self.item_id,), fetch="one")
        self.selected_customer_id = record[2]; self.date_var = tk.StringVar(value=record[0]); self.chalan_no_var = tk.StringVar(value=record[1]); self.customer_name_var = tk.StringVar(value=record[3]); self.address_var = tk.StringVar(value=record[4]); self.vehicle_no_var = tk.StringVar(value=record[5]); self.brick_type_var = tk.StringVar(value=record[6]); self.total_amount_var = tk.DoubleVar(value=record[7]); self.paid_amount_var = tk.DoubleVar(value=record[8]); self.brick_amount_var = tk.IntVar(value=record[9] or 0)
        self.create_widgets(); self.grab_set(); self.wait_window()
    def create_widgets(self):
        form_frame = ttk.Frame(self, padding=20); form_frame.pack(expand=True, fill="both")
        brick_types = [row[0] for row in self.db_controller.execute_query("SELECT name FROM brick_types ORDER BY name", fetch="all")]
        row = 0; ttk.Label(form_frame, text="Customer:").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        customer_display = f"{self.customer_name_var.get()} (ID: {self.selected_customer_id or 'N/A'})"
        ttk.Label(form_frame, text=customer_display, font=("Arial", 10, "bold")).grid(row=row, column=1, sticky="w", pady=5, padx=5); row += 1
        fields = {"Date:": self.date_var, "Chalan No:": self.chalan_no_var, "Address:": self.address_var, "Vehicle No:": self.vehicle_no_var, "Brick Amount:": self.brick_amount_var, "Brick Type:": self.brick_type_var, "Total Amount:": self.total_amount_var, "Paid Amount:": self.paid_amount_var}
        for label, var in fields.items():
            ttk.Label(form_frame, text=label).grid(row=row, column=0, sticky="w", pady=5, padx=5)
            if label == "Brick Type:": ttk.Combobox(form_frame, textvariable=var, values=brick_types).grid(row=row, column=1, sticky="ew", pady=5, padx=5)
            else: ttk.Entry(form_frame, textvariable=var, width=40).grid(row=row, column=1, sticky="ew", pady=5, padx=5)
            row += 1
        ttk.Button(form_frame, text="Save Changes", command=self.save_changes).grid(row=row, column=1, sticky="e", pady=10, padx=5)
    def save_changes(self):
        messagebox.showinfo("Info", "Editing a sale does not automatically update the ledger. Please make necessary adjustments in the Ledger Book manually.", parent=self)
        try: total = self.total_amount_var.get(); paid = self.paid_amount_var.get(); due = round(total - paid, 2)
        except (tk.TclError, ValueError): messagebox.showerror("Input Error", "Amounts must be valid numbers.", parent=self); return
        query = "UPDATE nagad_khata SET date=?, chalan_no=?, address=?, vehicle_no=?, brick_type=?, total_amount=?, paid_amount=?, due_amount=?, brick_amount=?, rate=? WHERE id = ?"
        params = (self.date_var.get(), self.chalan_no_var.get(), self.address_var.get(), self.vehicle_no_var.get(), self.brick_type_var.get(), total, paid, due, self.brick_amount_var.get(), total, self.item_id)
        self.db_controller.execute_query(query, params); messagebox.showinfo("Success", "Entry updated successfully.", parent=self); self.callback(); self.destroy()

class NagadKhataTab(ttk.Frame):
    def __init__(self, parent, db_controller, baki_khata_refresh_callback=None):
        super().__init__(parent)
        self.db_controller = db_controller
        self.baki_khata_refresh_callback = baki_khata_refresh_callback
        self.selected_customer_id = None
        
        # --- Form Variables ---
        self.date_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        self.chalan_no_var = tk.StringVar()
        self.customer_name_var = tk.StringVar()
        self.address_var = tk.StringVar()
        self.vehicle_no_var = tk.StringVar()
        self.brick_type_var = tk.StringVar()
        self.total_amount_var = tk.DoubleVar()
        self.paid_amount_var = tk.DoubleVar()
        self.brick_amount_var = tk.IntVar()
        self.customer_balance_var = tk.StringVar(value="Select a customer")
        self.customer_type_var = tk.StringVar(value="registered")
        
        # --- Filter Variables ---
        self.filter_by_customer_id = None
        self.filter_by_customer_name_var = tk.StringVar(value="Showing all transactions.")

        # --- Internal State ---
        self.chalan_reset_marker_id = 0
        self.all_customer_names = []
        self.all_addresses = []
        self.all_vehicles = []
        self.all_brick_amounts = []
        self.all_total_amounts = []
        self.suggestion_active = {}
        
        self.create_widgets()
        self.load_initial_data()

    def _setup_autocomplete(self, widget, tk_var, data_list_provider, var_name):
        self.suggestion_active[var_name] = False; widget.bind("<KeyRelease>", lambda e, w=widget, p=data_list_provider, v=var_name: self._on_keyrelease_autocomplete(e, w, p, v)); widget.bind("<Tab>", lambda e, w=widget, t=tk_var, v=var_name: self._on_tab_press(e, w, t, v))

    def _on_keyrelease_autocomplete(self, event, widget, data_list_provider, var_name):
        if event.keysym in ("BackSpace", "Tab", "Return", "Shift_L", "Shift_R", "Control_L", "Control_R", "Up", "Down", "Left", "Right", "Home", "End"): self.suggestion_active[var_name] = False; return
        current_text = widget.get();
        if not current_text: self.suggestion_active[var_name] = False; return
        data_list = getattr(self, data_list_provider)
        match = next((s for s in data_list if str(s).lower().startswith(current_text.lower())), None)
        if match and str(match).lower() != current_text.lower():
            self.suggestion_active[var_name] = True; end_pos = widget.index(tk.INSERT); widget.delete(end_pos, tk.END); widget.insert(end_pos, str(match)[len(current_text):]); widget.icursor(end_pos); widget.selection_range(end_pos, tk.END)
        else: self.suggestion_active[var_name] = False

    def _on_tab_press(self, event, widget, tk_var, var_name):
        if self.suggestion_active[var_name]:
            full_text = widget.get(); tk_var.set(full_text); widget.icursor(tk.END); widget.selection_clear(); self.suggestion_active[var_name] = False; return "break"
        else: widget.tk_focusNext().focus(); return "break"
        
    def create_widgets(self):
        # --- Main Layout ---
        form_frame = ttk.LabelFrame(self, text="Add New Sale", padding=15); form_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        history_frame = ttk.LabelFrame(self, text="Sales History (Double-click to Edit)", padding=15); history_frame.grid(row=0, column=1, rowspan=2, padx=10, pady=10, sticky="nsew")
        summary_frame = ttk.LabelFrame(self, text="Overall Summary", padding=15); summary_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- New Sale Form ---
        customer_type_frame = ttk.Frame(form_frame); customer_type_frame.grid(row=0, column=0, columnspan=2, sticky="w", pady=5); ttk.Radiobutton(customer_type_frame, text="Registered Customer", variable=self.customer_type_var, value="registered", command=self.toggle_customer_type).pack(side="left"); ttk.Radiobutton(customer_type_frame, text="One-Time Customer", variable=self.customer_type_var, value="onetime", command=self.toggle_customer_type).pack(side="left", padx=10)
        
        self.reg_customer_frame = ttk.Frame(form_frame); self.onetime_customer_frame = ttk.Frame(form_frame)
        ttk.Button(self.reg_customer_frame, text="👤 Select Customer...", command=self.select_customer).pack(side="left", padx=5); self.customer_name_label = ttk.Label(self.reg_customer_frame, text="-- No Customer Selected --", font=("Arial", 12, "bold")); self.customer_name_label.pack(side="left", padx=10); self.balance_label = ttk.Label(self.reg_customer_frame, textvariable=self.customer_balance_var, font=("Arial", 9, "italic")); self.balance_label.pack(side="right", padx=10)
        
        ttk.Label(self.onetime_customer_frame, text="Customer Name:").grid(row=0, column=0, sticky="w"); self.onetime_name_entry = ttk.Entry(self.onetime_customer_frame, textvariable=self.customer_name_var, width=30); self.onetime_name_entry.grid(row=0, column=1, sticky="ew"); ttk.Label(self.onetime_customer_frame, text="Address:").grid(row=1, column=0, sticky="w", pady=(5,0)); self.onetime_address_entry = ttk.Entry(self.onetime_customer_frame, textvariable=self.address_var, width=30); self.onetime_address_entry.grid(row=1, column=1, sticky="ew", pady=(5,0))
        
        fields_frame = ttk.Frame(form_frame); fields_frame.grid(row=2, column=0, columnspan=2, pady=5); form_fields = []
        row=0
        ttk.Label(fields_frame, text="Date:").grid(row=row, column=0, sticky="w"); date_entry = ttk.Entry(fields_frame, textvariable=self.date_var); date_entry.grid(row=row, column=1, pady=2); form_fields.append(date_entry); row+=1
        ttk.Label(fields_frame, text="Chalan No:").grid(row=row, column=0, sticky="w"); chalan_entry = ttk.Entry(fields_frame, textvariable=self.chalan_no_var); chalan_entry.grid(row=row, column=1, pady=2); form_fields.append(chalan_entry); row+=1
        ttk.Label(fields_frame, text="Vehicle No:").grid(row=row, column=0, sticky="w"); vehicle_entry = ttk.Entry(fields_frame, textvariable=self.vehicle_no_var); vehicle_entry.grid(row=row, column=1, pady=2); form_fields.append(vehicle_entry); row+=1
        ttk.Label(fields_frame, text="Brick Amount:").grid(row=row, column=0, sticky="w"); amount_entry = ttk.Entry(fields_frame, textvariable=self.brick_amount_var); amount_entry.grid(row=row, column=1, pady=2); form_fields.append(amount_entry); row+=1
        ttk.Label(fields_frame, text="Brick Type:").grid(row=row, column=0, sticky="w"); self.brick_type_combo = ttk.Combobox(fields_frame, textvariable=self.brick_type_var, state="readonly"); self.brick_type_combo.grid(row=row, column=1, pady=2, sticky="ew"); form_fields.append(self.brick_type_combo); row+=1
        ttk.Label(fields_frame, text="Total Amount:").grid(row=row, column=0, sticky="w"); total_amount_entry = ttk.Entry(fields_frame, textvariable=self.total_amount_var); total_amount_entry.grid(row=row, column=1, pady=2); form_fields.append(total_amount_entry); row+=1
        ttk.Label(fields_frame, text="Paid Amount:").grid(row=row, column=0, sticky="w"); paid_entry = ttk.Entry(fields_frame, textvariable=self.paid_amount_var); paid_entry.grid(row=row, column=1, pady=2); form_fields.append(paid_entry); row+=1
        
        self._setup_autocomplete(self.onetime_name_entry, self.customer_name_var, 'all_customer_names', 'onetime_customer'); self._setup_autocomplete(self.onetime_address_entry, self.address_var, 'all_addresses', 'onetime_address'); self._setup_autocomplete(vehicle_entry, self.vehicle_no_var, 'all_vehicles', 'vehicle'); self._setup_autocomplete(amount_entry, self.brick_amount_var, 'all_brick_amounts', 'brick_amount'); self._setup_autocomplete(total_amount_entry, self.total_amount_var, 'all_total_amounts', 'total_amount')
        for widget in form_fields: widget.bind("<Return>", lambda e: e.widget.tk_focusNext().focus())
        
        button_frame = ttk.Frame(fields_frame); button_frame.grid(row=row, column=1, sticky="e", pady=10); ttk.Button(button_frame, text="Add Entry", command=self.add_entry).pack(side="left"); ttk.Button(button_frame, text="Clear Form", command=self.clear_form).pack(side="left", padx=5)

        # --- History Frame Widgets ---
        history_frame.rowconfigure(2, weight=1)
        history_frame.columnconfigure(0, weight=1)

        # --- NEW: Filter Frame ---
        filter_frame = ttk.Frame(history_frame); filter_frame.grid(row=0, column=0, sticky='ew', pady=(0, 5))
        ttk.Button(filter_frame, text="Filter by Customer...", command=self.select_filter_customer).pack(side="left")
        ttk.Label(filter_frame, textvariable=self.filter_by_customer_name_var, font=("Arial", 9, "italic")).pack(side="left", padx=10)
        ttk.Button(filter_frame, text="Show All", command=self.clear_filter).pack(side="left")

        history_button_frame = ttk.Frame(history_frame); history_button_frame.grid(row=1, column=0, sticky='ew', pady=5)
        ttk.Button(history_button_frame, text="🖨️ Print Chalan", command=self.print_chalan).pack(side="left"); ttk.Button(history_button_frame, text="📄 Export to CSV", command=self.export_to_csv).pack(side="left", padx=10); ttk.Button(history_button_frame, text="🗑️ Delete Selected", command=self.delete_entry).pack(side="right")
        
        # --- Treeview with Scrollbars ---
        tree_container = ttk.Frame(history_frame)
        tree_container.grid(row=2, column=0, sticky='nsew')
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        columns = ("id", "date", "chalan_no", "customer_name", "address", "vehicle_no", "brick_amount", "total_amount", "paid_amount", "due_amount")
        self.tree = ttk.Treeview(tree_container, columns=columns, show="headings", height=15)
        self.tree.bind("<Double-1>", self.on_double_click)
        
        v_scroll = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        h_scroll = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        for col in columns: self.tree.heading(col, text=col.replace("_", " ").title()); self.tree.column(col, width=120, anchor="center")
        self.tree.column("id", width=40, anchor="center"); self.tree.column("customer_name", width=180, anchor="w"); self.tree.column("address", width=200, anchor="w")
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        # --- Summary Frame ---
        self.total_sales_var = tk.StringVar(value="Total Sales: 0.00"); self.total_paid_var = tk.StringVar(value="Total Paid: 0.00"); self.total_due_var = tk.StringVar(value="Total Due: 0.00"); ttk.Label(summary_frame, textvariable=self.total_sales_var, font=("Arial", 12, "bold")).pack(anchor="w"); ttk.Label(summary_frame, textvariable=self.total_paid_var, font=("Arial", 12, "bold")).pack(anchor="w"); ttk.Label(summary_frame, textvariable=self.total_due_var, font=("Arial", 12, "bold"), foreground="red").pack(anchor="w")
        
        self.toggle_customer_type()

    def add_entry(self):
        chalan_no = self.chalan_no_var.get()
        if not chalan_no: messagebox.showerror("Validation Error", "Chalan Number is required."); return
        
        # <<-- NEW: Duplicate Chalan Check -->>
        check_query = "SELECT id FROM nagad_khata WHERE chalan_no = ? AND id > ?"
        exists = self.db_controller.execute_query(check_query, (chalan_no, self.chalan_reset_marker_id), fetch="one")
        if exists:
            if not messagebox.askyesno("Confirm Duplicate", f"Chalan No '{chalan_no}' already exists. Are you sure you want to continue?"):
                return
        
        is_registered = self.customer_type_var.get() == "registered"
        if is_registered and not self.selected_customer_id: messagebox.showerror("Error", "Please select a registered customer."); return
        if not is_registered and not self.customer_name_var.get(): messagebox.showerror("Error", "Please enter a name for the one-time customer."); return
        if not self.total_amount_var.get() > 0: messagebox.showerror("Validation Error", "Total Amount must be greater than zero."); return
        try: total_amount = round(self.total_amount_var.get(), 2); paid_amount = round(self.paid_amount_var.get(), 2); due_amount = round(total_amount - paid_amount, 2)
        except tk.TclError: messagebox.showerror("Input Error", "Amounts must be valid numbers."); return
        customer_id = self.selected_customer_id if is_registered else None; customer_name = self.customer_name_var.get(); address = self.address_var.get(); entry_date = self.date_var.get()
        nagad_query = "INSERT INTO nagad_khata (customer_id, date, chalan_no, customer_name, address, vehicle_no, brick_type, total_amount, paid_amount, due_amount, brick_amount, rate) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        params = (customer_id, entry_date, chalan_no, customer_name, address, self.vehicle_no_var.get(), self.brick_type_var.get(), total_amount, paid_amount, due_amount, self.brick_amount_var.get() or 0, total_amount)
        new_id = self.db_controller.execute_query(nagad_query, params)
        if new_id:
            self.db_controller.execute_query("INSERT INTO ledger_book (date, party_name, description, debit, credit) VALUES (?, ?, ?, ?, ?)", (entry_date, customer_name, f"Sale via Chalan: {chalan_no} [SALE_FROM_CHALAN_ID:{new_id}]", total_amount, 0))
            if paid_amount > 0: self.db_controller.execute_query("INSERT INTO ledger_book (date, party_name, description, credit, debit) VALUES (?, ?, ?, ?, ?)", (entry_date, customer_name, f"Payment for Chalan: {chalan_no} [PAID_FOR_CHALAN_ID:{new_id}]", paid_amount, 0))
            if is_registered and due_amount > 0: self.auto_settle_from_advance(customer_id, customer_name)
            messagebox.showinfo("Success", "Sale recorded and ledger updated correctly."); self.clear_form()
            if due_amount > 0 and self.baki_khata_refresh_callback: self.baki_khata_refresh_callback()
            
            
    def auto_settle_from_advance(self, customer_id, customer_name):
        balance_query = "SELECT SUM(credit) - SUM(debit) FROM ledger_book WHERE party_name = ?"; balance = self.db_controller.execute_query(balance_query, (customer_name,), fetch="one")[0] or 0.0
        if balance > 0:
            dues_query = "SELECT id, due_amount FROM nagad_khata WHERE customer_id = ? AND due_amount > 0.01 ORDER BY id ASC"; due_records = self.db_controller.execute_query(dues_query, (customer_id,), fetch="all")
            if not due_records: return
            payment_to_apply = balance
            for chalan_id, chalan_due in due_records:
                if payment_to_apply <= 0: break
                payment_for_this_chalan = min(payment_to_apply, chalan_due); self.db_controller.execute_query("UPDATE nagad_khata SET paid_amount = paid_amount + ?, due_amount = due_amount - ? WHERE id = ?", (payment_for_this_chalan, payment_for_this_chalan, chalan_id))
                desc = f"Advance applied to Chalan ID: {chalan_id} [AUTO_SETTLED_ID:{chalan_id}]"; self.db_controller.execute_query("INSERT INTO ledger_book (date, party_name, description, debit, credit) VALUES (?, ?, ?, ?, ?)", (datetime.now().strftime('%Y-%m-%d'), customer_name, desc, payment_for_this_chalan, 0)); payment_to_apply -= payment_for_this_chalan

    def export_to_csv(self):
        try:
            path, msg = NagadService.export_to_csv(self.db_controller, customer_id=self.filter_by_customer_id)
            if path: messagebox.showinfo("Success", f"{msg}\nExport saved to: {os.path.abspath(path)}")
            else: messagebox.showwarning("Export Failed", msg)
        except Exception as e: messagebox.showerror("Export Error", f"An error occurred: {e}")

    def toggle_customer_type(self):
        if self.customer_type_var.get() == "registered": self.onetime_customer_frame.grid_forget(); self.reg_customer_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
        else: self.reg_customer_frame.grid_forget(); self.onetime_customer_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5); self.clear_selection()

    def select_customer(self):
        selection_window = CustomerSelectionWindow(self)
        if selection_window.selected_customer: self.selected_customer_id, name, address, _ = selection_window.selected_customer; self.customer_name_var.set(name); self.address_var.set(address); self.customer_name_label.config(text=name); self.update_customer_balance()

    def clear_selection(self): self.selected_customer_id = None; self.customer_name_var.set("-- No Customer Selected --"); self.address_var.set(""); self.customer_name_label.config(text="-- No Customer Selected --"); self.customer_balance_var.set("Balance: N/A"); self.balance_label.config(foreground="black")
    
    def clear_form(self): 
        self.clear_selection()
        self.vehicle_no_var.set("")
        self.brick_amount_var.set(0)
        self.total_amount_var.set(0.0)
        self.paid_amount_var.set(0.0)
        self.customer_name_var.set("")
        self.address_var.set("")
        self.refresh_data()

    def update_customer_balance(self):
        if not self.selected_customer_id: self.customer_balance_var.set("Balance: N/A"); return
        query = "SELECT SUM(credit) - SUM(debit) FROM ledger_book WHERE party_name = ?"; result = self.db_controller.execute_query(query, (self.customer_name_var.get(),), fetch="one"); balance = result[0] or 0.0
        color = "green" if balance >= 0 else "red"; self.balance_label.config(foreground=color); self.customer_balance_var.set(f"Balance: {balance:,.2f}")

    def refresh_data(self):
        self.chalan_reset_marker_id = int(self.db_controller.get_setting('chalan_reset_marker_id', 0))
        for item in self.tree.get_children(): self.tree.delete(item)
        
        query = "SELECT id, date, chalan_no, customer_name, address, vehicle_no, brick_amount, total_amount, paid_amount, due_amount FROM nagad_khata"
        params = []
        if self.filter_by_customer_id:
            query += " WHERE customer_id = ?"
            params.append(self.filter_by_customer_id)
        query += " ORDER BY id DESC"
        
        records = self.db_controller.execute_query(query, params, fetch="all")
        if records:
            for row in records: self.tree.insert("", "end", values=row)
            
        self.update_summary()
        self.fetch_all_autocomplete_data()
        self.fetch_and_update_brick_types()
        self.chalan_no_var.set(self._get_next_chalan_no())

    def _get_next_chalan_no(self):
        query = "SELECT MAX(CAST(chalan_no AS INTEGER)) FROM nagad_khata WHERE chalan_no GLOB '[0-9]*' AND id > ?"; result = self.db_controller.execute_query(query, (self.chalan_reset_marker_id,), fetch="one")
        if result and result[0] is not None: return str(result[0] + 1)
        return "1"

    def on_double_click(self, event):
        selected_item = self.tree.focus();
        if not selected_item: return
        item_id = self.tree.item(selected_item, "values")[0]; EditNagadWindow(self, self.db_controller, item_id, self.refresh_data)

    def delete_entry(self):
        selected_items = self.tree.selection()
        if not selected_items: messagebox.showwarning("No Selection", "Please select an entry to delete."); return
        if messagebox.askyesno("Confirm Delete", "This will also delete linked ledger entries... Are you sure?"):
            selected_item = selected_items[0]; record_id = self.tree.item(selected_item, 'values')[0]
            self.db_controller.execute_query("DELETE FROM ledger_book WHERE description LIKE ?", (f"%CHALAN_ID:{record_id}%",)); self.db_controller.execute_query("DELETE FROM nagad_khata WHERE id = ?", (record_id,)); self.refresh_data(); messagebox.showinfo("Success", "Entry and linked ledger records deleted.")

    def print_chalan(self, *args):
        selected_items = self.tree.selection()
        if not selected_items: messagebox.showwarning("No Selection", "Please select an entry to print."); return
        selected_item = selected_items[0]; record_id = self.tree.item(selected_item, 'values')[0]
        query = "SELECT * FROM nagad_khata WHERE id = ?"; record = self.db_controller.execute_query(query, (record_id,), fetch="one")
        if not record: messagebox.showerror("Error", "Could not find the selected record."); return
        columns = ["id", "customer_id", "date", "chalan_no", "customer_name", "address", "vehicle_no", "brick_type", "brick_amount", "rate", "total_amount", "paid_amount", "due_amount", "timestamp"]; chalan_data = dict(zip(columns, record))
        try:
            pdf_path = NagadService.generate_chalan_pdf(chalan_data)
            if messagebox.askyesno("Success", f"PDF chalan created at:\n{os.path.abspath(pdf_path)}\n\nDo you want to open it?"):
                if sys.platform == "win32": os.startfile(os.path.abspath(pdf_path))
                else: subprocess.call(["open", os.path.abspath(pdf_path)])
        except Exception as e: messagebox.showerror("PDF Error", f"Failed to generate PDF: {e}")

    def update_summary(self):
        query = "SELECT SUM(total_amount), SUM(paid_amount), SUM(due_amount) FROM nagad_khata"
        params = ()
        if self.filter_by_customer_id:
            query += " WHERE customer_id = ?"
            params = (self.filter_by_customer_id,)
        
        result = self.db_controller.execute_query(query, params, fetch="one")
        if result: 
            total_sales, total_paid, total_due = result
            self.total_sales_var.set(f"Total Sales: {total_sales or 0:,.2f} BDT")
            self.total_paid_var.set(f"Total Paid: {total_paid or 0:,.2f} BDT")
            self.total_due_var.set(f"Total Due: {total_due or 0:,.2f} BDT")

    def fetch_and_update_brick_types(self):
        query = "SELECT name FROM brick_types ORDER BY name"; records = self.db_controller.execute_query(query, fetch="all")
        if records:
            type_names = [row[0] for row in records]; self.brick_type_combo['values'] = type_names
            if type_names: self.brick_type_var.set(type_names[0])

    def fetch_all_autocomplete_data(self):
        self.all_customer_names = sorted(list(set([r[0] for r in self.db_controller.execute_query("SELECT DISTINCT customer_name FROM nagad_khata WHERE customer_name IS NOT NULL AND customer_name != ''", fetch="all")])))
        self.all_addresses = sorted(list(set([r[0] for r in self.db_controller.execute_query("SELECT DISTINCT address FROM nagad_khata WHERE address IS NOT NULL AND address != ''", fetch="all")])))
        self.all_vehicles = sorted(list(set([r[0] for r in self.db_controller.execute_query("SELECT DISTINCT vehicle_no FROM nagad_khata WHERE vehicle_no IS NOT NULL AND vehicle_no != ''", fetch="all")])))
        self.all_brick_amounts = sorted(list(set([r[0] for r in self.db_controller.execute_query("SELECT DISTINCT brick_amount FROM nagad_khata WHERE brick_amount > 0", fetch="all")])), reverse=True)
        self.all_total_amounts = sorted(list(set([r[0] for r in self.db_controller.execute_query("SELECT DISTINCT total_amount FROM nagad_khata WHERE total_amount > 0", fetch="all")])), reverse=True)

    def load_initial_data(self): self.refresh_data()

    # --- New Filter Methods ---
    def select_filter_customer(self):
        """Opens the customer selection window to choose a customer for filtering."""
        selection_window = CustomerSelectionWindow(self)
        if selection_window.selected_customer:
            cust_id, name, _, _ = selection_window.selected_customer
            self.filter_by_customer_id = cust_id
            self.filter_by_customer_name_var.set(f"Showing transactions for: {name}")
            self.refresh_data()

    def clear_filter(self):
        """Clears the customer filter and shows all transactions."""
        self.filter_by_customer_id = None
        self.filter_by_customer_name_var.set("Showing all transactions.")
        self.refresh_data()
