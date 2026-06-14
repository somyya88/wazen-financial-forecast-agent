from io import BytesIO
import pandas as pd

def build_excel_pack(
    file_rows,
    revenue_model,
    expense_model,
    financial_model,
    validation_checks,
    pnl_model=None,
    ratio_model=None,
    breakeven_model=None,
    forecast_model=None,
    glossary_model=None,
    confirmed_months=None,
    expense_mapping=None,
    tb_model=None,
    source_truth_report=None,
    comprehensive_model=None,
) -> bytes:
    output = BytesIO()
    financial_model = financial_model or {}
    validation_checks = validation_checks or []
    pnl_model = pnl_model or {}
    ratio_model = ratio_model or {}
    breakeven_model = breakeven_model or {}
    forecast_model = forecast_model if forecast_model is not None else pd.DataFrame()
    glossary_model = glossary_model if glossary_model is not None else pd.DataFrame()
    confirmed_months = confirmed_months or []
    expense_mapping = expense_mapping if expense_mapping is not None else pd.DataFrame()
    tb_model = tb_model or {}
    source_truth_report = source_truth_report or {}
    comprehensive_model = comprehensive_model or {}

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book

        title_fmt = workbook.add_format({"bold": True, "font_size": 16, "font_color": "#17479E"})
        header_fmt = workbook.add_format({
            "bold": True, "font_color": "white", "bg_color": "#17479E",
            "border": 1, "align": "center"
        })
        money_fmt = workbook.add_format({"num_format": "#,##0.00", "border": 1})
        pct_fmt = workbook.add_format({"num_format": "0.0%", "border": 1})
        text_fmt = workbook.add_format({"border": 1, "text_wrap": True})
        orange_fmt = workbook.add_format({"bold": True, "font_color": "#111827", "bg_color": "#FAA61A", "border": 1})

        # Executive Summary
        summary = pd.DataFrame([
            ["Analysis Period / فترة التحليل", ", ".join(confirmed_months)],
            ["Revenue / الإيرادات", pnl_model.get("revenue", financial_model.get("revenue", 0))],
            ["COGS / تكلفة الإيراد", pnl_model.get("cogs", 0)],
            ["TB Purchases Adjustment / مشتريات من ميزان المراجعة", pnl_model.get("tb_purchases_adjustment", 0)],
            ["Gross Profit / مجمل الربح", pnl_model.get("gross_profit", 0)],
            ["Opex / المصاريف التشغيلية", pnl_model.get("opex", 0)],
            ["EBITDA", pnl_model.get("ebitda", 0)],
            ["Net Profit / صافي الربح", pnl_model.get("net_profit", financial_model.get("gross_profit_preliminary", 0))],
            ["Financial Health Score", ratio_model.get("financial_health_score", 0)],
            ["Biggest Risk", ratio_model.get("biggest_risk", "")],
            ["Next Decision", ratio_model.get("next_decision", "")],
            ["Period Days / أيام الفترة", (source_truth_report.get("period") or {}).get("period_days", "")],
            ["Period Basis / أساس الفترة", (source_truth_report.get("period") or {}).get("period_basis", "")],
            ["Source of Truth Issues / ملاحظات التدقيق", " | ".join(source_truth_report.get("issues", []) or [])],
        ], columns=["Metric", "Value"])
        summary.to_excel(writer, sheet_name="Executive Summary", index=False)
        ws = writer.sheets["Executive Summary"]
        ws.write(0, 0, "Executive Summary", title_fmt)
        ws.set_column("A:A", 34)
        ws.set_column("B:B", 55)

        # Source Roles
        pd.DataFrame(file_rows).to_excel(writer, sheet_name="Source Roles", index=False)

        # Data Quality
        pd.DataFrame(validation_checks).to_excel(writer, sheet_name="Data Quality", index=False)

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

        # Expense Mapping
        if not expense_mapping.empty:
            expense_mapping.to_excel(writer, sheet_name="Expense Mapping", index=False)

        # P&L
        pnl_df = pnl_model.get("pnl", pd.DataFrame())
        if not pnl_df.empty:
            pnl_df.to_excel(writer, sheet_name="P&L", index=False)

        # Ratios
        ratios_df = ratio_model.get("ratios", pd.DataFrame())
        if not ratios_df.empty:
            ratios_df.to_excel(writer, sheet_name="Ratio Analysis", index=False)

        # Break-even
        be_summary = breakeven_model.get("summary", pd.DataFrame())
        be_scenarios = breakeven_model.get("scenarios", pd.DataFrame())
        if not be_summary.empty:
            be_summary.to_excel(writer, sheet_name="Break-even", index=False, startrow=0)
            if not be_scenarios.empty:
                be_scenarios.to_excel(writer, sheet_name="Break-even", index=False, startrow=len(be_summary) + 3)

        # Forecast
        if not forecast_model.empty:
            forecast_model.to_excel(writer, sheet_name="Forecast", index=False)

        # Glossary
        if not glossary_model.empty:
            glossary_model.to_excel(writer, sheet_name="Glossary", index=False)

        # V13.4 Audit Trail / Source of Truth
        sot = source_truth_report.get("source_of_truth", pd.DataFrame())
        if isinstance(sot, pd.DataFrame) and not sot.empty:
            sot.to_excel(writer, sheet_name="Source of Truth", index=False)

        account_mapping_audit = source_truth_report.get("account_mapping_audit", pd.DataFrame())
        if isinstance(account_mapping_audit, pd.DataFrame) and not account_mapping_audit.empty:
            account_mapping_audit.to_excel(writer, sheet_name="Account Mapping Audit", index=False)

        raw_tb = tb_model.get("tb", pd.DataFrame()) if isinstance(tb_model, dict) else pd.DataFrame()
        if isinstance(raw_tb, pd.DataFrame) and not raw_tb.empty:
            cols = [c for c in ["account_code", "account_code_norm", "account_name", "begin_debit", "begin_credit", "debit", "credit", "current_debit", "current_credit", "category"] if c in raw_tb.columns]
            raw_tb[cols].to_excel(writer, sheet_name="TB Normalized", index=False)

        comp_ratios = comprehensive_model.get("ratios", pd.DataFrame()) if isinstance(comprehensive_model, dict) else pd.DataFrame()
        if isinstance(comp_ratios, pd.DataFrame) and not comp_ratios.empty:
            comp_ratios.to_excel(writer, sheet_name="CFO Ratios Guarded", index=False)

        # Basic formatting
        for sheet_name, worksheet in writer.sheets.items():
            worksheet.freeze_panes(1, 0)
            worksheet.set_tab_color("#17479E")
            worksheet.set_column(0, 0, 22)
            worksheet.set_column(1, 1, 24)
            worksheet.set_column(2, 10, 18)
            try:
                worksheet.right_to_left()
            except Exception:
                pass

    output.seek(0)
    return output.read()
