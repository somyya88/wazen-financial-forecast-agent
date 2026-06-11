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


def build_readiness_profile(files: list[dict], business_profile: dict | None = None, models: dict | None = None) -> dict:
    role_map = _files_by_role(files)
    rows = []
    score = 0
    max_score = 100

    checks = [
        ("Business Context", "سياق النشاط", bool(business_profile and business_profile.get("sector") and business_profile.get("country")), 10, "تحديد البلد والقطاع ضروري لتفسير نسب السلامة."),
        ("Revenue", "الإيرادات", _has_role(role_map, "official_revenue_source"), 15, "مصدر الإيرادات الرسمي يمنع تضخيم المبيعات أو تكرارها."),
        ("Expenses", "المصروفات", _has_role(role_map, "official_expense_source"), 15, "مصدر المصروفات ضروري لتحليل الربحية والتكاليف."),
        ("Trial Balance", "ميزان المراجعة", _has_role(role_map, "validation_source"), 15, "ميزان المراجعة هو مرجع المطابقة وبناء القوائم."),
        ("Cash", "السيولة", _has_role(role_map, "cash_source"), 12, "تقرير السيولة أو كشوف البنك يرفع جودة قراءة النقد."),
        ("AR Aging", "أعمار العملاء", _has_role(role_map, "ar_aging_source"), 12, "أعمار العملاء تحول التحصيل من توصية عامة إلى قائمة عملاء وأرصدة."),
        ("AP Aging", "أعمار الموردين", _has_role(role_map, "ap_aging_source"), 8, "أعمار الموردين تكشف ضغط الالتزامات."),
        ("Details", "تفاصيل ترفع الدقة", _has_role(role_map, "revenue_detail_source") or len(role_map.get("supporting_source", [])) > 0, 8, "تفاصيل العملاء/الأصناف/السنة السابقة ترفع دقة التنبؤ."),
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

    if score >= 80:
        label = "جاهزية عالية"
        status = "يمكن إصدار تشخيص CFO جيد، مع إمكانية تعميق التوقع عند إضافة تفاصيل أكثر."
    elif score >= 55:
        label = "جاهزية متوسطة"
        status = "يمكن إصدار تحليل مفيد، لكن بعض النتائج يجب عرضها بدرجة ثقة متوسطة."
    else:
        label = "جاهزية محدودة"
        status = "يمكن إصدار قراءة مبدئية فقط؛ يلزم استكمال مصادر أساسية قبل الاعتماد على التوقعات."

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
    }


def build_missing_data_recommendations(profile: dict) -> pd.DataFrame:
    missing = set(profile.get("missing", []))
    rows = []
    if "أعمار العملاء" in missing:
        rows.append(["تحليل التحصيل", "ارفع أعمار ديون العملاء", "لإظهار العملاء المتأخرين بالأسماء والأرصدة وأولوية المتابعة."])
    if "السيولة" in missing:
        rows.append(["تحليل النقد", "ارفع تقرير السيولة النقدية أو كشوف البنك", "لحساب حركة النقد والـ Runway والتحقق من الربح النقدي."])
    if "تفاصيل ترفع الدقة" in missing:
        rows.append(["دقة التنبؤ", "ارفع مبيعات السنة السابقة أو مبيعات الأصناف/العملاء", "لاستخراج الموسمية، المرتجعات، الخصومات، وتركيز العملاء."])
    if "ميزان المراجعة" in missing:
        rows.append(["المطابقة", "ارفع ميزان المراجعة", "لمنع تحليل مبني على ملفات فرعية غير مطابقة للدفاتر."])
    if not rows:
        rows.append(["التحليل", "البيانات الحالية جيدة", "يمكن البدء بالتشخيص والسيناريوهات، ثم رفع ملفات تفصيلية عند الحاجة."])
    return pd.DataFrame(rows, columns=["المجال", "المطلوب بلغة بسيطة", "القيمة المضافة"])
