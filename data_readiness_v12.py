from __future__ import annotations

import pandas as pd

CORE_ROLES = {
    "official_revenue_source": "مصدر الإيرادات الرسمي",
    "official_expense_source": "مصدر المصروفات الرسمي",
    "validation_source": "ميزان المراجعة / مصدر التحقق",
}
LIQUIDITY_ROLES = {
    "cash_source": "مصدر السيولة / البنك",
    "ar_aging_source": "أعمار ديون العملاء",
    "ap_aging_source": "أعمار ديون الموردين",
}
ENHANCEMENT_SIGNALS = {
    "revenue_detail_source": "تفاصيل المبيعات / العملاء / الأصناف",
    "expense_detail_source": "تفاصيل مصروفات إضافية",
    "customer_report_source": "تقرير العملاء",
    "supplier_report_source": "تقرير الموردين",
    "supporting_source": "مصدر داعم",
}


def _files_by_role(files: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for f in files or []:
        role = str(f.get("selected_role") or "unknown")
        out.setdefault(role, []).append(f)
    return out


def _has_role(role_map: dict[str, list[dict]], role: str) -> bool:
    return bool(role_map.get(role))


def _avg_confidence(files: list[dict]) -> float:
    vals = []
    for f in files or []:
        try:
            if not f.get("read_error"):
                vals.append(float(f.get("confidence") or 0))
        except Exception:
            pass
    return sum(vals) / len(vals) if vals else 0.0




def detect_branch_signal(files: list[dict]) -> dict:
    """Detect whether uploaded files appear to include branch-level data."""
    branch_cols = ["فرع", "الفرع", "branch", "location", "موقع", "مركز"]
    hits = []
    for f in files or []:
        df = f.get("primary_df")
        if df is None or getattr(df, "empty", True):
            continue
        cols = " ".join([str(c).lower() for c in df.columns])
        sample = " ".join(df.astype(str).head(15).fillna("").values.flatten()).lower()
        if any(k.lower() in cols or k.lower() in sample for k in branch_cols):
            hits.append(f.get("file_name"))
    return {"has_branch_signal": bool(hits), "files": hits}


def build_readiness_profile(files: list[dict], business_profile: dict | None = None, models: dict | None = None) -> dict:
    role_map = _files_by_role(files)
    rows = []
    score = 0
    max_score = 100

    branch_signal = detect_branch_signal(files)
    wants_branch = bool(business_profile and str(business_profile.get("branch_mode", "")).startswith("إجمالي +"))

    checks = [
        ("Business Context", "سياق الشركة", bool(business_profile and business_profile.get("sector") and business_profile.get("country")), 10, "تحديد البلد والقطاع ضروري لتفسير نسب السلامة."),
        ("Revenue", "الإيرادات", _has_role(role_map, "official_revenue_source"), 15, "مصدر الإيرادات الرسمي يمنع تضخيم المبيعات أو تكرارها."),
        ("Expenses", "المصروفات", _has_role(role_map, "official_expense_source"), 15, "مصدر المصروفات ضروري لتحليل الربحية والتكاليف."),
        ("Trial Balance", "ميزان المراجعة", _has_role(role_map, "validation_source"), 15, "ميزان المراجعة هو مرجع المطابقة وبناء القوائم."),
        ("Cash", "السيولة", _has_role(role_map, "cash_source"), 12, "تقرير السيولة أو كشوف البنك يرفع جودة قراءة النقد."),
        ("AR Aging", "أعمار العملاء", _has_role(role_map, "ar_aging_source"), 12, "أعمار العملاء تحول التحصيل من توصية عامة إلى قائمة عملاء وأرصدة."),
        ("AP Aging", "أعمار الموردين", _has_role(role_map, "ap_aging_source"), 8, "أعمار الموردين تكشف ضغط الالتزامات."),
        ("Customer/Supplier Details", "تقارير العملاء والموردين", _has_role(role_map, "customer_report_source") or _has_role(role_map, "supplier_report_source"), 4, "تساعد في فهم تركّز العملاء والموردين، حتى لو لم تكن بديلًا عن أعمار الديون."),
        ("Details", "تفاصيل إضافية للتنبؤ", _has_role(role_map, "revenue_detail_source") or len(role_map.get("supporting_source", [])) > 0 or _has_role(role_map, "customer_report_source"), 4, "تفاصيل العملاء/الأصناف/السنة السابقة ترفع دقة التنبؤ."),
        ("Branch Readiness", "تحليل الفروع", (not wants_branch) or branch_signal["has_branch_signal"], 5, "إذا كانت الشركة متعددة الفروع، نحتاج ملفًا يحتوي عمود الفرع أو تقارير منفصلة لكل فرع."),
        ("Model", "النموذج المالي", bool(models), 5, "بناء النموذج يتيح التشخيص والسيناريوهات."),
    ]
    for key, label, ok, pts, note in checks:
        if ok:
            score += pts
        rows.append({
            "البند": label,
            "الحالة": "متوفر" if ok else "غير متوفر",
            "الأثر": note,
            "النقاط": pts if ok else 0,
        })

    confidence = _avg_confidence(files)
    if confidence >= 0.90:
        score += 0
    elif confidence < 0.60 and files:
        score = max(0, score - 10)

    # Owner-friendly readiness language: explain scope, not a generic score.
    has_revenue = _has_role(role_map, "official_revenue_source")
    has_expenses = _has_role(role_map, "official_expense_source")
    has_tb = _has_role(role_map, "validation_source")
    has_cash = _has_role(role_map, "cash_source")
    has_ar = _has_role(role_map, "ar_aging_source")

    if score >= 80:
        label = "نطاق تحليل قوي"
        status = "بحسب الملفات الحالية يمكن بناء قراءة ربحية وتشغيل وسيولة أولية، مع إمكانية الانتقال إلى التشخيص التنفيذي والسيناريوهات. التحليل يصبح أعمق عند إضافة مبيعات تفصيلية حسب العميل/الصنف أو سنة سابقة."
    elif has_revenue and has_expenses and has_tb:
        label = "نطاق تحليل مالي مقبول"
        missing_parts = []
        if not has_cash:
            missing_parts.append("حركة النقد")
        if not has_ar:
            missing_parts.append("أولويات التحصيل بالأسماء")
        missing_txt = " و".join(missing_parts) if missing_parts else "بعض التفاصيل التشغيلية"
        status = f"بحسب الملفات الحالية يمكن تحليل الربحية والمصاريف ومطابقة الأرقام مع ميزان المراجعة. ما زال تحليل {missing_txt} يحتاج ملفًا إضافيًا لرفع الدقة."
    elif has_revenue or has_expenses or has_tb:
        label = "نطاق قراءة مبدئية"
        status = "الملفات المرفوعة تكفي لفهم جزء من الصورة، لكنها لا تكفي لبناء نموذج مالي متكامل. نحتاج على الأقل ميزان مراجعة ومبيعات ومصروفات قبل إصدار تشخيص نهائي."
    else:
        label = "لا توجد بيانات مالية كافية"
        status = "ابدئي برفع ميزان المراجعة وتقرير المبيعات وتقرير المصروفات. بعدها يمكن للإيجنت بناء التشخيص المالي وربط النتائج بالتوصيات."

    missing = [r[1] for r in checks if not r[2]]
    uploaded_table = []
    for f in files or []:
        uploaded_table.append({
            "الملف": f.get("file_name"),
            "النوع المكتشف": f.get("detected_type"),
            "الدور": f.get("selected_role"),
            "الثقة": round(float(f.get("confidence") or 0) * 100, 1),
            "ملاحظة": f.get("role_reason") or (f.get("read_error") or ""),
        })

    return {
        "score": min(100, max(0, int(score))),
        "label": label,
        "status": status,
        "checks": pd.DataFrame(rows),
        "uploaded_files": pd.DataFrame(uploaded_table),
        "missing": missing,
        "role_map": role_map,
        "avg_confidence": confidence,
        "branch_signal": branch_signal,
    }


def build_missing_data_recommendations(profile: dict) -> pd.DataFrame:
    missing = set(profile.get("missing", []))
    rows = []
    if "أعمار العملاء" in missing:
        rows.append(["تحليل التحصيل", "ارفع أعمار ديون العملاء", "لإظهار العملاء المتأخرين بالأسماء والأرصدة وأولوية المتابعة."])
    if "السيولة" in missing:
        rows.append(["تحليل النقد", "ارفع تقرير السيولة النقدية أو كشوف البنك", "لحساب حركة النقد والـ Runway والتحقق من الربح النقدي."])
    if "تقارير العملاء والموردين" in missing:
        rows.append(["تركيز العملاء والموردين", "ارفع تقرير العملاء أو تقرير الموردين عند توفره", "يساعد في عرض الأسماء والأرصدة والتعاملات بشكل تفاعلي لاحقًا."])
    if "تفاصيل ترفع الدقة" in missing:
        rows.append(["دقة التنبؤ", "ارفع مبيعات السنة السابقة أو مبيعات الأصناف/العملاء", "لاستخراج الموسمية، المرتجعات، الخصومات، وتركيز العملاء."])
    if "ميزان المراجعة" in missing:
        rows.append(["المطابقة", "ارفع ميزان المراجعة", "لمنع تحليل مبني على ملفات فرعية غير مطابقة للدفاتر."])
    if not rows:
        rows.append(["تعميق التحليل", "مبيعات تفصيلية أو سنة سابقة عند توفرها", "ليست إلزامية الآن، لكنها تضيف تحليل الموسمية والخصومات والمرتجعات حسب العميل أو الصنف."])
    return pd.DataFrame(rows, columns=["المجال", "المطلوب بلغة بسيطة", "القيمة المضافة"])
