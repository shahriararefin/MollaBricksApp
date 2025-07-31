# molla_bricks/ui/views/settings_manager.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

class BrickTypeManagerWindow(tk.Toplevel):
    def __init__(self, parent, db_controller, refresh_callback):
        super().__init__(parent); self.transient(parent); self.title("Manage Brick Types"); self.db_controller = db_controller; self.refresh_callback = refresh_callback; self.new_type_var = tk.StringVar()
        self.create_widgets(); self.refresh_treeview(); self.protocol("WM_DELETE_WINDOW", self.on_close); self.grab_set(); self.wait_window()
    def create_widgets(self):
        main_frame = ttk.Frame(self, padding=10); main_frame.pack(fill="both", expand=True)
        add_frame = ttk.LabelFrame(main_frame, text="Add New Brick Type", padding=10); add_frame.pack(fill="x", pady=5)
        ttk.Entry(add_frame, textvariable=self.new_type_var, width=30).pack(side="left", fill="x", expand=True, padx=5); ttk.Button(add_frame, text="Add", command=self.add_type).pack(side="left")
        list_frame = ttk.LabelFrame(main_frame, text="Existing Types", padding=10); list_frame.pack(fill="both", expand=True, pady=5)
        self.tree = ttk.Treeview(list_frame, columns=("id", "name"), show="headings"); self.tree.heading("id", text="ID"); self.tree.column("id", width=50, anchor="center"); self.tree.heading("name", text="Brick Type Name"); self.tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=scrollbar.set); scrollbar.pack(side="right", fill="y")
        button_frame = ttk.Frame(main_frame); button_frame.pack(fill="x", pady=5); ttk.Button(button_frame, text="Edit Selected", command=self.edit_type).pack(side="left", padx=5); ttk.Button(button_frame, text="Delete Selected", command=self.delete_type).pack(side="left", padx=5); ttk.Button(button_frame, text="Close", command=self.on_close).pack(side="right")
    def refresh_treeview(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        records = self.db_controller.execute_query("SELECT id, name FROM brick_types ORDER BY name", fetch="all")
        if records:
            for row in records: self.tree.insert("", "end", values=row)
    def add_type(self):
        name = self.new_type_var.get().strip()
        if not name: messagebox.showwarning("Input Error", "Brick type name cannot be empty.", parent=self); return
        try: self.db_controller.execute_query("INSERT INTO brick_types (name) VALUES (?)", (name,)); self.new_type_var.set(""); self.refresh_treeview()
        except Exception as e: messagebox.showerror("Database Error", f"Could not add type. It might already exist.\n\n{e}", parent=self)
    def edit_type(self):
        selected_item = self.tree.focus();
        if not selected_item: messagebox.showwarning("No Selection", "Please select a type to edit.", parent=self); return
        item_id, old_name = self.tree.item(selected_item, "values")
        new_name = simpledialog.askstring("Edit Brick Type", "Enter the new name:", initialvalue=old_name, parent=self)
        if new_name and new_name.strip() != old_name:
            try: self.db_controller.execute_query("UPDATE brick_types SET name = ? WHERE id = ?", (new_name.strip(), item_id)); self.refresh_treeview()
            except Exception as e: messagebox.showerror("Database Error", f"Could not update type.\n\n{e}", parent=self)
    def delete_type(self):
        selected_item = self.tree.focus();
        if not selected_item: messagebox.showwarning("No Selection", "Please select a type to delete.", parent=self); return
        item_id, name = self.tree.item(selected_item, "values")
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{name}'?", parent=self):
            self.db_controller.execute_query("DELETE FROM brick_types WHERE id = ?", (item_id,)); self.refresh_treeview()
    def on_close(self):
        if self.refresh_callback: self.refresh_callback(); self.destroy()

# <<-- NEW: Class for managing Expense Categories -->>
class ExpenseCategoryManagerWindow(tk.Toplevel):
    def __init__(self, parent, db_controller, refresh_callback):
        super().__init__(parent); self.transient(parent); self.title("Manage Expense Categories"); self.db_controller = db_controller; self.refresh_callback = refresh_callback; self.new_cat_var = tk.StringVar()
        self.create_widgets(); self.refresh_treeview(); self.protocol("WM_DELETE_WINDOW", self.on_close); self.grab_set(); self.wait_window()
    def create_widgets(self):
        main_frame = ttk.Frame(self, padding=10); main_frame.pack(fill="both", expand=True)
        add_frame = ttk.LabelFrame(main_frame, text="Add New Category", padding=10); add_frame.pack(fill="x", pady=5)
        ttk.Entry(add_frame, textvariable=self.new_cat_var, width=30).pack(side="left", fill="x", expand=True, padx=5); ttk.Button(add_frame, text="Add", command=self.add_category).pack(side="left")
        list_frame = ttk.LabelFrame(main_frame, text="Existing Categories", padding=10); list_frame.pack(fill="both", expand=True, pady=5)
        self.tree = ttk.Treeview(list_frame, columns=("id", "name"), show="headings"); self.tree.heading("id", text="ID"); self.tree.column("id", width=50, anchor="center"); self.tree.heading("name", text="Category Name"); self.tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=scrollbar.set); scrollbar.pack(side="right", fill="y")
        button_frame = ttk.Frame(main_frame); button_frame.pack(fill="x", pady=5); ttk.Button(button_frame, text="Delete Selected", command=self.delete_category).pack(side="left", padx=5); ttk.Button(button_frame, text="Close", command=self.on_close).pack(side="right")
    def refresh_treeview(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        records = self.db_controller.execute_query("SELECT id, name FROM expense_categories ORDER BY name", fetch="all")
        if records:
            for row in records: self.tree.insert("", "end", values=row)
    def add_category(self):
        name = self.new_cat_var.get().strip()
        if not name: messagebox.showwarning("Input Error", "Category name cannot be empty.", parent=self); return
        try: self.db_controller.execute_query("INSERT INTO expense_categories (name) VALUES (?)", (name,)); self.new_cat_var.set(""); self.refresh_treeview()
        except Exception as e: messagebox.showerror("Database Error", f"Could not add category. It might already exist.\n\n{e}", parent=self)
    def delete_category(self):
        selected_item = self.tree.focus();
        if not selected_item: messagebox.showwarning("No Selection", "Please select a category to delete.", parent=self); return
        item_id, name = self.tree.item(selected_item, "values")
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{name}'?", parent=self):
            self.db_controller.execute_query("DELETE FROM expense_categories WHERE id = ?", (item_id,)); self.refresh_treeview()
    def on_close(self):
        if self.refresh_callback: self.refresh_callback(); self.destroy()