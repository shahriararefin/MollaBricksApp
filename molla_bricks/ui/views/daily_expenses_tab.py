# molla_bricks/ui/views/daily_expenses_tab.py
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from ...core.services.ai_service import AIService

# The EditExpenseWindow class is unchanged
class EditExpenseWindow(tk.Toplevel):
    def __init__(self, parent, db_controller, item_id, callback):
        super().__init__(parent); self.transient(parent); self.title("Edit Expense Entry"); self.db_controller = db_controller; self.item_id = item_id; self.callback = callback
        record = self.db_controller.execute_query("SELECT expense_date, category, description, amount FROM daily_expenses WHERE id = ?", (self.item_id,), fetch="one")
        self.date_var = tk.StringVar(value=record[0]); self.category_var = tk.StringVar(value=record[1]); self.description_var = tk.StringVar(value=record[2]); self.amount_var = tk.DoubleVar(value=record[3])
        self.create_widgets(); self.grab_set(); self.wait_window()
    def create_widgets(self):
        form_frame = ttk.Frame(self, padding=20); form_frame.pack(expand=True, fill="both")
        categories = [r[0] for r in self.db_controller.execute_query("SELECT name FROM expense_categories ORDER BY name", fetch="all")]
        fields = {"Date:": self.date_var, "Category:": self.category_var, "Description:": self.description_var, "Amount:": self.amount_var}
        for i, (label, var) in enumerate(fields.items()):
            ttk.Label(form_frame, text=label).grid(row=i, column=0, sticky="w", pady=5, padx=5)
            if label == "Category:": ttk.Combobox(form_frame, textvariable=var, values=categories, state="readonly").grid(row=i, column=1, sticky="ew", pady=5, padx=5)
            else: ttk.Entry(form_frame, textvariable=var, width=40).grid(row=i, column=1, sticky="ew", pady=5, padx=5)
        ttk.Button(form_frame, text="Save Changes", command=self.save_changes).grid(row=len(fields), column=1, sticky="e", pady=10, padx=5)
    def save_changes(self):
        amount = round(self.amount_var.get(), 2); category = self.category_var.get(); description = self.description_var.get(); expense_date = self.date_var.get()
        if not all([category, description, amount > 0]): messagebox.showerror("Error", "All fields are required.", parent=self); return
        self.db_controller.execute_query("UPDATE daily_expenses SET expense_date=?, category=?, description=?, amount=? WHERE id=?", (expense_date, category, description, amount, self.item_id))
        self.db_controller.execute_query("UPDATE ledger_book SET date=?, party_name=?, description=?, debit=? WHERE description LIKE ?", (expense_date, category, description, amount, f"%[EXPENSE_ID:{self.item_id}]%"))
        messagebox.showinfo("Success", "Expense updated successfully.", parent=self); self.callback(); self.destroy()

