import pandas as pd
from utils import find_column, to_number, normalize_text

ACCOUNT_RULES = {
    "Assets": ["نقد", "بنك", "صندوق", "ذمم مدينة", "عملاء", "اصل", "أصل", "assets", "cash", "bank", "receivable"],
    "Liabilities": ["ذمم دائنة", "مورد", "قرض", "التزام", "مقبوض مقدما", "مقدمة", "liabilities", "payable", "loan", "unearned"],
    "Equity": ["رأس المال", "راس المال", "حقوق", "ارباح مبقاة", "equity", "capital"],
    "Operating Revenue": ["صافي المبيعات", "المبيعات ( رئيسي )", "مبيعات اشتراك", "مبيعات تجديدات", "مبيعات قطاع"],
    "Sales Returns": ["مردودات المبيعات", "مردودات مبيعات"],
    "Other Revenue": ["ايرادات اخرى", "إيرادات أخرى", "ايرادات أخرى", "other income"],
    "COGS": ["تكلفة", "مشتريات", "cogs", "cost of sales"],
    "Operating Expenses": ["مصروف", "expenses", "opex"],
    "Depreciation": ["اهلاك", "إهلاك", "depreciation"],
    "Finance Costs": ["فوائد", "تمويل", "interest", "finance"],
    "Tax/Zakat": ["زكاة", "ضريبة", "tax", "zakat"],
}

def classify_account(name: str) -> str:
    text = normalize_text(name)

    # Avoid treating liabilities that contain the word revenue/sales as revenue.
    if any(k in text for k in ["مقبوض مقدما", "مستحقة", "ضريبة القيمة المضافة للمبيعات", "ايجار مقرات"]):
        return "Liabilities"

    for category, keys in ACCOUNT_RULES.items():
        if any(normalize_text(k) in text for k in keys):
            return category
    return "Unclassified"

def _find_net_sales(work: pd.DataFrame) -> float | None:
    """
    Best practice for this TB format:
    use the explicit row named 'صافي المبيعات' because it already nets sales, returns,
    discounts, or related debit movements.
    """
    if work.empty:
        return None

    exact = work["account_name"].astype(str).str.strip().eq("صافي المبيعات")
    if exact.any():
        row = work.loc[exact].iloc[0]
        if abs(float(row.get("net", 0))) > 0:
            return abs(float(row["net"]))
        credit = float(row.get("credit", 0))
        debit = float(row.get("debit", 0))
        return abs(credit - debit)

    # Fallback: use code 4 main revenue only when explicit net sales row is absent.
    code = work["account_code"].astype(str).str.strip()
    revenue_rows = work[code.str.startswith("401")]
    returns_rows = work[code.str.startswith("402")]
    if not revenue_rows.empty:
        sales = revenue_rows["credit"].sum() - revenue_rows["debit"].sum()
        returns = returns_rows["debit"].sum() - returns_rows["credit"].sum() if not returns_rows.empty else 0
        return max(0.0, float(sales - returns))

    return None

def parse_trial_balance(file_record: dict) -> dict:
    df = file_record["primary_df"].copy()
    account_col = find_column(df, ["اسم الحساب", "account name", "account", "الحساب", "البيان"])
    code_col = find_column(df, ["رقم الحساب", "account code", "code"])
    debit_col = find_column(df, ["مدين", "debit", "الحركة المدينة", "closing debit", "الرصيد الحالي(مدين)"])
    credit_col = find_column(df, ["دائن", "دائن ", "credit", "الحركة الدائنة", "closing credit", "الرصيد الحالي(دائن )"])

    if not account_col:
        return {"tb": pd.DataFrame(), "summary": pd.DataFrame(), "metrics": {}, "notes": ["لم يتم تحديد عمود اسم الحساب في ميزان المراجعة."]}

    work = df.copy()
    work["account_name"] = work[account_col].astype(str)
    work["account_code"] = work[code_col].astype(str) if code_col else ""
    work["category"] = work["account_name"].apply(classify_account)
    work["debit"] = to_number(work[debit_col]) if debit_col else 0
    work["credit"] = to_number(work[credit_col]) if credit_col else 0
    work["net"] = work["credit"] - work["debit"]

    summary = work.groupby("category", as_index=False)[["debit", "credit", "net"]].sum()

    net_sales = _find_net_sales(work)
    metrics = {
        "net_sales": net_sales,
        "net_sales_basis": "صافي المبيعات" if net_sales is not None else None,
    }

    return {
        "tb": work,
        "summary": summary,
        "metrics": metrics,
        "notes": ["تم استخراج صافي المبيعات من صف صافي المبيعات عند توفره بدلاً من جمع كل الحسابات التي تحتوي كلمة مبيعات."],
    }
