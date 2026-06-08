import pandas as pd

MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def next_months(existing_months, periods=6):
    if not existing_months:
        start = 0
    else:
        last = existing_months[-1]
        start = (MONTH_ORDER.index(last) + 1) % 12 if last in MONTH_ORDER else 0
    return [MONTH_ORDER[(start + i) % 12] for i in range(periods)]

def build_forecast(monthly_pnl_df, periods=6):
    if monthly_pnl_df is None or monthly_pnl_df.empty:
        return pd.DataFrame(), "لا توجد بيانات شهرية كافية للتوقع."

    months = monthly_pnl_df["month"].tolist()
    future = next_months(months, periods)
    avg_revenue = float(monthly_pnl_df["revenue"].mean())
    avg_expenses = float(monthly_pnl_df["expenses"].mean())

    rows = []
    scenarios = [
        ("Conservative", "متحفظ", -0.10, 0.05),
        ("Base", "أساسي", 0.00, 0.00),
        ("Growth", "نمو", 0.10, 0.03),
    ]

    for scenario, arabic, rev_growth, exp_growth in scenarios:
        rev = avg_revenue
        exp = avg_expenses
        for i, m in enumerate(future, 1):
            rev = rev * (1 + rev_growth)
            exp = exp * (1 + exp_growth)
            rows.append({
                "Scenario": scenario,
                "العربي": arabic,
                "month": m,
                "forecast_revenue": rev,
                "forecast_expenses": exp,
                "forecast_profit": rev - exp,
                "forecast_margin": (rev - exp) / rev if rev else 0,
            })

    return pd.DataFrame(rows), "التوقع مبني على متوسط الأداء الشهري مع 3 سيناريوهات أولية. يمكن لاحقاً ربطه بعدد العملاء والتحصيل والطاقة التشغيلية."
