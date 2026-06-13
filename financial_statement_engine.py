import pandas as pd

COGS_CATEGORIES = ["COGS", "Fuel", "Maintenance", "Spare Parts"]
DEPRECIATION_CATEGORIES = ["Depreciation"]
FINANCE_CATEGORIES = ["Finance Costs", "Interest", "Bank Charges"]

def build_pnl(revenue_model, expense_model, tb_model=None):
    # Primary logic: Trial Balance is enough for Level A financial analysis.
    # If TB cannot read revenue but a sales file is available, build a hybrid P&L instead of reporting revenue = 0.
    tb_income = tb_model.get("income_statement", {}) if tb_model else {}
    tb_revenue = float(tb_income.get("total_revenue", 0) or 0)
    external_revenue = float(revenue_model.get("total_revenue", 0)) if revenue_model else 0

    if tb_income.get("available") and (tb_revenue > 0 or external_revenue <= 0):
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
            "note": "قائمة الدخل مبنية من ميزان المراجعة كمصدر أساسي. ملفات المبيعات والمصاريف الشهرية تستخدم للتحليل والتوزيع، وليست شرطًا لبناء القوائم."
        }

    # Fallback / hybrid: use sales and expense files, and use TB costs/expenses if expense file is missing.
    revenue = external_revenue
    exp_long = expense_model.get("expense_long", pd.DataFrame()) if expense_model else pd.DataFrame()

    if exp_long.empty:
        cogs = float(tb_income.get("cogs", 0) or 0)
        opex = float(tb_income.get("operating_expenses", 0) or 0)
        depreciation = finance_costs = 0
        total_expenses = cogs + opex
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
        "source": "hybrid_or_analytical_files",
        "note": "تم بناء قائمة الدخل من أفضل الملفات المتاحة: المبيعات عند توفرها، والمصاريف/ميزان المراجعة للتكاليف. هذا وضع مرن لا يوقف التحليل عند نقص ملف تفصيلي."
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


def build_management_income_statement(pnl_model: dict, expense_model: dict | None = None):
    """
    Management P&L:
    Revenue
    - Cost of Revenue / COGS (official COGS + mapped direct costs when available)
    = Gross Operating Margin
    - Administrative Expenses
    - Selling & Marketing Expenses
    - Finance Costs / Needs Review
    = Net Profit
    """
    import pandas as pd

    def sf(x):
        try:
            return float(x)
        except Exception:
            return 0.0

    revenue = sf(pnl_model.get("revenue", 0))
    official_cogs = sf(pnl_model.get("cogs", 0))
    official_opex = sf(pnl_model.get("opex", 0))

    direct = admin = selling = finance = other = 0.0

    if expense_model and not expense_model.get("expense_long", pd.DataFrame()).empty:
        df = expense_model["expense_long"].copy()
        df["amount"] = pd.to_numeric(df.get("amount"), errors="coerce").fillna(0)
        cat_col = "user_category" if "user_category" in df.columns else "category"

        for _, r in df.iterrows():
            cat = str(r.get(cat_col, ""))
            amount = sf(r.get("amount", 0))
            if cat in ["Cost of Revenue", "Purchases", "COGS", "Spare Parts", "Fuel"]:
                direct += amount
            elif cat in ["Selling & Marketing", "Marketing", "Selling Opex"]:
                selling += amount
            elif cat in ["Finance Costs"]:
                finance += amount
            elif cat in ["Needs Review"]:
                other += amount
            else:
                admin += amount

        # Avoid double counting official COGS if mapped direct costs are from same expense file.
        cost_of_revenue = max(official_cogs, direct)
        total_mapped_opex = direct + admin + selling + finance + other
        # Scale non-direct opex to official opex if mapped expense file differs materially.
        non_direct = admin + selling + finance + other
        if non_direct > 0 and official_opex > 0:
            scale = official_opex / non_direct
            admin *= scale
            selling *= scale
            finance *= scale
            other *= scale
    else:
        cost_of_revenue = official_cogs
        admin = official_opex

    gross_operating_profit = revenue - cost_of_revenue
    operating_profit = gross_operating_profit - admin - selling - other
    net_profit = operating_profit - finance

    return pd.DataFrame([
        ["الإيرادات التشغيلية", "Operating Revenue", revenue],
        ["تكلفة الإيراد / تكلفة البضاعة المباعة", "Cost of Revenue / COGS", cost_of_revenue],
        ["مجمل الربح التشغيلي", "Gross Operating Profit", gross_operating_profit],
        ["المصاريف الإدارية والعمومية", "General & Administrative Expenses", admin],
        ["مصاريف البيع والتسويق", "Selling & Marketing Expenses", selling],
        ["مصاريف تشغيلية أخرى", "Other Operating Expenses", other],
        ["الربح التشغيلي", "Operating Profit", operating_profit],
        ["مصاريف تمويلية", "Finance Costs", finance],
        ["صافي الربح", "Net Profit", net_profit],
    ], columns=["العربي", "English", "Amount"])
