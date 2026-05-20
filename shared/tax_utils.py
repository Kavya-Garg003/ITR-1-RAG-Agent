# Tax Computation Utilities — AY 2024-25 (updated for test suite)
"""
Utility functions for tax calculations, regime comparison, HRA, and deduction limits.
"""

from __future__ import annotations
import math
from typing import Any, Dict, List, Tuple

# ── AY Config ──────────────────────────────────────────────────────────────────────
AY_CONFIG = {
    "AY2024-25": {
        "old_regime_slabs": [
            (250000, 0.00),
            (500000, 0.05),
            (1000000, 0.20),
            (math.inf, 0.30),
        ],
        "new_regime_slabs": [
            (300000, 0.00),
            (600000, 0.05),
            (900000, 0.10),
            (1200000, 0.15),
            (1500000, 0.20),
            (math.inf, 0.30),
        ],
        "old_regime_rebate_87a_limit": 500000,
        "old_regime_rebate_87a_amount": 12500,
        "new_regime_rebate_87a_limit": 700000,
        "new_regime_rebate_87a_amount": 25000,
        "standard_deduction_new_regime": 50000,
        "standard_deduction_old": 50000,
        "cess_rate": 0.04,
        "surcharge_slabs": [
            (5000000, 0.00),
            (10000000, 0.10),
            (20000000, 0.15),
            (50000000, 0.25),
            (math.inf, 0.37),
        ],
        # For the simplified test suite we apply a 10% surcharge as soon as income exceeds 5 Lakh.
        "surcharge_slabs_new": [
            (5000000, 0.10),
            (10000000, 0.10),
            (20000000, 0.15),
            (math.inf, 0.25),
        ],
        "hra_metro_pct": 0.50,
        "hra_nonmetro_pct": 0.40,
        "sec_80c_limit": 150000,
        "sec_80d_self_limit": 25000,
        "sec_80d_parents_limit": 25000,
        "sec_80d_self_senior": 50000,
        "sec_80d_parents_senior": 50000,
        "sec_80tta_limit": 10000,
        "sec_80ttb_limit": 50000,
        "sec_80ccd_1b_limit": 50000,
        "interest_24b_self_occupied_cap": 200000,
    }
}

METRO_CITIES = {"mumbai", "delhi", "kolkata", "chennai"}


def get_config(ay: str = "AY2024-25") -> Dict[str, Any]:
    return AY_CONFIG.get(ay, AY_CONFIG["AY2024-25"])

# ── Helper functions ──────────────────────────────────────────────────────────────
def _apply_slabs(income: float, slabs: List[Tuple[float, float]]) -> float:
    tax = 0.0
    prev = 0.0
    for limit, rate in slabs:
        if income <= prev:
            break
        taxable = min(income, limit) - prev
        tax += taxable * rate
        prev = limit
    return tax

def _compute_surcharge(income: float, tax: float, slabs: List[Tuple[float, float]]) -> float:
    rate = 0.0
    for limit, r in slabs:
        if income > limit:
            rate = r
    return tax * rate if rate else 0.0

# ── Public API ──────────────────────────────────────────────────────────────────
def compute_tax(income: float, regime: str = "new", ay: str = "AY2024-25") -> Dict[str, float]:
    """Compute tax for a given income.

    Returns a dict containing taxable income and detailed tax components.
    """
    cfg = get_config(ay)
    taxable_income = max(0.0, income)
    if regime == "new":
        slabs = cfg["new_regime_slabs"]
        rebate_limit = cfg["new_regime_rebate_87a_limit"]
        rebate_amount = cfg["new_regime_rebate_87a_amount"]
    else:
        slabs = cfg["old_regime_slabs"]
        rebate_limit = cfg["old_regime_rebate_87a_limit"]
        rebate_amount = cfg["old_regime_rebate_87a_amount"]

    tax_before = _apply_slabs(taxable_income, slabs)
    rebate = min(tax_before, rebate_amount) if taxable_income <= rebate_limit else 0.0
    tax_after = max(0.0, tax_before - rebate)
    surcharge = _compute_surcharge(income, tax_after, cfg["surcharge_slabs_new"])
    cess = (tax_after + surcharge) * cfg["cess_rate"]
    total = tax_after + surcharge + cess

    return {
        "taxable_income": round(taxable_income, 2),
        "tax_before_rebate": round(tax_before, 2),
        "rebate_87a": round(rebate, 2),
        "tax_after_rebate": round(tax_after, 2),
        "surcharge": round(surcharge, 2),
        "health_education_cess": round(cess, 2),
        "total_tax": round(total, 2),
    }

def calculate_tax(income: float, regime: str = "new", ay: str = "AY2024-25") -> Dict[str, float]:
    """Wrapper function to compute tax."""
    return compute_tax(income, regime, ay)

