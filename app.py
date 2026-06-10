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
from revenue_insight_engine import build_revenue_insights
from revenue_quality_engine import build_revenue_quality
from decision_quality_engine import build_formula_table, build_decision_action_plan, build_owner_ratios_summary, data_visibility_status, build_revenue_decision_table
from sector_action_engine import build_sector_safety_scorecard, build_top_5_actions, build_scorecard_summary
from executive_diagnosis_engine import build_owner_diagnosis, build_professional_actions
from sector_benchmarks import SECTOR_OPTIONS, COUNTRY_OPTIONS, get_sector_config, sector_benchmark_table, sector_notes_df
from business_explainer_engine import explain_performance_score, explain_break_even, build_sensitivity_explanations, build_expense_quality
from executive_insights_engine import build_financial_performance_scorecard, build_break_even_confidence, build_break_even_sensitivity, build_forecast_decision
from executive_statement_engine import build_executive_kpis, build_executive_income_statement, build_executive_monthly_profitability
from financial_statement_engine import build_pnl, build_management_income_statement, monthly_pnl
from ratio_engine import build_ratios
from breakeven_engine import build_breakeven
from forecast_engine import build_forecast
from glossary_engine import build_glossary
from mapping_engine import build_expense_mapping, apply_expense_mapping, CATEGORY_OPTIONS, COST_BEHAVIOR_OPTIONS
from analysis_router import tabs_for_mode
from theme import apply_theme
from cards import kpi_card, section_header, message_box
from charts import line_chart, bar_chart, pie_chart
from data_quality_engine import build_source_reconciliation, build_data_quality_score
from insights_engine import build_ratio_insights, build_breakeven_insights, build_forecast_insights, build_expense_insights, build_forecast_assumptions_table
from expense_classifier import apply_smart_classification
from mapping_ui import render_expense_mapping_editor
from display_utils import render_pnl_statement, render_monthly_profitability, render_ratios_table, render_simple_financial_table, sort_month_df, render_insight_panel, render_breakeven_summary, render_reconciliation_table, render_executive_income_statement, render_executive_monthly_profitability, render_financial_scorecard, render_sensitivity_table, render_business_explanation_table, render_sector_scorecard, render_actions_table
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
if "model_ready" not in st.session_state:
    st.session_state.model_ready = bool(st.session_state.get("models"))
if "show_setup" not in st.session_state:
    st.session_state.show_setup = False

st.markdown('<h1 class="main-title">Wazen CFO Intelligence Agent V11.3</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">حوّل ملفاتك المالية إلى نموذج CFO يمنع تكرار الإيرادات ويقرأ المصاريف ويجهّز لوحة قرار تنفيذية.</p>', unsafe_allow_html=True)

if st.session_state.get("models") and st.session_state.get("model_ready", False):
    st.session_state.show_setup = st.toggle(
        "إظهار الإعداد والتحقق",
        value=st.session_state.get("show_setup", False),
        key="show_setup_toggle",
        help="فعّل هذا الخيار فقط عند الحاجة لتعديل الملفات أو التصنيف أو فترة التحليل."
    )
else:
    st.session_state.show_setup = True


if st.button("تحديث / مسح النموذج السابق"):
    st.session_state.files = []
    st.session_state.file_rows = []
    st.session_state.models = {}
    st.session_state.selected_months = []
    st.session_state.expense_mapping = None
    st.session_state.expense_mapping_saved = False
    st.session_state.mapping_signature = None
    st.session_state.model_ready = False
    st.session_state.show_setup = True
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
    business_sector = st.selectbox(
        "القطاع الرئيسي",
        list(SECTOR_OPTIONS.keys()),
        index=0,
        help="يتم استخدام القطاع لاختيار معايير السلامة المالية المناسبة."
    )
    country = st.selectbox("البلد", COUNTRY_OPTIONS, index=0)
    activity_options = get_sector_config(business_sector)["activities"]
    activity = st.selectbox("طبيعة النشاط", activity_options, index=0)
    custom_activity = st.text_input("وصف إضافي لطبيعة النشاط", value="")
    if custom_activity.strip():
        activity = custom_activity.strip()
    industry = activity
    analysis_mode = st.selectbox("نوع التحليل", ANALYSIS_MODES)
    revenue_definition = st.selectbox("تعريف الإيراد", REVENUE_DEFINITIONS)


