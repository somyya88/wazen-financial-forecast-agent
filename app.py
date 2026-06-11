from __future__ import annotations

import pandas as pd
import streamlit as st

from config import APP_NAME, SOURCE_ROLES, REVENUE_DEFINITIONS
from data_reader import read_excel_file
from file_detector import detect_file_type
from source_roles import suggest_role
from file_role_resolver import apply_role_resolution_to_record, has_liquidity_files, liquidity_files_summary

from revenue_engine import build_revenue_model
from expense_engine import build_expense_model
from trial_balance_engine import parse_trial_balance
from validation_engine import validate_project
from financial_model import build_basic_financial_model
from financial_statement_engine import build_pnl, monthly_pnl
from ratio_engine import build_ratios
from breakeven_engine import build_breakeven
from forecast_engine import build_forecast
from glossary_engine import build_glossary
from period_engine import months_from_revenue_model, months_from_expense_model, common_months, filter_revenue_model, filter_expense_model
from mapping_engine import build_expense_mapping, apply_expense_mapping
from expense_classifier import apply_smart_classification
from mapping_ui import render_expense_mapping_editor
from sector_benchmarks import SECTOR_OPTIONS, COUNTRY_OPTIONS, get_sector_config
from sector_action_engine import build_sector_safety_scorecard, build_top_5_actions, build_scorecard_summary
from executive_diagnosis_engine import build_owner_diagnosis
from executive_insights_engine import build_financial_performance_scorecard, build_forecast_decision
from executive_statement_engine import build_executive_kpis, build_executive_income_statement, build_executive_monthly_profitability
from revenue_quality_engine import build_revenue_quality
from decision_quality_engine import build_owner_ratios_summary, build_formula_table, build_decision_action_plan
from insights_engine import build_forecast_insights, build_forecast_assumptions_table
from display_utils import (
    render_simple_financial_table,
    render_business_explanation_table,
    render_executive_income_statement,
    render_executive_monthly_profitability,
    render_sector_scorecard,
    render_actions_table,
    render_insight_panel,
    render_breakeven_summary,
)
from cards import kpi_card, section_header, message_box
from charts import line_chart, bar_chart, pie_chart
from excel_pack import build_excel_pack
from theme import apply_theme

from data_readiness_v12 import build_readiness_profile, build_missing_data_recommendations
from liquidity_engine_v12 import build_liquidity_collections_model, liquidity_cfo_narrative
from scenario_engine_v12 import base_inputs_from_models, run_simple_scenario, predefined_scenarios
from action_engine_v12 import build_action_center
from period_normalization_v12 import infer_validation_end_month, trim_months_to_end


st.set_page_config(page_title=APP_NAME, page_icon="📊", layout="wide")
apply_theme()


# -----------------------------------------------------------------------------
# Session state
# -----------------------------------------------------------------------------
DEFAULTS = {
    "files": [],
    "file_rows": [],
    "models": {},
    "liquidity_model": {},
    "business_profile": {},
    "selected_months": [],
    "expense_mapping": None,
    "expense_mapping_saved": False,
    "mapping_signature": None,
    "uploader_key": 0,
    "model_ready": False,
}
for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


def reset_all():
    for key, value in DEFAULTS.items():
        st.session_state[key] = [] if isinstance(value, list) else {} if isinstance(value, dict) else value
    st.session_state.uploader_key += 1


