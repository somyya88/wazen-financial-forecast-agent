import pandas as pd

def _sf(x):
    try:
        return float(x)
    except Exception:
        return 0.0

def _money(x):
    return f"{_sf(x):,.0f}"

def _pct(x):
    return f"{_sf(x)*100:.1f}%"

def classify_ratio(metric, value):
    v = _sf(value)
    if metric == "gross_margin":
        if v >= 0.55: return "قوي", "أعلى من 55%", "يحافظ على قدرة جيدة لتغطية تكلفة الإيراد."
        if v >= 0.40: return "جيد", "40% - 55%", "مقبول لكن يحتاج مراقبة تكلفة الإيراد."
        if v >= 0.25: return "يحتاج مراقبة", "25% - 40%", "قد يشير إلى ضغط في التسعير أو تكلفة المشتريات."
        return "خطر", "أقل من 25%", "يعني ضعف قدرة الإيرادات على تغطية التكلفة المباشرة."

    if metric == "net_margin":
        if v >= 0.20: return "قوي", "أعلى من 20%", "ربحية نهائية جيدة قابلة للبناء عليها."
        if v >= 0.10: return "جيد", "10% - 20%", "ربحية مقبولة مع حاجة لضبط المصاريف."
        if v >= 0.03: return "يحتاج مراقبة", "3% - 10%", "هامش محدود وقد يتأثر بأي ارتفاع في المصاريف."
        return "خطر", "أقل من 3%", "أي تراجع بسيط في الإيرادات قد يحول النتيجة إلى خسارة."

    if metric == "opex_ratio":
        if v <= 0.30: return "قوي", "أقل من 30%", "كفاءة تشغيلية جيدة."
        if v <= 0.45: return "جيد", "30% - 45%", "مقبول لكن يجب منع نمو المصاريف أسرع من الإيرادات."
        if v <= 0.60: return "يحتاج مراقبة", "45% - 60%", "المصاريف تستهلك جزءاً كبيراً من الإيرادات."
        return "خطر", "أعلى من 60%", "المصاريف التشغيلية تضغط على الربحية."

    if metric == "direct_cost_ratio":
        if v <= 0.35: return "جيد", "أقل من 35%", "تكلفة الإيراد ضمن مستوى مقبول."
        if v <= 0.50: return "يحتاج مراقبة", "35% - 50%", "تكلفة الإيراد تحتاج مراجعة."
        return "خطر", "أعلى من 50%", "قد تكون تكلفة المبيعات أو المشتريات مرتفعة."

    if metric == "expense_ratio":
        if v <= 0.70: return "جيد", "أقل من 70%", "جزء جيد من الإيراد يبقى لتكوين الربح."
        if v <= 0.85: return "يحتاج مراقبة", "70% - 85%", "الإيرادات تستهلك بشكل كبير قبل الوصول لصافي الربح."
        return "خطر", "أعلى من 85%", "هامش الربح النهائي معرض للضغط."

    if metric == "break_even_safety":
        if v >= 0.40: return "قوي", "أعلى من 40%", "يوجد هامش أمان جيد قبل الوصول للتعادل."
        if v >= 0.20: return "جيد", "20% - 40%", "هامش أمان مقبول."
        if v >= 0.10: return "يحتاج مراقبة", "10% - 20%", "هامش أمان محدود."
        return "خطر", "أقل من 10%", "النشاط قريب من نقطة التعادل."

    return "غير محدد", "—", "لا توجد قاعدة تقييم كافية."

