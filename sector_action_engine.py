
import pandas as pd

def sf(x):
    try: return float(x)
    except Exception: return 0.0

def pct(x): return f"{sf(x)*100:.1f}%"
def money(x): return f"{sf(x):,.0f}"

SECTOR_RULES = {
    "خدمي": {
        "gross_margin": {"label": "هامش مجمل الربح", "safe": 0.45, "watch": 0.30, "direction": "higher"},
        "net_margin": {"label": "هامش صافي الربح", "safe": 0.12, "watch": 0.06, "direction": "higher"},
        "opex_ratio": {"label": "نسبة المصاريف التشغيلية", "safe": 0.40, "watch": 0.55, "direction": "lower"},
        "direct_cost_ratio": {"label": "نسبة تكلفة الإيراد", "safe": 0.45, "watch": 0.60, "direction": "lower"},
        "margin_of_safety": {"label": "هامش الأمان", "safe": 0.25, "watch": 0.15, "direction": "higher"},
    },
    "تجاري": {
        "gross_margin": {"label": "هامش مجمل الربح", "safe": 0.25, "watch": 0.15, "direction": "higher"},
        "net_margin": {"label": "هامش صافي الربح", "safe": 0.07, "watch": 0.03, "direction": "higher"},
        "opex_ratio": {"label": "نسبة المصاريف التشغيلية", "safe": 0.22, "watch": 0.35, "direction": "lower"},
        "direct_cost_ratio": {"label": "نسبة تكلفة البضاعة", "safe": 0.75, "watch": 0.85, "direction": "lower"},
        "margin_of_safety": {"label": "هامش الأمان", "safe": 0.20, "watch": 0.10, "direction": "higher"},
    },
    "صناعي": {
        "gross_margin": {"label": "هامش مجمل الربح", "safe": 0.30, "watch": 0.20, "direction": "higher"},
        "net_margin": {"label": "هامش صافي الربح", "safe": 0.08, "watch": 0.03, "direction": "higher"},
        "opex_ratio": {"label": "نسبة المصاريف التشغيلية", "safe": 0.25, "watch": 0.40, "direction": "lower"},
        "direct_cost_ratio": {"label": "نسبة تكلفة الإنتاج", "safe": 0.70, "watch": 0.82, "direction": "lower"},
        "margin_of_safety": {"label": "هامش الأمان", "safe": 0.25, "watch": 0.12, "direction": "higher"},
    },
    "SaaS": {
        "gross_margin": {"label": "هامش مجمل الربح", "safe": 0.70, "watch": 0.55, "direction": "higher"},
        "net_margin": {"label": "هامش صافي الربح", "safe": 0.10, "watch": 0.00, "direction": "higher"},
        "opex_ratio": {"label": "نسبة المصاريف التشغيلية", "safe": 0.65, "watch": 0.85, "direction": "lower"},
        "direct_cost_ratio": {"label": "تكلفة تقديم الخدمة", "safe": 0.30, "watch": 0.45, "direction": "lower"},
        "margin_of_safety": {"label": "هامش الأمان", "safe": 0.20, "watch": 0.10, "direction": "higher"},
    },
}

def rules(sector): return SECTOR_RULES.get(sector, SECTOR_RULES["خدمي"])

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
        "revenue": revenue,
        "gross_profit": gross_profit,
        "net_profit": net_profit,
        "cogs": cogs,
        "opex": opex,
    }

def classify_gap(value, rule):
    safe, watch, direction = sf(rule["safe"]), sf(rule["watch"]), rule["direction"]
    if direction == "higher":
        gap = value - safe
        if value >= safe: status, severity = "آمن", 0
        elif value >= watch: status, severity = "مراقبة", min(100, abs(gap)*100)
        else: status, severity = "خطر", min(100, abs(value-watch)*100 + 35)
        benchmark_text = f"آمن إذا كان ≥ {pct(safe)}"
    else:
        gap = value - safe
        if value <= safe: status, severity = "آمن", 0
        elif value <= watch: status, severity = "مراقبة", min(100, abs(gap)*100)
        else: status, severity = "خطر", min(100, abs(value-watch)*100 + 35)
        benchmark_text = f"آمن إذا كان ≤ {pct(safe)}"
    return status, gap, severity, benchmark_text

