import pandas as pd

def _safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

def _pct(x):
    try:
        return f"{float(x)*100:.1f}%"
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

    if net_margin >= 0.20 and opex_ratio <= 0.50:
        status = "جيد"
        risk = "لا يظهر خطر مباشر، لكن يجب مراقبة قدرة الربح على الاستمرار عند زيادة النشاط."
        decision = "ثبتي نموذج الربحية الحالي وابني متابعة شهرية للهامش والتحصيل."
    elif net_margin > 0 and opex_ratio <= 0.75:
        status = "متوسط"
        risk = "الربح موجود، لكن المصاريف تستهلك جزءاً كبيراً من الإيرادات."
        decision = "راجعي أكبر 5 مصاريف وحددي ما هو ثابت وما هو قابل للتخفيض."
    else:
        status = "خطر"
        risk = "هامش الربح ضعيف أو سلبي، وقد يصبح النمو غير صحي إذا زادت المصاريف أسرع من الإيرادات."
        decision = "أوقفي أي توسع قبل مراجعة التسعير والتكاليف الثابتة."

    bullets = [
        f"هامش مجمل الربح: {_pct(gross_margin)} — يوضح قدرة الإيراد على تغطية تكلفة المبيعات.",
        f"نسبة المصاريف التشغيلية إلى الإيرادات: {_pct(opex_ratio)} — كلما ارتفعت قلّت مرونة الربح.",
        f"هامش صافي الربح: {_pct(net_margin)} — المؤشر الأوضح لقابلية النشاط للاستمرار.",
        f"نسبة تكلفة المبيعات: {_pct(cogs_ratio)} — مهمة لفهم أثر المشتريات والمخزون على الربحية.",
    ]

    return {
        "status": status,
        "risk": risk,
        "decision": decision,
        "bullets": bullets,
    }

def build_breakeven_insights(pnl_model: dict, breakeven_model: dict) -> dict:
    revenue = _safe_float(pnl_model.get("revenue", 0))
    be = _safe_float(breakeven_model.get("break_even_revenue", 0))
    gap = revenue - be
    margin_of_safety = gap / revenue if revenue else 0

    if gap >= 0:
        status = "فوق نقطة التعادل"
        risk = "النشاط يغطي نقطة التعادل حالياً، لكن هامش الأمان يحتاج متابعة شهرية."
        decision = "حافظي على مستوى الإيراد الحالي، وراقبي أي زيادة في التكاليف الثابتة."
    else:
        status = "تحت نقطة التعادل"
        risk = "الإيرادات الحالية لا تغطي نقطة التعادل، وهذا يعني أن أي انخفاض بسيط قد يضغط على السيولة."
        decision = "حددي فجوة الإيرادات المطلوبة أو اخفضي التكاليف الثابتة قبل التوسع."

    return {
        "status": status,
        "gap": gap,
        "margin_of_safety": margin_of_safety,
        "risk": risk,
        "decision": decision,
        "bullets": [
            f"إيراد التعادل: {be:,.0f}",
            f"فجوة التعادل: {gap:,.0f}",
            f"هامش الأمان: {margin_of_safety*100:.1f}%",
        ]
    }

def build_forecast_insights(forecast_df: pd.DataFrame, pnl_model: dict) -> dict:
    if forecast_df is None or forecast_df.empty:
        return {
            "status": "لا توجد توقعات كافية",
            "risk": "لا يمكن قراءة اتجاه مستقبلي بدون بيانات توقع.",
            "decision": "ارفعي مبيعات ومصاريف شهرية واضحة لبناء سيناريوهات أفضل.",
            "bullets": []
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
        scenario_summary.append({
            "السيناريو": g["العربي"].iloc[0] if "العربي" in g.columns else scenario,
            "Scenario": scenario,
            "متوسط الإيراد المتوقع": avg_rev,
            "متوسط الربح المتوقع": avg_profit,
            "هامش الربح المتوقع": avg_margin,
        })

    base = df[df["Scenario"].astype(str).str.lower().eq("base")]
    if base.empty:
        base = df
    avg_base_profit = base["forecast_profit"].mean() if "forecast_profit" in base.columns else 0
    avg_base_margin = base["forecast_margin"].mean() if "forecast_margin" in base.columns else 0

    if avg_base_profit > 0 and avg_base_margin >= 0.10:
        status = "توقعات مقبولة"
        risk = "التوقع الأساسي يحافظ على ربحية إيجابية، لكن يجب اختبار أثر انخفاض الإيرادات."
        decision = "استخدمي سيناريو النمو بحذر، واربطيه بالطاقة التشغيلية والتحصيل."
    elif avg_base_profit > 0:
        status = "توقعات حساسة"
        risk = "الربحية المتوقعة إيجابية لكنها ضعيفة، وقد تتأثر بسرعة بأي ارتفاع في المصاريف."
        decision = "لا تعتمدي التوسع قبل ضبط المصاريف المتكررة."
    else:
        status = "توقعات مقلقة"
        risk = "السيناريو الأساسي يشير إلى ربحية سلبية أو هامش ضعيف."
        decision = "راجعي التسعير والتكاليف قبل اتخاذ أي قرار توسع."

    return {
        "status": status,
        "risk": risk,
        "decision": decision,
        "summary_df": pd.DataFrame(scenario_summary),
        "bullets": [
            f"متوسط ربح السيناريو الأساسي: {avg_base_profit:,.0f}",
            f"هامش ربح السيناريو الأساسي: {avg_base_margin*100:.1f}%",
            "التوقع الحالي مبني على متوسطات شهرية أولية، وليس نموذجاً تشغيلياً كاملاً."
        ]
    }
