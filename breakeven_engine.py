import pandas as pd

def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default

def build_breakeven(pnl_model, expense_model):
    """
    Break-even must be based on official P&L values, not only analytical expense files.

    Logic:
    - Revenue and COGS come from the official P&L / Trial Balance.
    - Operating expenses come from the official P&L.
    - Expense Mapping is used only to split official operating expenses into fixed/variable/semi-variable proportions.
    - If mapping is unavailable, operating expenses are treated as fixed as a conservative default.
    """
    revenue = _safe_float(pnl_model.get("revenue", 0))
    official_opex = _safe_float(pnl_model.get("opex", 0))
    official_cogs = _safe_float(pnl_model.get("cogs", 0))

    if revenue <= 0:
        empty = pd.DataFrame()
        return {
            "summary": empty,
            "scenarios": empty,
            "note": "لا توجد إيرادات كافية لحساب نقطة التعادل.",
            "break_even_revenue": 0,
            "breakeven_revenue": 0,
            "breakeven_gap": 0,
            "margin_of_safety": 0,
            "fixed_costs": 0,
            "variable_costs": 0,
            "contribution_margin": 0,
        }

    exp_long = expense_model.get("expense_long", pd.DataFrame()) if expense_model else pd.DataFrame()

    if exp_long.empty or "amount" not in exp_long.columns:
        # Conservative fallback: COGS is variable, Opex is fixed.
        fixed_opex = official_opex
        variable_opex = 0.0
        semi_opex = 0.0
        note_extra = "لم يتم العثور على Expense Mapping صالح؛ تم اعتبار المصاريف التشغيلية تكاليف ثابتة كافتراض محافظ."
    else:
        work = exp_long.copy()
        if "cost_behavior" not in work.columns:
            work["cost_behavior"] = "Fixed"

        total_mapped = _safe_float(work["amount"].sum())
        if abs(total_mapped) < 0.000001:
            fixed_opex = official_opex
            variable_opex = 0.0
            semi_opex = 0.0
            note_extra = "قيمة Expense Mapping تساوي صفر؛ تم اعتبار المصاريف التشغيلية تكاليف ثابتة كافتراض محافظ."
        else:
            fixed_share = _safe_float(work.loc[work["cost_behavior"] == "Fixed", "amount"].sum()) / total_mapped
            variable_share = _safe_float(work.loc[work["cost_behavior"] == "Variable", "amount"].sum()) / total_mapped
            semi_share = _safe_float(work.loc[work["cost_behavior"] == "Semi-variable", "amount"].sum()) / total_mapped

            # Keep shares within reasonable bounds in case of negative adjustments.
            fixed_share = max(0.0, fixed_share)
            variable_share = max(0.0, variable_share)
            semi_share = max(0.0, semi_share)
            total_share = fixed_share + variable_share + semi_share

            if total_share == 0:
                fixed_share, variable_share, semi_share = 1.0, 0.0, 0.0
            else:
                fixed_share /= total_share
                variable_share /= total_share
                semi_share /= total_share

            fixed_opex = official_opex * fixed_share
            variable_opex = official_opex * variable_share
            semi_opex = official_opex * semi_share
            note_extra = "تم استخدام Expense Mapping لتوزيع المصاريف التشغيلية الرسمية بين ثابتة ومتغيرة وشبه متغيرة."

    fixed_costs = fixed_opex + (semi_opex * 0.50)
    variable_costs = official_cogs + variable_opex + (semi_opex * 0.50)

    variable_cost_ratio = variable_costs / revenue if revenue else 0
    contribution_margin = 1 - variable_cost_ratio

    if contribution_margin <= 0:
        breakeven_revenue = 0
        note = "هامش المساهمة صفر أو سلبي؛ لا يمكن حساب نقطة تعادل موثوقة قبل مراجعة التكاليف المتغيرة."
    else:
        breakeven_revenue = fixed_costs / contribution_margin
        note = "نقطة التعادل مبنية على قائمة الدخل الرسمية، مع استخدام Expense Mapping فقط لتوزيع المصاريف التشغيلية حسب نوع التكلفة."

    breakeven_gap = revenue - breakeven_revenue
    margin_of_safety = breakeven_gap / revenue if revenue else 0

    summary = pd.DataFrame([
        ["Revenue", "الإيرادات", revenue],
        ["COGS / Direct Variable Costs", "تكلفة المبيعات / تكاليف مباشرة متغيرة", official_cogs],
        ["Variable Opex", "مصاريف تشغيلية متغيرة", variable_opex],
        ["Semi-variable Opex", "مصاريف تشغيلية شبه متغيرة", semi_opex],
        ["Fixed Costs", "التكاليف الثابتة", fixed_costs],
        ["Variable Costs", "إجمالي التكاليف المتغيرة", variable_costs],
        ["Variable Cost Ratio", "نسبة التكلفة المتغيرة", variable_cost_ratio],
        ["Contribution Margin", "هامش المساهمة", contribution_margin],
        ["Break-even Revenue", "إيراد التعادل", breakeven_revenue],
        ["Break-even Gap", "فجوة التعادل", breakeven_gap],
        ["Margin of Safety", "هامش الأمان", margin_of_safety],
    ], columns=["English", "العربي", "Value"])

    scenarios = pd.DataFrame([
        ["Stress", "اختبار ضغط", fixed_costs * 1.10, max(0.05, contribution_margin - 0.10)],
        ["Conservative", "متحفظ", fixed_costs * 1.05, max(0.05, contribution_margin - 0.05)],
        ["Base", "أساسي", fixed_costs, contribution_margin],
        ["Efficiency", "تحسين كفاءة", fixed_costs * 0.97, min(0.95, contribution_margin + 0.03)],
        ["Growth", "نمو", fixed_costs * 1.03, min(0.95, contribution_margin + 0.05)],
    ], columns=["Scenario", "العربي", "Fixed Costs", "Contribution Margin"])
    scenarios["Break-even Revenue"] = scenarios.apply(
        lambda r: r["Fixed Costs"] / r["Contribution Margin"] if r["Contribution Margin"] > 0 else 0,
        axis=1
    )

    return {
        "summary": summary,
        "scenarios": scenarios,
        "break_even_revenue": breakeven_revenue,
        "breakeven_revenue": breakeven_revenue,
        "breakeven_gap": breakeven_gap,
        "margin_of_safety": margin_of_safety,
        "fixed_costs": fixed_costs,
        "variable_costs": variable_costs,
        "variable_cost_ratio": variable_cost_ratio,
        "contribution_margin": contribution_margin,
        "note": f"{note} {note_extra}"
    }
