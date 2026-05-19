"""
Form 16 Generator — TRACES Format
====================================
Generates 4 realistic dummy Form 16 PDFs matching the exact TRACES layout.
Run: python generate_form16s.py
Output: form16_priya_sharma.pdf, form16_rohit_mehta.pdf,
        form16_ananya_krishnan.pdf, form16_arjun_singh.pdf
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, HRFlowable, PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.platypus.flowables import Flowable
import os

# ── Colours ────────────────────────────────────────────────────────────────────

TRACES_TEAL   = colors.Color(0.0, 0.47, 0.53)    # #007888
HEADER_BLUE   = colors.Color(0.69, 0.87, 0.90)   # light blue table header
LIGHT_BLUE    = colors.Color(0.87, 0.95, 0.97)
GOV_BLUE      = colors.Color(0.0,  0.20, 0.53)
TABLE_BORDER  = colors.Color(0.5,  0.5,  0.5)
ZEBRA         = colors.Color(0.97, 0.97, 0.97)


# ── Paragraph styles ───────────────────────────────────────────────────────────

def _styles():
    s = getSampleStyleSheet()
    base = dict(fontName="Helvetica", fontSize=7, leading=9)
    return {
        "title":     ParagraphStyle("title",     fontName="Helvetica-Bold", fontSize=14, alignment=TA_CENTER, spaceAfter=2),
        "sub_title": ParagraphStyle("sub_title", fontName="Helvetica-Bold", fontSize=11, alignment=TA_CENTER, spaceAfter=2),
        "rule_ref":  ParagraphStyle("rule_ref",  fontName="Helvetica",      fontSize=8,  alignment=TA_CENTER, spaceAfter=4),
        "part":      ParagraphStyle("part",      fontName="Helvetica-Bold", fontSize=11, alignment=TA_CENTER, spaceAfter=2),
        "cert_desc": ParagraphStyle("cert_desc", **base,                    alignment=TA_CENTER, spaceAfter=3),
        "body":      ParagraphStyle("body",      **base,                    alignment=TA_LEFT),
        "body_c":    ParagraphStyle("body_c",    **base,                    alignment=TA_CENTER),
        "body_r":    ParagraphStyle("body_r",    **base,                    alignment=TA_RIGHT),
        "bold":      ParagraphStyle("bold",      fontName="Helvetica-Bold", fontSize=7, leading=9),
        "bold_c":    ParagraphStyle("bold_c",    fontName="Helvetica-Bold", fontSize=7, leading=9, alignment=TA_CENTER),
        "section":   ParagraphStyle("section",   fontName="Helvetica-Bold", fontSize=7.5, leading=10, spaceAfter=2),
        "small":     ParagraphStyle("small",     fontName="Helvetica",      fontSize=6,  leading=8),
        "verif":     ParagraphStyle("verif",     fontName="Helvetica",      fontSize=7,  leading=10, alignment=TA_JUSTIFY),
        "note":      ParagraphStyle("note",      fontName="Helvetica",      fontSize=6,  leading=8),
    }

ST = _styles()


def P(text, style="body"):
    return Paragraph(text, ST[style])


def fmt(n):
    """Format number as Indian Rs with 2 decimals."""
    if n == 0:
        return "0.00"
    return f"{n:,.2f}"


def num_to_words(n):
    """Convert integer to Indian currency words (simplified)."""
    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
            "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
            "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty",
            "Sixty", "Seventy", "Eighty", "Ninety"]

    def _below_1000(n):
        if n < 20:
            return ones[n]
        elif n < 100:
            return tens[n // 10] + (" " + ones[n % 10] if n % 10 else "")
        else:
            return ones[n // 100] + " Hundred" + (" and " + _below_1000(n % 100) if n % 100 else "")

    if n == 0:
        return "Zero"
    parts = []
    crore = n // 10000000; n %= 10000000
    lakh  = n // 100000;   n %= 100000
    thous = n // 1000;     n %= 1000
    rem   = n
    if crore: parts.append(_below_1000(crore) + " Crore")
    if lakh:  parts.append(_below_1000(lakh) + " Lakh")
    if thous: parts.append(_below_1000(thous) + " Thousand")
    if rem:   parts.append(_below_1000(rem))
    return " ".join(parts) + " Only"


# ── Page number footer ─────────────────────────────────────────────────────────

def _footer(canvas_obj, doc, employee, cert_no, total_pages):
    canvas_obj.saveState()
    canvas_obj.setFont("Helvetica", 6.5)
    page = canvas_obj.getPageNumber()
    canvas_obj.drawCentredString(A4[0] / 2, 12 * mm,
        f"Page {page} of {total_pages}")
    if page > 1:
        canvas_obj.setFont("Helvetica", 6)
        info = (f"Certificate Number: {cert_no}    "
                f"TAN of Employer: {employee['employer_tan']}    "
                f"PAN of Employee: {employee['employee_pan']}    "
                f"Assessment Year: {employee['assessment_year']}")
        canvas_obj.drawCentredString(A4[0] / 2, 17 * mm, info)
    canvas_obj.restoreState()


# ── TRACES header ──────────────────────────────────────────────────────────────

def _traces_header():
    """Return the top header rows (TRACES logo + GOI logo row)."""
    # Left: TDS TRACES text, Right: Government of India text
    header_data = [[
        P("<font color='#007888'><b>TDS</b></font>   <font size=8><b>TRACES</b><br/>"
          "<font size=5>Centralized Processing Cell</font><br/>"
          "<font size=5 color='#007888'>TDS Reconciliation Analysis and Correction Enabling System</font></font>", "body"),
        P("<b>Government of India</b><br/><font size=5>Income Tax Department</font>", "body_r"),
    ]]
    t = Table(header_data, colWidths=[120 * mm, 60 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


# ── Part A builder ─────────────────────────────────────────────────────────────

def build_part_a(emp, story):
    story.append(_traces_header())
    story.append(HRFlowable(width="100%", thickness=1, color=TRACES_TEAL))
    story.append(Spacer(1, 3 * mm))

    story.append(P("FORM NO. 16", "title"))
    story.append(P("[See rule 31(1)(a)]", "rule_ref"))
    story.append(P("PART A", "part"))
    story.append(Spacer(1, 1 * mm))
    story.append(P(
        "Certificate under Section 203 of the Income-tax Act, 1961 for tax deducted at source on salary "
        "paid to an employee under section 192 or pension/interest income of specified senior citizen "
        "under section 194P", "cert_desc"))
    story.append(HRFlowable(width="100%", thickness=0.5, color=TABLE_BORDER))

    # Certificate No / Last updated row
    cert_row = Table([[
        Table([[
            [P("Certificate No.", "bold"), P(emp["certificate_no"], "body")],
        ]], colWidths=[30 * mm, 60 * mm], style=TableStyle([
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, TABLE_BORDER),
        ])),
        Table([[
            [P("Last updated on", "bold"), P(emp["last_updated"], "body")],
        ]], colWidths=[35 * mm, 52 * mm]),
    ]], colWidths=[95 * mm, 90 * mm])
    cert_row.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 1),
                                   ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    story.append(cert_row)

    # Employer / Employee 2-column
    emp_table = Table([
        [P("Name and address of the Employer/Specified Bank", "bold_c"),
         P("Name and address of the Employee/Specified senior citizen", "bold_c")],
        [P(emp["employer_name"] + "\n" + emp["employer_address"], "body"),
         P(emp["employee_name"] + "\n" + emp["employee_address"], "body")],
    ], colWidths=[92 * mm, 92 * mm])
    emp_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BLUE),
        ("BOX",        (0, 0), (-1, -1), 0.5, TABLE_BORDER),
        ("INNERGRID",  (0, 0), (-1, -1), 0.3, TABLE_BORDER),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(emp_table)

    # PAN/TAN row
    pan_table = Table([
        [P("PAN of the Deductor", "bold_c"),
         P("TAN of the Deductor", "bold_c"),
         P("PAN of the\nEmployee/Specified senior\ncitizen", "bold_c"),
         P("Employee Reference No. provided by the\nEmployer (If available)", "bold_c")],
        [P(emp["employer_pan"], "body_c"),
         P(emp["employer_tan"], "body_c"),
         P(emp["employee_pan"], "body_c"),
         P("", "body_c")],
    ], colWidths=[35 * mm, 35 * mm, 35 * mm, 80 * mm])
    pan_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BLUE),
        ("BOX",        (0, 0), (-1, -1), 0.5, TABLE_BORDER),
        ("INNERGRID",  (0, 0), (-1, -1), 0.3, TABLE_BORDER),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(pan_table)

    # CIT / AY / Period row
    cit_table = Table([
        [P("CIT (TDS)", "bold_c"),
         P("Assessment Year", "bold_c"),
         P("Period with the Employer", "bold_c", )],
        [P(emp["cit_address"], "body"),
         P(emp["assessment_year"], "body_c"),
         Table([
             [P("From", "bold_c"), P("To", "bold_c")],
             [P(emp["period_from"], "body_c"), P(emp["period_to"], "body_c")],
         ], colWidths=[25 * mm, 25 * mm],
         style=TableStyle([("INNERGRID", (0,0), (-1,-1), 0.3, TABLE_BORDER)])
         )],
    ], colWidths=[62 * mm, 22 * mm, 100 * mm])
    cit_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), HEADER_BLUE),
        ("BOX",           (0, 0), (-1, -1), 0.5, TABLE_BORDER),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, TABLE_BORDER),
        ("SPAN",          (2, 0), (2, 0)),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(cit_table)
    story.append(Spacer(1, 2 * mm))

    # Summary of TDS table
    story.append(P("Summary of amount paid/credited and tax deducted at source thereon in respect of the employee",
                   "bold_c"))
    quarters = emp["quarters"]
    total_amount = sum(q["amount"] for q in quarters)
    total_deducted = sum(q["tds"] for q in quarters)

    q_data = [
        [P("Quarter(s)", "bold_c"),
         P("Receipt Numbers of original\nquarterly statements of TDS\nunder sub-section (3) of\nSection 200", "bold_c"),
         P("Amount paid/credited (Rs.)", "bold_c"),
         P("Amount of tax deducted\n(Rs.)", "bold_c"),
         P("Amount of tax deposited / remitted\n(Rs.)", "bold_c")],
    ]
    for i, q in enumerate(quarters):
        bg = LIGHT_BLUE if i % 2 == 0 else colors.white
        q_data.append([
            P(q["label"], "body_c"),
            P(q["receipt"], "body_c"),
            P(fmt(q["amount"]), "body_r"),
            P(fmt(q["tds"]),    "body_r"),
            P(fmt(q["tds"]),    "body_r"),
        ])
    q_data.append([
        P("Total (Rs.)", "bold"),
        P("", "body"),
        P(fmt(total_amount),   "body_r"),
        P(fmt(total_deducted), "body_r"),
        P(fmt(total_deducted), "body_r"),
    ])
    q_table = Table(q_data, colWidths=[10 * mm, 45 * mm, 42 * mm, 36 * mm, 48 * mm])
    q_style = [
        ("BACKGROUND",    (0, 0), (-1, 0), HEADER_BLUE),
        ("BOX",           (0, 0), (-1, -1), 0.5, TABLE_BORDER),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, TABLE_BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("FONTNAME",      (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND",    (0, -1), (-1, -1), LIGHT_BLUE),
    ]
    for i in range(1, len(quarters) + 1):
        if i % 2 == 1:
            q_style.append(("BACKGROUND", (0, i), (-1, i), LIGHT_BLUE))
    q_table.setStyle(TableStyle(q_style))
    story.append(q_table)
    story.append(Spacer(1, 3 * mm))

    # Section I (Book Adjustment) - usually blank for private companies
    story.append(P("I. DETAILS OF TAX DEDUCTED AND DEPOSITED IN THE CENTRAL GOVERNMENT ACCOUNT THROUGH BOOK ADJUSTMENT", "bold_c"))
    story.append(P("(The deductor to provide payment wise details of tax deducted and deposited with respect to the deductee)", "small"))
    ba_data = [
        [P("Sl. No.", "bold_c"),
         P("Tax Deposited in respect of the\ndeductee\n(Rs.)", "bold_c"),
         P("Receipt Numbers of Form\nNo. 24G", "bold_c"),
         P("DDO serial number in Form no.\n24G", "bold_c"),
         P("Date of transfer voucher\n(dd/mm/yyyy)", "bold_c"),
         P("Status of matching\nwith Form no. 24G", "bold_c")],
        [P("", "body"), P("", "body"), P("", "body"), P("", "body"), P("", "body"), P("", "body")],
        [P("Total (Rs.)", "bold"), P("", "body"), P("", "body"), P("", "body"), P("", "body"), P("", "body")],
    ]
    ba_table = Table(ba_data, colWidths=[10 * mm, 35 * mm, 35 * mm, 35 * mm, 35 * mm, 31 * mm])
    ba_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), HEADER_BLUE),
        ("BOX",           (0, 0), (-1, -1), 0.5, TABLE_BORDER),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, TABLE_BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(ba_table)
    story.append(Spacer(1, 2 * mm))

    # Section II (Challan)
    story.append(P("II. DETAILS OF TAX DEDUCTED AND DEPOSITED IN THE CENTRAL GOVERNMENT ACCOUNT THROUGH CHALLAN", "bold_c"))
    story.append(P("(The deductor to provide payment wise details of tax deducted and deposited with respect to the deductee)", "small"))
    challan_header = [
        P("Sl. No.", "bold_c"),
        P("Tax Deposited in respect of the\ndeductee\n(Rs.)", "bold_c"),
        P("BSR Code of the Bank\nBranch", "bold_c"),
        P("Date on which Tax deposited\n(dd/mm/yyyy)", "bold_c"),
        P("Challan Serial Number", "bold_c"),
        P("Status of matching with\nOLTAS*", "bold_c"),
    ]
    challan_data = [challan_header]
    for i, row in enumerate(emp["challan_rows"]):
        bg = LIGHT_BLUE if i % 2 == 0 else colors.white
        challan_data.append([
            P(str(row["sl"]), "body_c"),
            P(fmt(row["amount"]), "body_r"),
            P(row["bsr"], "body_c"),
            P(row["date"], "body_c"),
            P(row["serial"], "body_c"),
            P("F", "body_c"),
        ])
    challan_data.append([
        P("Total (Rs.)", "bold"), P(fmt(total_deducted), "body_r"),
        P("", "body"), P("", "body"), P("", "body"), P("", "body"),
    ])
    ch_table = Table(challan_data, colWidths=[10 * mm, 32 * mm, 32 * mm, 40 * mm, 40 * mm, 27 * mm])
    ch_style = [
        ("BACKGROUND",    (0, 0), (-1, 0), HEADER_BLUE),
        ("BOX",           (0, 0), (-1, -1), 0.5, TABLE_BORDER),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, TABLE_BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("FONTNAME",      (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND",    (0, -1), (-1, -1), LIGHT_BLUE),
    ]
    ch_table.setStyle(TableStyle(ch_style))
    story.append(ch_table)

    # Page break then verification
    story.append(PageBreak())

    # Remaining challan rows on page 2 (if any) — already all shown above
    # Verification
    tds_words = num_to_words(int(total_deducted))
    story.append(Spacer(1, 5 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=TABLE_BORDER))
    story.append(P("Verification", "bold_c"))
    story.append(Spacer(1, 2 * mm))
    verif_text = (
        f"I, <b>{emp['signatory_name']}</b>, son / daughter of <b>{emp['signatory_father']}</b> "
        f"working in the capacity of <b>{emp['signatory_designation']}</b> (designation) do hereby certify "
        f"that a sum of <b>Rs. {fmt(total_deducted)}</b> [Rs. {tds_words}] has been deducted and a sum of "
        f"<b>Rs. {fmt(total_deducted)}</b> [Rs. {tds_words}] has been deposited to the credit of the "
        "Central Government. I further certify that the information given above is true, complete and correct "
        "and is based on the books of account, documents, TDS statements, TDS deposited and other available records."
    )
    story.append(P(verif_text, "verif"))
    story.append(Spacer(1, 4 * mm))
    verif_sign = Table([
        [P(f"Place  {emp['signatory_place']}", "body"), P("", "body"),
         P("(Signature of person responsible for deduction of Tax)", "body_r")],
        [P(f"Date   {emp['sign_date']}", "body"),      P("", "body"), P("", "body")],
        [P("", "body"), P("", "body"),
         P(f"Designation: {emp['signatory_designation']}   Full Name: {emp['signatory_name']}", "bold")],
    ], colWidths=[55 * mm, 60 * mm, 70 * mm])
    verif_sign.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(verif_sign)
    story.append(Spacer(1, 4 * mm))

    # Notes
    notes = [
        "1. Part B (Annexure) of the certificate in Form No.16 shall be issued by the employer.",
        "2. If an assessee is employed under one employer during the year, Part 'A' of the certificate in Form No.16 issued for the quarter ending on 31st March of the financial year shall contain the details of tax deducted and deposited for all the quarters of the financial year.",
        "3. If an assessee is employed under more than one employer during the year, each of the employers shall issue Part A of the certificate in Form No.16 pertaining to the period for which such assessee was employed with each of the employers.",
        "4. To update PAN details in Income Tax Department database, apply for 'PAN change request' through NSDL or UTITSL.",
    ]
    story.append(P("<b>Notes:</b>", "note"))
    for n in notes:
        story.append(P(n, "note"))

    # Legend table
    story.append(Spacer(1, 3 * mm))
    story.append(P("Legend used in Form 16", "bold"))
    story.append(P("* Status of matching with OLTAS", "small"))
    legend_data = [
        [P("Legend", "bold_c"), P("Description", "bold_c"), P("Definition", "bold_c")],
        [P("U", "body_c"), P("Unmatched", "body"),
         P("Deductors have not deposited taxes or have furnished incorrect particulars of tax payment.", "small")],
        [P("P", "body_c"), P("Provisional", "body"),
         P("Provisional tax credit is effected only for TDS/TCS Statements filed by Government deductors.", "small")],
        [P("O", "body_c"), P("Overbooked", "body"),
         P("Payment details of TDS/TCS deposited in bank by deductor have matched with details mentioned in the TDS/TCS statement but the amount is over claimed.", "small")],
        [P("F", "body_c"), P("Final", "body"),
         P("Payment details of TDS/TCS deposited in bank by deductor have matched with the payment details mentioned in the TDS/TCS statement.", "small")],
    ]
    leg_table = Table(legend_data, colWidths=[12 * mm, 22 * mm, 148 * mm])
    leg_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BLUE),
        ("BOX",        (0, 0), (-1, -1), 0.5, TABLE_BORDER),
        ("INNERGRID",  (0, 0), (-1, -1), 0.3, TABLE_BORDER),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(leg_table)


# ── Part B builder ─────────────────────────────────────────────────────────────

def build_part_b(emp, story):
    story.append(PageBreak())
    story.append(_traces_header())
    story.append(HRFlowable(width="100%", thickness=1, color=TRACES_TEAL))
    story.append(Spacer(1, 2 * mm))
    story.append(P("FORM NO. 16", "title"))
    story.append(P("PART B", "part"))
    story.append(P(
        "Certificate under section 203 of the Income-tax Act, 1961 for tax deducted at source on salary "
        "paid to an employee under section 192 or pension/interest income of specified senior citizen under section 194P",
        "cert_desc"))
    story.append(HRFlowable(width="100%", thickness=0.5, color=TABLE_BORDER))

    # Cert no / last updated
    story.append(Table([[
        P(f"Certificate No.  {emp['certificate_no']}", "bold"),
        P(f"Last updated on   {emp['last_updated']}", "body_r"),
    ]], colWidths=[95 * mm, 90 * mm]))

    # Employer / Employee
    emp_table = Table([
        [P("Name and address of the Employer/Specified Bank", "bold_c"),
         P("Name and address of the Employee/Specified senior citizen", "bold_c")],
        [P(emp["employer_name"] + "\n" + emp["employer_address"], "body"),
         P(emp["employee_name"] + "\n" + emp["employee_address"], "body")],
    ], colWidths=[92 * mm, 92 * mm])
    emp_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BLUE),
        ("BOX",        (0, 0), (-1, -1), 0.5, TABLE_BORDER),
        ("INNERGRID",  (0, 0), (-1, -1), 0.3, TABLE_BORDER),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(emp_table)

    # PAN/TAN row
    pan_table = Table([
        [P("PAN of the Deductor", "bold_c"),
         P("TAN of the Deductor", "bold_c"),
         P("PAN of the Employee/Specified senior citizen", "bold_c")],
        [P(emp["employer_pan"], "body_c"),
         P(emp["employer_tan"], "body_c"),
         P(emp["employee_pan"], "body_c")],
    ], colWidths=[60 * mm, 60 * mm, 65 * mm])
    pan_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BLUE),
        ("BOX",        (0, 0), (-1, -1), 0.5, TABLE_BORDER),
        ("INNERGRID",  (0, 0), (-1, -1), 0.3, TABLE_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(pan_table)

    # CIT / AY / Period
    cit_table = Table([
        [P("CIT (TDS)", "bold_c"), P("Assessment Year", "bold_c"), P("Period with the Employer", "bold_c")],
        [P(emp["cit_address"], "body"), P(emp["assessment_year"], "body_c"),
         Table([[P("From", "bold_c"), P("To", "bold_c")],
                [P(emp["period_from"], "body_c"), P(emp["period_to"], "body_c")]],
               colWidths=[25 * mm, 25 * mm],
               style=TableStyle([("INNERGRID", (0,0),(-1,-1),0.3,TABLE_BORDER)]))],
    ], colWidths=[62 * mm, 22 * mm, 100 * mm])
    cit_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), HEADER_BLUE),
        ("BOX",           (0, 0), (-1, -1), 0.5, TABLE_BORDER),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, TABLE_BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(cit_table)
    story.append(Spacer(1, 2 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=TABLE_BORDER))
    story.append(P("Annexure - I", "bold"))
    story.append(P("Details of Salary Paid and any other income and tax deducted", "section"))

    s = emp["salary"]
    bac = "Yes" if emp.get("opted_115bac", False) else "No"
    story.append(Table([[
        P("Whether opting for taxation u/s 115BAC", "body"),
        P(bac, "bold"),
    ]], colWidths=[130 * mm, 55 * mm]))

    # Salary breakdown table
    COL1, COL2, COL3 = 130 * mm, 27 * mm, 28 * mm

    def sal_row(label, val1="", val2="", indent=0, bold_label=False):
        lb = "&nbsp;" * indent + label
        style_l = "bold" if bold_label else "body"
        return [P(lb, style_l), P(fmt(val1) if val1 != "" else "", "body_r"),
                P(fmt(val2) if val2 != "" else "", "body_r")]

    sal_data = [
        [P("1.", "bold"), P("Gross Salary", "bold"), P("Rs.", "bold_c"), P("Rs.", "bold_c")],
    ]
    # Restructure as single table with label + 2 amount columns
    sal_rows = [
        [P("1.", "bold"), P("Gross Salary", "bold"), P("Rs.", "bold_c"), P("Rs.", "bold_c")],
        [P("(a)", "body"), P("Salary as per provisions contained in section 17(1)", "body"),
         P(fmt(s["salary_17_1"]), "body_r"), P("", "body")],
        [P("(b)", "body"), P("Value of perquisites under section 17(2) (as per Form No. 12BA, wherever applicable)", "body"),
         P(fmt(s["perquisites_17_2"]), "body_r"), P("", "body")],
        [P("(c)", "body"), P("Profits in lieu of salary under section 17(3) (as per Form No. 12BA, wherever applicable)", "body"),
         P(fmt(s["profits_17_3"]), "body_r"), P("", "body")],
        [P("(d)", "body"), P("Total", "bold"), P("", "body"), P(fmt(s["gross_salary"]), "body_r")],
        [P("(e)", "body"), P("Reported total amount of salary received from other employer(s)", "body"),
         P("", "body"), P(fmt(s.get("other_employer_salary", 0)), "body_r")],
        [P("2.", "bold"), P("Less: Allowances to the extent exempt under section 10", "bold"), P("", "body"), P("", "body")],
        [P("(a)", "body"), P("Travel concession or assistance under section 10(5)", "body"),
         P(fmt(s["lta_10_5"]), "body_r"), P("", "body")],
        [P("(b)", "body"), P("Death-cum-retirement gratuity under section 10(10)", "body"),
         P(fmt(0), "body_r"), P("", "body")],
        [P("(c)", "body"), P("Commuted value of pension under section 10(10A)", "body"),
         P(fmt(0), "body_r"), P("", "body")],
        [P("(d)", "body"), P("Cash equivalent of leave salary encashment under section 10(10AA)", "body"),
         P(fmt(0), "body_r"), P("", "body")],
        [P("(e)", "body"), P("House rent allowance under section 10(13A)", "body"),
         P(fmt(s["hra_10_13a"]), "body_r"), P("", "body")],
        [P("(f)", "body"), P("Amount of any other exemption under section 10\n[Note: Break-up to be filled and signed by employer]", "body"),
         P("", "body"), P("", "body")],
        [P("(g)", "body"), P("Total amount of any other exemption under section 10", "body"),
         P(fmt(0), "body_r"), P("", "body")],
        [P("(h)", "body"), P("Total amount of exemption claimed under section 10 [2(a)+2(b)+2(c)+2(d)+2(e)+2(g)]", "body"),
         P("", "body"), P(fmt(s["total_exempt_10"]), "body_r")],
        [P("3.", "bold"), P("Total amount of salary received from current employer [1(d)-2(h)]", "bold"),
         P("", "body"), P(fmt(s["net_salary_from_employer"]), "body_r")],
        [P("4.", "bold"), P("Less: Deductions under section 16", "bold"), P("", "body"), P("", "body")],
        [P("(a)", "body"), P("Standard deduction under section 16(ia)", "body"),
         P(fmt(s["std_deduction"]), "body_r"), P("", "body")],
        [P("(b)", "body"), P("Entertainment allowance under section 16(ii)", "body"),
         P(fmt(s["entertainment_allow"]), "body_r"), P("", "body")],
        [P("(c)", "body"), P("Tax on employment under section 16(iii)", "body"),
         P(fmt(s["prof_tax"]), "body_r"), P("", "body")],
        [P("5.", "bold"), P("Total amount of deductions under section 16 [4(a)+4(b)+4(c)]", "bold"),
         P("", "body"), P(fmt(s["total_sec16"]), "body_r")],
        [P("6.", "bold"), P('Income chargeable under the head "Salaries" [(3+1(e)-5]', "bold"),
         P("", "body"), P(fmt(s["income_from_salary"]), "body_r")],
        [P("7.", "bold"), P("Add: Any other income reported by the employee under as per section 192 (2B)", "bold"),
         P("", "body"), P("", "body")],
        [P("(a)", "body"), P("Income (or admissible loss) from house property reported by employee offered for TDS", "body"),
         P(fmt(s.get("hp_income", 0)), "body_r"), P("", "body")],
        [P("(b)", "body"), P("Income under the head Other Sources offered for TDS", "body"),
         P(fmt(s.get("os_income", 0)), "body_r"), P("", "body")],
        [P("8.", "bold"), P("Total amount of other income reported by the employee [7(a)+7(b)]", "bold"),
         P("", "body"), P(fmt(s.get("hp_income", 0) + s.get("os_income", 0)), "body_r")],
        [P("9.", "bold"), P("Gross total income (6+8)", "bold"),
         P("", "body"), P(fmt(s["gross_total_income"]), "body_r")],
    ]
    sal_table = Table(sal_rows, colWidths=[10 * mm, 120 * mm, 27 * mm, 28 * mm])
    sal_style = [
        ("BOX",        (0, 0), (-1, -1), 0.5, TABLE_BORDER),
        ("INNERGRID",  (0, 0), (-1, -1), 0.3, TABLE_BORDER),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BLUE),
    ]
    sal_table.setStyle(TableStyle(sal_style))
    story.append(sal_table)

    # Page break for deductions
    story.append(PageBreak())

    # Chapter VI-A Deductions
    d = emp["deductions"]
    total_vi_a = d["total_vi_a"]
    taxable_income = s["gross_total_income"] - total_vi_a

    ded_header = [P("10.", "bold"), P("Deductions under Chapter VI-A", "bold"),
                  P("Gross Amount", "bold_c"), P("Deductible Amount", "bold_c")]
    ded_rows = [
        ded_header,
        [P("(a)", "body"),
         P("Deduction in respect of life insurance premia, contributions to provident fund etc. under section 80C", "body"),
         P(fmt(d["sec_80c"]), "body_r"), P(fmt(d["sec_80c"]), "body_r")],
        [P("(b)", "body"),
         P("Deduction in respect of contribution to certain pension funds under section 80CCC", "body"),
         P(fmt(d.get("sec_80ccc", 0)), "body_r"), P(fmt(d.get("sec_80ccc", 0)), "body_r")],
        [P("(c)", "body"),
         P("Deduction in respect of contribution by taxpayer to pension scheme under section 80CCD (1)", "body"),
         P(fmt(d.get("sec_80ccd1", 0)), "body_r"), P(fmt(d.get("sec_80ccd1", 0)), "body_r")],
        [P("(d)", "body"),
         P("Total deduction under section 80C, 80CCC and 80CCD(1)", "bold"),
         P(fmt(d["sec_80c"] + d.get("sec_80ccc", 0) + d.get("sec_80ccd1", 0)), "body_r"),
         P(fmt(d["sec_80c"] + d.get("sec_80ccc", 0) + d.get("sec_80ccd1", 0)), "body_r")],
        [P("(e)", "body"),
         P("Deductions in respect of amount paid/deposited to notified pension scheme under section 80CCD (1B)", "body"),
         P(fmt(d.get("sec_80ccd1b", 0)), "body_r"), P(fmt(d.get("sec_80ccd1b", 0)), "body_r")],
        [P("(f)", "body"),
         P("Deduction in respect of contribution by Employer to pension scheme under section 80CCD (2)", "body"),
         P(fmt(d.get("sec_80ccd2", 0)), "body_r"), P(fmt(d.get("sec_80ccd2", 0)), "body_r")],
        [P("(g)", "body"),
         P("Deduction in respect of health insurance premia under section 80D", "body"),
         P(fmt(d.get("sec_80d", 0)), "body_r"), P(fmt(d.get("sec_80d", 0)), "body_r")],
        [P("(h)", "body"),
         P("Deduction in respect of interest on loan taken for higher education under section 80E", "body"),
         P(fmt(d.get("sec_80e", 0)), "body_r"), P(fmt(d.get("sec_80e", 0)), "body_r")],
        [P("", "body"), P("", "body"), P("Gross\nAmount", "bold_c"),
         P("Qualifying\nAmount", "bold_c")],  # sub-header for 3-col items
        [P("(i)", "body"),
         P("Total Deduction in respect of donations to certain funds, charitable institutions, etc. under section 80G", "body"),
         P(fmt(0), "body_r"), P(fmt(0), "body_r")],
        [P("(j)", "body"),
         P("Deduction in respect of interest on deposits in savings account under section 80TTA", "body"),
         P(fmt(d.get("sec_80tta", 0)), "body_r"), P(fmt(d.get("sec_80tta", 0)), "body_r")],
        [P("(k)", "body"),
         P("Amount Deductible under any other provision (s) of Chapter VI-A\n[Note: Break-up to be filled and signed by employer]", "body"),
         P("", "body"), P("", "body")],
        [P("(l)", "body"),
         P("Total of amount deductible under any other provision(s) of Chapter VI-A", "body"),
         P(fmt(0), "body_r"), P(fmt(0), "body_r")],
        [P("11.", "bold"),
         P("Aggregate of deductible amount under Chapter VI-A [10(d)+10(e)+10(f)+10(g)+10(h)+10(i)+10(j)+10(l)]", "bold"),
         P("", "body"), P(fmt(total_vi_a), "body_r")],
        [P("12.", "bold"), P("Total taxable income (9-11)", "bold"),
         P("", "body"), P(fmt(taxable_income), "body_r")],
        [P("13.", "bold"), P("Tax on total income", "bold"),
         P("", "body"), P(fmt(emp["tax"]["tax_on_income"]), "body_r")],
        [P("14.", "bold"), P("Rebate under section 87A, if applicable", "bold"),
         P("", "body"), P(fmt(emp["tax"].get("rebate_87a", 0)), "body_r")],
        [P("15.", "bold"), P("Surcharge, wherever applicable", "bold"),
         P("", "body"), P(fmt(emp["tax"].get("surcharge", 0)), "body_r")],
        [P("16.", "bold"), P("Health and education cess", "bold"),
         P("", "body"), P(fmt(emp["tax"]["cess"]), "body_r")],
        [P("17.", "bold"), P("Tax payable (13+15+16-14)", "bold"),
         P("", "body"), P(fmt(emp["tax"]["tax_payable"]), "body_r")],
        [P("18.", "bold"), P("Less: Relief under section 89 (attach details)", "bold"),
         P("", "body"), P(fmt(0), "body_r")],
        [P("19.", "bold"), P("Net tax payable (17-18)", "bold"),
         P("", "body"), P(fmt(emp["tax"]["tax_payable"]), "body_r")],
    ]
    ded_table = Table(ded_rows, colWidths=[10 * mm, 120 * mm, 27 * mm, 28 * mm])
    ded_style = [
        ("BACKGROUND",    (0, 0), (-1, 0), HEADER_BLUE),
        ("BOX",           (0, 0), (-1, -1), 0.5, TABLE_BORDER),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, TABLE_BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        ("BACKGROUND",    (0, -3), (-1, -3), LIGHT_BLUE),  # tax payable
        ("BACKGROUND",    (0, -1), (-1, -1), LIGHT_BLUE),  # net tax
    ]
    ded_table.setStyle(TableStyle(ded_style))
    story.append(ded_table)
    story.append(Spacer(1, 4 * mm))

    # Verification Part B
    story.append(HRFlowable(width="100%", thickness=0.5, color=TABLE_BORDER))
    story.append(P("Verification", "bold_c"))
    story.append(Spacer(1, 2 * mm))
    verif_text = (
        f"I, <b>{emp['signatory_name']}</b>, son/daughter of <b>{emp['signatory_father']}</b>. "
        f"Working in the capacity of <b>{emp['signatory_designation']}</b> (Designation) do hereby certify "
        "that the information given above is true, complete and correct and is based on the books of account, "
        "documents, TDS statements, and other available records."
    )
    story.append(P(verif_text, "verif"))
    story.append(Spacer(1, 3 * mm))
    story.append(Table([
        [P(f"Place  {emp['signatory_place']}", "body"), P("", "body"),
         P("(Signature of person responsible for deduction of tax)", "body_r")],
        [P(f"Date   {emp['sign_date']}", "body"), P("", "body"),
         P(f"Full Name: {emp['signatory_name']}", "bold")],
    ], colWidths=[55 * mm, 60 * mm, 70 * mm]))


# ── Employee data ──────────────────────────────────────────────────────────────

EMPLOYEES = [
    {
        "filename": "form16_priya_sharma.pdf",
        "employee_name": "PRIYA SHARMA",
        "employee_address": "FLAT 302, SUNRISE APARTMENTS, KORAMANGALA 5TH BLOCK,\nBANGALORE - 560095, Karnataka",
        "employee_pan": "BAXPS7341R",
        "employer_name": "INFOSYS BPM LIMITED",
        "employer_address": "ELECTRONICS CITY, HOSUR ROAD,\nBANGALORE - 560100, Karnataka\n+(91)80-28520261\nHR@INFOSYSBPM.COM",
        "employer_pan": "AAACI1814H",
        "employer_tan": "BLRI03487E",
        "assessment_year": "2025-26",
        "period_from": "01-Apr-2023",
        "period_to": "31-Mar-2024",
        "certificate_no": "MLPQRST7",
        "last_updated": "15-May-2024",
        "cit_address": "The CIT (TDS)\nRoom No. 201, Income Tax Towers,\nResidency Road, Bangalore - 560025",
        "sign_date": "18-May-2024",
        "signatory_name": "RAJESH NAIR",
        "signatory_father": "KRISHNAN NAIR",
        "signatory_designation": "AUTHORISED SIGNATORY",
        "signatory_place": "BANGALORE",
        "opted_115bac": True,
        "quarters": [
            {"label": "Q1", "receipt": "ABCPQRST", "amount": 300000, "tds": 10338},
            {"label": "Q2", "receipt": "BCDRSTU V", "amount": 300000, "tds": 10337},
            {"label": "Q3", "receipt": "CDEFGHIJ", "amount": 300000, "tds": 10337},
            {"label": "Q4", "receipt": "DEFGHIJK", "amount": 300000, "tds": 10338},
        ],
        "challan_rows": [
            {"sl": 1, "amount": 10338, "bsr": "7560442", "date": "07-05-2023", "serial": "01234"},
            {"sl": 2, "amount": 10337, "bsr": "7560442", "date": "06-06-2023", "serial": "05678"},
            {"sl": 3, "amount": 10338, "bsr": "7560442", "date": "07-07-2023", "serial": "09012"},
            {"sl": 4, "amount": 10337, "bsr": "7560442", "date": "07-08-2023", "serial": "03456"},
            {"sl": 5, "amount": 10337, "bsr": "7560442", "date": "07-09-2023", "serial": "07890"},
            {"sl": 6, "amount": 10337, "bsr": "7560442", "date": "06-10-2023", "serial": "02345"},
            {"sl": 7, "amount": 10338, "bsr": "7560442", "date": "07-11-2023", "serial": "06789"},
            {"sl": 8, "amount": 10337, "bsr": "7560442", "date": "07-12-2023", "serial": "01023"},
            {"sl": 9, "amount": 10338, "bsr": "7560442", "date": "05-01-2024", "serial": "04567"},
            {"sl": 10, "amount": 10337, "bsr": "7560442", "date": "07-02-2024", "serial": "08901"},
            {"sl": 11, "amount": 10337, "bsr": "7560442", "date": "07-03-2024", "serial": "03234"},
            {"sl": 12, "amount": 10338, "bsr": "7560442", "date": "22-04-2024", "serial": "05678"},
        ],
        "salary": {
            "salary_17_1":          1200000,
            "perquisites_17_2":           0,
            "profits_17_3":               0,
            "gross_salary":         1200000,
            "lta_10_5":                   0,
            "hra_10_13a":            180000,
            "total_exempt_10":       180000,
            "net_salary_from_employer": 1020000,  # 1200000 - 180000
            "std_deduction":          50000,
            "entertainment_allow":        0,
            "prof_tax":                2400,
            "total_sec16":            52400,
            "income_from_salary":    967600,      # 1020000 - 52400
            "hp_income":                  0,
            "os_income":                  0,
            "gross_total_income":    967600,
        },
        "deductions": {
            "sec_80c":               0,
            "sec_80ccc":             0,
            "sec_80ccd1":            0,
            "sec_80ccd1b":           0,
            "sec_80ccd2":       120000,   # employer NPS
            "sec_80d":               0,
            "sec_80e":               0,
            "sec_80tta":             0,
            "total_vi_a":       120000,
        },
        "tax": {
            # Taxable = 967600 - 120000 = 847600
            # New regime: 0-3L=0, 3-6L=15000, 6-8.476L=24760 → 39760
            "tax_on_income":    39760,
            "rebate_87a":           0,
            "surcharge":            0,
            "cess":              1590,   # 4% of 39760
            "tax_payable":      41350,
        },
    },

    {
        "filename": "form16_rohit_mehta.pdf",
        "employee_name": "ROHIT MEHTA",
        "employee_address": "B-12, SEA VIEW APARTMENTS, BANDRA WEST,\nMUMBAI - 400050, Maharashtra",
        "employee_pan": "CVHPM3829K",
        "employer_name": "TATA CONSULTANCY SERVICES LIMITED",
        "employer_address": "TCS HOUSE, RAVELINE STREET, FORT,\nMUMBAI - 400001, Maharashtra\n+(91)22-67789100\nHR@TCS.COM",
        "employer_pan": "AAACT3518Q",
        "employer_tan": "MUMM08837B",
        "assessment_year": "2025-26",
        "period_from": "01-Apr-2023",
        "period_to": "31-Mar-2024",
        "certificate_no": "TCSABCDE",
        "last_updated": "20-May-2024",
        "cit_address": "The CIT (TDS)\nAayakar Bhavan, M.K. Road,\nMumbai - 400020",
        "sign_date": "20-May-2024",
        "signatory_name": "SURESH MALHOTRA",
        "signatory_father": "RAMESH MALHOTRA",
        "signatory_designation": "VP - HUMAN RESOURCES",
        "signatory_place": "MUMBAI",
        "opted_115bac": True,
        "quarters": [
            {"label": "Q1", "receipt": "EFGHIJKL", "amount": 500000, "tds": 38875},
            {"label": "Q2", "receipt": "FGHIJKLM", "amount": 500000, "tds": 38875},
            {"label": "Q3", "receipt": "GHIJKLMN", "amount": 525000, "tds": 38875},
            {"label": "Q4", "receipt": "HIJKLMNO", "amount": 525000, "tds": 38876},
        ],
        "challan_rows": [
            {"sl": 1, "amount": 38875, "bsr": "0020121", "date": "07-05-2023", "serial": "12345"},
            {"sl": 2, "amount": 38875, "bsr": "0020121", "date": "07-06-2023", "serial": "23456"},
            {"sl": 3, "amount": 38875, "bsr": "0020121", "date": "07-07-2023", "serial": "34567"},
            {"sl": 4, "amount": 38875, "bsr": "0020121", "date": "07-08-2023", "serial": "45678"},
            {"sl": 5, "amount": 38875, "bsr": "0020121", "date": "07-09-2023", "serial": "56789"},
            {"sl": 6, "amount": 38875, "bsr": "0020121", "date": "06-10-2023", "serial": "67890"},
            {"sl": 7, "amount": 38875, "bsr": "0020121", "date": "07-11-2023", "serial": "78901"},
            {"sl": 8, "amount": 38875, "bsr": "0020121", "date": "07-12-2023", "serial": "89012"},
            {"sl": 9, "amount": 38875, "bsr": "0020121", "date": "05-01-2024", "serial": "90123"},
            {"sl": 10, "amount": 38875, "bsr": "0020121", "date": "07-02-2024", "serial": "01234"},
            {"sl": 11, "amount": 38875, "bsr": "0020121", "date": "07-03-2024", "serial": "12305"},
            {"sl": 12, "amount": 38876, "bsr": "0020121", "date": "20-04-2024", "serial": "23456"},
        ],
        "salary": {
            "salary_17_1":          2000000,
            "perquisites_17_2":       50000,   # car perk
            "profits_17_3":               0,
            "gross_salary":         2050000,
            "lta_10_5":                   0,
            "hra_10_13a":            300000,
            "total_exempt_10":       300000,
            "net_salary_from_employer": 1750000,
            "std_deduction":          50000,
            "entertainment_allow":        0,
            "prof_tax":                2400,
            "total_sec16":            52400,
            "income_from_salary":   1697600,
            "hp_income":                  0,
            "os_income":                  0,
            "gross_total_income":   1697600,
        },
        "deductions": {
            "sec_80c":               0,
            "sec_80ccc":             0,
            "sec_80ccd1":            0,
            "sec_80ccd1b":           0,
            "sec_80ccd2":       200000,
            "sec_80d":               0,
            "sec_80e":               0,
            "sec_80tta":             0,
            "total_vi_a":       200000,
        },
        "tax": {
            # Taxable = 1697600 - 200000 = 1497600
            # 0-3L=0, 3-6L=15000, 6-9L=30000, 9-12L=45000, 12-14.976L=20%*297600=59520 → 149520
            "tax_on_income":   149520,
            "rebate_87a":           0,
            "surcharge":            0,
            "cess":              5981,   # 4% of 149520
            "tax_payable":     155501,
        },
    },

    {
        "filename": "form16_ananya_krishnan.pdf",
        "employee_name": "ANANYA KRISHNAN",
        "employee_address": "PLOT 7, SHIVAJI NAGAR, PIMPRI,\nPUNE - 411017, Maharashtra",
        "employee_pan": "DKNPA5612F",
        "employer_name": "WIPRO LIMITED",
        "employer_address": "DODDAKANNELLI, SARJAPUR ROAD,\nBANGALORE - 560035, Karnataka\n+(91)80-28440011\nHR@WIPRO.COM",
        "employer_pan": "AAACW0969J",
        "employer_tan": "PNQW01593G",
        "assessment_year": "2025-26",
        "period_from": "01-Apr-2023",
        "period_to": "31-Mar-2024",
        "certificate_no": "WPRABCDE",
        "last_updated": "10-May-2024",
        "cit_address": "The CIT (TDS)\nAayakar Bhavan, Senapati Bapat Road,\nPune - 411016",
        "sign_date": "12-May-2024",
        "signatory_name": "PRADEEP SHARMA",
        "signatory_father": "MOHAN SHARMA",
        "signatory_designation": "GENERAL MANAGER - HR",
        "signatory_place": "PUNE",
        "opted_115bac": True,
        "quarters": [
            {"label": "Q1", "receipt": "PQRSTUVW", "amount": 240000, "tds":  8778},
            {"label": "Q2", "receipt": "QRSTUVWX", "amount": 240000, "tds":  8777},
            {"label": "Q3", "receipt": "RSTUVWXY", "amount": 240000, "tds":  8778},
            {"label": "Q4", "receipt": "STUVWXYZ", "amount": 240000, "tds":  8777},
        ],
        "challan_rows": [
            {"sl": 1, "amount":  8778, "bsr": "5120021", "date": "07-05-2023", "serial": "22222"},
            {"sl": 2, "amount":  8777, "bsr": "5120021", "date": "07-06-2023", "serial": "33333"},
            {"sl": 3, "amount":  8778, "bsr": "5120021", "date": "07-07-2023", "serial": "44444"},
            {"sl": 4, "amount":  8777, "bsr": "5120021", "date": "07-08-2023", "serial": "55555"},
            {"sl": 5, "amount":  8778, "bsr": "5120021", "date": "07-09-2023", "serial": "66666"},
            {"sl": 6, "amount":  8777, "bsr": "5120021", "date": "06-10-2023", "serial": "77777"},
            {"sl": 7, "amount":  8778, "bsr": "5120021", "date": "07-11-2023", "serial": "88888"},
            {"sl": 8, "amount":  8777, "bsr": "5120021", "date": "07-12-2023", "serial": "99999"},
            {"sl": 9, "amount":  8778, "bsr": "5120021", "date": "05-01-2024", "serial": "11011"},
            {"sl": 10, "amount": 8777, "bsr": "5120021", "date": "07-02-2024", "serial": "22022"},
            {"sl": 11, "amount": 8778, "bsr": "5120021", "date": "07-03-2024", "serial": "33033"},
            {"sl": 12, "amount": 8777, "bsr": "5120021", "date": "15-Apr-2024", "serial": "44044"},
        ],
        "salary": {
            "salary_17_1":           960000,
            "perquisites_17_2":           0,
            "profits_17_3":               0,
            "gross_salary":          960000,
            "lta_10_5":                   0,
            "hra_10_13a":            120000,
            "total_exempt_10":       120000,
            "net_salary_from_employer": 840000,
            "std_deduction":          50000,
            "entertainment_allow":        0,
            "prof_tax":                2400,
            "total_sec16":            52400,
            "income_from_salary":    787600,
            "hp_income":                  0,
            "os_income":                  0,
            "gross_total_income":    787600,
        },
        "deductions": {
            "sec_80c":               0,
            "sec_80ccc":             0,
            "sec_80ccd1":            0,
            "sec_80ccd1b":           0,
            "sec_80ccd2":            0,
            "sec_80d":               0,
            "sec_80e":               0,
            "sec_80tta":             0,
            "total_vi_a":            0,
        },
        "tax": {
            # Taxable = 787600
            # New regime: 0-3L=0, 3-6L=15000, 6-7.876L=10%*187600=18760 → 33760
            # 87A: income 787600 > 700000, no rebate
            "tax_on_income":    33760,
            "rebate_87a":           0,
            "surcharge":            0,
            "cess":              1350,   # 4% of 33760
            "tax_payable":      35110,
        },
    },

    {
        "filename": "form16_arjun_singh.pdf",
        "employee_name": "ARJUN SINGH",
        "employee_address": "221, VASANT KUNJ, SECTOR-C,\nNEW DELHI - 110070, Delhi",
        "employee_pan": "FLZAS9034N",
        "employer_name": "HDFC BANK LIMITED",
        "employer_address": "HDFC BANK HOUSE, SENAPATI BAPAT MARG,\nLOWER PAREL, MUMBAI - 400013, Maharashtra\n+(91)22-66521000\nHR@HDFCBANK.COM",
        "employer_pan": "AAACH2702H",
        "employer_tan": "DELH05461E",
        "assessment_year": "2025-26",
        "period_from": "01-Apr-2023",
        "period_to": "31-Mar-2024",
        "certificate_no": "HDFCXYZ9",
        "last_updated": "25-May-2024",
        "cit_address": "The CIT (TDS)\nCentral Revenue Building, I.P. Estate,\nNew Delhi - 110002",
        "sign_date": "25-May-2024",
        "signatory_name": "MEENA AGARWAL",
        "signatory_father": "VINOD AGARWAL",
        "signatory_designation": "CHIEF PEOPLE OFFICER",
        "signatory_place": "MUMBAI",
        "opted_115bac": True,
        "quarters": [
            {"label": "Q1", "receipt": "UVWXYZAB", "amount": 450000, "tds": 29411},
            {"label": "Q2", "receipt": "VWXYZABC", "amount": 450000, "tds": 29412},
            {"label": "Q3", "receipt": "WXYZABCD", "amount": 450000, "tds": 29411},
            {"label": "Q4", "receipt": "XYZABCDE", "amount": 450000, "tds": 29411},
        ],
        "challan_rows": [
            {"sl":  1, "amount": 29411, "bsr": "0510001", "date": "07-05-2023", "serial": "11111"},
            {"sl":  2, "amount": 29412, "bsr": "0510001", "date": "07-06-2023", "serial": "22211"},
            {"sl":  3, "amount": 29411, "bsr": "0510001", "date": "07-07-2023", "serial": "33311"},
            {"sl":  4, "amount": 29411, "bsr": "0510001", "date": "07-08-2023", "serial": "44411"},
            {"sl":  5, "amount": 29411, "bsr": "0510001", "date": "07-09-2023", "serial": "55511"},
            {"sl":  6, "amount": 29412, "bsr": "0510001", "date": "06-10-2023", "serial": "66611"},
            {"sl":  7, "amount": 29411, "bsr": "0510001", "date": "07-11-2023", "serial": "77711"},
            {"sl":  8, "amount": 29411, "bsr": "0510001", "date": "07-12-2023", "serial": "88811"},
            {"sl":  9, "amount": 29411, "bsr": "0510001", "date": "05-01-2024", "serial": "99911"},
            {"sl": 10, "amount": 29411, "bsr": "0510001", "date": "07-02-2024", "serial": "10011"},
            {"sl": 11, "amount": 29411, "bsr": "0510001", "date": "07-03-2024", "serial": "11111"},
            {"sl": 12, "amount": 29412, "bsr": "0510001", "date": "20-04-2024", "serial": "12211"},
        ],
        "salary": {
            "salary_17_1":          1800000,
            "perquisites_17_2":           0,
            "profits_17_3":               0,
            "gross_salary":         1800000,
            "lta_10_5":               36000,
            "hra_10_13a":            252000,
            "total_exempt_10":       288000,
            "net_salary_from_employer": 1512000,
            "std_deduction":          50000,
            "entertainment_allow":        0,
            "prof_tax":                2400,
            "total_sec16":            52400,
            "income_from_salary":   1459600,
            "hp_income":                  0,
            "os_income":                  0,
            "gross_total_income":   1459600,
        },
        "deductions": {
            "sec_80c":               0,
            "sec_80ccc":             0,
            "sec_80ccd1":            0,
            "sec_80ccd1b":           0,
            "sec_80ccd2":       180000,
            "sec_80d":               0,
            "sec_80e":               0,
            "sec_80tta":             0,
            "total_vi_a":       180000,
        },
        "tax": {
            # Taxable = 1459600 - 180000 = 1279600
            # 0-3L=0, 3-6L=15000, 6-9L=30000, 9-12L=45000, 12-12.796L=20%*79600=15920 → 105920
            "tax_on_income":   105920,
            "rebate_87a":           0,
            "surcharge":            0,
            "cess":              4237,   # 4% of 105920
            "tax_payable":     110157,
        },
    },
]


# ── Generate all PDFs ──────────────────────────────────────────────────────────

def generate(emp: dict, out_dir: str = "."):
    out_path = os.path.join(out_dir, emp["filename"])
    total_pages = 4  # Part A: 2 pages, Part B: 2 pages

    doc = SimpleDocTemplate(
        out_path,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=12 * mm,
        bottomMargin=22 * mm,
    )

    story = []
    build_part_a(emp, story)
    build_part_b(emp, story)

    cert_no = emp["certificate_no"]

    def footer_fn(canvas_obj, doc):
        _footer(canvas_obj, doc, emp, cert_no, total_pages)

    doc.build(story, onFirstPage=footer_fn, onLaterPages=footer_fn)
    print(f"Generated: {out_path}")


if __name__ == "__main__":
    out = "sample_form16s"
    os.makedirs(out, exist_ok=True)
    for emp in EMPLOYEES:
        generate(emp, out)
    print(f"\nAll 4 Form 16s saved to: {out}/")