# -----------------------------------------------------------------------------
# Small UI helpers
# -----------------------------------------------------------------------------
def stage_box(title: str, body: str, status: str = ""):
    st.markdown(
        f"""
        <div class="executive-brief compact">
            <div class="brief-title">{title}</div>
            <div class="brief-text">{body}</div>
            {f'<div class="brief-subtext"><strong>الحالة:</strong> {status}</div>' if status else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_business_profile_from_inputs():
    return {
        "company_name": st.session_state.get("company_name", "Wazen Client"),
        "country": st.session_state.get("country", "السعودية"),
        "city": st.session_state.get("city", ""),
        "sector": st.session_state.get("business_sector", list(SECTOR_OPTIONS.keys())[0]),
        "activity": st.session_state.get("activity", ""),
        "business_model": st.session_state.get("business_model", "غير محدد"),
        "sales_channel": st.session_state.get("sales_channel", "غير محدد"),
        "currency": st.session_state.get("currency", "SAR"),
        "period_from": st.session_state.get("period_from", ""),
        "period_to": st.session_state.get("period_to", ""),
    }


def refresh_business_profile():
    st.session_state.business_profile = get_business_profile_from_inputs()
    return st.session_state.business_profile


# -----------------------------------------------------------------------------
# Sidebar navigation
# -----------------------------------------------------------------------------
st.markdown('<h1 class="main-title">Wazen CFO Intelligence Agent V12.0</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">تجربة تشخيص مالي موجهة: سياق النشاط → رفع الملفات → جاهزية البيانات → تشخيص CFO → سيناريوهات → إجراءات.</p>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## Wazen V12")
    st.caption("Financial Health & Action Intelligence")
    page = st.radio(
        "مسار العمل",
        [
            "1. إعداد النشاط",
            "2. رفع الملفات والمطابقة",
            "3. جاهزية التحليل",
            "4. التشخيص التنفيذي",
            "5. مساحة التحليل",
            "6. Scenario Studio",
            "7. التنبيهات والإجراءات",
            "8. التصدير",
        ],
        index=0,
    )
    st.divider()
    if st.button("بدء تحليل جديد / مسح الحالي"):
        reset_all()
        st.rerun()
    st.caption("V12 Foundation: UX + Readiness + Liquidity/Collections + Scenario Skeleton")


# -----------------------------------------------------------------------------
# Business setup
# -----------------------------------------------------------------------------
if page == "1. إعداد النشاط":
    section_header("1. إعداد النشاط قبل رفع الملفات")
    stage_box(
        "لماذا نبدأ بالسياق؟",
        "نفس النسبة قد تكون طبيعية في قطاع وخطيرة في قطاع آخر. لذلك يبدأ الإيجنت بالبلد والقطاع ونموذج العمل حتى يفسر المبيعات والسيولة والمرتجعات والخصومات بطريقة مناسبة.",
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.text_input("اسم الشركة", value=st.session_state.business_profile.get("company_name", "Wazen Client"), key="company_name")
        st.selectbox("البلد", COUNTRY_OPTIONS, index=COUNTRY_OPTIONS.index(st.session_state.business_profile.get("country", COUNTRY_OPTIONS[0])) if st.session_state.business_profile.get("country") in COUNTRY_OPTIONS else 0, key="country")
        st.text_input("المدينة", value=st.session_state.business_profile.get("city", ""), key="city")
    with c2:
        sectors = list(SECTOR_OPTIONS.keys())
        st.selectbox("القطاع", sectors, index=sectors.index(st.session_state.business_profile.get("sector", sectors[0])) if st.session_state.business_profile.get("sector") in sectors else 0, key="business_sector")
        act_options = get_sector_config(st.session_state.get("business_sector", sectors[0])).get("activities", ["غير محدد"])
        st.selectbox("طبيعة النشاط", act_options, index=0, key="activity")
        st.selectbox("نموذج العمل", ["B2B", "B2C", "B2B + B2C", "اشتراكات", "مشاريع", "فروع", "غير محدد"], index=6, key="business_model")
    with c3:
        st.selectbox("قناة البيع", ["فروع", "أونلاين", "أونلاين + فروع", "ميداني", "عقود", "غير محدد"], index=5, key="sales_channel")
        st.selectbox("العملة", ["SAR", "USD", "AED", "EUR", "SYP", "Other"], index=0, key="currency")
        st.text_input("فترة التحليل", value="مثال: 2026-01-01 إلى 2026-05-31", key="period_hint")

    if st.button("حفظ سياق النشاط", type="primary"):
        profile = refresh_business_profile()
        st.success("تم حفظ سياق النشاط. انتقلي إلى رفع الملفات والمطابقة.")
        st.json(profile)

    st.markdown("### ما الذي سيستخدمه الإيجنت من هذه البيانات؟")
    st.table(pd.DataFrame([
        ["القطاع", "اختيار نسب سلامة أولية وتفسير المرتجعات/الخصومات والهامش"],
        ["البلد/المدينة", "تهيئة العملة والضرائب والمقارنات المستقبلية"],
        ["نموذج العمل", "تحديد المؤشرات الأهم: تحصيل، أصناف، اشتراكات، مشاريع"],
        ["قناة البيع", "تفسير المرتجعات والخصومات وسلوك العملاء"],
    ], columns=["المدخل", "الأثر التحليلي"]))


# -----------------------------------------------------------------------------
# Upload and mapping
# -----------------------------------------------------------------------------
elif page == "2. رفع الملفات والمطابقة":
    section_header("2. مركز رفع الملفات والمطابقة")
    refresh_business_profile()

    with st.expander("الحد الأدنى والملفات التي ترفع جودة التحليل", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("#### الحد الأدنى")
            st.markdown("- ميزان المراجعة\n- تقرير المبيعات\n- تقرير المصروفات")
        with c2:
            st.markdown("#### للسيولة والتحصيل")
            st.markdown("- تقرير السيولة النقدية\n- أعمار ديون العملاء\n- أعمار ديون الموردين\n- كشوف البنك للتحقق")
        with c3:
            st.markdown("#### لرفع دقة التنبؤ")
            st.markdown("- مبيعات سنة سابقة\n- مبيعات الأصناف\n- مبيعات حسب العملاء\n- مرتجعات وخصومات\n- مخزون/رواتب/ضريبة")

    uploaded_files = st.file_uploader(
        "ارفع ملفات Excel المالية",
        type=["xlsx", "xls"],
        accept_multiple_files=True,
        key=f"financial_files_uploader_{st.session_state.uploader_key}",
    )

    if uploaded_files:
        st.success(f"تم اختيار {len(uploaded_files)} ملف: " + "، ".join([f.name for f in uploaded_files]))

    if uploaded_files and st.button("قراءة الملفات واكتشاف الأدوار", type="primary"):
        st.session_state.files = []
        st.session_state.file_rows = []
        errors = []
        with st.spinner("يتم قراءة الملفات واكتشاف النوع والدور..."):
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
                    errors.append(f"{data['file_name']}: {data['error']}")
                else:
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
                record = apply_role_resolution_to_record(record)
                st.session_state.files.append(record)
        if errors:
            st.warning("تمت قراءة بعض الملفات مع وجود أخطاء في ملفات أخرى.")
        else:
            st.success("تمت قراءة الملفات بنجاح.")

    if st.session_state.files:
        st.markdown("### أدوار الملفات")
        updated_rows = []
        for i, record in enumerate(st.session_state.files):
            with st.container():
                c1, c2, c3, c4 = st.columns([3.2, 1.7, 1, 2.3])
                c1.markdown(f"**{record['file_name']}**")
                c2.markdown(f"`{record['detected_type']}`")
                c3.markdown(f"{float(record.get('confidence') or 0):.0%}")
                selected = c4.selectbox(
                    "دور الملف",
                    SOURCE_ROLES,
                    index=SOURCE_ROLES.index(record.get("selected_role")) if record.get("selected_role") in SOURCE_ROLES else 0,
                    key=f"role_{i}",
                )
                record["selected_role"] = selected
                updated_rows.append({
                    "file_name": record.get("file_name"),
                    "detected_type": record.get("detected_type"),
                    "confidence": record.get("confidence"),
                    "suggested_role": record.get("suggested_role"),
                    "selected_role": selected,
                })
                if record.get("role_reason"):
                    st.caption(record["role_reason"])
                if record.get("read_error"):
                    message_box(record["read_error"], "warning")
                if record.get("primary_df") is not None and not record["primary_df"].empty:
                    with st.expander("معاينة أول 5 صفوف"):
                        st.dataframe(record["primary_df"].head(), use_container_width=True)
        st.session_state.file_rows = updated_rows

        st.markdown("### فترة التحليل وتصنيف المصاريف")
        readable_files = [r for r in st.session_state.files if not r.get("read_error")]
        revenue_preview_record = next((r for r in readable_files if r.get("selected_role") == "official_revenue_source"), None)
        expense_preview_record = next((r for r in readable_files if r.get("selected_role") == "official_expense_source"), None)

        revenue_definition = st.selectbox("تعريف الإيراد", REVENUE_DEFINITIONS, index=0)
        preview_revenue_model = build_revenue_model(revenue_preview_record, revenue_definition) if revenue_preview_record else None
        preview_expense_model = build_expense_model(expense_preview_record, preview_revenue_model.get("total_revenue", 0) if preview_revenue_model else 0) if expense_preview_record else None

        revenue_months = months_from_revenue_model(preview_revenue_model)
        expense_months = months_from_expense_model(preview_expense_model)
        suggested_months_raw = common_months(revenue_months, expense_months)
        validation_end_month = infer_validation_end_month(st.session_state.files)
        suggested_months = trim_months_to_end(suggested_months_raw, validation_end_month)
        st.caption(f"شهور الإيرادات: {', '.join(revenue_months) if revenue_months else 'غير متاح'}")
        st.caption(f"شهور المصاريف: {', '.join(expense_months) if expense_months else 'غير متاح'}")
        if validation_end_month and suggested_months != suggested_months_raw:
            st.warning(f"تم استبعاد الشهور بعد {validation_end_month} لأن ميزان المراجعة ينتهي عند هذا الشهر. يمكن تعديل الفترة يدويًا عند الحاجة.")
        selected_months = st.multiselect(
            "اعتماد شهور التحليل",
            options=suggested_months_raw or revenue_months or expense_months,
            default=st.session_state.selected_months or suggested_months or revenue_months or expense_months,
        )
        st.session_state.selected_months = selected_months

        if preview_expense_model and not preview_expense_model.get("expense_long", pd.DataFrame()).empty:
            industry = st.session_state.business_profile.get("activity") or st.session_state.business_profile.get("sector") or "غير محدد"
            initial_mapping = apply_smart_classification(build_expense_mapping(preview_expense_model, industry), use_openai=False)
            current_signature = "|".join(initial_mapping["account_name"].astype(str).tolist())
            if st.session_state.mapping_signature != current_signature:
                st.session_state.expense_mapping = initial_mapping.copy()
                st.session_state.expense_mapping_saved = False
                st.session_state.mapping_signature = current_signature
            st.info("راجعي تصنيف المصاريف قبل بناء النموذج. التعديلات لا تدخل الحسابات إلا بعد الحفظ.")
            edited_mapping = render_expense_mapping_editor(st.session_state.expense_mapping, key_prefix="expense_mapping_v12")
            if st.button("حفظ تصنيف المصاريف"):
                st.session_state.expense_mapping = edited_mapping.copy()
                st.session_state.expense_mapping_saved = True
                st.success("تم حفظ التصنيف.")
        else:
            st.info("لا توجد مصاريف كافية لبناء خريطة تصنيف الآن.")

        build_disabled = bool(preview_expense_model is not None and not st.session_state.expense_mapping_saved)
        if st.button("بناء النموذج المالي V12", disabled=build_disabled, type="primary"):
            with st.spinner("بناء النموذج المالي وطبقة السيولة والتحصيل..."):
                readable_files = [r for r in st.session_state.files if not r.get("read_error")]
                revenue_record = next((r for r in readable_files if r.get("selected_role") == "official_revenue_source"), None)
                expense_record = next((r for r in readable_files if r.get("selected_role") == "official_expense_source"), None)
                tb_candidates = [r for r in readable_files if r.get("selected_role") == "validation_source" and r.get("detected_type") == "trial_balance"]
                tb_record = next((r for r in tb_candidates if "ميزان" in r.get("file_name", "") or "trial" in r.get("file_name", "").lower()), None) or (tb_candidates[0] if tb_candidates else None)

                revenue_model = build_revenue_model(revenue_record, revenue_definition) if revenue_record else None
                expense_model = build_expense_model(expense_record, revenue_model.get("total_revenue", 0) if revenue_model else 0) if expense_record else None
                if expense_model and st.session_state.expense_mapping is not None and st.session_state.expense_mapping_saved:
                    expense_model = apply_expense_mapping(expense_model, st.session_state.expense_mapping)

                confirmed_months = st.session_state.selected_months
                revenue_model = filter_revenue_model(revenue_model, confirmed_months) if revenue_model else None
                expense_model = filter_expense_model(expense_model, confirmed_months) if expense_model else None
                revenue_total = revenue_model.get("total_revenue", 0) if revenue_model else 0
                if expense_model and revenue_total:
                    expense_model["expense_ratio"] = expense_model.get("total_expenses", 0) / revenue_total

                tb_model = parse_trial_balance(tb_record) if tb_record else None
                financial_model = build_basic_financial_model(revenue_model, expense_model)
                validation_checks = validate_project(st.session_state.file_rows, revenue_model, expense_model, tb_model)
                pnl_model = build_pnl(revenue_model, expense_model, tb_model)
                monthly_pnl_model = monthly_pnl(revenue_model, expense_model)
                ratio_model = build_ratios(pnl_model, expense_model)
                breakeven_model = build_breakeven(pnl_model, expense_model)
                forecast_model, forecast_note = build_forecast(monthly_pnl_model)
                glossary_model = build_glossary()
                liquidity_model = build_liquidity_collections_model(st.session_state.files)

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
                    "revenue_definition": revenue_definition,
                }
                st.session_state.liquidity_model = liquidity_model
                st.session_state.model_ready = True
            st.success("تم بناء نموذج V12. انتقلي إلى جاهزية التحليل أو التشخيص التنفيذي.")

        if build_disabled:
            st.warning("احفظي تصنيف المصاريف قبل بناء النموذج.")


# -----------------------------------------------------------------------------
# Readiness
# -----------------------------------------------------------------------------
elif page == "3. جاهزية التحليل":
    section_header("3. جاهزية التحليل")
    profile = build_readiness_profile(st.session_state.files, refresh_business_profile(), st.session_state.models)
    c1, c2, c3 = st.columns(3)
    with c1:
        kpi_card("Readiness Score", f"{profile['score']}%", profile["label"])
    with c2:
        kpi_card("ثقة اكتشاف الملفات", f"{profile['avg_confidence']*100:.0f}%", "متوسط الثقة في قراءة الملفات")
    with c3:
        kpi_card("ملفات مرفوعة", f"{len(st.session_state.files)}", "ليست كلها مصادر تحليل رئيسية")
    st.info(profile["status"])
    st.markdown("#### فحص الجاهزية")
    st.dataframe(profile["checks"], use_container_width=True, hide_index=True)
    st.markdown("#### الملفات المقروءة")
    st.dataframe(profile["uploaded_files"], use_container_width=True, hide_index=True)
    st.markdown("#### ماذا يرفع جودة التحليل؟")
    st.dataframe(build_missing_data_recommendations(profile), use_container_width=True, hide_index=True)


# -----------------------------------------------------------------------------
# Executive diagnosis
# -----------------------------------------------------------------------------
elif page == "4. التشخيص التنفيذي":
    section_header("4. التشخيص التنفيذي")
    if not st.session_state.models:
        st.warning("ابني النموذج المالي أولًا من صفحة رفع الملفات والمطابقة.")
    else:
        models = st.session_state.models
        pnl_model = models.get("pnl_model", {})
        expense_model = models.get("expense_model")
        breakeven_model = models.get("breakeven_model", {})
        revenue_model = models.get("revenue_model")
        liq_model = st.session_state.liquidity_model or build_liquidity_collections_model(st.session_state.files)
        st.session_state.liquidity_model = liq_model
        profile = refresh_business_profile()

        exec_kpis = build_executive_kpis(pnl_model, expense_model)
        perf = build_financial_performance_scorecard(pnl_model, breakeven_model)
        diag = build_owner_diagnosis(pnl_model, breakeven_model, expense_model, profile.get("sector", "غير محدد"), profile.get("country", ""), profile.get("activity", ""))
        liq_diag = liquidity_cfo_narrative(liq_model, pnl_model)

        st.markdown("### الإجابات التي تهم صاحب العمل")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            kpi_card("هل الشركة تربح؟", "نعم" if exec_kpis.get("net_profit", 0) > 0 else "لا", f"صافي الربح {exec_kpis.get('net_profit',0):,.0f}")
        with c2:
            kpi_card("هل الربح يتحول إلى نقد؟", liq_diag["risk"], liq_diag["problem"])
        with c3:
            kpi_card("أكبر منطقة خطر", liq_diag["risk"] if liq_model.get("available") else "غير مكتملة", liquidity_files_summary(st.session_state.files) if has_liquidity_files(st.session_state.files) else "نحتاج سيولة/ذمم")
        with c4:
            kpi_card("مؤشر الأداء", f"{min(float(perf.get('score',0) or 0),85):.0f}/100", "مؤشر ربحية وتشغيل أولي")

        st.markdown(
            f"""
            <div class="executive-diagnosis">
                <h3>تشخيص CFO</h3>
                <p><strong>الوضع:</strong> {diag.get('situation','')}</p>
                <p><strong>السيولة والتحصيل:</strong> {liq_diag['problem']}.</p>
                <p><strong>الإجراء الآن:</strong> {liq_diag['action'] if liq_model.get('available') else diag.get('action','')}</p>
                <p><strong>مؤشر المتابعة:</strong> {liq_diag['monitor']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("#### بطاقات مختصرة")
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            kpi_card("Net Sales", f"{exec_kpis.get('operating_revenue',0):,.0f}", "إيراد النشاط")
        with c2:
            kpi_card("Net Profit", f"{exec_kpis.get('net_profit',0):,.0f}", f"هامش {exec_kpis.get('net_margin',0)*100:.1f}%")
        with c3:
            kpi_card("Margin of Safety", f"{breakeven_model.get('margin_of_safety',0)*100:.1f}%", "قبل نقطة التعادل")
        with c4:
            cash_cards = (liq_model.get("cash") or {}).get("cards", {})
            kpi_card("Cash", f"{cash_cards.get('ending_cash',0):,.0f}", "من تقرير السيولة إن توفر")
        with c5:
            runway = cash_cards.get("cash_runway_months")
            kpi_card("Runway", "—" if runway is None else f"{runway:.1f} شهر", "مبدئي قبل تنظيف التحويلات")


# -----------------------------------------------------------------------------
# Analysis Workspace
# -----------------------------------------------------------------------------
elif page == "5. مساحة التحليل":
    section_header("5. مساحة التحليل")
    if not st.session_state.models:
        st.warning("ابني النموذج المالي أولًا.")
    else:
        models = st.session_state.models
        revenue_model = models.get("revenue_model")
        expense_model = models.get("expense_model")
        pnl_model = models.get("pnl_model", {})
        monthly_pnl_model = models.get("monthly_pnl_model", pd.DataFrame())
        breakeven_model = models.get("breakeven_model", {})
        liq_model = st.session_state.liquidity_model or build_liquidity_collections_model(st.session_state.files)
        tabs = st.tabs(["Revenue Quality", "Profitability", "Cash & Liquidity", "Collections", "Expenses", "Sector Safety"])

        with tabs[0]:
            st.subheader("جودة الإيراد")
            if revenue_model and not revenue_model.get("monthly_revenue", pd.DataFrame()).empty:
                rev_monthly = revenue_model["monthly_revenue"].copy()
                rev_monthly["revenue"] = pd.to_numeric(rev_monthly["revenue"], errors="coerce").fillna(0)
                rev_quality = build_revenue_quality(rev_monthly)
                c1,c2,c3,c4 = st.columns(4)
                with c1: kpi_card("إجمالي الإيرادات", f"{rev_quality['cards'].get('total',0):,.0f}", "خلال الفترة")
                with c2: kpi_card("متوسط شهري", f"{rev_quality['cards'].get('avg',0):,.0f}", "متوسط محافظ")
                with c3: kpi_card("أعلى شهر", str(rev_quality['cards'].get('best_month','—')), f"{rev_quality['cards'].get('max_share',0)*100:.1f}%")
                with c4: kpi_card("استقرار الإيراد", f"{rev_quality['cards'].get('stability_score',0):.0f}/100", rev_quality['cards'].get('quality_status','—'))
                render_insight_panel("قراءة CFO للإيراد", rev_quality["narrative"], rev_quality["risk"], rev_quality["action"], ["لا نكتفي بالمبيعات الإجمالية؛ في V12 القادم نقرأ الإجمالي والخصومات والمرتجعات والصافي عند توفر ملف تفصيلي."])
                line_chart(rev_monthly, "month", "revenue", "اتجاه الإيرادات")
                st.dataframe(rev_monthly, use_container_width=True, hide_index=True)
            else:
                st.info("لا توجد بيانات إيرادات كافية.")

        with tabs[1]:
            st.subheader("الربحية وقائمة الدخل")
            render_executive_income_statement(build_executive_income_statement(pnl_model, expense_model))
            if monthly_pnl_model is not None and not monthly_pnl_model.empty:
                st.markdown("#### الربحية الشهرية")
                render_executive_monthly_profitability(build_executive_monthly_profitability(monthly_pnl_model, pnl_model, expense_model))

        with tabs[2]:
            st.subheader("السيولة النقدية")
            cash = liq_model.get("cash", {})
            if cash.get("available"):
                cards = cash.get("cards", {})
                c1,c2,c3,c4 = st.columns(4)
                with c1: kpi_card("Cash In", f"{cards.get('total_cash_in',0):,.0f}", "داخلة خلال الفترة")
                with c2: kpi_card("Cash Out", f"{cards.get('total_cash_out',0):,.0f}", "خارجة خلال الفترة")
                with c3: kpi_card("Net Cash Flow", f"{cards.get('net_cash_flow',0):,.0f}", "صافي الحركة")
                with c4:
                    runway = cards.get("cash_runway_months")
                    kpi_card("Runway", "—" if runway is None else f"{runway:.1f} شهر", "مبدئي")
                monthly = cash.get("monthly", pd.DataFrame())
                if not monthly.empty:
                    st.dataframe(monthly, use_container_width=True, hide_index=True)
                    line_chart(monthly, "month", "ending_cash_proxy", "اتجاه الرصيد النقدي التراكمي")
            else:
                st.warning("لا يوجد تقرير سيولة نقدية مقروء. يمكن استخدام كشوف البنك لاحقًا للتحقق والتفصيل.")

        with tabs[3]:
            st.subheader("التحصيل وأعمار العملاء")
            ar = liq_model.get("ar", {})
            if ar.get("available"):
                cards = ar.get("cards", {})
                c1,c2,c3,c4 = st.columns(4)
                with c1: kpi_card("إجمالي الذمم", f"{cards.get('total_balance',0):,.0f}", "حسب ملف الأعمار")
                with c2: kpi_card("المتأخر", f"{cards.get('overdue_balance',0):,.0f}", f"{cards.get('overdue_pct',0)*100:.1f}%")
                with c3: kpi_card("تركيز أعلى 5", f"{cards.get('top5_concentration',0)*100:.1f}%", "خطر تركّز العملاء")
                with c4: kpi_card("عدد العملاء", f"{cards.get('count',0)}", "بحسب التقرير")
                st.markdown("#### أولويات التحصيل التفاعلية")
                st.dataframe(ar.get("detail", pd.DataFrame()).rename(columns={
                    "name": "العميل", "balance": "الرصيد", "age_days": "عمر الدين", "last_payment": "آخر سداد", "risk_level": "الخطر", "recommended_action": "الإجراء"
                }), use_container_width=True, hide_index=True)
            else:
                st.warning("لا يوجد ملف أعمار عملاء. لن نكتفي بتوصية عامة؛ عند رفعه سيظهر العملاء والأرصدة والأولوية.")

        with tabs[4]:
            st.subheader("المصاريف وهيكل التكلفة")
            if expense_model:
                monthly_exp = expense_model.get("monthly_expenses", pd.DataFrame()).copy()
                cat_df = expense_model.get("by_category", pd.DataFrame()).copy()
                c1,c2 = st.columns(2)
                with c1:
                    st.markdown("#### المصاريف الشهرية")
                    st.dataframe(monthly_exp, use_container_width=True, hide_index=True)
                    if not monthly_exp.empty: bar_chart(monthly_exp, "month", "expenses", "Monthly Expenses")
                with c2:
                    st.markdown("#### هيكل المصاريف")
                    st.dataframe(cat_df, use_container_width=True, hide_index=True)
                    if not cat_df.empty: pie_chart(cat_df, "category", "amount", "Expense Structure")
                st.markdown("#### أكبر بنود المصاريف")
                st.dataframe(expense_model.get("top_expenses", pd.DataFrame()), use_container_width=True, hide_index=True)
            else:
                st.info("لا توجد مصاريف كافية.")

        with tabs[5]:
            st.subheader("معايير السلامة حسب القطاع")
            profile = refresh_business_profile()
            scorecard = build_sector_safety_scorecard(pnl_model, breakeven_model, profile.get("sector","غير محدد"), profile.get("country",""), profile.get("activity",""))
            summary = build_scorecard_summary(scorecard, profile.get("sector","غير محدد"))
            render_insight_panel(summary["title"], summary["summary"], summary["risk"], summary["action"], ["المعايير الحالية أولية وقابلة للتعديل حسب القطاع والمدينة ونوع النشاط."])
            render_sector_scorecard(scorecard)
            st.markdown("#### أولويات التنفيذ")
            render_actions_table(build_top_5_actions(scorecard))


# -----------------------------------------------------------------------------
# Scenario Studio
# -----------------------------------------------------------------------------
elif page == "6. Scenario Studio":
    section_header("6. Scenario Studio")
    if not st.session_state.models:
        st.warning("ابني النموذج المالي أولًا.")
    else:
        liq_model = st.session_state.liquidity_model or build_liquidity_collections_model(st.session_state.files)
        base = base_inputs_from_models(st.session_state.models, liq_model)
        stage_box("سيناريوهات مبدئية", "هذه النسخة تربط المتغيرات الأساسية بالمبيعات والربح والنقد. في المرحلة التالية تصبح السيناريوهات أعمق حسب القطاع والمرتجعات والخصومات والأصناف.")

        st.markdown("### سيناريوهات جاهزة")
        pre = predefined_scenarios(base)
        st.dataframe(pre, use_container_width=True, hide_index=True)

        st.markdown("### سيناريو تفاعلي")
        c1,c2,c3 = st.columns(3)
        with c1:
            sales_growth = st.slider("نمو المبيعات %", -30, 50, 0)
            discount_rate = st.slider("نسبة الخصومات %", 0, 30, 0)
            return_rate = st.slider("نسبة المرتجعات %", 0, 30, 0)
        with c2:
            collection_rate = st.slider("نسبة التحصيل المتوقعة %", 0, 100, 40)
            opex_change = st.slider("تغير المصروفات %", -30, 50, 0)
            cogs_change = st.slider("تغير تكلفة المبيعات %", -20, 40, 0)
        with c3:
            supplier_payment = st.number_input("دفعات موردين إضافية", value=0.0, step=1000.0)
            tax_payment = st.number_input("ضريبة/زكاة متوقعة", value=0.0, step=1000.0)

        res = run_simple_scenario(base, {
            "sales_growth_pct": sales_growth,
            "discount_rate_pct": discount_rate,
            "return_rate_pct": return_rate,
            "collection_rate_pct": collection_rate,
            "opex_change_pct": opex_change,
            "cogs_change_pct": cogs_change,
            "supplier_payment": supplier_payment,
            "tax_payment": tax_payment,
        })
        c1,c2,c3,c4 = st.columns(4)
        with c1: kpi_card("Net Sales", f"{res['net_sales']:,.0f}", f"تسرب تجاري {res['commercial_leakage']:,.0f}")
        with c2: kpi_card("Net Profit", f"{res['net_profit']:,.0f}", "بعد أثر السيناريو")
        with c3: kpi_card("Cash after 30 days", f"{res['ending_cash_30']:,.0f}", "تقدير أولي")
        with c4: kpi_card("Runway", "—" if res['cash_runway_months'] is None else f"{res['cash_runway_months']:.1f} شهر", res["risk_level"])


# -----------------------------------------------------------------------------
# Action Center
# -----------------------------------------------------------------------------
elif page == "7. التنبيهات والإجراءات":
    section_header("7. مركز التنبيهات والإجراءات")
    profile = build_readiness_profile(st.session_state.files, refresh_business_profile(), st.session_state.models)
    liq_model = st.session_state.liquidity_model or build_liquidity_collections_model(st.session_state.files)
    actions = build_action_center(st.session_state.models, liq_model, profile)
    stage_box("قاعدة الصفحة", "كل تنبيه يجب أن يحتوي: المشكلة، الدليل، الأثر، الإجراء، المدة، ومؤشر المتابعة. لا توجد توصيات عامة دون أرقام أو قائمة عملاء/بنود عندما تكون البيانات متاحة.")
    st.dataframe(actions, use_container_width=True, hide_index=True)


# -----------------------------------------------------------------------------
# Export
# -----------------------------------------------------------------------------
elif page == "8. التصدير":
    section_header("8. التصدير")
    if not st.session_state.models:
        st.warning("ابني النموذج المالي أولًا.")
    else:
        models = st.session_state.models
        excel_bytes = build_excel_pack(
            st.session_state.file_rows,
            models.get("revenue_model"),
            models.get("expense_model"),
            models.get("financial_model"),
            models.get("validation_checks"),
            pnl_model=models.get("pnl_model"),
            ratio_model=models.get("ratio_model"),
            breakeven_model=models.get("breakeven_model"),
            forecast_model=models.get("forecast_model"),
            glossary_model=models.get("glossary_model"),
            confirmed_months=models.get("confirmed_months", []),
            expense_mapping=models.get("expense_mapping", pd.DataFrame()),
        )
        st.download_button(
            "تحميل Excel CFO Pack",
            data=excel_bytes,
            file_name="wazen_cfo_pack_v12.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.info("سيتم لاحقًا إضافة PDF Executive Summary بنفس مسار التشخيص والتنبيهات.")
