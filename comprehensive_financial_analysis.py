from __future__ import annotations

import math
import re
from typing import Any

import pandas as pd

from financial_intelligence_v2 import build_metric_pack, build_cfo_intelligence
from tb_cfo_diagnostic_v12_9 import (
    build_segment_pnl_from_tb,
    build_revenue_quality_from_tb,
    build_balance_quality_flags,
    infer_activity_profile,
)

MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
AR_MONTHS = {"Jan":"يناير", "Feb":"فبراير", "Mar":"مارس", "Apr":"أبريل", "May":"مايو", "Jun":"يونيو", "Jul":"يوليو", "Aug":"أغسطس", "Sep":"سبتمبر", "Oct":"أكتوبر", "Nov":"نوفمبر", "Dec":"ديسمبر"}


def _num(x: Any) -> float:
    try:
        if pd.isna(x):
            return 0.0
    except Exception:
        pass
    try:
        return float(x)
    except Exception:
        return 0.0


def _safe_div(a: float, b: float) -> float | None:
    a, b = _num(a), _num(b)
    if abs(b) < 1e-9:
        return None
    return a / b


def _pct(x: float | None) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "غير متاح"
    return f"{x*100:.1f}%"


def _money(x: float | None) -> str:
    if x is None:
        return "غير متاح"
    return f"{x:,.0f}"


def _code_str(value) -> str:
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
    for a,b in repl.items():
        s = s.replace(a,b)
    return s


def _is_parent_code(code: str, all_codes: list[str]) -> bool:
    if not code:
        return False
    return any(other != code and other.startswith(code) and len(other) > len(code) for other in all_codes)


def _prepare_tb(tb_model: dict | None) -> pd.DataFrame:
    tb = tb_model.get("tb", pd.DataFrame()) if tb_model else pd.DataFrame()
    if tb is None or tb.empty:
        return pd.DataFrame()
    out = tb.copy()
    for col in ["account_code_norm", "account_name", "current_debit", "current_credit", "begin_debit", "begin_credit", "debit", "credit"]:
        if col not in out.columns:
            out[col] = "" if col in ["account_code_norm", "account_name"] else 0.0
    out["account_code_norm"] = out["account_code_norm"].apply(_code_str)
    for col in ["current_debit", "current_credit", "begin_debit", "begin_credit", "debit", "credit"]:
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)
    out["closing_net_debit"] = out["current_debit"] - out["current_credit"]
    out["beginning_net_debit"] = out["begin_debit"] - out["begin_credit"]
    out["closing_abs"] = out["closing_net_debit"].abs()
    return out


def _row_by_code(tb: pd.DataFrame, code: str) -> pd.Series | None:
    if tb.empty:
        return None
    mask = tb["account_code_norm"].eq(code)
    if mask.any():
        return tb.loc[mask].iloc[0]
    return None


def _amount_by_code(tb: pd.DataFrame, code: str, natural: str = "debit", absolute: bool = True) -> float:
    row = _row_by_code(tb, code)
    if row is None:
        return 0.0
    val = _num(row.get("current_debit")) - _num(row.get("current_credit"))
    if natural == "credit":
        val = -val
    return abs(val) if absolute else val


def _sum_leaf_by_prefix(tb: pd.DataFrame, prefixes: list[str], natural: str = "debit", name_contains: list[str] | None = None) -> float:
    if tb.empty:
        return 0.0
    mask = pd.Series(False, index=tb.index)
    for p in prefixes:
        mask |= tb["account_code_norm"].str.startswith(p, na=False)
    if name_contains:
        keys = [_norm(k) for k in name_contains]
        mask &= tb["account_name"].apply(lambda x: any(k in _norm(x) for k in keys))
    sub = tb.loc[mask].copy()
    if sub.empty:
        return 0.0
    all_codes = tb["account_code_norm"].astype(str).tolist()
    sub = sub[~sub["account_code_norm"].astype(str).apply(lambda c: _is_parent_code(c, all_codes))]
    val = float((sub["current_debit"] - sub["current_credit"]).sum())
    if natural == "credit":
        val = -val
    return abs(val)


def _sum_leaf_by_name(tb: pd.DataFrame, keys: list[str], natural: str = "debit") -> float:
    if tb.empty:
        return 0.0
    norm_keys = [_norm(k) for k in keys]
    mask = tb["account_name"].apply(lambda x: any(k in _norm(x) for k in norm_keys))
    sub = tb.loc[mask].copy()
    if sub.empty:
        return 0.0
    all_codes = tb["account_code_norm"].astype(str).tolist()
    sub = sub[~sub["account_code_norm"].astype(str).apply(lambda c: _is_parent_code(c, all_codes))]
    val = float((sub["current_debit"] - sub["current_credit"]).sum())
    if natural == "credit":
        val = -val
    return abs(val)


def _liquidity_cards(liquidity_model: dict | None) -> dict:
    if not liquidity_model:
        return {}
    cash = liquidity_model.get("cash", {}) or {}
    if not cash.get("available"):
        return {}
    return cash.get("cards", {}) or {}


