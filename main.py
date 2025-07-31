# main.py
import tkinter as tk
# --- MODIFIED: Import ttkbootstrap instead of ttk ---
import ttkbootstrap as ttk
from tkinter import messagebox
import logging, os, sys
from datetime import datetime, timedelta
import threading

# --- Local Imports ---
from molla_bricks.core.db.db_controller import DBController
from molla_bricks.core.services.ai_service import AIService
from molla_bricks.ui.custom_calendar import CalendarPopup
from molla_bricks.core.services.ledger_service import LedgerService
from molla_bricks.ui.views.dashboard import Dashboard
from molla_bricks.ui.views.customers_tab import CustomersTab
from molla_bricks.ui.views.nagad_khata.nagad_khata_tab import NagadKhataTab
from molla_bricks.ui.views.ledger_book.ledger_khata_tab import LedgerKhataTab
from molla_bricks.ui.views.baki_khata.baki_khata_tab import BakiKhataTab
from molla_bricks.ui.views.salary_tab import SalaryTab
from molla_bricks.ui.views.daily_expenses_tab import DailyExpensesTab
from molla_bricks.ui.views.insights_tab import InsightsTab
from molla_bricks.ui.views.settings_manager import BrickTypeManagerWindow, ExpenseCategoryManagerWindow

# LoginFrame is unchanged but will inherit the new style
class LoginFrame(ttk.Frame):
    def __init__(self, container, db_controller, show_main_app_callback):
        super().__init__(container); self.db_controller = db_controller; self.show_main_app_callback = show_main_app_callback; self.username_var = tk.StringVar(); self.password_var = tk.StringVar(); self.grid_rowconfigure(0, weight=1); self.grid_columnconfigure(0, weight=1); frame = ttk.Frame(self, padding=20); frame.grid(); ttk.Label(frame, text="Molla Bricks Login", font=("Arial", 20, "bold")).grid(row=0, column=0, columnspan=2, pady=20); ttk.Label(frame, text="Username:", font=("Arial", 12)).grid(row=1, column=0, sticky="w", pady=5); username_entry = ttk.Entry(frame, textvariable=self.username_var, width=30, font=("Arial", 11)); username_entry.grid(row=1, column=1, pady=5); username_entry.focus_set(); ttk.Label(frame, text="Password:", font=("Arial", 12)).grid(row=2, column=0, sticky="w", pady=5); ttk.Entry(frame, textvariable=self.password_var, show="*", width=30, font=("Arial", 11)).grid(row=2, column=1, pady=5); ttk.Button(frame, text="Login", command=self.attempt_login, bootstyle="primary").grid(row=3, column=1, sticky="e", pady=20); self.bind_all("<Return>", self.attempt_login)
    def attempt_login(self, event=None):
        username = self.username_var.get(); password = self.password_var.get()
        if self.db_controller.verify_user(username, password): self.unbind_all("<Return>"); self.show_main_app_callback(username)
        else: messagebox.showerror("Login Failed", "Invalid username or password.")

class ChangePasswordWindow(tk.Toplevel):
    def __init__(self, parent, db_controller, username):
        super().__init__(parent); self.title("Change Password"); self.db_controller = db_controller; self.username = username; self.old_pass_var = tk.StringVar(); self.new_pass_var = tk.StringVar(); self.confirm_pass_var = tk.StringVar(); main_frame = ttk.Frame(self, padding=20); main_frame.pack(fill="both", expand=True); ttk.Label(main_frame, text="Old Password:").grid(row=0, column=0, sticky="w", pady=5); ttk.Entry(main_frame, textvariable=self.old_pass_var, show="*").grid(row=0, column=1, pady=5); ttk.Label(main_frame, text="New Password:").grid(row=1, column=0, sticky="w", pady=5); ttk.Entry(main_frame, textvariable=self.new_pass_var, show="*").grid(row=1, column=1, pady=5); ttk.Label(main_frame, text="Confirm New Password:").grid(row=2, column=0, sticky="w", pady=5); ttk.Entry(main_frame, textvariable=self.confirm_pass_var, show="*").grid(row=2, column=1, pady=5); ttk.Button(main_frame, text="Save Changes", command=self.save_new_password, bootstyle="primary").grid(row=3, columnspan=2, pady=10); self.transient(parent); self.grab_set(); self.focus_set()
    def save_new_password(self):
        old_pass = self.old_pass_var.get(); new_pass = self.new_pass_var.get(); confirm_pass = self.confirm_pass_var.get()
        if not all([old_pass, new_pass, confirm_pass]): messagebox.showerror("Error", "All fields are required.", parent=self); return
        if not self.db_controller.verify_user(self.username, old_pass): messagebox.showerror("Error", "Old password is not correct.", parent=self); return
        if new_pass != confirm_pass: messagebox.showerror("Error", "New passwords do not match.", parent=self); return
        if len(new_pass) < 4: messagebox.showwarning("Warning", "Password should be at least 4 characters long.", parent=self); return
        self.db_controller.change_password(self.username, new_pass); messagebox.showinfo("Success", "Password changed successfully.", parent=self); self.destroy()