def build_financial_performance_scorecard(pnl_model: dict, breakeven_model: dict | None = None, data_quality: dict | None = None):
    revenue = _sf(pnl_model.get("revenue", 0))
    gross_profit = _sf(pnl_model.get("gross_profit", 0))
    net_profit = _sf(pnl_model.get("net_profit", 0))
    cogs = _sf(pnl_model.get("cogs", 0))
    opex = _sf(pnl_model.get("opex", 0))

    gross_margin = gross_profit / revenue if revenue else 0
    net_margin = net_profit / revenue if revenue else 0
    opex_ratio = opex / revenue if revenue else 0
    direct_cost_ratio = cogs / revenue if revenue else 0
    expense_ratio = (cogs + opex) / revenue if revenue else 0
    margin_of_safety = _sf((breakeven_model or {}).get("margin_of_safety", 0))

    metrics = [
        ("هامش مجمل الربح", "Gross Margin", "gross_margin", gross_margin, "يقيس قدرة الإيرادات على تغطية تكلفة الإيراد المباشرة."),
        ("هامش صافي الربح", "Net Margin", "net_margin", net_margin, "يقيس النتيجة النهائية المتبقية بعد كل التكاليف والمصاريف."),
        ("نسبة المصاريف التشغيلية", "Opex Ratio", "opex_ratio", opex_ratio, "تقيس عبء المصاريف الإدارية والتشغيلية على الإيرادات."),
        ("نسبة تكلفة الإيراد", "Direct Cost Ratio", "direct_cost_ratio", direct_cost_ratio, "تقيس أثر المشتريات وتكلفة الخدمة أو البضاعة على الربحية."),
        ("إجمالي التكاليف والمصاريف", "Expense Ratio", "expense_ratio", expense_ratio, "يوضح مقدار الإيراد المستهلك قبل تكوين صافي الربح."),
        ("هامش الأمان", "Margin of Safety", "break_even_safety", margin_of_safety, "يقيس المسافة بين الإيراد الحالي ونقطة التعادل."),
    ]

    rows = []
    score_points = []
    for ar, en, key, value, why in metrics:
        rating, threshold, decision = classify_ratio(key, value)
        score = {"قوي": 100, "جيد": 80, "يحتاج مراقبة": 55, "خطر": 25}.get(rating, 50)
        score_points.append(score)
        rows.append({
            "المؤشر": ar,
            "English": en,
            "القيمة": value,
            "التقييم": rating,
            "حدود القراءة": threshold,
            "لماذا يهم؟": why,
            "أثر القرار": decision,
        })

    # Data quality can reduce the score.
    base_score = sum(score_points) / len(score_points) if score_points else 0
    dq_score = None
    if data_quality:
        dq_score = _sf(data_quality.get("score", 100))
        final_score = (base_score * 0.80) + (dq_score * 0.20)
    else:
        final_score = base_score

    if net_margin >= 0.20 and opex_ratio <= 0.45 and margin_of_safety >= 0.30:
        status = "أداء قوي قابل للبناء عليه"
        risk = "الخطر الرئيسي ليس في الربحية الحالية، بل في المحافظة على الهامش عند زيادة حجم النشاط."
        action = "تثبيت نموذج الربحية، ومراقبة تكلفة الإيراد والمصاريف التشغيلية قبل أي توسع."
    elif net_margin >= 0.10 and margin_of_safety >= 0.20:
        status = "أداء جيد مع نقاط مراقبة"
        risk = "الربحية جيدة، لكن المصاريف أو تكلفة الإيراد قد تضغط على الهامش إذا نمت أسرع من المبيعات."
        action = "وضع حد شهري للمصاريف، ومراجعة البنود الأكبر قبل اعتماد التوسع."
    else:
        status = "أداء يحتاج تدخل"
        risk = "الهامش أو هامش الأمان لا يوفران مساحة كافية لتحمل انخفاض الإيرادات أو ارتفاع المصاريف."
        action = "مراجعة التسعير والتكاليف الثابتة والمتغيرة قبل قرارات التوسع."

    return {
        "score": round(final_score, 0),
        "status": status,
        "risk": risk,
        "action": action,
        "scorecard": pd.DataFrame(rows),
        "drivers": [
            f"هامش صافي الربح: {_pct(net_margin)}",
            f"نسبة المصاريف التشغيلية: {_pct(opex_ratio)}",
            f"هامش الأمان: {_pct(margin_of_safety)}",
            f"نسبة تكلفة الإيراد: {_pct(direct_cost_ratio)}",
        ],
    }

