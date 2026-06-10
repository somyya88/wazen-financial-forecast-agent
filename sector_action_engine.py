import pandas as pd

def sf(x):
    try: return float(x)
    except Exception: return 0.0

def pct(x): return f"{sf(x)*100:.1f}%"

RULES = {
    "خدمي": {
        "gross_margin": ("هامش مجمل الربح", .45, .30, "higher"),
        "net_margin": ("هامش صافي الربح", .12, .06, "higher"),
        "opex_ratio": ("نسبة المصاريف التشغيلية", .40, .55, "lower"),
        "direct_cost_ratio": ("نسبة تكلفة الإيراد", .45, .60, "lower"),
        "margin_of_safety": ("هامش الأمان", .25, .15, "higher"),
    },
    "تجاري": {
        "gross_margin": ("هامش مجمل الربح", .25, .15, "higher"),
        "net_margin": ("هامش صافي الربح", .07, .03, "higher"),
        "opex_ratio": ("نسبة المصاريف التشغيلية", .22, .35, "lower"),
        "direct_cost_ratio": ("نسبة تكلفة البضاعة", .75, .85, "lower"),
        "margin_of_safety": ("هامش الأمان", .20, .10, "higher"),
    },
    "صناعي": {
        "gross_margin": ("هامش مجمل الربح", .30, .20, "higher"),
        "net_margin": ("هامش صافي الربح", .08, .03, "higher"),
        "opex_ratio": ("نسبة المصاريف التشغيلية", .25, .40, "lower"),
        "direct_cost_ratio": ("نسبة تكلفة الإنتاج", .70, .82, "lower"),
        "margin_of_safety": ("هامش الأمان", .25, .12, "higher"),
    },
    "SaaS": {
        "gross_margin": ("هامش مجمل الربح", .70, .55, "higher"),
        "net_margin": ("هامش صافي الربح", .10, .00, "higher"),
        "opex_ratio": ("نسبة المصاريف التشغيلية", .65, .85, "lower"),
        "direct_cost_ratio": ("تكلفة تقديم الخدمة", .30, .45, "lower"),
        "margin_of_safety": ("هامش الأمان", .20, .10, "higher"),
    },
}

def get_rules(sector):
    return RULES.get(sector, RULES["خدمي"])

def compute_metrics(pnl_model, breakeven_model=None):
    revenue = sf(pnl_model.get("revenue", 0))
    gross_profit = sf(pnl_model.get("gross_profit", 0))
    net_profit = sf(pnl_model.get("net_profit", 0))
    cogs = sf(pnl_model.get("cogs", 0))
    opex = sf(pnl_model.get("opex", 0))
    return {
        "gross_margin": gross_profit / revenue if revenue else 0,
        "net_margin": net_profit / revenue if revenue else 0,
        "opex_ratio": opex / revenue if revenue else 0,
        "direct_cost_ratio": cogs / revenue if revenue else 0,
        "margin_of_safety": sf((breakeven_model or {}).get("margin_of_safety", 0)),
    }

def status_and_gap(value, safe, watch, direction):
    if direction == "higher":
        gap = value - safe
        if value >= safe: return "آمن", gap, 0, f"آمن إذا كان ≥ {pct(safe)}"
        if value >= watch: return "مراقبة", gap, abs(gap)*100, f"آمن إذا كان ≥ {pct(safe)}"
        return "خطر", gap, abs(value-watch)*100 + 35, f"آمن إذا كان ≥ {pct(safe)}"
    gap = value - safe
    if value <= safe: return "آمن", gap, 0, f"آمن إذا كان ≤ {pct(safe)}"
    if value <= watch: return "مراقبة", gap, abs(gap)*100, f"آمن إذا كان ≤ {pct(safe)}"
    return "خطر", gap, abs(value-watch)*100 + 35, f"آمن إذا كان ≤ {pct(safe)}"

def meaning(metric, status):
    if metric == "opex_ratio":
        return "المصاريف التشغيلية تستهلك جزءاً كبيراً من الإيرادات، وهذا يضغط على الربح والسيولة عند أي تراجع في المبيعات." if status != "آمن" else "المصاريف التشغيلية ضمن مستوى مقبول، لكن يجب مراقبة البنود الثابتة شهرياً."
    if metric == "direct_cost_ratio":
        return "تكلفة الإيراد مرتفعة؛ أي أن جزءاً كبيراً من كل عملية بيع يخرج قبل الوصول إلى مجمل الربح." if status != "آمن" else "تكلفة الإيراد ضمن مستوى مقبول ويمكن البناء على الهامش المباشر."
    if metric == "gross_margin":
        return "مجمل الربح لا يعطي مساحة كافية قبل المصاريف الإدارية والتسويقية." if status != "آمن" else "مجمل الربح جيد مقارنة بطبيعة القطاع."
    if metric == "net_margin":
        return "صافي الربح لا يترك مساحة كافية لامتصاص تأخر التحصيل أو ارتفاع التكاليف." if status != "آمن" else "صافي الربح جيد، لكن الحفاظ عليه يتطلب ضبط المصاريف."
    if metric == "margin_of_safety":
        return "النشاط قريب من نقطة التعادل؛ أي انخفاض في الإيراد أو زيادة في التكاليف قد يضغط الربحية." if status != "آمن" else "هناك مسافة جيدة قبل نقطة التعادل، وهذا يعطي مساحة لإدارة المصاريف بهدوء."
    return "يحتاج مراجعة."

