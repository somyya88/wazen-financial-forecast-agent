
def _norm(s):
    return str(s or "").strip().lower().replace("_"," ").replace("-"," ").replace("#"," ")

def resolve_by_filename(filename, detected_type="", suggested_role="", confidence=0):
    name = _norm(filename)
    conf = float(confidence or 0)
    detected = _norm(detected_type)

    if any(x in name for x in ["أعمار ديون العملاء", "اعمار ديون العملاء", "أعمار العملاء", "اعمار العملاء", "ديون العملاء", "ذمم العملاء", "customer aging", "receivable"]):
        return "ar_aging", "ar_aging_source", max(conf, .98), "أعمار عملاء: يستخدم للتحصيل والسيولة."
    if any(x in name for x in ["أعمار ديون الموردين", "اعمار ديون الموردين", "أعمار الموردين", "اعمار الموردين", "ديون الموردين", "ذمم الموردين", "supplier aging", "vendor aging", "payable"]):
        return "ap_aging", "ap_aging_source", max(conf, .98), "أعمار موردين: يستخدم للالتزامات والسيولة."

    if any(x in name for x in ["تقرير العملاء", "كشف العملاء", "حساب العملاء", "customer report", "customer statement"]):
        return "customer_report", "customer_report_source", max(conf, .94), "تقرير عملاء: يستخدم لتفاصيل العملاء، التركّز، وربطه لاحقًا بالمبيعات والتحصيل."
    if any(x in name for x in ["تقرير الموردين", "كشف الموردين", "حساب الموردين", "supplier report", "vendor report", "supplier statement"]):
        return "supplier_report", "supplier_report_source", max(conf, .94), "تقرير موردين: يستخدم لتفاصيل الموردين وضغط الالتزامات وربطه لاحقًا بالدفع."

    if any(x in name for x in ["تقرير السيولة النقدية", "السيولة النقدية", "cash liquidity", "cash flow report"]):
        return "cash_liquidity_report", "cash_source", max(conf, .98), "تقرير سيولة نقدية: يستخدم كمدخل تنفيذي لحركة النقد الشهرية."

    bank_words = ["كشف حساب البنك", "كشف حساب", "حساب البنك", "البنك الأهلي", "البنك الاهلي", "الأهلي", "الاهلي", "الراجحي", "بنك", "bank statement", "statement", "ahli", "rajhi"]
    tb_words = ["ميزان المراجعة", "ميزان مراجعه", "trial balance"]
    if any(x in name for x in bank_words) and not any(x in name for x in tb_words):
        return "bank_statement", "cash_source", max(conf, .98), "كشف بنك: يستخدم للسيولة والمطابقة وليس لقائمة الدخل."

    if any(x in name for x in tb_words) or "trial_balance" in detected:
        return "trial_balance", "validation_source", max(conf, .98), "ميزان مراجعة: المصدر الرسمي لقائمة الدخل."

    if any(x in name for x in ["المبيعات الشهرية", "مبيعات شهرية", "monthly sales"]) or "sales" in detected:
        return detected_type or "monthly_sales_wide", "official_revenue_source", max(conf, .90), "ملف مبيعات للتحليل الشهري."
    if any(x in name for x in ["تقرير المصروفات", "المصروفات", "مصروفات", "expenses", "expense"]) or "expense" in detected:
        return detected_type or "expense_monthly", "official_expense_source", max(conf, .90), "ملف مصاريف للتحليل والتصنيف."

    return detected_type or "unknown", suggested_role or "supporting_source", conf or .25, "غير مؤكد؛ يحتاج تحديد يدوي."

def apply_role_resolution_to_record(record):
    detected, role, conf, reason = resolve_by_filename(
        record.get("file_name") or record.get("filename") or "",
        record.get("detected_type") or record.get("type") or "",
        record.get("selected_role") or record.get("suggested_role") or "",
        record.get("confidence", 0),
    )
    record["detected_type"] = detected
    record["suggested_role"] = role
    record["selected_role"] = role
    record["confidence"] = conf
    record["role_reason"] = reason
    return record

def has_liquidity_files(files):
    roles = {str(f.get("selected_role") or "").lower() for f in (files or [])}
    return bool(roles.intersection({"cash_source", "ar_aging_source", "ap_aging_source"}))

def liquidity_files_summary(files):
    roles = {str(f.get("selected_role") or "").lower() for f in (files or [])}
    out=[]
    if "cash_source" in roles:
        out.append("كشف بنك")
    if "ar_aging_source" in roles:
        out.append("أعمار العملاء")
    if "ap_aging_source" in roles:
        out.append("أعمار الموردين")
    if "customer_report_source" in roles:
        out.append("تقرير العملاء")
    if "supplier_report_source" in roles:
        out.append("تقرير الموردين")
    return "، ".join(out) if out else "غير مرفقة"
