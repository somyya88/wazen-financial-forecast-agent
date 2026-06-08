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

st.markdown('<h1 class="main-title">Wazen CFO Intelligence Agent V7</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">حوّل ملفاتك المالية إلى نموذج CFO يمنع تكرار الإيرادات ويقرأ المصاريف ويجهّز لوحة قرار تنفيذية.</p>', unsafe_allow_html=True)

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
)

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

    if st.button("بناء النموذج المالي الأولي"):
        readable_files = [r for r in st.session_state.files if not r.get("read_error")]
        revenue_record = next((r for r in readable_files if r["selected_role"] == "official_revenue_source"), None)
        expense_record = next((r for r in readable_files if r["selected_role"] == "official_expense_source"), None)
        tb_record = next((r for r in readable_files if r["selected_role"] == "validation_source" and r["detected_type"] == "trial_balance"), None)

        revenue_model = build_revenue_model(revenue_record, revenue_definition) if revenue_record else None
        revenue_total = revenue_model.get("total_revenue", 0) if revenue_model else 0

        expense_model = build_expense_model(expense_record, revenue_total) if expense_record else None
        tb_model = parse_trial_balance(tb_record) if tb_record else None
        financial_model = build_basic_financial_model(revenue_model, expense_model)
        validation_checks = validate_project(updated_rows, revenue_model, expense_model, tb_model)

        st.session_state.models = {
            "revenue_model": revenue_model,
            "expense_model": expense_model,
            "tb_model": tb_model,
            "financial_model": financial_model,
            "validation_checks": validation_checks,
        }
        st.success("تم بناء النموذج المالي الأولي.")

if st.session_state.models:
    models = st.session_state.models
    revenue_model = models.get("revenue_model")
    expense_model = models.get("expense_model")
    financial_model = models.get("financial_model")
    validation_checks = models.get("validation_checks")

    section_header("3. فحص جودة البيانات")

    for check in validation_checks:
        message_box(f"**{check['check']}** — {check['message']}", check["level"])

    section_header("4. Dashboard أولي")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Revenue / الإيرادات", f"{financial_model.get('revenue', 0):,.0f}", "من مصدر الإيرادات الرسمي فقط")
    with c2:
        kpi_card("Expenses / المصاريف", f"{financial_model.get('expenses', 0):,.0f}", "من مصدر المصاريف الرسمي")
    with c3:
        kpi_card("Preliminary Profit / ربح أولي", f"{financial_model.get('gross_profit_preliminary', 0):,.0f}", "قبل فصل COGS وOpex")
    with c4:
        kpi_card("Preliminary Margin / هامش أولي", f"{financial_model.get('net_margin_preliminary', 0):.1%}", "مؤشر أولي فقط")

    active_tabs = tabs_for_mode(analysis_mode)
    section_header("5. الصفحات المفعلة حسب نوع التحليل")
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
            elif tab_name == "Export":
                st.subheader("تصدير Excel CFO Pack")
                excel_bytes = build_excel_pack(
                    st.session_state.file_rows,
                    revenue_model,
                    expense_model,
                    financial_model,
                    validation_checks,
                )
                st.download_button(
                    "تحميل Excel CFO Pack",
                    data=excel_bytes,
                    file_name="wazen_cfo_pack_v7.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            else:
                st.info("هذه الصفحة ستكون ضمن Sprint 2 بعد تثبيت صحة القراءة والمنطق المالي.")
