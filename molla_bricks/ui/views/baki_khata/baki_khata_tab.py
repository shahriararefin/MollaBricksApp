# molla_bricks/ui/views/baki_khata/baki_khata_tab.py
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import os, csv, sys
from molla_bricks.core.services.nagad_service import NagadService
from molla_bricks.ui.custom_calendar import CalendarPopup

class AdvancedSettlementWindow(tk.Toplevel):
    def __init__(self, parent, db_controller, customer_id, customer_name, callback):
        super().__init__(parent); self.transient(parent); self.title(f"Advanced Settlement for {customer_name}"); self.geometry("700x500")
        self.db_controller = db_controller; self.customer_id = customer_id; self.customer_name = customer_name; self.callback = callback
        self.payment_date_var = tk.StringVar(master=self, value=datetime.now().strftime('%Y-%m-%d')); self.total_payment_var = tk.DoubleVar(master=self, value=0.0)
        self.total_allocated_var = tk.StringVar(master=self, value="Allocated: 0.00"); self.remaining_var = tk.StringVar(master=self, value="Remaining: 0.00")
        self.create_widgets(); self.load_dues()
        self.total_payment_var.trace_add("write", self._auto_allocate_payment)
        self.grab_set(); self.wait_window()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding=10); main_frame.pack(fill="both", expand=True)
        top_frame = ttk.Frame(main_frame); top_frame.pack(fill="x", pady=5)
        ttk.Label(top_frame, text="Payment Date:").pack(side="left", padx=5); ttk.Entry(top_frame, textvariable=self.payment_date_var, width=12).pack(side="left"); ttk.Button(top_frame, text="📅", width=3, command=lambda: CalendarPopup(self, self.payment_date_var)).pack(side="left")
        ttk.Label(top_frame, text="Total Payment Received:").pack(side="left", padx=20); ttk.Entry(top_frame, textvariable=self.total_payment_var, width=15).pack(side="left")
        tree_frame = ttk.LabelFrame(main_frame, text="Allocate Payment (Double-click 'Amount to Pay' cell to edit)", padding=10); tree_frame.pack(fill="both", expand=True, pady=10)
        columns = ("id", "date", "chalan_no", "due_amount", "pay_amount"); self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        self.tree.heading("id", text="ID"); self.tree.column("id", width=40); self.tree.heading("date", text="Chalan Date"); self.tree.column("date", width=100); self.tree.heading("chalan_no", text="Chalan No"); self.tree.column("chalan_no", width=80); self.tree.heading("due_amount", text="Amount Due"); self.tree.column("due_amount", anchor="e"); self.tree.heading("pay_amount", text="Amount to Pay"); self.tree.column("pay_amount", anchor="e")
        self.tree.bind("<Double-1>", self.on_edit_cell); self.tree.pack(side="left", fill="both", expand=True); scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=scrollbar.set); scrollbar.pack(side="right", fill="y")
        summary_frame = ttk.Frame(main_frame); summary_frame.pack(fill="x", pady=5); ttk.Label(summary_frame, textvariable=self.total_allocated_var, font=("Arial", 10, "bold")).pack(side="left"); ttk.Label(summary_frame, textvariable=self.remaining_var, font=("Arial", 10, "bold")).pack(side="right")
        ttk.Button(main_frame, text="Confirm & Save Settlement", command=self.save_settlement, style="Accent.TButton").pack(side="right", pady=10)

    def _auto_allocate_payment(self, *args):
        try: payment_to_allocate = self.total_payment_var.get()
        except (tk.TclError, ValueError): payment_to_allocate = 0.0
        for item_id in self.tree.get_children():
            due_val = float(self.tree.set(item_id, "due_amount")); amount_to_pay = min(payment_to_allocate, due_val)
            self.tree.set(item_id, "pay_amount", f"{amount_to_pay:.2f}"); payment_to_allocate -= amount_to_pay
        self.update_summary()

    def load_dues(self):
        query = "SELECT id, date, chalan_no, due_amount FROM nagad_khata WHERE customer_id = ? AND due_amount > 0.01 ORDER BY id ASC"
        records = self.db_controller.execute_query(query, (self.customer_id,), fetch="all")
        if records:
            for row in records: self.tree.insert("", "end", values=(row[0], row[1], row[2], f"{row[3]:.2f}", "0.00"), iid=row[0])

    def on_edit_cell(self, event):
        item_id = self.tree.focus(); column = self.tree.identify_column(event.x)
        if not item_id or column != "#5": return
        x, y, width, height = self.tree.bbox(item_id, column); value = self.tree.set(item_id, column)
        entry = ttk.Entry(self.tree, width=width); entry.place(x=x, y=y, width=width, height=height); entry.insert(0, value); entry.focus_set()
        def on_focus_out(event):
            try:
                pay_val = float(entry.get()) if entry.get() else 0.0; due_val = float(self.tree.set(item_id, "due_amount"))
                if pay_val > due_val: pay_val = due_val
                self.tree.set(item_id, column, f"{pay_val:.2f}")
            except ValueError: self.tree.set(item_id, column, "0.00")
            finally: entry.destroy(); self.update_summary()
        entry.bind("<FocusOut>", on_focus_out); entry.bind("<Return>", on_focus_out)

    def update_summary(self, *args):
        allocated = sum(float(self.tree.set(item, "pay_amount") or 0.0) for item in self.tree.get_children())
        total_payment = self.total_payment_var.get(); self.total_allocated_var.set(f"Allocated: {allocated:,.2f}"); self.remaining_var.set(f"Remaining: {total_payment - allocated:,.2f}")

    def save_settlement(self):
        total_payment = self.total_payment_var.get(); total_allocated = sum(float(self.tree.set(item, "pay_amount") or 0.0) for item in self.tree.get_children())
        if total_allocated > total_payment: messagebox.showerror("Error", "Allocated amount cannot be greater than the total payment received.", parent=self); return
        if total_allocated <= 0: messagebox.showwarning("No Allocation", "No payment amounts were allocated to any dues.", parent=self); return
        payment_date = self.payment_date_var.get(); ledger_desc = f"Lump-sum payment of {total_allocated:,.2f} received, allocated across multiple chalans."
        self.db_controller.execute_query("INSERT INTO ledger_book (date, party_name, description, credit) VALUES (?, ?, ?, ?)", (payment_date, self.customer_name, ledger_desc, total_allocated))
        for item_id in self.tree.get_children():
            pay_amount = float(self.tree.set(item_id, "pay_amount") or 0.0)
            if pay_amount > 0: self.db_controller.execute_query("UPDATE nagad_khata SET paid_amount = paid_amount + ?, due_amount = due_amount - ? WHERE id = ?", (pay_amount, pay_amount, item_id))
        messagebox.showinfo("Success", "Settlement saved successfully.", parent=self); self.callback(); self.destroy()

