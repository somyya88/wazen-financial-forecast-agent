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

    # Cash liquidity report
    cash_liq_keywords = ["الأموال الجاهزة", "الاموال الجاهزة", "الباقي", "السيولة", "cash liquidity", "cash flow", "نقدية"]
    score["cash_liquidity_report"] = sum(k.lower() in cols or k.lower() in sample_text for k in cash_liq_keywords) + len(month_cols)

    # AR/AP aging
    ar_keywords = ["أعمار ديون العملاء", "اعمار ديون العملاء", "عميل", "آخر سداد", "عمر الدين", "31-60", "receivable", "customer aging"]
    ap_keywords = ["أعمار ديون الموردين", "اعمار ديون الموردين", "مورد", "آخر سداد", "عمر الدين", "31-60", "payable", "vendor aging", "supplier aging"]
    score["ar_aging"] = sum(k.lower() in cols or k.lower() in sample_text for k in ar_keywords)
    score["ap_aging"] = sum(k.lower() in cols or k.lower() in sample_text for k in ap_keywords)

    # Customer / Supplier master or statement reports
    customer_report_keywords = ["تقرير العملاء", "العملاء", "customer report", "customer statement", "كشف العملاء", "حساب العميل"]
    supplier_report_keywords = ["تقرير الموردين", "الموردين", "supplier report", "vendor report", "كشف الموردين", "حساب المورد"]
    score["customer_report"] = sum(k.lower() in cols or k.lower() in sample_text for k in customer_report_keywords)
    score["supplier_report"] = sum(k.lower() in cols or k.lower() in sample_text for k in supplier_report_keywords)

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

    # Strong TB layouts: account code/name + opening/current debit/credit columns must be Trial Balance,
    # even if the sample text contains expense/payroll words.
    tb_layout_signal = (
        ("رقم الحساب" in cols or "account code" in cols or "رمز الحساب" in cols)
        and ("اسم الحساب" in cols or "account name" in cols or "الحساب" in cols)
        and ("مدين" in cols or "debit" in cols)
        and ("دائن" in cols or "credit" in cols)
        and ("الرصيد الحالي" in cols or "نهاية المدة" in cols or "closing" in cols or "current" in cols)
    )

    # Strong explicit layouts should win before generic bank/trial-balance keywords.
    if tb_layout_signal:
        best_type = "trial_balance"
        best_score = max(score.get("trial_balance", 0), 8)
    elif score.get("cash_liquidity_report", 0) >= 4 and len(month_cols) >= 2:
        best_type = "cash_liquidity_report"
        best_score = score[best_type]
    elif score.get("ar_aging", 0) >= 4 and "عميل" in sample_text:
        best_type = "ar_aging"
        best_score = score[best_type]
    elif score.get("ap_aging", 0) >= 4 and "مورد" in sample_text:
        best_type = "ap_aging"
        best_score = score[best_type]
    elif score.get("customer_report", 0) >= 3 and "عميل" in sample_text and "عمر الدين" not in sample_text:
        best_type = "customer_report"
        best_score = score[best_type]
    elif score.get("supplier_report", 0) >= 3 and "مورد" in sample_text and "عمر الدين" not in sample_text:
        best_type = "supplier_report"
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
