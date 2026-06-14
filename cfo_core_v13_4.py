from __future__ import annotations

from typing import Any
import math
import pandas as pd

MONTH_DAYS = 30.4375
MONTH_ALIASES = {
    "jan":"Jan", "january":"Jan", "يناير":"Jan", "كانون الثاني":"Jan",
    "feb":"Feb", "february":"Feb", "فبراير":"Feb", "شباط":"Feb",
    "mar":"Mar", "march":"Mar", "مارس":"Mar", "اذار":"Mar", "آذار":"Mar",
    "apr":"Apr", "april":"Apr", "ابريل":"Apr", "أبريل":"Apr", "نيسان":"Apr",
    "may":"May", "ماي":"May", "مايو":"May", "ايار":"May", "أيار":"May",
    "jun":"Jun", "june":"Jun", "يونيو":"Jun", "حزيران":"Jun",
    "jul":"Jul", "july":"Jul", "يوليو":"Jul", "تموز":"Jul",
    "aug":"Aug", "august":"Aug", "اغسطس":"Aug", "أغسطس":"Aug", "اب":"Aug", "آب":"Aug",
    "sep":"Sep", "september":"Sep", "سبتمبر":"Sep", "ايلول":"Sep", "أيلول":"Sep",
    "oct":"Oct", "october":"Oct", "اكتوبر":"Oct", "أكتوبر":"Oct", "تشرين الاول":"Oct",
    "nov":"Nov", "november":"Nov", "نوفمبر":"Nov", "تشرين الثاني":"Nov",
    "dec":"Dec", "december":"Dec", "ديسمبر":"Dec", "كانون الاول":"Dec",
}
MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _num(x: Any, default: float = 0.0) -> float:
    try:
        if x is None or pd.isna(x):
            return default
    except Exception:
        pass
    try:
        return float(x)
    except Exception:
        return default


def _norm(text: Any) -> str:
    s = "" if text is None else str(text)
    s = s.strip().lower()
    for a, b in {"أ":"ا", "إ":"ا", "آ":"ا", "ة":"ه", "ى":"ي", "ـ":"", "\u200f":"", "\u200e":""}.items():
        s = s.replace(a, b)
    return " ".join(s.split())


def canonical_month(value: Any) -> str | None:
    text = _norm(value)
    if not text:
        return None
    if text in MONTH_ALIASES:
        return MONTH_ALIASES[text]
    # Accept values like "Jan-2026" or "2026 يناير".
    for k, v in MONTH_ALIASES.items():
        if k and k in text:
            return v
    return None


def infer_period_context(selected_months: list[str] | None = None, profile: dict | None = None, tb_model: dict | None = None) -> dict:
    """Return period assumptions used by DSO/DPO/DIO and forecast notes.

    The old model used a fixed 150 days. V13.4 derives days from selected
    months when possible. If no month information exists, it marks the period
    as an assumption instead of silently pretending it is factual.
    """
    selected_months = selected_months or []
    months = []
    for m in selected_months:
        cm = canonical_month(m)
        if cm and cm not in months:
            months.append(cm)
    if months:
        days = max(1.0, len(months) * MONTH_DAYS)
        basis = "selected_months"
        note = f"تم احتساب أيام الفترة من عدد الشهور المعتمدة ({len(months)} شهر)."
    else:
        days = MONTH_DAYS * 12
        basis = "assumption_annualized"
        note = "لم تُحدد شهور التحليل؛ تم استخدام 12 شهرًا كافتراض محافظ بدل 150 يومًا ثابتة."
    return {
        "period_months": months,
        "period_month_count": len(months) if months else 12,
        "period_days": round(days, 2),
        "period_basis": basis,
        "period_note": note,
    }


