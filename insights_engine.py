import pandas as pd

def _safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

def _pct(x):
    try:
        return f"{float(x)*100:.1f}٪"
    except Exception:
        return "—"

def build_ratio_insights(pnl_model: dict, ratio_model: dict | None = None) -> dict:
    revenue = _safe_float(pnl_model.get("revenue", 0))
    net_profit = _safe_float(pnl_model.get("net_profit", 0))
    cogs = _safe_float(pnl_model.get("cogs", 0))
    opex = _safe_float(pnl_model.get("opex", 0))
    gross_profit = _safe_float(pnl_model.get("gross_profit", 0))

    gross_margin = gross_profit / revenue if revenue else 0
    net_margin = net_profit / revenue if revenue else 0
    opex_ratio = opex / revenue if revenue else 0
    cogs_ratio = cogs / revenue if revenue else 0
    expense_ratio = (cogs + opex) / revenue if revenue else 0

    if net_margin >= 0.20 and gross_margin >= 0.50 and opex_ratio <= 0.50:
        status = "ربحية قوية مع حاجة للرقابة"
        risk = "المؤشرات الحالية جيدة، لكن ارتفاع المصاريف التشغيلية أو ضعف التحصيل قد يضغط على هامش الربح عند زيادة حجم النشاط."
        decision = "الإجراء المقترح: تثبيت نموذج الربحية الحالي، ومراقبة أكبر بنود المصاريف والتحصيل قبل اعتماد توسع جديد."
    elif net_margin > 0 and opex_ratio <= 0.75:
        status = "ربحية مقبولة لكنها حساسة"
        risk = "النشاط رابح، لكن جزءاً كبيراً من الإيرادات يذهب إلى المصاريف، ما يقلل مرونة الشركة أمام أي تراجع في المبيعات."
        decision = "الإجراء المقترح: مراجعة أكبر 5 بنود مصاريف، وتحديد البنود القابلة للتخفيض دون التأثير على التشغيل."
    else:
        status = "هامش ربح تحت الضغط"
        risk = "هامش الربح ضعيف أو سلبي، وقد يتحول النمو إلى عبء مالي إذا زادت المصاريف أسرع من الإيرادات."
        decision = "الإجراء المقترح: إيقاف قرارات التوسع مؤقتاً إلى حين مراجعة التسعير والتكاليف الثابتة والمتغيرة."

    bullets = [
        f"هامش مجمل الربح {_pct(gross_margin)}: قدرة جيدة على تغطية تكلفة المبيعات إذا بقيت المشتريات تحت السيطرة.",
        f"نسبة المصاريف التشغيلية {_pct(opex_ratio)}: مستوى يحتاج متابعة لأنه يستهلك جزءاً مهماً من الإيرادات.",
        f"هامش صافي الربح {_pct(net_margin)}: مؤشر جيد حالياً، لكن استمراره مشروط بضبط المصاريف والتحصيل.",
        f"نسبة تكلفة المبيعات {_pct(cogs_ratio)}: توضح أثر المشتريات والمخزون على الربحية.",
        f"إجمالي المصاريف إلى الإيرادات {_pct(expense_ratio)}: يوضح مقدار الإيراد المستهلك قبل تكوين صافي الربح.",
    ]

    return {
        "status": status,
        "risk": risk,
        "decision": decision,
        "bullets": bullets,
    }

