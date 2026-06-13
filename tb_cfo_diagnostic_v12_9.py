from __future__ import annotations

from typing import Any
import math
import re
import pandas as pd

# V13.0 note:
# This file intentionally keeps the old import name for backward compatibility,
# but the logic below is no longer built around one sample TB or a fixed
# "third sector" case. It is a generic TB-first, sector-aware diagnostic engine.

# -----------------------------------------------------------------------------
# Generic helpers
# -----------------------------------------------------------------------------
def _num(x: Any) -> float:
    try:
        if x is None or pd.isna(x):
            return 0.0
    except Exception:
        pass
    try:
        return float(x)
    except Exception:
        return 0.0


def _safe_div(a: Any, b: Any):
    a, b = _num(a), _num(b)
    if abs(b) < 1e-9:
        return None
    return a / b


def _pct(x: float | None) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "غير متاح"
    return f"{x*100:.1f}%"


def _code(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    try:
        return str(int(float(value)))
    except Exception:
        return str(value).strip().replace(".0", "")


def _norm(text: Any) -> str:
    s = "" if text is None else str(text)
    s = s.strip().lower()
    repl = {"أ":"ا", "إ":"ا", "آ":"ا", "ة":"ه", "ى":"ي", "ـ":"", "\u200f":"", "\u200e":""}
    for a, b in repl.items():
        s = s.replace(a, b)
    return s


def _contains(text: Any, keys: list[str]) -> bool:
    t = _norm(text)
    return any(_norm(k) in t for k in keys)


def prepare_tb(tb_model: dict | None) -> pd.DataFrame:
    tb = tb_model.get("tb", pd.DataFrame()) if tb_model else pd.DataFrame()
    if tb is None or tb.empty:
        return pd.DataFrame()
    out = tb.copy()
    for col in ["account_code_norm", "account_name", "current_debit", "current_credit", "begin_debit", "begin_credit", "debit", "credit"]:
        if col not in out.columns:
            out[col] = "" if col in ["account_code_norm", "account_name"] else 0.0
    out["account_code_norm"] = out["account_code_norm"].apply(_code)
    out["account_name"] = out["account_name"].astype(str)
    for col in ["current_debit", "current_credit", "begin_debit", "begin_credit", "debit", "credit"]:
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)
    out["closing_debit_net"] = out["current_debit"] - out["current_credit"]
    out["movement_debit_net"] = out["debit"] - out["credit"]
    return out


def is_parent_code(code: str, all_codes: list[str]) -> bool:
    code = str(code or "")
    if not code:
        return False
    return any(str(other) != code and str(other).startswith(code) and len(str(other)) > len(code) for other in all_codes)


def leaf_rows(tb: pd.DataFrame) -> pd.DataFrame:
    if tb.empty:
        return tb.copy()
    all_codes = tb["account_code_norm"].astype(str).tolist()
    return tb[~tb["account_code_norm"].astype(str).apply(lambda c: is_parent_code(c, all_codes))].copy()


def _row_amount(row: pd.Series, natural: str = "debit", basis: str = "movement", signed: bool = False) -> float:
    if basis == "closing":
        val = _num(row.get("current_debit")) - _num(row.get("current_credit"))
    else:
        # Income statement accounts should use movement; fallback to closing if no movement.
        if abs(_num(row.get("debit"))) + abs(_num(row.get("credit"))) > 0:
            val = _num(row.get("debit")) - _num(row.get("credit"))
        else:
            val = _num(row.get("current_debit")) - _num(row.get("current_credit"))
    if natural == "credit":
        val = -val
    return val if signed else max(0.0, val)


