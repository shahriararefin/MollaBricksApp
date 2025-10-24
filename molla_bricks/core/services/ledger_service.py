# molla_bricks/core/services/ledger_service.py
import os
import csv
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

# --- Reusable Header/Footer Function ---
def _pdf_header_footer(canvas, doc):
    canvas.saveState()
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle(name='HeaderTitle', fontName='Helvetica-Bold', fontSize=18, alignment=TA_CENTER)
    addr_style = ParagraphStyle(name='HeaderAddress', fontName='Helvetica', fontSize=10, alignment=TA_CENTER)
    
    p = Paragraph("Molla Bricks and Co.", header_style)
    p.wrapOn(canvas, doc.width, doc.topMargin)
    p.drawOn(canvas, doc.leftMargin, doc.height + doc.topMargin - 0.5*inch)
    
    y = doc.height + doc.topMargin - 0.75*inch
    p_addr = Paragraph("Address: Chandrail, Dhamrai, Dhaka", addr_style)
    p_addr.wrapOn(canvas, doc.width, doc.topMargin)
    p_addr.drawOn(canvas, doc.leftMargin, y); y -= 0.2*inch
    
    p_contact = Paragraph("Contact: 01712515056", addr_style)
    p_contact.wrapOn(canvas, doc.width, doc.topMargin)
    p_contact.drawOn(canvas, doc.leftMargin, y)

    canvas.line(doc.width - doc.rightMargin - 2.5*inch, doc.bottomMargin - 0.2*inch, doc.width - doc.rightMargin, doc.bottomMargin - 0.2*inch)
    p_footer = Paragraph("Authorized Signature", styles['Normal'])
    p_footer.style.alignment = TA_RIGHT
    p_footer.wrapOn(canvas, doc.width, doc.bottomMargin)
    p_footer.drawOn(canvas, 0, doc.bottomMargin - 0.4*inch)
    canvas.restoreState()

