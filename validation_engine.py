import pandas as pd
from source_roles import validate_source_roles

def validate_project(file_rows: list[dict], revenue_model: dict | None = None, expense_model: dict | None = None, tb_model: dict | None = None) -> list[dict]:
    checks = []

    for warning in validate_source_roles(file_rows):
        checks.append({"level": "warning", "check": "Source Roles", "message": warning})

    has_tb = any(r.get("selected_role") == "validation_source" and r.get("detected_type") == "trial_balance" for r in file_rows)
    if has_tb:
        checks.append({"level": "success", "check": "P&L Source", "message": "سيتم استخدام ميزان المراجعة كمصدر أساسي لإعداد قائمة الدخل، بينما تستخدم ملفات المبيعات والمصاريف للتحليل الشهري."})

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

    # Compare official revenue with reliable TB net sales metric, not raw credit totals.
    if tb_model:
        metrics_for_purchase = tb_model.get("metrics", {}) if isinstance(tb_model, dict) else {}
        tb_purchases = metrics_for_purchase.get("net_purchases")
        if tb_purchases:
            checks.append({
                "level": "info",
                "check": "Purchases from Trial Balance",
                "message": f"تم اكتشاف صافي مشتريات في ميزان المراجعة بقيمة {tb_purchases:,.2f}. سيتم استخدامها كتكلفة إيراد داعمة إذا لم تكن موجودة في تقرير المصروفات."
            })

    if tb_model and revenue_model:
        metrics = tb_model.get("metrics", {}) if isinstance(tb_model, dict) else {}
        tb_revenue = metrics.get("net_sales")
        if tb_revenue:
            app_revenue = revenue_model.get("total_revenue", 0)
            diff = app_revenue - tb_revenue
            diff_pct = abs(diff) / tb_revenue if tb_revenue else 0
            level = "success" if diff_pct <= 0.01 else ("info" if diff_pct <= 0.05 else "warning")
            checks.append({
                "level": level,
                "check": "Revenue vs Trial Balance",
                "message": f"فرق الإيرادات بين المصدر الرسمي وميزان المراجعة: {diff:,.2f} ({diff_pct:.1%})."
            })
        else:
            checks.append({
                "level": "info",
                "check": "Revenue vs Trial Balance",
                "message": "لم يتم العثور على صف صافي المبيعات في ميزان المراجعة للمطابقة."
            })

    return checks
