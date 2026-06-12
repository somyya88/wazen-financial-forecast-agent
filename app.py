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
from comprehensive_financial_analysis import build_comprehensive_financial_analysis
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
    "nav_page": "1. إعداد النشاط",
    "pending_rebuild": False,
    "revenue_definition": REVENUE_DEFINITIONS[0],
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
        "branch_mode": st.session_state.get("branch_mode", "تحليل إجمالي فقط"),
        "branch_count": st.session_state.get("branch_count", 1),
        "currency": st.session_state.get("currency", "SAR"),
        "period_from": st.session_state.get("period_from", ""),
        "period_to": st.session_state.get("period_to", ""),
    }


def refresh_business_profile():
    st.session_state.business_profile = get_business_profile_from_inputs()
    return st.session_state.business_profile

def safe_multiselect(label, options, default=None, **kwargs):
    """Streamlit multiselect that never crashes when defaults are not in options."""
    options = list(options or [])
    default = [x for x in (default or []) if x in options]
    return st.multiselect(label, options=options, default=default, **kwargs)


def render_hero(title: str, body: str):
    st.markdown(f"""
    <div class="wazen-hero">
        <h2>{title}</h2>
        <p>{body}</p>
    </div>
    """, unsafe_allow_html=True)


def render_requirement_cards():
    st.markdown("""
    <div class="ux-card-grid">
        <div class="ux-card must-have">
            <span class="required-badge">★ الحد الأدنى للتحليل</span>
            <div class="ux-card-title">ميزان مراجعة + مبيعات + مصروفات</div>
            <div class="ux-card-text">هذه الملفات هي أساس بناء القوائم، الربحية، ومطابقة النتائج. عند نقصها لا يتم بناء نموذج مالي نهائي.</div>
        </div>
        <div class="ux-card should-have">
            <span class="enhance-badge">يرفع دقة القرار</span>
            <div class="ux-card-title">تقرير السيولة + أعمار العملاء + أعمار الموردين</div>
            <div class="ux-card-text">تحول التحليل من أرقام عامة إلى نقد، تحصيل، أسماء عملاء، وأولويات متابعة.</div>
        </div>
        <div class="ux-card optional-data">
            <span class="optional-badge">اختياري للتعمق</span>
            <div class="ux-card-title">سنة سابقة + أصناف + عملاء + فروع</div>
            <div class="ux-card-text">تستخدم للموسمية، المرتجعات، الخصومات، تركّز العملاء، وتحليل الفروع والمنتجات.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def minimum_model_status(files: list[dict]) -> dict:
    """Return whether we have the minimum sources for a defensible financial model."""
    readable = [r for r in files or [] if not r.get("read_error")]
    roles = {str(r.get("selected_role") or "") for r in readable}
    has_revenue = "official_revenue_source" in roles
    has_expense = "official_expense_source" in roles
    has_tb = "validation_source" in roles
    missing = []
    if not has_tb:
        missing.append("ميزان المراجعة")
    if not has_revenue:
        missing.append("تقرير المبيعات")
    if not has_expense:
        missing.append("تقرير المصروفات")
    return {
        "ok": has_revenue and has_expense and has_tb,
        "has_revenue": has_revenue,
        "has_expense": has_expense,
        "has_tb": has_tb,
        "missing": missing,
    }


def render_minimum_model_guard(status: dict):
    missing = "، ".join(status.get("missing") or [])
    st.markdown(f"""
    <div class="wazen-soft-warning">
        <strong>لا يمكن بناء نموذج مالي موثوق بعد.</strong><br>
        الملفات الناقصة للحد الأدنى: {missing or '—'}.<br>
        يمكنك رفع ملف واحد أو أكثر الآن، لكن زر بناء النموذج لن يعمل قبل توفر ميزان المراجعة والمبيعات والمصروفات.
    </div>
    """, unsafe_allow_html=True)


def render_suggested_file_column(profile: dict):
    recs = build_missing_data_recommendations(profile)
    if recs.empty:
        return
    st.markdown("#### ملفات مقترحة")
    st.caption("أضيفي الملف المناسب من بطاقة التوصية نفسها.")
    for idx, row in recs.iterrows():
        المجال = str(row.get("المجال", ""))
        المطلوب = str(row.get("المطلوب بلغة بسيطة", ""))
        القيمة = str(row.get("القيمة المضافة", ""))
        st.markdown(f"""
        <div class="side-file-card">
            <span>{المجال}</span>
            <h4>{المطلوب}</h4>
            <p>{القيمة}</p>
        </div>
        """, unsafe_allow_html=True)
        files = st.file_uploader(
            f"إضافة: {المطلوب}",
            type=["xlsx", "xls"],
            accept_multiple_files=True,
            key=f"side_reco_upload_{idx}_{st.session_state.uploader_key}",
        )
        if files and st.button(f"قراءة هذا الملف #{idx+1}", key=f"side_reco_btn_{idx}"):
            with st.spinner("يتم إضافة الملف وقراءة أثره..."):
                errors = ingest_uploaded_files(files, append=True)
                st.session_state.liquidity_model = build_liquidity_collections_model(st.session_state.files)
                status = minimum_model_status(st.session_state.files)
                if status["ok"]:
                    build_models_from_session(st.session_state.get("revenue_definition", REVENUE_DEFINITIONS[0]))
                else:
                    st.session_state.pending_rebuild = True
            if errors:
                st.warning("تمت الإضافة مع ملاحظات قراءة لبعض الملفات.")
            else:
                st.success("تمت إضافة الملف بنجاح.")
            st.rerun()


def render_business_profile_summary(profile: dict):
    rows = [
        ["الشركة", profile.get("company_name", "—")],
        ["السوق", f"{profile.get('country','—')} / {profile.get('city') or 'مدينة غير محددة'}"],
        ["القطاع", profile.get("sector", "—")],
        ["النشاط", profile.get("activity", "—")],
        ["نموذج العمل", profile.get("business_model", "—")],
        ["قناة البيع", profile.get("sales_channel", "—")],
        ["الفروع", profile.get("branch_mode", "تحليل إجمالي فقط")],
        ["العملة", profile.get("currency", "—")],
    ]
    st.dataframe(pd.DataFrame(rows, columns=["المدخل", "القيمة"]), use_container_width=True, hide_index=True)

def render_readiness_upload_actions(profile: dict):
    recs = build_missing_data_recommendations(profile)
    if recs.empty:
        return
    st.markdown("### ملفات مقترحة لرفع جودة التحليل")
    st.caption("بدل الرجوع لصفحة البداية، يمكن إضافة الملف من نفس بطاقة التوصية وسيتم ضمه للقراءة الحالية مباشرة.")
    for idx, row in recs.iterrows():
        المجال = str(row.get("المجال", ""))
        المطلوب = str(row.get("المطلوب بلغة بسيطة", ""))
        القيمة = str(row.get("القيمة المضافة", ""))
        st.markdown(f"""
        <div class="file-request-card">
            <div class="file-request-domain">{المجال}</div>
            <div class="file-request-title">{المطلوب}</div>
            <div class="file-request-text">{القيمة}</div>
        </div>
        """, unsafe_allow_html=True)
        files = st.file_uploader(
            f"إضافة ملف لهذا البند: {المطلوب}",
            type=["xlsx", "xls"],
            accept_multiple_files=True,
            key=f"readiness_action_upload_{idx}_{st.session_state.uploader_key}",
        )
        if files and st.button(f"قراءة وإضافة الملف المقترح #{idx+1}", key=f"readiness_action_btn_{idx}"):
            with st.spinner("يتم قراءة الملف وإضافته للنموذج الحالي..."):
                errors = ingest_uploaded_files(files, append=True)
                st.session_state.liquidity_model = build_liquidity_collections_model(st.session_state.files)
                # Rebuild model immediately when enough data exists; this keeps the user in the same flow.
                if st.session_state.files:
                    try:
                        build_models_from_session(st.session_state.get("revenue_definition", REVENUE_DEFINITIONS[0]))
                    except Exception:
                        st.session_state.pending_rebuild = True
                else:
                    st.session_state.pending_rebuild = True
            if errors:
                st.warning("تمت الإضافة مع ملاحظات قراءة لبعض الملفات. راجعي جدول الملفات المقروءة.")
            else:
                st.success("تمت إضافة الملف وقراءة أثره ضمن نفس الصفحة.")
            st.rerun()




def build_cfo_executive_brief(exec_kpis: dict, pnl_model: dict, liq_model: dict, liq_diag: dict, profile: dict) -> dict:
    revenue = float(exec_kpis.get("revenue") or exec_kpis.get("operating_revenue") or 0)
    operating_revenue = float(exec_kpis.get("operating_revenue") or revenue or 0)
    net_profit = float(exec_kpis.get("net_profit") or 0)
    net_margin = (net_profit / revenue) if revenue else 0
    opex_ratio = float(exec_kpis.get("opex_ratio") or 0)
    gross_margin = float(exec_kpis.get("gross_margin") or 0)
    sector = profile.get("sector", "النشاط")

    if revenue <= 0:
        headline = "لا يمكن إصدار تشخيص ربحي موثوق قبل قراءة الإيرادات."
        issue = "مصدر الإيرادات غير مكتمل أو لم يُبنَ النموذج بعد."
        action = "ارفع ملف المبيعات أو ميزان المراجعة، ثم أعد بناء النموذج."
        tone = "danger"
    elif net_profit < 0:
        headline = "النشاط لا يحقق ربحًا صافيًا خلال الفترة الحالية."
        issue = f"كل {revenue:,.0f} من الإيرادات انتهت إلى خسارة صافية تقارب {abs(net_profit):,.0f}. المشكلة ليست رقمًا محاسبيًا فقط؛ هي ضغط هامش أو مصاريف أو تكلفة إيراد أعلى من قدرة المبيعات."
        action = "ابدأ بتحليل أكبر بنود المصروفات والتكلفة، ثم افصل البنود الثابتة عن المتغيرة قبل أي توسع أو التزام جديد."
        tone = "danger"
    elif opex_ratio > 0.55:
        headline = "الشركة تحقق ربحًا، لكن جودة الربح تحت ضغط تشغيلي."
        issue = f"المصاريف التشغيلية تستهلك {opex_ratio*100:.1f}% من الإيرادات. هذا لا يعني تناقضًا مع الربح؛ قد يوجد مجمل ربح كافٍ، لكن هامش الأمان ضعيف وأي تأخر تحصيل أو ارتفاع تكلفة قد يمتص الربح."
        action = "راجع أكبر 10 مصاريف ثابتة وشبه ثابتة، وحدد أي بند لا يرتبط مباشرة بالإيراد أو التحصيل."
        tone = "warning"
    elif net_margin < 0.08:
        headline = "الربح موجود لكنه لا يعطي مساحة كافية للمخاطر."
        issue = f"هامش صافي الربح {net_margin*100:.1f}% فقط. في قطاع {sector}، هذا يحتاج مراقبة لأن أي خصومات أو مرتجعات أو تأخر تحصيل قد يحول الربح إلى ضغط نقدي."
        action = "اربط المبيعات بالصافي بعد الخصومات والمرتجعات، ثم راقب التحصيل أسبوعيًا لا شهريًا."
        tone = "warning"
    else:
        headline = "الوضع الربحي مقبول مبدئيًا، لكن القرار يعتمد على جودة النقد والتحصيل."
        issue = f"هامش صافي الربح {net_margin*100:.1f}% ومجمل الهامش {gross_margin*100:.1f}%. لا يكفي الحكم من الربحية؛ يجب اختبار هل الربح يتحول إلى نقد."
        action = "انتقل إلى السيولة والتحصيل، وحدد العملاء أو البنود التي تحبس النقد."
        tone = "ok"

    cash_line = ""
    if liq_model.get("available") or (liq_model.get("cash") or {}).get("available"):
        cash_line = f"قراءة النقد الحالية: {liq_diag.get('problem','تحتاج مراجعة السيولة')}."
    else:
        cash_line = "قراءة النقد غير مكتملة: ارفع تقرير السيولة النقدية أو أعمار العملاء ليتم تحويل الربحية إلى تشخيص نقدي."

    return {"headline": headline, "issue": issue, "action": action, "cash_line": cash_line, "tone": tone}

def make_file_record(uploaded):
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
    return apply_role_resolution_to_record(record)


def ingest_uploaded_files(uploaded_files, append: bool = False):
    if not append:
        st.session_state.files = []
        st.session_state.file_rows = []
    errors = []
    existing_names = {f.get("file_name") for f in st.session_state.files}
    for uploaded in uploaded_files or []:
        record = make_file_record(uploaded)
        if append and record.get("file_name") in existing_names:
            # Replace same-name file instead of duplicating it.
            st.session_state.files = [f for f in st.session_state.files if f.get("file_name") != record.get("file_name")]
        if record.get("read_error"):
            errors.append(f"{record.get('file_name')}: {record.get('read_error')}")
        st.session_state.files.append(record)
    return errors


def build_models_from_session(revenue_definition: str | None = None):
    """Build all financial models from the currently selected files.
    Used by the upload page and by the readiness page after adding files directly.
    """
    revenue_definition = revenue_definition or st.session_state.get("revenue_definition", REVENUE_DEFINITIONS[0])
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
    revenue_model = filter_revenue_model(revenue_model, confirmed_months) if revenue_model and confirmed_months else revenue_model
    expense_model = filter_expense_model(expense_model, confirmed_months) if expense_model and confirmed_months else expense_model
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
    comprehensive_model = build_comprehensive_financial_analysis(
        tb_model, pnl_model, expense_model, revenue_model, monthly_pnl_model, liquidity_model, refresh_business_profile(), breakeven_model, st.session_state.get("ai_narrative_enabled", False)
    )

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
        "comprehensive_model": comprehensive_model,
    }
    st.session_state.liquidity_model = liquidity_model
    st.session_state.model_ready = True
    st.session_state.pending_rebuild = False
    return True




PAGE_OPTIONS = [
    "1. إعداد النشاط",
    "2. رفع الملفات والمطابقة",
    "3. جاهزية التحليل",
    "4. التشخيص التنفيذي",
    "5. مساحة التحليل",
    "6. استوديو السيناريوهات",
    "7. التنبيهات والإجراءات",
    "8. التصدير",
]

def go_to(page_name: str):
    if page_name in PAGE_OPTIONS:
        st.session_state.nav_page = page_name
        st.rerun()

# -----------------------------------------------------------------------------
# Sidebar navigation
# -----------------------------------------------------------------------------
st.markdown('<h1 class="main-title">Wazen CFO Intelligence Agent V12.5</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">من بيانات محاسبية خام إلى تشخيص مالي وتنبيهات تنفيذية وسيناريوهات قرار.</p>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## Wazen V12")
    st.caption("Financial Health & Action Intelligence")
    if st.session_state.get("nav_page") not in PAGE_OPTIONS:
        st.session_state.nav_page = PAGE_OPTIONS[0]
    page = st.radio(
        "مسار العمل",
        PAGE_OPTIONS,
        index=PAGE_OPTIONS.index(st.session_state.nav_page),
    )
    st.session_state.nav_page = page
    st.divider()
    if st.button("بدء تحليل جديد / مسح الحالي"):
        reset_all()
        st.session_state.nav_page = PAGE_OPTIONS[0]
        st.rerun()
    st.checkbox("تفعيل صياغة AI للملخص التنفيذي إذا كان المفتاح متاحًا", key="ai_narrative_enabled", value=st.session_state.get("ai_narrative_enabled", False))
    st.caption("V12.5: Diagnostic Rules + CFO Narrative + Health Score")


# -----------------------------------------------------------------------------
# Business setup
# -----------------------------------------------------------------------------
if page == "1. إعداد النشاط":
    section_header("1. إعداد النشاط قبل رفع الملفات")
    render_hero(
        "إعداد ذكي قبل التحليل",
        "هذه الخطوة لا تجمع بيانات شكلية؛ هي التي تحدد كيف يفسّر الإيجنت الهامش، الخصومات، المرتجعات، السيولة، والتحصيل حسب البلد والقطاع وطبيعة العمل."
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.text_input("اسم الشركة", value=st.session_state.business_profile.get("company_name", "Wazen Client"), key="company_name")
        st.selectbox("البلد ★", COUNTRY_OPTIONS, index=COUNTRY_OPTIONS.index(st.session_state.business_profile.get("country", COUNTRY_OPTIONS[0])) if st.session_state.business_profile.get("country") in COUNTRY_OPTIONS else 0, key="country")
        st.text_input("المدينة", value=st.session_state.business_profile.get("city", ""), key="city", placeholder="مثال: الرياض، جدة، الدمام")
    with c2:
        sectors = list(SECTOR_OPTIONS.keys())
        st.selectbox("القطاع ★", sectors, index=sectors.index(st.session_state.business_profile.get("sector", sectors[0])) if st.session_state.business_profile.get("sector") in sectors else 0, key="business_sector")
        act_options = get_sector_config(st.session_state.get("business_sector", sectors[0])).get("activities", ["غير محدد"])
        st.selectbox("طبيعة النشاط ★", act_options, index=0, key="activity")
        st.selectbox("نموذج العمل", ["B2B", "B2C", "B2B + B2C", "اشتراكات", "مشاريع", "فروع", "غير محدد"], index=6, key="business_model")
    with c3:
        st.selectbox("قناة البيع", ["فروع", "أونلاين", "أونلاين + فروع", "ميداني", "عقود", "غير محدد"], index=5, key="sales_channel")
        st.selectbox("تحليل الفروع", ["تحليل إجمالي فقط", "إجمالي + حسب الفروع إذا وجدت في البيانات", "كل فرع كحالة منفصلة لاحقًا"], index=0, key="branch_mode")
        st.number_input("عدد الفروع التقريبي", min_value=1, max_value=500, value=int(st.session_state.business_profile.get("branch_count", 1) or 1), key="branch_count")
        st.selectbox("العملة", ["SAR", "USD", "AED", "EUR", "SYP", "Other"], index=0, key="currency")

    st.caption("★ حقول أساسية. باقي الحقول تساعد في رفع دقة التفسير، ويمكن تعديلها لاحقًا.")

    if st.button("حفظ سياق النشاط والانتقال للملفات", type="primary"):
        refresh_business_profile()
        go_to("2. رفع الملفات والمطابقة")

    st.markdown("### ما الذي سيستخدمه الإيجنت من هذه البيانات؟")
    st.table(pd.DataFrame([
        ["القطاع", "اختيار معايير سلامة أولية وتفسير المرتجعات/الخصومات والهامش حسب النشاط"],
        ["البلد/المدينة", "تهيئة العملة والضرائب والمقارنات المستقبلية"],
        ["نموذج العمل وقناة البيع", "تحديد المؤشرات الأهم: تحصيل، أصناف، اشتراكات، مشاريع، فروع"],
        ["تحليل الفروع", "إذا ظهر عمود الفرع أو رفعت تقارير منفصلة، يظهر التحليل إجماليًا وحسب الفرع لاحقًا"],
    ], columns=["المدخل", "الأثر التحليلي"]))


# -----------------------------------------------------------------------------
# Upload and mapping
# -----------------------------------------------------------------------------
elif page == "2. رفع الملفات والمطابقة":
    section_header("2. مركز رفع الملفات والمطابقة")
    refresh_business_profile()

    render_hero("مركز رفع الملفات", "ارفعي ما هو متاح من النظام المحاسبي. الإيجنت لا يتوقف عند نقص البيانات؛ لكنه يوضح مستوى الثقة وما الذي يرفع جودة التحليل.")
    render_requirement_cards()

    uploaded_files = st.file_uploader(
        "ارفع ملفات Excel المالية",
        type=["xlsx", "xls"],
        accept_multiple_files=True,
        key=f"financial_files_uploader_{st.session_state.uploader_key}",
    )

    if uploaded_files:
        st.success(f"تم اختيار {len(uploaded_files)} ملف: " + "، ".join([f.name for f in uploaded_files]))

    if uploaded_files and st.button("قراءة الملفات واكتشاف الأدوار", type="primary"):
        with st.spinner("يتم قراءة الملفات واكتشاف النوع والدور..."):
            errors = ingest_uploaded_files(uploaded_files, append=False)
        if errors:
            st.warning("تمت قراءة بعض الملفات مع وجود أخطاء في ملفات أخرى. لن تظهر صفحة برمجية؛ سيظهر سبب الخطأ بلغة واضحة ضمن جدول الملفات.")
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

        revenue_definition = st.selectbox("تعريف الإيراد", REVENUE_DEFINITIONS, index=REVENUE_DEFINITIONS.index(st.session_state.get("revenue_definition", REVENUE_DEFINITIONS[0])) if st.session_state.get("revenue_definition") in REVENUE_DEFINITIONS else 0)
        st.session_state.revenue_definition = revenue_definition
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
        month_options = suggested_months_raw or revenue_months or expense_months
        month_default = st.session_state.selected_months or suggested_months or revenue_months or expense_months
        selected_months = safe_multiselect(
            "اعتماد شهور التحليل",
            options=month_options,
            default=month_default,
        )
        st.session_state.selected_months = selected_months

        if preview_expense_model and not preview_expense_model.get("expense_long", pd.DataFrame()).empty:
            industry = st.session_state.business_profile.get("activity") or st.session_state.business_profile.get("sector") or "غير محدد"
            base_mapping = build_expense_mapping(preview_expense_model, industry)
            current_signature = "|".join(base_mapping["account_name"].astype(str).tolist())
            # Performance fix: do not re-run AI/rule classification on every table edit.
            # Classification is generated once per file signature, then user edits remain as a draft until saved.
            if st.session_state.mapping_signature != current_signature or st.session_state.expense_mapping is None:
                with st.spinner("تصنيف الحسابات لأول مرة حسب القطاع..."):
                    initial_mapping = apply_smart_classification(base_mapping, sector_context=industry, use_openai=True)
                st.session_state.expense_mapping = initial_mapping.copy()
                st.session_state.expense_mapping_saved = False
                st.session_state.mapping_signature = current_signature
            st.info("تم بناء خريطة المصاريف من الحسابات نفسها مع مراعاة القطاع المحدد. في الشركات البرمجية، الرواتب التشغيلية وخدمات التنفيذ/الدعم تُعامل كتكلفة إيراد عند وجود دلالة واضحة، ورواتب المبيعات ضمن البيع والتسويق، والرواتب الإدارية ضمن المصاريف الإدارية. راجعي فقط البنود منخفضة الثقة أو المصنفة بحاجة مراجعة.")
            edited_mapping = render_expense_mapping_editor(st.session_state.expense_mapping, key_prefix="expense_mapping_v12")
            if st.button("حفظ تصنيف المصاريف", type="secondary"):
                st.session_state.expense_mapping = edited_mapping.copy()
                st.session_state.expense_mapping_saved = True
                st.success("تم حفظ التصنيف. يمكنك الآن بناء النموذج المالي.")
        else:
            st.info("لا توجد مصاريف كافية لبناء خريطة تصنيف الآن.")

        min_status = minimum_model_status(st.session_state.files)
        build_disabled = bool((preview_expense_model is not None and not st.session_state.expense_mapping_saved) or not min_status["ok"])
        if not min_status["ok"]:
            render_minimum_model_guard(min_status)
        if st.button("بناء النموذج المالي V12", disabled=build_disabled, type="primary"):
            with st.spinner("بناء النموذج المالي وطبقة السيولة والتحصيل..."):
                build_models_from_session(revenue_definition)
            go_to("3. جاهزية التحليل")

        if preview_expense_model is not None and not st.session_state.expense_mapping_saved:
            st.warning("احفظي تصنيف المصاريف قبل بناء النموذج.")


# -----------------------------------------------------------------------------
# Readiness
# -----------------------------------------------------------------------------
elif page == "3. جاهزية التحليل":
    section_header("3. قابلية التحليل من البيانات الحالية")
    render_hero("ما الذي يمكن استخراجه الآن؟", "هذه الصفحة تترجم الملفات المرفوعة إلى نطاق تحليل واضح: ماذا نستطيع تشخيصه بثقة، وما الذي يحتاج ملفًا إضافيًا قبل الاعتماد على التوقعات.")

    profile = build_readiness_profile(st.session_state.files, refresh_business_profile(), st.session_state.models)
    main_col, side_col = st.columns([2.7, 1])
    with main_col:
        c1, c2, c3 = st.columns(3)
        with c1:
            kpi_card("درجة قابلية التحليل", f"{profile['score']}%", profile["label"])
        with c2:
            kpi_card("ثقة قراءة الملفات", f"{profile['avg_confidence']*100:.0f}%", "مدى وضوح بنية الملفات")
        with c3:
            branch_note = "يمكن تحليله" if profile.get("branch_signal",{}).get("has_branch_signal") else "غير متوفر"
            kpi_card("تحليل الفروع", branch_note, "حسب الأعمدة أو نصوص الملفات")

        st.markdown(f"""
        <div class="wazen-action-box">
            <h3>{profile['label']}</h3>
            <p>{profile['status']}</p>
        </div>
        """, unsafe_allow_html=True)
    with side_col:
        render_suggested_file_column(profile)

    if st.session_state.get("pending_rebuild"):
        min_status = minimum_model_status(st.session_state.files)
        if not min_status["ok"]:
            render_minimum_model_guard(min_status)
        elif st.button("تحديث النموذج بالملفات المضافة", type="primary"):
            with st.spinner("إعادة بناء النموذج..."):
                build_models_from_session(st.session_state.get("revenue_definition", REVENUE_DEFINITIONS[0]))
            st.success("تم تحديث النموذج بالملفات الجديدة.")
            st.rerun()

    st.markdown("### نطاق التحليل المتاح")
    checks_df = profile["checks"].copy()
    if not checks_df.empty:
        checks_df["الحالة"] = checks_df["الحالة"].replace({"متوفر": "✅ متوفر", "غير متوفر": "⚠️ غير متوفر"})
    st.dataframe(checks_df, use_container_width=True, hide_index=True)

    st.markdown("### الملفات المقروءة")
    uploaded_df = profile["uploaded_files"].copy()
    if uploaded_df.empty:
        st.info("لم يتم رفع ملفات بعد.")
    else:
        st.dataframe(uploaded_df, use_container_width=True, hide_index=True)

    st.markdown("### كيف نرفع دقة القرار؟")
    st.caption("تظهر الملفات المقترحة في العمود الجانبي مع إمكانية إضافتها مباشرة دون الرجوع لصفحة الرفع.")

    if profile.get("branch_signal", {}).get("files"):
        st.markdown("### ملفات يظهر فيها أثر للفروع")
        st.write("، ".join(profile["branch_signal"]["files"]))


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

        st.markdown("### التشخيص قبل الأرقام")
        full_model = models.get("comprehensive_model", {})
        cfo_reading = full_model.get("cfo_reading") or {}
        if cfo_reading:
            headline = cfo_reading.get("headline", "")
            diagnosis_text = cfo_reading.get("diagnosis", "")
            cash_text = cfo_reading.get("liquidity", "")
            action_text = cfo_reading.get("action", "")
        else:
            cfo_brief = build_cfo_executive_brief(exec_kpis, pnl_model, liq_model, liq_diag, profile)
            headline = cfo_brief["headline"]
            diagnosis_text = cfo_brief["issue"]
            cash_text = cfo_brief["cash_line"]
            action_text = cfo_brief["action"]
        tone_class = "danger" if exec_kpis.get("net_profit",0) < 0 else "focus"
        st.markdown(f"""
        <div class="cfo-brief-pro">
            <h3>أكبر رسالة لصاحب العمل الآن</h3>
            <p class="{tone_class}">{headline}</p>
            <p><strong>قراءة البيانات:</strong> {diagnosis_text}</p>
            <p><strong>السيولة ورأس المال العامل:</strong> {cash_text}</p>
            <p><strong>الإجراء العملي القادم:</strong> {action_text}</p>
        </div>
        """, unsafe_allow_html=True)

        health = full_model.get("financial_health_score", {}) if full_model else {}
        questions = cfo_reading.get("four_questions", {}) if cfo_reading else {}
        if health:
            h1, h2 = st.columns([1, 3])
            with h1:
                kpi_card("Financial Health Score", f"{health.get('score',0):.0f}/100", health.get("label", ""))
            with h2:
                if cfo_reading.get("ai_summary"):
                    st.markdown("#### قراءة AI CFO")
                    st.write(cfo_reading.get("ai_summary"))
                if questions:
                    st.markdown("#### الأسئلة الأربعة")
                    st.dataframe(pd.DataFrame([{"السؤال": k, "الإجابة": v} for k, v in questions.items()]), use_container_width=True, hide_index=True)

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
            kpi_card("صافي الإيرادات", f"{exec_kpis.get('operating_revenue',0):,.0f}", "إيراد النشاط")
        with c2:
            kpi_card("صافي الربح", f"{exec_kpis.get('net_profit',0):,.0f}", f"هامش {exec_kpis.get('net_margin',0)*100:.1f}%")
        with c3:
            kpi_card("هامش الأمان", f"{breakeven_model.get('margin_of_safety',0)*100:.1f}%", "قبل نقطة التعادل")
        with c4:
            cash_cards = (liq_model.get("cash") or {}).get("cards", {})
            kpi_card("النقد", f"{cash_cards.get('ending_cash',0):,.0f}", "من تقرير السيولة إن توفر")
        with c5:
            runway = cash_cards.get("cash_runway_months")
            kpi_card("فترة التغطية النقدية", "—" if runway is None else f"{runway:.1f} شهر", "مبدئي قبل تنظيف التحويلات")


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
        full_model = models.get("comprehensive_model", {})
        tabs = st.tabs(["قراءة البيانات", "النسب المالية", "التحليل الرأسي والأفقي", "جودة الإيراد", "الربحية", "السيولة والنقد", "التحصيل", "المصاريف", "معايير القطاع"])

        with tabs[0]:
            st.subheader("قراءة البيانات المالية")
            cfo_reading = full_model.get("cfo_reading", {})
            if cfo_reading:
                st.markdown(f"""
                <div class="cfo-brief-pro">
                    <h3>قراءة CFO من البيانات الحالية</h3>
                    <p class="focus">{cfo_reading.get('headline','')}</p>
                    <p><strong>التشخيص:</strong> {cfo_reading.get('diagnosis','')}</p>
                    <p><strong>السيولة:</strong> {cfo_reading.get('liquidity','')}</p>
                    <p><strong>الإجراء:</strong> {cfo_reading.get('action','')}</p>
                </div>
                """, unsafe_allow_html=True)
            data_reading = full_model.get("data_reading", pd.DataFrame())
            if not data_reading.empty:
                st.markdown("#### ما الذي قرأه الإيجنت من الملفات؟")
                st.dataframe(data_reading, use_container_width=True, hide_index=True)
            mgmt = full_model.get("management_pnl", {})
            if mgmt and not mgmt.get("management_table", pd.DataFrame()).empty:
                st.markdown("#### قائمة الدخل الإدارية بعد إعادة تصنيف تكلفة الإيراد")
                st.caption("هذه القراءة تعالج المشكلة التي ظهرت في الشركات البرمجية: رواتب التشغيل والدعم والتنفيذ ليست دائمًا مصاريف إدارية؛ قد تكون تكلفة إيراد إذا كانت مرتبطة بتقديم الخدمة.")
                st.dataframe(mgmt.get("management_table"), use_container_width=True, hide_index=True)
            bs = (full_model.get("balance_sheet") or {})
            if bs.get("available"):
                st.markdown("#### المركز المالي التحليلي")
                st.dataframe(bs.get("balance_sheet", pd.DataFrame()), use_container_width=True, hide_index=True)
            else:
                st.info("المركز المالي غير متاح قبل قراءة ميزان مراجعة صالح.")

        with tabs[1]:
            st.subheader("النسب المالية ومعايير السلامة")
            st.caption("هذه النسب هي الحد الأدنى لأي محلل مالي: ربحية، سيولة، مديونية، وكفاءة. المعايير هنا إرشادية قابلة للتعديل حسب القطاع والمدينة ونموذج العمل.")
            health = full_model.get("financial_health_score", {})
            findings_df = full_model.get("diagnostic_findings", pd.DataFrame())
            if health:
                c1, c2 = st.columns([1, 3])
                with c1:
                    kpi_card("Financial Health Score", f"{health.get('score',0):.0f}/100", health.get("label", ""))
                with c2:
                    st.caption("الدرجة مركبة من الربحية والسيولة ورأس المال العامل والمديونية وجودة التدفق النقدي. انخفاض الدرجة يجب أن يظهر معه سبب وإجراء، وليس رقمًا فقط.")
            if isinstance(findings_df, pd.DataFrame) and not findings_df.empty:
                st.markdown("#### أهم نتائج التشخيص مرتبة حسب الأولوية")
                st.dataframe(findings_df.drop(columns=["الأولوية"], errors="ignore").head(5), use_container_width=True, hide_index=True)
            ratio_df = full_model.get("ratios", pd.DataFrame())
            if not ratio_df.empty:
                groups = list(ratio_df["المجموعة"].dropna().unique())
                selected_groups = safe_multiselect("فلترة مجموعات النسب", groups, default=groups)
                view = ratio_df[ratio_df["المجموعة"].isin(selected_groups)] if selected_groups else ratio_df
                st.dataframe(view, use_container_width=True, hide_index=True)
                st.markdown("#### قراءة سريعة")
                risk_rows = ratio_df[ratio_df["الحكم"].isin(["خطر", "ضعيف"])]
                if risk_rows.empty:
                    st.success("لا تظهر مؤشرات خطر حادة ضمن النسب المحسوبة، لكن القرار النهائي يحتاج قراءة السيولة والتحصيل والتصنيف النهائي للمصاريف.")
                else:
                    for _, r in risk_rows.head(5).iterrows():
                        st.warning(f"{r['المؤشر']}: {r['النتيجة']} — {r.get('قراءة CFO', r.get('قراءة أولية', ""))}")
            else:
                st.info("لا يمكن حساب النسب قبل بناء قائمة دخل ومركز مالي.")

        with tabs[2]:
            st.subheader("التحليل الرأسي والأفقي")
            st.markdown("#### التحليل الرأسي لقائمة الدخل")
            vi = full_model.get("vertical_income", pd.DataFrame())
            if not vi.empty:
                st.dataframe(vi, use_container_width=True, hide_index=True)
            st.markdown("#### التحليل الرأسي للمركز المالي")
            vb = full_model.get("vertical_balance", pd.DataFrame())
            if not vb.empty:
                st.dataframe(vb, use_container_width=True, hide_index=True)
            st.markdown("#### التحليل الأفقي الشهري")
            hm = full_model.get("horizontal_monthly", pd.DataFrame())
            if not hm.empty:
                st.dataframe(hm, use_container_width=True, hide_index=True)
            else:
                st.info("التحليل الأفقي الشهري يحتاج مبيعات ومصاريف شهرية مقروءة.")
            st.markdown("#### أكبر تغيرات المركز المالي بين أول وآخر الفترة")
            hb = full_model.get("horizontal_balance", pd.DataFrame())
            if not hb.empty:
                st.dataframe(hb, use_container_width=True, hide_index=True)

        with tabs[3]:
            st.subheader("جودة الإيراد")
            if revenue_model and not revenue_model.get("monthly_revenue", pd.DataFrame()).empty:
                rev_monthly = revenue_model["monthly_revenue"].copy()
                rev_monthly["revenue"] = pd.to_numeric(rev_monthly["revenue"], errors="coerce").fillna(0)
                rev_quality = build_revenue_quality(rev_monthly)
                c1,c2,c3,c4 = st.columns(4)
                with c1: kpi_card("إجمالي الإيرادات", f"{rev_quality['cards'].get('total',0):,.0f}", "خلال الفترة")
                with c2: kpi_card("متوسط شهري", f"{rev_quality['cards'].get('avg',0):,.0f}", "متوسط محافظ")
                with c3: kpi_card("أعلى شهر", str(rev_quality['cards'].get('best_month','—')), f"{rev_quality['cards'].get('max_share',0)*100:.1f}%")
                with c4: kpi_card("انتظام الإيراد", f"{rev_quality['cards'].get('stability_score',0):.0f}/100", "مؤشر يختبر التذبذب وتركيز أعلى شهر")
                render_insight_panel("قراءة مالية للإيراد", rev_quality["narrative"], rev_quality["risk"], rev_quality["action"], ["انتظام الإيراد يعني: هل الإيراد متوازن عبر الأشهر أم معتمد على شهر أو عقد استثنائي؟", "لا نكتفي بالمبيعات الإجمالية؛ المرحلة التالية ستقرأ الإجمالي والخصومات والمرتجعات والصافي عند توفر ملف تفصيلي."])
                st.markdown("#### تفسير مؤشرات جودة الإيراد")
                st.dataframe(rev_quality.get("quality_table", pd.DataFrame()), use_container_width=True, hide_index=True)
                line_chart(rev_monthly, "month", "revenue", "اتجاه الإيرادات")
                st.dataframe(rev_quality.get("monthly_table", rev_monthly), use_container_width=True, hide_index=True)
            else:
                st.info("لا توجد بيانات إيرادات كافية.")

        with tabs[4]:
            st.subheader("الربحية وقائمة الدخل")
            render_executive_income_statement(build_executive_income_statement(pnl_model, expense_model))
            if monthly_pnl_model is not None and not monthly_pnl_model.empty:
                st.markdown("#### الربحية الشهرية")
                render_executive_monthly_profitability(build_executive_monthly_profitability(monthly_pnl_model, pnl_model, expense_model))

        with tabs[5]:
            st.subheader("السيولة النقدية")
            cash = liq_model.get("cash", {})
            if cash.get("available"):
                cards = cash.get("cards", {})
                c1,c2,c3,c4 = st.columns(4)
                with c1: kpi_card("النقد الداخل", f"{cards.get('total_cash_in',0):,.0f}", "داخلة خلال الفترة")
                with c2: kpi_card("النقد الخارج", f"{cards.get('total_cash_out',0):,.0f}", "خارجة خلال الفترة")
                with c3: kpi_card("صافي الحركة النقدية", f"{cards.get('net_cash_flow',0):,.0f}", "صافي الحركة")
                with c4:
                    runway = cards.get("cash_runway_months")
                    kpi_card("فترة التغطية النقدية", "—" if runway is None else f"{runway:.1f} شهر", "مبدئي")
                monthly = cash.get("monthly", pd.DataFrame())
                if not monthly.empty:
                    st.dataframe(monthly, use_container_width=True, hide_index=True)
                    line_chart(monthly, "month", "ending_cash_proxy", "اتجاه الرصيد النقدي التراكمي")
            else:
                st.warning("لا يوجد تقرير سيولة نقدية مقروء. يمكن استخدام كشوف البنك لاحقًا للتحقق والتفصيل، لكن الأفضل رفع تقرير السيولة النقدية للحصول على قراءة شهرية مباشرة.")
                cash_extra = st.file_uploader("إضافة تقرير السيولة النقدية من هنا", type=["xlsx", "xls"], accept_multiple_files=True, key="cash_tab_extra_upload")
                if cash_extra and st.button("قراءة تقرير السيولة وتحديث التحليل", key="cash_tab_extra_btn"):
                    ingest_uploaded_files(cash_extra, append=True)
                    build_models_from_session(st.session_state.get("revenue_definition", REVENUE_DEFINITIONS[0]))
                    st.success("تم تحديث تحليل السيولة.")
                    st.rerun()

        with tabs[6]:
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
                st.warning("لا يوجد ملف أعمار عملاء. لن نكتفي بتوصية عامة؛ عند رفعه سيظهر العملاء والأرصدة وأولوية التحصيل بالأسماء.")
                ar_extra = st.file_uploader("إضافة أعمار ديون العملاء من هنا", type=["xlsx", "xls"], accept_multiple_files=True, key="ar_tab_extra_upload")
                if ar_extra and st.button("قراءة أعمار العملاء وتحديث التحليل", key="ar_tab_extra_btn"):
                    ingest_uploaded_files(ar_extra, append=True)
                    build_models_from_session(st.session_state.get("revenue_definition", REVENUE_DEFINITIONS[0]))
                    st.success("تم تحديث تحليل التحصيل.")
                    st.rerun()

        with tabs[7]:
            st.subheader("المصاريف وهيكل التكلفة")
            if expense_model:
                monthly_exp = expense_model.get("monthly_expenses", pd.DataFrame()).copy()
                cat_df = expense_model.get("by_category", pd.DataFrame()).copy()
                c1,c2 = st.columns(2)
                with c1:
                    st.markdown("#### المصاريف الشهرية")
                    st.dataframe(monthly_exp, use_container_width=True, hide_index=True)
                    if not monthly_exp.empty: bar_chart(monthly_exp, "month", "expenses", "المصاريف الشهرية")
                with c2:
                    st.markdown("#### هيكل المصاريف")
                    st.dataframe(cat_df, use_container_width=True, hide_index=True)
                    if not cat_df.empty: pie_chart(cat_df, "category", "amount", "Expense Structure")
                st.markdown("#### أكبر بنود المصاريف")
                st.dataframe(expense_model.get("top_expenses", pd.DataFrame()), use_container_width=True, hide_index=True)
            else:
                st.info("لا توجد مصاريف كافية.")

        with tabs[8]:
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
elif page == "6. استوديو السيناريوهات":
    section_header("6. استوديو السيناريوهات")
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
        st.caption("كل مؤشر مضبوط بحيث يكون 0 في المنتصف: اليمين يعني تحسن/زيادة، واليسار يعني انخفاض/تراجع. القيم هنا تغير عن الوضع الحالي وليست أرقامًا نهائية جامدة.")
        base_collection = 40
        c1,c2,c3 = st.columns(3)
        with c1:
            sales_growth = st.slider("تغير المبيعات %", -50, 50, 0)
            discount_delta = st.slider("تغير الخصومات — نقطة مئوية", -30, 30, 0)
            return_delta = st.slider("تغير المرتجعات — نقطة مئوية", -30, 30, 0)
        with c2:
            dso_delta = st.slider("تغير أيام التحصيل DSO", -60, 60, 0, help="السالب يعني تحصيل أسرع، والموجب يعني تحصيل أبطأ")
            dpo_delta = st.slider("تغير أيام السداد DPO", -60, 60, 0, help="السالب يعني سداد أسرع للموردين، والموجب يعني تأخير السداد")
            opex_change = st.slider("تغير المصروفات %", -50, 50, 0)
        with c3:
            cogs_change = st.slider("تغير تكلفة المبيعات %", -50, 50, 0)
            supplier_payment = st.number_input("دفعات موردين إضافية", value=0.0, step=1000.0)
            tax_payment = st.number_input("ضريبة/زكاة متوقعة", value=0.0, step=1000.0)

        res = run_simple_scenario(base, {
            "sales_growth_pct": sales_growth,
            "discount_change_pp": discount_delta,
            "return_change_pp": return_delta,
            "dso_days_delta": dso_delta,
            "dpo_days_delta": dpo_delta,
            "opex_change_pct": opex_change,
            "cogs_change_pct": cogs_change,
            "supplier_payment": supplier_payment,
            "tax_payment": tax_payment,
        })
        c1,c2,c3,c4 = st.columns(4)
        with c1: kpi_card("صافي الإيرادات", f"{res['net_sales']:,.0f}", f"تسرب تجاري {res['commercial_leakage']:,.0f}")
        with c2: kpi_card("صافي الربح", f"{res['net_profit']:,.0f}", "بعد أثر السيناريو")
        with c3: kpi_card("النقد بعد 30 يوم", f"{res['ending_cash_30']:,.0f}", "تقدير أولي")
        with c4: kpi_card("فترة التغطية النقدية", "—" if res['cash_runway_months'] is None else f"{res['cash_runway_months']:.1f} شهر", res["risk_level"])


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
