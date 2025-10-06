# app/services/pdf.py
from pathlib import Path
import io
from decimal import Decimal, ROUND_HALF_UP
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONTS_DIR = Path(__file__).resolve().parent.parent / "templates" / "fonts"

def _try_register_noto() -> tuple[str, str]:
    """
    Try to register Noto Sans (Unicode). If fonts are missing,
    fall back to Helvetica so we never crash.
    Returns (normal_font_name, bold_font_name).
    """
    try:
        if "NotoSans" not in pdfmetrics.getRegisteredFontNames():
            reg = FONTS_DIR / "NotoSans-Regular.ttf"
            bold = FONTS_DIR / "NotoSans-Bold.ttf"
            if reg.exists() and bold.exists():
                pdfmetrics.registerFont(TTFont("NotoSans", str(reg)))
                pdfmetrics.registerFont(TTFont("NotoSans-Bold", str(bold)))
                pdfmetrics.registerFontFamily("NotoSans", normal="NotoSans", bold="NotoSans-Bold")
            else:
                return ("Helvetica", "Helvetica-Bold")
        return ("NotoSans", "NotoSans-Bold")
    except Exception:
        return ("Helvetica", "Helvetica-Bold")

def _q2(x) -> Decimal:
    try:
        d = Decimal(str(x))
    except Exception:
        d = Decimal("0")
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def _fmt2(x) -> str:
    return f"{_q2(x):.2f}"

def _fmt_addr(p: dict) -> str:
    parts = []
    if p.get("address_line"):
        parts.append(str(p["address_line"]))
    city_line = " ".join(s for s in [
        str(p.get("city") or "") if p.get("city") else "",
        f"jud. {p['county']}" if p.get("county") else "",
        str(p.get("postal_code") or "") if p.get("postal_code") else ""
    ] if s)
    if city_line:
        parts.append(city_line)
    if p.get("country"):
        parts.append(str(p["country"]))
    return ", ".join(parts)

def render_invoice_pdf(invoice: dict, items: list[dict], base_profile: dict, client_profile: dict) -> bytes:
    """
    Generează PDF (bytes) cu ReportLab.
    - Folosește Noto Sans dacă e disponibil; altfel Helvetica.
    - Afișează coloană de greutate (kg) dacă item-urile includ 'weight_kg'.
    """
    font_normal, font_bold = _try_register_noto()

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
        "NormalCustom", parent=ss["Normal"], fontName=font_normal, fontSize=10, leading=13
    )
    strong = ParagraphStyle(
        "BoldCustom", parent=normal, fontName=font_bold
    )
    h1 = ParagraphStyle(
        "H1Custom", parent=strong, fontSize=16, leading=18, spaceAfter=6
    )
    small = ParagraphStyle(
        "SmallCustom", parent=normal, fontSize=9, leading=11, textColor=colors.grey
    )

    story = []
    # Header
    story.append(Paragraph(f"Factura {invoice.get('invoice_number','')}", h1))
    story.append(Paragraph(
        f"Emisă: {invoice.get('issue_date','')} • Scadentă: {invoice.get('due_date','')}", small
    ))
    story.append(Spacer(1, 6))

    # Furnizor / Client
    def block_company(title, p):
        p = p or {}
        lines = []
        lines.append([Paragraph(f"<b>{title}</b>", strong), ""])
        name = p.get("legal_name") or p.get("company_name", "")
        lines.append([Paragraph(f"<b>{name}</b>", normal), ""])
        if p.get("cui"):           lines.append([f"CUI: {p['cui']}", ""])
        if p.get("reg_com"):       lines.append([f"Reg. Com.: {p['reg_com']}", ""])
        addr = _fmt_addr(p)
        if addr:                   lines.append([f"Adresă: {addr}", ""])
        if p.get("iban"):
            bank = f" ({p['bank_name']})" if p.get("bank_name") else ""
            lines.append([f"IBAN: {p['iban']}{bank}", ""])
        if p.get("email_billing"): lines.append([f"Email: {p['email_billing']}", ""])
        if p.get("phone_billing"): lines.append([f"Telefon: {p['phone_billing']}", ""])
        tbl = Table(lines, colWidths=[85*mm, 85*mm])
        tbl.setStyle(TableStyle([
            ("FONT", (0,0), (-1,-1), font_normal, 10),
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
    currency = invoice.get("currency", "RON")
    has_weight = any("weight_kg" in it for it in (items or []))

    if has_weight:
        head = ["#", "Descriere", "Greutate (kg)", "Cant.", "UM", "Preț unitar", "Valoare"]
        col_widths = [12*mm, 66*mm, 22*mm, 18*mm, 14*mm, 24*mm, 24*mm]  # total ~180mm
    else:
        head = ["#", "Descriere", "Cant.", "UM", "Preț unitar", "Valoare"]
        col_widths = [12*mm, 78*mm, 18*mm, 14*mm, 30*mm, 28*mm]

    data = [head]
    for it in (items or []):
        row = [
            it.get("line_no", 1),
            it.get("description", ""),
        ]
        if has_weight:
            row.append(_fmt2(it.get("weight_kg", 0)))
        row.extend([
            _fmt2(it.get("qty", 0)),
            it.get("unit", ""),
            f"{_fmt2(it.get('unit_price', 0))} {currency}",
            f"{_fmt2(it.get('line_total', 0))} {currency}",
        ])
        data.append(row)

    line_tbl = Table(
        data,
        colWidths=col_widths,
        repeatRows=1
    )
    line_tbl.setStyle(TableStyle([
        ("FONT", (0,0), (-1,-1), font_normal, 10),
        ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#DDDDDD")),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#F7F7F7")),
        ("ALIGN", (2,1), (-1,-1), "RIGHT"),
        ("ALIGN", (1,0), (1,0), "LEFT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(line_tbl)
    story.append(Spacer(1, 6))

    # Totaluri
    subtotal = _fmt2(invoice.get("subtotal", 0))
    vat_rate = invoice.get("vat_rate", "0")
    vat_amount = _fmt2(invoice.get("vat_amount", 0))
    total = _fmt2(invoice.get("total", 0))

    totals = Table([
        ["", "Subtotal", f"{subtotal} {currency}"],
        ["", f"TVA ({vat_rate}%)", f"{vat_amount} {currency}"],
        ["", "Total", f"{total} {currency}"],
    ], colWidths=[110*mm, 40*mm, 40*mm])
    totals.setStyle(TableStyle([
        ("FONT", (0,0), (-1,-1), font_normal, 10),
        ("ALIGN", (1,0), (-1,-1), "RIGHT"),
        ("LINEABOVE", (1,2), (2,2), 0.25, colors.black),
        ("FONT", (1,2), (2,2), font_bold, 10),
        ("RIGHTPADDING", (2,0), (2,-1), 2),
    ]))
    story.append(totals)
    story.append(Spacer(1, 8))
    story.append(Paragraph("Document generat automat.", small))

    doc.build(story)
    return buf.getvalue()
