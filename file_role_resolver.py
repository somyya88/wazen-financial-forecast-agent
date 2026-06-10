
def _norm(s):
    return str(s or "").strip().lower().replace("_", " ").replace("-", " ")

def resolve_file_role(filename="", detected_type="", current_role="", confidence=0):
    name = _norm(filename)
    detected = _norm(detected_type)
    conf = float(confidence or 0)
    if any(w in name for w in ["كشف حساب", "حساب البنك", "البنك", "بنك", "الاهلي", "الأهلي", "الراجحي", "bank statement", "ahli", "rajhi"]) and not any(w in name for w in ["ميزان", "trial balance"]):
        return {"role":"cash_source", "type":"bank_statement", "confidence":max(conf, .95), "reason":"كشف بنك: يستخدم للسيولة والمطابقة، وليس لبناء قائمة الدخل."}
    if any(w in name for w in ["أعمار العملاء", "اعمار العملاء", "ذمم العملاء", "العملاء", "receivable", "customer aging"]):
        return {"role":"supporting_source", "type":"ar_aging", "confidence":max(conf, .95), "reason":"أعمار العملاء: يستخدم للتحصيل والسيولة، وليس لبناء قائمة الدخل."}
    if any(w in name for w in ["أعمار الموردين", "اعمار الموردين", "ذمم الموردين", "الموردين", "payable", "supplier aging", "vendor aging"]):
        return {"role":"supporting_source", "type":"ap_aging", "confidence":max(conf, .95), "reason":"أعمار الموردين: يستخدم للالتزامات والسيولة، وليس لبناء قائمة الدخل."}
    if any(w in name for w in ["ميزان المراجعة", "ميزان مراجعه", "trial balance"]) or "trial balance" in detected or "trial_balance" in detected:
        return {"role":"validation_source", "type":"trial_balance", "confidence":max(conf, .98), "reason":"ميزان المراجعة هو المصدر الرسمي لقائمة الدخل."}
    if any(w in name for w in ["المبيعات الشهرية", "مبيعات شهرية", "monthly sales"]) or "sales" in detected:
        return {"role":"official_revenue_source", "type": detected_type or "monthly_sales_wide", "confidence":max(conf, .85), "reason":"المبيعات للتحليل الشهري وتوزيع الإيراد."}
    if any(w in name for w in ["تقرير المصروفات", "المصروفات", "expenses", "expense"]) or "expense" in detected:
        return {"role":"official_expense_source", "type": detected_type or "expense_monthly", "confidence":max(conf, .90), "reason":"المصاريف للتحليل التفصيلي والتصنيف."}
    return {"role": current_role or "supporting_source", "type": detected_type or "unknown", "confidence": conf or .25, "reason":"مصدر داعم لم يتم التعرف عليه بثقة."}