def _sum_leaf_prefix(tb: pd.DataFrame, prefixes: list[str], natural: str = "debit", basis: str = "movement") -> float:
    if tb.empty:
        return 0.0
    lf = leaf_rows(tb)
    mask = pd.Series(False, index=lf.index)
    for p in prefixes:
        mask |= lf["account_code_norm"].astype(str).str.startswith(str(p), na=False)
    if not mask.any():
        return 0.0
    return float(lf.loc[mask].apply(lambda r: _row_amount(r, natural=natural, basis=basis), axis=1).sum())


def _sum_leaf_names(tb: pd.DataFrame, keys: list[str], natural: str = "debit", basis: str = "closing", exclude_prefixes: list[str] | None = None) -> float:
    if tb.empty:
        return 0.0
    lf = leaf_rows(tb)
    mask = lf["account_name"].apply(lambda x: _contains(x, keys))
    if exclude_prefixes:
        for p in exclude_prefixes:
            mask &= ~lf["account_code_norm"].astype(str).str.startswith(str(p), na=False)
    if not mask.any():
        return 0.0
    return float(lf.loc[mask].apply(lambda r: _row_amount(r, natural=natural, basis=basis), axis=1).sum())


# -----------------------------------------------------------------------------
# Sector + activity inference
# -----------------------------------------------------------------------------
def infer_activity_profile(tb_model: dict | None, profile: dict | None = None) -> dict:
    tb = prepare_tb(tb_model)
    profile = profile or {}
    text = " ".join(tb.get("account_name", pd.Series(dtype=str)).astype(str).tolist()) if not tb.empty else ""
    ctx = _norm(" ".join([str(profile.get(k, "")) for k in ["sector", "activity", "business_model", "sales_channel"]]) + " " + text)
    evidence: list[str] = []
    inferred = "general"
    if any(k in ctx for k in ["مبرمج", "برمج", "دعم فني", "اشتراك", "تجديد", "erp", "hr", "تقنيه", "تقنية", "منصه", "منصة", "saas"]):
        inferred = "software_saas"
        evidence.append("الحسابات تشير إلى برمجيات/اشتراكات/دعم فني، لذلك يجب تصنيف تكلفة تقديم الخدمة بعناية لا كمصاريف إدارية فقط.")
    if any(k in ctx for k in ["مطعم", "مقهى", "مقاهي", "وجبات", "غذائي", "صالة", "توصيل"]):
        inferred = "restaurant" if inferred == "general" else inferred
        evidence.append("توجد مؤشرات مطاعم/توصيل؛ تكلفة المواد والعمالة والتطبيقات تصبح مؤشرات أساسية عند توفرها.")
    if any(k in ctx for k in ["مقاول", "مستخلص", "احتجاز", "اعمال تحت التنفيذ", "مشروع تحت التنفيذ"]):
        inferred = "contracting" if inferred == "general" else inferred
        evidence.append("توجد مؤشرات مشاريع/مقاولات؛ التحليل يجب أن يقرأ هامش المشروع والمستخلصات والاحتجازات عند توفرها.")
    if any(k in ctx for k in ["مخزون", "بضاعه", "بضاعة", "جمله", "جملة", "تجزئه", "تجزئة", "retail", "wholesale"]):
        inferred = "trading" if inferred == "general" else inferred
        evidence.append("توجد مؤشرات تجارة/مخزون؛ دوران المخزون وجودة الهامش تصبح مهمة عند توفر المخزون.")

    selected = str(profile.get("sector", "") or "")
    selected_n = _norm(selected)
    mismatch = bool(selected and inferred != "general" and selected_n in ["تجاري", "تجاره", "تجارة", "عام", "خدمات عامه", "خدمات عامة"])

    streams = detect_activity_streams(tb, profile)
    material_streams = [s for s in streams.get("stream_names", []) if s != "النشاط العام"]
    if material_streams:
        evidence.append("تم اكتشاف أكثر من مسار نشاط/قناة/مشروع داخل الحسابات. يجب عرض الفصل كقراءة مقترحة قابلة للتأكيد لا كحقيقة جامدة.")

    return {
        "selected_sector": selected,
        "inferred_sector": inferred,
        "sector_mismatch": mismatch,
        "stream_names": streams.get("stream_names", []),
        "material_streams": material_streams,
        "has_third_sector": any("قطاع ثالث" in _norm(x) or "جمع" in _norm(x) for x in material_streams),
        "evidence": evidence,
    }


