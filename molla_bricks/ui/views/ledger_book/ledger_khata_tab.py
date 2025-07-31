import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, timedelta
import os, subprocess, sys, re
from molla_bricks.ui.custom_calendar import CalendarPopup
from molla_bricks.core.services.ledger_service import LedgerService

class EditLedgerWindow(tk.Toplevel):
    def __init__(self, parent, db_controller, item_id, callback):
        super().__init__(parent); self.transient(parent); self.title("Edit Ledger Entry"); self.db_controller = db_controller; self.item_id = item_id; self.callback = callback
        query = "SELECT date, party_name, description, credit, debit FROM ledger_book WHERE id = ?"; record = self.db_controller.execute_query(query, (self.item_id,), fetch="one")
        self.date_var = tk.StringVar(value=record[0]); self.party_name_var = tk.StringVar(value=record[1]); self.description_var = tk.StringVar(value=record[2]); self.credit_var = tk.DoubleVar(value=record[3]); self.debit_var = tk.DoubleVar(value=record[4])
        self.create_widgets(); self.grab_set(); self.wait_window()
    def create_widgets(self):
        form_frame = ttk.Frame(self, padding=20); form_frame.pack(expand=True, fill="both")
        fields = {"Date:": self.date_var, "Party Name:": self.party_name_var, "Description:": self.description_var, "Credit:": self.credit_var, "Debit:": self.debit_var}
        for i, (label, var) in enumerate(fields.items()): ttk.Label(form_frame, text=label).grid(row=i, column=0, sticky="w", pady=5, padx=5); ttk.Entry(form_frame, textvariable=var, width=40).grid(row=i, column=1, sticky="ew", pady=5, padx=5)
        ttk.Button(form_frame, text="Save Changes", command=self.save_changes).grid(row=len(fields), column=1, sticky="e", pady=10, padx=5)
    def save_changes(self):
        query = "UPDATE ledger_book SET date=?, party_name=?, description=?, credit=?, debit=? WHERE id = ?"; params = (self.date_var.get(), self.party_name_var.get(), self.description_var.get(), round(self.credit_var.get(), 2), round(self.debit_var.get(), 2), self.item_id)
        self.db_controller.execute_query(query, params); messagebox.showinfo("Success", "Entry updated successfully.", parent=self); self.callback(); self.destroy()

