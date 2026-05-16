"""
Bank Statement Parser
=====================
Hybrid Text-Vision extraction.
Enhancement: Also extracts personal info (account number, IFSC, bank name, holder name)
from statement headers for the ITR-1 personal info section.
Uses SHA256 cache for deterministic results.
"""

from __future__ import annotations
import sys
import json
import base64
import hashlib
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import fitz
from .pdf_utils import pdf_to_structured_text
from shared.llm_client import complete_with_system, complete_vision

_CACHE_DIR = Path(__file__).parent.parent.parent / "uploads" / "cache"


@dataclass
class Transaction:
    date:        str
    description: str
    amount:      float
    category:    str   # "salary", "interest_savings", "interest_fd", "tax_deducted", "other"

@dataclass
class BankStatementData:
    bank_name:               Optional[str] = None
    account_number:          Optional[str] = None
    name:                    Optional[str] = None
    ifsc_code:               Optional[str] = None     # NEW: extracted from header
    period_from:             Optional[str] = None
    period_to:               Optional[str] = None

    total_salary_credits:    float = 0.0
    total_savings_interest:  float = 0.0
    total_fd_interest:       float = 0.0
    total_tds_deducted:      float = 0.0

    transactions:            list[Transaction] = field(default_factory=list)
    parse_confidence:        float = 0.0
    warnings:                list  = field(default_factory=list)


# ── Cache utilities ────────────────────────────────────────────────────────────

def _pdf_hash(pdf_path: str) -> str:
    h = hashlib.sha256()
    with open(pdf_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _load_cache(cache_key: str) -> Optional[BankStatementData]:
    try:
        cache_file = _CACHE_DIR / f"{cache_key}_bank.json"
        if cache_file.exists():
            with open(cache_file, encoding="utf-8") as f:
                d = json.load(f)
            res = BankStatementData()
            txs = d.pop("transactions", [])
            for k, v in d.items():
                if hasattr(res, k):
                    setattr(res, k, v)
            for t in txs:
                try:
                    res.transactions.append(Transaction(**t))
                except:
                    pass
            print(f"[BankStatement] Cache hit ({cache_key}) — returning cached result.")
            return res
    except Exception as e:
        print(f"[BankStatement] Cache read error: {e}")
    return None


def _save_cache(cache_key: str, result: BankStatementData):
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = _CACHE_DIR / f"{cache_key}_bank.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(asdict(result), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[BankStatement] Cache write error: {e}")


def extract_pdf_images(pdf_path: str, max_pages: int = 5) -> list[str]:
    doc = fitz.open(pdf_path)
    b64_imgs = []
    zoom = fitz.Matrix(1.5, 1.5)
    for i in range(min(len(doc), max_pages)):
        page = doc.load_page(i)
        img_bytes = page.get_pixmap(matrix=zoom).tobytes("png")
        b64_imgs.append(base64.b64encode(img_bytes).decode("utf-8"))
    doc.close()
    return b64_imgs


_BANK_SYSTEM = """You are an elite bank statement extractor.
Analyze the bank statement text/image and return ONLY a valid, raw JSON object.

CRITICAL RULES:
1. Extract ONLY values actually printed in the document. Do NOT guess or compute.
2. For totals: sum only transactions of that specific category from the transactions list.
3. IFSC code is usually a 11-character alphanumeric code like SBIN0001234 or HDFC0002345.
4. account_number is usually a long numeric string (10-18 digits).

Required JSON keys:
{
  "bank_name": "string or null",
  "account_number": "string or null",
  "name": "string or null",
  "ifsc_code": "string or null",
  "period_from": "string or null",
  "period_to": "string or null",
  "total_salary_credits": 0.0,
  "total_savings_interest": 0.0,
  "total_fd_interest": 0.0,
  "total_tds_deducted": 0.0,
  "transactions": [
    {"date": "DD/MM/YYYY", "description": "...", "amount": 0.0, "category": "salary|interest_savings|interest_fd|tax_deducted|other"}
  ]
}

Category rules:
- "salary": credits with descriptions containing NEFT/PAYROLL/SAL/SALARY/PAYROLL
- "interest_savings": credits with INT CREDITED/SB INT/QUARTERLY INT/SAVINGS INTEREST
- "interest_fd": credits with FD INT/TERM DEPOSIT/TDR INT/FIXED DEPOSIT INTEREST
- "tax_deducted": debits with TDS/TAX DEDUCTED AT SOURCE
- "other": everything else

Convert all amounts to clean floats. Debit amounts should be negative."""


