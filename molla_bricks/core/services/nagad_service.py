# molla_bricks/core/services/nagad_service.py
import os, csv
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors

class NagadService:
    @staticmethod
    def generate_chalan_pdf(chalan_data):
        os.makedirs("chalans", exist_ok=True); file_path = f"chalans/chalan_{chalan_data['id']}_{chalan_data.get('chalan_no', 'NA')}.pdf"
        c = canvas.Canvas(file_path, pagesize=letter); width, height = letter
        y = height - 0.75 * inch; c.setFont("Helvetica-Bold", 20); c.drawCentredString(width / 2.0, y, "Molla Bricks and Co."); y -= 0.25 * inch
        c.setFont("Helvetica", 12); c.drawCentredString(width / 2.0, y, "Address: Chanrail, Dhamrai, Dhaka"); y -= 0.20 * inch
        c.drawCentredString(width / 2.0, y, "Contact: 01712515056, 01954894353"); y -= 0.40 * inch
        c.setFont("Helvetica-Bold", 14); c.drawCentredString(width / 2.0, y, "CHALAN / INVOICE"); y -= 0.7 * inch
        c.setFont("Helvetica", 11); c.drawString(inch, y, f"Chalan No: {chalan_data.get('chalan_no', 'NA')}"); c.drawRightString(width - inch, y, f"Date: {chalan_data['date']}"); y -= 0.25 * inch
        c.drawString(inch, y, f"Customer Name: {chalan_data['customer_name']}"); y -= 0.22 * inch
        c.drawString(inch, y, f"Address: {chalan_data['address']}"); y -= 0.22 * inch
        c.drawString(inch, y, f"Vehicle No: {chalan_data['vehicle_no']}"); y -= 0.3 * inch
        c.line(inch, y, width - inch, y); y -= 0.3 * inch
        c.setFont("Helvetica-Bold", 11); c.drawString(inch, y, "Description"); c.drawRightString(width - inch, y, "Amount (BDT)"); y -= 0.3 * inch
        c.setFont("Helvetica", 11); c.drawString(inch, y, f"Bricks ({chalan_data['brick_type']})"); c.drawRightString(width - inch, y, f"{chalan_data['total_amount']:,.2f}"); y -= 0.3 * inch
        c.line(inch, y, width - inch, y); y -= 0.5 * inch
        c.setFont("Helvetica", 11); c.drawRightString(width - 2.5 * inch, y, "Total:"); c.drawRightString(width - inch, y, f"{chalan_data['total_amount']:,.2f} BDT"); y -= 0.3 * inch
        c.drawRightString(width - 2.5 * inch, y, "Paid:"); c.drawRightString(width - inch, y, f"{chalan_data['paid_amount']:,.2f} BDT"); y -= 0.3 * inch
        c.setFont("Helvetica-Bold", 12); c.drawRightString(width - 2.5 * inch, y, "Due:"); c.drawRightString(width - inch, y, f"{chalan_data['due_amount']:,.2f} BDT")
        y_foot = 1.5 * inch; c.line(inch, y_foot, inch + 2*inch, y_foot); c.line(width - inch - 2*inch, y_foot, width - inch, y_foot)
        c.setFont("Helvetica", 10); c.drawString(inch, y_foot - 0.2*inch, "Customer Signature"); c.drawRightString(width - inch, y_foot - 0.2*inch, "Authorized Signature")
        c.save(); return file_path

    @staticmethod
    def export_to_csv(db_controller):
        os.makedirs("exports", exist_ok=True); timestamp = datetime.now().strftime("%Y%m%d_%H%M%S"); file_path = f"exports/nagad_khata_export_{timestamp}.csv"
        query = "SELECT * FROM nagad_khata ORDER BY id ASC"; records = db_controller.execute_query(query, fetch="all")
        if not records: return None, "No data to export."
        header = ["id", "date", "chalan_no", "customer_name", "address", "vehicle_no", "brick_type", "brick_amount", "rate", "total_amount", "paid_amount", "due_amount", "timestamp"]
        with open(file_path, 'w', newline='', encoding='utf-8') as f: writer = csv.writer(f); writer.writerow(header); writer.writerows(records)
        return file_path, "Export successful!"

    # <<-- NEW: Function to create a PDF statement of dues -->>
    @staticmethod
    def generate_due_report_pdf(transactions, summary):
        os.makedirs("reports", exist_ok=True)
        customer_name = summary.get('customer_name', 'AllCustomers')
        safe_customer_name = "".join(c for c in customer_name if c.isalnum())
        file_path = f"reports/dues_{safe_customer_name}_{datetime.now().strftime('%Y%m%d')}.pdf"

        c = canvas.Canvas(file_path, pagesize=letter)
        width, height = letter

        y = height - 0.75 * inch; c.setFont("Helvetica-Bold", 16); c.drawCentredString(width / 2.0, y, "Statement of Dues")
        y -= 0.3 * inch; c.setFont("Helvetica", 12); c.drawCentredString(width / 2.0, y, f"Customer: {customer_name}")
        y -= 0.2 * inch; c.drawCentredString(width / 2.0, y, f"Report Date: {datetime.now().strftime('%Y-%m-%d')}")
        y -= 0.5 * inch

        table_data = [["Date", "Chalan No", "Total Amount", "Paid Amount", "Due Amount"]]
        for row in transactions:
            # Assumes row format: (id, date, chalan_no, customer_name, total, paid, due)
            formatted_row = [row[1], row[2], f"{row[4]:,.2f}", f"{row[5]:,.2f}", f"{row[6]:,.2f}"]
            table_data.append(formatted_row)
        
        table_data.append(["", "GRAND TOTAL:", "", "", f"{summary['total_due']:,.2f}"])

        t = Table(table_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12), ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey), ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (2, 1), (-1, -2), 'RIGHT'), ('ALIGN', (-1, -1), (-1, -1), 'RIGHT')
        ])
        t.setStyle(style); t.wrapOn(c, width, height); t.drawOn(c, 0.5*inch, y - (len(table_data) * 0.25 * inch))
        
        c.save(); return file_path