def _sector_type(profile: dict | None) -> str:
    p = profile or {}
    text = _norm(" ".join([str(p.get(k, "")) for k in ["sector", "activity", "business_model", "sales_channel"]]))
    if any(k in text for k in ["saas", "برمج", "تقنيه", "تقنية", "اشتراك", "منصه", "منصة"]):
        return "software_saas"
    if any(k in text for k in ["مطعم", "مقهى", "مقاهي"]):
        return "restaurant"
    if any(k in text for k in ["مقاول", "مشروع"]):
        return "contracting"
    if any(k in text for k in ["تجارة", "تجاري", "جمله", "جملة", "تجزئه", "تجزئة"]):
        return "trading"
    if any(k in text for k in ["صناعه", "صناعة", "مصنع"]):
        return "manufacturing"
    if any(k in text for k in ["تاجير", "تأجير", "ايجار اصول", "اسطول"]):
        return "rental"
    if any(k in text for k in ["صحي", "طبي", "عياده", "عيادة"]):
        return "healthcare"
    return "general"


# -----------------------------------------------------------------------------
# Business stream detector: generic, not tied to one sample file
# -----------------------------------------------------------------------------
def _stream_label_from_name(name: Any) -> str:
    t = _norm(name)
    # Special labels are examples of activity streams, not fixed business rules.
    if "قطاع ثالث" in t or "جمعيه" in t or "جمعيات" in t or "جمعية" in str(name):
        return "قطاع/جمعيات"
    if "الفروع" in t:
        return "النشاط الأساسي"
    if "فرع" in t:
        # Keep generic branch label to avoid creating noisy branch names; users can confirm branch-level analysis later.
        return "فروع"
    if "مشروع" in t or "مستخلص" in t or "احتجاز" in t:
        return "مشاريع"
    if "صاله" in t or "صالة" in str(name):
        return "صالة"
    if "توصيل" in t or "delivery" in t:
        return "توصيل"
    if "جمله" in t or "جملة" in str(name):
        return "جملة"
    if "تجزئه" in t or "تجزئة" in str(name):
        return "تجزئة"
    # For subscription/software businesses, these are usually one core business stream unless the user confirms otherwise.
    if any(k in t for k in ["اشتراك", "تجديد", "انظمه", "انظمة", "نظام", "تنفيذ", "تشغيل", "تشغيليه", "تشغيلية", "دعم", "مبرمج", "برمج", "سمارت"]):
        return "النشاط الأساسي"
    if "صيانة" in str(name) or "صيانه" in t:
        return "صيانة"
    return "النشاط العام"


def detect_activity_streams(tb: pd.DataFrame, profile: dict | None = None) -> dict:
    if tb is None or tb.empty:
        return {"stream_names": [], "confidence": "غير متاحة", "note": "لا توجد حسابات للقراءة."}
    lf = leaf_rows(tb).copy()
    lf["stream"] = lf["account_name"].apply(_stream_label_from_name)
    # Materiality by revenue/cost/expense movement.
    rev_mask = lf["account_code_norm"].astype(str).str.startswith("4", na=False)
    cost_mask = lf["account_code_norm"].astype(str).str.startswith(("3", "5"), na=False)
    relevant = lf[rev_mask | cost_mask].copy()
    names = sorted([x for x in relevant["stream"].dropna().unique().tolist() if x])
    non_general = [x for x in names if x != "النشاط العام"]
    confidence = "مرتفعة" if len(non_general) >= 1 else "متوسطة"
    note = "تم اكتشاف مسارات من أسماء الحسابات، ويجب اعتبارها مقترح فصل قابل للتأكيد." if non_general else "لم تظهر مسارات نشاط واضحة خارج النشاط العام."
    return {"stream_names": names, "confidence": confidence, "note": note}