def _ar_cards(liquidity_model: dict | None) -> dict:
    if not liquidity_model:
        return {}
    ar = liquidity_model.get("ar", {}) or {}
    if not ar.get("available"):
        return {}
    return ar.get("cards", {}) or {}


def _ap_cards(liquidity_model: dict | None) -> dict:
    if not liquidity_model:
        return {}
    ap = liquidity_model.get("ap", {}) or {}
    if not ap.get("available"):
        return {}
    return ap.get("cards", {}) or {}



def build_management_pnl_snapshot(pnl_model: dict, expense_model: dict | None = None, tb_model: dict | None = None, profile: dict | None = None) -> dict:
    """
    Reclassifies the official P&L into a management view.
    Net profit remains tied to the official numbers, but gross margin becomes meaningful by moving
    direct delivery/operations costs to Cost of Revenue when expense mapping says so.
    """
    # V12.9: If a Trial Balance is available, build a management P&L directly from its account hierarchy.
    # This prevents a false Gross Margin when delivery/support/third-sector costs sit in expense accounts.
    tb_deep = build_segment_pnl_from_tb(tb_model, profile) if tb_model else {"available": False}
    if tb_deep.get("available"):
        m = tb_deep.get("metrics", {}) or {}
        mgmt_table = tb_deep.get("table", pd.DataFrame())
        return {
            "revenue": _num(m.get("revenue")),
            "official_cogs": _num(m.get("purchases")),
            "direct_reclassified": _num(m.get("core_direct_ops")) + _num(m.get("third_cost")),
            "cogs": _num(m.get("cost_of_revenue")),
            "gross_profit": _num(m.get("gross_profit")),
            "opex": _num(m.get("operating_expenses")),
            "direct_operations_after_gross": _num(m.get("direct_operations_after_gross")),
            "selling_marketing": _num(m.get("selling_marketing")),
            "admin_opex": _num(m.get("admin")),
            "finance_bank": _num(m.get("finance_payment")),
            "other_opex": _num(m.get("other_opex")),
            "cogs_basis": m.get("cogs_basis"),
            "cogs_note": m.get("cogs_note"),
            "opening_inventory": _num(m.get("opening_inventory")),
            "net_purchases": _num(m.get("net_purchases")),
            "ending_inventory": _num(m.get("ending_inventory")),
            "net_profit": _num(m.get("official_net_profit")),
            "management_table": mgmt_table,
            "segment_table": tb_deep.get("segment_table", pd.DataFrame()),
            "stream_detector": tb_deep.get("stream_detector", {}),
            "revenue_quality": tb_deep.get("revenue_quality", {}),
            "warnings": tb_deep.get("warnings", []),
            "source_note": "V13.0 TB-first dynamic management P&L: يكتشف مسارات النشاط والتكلفة حسب الحسابات والقطاع، ولا يعتمد على نمط ملف واحد.",
        }

    revenue = _num(pnl_model.get("revenue"))
    official_cogs = _num(pnl_model.get("cogs"))
    official_opex = _num(pnl_model.get("opex"))
    direct = selling = admin = finance = other = bank = 0.0

    if expense_model and not expense_model.get("expense_long", pd.DataFrame()).empty:
        df = expense_model.get("expense_long", pd.DataFrame()).copy()
        df["amount"] = pd.to_numeric(df.get("amount"), errors="coerce").fillna(0.0)
        cat_col = "category"
        for _, r in df.iterrows():
            cat = str(r.get(cat_col, ""))
            amt = _num(r.get("amount"))
            if cat in ["Cost of Revenue", "Purchases", "COGS", "Fuel", "Spare Parts", "Maintenance"]:
                direct += amt
            elif cat in ["Selling & Marketing", "Marketing", "Selling Opex"]:
                selling += amt
            elif cat in ["Finance Costs"]:
                finance += amt
            elif cat in ["Bank Charges"]:
                bank += amt
            elif cat in ["Needs Review"]:
                other += amt
            else:
                admin += amt
        mapped_total = direct + selling + admin + finance + other + bank
        # Use official opex total as control total to avoid overstating expenses due to file duplication.
        if mapped_total and official_opex and abs(mapped_total - official_opex) / max(abs(official_opex), 1) < .20:
            factor = official_opex / mapped_total
            direct *= factor; selling *= factor; admin *= factor; finance *= factor; other *= factor; bank *= factor
    else:
        admin = official_opex

    adjusted_cogs = official_cogs + direct
    adjusted_opex = max(0.0, official_opex - direct) if official_opex else (admin + selling + finance + other + bank)
    gross_profit = revenue - adjusted_cogs
    operating_profit = revenue - adjusted_cogs - adjusted_opex
    net_profit = _num(pnl_model.get("net_profit"))
    if not net_profit and revenue:
        net_profit = operating_profit

    mgmt_table = pd.DataFrame([
        ["الإيرادات", revenue, "إيراد النشاط / صافي المبيعات"],
        ["تكلفة الإيراد من ميزان المراجعة", official_cogs, "مشتريات أو تكلفة مباشرة مصنفة رسميًا"],
        ["تكاليف تشغيل مباشرة معاد تصنيفها", direct, "رواتب تشغيل/دعم/تنفيذ/مشاريع/صيانة مرتبطة بتقديم الخدمة"],
        ["إجمالي تكلفة الإيراد", adjusted_cogs, "تكلفة الإيراد الرسمية + المصاريف المباشرة المعاد تصنيفها"],
        ["مجمل الربح الإداري", gross_profit, "الإيراد بعد تكلفة تقديم الخدمة"],
        ["مصاريف بيع وتسويق", selling, "مبيعات، تسويق، عمولات"],
        ["مصاريف إدارية وعمومية", admin, "إدارة، رواتب إدارية، إيجارات، خدمات عامة"],
        ["مصاريف بنكية وتمويلية", finance + bank, "تمويل، رسوم، بوابات دفع"],
        ["بنود بحاجة مراجعة", other, "حسابات لم يعتمد لها تصنيف مالي نهائي؛ لا تعرض كبنود بحاجة مراجعة معتمدة"],
        ["صافي الربح", net_profit, "مرتبط بإجمالي قائمة الدخل بعد إعادة عرض التصنيف"],
    ], columns=["البند", "القيمة", "القراءة"])

    return {
        "revenue": revenue,
        "official_cogs": official_cogs,
        "direct_reclassified": direct,
        "cogs": adjusted_cogs,
        "gross_profit": gross_profit,
        "opex": adjusted_opex,
        "selling_marketing": selling,
        "admin_opex": admin,
        "finance_bank": finance + bank,
        "other_opex": other,
        "net_profit": net_profit,
        "management_table": mgmt_table,
        "source_note": "قائمة دخل إدارية: تعيد عرض تكلفة الإيراد والمصاريف حسب خريطة التصنيف دون تغيير صافي الربح الرسمي.",
    }

