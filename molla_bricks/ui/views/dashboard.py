# molla_bricks/ui/views/dashboard.py
import tkinter as tk
# --- MODIFIED: Import ttkbootstrap instead of ttk ---
import ttkbootstrap as ttk
from tkinter import messagebox
from datetime import datetime, timedelta

class Dashboard(ttk.Frame):
    def __init__(self, parent, db_controller):
        super().__init__(parent)
        self.db_controller = db_controller
        self.filter_period_var = tk.StringVar(value="This Month")
        
        # NOTE: Styles are now inherited from the main AppController window
        # We can use bootstyle attributes directly on widgets
        
        self.create_widgets()
        self.refresh_data()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(expand=True, fill="both")
        
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(header_frame, text="Business Health Overview", font=("", 20, "bold")).pack(side="left")
        
        action_frame = ttk.Frame(header_frame)
        action_frame.pack(side="right")
        ttk.Button(action_frame, text="🔄 Refresh", command=self.refresh_data, bootstyle="secondary").pack(side="right")
        filter_options = ["This Month", "Today", "This Week", "This Year", "All Time"]
        period_combo = ttk.Combobox(action_frame, textvariable=self.filter_period_var, values=filter_options, state="readonly", width=12)
        period_combo.pack(side="right", padx=10)
        period_combo.bind("<<ComboboxSelected>>", self.refresh_data)
        ttk.Label(action_frame, text="Period:").pack(side="right")
        
        top_content_frame = ttk.Frame(main_frame)
        top_content_frame.pack(fill="x", pady=10)
        top_content_frame.grid_columnconfigure(0, weight=2)
        top_content_frame.grid_columnconfigure(1, weight=1)

        cards_frame = ttk.Frame(top_content_frame)
        cards_frame.grid(row=0, column=0, sticky="nsew")
        cards_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.alerts_frame = ttk.LabelFrame(top_content_frame, text="🔔 Alerts & Reminders", padding=15, bootstyle="info")
        self.alerts_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        # Card widgets
        self.revenue_card = self.create_summary_card(cards_frame, "Total Revenue (Sales)", "0.00", "success")
        self.revenue_card.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.dues_card = self.create_summary_card(cards_frame, "Total Outstanding Dues", "0.00", "danger")
        self.dues_card.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        self.potential_revenue_card = self.create_summary_card(cards_frame, "Potential Revenue", "0.00", "primary")
        self.potential_revenue_card.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")
        self.expense_card = self.create_summary_card(cards_frame, "Total Expenses", "0.00", "warning")
        self.expense_card.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        self.profit_card = self.create_summary_card(cards_frame, "Net Profit / Loss", "0.00", "light")
        self.profit_card.grid(row=1, column=1, padx=5, pady=5, sticky="nsew", columnspan=2)
        
        history_frame = ttk.LabelFrame(main_frame, text="Activity in Period", padding=15)
        history_frame.pack(fill="both", expand=True, pady=10)
        columns = ("date", "type", "details", "amount"); self.tree = ttk.Treeview(history_frame, columns=columns, show="headings", bootstyle="primary")
        self.tree.heading("date", text="Date & Time"); self.tree.column("date", width=150); self.tree.heading("type", text="Type"); self.tree.column("type", width=100, anchor="center"); self.tree.heading("details", text="Details"); self.tree.column("details", width=400); self.tree.heading("amount", text="Amount (BDT)"); self.tree.column("amount", width=150, anchor="e")
        scrollbar = ttk.Scrollbar(history_frame, orient="vertical", command=self.tree.yview, bootstyle="round-primary"); self.tree.configure(yscrollcommand=scrollbar.set); self.tree.pack(side="left", fill="both", expand=True); scrollbar.pack(side="right", fill="y")

    def create_summary_card(self, parent, title, initial_value, bootstyle):
        card = ttk.Frame(parent, padding=10, bootstyle="secondary")
        ttk.Label(card, text=title).pack(anchor="w")
        value_label = ttk.Label(card, text=initial_value, font=("", 16, "bold"), bootstyle=f"{bootstyle}-inverse")
        value_label.pack(anchor="w", pady=(5, 0)); card.value_label = value_label
        return card
    
    def _get_date_range(self):
        period = self.filter_period_var.get(); today = datetime.now().date()
        if period == "Today": return today, today
        elif period == "This Week": return today - timedelta(days=today.weekday()), today
        elif period == "This Month": return today.replace(day=1), today
        elif period == "This Year": return today.replace(month=1, day=1), today
        else: return None

    def refresh_data(self, event=None):
        try:
            self._update_summary_cards()
            self._update_activity_list()
            self._update_alerts_panel()
        except Exception as e: messagebox.showerror("Dashboard Error", f"Could not refresh dashboard data.\nError: {e}", parent=self)
            
    def _update_alerts_panel(self):
        for widget in self.alerts_frame.winfo_children(): widget.destroy()
        alerts = []
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        overdue_query = "SELECT COUNT(id) FROM nagad_khata WHERE due_amount > 0.01 AND date <= ?"; overdue_count = self.db_controller.execute_query(overdue_query, (thirty_days_ago,), fetch="one")[0] or 0
        if overdue_count > 0: alerts.append(f"⚠️ You have {overdue_count} unpaid due(s) older than 30 days.")
        
        today = datetime.now().date()
        if today.day > 5:
            last_month_date = today.replace(day=1) - timedelta(days=1); last_month_str = last_month_date.strftime('%Y-%m')
            paid_staff_ids = {row[0] for row in self.db_controller.execute_query("SELECT DISTINCT staff_id FROM salary_payments WHERE STRFTIME('%Y-%m', payment_date) = ?", (last_month_str,), fetch="all")}
            all_staff_ids = {row[0] for row in self.db_controller.execute_query("SELECT id FROM staff", fetch="all")}
            if all_staff_ids - paid_staff_ids: alerts.append(f"🔔 Reminder: Salaries for {last_month_date.strftime('%B')} may be due.")
        
        if not alerts: ttk.Label(self.alerts_frame, text="✅ No critical alerts.", bootstyle="success").pack(anchor="w")
        else:
            for alert_text in alerts: ttk.Label(self.alerts_frame, text=alert_text, bootstyle="warning").pack(anchor="w")

    def _update_summary_cards(self):
        date_range = self._get_date_range(); nagad_where, expense_where, salary_where, params = ("", "", "", ())
        if date_range:
            start_date, end_date = date_range[0].strftime('%Y-%m-%d'), date_range[1].strftime('%Y-%m-%d')
            nagad_where = "WHERE date(timestamp) BETWEEN ? AND ?"; expense_where = "WHERE date(expense_date) BETWEEN ? AND ?"; salary_where = "WHERE date(payment_date) BETWEEN ? AND ?"; params = (start_date, end_date)
        revenue = self.db_controller.execute_query(f"SELECT SUM(total_amount) FROM nagad_khata {nagad_where}", params, fetch="one")[0] or 0
        total_dues = self.db_controller.execute_query(f"SELECT SUM(due_amount) FROM nagad_khata {nagad_where}", params, fetch="one")[0] or 0
        salary_expense = self.db_controller.execute_query(f"SELECT SUM(paid_amount) FROM salary_payments {salary_where}", params, fetch="one")[0] or 0
        daily_expense = self.db_controller.execute_query(f"SELECT SUM(amount) FROM daily_expenses {expense_where}", params, fetch="one")[0] or 0
        total_expenses = salary_expense + daily_expense; net_profit = revenue - total_expenses
        self.revenue_card.value_label.config(text=f"{revenue:,.2f} BDT"); self.dues_card.value_label.config(text=f"{total_dues:,.2f} BDT")
        self.potential_revenue_card.value_label.config(text=f"{revenue + total_dues:,.2f} BDT"); self.expense_card.value_label.config(text=f"{total_expenses:,.2f} BDT")
        self.profit_card.value_label.config(text=f"{net_profit:,.2f} BDT"); self.profit_card.value_label.config(bootstyle="success-inverse" if net_profit >= 0 else "danger-inverse")

    def _update_activity_list(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        date_range = self._get_date_range(); nagad_where, expense_where, salary_where, params = ("", "", "", ())
        if date_range:
            start_date, end_date = date_range[0].strftime('%Y-%m-%d'), date_range[1].strftime('%Y-%m-%d')
            nagad_where = "WHERE date(timestamp) BETWEEN ? AND ?"; expense_where = "WHERE date(expense_date) BETWEEN ? AND ?"; salary_where = "WHERE date(payment_date) BETWEEN ? AND ?"; params = (start_date, end_date)
        activity_query = f"""
        SELECT datetime(timestamp), 'Sale', customer_name || ' (' || brick_amount || ' bricks)', total_amount FROM nagad_khata {nagad_where}
        UNION ALL SELECT datetime(payment_date), 'Salary', 'Payment to ' || s.name, p.paid_amount FROM salary_payments p JOIN staff s ON p.staff_id = s.id {salary_where}
        UNION ALL SELECT datetime(expense_date), 'Expense', category || ' - ' || description, amount FROM daily_expenses {expense_where}
        ORDER BY 1 DESC LIMIT 20; """
        q_params = params * 3 if date_range else (); records = self.db_controller.execute_query(activity_query, q_params, fetch="all")
        if records:
            for row in records:
                try: formatted_date = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S').strftime('%d %b %Y, %I:%M %p')
                except (ValueError, TypeError): formatted_date = row[0]
                self.tree.insert("", "end", values=(formatted_date, row[1], row[2], f"{row[3]:,.2f}"))