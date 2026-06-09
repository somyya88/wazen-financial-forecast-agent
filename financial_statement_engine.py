import pandas as pd

COGS_CATEGORIES = ["COGS", "Fuel", "Maintenance", "Spare Parts"]
DEPRECIATION_CATEGORIES = ["Depreciation"]
FINANCE_CATEGORIES = ["Finance Costs", "Interest", "Bank Charges"]

def build_pnl(revenue_model, expense_model, tb_model=None):
    # Primary logic: if Trial Balance income statement is available, use it as the official P&L.
    tb_income = tb_model.get("income_statement", {}) if tb_model else {}
    if tb_income.get("available"):
        pnl = tb_income.get("pnl", pd.DataFrame())

        return {
            "pnl": pnl,
            "revenue": tb_income.get("total_revenue", 0),
            "net_sales": tb_income.get("net_sales", 0),
            "other_revenue": tb_income.get("other_revenue", 0),
            "opening_inventory": tb_income.get("opening_inventory", 0),
            "net_purchases": tb_income.get("net_purchases", 0),
            "ending_inventory": tb_income.get("ending_inventory", 0),
            "cogs": tb_income.get("cogs", 0),
            "gross_profit": tb_income.get("gross_profit", 0),
            "opex": tb_income.get("operating_expenses", 0),
            "ebitda": tb_income.get("ebitda", 0),
            "depreciation": 0,
            "ebit": tb_income.get("ebitda", 0),
            "finance_costs": 0,
            "net_profit": tb_income.get("net_profit", 0),
            "total_expenses": tb_income.get("cogs", 0) + tb_income.get("operating_expenses", 0),
            "source": "trial_balance",
            "note": "قائمة الدخل مبنية من ميزان المراجعة كمصدر أساسي. ملفات المبيعات والمصاريف الشهرية تستخدم للتحليل فقط."
        }

    # Fallback: use analytical files only if TB is unavailable.
    revenue = float(revenue_model.get("total_revenue", 0)) if revenue_model else 0
    exp_long = expense_model.get("expense_long", pd.DataFrame()) if expense_model else pd.DataFrame()

    if exp_long.empty:
        cogs = opex = depreciation = finance_costs = total_expenses = 0
    else:
        total_expenses = float(exp_long["amount"].sum())
        cogs = float(exp_long.loc[exp_long["category"].isin(COGS_CATEGORIES), "amount"].sum())
        depreciation = float(exp_long.loc[exp_long["category"].isin(DEPRECIATION_CATEGORIES), "amount"].sum())
        finance_costs = float(exp_long.loc[exp_long["category"].isin(FINANCE_CATEGORIES), "amount"].sum())
        excluded = COGS_CATEGORIES + DEPRECIATION_CATEGORIES + FINANCE_CATEGORIES
        opex = float(exp_long.loc[~exp_long["category"].isin(excluded), "amount"].sum())

    gross_profit = revenue - cogs
    ebitda = gross_profit - opex
    ebit = ebitda - depreciation
    net_profit = ebit - finance_costs

    pnl = pd.DataFrame([
        ["Revenue", "الإيرادات", revenue],
        ["COGS / Direct Costs", "تكلفة الإيراد / التكاليف المباشرة", cogs],
        ["Gross Profit", "مجمل الربح", gross_profit],
        ["Operating Expenses", "المصاريف التشغيلية", opex],
        ["EBITDA", "الربح قبل الفوائد والضرائب والإهلاك", ebitda],
        ["Depreciation", "الإهلاك", depreciation],
        ["EBIT", "الربح التشغيلي", ebit],
        ["Finance Costs", "تكاليف التمويل", finance_costs],
        ["Net Profit", "صافي الربح", net_profit],
    ], columns=["English", "العربي", "Amount"])

    return {
        "pnl": pnl,
        "revenue": revenue,
        "cogs": cogs,
        "gross_profit": gross_profit,
        "opex": opex,
        "ebitda": ebitda,
        "depreciation": depreciation,
        "ebit": ebit,
        "finance_costs": finance_costs,
        "net_profit": net_profit,
        "total_expenses": total_expenses,
        "source": "analytical_files",
        "note": "تم بناء قائمة الدخل من الملفات التحليلية لعدم توفر ميزان مراجعة صالح."
    }

def monthly_pnl(revenue_model, expense_model):
    rev = revenue_model.get("monthly_revenue", pd.DataFrame()).copy() if revenue_model else pd.DataFrame()
    exp = expense_model.get("monthly_expenses", pd.DataFrame()).copy() if expense_model else pd.DataFrame()
    if rev.empty:
        return pd.DataFrame(columns=["month", "revenue", "expenses", "preliminary_profit", "margin"])
    if exp.empty:
        rev["expenses"] = 0
    else:
        rev = rev.merge(exp, on="month", how="left")
        rev["expenses"] = rev["expenses"].fillna(0)
    rev["preliminary_profit"] = rev["revenue"] - rev["expenses"]
    rev["margin"] = rev.apply(lambda r: r["preliminary_profit"] / r["revenue"] if r["revenue"] else 0, axis=1)
    return rev