def classify_tb_account(name: Any, code: Any = "") -> tuple[str, str, str]:
    """Classify an account into a CFO statement bucket with confidence.

    This does not replace manual mapping; it creates a transparent first draft
    and exposes confidence so the UI/export can show where review is needed.
    """
    n = _norm(name)
    c = str(code or "").strip().replace(".0", "")

    # Specific name rules first.
    rules: list[tuple[str, str, list[str], str]] = [
        ("cash", "Cash & Bank", ["نقد", "صندوق", "بنك", "bank", "cash"], "high_name"),
        ("accounts_receivable", "Accounts Receivable", ["عملاء", "عميل", "ذمم مدينه", "receivable", "customer"], "high_name"),
        ("inventory", "Inventory", ["مخزون", "بضاعه", "inventory", "stock"], "high_name"),
        ("fixed_assets", "Fixed Assets", ["اصل ثابت", "اصول ثابته", "معدات", "سيارات", "vehicles", "equipment", "fixed asset"], "medium_name"),
        ("accounts_payable", "Accounts Payable", ["مورد", "موردين", "ذمم دائنه", "payable", "supplier"], "high_name"),
        ("loans", "Loans & Financing", ["قرض", "قروض", "تمويل", "loan", "borrowing"], "medium_name"),
        ("equity", "Equity", ["راس المال", "رأس المال", "حقوق", "ارباح مبقاه", "capital", "equity"], "medium_name"),
        ("net_sales", "Net Sales", ["صافي المبيعات", "net sales"], "high_name"),
        ("sales_returns", "Sales Returns", ["مردودات المبيعات", "مرتجع مبيعات", "sales return"], "medium_name"),
        ("sales_discounts", "Sales Discounts", ["خصم ممنوح", "خصومات مبيعات", "sales discount"], "medium_name"),
        ("revenue", "Operating Revenue", ["مبيعات", "ايراد", "ايرادات", "revenue", "sales", "income"], "medium_name"),
        ("purchases", "Purchases / Direct Cost", ["مشتريات", "تكلفه المبيعات", "تكلفه الايراد", "cogs", "cost of revenue", "direct cost"], "medium_name"),
        ("depreciation", "Depreciation & Amortization", ["اهلاك", "استهلاك", "depreciation", "amortization"], "high_name"),
        ("finance_costs", "Finance Costs", ["فوائد", "مصروف تمويل", "تكاليف تمويل", "رسوم بنكيه", "bank charges", "interest", "finance cost"], "high_name"),
        ("tax_zakat", "Tax / Zakat", ["زكاه", "ضريبه", "tax", "zakat"], "medium_name"),
        ("selling_marketing", "Selling & Marketing", ["تسويق", "اعلان", "دعايه", "عموله بيع", "marketing", "selling"], "medium_name"),
        ("payroll", "Payroll", ["رواتب", "اجور", "بدلات", "salary", "payroll", "wages"], "medium_name"),
        ("rent", "Rent", ["ايجار", "rent"], "medium_name"),
        ("opex", "Operating Expenses", ["مصروف", "مصاريف", "expense", "opex"], "low_name"),
    ]
    for bucket, label, keys, confidence in rules:
        if any(k in n for k in [_norm(x) for x in keys]):
            return bucket, label, confidence

    # Code-family fallback: transparent but lower confidence because charts differ.
    if c.startswith("1"):
        return "assets", "Assets - code based", "low_code"
    if c.startswith("2"):
        return "liabilities", "Liabilities - code based", "low_code"
    if c.startswith("3"):
        return "equity_or_purchases", "Equity/Purchases - code based", "low_code"
    if c.startswith("4"):
        return "revenue", "Operating Revenue - code based", "medium_code"
    if c.startswith("5"):
        return "opex", "Operating Expenses - code based", "medium_code"
    return "unclassified", "Needs Manual Mapping", "needs_review"