class DailyExpensesTab(ttk.Frame):
    def __init__(self, parent, db_controller):
        super().__init__(parent, padding=15); self.db_controller = db_controller
        self.ai_service = AIService(db_controller)
        self.date_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d')); self.category_var = tk.StringVar(); self.description_var = tk.StringVar(); self.amount_var = tk.DoubleVar()
        self.filter_month_var = tk.StringVar(value=datetime.now().strftime("%B")); self.filter_year_var = tk.StringVar(value=datetime.now().strftime("%Y"))
        self.create_widgets(); self.refresh_data()

    def create_widgets(self):
        left_frame = ttk.Frame(self); left_frame.grid(row=0, column=0, padx=(0, 10), sticky="ns"); right_frame = ttk.Frame(self); right_frame.grid(row=0, column=1, sticky="nsew"); self.grid_columnconfigure(1, weight=1)
        form_frame = ttk.LabelFrame(left_frame, text="Add Daily Expense", padding=15); form_frame.pack(fill="x")
        ttk.Label(form_frame, text="Date:").grid(row=0, column=0, sticky="w"); ttk.Entry(form_frame, textvariable=self.date_var).grid(row=0, column=1, pady=5, sticky="ew")
        ttk.Label(form_frame, text="Category:").grid(row=1, column=0, sticky="w"); self.category_combo = ttk.Combobox(form_frame, textvariable=self.category_var, state="readonly"); self.category_combo.grid(row=1, column=1, pady=5, sticky="ew")
        ttk.Label(form_frame, text="Description:").grid(row=2, column=0, sticky="w"); 
        description_entry = ttk.Entry(form_frame, textvariable=self.description_var)
        description_entry.grid(row=2, column=1, pady=5, sticky="ew")
        description_entry.bind("<FocusOut>", self.predict_category)
        ttk.Label(form_frame, text="Amount:").grid(row=3, column=0, sticky="w"); ttk.Entry(form_frame, textvariable=self.amount_var).grid(row=3, column=1, pady=5, sticky="ew")
        ttk.Button(form_frame, text="Add Expense", command=self.add_expense).grid(row=4, column=1, sticky="e", pady=10)
        
        # <<-- REMOVED: The AI training button is no longer needed -->>
        summary_frame = ttk.LabelFrame(left_frame, text="Monthly Expense Summary", padding=15); summary_frame.pack(fill="x", pady=10)
        self.summary_total_var = tk.StringVar(value="Total Expenses: 0.00"); ttk.Label(summary_frame, textvariable=self.summary_total_var, font=("Arial", 12, "bold"), foreground="red").pack(anchor="w")
        filter_frame = ttk.LabelFrame(right_frame, text="Filter View", padding=10); filter_frame.pack(fill="x")
        months = [datetime(2000, m, 1).strftime('%B') for m in range(1, 13)]
        ttk.Label(filter_frame, text="Month:").pack(side="left", padx=5); ttk.Combobox(filter_frame, textvariable=self.filter_month_var, values=months, state="readonly", width=12).pack(side="left", padx=5)
        ttk.Label(filter_frame, text="Year:").pack(side="left", padx=5); ttk.Entry(filter_frame, textvariable=self.filter_year_var, width=6).pack(side="left", padx=5)
        ttk.Button(filter_frame, text="Filter", command=self.refresh_data).pack(side="left", padx=5)
        history_frame = ttk.LabelFrame(right_frame, text="Expense History (Double-click to Edit)", padding=10); history_frame.pack(fill="both", expand=True, pady=10)
        columns = ("id", "date", "category", "description", "amount"); self.tree = ttk.Treeview(history_frame, columns=columns, show="headings")
        self.tree.heading("id", text="ID"); self.tree.column("id", width=40); self.tree.heading("date", text="Date"); self.tree.column("date", width=100); self.tree.heading("category", text="Category"); self.tree.column("category", width=120); self.tree.heading("description", text="Description"); self.tree.column("description", width=250); self.tree.heading("amount", text="Amount"); self.tree.column("amount", width=100, anchor="e"); self.tree.bind("<Double-1>", lambda e: self.edit_expense())
        self.tree.pack(side="left", fill="both", expand=True); scrollbar = ttk.Scrollbar(history_frame, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=scrollbar.set); scrollbar.pack(side="right", fill="y")
        button_frame = ttk.Frame(history_frame); button_frame.pack(fill="x", pady=5); ttk.Button(button_frame, text="Edit Selected", command=self.edit_expense).pack(side="left"); ttk.Button(button_frame, text="Delete Selected", command=self.delete_expense).pack(side="left", padx=5)

    def predict_category(self, event):
        description = self.description_var.get()
        if description:
            predicted_category = self.ai_service.predict_expense_category(description)
            if predicted_category and predicted_category in self.category_combo['values']:
                self.category_var.set(predicted_category)

    def add_expense(self):
        amount = round(self.amount_var.get(), 2); category = self.category_var.get(); description = self.description_var.get(); expense_date = self.date_var.get()
        if not all([category, description, amount > 0]): messagebox.showerror("Error", "All fields and a valid amount are required."); return
        if self.ai_service.is_expense_anomaly(category, amount):
            msg = f"This expense amount ({amount:,.2f}) seems unusually high for '{category}'. Are you sure?"
            if not messagebox.askyesno("Anomaly Detected", msg, icon='warning', parent=self): return
        expense_query = "INSERT INTO daily_expenses (expense_date, category, description, amount) VALUES (?, ?, ?, ?)"; new_id = self.db_controller.execute_query(expense_query, (expense_date, category, description, amount))
        ledger_desc = f"{description} [EXPENSE_ID:{new_id}]"; ledger_query = "INSERT INTO ledger_book (date, party_name, description, debit, credit) VALUES (?, ?, ?, ?, ?)"
        self.db_controller.execute_query(ledger_query, (expense_date, category, ledger_desc, amount, 0))
        messagebox.showinfo("Success", "Expense recorded and added to ledger."); self.description_var.set(""); self.amount_var.set(0.0); self.refresh_data()
    
    # Other methods are unchanged...
    def fetch_and_update_categories(self):
        records = self.db_controller.execute_query("SELECT name FROM expense_categories ORDER BY name", fetch="all")
        if records: cat_names = [row[0] for row in records]; self.category_combo['values'] = cat_names
        if cat_names and not self.category_var.get(): self.category_var.set(cat_names[0])
    def edit_expense(self):
        selected_item = self.tree.focus();
        if not selected_item: messagebox.showwarning("No Selection", "Please select an expense to edit."); return
        item_id = self.tree.item(selected_item, "values")[0]; EditExpenseWindow(self, self.db_controller, item_id, self.refresh_data)
    def delete_expense(self):
        selected_item = self.tree.focus();
        if not selected_item: messagebox.showwarning("No Selection", "Please select an expense to delete."); return
        item_id = self.tree.item(selected_item, "values")[0]
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this expense?\nThis will also remove the corresponding entry from the Ledger Book."):
            self.db_controller.execute_query("DELETE FROM ledger_book WHERE description LIKE ?", (f"%[EXPENSE_ID:{item_id}]%",)); self.db_controller.execute_query("DELETE FROM daily_expenses WHERE id = ?", (item_id,)); self.refresh_data()
    def refresh_data(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        month_num = datetime.strptime(self.filter_month_var.get(), "%B").month; month_year_str = f"{self.filter_year_var.get()}-{month_num:02d}"
        query = "SELECT id, expense_date, category, description, amount FROM daily_expenses WHERE STRFTIME('%Y-%m', expense_date) = ? ORDER BY expense_date DESC"; records = self.db_controller.execute_query(query, (month_year_str,), fetch="all")
        total_expense = 0
        if records:
            for row in records: self.tree.insert("", "end", values=row); total_expense += row[4]
        self.summary_total_var.set(f"Total Expenses: {total_expense:,.2f} BDT"); self.fetch_and_update_categories()