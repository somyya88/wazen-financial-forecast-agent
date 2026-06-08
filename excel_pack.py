from io import BytesIO
import pandas as pd

def build_excel_pack(file_rows, revenue_model, expense_model, financial_model, validation_checks) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book

        header_fmt = workbook.add_format({
            "bold": True,
            "font_color": "white",
            "bg_color": "#17479E",
            "border": 1,
            "align": "center",
        })
        money_fmt = workbook.add_format({"num_format": "#,##0.00", "border": 1})
        text_fmt = workbook.add_format({"border": 1})
        title_fmt = workbook.add_format({"bold": True, "font_size": 16, "font_color": "#17479E"})

        # Executive Summary
        summary = pd.DataFrame([
            ["Revenue / الإيرادات", financial_model.get("revenue", 0)],
            ["Expenses / المصاريف", financial_model.get("expenses", 0)],
            ["Preliminary Profit / ربح أولي", financial_model.get("gross_profit_preliminary", 0)],
            ["Preliminary Margin / هامش أولي", financial_model.get("net_margin_preliminary", 0)],
            ["Note", financial_model.get("note", "")],
        ], columns=["Metric", "Value"])
        summary.to_excel(writer, sheet_name="Executive Summary", index=False)
        ws = writer.sheets["Executive Summary"]
        ws.write(0, 0, "Executive Summary", title_fmt)
        ws.set_column("A:A", 32)
        ws.set_column("B:B", 22)

        # Source Roles
        pd.DataFrame(file_rows).to_excel(writer, sheet_name="Source Roles", index=False)

        # Revenue
        if revenue_model and not revenue_model.get("monthly_revenue", pd.DataFrame()).empty:
            revenue_model["monthly_revenue"].to_excel(writer, sheet_name="Revenue", index=False)

        # Expenses
        if expense_model:
            if not expense_model.get("monthly_expenses", pd.DataFrame()).empty:
                expense_model["monthly_expenses"].to_excel(writer, sheet_name="Monthly Expenses", index=False)
            if not expense_model.get("by_category", pd.DataFrame()).empty:
                expense_model["by_category"].to_excel(writer, sheet_name="Expense Structure", index=False)
            if not expense_model.get("top_expenses", pd.DataFrame()).empty:
                expense_model["top_expenses"].to_excel(writer, sheet_name="Top Expenses", index=False)

        # Data Quality
        pd.DataFrame(validation_checks).to_excel(writer, sheet_name="Data Quality", index=False)

        # Glossary
        glossary = pd.DataFrame([
            ["الإيرادات", "Revenue", "الدخل الناتج عن النشاط الرئيسي", "Sum of official revenue source", "أساس قياس النمو"],
            ["المصاريف", "Expenses", "تكاليف ومصاريف التشغيل", "Sum of official expense source", "تؤثر على الربحية والتعادل"],
            ["نقطة التعادل", "Break-even", "مستوى الإيراد الذي يغطي التكاليف", "Fixed Costs / Contribution Margin", "تحدد الحد الأدنى المطلوب للبيع"],
            ["هامش الربح", "Profit Margin", "نسبة الربح إلى الإيراد", "Profit / Revenue", "يقيس كفاءة الربحية"],
        ], columns=["العربي", "English", "المعنى المبسط", "المعادلة", "لماذا يهم؟"])
        glossary.to_excel(writer, sheet_name="Glossary", index=False)

        # Apply simple formatting
        for sheet_name, worksheet in writer.sheets.items():
            worksheet.freeze_panes(1, 0)
            worksheet.set_tab_color("#17479E")
            try:
                worksheet.right_to_left()
            except Exception:
                pass

    output.seek(0)
    return output.read()
