import pandas as pd
from utils import detect_month_columns, to_number, month_label, find_column, normalize_text

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
    return "Needs Review"

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
                # Keep the sign as-is.
                # Negative expense lines usually represent reversals/credit notes
                # and should reduce total expenses, not increase them.
                long_rows.append({
                    "account_code": account_code,
                    "account_name": account_name,
                    "category": category,
                    "month": month_label(col),
                    "amount": amount,
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
    # Keep the sign as-is. Negative lines reduce expenses.
    work["amount"] = to_number(work[amount_col])
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


def build_expense_model_from_trial_balance(tb_model: dict | None, revenue_total: float | None = None) -> dict:
    """Build an expense model directly from Trial Balance.

    This is important for Level A analysis: a Trial Balance alone contains expense
    accounts, so the app must not say "no expenses" just because a monthly expense
    detail file was not uploaded. Monthly expense files are for trend/detail, not a
    prerequisite for a cost structure reading.
    """
    if not tb_model:
        return {
            "expense_long": pd.DataFrame(),
            "monthly_expenses": pd.DataFrame(),
            "by_category": pd.DataFrame(),
            "top_expenses": pd.DataFrame(),
            "total_expenses": 0,
            "expense_ratio": None,
            "notes": ["ميزان المراجعة غير متاح لاستخراج المصاريف."],
            "source": "trial_balance",
        }

    tb = tb_model.get("tb", pd.DataFrame()).copy()
    if tb.empty:
        return {
            "expense_long": pd.DataFrame(),
            "monthly_expenses": pd.DataFrame(),
            "by_category": pd.DataFrame(),
            "top_expenses": pd.DataFrame(),
            "total_expenses": 0,
            "expense_ratio": None,
            "notes": ["لم يتم العثور على حسابات ميزان مراجعة قابلة للقراءة."],
            "source": "trial_balance",
        }

    for col in ["account_code_norm", "account_name", "debit", "credit", "current_debit", "current_credit"]:
        if col not in tb.columns:
            tb[col] = "" if col in ["account_code_norm", "account_name"] else 0
    for col in ["debit", "credit", "current_debit", "current_credit"]:
        tb[col] = pd.to_numeric(tb[col], errors="coerce").fillna(0.0)

    all_codes = tb["account_code_norm"].astype(str).tolist()
    def is_parent(code: str) -> bool:
        if not code:
            return False
        return any(other != code and str(other).startswith(str(code)) and len(str(other)) > len(str(code)) for other in all_codes)

    leaf = tb[~tb["account_code_norm"].astype(str).apply(is_parent)].copy()
    names = leaf["account_name"].astype(str).apply(normalize_text)
    codes = leaf["account_code_norm"].astype(str)
    expense_mask = codes.str.startswith("5", na=False) | names.str.contains(
        "مصروف|مصاريف|راتب|رواتب|اجور|أجور|ايجار|إيجار|بدل|عموله|عمولات|تسويق|دعايه|اعلان|اتعاب|رسوم|اشتراك|صيانة|صيانه|تنقل|سفر|ضيافه|نظافه|بوابة الدفع|بنكي|فوائد|زكاة|ضريبة",
        regex=True,
        na=False,
    )
    exp = leaf[expense_mask].copy()

    if exp.empty:
        return {
            "expense_long": pd.DataFrame(columns=["account_code", "account_name", "category", "month", "amount"]),
            "monthly_expenses": pd.DataFrame(columns=["month", "expenses"]),
            "by_category": pd.DataFrame(columns=["category", "amount"]),
            "top_expenses": pd.DataFrame(columns=["account_name", "category", "amount"]),
            "total_expenses": 0,
            "expense_ratio": None,
            "notes": ["لم يتم العثور على حسابات مصروفات واضحة داخل ميزان المراجعة."],
            "source": "trial_balance",
        }

    # Prefer period movement. If movement is missing, fall back to closing debit/credit.
    movement_total = float((exp["debit"].abs() + exp["credit"].abs()).sum())
    if movement_total > 0:
        exp["amount"] = exp["debit"] - exp["credit"]
        basis = "حركة الفترة من ميزان المراجعة"
    else:
        exp["amount"] = exp["current_debit"] - exp["current_credit"]
        basis = "رصيد آخر الفترة من ميزان المراجعة"

    exp = exp[exp["amount"].abs() > 0].copy()
    exp["amount"] = exp["amount"].astype(float)
    exp["account_code"] = exp["account_code_norm"].astype(str)
    exp["account_name"] = exp["account_name"].astype(str)
    exp["category"] = exp["account_name"].apply(classify_expense)
    exp["month"] = "Total"

    long_df = exp[["account_code", "account_name", "category", "month", "amount"]].copy()
    monthly = pd.DataFrame([{"month": "Total", "expenses": float(long_df["amount"].sum())}])
    by_category = long_df.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
    top_expenses = long_df.groupby(["account_name", "category"], as_index=False)["amount"].sum().sort_values("amount", ascending=False).head(15)
    total_expenses = float(long_df["amount"].sum()) if not long_df.empty else 0.0
    expense_ratio = (total_expenses / revenue_total) if revenue_total else None

    return {
        "expense_long": long_df,
        "monthly_expenses": monthly,
        "by_category": by_category,
        "top_expenses": top_expenses,
        "total_expenses": total_expenses,
        "expense_ratio": expense_ratio,
        "notes": [f"تم استخراج المصاريف من ميزان المراجعة باستخدام {basis}. ملف المصروفات الشهري يضيف توزيعًا شهريًا ولا يوقف تحليل المصاريف."],
        "source": "trial_balance",
    }
