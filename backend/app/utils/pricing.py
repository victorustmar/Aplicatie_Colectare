# app/utils/pricing.py
from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict

# === TARIFE ===
# Portable (lei / buc)
PORTABLE_RATES: Dict[str, Decimal] = {
    "pastila":     Decimal("0.01"),
    "g_0_50":      Decimal("0.04"),
    "g_51_150":    Decimal("0.11"),
    "g_151_250":   Decimal("0.38"),
    "g_251_500":   Decimal("0.80"),
    "g_501_750":   Decimal("0.98"),
    "g_751_1000":  Decimal("1.20"),
    "g_over_1000": Decimal("1.38"),
}

# Auto & industriale (lei / kg)
AUTO_IND_RATES: Dict[str, Decimal] = {
    "auto_plumb":  Decimal("0.35"),  # 3a
    "auto_nicd":   Decimal("1.38"),  # 3b
    "auto_altele": Decimal("1.38"),  # 3c
    "ind_plumb":   Decimal("0.35"),  # 4a
    "ind_nicd":    Decimal("1.38"),  # 4b
    "ind_altele":  Decimal("1.38"),  # 4c
}

# Structură cu zerouri pentru inițializare/normalizare
DEFAULT_BATTERIES: Dict[str, Dict[str, Decimal | int | float]] = {
    "portable": {k: 0 for k in PORTABLE_RATES.keys()},
    "auto_ind": {k: 0 for k in AUTO_IND_RATES.keys()},
}

def _to_int(x: Any) -> int:
    try:
        return int(x) if x is not None else 0
    except Exception:
        return 0

def _to_dec(x: Any) -> Decimal:
    try:
        return Decimal(str(x)) if x is not None else Decimal("0")
    except Exception:
        return Decimal("0")

def normalize_batteries(b: Any) -> Dict[str, Dict[str, Decimal | int]]:
    """
    Asigură cheile așteptate și tipuri numerice (int pentru bucăți, Decimal pentru kg).
    """
    b = b or {}
    out = {
        "portable": {},
        "auto_ind": {},
    }
    p = (b.get("portable") or {})
    for k in PORTABLE_RATES:
        out["portable"][k] = _to_int(p.get(k, 0))

    a = (b.get("auto_ind") or {})
    for k in AUTO_IND_RATES:
        out["auto_ind"][k] = _to_dec(a.get(k, 0))
    return out

def compute_totals(batteries: Any) -> Dict[str, Decimal]:
    """
    Calculează subtotal (lei) și greutate totală (kg) pe baza structurii din pasul 1.
    Returnează:
      - subtotal: Decimal (lei, rotunjit 2 zecimale)
      - total_weight: Decimal (kg, rotunjit 2 zecimale)
    """
    b = normalize_batteries(batteries)

    # Portable: lei/buc * bucăți
    subtotal_portable = sum(
        PORTABLE_RATES[k] * Decimal(b["portable"][k])
        for k in PORTABLE_RATES.keys()
    )

    # Auto/ind: lei/kg * kg și greutatea totală
    subtotal_auto = sum(
        AUTO_IND_RATES[k] * _to_dec(b["auto_ind"][k])
        for k in AUTO_IND_RATES.keys()
    )
    total_weight = sum(
        _to_dec(b["auto_ind"][k]) for k in AUTO_IND_RATES.keys()
    )

    subtotal = (subtotal_portable + subtotal_auto).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total_weight = total_weight.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return {"subtotal": subtotal, "total_weight": total_weight}
