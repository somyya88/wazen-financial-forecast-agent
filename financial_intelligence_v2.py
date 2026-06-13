from __future__ import annotations

import math
import os
import json
from typing import Any

import pandas as pd


# -----------------------------------------------------------------------------
# Small helpers
# -----------------------------------------------------------------------------
def _num(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        if pd.isna(x):
            return default
    except Exception:
        pass
    try:
        return float(x)
    except Exception:
        return default


def _safe_div(a: Any, b: Any) -> float | None:
    a, b = _num(a), _num(b)
    if abs(b) < 1e-9:
        return None
    return a / b


def _pct(x: float | None) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "غير متاح"
    return f"{x*100:.1f}%"


def _ratio(x: float | None) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "غير متاح"
    return f"{x:.2f}x"


def _days(x: float | None) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "غير متاح"
    return f"{x:.0f} يوم"


def _months(x: float | None) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "غير متاح"
    return f"{x:.1f} شهر"


def _money(x: float | None) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "غير متاح"
    return f"{x:,.0f}"


def _norm(text: Any) -> str:
    s = "" if text is None else str(text)
    s = s.strip().lower()
    repl = {"أ":"ا", "إ":"ا", "آ":"ا", "ة":"ه", "ى":"ي", "ـ":"", "\u200f":"", "\u200e":""}
    for a, b in repl.items():
        s = s.replace(a, b)
    return s


def _sector_type(profile: dict | None) -> str:
    profile = profile or {}
    text = _norm(" ".join([str(profile.get(k, "")) for k in ["sector", "activity", "business_model", "sales_channel"]]))
    if any(k in text for k in ["saas", "برمج", "منصه", "منصة", "اشتراك", "تقنيه", "تقنية"]):
        return "saas"
    if any(k in text for k in ["مطعم", "مقهى", "مقاهي", "food", "restaurant"]):
        return "restaurant"
    if any(k in text for k in ["مقاول", "مشاريع", "انشاء", "construction"]):
        return "contracting"
    if any(k in text for k in ["تجارة", "تجاري", "تجزئة", "جملة", "retail", "wholesale"]):
        return "trading"
    if any(k in text for k in ["صحي", "عياد", "طبي"]):
        return "healthcare"
    return "general"


# -----------------------------------------------------------------------------
# Benchmarks and status rules. These are advisory, not hard universal standards.
# -----------------------------------------------------------------------------
def _status(metric: str, value: float | None, sector: str = "general") -> tuple[str, str]:
    if value is None:
        return "غير محسوب", "لا تتوفر بيانات كافية للحساب."

    if metric == "gross_margin":
        if sector == "saas":
            if value >= 0.60: return "جيد", "الهامش الإجمالي مناسب مبدئيًا لنموذج برمجي إذا كانت تكلفة الخدمة مصنفة بدقة."
            if value >= 0.40: return "متوسط", "الهامش مقبول لكنه يحتاج متابعة تكلفة الدعم والتشغيل والتنفيذ."
            return "خطر", "هامش الربح الإجمالي منخفض لنشاط برمجي؛ المشكلة قد تكون في التسعير أو تكلفة تقديم الخدمة."
        if sector == "restaurant":
            if value >= 0.55: return "جيد", "الهامش الإجمالي جيد مبدئيًا إذا كانت تكلفة المواد والعمالة المباشرة محسوبة بدقة."
            if value >= 0.35: return "متوسط", "الهامش يحتاج مراقبة تكلفة المواد والهدر والخصومات."
            return "خطر", "الهامش منخفض وقد يشير إلى ارتفاع تكلفة المواد أو التسعير غير الكافي."
        if value >= 0.35: return "جيد", "الهامش الإجمالي جيد مبدئيًا."
        if value >= 0.20: return "متوسط", "الهامش يحتاج فحص التكلفة المباشرة والتسعير."
        return "خطر", "الهامش الإجمالي ضعيف ويحتاج معالجة قبل التركيز على المصاريف الإدارية."

    if metric in ["operating_margin", "ebitda_margin"]:
        if value >= 0.15: return "جيد", "التشغيل يترك هامشًا مناسبًا بعد تكلفة الإيراد والمصاريف التشغيلية."
        if value >= 0.05: return "متوسط", "الشركة تحقق ربحًا تشغيليًا لكن هامش الأمان محدود."
        if value >= 0: return "ضعيف", "التشغيل موجب لكنه قريب من نقطة التعادل."
        return "خطر", "التشغيل غير مربح؛ النشاط لا يغطي كلفته التشغيلية الحالية."

    if metric == "net_margin":
        if value >= 0.10: return "جيد", "صافي الربح جيد مبدئيًا."
        if value >= 0.03: return "متوسط", "صافي الربح موجود لكنه حساس لأي ارتفاع تكلفة أو تأخر تحصيل."
        if value >= 0: return "ضعيف", "صافي الربح ضعيف ولا يعطي هامش أمان كافٍ."
        return "خطر", "الشركة خاسرة خلال الفترة."

    if metric in ["admin_ratio", "sm_ratio", "opex_ratio", "cogs_ratio"]:
        # For cost ratios, lower is generally better but sector context matters.
        if metric == "admin_ratio":
            if value <= 0.12: return "جيد", "المصاريف الإدارية تبدو منضبطة كنسبة من الإيراد."
            if value <= 0.25: return "متوسط", "المصاريف الإدارية تحتاج متابعة حتى لا تلتهم الهامش."
            return "خطر", "المصاريف الإدارية مرتفعة وقد تكون ضغطًا هيكليًا على الربحية."
        if metric == "sm_ratio":
            if value <= 0.10: return "جيد", "تكلفة البيع والتسويق منضبطة مبدئيًا."
            if value <= 0.25: return "متوسط", "تكلفة النمو تحتاج ربطًا بنتائج المبيعات والعملاء الجدد."
            return "خطر", "تكلفة البيع والتسويق مرتفعة وقد تعني شراء الإيراد بهامش ضعيف."
        if metric == "cogs_ratio":
            if value <= 0.45: return "جيد", "تكلفة الإيراد تترك هامشًا جيدًا."
            if value <= 0.65: return "متوسط", "تكلفة الإيراد تحتاج متابعة."
            return "خطر", "تكلفة الإيراد تلتهم نسبة كبيرة من المبيعات."
        if value <= 0.65: return "جيد", "عبء المصاريف التشغيلية مقبول مبدئيًا."
        if value <= 0.90: return "متوسط", "المصاريف التشغيلية تضغط الهامش."
        return "خطر", "المصاريف التشغيلية تستهلك معظم الإيراد."

    if metric == "current_ratio":
        if value >= 1.5: return "جيد", "الأصول المتداولة تغطي الالتزامات القصيرة بهامش مناسب."
        if value >= 1.0: return "متوسط", "السيولة المحاسبية تغطي الالتزامات لكن هامش الأمان محدود."
        return "خطر", "الأصول المتداولة لا تغطي الالتزامات القصيرة."

    if metric == "quick_ratio":
        if value >= 1.0: return "جيد", "السيولة السريعة تكفي مبدئيًا دون الاعتماد على المخزون."
        if value >= 0.6: return "متوسط", "الشركة تعتمد على سرعة التحصيل لتأمين السيولة."
        return "خطر", "السيولة السريعة ضعيفة أمام الالتزامات القصيرة."

    if metric == "cash_ratio":
        if value >= 0.5: return "جيد", "النقد يغطي جزءًا جيدًا من الالتزامات القصيرة."
        if value >= 0.2: return "متوسط", "النقد المباشر محدود ويحتاج مراقبة."
        return "خطر", "النقد الفوري ضعيف أمام الالتزامات القصيرة."

    if metric in ["dso", "dpo", "dio", "ccc"]:
        if metric == "dso":
            if value <= 30: return "جيد", "التحصيل سريع مبدئيًا."
            if value <= 60: return "متوسط", "التحصيل يحتاج متابعة دورية."
            return "خطر", "التحصيل بطيء ويضغط السيولة."
        if metric == "dpo":
            if value <= 30: return "جيد", "السداد للموردين سريع نسبيًا ولا يظهر اعتمادًا كبيرًا على الموردين."
            if value <= 75: return "متوسط", "الشركة تستفيد من آجال الموردين لكن يجب مراقبة العلاقة معهم."
            return "خطر", "تأخير السداد للموردين مرتفع وقد يخفي ضغط سيولة."
        if metric == "dio":
            if value <= 45: return "جيد", "المخزون يتحول إلى مبيعات بسرعة مقبولة."
            if value <= 90: return "متوسط", "المخزون يحتاج متابعة حتى لا يحبس النقد."
            return "خطر", "المخزون بطيء وقد يحبس رأس المال العامل."
        if value <= 45: return "جيد", "دورة النقد قصيرة نسبيًا."
        if value <= 90: return "متوسط", "دورة النقد تحتاج متابعة."
        return "خطر", "دورة النقد طويلة وتحبس السيولة داخل التشغيل."

    if metric == "runway":
        if value >= 3: return "جيد", "النقد يغطي عدة أشهر من الخروج النقدي."
        if value >= 1: return "متوسط", "النقد يغطي فترة قصيرة ويحتاج متابعة شهرية."
        return "خطر", "النقد لا يغطي شهرًا كاملًا من متوسط الخروج النقدي."

    if metric in ["debt_ratio", "debt_to_equity"]:
        if metric == "debt_ratio":
            if value <= 0.5: return "جيد", "الاعتماد على الالتزامات ضمن مستوى محافظ."
            if value <= 0.75: return "متوسط", "المديونية تحتاج متابعة."
            return "خطر", "الالتزامات تمول نسبة عالية من الأصول."
        if value <= 1.0: return "جيد", "الالتزامات أقل من أو قريبة من حقوق الملكية."
        if value <= 2.0: return "متوسط", "الرافعة المالية متوسطة."
        return "خطر", "الالتزامات مرتفعة قياسًا بحقوق الملكية."

    if metric == "ocf_net_income":
        if value >= 1.0: return "جيد", "التدفق النقدي التشغيلي يغطي صافي الربح أو يتجاوزه."
        if value >= 0.6: return "متوسط", "جزء من الربح يتحول إلى نقد لكن الجودة تحتاج متابعة."
        if value >= 0: return "خطر", "الربح لا يتحول إلى نقد بشكل كافٍ."
        return "خطر", "التدفق النقدي عكس الربح، وهو إنذار لجودة الأرباح أو التحصيل."

    if metric in ["asset_turnover", "fixed_asset_turnover", "roa", "roe", "receivables_turnover", "payables_turnover", "inventory_turnover", "margin_of_safety"]:
        return "إرشادي", "مؤشر تحليلي يحتاج قراءة مع القطاع والاتجاه السابق."

    return "إرشادي", "مؤشر إرشادي."


def _fmt(metric: str, value: float | None) -> str:
    if metric in ["gross_margin", "operating_margin", "ebitda_margin", "net_margin", "admin_ratio", "sm_ratio", "opex_ratio", "cogs_ratio", "debt_ratio", "roa", "roe", "margin_of_safety", "ocf_net_income"]:
        return _pct(value)
    if metric in ["current_ratio", "quick_ratio", "cash_ratio", "debt_to_equity", "asset_turnover", "fixed_asset_turnover", "receivables_turnover", "payables_turnover", "inventory_turnover"]:
        return _ratio(value)
    if metric in ["dso", "dpo", "dio", "ccc"]:
        return _days(value)
    if metric == "runway":
        return _months(value)
    if metric in ["break_even_sales", "working_capital"]:
        return _money(value)
    return _money(value)


# -----------------------------------------------------------------------------
# Metric pack
# -----------------------------------------------------------------------------
def build_metric_pack(pnl_model: dict, management_pnl: dict, balance_model: dict, liquidity_model: dict | None, breakeven_model: dict | None = None, profile: dict | None = None) -> dict:
    profile = profile or {}
    sector = _sector_type(profile)
    b = (balance_model or {}).get("metrics", {}) if balance_model else {}
    cash_cards = (((liquidity_model or {}).get("cash") or {}).get("cards") or {})
    ar_cards = (((liquidity_model or {}).get("ar") or {}).get("cards") or {})
    ap_cards = (((liquidity_model or {}).get("ap") or {}).get("cards") or {})
    breakeven_model = breakeven_model or {}

    revenue = _num(management_pnl.get("revenue"), _num(pnl_model.get("revenue")))
    cogs = _num(management_pnl.get("cogs"), _num(pnl_model.get("cogs")))
    gross_profit = _num(management_pnl.get("gross_profit"), _num(pnl_model.get("gross_profit")))
    opex = _num(management_pnl.get("opex"), _num(pnl_model.get("opex")))
    operating_profit = _num(management_pnl.get("revenue")) - _num(management_pnl.get("cogs")) - _num(management_pnl.get("opex"))
    net_profit = _num(management_pnl.get("net_profit"), _num(pnl_model.get("net_profit")))
    admin = _num(management_pnl.get("admin_opex"))
    sm = _num(management_pnl.get("selling_marketing"))

    current_assets = _num(b.get("current_assets"))
    current_liabilities = _num(b.get("current_liabilities"))
    cash = _num(b.get("cash")) or _num(cash_cards.get("ending_cash"))
    ar = _num(b.get("ar")) or _num(ar_cards.get("total_balance"))
    ap = _num(b.get("ap")) or _num(ap_cards.get("total_balance"))
    inventory = _num(b.get("inventory"))
    total_assets = _num(b.get("total_assets"))
    fixed_assets = _num(b.get("fixed_assets"))
    total_liabilities = _num(b.get("total_liabilities"))
    equity = _num(b.get("equity"))
    working_capital = _num(b.get("working_capital"), current_assets - current_liabilities)

    period_days = float(profile.get("period_days") or 150.0)
    daily_revenue = revenue / period_days if revenue else 0
    daily_cogs = cogs / period_days if cogs else 0
    # Do not display 0 days as a valid DSO/DPO/CCC when no AR/AP/Inventory balance exists.
    # 0 can be a real result only if the source explicitly has zero receivables/payables; in generic TB reading, absence should be "غير محسوب".
    dso = _safe_div(ar, daily_revenue) if (daily_revenue and ar > 0) else None
    dpo = _safe_div(ap, daily_cogs) if (daily_cogs and ap > 0) else None
    dio = _safe_div(inventory, daily_cogs) if (daily_cogs and inventory > 0) else None
    ccc = (dso if dso is not None else 0) + (dio if dio is not None else 0) - (dpo if dpo is not None else 0) if (dso is not None or dio is not None or dpo is not None) else None
    runway = cash_cards.get("cash_runway_months")
    runway = None if runway in [None, ""] else _num(runway)
    net_cash_flow = cash_cards.get("net_cash_flow")
    ocf_proxy = _safe_div(net_cash_flow, net_profit) if net_cash_flow is not None and abs(net_profit) > 1e-9 else None

    metrics = {
        "revenue": revenue,
        "gross_margin": _safe_div(gross_profit, revenue),
        "cogs_ratio": _safe_div(cogs, revenue),
        "operating_margin": _safe_div(operating_profit, revenue),
        "ebitda_margin": _safe_div(_num(pnl_model.get("ebitda", operating_profit)), revenue),
        "net_margin": _safe_div(net_profit, revenue),
        "admin_ratio": _safe_div(admin, revenue),
        "sm_ratio": _safe_div(sm, revenue),
        "opex_ratio": _safe_div(opex, revenue),
        "current_ratio": _safe_div(current_assets, current_liabilities),
        "quick_ratio": _safe_div(cash + ar, current_liabilities),
        "cash_ratio": _safe_div(cash, current_liabilities),
        "working_capital": working_capital,
        "runway": runway,
        "dso": dso,
        "receivables_turnover": _safe_div(revenue, ar),
        "dpo": dpo,
        "payables_turnover": _safe_div(cogs, ap),
        "dio": dio,
        "inventory_turnover": _safe_div(cogs, inventory),
        "ccc": ccc,
        "asset_turnover": _safe_div(revenue, total_assets),
        "fixed_asset_turnover": _safe_div(revenue, fixed_assets),
        "roa": _safe_div(net_profit, total_assets),
        "roe": _safe_div(net_profit, equity),
        "debt_ratio": _safe_div(total_liabilities, total_assets),
        "debt_to_equity": _safe_div(total_liabilities, equity),
        "ocf_net_income": ocf_proxy,
        "break_even_sales": _num(breakeven_model.get("break_even_sales")) or None,
        "margin_of_safety": breakeven_model.get("margin_of_safety"),
    }

    definitions = [
        ("الربحية", "هامش مجمل الربح", "gross_margin", "مجمل الربح ÷ صافي الإيرادات", "هل العمل الأساسي يترك هامشًا قبل الإدارة والتسويق؟"),
        ("الربحية", "نسبة تكلفة الإيراد", "cogs_ratio", "تكلفة الإيراد ÷ صافي الإيرادات", "كم تستهلك تكلفة تقديم الخدمة أو المنتج من كل ريال مبيعات؟"),
        ("الربحية", "هامش الربح التشغيلي", "operating_margin", "الربح التشغيلي ÷ صافي الإيرادات", "هل التشغيل مربح بعد تكلفة الإيراد والمصاريف الإدارية والتسويقية؟"),
        ("الربحية", "هامش EBITDA", "ebitda_margin", "EBITDA ÷ صافي الإيرادات", "هل النشاط يولد ربحًا قبل التمويل والإهلاك؟"),
        ("الربحية", "هامش صافي الربح", "net_margin", "صافي الربح ÷ صافي الإيرادات", "ما النتيجة النهائية من كل ريال مبيعات؟"),
        ("المصاريف", "المصاريف الإدارية من الإيراد", "admin_ratio", "المصاريف الإدارية ÷ صافي الإيرادات", "هل الهيكل الإداري يضغط الربحية؟"),
        ("المصاريف", "البيع والتسويق من الإيراد", "sm_ratio", "مصاريف البيع والتسويق ÷ صافي الإيرادات", "هل تكلفة النمو منضبطة؟"),
        ("السيولة", "رأس المال العامل", "working_capital", "الأصول المتداولة - الالتزامات المتداولة", "هل لدى الشركة مساحة تشغيل قصيرة الأجل؟"),
        ("السيولة", "نسبة التداول", "current_ratio", "الأصول المتداولة ÷ الالتزامات المتداولة", "هل تغطي الأصول القصيرة الالتزامات القصيرة؟"),
        ("السيولة", "النسبة السريعة", "quick_ratio", "النقد + العملاء ÷ الالتزامات المتداولة", "هل يمكن السداد دون الاعتماد على المخزون؟"),
        ("السيولة", "نسبة النقدية", "cash_ratio", "النقد ÷ الالتزامات المتداولة", "كم من الالتزامات القصيرة يمكن تغطيته نقدًا فورًا؟"),
        ("السيولة", "Cash Runway", "runway", "النقد ÷ متوسط الخروج النقدي الشهري", "كم شهر يغطي النقد المتاح؟"),
        ("التحصيل ورأس المال العامل", "أيام التحصيل DSO", "dso", "العملاء ÷ متوسط المبيعات اليومية", "كم يوم تحتاج المبيعات لتتحول إلى نقد؟"),
        ("التحصيل ورأس المال العامل", "دوران الذمم المدينة", "receivables_turnover", "صافي الإيرادات ÷ العملاء", "كم مرة تتحول الذمم إلى نقد خلال الفترة؟"),
        ("التحصيل ورأس المال العامل", "أيام السداد DPO", "dpo", "الموردون ÷ متوسط تكلفة الإيراد اليومية", "كم يوم تستفيد الشركة من آجال الموردين؟"),
        ("التحصيل ورأس المال العامل", "أيام المخزون DIO", "dio", "المخزون ÷ متوسط تكلفة الإيراد اليومية", "كم يوم يبقى المخزون قبل البيع؟"),
        ("التحصيل ورأس المال العامل", "دورة تحويل النقد CCC", "ccc", "DSO + DIO - DPO", "كم يوم يبقى النقد محبوسًا داخل التشغيل؟"),
        ("الدوران والكفاءة", "دوران الأصول", "asset_turnover", "الإيرادات ÷ إجمالي الأصول", "ما كفاءة الأصول في توليد الإيراد؟"),
        ("الدوران والكفاءة", "دوران الأصول الثابتة", "fixed_asset_turnover", "الإيرادات ÷ الأصول الثابتة", "ما كفاءة تشغيل الأصول الثابتة؟"),
        ("العائد", "العائد على الأصول ROA", "roa", "صافي الربح ÷ إجمالي الأصول", "ما العائد الناتج من الأصول؟"),
        ("العائد", "العائد على حقوق الملكية ROE", "roe", "صافي الربح ÷ حقوق الملكية", "ما العائد على رأس مال الملاك؟"),
        ("المديونية والسلامة", "نسبة الالتزامات إلى الأصول", "debt_ratio", "إجمالي الالتزامات ÷ إجمالي الأصول", "كم من الأصول ممول بالتزامات؟"),
        ("المديونية والسلامة", "الالتزامات إلى حقوق الملكية", "debt_to_equity", "إجمالي الالتزامات ÷ حقوق الملكية", "ما مستوى الرافعة المالية؟"),
        ("جودة الربح", "التدفق التشغيلي إلى صافي الربح", "ocf_net_income", "صافي التدفق النقدي التشغيلي ÷ صافي الربح", "هل الربح يتحول إلى نقد؟"),
        ("التعادل", "مبيعات نقطة التعادل", "break_even_sales", "التكاليف الثابتة ÷ هامش المساهمة", "كم مبيعات تحتاج الشركة لتغطية تكاليفها؟"),
        ("التعادل", "هامش الأمان", "margin_of_safety", "المبيعات الحالية - نقطة التعادل ÷ المبيعات الحالية", "كم تستطيع المبيعات أن تنخفض قبل الخسارة؟"),
    ]
    rows = []
    for group, name, key, formula, question in definitions:
        val = metrics.get(key)
        status, brief = _status(key, val, sector)
        rows.append({
            "المجموعة": group,
            "المؤشر": name,
            "الكود": key,
            "النتيجة": _fmt(key, val),
            "الحكم": status,
            "طريقة الحساب": formula,
            "سؤال الإدارة": question,
            "قراءة أولية": brief,
            "القيمة الرقمية": val,
        })
    ratios = pd.DataFrame(rows)
    return {
        "metrics": metrics,
        "ratios": ratios,
        "sector_type": sector,
        "data_quality": _data_quality(liquidity_model, metrics),
    }


def _data_quality(liquidity_model: dict | None, metrics: dict) -> dict:
    cash_available = bool((((liquidity_model or {}).get("cash") or {}).get("available")))
    ar_available = bool((((liquidity_model or {}).get("ar") or {}).get("available")))
    ap_available = bool((((liquidity_model or {}).get("ap") or {}).get("available")))
    return {
        "cash_available": cash_available,
        "ar_available": ar_available,
        "ap_available": ap_available,
        "can_judge_cash": cash_available or metrics.get("cash_ratio") is not None,
        "can_judge_collection": ar_available or metrics.get("dso") is not None,
    }


# -----------------------------------------------------------------------------
# Diagnostic layer + narratives
# -----------------------------------------------------------------------------
def _priority(status: str, weight: int = 50) -> int:
    return {"خطر": 100, "ضعيف": 80, "متوسط": 55, "جيد": 20, "إرشادي": 30, "غير محسوب": 10}.get(status, weight)


def build_diagnostic_findings(metric_pack: dict, profile: dict | None = None) -> pd.DataFrame:
    m = metric_pack.get("metrics", {})
    sector = metric_pack.get("sector_type", "general")
    rows = []

    def add(area, title, evidence, risk, cause, impact, action, monitor, priority):
        rows.append({
            "المجال": area,
            "النتيجة التنفيذية": title,
            "الدليل": evidence,
            "مستوى الخطورة": risk,
            "السبب المحتمل": cause,
            "الأثر المالي": impact,
            "الإجراء المقترح": action,
            "مؤشر المتابعة": monitor,
            "الأولوية": priority,
        })

    gm = m.get("gross_margin")
    om = m.get("operating_margin")
    nm = m.get("net_margin")
    admin = m.get("admin_ratio")
    sm = m.get("sm_ratio")
    dso = m.get("dso")
    runway = m.get("runway")
    cr = m.get("current_ratio")
    cashr = m.get("cash_ratio")
    ccc = m.get("ccc")
    ocf = m.get("ocf_net_income")

    if gm is not None:
        st, _ = _status("gross_margin", gm, sector)
        if st in ["خطر", "متوسط"]:
            add("الربحية", "هامش الربح الإجمالي يحتاج مراجعة قبل الحكم على المصاريف الإدارية.", f"هامش مجمل الربح {_pct(gm)}", st, "تكلفة تقديم الخدمة أو تكلفة المبيعات مرتفعة، أو أن التسعير لا يغطي التكلفة المباشرة.", "كل تراجع في هذا الهامش يقلل قدرة الشركة على تغطية الإدارة والتسويق والتمويل.", "افصل تكلفة الإيراد حسب فريق التشغيل/الخدمة/العميل أو الصنف، وراجع الأسعار أو حدود الخدمة.", "Gross Margin و COGS %", _priority(st, 90))

    if gm is not None and om is not None:
        if gm > 0.35 and om < 0.05:
            add("التشغيل", "النشاط الأساسي يترك هامشًا، لكن التشغيل يستهلكه بعد الإدارة والتسويق.", f"Gross Margin {_pct(gm)} مقابل Operating Margin {_pct(om)}", "خطر" if om < 0 else "متوسط", "المصاريف الإدارية أو التسويقية أو الهيكل التشغيلي نمت أسرع من قدرة الإيراد.", "قد تستمر المبيعات بالنمو دون أن تتحول إلى ربح تشغيلي.", "راجع المصاريف الإدارية والتسويقية كنسبة من الإيراد وحدد أكبر 10 بنود تضغط التشغيل.", "Operating Margin و Admin % و S&M %", 95 if om < 0 else 75)
        elif gm <= 0.30 and om < 0:
            add("نموذج العمل", "المشكلة تبدأ من اقتصاد الخدمة أو المنتج، وليس من المصاريف الإدارية فقط.", f"Gross Margin {_pct(gm)} و Operating Margin {_pct(om)}", "خطر", "تكلفة الإيراد عالية أو التسعير ضعيف أو هناك خدمات/منتجات بهامش منخفض.", "خفض المصاريف الإدارية وحده لن يعالج الخسارة إذا بقي الهامش الإجمالي ضعيفًا.", "ابدأ بتسعير الباقات/الخدمات أو تكلفة الصنف/الخدمة قبل التوسع.", "Gross Margin by service/product", 100)

    if nm is not None and nm < 0:
        add("الربحية النهائية", "الشركة خاسرة خلال الفترة بعد تحميل كل التكاليف.", f"Net Margin {_pct(nm)}", "خطر", "الخسارة قد تكون نتيجة ضعف الهامش، تضخم المصاريف، أو بنود غير متكررة.", "استمرار الخسارة يضغط النقد ورأس المال العامل ويقلل قدرة الشركة على النمو الآمن.", "حوّل قائمة الدخل إلى خطة: تكلفة الإيراد أولًا، ثم الإدارة والتسويق، ثم البنود غير المتكررة.", "Net Margin و Break-even Gap", 90)

    if admin is not None and admin > 0.25:
        add("المصاريف", "المصاريف الإدارية تستهلك نسبة مرتفعة من الإيراد.", f"Admin Expenses / Revenue {_pct(admin)}", "خطر", "هيكل إداري ثقيل أو مصاريف عامة لا ترتبط مباشرة بنمو الإيرادات.", "حتى لو تحسن الهامش، قد لا يظهر أثره على صافي الربح بسبب عبء الإدارة.", "رتّب أكبر بنود الإدارة حسب المبلغ، وحدد ما يمكن تأجيله أو التفاوض عليه أو ربطه بمؤشر أداء.", "Admin % of Revenue", 82)

    if sm is not None and sm > 0.25:
        add("النمو", "تكلفة البيع والتسويق مرتفعة وتحتاج ربطها بنتائج فعلية.", f"S&M / Revenue {_pct(sm)}", "متوسط", "حملات أو عمولات أو تكلفة مبيعات غير مرتبطة بوضوح بعائد قابل للقياس.", "قد ترتفع المبيعات ظاهريًا بينما يتآكل الهامش بسبب تكلفة النمو.", "اربط مصاريف التسويق والعملاء الجدد وصافي الإيراد، ولا توسع الإنفاق قبل معرفة العائد.", "S&M % و Revenue Growth", 70)

    if cr is not None and cashr is not None and cr >= 1.2 and cashr < 0.2:
        add("السيولة", "السيولة المحاسبية أفضل من السيولة النقدية الفعلية.", f"Current Ratio {_ratio(cr)} مقابل Cash Ratio {_ratio(cashr)}", "متوسط", "جزء من الأصول المتداولة موجود في العملاء أو المخزون وليس نقدًا جاهزًا.", "قد تبدو الشركة آمنة محاسبيًا لكنها تتعرض لضغط عند موعد الرواتب أو الموردين.", "اقرأ Current Ratio مع DSO وأعمار العملاء، ولا تعتمد عليه وحده للحكم على السيولة.", "Cash Ratio و DSO و Cash Runway", 78)

    if runway is not None and runway < 1:
        add("النقد", "النقد الحالي لا يغطي شهرًا كاملًا من الخروج النقدي.", f"Cash Runway {_months(runway)}", "خطر", "الخروج النقدي الشهري أعلى من الرصيد المتاح أو التحصيل لا يعود بسرعة كافية.", "قد تظهر حاجة تمويل أو تأجيل مدفوعات خلال 30 يومًا إذا لم يتحسن التحصيل.", "ابنِ خطة تحصيل أسبوعية وربطها بأكبر أرصدة العملاء، وراجع المدفوعات غير الحرجة.", "Cash Balance و Runway", 96)

    if dso is not None and dso > 60:
        add("التحصيل", "المبيعات تتحول إلى نقد ببطء.", f"DSO {_days(dso)}", "خطر", "شروط دفع طويلة أو ضعف متابعة التحصيل أو تركّز الذمم عند عدد محدود من العملاء.", "الشركة تموّل العملاء من نقدها، ما يضغط الرواتب والموردين حتى لو كانت المبيعات جيدة.", "ابدأ بأكبر العملاء المتأخرين حسب الرصيد والعمر، وضع حدًا ائتمانيًا للعملاء المتأخرين.", "DSO و Overdue AR %", 94)

    if ccc is not None and ccc > 90:
        add("رأس المال العامل", "دورة تحويل النقد طويلة وتحبس السيولة داخل التشغيل.", f"CCC {_days(ccc)}", "خطر", "التحصيل بطيء، المخزون بطيء، أو شروط السداد للموردين لا تكفي لتعويض دورة النقد.", "كلما طالت الدورة احتاجت الشركة تمويلًا أكبر لنفس مستوى المبيعات.", "حسّن DSO أولًا، ثم راجع DIO/DPO حسب توفر البيانات.", "CCC = DSO + DIO - DPO", 86)

    if ocf is not None and ocf < 0.6:
        add("جودة الربح", "الربح لا يتحول إلى نقد بالقدر الكافي.", f"OCF / Net Income {_pct(ocf)}", "خطر", "الربح قد يكون محبوسًا في الذمم أو متأثرًا بحركات غير نقدية أو تأخر التحصيل.", "الأرباح الدفترية لا تحمي الشركة إذا لم تتحول إلى نقد تشغيلي.", "قارن صافي الربح بالتدفق النقدي التشغيلي وبأعمار العملاء قبل اعتماد التوسع.", "OCF / Net Income", 90)

    if not rows:
        add("الوضع العام", "لا تظهر إشارة خطر حادة من المؤشرات المحسوبة، لكن الحكم النهائي يحتاج متابعة الاتجاهات والسيولة.", "المؤشرات الأساسية ضمن نطاق مقبول مبدئيًا", "منخفض", "لا توجد فجوة واضحة من البيانات الحالية، أو أن بعض الملفات الناقصة تخفض عمق التشخيص.", "الخطر القادم غالبًا يظهر من التحصيل أو المصاريف أو تغير الهامش وليس من رقم واحد.", "تابع Gross Margin وOperating Margin وDSO وCash Runway شهريًا.", "Financial Health Score", 30)

    df = pd.DataFrame(rows).sort_values("الأولوية", ascending=False).reset_index(drop=True)
    return df


def build_ratio_narratives(metric_pack: dict, findings: pd.DataFrame | None = None, profile: dict | None = None) -> pd.DataFrame:
    ratios = metric_pack.get("ratios", pd.DataFrame()).copy()
    if ratios.empty:
        return ratios
    m = metric_pack.get("metrics", {})
    sector = metric_pack.get("sector_type", "general")

    def narrative_for(row):
        key = row.get("الكود")
        val = m.get(key)
        status = row.get("الحكم", "")
        result = row.get("النتيجة", "غير متاح")
        name = row.get("المؤشر", "")
        # Default professional structure.
        meaning = f"{name} بلغ {result}. هذا المؤشر يجيب عن سؤال: {row.get('سؤال الإدارة','')}."
        cause = row.get("قراءة أولية", "")
        impact = "يجب قراءة هذا المؤشر مع باقي مؤشرات الربحية والسيولة والتحصيل قبل اتخاذ قرار منفرد."
        action = "راقب المؤشر شهريًا، وقارنه بالفترة السابقة وبمعيار القطاع عند توفره."
        monitor = name

        if key == "gross_margin":
            meaning = f"هامش مجمل الربح {result} يوضح هل النشاط الأساسي يترك هامشًا كافيًا قبل المصاريف الإدارية والتسويقية."
            if sector == "saas":
                cause = "في نشاط SaaS يجب التأكد أن رواتب التشغيل والدعم والتنفيذ والاستضافة مصنفة ضمن تكلفة الإيراد عند ارتباطها بتقديم الخدمة؛ وإلا سيظهر الهامش أعلى من حقيقته."
            else:
                cause = "إذا كان الهامش ضعيفًا فالأسباب عادة ترتبط بالتسعير، تكلفة الموردين، الخصومات، المرتجعات، أو تكلفة التنفيذ المباشرة."
            impact = "ضعف هذا الهامش يعني أن المشكلة تبدأ قبل المصاريف الإدارية، وبالتالي لا يكفي خفض الإدارة وحده لمعالجة الربحية."
            action = "افصل تكلفة الإيراد حسب خدمة/صنف/عميل، وراجع الأسعار أو تكلفة تقديم الخدمة قبل التوسع."
            monitor = "Gross Margin وCOGS %"
        elif key == "operating_margin":
            meaning = f"هامش الربح التشغيلي {result} يوضح هل الشركة تحقق ربحًا بعد تكلفة الإيراد والمصاريف الإدارية والتسويقية."
            cause = "إذا كان Gross Margin جيدًا بينما هامش التشغيل ضعيفًا، فالمشكلة غالبًا في الإدارة أو التسويق أو هيكل التشغيل لا في المنتج نفسه."
            impact = "هامش التشغيل الضعيف يجعل الشركة حساسة لأي تراجع مبيعات أو تأخر تحصيل."
            action = "راجع المصاريف الإدارية والتسويقية كنسبة من الإيراد، وحدد البنود التي نمت أسرع من المبيعات."
            monitor = "Operating Margin وAdmin % وS&M %"
        elif key == "admin_ratio":
            meaning = f"المصاريف الإدارية تمثل {result} من الإيراد، وهذا يوضح حجم العبء الإداري على كل ريال مبيعات."
            cause = "ارتفاعها قد يعني توسعًا إداريًا سابقًا لنمو الإيراد، أو عقودًا ثابتة لا تتغير مع حجم المبيعات."
            impact = "كلما ارتفعت هذه النسبة تقل قدرة الشركة على تحويل الهامش الإجمالي إلى ربح تشغيلي."
            action = "رتّب أكبر بنود الإدارة، ثم صنفها إلى: ضروري، قابل للتفاوض، قابل للتأجيل، أو يحتاج إيقاف."
            monitor = "Admin Expenses / Revenue"
        elif key == "current_ratio":
            meaning = f"نسبة التداول {result} تقيس قدرة الأصول المتداولة على تغطية الالتزامات قصيرة الأجل."
            cause = "هذه النسبة قد تكون جيدة محاسبيًا لكنها لا تعني توفر النقد إذا كانت الأصول المتداولة متركزة في الذمم أو المخزون."
            impact = "الاعتماد عليها وحدها قد يخفي ضغطًا نقديًا عند حلول الرواتب أو الموردين."
            action = "اقرأها مع Quick Ratio وCash Ratio وDSO قبل الحكم على السيولة."
            monitor = "Current Ratio + Cash Ratio + DSO"
        elif key == "dso":
            meaning = f"DSO بلغ {result}، أي أن الشركة تحتاج هذه المدة تقريبًا لتحصيل مبيعاتها من العملاء."
            cause = "السبب المحتمل هو شروط دفع طويلة، ضعف متابعة التحصيل، أو تركّز الذمم عند عملاء محددين."
            impact = "كل يوم إضافي في التحصيل يعني نقدًا محبوسًا أكثر، وقد يضغط الرواتب والموردين حتى لو كانت المبيعات جيدة."
            action = "ابدأ بأكبر العملاء المتأخرين حسب الرصيد والعمر، وضع خطة تحصيل أسبوعية وحدود ائتمان للعملاء المتأخرين."
            monitor = "DSO وOverdue AR %"
        elif key == "runway":
            meaning = f"Cash Runway {result} يوضح كم شهر يغطي النقد المتاح متوسط الخروج النقدي."
            cause = "ضعف الفترة قد يكون بسبب خروج نقدي مرتفع، تحصيل بطيء، أو مدفوعات غير متكررة."
            impact = "إذا كانت الفترة أقل من شهر، فالشركة تحتاج تحركًا سريعًا في التحصيل أو المدفوعات."
            action = "راجع التحصيل المتوقع خلال 14 يومًا، وحدد المدفوعات التي يمكن تأجيلها دون الإضرار بالتشغيل."
            monitor = "Cash Balance وCash Runway"
        elif key == "ccc":
            meaning = f"دورة تحويل النقد {result} تقيس عدد الأيام التي يبقى فيها النقد محبوسًا في العملاء والمخزون بعد خصم آجال الموردين."
            cause = "طول الدورة ينتج غالبًا من DSO مرتفع، DIO مرتفع، أو DPO قصير."
            impact = "كلما طالت الدورة احتاجت الشركة تمويلًا أكبر لتشغيل نفس حجم المبيعات."
            action = "ابدأ بالمكون الأكبر من الدورة: التحصيل، المخزون، أو شروط الموردين."
            monitor = "DSO + DIO - DPO"
        elif key == "ocf_net_income":
            meaning = f"مؤشر التدفق التشغيلي إلى صافي الربح {result} يختبر جودة الأرباح: هل تتحول إلى نقد أم تبقى دفترية."
            cause = "الانخفاض قد يشير إلى تضخم الذمم، ضعف التحصيل، أو أرباح غير نقدية."
            impact = "الأرباح التي لا تتحول إلى نقد لا تكفي لحماية الرواتب والموردين والنمو."
            action = "قارن صافي الربح بتقرير السيولة وأعمار العملاء قبل اعتماد أي توسع."
            monitor = "OCF / Net Income وDSO"
        return pd.Series({
            "قراءة CFO": f"{meaning} {cause} {impact}",
            "الإجراء التنفيذي": action,
            "مؤشر المتابعة": monitor,
        })

    add = ratios.apply(narrative_for, axis=1)
    ratios = pd.concat([ratios, add], axis=1)
    ratios["أولوية العرض"] = ratios["الحكم"].apply(lambda s: _priority(str(s)))
    return ratios.sort_values(["أولوية العرض", "المجموعة"], ascending=[False, True]).reset_index(drop=True)


def build_health_score(metric_pack: dict) -> dict:
    m = metric_pack.get("metrics", {})
    sector = metric_pack.get("sector_type", "general")
    components = []

    def score_metric(key, weight):
        val = m.get(key)
        st, note = _status(key, val, sector)
        base = {"جيد": 1.0, "متوسط": 0.65, "ضعيف": 0.40, "خطر": 0.15, "إرشادي": 0.55}.get(st, 0.35)
        return {"المحور": key, "الوزن": weight, "الحكم": st, "النقاط": round(weight * base, 1), "القراءة": note}

    components.append(score_metric("gross_margin", 12))
    components.append(score_metric("operating_margin", 8))
    components.append(score_metric("net_margin", 5))
    components.append(score_metric("current_ratio", 8))
    components.append(score_metric("quick_ratio", 7))
    components.append(score_metric("cash_ratio", 5))
    components.append(score_metric("dso", 8))
    components.append(score_metric("ccc", 7))
    components.append(score_metric("debt_ratio", 8))
    components.append(score_metric("debt_to_equity", 7))
    components.append(score_metric("ocf_net_income", 10))
    components.append(score_metric("runway", 15))

    df = pd.DataFrame(components)
    total_weight = df["الوزن"].sum() or 1
    score = round(float(df["النقاط"].sum()) / total_weight * 100, 1)
    if score >= 85: label = "ممتاز"
    elif score >= 70: label = "جيد"
    elif score >= 55: label = "يحتاج متابعة"
    elif score >= 40: label = "مرتفع المخاطر"
    else: label = "خطر حرج"
    return {"score": score, "label": label, "components": df}


def build_executive_summary(metric_pack: dict, findings: pd.DataFrame, health: dict, profile: dict | None = None, use_ai: bool = False) -> dict:
    m = metric_pack.get("metrics", {})
    sector = metric_pack.get("sector_type", "general")
    dq = metric_pack.get("data_quality", {})

    gm = m.get("gross_margin")
    om = m.get("operating_margin")
    nm = m.get("net_margin")
    admin = m.get("admin_ratio")
    sm = m.get("sm_ratio")
    dso = m.get("dso")
    runway = m.get("runway")
    ccc = m.get("ccc")

    # Four core questions.
    q_profit = "نعم، لكن هامش الأمان يحتاج متابعة" if (nm is not None and nm > 0) else "لا، الشركة لا تحقق ربحًا صافيًا خلال الفترة" if nm is not None else "غير محسوم من البيانات الحالية"
    q_liquidity = "السيولة تحتاج متابعة" if (runway is None or runway < 1.5) else "السيولة مقبولة مبدئيًا"
    q_collection = "التحصيل بطيء" if (dso is not None and dso > 60) else "التحصيل مقبول مبدئيًا" if dso is not None else "لا يمكن الحكم دون أعمار العملاء أو مبيعات آجلة"
    q_safety = health.get("label", "غير محسوم")

    headline = f"الصحة المالية الحالية: {health.get('score',0):.0f}/100 — {health.get('label','غير مصنف')}."

    profit_model = (
        f"هامش الربح الإجمالي {_pct(gm)} وهامش الربح التشغيلي {_pct(om)}. "
        f"هذه القراءة تفصل بين اقتصاد العمل الأساسي وبين أثر المصاريف الإدارية والتسويقية. "
        f"إذا كان الهامش الإجمالي ضعيفًا فالمشكلة تبدأ من التسعير أو تكلفة تقديم الخدمة؛ أما إذا كان الهامش الإجمالي مقبولًا وهامش التشغيل ضعيفًا فالمشكلة غالبًا بعد التشغيل المباشر، في الإدارة أو التسويق أو بنية التكاليف."
    )
    expense_line = (
        f"المصاريف الإدارية تمثل {_pct(admin)} من الإيراد، ومصاريف البيع والتسويق تمثل {_pct(sm)}. "
        "هذه النسب يجب قراءتها مع نمو الإيراد: إذا كانت المصاريف تنمو أسرع من المبيعات فالخطر ليس في رقم المصروف فقط، بل في تضخم الهيكل قبل نضج الإيراد."
    )
    liquidity_line = (
        f"من ناحية السيولة، Cash Runway يساوي {_months(runway)}، وDSO يساوي {_days(dso)}، وCCC يساوي {_days(ccc)}. "
        "الحكم على السيولة لا يعتمد على النقد وحده؛ بل على سرعة تحصيل العملاء وشروط الموردين وحجم رأس المال العامل المحبوس داخل التشغيل."
    )
    data_line = "درجة الثقة أعلى عند توفر ميزان مراجعة، تقرير سيولة، أعمار عملاء وموردين، ومبيعات تفصيلية. "
    if not dq.get("cash_available"):
        data_line += "تقرير السيولة غير متاح أو غير مكتمل، لذلك قراءة النقد يجب أن تبقى محافظة. "
    if not dq.get("ar_available"):
        data_line += "أعمار العملاء غير متاحة، لذلك قراءة DSO والتحصيل قد تعتمد على ميزان المراجعة فقط. "

    top = findings.head(3).to_dict("records") if isinstance(findings, pd.DataFrame) and not findings.empty else []
    top_action = top[0]["الإجراء المقترح"] if top else "تابع المؤشرات التنفيذية شهريًا وقارنها بالفترة السابقة."

    summary = {
        "headline": headline,
        "diagnosis": profit_model,
        "liquidity": liquidity_line,
        "action": top_action,
        "profit_model": profit_model,
        "expense_structure": expense_line,
        "data_confidence": data_line,
        "four_questions": {
            "هل الشركة تربح فعلاً؟": q_profit,
            "هل السيولة كافية؟": q_liquidity,
            "هل العملاء يدفعون بالسرعة المطلوبة؟": q_collection,
            "هل الشركة آمنة للاستمرار والنمو؟": q_safety,
        },
        "top_findings": top,
    }

    ai_text = _try_ai_summary(metric_pack, findings, health, profile, summary) if use_ai else None
    if ai_text:
        summary["ai_summary"] = ai_text
    return summary


def _try_ai_summary(metric_pack, findings, health, profile, fallback_summary):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        try:
            import streamlit as st
            key = st.secrets.get("OPENAI_API_KEY") or st.secrets.get("openai_api_key")
        except Exception:
            key = None
    if not key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        payload = {
            "company_context": profile or {},
            "health": {"score": health.get("score"), "label": health.get("label")},
            "metrics": {k: v for k, v in (metric_pack.get("metrics") or {}).items() if isinstance(v, (int, float)) or v is None},
            "findings": (findings.head(5).to_dict("records") if isinstance(findings, pd.DataFrame) else []),
            "rules_summary": fallback_summary,
        }
        system = """
أنت CFO عربي محترف بخبرة 10+ سنوات. لا تحسب أرقامًا جديدة. استخدم الأرقام المرسلة فقط.
اكتب ملخصًا تنفيذيًا مرنًا حسب القطاع والبيانات. يجب أن يوضح: هامش الربح الإجمالي، هامش التشغيل، السيولة، التحصيل، الخطر الأكبر، والإجراء خلال 30 يوم.
لا تكتب نصًا عامًا. كل جملة مهمة يجب أن ترتبط بمؤشر أو فجوة أو نقص بيانات.
"""
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.25,
            messages=[{"role":"system", "content": system}, {"role":"user", "content": json.dumps(payload, ensure_ascii=False)}],
        )
        return resp.choices[0].message.content
    except Exception:
        return None


def build_cfo_intelligence(metric_pack: dict, profile: dict | None = None, use_ai: bool = False) -> dict:
    findings = build_diagnostic_findings(metric_pack, profile)
    enriched = build_ratio_narratives(metric_pack, findings, profile)
    health = build_health_score(metric_pack)
    summary = build_executive_summary(metric_pack, findings, health, profile, use_ai=use_ai)
    return {
        "ratios_enriched": enriched,
        "diagnostic_findings": findings,
        "financial_health_score": health,
        "executive_summary": summary,
    }