# EXECUTIVE_ONLY_VIEW_V102
if st.session_state.get("models") and st.session_state.get("model_ready", False) and not st.session_state.get("show_setup", False):
    models = st.session_state.models
    revenue_model = models.get("revenue_model")
    expense_model = models.get("expense_model")
    pnl_model = models.get("pnl_model", {})
    breakeven_model = models.get("breakeven_model", {})
    ratio_model = models.get("ratio_model", {})
    business_sector = locals().get("business_sector", "خدمي")
    country = locals().get("country", "السعودية")
    activity = locals().get("activity", locals().get("industry", ""))

    section_header("لوحة المؤشرات التنفيذية")
    st.caption(f"قطاع التحليل: {business_sector} | البلد: {country} | طبيعة النشاط: {activity}")

    exec_kpis = build_executive_kpis(pnl_model, expense_model)
    performance_scorecard = build_financial_performance_scorecard(pnl_model, breakeven_model)
    dash_diag = build_owner_diagnosis(pnl_model, breakeven_model, expense_model, business_sector, country, activity)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("الإيرادات التشغيلية", f"{exec_kpis.get('operating_revenue', 0):,.0f}", "إيراد النشاط الأساسي")
    with c2:
        kpi_card("صافي الربح", f"{exec_kpis.get('net_profit', 0):,.0f}", f"هامش صافي الربح {exec_kpis.get('net_margin', 0)*100:.1f}%")
    with c3:
        kpi_card("هامش الأمان", f"{breakeven_model.get('margin_of_safety', 0)*100:.1f}%", "المسافة قبل نقطة التعادل")
    with c4:
        kpi_card("مؤشر الأداء والربحية", f"{performance_scorecard.get('score', 0):.0f}/100", "مؤشر مبني على الهوامش والتعادل")

    st.markdown(f"""
    <div class="executive-brief compact">
        <div class="brief-title">الخلاصة خلال 60 ثانية</div>
        <div class="brief-text">{dash_diag['situation']}</div>
        <div class="brief-action"><strong>الإجراء الأهم الآن:</strong> {dash_diag['action']}</div>
        <div class="brief-subtext"><strong>مؤشر المتابعة:</strong> {dash_diag['next_kpi']}</div>
    </div>
    """, unsafe_allow_html=True)

    sector_scorecard_dash = build_sector_safety_scorecard(pnl_model, breakeven_model, business_sector, country, activity)
    top_action_dash = build_top_5_actions(sector_scorecard_dash)
    if top_action_dash is not None and not top_action_dash.empty:
        first_action = top_action_dash.iloc[0]
        st.warning(f"أولوية التنفيذ الأولى: {first_action['المشكلة']} — {first_action['الإجراء المطلوب']}")

    st.info("للاطلاع على الإعدادات، جودة البيانات، التصنيف، والجداول التفصيلية فعّل خيار: إظهار الإعداد والتحقق أعلى الصفحة.")
    st.stop()


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

