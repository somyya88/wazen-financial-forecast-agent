import streamlit as st
import pandas as pd

from config import APP_NAME, SOURCE_ROLES, REVENUE_DEFINITIONS, ANALYSIS_MODES
from data_reader import read_excel_file
from file_detector import detect_file_type
from source_roles import suggest_role
from revenue_engine import build_revenue_model
from expense_engine import build_expense_model
from trial_balance_engine import parse_trial_balance
from validation_engine import validate_project
from financial_model import build_basic_financial_model
from period_engine import months_from_revenue_model, months_from_expense_model, common_months, filter_revenue_model, filter_expense_model
from financial_statement_engine import build_pnl, monthly_pnl
from ratio_engine import build_ratios
from breakeven_engine import build_breakeven
from forecast_engine import build_forecast
from glossary_engine import build_glossary
from mapping_engine import build_expense_mapping, apply_expense_mapping, CATEGORY_OPTIONS, COST_BEHAVIOR_OPTIONS
from analysis_router import tabs_for_mode
from theme import apply_theme
from cards import kpi_card, section_header, message_box
from charts import line_chart, bar_chart, pie_chart
from excel_pack import build_excel_pack

st.set_page_config(page_title=APP_NAME, page_icon="📊", layout="wide")
apply_theme()

if "files" not in st.session_state:
    st.session_state.files = []
if "file_rows" not in st.session_state:
    st.session_state.file_rows = []
if "models" not in st.session_state:
    st.session_state.models = {}
if "selected_months" not in st.session_state:
    st.session_state.selected_months = []
if "expense_mapping" not in st.session_state:
    st.session_state.expense_mapping = None
if "expense_mapping_saved" not in st.session_state:
    st.session_state.expense_mapping_saved = False
if "mapping_signature" not in st.session_state:
    st.session_state.mapping_signature = None
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

st.markdown('<h1 class="main-title">Wazen CFO Intelligence Agent V8.6.1</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">حوّل ملفاتك المالية إلى نموذج CFO يمنع تكرار الإيرادات ويقرأ المصاريف ويجهّز لوحة قرار تنفيذية.</p>', unsafe_allow_html=True)

if st.button("تحديث / مسح النموذج السابق"):
    st.session_state.files = []
    st.session_state.file_rows = []
    st.session_state.models = {}
    st.session_state.selected_months = []
    st.session_state.expense_mapping = None
    st.session_state.expense_mapping_saved = False
    st.session_state.mapping_signature = None
    st.session_state.uploader_key += 1
    st.rerun()


with st.sidebar:
    st.markdown("## مراحل العمل")
    st.markdown("""
    1. إعداد الشركة  
    2. رفع الملفات  
    3. تحديد أدوار المصادر  
    4. تعريف الإيراد  
    5. جودة البيانات  
    6. Dashboard  
    7. Export  
    """)
    st.divider()
    company_name = st.text_input("اسم الشركة", value="Wazen Client")
    industry = st.text_input("نوع النشاط", value="تأجير قاطرات ومقطورات")
    analysis_mode = st.selectbox("نوع التحليل", ANALYSIS_MODES)
    revenue_definition = st.selectbox("تعريف الإيراد", REVENUE_DEFINITIONS)

section_header("1. رفع الملفات واكتشاف نوعها")

uploaded_files = st.file_uploader(
    "ارفع ملفات Excel المالية",
    type=["xlsx", "xls"],
    accept_multiple_files=True,
    key=f"financial_files_uploader_{st.session_state.uploader_key}",
    help="إذا لم تظهر الملفات بعد الاختيار، اضغطي زر تحديث / مسح النموذج السابق ثم جرّبي السحب والإفلات."
)

if not uploaded_files:
    st.caption("ملاحظة: بعد اختيار الملفات يجب أن تظهر أسماؤها هنا. إذا لم تظهر، اضغطي زر تحديث / مسح النموذج السابق أعلى الصفحة.")

if uploaded_files:
    st.success(f"تم اختيار {len(uploaded_files)} ملف/ملفات: " + "، ".join([f.name for f in uploaded_files]))

