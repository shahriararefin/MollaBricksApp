# molla_bricks/ui/views/insights_tab.py
import tkinter as tk
from tkinter import ttk, messagebox

class InsightsTab(ttk.Frame):
    def __init__(self, parent, db_controller):
        super().__init__(parent, padding=15)
        self.db_controller = db_controller
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(expand=True, fill="both")

        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(header_frame, text="Customer Insights", font=("Arial", 20, "bold")).pack(side="left")
        ttk.Button(header_frame, text="🔄 Refresh Data", command=self.refresh_data).pack(side="right")
        
        # Grid for the two report frames
        reports_frame = ttk.Frame(main_frame)
        reports_frame.pack(fill="both", expand=True)
        reports_frame.grid_columnconfigure(0, weight=1)
        reports_frame.grid_columnconfigure(1, weight=1)

        # --- Most Valuable Customers ---
        valuable_frame = ttk.LabelFrame(reports_frame, text="Top 5 Most Valuable Customers (by Total Spent)", padding=10)
        valuable_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        valuable_frame.grid_rowconfigure(0, weight=1)
        valuable_frame.grid_columnconfigure(0, weight=1)

        valuable_cols = ("rank", "name", "total_spent")
        self.valuable_tree = ttk.Treeview(valuable_frame, columns=valuable_cols, show="headings")
        self.valuable_tree.heading("rank", text="Rank")
        self.valuable_tree.column("rank", width=50, anchor="center")
        self.valuable_tree.heading("name", text="Customer Name")
        self.valuable_tree.heading("total_spent", text="Total Amount Spent (BDT)")
        self.valuable_tree.column("total_spent", anchor="e")
        self.valuable_tree.grid(row=0, column=0, sticky="nsew")
        
        # --- Most Frequent Customers ---
        frequent_frame = ttk.LabelFrame(reports_frame, text="Top 5 Most Frequent Customers (by No. of Sales)", padding=10)
        frequent_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        frequent_frame.grid_rowconfigure(0, weight=1)
        frequent_frame.grid_columnconfigure(0, weight=1)

        frequent_cols = ("rank", "name", "sales_count")
        self.frequent_tree = ttk.Treeview(frequent_frame, columns=frequent_cols, show="headings")
        self.frequent_tree.heading("rank", text="Rank")
        self.frequent_tree.column("rank", width=50, anchor="center")
        self.frequent_tree.heading("name", text="Customer Name")
        self.frequent_tree.heading("sales_count", text="Number of Sales")
        self.frequent_tree.column("sales_count", anchor="center")
        self.frequent_tree.grid(row=0, column=0, sticky="nsew")

    def refresh_data(self):
        self._update_top_valuable()
        self._update_top_frequent()

    def _update_top_valuable(self):
        for item in self.valuable_tree.get_children(): self.valuable_tree.delete(item)
        
        query = """
            SELECT customer_name, SUM(total_amount) as total_spent
            FROM nagad_khata
            WHERE customer_id IS NOT NULL
            GROUP BY customer_id
            ORDER BY total_spent DESC
            LIMIT 5;
        """
        records = self.db_controller.execute_query(query, fetch="all")
        if records:
            for i, row in enumerate(records, 1):
                name, total_spent = row
                self.valuable_tree.insert("", "end", values=(f"#{i}", name, f"{total_spent:,.2f}"))

    def _update_top_frequent(self):
        for item in self.frequent_tree.get_children(): self.frequent_tree.delete(item)
        
        query = """
            SELECT customer_name, COUNT(id) as sales_count
            FROM nagad_khata
            WHERE customer_id IS NOT NULL
            GROUP BY customer_id
            ORDER BY sales_count DESC
            LIMIT 5;
        """
        records = self.db_controller.execute_query(query, fetch="all")
        if records:
            for i, row in enumerate(records, 1):
                name, sales_count = row
                self.frequent_tree.insert("", "end", values=(f"#{i}", name, sales_count))