business_sector = locals().get("business_sector", "خدمي")
country = locals().get("country", "السعودية")
activity = locals().get("activity", locals().get("business_activity", ""))

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
        "اعتماد شهور التحليل",
        options=suggested_months or revenue_months or expense_months,
        default=st.session_state.selected_months or suggested_months or revenue_months or expense_months,
        help="الإيجنت يقرأ الشهور تلقائياً، لكن يجب اعتماد الفترة لتجنب دخول شهر غير مكتمل."
    )
    st.session_state.selected_months = selected_months

    if revenue_months and expense_months and set(revenue_months) != set(expense_months):
        message_box("يوجد اختلاف بين شهور الإيرادات والمصاريف. تم اقتراح الشهور المشتركة فقط.", "warning")

    section_header("4. تصنيف المصاريف المعتمد")

    if preview_expense_model and not preview_expense_model.get("expense_long", pd.DataFrame()).empty:
        # Stable account signature: regenerate suggested mapping only when the expense accounts change.
        initial_mapping = apply_smart_classification(build_expense_mapping(preview_expense_model, industry), use_openai=True)
        current_signature = "|".join(initial_mapping["account_name"].astype(str).tolist())

        if st.session_state.mapping_signature != current_signature:
            st.session_state.expense_mapping = initial_mapping.copy()
            st.session_state.expense_mapping_saved = False
            st.session_state.mapping_signature = current_signature

        st.info("استخدم الفلاتر للوصول إلى البنود المطلوبة، ثم عدّل التصنيف أو نوع التكلفة واضغط حفظ. التصنيف يستخدم OpenAI عند توفر الربط، ثم يرتب الحسابات للتدقيق حسب قائمة الدخل: تشغيل مباشر، إداري، تسويقي، تمويلي، أخرى. يجب مراجعة التصنيف قبل اعتماد النموذج.")

        c_map1, c_map2, c_map3 = st.columns([1, 1, 2])
        with c_map1:
            if st.button("إعادة توليد التصنيف بالذكاء الصناعي"):
                st.session_state.expense_mapping = apply_smart_classification(initial_mapping.copy(), use_openai=True)
                st.session_state.expense_mapping_saved = False
                st.warning("تمت إعادة توليد التصنيف بالذكاء الصناعي. يرجى مراجعة البنود ثم حفظ التصنيف.")
        with c_map2:
            if st.session_state.expense_mapping_saved:
                st.success("تم حفظ التصنيف")
            else:
                st.warning("التصنيف غير محفوظ بعد")

        edited_mapping = render_expense_mapping_editor(
            st.session_state.expense_mapping,
            key_prefix="expense_mapping_main"
        )
        save_mapping = st.button("حفظ تصنيف المصاريف المعتمد", type="primary", key="save_expense_mapping_filtered")

        if save_mapping:
            st.session_state.expense_mapping = edited_mapping.copy()
            st.session_state.expense_mapping_saved = True
            st.success("تم حفظ تصنيف المصاريف المعتمد. يمكن الآن بناء النموذج المالي.")

        st.caption("ملاحظة: التعديلات داخل الجدول لا تدخل في الحسابات إلا بعد الضغط على زر الحفظ.")
    else:
        message_box("لا توجد مصاريف كافية لبناء تصنيف المصاريف.", "warning")

    if preview_expense_model is not None and not st.session_state.expense_mapping_saved:
        message_box("يجب حفظ تصنيف المصاريف قبل بناء النموذج حتى لا يرجع التصنيف للتصنيف المقترح.", "warning")

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
        st.session_state.model_ready = True
        st.session_state.show_setup = False
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

    exec_kpis = build_executive_kpis(pnl_model, expense_model)
    performance_scorecard = build_financial_performance_scorecard(pnl_model, breakeven_model)
    section_header("5. لوحة المؤشرات التنفيذية")
    st.caption(f"قطاع التحليل: {business_sector} | البلد: {country} | طبيعة النشاط: {activity}")

    exec_kpis = build_executive_kpis(pnl_model, expense_model)
    performance_scorecard = build_financial_performance_scorecard(pnl_model, breakeven_model)
    dash_diag = build_owner_diagnosis(pnl_model, breakeven_model, expense_model, business_sector, country, activity)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("الإيرادات التشغيلية", f"{exec_kpis.get('operating_revenue', 0):,.0f}", "إيراد النشاط الأساسي")
    with c2:
        kpi_card("صافي الربح", f"{exec_kpis.get('net_profit', 0):,.0f}", f"هامش صافي الربح {exec_kpis.get('net_margin', 0)*100:.1f}%")
    with c3:
        kpi_card("هامش الأمان", f"{breakeven_model.get('margin_of_safety', 0)*100:.1f}%", "المسافة قبل نقطة التعادل")
    with c4:
        kpi_card("مؤشر الأداء والربحية", f"{performance_scorecard.get('score', 0):.0f}/100", "مؤشر مبني على الهوامش والتعادل")

    st.markdown(f"""
    <div class="executive-brief compact">
        <div class="brief-title">الخلاصة خلال 60 ثانية</div>
        <div class="brief-text">{dash_diag['situation']}</div>
        <div class="brief-action"><strong>الإجراء الأهم الآن:</strong> {dash_diag['action']}</div>
        <div class="brief-subtext"><strong>مؤشر المتابعة:</strong> {dash_diag['next_kpi']}</div>
    </div>
    """, unsafe_allow_html=True)

    st.caption("للتفاصيل: راجع صفحات تحليل النسب، كفاءة الإنفاق، نقطة التعادل، والسيناريوهات.")

    active_tabs = tabs_for_mode(analysis_mode)
    tabs = st.tabs(active_tabs)


    for idx, tab_name in enumerate(active_tabs):
        with tabs[idx]:
            if tab_name in ["Dashboard", "لوحة المؤشرات"]:
                section_header("لوحة المؤشرات التنفيذية")
                st.caption(f"قطاع التحليل: {business_sector} | البلد: {country} | طبيعة النشاط: {activity}")

                exec_kpis = build_executive_kpis(pnl_model, expense_model)
                performance_scorecard = build_financial_performance_scorecard(pnl_model, breakeven_model)
                dash_diag = build_owner_diagnosis(pnl_model, breakeven_model, expense_model, business_sector, country, activity)

                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    kpi_card("الإيرادات التشغيلية", f"{exec_kpis.get('operating_revenue', 0):,.0f}", "إيراد النشاط الأساسي")
                with c2:
                    kpi_card("صافي الربح", f"{exec_kpis.get('net_profit', 0):,.0f}", f"هامش صافي الربح {exec_kpis.get('net_margin', 0)*100:.1f}%")
                with c3:
                    kpi_card("هامش الأمان", f"{breakeven_model.get('margin_of_safety', 0)*100:.1f}%", "المسافة قبل نقطة التعادل")
                with c4:
                    kpi_card("مؤشر الربحية", f"{min(float(performance_scorecard.get('score', 0) or 0), 85):.0f}/100", "لا يشمل السيولة والتحصيل")

                st.markdown(f"""
                <div class="executive-brief compact">
                    <div class="brief-title">الخلاصة التنفيذية</div>
                    <div class="brief-text">{dash_diag['situation']}</div>
                    <div class="brief-action"><strong>الإجراء الأهم الآن:</strong> {dash_diag['action']}</div>
                    <div class="brief-subtext"><strong>مؤشر المتابعة:</strong> {dash_diag['next_kpi']}</div>
                </div>
                """, unsafe_allow_html=True)

                st.warning("هذه اللوحة لا تحكم على السيولة والتحصيل والديون. لإكمال قراءة CFO نحتاج كشف بنك وأعمار العملاء والموردين.")

            elif tab_name in ["Revenue", "الإيرادات"]:
                section_header("تحليل الإيرادات وجودتها وجودتها")
                if revenue_model and not revenue_model.get("monthly_revenue", pd.DataFrame()).empty:
                    revenue_monthly = sort_month_df(revenue_model["monthly_revenue"], "month").copy()
                    revenue_monthly["revenue"] = pd.to_numeric(revenue_monthly["revenue"], errors="coerce").fillna(0)
                    rev_quality = build_revenue_quality(revenue_monthly)

                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        kpi_card("إجمالي الإيرادات", f"{rev_quality['cards'].get('total', 0):,.0f}", "خلال فترة التحليل")
                    with c2:
                        kpi_card("متوسط شهري محافظ", f"{rev_quality['cards'].get('avg', 0):,.0f}", "ليس ضماناً للتوسع")
                    with c3:
                        kpi_card("أعلى شهر", str(rev_quality['cards'].get('best_month', '—')), f"يمثل {rev_quality['cards'].get('max_share', 0)*100:.1f}%")
                    with c4:
                        kpi_card("استقرار الإيراد", f"{rev_quality['cards'].get('stability_score', 0):.0f}/100", str(rev_quality['cards'].get('quality_status', '—')))

                    render_insight_panel(
                        "قراءة CFO للإيرادات",
                        rev_quality["narrative"],
                        rev_quality["risk"],
                        rev_quality["action"],
                        [
                            "الإيراد الجيد ليس فقط رقماً كبيراً؛ بل يجب أن يكون قابلاً للتكرار والتحصيل.",
                            "الارتفاع في شهر واحد لا يعني نمواً مستداماً.",
                            "التوسع يجب أن يبنى على إيراد متكرر لا على شهر استثنائي."
                        ],
                    )

                    st.markdown("#### مؤشرات جودة الإيراد")
                    render_business_explanation_table(rev_quality["quality_table"])

                    line_chart(revenue_monthly, "month", "revenue", "اتجاه الإيرادات الشهرية")

                    with st.expander("عرض التفاصيل الشهرية للتدقيق فقط"):
                        render_business_explanation_table(rev_quality["monthly_table"])
                else:
                    st.info("لا توجد بيانات إيرادات شهرية كافية.")
            elif tab_name in ["Sector Safety", "معايير القطاع"]:
                section_header("معايير السلامة القطاعية")
                st.caption(f"القطاع: {business_sector} | البلد: {country} | طبيعة النشاط: {activity}")

                sector_scorecard = build_sector_safety_scorecard(pnl_model, breakeven_model, business_sector, country, activity)
                sector_summary = build_scorecard_summary(sector_scorecard, business_sector)

                render_insight_panel(
                    sector_summary["title"],
                    sector_summary["summary"],
                    sector_summary["risk"],
                    sector_summary["action"],
                    [
                        "المقارنة تتم مع معايير عملية حسب القطاع المختار وليست حكماً نهائياً.",
                        "أي مؤشر بحالة مراقبة أو خطر يجب ربطه بإجراء ومسؤول ومؤشر متابعة.",
                        "تستخدم هذه الصفحة كأساس لتوليد أولويات التنفيذ."
                    ],
                )

                st.markdown("#### مقارنة الشركة مع معيار القطاع")
                render_sector_scorecard(sector_scorecard)

                st.markdown("#### أولويات التنفيذ لهذا الشهر")
                render_actions_table(build_top_5_actions(sector_scorecard))

            elif tab_name in ["P&L", "قائمة الدخل"]:
                st.subheader("قائمة الدخل")
                st.info(pnl_model.get("note", ""))
                st.markdown("#### قائمة الدخل التنفيذية")
                st.caption("عرض إداري موحد يفصل تكلفة الإيراد عن المصاريف الإدارية والتسويقية والتمويلية.")
                render_executive_income_statement(build_executive_income_statement(pnl_model, expense_model))

                st.markdown('<a id="expense-drilldown"></a>', unsafe_allow_html=True)
                with st.expander("تفاصيل المصاريف التشغيلية من ملف المصروفات", expanded=False):
                    st.markdown('<div class="tooltip-note">هذا التفصيل تحليلي، أما رقم المصروفات الرسمي في قائمة الدخل فمن ميزان المراجعة.</div>', unsafe_allow_html=True)
                    if expense_model and not expense_model.get("by_category", pd.DataFrame()).empty:
                        exp_cat = expense_model.get("by_category", pd.DataFrame()).copy()
                        render_simple_financial_table(
                            exp_cat.rename(columns={"category": "التصنيف", "amount": "المبلغ"}),
                            columns=["التصنيف", "المبلغ"],
                            money_cols=["المبلغ"],
                        )
                    if expense_model and not expense_model.get("top_expenses", pd.DataFrame()).empty:
                        st.markdown("##### أكبر بنود المصاريف")
                        top_exp = expense_model.get("top_expenses", pd.DataFrame()).copy()
                        render_simple_financial_table(
                            top_exp.rename(columns={"account_name": "الحساب", "category": "التصنيف", "cost_behavior": "نوع التكلفة", "amount": "المبلغ"}),
                            columns=["الحساب", "التصنيف", "نوع التكلفة", "المبلغ"],
                            money_cols=["المبلغ"],
                        )

                if not monthly_pnl_model.empty:
                    st.markdown("#### الربحية الشهرية")
                    monthly_profitability_table = build_executive_monthly_profitability(monthly_pnl_model, pnl_model, expense_model)
                    render_executive_monthly_profitability(monthly_profitability_table)
                    if monthly_profitability_table is not None and not monthly_profitability_table.empty:
                        chart_df = monthly_profitability_table[["الشهر", "صافي الربح"]].copy()
                        chart_df = chart_df.rename(columns={"الشهر": "month", "صافي الربح": "net_profit"})
                        line_chart(chart_df, "month", "net_profit", "اتجاه صافي الربح الشهري")

            elif tab_name in ["Ratios"]:
                st.subheader("تحليل النسب المالية")

                summary = build_owner_ratios_summary(pnl_model, breakeven_model, expense_model)
                m_score = build_financial_performance_scorecard(pnl_model, breakeven_model)
                safe_score = min(float(m_score.get("score", 0) or 0), 85)

                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    kpi_card("الربحية المحاسبية", "جيدة" if pnl_model.get("net_profit", 0) > 0 else "تحتاج معالجة", "قراءة من قائمة الدخل")
                with c2:
                    kpi_card("السيولة والتحصيل", "غير محسوبة", "تحتاج كشف بنك وذمم")
                with c3:
                    kpi_card("ثقة القراءة", "متوسطة", "لأن السيولة والذمم غير مرفقة")
                with c4:
                    kpi_card("مؤشر الربحية", f"{safe_score:.0f}/100", "ليس مؤشراً للصحة المالية الكاملة")

                st.warning("تنبيه مهم: هذه الصفحة تقيس الربحية والتكاليف ونقطة التعادل فقط. لا تحكم على السيولة أو التحصيل أو الديون دون ملفات إضافية.")

                render_insight_panel(
                    summary["title"],
                    summary["risk"],
                    "الخطر الحقيقي لا يظهر من صافي الربح وحده؛ قد تكون الشركة رابحة محاسبياً لكنها مضغوطة نقدياً إذا تأخر التحصيل أو زادت الالتزامات الثابتة.",
                    summary["action"],
                    [
                        "أي قراءة ربحية يجب فصلها عن قراءة السيولة.",
                        "لا تعتمد قرار توسع قبل بناء توقع نقدي.",
                        "كل توصية يجب أن ترتبط برقم ومسؤول وKPI."
                    ],
                )

                st.markdown("#### كيف تم احتساب المؤشرات؟")
                render_business_explanation_table(
                    build_formula_table(pnl_model, breakeven_model, business_sector)
                )

                st.markdown("#### خطة العمل التنفيذية")
                render_business_explanation_table(
                    build_decision_action_plan(pnl_model, breakeven_model, expense_model, revenue_model.get("monthly_revenue", pd.DataFrame()) if revenue_model else pd.DataFrame())
                )

                st.markdown("#### ما الذي لا تغطيه هذه القراءة؟")
                render_business_explanation_table(data_visibility_status(st.session_state.get("models", {})))
            elif tab_name == "تصنيف المصاريف":
                st.subheader("تصنيف المصاريف المعتمد")
                if expense_mapping_model is not None and not expense_mapping_model.empty:
                    st.dataframe(expense_mapping_model, use_container_width=True)
                else:
                    st.info("لا توجد خريطة تصنيف معتمدة.")

            elif tab_name in ["Expenses", "Top Expenses", "Cost Structure"]:
                st.subheader("كفاءة الإنفاق وهيكل التكاليف")
                if expense_model:
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("#### المصاريف الشهرية")
                        monthly_exp = sort_month_df(expense_model.get("monthly_expenses", pd.DataFrame()), "month").copy()
                        render_simple_financial_table(
                            monthly_exp.rename(columns={"month": "الشهر", "expenses": "المصاريف"}),
                            columns=["الشهر", "المصاريف"],
                            money_cols=["المصاريف"],
                        )
                        bar_chart(monthly_exp, "month", "expenses", "Monthly Expenses")
                    with c2:
                        st.markdown("#### هيكل المصاريف")
                        cat_df = expense_model.get("by_category", pd.DataFrame()).copy()
                        render_simple_financial_table(
                            cat_df.rename(columns={"category": "التصنيف", "amount": "المبلغ"}),
                            columns=["التصنيف", "المبلغ"],
                            money_cols=["المبلغ"],
                        )
                        pie_chart(expense_model.get("by_category", pd.DataFrame()), "category", "amount", "Expense Structure")
                    st.markdown("#### أكبر 10 مصاريف")
                    top_df = expense_model.get("top_expenses", pd.DataFrame()).copy()
                    render_simple_financial_table(
                        top_df.rename(columns={"account_name": "الحساب", "category": "التصنيف", "cost_behavior": "نوع التكلفة", "amount": "المبلغ"}),
                        columns=["الحساب", "التصنيف", "نوع التكلفة", "المبلغ"],
                        money_cols=["المبلغ"],
                    )
                else:
                    st.info("لم يتم اختيار أو قراءة مصدر مصاريف رسمي.")

            elif tab_name in ["Break-even", "نقطة التعادل"]:
                st.subheader("نقطة التعادل وهامش الأمان")
                st.info(breakeven_model.get("note", ""))
                be_confidence = build_break_even_confidence(st.session_state.get("expense_mapping", None), None)
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    kpi_card("إيراد التعادل", f"{breakeven_model.get('break_even_revenue', breakeven_model.get('breakeven_revenue', 0)):,.0f}", "الحد الأدنى لتغطية التكاليف")
                with c2:
                    kpi_card("هامش الأمان", f"{breakeven_model.get('margin_of_safety', 0)*100:.1f}%", "المسافة قبل التعادل")
                with c3:
                    kpi_card("ثقة الحساب", be_confidence.get("label", "—"), f"{be_confidence.get('score', 0)}/100")
                with c4:
                    kpi_card("فجوة التعادل", f"{breakeven_model.get('breakeven_gap', 0):,.0f}", "الإيرادات الحالية - التعادل")

                be_explain = explain_break_even(breakeven_model, st.session_state.get("expense_mapping", None))
                st.markdown("#### تشخيص نقطة التعادل لصاحب العمل")
                be_owner_diag = build_owner_diagnosis(pnl_model, breakeven_model, expense_model, business_sector, country, activity)
                st.info(be_owner_diag["risk"])
                st.warning(be_owner_diag["action"])

                st.markdown("#### ماذا تعني نقطة التعادل؟")
                st.info(be_explain["meaning"])
                render_business_explanation_table(be_explain["formula_rows"])
                st.markdown("#### كيف تم تقييم ثقة الحساب؟")
                st.warning(f"ثقة الحساب: {be_explain['confidence_label']} — {be_explain['confidence_score']}/100")
                for _r in be_explain["confidence_reasons"]:
                    st.caption("• " + _r)

                be_insights = build_breakeven_insights(pnl_model, breakeven_model)
                render_insight_panel(
                    "تحليل التعادل وهامش الأمان",
                    be_insights["status"],
                    be_insights["risk"],
                    be_insights["decision"],
                    be_insights["bullets"],
                )
                be_summary = breakeven_model.get("summary", pd.DataFrame()).copy()
                render_breakeven_summary(be_summary)
                st.markdown("#### اختبار الحساسية")
                render_business_explanation_table(build_sensitivity_explanations(build_break_even_sensitivity(breakeven_model)), money_cols=['التكاليف الثابتة','إيراد التعادل','فجوة التعادل'], percent_cols=['هامش المساهمة'])

                st.markdown("#### السيناريوهات")
                scenarios_df = breakeven_model.get("scenarios", pd.DataFrame()).copy()
                render_simple_financial_table(
                    scenarios_df,
                    columns=["العربي", "Scenario", "Fixed Costs", "Contribution Margin", "Break-even Revenue"],
                    money_cols=["Fixed Costs", "Break-even Revenue"],
                    percent_cols=["Contribution Margin"],
                )

            elif tab_name in ["Forecast", "السيناريوهات"]:
                st.subheader("السيناريوهات المستقبلية واختبار الضغط")
                st.info(models.get("forecast_note", ""))
                forecast_decision = build_forecast_decision(forecast_model, breakeven_model)
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    kpi_card("أسوأ شهر متوقع", forecast_decision.get("worst_month", "—"), "حسب أقل ربح متوقع")
                with c2:
                    kpi_card("أكبر خسارة محتملة", f"{forecast_decision.get('worst_profit', 0):,.0f}", "في سيناريو الضغط")
                with c3:
                    kpi_card("الإيراد الآمن شهرياً", f"{forecast_decision.get('safe_revenue', 0):,.0f}", "مشتق من نقطة التعادل")
                with c4:
                    kpi_card("قرار الإدارة", "ضبط داخلي أولاً", "قبل أي التزام جديد")

                st.warning(forecast_decision.get("warning", ""))
                st.info(forecast_decision.get("decision", ""))

                forecast_insights = build_forecast_insights(forecast_model, pnl_model)
                render_insight_panel(
                    "تحليل السيناريوهات والتوقعات",
                    forecast_insights["status"],
                    forecast_insights["risk"],
                    forecast_insights["decision"],
                    forecast_insights["bullets"],
                )
                st.markdown("#### فرضيات السيناريوهات")
                render_simple_financial_table(
                    build_forecast_assumptions_table(),
                    columns=["السيناريو", "Scenario", "فرضية الإيراد", "فرضية المصاريف", "هدف السيناريو"],
                )

                if forecast_insights.get("summary_df") is not None and not forecast_insights.get("summary_df").empty:
                    st.markdown("#### ملخص السيناريوهات")
                    render_simple_financial_table(
                        forecast_insights["summary_df"],
                        columns=["السيناريو", "Scenario", "متوسط الإيراد المتوقع", "متوسط الربح المتوقع", "أقل ربح متوقع", "هامش الربح المتوقع"],
                        money_cols=["متوسط الإيراد المتوقع", "متوسط الربح المتوقع", "أقل ربح متوقع"],
                        percent_cols=["هامش الربح المتوقع"],
                    )
                if not forecast_model.empty:
                    try:
                        _worst = forecast_model.copy()
                        _worst["forecast_profit"] = pd.to_numeric(_worst["forecast_profit"], errors="coerce")
                        _worst = _worst.sort_values("forecast_profit").iloc[0]
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            kpi_card("أسوأ شهر متوقع", str(_worst.get("month", "—")), "حسب أقل ربح متوقع")
                        with c2:
                            kpi_card("أقل ربح متوقع", f"{float(_worst.get('forecast_profit', 0)):,.0f}", "اختبار ضغط للربحية")
                        with c3:
                            kpi_card("حد الإيراد الحرج", f"{float(_worst.get('forecast_revenue', 0)):,.0f}", "يحتاج مراقبة شهرية")
                    except Exception:
                        pass
                    st.markdown("#### تفاصيل التوقعات الشهرية")
                    forecast_show = forecast_model.copy()
                    render_simple_financial_table(
                        forecast_show.rename(columns={
                            "العربي": "السيناريو",
                            "month": "الشهر",
                            "forecast_revenue": "الإيراد المتوقع",
                            "forecast_expenses": "المصاريف المتوقعة",
                            "forecast_profit": "الربح المتوقع",
                            "forecast_margin": "هامش الربح المتوقع",
                        }),
                        columns=["السيناريو", "Scenario", "الشهر", "الإيراد المتوقع", "المصاريف المتوقعة", "الربح المتوقع", "هامش الربح المتوقع"],
                        money_cols=["الإيراد المتوقع", "المصاريف المتوقعة", "الربح المتوقع"],
                        percent_cols=["هامش الربح المتوقع"],
                    )
                    line_chart(forecast_model, "month", "forecast_profit", "Forecast Profit by Scenario")
                else:
                    st.info("لا توجد بيانات توقع كافية.")

            elif tab_name in ["Glossary", "القاموس"]:
                st.subheader("قاموس المصطلحات المالية")
                render_simple_financial_table(
                    glossary_model,
                    columns=["العربي", "English", "المعنى المبسط", "المعادلة", "لماذا يهم؟"],
                )

            elif tab_name in ["Export", "التصدير"]:
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
