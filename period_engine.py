import pandas as pd

MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def normalize_months(months):
    clean = []
    for m in months:
        if pd.isna(m):
            continue
        s = str(m).strip()
        if s and s not in clean:
            clean.append(s)
    return sorted(clean, key=lambda x: MONTH_ORDER.index(x) if x in MONTH_ORDER else 99)

def months_from_revenue_model(revenue_model):
    if not revenue_model:
        return []
    df = revenue_model.get("monthly_revenue", pd.DataFrame())
    if df.empty or "month" not in df.columns:
        return []
    return normalize_months(df["month"].tolist())

def months_from_expense_model(expense_model):
    if not expense_model:
        return []
    df = expense_model.get("monthly_expenses", pd.DataFrame())
    if df.empty or "month" not in df.columns:
        return []
    return normalize_months(df["month"].tolist())

def common_months(revenue_months, expense_months):
    if revenue_months and expense_months:
        return normalize_months([m for m in revenue_months if m in set(expense_months)])
    return normalize_months(revenue_months or expense_months)

def filter_revenue_model(revenue_model, selected_months):
    if not revenue_model or not selected_months:
        return revenue_model
    out = dict(revenue_model)
    df = out.get("monthly_revenue", pd.DataFrame()).copy()
    if not df.empty and "month" in df.columns:
        df = df[df["month"].isin(selected_months)].copy()
        out["monthly_revenue"] = df
        out["total_revenue"] = float(df["revenue"].sum()) if "revenue" in df.columns else 0
        out["notes"] = out.get("notes", []) + [f"تم اعتماد فترة التحليل للشهور: {', '.join(selected_months)}"]
    return out

def filter_expense_model(expense_model, selected_months):
    if not expense_model or not selected_months:
        return expense_model
    out = dict(expense_model)

    long_df = out.get("expense_long", pd.DataFrame()).copy()
    if not long_df.empty and "month" in long_df.columns:
        long_df = long_df[long_df["month"].isin(selected_months)].copy()
        out["expense_long"] = long_df
        out["total_expenses"] = float(long_df["amount"].sum()) if "amount" in long_df.columns else 0
        out["monthly_expenses"] = long_df.groupby("month", as_index=False)["amount"].sum().rename(columns={"amount": "expenses"})
        out["by_category"] = long_df.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False) if "category" in long_df.columns else pd.DataFrame()
        out["top_expenses"] = long_df.groupby(["account_name", "category"], as_index=False)["amount"].sum().sort_values("amount", ascending=False).head(10) if {"account_name","category"}.issubset(long_df.columns) else pd.DataFrame()
        out["notes"] = out.get("notes", []) + [f"تم اعتماد فترة التحليل للشهور: {', '.join(selected_months)}"]
    return out
