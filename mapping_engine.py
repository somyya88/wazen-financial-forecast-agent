import pandas as pd

CATEGORY_OPTIONS = [
    "COGS",
    "Payroll",
    "Marketing",
    "Rent",
    "Maintenance",
    "Fuel",
    "Spare Parts",
    "Depreciation",
    "Finance Costs",
    "Bank Charges",
    "Admin Opex",
    "Selling Opex",
    "Other Opex",
]

COST_BEHAVIOR_OPTIONS = [
    "Fixed",
    "Variable",
    "Semi-variable",
]

DEFAULT_COST_BEHAVIOR = {
    "COGS": "Variable",
    "Fuel": "Variable",
    "Marketing": "Variable",
    "Maintenance": "Semi-variable",
    "Spare Parts": "Variable",
    "Payroll": "Fixed",
    "Rent": "Fixed",
    "Depreciation": "Fixed",
    "Finance Costs": "Fixed",
    "Bank Charges": "Variable",
    "Admin Opex": "Fixed",
    "Selling Opex": "Semi-variable",
    "Other Opex": "Fixed",
}

TRANSPORT_DIRECT_KEYWORDS = [
    "وقود", "ديزل", "بنزين", "زيوت", "صيانة", "قطع غيار", "تأمين سيارات",
    "تأمين المركبات", "ترخيص", "تراخيص", "سائق", "سائقين", "tracking",
    "تتبع", "مقطورة", "قاطرة", "إطارات", "اطارات"
]

def suggest_category_for_transport(account_name: str, current_category: str) -> str:
    text = str(account_name).lower()
    if any(k.lower() in text for k in TRANSPORT_DIRECT_KEYWORDS):
        if "صيانة" in text:
            return "Maintenance"
        if "قطع" in text or "غيار" in text:
            return "Spare Parts"
        if "وقود" in text or "ديزل" in text or "بنزين" in text or "زيوت" in text:
            return "Fuel"
        return "COGS"

    if current_category == "Interest":
        return "Finance Costs"
    return current_category if current_category in CATEGORY_OPTIONS else "Other Opex"

def build_expense_mapping(expense_model: dict, industry: str = "") -> pd.DataFrame:
    exp_long = expense_model.get("expense_long", pd.DataFrame()) if expense_model else pd.DataFrame()
    if exp_long.empty:
        return pd.DataFrame(columns=[
            "account_name", "current_category", "user_category", "cost_behavior", "amount"
        ])

    grouped = (
        exp_long.groupby(["account_name", "category"], as_index=False)["amount"]
        .sum()
        .sort_values("amount", ascending=False)
    )
    rows = []
    for _, row in grouped.iterrows():
        current = row["category"]
        suggested = suggest_category_for_transport(row["account_name"], current)
        behavior = DEFAULT_COST_BEHAVIOR.get(suggested, "Fixed")
        rows.append({
            "account_name": row["account_name"],
            "current_category": current,
            "user_category": suggested,
            "cost_behavior": behavior,
            "amount": float(row["amount"]),
        })
    return pd.DataFrame(rows)

def apply_expense_mapping(expense_model: dict, mapping_df: pd.DataFrame) -> dict:
    if not expense_model or mapping_df is None or mapping_df.empty:
        return expense_model

    out = dict(expense_model)
    exp_long = out.get("expense_long", pd.DataFrame()).copy()
    if exp_long.empty:
        return out

    clean_map = mapping_df.copy()
    clean_map = clean_map[["account_name", "user_category", "cost_behavior"]].drop_duplicates("account_name")

    exp_long = exp_long.merge(clean_map, on="account_name", how="left")
    exp_long["category"] = exp_long["user_category"].fillna(exp_long["category"])
    exp_long["cost_behavior"] = exp_long["cost_behavior"].fillna(exp_long["category"].map(DEFAULT_COST_BEHAVIOR)).fillna("Fixed")
    exp_long = exp_long.drop(columns=["user_category"], errors="ignore")

    out["expense_long"] = exp_long
    out["total_expenses"] = float(exp_long["amount"].sum()) if "amount" in exp_long.columns else 0
    out["monthly_expenses"] = exp_long.groupby("month", as_index=False)["amount"].sum().rename(columns={"amount": "expenses"})
    out["by_category"] = exp_long.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
    out["by_cost_behavior"] = exp_long.groupby("cost_behavior", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
    out["top_expenses"] = (
        exp_long.groupby(["account_name", "category", "cost_behavior"], as_index=False)["amount"]
        .sum()
        .sort_values("amount", ascending=False)
        .head(10)
    )
    out["notes"] = out.get("notes", []) + ["تم تطبيق Expense Mapping المعتمد من المستخدم على التصنيف المالي."]
    return out
