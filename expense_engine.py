import pandas as pd
from core.utils import detect_month_columns, to_number, month_label, find_column, normalize_text

CATEGORY_RULES = {
    "Payroll": ["راتب", "رواتب", "اجور", "أجور", "salary", "payroll", "wage"],
    "Marketing": ["تسويق", "اعلان", "إعلان", "marketing", "advertising", "ads"],
    "Rent": ["ايجار", "إيجار", "rent"],
    "COGS": ["تكلفة", "cost of sales", "cogs", "مشتريات", "بضاعة"],
    "Maintenance": ["صيانة", "maintenance", "repair"],
    "Fuel": ["وقود", "fuel", "بنزين", "ديزل", "زيوت", "oil"],
    "Spare Parts": ["قطع غيار", "spare", "parts"],
    "Depreciation": ["اهلاك", "إهلاك", "depreciation"],
    "Interest": ["فوائد", "فائدة", "interest", "finance cost"],
    "Bank Charges": ["عمولة بنكية", "عمولات بنكية", "bank charge", "bank fees"],
    "Selling Opex": ["بيع", "مبيعات", "sales expense", "commission"],
    "Admin Opex": ["اداري", "إداري", "admin", "office", "مكتبية"],
}

def classify_expense(account_name: str) -> str:
    text = normalize_text(account_name)
    for category, keys in CATEGORY_RULES.items():
        if any(normalize_text(k) in text for k in keys):
            return category
    return "Other Opex"

def build_expense_model(file_record: dict, revenue_total: float | None = None) -> dict:
    df = file_record["primary_df"].copy()
    month_cols = detect_month_columns(list(df.columns))

    if month_cols:
        return _wide_expenses(df, month_cols, revenue_total)
    return _transaction_expenses(df, revenue_total)

def _wide_expenses(df: pd.DataFrame, month_cols: list[str], revenue_total: float | None) -> dict:
    account_col = find_column(df, ["اسم الحساب", "account name", "account", "الحساب", "البيان"])
    code_col = find_column(df, ["رقم الحساب", "account code", "code"])
    notes = []

    text_cols = [c for c in df.columns if df[c].dtype == "object"]
    mask_total = pd.Series(False, index=df.index)
    for c in text_cols:
        mask_total = mask_total | df[c].astype(str).str.contains("الإجمالي|اجمالي|total", case=False, na=False)
    if mask_total.any():
        df = df[~mask_total].copy()
        notes.append("تم استبعاد صفوف إجمالي محتملة لمنع التكرار.")

    long_rows = []
    for _, row in df.iterrows():
        account_name = str(row.get(account_col, "Unknown")) if account_col else "Unknown"
        account_code = str(row.get(code_col, "")) if code_col else ""
        category = classify_expense(account_name)
        for col in month_cols:
            amount = float(to_number(pd.Series([row[col]])).iloc[0])
            if amount != 0:
                long_rows.append({
                    "account_code": account_code,
                    "account_name": account_name,
                    "category": category,
                    "month": month_label(col),
                    "amount": abs(amount),
                })

    long_df = pd.DataFrame(long_rows)
    if long_df.empty:
        long_df = pd.DataFrame(columns=["account_code", "account_name", "category", "month", "amount"])

    monthly = long_df.groupby("month", as_index=False)["amount"].sum().rename(columns={"amount": "expenses"})
    by_category = long_df.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
    top_expenses = long_df.groupby(["account_name", "category"], as_index=False)["amount"].sum().sort_values("amount", ascending=False).head(10)

    total_expenses = float(long_df["amount"].sum()) if not long_df.empty else 0
    expense_ratio = (total_expenses / revenue_total) if revenue_total else None

    return {
        "expense_long": long_df,
        "monthly_expenses": monthly,
        "by_category": by_category,
        "top_expenses": top_expenses,
        "total_expenses": total_expenses,
        "expense_ratio": expense_ratio,
        "notes": notes,
    }

def _transaction_expenses(df: pd.DataFrame, revenue_total: float | None) -> dict:
    amount_col = find_column(df, ["amount", "المبلغ", "قيمة", "debit", "مدين"])
    account_col = find_column(df, ["اسم الحساب", "account name", "account", "الحساب", "description", "الوصف", "البيان"])
    date_col = find_column(df, ["date", "التاريخ", "month", "الشهر"])

    if not amount_col:
        return {
            "expense_long": pd.DataFrame(),
            "monthly_expenses": pd.DataFrame(),
            "by_category": pd.DataFrame(),
            "top_expenses": pd.DataFrame(),
            "total_expenses": 0,
            "expense_ratio": None,
            "notes": ["لم يتم العثور على عمود مبلغ للمصاريف."],
        }

    work = df.copy()
    work["amount"] = abs(to_number(work[amount_col]))
    work["account_name"] = work[account_col].astype(str) if account_col else "Unknown"
    work["category"] = work["account_name"].apply(classify_expense)
    if date_col:
        dates = pd.to_datetime(work[date_col], errors="coerce")
        work["month"] = dates.dt.strftime("%b").fillna(work[date_col].astype(str))
    else:
        work["month"] = "Total"

    long_df = work[["account_name", "category", "month", "amount"]]
    monthly = long_df.groupby("month", as_index=False)["amount"].sum().rename(columns={"amount": "expenses"})
    by_category = long_df.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
    top_expenses = long_df.groupby(["account_name", "category"], as_index=False)["amount"].sum().sort_values("amount", ascending=False).head(10)
    total_expenses = float(long_df["amount"].sum())
    expense_ratio = (total_expenses / revenue_total) if revenue_total else None

    return {
        "expense_long": long_df,
        "monthly_expenses": monthly,
        "by_category": by_category,
        "top_expenses": top_expenses,
        "total_expenses": total_expenses,
        "expense_ratio": expense_ratio,
        "notes": [],
    }
