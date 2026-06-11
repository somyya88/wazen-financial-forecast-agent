from __future__ import annotations
import re
from datetime import datetime

MONTH_ORDER = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
AR_TO_EN = {
    "يناير":"Jan", "فبراير":"Feb", "مارس":"Mar", "إبريل":"Apr", "أبريل":"Apr", "ابريل":"Apr", "ماي":"May", "مايو":"May",
    "يونيو":"Jun", "يوليو":"Jul", "أغسطس":"Aug", "اغسطس":"Aug", "سبتمبر":"Sep", "أكتوبر":"Oct", "اكتوبر":"Oct", "نوفمبر":"Nov", "ديسمبر":"Dec",
}

def infer_validation_end_month(files: list[dict]) -> str | None:
    """Infer analysis end month from Trial Balance filename, e.g. إلى تاريخ_2026-05-31."""
    for f in files or []:
        if f.get("selected_role") == "validation_source" or f.get("detected_type") == "trial_balance":
            name = str(f.get("file_name") or "")
            dates = re.findall(r"(20\d{2})[-_/](\d{1,2})[-_/](\d{1,2})", name)
            if dates:
                y,m,d = dates[-1]
                try:
                    idx = int(m) - 1
                    if 0 <= idx < 12:
                        return MONTH_ORDER[idx]
                except Exception:
                    pass
    return None


def normalize_month_token(m: str) -> str:
    s = str(m).strip()
    if s in MONTH_ORDER:
        return s
    for ar,en in AR_TO_EN.items():
        if ar in s:
            return en
    return s[:3].title() if s else s


def trim_months_to_end(months: list[str], end_month: str | None) -> list[str]:
    if not months or not end_month:
        return months or []
    end = normalize_month_token(end_month)
    if end not in MONTH_ORDER:
        return months
    allowed = set(MONTH_ORDER[:MONTH_ORDER.index(end)+1])
    return [m for m in months if normalize_month_token(m) in allowed]