# Updated LedgerKhataTab Class
class LedgerKhataTab(ttk.Frame):
    def __init__(self, parent, db_controller):
        super().__init__(parent)
        self.db_controller = db_controller
        self.date_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        self.party_name_var = tk.StringVar()
        self.description_var = tk.StringVar()
        self.credit_var = tk.DoubleVar(value=0.0)
        self.debit_var = tk.DoubleVar(value=0.0)
        self.all_party_names = []
        
        today = datetime.now().date()
        # MODIFIED: filter_party_var is now initialized to "All Parties"
        self.filter_party_var = tk.StringVar(value="All Parties") 
        self.filter_start_date_var = tk.StringVar(value=(today - timedelta(days=365)).strftime('%Y-%m-%d')) # Default to one year
        self.filter_end_date_var = tk.StringVar(value=today.strftime('%Y-%m-%d'))

        self._current_credit = 0.0
        self._current_debit = 0.0
        self._current_balance = 0.0
        self._last_view_was_filtered_by_date = False # Renamed for clarity

        self.create_widgets()
        self.load_initial_data()
    
    # --- No changes needed in add_entry, auto_settle_dues, or the top part of create_widgets ---
    
    def add_entry(self):
        party_name = self.party_name_var.get()
        description = self.description_var.get()
        if not party_name:
            messagebox.showerror("Validation Error", "Party Name is required.")
            return
        try:
            credit = round(self.credit_var.get(), 2)
            debit = round(self.debit_var.get(), 2)
        except tk.TclError:
            messagebox.showerror("Input Error", "Credit and Debit must be valid numbers.")
            return
        if credit > 0 and debit > 0:
            messagebox.showwarning("Input Warning", "Please enter either a Credit or a Debit, not both.")
            return
        
        query = "INSERT INTO ledger_book (date, party_name, description, credit, debit) VALUES (?, ?, ?, ?, ?)"
        params = (self.date_var.get(), party_name, description, credit, debit)
        new_id = self.db_controller.execute_query(query, params)
        
        if new_id and credit > 0:
            if messagebox.askyesno("Settle Dues?", "Do you want to use this credit amount to automatically settle this party's oldest outstanding dues?"):
                self.auto_settle_dues(party_name, credit, new_id)
        
        messagebox.showinfo("Success", "Ledger entry added successfully!")
        self.clear_form()
        self.refresh_data() # Refresh after adding

    def auto_settle_dues(self, party_name, payment_amount, ledger_entry_id):
        customer_id_record = self.db_controller.execute_query("SELECT id FROM customers WHERE name = ?", (party_name,), fetch="one")
        if not customer_id_record:
            messagebox.showinfo("Info", "This party is not a registered customer, so automatic due settlement cannot be applied.", parent=self)
            return

        customer_id = customer_id_record[0]
        dues_query = "SELECT id, due_amount FROM nagad_khata WHERE customer_id = ? AND due_amount > 0.01 ORDER BY id ASC"
        due_records = self.db_controller.execute_query(dues_query, (customer_id,), fetch="all")
        
        if not due_records:
            messagebox.showinfo("Info", "No outstanding dues found for this customer.", parent=self)
            return
            
        payment_to_apply = payment_amount
        settled_chalans = []
        for chalan_id, chalan_due in due_records:
            if payment_to_apply <= 0: break
            payment_for_this_chalan = min(payment_to_apply, chalan_due)
            
            update_query = "UPDATE nagad_khata SET paid_amount = paid_amount + ?, due_amount = due_amount - ? WHERE id = ?"
            self.db_controller.execute_query(update_query, (payment_for_this_chalan, payment_for_this_chalan, chalan_id))
            
            payment_to_apply -= payment_for_this_chalan
            settled_chalans.append(f"Chalan ID {chalan_id} (Paid: {payment_for_this_chalan:,.2f})")
        
        if settled_chalans:
            settlement_desc = " | Auto-settled: " + ", ".join(settled_chalans)
            self.db_controller.execute_query("UPDATE ledger_book SET description = description || ? WHERE id = ?", (settlement_desc, ledger_entry_id))
            messagebox.showinfo("Settlement Complete", f"Successfully applied ৳{payment_amount - payment_to_apply:,.2f} to {len(settled_chalans)} due chalan(s).", parent=self)

    def create_widgets(self):
        # --- This part of the method is unchanged ---
        form_frame = ttk.LabelFrame(self, text="Add Ledger Entry", padding=15)
        form_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        history_frame = ttk.LabelFrame(self, text="Transaction History (Double-click to Edit)", padding=15)
        history_frame.grid(row=0, column=1, rowspan=2, padx=10, pady=10, sticky="nsew")
        summary_frame = ttk.LabelFrame(self, text="Ledger Summary", padding=15)
        summary_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.grid_columnconfigure(1, weight=1)
        
        ttk.Label(form_frame, text="Date:").grid(row=0, column=0, sticky="w", pady=3)
        date_entry_frame = ttk.Frame(form_frame)
        date_entry_frame.grid(row=0, column=1, sticky="ew", pady=3)
        date_entry = ttk.Entry(date_entry_frame, textvariable=self.date_var, width=22)
        date_entry.pack(side="left")
        ttk.Button(date_entry_frame, text="📅", width=3, command=lambda: CalendarPopup(self, self.date_var)).pack(side="left", padx=5)
        
        ttk.Label(form_frame, text="Party Name:").grid(row=1, column=0, sticky="w", pady=3)
        self.party_name_combo = ttk.Combobox(form_frame, textvariable=self.party_name_var, width=28)
        self.party_name_combo.grid(row=1, column=1, sticky="ew", pady=3)
        self.party_name_combo.bind('<KeyRelease>', self.update_autocomplete_list)
        
        ttk.Label(form_frame, text="Description:").grid(row=2, column=0, sticky="w", pady=3)
        desc_entry = ttk.Entry(form_frame, textvariable=self.description_var, width=30)
        desc_entry.grid(row=2, column=1, sticky="ew", pady=3)
        
        ttk.Label(form_frame, text="Credit (Joma):").grid(row=3, column=0, sticky="w", pady=3)
        credit_entry = ttk.Entry(form_frame, textvariable=self.credit_var, width=30)
        credit_entry.grid(row=3, column=1, sticky="ew", pady=3)
        
        ttk.Label(form_frame, text="Debit (Khoroch):").grid(row=4, column=0, sticky="w", pady=3)
        debit_entry = ttk.Entry(form_frame, textvariable=self.debit_var, width=30)
        debit_entry.grid(row=4, column=1, sticky="ew", pady=3)
        
        for widget in [date_entry, self.party_name_combo, desc_entry, credit_entry, debit_entry]:
            widget.bind("<Return>", lambda e: e.widget.tk_focusNext().focus())
        
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="Add Entry", command=self.add_entry).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Clear", command=self.clear_form).pack(side="left", padx=5)

        # --- Filter frame and below is unchanged until populate_tree_and_summary ---
        filter_frame = ttk.LabelFrame(history_frame, text="Filter View", padding=10)
        filter_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(filter_frame, text="Party:").pack(side="left", padx=5)
        self.party_filter_combo = ttk.Combobox(filter_frame, textvariable=self.filter_party_var, state="readonly")
        self.party_filter_combo.pack(side="left", padx=5, fill="x", expand=True)
        self.party_filter_combo.bind("<<ComboboxSelected>>", self.on_filter_or_party_select)
        
        ttk.Label(filter_frame, text="From:").pack(side="left", padx=5)
        start_date_entry = ttk.Entry(filter_frame, textvariable=self.filter_start_date_var, width=12)
        start_date_entry.pack(side="left")
        ttk.Button(filter_frame, text="📅", width=3, command=lambda: CalendarPopup(self, self.filter_start_date_var)).pack(side="left")
        
        ttk.Label(filter_frame, text="To:").pack(side="left", padx=5)
        end_date_entry = ttk.Entry(filter_frame, textvariable=self.filter_end_date_var, width=12)
        end_date_entry.pack(side="left")
        ttk.Button(filter_frame, text="📅", width=3, command=lambda: CalendarPopup(self, self.filter_end_date_var)).pack(side="left")
        
        ttk.Button(filter_frame, text="Filter by Date", command=self.on_filter_or_party_select).pack(side="left", padx=5)
        
        history_actions_frame = ttk.Frame(history_frame)
        history_actions_frame.pack(fill="x", pady=5)
        ttk.Button(history_actions_frame, text="🖨️ Print Statement", command=self.print_report).pack(side="left")
        ttk.Button(history_actions_frame, text="📄 Export to CSV", command=self.export_to_csv).pack(side="left", padx=5)
        ttk.Button(history_actions_frame, text="🗑️ Delete", command=self.delete_entry).pack(side="right")
        
        columns = ("id", "date", "party", "description", "credit", "debit")
        self.tree = ttk.Treeview(history_frame, columns=columns, show="headings", height=15)
        self.tree.heading("id", text="ID")
        self.tree.column("id", width=40)
        self.tree.heading("date", text="Date")
        self.tree.column("date", width=90)
        self.tree.heading("party", text="Party Name")
        self.tree.column("party", width=150)
        self.tree.heading("description", text="Description")
        self.tree.column("description", width=250)
        self.tree.heading("credit", text="Credit")
        self.tree.column("credit", width=90, anchor="e")
        self.tree.heading("debit", text="Debit")
        self.tree.column("debit", width=90, anchor="e")
        self.tree.bind("<Double-1>", self.on_double_click)
        
        scrollbar = ttk.Scrollbar(history_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.total_credit_var = tk.StringVar(value="Total Credit: 0.00")
        self.total_debit_var = tk.StringVar(value="Total Debit: 0.00")
        self.balance_var = tk.StringVar(value="Balance: 0.00")
        
        ttk.Label(summary_frame, textvariable=self.total_credit_var, font=("Arial", 12, "bold"), foreground="green").pack(anchor="w")
        ttk.Label(summary_frame, textvariable=self.total_debit_var, font=("Arial", 12, "bold"), foreground="red").pack(anchor="w")
        ttk.Label(summary_frame, textvariable=self.balance_var, font=("Arial", 14, "bold")).pack(anchor="w", pady=5)

    def on_filter_or_party_select(self, event=None):
        """Refreshes data based on filter settings."""
        self.refresh_data()

    def refresh_data(self, event=None):
        """Refreshes the data in the tree, respecting the current view state."""
        party_name_filter = self.filter_party_var.get()
        start_date = self.filter_start_date_var.get()
        end_date = self.filter_end_date_var.get()
        
        self.populate_tree_and_summary(party_name_filter, start_date, end_date)

    def populate_tree_and_summary(self, party_name, start_date, end_date):
        for item in self.tree.get_children():
            self.tree.delete(item)

        params = []
        # MODIFIED: Query logic now handles "All Parties" selection
        is_all_parties_view = (party_name == "All Parties")
        
        if is_all_parties_view:
            query = "SELECT id, date, party_name, description, credit, debit FROM ledger_book WHERE date BETWEEN ? AND ?"
            params.extend([start_date, end_date])
        else:
            # This is for a specific party
            query = "SELECT id, date, party_name, description, credit, debit FROM ledger_book WHERE party_name = ? AND date BETWEEN ? AND ?"
            params.extend([party_name, start_date, end_date])

        query += " ORDER BY date DESC, id DESC"
        
        records = self.db_controller.execute_query(query, tuple(params), fetch="all")

        opening_balance = 0.0
        # Opening balance only makes sense for a single party
        if not is_all_parties_view:
            ob_query = "SELECT SUM(credit) - SUM(debit) FROM ledger_book WHERE party_name = ? AND date < ?"
            opening_balance = self.db_controller.execute_query(ob_query, (party_name, start_date), fetch="one")[0] or 0.0

        total_credit = 0
        total_debit = 0
        if records:
            for row in records:
                self.tree.insert("", "end", values=row)
                total_credit += row[4]
                total_debit += row[5]
                
        self._current_credit = total_credit
        self._current_debit = total_debit
        self._current_balance = opening_balance + total_credit - total_debit
        self.update_summary_labels()

    def update_summary_labels(self):
        # MODIFIED: Summary labels now adapt to the view
        is_all_parties_view = (self.filter_party_var.get() == "All Parties")
        
        credit_text = f"Credit in Period: {self._current_credit:,.2f} BDT"
        debit_text = f"Debit in Period: {self._current_debit:,.2f} BDT"
        
        if is_all_parties_view:
            balance_text = f"Net Flow in Period: {self._current_credit - self._current_debit:,.2f} BDT"
        else:
            balance_text = f"Closing Balance: {self._current_balance:,.2f} BDT"
        
        self.total_credit_var.set(credit_text)
        self.total_debit_var.set(debit_text)
        self.balance_var.set(balance_text)

    def _move_to_next_widget(self, event):
        event.widget.tk_focusNext().focus()
        return "break"

    def open_calendar(self):
        CalendarPopup(self, self.date_var)

    def delete_entry(self, event=None):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select an entry to delete.")
            return
        
        item_id, _, party_name, description, credit, debit = self.tree.item(selected_items[0], 'values')
        
        settlement_match = re.search(r"\[PAID_FOR_CHALAN_ID:(\d+)\]", description)
        due_match = re.search(r"\[SALE_FROM_CHALAN_ID:(\d+)\]", description)
        
        if settlement_match:
            if not messagebox.askyesno("Confirm Reversal", "This is a due settlement payment linked to a Chalan. Reversing it will add the due amount back. Are you sure?"):
                return
            chalan_id_to_reverse = int(settlement_match.group(1))
            amount_to_reverse = float(credit)
            self.db_controller.execute_query("UPDATE nagad_khata SET paid_amount = paid_amount - ?, due_amount = due_amount + ? WHERE id = ?", (amount_to_reverse, amount_to_reverse, chalan_id_to_reverse))
        
        elif due_match:
            messagebox.showerror("Action Not Allowed", "This is an automatic entry from a sale. To remove it, please delete the original sale from the Nagad Khata tab.", parent=self)
            return
            
        elif not messagebox.askyesno("Confirm Delete", "Are you sure you want to permanently delete this ledger entry? This action cannot be undone."):
            return
            
        self.db_controller.execute_query("DELETE FROM ledger_book WHERE id = ?", (item_id,))
        self.refresh_data()

    def print_report(self):
        party_name = self.filter_party_var.get()
        if party_name == "All Parties":
            messagebox.showwarning("Selection Required", "Please select a specific Party to generate a statement.", parent=self)
            return

        start_date = self.filter_start_date_var.get()
        end_date = self.filter_end_date_var.get()
        ob_query = "SELECT SUM(credit) - SUM(debit) FROM ledger_book WHERE party_name = ? AND date < ?"
        opening_balance = self.db_controller.execute_query(ob_query, (party_name, start_date), fetch="one")[0] or 0.0
        
        trans_query = "SELECT date, description, credit, debit FROM ledger_book WHERE party_name = ? AND date BETWEEN ? AND ? ORDER BY date ASC, id ASC"
        transactions = self.db_controller.execute_query(trans_query, (party_name, start_date, end_date), fetch="all")
        
        try:
            pdf_path = LedgerService.generate_ledger_pdf(party_name, start_date, end_date, opening_balance, transactions)
            if messagebox.askyesno("Success", f"PDF statement created:\n{os.path.abspath(pdf_path)}\n\nDo you want to open it?"):
                if sys.platform == "win32":
                    os.startfile(os.path.abspath(pdf_path))
                else:
                    subprocess.call(["open", os.path.abspath(pdf_path)])
        except Exception as e:
            messagebox.showerror("PDF Error", f"Failed to generate PDF: {e}", parent=self)

    def update_autocomplete_list(self, event):
        current_text = self.party_name_var.get().lower()
        if not current_text:
            self.party_name_combo['values'] = self.all_party_names
        else:
            self.party_name_combo['values'] = [name for name in self.all_party_names if current_text in name.lower()]
    
    def clear_form(self):
        self.party_name_var.set("")
        self.description_var.set("")
        self.credit_var.set(0.0)
        self.debit_var.set(0.0)
    
    def fetch_all_party_names(self):
        ledger_parties = self.db_controller.execute_query("SELECT DISTINCT party_name FROM ledger_book WHERE party_name IS NOT NULL AND party_name != ''", fetch="all")
        customer_parties = self.db_controller.execute_query("SELECT name FROM customers WHERE name IS NOT NULL AND name != ''", fetch="all")
        
        party_set = set()
        if ledger_parties:
            for p in ledger_parties: party_set.add(p[0])
        if customer_parties:
            for p in customer_parties: party_set.add(p[0])
        
        sorted_parties = sorted(list(party_set))
        self.all_party_names = sorted_parties
        
        # MODIFIED: Add "All Parties" to the list for filtering
        filter_list = ["All Parties"] + sorted_parties
        self.party_filter_combo['values'] = filter_list
        self.party_name_combo['values'] = sorted_parties # This one doesn't need "All Parties"
        
        # Set default selection if not already set
        if not self.filter_party_var.get():
             self.filter_party_var.set("All Parties")
    
    def load_initial_data(self):
        self.fetch_all_party_names()
        self.refresh_data()
    
    def on_double_click(self, event):
        selected_item = self.tree.focus()
        if not selected_item:
            return
        item_id = self.tree.item(selected_item, "values")[0]
        EditLedgerWindow(self, self.db_controller, item_id, self.refresh_data)
    
    def export_to_csv(self):
        try:
            path, msg = LedgerService.export_to_csv(self.db_controller)
            if path:
                messagebox.showinfo("Success", f"{msg}\nExport saved to: {os.path.abspath(path)}")
            else:
                messagebox.showwarning("Export Failed", msg)
        except Exception as e:
            messagebox.showerror("Export Error", f"An error occurred: {e}")