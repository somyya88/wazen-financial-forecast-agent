from dataclasses import dataclass
import pandas as pd
from utils import normalize_text, detect_month_columns

@dataclass
class DetectionResult:
    file_type: str
    confidence: float
    reasons: list[str]

def _joined_columns(df: pd.DataFrame) -> str:
    return " ".join([normalize_text(c) for c in df.columns])

def detect_file_type(df: pd.DataFrame) -> DetectionResult:
    if df is None or df.empty:
        return DetectionResult("unknown", 0.1, ["Empty or unreadable file"])

    cols = _joined_columns(df)
    month_cols = detect_month_columns(list(df.columns))
    sample_text = " ".join(df.astype(str).head(20).fillna("").values.flatten()).lower()

    score = {}

    # Trial balance
    tb_keywords = ["ميزان", "مراجعة", "trial", "balance", "مدين", "دائن", "debit", "credit", "رصيد"]
    score["trial_balance"] = sum(k in cols or k in sample_text for k in tb_keywords)

    # Monthly sales wide
    sales_keywords = ["مبيعات", "sales", "revenue", "ايراد", "إيراد", "صافي المبيعات", "ضريبة"]
    score["monthly_sales_wide"] = sum(k.lower() in cols or k.lower() in sample_text for k in sales_keywords) + len(month_cols)

    # Expense monthly
    exp_keywords = ["مصروف", "مصروفات", "expenses", "expense", "تكلفة", "cost", "account", "اسم الحساب", "رقم الحساب"]
    score["expense_monthly"] = sum(k.lower() in cols or k.lower() in sample_text for k in exp_keywords) + len(month_cols)

    # Item sales
    item_keywords = ["صنف", "الأصناف", "item", "product", "quantity", "كمية", "وحدة", "unit"]
    score["item_sales"] = sum(k.lower() in cols or k.lower() in sample_text for k in item_keywords)

    # Bank statement
    bank_keywords = ["bank", "بنك", "كشف", "statement", "transaction", "عملية", "رصيد", "balance", "iban"]
    score["bank_statement"] = sum(k.lower() in cols or k.lower() in sample_text for k in bank_keywords)

    # Payroll
    payroll_keywords = ["راتب", "رواتب", "salary", "payroll", "employee", "موظف", "أجر", "اجور", "أجور"]
    score["payroll"] = sum(k.lower() in cols or k.lower() in sample_text for k in payroll_keywords)

    # Invoice sales
    invoice_keywords = ["invoice", "فاتورة", "عميل", "customer", "vat", "ضريبة", "discount", "خصم"]
    score["invoice_sales"] = sum(k.lower() in cols or k.lower() in sample_text for k in invoice_keywords)

    # Tie-breaking rules
    best_type = max(score, key=score.get)
    best_score = score[best_type]

    # Better rule for wide monthly expense vs sales
    if len(month_cols) >= 2:
        if score["expense_monthly"] >= score["monthly_sales_wide"] and ("مصروف" in sample_text or "expense" in sample_text or "اسم الحساب" in cols):
            best_type = "expense_monthly"
            best_score = score["expense_monthly"]
        elif "مبيعات" in sample_text or "sales" in sample_text or "revenue" in sample_text:
            best_type = "monthly_sales_wide"
            best_score = score["monthly_sales_wide"]

    confidence = min(0.98, max(0.25, best_score / 10))
    if best_score <= 1:
        best_type = "unknown"
        confidence = 0.25

    reasons = [
        f"Detected {len(month_cols)} monthly columns",
        f"Keyword scores: {score}",
    ]
    return DetectionResult(best_type, round(confidence, 2), reasons)
