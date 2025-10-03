# app/services/pdf.py
from pathlib import Path
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONTS_DIR = Path(__file__).resolve().parent.parent / "templates" / "fonts"

def _register_fonts():
    """Register TTF fonts once (idempotent)."""
    if "NotoSans" in pdfmetrics.getRegisteredFontNames():
        return
    reg = FONTS_DIR / "NotoSans-Regular.ttf"
    bold = FONTS_DIR / "NotoSans-Bold.ttf"
    if not reg.exists() or not bold.exists():
        # Fall back la DejaVu dacă preferi sau ridică o eroare clară
        raise FileNotFoundError(f"Missing Noto Sans TTFs in {FONTS_DIR}")
    pdfmetrics.registerFont(TTFont("NotoSans", str(reg)))
    pdfmetrics.registerFont(TTFont("NotoSans-Bold", str(bold)))
    pdfmetrics.registerFontFamily("NotoSans", normal="NotoSans", bold="NotoSans-Bold")

def render_invoice_pdf(invoice: dict, items: list[dict], base_profile: dict, client_profile: dict) -> bytes:
    """
    Generează PDF (bytes) cu ReportLab, folosind Noto Sans (Unicode-ready).
    """
    _register_fonts()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Factura {invoice.get('invoice_number','')}",
    )

    ss = getSampleStyleSheet()
    normal = ParagraphStyle(
        "NotoNormal", parent=ss["Normal"], fontName="NotoSans", fontSize=10, leading=13
    )
    strong = ParagraphStyle(
        "NotoBold", parent=normal, fontName="NotoSans-Bold"
    )
    h1 = ParagraphStyle(
        "NotoH1", parent=strong, fontSize=16, leading=18, spaceAfter=6
    )
    small = ParagraphStyle(
        "NotoSmall", parent=normal, fontSize=9, leading=11, textColor=colors.grey
    )

    story = []
    # Header
    story.append(Paragraph(f"Factura {invoice['invoice_number']}", h1))
    story.append(Paragraph(
        f"Emisă: {invoice['issue_date']} • Scadentă: {invoice['due_date']}", small
    ))
    story.append(Spacer(1, 6))

    # Furnizor / Client
    def block_company(title, p):
        lines = []
        if not p:
            p = {}
        lines.append([Paragraph(f"<b>{title}</b>", strong), ""])
        lines.append([Paragraph(f"<b>{p.get('legal_name') or p.get('company_name','')}</b>", normal), ""])
        if p.get("cui"):        lines.append([f"CUI: {p['cui']}", ""])
        if p.get("reg_com"):    lines.append([f"Reg. Com.: {p['reg_com']}", ""])
        if p.get("address_line"): lines.append([f"Adresă: {p['address_line']}", ""])
        if p.get("iban"):       lines.append([f"IBAN: {p['iban']}" + (f" ({p['bank_name']})" if p.get('bank_name') else ""), ""])
        if p.get("email_billing"): lines.append([f"Email: {p['email_billing']}", ""])
        if p.get("phone_billing"): lines.append([f"Telefon: {p['phone_billing']}", ""])
        tbl = Table(lines, colWidths=[85*mm, 85*mm])
        tbl.setStyle(TableStyle([
            ("FONT", (0,0), (-1,-1), "NotoSans", 10),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("BOTTOMPADDING", (0,0), (-1,-1), 1),
            ("TOPPADDING", (0,0), (-1,-1), 1),
        ]))
        return tbl

    top_tbl = Table(
        [[block_company("Furnizor (BASE)", base_profile),
          block_company("Client", client_profile)]],
        colWidths=[90*mm, 90*mm],
        hAlign="LEFT"
    )
    top_tbl.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP")]))
    story.append(Spacer(1, 6))
    story.append(top_tbl)
    story.append(Spacer(1, 8))

    # Tabel linii
    head = ["#", "Descriere", "Cant.", "UM", "Preț unitar", "Valoare"]
    data = [head]
    for it in items:
        data.append([
            it.get("line_no", 1),
            it.get("description", ""),
            f"{it.get('qty', 0)}",
            it.get("unit", ""),
            f"{it.get('unit_price', 0)} {invoice.get('currency','')}",
            f"{it.get('line_total', 0)} {invoice.get('currency','')}",
        ])

    line_tbl = Table(
        data,
        colWidths=[12*mm, 78*mm, 18*mm, 14*mm, 30*mm, 28*mm],
        repeatRows=1
    )
    line_tbl.setStyle(TableStyle([
        ("FONT", (0,0), (-1,-1), "NotoSans", 10),
        ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#DDDDDD")),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#F7F7F7")),
        ("ALIGN", (2,1), (2,-1), "RIGHT"),
        ("ALIGN", (4,1), (5,-1), "RIGHT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(line_tbl)
    story.append(Spacer(1, 6))

    # Totaluri
    totals = Table([
        ["", "Subtotal", f"{invoice['subtotal']} {invoice['currency']}"],
        ["", f"TVA ({invoice['vat_rate']}%)", f"{invoice['vat_amount']} {invoice['currency']}"],
        ["", "Total", f"{invoice['total']} {invoice['currency']}"],
    ], colWidths=[110*mm, 40*mm, 40*mm])
    totals.setStyle(TableStyle([
        ("FONT", (0,0), (-1,-1), "NotoSans", 10),
        ("ALIGN", (1,0), (-1,-1), "RIGHT"),
        ("LINEABOVE", (1,2), (2,2), 0.25, colors.black),
        ("FONT", (1,2), (2,2), "NotoSans-Bold", 10),
        ("RIGHTPADDING", (2,0), (2,-1), 2),
    ]))
    story.append(totals)
    story.append(Spacer(1, 8))
    story.append(Paragraph("Document generat automat.", small))

    doc.build(story)
    return buf.getvalue()
