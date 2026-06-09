import pandas as pd

PERCENT_KEYWORDS = ["margin", "ratio", "score", "هامش", "نسبة"]

def fmt_number(value, decimals=0):
    try:
        if pd.isna(value):
            return ""
        return f"{float(value):,.{decimals}f}"
    except Exception:
        return value

def fmt_amount(value):
    try:
        if pd.isna(value):
            return ""
        val = float(value)
        return f"{val:,.0f}" if abs(val) >= 1000 else f"{val:,.2f}".rstrip("0").rstrip(".")
    except Exception:
        return value

def fmt_percent(value):
    try:
        if pd.isna(value):
            return ""
        return f"{float(value):.1%}"
    except Exception:
        text = str(value)
        return text if "%" in text else value

def _is_percent_row(row):
    text = " ".join(str(v).lower() for v in row.values)
    return any(k.lower() in text for k in PERCENT_KEYWORDS)

def format_financial_table(df: pd.DataFrame) -> pd.DataFrame:
    """Display order: Arabic on the right, English next to it, numbers on the left in RTL Streamlit."""
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()

    # Format numeric columns by context.
    for col in out.columns:
        if pd.api.types.is_numeric_dtype(out[col]):
            if "margin" in str(col).lower() or "ratio" in str(col).lower() or str(col).lower() in ["value"]:
                # Value can be amount in some tables, so handle row by row below for Value.
                pass

    if "Value" in out.columns:
        out["Value"] = out.apply(lambda r: fmt_percent(r["Value"]) if _is_percent_row(r) else fmt_amount(r["Value"]), axis=1)
    if "Amount" in out.columns:
        out["Amount"] = out["Amount"].apply(fmt_amount)

    # Common monthly/profit columns.
    for col in ["revenue", "expenses", "preliminary_profit", "forecast_revenue", "forecast_expenses", "forecast_profit", "amount", "Break-even Revenue", "Fixed Costs", "Contribution Margin"]:
        if col in out.columns:
            if "margin" in col.lower() or col == "Contribution Margin":
                out[col] = out[col].apply(fmt_percent)
            else:
                out[col] = out[col].apply(fmt_amount)
    for col in ["margin", "forecast_margin"]:
        if col in out.columns:
            out[col] = out[col].apply(fmt_percent)

    # Rename analytical columns.
    rename_map = {
        "month": "الشهر",
        "revenue": "الإيرادات",
        "expenses": "المصاريف",
        "preliminary_profit": "الربح الأولي",
        "margin": "الهامش",
        "category": "التصنيف",
        "amount": "المبلغ",
        "account_name": "الحساب",
        "current_category": "التصنيف الحالي",
        "user_category": "التصنيف المعتمد",
        "cost_behavior": "نوع التكلفة",
        "Scenario": "Scenario",
        "forecast_revenue": "الإيرادات المتوقعة",
        "forecast_expenses": "المصاريف المتوقعة",
        "forecast_profit": "الربح المتوقع",
        "forecast_margin": "الهامش المتوقع",
        "English": "English",
        "العربي": "العربي",
        "Amount": "المبلغ",
        "Value": "القيمة",
        "Why it matters": "لماذا يهم؟",
    }
    out = out.rename(columns={k:v for k,v in rename_map.items() if k in out.columns})

    # Reorder bilingual financial statement rows: amount at left, English middle, Arabic right.
    cols = list(out.columns)
    priority_left = [c for c in ["المبلغ", "القيمة", "الإيرادات", "المصاريف", "الربح الأولي", "الهامش", "الإيرادات المتوقعة", "المصاريف المتوقعة", "الربح المتوقع", "الهامش المتوقع"] if c in cols]
    priority_middle = [c for c in ["English", "Scenario"] if c in cols]
    priority_right = [c for c in ["العربي", "الشهر", "التصنيف", "الحساب", "التصنيف الحالي", "التصنيف المعتمد", "نوع التكلفة", "لماذا يهم؟"] if c in cols]
    remaining = [c for c in cols if c not in priority_left + priority_middle + priority_right]

    # In Streamlit RTL, left-to-right physical order still follows list order; we want numbers first, Arabic last.
    ordered = priority_left + priority_middle + remaining + priority_right
    return out[ordered]

def style_dataframe(df: pd.DataFrame):
    return format_financial_table(df)