def build_balance_sheet_reading(tb_model: dict | None, liquidity_model: dict | None = None) -> dict:
    tb = _prepare_tb(tb_model)
    if tb.empty:
        return {"available": False, "balance_sheet": pd.DataFrame(), "metrics": {}, "vertical": pd.DataFrame(), "horizontal": pd.DataFrame(), "notes": ["ميزان المراجعة غير متاح."]}

    total_assets = _amount_by_code(tb, "1", "debit")
    fixed_assets = _amount_by_code(tb, "101", "debit")
    current_assets = _amount_by_code(tb, "102", "debit") + _amount_by_code(tb, "103", "debit")
    cash = _amount_by_code(tb, "103", "debit") or _sum_leaf_by_name(tb, ["بنك", "صندوق", "نقد", "الأموال الجاهزة", "اموال جاهزه", "cash", "bank"], "debit")
    ar_report = _ar_cards(liquidity_model).get("total_balance")
    ar_quality = "valid"
    ar_credit_balance = 0.0
    if ar_report not in [None, ""]:
        ar = _num(ar_report)
        ar_source_note = "أعمار العملاء"
    else:
        # Signed AR check: a credit-balance customer account is not receivable and must not produce fake DSO.
        ar_raw = _amount_by_code(tb, "10202", "debit", absolute=False)
        if ar_raw <= 0:
            # Try broad name search, but keep signed logic.
            customer_credit = 0.0
            lf = tb[tb["account_name"].apply(lambda x: "عميل" in _norm(x) or "عملاء" in _norm(x) or "ذمم مدينة" in _norm(x))].copy()
            if not lf.empty:
                signed = float((lf["current_debit"] - lf["current_credit"]).sum())
                if signed < 0:
                    customer_credit = abs(signed)
            ar = 0.0
            ar_quality = "credit_balance" if (ar_raw < 0 or customer_credit > 0) else "missing"
            ar_credit_balance = abs(ar_raw) if ar_raw < 0 else customer_credit
            ar_source_note = "حساب العملاء يظهر دائنًا أو غير واضح"
        else:
            ar = ar_raw
            ar_source_note = "ميزان المراجعة / رصيد عملاء مدين"
    inventory = _sum_leaf_by_name(tb, ["مخزون", "بضاعة"], "debit")

    total_liabilities_equity = _amount_by_code(tb, "2", "credit")
    equity = _amount_by_code(tb, "201", "credit") + _amount_by_code(tb, "202", "credit")
    current_liabilities = _amount_by_code(tb, "204", "credit") + _amount_by_code(tb, "205", "credit")
    if current_liabilities <= 0:
        current_liabilities = _sum_leaf_by_name(tb, ["دائن", "مستحق", "ضريبة القيمة المضافة للمبيعات", "زكاة", "مورد", "payable"], "credit")
    total_liabilities = current_liabilities + _sum_leaf_by_name(tb, ["قرض", "تمويل", "loan"], "credit")
    if total_liabilities <= 0 and total_liabilities_equity and equity:
        total_liabilities = max(0.0, total_liabilities_equity - equity)

    ap_report = _ap_cards(liquidity_model).get("total_balance")
    ap = _num(ap_report) if ap_report not in [None, ""] else _sum_leaf_by_name(tb, ["مورد", "ذمم دائنة", "دائنون", "payable"], "credit")
    if abs(ap) < 1.0:
        ap = 0.0

    if total_assets <= 0:
        total_assets = fixed_assets + current_assets

    rows = [
        ["الأصول الثابتة", fixed_assets, "ميزان المراجعة"],
        ["الأصول المتداولة", current_assets, "ميزان المراجعة / يشمل النقد إذا ظهر مستقلًا"],
        ["النقد وما في حكمه", cash, "ميزان المراجعة / تقرير السيولة إن وجد"],
        ["العملاء / الذمم المدينة", ar, ar_source_note],
        ["المخزون", inventory, "ميزان المراجعة إن وجد"],
        ["إجمالي الأصول", total_assets, "ميزان المراجعة"],
        ["الالتزامات المتداولة", current_liabilities, "ميزان المراجعة"],
        ["الموردون / الذمم الدائنة", ap, "أعمار الموردين إن وجدت وإلا ميزان المراجعة"],
        ["إجمالي الالتزامات", total_liabilities, "تقدير من ميزان المراجعة"],
        ["حقوق الملكية", equity, "ميزان المراجعة"],
    ]
    bs = pd.DataFrame(rows, columns=["البند", "القيمة", "المصدر"])

    vertical = bs[bs["البند"].isin(["الأصول الثابتة", "الأصول المتداولة", "النقد وما في حكمه", "العملاء / الذمم المدينة", "المخزون", "الالتزامات المتداولة", "إجمالي الالتزامات", "حقوق الملكية"])].copy()
    vertical["نسبة من إجمالي الأصول"] = vertical["القيمة"].apply(lambda x: _safe_div(x, total_assets))
    vertical["نسبة من إجمالي الأصول"] = vertical["نسبة من إجمالي الأصول"].apply(_pct)

    all_codes = tb["account_code_norm"].astype(str).tolist()
    leaves = tb[~tb["account_code_norm"].astype(str).apply(lambda c: _is_parent_code(c, all_codes))].copy()
    leaves["رصيد أول الفترة"] = leaves["beginning_net_debit"]
    leaves["رصيد آخر الفترة"] = leaves["closing_net_debit"]
    leaves["التغير"] = leaves["رصيد آخر الفترة"] - leaves["رصيد أول الفترة"]
    leaves["نسبة التغير"] = leaves.apply(lambda r: _safe_div(r["التغير"], abs(r["رصيد أول الفترة"])), axis=1)
    horizontal = leaves.loc[leaves["التغير"].abs().sort_values(ascending=False).index, ["account_name", "رصيد أول الفترة", "رصيد آخر الفترة", "التغير", "نسبة التغير"]].head(20)
    horizontal = horizontal.rename(columns={"account_name": "الحساب"})
    horizontal["نسبة التغير"] = horizontal["نسبة التغير"].apply(_pct)

    metrics = {
        "total_assets": total_assets,
        "fixed_assets": fixed_assets,
        "current_assets": current_assets,
        "cash": cash,
        "ar": ar,
        "ar_quality": ar_quality,
        "ar_credit_balance": ar_credit_balance,
        "inventory": inventory,
        "current_liabilities": current_liabilities,
        "ap": ap,
        "total_liabilities": total_liabilities,
        "equity": equity,
        "working_capital": current_assets - current_liabilities,
    }
    return {"available": True, "balance_sheet": bs, "metrics": metrics, "vertical": vertical, "horizontal": horizontal, "notes": []}


