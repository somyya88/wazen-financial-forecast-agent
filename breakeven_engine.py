import pandas as pd

VARIABLE_CATEGORIES = ["COGS", "Fuel", "Maintenance", "Spare Parts", "Marketing"]

def build_breakeven(pnl_model, expense_model):
    revenue = pnl_model.get("revenue", 0)
    exp_long = expense_model.get("expense_long", pd.DataFrame()) if expense_model else pd.DataFrame()

    if exp_long.empty or revenue == 0:
        return {
            "summary": pd.DataFrame(),
            "scenarios": pd.DataFrame(),
            "note": "لا توجد بيانات كافية لحساب نقطة التعادل."
        }

    variable_costs = float(exp_long.loc[exp_long["category"].isin(VARIABLE_CATEGORIES), "amount"].sum())
    total_expenses = float(exp_long["amount"].sum())
    fixed_costs = total_expenses - variable_costs
    variable_cost_ratio = variable_costs / revenue if revenue else 0
    contribution_margin = 1 - variable_cost_ratio
    breakeven_revenue = fixed_costs / contribution_margin if contribution_margin > 0 else 0
    breakeven_gap = revenue - breakeven_revenue
    margin_of_safety = breakeven_gap / revenue if revenue else 0

    summary = pd.DataFrame([
        ["Revenue", "الإيرادات", revenue],
        ["Variable Costs", "التكاليف المتغيرة", variable_costs],
        ["Fixed Costs", "التكاليف الثابتة", fixed_costs],
        ["Variable Cost Ratio", "نسبة التكلفة المتغيرة", variable_cost_ratio],
        ["Contribution Margin", "هامش المساهمة", contribution_margin],
        ["Break-even Revenue", "إيراد التعادل", breakeven_revenue],
        ["Break-even Gap", "فجوة التعادل", breakeven_gap],
        ["Margin of Safety", "هامش الأمان", margin_of_safety],
    ], columns=["English", "العربي", "Value"])

    scenarios = pd.DataFrame([
        ["Conservative", "متحفظ", fixed_costs * 1.05, max(0.05, contribution_margin - 0.05)],
        ["Base", "أساسي", fixed_costs, contribution_margin],
        ["Growth", "نمو", fixed_costs * 1.03, min(0.95, contribution_margin + 0.05)],
    ], columns=["Scenario", "العربي", "Fixed Costs", "Contribution Margin"])
    scenarios["Break-even Revenue"] = scenarios["Fixed Costs"] / scenarios["Contribution Margin"]

    return {
        "summary": summary,
        "scenarios": scenarios,
        "breakeven_revenue": breakeven_revenue,
        "breakeven_gap": breakeven_gap,
        "margin_of_safety": margin_of_safety,
        "note": "نقطة التعادل مبنية على تصنيف أولي للتكاليف المتغيرة والثابتة. الدقة تتحسن بعد Mapping الحسابات."
    }
