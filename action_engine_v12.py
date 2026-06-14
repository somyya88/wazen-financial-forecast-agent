from __future__ import annotations

import pandas as pd


def build_action_center(models: dict | None, liquidity_model: dict | None, readiness_profile: dict | None = None) -> pd.DataFrame:
    rows = []
    models = models or {}
    pnl = models.get("pnl_model", {}) or {}
    expense = models.get("expense_model", {}) or {}
    liq = liquidity_model or {}
    cash = (liq.get("cash") or {})
    ar = (liq.get("ar") or {})

    net_profit = float(pnl.get("net_profit") or 0) if isinstance(pnl, dict) else 0
    total_revenue = float(pnl.get("total_revenue") or 0) if isinstance(pnl, dict) else 0
    net_margin = net_profit / total_revenue if total_revenue else 0

    if total_revenue and net_margin < 0.08:
        rows.append(["ربحية", "هامش الربح منخفض", f"هامش صافي الربح {net_margin*100:.1f}%", "راجع أكبر 10 مصاريف وهوامش تكلفة المبيعات", "30 يوم", "هامش صافي الربح"])
    elif total_revenue:
        rows.append(["ربحية", "الربحية تحتاج ربطها بالنقد", f"صافي الربح {net_profit:,.0f}", "قارن الربح بصافي الحركة النقدية والتحصيل", "شهري", "Profit-to-Cash"])

    if cash.get("available"):
        c = cash.get("cards", {})
        runway = c.get("cash_runway_months")
        net_cash = c.get("net_cash_flow", 0) or 0
        if runway is not None and runway < 1:
            rows.append(["سيولة", "Runway أقل من شهر", f"النقد يغطي {runway:.1f} شهر تقريبًا", "جمّد المدفوعات غير الحرجة وابدأ خطة تحصيل أسبوعية", "14 يوم", "Cash Runway"])
        elif net_cash < 0:
            rows.append(["سيولة", "صافي الحركة النقدية سلبي", f"صافي الحركة {net_cash:,.0f}", "حلل أشهر الضغط وافصل المتكرر عن غير المتكرر", "30 يوم", "Net Cash Flow"])

    if ar.get("available"):
        a = ar.get("cards", {})
        overdue_pct = a.get("overdue_pct", 0) or 0
        conc = a.get("top5_concentration", 0) or 0
        if overdue_pct > 0.25 or conc > 0.6:
            rows.append(["تحصيل", "خطر الذمم مركز أو متأخر", f"المتأخر {overdue_pct*100:.1f}%، تركيز أعلى 5 عملاء {conc*100:.1f}%", "ابدأ بالعملاء الأعلى رصيدًا في جدول الأولويات", "7-14 يوم", "Overdue AR / Top 5"])
        else:
            rows.append(["تحصيل", "الذمم لا تظهر ضغطًا عاليًا", f"إجمالي العملاء {a.get('total_balance',0):,.0f}", "استمر في المتابعة الوقائية ولا ترفع حدود الائتمان دون سياسة", "شهري", "AR Aging"])

    if readiness_profile and readiness_profile.get("score", 0) < 60:
        rows.append(["جودة بيانات", "دقة التوقع محدودة", f"جاهزية التحليل {readiness_profile.get('score')}%", "استكمل ملف السيولة/أعمار العملاء/مبيعات تفصيلية حسب النقص", "قبل الاعتماد النهائي", "درجة قابلية التحليل"])

    if not rows:
        rows.append(["تشغيل", "لا توجد إنذارات كافية بعد", "البيانات الحالية تحتاج بناء النموذج أو رفع مصادر إضافية", "ابدأ بجاهزية التحليل ثم التشخيص التنفيذي", "اليوم", "Data Readiness"])

    return pd.DataFrame(rows, columns=["المجال", "المشكلة/الفرصة", "الدليل", "الإجراء المقترح", "المدة", "مؤشر المتابعة"])