def _benchmark_status(metric: str, value: float | None, sector: str = "") -> tuple[str, str, str]:
    if value is None:
        return "غير محسوب", "غير متاح", "البيانات الحالية لا تكفي للحساب."
    sector_n = _norm(sector)
    # Benchmarks are deliberately conservative safety ranges, not absolute valuation advice.
    if metric == "gross_margin":
        if "saas" in sector_n or "برمج" in sector_n or "اشتراك" in sector_n:
            if value >= .60: return "جيد", "≥ 60%", "هامش إجمالي مناسب غالبًا لشركة برمجية إذا كانت تكلفة الإيراد مصنفة بدقة."
            if value >= .40: return "متوسط", "40%–60%", "الهامش يحتاج فحص تكلفة الإيراد والدعم والتنفيذ."
            return "خطر", "< 40%", "تكلفة تقديم الخدمة مرتفعة أو التصنيف يحتاج مراجعة."
        if value >= .35: return "جيد", "≥ 35%", "هامش إجمالي مقبول مبدئيًا حسب نشاط غير مصنع."
        if value >= .20: return "متوسط", "20%–35%", "الهامش يحتاج مراقبة."
        return "خطر", "< 20%", "الهامش ضعيف ويحتاج مراجعة تسعير أو تكلفة."
    if metric == "net_margin":
        if value >= .10: return "جيد", "≥ 10%", "الشركة تحقق هامش ربح صافي صحي مبدئيًا."
        if value >= .03: return "متوسط", "3%–10%", "الربح موجود لكنه حساس لأي ارتفاع تكلفة أو تأخر تحصيل."
        if value >= 0: return "ضعيف", "0%–3%", "هامش ربح شبه معدوم."
        return "خطر", "< 0%", "الشركة خاسرة خلال الفترة."
    if metric == "current_ratio":
        if value >= 1.5: return "جيد", "≥ 1.5x", "الأصول المتداولة تغطي الالتزامات المتداولة بهامش مقبول."
        if value >= 1.0: return "متوسط", "1.0x–1.5x", "السيولة المحاسبية تغطي الالتزامات لكن هامش الأمان محدود."
        return "خطر", "< 1.0x", "الالتزامات المتداولة أعلى من الأصول المتداولة."
    if metric == "quick_ratio":
        if value >= 1.0: return "جيد", "≥ 1.0x", "السيولة السريعة قادرة على تغطية الالتزامات المتداولة."
        if value >= .6: return "متوسط", "0.6x–1.0x", "تحتاج متابعة التحصيل."
        return "خطر", "< 0.6x", "الاعتماد على تحصيل سريع أو تمويل قصير الأجل مرتفع."
    if metric == "cash_ratio":
        if value >= .5: return "جيد", "≥ 0.5x", "النقد يغطي جزءًا جيدًا من الالتزامات المتداولة."
        if value >= .2: return "متوسط", "0.2x–0.5x", "النقد محدود لكنه ليس معدومًا."
        return "خطر", "< 0.2x", "النقد المباشر ضعيف أمام الالتزامات القصيرة."
    if metric == "debt_ratio":
        if value <= .5: return "جيد", "≤ 50%", "الاعتماد على الالتزامات ضمن مستوى محافظ."
        if value <= .75: return "متوسط", "50%–75%", "المديونية تحتاج مراقبة."
        return "خطر", "> 75%", "جزء كبير من الأصول ممول بالتزامات."
    if metric == "debt_to_equity":
        if value <= 1.0: return "جيد", "≤ 1.0x", "الالتزامات أقل من أو قريبة من حقوق الملكية."
        if value <= 2.0: return "متوسط", "1.0x–2.0x", "الرافعة المالية متوسطة وتحتاج متابعة."
        return "خطر", "> 2.0x", "الاعتماد على الالتزامات مرتفع قياسًا بحقوق الملكية."
    if metric == "dso":
        if value <= 30: return "جيد", "≤ 30 يوم", "التحصيل سريع مبدئيًا."
        if value <= 60: return "متوسط", "30–60 يوم", "التحصيل يحتاج متابعة دورية."
        return "خطر", "> 60 يوم", "التحصيل بطيء ويضغط السيولة."
    if metric == "runway":
        if value >= 3: return "جيد", "≥ 3 أشهر", "هامش أمان نقدي مقبول."
        if value >= 1: return "متوسط", "1–3 أشهر", "السيولة تحتاج مراقبة شهرية."
        return "خطر", "< شهر", "السيولة لا تغطي شهرًا كاملًا من متوسط الخروج النقدي."
    return "إرشادي", "—", "مؤشر إرشادي."