def action(metric, status):
    if status == "آمن":
        return "حافظ على المستوى الحالي وراقب المؤشر شهرياً."
    return {
        "opex_ratio": "راجع أكبر 5 بنود مصاريف تشغيلية وصنفها إلى: ضرورية، قابلة للتفاوض، قابلة للإيقاف.",
        "direct_cost_ratio": "راجع التسعير والمشتريات وتكلفة تقديم الخدمة أو المنتج حسب كل نشاط.",
        "gross_margin": "راجع التسعير وتكلفة الشراء أو تكلفة تقديم الخدمة قبل خفض المصاريف العامة.",
        "net_margin": "حلل العملاء أو الخدمات الأعلى ربحية وخفف البنود التي لا تخدم الإيراد.",
        "margin_of_safety": "أوقف أي التزام ثابت جديد وارفع الإيراد المتكرر أو اخفض التكاليف الثابتة.",
    }.get(metric, "حدد إجراء رقابي شهري.")

def owner(metric):
    return {
        "gross_margin": "المالية + التشغيل",
        "net_margin": "المالية + الإدارة",
        "opex_ratio": "المالية + التشغيل",
        "direct_cost_ratio": "المالية + المشتريات/التشغيل",
        "margin_of_safety": "المالية + الإدارة",
    }.get(metric, "الإدارة المالية")

def kpi(metric, safe):
    return {
        "gross_margin": f"هامش مجمل ربح لا يقل عن {pct(safe)}.",
        "net_margin": f"هامش صافي ربح لا يقل عن {pct(safe)}.",
        "opex_ratio": f"مصاريف تشغيلية لا تتجاوز {pct(safe)} من الإيرادات.",
        "direct_cost_ratio": f"تكلفة إيراد لا تتجاوز {pct(safe)}.",
        "margin_of_safety": f"هامش أمان لا يقل عن {pct(safe)}.",
    }.get(metric, "مراجعة شهرية.")

def build_sector_safety_scorecard(pnl_model, breakeven_model=None, sector="خدمي", country="", activity=""):
    metrics = compute_metrics(pnl_model, breakeven_model)
    rows = []
    for metric, (label, safe, watch, direction) in get_rules(sector).items():
        value = metrics.get(metric, 0)
        st, gap, sev, bench = status_and_gap(value, safe, watch, direction)
        rows.append({
            "المؤشر": label,
            "قيمة الشركة": value,
            "معيار السلامة": bench,
            "الفجوة عن المعيار": gap,
            "الحالة": st,
            "ماذا يعني؟": meaning(metric, st),
            "الإجراء العملي": action(metric, st),
            "المسؤول": owner(metric),
            "KPI الشهر القادم": kpi(metric, safe),
            "_severity": sev,
        })
    return pd.DataFrame(rows).sort_values("_severity", ascending=False).reset_index(drop=True)

def build_top_5_actions(scorecard_df):
    if scorecard_df is None or scorecard_df.empty:
        return pd.DataFrame()
    df = scorecard_df.copy()
    df["_p"] = df["الحالة"].map({"خطر": 3, "مراقبة": 2, "آمن": 1}).fillna(0)
    df = df.sort_values(["_p", "_severity"], ascending=False).head(5)
    return pd.DataFrame([{
        "الأولوية": i,
        "المشكلة": f"{r['المؤشر']} — {r['الحالة']}",
        "لماذا يهم؟": r["ماذا يعني؟"],
        "الإجراء المطلوب": r["الإجراء العملي"],
        "المسؤول": r["المسؤول"],
        "مؤشر المتابعة": r["KPI الشهر القادم"],
    } for i, (_, r) in enumerate(df.iterrows(), 1)])

def build_scorecard_summary(scorecard_df, sector="خدمي"):
    if scorecard_df is None or scorecard_df.empty:
        return {"title": "لا توجد بيانات كافية", "summary": "لا يمكن بناء مقارنة قطاعية.", "risk": "التحليل غير مكتمل.", "action": "ارفع الملفات المطلوبة."}
    risk_rows = scorecard_df[scorecard_df["الحالة"].isin(["خطر", "مراقبة"])]
    if risk_rows.empty:
        return {"title": "الأداء ضمن الحدود المقبولة", "summary": f"المؤشرات الأساسية ضمن معايير قطاع {sector}.", "risk": "الخطر هو فقدان الانضباط عند إضافة التزامات ثابتة.", "action": "اعتمد سقف مصاريف شهري وراجع أي التزام جديد."}
    top = risk_rows.iloc[0]
    return {"title": f"أكبر نقطة تحتاج انتباه: {top['المؤشر']}", "summary": top["ماذا يعني؟"], "risk": f"الحالة الحالية: {top['الحالة']}.", "action": top["الإجراء العملي"]}
