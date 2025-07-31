# molla_bricks/core/db/db_controller.py
import sqlite3, os, shutil
from datetime import datetime
import logging, traceback, hashlib

os.makedirs('molla_bricks/logs', exist_ok=True)
logging.basicConfig(filename='molla_bricks/logs/db_log.txt', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
LATEST_DB_VERSION = 9

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
        if current_version >= LATEST_DB_VERSION: return
        logging.info(f"DB requires migration. Current: {current_version}, Target: {LATEST_DB_VERSION}")
        if current_version < 8: self._migrate_to_v8()
        if current_version < 9: self._migrate_to_v9()
        logging.info("All migrations applied successfully.")
    def _update_db_version(self, version): self.set_setting('db_version', version); logging.info(f"Upgraded database to version {version}")
    def _migrate_to_v8(self):
        self.execute_query("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'admin');")
        self.execute_query("CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY, name TEXT NOT NULL, address TEXT, phone TEXT);")
        self.execute_query("CREATE TABLE IF NOT EXISTS nagad_khata (id INTEGER PRIMARY KEY, customer_id INTEGER, date TEXT, chalan_no TEXT, customer_name TEXT, address TEXT, vehicle_no TEXT, brick_type TEXT, brick_amount INTEGER, rate REAL, total_amount REAL, paid_amount REAL, due_amount REAL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE SET NULL);")
        self.execute_query("CREATE TABLE IF NOT EXISTS ledger_book (id INTEGER PRIMARY KEY, date TEXT, party_name TEXT, description TEXT, credit REAL DEFAULT 0, debit REAL DEFAULT 0, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP);")
        self.execute_query("CREATE TABLE IF NOT EXISTS brick_types (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);")
        self.execute_query("CREATE TABLE IF NOT EXISTS staff (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, monthly_salary REAL NOT NULL DEFAULT 0);")
        self.execute_query("CREATE TABLE IF NOT EXISTS salary_payments (id INTEGER PRIMARY KEY, staff_id INTEGER NOT NULL, payment_date TEXT NOT NULL, paid_amount REAL NOT NULL, notes TEXT, FOREIGN KEY (staff_id) REFERENCES staff (id) ON DELETE CASCADE);")
        self.execute_query("CREATE TABLE IF NOT EXISTS expense_categories (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);")
        self.execute_query("CREATE TABLE IF NOT EXISTS daily_expenses (id INTEGER PRIMARY KEY, expense_date TEXT NOT NULL, category TEXT NOT NULL, description TEXT, amount REAL NOT NULL);")
        if self.execute_query("SELECT COUNT(id) FROM users", fetch="one")[0] == 0: self.execute_query("INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'admin')", ('admin', self._hash_password('admin')))
        if self.execute_query("SELECT COUNT(id) FROM brick_types", fetch="one")[0] == 0:
            for item in [("Class 1",), ("Class 2",), ("Picket",)]: self.execute_query("INSERT INTO brick_types (name) VALUES (?)", item)
        if self.execute_query("SELECT COUNT(id) FROM expense_categories", fetch="one")[0] == 0:
            for item in [("Fuel",), ("Office Supplies",), ("Maintenance",)]: self.execute_query("INSERT INTO expense_categories (name) VALUES (?)", item)
        self._update_db_version(8)
    def _migrate_to_v9(self):
        self.execute_query("CREATE TABLE IF NOT EXISTS contractors (id INTEGER PRIMARY KEY, name TEXT NOT NULL, section TEXT NOT NULL, phone TEXT, UNIQUE(name, section));")
        self.execute_query("CREATE TABLE IF NOT EXISTS contractor_payments (id INTEGER PRIMARY KEY, contractor_id INTEGER NOT NULL, payment_date TEXT NOT NULL, amount REAL NOT NULL, description TEXT, FOREIGN KEY (contractor_id) REFERENCES contractors (id) ON DELETE CASCADE);")
        self._update_db_version(9)
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