class PnLDateSelectionWindow(tk.Toplevel):
    def __init__(self, parent, db_controller):
        super().__init__(parent); self.title("Generate P&L Statement"); self.db_controller = db_controller; today = datetime.now().date(); self.start_date_var = tk.StringVar(value=(today.replace(day=1)).strftime('%Y-%m-%d')); self.end_date_var = tk.StringVar(value=today.strftime('%Y-%m-%d')); main_frame = ttk.Frame(self, padding=20); main_frame.pack(fill="both", expand=True); ttk.Label(main_frame, text="Select Period for Report", font=("Arial", 14)).grid(row=0, column=0, columnspan=3, pady=(0,15)); ttk.Label(main_frame, text="Start Date:").grid(row=1, column=0, sticky="w"); ttk.Entry(main_frame, textvariable=self.start_date_var).grid(row=1, column=1); ttk.Button(main_frame, text="📅", width=3, command=lambda: CalendarPopup(self, self.start_date_var)).grid(row=1, column=2, padx=5); ttk.Label(main_frame, text="End Date:").grid(row=2, column=0, sticky="w", pady=5); ttk.Entry(main_frame, textvariable=self.end_date_var).grid(row=2, column=1, pady=5); ttk.Button(main_frame, text="📅", width=3, command=lambda: CalendarPopup(self, self.end_date_var)).grid(row=2, column=2, padx=5); ttk.Button(main_frame, text="Generate Report", command=self.generate, bootstyle="primary").grid(row=3, column=1, columnspan=2, pady=10); self.transient(parent); self.grab_set(); self.wait_window()
    def generate(self):
        start_date = self.start_date_var.get(); end_date = self.end_date_var.get(); total_revenue = self.db_controller.execute_query("SELECT SUM(total_amount) FROM nagad_khata WHERE date BETWEEN ? AND ?", (start_date, end_date), fetch="one")[0] or 0; daily_expenses = self.db_controller.execute_query("SELECT category, SUM(amount) FROM daily_expenses WHERE expense_date BETWEEN ? AND ? GROUP BY category", (start_date, end_date), fetch="all") or []; salary_expenses = self.db_controller.execute_query("SELECT SUM(paid_amount) FROM salary_payments WHERE payment_date BETWEEN ? AND ?", (start_date, end_date), fetch="one")[0] or 0; contractor_expenses = self.db_controller.execute_query("SELECT SUM(amount) FROM contractor_payments WHERE payment_date BETWEEN ? AND ?", (start_date, end_date), fetch="one")[0] or 0
        expenses_by_cat = {cat: amt for cat, amt in daily_expenses};
        if salary_expenses > 0: expenses_by_cat['Salary (Monthly Staff)'] = salary_expenses
        if contractor_expenses > 0: expenses_by_cat['Contractual Labor'] = contractor_expenses
        revenue_data = {'total_revenue': total_revenue}; expense_data = {'total_expenses': sum(expenses_by_cat.values()), 'by_category': expenses_by_cat}
        try:
            pdf_path = LedgerService.generate_pnl_pdf(start_date, end_date, revenue_data, expense_data)
            if messagebox.askyesno("Success", f"PDF statement created:\n{os.path.abspath(pdf_path)}\n\nDo you want to open it?"):
                if sys.platform == "win32": os.startfile(os.path.abspath(pdf_path))
                else: subprocess.call(["open", os.path.abspath(pdf_path)])
            self.destroy()
        except Exception as e: messagebox.showerror("PDF Error", f"Failed to generate PDF: {e}", parent=self)