def build_break_even_confidence(expense_mapping_df=None, data_quality=None):
    score = 80
    reasons = []

    if data_quality:
        dq = _sf(data_quality.get("score", 100))
        if dq < 75:
            score -= 15
            reasons.append("جودة البيانات أقل من المستوى المثالي.")
        else:
            reasons.append("مصادر البيانات الأساسية متوفرة.")

    if expense_mapping_df is not None and not getattr(expense_mapping_df, "empty", True):
        df = expense_mapping_df.copy()
        if "classification_confidence" in df.columns:
            low = pd.to_numeric(df["classification_confidence"], errors="coerce").fillna(100)
            low_share = (low < 70).mean()
            if low_share > 0.25:
                score -= 15
                reasons.append("نسبة ملحوظة من البنود ذات ثقة تصنيف منخفضة.")
        if "user_category" in df.columns:
            other_share = df["user_category"].astype(str).str.contains("Other", case=False, na=False).mean()
            if other_share > 0.25:
                score -= 15
                reasons.append("نسبة Needs Review مرتفعة وتؤثر على دقة توزيع التكاليف.")
    else:
        score -= 20
        reasons.append("لا يوجد جدول تصنيف مصاريف كافٍ لتقييم الثقة.")

    score = max(0, min(100, int(score)))
    label = "عالية" if score >= 80 else ("متوسطة" if score >= 60 else "منخفضة")
    return {"score": score, "label": label, "reasons": reasons}

def build_break_even_sensitivity(breakeven_model: dict):
    revenue = _sf((breakeven_model or {}).get("revenue", 0))
    base_be = _sf((breakeven_model or {}).get("break_even_revenue", (breakeven_model or {}).get("breakeven_revenue", 0)))
    fixed = _sf((breakeven_model or {}).get("fixed_costs", 0))
    cm = _sf((breakeven_model or {}).get("contribution_margin", 0))

    scenarios = [
        ("الوضع الحالي", "Base", fixed, cm),
        ("ارتفاع التكاليف الثابتة 10%", "Fixed +10%", fixed * 1.10, cm),
        ("انخفاض هامش المساهمة 5 نقاط", "CM -5 pts", fixed, max(0.05, cm - 0.05)),
        ("ارتفاع التكاليف + انخفاض الهامش", "Combined Stress", fixed * 1.10, max(0.05, cm - 0.05)),
        ("تحسين كفاءة 5%", "Efficiency +5%", fixed * 0.95, min(0.95, cm + 0.05)),
    ]

    rows = []
    for ar, en, fx, c in scenarios:
        be = fx / c if c > 0 else 0
        gap = revenue - be if revenue else 0
        rows.append({
            "السيناريو": ar,
            "English": en,
            "التكاليف الثابتة": fx,
            "هامش المساهمة": c,
            "إيراد التعادل": be,
            "فجوة التعادل": gap,
            "القراءة": "آمن" if gap > revenue * 0.25 else ("مراقبة" if gap > 0 else "خطر"),
        })
    return pd.DataFrame(rows)

def build_forecast_decision(forecast_df: pd.DataFrame, breakeven_model: dict):
    if forecast_df is None or forecast_df.empty:
        return {
            "warning": "لا توجد بيانات توقعات كافية.",
            "safe_revenue": 0,
            "worst_month": "—",
            "worst_profit": 0,
            "decision": "رفع بيانات شهرية كافية قبل اعتماد التوقع."
        }

    df = forecast_df.copy()
    for c in ["forecast_revenue", "forecast_expenses", "forecast_profit"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    worst = df.sort_values("forecast_profit").iloc[0]
    worst_month = str(worst.get("month", "—"))
    worst_profit = _sf(worst.get("forecast_profit", 0))
    worst_rev = _sf(worst.get("forecast_revenue", 0))
    be_total = _sf((breakeven_model or {}).get("break_even_revenue", (breakeven_model or {}).get("breakeven_revenue", 0)))
    # Current model is for the uploaded period; use average monthly safe revenue if forecast is monthly.
    months_count = max(1, len(df["month"].dropna().unique()) if "month" in df.columns else 1)
    safe_revenue_monthly = be_total / max(1, min(months_count, 6))

    if worst_profit < 0:
        warning = f"تحذير: السيناريو المتحفظ يتحول إلى خسارة في {worst_month} بقيمة {abs(worst_profit):,.0f}."
        decision = f"عدم اعتماد التوسع قبل ضمان إيراد شهري أعلى من {safe_revenue_monthly:,.0f} وضبط سقف المصاريف."
    else:
        warning = "لا تظهر خسارة مباشرة في السيناريوهات، لكن يجب مراقبة أقل شهر متوقع."
        decision = f"يمكن دراسة النمو بشرط الحفاظ على إيراد شهري لا يقل عن {safe_revenue_monthly:,.0f}."

    return {
        "warning": warning,
        "safe_revenue": safe_revenue_monthly,
        "worst_month": worst_month,
        "worst_profit": worst_profit,
        "worst_revenue": worst_rev,
        "decision": decision,
    }