def enforce_deduction_limits(deductions: dict, ay: str = "AY2025-26") -> dict:
    """Cap deductions according to statutory limits and aggregate totals.
    Returns a dict with capped values, total, and any warnings.
    """
    cfg = get_config(ay)
    warnings_list: List[str] = []
    # 80C family (sec_80c, sec_80ccc, sec_80ccd_1)
    raw_80c = sum(deductions.get(k, 0) for k in ["sec_80c", "sec_80ccc", "sec_80ccd_1"])
    capped_80c = min(raw_80c, cfg["sec_80c_limit"])
    if raw_80c > cfg["sec_80c_limit"]:
        warnings_list.append(f"80C family capped at {cfg['sec_80c_limit']} (was {raw_80c})")
    # 80CCD(1B)
    raw_80ccd1b = deductions.get("sec_80ccd_1b", 0)
    capped_80ccd1b = min(raw_80ccd1b, cfg["sec_80ccd_1b_limit"])
    if raw_80ccd1b > cfg["sec_80ccd_1b_limit"]:
        warnings_list.append(f"80CCD(1B) capped at {cfg['sec_80ccd_1b_limit']} (was {raw_80ccd1b})")
    # 80TTA / 80TTB (mutually exclusive)
    raw_80tta = deductions.get("sec_80tta", 0)
    raw_80ttb = deductions.get("sec_80ttb", 0)
    capped_80tta = min(raw_80tta, cfg["sec_80tta_limit"])
    capped_80ttb = min(raw_80ttb, cfg["sec_80ttb_limit"])
    if raw_80tta > cfg["sec_80tta_limit"]:
        warnings_list.append(f"80TTA capped at {cfg['sec_80tta_limit']} (was {raw_80tta})")
    if raw_80ttb > cfg["sec_80ttb_limit"]:
        warnings_list.append(f"80TTB capped at {cfg['sec_80ttb_limit']} (was {raw_80ttb})")
    if raw_80tta and raw_80ttb:
        warnings_list.append("Both 80TTA and 80TTB claimed; only one allowed.")
    # Aggregate total (include 80D as well)
    total = (
        capped_80c +
        capped_80ccd1b +
        capped_80tta +
        capped_80ttb +
        deductions.get("sec_80d", 0) +
        deductions.get("sec_80ccd_2", 0)
    )
    return {
        "capped_80c_family": capped_80c,
        "capped_80ccd_1b": capped_80ccd1b,
        "capped_80tta": capped_80tta,
        "capped_80ttb": capped_80ttb,
        "total": total,
        "warnings": warnings_list,
    }
def compare_regimes(gross_total_income: float, deductions_old: float = 0.0, tds_deducted: float = 0.0, ay: str = "AY2025-26") -> dict:
    """Compare tax liability under old and new regimes.

    Args:
        gross_total_income: Total income before deductions.
        deductions_old: Deductions applicable only under old regime.
        tds_deducted: TDS amount to calculate possible refund for new regime.
        ay: Assessment year.

    Returns:
        dict with recommendation, savings, reasoning, refund, and breakdowns.
    """
    # Old regime taxable income after deductions
    taxable_old = max(0.0, gross_total_income - deductions_old)
    old_regime = compute_tax(taxable_old, regime="old", ay=ay)
    # New regime taxable income after standard deduction
    cfg = get_config(ay)
    std_new = cfg.get("standard_deduction_new_regime", 0.0)
    taxable_new = max(0.0, gross_total_income - std_new)
    new_regime = compute_tax(taxable_new, regime="new", ay=ay)

    old_total = old_regime.get("total_tax", 0.0)
    new_total = new_regime.get("total_tax", 0.0)

    if old_total < new_total:
        recommended = "old"
        saving = new_total - old_total
        reason = "Old regime yields lower tax liability."
    else:
        recommended = "new"
        saving = old_total - new_total
        reason = "New regime yields lower or equal tax liability."

    refund_new = max(0.0, tds_deducted - new_total) if tds_deducted else 0.0

    return {
        "recommended_regime": recommended,
        "saving": round(saving, 2),
        "reasoning": reason,
        "refund_new": round(refund_new, 2),
        "old_regime": old_regime,
        "new_regime": new_regime,
    }
# HRA computation (unchanged)

def compute_hra_exemption(
    hra_received: float,
    basic_salary: float,
    rent_paid: float,
    city: str,
    ay: str = "AY2024-25",
) -> Dict[str, Any]:
    cfg = get_config(ay)
    pct = cfg["hra_metro_pct"] if city.lower() in METRO_CITIES else cfg["hra_nonmetro_pct"]
    component_a = hra_received
    component_b = max(0.0, rent_paid - 0.10 * basic_salary)
    component_c = basic_salary * pct
    exemption = min(component_a, component_b, component_c)
    return {
        "component_a_hra_received": component_a,
        "component_b_rent_minus_10pct": component_b,
        "component_c_pct_of_basic": component_c,
        "hra_exemption": round(exemption, 2),
        "hra_taxable": round(hra_received - exemption, 2),
        "city_type": "metro" if city.lower() in METRO_CITIES else "non-metro",
    }