def build_ratio_scorecard(pnl_model: dict, balance_model: dict, liquidity_model: dict | None, sector: str = "") -> dict:
    metrics = balance_model.get("metrics", {}) if balance_model else {}
    revenue = _num(pnl_model.get("revenue"))
    cogs = _num(pnl_model.get("cogs"))
    gross_profit = _num(pnl_model.get("gross_profit"))
    opex = _num(pnl_model.get("opex"))
    ebitda = _num(pnl_model.get("ebitda"))
    net_profit = _num(pnl_model.get("net_profit"))

    current_assets = _num(metrics.get("current_assets"))
    current_liabilities = _num(metrics.get("current_liabilities"))
    cash = _num(metrics.get("cash"))
    ar = _num(metrics.get("ar"))
    inventory = _num(metrics.get("inventory"))
    total_assets = _num(metrics.get("total_assets"))
    total_liabilities = _num(metrics.get("total_liabilities"))
    equity = _num(metrics.get("equity"))
    ap = _num(metrics.get("ap"))

    cash_cards = _liquidity_cards(liquidity_model)
    runway = cash_cards.get("cash_runway_months")
    runway = None if runway is None else _num(runway)

    period_days = float((sector if isinstance(sector, dict) else {}).get("period_days", 0) or 0) if isinstance(sector, dict) else 0
    if not period_days:
        period_days = 365.25  # V13.4: safe annualized fallback; app injects actual selected-month days when available.
    dso = _safe_div(ar, revenue / period_days) if revenue else None
    dpo = _safe_div(ap, cogs / period_days) if cogs else None

    ratio_defs = [
        ("الربحية", "هامش مجمل الربح", "gross_margin", _safe_div(gross_profit, revenue), "مجمل الربح ÷ الإيرادات", "هل البيع يترك هامشًا كافيًا قبل المصاريف؟"),
        ("الربحية", "هامش التشغيل", "operating_margin", _safe_div(ebitda, revenue), "الربح التشغيلي ÷ الإيرادات", "هل التشغيل نفسه مربح قبل التمويل؟"),
        ("الربحية", "هامش صافي الربح", "net_margin", _safe_div(net_profit, revenue), "صافي الربح ÷ الإيرادات", "هل النتيجة النهائية مقبولة؟"),
        ("الربحية", "نسبة المصاريف التشغيلية", "opex_ratio", _safe_div(opex, revenue), "المصاريف التشغيلية ÷ الإيرادات", "هل المصاريف تستهلك قدرة الإيراد؟"),
        ("السيولة", "رأس المال العامل", "working_capital", metrics.get("working_capital"), "الأصول المتداولة - الالتزامات المتداولة", "هل توجد مساحة تشغيل قصيرة الأجل؟"),
        ("السيولة", "نسبة التداول", "current_ratio", _safe_div(current_assets, current_liabilities), "الأصول المتداولة ÷ الالتزامات المتداولة", "هل الأصول القصيرة تغطي الالتزامات القصيرة؟"),
        ("السيولة", "النسبة السريعة", "quick_ratio", _safe_div(cash + ar, current_liabilities), "النقد + العملاء ÷ الالتزامات المتداولة", "هل يمكن السداد دون انتظار المخزون؟"),
        ("السيولة", "نسبة النقدية", "cash_ratio", _safe_div(cash, current_liabilities), "النقد ÷ الالتزامات المتداولة", "ما قدرة السداد النقدي الفوري؟"),
        ("السيولة", "Cash Runway", "runway", runway, "النقد ÷ متوسط الخروج النقدي الشهري", "كم شهر يغطي النقد المتاح؟"),
        ("المديونية", "نسبة الالتزامات إلى الأصول", "debt_ratio", _safe_div(total_liabilities, total_assets), "إجمالي الالتزامات ÷ إجمالي الأصول", "كم من الأصول ممول بالتزامات؟"),
        ("المديونية", "الالتزامات إلى حقوق الملكية", "debt_to_equity", _safe_div(total_liabilities, equity), "إجمالي الالتزامات ÷ حقوق الملكية", "ما مستوى الرافعة المالية؟"),
        ("الكفاءة", "أيام التحصيل DSO", "dso", dso, "العملاء ÷ متوسط المبيعات اليومية", "كم يوم تحتاج المبيعات لتتحول إلى نقد؟"),
        ("الكفاءة", "أيام دفع الموردين DPO", "dpo", dpo, "الموردون ÷ متوسط تكلفة المبيعات اليومية", "هل الشركة تمول نفسها من الموردين؟"),
    ]
    rows = []
    for group, name, key, val, formula, question in ratio_defs:
        status, benchmark, interpretation = _benchmark_status(key, val, sector)
        value_display = _money(val) if key in ["working_capital"] else (f"{val:.1f} شهر" if key == "runway" and val is not None else (f"{val:.1f} يوم" if key in ["dso", "dpo"] and val is not None else (f"{val:.2f}x" if key in ["current_ratio", "quick_ratio", "cash_ratio", "debt_to_equity"] and val is not None else _pct(val))))
        rows.append([group, name, value_display, benchmark, status, formula, question, interpretation])
    df = pd.DataFrame(rows, columns=["المجموعة", "المؤشر", "النتيجة", "معيار السلامة", "الحكم", "طريقة الحساب", "سؤال الإدارة", "القراءة"])
    return {"ratios": df}