class MainApplication(ttk.Frame):
    def __init__(self, container, db_controller):
        super().__init__(container); self.db_controller = db_controller
        main_frame = ttk.Frame(self, padding="10"); main_frame.pack(expand=True, fill="both")
        self.notebook = ttk.Notebook(main_frame, bootstyle="primary"); self.notebook.pack(expand=True, fill="both")
        self.dashboard_tab = Dashboard(self.notebook, self.db_controller); self.insights_tab = InsightsTab(self.notebook, self.db_controller); self.customers_tab = CustomersTab(self.notebook, self.db_controller); self.baki_khata_tab = BakiKhataTab(self.notebook, self.db_controller)
        self.nagad_khata_tab = NagadKhataTab(self.notebook, self.db_controller, baki_khata_refresh_callback=self.baki_khata_tab.refresh_data)
        self.ledger_book_tab = LedgerKhataTab(self.notebook, self.db_controller); self.salary_tab = SalaryTab(self.notebook, self.db_controller); self.expenses_tab = DailyExpensesTab(self.notebook, self.db_controller)
        self.notebook.add(self.dashboard_tab, text="Dashboard"); self.notebook.add(self.insights_tab, text="Insights"); self.notebook.add(self.customers_tab, text="Customers"); self.notebook.add(self.nagad_khata_tab, text="Nagad Khata"); self.notebook.add(self.baki_khata_tab, text="Baki Khata (Dues)"); self.notebook.add(self.ledger_book_tab, text="Ledger Book"); self.notebook.add(self.salary_tab, text="Salary"); self.notebook.add(self.expenses_tab, text="Daily Expenses")
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
    # --- main.py ---
# In the MainApplication class...

    def on_tab_changed(self, event):
        try:
            selected_tab_index = self.notebook.index(self.notebook.select())
            if selected_tab_index == 0: self.dashboard_tab.refresh_data()
            elif selected_tab_index == 1: self.insights_tab.refresh_data()
            elif selected_tab_index == 2: self.customers_tab.refresh_data()
            # MODIFIED: Ensure you are calling the correct refresh method for Baki Khata
            elif selected_tab_index == 4: self.baki_khata_tab.refresh_data() 
            elif selected_tab_index == 5: self.ledger_book_tab.refresh_data()
            elif selected_tab_index == 6: self.salary_tab.refresh_data()
            elif selected_tab_index == 7: self.expenses_tab.refresh_data()
        except tk.TclError:
            pass # Tab is being switched, can ignore this error

