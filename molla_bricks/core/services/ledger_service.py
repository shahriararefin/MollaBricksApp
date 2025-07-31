# molla_bricks/core/services/ledger_service.py
import os, csv, re
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors

class LedgerService:
    @staticmethod
    def generate_ledger_pdf(party_name, start_date, end_date, opening_balance, transactions):
        # This function is unchanged and correct
        os.makedirs("reports", exist_ok=True)
        safe_party_name = "".join(c for c in party_name if c.isalnum())
        file_path = f"reports/statement_{safe_party_name}_{datetime.now().strftime('%Y%m%d')}.pdf"
        c = canvas.Canvas(file_path, pagesize=letter); width, height = letter; y = height - 0.75 * inch
        c.setFont("Helvetica-Bold", 18); c.drawCentredString(width / 2.0, y, "Statement of Account"); y -= 0.3 * inch
        c.setFont("Helvetica", 12); c.drawCentredString(width / 2.0, y, f"Party: {party_name}"); y -= 0.2 * inch
        c.drawCentredString(width / 2.0, y, f"Period: {start_date} to {end_date}"); y -= 0.5 * inch
        table_data = [["Date", "Description", "Bill (Debit)", "Paid (Credit)", "Balance"]]
        table_data.append(["", "Opening Balance", "", "", f"{opening_balance:,.2f}"])
        running_balance = opening_balance; total_debit = 0; total_credit = 0
        for row in transactions:
            credit = row[2]; debit = row[3]; running_balance += credit - debit; total_credit += credit; total_debit += debit
            clean_description = re.sub(r'\[.*?\]', '', row[1]).strip()
            formatted_row = [row[0], clean_description, f"{debit:,.2f}" if debit > 0 else "", f"{credit:,.2f}" if credit > 0 else "", f"{running_balance:,.2f}"]
            table_data.append(formatted_row)
        table_data.append(["", "Totals for Period:", f"{total_debit:,.2f}", f"{total_credit:,.2f}", ""])
        table_data.append(["", "Closing Balance:", "", "", f"{running_balance:,.2f}"])
        t = Table(table_data, colWidths=[1*inch, 3.5*inch, 1*inch, 1*inch, 1*inch])
        style = TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey),('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),('ALIGN', (0, 0), (-1, -1), 'LEFT'),('ALIGN', (2, 0), (-1, -1), 'RIGHT'),('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),('GRID', (0, 0), (-1, -1), 1, colors.black),('BACKGROUND', (0, -2), (-1, -1), colors.lightgrey),('FONTNAME', (0, -2), (-1, -1), 'Helvetica-Bold'),('SPAN', (0, -1), (1, -1))])
        t.setStyle(style); t.wrapOn(c, width, height); t.drawOn(c, 0.5*inch, y - (len(table_data) * 0.25 * inch)); c.save(); return file_path

    # <<-- NEW: Function to generate a detailed Profit & Loss Statement PDF -->>
    @staticmethod
    def generate_pnl_pdf(start_date, end_date, revenue_data, expense_data):
        os.makedirs("reports", exist_ok=True)
        file_path = f"reports/pnl_statement_{start_date}_to_{end_date}.pdf"
        
        c = canvas.Canvas(file_path, pagesize=letter)
        width, height = letter
        y = height - 0.75 * inch

        # --- Header ---
        c.setFont("Helvetica-Bold", 18); c.drawCentredString(width / 2.0, y, "Profit & Loss Statement"); y -= 0.3 * inch
        c.setFont("Helvetica", 12); c.drawCentredString(width / 2.0, y, f"Period: {start_date} to {end_date}"); y -= 0.6 * inch

        total_revenue = revenue_data['total_revenue']
        total_expenses = expense_data['total_expenses']
        net_profit = total_revenue - total_expenses
        
        # --- Revenue Section ---
        c.setFont("Helvetica-Bold", 14); c.drawString(inch, y, "Revenue"); y -= 0.3 * inch
        c.line(inch, y + 0.05 * inch, width - inch, y + 0.05 * inch)
        c.setFont("Helvetica", 11)
        c.drawString(inch * 1.2, y, "Total Sales Revenue"); c.drawRightString(width - inch, y, f"{total_revenue:,.2f}"); y -= 0.4 * inch
        c.setFont("Helvetica-Bold", 11)
        c.drawString(inch * 1.2, y, "Total Revenue"); c.drawRightString(width - inch, y, f"{total_revenue:,.2f}"); y -= 0.6 * inch

        # --- Expenses Section ---
        c.setFont("Helvetica-Bold", 14); c.drawString(inch, y, "Expenses"); y -= 0.3 * inch
        c.line(inch, y + 0.05 * inch, width - inch, y + 0.05 * inch)
        c.setFont("Helvetica", 11)
        
        for category, amount in expense_data['by_category'].items():
            c.drawString(inch * 1.2, y, category); c.drawRightString(width - inch, y, f"{amount:,.2f}"); y -= 0.25 * inch
        
        y -= 0.15 * inch
        c.setFont("Helvetica-Bold", 11)
        c.drawString(inch * 1.2, y, "Total Expenses"); c.drawRightString(width - inch, y, f"{total_expenses:,.2f}"); y -= 0.6 * inch

        # --- Net Profit/Loss Section ---
        c.line(inch, y, width - inch, y)
        y -= 0.4 * inch
        c.setFont("Helvetica-Bold", 14)
        profit_text = "Net Profit" if net_profit >= 0 else "Net Loss"
        c.drawString(inch, y, profit_text)
        c.drawRightString(width - inch, y, f"{net_profit:,.2f}")

        c.save()
        return file_path

    # The export_to_csv method is unchanged
    @staticmethod
    def export_to_csv(db_controller):
        os.makedirs("exports", exist_ok=True); timestamp = datetime.now().strftime("%Y%m%d_%H%M%S"); file_path = f"exports/ledger_book_export_{timestamp}.csv"
        query = "SELECT * FROM ledger_book ORDER BY id ASC"; records = db_controller.execute_query(query, fetch="all")
        if not records: return None, "No data to export."
        header = ["id", "date", "party_name", "description", "credit", "debit", "timestamp"]
        with open(file_path, 'w', newline='', encoding='utf-8') as f: writer = csv.writer(f); writer.writerow(header); writer.writerows(records)
        return file_path, "Export successful!"