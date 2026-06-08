import pandas as pd

def build_basic_financial_model(revenue_model: dict | None, expense_model: dict | None) -> dict:
    revenue_total = revenue_model.get("total_revenue", 0) if revenue_model else 0
    expense_total = expense_model.get("total_expenses", 0) if expense_model else 0
    gross_profit = revenue_total - expense_total
    net_margin = gross_profit / revenue_total if revenue_total else 0

    return {
        "revenue": revenue_total,
        "expenses": expense_total,
        "gross_profit_preliminary": gross_profit,
        "net_margin_preliminary": net_margin,
        "note": "هذا نموذج أولي. سيتم فصل COGS وOpex وEBITDA في Sprint 2.",
    }
