def suggest_role(file_type: str) -> str:
    mapping = {
        "monthly_sales_wide": "official_revenue_source",
        "invoice_sales": "official_revenue_source",
        "item_sales": "revenue_detail_source",
        "expense_monthly": "official_expense_source",
        "payroll": "expense_detail_source",
        "trial_balance": "validation_source",
        "bank_statement": "cash_source",
        "cash_liquidity_report": "cash_source",
        "ar_aging": "ar_aging_source",
        "ap_aging": "ap_aging_source",
        "customer_report": "customer_report_source",
        "supplier_report": "supplier_report_source",
        "unknown": "supporting_source",
    }
    return mapping.get(file_type, "supporting_source")

def validate_source_roles(file_rows: list[dict]) -> list[str]:
    warnings = []
    official_revenue = [r for r in file_rows if r.get("selected_role") == "official_revenue_source"]
    official_expense = [r for r in file_rows if r.get("selected_role") == "official_expense_source"]
    revenue_like = [r for r in file_rows if r.get("detected_type") in ["monthly_sales_wide", "item_sales", "invoice_sales", "trial_balance"]]

    if len(official_revenue) == 0:
        warnings.append("يجب اختيار مصدر رسمي واحد للإيرادات قبل التحليل.")
    if len(official_revenue) > 1:
        warnings.append("تم اختيار أكثر من مصدر رسمي للإيرادات. هذا قد يؤدي إلى تضخيم الإيرادات.")
    if len(revenue_like) > 1:
        warnings.append("تم اكتشاف أكثر من ملف مرتبط بالمبيعات. لن يتم جمعها تلقائياً.")
    if len(official_expense) == 0 and not any(r.get("selected_role") == "validation_source" for r in file_rows):
        warnings.append("لم يتم اختيار مصدر مصاريف رسمي أو ميزان مراجعة للتحقق.")
    return warnings