def metric_interpretation(metric_key, value, sector, status):
    if metric_key == "gross_margin":
        return ("قدرة النشاط على تغطية تكلفة الإيراد جيدة مقارنة بطبيعة القطاع. المشكلة، إن وجدت، غالباً ليست في تكلفة البيع المباشرة بل في المصاريف اللاحقة أو التحصيل."
                if status == "آمن" else
                "مجمل الربح لا يعطي مساحة كافية قبل المصاريف الإدارية والتسويقية. يجب فحص التسعير وتكلفة الشراء أو تكلفة تقديم الخدمة قبل التفكير بخفض عام للمصاريف.")
    if metric_key == "net_margin":
        return ("صافي الربح جيد مقارنة بمعيار القطاع، لكن الحفاظ عليه يتطلب منع نمو المصاريف أسرع من الإيراد."
                if status == "آمن" else
                "الربح النهائي لا يترك مساحة كافية لامتصاص تأخر التحصيل أو ارتفاع التكاليف. زيادة المبيعات وحدها قد لا تحل المشكلة إذا بقيت الهوامش ضعيفة.")
    if metric_key == "opex_ratio":
        return ("المصاريف التشغيلية ضمن مستوى مقبول قياساً بالإيراد، لكن يجب مراقبة البنود الثابتة لأنها ترفع نقطة التعادل عند نموها."
                if status == "آمن" else
                "المصاريف التشغيلية تستهلك جزءاً كبيراً من الإيرادات. الخطر أن تبقى هذه المصاريف ثابتة حتى لو تراجعت المبيعات، مما يضغط على السيولة والربح.")
    if metric_key == "direct_cost_ratio":
        return ("تكلفة الإيراد ضمن مستوى مقبول، مما يعني أن الهامش المباشر قابل للبناء عليه إذا بقيت المشتريات والتشغيل تحت السيطرة."
                if status == "آمن" else
                "تكلفة الإيراد مرتفعة. هذا يعني أن جزءاً كبيراً من كل عملية بيع يخرج قبل أن يصل النشاط إلى مجمل الربح؛ يجب مراجعة التسعير والمشتريات وتكلفة تقديم الخدمة.")
    if metric_key == "margin_of_safety":
        return ("هناك مسافة جيدة بين الإيرادات الحالية ونقطة التعادل. هذا لا يعني التوسع تلقائياً، بل يعني وجود مساحة لإعادة ترتيب المصاريف وتحسين التحصيل بهدوء."
                if status == "آمن" else
                "النشاط قريب نسبياً من نقطة التعادل. أي انخفاض في الإيرادات أو زيادة في التكاليف الثابتة قد يحول الربحية إلى ضغط سريع.")
    return "يحتاج المؤشر إلى مراجعة إضافية."

def recommended_action(metric_key, status, value, sector):
    if status == "آمن":
        return "الحفاظ على المستوى الحالي، مع متابعة شهرية للتأكد من عدم تدهور المؤشر."
    mapping = {
        "opex_ratio": "راجع أكبر 5 بنود مصاريف تشغيلية، وصنفها إلى: ضرورية، قابلة للتفاوض، قابلة للإيقاف. لا تضف أي مصروف ثابت جديد قبل ربطه بإيراد أو تحصيل واضح.",
        "direct_cost_ratio": "راجع تكلفة الإيراد حسب المنتج أو الخدمة، وقارن سعر البيع بالتكلفة المباشرة. ابدأ بالبنود ذات الهامش الأقل قبل أي قرار توسع في المبيعات.",
        "gross_margin": "راجع التسعير والمشتريات والهدر التشغيلي. إذا كان الهامش منخفضاً من البداية، فلن يحل خفض المصاريف الإدارية وحده المشكلة.",
        "net_margin": "اربط خفض المصاريف بتحسين الربحية الفعلية. ابدأ بتحليل العملاء أو الخدمات الأعلى ربحاً وتخفيف البنود التي لا تخدم الإيراد.",
        "margin_of_safety": "ارفع هامش الأمان إما بزيادة الإيراد المتكرر أو خفض التكاليف الثابتة. أوقف أي التزام ثابت جديد حتى يتحسن المؤشر.",
    }
    return mapping.get(metric_key, "راجع المؤشر مع الإدارة المالية وحدد إجراء رقابي شهري.")

def owner_for_metric(metric_key):
    return {
        "gross_margin": "الإدارة المالية + التشغيل",
        "net_margin": "الإدارة المالية + الإدارة العامة",
        "opex_ratio": "الإدارة المالية + التشغيل",
        "direct_cost_ratio": "الإدارة المالية + المشتريات/التشغيل",
        "margin_of_safety": "الإدارة المالية + الإدارة العامة",
    }.get(metric_key, "الإدارة المالية")

