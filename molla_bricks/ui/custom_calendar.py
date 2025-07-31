# molla_bricks/ui/custom_calendar.py
import tkinter as tk
from tkinter import ttk
import calendar
from datetime import datetime

class CalendarPopup(tk.Toplevel):
    def __init__(self, parent, date_var):
        super().__init__(parent)
        self.transient(parent)
        self.title("Select Date")
        self.date_var = date_var
        
        self.today = datetime.now()
        self.cal = calendar.Calendar()
        self.year = self.today.year
        self.month = self.today.month

        self.create_widgets()
        self.update_calendar()

        # Center the popup on the parent window
        self.grab_set() # Make the popup modal
        self.wait_window()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding=5)
        main_frame.pack(expand=True, fill="both")

        header_frame = ttk.Frame(main_frame)
        header_frame.pack(pady=5)

        ttk.Button(header_frame, text="<", command=self.prev_month, width=3).pack(side="left")
        self.month_year_label = ttk.Label(header_frame, text="", font=("Arial", 12, "bold"), width=15, anchor="center")
        self.month_year_label.pack(side="left", padx=5)
        ttk.Button(header_frame, text=">", command=self.next_month, width=3).pack(side="left")

        self.days_frame = ttk.Frame(main_frame)
        self.days_frame.pack()
        
        # Weekday headers
        weekdays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        for i, day in enumerate(weekdays):
            ttk.Label(self.days_frame, text=day, font=("Arial", 9, "bold")).grid(row=0, column=i, padx=2, pady=2)

    def update_calendar(self):
        # Clear old day buttons
        for widget in self.days_frame.winfo_children():
            if widget.grid_info()['row'] > 0: # Avoid destroying weekday labels
                widget.destroy()

        self.month_year_label['text'] = f"{calendar.month_name[self.month]} {self.year}"
        month_days = self.cal.monthdayscalendar(self.year, self.month)

        for r, week in enumerate(month_days, 1):
            for c, day in enumerate(week):
                if day != 0:
                    btn = ttk.Button(self.days_frame, text=str(day), width=4,
                                     command=lambda d=day: self.select_date(d))
                    btn.grid(row=r, column=c, padx=2, pady=2)

    def select_date(self, day):
        selected_date = f"{self.year}-{self.month:02d}-{day:02d}"
        self.date_var.set(selected_date)
        self.destroy()

    def next_month(self):
        self.month += 1
        if self.month > 12:
            self.month = 1
            self.year += 1
        self.update_calendar()

    def prev_month(self):
        self.month -= 1
        if self.month < 1:
            self.month = 12
            self.year -= 1
        self.update_calendar()