# -----------------------------------------------------------------------------
# Revenue quality from TB
# -----------------------------------------------------------------------------
def build_revenue_quality_from_tb(tb_model: dict | None) -> dict:
    tb = prepare_tb(tb_model)
    if tb.empty:
        return {"available": False, "cards": {}, "table": pd.DataFrame(), "narrative": "لا يوجد ميزان مراجعة صالح لقراءة جودة الإيراد."}
    gross_sales = _sum_leaf_prefix(tb, ["401"], natural="credit", basis="movement")
    returns = _sum_leaf_prefix(tb, ["402"], natural="debit", basis="movement")
    discounts = _sum_leaf_prefix(tb, ["403"], natural="debit", basis="movement")
    if gross_sales == 0:
        gross_sales = _sum_leaf_names(tb, ["مبيعات", "sales"], natural="credit", basis="movement", exclude_prefixes=["402", "403"])
    if returns == 0:
        returns = _sum_leaf_names(tb, ["مردود", "مرتجع", "returns"], natural="debit", basis="movement")
    if discounts == 0:
        discounts = _sum_leaf_names(tb, ["خصم ممنوح", "خصومات", "discount"], natural="debit", basis="movement")
    net_sales = gross_sales - returns - discounts
    leakage = returns + discounts
    leakage_ratio = _safe_div(leakage, gross_sales)
    other_revenue = _sum_leaf_prefix(tb, ["6"], natural="credit", basis="movement")
    rows = [
        ["إجمالي المبيعات قبل الخصومات والمردودات", gross_sales, "حسابات المبيعات من ميزان المراجعة"],
        ["مردودات المبيعات", returns, "حسابات مردودات المبيعات"],
        ["الخصومات الممنوحة", discounts, "حسابات الخصومات الممنوحة"],
        ["تآكل الإيراد", leakage, "الخصومات + المردودات"],
        ["صافي المبيعات", net_sales, "إجمالي المبيعات - المردودات - الخصومات"],
        ["إيرادات أخرى", other_revenue, "حسابات الإيرادات الأخرى إن وجدت"],
    ]
    table = pd.DataFrame(rows, columns=["البند", "القيمة", "المصدر"])
    if gross_sales <= 0:
        narrative = "لم تُقرأ مبيعات إجمالية من ميزان المراجعة، لذلك لا يمكن حساب جودة الإيراد من الخصومات والمردودات."
    elif leakage_ratio is not None and leakage_ratio >= .20:
        narrative = f"تآكل الإيراد يبلغ {_pct(leakage_ratio)} من إجمالي المبيعات؛ هذا خطر لأن رقم المبيعات الخام لا يعكس صافي القيمة التي بقيت للشركة."
    elif leakage_ratio is not None and leakage_ratio >= .10:
        narrative = f"تآكل الإيراد يبلغ {_pct(leakage_ratio)}؛ يحتاج متابعة حسب القطاع وسياسة الخصومات والمرتجعات."
    else:
        narrative = f"تآكل الإيراد يبلغ {_pct(leakage_ratio)}؛ لا يظهر كخطر رئيسي من الميزان وحده."
    return {
        "available": gross_sales > 0,
        "gross_sales": gross_sales,
        "returns": returns,
        "discounts": discounts,
        "revenue_leakage": leakage,
        "leakage_ratio": leakage_ratio,
        "net_sales": net_sales,
        "other_revenue": other_revenue,
        "cards": {"gross_sales": gross_sales, "returns": returns, "discounts": discounts, "net_sales": net_sales, "leakage_ratio": leakage_ratio},
        "table": table,
        "narrative": narrative,
    }