def build_vertical_income_statement(pnl_model: dict) -> pd.DataFrame:
    rows = []
    revenue = _num(pnl_model.get("revenue"))
    items = [
        ("الإيرادات", _num(pnl_model.get("revenue"))),
        ("تكلفة الإيراد / المبيعات", _num(pnl_model.get("cogs"))),
        ("مجمل الربح", _num(pnl_model.get("gross_profit"))),
        ("المصاريف التشغيلية", _num(pnl_model.get("opex"))),
        ("الربح التشغيلي", _num(pnl_model.get("ebitda"))),
        ("صافي الربح", _num(pnl_model.get("net_profit"))),
    ]
    for label, amount in items:
        rows.append([label, amount, _pct(_safe_div(amount, revenue))])
    return pd.DataFrame(rows, columns=["البند", "القيمة", "نسبة من الإيرادات"])


def build_horizontal_monthly_analysis(monthly_pnl_model: pd.DataFrame | None) -> pd.DataFrame:
    if monthly_pnl_model is None or monthly_pnl_model.empty:
        return pd.DataFrame()
    df = monthly_pnl_model.copy()
    for col in ["revenue", "expenses", "preliminary_profit"]:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df["month_order"] = df["month"].map({m:i for i,m in enumerate(MONTH_ORDER)}).fillna(99)
    df = df.sort_values("month_order")
    df["تغير الإيراد عن الشهر السابق"] = df["revenue"].pct_change()
    df["تغير المصروفات عن الشهر السابق"] = df["expenses"].pct_change()
    df["تغير الربح عن الشهر السابق"] = df["preliminary_profit"].pct_change()
    out = pd.DataFrame({
        "الشهر": df["month"].map(AR_MONTHS).fillna(df["month"]),
        "الإيرادات": df["revenue"],
        "المصروفات": df["expenses"],
        "الربح/الخسارة الشهرية": df["preliminary_profit"],
        "نمو الإيراد": df["تغير الإيراد عن الشهر السابق"].apply(lambda x: "—" if pd.isna(x) else _pct(x)),
        "نمو المصروفات": df["تغير المصروفات عن الشهر السابق"].apply(lambda x: "—" if pd.isna(x) else _pct(x)),
        "تغير الربحية": df["تغير الربح عن الشهر السابق"].apply(lambda x: "—" if pd.isna(x) else _pct(x)),
    })
    return out


