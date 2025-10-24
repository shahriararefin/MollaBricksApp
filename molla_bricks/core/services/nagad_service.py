# molla_bricks/core/services/nagad_service.py
import os, csv
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

# --- Font Registration ---
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register the Bengali font
font_path = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'fonts', 'Kalpurush.ttf')
if os.path.exists(font_path):
    pdfmetrics.registerFont(TTFont('Kalpurush', font_path))
else:
    print(f"Warning: Font file not found at {font_path}. Bengali text may not render.")

# --- Reusable Header/Footer Function ---
def _pdf_header_footer(canvas, doc):
    canvas.saveState()
    styles = getSampleStyleSheet()
    
    # --- Header (Centered) ---
    try:
        # Try to use the Bengali font
        header_style = ParagraphStyle(name='HeaderTitle', fontName='Kalpurush', fontSize=20, alignment=TA_CENTER)
        header_text = "মোল্লা ব্রিকস এন্ড কোং"
    except:
        # Fallback to English
        header_style = styles['h1']
        header_style.alignment = TA_CENTER
        header_text = "Molla Bricks and Co."
        
    p = Paragraph(header_text, header_style)
    p.wrapOn(canvas, doc.width, doc.topMargin)
    p.drawOn(canvas, doc.leftMargin, doc.height + doc.topMargin - 0.5*inch)
    
    y = doc.height + doc.topMargin - 0.75*inch
    addr_style = ParagraphStyle(name='HeaderAddress', fontName='Helvetica', fontSize=10, alignment=TA_CENTER)
    
    p_addr = Paragraph("Address: Chandrail, Dhamrai, Dhaka", addr_style)
    p_addr.wrapOn(canvas, doc.width, doc.topMargin)
    p_addr.drawOn(canvas, doc.leftMargin, y); y -= 0.2*inch
    
    p_contact = Paragraph("Contact: 01712515056", addr_style)
    p_contact.wrapOn(canvas, doc.width, doc.topMargin)
    p_contact.drawOn(canvas, doc.leftMargin, y)

    # --- Footer (Signature Line) ---
    canvas.line(doc.width - doc.rightMargin - 2.5*inch, doc.bottomMargin - 0.2*inch, doc.width - doc.rightMargin, doc.bottomMargin - 0.2*inch)
    p_footer = Paragraph("Authorized Signature", styles['Normal'])
    p_footer.style.alignment = TA_RIGHT
    p_footer.wrapOn(canvas, doc.width, doc.bottomMargin)
    p_footer.drawOn(canvas, 0, doc.bottomMargin - 0.4*inch)
    
    canvas.restoreState()