# -----------------------------------------------------------------------------
# Sector-aware cost classification
# -----------------------------------------------------------------------------
def _classify_expense_function(code: str, name: str, profile: dict | None = None) -> str:
    t = _norm(name)
    sector = _sector_type(profile)
    code = str(code or "")
    if code.startswith("3"):
        return "cost_of_revenue"
    if code.startswith("4"):
        return "revenue"
    if code.startswith("6"):
        return "other_revenue"

    # Direct service/product/project cost - sector aware and account-name aware.
    direct_keys = [
        "تكلفة", "مشتريات", "مواد", "بضاعه", "بضاعة", "تشغيل", "دعم فني", "تنفيذ", "مبرمج", "فني", "عمال", "انتاج", "إنتاج", "مشروع", "قطاع", "جمعيه", "جمعية", "حمله", "حملة", "صيانة", "صيانه", "استضافه", "استضافة", "خادم", "سيرفر", "توصيل", "شحن", "طهاه", "طهاة", "اطباء", "أطباء", "طبيب", "دواء", "ادوية", "أدوية", "مستلزمات", "وقود", "قطع غيار"
    ]
    if any(k in t for k in [_norm(x) for x in direct_keys]):
        return "cost_of_revenue"
    # Some account structures put direct operations in 50101 and special projects in 502, but this is a fallback, not the main rule.
    if code.startswith("50101") or code.startswith("502"):
        return "cost_of_revenue"

    sm_keys = ["بيع", "مبيعات", "تسويق", "دعايه", "دعاية", "اعلان", "إعلان", "اعلانات", "حمله تسويقيه", "عموله مبيعات", "عمولة مبيعات", "مندوب", "اكتساب", "commission", "marketing"]
    if any(_norm(k) in t for k in sm_keys) or code.startswith("50103"):
        return "selling_marketing"

    finance_keys = ["بنك", "بنكي", "رسوم", "عموله بنكيه", "عمولة بنكية", "فوائد", "تمويل", "بوابه دفع", "بوابة دفع", "مدى", "فيزا", "تامارا", "تابي"]
    if any(_norm(k) in t for k in finance_keys):
        return "finance_payment"

    tax_keys = ["زكاه", "زكاة", "ضريبه", "ضريبة", "vat", "tax"]
    if any(_norm(k) in t for k in tax_keys):
        return "tax_zakat"

    # Default operating/admin. This should be reviewable by the user.
    return "admin_opex"


def _leaf_income_expense_rows(tb: pd.DataFrame, profile: dict | None = None) -> pd.DataFrame:
    lf = leaf_rows(tb).copy()
    lf["amount_debit"] = lf.apply(lambda r: _row_amount(r, natural="debit", basis="movement"), axis=1)
    lf["amount_credit"] = lf.apply(lambda r: _row_amount(r, natural="credit", basis="movement"), axis=1)
    lf["stream"] = lf["account_name"].apply(_stream_label_from_name)
    lf["function"] = lf.apply(lambda r: _classify_expense_function(r.get("account_code_norm"), r.get("account_name"), profile), axis=1)
    return lf


