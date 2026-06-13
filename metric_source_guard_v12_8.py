from __future__ import annotations

from typing import Any
import pandas as pd

from metric_catalog_v12_8 import get_metric_meta
from sector_profile_engine_v12_8 import metric_applicability


def _has_role(files: list[dict], role: str) -> bool:
    return any((f.get("selected_role") == role and not f.get("read_error")) for f in (files or []))


def _has_tb(files: list[dict]) -> bool:
    return _has_role(files, "validation_source")


def _num_or_none(x: Any):
    try:
        if x is None or pd.isna(x):
            return None
    except Exception:
        pass
    try:
        return float(x)
    except Exception:
        return None


def build_metric_guard_report(ratio_df: pd.DataFrame, metric_pack: dict | None, profile: dict | None, files: list[dict] | None, full_model: dict | None = None) -> pd.DataFrame:
    ratio_df = ratio_df.copy() if isinstance(ratio_df, pd.DataFrame) else pd.DataFrame()
    if ratio_df.empty:
        return ratio_df

    metric_pack = metric_pack or {}
    metrics = metric_pack.get("metrics", {}) or {}
    full_model = full_model or {}
    balance = full_model.get("balance_sheet", {}) or {}
    balance_metrics = balance.get("metrics", {}) or {}
    ar_quality = str(balance_metrics.get("ar_quality", ""))

    evidence = {
        "has_inventory": bool(_num_or_none(balance_metrics.get("inventory")) and abs(_num_or_none(balance_metrics.get("inventory")) or 0) > 1e-9),
        "has_tb": _has_tb(files or []),
        "has_cash_file": _has_role(files or [], "cash_source"),
        "has_ar_aging": _has_role(files or [], "ar_aging_source"),
        "has_ap_aging": _has_role(files or [], "ap_aging_source"),
        "has_revenue": _has_role(files or [], "official_revenue_source"),
        "has_expense": _has_role(files or [], "official_expense_source"),
    }

    source_map = {
        "revenue_leakage_ratio": "ميزان المراجعة / Gross Sales + Returns + Discounts",
        "gross_margin": "ميزان المراجعة / قائمة الدخل",
        "cogs_ratio": "ميزان المراجعة بعد التصنيف",
        "operating_margin": "ميزان المراجعة / قائمة الدخل",
        "ebitda_margin": "قائمة الدخل مع الإهلاك والاستهلاك إن وجد",
        "net_margin": "ميزان المراجعة / قائمة الدخل",
        "admin_ratio": "ميزان المراجعة بعد خريطة التصنيف",
        "sm_ratio": "ميزان المراجعة بعد خريطة التصنيف",
        "working_capital": "المركز المالي من ميزان المراجعة",
        "current_ratio": "المركز المالي من ميزان المراجعة",
        "quick_ratio": "المركز المالي من ميزان المراجعة",
        "cash_ratio": "المركز المالي من ميزان المراجعة",
        "runway": "تقرير السيولة / كشف البنك المصنف",
        "dso": "متوسط الذمم + المبيعات / أعمار العملاء للتفصيل",
        "receivables_turnover": "المبيعات + الذمم المدينة",
        "dpo": "الموردون + تكلفة الإيراد",
        "payables_turnover": "تكلفة الإيراد + الموردون",
        "dio": "المخزون + تكلفة الإيراد",
        "inventory_turnover": "المخزون + تكلفة الإيراد",
        "ccc": "DSO + DIO - DPO",
        "asset_turnover": "الإيرادات + الأصول",
        "fixed_asset_turnover": "الإيرادات + الأصول الثابتة",
        "roa": "صافي الربح + الأصول",
        "roe": "صافي الربح + حقوق الملكية",
        "debt_ratio": "المركز المالي من ميزان المراجعة",
        "debt_to_equity": "المركز المالي من ميزان المراجعة",
        "ocf_net_income": "تدفقات نقدية تشغيلية / تقرير سيولة كبديل",
        "break_even_sales": "نموذج تعادل تقديري من سلوك التكلفة",
        "margin_of_safety": "نقطة التعادل + المبيعات",
    }

    def guard(row):
        code = str(row.get("الكود", ""))
        meta = get_metric_meta(code)
        app = metric_applicability(code, profile, evidence)
        val = metrics.get(code)
        numeric = _num_or_none(val)
        result_txt = str(row.get("النتيجة", ""))

        if app.get("display") == "hide":
            state = "غير قابل للتطبيق"
            confidence = "غير مطبق"
            display_rule = "إخفاء من الملخص"
            note = app.get("reason")
        elif code in ["dso", "receivables_turnover"] and ar_quality in ["credit_balance", "missing"]:
            state = "غير قابل للحساب"
            confidence = "منخفضة"
            display_rule = "يعرض كفجوة بيانات لا كرقم"
            note = "حساب العملاء في الميزان ليس رصيدًا مدينًا صالحًا للتحصيل؛ لا يجوز حساب DSO قبل رفع تقرير العملاء أو أعمار الديون."
        elif numeric is None or result_txt in ["غير متاح", "غير محسوب", "nan", "None", ""]:
            state = "غير قابل للحساب"
            confidence = "منخفضة"
            display_rule = "يعرض كفجوة بيانات لا كرقم"
            note = meta.get("needs", "مدخلات غير مكتملة")
        else:
            state = app.get("state", "محسوب")
            # lower confidence when metric ideally needs average but only one TB may exist
            if meta.get("must_average") and not (evidence.get("has_ar_aging") or evidence.get("has_ap_aging")):
                confidence = "متوسطة / تقديرية"
                note = "المؤشر محسوب من البيانات المتاحة؛ دقته ترتفع عند توفر أرصدة أول وآخر أو أعمار تفصيلية."
            elif code in ["runway", "ocf_net_income"] and not evidence.get("has_cash_file"):
                confidence = "منخفضة"
                note = "يحتاج تقرير سيولة أو تدفقات نقدية حتى يصبح موثوقًا."
            else:
                confidence = "مرتفعة" if evidence.get("has_tb") or code in ["runway"] else "متوسطة"
                note = meta.get("cma", app.get("reason", ""))
            display_rule = "ملخص" if app.get("display") == "summary" else "تفاصيل"
        return pd.Series({
            "حالة المؤشر": state,
            "مصدر الحساب": source_map.get(code, meta.get("primary", "غير محدد")),
            "درجة الثقة": confidence,
            "شرط العرض": display_rule,
            "ملاحظة CMA": note,
            "المطلوب للحساب": meta.get("needs", "—"),
            "المصدر الأساسي": meta.get("primary", "—"),
        })

    add = ratio_df.apply(guard, axis=1)
    out = pd.concat([ratio_df, add], axis=1)
    priority = {"أساسي": 4, "مهم عند توفر البيانات": 3, "تقديري": 2, "ثانوي": 1, "غير قابل للحساب": 0, "غير قابل للتطبيق": -1}
    out["ترتيب الحارس"] = out["حالة المؤشر"].map(priority).fillna(1)
    return out.sort_values(["ترتيب الحارس", "أولوية العرض" if "أولوية العرض" in out.columns else "ترتيب الحارس"], ascending=False).reset_index(drop=True)


def metric_guard_summary(guarded_df: pd.DataFrame) -> dict:
    if guarded_df is None or guarded_df.empty:
        return {"coverage": 0, "confidence": "غير متاح", "available": 0, "total": 0}
    total = len(guarded_df)
    available = int((~guarded_df["حالة المؤشر"].astype(str).isin(["غير قابل للحساب", "غير قابل للتطبيق"])).sum())
    coverage = round(available / total * 100, 0) if total else 0
    high = int(guarded_df["درجة الثقة"].astype(str).str.contains("مرتفعة", na=False).sum())
    mid = int(guarded_df["درجة الثقة"].astype(str).str.contains("متوسطة", na=False).sum())
    if available == 0:
        conf = "غير متاح"
    elif high / max(available, 1) >= .55:
        conf = "مرتفعة"
    elif (high + mid) / max(available, 1) >= .60:
        conf = "متوسطة"
    else:
        conf = "منخفضة"
    return {"coverage": coverage, "confidence": conf, "available": available, "total": total}
