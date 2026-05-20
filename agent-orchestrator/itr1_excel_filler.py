"""
ITR-1 Excel Form Filler
========================
Takes parsed form data (from the agent pipeline) and generates a clean,
single-sheet Excel (.xlsx) summary.
"""

from __future__ import annotations
import uuid
import warnings
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill

warnings.filterwarnings("ignore")

# Paths
PROJECT_ROOT  = Path(__file__).parent.parent
OUTPUT_DIR    = PROJECT_ROOT / "agent-orchestrator" / "filled_forms"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def _get_nested(data: dict, dot_path: str) -> Any:
    parts = dot_path.split(".")
    cur = data
    for p in parts:
        if isinstance(cur, dict):
            cur = cur.get(p)
        elif isinstance(cur, list):
            try:
                cur = cur[int(p)]
            except (ValueError, IndexError):
                return None
        else:
            return None
        if cur is None:
            return None
    return cur

def _fmt(val: Any, is_numeric: bool = False) -> Any:
    if val is None:
        return 0 if is_numeric else ""
    if is_numeric:
        try:
            return round(float(val))
        except (ValueError, TypeError):
            return 0
    return str(val)

def _add_section(ws, row, title):
    cell = ws.cell(row=row, column=1, value=title)
    cell.font = Font(bold=True, size=14, color="FFFFFF")
    cell.fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
    cell.alignment = Alignment(vertical="center")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
    return row + 1

def _add_row(ws, row, label, value, is_numeric=False):
    c1 = ws.cell(row=row, column=1, value=label)
    c1.font = Font(bold=True)
    c1.alignment = Alignment(wrap_text=True, vertical="center")
    
    val = _fmt(value, is_numeric)
    c2 = ws.cell(row=row, column=2, value=val)
    c2.alignment = Alignment(vertical="center")
    if is_numeric:
        c2.number_format = '₹#,##0'
        c2.alignment = Alignment(horizontal="right", vertical="center")
        
    return row + 1