def build_segment_pnl_from_tb(tb_model: dict | None, profile: dict | None = None) -> dict:
    """Builds a generic management P&L and optional segment stream P&L.

    It does not hard-code one company's pattern. Segments are detected from account names
    as branches/projects/channels/services/activity streams and shown as suggested analytical splits.
    """
    tb = prepare_tb(tb_model)
    if tb.empty:
        return {"available": False, "table": pd.DataFrame(), "metrics": {}, "warnings": []}

    revq = build_revenue_quality_from_tb(tb_model)
    lf = _leaf_income_expense_rows(tb, profile)

    # Revenue by stream.
    # Prefer account-code families when they exist. Name fallback is used only when the TB has no codes.
    codes = lf["account_code_norm"].astype(str)
    has_401 = codes.str.startswith("401", na=False).any()
    has_402 = codes.str.startswith("402", na=False).any()
    has_403 = codes.str.startswith("403", na=False).any()
    sales_mask = codes.str.startswith("401", na=False) if has_401 else lf["account_name"].apply(lambda x: _contains(x, ["مبيعات", "sales"]) and not _contains(x, ["مردود", "مرتجع", "خصم"]))
    returns_mask = codes.str.startswith("402", na=False) if has_402 else lf["account_name"].apply(lambda x: _contains(x, ["مردود", "مرتجع", "returns"]))
    discounts_mask = codes.str.startswith("403", na=False) if has_403 else lf["account_name"].apply(lambda x: _contains(x, ["خصم ممنوح", "خصومات", "discount"]))
    expense_mask = codes.str.startswith("5", na=False) | codes.str.startswith("3", na=False)

    gross_sales = float(lf.loc[sales_mask].apply(lambda r: _row_amount(r, natural="credit", basis="movement"), axis=1).sum())
    returns = float(lf.loc[returns_mask].apply(lambda r: _row_amount(r, natural="debit", basis="movement"), axis=1).sum())
    discounts = float(lf.loc[discounts_mask].apply(lambda r: _row_amount(r, natural="debit", basis="movement"), axis=1).sum())
    net_sales = gross_sales - returns - discounts
    other_revenue = _sum_leaf_prefix(tb, ["6"], natural="credit", basis="movement")
    total_revenue = net_sales + other_revenue

    # Cost/function totals.
    cost_of_revenue = float(lf.loc[expense_mask & lf["function"].eq("cost_of_revenue")].apply(lambda r: _row_amount(r, natural="debit", basis="movement"), axis=1).sum())
    admin = float(lf.loc[expense_mask & lf["function"].eq("admin_opex")].apply(lambda r: _row_amount(r, natural="debit", basis="movement"), axis=1).sum())
    selling = float(lf.loc[expense_mask & lf["function"].eq("selling_marketing")].apply(lambda r: _row_amount(r, natural="debit", basis="movement"), axis=1).sum())
    finance = float(lf.loc[expense_mask & lf["function"].eq("finance_payment")].apply(lambda r: _row_amount(r, natural="debit", basis="movement"), axis=1).sum())
    tax_zakat = float(lf.loc[expense_mask & lf["function"].eq("tax_zakat")].apply(lambda r: _row_amount(r, natural="debit", basis="movement"), axis=1).sum())
    all_expenses = float(lf.loc[expense_mask].apply(lambda r: _row_amount(r, natural="debit", basis="movement"), axis=1).sum())
    other_opex = max(0.0, all_expenses - cost_of_revenue - admin - selling - finance - tax_zakat)

    gross_profit = total_revenue - cost_of_revenue
    operating_profit = gross_profit - admin - selling - other_opex
    official_net_profit = total_revenue - all_expenses

    # Build stream table.
    streams = sorted(set(lf.get("stream", pd.Series(dtype=str)).fillna("النشاط العام").tolist()))
    seg_rows = []
    for stream in streams:
        smask = lf["stream"].eq(stream)
        s_gross = float(lf.loc[smask & sales_mask].apply(lambda r: _row_amount(r, natural="credit", basis="movement"), axis=1).sum())
        s_returns = float(lf.loc[smask & returns_mask].apply(lambda r: _row_amount(r, natural="debit", basis="movement"), axis=1).sum())
        s_discounts = float(lf.loc[smask & discounts_mask].apply(lambda r: _row_amount(r, natural="debit", basis="movement"), axis=1).sum())
        s_net = s_gross - s_returns - s_discounts
        s_cost = float(lf.loc[smask & expense_mask & lf["function"].eq("cost_of_revenue")].apply(lambda r: _row_amount(r, natural="debit", basis="movement"), axis=1).sum())
        material = max(abs(s_net), abs(s_cost))
        if material > max(total_revenue * 0.03, 1):
            seg_rows.append([stream, s_gross, s_returns + s_discounts, s_net, s_cost, s_net - s_cost, _safe_div(s_net - s_cost, s_net), "مقترح آلي من أسماء الحسابات"])
    if not seg_rows:
        seg_rows = [["النشاط العام", gross_sales, returns + discounts, net_sales, cost_of_revenue, net_sales - cost_of_revenue, _safe_div(net_sales - cost_of_revenue, net_sales), "لم تظهر مسارات فرعية جوهرية"]]
    segment_table = pd.DataFrame(seg_rows, columns=["المسار", "إجمالي المبيعات", "خصومات ومردودات", "صافي الإيراد", "التكلفة المباشرة", "النتيجة قبل الإدارة", "الهامش", "درجة الاعتماد"])

    rows = [
        ["إجمالي المبيعات", gross_sales, "قبل الخصومات والمردودات"],
        ["تآكل الإيراد: مردودات وخصومات", -returns - discounts, f"{_pct(_safe_div(returns + discounts, gross_sales))} من إجمالي المبيعات"],
        ["صافي المبيعات", net_sales, "بعد الخصومات والمردودات"],
        ["إيرادات أخرى", other_revenue, "ليست من النشاط الرئيسي غالبًا"],
        ["تكلفة الإيراد / تقديم الخدمة", -cost_of_revenue, "مشتريات + تكلفة مباشرة + تشغيل/دعم/مشروع/قطاع حسب طبيعة الحساب"],
        ["مجمل الربح الإداري", gross_profit, "بعد تكلفة الإيراد المقروءة بعمق من الحسابات"],
        ["المصاريف الإدارية", -admin, "إدارة وعمومية وبنود مشتركة"],
        ["البيع والتسويق", -selling, "مصاريف مبيعات وتسويق وعمولات"],
        ["تمويل/بوابات دفع/رسوم بنكية", -finance, "يعرض منفصلًا حتى لا يشوه الإدارة أو تكلفة الإيراد"],
        ["مصروفات أخرى بحاجة مراجعة", -other_opex, "بنود لم تُصنف بثقة كافية"],
        ["صافي الربح/الخسارة", official_net_profit, "صافي نتيجة الفترة من ميزان المراجعة بعد العرض الإداري"],
    ]
    table = pd.DataFrame(rows, columns=["البند", "القيمة", "القراءة"])

    warnings: list[str] = []
    leakage_ratio = _safe_div(returns + discounts, gross_sales)
    if leakage_ratio is not None and leakage_ratio >= .20:
        warnings.append("تآكل الإيراد مرتفع؛ يجب تحليل الخصومات والمردودات قبل اعتبار المبيعات نموًا صحيًا.")
    # material zero-margin or pass-through stream.
    for _, r in segment_table.iterrows():
        net = _num(r.get("صافي الإيراد")); cost = _num(r.get("التكلفة المباشرة")); result = _num(r.get("النتيجة قبل الإدارة"))
        if net > total_revenue * .15 and cost > 0 and abs(result) / max(net, 1) < .03:
            warnings.append(f"المسار '{r.get('المسار')}' جوهري وحركته شبه متعادلة؛ تحقق هل يسجل Gross أم Net وهل الشركة Principal أم Agent أو وسيط.")
    if total_revenue > 0 and official_net_profit < 0 and gross_profit > 0:
        warnings.append("النشاط يترك هامشًا قبل الإدارة، لكن المصاريف التالية تستهلك الهامش وينتج عنها خسارة صافية.")
    if len([r for _, r in segment_table.iterrows() if r.get("المسار") != "النشاط العام"]) > 0:
        warnings.append("فصل المسارات مقترح آلي من أسماء الحسابات؛ يجب عرضه للمستخدم للتأكيد أو الدمج أو إعادة التسمية قبل اعتماده نهائيًا.")

    metrics = {
        "revenue": total_revenue,
        "net_sales": net_sales,
        "gross_sales": gross_sales,
        "returns": returns,
        "discounts": discounts,
        "revenue_leakage": returns + discounts,
        "leakage_ratio": leakage_ratio,
        "cost_of_revenue": cost_of_revenue,
        "gross_profit": gross_profit,
        "gross_margin": _safe_div(gross_profit, total_revenue),
        "admin": admin,
        "selling_marketing": selling,
        "finance_payment": finance,
        "tax_zakat": tax_zakat,
        "other_opex": other_opex,
        "all_expenses": all_expenses,
        "admin_ratio": _safe_div(admin, total_revenue),
        "sm_ratio": _safe_div(selling, total_revenue),
        "finance_ratio": _safe_div(finance, total_revenue),
        "cogs_ratio": _safe_div(cost_of_revenue, total_revenue),
        "official_net_profit": official_net_profit,
        "net_margin": _safe_div(official_net_profit, total_revenue),
        "operating_margin": _safe_div(operating_profit, total_revenue),
        "operating_profit": operating_profit,
        "classification_confidence": "متوسطة" if other_opex > total_revenue * .05 else "مرتفعة",
        "stream_count": len(segment_table),
    }
    return {
        "available": total_revenue > 0 or all_expenses > 0,
        "table": table,
        "segment_table": segment_table,
        "metrics": metrics,
        "warnings": warnings,
        "revenue_quality": revq,
        "stream_detector": detect_activity_streams(tb, profile),
    }


