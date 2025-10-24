# molla_bricks/core/db/db_controller.py
import sqlite3, os, shutil
from datetime import datetime
import logging, traceback, hashlib

os.makedirs('molla_bricks/logs', exist_ok=True)
logging.basicConfig(filename='molla_bricks/logs/db_log.txt', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
LATEST_DB_VERSION = 16 # <-- UPDATED to 16

class DBController:
    def __init__(self, db_path='data/app_data.db'):
        os.makedirs(os.path.dirname(db_path), exist_ok=True); self.db_path = db_path; self.conn = None
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.execute("PRAGMA foreign_keys = 1"); logging.info(f"Successfully connected to database at {self.db_path}"); self._run_migrations()
        except sqlite3.Error as e: logging.error(f"Error connecting to database: {e}"); print(f"Error connecting to database: {e}")

    def execute_query(self, query, params=(), fetch=None):
        try:
            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute(query, params)
                if query.strip().upper().startswith('INSERT'): return cursor.lastrowid
                if query.strip().upper().startswith(('UPDATE', 'DELETE')): return cursor.rowcount
                if fetch == 'one': return cursor.fetchone()
                elif fetch == 'all': return cursor.fetchall()
        except sqlite3.Error as e: logging.error(f"Query Failed: {query} | Params: {params} | Error: {e}"); logging.error(traceback.format_exc()); return None

    def _run_migrations(self):
        self.execute_query("CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT);")
        current_version = int(self.get_setting('db_version', 0))
        if current_version >= LATEST_DB_VERSION: logging.info("Database is up to date."); return
        logging.info(f"DB requires migration. Current: {current_version}, Target: {LATEST_DB_VERSION}")
        
        if current_version < 1: self._migrate_to_v1_base_tables()
        if current_version < 2: self._migrate_to_v2_brick_types()
        if current_version < 3: self._migrate_to_v3_expenses()
        if current_version < 4: self._migrate_to_v4_staff()
        if current_version < 5: self._migrate_to_v5_users()
        if current_version < 6: self._migrate_to_v6_customers()
        if current_version < 7: self._migrate_to_v7_customer_fk()
        if current_version < 8: self._migrate_to_v8_customer_phone_fix()
        if current_version < 9: self._migrate_to_v9_contractors()
        if current_version < 10: self._migrate_to_v10_financial_year()
        if current_version < 11: self._migrate_to_v11_production_modules()
        if current_version < 12: self._migrate_to_v12_owner_module()
        if current_version < 13: self._migrate_to_v13_accounts_modules()
        if current_version < 14: self._migrate_to_v14_coal_module()
        if current_version < 15: self._migrate_to_v15_brick_types_expansion()
        if current_version < 16: self._migrate_to_v16_sales_invoice() # <-- NEW
        
        logging.info("All migrations applied successfully.")
        
    def _update_db_version(self, version): self.set_setting('db_version', version); logging.info(f"Upgraded database to version {version}")
    
    # --- All previous migrations are unchanged ---
    def _migrate_to_v1_base_tables(self):
        self.execute_query("CREATE TABLE IF NOT EXISTS nagad_khata (id INTEGER PRIMARY KEY, date TEXT, chalan_no TEXT, customer_name TEXT, address TEXT, vehicle_no TEXT, brick_type TEXT, brick_amount INTEGER, rate REAL, total_amount REAL, paid_amount REAL, due_amount REAL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP);")
        self.execute_query("CREATE TABLE IF NOT EXISTS ledger_book (id INTEGER PRIMARY KEY, date TEXT, party_name TEXT, description TEXT, credit REAL DEFAULT 0, debit REAL DEFAULT 0, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP);")
        self._update_db_version(1)
    def _migrate_to_v2_brick_types(self):
        self.execute_query("CREATE TABLE IF NOT EXISTS brick_types (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);")
        if self.execute_query("SELECT COUNT(id) FROM brick_types", fetch="one")[0] == 0:
            for item in [("Class 1",), ("Class 2",), ("Picket",)]: self.execute_query("INSERT INTO brick_types (name) VALUES (?)", item)
        self._update_db_version(2)
    def _migrate_to_v3_expenses(self):
        self.execute_query("CREATE TABLE IF NOT EXISTS expense_categories (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);")
        if self.execute_query("SELECT COUNT(id) FROM expense_categories", fetch="one")[0] == 0:
            for item in [("Fuel",), ("Office Supplies",), ("Maintenance",)]: self.execute_query("INSERT INTO expense_categories (name) VALUES (?)", item)
        self.execute_query("CREATE TABLE IF NOT EXISTS daily_expenses (id INTEGER PRIMARY KEY, expense_date TEXT NOT NULL, category TEXT NOT NULL, description TEXT, amount REAL NOT NULL);")
        self._update_db_version(3)
    def _migrate_to_v4_staff(self):
        self.execute_query("CREATE TABLE IF NOT EXISTS staff (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, monthly_salary REAL NOT NULL DEFAULT 0);")
        self.execute_query("CREATE TABLE IF NOT EXISTS salary_payments (id INTEGER PRIMARY KEY, staff_id INTEGER NOT NULL, payment_date TEXT NOT NULL, paid_amount REAL NOT NULL, notes TEXT, FOREIGN KEY (staff_id) REFERENCES staff (id) ON DELETE CASCADE);")
        self._update_db_version(4)
    def _migrate_to_v5_users(self):
        self.execute_query("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'admin');")
        if self.execute_query("SELECT COUNT(id) FROM users", fetch="one")[0] == 0: self.execute_query("INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'admin')", ('admin', self._hash_password('admin')))
        self._update_db_version(5)
    def _migrate_to_v6_customers(self):
        self.execute_query("CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY, name TEXT NOT NULL, address TEXT, phone TEXT UNIQUE);")
        self._update_db_version(6)
    def _migrate_to_v7_customer_fk(self):
        try: self.execute_query("ALTER TABLE nagad_khata ADD COLUMN customer_id INTEGER REFERENCES customers(id) ON DELETE SET NULL;")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e): raise e
        self._update_db_version(7)
    def _migrate_to_v8_customer_phone_fix(self):
        try:
            self.execute_query("BEGIN TRANSACTION;"); self.execute_query("ALTER TABLE customers RENAME TO customers_old;"); self.execute_query("CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT NOT NULL, address TEXT, phone TEXT);"); self.execute_query("INSERT INTO customers (id, name, address, phone) SELECT id, name, address, phone FROM customers_old;"); self.execute_query("DROP TABLE customers_old;"); self.execute_query("COMMIT;")
        except Exception as e:
            self.execute_query("ROLLBACK;");
            if "no such table: customers_old" not in str(e) and "no such table: customers" not in str(e): raise e
        self._update_db_version(8)
    def _migrate_to_v9_contractors(self):
        self.execute_query("CREATE TABLE IF NOT EXISTS contractors (id INTEGER PRIMARY KEY, name TEXT NOT NULL, section TEXT NOT NULL, phone TEXT, UNIQUE(name, section));")
        self.execute_query("CREATE TABLE IF NOT EXISTS contractor_payments (id INTEGER PRIMARY KEY, contractor_id INTEGER NOT NULL, payment_date TEXT NOT NULL, amount REAL NOT NULL, description TEXT, FOREIGN KEY (contractor_id) REFERENCES contractors (id) ON DELETE CASCADE);")
        self._update_db_version(9)
    def _migrate_to_v10_financial_year(self):
        self.execute_query("CREATE TABLE IF NOT EXISTS financial_year_end (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, status TEXT, customer_left REAL DEFAULT 0, cash_in_hand REAL DEFAULT 0, cash_in_bank REAL DEFAULT 0, cash_in_mobile REAL DEFAULT 0, supplier_payable REAL DEFAULT 0, cost REAL DEFAULT 0, owner_provided REAL DEFAULT 0, owner_accepted REAL DEFAULT 0, description TEXT, start_date TEXT, end_date TEXT);")
        self._update_db_version(10)
    def _migrate_to_v11_production_modules(self):
        self.execute_query("CREATE TABLE IF NOT EXISTS pot_entries (id INTEGER PRIMARY KEY, date TEXT NOT NULL, pot_name TEXT NOT NULL, mill_number INTEGER, quantity_shaped INTEGER, status TEXT, notes TEXT)"); self.execute_query("CREATE TABLE IF NOT EXISTS round_entries (id INTEGER PRIMARY KEY, date TEXT NOT NULL, round_name TEXT NOT NULL, pot_id INTEGER, bricks_loaded INTEGER, coal_cost REAL, firing_status TEXT, notes TEXT, FOREIGN KEY (pot_id) REFERENCES pot_entries(id))"); self.execute_query("CREATE TABLE IF NOT EXISTS load_unload (id INTEGER PRIMARY KEY, date TEXT NOT NULL, type TEXT NOT NULL, chalan_no TEXT, brick_type TEXT, quantity INTEGER, rate REAL, total_cost REAL, contractor_name TEXT)"); self.execute_query("CREATE TABLE IF NOT EXISTS owner_cash (id INTEGER PRIMARY KEY, date TEXT NOT NULL, type TEXT NOT NULL, description TEXT, amount REAL)")
        self._update_db_version(11)
    def _migrate_to_v12_owner_module(self):
        self.execute_query("CREATE TABLE IF NOT EXISTS owners (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, phone TEXT, email TEXT, address TEXT, status TEXT);")
        if self.execute_query("SELECT COUNT(id) FROM owners", fetch="one")[0] == 0:
            self.execute_query("INSERT INTO owners (name, phone, email, address, status) VALUES (?, ?, ?, ?, ?)", ('CEO', '01512345678', 'ceo@email.com', 'Nikunja 2', 'Active'))
        try: self.execute_query("ALTER TABLE owner_cash ADD COLUMN voucher_no TEXT;")
        except: pass
        try: self.execute_query("ALTER TABLE owner_cash ADD COLUMN owner_id INTEGER REFERENCES owners(id);")
        except: pass
        try: self.execute_query("ALTER TABLE owner_cash ADD COLUMN payment_method TEXT;")
        except: pass
        try: self.execute_query("ALTER TABLE owner_cash ADD COLUMN account TEXT;")
        except: pass
        self._update_db_version(12)
    def _migrate_to_v13_accounts_modules(self):
        self.execute_query("CREATE TABLE IF NOT EXISTS chart_of_accounts (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, type TEXT NOT NULL, description TEXT)"); self.execute_query("CREATE TABLE IF NOT EXISTS bank_accounts (id INTEGER PRIMARY KEY, bank_name TEXT NOT NULL, account_name TEXT NOT NULL UNIQUE, account_number TEXT, branch TEXT, balance REAL DEFAULT 0)"); self.execute_query("CREATE TABLE IF NOT EXISTS mobile_bank_accounts (id INTEGER PRIMARY KEY, provider_name TEXT NOT NULL, account_name TEXT NOT NULL UNIQUE, account_number TEXT, balance REAL DEFAULT 0)")
        self._update_db_version(13)
    def _migrate_to_v14_coal_module(self):
        self.execute_query("CREATE TABLE IF NOT EXISTS coal_sectors (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)"); self.execute_query("CREATE TABLE IF NOT EXISTS coal_sub_sectors (id INTEGER PRIMARY KEY, name TEXT NOT NULL, sector_id INTEGER NOT NULL, FOREIGN KEY (sector_id) REFERENCES coal_sectors(id) ON DELETE CASCADE)"); self.execute_query("CREATE TABLE IF NOT EXISTS coal_purchases (id INTEGER PRIMARY KEY, date TEXT NOT NULL, fiscal_year TEXT, voucher_no TEXT, sector TEXT, sub_sector TEXT, quantity REAL, rate REAL, total REAL, notes TEXT)")
        self._update_db_version(14)
    def _migrate_to_v15_brick_types_expansion(self):
        try: self.execute_query("ALTER TABLE brick_types ADD COLUMN product_code TEXT;")
        except: pass
        try: self.execute_query("ALTER TABLE brick_types ADD COLUMN category TEXT;")
        except: pass
        try: self.execute_query("ALTER TABLE brick_types ADD COLUMN unit TEXT;")
        except: pass
        try: self.execute_query("ALTER TABLE brick_types ADD COLUMN status TEXT DEFAULT 'Active';")
        except: pass
        try: self.execute_query("ALTER TABLE brick_types ADD COLUMN photo_path TEXT;")
        except: pass
        try: self.execute_query("ALTER TABLE brick_types ADD COLUMN made_by TEXT;")
        except: pass
        self._update_db_version(15)

    # --- NEW: Migration for Sales Invoices ---
    def _migrate_to_v16_sales_invoice(self):
        self.execute_query("""
            CREATE TABLE IF NOT EXISTS sales_invoices (
                id INTEGER PRIMARY KEY,
                invoice_no TEXT NOT NULL UNIQUE,
                sale_date TEXT NOT NULL,
                party_id INTEGER NOT NULL,
                vehicle_no TEXT,
                total REAL,
                paid REAL,
                due REAL,
                notes TEXT,
                status TEXT,
                FOREIGN KEY (party_id) REFERENCES customers(id)
            )
        """)
        self.execute_query("""
            CREATE TABLE IF NOT EXISTS sales_items (
                id INTEGER PRIMARY KEY,
                invoice_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                product_name TEXT,
                quantity INTEGER,
                rate REAL,
                subtotal REAL,
                FOREIGN KEY (invoice_id) REFERENCES sales_invoices(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES brick_types(id)
            )
        """)
        self._update_db_version(16)
        
    def get_setting(self, key, default=None): result = self.execute_query("SELECT value FROM app_settings WHERE key = ?", (key,), fetch="one"); return result[0] if result else default
    def set_setting(self, key, value): self.execute_query("INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)", (key, str(value)))
    def _hash_password(self, password): return hashlib.sha256(password.encode('utf-8')).hexdigest()
    def verify_user(self, username, password): user = self.execute_query("SELECT password_hash FROM users WHERE username = ?", (username,), fetch="one"); return user and user[0] == self._hash_password(password)
    def change_password(self, username, new_password): self.execute_query("UPDATE users SET password_hash = ? WHERE username = ?", (self._hash_password(new_password), username))
    def backup_db(self, backup_dir='molla_bricks/backups/'):
        os.makedirs(backup_dir, exist_ok=True); timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S'); backup_path = os.path.join(backup_dir, f'backup_{timestamp}.db')
        try: shutil.copy2(self.db_path, backup_path); return backup_path, "Backup successful!"
        except Exception as e: return None, f"Backup failed: {e}"
    def close_connection(self):
        if self.conn: self.conn.close()