if uploaded_files and st.button("قراءة واكتشاف الملفات"):
    st.session_state.files = []
    st.session_state.file_rows = []

    errors = []
    for uploaded in uploaded_files:
        data = read_excel_file(uploaded)

        if data.get("error"):
            record = {
                "file_name": data["file_name"],
                "sheets": data.get("sheets", {}),
                "primary_df": data.get("primary_df", pd.DataFrame()),
                "detected_type": "unknown",
                "confidence": 0.0,
                "reasons": [data["error"]],
                "suggested_role": "ignored",
                "selected_role": "ignored",
                "read_error": data["error"],
                "repaired": False,
            }
            st.session_state.files.append(record)
            errors.append(f"{data['file_name']}: {data['error']}")
            continue

        detection = detect_file_type(data["primary_df"])
        role = suggest_role(detection.file_type)

        record = {
            "file_name": data["file_name"],
            "sheets": data["sheets"],
            "primary_df": data["primary_df"],
            "detected_type": detection.file_type,
            "confidence": detection.confidence,
            "reasons": detection.reasons,
            "suggested_role": role,
            "selected_role": role,
            "read_error": None,
            "repaired": data.get("repaired", False),
        }
        st.session_state.files.append(record)

    if errors:
        st.warning("تم رفع بعض الملفات لكن تعذر قراءة بعضها. راجعي التنبيهات تحت كل ملف.")
    else:
        st.success("تمت قراءة الملفات واكتشاف أنواعها.")