def parse_bank_statement(pdf_path: str) -> BankStatementData:
    # ── Check cache first ─────────────────────────────────────────────────────
    cache_key = _pdf_hash(pdf_path)
    cached = _load_cache(cache_key)
    if cached is not None:
        return cached

    # 1. Try Structured Text Parsing first (Best for Digital PDFs)
    structured_text = pdf_to_structured_text(pdf_path)
    result_data = None

    if len(structured_text.strip()) > 150:
        print("[BankStatement] Using Structured Text parsing...")
        try:
            response = complete_with_system(
                system=_BANK_SYSTEM,
                user=f"Extract data from this structured statement text:\n\n{structured_text[:12000]}"
            )
            cleaned = response.replace("```json", "").replace("```", "").strip()
            result_data = json.loads(cleaned)
        except Exception as e:
            print(f"[BankStatement] Text parsing failed: {e}")

    # 2. Vision Fallback (Only if Text Parsing failed or returned no data)
    if not result_data or not result_data.get("bank_name"):
        print("[BankStatement] Falling back to Vision AI (OCR)...")
        try:
            b64_images = extract_pdf_images(pdf_path, max_pages=5)
            response = complete_vision(
                prompt="Analyze this bank statement and return the requested JSON schema.",
                base64_images=b64_images,
                system=_BANK_SYSTEM
            )
            cleaned = response.replace("```json", "").replace("```", "").strip()
            result_data = json.loads(cleaned)
        except Exception as e:
            print(f"[BankStatement] Vision fallback failed: {e}")
            err = BankStatementData()
            err.warnings.append(f"Vision Parsing failed: {str(e)}")
            return err

    # 3. Build Final Object
    res = BankStatementData()
    txs = result_data.pop("transactions", [])

    # Fill basic fields
    for k, v in result_data.items():
        if hasattr(res, k) and v is not None:
            if isinstance(getattr(res, k), float):
                try:
                    clean_v = str(v).replace(",", "").replace(" ", "").strip()
                    setattr(res, k, float(clean_v) if clean_v else 0.0)
                except:
                    pass
            else:
                setattr(res, k, str(v).strip())

    # Fill transactions
    for t in txs:
        try:
            res.transactions.append(Transaction(
                date=str(t.get("date", "")),
                description=str(t.get("description", "")),
                amount=float(str(t.get("amount", 0)).replace(",", "")),
                category=str(t.get("category", "other"))
            ))
        except:
            pass

    # ── Post-parse: recompute totals from transaction list if LLM totals are 0 ──
    if res.total_savings_interest == 0 and res.transactions:
        res.total_savings_interest = sum(
            t.amount for t in res.transactions if t.category == "interest_savings" and t.amount > 0
        )
    if res.total_fd_interest == 0 and res.transactions:
        res.total_fd_interest = sum(
            t.amount for t in res.transactions if t.category == "interest_fd" and t.amount > 0
        )
    if res.total_salary_credits == 0 and res.transactions:
        res.total_salary_credits = sum(
            t.amount for t in res.transactions if t.category == "salary" and t.amount > 0
        )
    if res.total_tds_deducted == 0 and res.transactions:
        res.total_tds_deducted = abs(sum(
            t.amount for t in res.transactions if t.category == "tax_deducted"
        ))

    res.parse_confidence = 1.0

    # ── Save to cache ─────────────────────────────────────────────────────────
    _save_cache(cache_key, res)
    return res


def bank_statement_to_dict(data: BankStatementData) -> dict:
    return asdict(data)