class LedgerService:
    @staticmethod
    def generate_ledger_pdf(party_name, start_date, end_date, opening_balance, transactions):
        os.makedirs("exports/statements", exist_ok=True)
        safe_name = "".join(c for c in party_name if c.isalnum())
        file_path = os.path.abspath(f"exports/statements/statement_{safe_name}_{datetime.now().strftime('%Y%m%d')}.pdf")
        doc = SimpleDocTemplate(file_path, pagesize=A4, topMargin=1.5*inch, bottomMargin=1*inch)
        story = []; styles = getSampleStyleSheet()
        story.append(Paragraph("Statement of Account", styles['h2']))
        story.append(Paragraph(f"<b>Party:</b> {party_name}", styles['h3']))
        story.append(Paragraph(f"<b>Period:</b> {start_date} to {end_date}", styles['BodyText']))
        story.append(Spacer(1, 0.25*inch))
        data = [["Date", "Description", "Debit (Bill)", "Credit (Paid)", "Balance"]]
        styles.add(ParagraphStyle(name='RightAlign', alignment=TA_RIGHT))
        balance = opening_balance
        data.append(["", Paragraph("<b>Opening Balance</b>", styles['BodyText']), "", "", Paragraph(f"<b>{balance:,.2f}</b>", styles['RightAlign'])])
        for row in transactions:
            date, desc, credit, debit = row; balance += credit - debit
            data.append([date, Paragraph(desc, styles['BodyText']), Paragraph(f"{debit:,.2f}", styles['RightAlign']), Paragraph(f"{credit:,.2f}", styles['RightAlign']), Paragraph(f"{balance:,.2f}", styles['RightAlign'])])
        data.append(["", Paragraph("<b>Closing Balance</b>", styles['BodyText']), "", "", Paragraph(f"<b>{balance:,.2f}</b>", styles['RightAlign'])])
        table = Table(data, colWidths=[0.8*inch, 3.7*inch, 1*inch, 1*inch, 1.2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BOX', (0, 0), (-1, -1), 1, colors.black), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey), ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('SPAN', (0, -1), (3, -1))
        ])); story.append(table)
        doc.build(story, onFirstPage=_pdf_header_footer, onLaterPages=_pdf_header_footer); return file_path

    @staticmethod
    def generate_pnl_pdf(start_date, end_date, revenue_data, expense_data):
        os.makedirs("exports/reports", exist_ok=True)
        file_path = os.path.abspath(f"exports/reports/pnl_{start_date}_to_{end_date}.pdf")
        doc = SimpleDocTemplate(file_path, pagesize=A4, topMargin=1.5*inch, bottomMargin=1*inch)
        story = []; styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='RightAlign', alignment=TA_RIGHT))
        story.append(Paragraph("Profit & Loss Statement", styles['h2']))
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
        profit_style = ParagraphStyle(name='Profit', fontName='Helvetica-Bold', fontSize=14, alignment=TA_RIGHT)
        profit_text = f"Net Profit: {net_profit:,.2f} BDT"
        if net_profit < 0:
            profit_style.textColor = colors.red; profit_text = f"Net Loss: {net_profit:,.2f} BDT"
        else:
            profit_style.textColor = colors.green
        story.append(Paragraph(profit_text, profit_style))
        doc.build(story, onFirstPage=_pdf_header_footer, onLaterPages=_pdf_header_footer); return file_path

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
    
    # --- NEW: Function to generate Coal Statement PDF ---
    @staticmethod
    def generate_coal_statement_pdf(start_date, end_date, sector, entries, totals):
        os.makedirs("exports/reports", exist_ok=True)
        file_path = os.path.abspath(f"exports/reports/coal_statement_{datetime.now().strftime('%Y%m%d')}.pdf")
        
        doc = SimpleDocTemplate(file_path, pagesize=landscape(A4), topMargin=1.5*inch, bottomMargin=1*inch)
        story = []; styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='RightAlign', alignment=TA_RIGHT))
        styles.add(ParagraphStyle(name='LeftAlign', alignment=TA_LEFT))

        story.append(Paragraph("Coal Statement", styles['h2']))
        story.append(Paragraph(f"<b>Period:</b> {start_date} to {end_date}", styles['BodyText']))
        if sector:
            story.append(Paragraph(f"<b>Sector:</b> {sector}", styles['BodyText']))
        story.append(Spacer(1, 0.25*inch))
        
        table_data = [["No.", "Date", "Fiscal year", "Voucher No.", "Sector", "Quantity", "Rate", "Total", "Notes"]]
        for i, row in enumerate(entries):
            table_data.append([
                i + 1,
                row[1], # Date
                row[2], # Fiscal Year
                row[3], # Voucher
                row[4], # Sector
                Paragraph(f"{row[6]:,.2f}", styles['RightAlign']), # Quantity
                Paragraph(f"{row[7]:,.2f}", styles['RightAlign']), # Rate
                Paragraph(f"{row[8]:,.2f}", styles['RightAlign']), # Total
                Paragraph(row[9] or '', styles['LeftAlign']), # Notes
            ])
        
        # --- Totals Row ---
        table_data.append([
            Paragraph("<b>Total</b>", styles['BodyText']),
            "", "", "", "",
            Paragraph(f"<b>{totals['quantity']:,.2f}</b>", styles['RightAlign']),
            "",
            Paragraph(f"<b>{totals['amount']:,.2f}</b>", styles['RightAlign']),
            ""
        ])

        table = Table(table_data, colWidths=[0.5*inch, 1*inch, 1*inch, 1*inch, 1.5*inch, 1*inch, 1*inch, 1.2*inch, 2.3*inch])
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('SPAN', (0, -1), (4, -1)), # Span "Total" text
            ('ALIGN', (0, -1), (4, -1), 'RIGHT'),
        ])
        table.setStyle(style)
        story.append(table)
        
        doc.build(story, onFirstPage=_pdf_header_footer, onLaterPages=_pdf_header_footer)
        return file_path