def fill_itr1_excel(itr_data: dict, session_id: str) -> Path:
    unique_id = uuid.uuid4().hex[:8]
    out_path = OUTPUT_DIR / f"ITR1_filled_{session_id}_{unique_id}.xlsx"
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "ITR-1 Summary"
    
    ws.column_dimensions['A'].width = 45
    ws.column_dimensions['B'].width = 25
    ws.column_dimensions['C'].width = 15
    
    form = itr_data.get("itr1_form", itr_data)
    
    title = ws.cell(row=1, column=1, value="ITR-1 Form Summary (AY 2025-26)")
    title.font = Font(bold=True, size=18)
    ws.merge_cells("A1:C1")
    
    r = 3
    
    # Personal Info
    r = _add_section(ws, r, "Part A: Personal Information")
    r = _add_row(ws, r, "First Name", _get_nested(form, "personal_info.first_name"))
    r = _add_row(ws, r, "Last Name", _get_nested(form, "personal_info.last_name"))
    r = _add_row(ws, r, "PAN", _get_nested(form, "personal_info.pan"))
    r = _add_row(ws, r, "Aadhaar", _get_nested(form, "personal_info.aadhaar"))
    r = _add_row(ws, r, "Date of Birth", _get_nested(form, "personal_info.dob"))
    r = _add_row(ws, r, "Email", _get_nested(form, "personal_info.email"))
    r = _add_row(ws, r, "Mobile", _get_nested(form, "personal_info.mobile"))
    r = _add_row(ws, r, "Bank Account", _get_nested(form, "personal_info.bank_account_number") or _get_nested(form, "personal_info.bank_account"))
    r = _add_row(ws, r, "IFSC", _get_nested(form, "personal_info.bank_ifsc"))
    r += 1
    
    # Salary Income
    r = _add_section(ws, r, "Schedule S: Salary Income")
    r = _add_row(ws, r, "Gross Salary", _get_nested(form, "salary_income.gross_salary"), True)
    r = _add_row(ws, r, "Less: Exempt Allowances", _get_nested(form, "salary_income.total_exempt_allowances"), True)
    r = _add_row(ws, r, "Net Salary", _get_nested(form, "salary_income.net_salary"), True)
    r = _add_row(ws, r, "Less: Standard Deduction (16ia)", _get_nested(form, "salary_income.standard_deduction_16ia"), True)
    r = _add_row(ws, r, "Less: Professional Tax", _get_nested(form, "salary_income.professional_tax_16iii"), True)
    r = _add_row(ws, r, "Income Chargeable under Salaries", _get_nested(form, "salary_income.taxable_salary"), True)
    r += 1

    # House Property
    r = _add_section(ws, r, "Schedule HP: House Property")
    r = _add_row(ws, r, "Income / (Loss) from House Property", _get_nested(form, "house_property.total_income_hp"), True)
    r += 1
    
    # Other Sources
    r = _add_section(ws, r, "Schedule OS: Other Sources")
    r = _add_row(ws, r, "Savings Bank Interest", _get_nested(form, "other_sources.savings_bank_interest"), True)
    r = _add_row(ws, r, "Fixed Deposit Interest", _get_nested(form, "other_sources.fd_interest"), True)
    r = _add_row(ws, r, "Dividends", _get_nested(form, "other_sources.dividends"), True)
    r = _add_row(ws, r, "Total Other Sources Income", _get_nested(form, "other_sources.total_other_sources"), True)
    r += 1
    
    # Deductions
    r = _add_section(ws, r, "Chapter VI-A Deductions")
    r = _add_row(ws, r, "80CCD(2) - Employer NPS", _get_nested(form, "deductions.sec_80ccd_2"), True)
    r = _add_row(ws, r, "Total Deductions (New Regime)", _get_nested(form, "deductions.total_deductions"), True)
    r += 1
    
    # Tax Computation
    r = _add_section(ws, r, "Part B-ATI: Tax Computation")
    r = _add_row(ws, r, "Gross Total Income", _get_nested(form, "tax_computation.gross_total_income"), True)
    r = _add_row(ws, r, "Total Taxable Income", _get_nested(form, "tax_computation.taxable_income"), True)
    r = _add_row(ws, r, "Tax on Total Income", _get_nested(form, "tax_computation.tax_before_rebate"), True)
    r = _add_row(ws, r, "Rebate u/s 87A", _get_nested(form, "tax_computation.rebate_87a"), True)
    r = _add_row(ws, r, "Health & Education Cess", _get_nested(form, "tax_computation.health_education_cess"), True)
    r = _add_row(ws, r, "Total Tax Liability", _get_nested(form, "tax_computation.total_tax_liability"), True)
    r += 1
    
    # TDS and Taxes Paid
    r = _add_section(ws, r, "Taxes Paid")
    tds = _get_nested(form, "tds_details") or []
    if tds and isinstance(tds, list) and len(tds) > 0:
        r = _add_row(ws, r, "Employer Name", _get_nested(tds[0], "employer_name"), False)
        r = _add_row(ws, r, "Employer TAN", _get_nested(tds[0], "employer_tan"), False)
    r = _add_row(ws, r, "Total TDS Deducted", _get_nested(form, "tax_computation.tds_deducted"), True)
    r = _add_row(ws, r, "Tax Payable", _get_nested(form, "tax_computation.tax_payable"), True)
    r = _add_row(ws, r, "Refund", _get_nested(form, "tax_computation.refund"), True)
    
    wb.save(str(out_path))
    return out_path

def get_filled_form_path(session_id: str) -> Path | None:
    p = OUTPUT_DIR / f"ITR1_filled_{session_id}.xlsx"
    return p if p.exists() else None

def export_to_pdf_win32(excel_path: Path) -> Path:
    import win32com.client
    import pythoncom
    
    pdf_path = excel_path.with_suffix(".pdf")
    if pdf_path.exists():
        pdf_path.unlink()
        
    pythoncom.CoInitialize()
    excel = None
    try:
        excel = win32com.client.Dispatch("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        excel.AutomationSecurity = 3
        
        wb = excel.Workbooks.Open(str(excel_path.resolve()))
        wb.ActiveSheet.ExportAsFixedFormat(0, str(pdf_path.resolve()))
        wb.Close(SaveChanges=False)
    except Exception as e:
        print(f"Failed to export PDF via win32com: {e}")
        raise
    finally:
        if excel:
            excel.Quit()
        pythoncom.CoUninitialize()
        
    return pdf_path