def next_kpi(metric_key, rule):
    safe = rule["safe"]
    labels = {
        "opex_ratio": f"إبقاء المصاريف التشغيلية عند أو دون {pct(safe)} من الإيرادات.",
        "direct_cost_ratio": f"تقريب تكلفة الإيراد إلى {pct(safe)} أو أقل حسب معيار القطاع.",
        "gross_margin": f"الحفاظ على هامش مجمل ربح لا يقل عن {pct(safe)}.",
        "net_margin": f"الحفاظ على هامش صافي ربح لا يقل عن {pct(safe)}.",
        "margin_of_safety": f"الحفاظ على هامش أمان لا يقل عن {pct(safe)}.",
    }
    return labels.get(metric_key, "مراجعة المؤشر شهرياً.")

def build_sector_safety_scorecard(pnl_model, breakeven_model=None, sector="خدمي", country="", activity=""):
    metrics = compute_metrics(pnl_model, breakeven_model)
    rows = []
    for key, rule in rules(sector).items():
        value = sf(metrics.get(key, 0))
        status, gap, severity, benchmark_text = classify_gap(value, rule)
        rows.append({
            "المؤشر": rule["label"],
            "قيمة الشركة": value,
            "معيار السلامة": benchmark_text,
            "الفجوة عن المعيار": gap,
            "الحالة": status,
            "ماذا يعني؟": metric_interpretation(key, value, sector, status),
            "الإجراء العملي": recommended_action(key, status, value, sector),
            "المسؤول": owner_for_metric(key),
            "KPI الشهر القادم": next_kpi(key, rule),
            "_severity": severity,
            "_metric_key": key,
        })
    return pd.DataFrame(rows).sort_values("_severity", ascending=False).reset_index(drop=True)

def build_top_5_actions(scorecard_df):
    if scorecard_df is None or scorecard_df.empty:
        return pd.DataFrame()
    df = scorecard_df.copy()
    df["_priority_status"] = df["الحالة"].map({"خطر": 3, "مراقبة": 2, "آمن": 1}).fillna(0)
    df = df.sort_values(["_priority_status", "_severity"], ascending=False).head(5)
    actions = []
    for i, (_, r) in enumerate(df.iterrows(), start=1):
        actions.append({
            "الأولوية": i,
            "المشكلة": f"{r['المؤشر']} — {r['الحالة']}",
            "لماذا يهم؟": r["ماذا يعني؟"],
            "الإجراء المطلوب": r["الإجراء العملي"],
            "المسؤول": r["المسؤول"],
            "مؤشر المتابعة": r["KPI الشهر القادم"],
        })
    return pd.DataFrame(actions)

def build_scorecard_summary(scorecard_df, sector="خدمي"):
    if scorecard_df is None or scorecard_df.empty:
        return {"title": "لا توجد بيانات كافية", "summary": "لا يمكن بناء مقارنة قطاعية قبل توفر قائمة دخل ونقطة تعادل.", "risk": "جودة التحليل غير كافية.", "action": "ارفع الملفات المطلوبة ثم أعد بناء النموذج."}
    risk_rows = scorecard_df[scorecard_df["الحالة"].isin(["خطر", "مراقبة"])]
    if risk_rows.empty:
        return {"title": "الأداء ضمن الحدود المقبولة للقطاع", "summary": f"المؤشرات الأساسية تبدو ضمن معايير السلامة المختارة لقطاع {sector}. الأولوية الآن هي تثبيت الانضباط الداخلي ومراقبة الهوامش شهرياً.", "risk": "الخطر الرئيسي هو إضافة تكاليف ثابتة أو توسع غير مدروس يرفع نقطة التعادل.", "action": "اعتمد سقف مصاريف شهري، وراجع أثر أي التزام جديد على نقطة التعادل قبل الموافقة عليه."}
    top = risk_rows.iloc[0]
    return {"title": f"أكبر نقطة تحتاج انتباه: {top['المؤشر']}", "summary": top["ماذا يعني؟"], "risk": f"الفجوة عن معيار القطاع تظهر في بند: {top['المؤشر']}، والحالة الحالية: {top['الحالة']}.", "action": top["الإجراء العملي"]}