def build_data_reading_summary(pnl_model: dict, balance_model: dict, liquidity_model: dict | None, revenue_quality: dict | None = None, balance_flags: dict | None = None) -> pd.DataFrame:
    b = balance_model.get("metrics", {}) if balance_model else {}
    cash_cards = _liquidity_cards(liquidity_model)
    ar_cards = _ar_cards(liquidity_model)
    rq = revenue_quality or {}
    rows = [
        ["الإيرادات", _money(_num(pnl_model.get("revenue"))), pnl_model.get("source", "trial_balance"), "تستخدم للحكم على الربحية والهامش."],
        ["إجمالي المبيعات قبل التآكل", _money(_num(rq.get("gross_sales"))), "ميزان المراجعة / حسابات 401", "يكشف حجم المبيعات قبل الخصومات والمردودات."],
        ["تآكل الإيراد", _money(_num(rq.get("revenue_leakage"))), "مردودات + خصومات من الميزان", "إذا كان مرتفعًا فهو خطر جودة إيراد قبل أي تحليل مصاريف."],
        ["تكلفة الإيراد / المبيعات", _money(_num(pnl_model.get("cogs"))), "ميزان المراجعة + تصنيف إداري عميق", "تحدد جودة الهامش ولا يجوز حصرها في المشتريات فقط."],
        ["المصاريف التشغيلية", _money(_num(pnl_model.get("opex"))), "ميزان المراجعة + خريطة المصاريف", "تقيس ضغط الإدارة والبيع والتسويق على الإيراد."],
        ["صافي الربح", _money(_num(pnl_model.get("net_profit"))), "قائمة الدخل التحليلية", "النتيجة النهائية للفترة."],
        ["النقد", _money(_num(b.get("cash")) or _num(cash_cards.get("ending_cash"))), "ميزان المراجعة / تقرير السيولة", "يستخدم للحكم على القدرة النقدية وليس الربحية."],
        ["العملاء", _money(_num(b.get("ar")) or _num(ar_cards.get("total_balance"))), str(b.get("ar_quality", "ميزان المراجعة")), "لا يحسب DSO إذا كان حساب العملاء دائنًا."],
        ["الالتزامات المتداولة", _money(_num(b.get("current_liabilities"))), "ميزان المراجعة", "أساس نسب السيولة."],
    ]
    bf = (balance_flags or {}).get("metrics", {}) if balance_flags else {}
    if bf.get("rnd_assets"):
        rows.append(["مشاريع البحث والتطوير", _money(_num(bf.get("rnd_assets"))), "ميزان المراجعة / أصول غير ملموسة أو مشاريع", "تحتاج اختبار منفعة مستقبلية وإطفاء/هبوط إذا كانت جوهرية."])
    return pd.DataFrame(rows, columns=["ما تمت قراءته", "القيمة", "المصدر", "لماذا يهم؟"])


def build_cfo_reading(full: dict, profile: dict | None = None) -> dict:
    profile = profile or {}
    pnl = full.get("pnl_model", {})
    revenue = _num(pnl.get("revenue"))
    net_profit = _num(pnl.get("net_profit"))
    gross_margin = _safe_div(_num(pnl.get("gross_profit")), revenue)
    net_margin = _safe_div(net_profit, revenue)
    opex_ratio = _safe_div(_num(pnl.get("opex")), revenue)
    metrics = full.get("balance_sheet", {}).get("metrics", {})
    current_ratio = _safe_div(_num(metrics.get("current_assets")), _num(metrics.get("current_liabilities")))
    cash = _num(metrics.get("cash"))
    wc = _num(metrics.get("working_capital"))

    if revenue <= 0:
        headline = "لا توجد قراءة مالية موثوقة قبل تثبيت مصدر الإيرادات."
        diagnosis = "النموذج لم يقرأ إيرادًا قابلًا للاعتماد، لذلك لا يمكن حساب الربحية أو النسب بصورة مهنية."
        action = "ثبّت ملف المبيعات أو ميزان المراجعة كمصدر رسمي للإيرادات ثم أعد بناء النموذج."
    elif net_profit < 0:
        headline = "الشركة خاسرة خلال الفترة، والمشكلة يجب أن تُفصل بين الهامش والتشغيل لا أن تُعرض كرقم خسارة فقط."
        diagnosis = f"الإيرادات بلغت {_money(revenue)}، لكنها انتهت إلى خسارة تقارب {_money(abs(net_profit))}. هامش صافي الربح {_pct(net_margin)}. القراءة المهنية هنا: إما أن تكلفة الإيراد مرتفعة، أو المصاريف التشغيلية سبقت قدرة المبيعات، أو أن التصنيف يحتاج فصلًا أدق بين تكلفة الإيراد والمصاريف الإدارية والتسويقية."
        action = "ابدأ بجدول التحليل الرأسي: افصل تكلفة الإيراد، البيع والتسويق، والإدارة. ثم راجع أكبر 10 بنود أثرت على الخسارة قبل أي توسع أو التزام جديد."
    elif net_margin is not None and net_margin < .05:
        headline = "الشركة رابحة لكن هامش الأمان ضعيف."
        diagnosis = f"صافي الهامش {_pct(net_margin)}. هذا يعني أن الشركة قد تبدو رابحة، لكنها حساسة لأي خصم أو مرتجع أو تأخر تحصيل أو زيادة رواتب."
        action = "ركز على جودة الإيراد والتحصيل قبل زيادة المصروفات."
    else:
        headline = "الربحية مقبولة مبدئيًا، لكن القرار لا يكتمل دون السيولة والتحصيل."
        diagnosis = f"هامش مجمل الربح {_pct(gross_margin)} وصافي الهامش {_pct(net_margin)}. يجب الآن اختبار هل هذا الربح يتحول إلى نقد أم يبقى في العملاء أو يتآكل في المصاريف."
        action = "انتقل إلى نسب السيولة والتحصيل وحدد أولويات النقد."

    liquidity_line = ""
    if current_ratio is not None:
        liquidity_line = f"نسبة التداول {_safe_ratio_text(current_ratio)} ورأس المال العامل {_money(wc)}. النقد المقروء {_money(cash)}. هذه القراءة لا تكفي وحدها؛ يجب ربطها بأعمار العملاء والموردين."
    else:
        liquidity_line = "نسب السيولة غير مكتملة لأن الالتزامات أو الأصول المتداولة غير واضحة من البيانات الحالية."

    return {"headline": headline, "diagnosis": diagnosis, "liquidity": liquidity_line, "action": action}


