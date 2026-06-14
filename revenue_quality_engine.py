import pandas as pd
import numpy as np

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
    v = sf(x)
    return f"({abs(v):,.0f})" if v < 0 else f"{v:,.0f}"

def pct(x):
    v = sf(x)
    if abs(v) <= 1.5:
        v *= 100
    return f"{v:.1f}%"

def prepare_revenue_df(monthly_df):
    if monthly_df is None or monthly_df.empty or "revenue" not in monthly_df.columns:
        return pd.DataFrame()
    df = monthly_df.copy()
    df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce").fillna(0)
    df = df[df["revenue"] > 0].copy()
    df["month_ar"] = df["month"].map(lambda x: MONTH_AR.get(str(x), str(x)))
    df["mom_change"] = df["revenue"].diff()
    df["mom_growth"] = df["revenue"].pct_change()
    return df

def build_revenue_quality(monthly_df):
    df = prepare_revenue_df(monthly_df)
    if df.empty:
        return {
            "cards": {},
            "quality_table": pd.DataFrame(),
            "monthly_table": pd.DataFrame(),
            "narrative": "لا توجد بيانات إيرادات شهرية كافية لبناء تحليل جودة الإيراد.",
            "risk": "غياب الإيرادات الشهرية يمنع تقييم الاستقرار والتذبذب.",
            "action": "ارفع ملف مبيعات شهري واضح أو اربط الإيرادات بمصدر رسمي.",
        }

    total = df["revenue"].sum()
    avg = df["revenue"].mean()
    median = df["revenue"].median()
    std = df["revenue"].std(ddof=0)
    cv = std / avg if avg else 0
    best = df.loc[df["revenue"].idxmax()]
    worst = df.loc[df["revenue"].idxmin()]
    max_share = best["revenue"] / total if total else 0
    gap = best["revenue"] - worst["revenue"]
    trend = (df["revenue"].iloc[-1] - df["revenue"].iloc[0]) / df["revenue"].iloc[0] if df["revenue"].iloc[0] else 0
    negative_mom = int((df["mom_growth"].dropna() < 0).sum())
    stability_score = max(0, min(100, 100 - cv * 180 - max(0, max_share - 0.25) * 120 - negative_mom * 5))

    if cv >= 0.25 or max_share >= 0.30:
        quality_status = "يحتاج تحقق"
    elif cv >= 0.15:
        quality_status = "متوسط"
    else:
        quality_status = "مستقر نسبياً"

    quality_table = pd.DataFrame([
        {
            "المؤشر": "تركيز أعلى شهر",
            "القيمة": pct(max_share),
            "الدليل": f"{best['month_ar']} حقق {money(best['revenue'])} من أصل {money(total)}.",
            "القراءة": "كلما ارتفع تركّز الإيراد في شهر واحد، زاد خطر بناء قرارات على إيراد غير متكرر.",
            "الإجراء": "تحقق هل أعلى شهر ناتج عن عقد متكرر أم عملية استثنائية."
        },
        {
            "المؤشر": "الفجوة بين أعلى وأقل شهر",
            "القيمة": money(gap),
            "الدليل": f"أعلى شهر {best['month_ar']} مقابل أقل شهر {worst['month_ar']}.",
            "القراءة": "الفجوة الكبيرة تعني أن المتوسط الشهري قد يكون مضللاً عند التخطيط للمصاريف الثابتة.",
            "الإجراء": "استخدم متوسطاً محافظاً أو وسيط الإيراد قبل أي التزام ثابت."
        },
        {
            "المؤشر": "تذبذب الإيراد",
            "القيمة": pct(cv),
            "الدليل": f"متوسط الإيراد {money(avg)} والانحراف عن المتوسط يعكس انتظام الإيراد.",
            "القراءة": "التذبذب العالي يصعّب التنبؤ ويزيد الحاجة إلى توقع سيولة أسبوعي.",
            "الإجراء": "اربط التذبذب بالعملاء أو العقود أو الفروع لتحديد مصدر عدم الاستقرار."
        },
        {
            "المؤشر": "اتجاه الفترة",
            "القيمة": pct(trend),
            "الدليل": f"مقارنة آخر شهر بأول شهر في فترة التحليل.",
            "القراءة": "الاتجاه وحده لا يكفي للحكم، لكنه يكشف إن كان الأداء يتحسن أو يتراجع.",
            "الإجراء": "افصل أثر الموسم أو العقد الاستثنائي عن النمو الحقيقي."
        },
        {
            "المؤشر": "درجة استقرار الإيراد",
            "القيمة": f"{stability_score:.0f}/100",
            "الدليل": "تحسب من التذبذب، تركّز أعلى شهر، وعدد أشهر الانخفاض.",
            "القراءة": "هذه ليست درجة صحة مالية؛ هي مؤشر أولي لاستقرار الإيراد فقط.",
            "الإجراء": "ارفع تفاصيل الإيرادات حسب عميل/خدمة لرفع دقة القراءة."
        },
    ])

    monthly_table = df.copy()
    monthly_table["الشهر"] = monthly_table["month_ar"]
    monthly_table["الإيراد"] = monthly_table["revenue"]
    monthly_table["التغير عن الشهر السابق"] = monthly_table["mom_change"]
    monthly_table["نمو شهري"] = monthly_table["mom_growth"].apply(lambda x: "" if pd.isna(x) else pct(x))
    monthly_table["حصة الشهر من الإجمالي"] = monthly_table["revenue"].apply(lambda x: pct(x / total if total else 0))
    monthly_table["القراءة"] = monthly_table["revenue"].apply(lambda x: "فوق المتوسط" if x >= avg else "تحت المتوسط")
    monthly_table = monthly_table[["الشهر", "الإيراد", "التغير عن الشهر السابق", "نمو شهري", "حصة الشهر من الإجمالي", "القراءة"]]

    narrative = (
        f"الإيراد خلال الفترة بلغ {money(total)} بمتوسط شهري {money(avg)}. "
        f"أعلى شهر هو {best['month_ar']} ويمثل {pct(max_share)} من إجمالي الإيرادات. "
        f"هذا يعني أن قراءة الإيراد لا يجب أن تكتفي بالإجمالي؛ يجب اختبار ما إذا كان أعلى شهر متكرراً أم استثنائياً."
    )

    if quality_status == "يحتاج تحقق":
        risk = "الخطر أن يتم بناء قرار التزام مالي جديد أو مصروف ثابت على متوسط إيراد متأثر بشهر مرتفع أو تذبذب غير مفسر."
        action = "قبل أي التزام مالي جديد، افصل الإيراد المتكرر عن الإيراد الاستثنائي، وحلل أعلى 5 عملاء أو عقود خلال الفترة."
    elif quality_status == "متوسط":
        risk = "الإيراد مقبول لكنه يحتاج مراقبة لأن التذبذب قد يؤثر على السيولة الشهرية."
        action = "استخدم المتوسط الشهري كخط أساس، لكن اختبر أثر انخفاض الإيراد 10% على نقطة التعادل والسيولة."
    else:
        risk = "لا يظهر خطر كبير في انتظام الإيراد من البيانات الشهرية المتاحة، لكن السيولة والتحصيل غير محسوبين."
        action = "حافظ على انتظام الإيراد وابدأ بربطه بالتحصيل والعملاء لقياس جودة النقد لا المبيعات فقط."

    return {
        "cards": {
            "total": total,
            "avg": avg,
            "best_month": best["month_ar"],
            "max_share": max_share,
            "cv": cv,
            "stability_score": stability_score,
            "quality_status": quality_status,
            "median": median,
            "gap": gap,
        },
        "quality_table": quality_table,
        "monthly_table": monthly_table,
        "narrative": narrative,
        "risk": risk,
        "action": action,
    }