if st.session_state.files:
    section_header("2. تحديد دور كل ملف")

    updated_rows = []
    for i, record in enumerate(st.session_state.files):
        with st.container():
            c1, c2, c3, c4 = st.columns([3, 2, 1, 3])
            c1.markdown(f"**{record['file_name']}**")
            c2.markdown(f"`{record['detected_type']}`")
            c3.markdown(f"{record['confidence']:.0%}")
            selected = c4.selectbox(
                "دور الملف",
                SOURCE_ROLES,
                index=SOURCE_ROLES.index(record["selected_role"]) if record["selected_role"] in SOURCE_ROLES else 0,
                key=f"role_{i}",
            )
            record["selected_role"] = selected
            updated_rows.append({
                "file_name": record["file_name"],
                "detected_type": record["detected_type"],
                "confidence": record["confidence"],
                "suggested_role": record["suggested_role"],
                "selected_role": selected,
            })
            if record.get("repaired"):
                message_box("تم إصلاح ملف Excel تلقائياً بسبب مشكلة في ملف الأنماط Styles XML.", "info")
            if record.get("read_error"):
                message_box(record["read_error"], "warning")
            with st.expander("معاينة أول 5 صفوف"):
                if record["primary_df"].empty:
                    st.info("لا توجد بيانات قابلة للعرض لهذا الملف.")
                else:
                    st.dataframe(record["primary_df"].head(), use_container_width=True)

    st.session_state.file_rows = updated_rows

    role_warnings = []
    official_revenue_count = sum(1 for r in updated_rows if r["selected_role"] == "official_revenue_source")
    if official_revenue_count > 1:
        role_warnings.append("تم اختيار أكثر من مصدر رسمي للإيرادات. يجب اختيار ملف واحد فقط.")
    elif official_revenue_count == 0:
        role_warnings.append("لم يتم اختيار مصدر رسمي للإيرادات بعد.")

    revenue_like_count = sum(1 for r in updated_rows if r["detected_type"] in ["monthly_sales_wide", "item_sales", "invoice_sales", "trial_balance"])
    if revenue_like_count > 1:
        role_warnings.append("تم اكتشاف أكثر من ملف مرتبط بالإيرادات. لن يتم جمعها تلقائياً.")

    for w in role_warnings:
        message_box(w, "warning")

    section_header("3. تأكيد فترة التحليل")

    readable_files_preview = [r for r in st.session_state.files if not r.get("read_error")]
    revenue_preview_record = next((r for r in readable_files_preview if r["selected_role"] == "official_revenue_source"), None)
    expense_preview_record = next((r for r in readable_files_preview if r["selected_role"] == "official_expense_source"), None)

    preview_revenue_model = build_revenue_model(revenue_preview_record, revenue_definition) if revenue_preview_record else None
    preview_expense_model = build_expense_model(expense_preview_record, preview_revenue_model.get("total_revenue", 0) if preview_revenue_model else 0) if expense_preview_record else None

    revenue_months = months_from_revenue_model(preview_revenue_model)
    expense_months = months_from_expense_model(preview_expense_model)
    suggested_months = common_months(revenue_months, expense_months)

    st.markdown(f"**شهور الإيرادات المكتشفة:** {', '.join(revenue_months) if revenue_months else 'غير متاح'}")
    st.markdown(f"**شهور المصاريف المكتشفة:** {', '.join(expense_months) if expense_months else 'غير متاح'}")
    st.markdown(f"**الفترة المقترحة للتحليل:** {', '.join(suggested_months) if suggested_months else 'غير متاح'}")

    selected_months = st.multiselect(
        "اعتمدي شهور التحليل",
        options=suggested_months or revenue_months or expense_months,
        default=st.session_state.selected_months or suggested_months or revenue_months or expense_months,
        help="الإيجنت يقرأ الشهور تلقائياً، لكن يجب اعتماد الفترة لتجنب دخول شهر غير مكتمل."
    )
    st.session_state.selected_months = selected_months

    if revenue_months and expense_months and set(revenue_months) != set(expense_months):
        message_box("يوجد اختلاف بين شهور الإيرادات والمصاريف. تم اقتراح الشهور المشتركة فقط.", "warning")

    section_header("4. تصنيف المصاريف Expense Mapping")

    if preview_expense_model and not preview_expense_model.get("expense_long", pd.DataFrame()).empty:
        # Stable account signature: regenerate suggested mapping only when the expense accounts change.
        initial_mapping = build_expense_mapping(preview_expense_model, industry)
        current_signature = "|".join(initial_mapping["account_name"].astype(str).tolist())

        if st.session_state.mapping_signature != current_signature:
            st.session_state.expense_mapping = initial_mapping.copy()
            st.session_state.expense_mapping_saved = False
            st.session_state.mapping_signature = current_signature

        st.info("عدّلي التصنيف ثم اضغطي **حفظ Expense Mapping**. زر إعادة التوليد يمسح تعديلاتك ويعيد التصنيف الآلي فقط.")

        c_map1, c_map2, c_map3 = st.columns([1, 1, 2])
        with c_map1:
            if st.button("إعادة توليد التصنيف المقترح"):
                st.session_state.expense_mapping = initial_mapping.copy()
                st.session_state.expense_mapping_saved = False
                st.warning("تمت إعادة توليد التصنيف المقترح. راجعي الجدول ثم اضغطي حفظ.")
        with c_map2:
            if st.session_state.expense_mapping_saved:
                st.success("تم حفظ التصنيف")
            else:
                st.warning("التصنيف غير محفوظ بعد")

        with st.form("expense_mapping_form"):
            edited_mapping = st.data_editor(
                st.session_state.expense_mapping,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "account_name": st.column_config.TextColumn("الحساب", disabled=True),
                    "current_category": st.column_config.TextColumn("التصنيف الحالي", disabled=True),
                    "user_category": st.column_config.SelectboxColumn("التصنيف المعتمد", options=CATEGORY_OPTIONS, required=True),
                    "cost_behavior": st.column_config.SelectboxColumn("نوع التكلفة", options=COST_BEHAVIOR_OPTIONS, required=True),
                    "amount": st.column_config.NumberColumn("المبلغ", format="%.2f", disabled=True),
                },
                key="expense_mapping_editor_v83",
                num_rows="fixed",
            )

            save_mapping = st.form_submit_button("حفظ Expense Mapping")

        if save_mapping:
            st.session_state.expense_mapping = edited_mapping.copy()
            st.session_state.expense_mapping_saved = True
            st.success("تم حفظ Expense Mapping. يمكنك الآن بناء النموذج المالي.")

        st.caption("ملاحظة: التعديلات داخل الجدول لا تدخل في الحسابات إلا بعد الضغط على زر الحفظ.")
    else:
        message_box("لا توجد مصاريف كافية لبناء Expense Mapping.", "warning")

    if preview_expense_model is not None and not st.session_state.expense_mapping_saved:
        message_box("يجب حفظ Expense Mapping قبل بناء النموذج حتى لا يرجع التصنيف للتصنيف المقترح.", "warning")

    if st.button("بناء النموذج المالي الأولي", disabled=(preview_expense_model is not None and not st.session_state.expense_mapping_saved)):
        readable_files = [r for r in st.session_state.files if not r.get("read_error")]
        revenue_record = next((r for r in readable_files if r["selected_role"] == "official_revenue_source"), None)
        expense_record = next((r for r in readable_files if r["selected_role"] == "official_expense_source"), None)
        tb_record = next((r for r in readable_files if r["selected_role"] == "validation_source" and r["detected_type"] == "trial_balance"), None)

        revenue_model = build_revenue_model(revenue_record, revenue_definition) if revenue_record else None
        expense_model = build_expense_model(expense_record, revenue_model.get("total_revenue", 0) if revenue_model else 0) if expense_record else None

        # Apply user-approved expense mapping before period filtering and financial modeling.
        if expense_model and st.session_state.expense_mapping is not None and st.session_state.expense_mapping_saved:
            expense_model = apply_expense_mapping(expense_model, st.session_state.expense_mapping)

        # Apply confirmed analysis period.
        confirmed_months = st.session_state.selected_months
        revenue_model = filter_revenue_model(revenue_model, confirmed_months) if revenue_model else None
        expense_model = filter_expense_model(expense_model, confirmed_months) if expense_model else None

        revenue_total = revenue_model.get("total_revenue", 0) if revenue_model else 0
        if expense_model and revenue_total:
            expense_model["expense_ratio"] = expense_model.get("total_expenses", 0) / revenue_total

        tb_model = parse_trial_balance(tb_record) if tb_record else None
        financial_model = build_basic_financial_model(revenue_model, expense_model)
        validation_checks = validate_project(updated_rows, revenue_model, expense_model, tb_model)

        pnl_model = build_pnl(revenue_model, expense_model, tb_model)
        monthly_pnl_model = monthly_pnl(revenue_model, expense_model)
        ratio_model = build_ratios(pnl_model, expense_model)
        breakeven_model = build_breakeven(pnl_model, expense_model)
        forecast_model, forecast_note = build_forecast(monthly_pnl_model)
        glossary_model = build_glossary()

        st.session_state.models = {
            "revenue_model": revenue_model,
            "expense_model": expense_model,
            "tb_model": tb_model,
            "financial_model": financial_model,
            "validation_checks": validation_checks,
            "pnl_model": pnl_model,
            "monthly_pnl_model": monthly_pnl_model,
            "ratio_model": ratio_model,
            "breakeven_model": breakeven_model,
            "forecast_model": forecast_model,
            "forecast_note": forecast_note,
            "glossary_model": glossary_model,
            "confirmed_months": confirmed_months,
            "expense_mapping": st.session_state.expense_mapping,
        }
        st.success("تم بناء النموذج المالي الأولي.")

