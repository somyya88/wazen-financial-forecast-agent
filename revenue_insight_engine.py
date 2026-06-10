import pandas as pd

MONTH_AR = {
    "Jan": "يناير", "Feb": "فبراير", "Mar": "مارس", "Apr": "أبريل", "May": "مايو", "Jun": "يونيو",
    "Jul": "يوليو", "Aug": "أغسطس", "Sep": "سبتمبر", "Oct": "أكتوبر", "Nov": "نوفمبر", "Dec": "ديسمبر",
}

def sf(x):
    try:
        return float(x)
    except Exception:
        return 0.0

def money(x):
    return f"{sf(x):,.0f}"

def pct(x):
    return f"{sf(x)*100:.1f}%"

def build_revenue_insights(monthly_df):
    if monthly_df is None or monthly_df.empty or "revenue" not in monthly_df.columns:
        return {"cards": {}, "summary": "لا توجد بيانات إيرادات شهرية كافية.", "action": "راجع ملف الإيرادات.", "table": pd.DataFrame()}

    df = monthly_df.copy()
    df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce").fillna(0)
    df = df[df["revenue"] > 0].copy()
    if df.empty:
        return {"cards": {}, "summary": "لا توجد إيرادات موجبة قابلة للتحليل.", "action": "راجع مصدر الإيرادات.", "table": pd.DataFrame()}

    total = df["revenue"].sum()
    avg = df["revenue"].mean()
    best = df.loc[df["revenue"].idxmax()]
    worst = df.loc[df["revenue"].idxmin()]
    volatility = (df["revenue"].std() / avg) if avg else 0
    first, last = df["revenue"].iloc[0], df["revenue"].iloc[-1]
    trend = ((last - first) / first) if first else 0

    best_month = MONTH_AR.get(str(best.get("month", "")), str(best.get("month", "")))
    worst_month = MONTH_AR.get(str(worst.get("month", "")), str(worst.get("month", "")))

    if volatility > 0.25:
        summary = f"الإيرادات متذبذبة؛ أعلى شهر هو {best_month} بقيمة {money(best['revenue'])}، وأقل شهر هو {worst_month} بقيمة {money(worst['revenue'])}. الاعتماد على إجمالي الفترة وحده قد يعطي صورة غير كافية عن انتظام الإيراد."
        action = "لا تُبنى الالتزامات الثابتة على شهر مرتفع واحد. استخدم متوسطاً محافظاً، وراجع سبب انخفاض الشهر الأضعف قبل أي التزام جديد."
    elif trend < -0.05:
        summary = f"اتجاه الإيراد يميل للانخفاض بنسبة {pct(trend)} مقارنة ببداية الفترة. يجب تفسير الانخفاض: هل هو موسمي أم مرتبط بالطلب أو التحصيل أو التسعير؟"
        action = "راجع أسباب انخفاض الإيراد واربطها بعدد العملاء أو العقود أو الفروع قبل اتخاذ قرارات خفض أو نمو."
    else:
        summary = f"الإيرادات مستقرة نسبياً بمتوسط شهري {money(avg)}. لكن جودة الإيراد لا تُقاس بالاستقرار فقط، بل بقدرته على تغطية المصاريف ونقطة التعادل."
        action = "استخدم المتوسط الشهري كخط أساس للتخطيط، وراقب أن لا تنمو المصاريف التشغيلية أسرع من الإيرادات."

    table = df[["month", "revenue"]].copy()
    table["الشهر"] = table["month"].map(lambda x: MONTH_AR.get(str(x), str(x)))
    table["الإيراد"] = table["revenue"]
    table["مقارنة بالمتوسط"] = table["revenue"] - avg
    table["الحالة"] = table["revenue"].apply(lambda x: "فوق المتوسط" if x >= avg else "تحت المتوسط")
    table = table[["الشهر", "الإيراد", "مقارنة بالمتوسط", "الحالة"]]

    return {
        "cards": {
            "total": total,
            "avg": avg,
            "best_month": best_month,
            "worst_month": worst_month,
            "volatility": volatility,
            "trend": trend,
        },
        "summary": summary,
        "action": action,
        "table": table,
    }