class NagadService:
    @staticmethod
    def generate_chalan_pdf(chalan_data):
        os.makedirs("exports/chalans", exist_ok=True)
        chalan_no = chalan_data.get('chalan_no', 'N-A')
        file_path = os.path.abspath(f"exports/chalans/chalan_{chalan_no}_{datetime.now().strftime('%Y%m%d')}.pdf")
        
        doc = SimpleDocTemplate(file_path, pagesize=A4, topMargin=1.5*inch, bottomMargin=1*inch)
        story = []
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='RightAlign', alignment=TA_RIGHT))
        
        story.append(Paragraph("<u>CHALAN / INVOICE</u>", styles['h2']))
        story.append(Spacer(1, 0.25*inch))

        info_data = [
            [f"Chalan No: {chalan_data.get('chalan_no', 'N/A')}", f"Date: {chalan_data.get('date', 'N/A')}"],
            [f"Customer Name: {chalan_data.get('customer_name', 'N/A')}", ""],
            [f"Address: {chalan_data.get('address', 'N/A')}", ""],
            [f"Vehicle No: {chalan_data.get('vehicle_no', 'N/A')}", ""],
        ]
        info_table = Table(info_data, colWidths=[3*inch, 3*inch])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'), ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.2*inch))

        item_data = [
            ["Description", "Amount (BDT)"],
            [f"Bricks ({chalan_data.get('brick_type', '')}) - {chalan_data.get('brick_amount', 0)} pcs", Paragraph(f"{chalan_data.get('total_amount', 0):,.2f}", styles['RightAlign'])]
        ]
        item_table = Table(item_data, colWidths=[5*inch, 1.5*inch])
        item_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'), ('ALIGN', (1, 1), (1, 1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black), ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(item_table)
        story.append(Spacer(1, 0.1*inch))
        
        totals_data = [
            ["Total:", f"{chalan_data.get('total_amount', 0):,.2f} BDT"],
            ["Paid:", f"{chalan_data.get('paid_amount', 0):,.2f} BDT"],
            [Paragraph("<b>Due:</b>", styles['BodyText']), Paragraph(f"<b>{chalan_data.get('due_amount', 0):,.2f} BDT</b>", styles['RightAlign'])],
        ]
        totals_table = Table(totals_data, colWidths=[4.5*inch, 2*inch])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'), ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'), # Make Due bold
            ('FONTSIZE', (0, 0), (-1, -1), 11), ('TOPPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(totals_table)
        
        doc.build(story, onFirstPage=_pdf_header_footer, onLaterPages=_pdf_header_footer)
        return file_path
    
    @staticmethod
    def export_to_csv(db_controller):
        os.makedirs("exports", exist_ok=True)
        file_path = f"exports/nagad_khata_export_{datetime.now().strftime('%Y%m%d')}.csv"
        header = ["id", "date", "chalan_no", "customer_name", "address", "vehicle_no", "brick_type", "brick_amount", "total_amount", "paid_amount", "due_amount", "timestamp"]
        query = "SELECT id, date, chalan_no, customer_name, address, vehicle_no, brick_type, brick_amount, total_amount, paid_amount, due_amount, timestamp FROM nagad_khata ORDER BY id DESC"
        records = db_controller.execute_query(query, fetch="all")
        if not records: return None, "No data to export."
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f); writer.writerow(header); writer.writerows(records)
        return file_path, "Export successful!"

    @staticmethod
    def generate_due_report_pdf(transactions, summary):
        os.makedirs("exports/reports", exist_ok=True)
        customer_name = summary.get('customer_name', 'AllCustomers')
        safe_customer_name = "".join(c for c in customer_name if c.isalnum())
        file_path = os.path.abspath(f"exports/reports/dues_{safe_customer_name}_{datetime.now().strftime('%Y%m%d')}.pdf")

        doc = SimpleDocTemplate(file_path, pagesize=letter, topMargin=1.5*inch, bottomMargin=1*inch)
        story = []
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='RightAlign', alignment=TA_RIGHT))

        story.append(Paragraph("Statement of Dues", styles['h2']))
        story.append(Paragraph(f"<b>Customer:</b> {customer_name}", styles['h3']))
        story.append(Paragraph(f"<b>Report Date:</b> {datetime.now().strftime('%Y-%m-%d')}", styles['BodyText']))
        story.append(Spacer(1, 0.5*inch))

        table_data = [["Date", "Chalan No", "Total Amount", "Paid Amount", "Due Amount"]]
        for row in transactions:
            formatted_row = [row[1], row[2], f"{row[4]:,.2f}", f"{row[5]:,.2f}", f"{row[6]:,.2f}"]
            table_data.append(formatted_row)
        
        # --- FIXED: Use Paragraph objects for bold text ---
        table_data.append([
            Paragraph("<b>GRAND TOTAL:</b>", styles['BodyText']), 
            "", "", "", 
            Paragraph(f"<b>{summary['total_due']:,.2f}</b>", styles['RightAlign'])
        ])

        t = Table(table_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12), ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey), ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (2, 1), (-1, -2), 'RIGHT'), ('ALIGN', (-1, -1), (-1, -1), 'RIGHT'),
            ('SPAN', (0, -1), (3, -1)) # Span the GRAND TOTAL text
        ])
        t.setStyle(style)
        story.append(t)
        
        doc.build(story, onFirstPage=_pdf_header_footer, onLaterPages=_pdf_header_footer)
        return file_path