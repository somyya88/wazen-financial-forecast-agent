import pandas as pd

def safe_div(a, b):
    return a / b if b else 0

def build_ratios(pnl_model, expense_model=None):
    revenue = pnl_model.get("revenue", 0)
    ratios = [
        ["Gross Margin %", "هامش مجمل الربح", safe_div(pnl_model.get("gross_profit", 0), revenue), "يقيس قدرة الإيرادات على تغطية التكلفة المباشرة."],
        ["EBITDA Margin %", "هامش EBITDA", safe_div(pnl_model.get("ebitda", 0), revenue), "يقيس ربحية النشاط قبل الإهلاك والتمويل."],
        ["Net Margin %", "هامش صافي الربح", safe_div(pnl_model.get("net_profit", 0), revenue), "يقيس النتيجة النهائية مقابل الإيرادات."],
        ["Opex Ratio %", "نسبة المصاريف التشغيلية", safe_div(pnl_model.get("opex", 0), revenue), "يقيس عبء المصاريف التشغيلية على الإيرادات."],
        ["COGS Ratio %", "نسبة تكلفة الإيراد", safe_div(pnl_model.get("cogs", 0), revenue), "يقيس تكلفة تقديم الخدمة أو المنتج."],
        ["Expense Ratio %", "نسبة إجمالي المصاريف", safe_div(pnl_model.get("total_expenses", 0), revenue), "يقيس إجمالي المصاريف إلى الإيرادات."],
    ]

    score = 50
    net_margin = ratios[2][2]
    ebitda_margin = ratios[1][2]
    expense_ratio = ratios[5][2]

    if net_margin > 0.10:
        score += 20
    elif net_margin > 0:
        score += 10
    else:
        score -= 15

    if ebitda_margin > 0.15:
        score += 15
    elif ebitda_margin < 0:
        score -= 10

    if expense_ratio < 0.75:
        score += 15
    elif expense_ratio > 1:
        score -= 15

    score = max(0, min(100, score))

    df = pd.DataFrame(ratios, columns=["English", "العربي", "Value", "Why it matters"])
    return {
        "ratios": df,
        "financial_health_score": score,
        "biggest_risk": _biggest_risk(df, score),
        "next_decision": _next_decision(df, score),
    }

def _biggest_risk(ratios_df, score):
    net_margin = float(ratios_df.loc[ratios_df["English"] == "Net Margin %", "Value"].iloc[0])
    expense_ratio = float(ratios_df.loc[ratios_df["English"] == "Expense Ratio %", "Value"].iloc[0])
    if net_margin < 0:
        return "الخطر الأكبر: المصاريف أعلى من الإيرادات خلال الفترة المعتمدة."
    if expense_ratio > 0.95:
        return "الخطر الأكبر: هامش الأمان ضعيف لأن المصاريف تستهلك معظم الإيرادات."
    if score < 50:
        return "الخطر الأكبر: ضعف الصحة المالية حسب المؤشرات الأولية."
    return "لا يظهر خطر حاد، لكن يجب متابعة هامش الربح والتحصيل."

def _next_decision(ratios_df, score):
    net_margin = float(ratios_df.loc[ratios_df["English"] == "Net Margin %", "Value"].iloc[0])
    if net_margin < 0:
        return "القرار القادم: مراجعة أعلى بنود المصروفات قبل أي توسع جديد."
    if net_margin < 0.05:
        return "القرار القادم: تحسين الهامش عبر التسعير أو خفض التكاليف المباشرة."
    return "القرار القادم: تثبيت الربحية وبناء توقعات نمو محافظة."
