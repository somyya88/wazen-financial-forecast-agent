import re
import pandas as pd
from typing import Any, List

AR_MONTHS = {
    "يناير": "Jan", "كانون الثاني": "Jan", "jan": "Jan", "january": "Jan",
    "فبراير": "Feb", "شباط": "Feb", "feb": "Feb", "february": "Feb",
    "مارس": "Mar", "آذار": "Mar", "mar": "Mar", "march": "Mar",
    "أبريل": "Apr", "ابريل": "Apr", "نيسان": "Apr", "apr": "Apr", "april": "Apr",
    "مايو": "May", "أيار": "May", "may": "May",
    "يونيو": "Jun", "حزيران": "Jun", "jun": "Jun", "june": "Jun",
    "يوليو": "Jul", "تموز": "Jul", "jul": "Jul", "july": "Jul",
    "أغسطس": "Aug", "اغسطس": "Aug", "آب": "Aug", "aug": "Aug", "august": "Aug",
    "سبتمبر": "Sep", "أيلول": "Sep", "sep": "Sep", "september": "Sep",
    "أكتوبر": "Oct", "اكتوبر": "Oct", "تشرين الأول": "Oct", "oct": "Oct", "october": "Oct",
    "نوفمبر": "Nov", "تشرين الثاني": "Nov", "nov": "Nov", "november": "Nov",
    "ديسمبر": "Dec", "كانون الأول": "Dec", "dec": "Dec", "december": "Dec",
}

MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def normalize_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df

def to_number(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("SAR", "", regex=False)
        .str.replace("ريال", "", regex=False)
        .str.replace("ر.س", "", regex=False)
        .str.strip()
    )
    return pd.to_numeric(cleaned, errors="coerce").fillna(0)

def detect_month_columns(columns: List[str]) -> List[str]:
    result = []
    for col in columns:
        c = normalize_text(col)
        if c in AR_MONTHS:
            result.append(col)
            continue
        for key in AR_MONTHS:
            if key in c and "total" not in c and "الإجمالي" not in c and "اجمالي" not in c:
                result.append(col)
                break
    return result

def month_label(column_name: str) -> str:
    c = normalize_text(column_name)
    for key, val in AR_MONTHS.items():
        if key in c:
            return val
    return str(column_name)

def find_column(df: pd.DataFrame, candidates: List[str]) -> str | None:
    normalized = {normalize_text(c): c for c in df.columns}
    for candidate in candidates:
        nc = normalize_text(candidate)
        if nc in normalized:
            return normalized[nc]
    for col in df.columns:
        ncol = normalize_text(col)
        if any(normalize_text(c) in ncol for c in candidates):
            return col
    return None
