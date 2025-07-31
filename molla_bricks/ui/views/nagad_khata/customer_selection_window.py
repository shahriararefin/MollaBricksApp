# molla_bricks/ui/views/nagad_khata/customer_selection_window.py
import tkinter as tk
from tkinter import ttk, messagebox

class CustomerSelectionWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.db_controller = parent.db_controller
        self.transient(parent)
        self.title("Select a Customer")
        self.geometry("650x400")
        self.selected_customer = None

        search_frame = ttk.Frame(self, padding=10)
        search_frame.pack(fill="x")
        ttk.Label(search_frame, text="Search (by Name or Phone):").pack(side="left")
        search_var = tk.StringVar()
        search_var.trace_add("write", lambda *args: self.search_customers(search_var.get()))
        ttk.Entry(search_frame, textvariable=search_var).pack(side="left", fill="x", expand=True, padx=5)

        tree_frame = ttk.Frame(self, padding=10)
        tree_frame.pack(fill="both", expand=True)
        columns = ("id", "name", "address", "phone")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        self.tree.heading("id", text="ID"); self.tree.column("id", width=50)
        self.tree.heading("name", text="Name"); self.tree.column("name", width=150)
        self.tree.heading("address", text="Address"); self.tree.column("address", width=200)
        self.tree.heading("phone", text="Phone No."); self.tree.column("phone", width=120)
        self.tree.bind("<Double-1>", self.on_select)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set); scrollbar.pack(side="right", fill="y")
        
        button_frame = ttk.Frame(self, padding=10)
        button_frame.pack(fill="x")
        ttk.Button(button_frame, text="Select Customer", command=self.on_select, style="Accent.TButton").pack(side="right")
        
        self.refresh_list()
        self.grab_set()
        self.wait_window()

    def refresh_list(self, search_term=""):
        for item in self.tree.get_children(): self.tree.delete(item)
        if search_term:
            query = "SELECT * FROM customers WHERE name LIKE ? OR phone LIKE ? ORDER BY name"
            params = (f"%{search_term}%", f"%{search_term}%")
        else:
            query = "SELECT * FROM customers ORDER BY name"; params = ()
        records = self.db_controller.execute_query(query, params, fetch="all")
        if records:
            for row in records: self.tree.insert("", "end", values=row)

    def search_customers(self, search_term):
        self.refresh_list(search_term)

    def on_select(self, event=None):
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("No Selection", "Please select a customer from the list.", parent=self)
            return
        self.selected_customer = self.tree.item(selected_item, "values")
        self.destroy()