# -----------------------------------------------------------------------------
# Balance flags
# -----------------------------------------------------------------------------
def build_balance_quality_flags(tb_model: dict | None) -> dict:
    tb = prepare_tb(tb_model)
    if tb.empty:
        return {"flags": [], "metrics": {}}
    total_assets = _sum_leaf_prefix(tb, ["1"], natural="debit", basis="closing")
    parent_assets = tb[tb["account_code_norm"].eq("1")]
    if not parent_assets.empty:
        total_assets = max(total_assets, _row_amount(parent_assets.iloc[0], natural="debit", basis="closing"))
    rnd_assets = _sum_leaf_prefix(tb, ["10108"], natural="debit", basis="closing")
    rnd_ratio = _safe_div(rnd_assets, total_assets)

    # Signed customer account check: parent and leaf balances.
    cust_rows = tb[tb["account_name"].apply(lambda x: _contains(x, ["عميل", "عملاء", "ذمم مدينة", "receivable"]))].copy()
    customer_credit_balance = 0.0
    if not cust_rows.empty:
        parent = cust_rows[cust_rows["account_code_norm"].astype(str).str.startswith("10202", na=False)]
        if not parent.empty:
            signed = float((parent["current_debit"] - parent["current_credit"]).sum())
            if signed < 0:
                customer_credit_balance = abs(signed)
        else:
            signed = float((leaf_rows(cust_rows)["current_debit"] - leaf_rows(cust_rows)["current_credit"]).sum())
            if signed < 0:
                customer_credit_balance = abs(signed)
    flags: list[str] = []
    if rnd_ratio is not None and rnd_ratio >= .50:
        flags.append(f"مشاريع البحث والتطوير/الأصول المطورة تمثل {_pct(rnd_ratio)} من الأصول؛ يجب اختبار المنفعة المستقبلية والإطفاء/الهبوط قبل الاعتماد على قوة المركز المالي.")
    if customer_credit_balance > 0:
        flags.append("حساب العملاء يظهر دائنًا أو غير طبيعي؛ لا يجوز حساب DSO كذمم مدينة عادية قبل رفع تقرير العملاء أو أعمار الديون.")
    return {"flags": flags, "metrics": {"total_assets": total_assets, "rnd_assets": rnd_assets, "rnd_asset_ratio": rnd_ratio, "customer_credit_balance": customer_credit_balance}}