class BakiKhataTab(ttk.Frame):
    def __init__(self, parent, db_controller):
        super().__init__(parent); self.db_controller = db_controller; self.filter_customer_var = tk.StringVar(); self.filter_chalan_var = tk.StringVar(); self.customer_map = {}
        self.create_widgets()
    
    def create_widgets(self):
        main_frame = ttk.Frame(self, padding=10); main_frame.pack(expand=True, fill="both")
        top_frame = ttk.Frame(main_frame); top_frame.pack(fill="x", pady=5)
        
        ttk.Label(top_frame, text="Filter by Customer:").pack(side="left", padx=(0,5)); self.customer_combo = ttk.Combobox(top_frame, textvariable=self.filter_customer_var, state="readonly", width=30); self.customer_combo.pack(side="left")
        ttk.Label(top_frame, text="Chalan No:").pack(side="left", padx=(10,5)); ttk.Entry(top_frame, textvariable=self.filter_chalan_var, width=10).pack(side="left")
        ttk.Button(top_frame, text="Filter", command=self.refresh_data).pack(side="left", padx=5); ttk.Button(top_frame, text="Show All", command=self.show_all).pack(side="left", padx=5)
        
        action_frame = ttk.Frame(top_frame); action_frame.pack(side="right")
        ttk.Button(action_frame, text="💰 Advanced Settlement...", command=self.advanced_settle).pack(side="left", padx=5)
        ttk.Button(action_frame, text="📄 Export CSV", command=self.export_to_csv).pack(side="left", padx=5)
        ttk.Button(action_frame, text="🖨️ Print Report", command=self.print_report).pack(side="left")
        
        history_frame = ttk.LabelFrame(main_frame, text="Outstanding Dues", padding=15); history_frame.pack(fill="both", expand=True, pady=10)
        self.total_due_var = tk.StringVar(value="Total Displayed Due: 0.00 BDT"); ttk.Label(history_frame, textvariable=self.total_due_var, font=("Arial", 14, "bold"), foreground="red").pack(anchor="e", pady=(0,5))
        columns = ("id", "date", "chalan_no", "customer_name", "total_amount", "paid_amount", "due_amount"); self.tree = ttk.Treeview(history_frame, columns=columns, show="headings")
        for col in columns: self.tree.heading(col, text=col.replace("_", " ").title()); self.tree.column(col, anchor="center")
        scrollbar = ttk.Scrollbar(history_frame, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=scrollbar.set); self.tree.pack(side="left", fill="both", expand=True); scrollbar.pack(side="right", fill="y")

    def advanced_settle(self):
        customer_name = self.filter_customer_var.get(); customer_id = self.customer_map.get(customer_name)
        if not customer_id: messagebox.showwarning("Selection Required", "Please filter by a specific customer before using Advanced Settlement.", parent=self); return
        AdvancedSettlementWindow(self, self.db_controller, customer_id, customer_name, self.refresh_data)

    def show_all(self): self.filter_customer_var.set(""); self.filter_chalan_var.set(""); self.refresh_data()
    
    def refresh_data(self):
        self.fetch_and_update_customer_list(); self.refresh_due_list()
        
    def fetch_and_update_customer_list(self):
        current_selection = self.filter_customer_var.get()
        query = "SELECT c.id, c.name FROM customers c JOIN nagad_khata n ON c.id = n.customer_id WHERE n.due_amount > 0.01 GROUP BY c.id ORDER BY c.name"
        records = self.db_controller.execute_query(query, fetch="all")
        if records: 
            self.customer_map = {name: id for id, name in records}; customer_names = list(self.customer_map.keys())
            self.customer_combo['values'] = customer_names
            if current_selection not in customer_names: self.filter_customer_var.set("")
        else: self.customer_map = {}; self.customer_combo['values'] = []; self.filter_customer_var.set("")
            
    def refresh_due_list(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        customer_name_filter = self.filter_customer_var.get(); customer_id_filter = self.customer_map.get(customer_name_filter); chalan_filter = self.filter_chalan_var.get()
        query = "SELECT id, date, chalan_no, customer_name, total_amount, paid_amount, due_amount FROM nagad_khata WHERE due_amount > 0.01"
        params = []
        if customer_id_filter: query += " AND customer_id = ?"; params.append(customer_id_filter)
        if chalan_filter: query += " AND chalan_no LIKE ?"; params.append(f"%{chalan_filter}%")
        query += " ORDER BY id ASC"; records = self.db_controller.execute_query(query, tuple(params), fetch="all")
        if records:
            for row in records: self.tree.insert("", "end", values=row)
        self.update_summary()
        
    def update_summary(self):
        customer_name_filter = self.filter_customer_var.get(); customer_id_filter = self.customer_map.get(customer_name_filter); chalan_filter = self.filter_chalan_var.get()
        query = "SELECT SUM(due_amount) FROM nagad_khata WHERE due_amount > 0.01"; params = []
        if customer_id_filter: query += " AND customer_id = ?"; params.append(customer_id_filter)
        if chalan_filter: query += " AND chalan_no LIKE ?"; params.append(f"%{chalan_filter}%")
        result = self.db_controller.execute_query(query, tuple(params), fetch="one"); self.total_due_var.set(f"Total Displayed Due: {(result[0] or 0):,.2f} BDT")

    def print_report(self):
        customer_name_filter = self.filter_customer_var.get(); customer_id_filter = self.customer_map.get(customer_name_filter)
        if not customer_id_filter: messagebox.showwarning("Selection Required", "Please filter by a specific customer to generate a report.", parent=self); return
        query = "SELECT id, date, chalan_no, customer_name, total_amount, paid_amount, due_amount FROM nagad_khata WHERE due_amount > 0.01 AND customer_id = ? ORDER BY id ASC"
        transactions = self.db_controller.execute_query(query, (customer_id_filter,), fetch="all")
        if not transactions: messagebox.showwarning("No Data", "This customer has no outstanding dues to report.", parent=self); return
        total_due = sum(row[6] for row in transactions); summary = {"customer_name": customer_name_filter, "total_due": total_due}
        try:
            pdf_path = NagadService.generate_due_report_pdf(transactions, summary)
            if messagebox.askyesno("Success", f"PDF report created at:\n{os.path.abspath(pdf_path)}\n\nDo you want to open it?"):
                if sys.platform == "win32": os.startfile(os.path.abspath(pdf_path))
                else: subprocess.call(["open", os.path.abspath(pdf_path)])
        except Exception as e: messagebox.showerror("PDF Error", f"Failed to generate PDF: {e}", parent=self)

    def export_to_csv(self):
        os.makedirs("exports", exist_ok=True); safe_name = "".join(c for c in "all_dues" if c.isalnum()); file_path = f"exports/all_dues_{datetime.now().strftime('%Y%m%d')}.csv"
        records = self.db_controller.execute_query("SELECT id, date, chalan_no, customer_name, total_amount, paid_amount, due_amount FROM nagad_khata WHERE due_amount > 0.01 ORDER BY id ASC", fetch="all")
        if not records: messagebox.showwarning("No Data", "There are no outstanding dues to export.", parent=self); return
        header = ["ID", "Date", "Chalan No", "Customer Name", "Total Amount", "Paid Amount", "Due Amount"]
        with open(file_path, 'w', newline='', encoding='utf-8') as f: writer = csv.writer(f); writer.writerow(header); writer.writerows(records)
        messagebox.showinfo("Success", f"Export successful!\nFile saved to: {os.path.abspath(file_path)}", parent=self)

    def load_initial_data(self): self.refresh_data()