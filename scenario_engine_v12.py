from __future__ import annotations

import pandas as pd


def _num(x, default=0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def base_inputs_from_models(models: dict | None, liquidity_model: dict | None = None) -> dict:
    models = models or {}
    pnl = models.get("pnl_model", {}) or {}
    expense = models.get("expense_model", {}) or {}
    revenue = models.get("revenue_model", {}) or {}
    cash_cards = (((liquidity_model or {}).get("cash") or {}).get("cards") or {})
    ar_cards = (((liquidity_model or {}).get("ar") or {}).get("cards") or {})
    ap_cards = (((liquidity_model or {}).get("ap") or {}).get("cards") or {})

    total_revenue = _num(pnl.get("total_revenue"), _num(revenue.get("total_revenue")))
    cogs = _num(pnl.get("cogs"), 0)
    opex = _num(pnl.get("operating_expenses"), _num(expense.get("total_expenses"), 0))
    cash = _num(cash_cards.get("ending_cash"), 0)
    monthly_cash_out = _num(cash_cards.get("avg_monthly_cash_out"), 0)
    ar = _num(ar_cards.get("total_balance"), 0)
    ap = _num(ap_cards.get("total_balance"), 0)

    return {
        "revenue": total_revenue,
        "cogs": cogs,
        "opex": opex,
        "cash_balance": cash,
        "monthly_cash_out": monthly_cash_out,
        "ar_balance": ar,
        "ap_balance": ap,
    }


def run_simple_scenario(base: dict, assumptions: dict) -> dict:
    revenue = _num(base.get("revenue"))
    cogs = _num(base.get("cogs"))
    opex = _num(base.get("opex"))
    cash = _num(base.get("cash_balance"))
    monthly_cash_out = _num(base.get("monthly_cash_out")) or max(opex / 5, 1)
    ar = _num(base.get("ar_balance"))
    ap = _num(base.get("ap_balance"))

    sales_growth = _num(assumptions.get("sales_growth_pct")) / 100
    discount_rate = _num(assumptions.get("discount_rate_pct")) / 100
    return_rate = _num(assumptions.get("return_rate_pct")) / 100
    collection_rate = _num(assumptions.get("collection_rate_pct")) / 100
    opex_change = _num(assumptions.get("opex_change_pct")) / 100
    cogs_change = _num(assumptions.get("cogs_change_pct")) / 100
    tax_payment = _num(assumptions.get("tax_payment"))
    supplier_payment = _num(assumptions.get("supplier_payment"))

    gross_sales = revenue * (1 + sales_growth)
    leakage = gross_sales * max(0, discount_rate + return_rate)
    net_sales = max(0, gross_sales - leakage)
    cogs_forecast = cogs * (1 + cogs_change) * (net_sales / revenue if revenue else 1)
    opex_forecast = opex * (1 + opex_change)
    gross_profit = net_sales - cogs_forecast
    net_profit = gross_profit - opex_forecast

    expected_collection = (net_sales * collection_rate) + (ar * min(collection_rate, 1))
    expected_cash_out = monthly_cash_out + supplier_payment + tax_payment + max(0, opex_forecast - opex) / 5
    ending_cash_30 = cash + expected_collection - expected_cash_out
    runway = ending_cash_30 / expected_cash_out if expected_cash_out else None

    return {
        "gross_sales": gross_sales,
        "commercial_leakage": leakage,
        "net_sales": net_sales,
        "gross_profit": gross_profit,
        "net_profit": net_profit,
        "expected_collection": expected_collection,
        "expected_cash_out": expected_cash_out,
        "ending_cash_30": ending_cash_30,
        "cash_runway_months": runway,
        "risk_level": "عالي" if runway is not None and runway < 1 else "متوسط" if runway is not None and runway < 2 else "منخفض",
    }


def predefined_scenarios(base: dict) -> pd.DataFrame:
    scenarios = {
        "الوضع الحالي": {"sales_growth_pct": 0, "discount_rate_pct": 0, "return_rate_pct": 0, "collection_rate_pct": 40, "opex_change_pct": 0, "cogs_change_pct": 0, "supplier_payment": 0, "tax_payment": 0},
        "تحصيل أفضل": {"sales_growth_pct": 0, "discount_rate_pct": 0, "return_rate_pct": 0, "collection_rate_pct": 65, "opex_change_pct": 0, "cogs_change_pct": 0, "supplier_payment": 0, "tax_payment": 0},
        "تسرب تجاري مرتفع": {"sales_growth_pct": 5, "discount_rate_pct": 8, "return_rate_pct": 10, "collection_rate_pct": 40, "opex_change_pct": 0, "cogs_change_pct": 0, "supplier_payment": 0, "tax_payment": 0},
        "ضغط سيولة": {"sales_growth_pct": -5, "discount_rate_pct": 3, "return_rate_pct": 5, "collection_rate_pct": 25, "opex_change_pct": 5, "cogs_change_pct": 3, "supplier_payment": 0, "tax_payment": 0},
        "ضبط مصروفات": {"sales_growth_pct": 0, "discount_rate_pct": 0, "return_rate_pct": 0, "collection_rate_pct": 45, "opex_change_pct": -10, "cogs_change_pct": 0, "supplier_payment": 0, "tax_payment": 0},
    }
    rows = []
    for name, assumptions in scenarios.items():
        res = run_simple_scenario(base, assumptions)
        rows.append({
            "السيناريو": name,
            "صافي المبيعات المتوقع": res["net_sales"],
            "الربح المتوقع": res["net_profit"],
            "التحصيل المتوقع": res["expected_collection"],
            "النقد بعد 30 يوم": res["ending_cash_30"],
            "Runway": res["cash_runway_months"],
            "الخطر": res["risk_level"],
        })
    return pd.DataFrame(rows)
