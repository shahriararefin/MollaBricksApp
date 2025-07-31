# molla_bricks/ui/views/customers_tab.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

class CustomersTab(ttk.Frame):
    def __init__(self, parent, db_controller):
        super().__init__(parent, padding=15)
        self.db_controller = db_controller
        self.name_var = tk.StringVar(); self.address_var = tk.StringVar(); self.phone_var = tk.StringVar()
        self.search_var = tk.StringVar(); self.search_var.trace_add("write", lambda *args: self.search_customers())
        self.create_widgets(); self.refresh_customer_list()

    def create_widgets(self):
        left_frame = ttk.Frame(self); left_frame.grid(row=0, column=0, padx=(0, 10), sticky="ns")
        right_frame = ttk.Frame(self); right_frame.grid(row=0, column=1, sticky="nsew"); self.grid_columnconfigure(1, weight=1)
        form_frame = ttk.LabelFrame(left_frame, text="Add/Edit Customer", padding=15); form_frame.pack(fill="x")
        ttk.Label(form_frame, text="Name:").grid(row=0, column=0, sticky="w", pady=2); ttk.Entry(form_frame, textvariable=self.name_var, width=30).grid(row=0, column=1, pady=2)
        ttk.Label(form_frame, text="Address:").grid(row=1, column=0, sticky="w", pady=2); ttk.Entry(form_frame, textvariable=self.address_var, width=30).grid(row=1, column=1, pady=2)
        ttk.Label(form_frame, text="Phone No:").grid(row=2, column=0, sticky="w", pady=2); ttk.Entry(form_frame, textvariable=self.phone_var, width=30).grid(row=2, column=1, pady=2)
        button_frame = ttk.Frame(form_frame); button_frame.grid(row=3, column=1, sticky="ew", pady=10)
        ttk.Button(button_frame, text="Add New", command=self.add_customer).pack(side="left", expand=True)
        ttk.Button(button_frame, text="Save Changes", command=self.save_changes).pack(side="left", expand=True, padx=5)
        ttk.Button(button_frame, text="Clear Form", command=self.clear_form).pack(side="left", expand=True)
        list_frame = ttk.LabelFrame(right_frame, text="Customer List", padding=15); list_frame.pack(fill="both", expand=True)
        ttk.Label(list_frame, text="Search:").pack(anchor="w"); ttk.Entry(list_frame, textvariable=self.search_var).pack(fill="x", pady=(0, 10))
        columns = ("id", "name", "address", "phone"); self.tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        self.tree.heading("id", text="ID"); self.tree.column("id", width=50); self.tree.heading("name", text="Name"); self.tree.column("name", width=200); self.tree.heading("address", text="Address"); self.tree.column("address", width=250); self.tree.heading("phone", text="Phone No."); self.tree.column("phone", width=150)
        self.tree.bind("<<TreeviewSelect>>", self.on_customer_select); self.tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=scrollbar.set); scrollbar.pack(side="right", fill="y")
        ttk.Button(list_frame, text="Delete Selected Customer", command=self.delete_customer).pack(pady=10, anchor="e")

    # <<-- MODIFIED: This function is now much smarter -->>
    def add_customer(self):
        name = self.name_var.get().strip(); address = self.address_var.get().strip(); phone = self.phone_var.get().strip()
        if not name: messagebox.showerror("Input Error", "Customer Name is required.", parent=self); return

        # 1. Check for past one-time transactions with this name
        query = "SELECT COUNT(id) FROM nagad_khata WHERE customer_name = ? AND customer_id IS NULL"
        past_transactions_count = self.db_controller.execute_query(query, (name,), fetch="one")[0]

        link_past_transactions = False
        if past_transactions_count > 0:
            msg = f"Found {past_transactions_count} past one-time transaction(s) for '{name}'.\n\nDo you want to link them to this new registered profile?"
            if messagebox.askyesno("Link Past Transactions?", msg, parent=self):
                link_past_transactions = True

        # 2. Add the new customer to the customers table
        try:
            insert_query = "INSERT INTO customers (name, address, phone) VALUES (?, ?, ?)"
            new_customer_id = self.db_controller.execute_query(insert_query, (name, address, phone))
            messagebox.showinfo("Success", "Customer added successfully.", parent=self)
        except Exception as e:
            messagebox.showerror("Database Error", f"Could not add customer. The phone number might already exist.\n\nError: {e}", parent=self)
            return

        # 3. If user agreed, update the old transactions with the new customer ID
        if link_past_transactions and new_customer_id:
            update_query = "UPDATE nagad_khata SET customer_id = ? WHERE customer_name = ? AND customer_id IS NULL"
            rows_updated = self.db_controller.execute_query(update_query, (new_customer_id, name))
            messagebox.showinfo("Link Successful", f"Successfully linked {rows_updated} past transaction(s) to the new profile.", parent=self)

        self.clear_form(); self.refresh_customer_list()

    # All other methods are unchanged
    def refresh_customer_list(self):
        search_term = self.search_var.get()
        for item in self.tree.get_children(): self.tree.delete(item)
        if search_term: query = "SELECT * FROM customers WHERE name LIKE ? OR phone LIKE ? ORDER BY name"; params = (f"%{search_term}%", f"%{search_term}%")
        else: query = "SELECT * FROM customers ORDER BY name"; params = ()
        records = self.db_controller.execute_query(query, params, fetch="all")
        if records:
            for row in records: self.tree.insert("", "end", values=row, iid=row[0])
    def search_customers(self): self.refresh_customer_list()
    def save_changes(self):
        selected_item = self.tree.focus();
        if not selected_item: messagebox.showwarning("No Selection", "Please select a customer from the list to save changes.", parent=self); return
        name = self.name_var.get().strip(); phone = self.phone_var.get().strip()
        if not name: messagebox.showerror("Input Error", "Customer Name is required.", parent=self); return
        try:
            self.db_controller.execute_query("UPDATE customers SET name=?, address=?, phone=? WHERE id=?", (name, self.address_var.get(), phone, selected_item))
            self.clear_form(); self.refresh_customer_list()
        except Exception as e: messagebox.showerror("Database Error", f"Could not save changes.\n\nError: {e}", parent=self)
    def delete_customer(self):
        selected_item = self.tree.focus();
        if not selected_item: messagebox.showwarning("No Selection", "Please select a customer to delete.", parent=self); return
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this customer?\nThis will not delete their past sales records, but will unlink them."):
            self.db_controller.execute_query("DELETE FROM customers WHERE id = ?", (selected_item,)); self.clear_form(); self.refresh_customer_list()
    def on_customer_select(self, event):
        selected_item = self.tree.focus()
        if not selected_item: return
        values = self.tree.item(selected_item, "values"); self.name_var.set(values[1]); self.address_var.set(values[2]); self.phone_var.set(values[3])
    def clear_form(self):
        self.name_var.set(""); self.address_var.set(""); self.phone_var.set("")
        if self.tree.focus(): self.tree.selection_remove(self.tree.focus())
    def refresh_data(self): self.refresh_customer_list()