def _safe_ratio_text(x: float | None) -> str:
    if x is None:
        return "غير متاحة"
    return f"{x:.2f}x"


def build_comprehensive_financial_analysis(tb_model: dict | None, pnl_model: dict, expense_model: dict | None, revenue_model: dict | None, monthly_pnl_model: pd.DataFrame | None, liquidity_model: dict | None, profile: dict | None = None, breakeven_model: dict | None = None, use_ai_narrative: bool = False) -> dict:
    """V12.5 comprehensive model.

    Deterministic engines calculate financial statements and ratios.
    The CFO Intelligence layer then produces diagnostic findings, financial health score,
    professional ratio readings, and an optional AI-written executive narrative.
    """
    profile = profile or {}
    management_pnl = build_management_pnl_snapshot(pnl_model, expense_model, tb_model, profile)
    revenue_quality_tb = management_pnl.get("revenue_quality") or build_revenue_quality_from_tb(tb_model)
    segment_analysis = {"segment_table": management_pnl.get("segment_table", pd.DataFrame()), "warnings": management_pnl.get("warnings", []), "stream_detector": management_pnl.get("stream_detector", {})}
    balance_flags = build_balance_quality_flags(tb_model)
    activity_profile = infer_activity_profile(tb_model, profile)

    ratio_pnl = dict(pnl_model or {})
    ratio_pnl.update({
        "revenue": management_pnl.get("revenue", 0),
        "cogs": management_pnl.get("cogs", 0),
        "gross_profit": management_pnl.get("gross_profit", 0),
        "opex": management_pnl.get("opex", 0),
        "ebitda": management_pnl.get("revenue",0) - management_pnl.get("cogs",0) - management_pnl.get("opex",0),
        "net_profit": management_pnl.get("net_profit", 0),
        "admin_opex": management_pnl.get("admin_opex", 0),
        "selling_marketing": management_pnl.get("selling_marketing", 0),
        "finance_bank": management_pnl.get("finance_bank", 0),
        "other_opex": management_pnl.get("other_opex", 0),
        "revenue_leakage_ratio": revenue_quality_tb.get("leakage_ratio"),
    })
    balance = build_balance_sheet_reading(tb_model, liquidity_model)
    metric_pack = build_metric_pack(ratio_pnl, management_pnl, balance, liquidity_model, breakeven_model, profile)
    cfo_intel = build_cfo_intelligence(metric_pack, profile, use_ai=use_ai_narrative)
    vertical_income = build_vertical_income_statement(ratio_pnl)
    horizontal_monthly = build_horizontal_monthly_analysis(monthly_pnl_model)
    data_reading = build_data_reading_summary(ratio_pnl, balance, liquidity_model, revenue_quality_tb, balance_flags)
    return {
        "available": True,
        "management_pnl": management_pnl,
        "balance_sheet": balance,
        "revenue_quality_tb": revenue_quality_tb,
        "segment_analysis": segment_analysis,
        "stream_detector": segment_analysis.get("stream_detector", {}),
        "balance_quality_flags": balance_flags,
        "activity_profile": activity_profile,
        "metric_pack": metric_pack,
        "ratios": cfo_intel.get("ratios_enriched", pd.DataFrame()),
        "financial_health_score": cfo_intel.get("financial_health_score", {}),
        "diagnostic_findings": cfo_intel.get("diagnostic_findings", pd.DataFrame()),
        "vertical_income": vertical_income,
        "vertical_balance": balance.get("vertical", pd.DataFrame()),
        "horizontal_monthly": horizontal_monthly,
        "horizontal_balance": balance.get("horizontal", pd.DataFrame()),
        "data_reading": data_reading,
        "cfo_reading": cfo_intel.get("executive_summary", {}),
    }