def build_account_mapping_audit(tb_model: dict | None) -> pd.DataFrame:
    tb = (tb_model or {}).get("tb", pd.DataFrame())
    if tb is None or tb.empty:
        return pd.DataFrame(columns=["account_code", "account_name", "cfo_bucket", "cfo_label", "classification_confidence", "mapping_source"])
    rows = []
    for _, r in tb.iterrows():
        code = r.get("account_code_norm", r.get("account_code", ""))
        name = r.get("account_name", "")
        bucket, label, conf = classify_tb_account(name, code)
        rows.append({
            "account_code": code,
            "account_name": name,
            "cfo_bucket": bucket,
            "cfo_label": label,
            "classification_confidence": conf,
            "mapping_source": "deterministic_rules_v13_4",
            "closing_debit": _num(r.get("current_debit")),
            "closing_credit": _num(r.get("current_credit")),
            "movement_debit": _num(r.get("debit")),
            "movement_credit": _num(r.get("credit")),
        })
    return pd.DataFrame(rows)


def build_source_of_truth_report(
    tb_model: dict | None,
    revenue_model: dict | None,
    expense_model: dict | None,
    pnl_model: dict | None,
    selected_months: list[str] | None,
    profile: dict | None,
) -> dict:
    period = infer_period_context(selected_months, profile, tb_model)
    mapping = build_account_mapping_audit(tb_model)
    pnl_model = pnl_model or {}
    tb_income = ((tb_model or {}).get("income_statement") or {})
    external_revenue = _num((revenue_model or {}).get("total_revenue"), None)
    tb_revenue = _num(tb_income.get("total_revenue"), None)
    pnl_revenue = _num(pnl_model.get("revenue"), None)

    revenue_gap = None
    if external_revenue not in [None, 0] and tb_revenue not in [None, 0]:
        revenue_gap = pnl_revenue - external_revenue

    issues = []
    if mapping.empty:
        issues.append("لا توجد خريطة حسابات من ميزان المراجعة؛ ستبقى النسب المحاسبية محدودة.")
    elif (mapping["classification_confidence"].astype(str).str.contains("needs_review|low", regex=True).mean() > 0.35):
        issues.append("نسبة كبيرة من الحسابات مصنفة بثقة منخفضة؛ يلزم اعتماد Account Mapping قبل استخدام القرار النهائي.")
    if period.get("period_basis") != "selected_months":
        issues.append(period.get("period_note"))
    if revenue_gap is not None and abs(revenue_gap) > max(abs(external_revenue) * 0.05, 1):
        issues.append("يوجد فرق جوهري بين إيراد ملف المبيعات والإيراد المعتمد في قائمة الدخل؛ يجب مطابقة تعريف الإيراد.")

    source_rows = [
        {"metric": "Revenue", "value": pnl_revenue, "source": pnl_model.get("source", "unknown"), "confidence": "high" if tb_revenue else "medium", "note": "مصدر الحقيقة هو ميزان المراجعة عند توفره، وملف المبيعات يستخدم للتحقق أو عند غياب الميزان."},
        {"metric": "COGS", "value": _num(pnl_model.get("cogs")), "source": pnl_model.get("cogs_basis", "pnl_model"), "confidence": "medium", "note": "ترتفع الثقة عند وجود مخزون أول/آخر أو حساب تكلفة مبيعات مقفل."},
        {"metric": "EBITDA", "value": _num(pnl_model.get("ebitda")), "source": "P&L core", "confidence": "medium", "note": "V13.4 يفصل الإهلاك والتمويل والزكاة/الضريبة عند قراءتها من الميزان."},
        {"metric": "Net Profit", "value": _num(pnl_model.get("net_profit")), "source": "P&L core", "confidence": "medium", "note": "يجب أن يطابق نفس الرقم في الداشبورد والتصدير."},
        {"metric": "Period Days", "value": period.get("period_days"), "source": period.get("period_basis"), "confidence": "high" if period.get("period_basis") == "selected_months" else "assumption", "note": period.get("period_note")},
    ]
    return {
        "period": period,
        "account_mapping_audit": mapping,
        "source_of_truth": pd.DataFrame(source_rows),
        "issues": issues,
    }
