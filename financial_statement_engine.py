import pandas as pd

COGS_CATEGORIES = ["COGS", "Fuel", "Maintenance", "Spare Parts"]
DEPRECIATION_CATEGORIES = ["Depreciation"]
FINANCE_CATEGORIES = ["Finance Costs", "Interest", "Bank Charges"]

def _expense_contains_purchases(exp_long: pd.DataFrame) -> bool:
    if exp_long is None or exp_long.empty or "account_name" not in exp_long.columns:
        return False
    names = " ".join(exp_long["account_name"].astype(str).tolist())
    return ("مشتريات" in names) or ("صافي المشتريات" in names) or ("purchases" in names.lower())

def build_pnl(revenue_model, expense_model, tb_model=None):
    revenue = float(revenue_model.get("total_revenue", 0)) if revenue_model else 0
    exp_long = expense_model.get("expense_long", pd.DataFrame()) if expense_model else pd.DataFrame()

    if exp_long.empty:
        cogs = opex = depreciation = finance_costs = expense_source_total = 0
    else:
        expense_source_total = float(exp_long["amount"].sum())
        cogs = float(exp_long.loc[exp_long["category"].isin(COGS_CATEGORIES), "amount"].sum())
        depreciation = float(exp_long.loc[exp_long["category"].isin(DEPRECIATION_CATEGORIES), "amount"].sum())
        finance_costs = float(exp_long.loc[exp_long["category"].isin(FINANCE_CATEGORIES), "amount"].sum())
        excluded = COGS_CATEGORIES + DEPRECIATION_CATEGORIES + FINANCE_CATEGORIES
        opex = float(exp_long.loc[~exp_long["category"].isin(excluded), "amount"].sum())

    # Add purchases from Trial Balance when available and not already present in expense report.
    tb_purchases_adjustment = 0
    if tb_model:
        metrics = tb_model.get("metrics", {}) if isinstance(tb_model, dict) else {}
        net_purchases = metrics.get("net_purchases")
        if net_purchases and not _expense_contains_purchases(exp_long):
            tb_purchases_adjustment = float(net_purchases)
            cogs += tb_purchases_adjustment

    gross_profit = revenue - cogs
    ebitda = gross_profit - opex
    ebit = ebitda - depreciation
    net_profit = ebit - finance_costs
    total_expenses = expense_source_total + tb_purchases_adjustment

    rows = [
        ["Revenue", "الإيرادات", revenue],
        ["COGS / Direct Costs", "تكلفة الإيراد / التكاليف المباشرة", cogs],
    ]

    if tb_purchases_adjustment:
        rows.append(["TB Purchases Adjustment", "مشتريات من ميزان المراجعة", tb_purchases_adjustment])

    rows += [
        ["Gross Profit", "مجمل الربح", gross_profit],
        ["Operating Expenses", "المصاريف التشغيلية", opex],
        ["EBITDA", "الربح قبل الفوائد والضرائب والإهلاك", ebitda],
        ["Depreciation", "الإهلاك", depreciation],
        ["EBIT", "الربح التشغيلي", ebit],
        ["Finance Costs", "تكاليف التمويل", finance_costs],
        ["Net Profit", "صافي الربح", net_profit],
    ]

    pnl = pd.DataFrame(rows, columns=["English", "العربي", "Amount"])

    note = "تم بناء قائمة الدخل بناءً على Expense Mapping."
    if tb_purchases_adjustment:
        note += " كما تم إدراج صافي المشتريات من ميزان المراجعة ضمن تكلفة الإيراد لأنها غير ظاهرة في تقرير المصروفات."

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
        "expense_source_total": expense_source_total,
        "tb_purchases_adjustment": tb_purchases_adjustment,
        "note": note
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
