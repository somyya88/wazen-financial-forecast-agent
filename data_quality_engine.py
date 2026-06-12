import pandas as pd

def _safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

def build_source_reconciliation(pnl_model: dict, revenue_model: dict | None, expense_model: dict | None) -> pd.DataFrame:
    official_revenue = _safe_float(pnl_model.get("revenue", 0))
    official_expenses = _safe_float(pnl_model.get("opex", 0)) + _safe_float(pnl_model.get("cogs", 0))
    official_net_profit = _safe_float(pnl_model.get("net_profit", 0))

    monthly_revenue = 0.0
    if revenue_model and not revenue_model.get("monthly_revenue", pd.DataFrame()).empty:
        monthly_revenue = _safe_float(pd.to_numeric(revenue_model["monthly_revenue"]["revenue"], errors="coerce").sum())

    monthly_expenses = 0.0
    if expense_model and not expense_model.get("monthly_expenses", pd.DataFrame()).empty:
        monthly_expenses = _safe_float(pd.to_numeric(expense_model["monthly_expenses"]["expenses"], errors="coerce").sum())

    supporting_profit = monthly_revenue - monthly_expenses
    df = pd.DataFrame([
        ["الإيرادات", "Revenue", official_revenue, monthly_revenue, official_revenue - monthly_revenue],
        ["إجمالي التكاليف والمصاريف", "Costs & Expenses", official_expenses, monthly_expenses, official_expenses - monthly_expenses],
        ["صافي الربح", "Net Profit", official_net_profit, supporting_profit, official_net_profit - supporting_profit],
    ], columns=["البند", "English", "من ميزان المراجعة", "من الملفات الشهرية", "الفرق"])

    def assess(row):
        official = abs(_safe_float(row["من ميزان المراجعة"]))
        diff = abs(_safe_float(row["الفرق"]))
        ratio = diff / official if official else (0 if diff == 0 else 1)
        if ratio <= 0.02:
            return "مطابق تقريباً"
        if ratio <= 0.10:
            return "فرق مقبول يحتاج تفسير"
        return "فرق جوهري يحتاج مراجعة"

    df["التقييم"] = df.apply(assess, axis=1)
    return df

def build_data_quality_score(pnl_model: dict, revenue_model: dict | None, expense_model: dict | None) -> dict:
    score = 100
    checks = []

    if pnl_model and _safe_float(pnl_model.get("revenue", 0)) > 0:
        checks.append(("ميزان المراجعة", "متوفر ويستخدم كمصدر رسمي", "جيد"))
    else:
        score -= 35
        checks.append(("ميزان المراجعة", "غير مكتمل أو لا يحتوي إيرادات واضحة", "خطر"))

    if revenue_model and not revenue_model.get("monthly_revenue", pd.DataFrame()).empty:
        checks.append(("ملف المبيعات الشهرية", "متوفر للتحليل الشهري", "جيد"))
    else:
        score -= 15
        checks.append(("ملف المبيعات الشهرية", "غير متوفر أو غير مقروء", "تنبيه"))

    if expense_model and not expense_model.get("monthly_expenses", pd.DataFrame()).empty:
        checks.append(("ملف المصاريف الشهرية", "متوفر للتحليل الشهري", "جيد"))
    else:
        score -= 15
        checks.append(("ملف المصاريف الشهرية", "غير متوفر أو غير مقروء", "تنبيه"))

    other_share = 0.0
    if expense_model and not expense_model.get("by_category", pd.DataFrame()).empty:
        cat = expense_model["by_category"].copy()
        cat["amount"] = pd.to_numeric(cat["amount"], errors="coerce").fillna(0)
        total = _safe_float(cat["amount"].sum())
        other = _safe_float(cat.loc[cat["category"].astype(str).str.contains("Other", case=False, na=False), "amount"].sum()) if "category" in cat.columns else 0
        other_share = other / total if total else 0
        if other_share > 0.25:
            score -= 15
            checks.append(("تصنيف المصاريف", f"Needs Review يمثل {other_share*100:.1f}% من المصاريف", "يحتاج مراجعة"))
        else:
            checks.append(("تصنيف المصاريف", "نسبة البنود العامة ضمن مستوى مقبول", "جيد"))
    else:
        score -= 10
        checks.append(("تصنيف المصاريف", "لا يوجد هيكل مصاريف كافٍ", "تنبيه"))

    return {
        "score": max(0, min(100, int(score))),
        "checks": pd.DataFrame(checks, columns=["العنصر", "الملاحظة", "الحالة"]),
        "other_share": other_share,
    }
