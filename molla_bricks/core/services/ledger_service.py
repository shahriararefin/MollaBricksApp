# molla_bricks/core/services/ledger_service.py
import os
import csv
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch

class LedgerService:

    @staticmethod
    def generate_ledger_pdf(party_name, start_date, end_date, opening_balance, transactions):
        os.makedirs("exports/statements", exist_ok=True)
        safe_name = "".join(c for c in party_name if c.isalnum())
        file_path = os.path.abspath(f"exports/statements/statement_{safe_name}_{datetime.now().strftime('%Y%m%d')}.pdf")
        
        doc = SimpleDocTemplate(file_path, pagesize=A4, topMargin=1*inch, bottomMargin=1*inch)
        story = []
        styles = getSampleStyleSheet()
        
        story.append(Paragraph("Statement of Account", styles['h1']))
        story.append(Paragraph(f"<b>Party:</b> {party_name}", styles['h3']))
        story.append(Paragraph(f"<b>Period:</b> {start_date} to {end_date}", styles['BodyText']))
        story.append(Spacer(1, 0.25*inch))

        data = [["Date", "Description", "Debit (Bill)", "Credit (Paid)", "Balance"]]
        styles.add(ParagraphStyle(name='RightAlign', alignment=1)) # 1 = TA_RIGHT

        balance = opening_balance
        data.append(["", Paragraph("<b>Opening Balance</b>", styles['BodyText']), "", "", Paragraph(f"<b>{balance:,.2f}</b>", styles['RightAlign'])])

        for row in transactions:
            date, desc, credit, debit = row
            balance += credit - debit
            data.append([
                date,
                Paragraph(desc, styles['BodyText']),
                Paragraph(f"{debit:,.2f}", styles['RightAlign']),
                Paragraph(f"{credit:,.2f}", styles['RightAlign']),
                Paragraph(f"{balance:,.2f}", styles['RightAlign'])
            ])
        
        story.append(Spacer(1, 0.1*inch))
        data.append(["", Paragraph("<b>Closing Balance</b>", styles['BodyText']), "", "", Paragraph(f"<b>{balance:,.2f}</b>", styles['RightAlign'])])
        
        table = Table(data, colWidths=[0.8*inch, 3.7*inch, 1*inch, 1*inch, 1.2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        story.append(table)
        
        doc.build(story)
        return file_path

    @staticmethod
    def generate_pnl_pdf(start_date, end_date, revenue_data, expense_data):
        os.makedirs("exports/reports", exist_ok=True)
        file_path = os.path.abspath(f"exports/reports/pnl_{start_date}_to_{end_date}.pdf")
        
        doc = SimpleDocTemplate(file_path, pagesize=A4, topMargin=1*inch, bottomMargin=1*inch)
        story = []; styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='RightAlign', alignment=1))

        story.append(Paragraph("Profit & Loss Statement", styles['h1']))
        story.append(Paragraph(f"<b>Period:</b> {start_date} to {end_date}", styles['BodyText']))
        story.append(Spacer(1, 0.25*inch))

        story.append(Paragraph("Revenue", styles['h3']))
        revenue = revenue_data.get('total_revenue', 0)
        data = [["Description", "Amount (BDT)"], ["Total Sales Revenue", Paragraph(f"{revenue:,.2f}", styles['RightAlign'])]]
        table = Table(data, colWidths=[5*inch, 2*inch]); table.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 1, colors.black), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold')])); story.append(table)
        story.append(Spacer(1, 0.2*inch))

        story.append(Paragraph("Expenses", styles['h3']))
        data = [["Category", "Amount (BDT)"]]
        total_expenses = expense_data.get('total_expenses', 0)
        for category, amount in expense_data.get('by_category', {}).items():
            data.append([category, Paragraph(f"{amount:,.2f}", styles['RightAlign'])])
        data.append([Paragraph("<b>Total Expenses</b>", styles['BodyText']), Paragraph(f"<b>{total_expenses:,.2f}</b>", styles['RightAlign'])])
        table = Table(data, colWidths=[5*inch, 2*inch]); table.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 1, colors.black), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold')])); story.append(table)
        story.append(Spacer(1, 0.2*inch))

        net_profit = revenue - total_expenses
        profit_style = ParagraphStyle(name='Profit', fontName='Helvetica-Bold', fontSize=14, alignment=1)
        profit_text = f"Net Profit: {net_profit:,.2f} BDT"
        if net_profit < 0:
            profit_style.textColor = colors.red
            profit_text = f"Net Loss: {net_profit:,.2f} BDT"
        else:
            profit_style.textColor = colors.green
        
        story.append(Paragraph(profit_text, profit_style))
        doc.build(story); return file_path

    @staticmethod
    def export_to_csv(db_controller):
        os.makedirs("exports", exist_ok=True)
        file_path = f"exports/ledger_export_{datetime.now().strftime('%Y%m%d')}.csv"
        header = ["id", "date", "party_name", "description", "credit", "debit", "timestamp"]
        query = "SELECT * FROM ledger_book ORDER BY id DESC"
        records = db_controller.execute_query(query, fetch="all")
        if not records: return None, "No data to export."
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f); writer.writerow(header); writer.writerows(records)
        return file_path, "Export successful!"