if st.session_state.models:
    models = st.session_state.models
    revenue_model = models.get("revenue_model")
    expense_model = models.get("expense_model")
    financial_model = models.get("financial_model")
    validation_checks = models.get("validation_checks")
    pnl_model = models.get("pnl_model", {})
    monthly_pnl_model = models.get("monthly_pnl_model", pd.DataFrame())
    ratio_model = models.get("ratio_model", {})
    breakeven_model = models.get("breakeven_model", {})
    forecast_model = models.get("forecast_model", pd.DataFrame())
    glossary_model = models.get("glossary_model", pd.DataFrame())
    expense_mapping_model = models.get("expense_mapping", pd.DataFrame())

    section_header("3. فحص جودة البيانات")

    for check in validation_checks:
        message_box(f"**{check['check']}** — {check['message']}", check["level"])

    section_header("5. Dashboard أولي")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Revenue / الإيرادات", f"{pnl_model.get('revenue', 0):,.0f}", "من مصدر الإيرادات الرسمي فقط")
    with c2:
        kpi_card("EBITDA / الربح التشغيلي", f"{pnl_model.get('ebitda', 0):,.0f}", "بعد فصل COGS وOpex مبدئياً")
    with c3:
        kpi_card("Net Profit / صافي الربح", f"{pnl_model.get('net_profit', 0):,.0f}", "حسب التصنيف الحالي")
    with c4:
        kpi_card("Health Score / الصحة المالية", f"{ratio_model.get('financial_health_score', 0):.0f}/100", ratio_model.get("biggest_risk", ""))

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        kpi_card("Expenses / المصاريف", f"{pnl_model.get('total_expenses', 0):,.0f}", "من مصدر المصاريف الرسمي")
    with c6:
        kpi_card("Break-even / إيراد التعادل", f"{breakeven_model.get('breakeven_revenue', 0):,.0f}", "تقدير أولي")
    with c7:
        kpi_card("Break-even Gap / فجوة التعادل", f"{breakeven_model.get('breakeven_gap', 0):,.0f}", "الإيرادات الحالية - التعادل")
    with c8:
        kpi_card("Next Decision / القرار القادم", "", ratio_model.get("next_decision", ""))

    active_tabs = tabs_for_mode(analysis_mode)
    section_header("6. الصفحات المفعلة حسب نوع التحليل")
    st.write(" / ".join(active_tabs))

    tabs = st.tabs(active_tabs)

    for idx, tab_name in enumerate(active_tabs):
        with tabs[idx]:
            if tab_name in ["Dashboard", "Revenue"]:
                st.subheader("تحليل الإيرادات")
                if revenue_model and not revenue_model.get("monthly_revenue", pd.DataFrame()).empty:
                    st.dataframe(revenue_model["monthly_revenue"], use_container_width=True)
                    line_chart(revenue_model["monthly_revenue"], "month", "revenue", "Revenue Trend")
                else:
                    st.info("لا توجد بيانات إيرادات كافية.")

            elif tab_name == "P&L":
                st.subheader("قائمة الدخل")
                st.info(pnl_model.get("note", ""))
                st.dataframe(pnl_model.get("pnl", pd.DataFrame()), use_container_width=True)
                if not monthly_pnl_model.empty:
                    st.markdown("#### الربحية الشهرية")
                    st.dataframe(monthly_pnl_model, use_container_width=True)
                    line_chart(monthly_pnl_model, "month", "preliminary_profit", "Monthly Profitability")

            elif tab_name in ["Ratios"]:
                st.subheader("تحليل النسب")
                ratios_df = ratio_model.get("ratios", pd.DataFrame())
                if not ratios_df.empty:
                    show = ratios_df.copy()
                    show["Value"] = show["Value"].apply(lambda x: f"{x:.1%}")
                    st.dataframe(show, use_container_width=True)
                message_box(ratio_model.get("biggest_risk", ""), "warning")
                message_box(ratio_model.get("next_decision", ""), "info")

            elif tab_name == "Expense Mapping":
                st.subheader("Expense Mapping المعتمد")
                if expense_mapping_model is not None and not expense_mapping_model.empty:
                    st.dataframe(expense_mapping_model, use_container_width=True)
                else:
                    st.info("لا توجد خريطة تصنيف معتمدة.")

            elif tab_name in ["Expenses", "Top Expenses", "Cost Structure"]:
                st.subheader("تحليل المصاريف")
                if expense_model:
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("#### المصاريف الشهرية")
                        st.dataframe(expense_model.get("monthly_expenses", pd.DataFrame()), use_container_width=True)
                        bar_chart(expense_model.get("monthly_expenses", pd.DataFrame()), "month", "expenses", "Monthly Expenses")
                    with c2:
                        st.markdown("#### هيكل المصاريف")
                        st.dataframe(expense_model.get("by_category", pd.DataFrame()), use_container_width=True)
                        pie_chart(expense_model.get("by_category", pd.DataFrame()), "category", "amount", "Expense Structure")
                    st.markdown("#### أكبر 10 مصاريف")
                    st.dataframe(expense_model.get("top_expenses", pd.DataFrame()), use_container_width=True)
                else:
                    st.info("لم يتم اختيار أو قراءة مصدر مصاريف رسمي.")

            elif tab_name == "Break-even":
                st.subheader("تحليل نقطة التعادل")
                st.info(breakeven_model.get("note", ""))
                st.dataframe(breakeven_model.get("summary", pd.DataFrame()), use_container_width=True)
                st.markdown("#### السيناريوهات")
                st.dataframe(breakeven_model.get("scenarios", pd.DataFrame()), use_container_width=True)

            elif tab_name == "Forecast":
                st.subheader("التوقعات والسيناريوهات")
                st.info(models.get("forecast_note", ""))
                st.dataframe(forecast_model, use_container_width=True)
                if not forecast_model.empty:
                    line_chart(forecast_model, "month", "forecast_profit", "Forecast Profit by Scenario")

            elif tab_name == "Glossary":
                st.subheader("قاموس المصطلحات المالية")
                st.dataframe(glossary_model, use_container_width=True)

            elif tab_name == "Export":
                st.subheader("تصدير Excel CFO Pack")
                excel_bytes = build_excel_pack(
                    st.session_state.file_rows,
                    revenue_model,
                    expense_model,
                    financial_model,
                    validation_checks,
                    pnl_model=pnl_model,
                    ratio_model=ratio_model,
                    breakeven_model=breakeven_model,
                    forecast_model=forecast_model,
                    glossary_model=glossary_model,
                    confirmed_months=models.get("confirmed_months", []),
                    expense_mapping=expense_mapping_model,
                )
                st.download_button(
                    "تحميل Excel CFO Pack",
                    data=excel_bytes,
                    file_name="wazen_cfo_pack_v8.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
