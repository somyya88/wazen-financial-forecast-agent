import pandas as pd
from core.utils import find_column, to_number, normalize_text

ACCOUNT_RULES = {
    "Assets": ["نقد", "بنك", "صندوق", "ذمم مدينة", "عملاء", "اصل", "أصل", "assets", "cash", "bank", "receivable"],
    "Liabilities": ["ذمم دائنة", "مورد", "قرض", "التزام", "liabilities", "payable", "loan"],
    "Equity": ["رأس المال", "راس المال", "حقوق", "ارباح مبقاة", "equity", "capital"],
    "Operating Revenue": ["مبيعات", "ايراد", "إيراد", "sales", "revenue"],
    "Other Revenue": ["ايرادات اخرى", "إيرادات أخرى", "other income"],
    "COGS": ["تكلفة", "مشتريات", "cogs", "cost of sales"],
    "Operating Expenses": ["مصروف", "expenses", "opex"],
    "Depreciation": ["اهلاك", "إهلاك", "depreciation"],
    "Finance Costs": ["فوائد", "تمويل", "interest", "finance"],
    "Tax/Zakat": ["زكاة", "ضريبة", "tax", "zakat"],
}

def classify_account(name: str) -> str:
    text = normalize_text(name)
    for category, keys in ACCOUNT_RULES.items():
        if any(normalize_text(k) in text for k in keys):
            return category
    return "Unclassified"

def parse_trial_balance(file_record: dict) -> dict:
    df = file_record["primary_df"].copy()
    account_col = find_column(df, ["اسم الحساب", "account name", "account", "الحساب", "البيان"])
    code_col = find_column(df, ["رقم الحساب", "account code", "code"])
    debit_col = find_column(df, ["debit", "مدين", "closing debit", "رصيد مدين"])
    credit_col = find_column(df, ["credit", "دائن", "closing credit", "رصيد دائن"])

    if not account_col:
        return {"tb": pd.DataFrame(), "summary": pd.DataFrame(), "notes": ["لم يتم تحديد عمود اسم الحساب في ميزان المراجعة."]}

    work = df.copy()
    work["account_name"] = work[account_col].astype(str)
    work["account_code"] = work[code_col].astype(str) if code_col else ""
    work["category"] = work["account_name"].apply(classify_account)
    work["debit"] = to_number(work[debit_col]) if debit_col else 0
    work["credit"] = to_number(work[credit_col]) if credit_col else 0
    work["net"] = work["credit"] - work["debit"]

    summary = work.groupby("category", as_index=False)[["debit", "credit", "net"]].sum()
    return {"tb": work, "summary": summary, "notes": []}
