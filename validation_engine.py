import pandas as pd
from core.source_roles import validate_source_roles

def validate_project(file_rows: list[dict], revenue_model: dict | None = None, expense_model: dict | None = None, tb_model: dict | None = None) -> list[dict]:
    checks = []

    for warning in validate_source_roles(file_rows):
        checks.append({"level": "warning", "check": "Source Roles", "message": warning})

    official_revenue = [r for r in file_rows if r.get("selected_role") == "official_revenue_source"]
    if len(official_revenue) == 1:
        checks.append({"level": "success", "check": "Revenue Source", "message": f"تم اعتماد ملف الإيرادات الرسمي: {official_revenue[0]['file_name']}"})

    if revenue_model:
        total = revenue_model.get("total_revenue", 0)
        if total <= 0:
            checks.append({"level": "error", "check": "Revenue Value", "message": "قيمة الإيرادات صفر أو غير مقروءة."})
        else:
            checks.append({"level": "success", "check": "Revenue Value", "message": f"تم استخراج إيرادات بقيمة {total:,.2f}."})
        for note in revenue_model.get("notes", []):
            checks.append({"level": "info", "check": "Revenue Notes", "message": note})

    if expense_model:
        total = expense_model.get("total_expenses", 0)
        if total <= 0:
            checks.append({"level": "warning", "check": "Expense Value", "message": "لم يتم استخراج مصاريف واضحة."})
        else:
            checks.append({"level": "success", "check": "Expense Value", "message": f"تم استخراج مصاريف بقيمة {total:,.2f}."})
        for note in expense_model.get("notes", []):
            checks.append({"level": "info", "check": "Expense Notes", "message": note})

    # Compare with TB if available
    if tb_model and revenue_model and not tb_model.get("summary", pd.DataFrame()).empty:
        summary = tb_model["summary"]
        tb_revenue = summary.loc[summary["category"].isin(["Operating Revenue", "Other Revenue"]), "credit"].sum()
        if tb_revenue:
            app_revenue = revenue_model.get("total_revenue", 0)
            diff = app_revenue - tb_revenue
            diff_pct = abs(diff) / tb_revenue if tb_revenue else 0
            level = "success" if diff_pct <= 0.05 else "warning"
            checks.append({
                "level": level,
                "check": "Revenue vs Trial Balance",
                "message": f"فرق الإيرادات بين المصدر الرسمي وميزان المراجعة: {diff:,.2f} ({diff_pct:.1%})."
            })

    return checks