def build_breakeven_insights(pnl_model: dict, breakeven_model: dict) -> dict:
    revenue = _safe_float(pnl_model.get("revenue", 0))
    be = _safe_float(
        breakeven_model.get("break_even_revenue", breakeven_model.get("breakeven_revenue", 0))
    )
    gap = revenue - be
    margin_of_safety = gap / revenue if revenue else 0
    contribution_margin = _safe_float(breakeven_model.get("contribution_margin", 0))
    fixed_costs = _safe_float(breakeven_model.get("fixed_costs", 0))

    if be <= 0 or contribution_margin <= 0:
        status = "غير قابل للاعتماد قبل مراجعة التكاليف"
        risk = "نقطة التعادل غير موثوقة لأن هامش المساهمة صفر/سلبي أو لأن توزيع التكاليف غير مكتمل."
        decision = "الإجراء المقترح: مراجعة Expense Mapping وتحديد التكاليف الثابتة والمتغيرة قبل استخدام النتيجة في القرار."
    elif gap >= 0 and margin_of_safety >= 0.25:
        status = "فوق نقطة التعادل بهامش آمن"
        risk = "النشاط يغطي نقطة التعادل حالياً، لكن أي زيادة في التكاليف الثابتة ستخفض هامش الأمان."
        decision = "الإجراء المقترح: الحفاظ على مستوى الإيراد الحالي، مع منع نمو التكاليف الثابتة أسرع من نمو المبيعات."
    elif gap >= 0:
        status = "فوق نقطة التعادل بهامش محدود"
        risk = "النشاط فوق التعادل، لكن هامش الأمان محدود وقد يتأثر بانخفاض الإيرادات أو ارتفاع المصاريف."
        decision = "الإجراء المقترح: رفع الإيراد المتكرر أو تخفيض التكاليف الثابتة قبل الالتزام بتوسع جديد."
    else:
        status = "تحت نقطة التعادل"
        risk = "الإيرادات الحالية لا تغطي نقطة التعادل، ما يعني أن التشغيل يحتاج تصحيحاً في الإيراد أو التكاليف."
        decision = "الإجراء المقترح: تحديد فجوة الإيراد المطلوبة وخطة تخفيض تكاليف قبل أي قرار توسع."

    return {
        "status": status,
        "gap": gap,
        "margin_of_safety": margin_of_safety,
        "risk": risk,
        "decision": decision,
        "bullets": [
            f"إيراد التعادل: {be:,.0f}",
            f"التكاليف الثابتة المستخدمة في الحساب: {fixed_costs:,.0f}",
            f"فجوة التعادل: {gap:,.0f}",
            f"هامش الأمان: {_pct(margin_of_safety)}",
        ]
    }

