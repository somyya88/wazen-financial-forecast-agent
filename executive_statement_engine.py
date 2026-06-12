import pandas as pd

def _sf(x):
    try:
        return float(x)
    except Exception:
        return 0.0

def build_executive_income_statement(pnl_model: dict, expense_model: dict | None = None):
    """
    Single executive P&L:
    Operating Revenue
    Other Revenue
    Total Revenue
    Cost of Revenue
    Gross Profit
    G&A
    Selling & Marketing
    Needs Review
    Total Operating Expenses
    Operating Profit
    Finance Costs
    Net Profit
    """
    operating_revenue = _sf(pnl_model.get("net_sales", pnl_model.get("sales", pnl_model.get("operating_revenue", 0))))
    total_revenue = _sf(pnl_model.get("revenue", 0))
    other_revenue = _sf(pnl_model.get("other_revenue", max(0, total_revenue - operating_revenue)))

    # If net_sales key not available, infer from P&L table.
    if operating_revenue == 0 and pnl_model.get("pnl") is not None:
        try:
            df = pnl_model.get("pnl")
            row = df[df["English"].astype(str).str.contains("Net Sales", case=False, na=False)]
            if not row.empty:
                operating_revenue = _sf(row.iloc[0]["Amount"])
        except Exception:
            pass

    if total_revenue == 0:
        total_revenue = operating_revenue + other_revenue

    official_cogs = _sf(pnl_model.get("cogs", 0))
    official_opex = _sf(pnl_model.get("opex", 0))
    official_net_profit = _sf(pnl_model.get("net_profit", 0))

    direct = admin = selling = finance = other = 0.0

    if expense_model and not expense_model.get("expense_long", pd.DataFrame()).empty:
        exp = expense_model["expense_long"].copy()
        exp["amount"] = pd.to_numeric(exp.get("amount"), errors="coerce").fillna(0)
        cat_col = "user_category" if "user_category" in exp.columns else ("category" if "category" in exp.columns else None)

        if cat_col:
            for _, r in exp.iterrows():
                cat = str(r.get(cat_col, ""))
                amount = _sf(r.get("amount", 0))
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

    # Cost of revenue must include official COGS / purchases first.
    cost_of_revenue = official_cogs if official_cogs else direct

    # Scale operating expense buckets to official opex to avoid mismatch with TB.
    non_direct = admin + selling + other
    if non_direct > 0 and official_opex > 0:
        scale = official_opex / non_direct
        admin *= scale
        selling *= scale
        other *= scale
    elif official_opex > 0:
        admin = official_opex

    gross_profit = total_revenue - cost_of_revenue
    total_operating_expenses = admin + selling + other
    operating_profit = gross_profit - total_operating_expenses

    # If official net profit differs, show finance/other adjustment as reconciling line.
    finance_costs = finance
    adjustment = operating_profit - finance_costs - official_net_profit
    if abs(adjustment) > 1:
        finance_costs += adjustment

    net_profit = operating_profit - finance_costs

    rows = [
        ["section", "الإيرادات", "", ""],
        ["line", "الإيرادات التشغيلية", "Operating Revenue", operating_revenue],
        ["line", "إيرادات أخرى", "Other Revenue", other_revenue],
        ["total", "إجمالي الإيرادات", "Total Revenue", total_revenue],

        ["section", "تكلفة الإيراد", "", ""],
        ["line", "تكلفة الإيراد / تكلفة البضاعة المباعة", "Cost of Revenue / COGS", cost_of_revenue],
        ["total", "مجمل الربح", "Gross Profit", gross_profit],

        ["section", "المصاريف التشغيلية", "", ""],
        ["line", "المصاريف الإدارية والعمومية", "General & Administrative Expenses", admin],
        ["line", "مصاريف البيع والتسويق", "Selling & Marketing Expenses", selling],
        ["line", "مصاريف تشغيلية أخرى", "Other Operating Expenses", other],
        ["total", "إجمالي المصاريف التشغيلية", "Total Operating Expenses", total_operating_expenses],

        ["total", "الربح التشغيلي", "Operating Profit", operating_profit],
        ["line", "مصاريف تمويلية / تسويات أخرى", "Finance Costs / Other Adjustments", finance_costs],
        ["net", "صافي الربح", "Net Profit", net_profit],
    ]

    return pd.DataFrame(rows, columns=["row_type", "العربي", "English", "Amount"])