# <<-- MODIFIED: The main AppController now uses ttkbootstrap -->>
class AppController(ttk.Window):
    def __init__(self, db_controller):
        # Use a theme from ttkbootstrap, e.g., "superhero" (dark) or "litera" (light)
        super().__init__(themename="superhero")
        self.db_controller = db_controller; self.title("Molla Bricks App"); self.geometry("1300x750")
        self.current_user = None
        self.container = ttk.Frame(self); self.container.pack(expand=True, fill="both"); self.container.grid_rowconfigure(0, weight=1); self.container.grid_columnconfigure(0, weight=1)
        self.login_frame = LoginFrame(self.container, self.db_controller, self.show_main_app); self.login_frame.grid(row=0, column=0, sticky="nsew")
        self.main_app_frame = None; self.protocol("WM_DELETE_WINDOW", self.on_closing)
    def show_main_app(self, username):
        self.current_user = username; self.login_frame.destroy(); self.main_app_frame = MainApplication(self.container, self.db_controller); self.main_app_frame.grid(row=0, column=0, sticky="nsew"); self.config(menu=self.create_menu())
        self.run_background_tasks()
    def create_menu(self):
        menubar = tk.Menu(self); file_menu = tk.Menu(menubar, tearoff=0); file_menu.add_command(label="Backup Database", command=self.backup_database); file_menu.add_command(label="Change Password...", command=self.open_change_password_window); file_menu.add_separator(); file_menu.add_command(label="Exit", command=self.on_closing); menubar.add_cascade(label="File", menu=file_menu)
        reports_menu = tk.Menu(menubar, tearoff=0); reports_menu.add_command(label="Profit & Loss Statement...", command=self.open_pnl_report_window); menubar.add_cascade(label="Reports", menu=reports_menu)
        manage_menu = tk.Menu(menubar, tearoff=0); manage_menu.add_command(label="Brick Types...", command=self.open_brick_type_manager); manage_menu.add_command(label="Expense Categories...", command=self.open_expense_category_manager); manage_menu.add_separator(); manage_menu.add_command(label="Reset Chalan Sequence...", command=self.reset_chalan_sequence); menubar.add_cascade(label="Manage", menu=manage_menu)
        return menubar
    def run_background_tasks(self):
        def _train_ai():
            try: ai_service = AIService(self.db_controller); results = ai_service.train_all_models(); self.db_controller.set_setting('last_ai_train_timestamp', datetime.now().isoformat()); print(f"Automatic AI Training complete: {results}")
            except Exception as e: print(f"Automatic AI training failed: {e}")
        last_train_str = self.db_controller.get_setting('last_ai_train_timestamp'); needs_training = True
        if last_train_str:
            last_train_time = datetime.fromisoformat(last_train_str)
            if (datetime.now() - last_train_time) < timedelta(days=7): needs_training = False
        if needs_training:
            training_thread = threading.Thread(target=_train_ai, daemon=True); training_thread.start()
    def on_closing(self):
        try:
            last_backup_str = self.db_controller.get_setting('last_auto_backup_timestamp'); needs_backup = True
            if last_backup_str:
                last_backup_time = datetime.fromisoformat(last_backup_str)
                if (datetime.now() - last_backup_time) < timedelta(hours=23): needs_backup = False
            if needs_backup:
                path, _ = self.db_controller.backup_db()
                if path: self.db_controller.set_setting('last_auto_backup_timestamp', datetime.now().isoformat()); print(f"Automatic backup created at: {path}")
        except Exception as e: print(f"Automatic backup failed: {e}")
        if messagebox.askokcancel("Quit", "Do you want to exit MollaBricksApp?"): self.destroy()
    def open_pnl_report_window(self): PnLDateSelectionWindow(self, self.db_controller)
    def open_change_password_window(self): ChangePasswordWindow(self, self.db_controller, self.current_user)
    def open_brick_type_manager(self): BrickTypeManagerWindow(self, self.db_controller, self.main_app_frame.nagad_khata_tab.fetch_and_update_brick_types)
    def open_expense_category_manager(self): ExpenseCategoryManagerWindow(self, self.db_controller, self.main_app_frame.expenses_tab.fetch_and_update_categories)
    def reset_chalan_sequence(self):
        if messagebox.askyesno("Confirm New Chalan Book", "Are you sure?"):
            last_id = self.db_controller.execute_query("SELECT MAX(id) FROM nagad_khata", fetch="one")[0] or 0
            self.db_controller.set_setting('chalan_reset_marker_id', last_id); self.main_app_frame.nagad_khata_tab.refresh_data(); messagebox.showinfo("Success", "Chalan sequence has been reset.")
    def backup_database(self):
        path, msg = self.db_controller.backup_db();
        if path: messagebox.showinfo("Success", f"{msg}\nBackup saved to: {os.path.abspath(path)}")
        else: messagebox.showerror("Backup Failed", msg)

if __name__ == '__main__':
    db_controller_instance = None
    try:
        db_controller_instance = DBController(); app = AppController(db_controller_instance); app.mainloop()
    except Exception as e:
        logging.basicConfig(filename='molla_bricks/logs/app_error.log', level=logging.CRITICAL)
        logging.critical(f"Application failed to start: {e}", exc_info=True); messagebox.showerror("Application Error", f"A critical error occurred: {e}\nSee logs for details.")
    finally:
        if db_controller_instance: db_controller_instance.close_connection()