def build_forecast_insights(forecast_df: pd.DataFrame, pnl_model: dict) -> dict:
    if forecast_df is None or forecast_df.empty:
        return {
            "status": "بيانات توقع غير كافية",
            "risk": "لا يمكن قراءة اتجاه مستقبلي بدون بيانات مبيعات ومصاريف شهرية واضحة.",
            "decision": "الإجراء المقترح: رفع بيانات شهرية مكتملة وربط التوقع بعدد العملاء والتحصيل والطاقة التشغيلية.",
            "bullets": [],
            "summary_df": pd.DataFrame()
        }

    df = forecast_df.copy()
    for col in ["forecast_revenue", "forecast_expenses", "forecast_profit", "forecast_margin"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    scenario_summary = []
    for scenario, g in df.groupby("Scenario"):
        avg_rev = g["forecast_revenue"].mean() if "forecast_revenue" in g.columns else 0
        avg_profit = g["forecast_profit"].mean() if "forecast_profit" in g.columns else 0
        avg_margin = g["forecast_margin"].mean() if "forecast_margin" in g.columns else 0
        min_profit = g["forecast_profit"].min() if "forecast_profit" in g.columns else 0
        scenario_summary.append({
            "السيناريو": g["العربي"].iloc[0] if "العربي" in g.columns else scenario,
            "Scenario": scenario,
            "متوسط الإيراد المتوقع": avg_rev,
            "متوسط الربح المتوقع": avg_profit,
            "أقل ربح متوقع": min_profit,
            "هامش الربح المتوقع": avg_margin,
        })

    base = df[df["Scenario"].astype(str).str.lower().eq("base")]
    if base.empty:
        base = df
    avg_base_profit = base["forecast_profit"].mean() if "forecast_profit" in base.columns else 0
    avg_base_margin = base["forecast_margin"].mean() if "forecast_margin" in base.columns else 0
    min_all_profit = df["forecast_profit"].min() if "forecast_profit" in df.columns else 0

    if avg_base_profit > 0 and avg_base_margin >= 0.10 and min_all_profit >= 0:
        status = "توقعات إيجابية"
        risk = "السيناريو الأساسي يحافظ على ربحية جيدة، لكن يجب اختبار أثر انخفاض الإيرادات وارتفاع المصاريف."
        decision = "الإجراء المقترح: استخدام سيناريو النمو بحذر وربطه بالطاقة التشغيلية والتحصيل."
    elif avg_base_profit > 0:
        status = "توقعات إيجابية مع نقطة ضغط"
        risk = "الربحية المتوقعة إيجابية في السيناريو الأساسي، لكن بعض السيناريوهات قد تقترب من الخسارة."
        decision = "الإجراء المقترح: عدم اعتماد التوسع إلا بعد تحديد حد أدنى للإيراد الشهري وحد أقصى للمصاريف."
    else:
        status = "توقعات مقلقة"
        risk = "السيناريو الأساسي يشير إلى ربحية ضعيفة أو سلبية."
        decision = "الإجراء المقترح: مراجعة التسعير والتكاليف قبل اتخاذ أي قرار توسع."

    return {
        "status": status,
        "risk": risk,
        "decision": decision,
        "summary_df": pd.DataFrame(scenario_summary),
        "bullets": [
            f"متوسط ربح السيناريو الأساسي: {avg_base_profit:,.0f}",
            f"هامش ربح السيناريو الأساسي: {_pct(avg_base_margin)}",
            f"أقل ربح متوقع بين السيناريوهات: {min_all_profit:,.0f}",
            "التوقع الحالي مبني على متوسطات شهرية أولية، ويحتاج لاحقاً إلى ربطه بعدد العملاء والتحصيل والطاقة التشغيلية.",
        ]
    }


def build_expense_insights(pnl_model: dict, expense_model: dict | None) -> dict:
    revenue = _safe_float(pnl_model.get("revenue", 0))
    if not expense_model or expense_model.get("by_category", pd.DataFrame()).empty:
        return {
            "status": "بيانات مصاريف غير كافية",
            "risk": "لا يمكن تحليل كفاءة الإنفاق دون ملف مصاريف واضح أو تصنيف بنود المصاريف.",
            "decision": "الإجراء المقترح: رفع ملف مصاريف شهري مفصل وربط كل بند بتصنيف واضح.",
            "bullets": [],
            "expense_ratio_df": pd.DataFrame(),
        }

    cat = expense_model["by_category"].copy()
    cat["amount"] = pd.to_numeric(cat["amount"], errors="coerce").fillna(0)
    cat["النسبة من الإيراد"] = cat["amount"] / revenue if revenue else 0

    max_row = cat.sort_values("amount", ascending=False).iloc[0]
    max_cat = str(max_row.get("category", ""))
    max_amount = _safe_float(max_row.get("amount", 0))
    max_ratio = _safe_float(max_row.get("النسبة من الإيراد", 0))

    other_rows = cat[cat["category"].astype(str).str.contains("Other", case=False, na=False)]
    other_amount = _safe_float(other_rows["amount"].sum()) if not other_rows.empty else 0
    other_ratio = other_amount / revenue if revenue else 0

    if other_ratio > 0.15:
        status = "تصنيف المصاريف يحتاج تفصيل"
        risk = f"بند Other Opex مرتفع ويمثل {other_ratio*100:.1f}% من الإيرادات، ما يقلل دقة قرارات خفض التكاليف."
        decision = "الإجراء المقترح: تفصيل بنود Other Opex أولاً، ثم إعادة بناء تحليل المصاريف ونقطة التعادل."
    elif max_ratio > 0.20:
        status = "تركز مصاريف واضح"
        risk = f"أكبر بند مصاريف هو {max_cat} ويمثل {max_ratio*100:.1f}% من الإيرادات."
        decision = "الإجراء المقترح: مراجعة هذا البند وتحديد هل هو ثابت أم قابل للتخفيض."
    else:
        status = "هيكل مصاريف مقبول مبدئياً"
        risk = "لا يظهر تركز حاد في بند واحد، لكن يجب متابعة تطور المصاريف شهرياً مقابل الإيرادات."
        decision = "الإجراء المقترح: اعتماد متابعة شهرية لنسبة المصاريف من الإيراد."

    ratio_df = cat.rename(columns={"category": "التصنيف", "amount": "المبلغ"})
    ratio_df["التقييم"] = ratio_df["النسبة من الإيراد"].apply(lambda x: "مرتفع" if x > 0.20 else ("متوسط" if x > 0.10 else "مقبول"))

    return {
        "status": status,
        "risk": risk,
        "decision": decision,
        "bullets": [
            f"أكبر بند مصاريف: {max_cat} بقيمة {max_amount:,.0f}.",
            f"نسبة أكبر بند من الإيراد: {max_ratio*100:.1f}%.",
            f"نسبة Other Opex من الإيراد: {other_ratio*100:.1f}%.",
        ],
        "expense_ratio_df": ratio_df[["التصنيف", "المبلغ", "النسبة من الإيراد", "التقييم"]],
    }

def build_forecast_assumptions_table():
    return pd.DataFrame([
        ["متحفظ", "Conservative", "انخفاض تدريجي في الإيراد", "ارتفاع تدريجي في المصاريف", "اختبار قدرة النشاط على تحمل ضغط السوق"],
        ["أساسي", "Base", "استمرار متوسط الأداء الحالي", "ثبات نسبي في المصاريف", "قياس استمرار الوضع الحالي دون توسع"],
        ["نمو", "Growth", "زيادة الإيراد فوق المتوسط الحالي", "ارتفاع محدود في المصاريف", "اختبار أثر التوسع المنضبط"],
    ], columns=["السيناريو", "Scenario", "فرضية الإيراد", "فرضية المصاريف", "هدف السيناريو"])