def build_executive_kpis(pnl_model: dict, expense_model: dict | None = None):
    stmt = build_executive_income_statement(pnl_model, expense_model)
    def val(ar):
        r = stmt[stmt["العربي"].eq(ar)]
        return _sf(r.iloc[0]["Amount"]) if not r.empty else 0.0

    revenue = val("إجمالي الإيرادات")
    operating_revenue = val("الإيرادات التشغيلية")
    cost = val("تكلفة الإيراد / تكلفة البضاعة المباعة")
    gross = val("مجمل الربح")
    opex = val("إجمالي المصاريف التشغيلية")
    operating_profit = val("الربح التشغيلي")
    net_profit = val("صافي الربح")

    gross_margin = gross / revenue if revenue else 0
    net_margin = net_profit / revenue if revenue else 0
    opex_ratio = opex / revenue if revenue else 0

    if opex_ratio > 0.45:
        action = "مراجعة المصاريف التشغيلية"
        reason = f"المصاريف التشغيلية تمثل {opex_ratio*100:.1f}% من الإيرادات"
    elif net_margin < 0.10:
        action = "تحسين هامش الربح"
        reason = f"هامش صافي الربح {net_margin*100:.1f}%"
    else:
        action = "تثبيت الهامش قبل التوسع"
        reason = f"هامش صافي الربح {net_margin*100:.1f}%"

    return {
        "statement": stmt,
        "operating_revenue": operating_revenue,
        "revenue": revenue,
        "cost_of_revenue": cost,
        "gross_profit": gross,
        "gross_margin": gross_margin,
        "operating_expenses": opex,
        "operating_profit": operating_profit,
        "net_profit": net_profit,
        "net_margin": net_margin,
        "opex_ratio": opex_ratio,
        "next_action": action,
        "next_action_reason": reason,
    }

def build_executive_monthly_profitability(monthly_pnl_df: pd.DataFrame, pnl_model: dict, expense_model: dict | None = None):
    if monthly_pnl_df is None or monthly_pnl_df.empty:
        return pd.DataFrame()

    df = monthly_pnl_df.copy()
    for c in ["revenue", "expenses"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    total_revenue = df["revenue"].sum() if "revenue" in df.columns else 0
    cogs_total = _sf(pnl_model.get("cogs", 0))
    if total_revenue:
        df["cost_of_revenue"] = df["revenue"] / total_revenue * cogs_total
    else:
        df["cost_of_revenue"] = 0

    df["gross_profit"] = df["revenue"] - df["cost_of_revenue"]
    df["gross_margin"] = df.apply(lambda r: r["gross_profit"] / r["revenue"] if r["revenue"] else 0, axis=1)
    df["operating_expenses"] = df["expenses"]
    df["net_profit"] = df["gross_profit"] - df["operating_expenses"]
    df["net_margin"] = df.apply(lambda r: r["net_profit"] / r["revenue"] if r["revenue"] else 0, axis=1)

    month_ar = {
        "Jan": "يناير", "Feb": "فبراير", "Mar": "مارس", "Apr": "أبريل", "May": "مايو",
        "Jun": "يونيو", "Jul": "يوليو", "Aug": "أغسطس", "Sep": "سبتمبر",
        "Oct": "أكتوبر", "Nov": "نوفمبر", "Dec": "ديسمبر",
    }
    return pd.DataFrame({
        "الشهر": df["month"].map(lambda x: month_ar.get(str(x), str(x))),
        "الإيراد": df["revenue"],
        "تكلفة الإيراد": df["cost_of_revenue"],
        "مجمل الربح": df["gross_profit"],
        "هامش مجمل الربح": df["gross_margin"],
        "المصاريف التشغيلية": df["operating_expenses"],
        "صافي الربح": df["net_profit"],
        "هامش صافي الربح": df["net_margin"],
    })
