from __future__ import annotations

import re
import pandas as pd
import streamlit as st

from config import APP_NAME, SOURCE_ROLES, REVENUE_DEFINITIONS
from cfo_core_v13_4 import infer_period_context, build_source_of_truth_report
from data_reader import read_excel_file
from file_detector import detect_file_type
from source_roles import suggest_role
from file_role_resolver import apply_role_resolution_to_record, has_liquidity_files, liquidity_files_summary

from revenue_engine import build_revenue_model
from expense_engine import build_expense_model, build_expense_model_from_trial_balance
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
from ai_executive_diagnosis_engine import (
    build_ai_diagnosis_payload,
    generate_ai_executive_diagnosis,
    fallback_executive_diagnosis,
    payload_signature,
    openai_available,
)
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
from sector_profile_engine_v12_8 import get_sector_intelligence_profile, sector_profile_table
from metric_source_guard_v12_8 import build_metric_guard_report, metric_guard_summary
from benchmark_intelligence_engine_v12_8 import build_benchmark_intelligence
from decision_ux_v12_8 import (
    render_sector_intelligence_panel,
    render_metric_guard_experience,
    render_cfo_command_center,
    render_metric_catalog_reference,
)


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
    "ai_exec_diag_cache": {},
    "ai_exec_diag_signature": "",
    "analysis_year": None,
    "base_year": None,
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
            <span class="required-badge">★ الحد الأدنى لبناء القوائم</span>
            <div class="ux-card-title">ميزان مراجعة واحد كافٍ للبدء</div>
            <div class="ux-card-text">من ميزان المراجعة يتم استخراج قائمة الدخل، المركز المالي، الربحية، السيولة الأساسية، والمديونية. لا يتوقف التحليل عند غياب الملفات التفصيلية.</div>
        </div>
        <div class="ux-card should-have">
            <span class="enhance-badge">يرفع دقة القرار</span>
            <div class="ux-card-title">مبيعات + مصروفات + سنة سابقة</div>
            <div class="ux-card-text">تضيف التحليل الشهري، المقارنة مع العام السابق، اتجاهات الإيراد، نسب المصاريف، والتنبؤ الأولي.</div>
        </div>
        <div class="ux-card optional-data">
            <span class="optional-badge">تحليل CFO متقدم</span>
            <div class="ux-card-title">سيولة + أعمار عملاء/موردين + أصناف/فروع</div>
            <div class="ux-card-text">تضيف DSO وDPO وCCC، أولويات التحصيل بالأسماء، تحليل المنتجات والفروع، والسيناريوهات الأدق.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def minimum_model_status(files: list[dict]) -> dict:
    """File-aware model gate.
    A trial balance alone is enough to build Level A financial analysis.
    Revenue/expense/cash/aging files increase depth but must not block analysis.
    """
    readable = [r for r in files or [] if not r.get("read_error")]
    roles = {str(r.get("selected_role") or "") for r in readable}
    has_revenue = "official_revenue_source" in roles
    has_expense = "official_expense_source" in roles
    has_tb = "validation_source" in roles
    has_cash = "cash_source" in roles
    has_ar = "ar_aging_source" in roles
    has_ap = "ap_aging_source" in roles

    # Level A: Trial balance. Alternative starter: monthly revenue + expense when TB is absent.
    ok = has_tb or (has_revenue and has_expense)
    missing = []
    if not ok:
        missing.append("ميزان مراجعة أو ملف مبيعات مع ملف مصروفات")

    if has_tb:
        level = "A - Financial Analysis"
        message = "يمكن بناء القوائم المالية والنسب الأساسية من ميزان المراجعة. الملفات الأخرى ستضيف عمقًا، لكنها ليست شرطًا لبدء التحليل."
    elif has_revenue and has_expense:
        level = "A مبدئي - Operational P&L"
        message = "يمكن بناء قراءة أولية للربحية من المبيعات والمصروفات، لكن المركز المالي ونسب السيولة تحتاج ميزان مراجعة."
    else:
        level = "غير جاهز"
        message = "يلزم ملف أساس واحد على الأقل: ميزان مراجعة، أو مبيعات ومصروفات معًا."

    return {
        "ok": ok,
        "level": level,
        "message": message,
        "has_revenue": has_revenue,
        "has_expense": has_expense,
        "has_tb": has_tb,
        "has_cash": has_cash,
        "has_ar": has_ar,
        "has_ap": has_ap,
        "missing": missing,
    }


def render_minimum_model_guard(status: dict):
    missing = "، ".join(status.get("missing") or [])
    st.markdown(f"""
    <div class="wazen-soft-warning">
        <strong>لا يوجد ملف أساس كافٍ لبناء النموذج بعد.</strong><br>
        المطلوب للبدء: {missing or 'ميزان مراجعة أو مبيعات + مصروفات'}.<br>
        ملاحظة: ميزان المراجعة وحده يكفي لاستخراج قائمة دخل ومركز مالي ونسب أساسية، ثم تُستخدم باقي الملفات لتعميق التحليل لا لإيقافه.
    </div>
    """, unsafe_allow_html=True)


def _ratio_row(ratio_df: pd.DataFrame, code: str) -> dict:
    if ratio_df is None or ratio_df.empty or "الكود" not in ratio_df.columns:
        return {}
    m = ratio_df[ratio_df["الكود"].astype(str).eq(code)]
    if m.empty:
        return {}
    return m.iloc[0].to_dict()


def _ratio_result(ratio_df: pd.DataFrame, code: str, default="غير محسوب") -> str:
    row = _ratio_row(ratio_df, code)
    return str(row.get("النتيجة", default)) if row else default


def _ratio_status(ratio_df: pd.DataFrame, code: str) -> str:
    row = _ratio_row(ratio_df, code)
    return str(row.get("الحكم", "")) if row else ""



def _as_number(value, default=None):
    try:
        if value is None or pd.isna(value):
            return default
    except Exception:
        pass
    if isinstance(value, str):
        txt = value.replace(',', '').replace('%','').replace('x','').replace('يوم','').replace('شهر','').strip()
        if txt in ['—', '-', 'غير متاح', 'غير محسوب', '']:
            return default
        try:
            return float(txt)
        except Exception:
            return default
    try:
        return float(value)
    except Exception:
        return default


def _money0(value):
    n = _as_number(value, 0.0)
    return f"{n:,.0f}"


def _pct0(value):
    n = _as_number(value, None)
    return "—" if n is None else f"{n*100:.1f}%"


def _metric_value(full_model: dict, code: str):
    return ((full_model.get('metric_pack', {}) or {}).get('metrics', {}) or {}).get(code)


# -----------------------------------------------------------------------------
# V13.5 decision-quality helpers
# -----------------------------------------------------------------------------
BENCHMARK_KEY_MAP = {
    "cogs_ratio": "direct_cost_ratio",
    "direct_cost_ratio": "direct_cost_ratio",
    "gross_margin": "gross_margin",
    "net_margin": "net_margin",
    "opex_ratio": "opex_ratio",
    "admin_ratio": "opex_ratio",
    "sm_ratio": "opex_ratio",
    "revenue_leakage_ratio": "return_rate",
    "discount_rate": "discount_rate",
    "return_rate": "return_rate",
    "margin_of_safety": "margin_of_safety",
}

GENERIC_RATIO_BENCHMARKS = {
    "operating_margin": {"safe": 0.10, "watch": 0.00, "direction": "higher", "unit": "%", "label": "هامش تشغيل"},
    "net_margin": {"safe": 0.07, "watch": 0.03, "direction": "higher", "unit": "%", "label": "صافي هامش"},
    "current_ratio": {"safe": 1.50, "watch": 1.00, "direction": "higher", "unit": "x", "label": "سيولة قصيرة الأجل"},
    "quick_ratio": {"safe": 1.00, "watch": 0.60, "direction": "higher", "unit": "x", "label": "سيولة سريعة"},
    "cash_ratio": {"safe": 0.50, "watch": 0.20, "direction": "higher", "unit": "x", "label": "غطاء نقدي فوري"},
    "dso": {"safe": 30.0, "watch": 60.0, "direction": "lower", "unit": "يوم", "label": "أيام تحصيل"},
    "dpo": {"safe": 45.0, "watch": 75.0, "direction": "band", "unit": "يوم", "label": "أيام سداد"},
    "ccc": {"safe": 30.0, "watch": 75.0, "direction": "lower", "unit": "يوم", "label": "دورة نقد"},
    "receivables_turnover": {"safe": 8.0, "watch": 4.0, "direction": "higher", "unit": "x", "label": "دوران ذمم"},
    "inventory_turnover": {"safe": 6.0, "watch": 3.0, "direction": "higher", "unit": "x", "label": "دوران مخزون"},
    "debt_ratio": {"safe": 0.50, "watch": 0.75, "direction": "lower", "unit": "%", "label": "نسبة الالتزامات"},
    "debt_to_equity": {"safe": 1.00, "watch": 2.00, "direction": "lower", "unit": "x", "label": "رافعة مالية"},
}


def _metric_raw_value(full_model: dict, code: str):
    return ((full_model.get('metric_pack', {}) or {}).get('metrics', {}) or {}).get(code)


def _metric_current_value(full_model: dict, ratio_row: dict | None, code: str):
    raw = _metric_raw_value(full_model, code)
    if raw is not None:
        return _as_number(raw, None)
    if ratio_row:
        return _as_number(ratio_row.get('النتيجة'), None)
    return None


def _fmt_benchmark_value(value, unit: str = "%") -> str:
    n = _as_number(value, None)
    if n is None:
        return "—"
    if unit == "%":
        return f"{n*100:.1f}%"
    if unit == "x":
        return f"{n:.2f}x"
    if unit == "يوم":
        return f"{n:.0f} يوم"
    return f"{n:,.0f}"


def _benchmark_for_metric(code: str, profile: dict | None = None) -> dict:
    profile = profile or refresh_business_profile()
    sector = profile.get('sector', 'خدمي')
    cfg = get_sector_config(sector)
    key = BENCHMARK_KEY_MAP.get(code, code)
    b = (cfg.get('benchmarks') or {}).get(key)
    if b:
        direction = 'lower' if key in ['direct_cost_ratio', 'opex_ratio', 'return_rate', 'discount_rate'] else 'higher'
        return {
            'available': True,
            'key': key,
            'label': b.get('label', key),
            'safe': b.get('safe'),
            'watch': b.get('watch'),
            'direction': direction,
            'unit': '%',
            'basis': 'معيار قطاعي إرشادي داخلي',
            'confidence': 'إرشادي حتى ربط مصدر خارجي موثق',
        }
    g = GENERIC_RATIO_BENCHMARKS.get(code)
    if g:
        return {
            'available': True,
            'key': code,
            'label': g.get('label', code),
            'safe': g.get('safe'),
            'watch': g.get('watch'),
            'direction': g.get('direction'),
            'unit': g.get('unit', 'x'),
            'basis': 'قاعدة مالية عامة إرشادية',
            'confidence': 'إرشادي',
        }
    return {'available': False, 'basis': 'لا يوجد معيار مدمج لهذا المؤشر', 'confidence': '—'}


def _benchmark_range_text(b: dict) -> str:
    if not b or not b.get('available'):
        return 'لا يوجد معيار مدمج'
    unit = b.get('unit', '%')
    safe = _fmt_benchmark_value(b.get('safe'), unit)
    watch = _fmt_benchmark_value(b.get('watch'), unit)
    direction = b.get('direction')
    if direction == 'lower':
        return f"آمن ≤ {safe} | مراقبة ≤ {watch}"
    if direction == 'band':
        return f"إرشادي حول {safe} | راقب بعد {watch}"
    return f"آمن ≥ {safe} | مراقبة ≥ {watch}"


def _benchmark_status_for_value(code: str, value, profile: dict | None = None) -> tuple[str, str]:
    b = _benchmark_for_metric(code, profile)
    n = _as_number(value, None)
    if n is None:
        return 'غير محسوب', 'لا توجد قيمة صالحة للمقارنة.'
    if not b.get('available'):
        return 'إرشادي', 'لا يوجد معيار مدمج؛ اعتمد المقارنة الداخلية أولًا.'
    safe = _as_number(b.get('safe'), None)
    watch = _as_number(b.get('watch'), None)
    direction = b.get('direction')
    if safe is None or watch is None:
        return 'إرشادي', 'المعيار غير مكتمل.'
    if direction == 'lower':
        if n <= safe:
            return 'ضمن الآمن', 'القيمة ضمن النطاق الآمن الإرشادي.'
        if n <= watch:
            return 'مراقبة', 'القيمة أعلى من الآمن لكنها لم تصل لمستوى خطر.'
        return 'خطر', 'القيمة تتجاوز نطاق المراقبة وتحتاج إجراء.'
    if direction == 'band':
        if n <= watch:
            return 'مقبول', 'القيمة ضمن نطاق مقبول مبدئيًا، لكن الحكم يعتمد على شروط الموردين والتحصيل.'
        return 'مراقبة', 'القيمة مرتفعة؛ تأكد أنها ليست نتيجة تأخر سداد ضار بالعلاقات أو السمعة.'
    # higher is better
    if n >= safe:
        return 'ضمن الآمن', 'القيمة أعلى من حد الأمان الإرشادي.'
    if n >= watch:
        return 'مراقبة', 'القيمة مقبولة لكن هامش الأمان محدود.'
    return 'خطر', 'القيمة أقل من نطاق المراقبة وتحتاج إجراء.'


def _enrich_ratios_with_benchmarks(df: pd.DataFrame, full_model: dict | None = None, profile: dict | None = None) -> pd.DataFrame:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return df
    profile = profile or refresh_business_profile()
    full_model = full_model or {}
    out = df.copy()
    codes = out.get('الكود', pd.Series([''] * len(out))).astype(str).tolist()
    standards, comparisons, bases = [], [], []
    for i, (_, row) in enumerate(out.iterrows()):
        code = codes[i]
        b = _benchmark_for_metric(code, profile)
        val = _metric_current_value(full_model, row.to_dict(), code)
        status, note = _benchmark_status_for_value(code, val, profile)
        standards.append(_benchmark_range_text(b))
        comparisons.append(status)
        bases.append(b.get('basis', '—'))
    out['المعيار بجانب النسبة'] = standards
    out['مقارنة بالمعيار'] = comparisons
    out['نوع المعيار'] = bases
    return out


def _trend_badge_from_value(value) -> str:
    txt = str(value or '').strip()
    if txt in ['', '—', '-', 'nan', 'None']:
        return '<span class="v138-trend neutral">▬ —</span>'
    n = _as_number(txt, None)
    if n is None:
        return _html_escape(txt)
    if abs(n) < 1e-9:
        return f'<span class="v138-trend neutral">▬ {txt}</span>'
    if n > 0:
        return f'<span class="v138-trend ok">▲ {txt}</span>'
    return f'<span class="v138-trend danger">▼ {txt}</span>'


def _add_trend_indicator(df: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return df
    out = df.copy()
    trend_cols = [c for c in out.columns if any(k in str(c) for k in ['نمو', 'تغير', 'نسبة التغير'])]
    for col in trend_cols:
        out[col] = out[col].apply(_trend_badge_from_value)
    if 'مؤشر الاتجاه' in out.columns:
        out = out.drop(columns=['مؤشر الاتجاه'])
    return out


def _ratio_source_note(full_model: dict, code: str) -> str:
    period = (full_model.get('source_of_truth_report', {}) or {}).get('period', {}) if full_model else {}
    days = period.get('period_days') or '—'
    basis = period.get('period_basis') or 'غير محدد'
    notes = {
        'current_ratio': 'من المركز المالي: الأصول المتداولة ÷ الالتزامات المتداولة.',
        'quick_ratio': 'من المركز المالي: النقد + العملاء ÷ الالتزامات المتداولة. لا يعتمد على المخزون.',
        'cash_ratio': 'من المركز المالي: النقد ÷ الالتزامات المتداولة. يقيس السداد الفوري فقط.',
        'working_capital': 'من المركز المالي: الأصول المتداولة - الالتزامات المتداولة.',
        'dso': f'تقديري من ميزان المراجعة: رصيد العملاء ÷ متوسط المبيعات اليومية. أيام الفترة المستخدمة: {days}، الأساس: {basis}. الدقة ترتفع عند رفع أعمار العملاء أو رصيد أول/آخر الفترة.',
        'receivables_turnover': 'تقديري من المبيعات ورصيد العملاء. لا يعطي أسماء العملاء أو أولويات التحصيل دون تقرير أعمار العملاء.',
        'dpo': f'تقديري من ميزان المراجعة: الموردون ÷ متوسط تكلفة المبيعات اليومية. أيام الفترة المستخدمة: {days}، الأساس: {basis}. الدقة ترتفع عند رفع أعمار الموردين.',
        'ccc': 'DSO + DIO - DPO. لا يُعتمد كقرار نهائي إذا كانت DSO/DPO/DIO تقديرية أو ناقصة.',
    }
    return notes.get(code, 'مصدر الرقم موضح في حارس المؤشر.')


def _cost_line_status(category: str, ratio_value, profile: dict | None = None) -> str:
    cat = str(category or '').lower()
    if 'cost' in cat or 'cogs' in cat or 'تكلفة' in cat:
        code = 'cogs_ratio'
    elif 'marketing' in cat or 'selling' in cat or 'تسويق' in cat or 'بيع' in cat:
        code = 'sm_ratio'
    else:
        code = 'opex_ratio'
    status, _ = _benchmark_status_for_value(code, ratio_value, profile)
    return status


def _has_inventory_context(full_model: dict, profile: dict | None = None) -> bool:
    profile = profile or refresh_business_profile()
    sector_text = " ".join([str(profile.get(k, '')) for k in ['sector','activity','business_model','sales_channel']]).lower()
    inventory_words = ['تجارة', 'تجاري', 'مطعم', 'مقهى', 'محامص', 'تموين', 'صناعة', 'تصنيع', 'مخزون', 'جملة', 'تجزئة']
    inv = (((full_model.get('balance_sheet', {}) or {}).get('metrics', {}) or {}).get('inventory'))
    return abs(_as_number(inv, 0.0) or 0.0) > 1e-6 or any(w in sector_text for w in inventory_words)


def _confidence_layers(full_model: dict, guarded_df: pd.DataFrame | None = None) -> dict:
    has_tb = bool((full_model.get('balance_sheet', {}) or {}).get('available') or not (full_model.get('data_reading', pd.DataFrame())).empty)
    cogs_basis = str((full_model.get('management_pnl', {}) or {}).get('cogs_basis') or '')
    inventory_sensitive = _has_inventory_context(full_model) and cogs_basis != 'periodic_inventory_formula'
    low_items = 0
    if isinstance(guarded_df, pd.DataFrame) and not guarded_df.empty and 'درجة الثقة' in guarded_df.columns:
        low_items = int(guarded_df['درجة الثقة'].astype(str).str.contains('منخفضة', na=False).sum())
    classification = 'متوسطة' if inventory_sensitive else 'مرتفعة'
    diagnosis = 'متوسطة' if inventory_sensitive or low_items else 'مرتفعة'
    return {
        'data': 'مرتفعة' if has_tb else 'متوسطة',
        'classification': classification,
        'diagnosis': diagnosis,
        'data_note': 'الملفات مقروءة ويمكن تتبع مصدر الرقم.' if has_tb else 'مصادر البيانات محدودة أو غير مكتملة.',
        'classification_note': 'تحتاج تكلفة الإيراد تحققًا من المخزون/تكلفة المبيعات عند وجود نشاط بضاعة.' if inventory_sensitive else 'التصنيف الحالي لا يظهر فجوة جوهرية واضحة.',
        'diagnosis_note': 'القراءة قابلة للاستخدام لكنها ليست نهائية قبل تثبيت تكلفة المبيعات والسيولة النقدية.' if diagnosis != 'مرتفعة' else 'القراءة مدعومة بمصادر كافية حاليًا.',
    }


def _tone_from_status(status: str) -> str:
    text = str(status or '')
    if 'خطر' in text or 'مرتفع' in text or 'خس' in text:
        return 'danger'
    if 'متوسط' in text or 'تقدير' in text or 'مراجعة' in text or 'غير' in text:
        return 'warning'
    return 'ok'




def _decision_tone_from_status(status: str) -> str:
    """Map Arabic decision status to the CSS tone used by decision cards."""
    text = str(status or '')
    if any(k in text for k in ['خطر', 'خسارة', 'خاسر', 'ضعيف', 'خارج', 'مرتفع جداً']):
        return 'danger'
    if any(k in text for k in ['مراقبة', 'تحتاج', 'غير', 'مبدئي', 'متوسط', 'محدود']):
        return 'warning'
    return 'ok'


def _basis_for_decision(metric_key: str, value, profile: dict | None = None) -> dict:
    """Return an auditable status/benchmark basis for executive decision cards.

    This function was referenced by the V14 decision dashboard but was missing from
    the packaged app, causing a NameError on the decision indicators tab.
    """
    profile = profile or {}
    sector = profile.get('sector') or profile.get('القطاع') or 'خدمي'
    cfg = get_sector_config(sector)
    benchmarks = (cfg or {}).get('benchmarks', {}) if isinstance(cfg, dict) else {}

    # Metric-specific thresholds. Values are decimal ratios, not percentages.
    defaults = {
        'operating_margin': {'safe': 0.05, 'watch': 0.00, 'label': 'هامش التشغيل', 'direction': 'higher'},
        'current_ratio': {'safe': 1.50, 'watch': 1.00, 'label': 'نسبة التداول', 'direction': 'higher'},
        'quick_ratio': {'safe': 1.00, 'watch': 0.60, 'label': 'النسبة السريعة', 'direction': 'higher'},
        'cash_ratio': {'safe': 0.50, 'watch': 0.20, 'label': 'نسبة النقدية', 'direction': 'higher'},
        'debt_ratio': {'safe': 0.50, 'watch': 0.75, 'label': 'الالتزامات إلى الأصول', 'direction': 'lower'},
        'debt_to_equity': {'safe': 1.00, 'watch': 2.00, 'label': 'الالتزامات إلى حقوق الملكية', 'direction': 'lower'},
    }

    b = benchmarks.get(metric_key)
    if b:
        direction = 'lower' if metric_key in ['opex_ratio', 'direct_cost_ratio', 'return_rate', 'discount_rate', 'cogs_ratio'] else 'higher'
        label = b.get('label') or metric_key
        safe = b.get('safe')
        watch = b.get('watch')
        source = f"معيار قطاعي إرشادي داخلي — {sector}"
    else:
        d = defaults.get(metric_key, {'safe': None, 'watch': None, 'label': metric_key, 'direction': 'higher'})
        direction = d.get('direction', 'higher')
        label = d.get('label', metric_key)
        safe = d.get('safe')
        watch = d.get('watch')
        source = 'قاعدة مالية إرشادية عامة'

    n = _as_number(value, None)
    if n is None or safe is None or watch is None:
        return {
            'status': 'غير متاح',
            'benchmark': 'لا يوجد معيار رقمي مدمج',
            'basis': source,
            'label': label,
        }

    if direction == 'lower':
        # For lower-better ratios: <= safe is good, <= watch needs monitoring, > watch is risky.
        if n <= safe:
            status = 'ضمن الأمان'
        elif n <= watch:
            status = 'تحت المراقبة'
        else:
            status = 'خطر'
        benchmark = f"آمن ≤ {safe:.1%} | مراقبة ≤ {watch:.1%}" if abs(safe) <= 3 and abs(watch) <= 3 else f"آمن ≤ {safe:,.2f} | مراقبة ≤ {watch:,.2f}"
    else:
        # For higher-better ratios: >= safe is good, >= watch needs monitoring, < watch is risky.
        if n >= safe:
            status = 'ضمن الأمان'
        elif n >= watch:
            status = 'تحت المراقبة'
        else:
            status = 'خطر'
        benchmark = f"آمن ≥ {safe:.1%} | مراقبة ≥ {watch:.1%}" if abs(safe) <= 3 and abs(watch) <= 3 and metric_key not in ['current_ratio','quick_ratio','cash_ratio'] else f"آمن ≥ {safe:,.2f}x | مراقبة ≥ {watch:,.2f}x"

    return {
        'status': status,
        'benchmark': benchmark,
        'basis': source,
        'label': label,
    }

def _html_escape(text):
    return str(text or '').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')


def _html_attr_escape(text):
    return _html_escape(text).replace('\"', '&quot;').replace("'", '&#39;').replace('\n', '&#10;')


def _plain_tip(*parts):
    return '\n'.join([str(x).strip() for x in parts if str(x or '').strip()])

def _fmt_cell(value):
    n = _as_number(value, None)
    if n is not None and not isinstance(value, str):
        return f"{n:,.0f}" if abs(n) >= 1000 else f"{n:,.2f}".rstrip('0').rstrip('.')
    txt = str(value or '')
    return txt


def _status_tone(text):
    t = str(text or '')
    if any(k in t for k in ['خطر', 'خسارة', 'منخفض', 'غير قابل']):
        return 'danger'
    if any(k in t for k in ['متوسط', 'تقدير', 'مراجعة', 'تحتاج', 'غير متاح']):
        return 'warning'
    if any(k in t for k in ['جيد', 'مرتفعة', 'مكتمل', 'محسوب']):
        return 'ok'
    return 'neutral'


def _badge(text, tone=None):
    tone = tone or _status_tone(text)
    return f'<span class="v132-badge {tone}">{_html_escape(text)}</span>'


def _render_lux_table(df: pd.DataFrame, columns: list[str] | None = None, max_rows: int = 30, title: str | None = None):
    if not isinstance(df, pd.DataFrame) or df.empty:
        st.info('لا توجد بيانات للعرض.')
        return
    work = df.copy()
    label_map = {
        "ملاحظة CMA": "قراءة مهنية",
        "سؤال الإدارة": "السؤال المالي",
        "مصدر الحساب": "مصدر الرقم",
        "حالة المؤشر": "حالة القراءة",
    }
    work = work.rename(columns=label_map)
    if columns:
        wanted = [label_map.get(c, c) for c in columns]
        wanted = [c for c in wanted if c in work.columns]
        if wanted:
            work = work[wanted]
    work = work.head(max_rows)
    rows = []
    for _, r in work.iterrows():
        tds = []
        for col in work.columns:
            val = r.get(col, '')
            txt = _fmt_cell(val)
            cls = ''
            if str(col) in ['الحكم', 'درجة الثقة', 'حالة المؤشر', 'حالة القراءة', 'مستوى الخطورة', 'مقارنة بالمعيار']:
                txt = _badge(txt)
                cls = ' class="tag-cell"'
            tds.append(f'<td{cls}>{txt}</td>')
        rows.append('<tr>' + ''.join(tds) + '</tr>')
    th = ''.join([f'<th>{_html_escape(c)}</th>' for c in work.columns])
    title_html = f'<div class="v132-table-title">{_html_escape(title)}</div>' if title else ''
    html = '<div class="v132-table-card">' + title_html + '<div class="v132-table-scroll"><table class="v132-table"><thead><tr>' + th + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div></div>'
    st.markdown(html, unsafe_allow_html=True)


def _summary_tile(icon: str, title: str, value: str, note: str, tone: str = 'neutral'):
    st.markdown(f"""
    <div class="v132-summary-tile {tone}">
      <div class="v132-summary-icon">{_html_escape(icon)}</div>
      <div class="v132-summary-content">
        <span>{_html_escape(title)}</span>
        <strong>{_html_escape(value)}</strong>
        <em>{_html_escape(note)}</em>
      </div>
    </div>
    """, unsafe_allow_html=True)


def _cogs_formula_info(full_model: dict) -> dict:
    mgmt = full_model.get('management_pnl', {}) or {}
    opening = _as_number(mgmt.get('opening_inventory'), 0)
    purchases = _as_number(mgmt.get('net_purchases'), 0)
    ending = _as_number(mgmt.get('ending_inventory'), 0)
    basis = str(mgmt.get('cogs_basis') or '')
    cogs = _as_number(mgmt.get('cogs'), None)
    if basis == 'periodic_inventory_formula':
        return {'status':'مكتملة', 'tone':'ok', 'formula':f'{_money0(opening)} + {_money0(purchases)} - {_money0(ending)} = {_money0(cogs)}', 'note':'تكلفة البضاعة المباعة مستخرجة من ميزان المراجعة وفق الجرد الدوري.'}
    if opening or ending or purchases:
        return {'status':'تحتاج تحقق', 'tone':'warning', 'formula':f'{_money0(opening)} + {_money0(purchases)} - {_money0(ending)}', 'note':'يمكن استخراج تكلفة البضاعة من ميزان المراجعة إذا توفرت عناصر الجرد الدوري: مخزون أول المدة + صافي المشتريات - مخزون آخر المدة. إذا لم تُقرأ هذه العناصر بوضوح، اطلب من المستخدم مخزون أول/آخر الفترة أو تقرير المخزون.'}
    return {'status':'تحتاج تحديد', 'tone':'warning', 'formula':'مخزون أول المدة + صافي المشتريات - مخزون آخر المدة', 'note':'إذا كان النشاط يبيع بضاعة أو لديه مخزون، لا تعتمد المشتريات وحدها كتلكفة مبيعات. اطلب مخزون أول وآخر الفترة أو حساب تكلفة مبيعات مقفل من الميزان.'}



def _render_cogs_quality_note(full_model: dict, compact: bool = True):
    """Professional COGS note. The formula is not exposed as a primitive visual block.
    It is kept as audit methodology inside an expander only.
    """
    info = _cogs_formula_info(full_model)
    title = 'تكلفة الإيراد / تكلفة البضاعة'
    if compact:
        st.markdown(f"""
        <div class="v136-method-card {info['tone']}">
            <div class="v136-method-title">{_html_escape(title)}</div>
            <div class="v136-method-status">{_html_escape(info['status'])}</div>
            <p>{_html_escape(info['note'])}</p>
        </div>
        """, unsafe_allow_html=True)
    with st.expander("منهجية التحقق من تكلفة الإيراد"):
        st.write("يعتمد الإيجنت على هذه القاعدة داخليًا عند وجود مخزون، لكنه لا يجعلها حكمًا نهائيًا إلا إذا كانت عناصر المخزون والمشتريات مقروءة بوضوح.")
        st.table(pd.DataFrame([
            {"العنصر": "مخزون أول المدة", "القيمة المقروءة": _money0((full_model.get('management_pnl', {}) or {}).get('opening_inventory', 0))},
            {"العنصر": "صافي المشتريات / التكلفة المباشرة", "القيمة المقروءة": _money0((full_model.get('management_pnl', {}) or {}).get('net_purchases', 0))},
            {"العنصر": "مخزون آخر المدة", "القيمة المقروءة": _money0((full_model.get('management_pnl', {}) or {}).get('ending_inventory', 0))},
            {"العنصر": "تكلفة الإيراد المعتمدة", "القيمة المقروءة": _money0((full_model.get('management_pnl', {}) or {}).get('cogs', 0))},
        ]))


def _leaf_tb_rows(tb_model: dict | None) -> pd.DataFrame:
    work = (tb_model or {}).get('tb', pd.DataFrame())
    if not isinstance(work, pd.DataFrame) or work.empty:
        return pd.DataFrame()
    out = work.copy()
    if 'account_code_norm' in out.columns:
        codes = out['account_code_norm'].astype(str).tolist()
        def is_parent(c):
            c = str(c or '')
            return bool(c) and any(o != c and str(o).startswith(c) and len(str(o)) > len(c) for o in codes)
        out = out[~out['account_code_norm'].astype(str).apply(is_parent)].copy()
    return out


def _tb_income_amounts(tb_model: dict | None) -> dict:
    pnl = ((tb_model or {}).get('income_statement', {}) or {}).get('pnl', pd.DataFrame())
    if not isinstance(pnl, pd.DataFrame) or pnl.empty:
        return {}
    out = {}
    for _, r in pnl.iterrows():
        key = str(r.get('English') or r.get('العربي') or '')
        out[key] = _as_number(r.get('Amount'), 0.0) or 0.0
    return out


def _pct_change(current, previous):
    c = _as_number(current, 0.0) or 0.0
    p = _as_number(previous, 0.0) or 0.0
    if abs(p) < 1e-9:
        return None
    return (c - p) / abs(p)


def _fmt_change_pct(x):
    n = _as_number(x, None)
    return '—' if n is None else f"{n*100:.1f}%"


def _trend_from_numbers(current, previous, inverse: bool = False) -> str:
    c = _as_number(current, 0.0) or 0.0
    p = _as_number(previous, 0.0) or 0.0
    if abs(c - p) < 1e-9:
        return 'ثابت'
    up = c > p
    if inverse:
        return 'ارتفاع يحتاج متابعة' if up else 'انخفاض إيجابي'
    return 'ارتفاع' if up else 'انخفاض'


def _change_badge(pct, current=None, previous=None, inverse: bool = False):
    n = _as_number(pct, None)
    if n is None:
        return '<span class="v138-trend neutral">▬ —</span>'
    if abs(n) < 0.0005:
        return '<span class="v138-trend neutral">▬ ثابت</span>'
    up = n > 0
    good = (not inverse and up) or (inverse and not up)
    tone = 'ok' if good else 'danger'
    arrow = '▲' if up else '▼'
    return f'<span class="v138-trend {tone}">{arrow} {n*100:.1f}%</span>'


def _build_prior_tb_comparison(current_tb_model: dict | None, previous_tb_model: dict | None, current_label: str = 'الفترة الحالية', previous_label: str = 'الفترة السابقة') -> dict:
    if not current_tb_model or not previous_tb_model:
        return {"available": False, "reason": "لا يوجد ميزان مراجعة لفترة مقارنة."}
    cur_income = _tb_income_amounts(current_tb_model)
    prev_income = _tb_income_amounts(previous_tb_model)
    keys = [
        ('Net Sales', 'صافي المبيعات', False),
        ('Total Revenue', 'إجمالي الإيرادات', False),
        ('COGS', 'تكلفة الإيراد / المبيعات', True),
        ('Gross Profit', 'مجمل الربح', False),
        ('Operating Expenses', 'المصاريف التشغيلية', True),
        ('EBITDA', 'EBITDA', False),
        ('Finance Costs', 'تكاليف التمويل', True),
        ('Tax / Zakat', 'الزكاة والضريبة', True),
        ('Net Profit', 'صافي الربح', False),
    ]
    income_rows = []
    for key, label, inverse in keys:
        cur = cur_income.get(key, 0.0)
        prev = prev_income.get(key, 0.0)
        ch = cur - prev
        pct = _pct_change(cur, prev)
        income_rows.append({
            'البند': label,
            previous_label: prev,
            current_label: cur,
            'التغير': ch,
            'نسبة التغير': _change_badge(pct, cur, prev, inverse=inverse),
        })
    income_df = pd.DataFrame(income_rows)

    cur_rows = _leaf_tb_rows(current_tb_model)
    prev_rows = _leaf_tb_rows(previous_tb_model)
    balance_df = pd.DataFrame()
    if not cur_rows.empty and not prev_rows.empty:
        for df in [cur_rows, prev_rows]:
            if 'account_key_cmp' not in df.columns:
                pass
        def prep(df):
            d = df.copy()
            key_col = 'account_code_norm' if 'account_code_norm' in d.columns and d['account_code_norm'].astype(str).str.len().gt(0).any() else 'account_name'
            d['cmp_key'] = d[key_col].astype(str)
            d['الحساب'] = d.get('account_name', pd.Series(dtype=str)).astype(str)
            d['closing_signed'] = pd.to_numeric(d.get('current_debit', 0), errors='coerce').fillna(0) - pd.to_numeric(d.get('current_credit', 0), errors='coerce').fillna(0)
            if 'category' in d.columns:
                d['التصنيف'] = d['category'].astype(str)
            else:
                d['التصنيف'] = '—'
            return d[['cmp_key','الحساب','التصنيف','closing_signed']]
        c = prep(cur_rows).rename(columns={'closing_signed': current_label})
        p = prep(prev_rows).rename(columns={'closing_signed': previous_label})
        merged = pd.merge(c, p[['cmp_key', previous_label]], on='cmp_key', how='outer')
        merged['الحساب'] = merged['الحساب'].fillna(merged['cmp_key'])
        merged[current_label] = pd.to_numeric(merged[current_label], errors='coerce').fillna(0)
        merged[previous_label] = pd.to_numeric(merged[previous_label], errors='coerce').fillna(0)
        merged['التغير'] = merged[current_label] - merged[previous_label]
        merged['نسبة التغير'] = merged.apply(lambda r: _change_badge(_pct_change(r[current_label], r[previous_label]), r[current_label], r[previous_label]), axis=1)
        balance_df = merged.reindex(merged['التغير'].abs().sort_values(ascending=False).index).head(25)[['الحساب','التصنيف', previous_label, current_label, 'التغير','نسبة التغير']]

    summary = {
        'revenue_change_pct': _pct_change(cur_income.get('Total Revenue', 0), prev_income.get('Total Revenue', 0)),
        'gross_profit_change_pct': _pct_change(cur_income.get('Gross Profit', 0), prev_income.get('Gross Profit', 0)),
        'net_profit_change_pct': _pct_change(cur_income.get('Net Profit', 0), prev_income.get('Net Profit', 0)),
        'expense_change_pct': _pct_change(cur_income.get('Operating Expenses', 0), prev_income.get('Operating Expenses', 0)),
        'current_label': current_label,
        'previous_label': previous_label,
    }
    return {"available": True, "income": income_df, "balance": balance_df, "summary": summary, "reason": "تمت المقارنة بين ميزاني مراجعة لفترتين/سنتين."}


def _decision_card(icon: str, title: str, verdict: str, evidence: str, action: str, tone: str = 'warning', benchmark: str = '', basis: str = '', implication: str = ''):
    """Decision card with visible rationale and native hover title.
    The card does not hide critical reasoning behind hover; hover adds a compact audit note only.
    """
    tip = _plain_tip(
        f"الحكم: {verdict}",
        f"الدليل: {evidence}",
        f"المعيار: {benchmark or 'لا يوجد معيار رقمي مدمج'}",
        f"مصدر المعيار: {basis or 'منطق مالي داخلي'}",
        f"الأثر: {implication}",
        f"الإجراء: {action}",
    )
    st.markdown(f"""
    <div class="v140-decision-card {tone}" title="{_html_attr_escape(tip)}">
        <div class="v140-card-head">
            <div class="v140-decision-icon">{_html_escape(icon)}</div>
            <div>
                <div class="v140-decision-title">{_html_escape(title)}</div>
                <div class="v140-decision-verdict">{_html_escape(verdict)}</div>
            </div>
        </div>
        <div class="v140-decision-line"><strong>الدليل</strong><span>{_html_escape(evidence)}</span></div>
        <div class="v140-decision-line"><strong>المعيار</strong><span>{_html_escape(benchmark or 'لا يوجد معيار رقمي مدمج')}</span></div>
        <div class="v140-decision-line"><strong>الأثر</strong><span>{_html_escape(implication or 'يحتاج ربطاً بالنتيجة التشغيلية والبيانات المتاحة.')}</span></div>
        <div class="v140-decision-action"><strong>الإجراء</strong><span>{_html_escape(action)}</span></div>
    </div>
    """, unsafe_allow_html=True)


def _available_ratio_text(label: str, value, suffix: str = '') -> str:
    n = _as_number(value, None)
    if n is None:
        return f"{label}: غير متاح"
    if suffix == '%':
        return f"{label}: {n*100:.1f}%"
    if suffix == 'x':
        return f"{label}: {n:.2f}x"
    return f"{label}: {n:,.0f}"


def _build_decisions(full_model: dict, guarded_df: pd.DataFrame | None = None) -> list[dict]:
    gm = _metric_value(full_model, 'gross_margin')
    cogs = _metric_value(full_model, 'cogs_ratio')
    op = _metric_value(full_model, 'operating_margin')
    nm = _metric_value(full_model, 'net_margin')
    qr = _metric_value(full_model, 'quick_ratio')
    cr_cash = _metric_value(full_model, 'cash_ratio')
    current = _metric_value(full_model, 'current_ratio')
    dr = _metric_value(full_model, 'debt_ratio')
    mg = full_model.get('management_pnl', {}) or {}
    profile = refresh_business_profile()

    opex_ratio = _as_number(mg.get('opex_ratio'), None)
    if opex_ratio is None:
        rev = _as_number(mg.get('revenue'), 0.0) or 0.0
        opex = _as_number(mg.get('opex'), None)
        opex_ratio = (opex / rev) if rev and opex is not None else None
    admin_ratio = None
    sm_ratio = None
    rev = _as_number(mg.get('revenue'), 0.0) or 0.0
    if rev:
        admin_ratio = (_as_number(mg.get('admin_opex'), None) or 0.0) / rev if mg.get('admin_opex') is not None else None
        sm_ratio = (_as_number(mg.get('selling_marketing'), None) or 0.0) / rev if mg.get('selling_marketing') is not None else None

    decisions = []

    gm_basis = _basis_for_decision('gross_margin', gm, profile)
    op_basis = _basis_for_decision('operating_margin', op, profile)
    # Profit model card must not contradict operating loss.
    if op is not None and op < 0:
        verdict = 'هامش أولي موجود لكن التشغيل لا يحتفظ بالربح'
        tone = 'danger'
        implication = 'المشكلة بعد مجمل الربح: المصاريف أو التصنيف أو تكلفة تقديم الخدمة تلتهم الهامش.'
    elif gm is None:
        verdict = 'غير محسوم قبل تثبيت تكلفة الإيراد'
        tone = 'warning'
        implication = 'لا يصح الحكم على نموذج الربح دون قراءة مجمل الربح وتكلفة الإيراد.'
    else:
        verdict = gm_basis['status']
        tone = _decision_tone_from_status(verdict)
        implication = 'الحكم يظل أولياً إلى أن تُراجع المصاريف التشغيلية وصافي النتيجة.'
    decisions.append({
        'icon': '🧮',
        'title': 'ربحية النموذج',
        'verdict': verdict,
        'evidence': ' | '.join([_available_ratio_text('مجمل الربح', gm, '%'), _available_ratio_text('هامش التشغيل', op, '%'), _available_ratio_text('صافي الهامش', nm, '%')]),
        'benchmark': f"مجمل الربح: {gm_basis['benchmark']} | التشغيل: {op_basis['benchmark']}",
        'basis': f"{gm_basis['basis']} / {op_basis['basis']}",
        'action': 'ثبّت تكلفة الإيراد ثم اربط الهامش بالمشروع أو الخدمة أو العميل عند توفر التفصيل.',
        'implication': implication,
        'tone': tone,
    })

    # Operating cost card.
    opex_basis = _basis_for_decision('opex_ratio', opex_ratio, profile)
    if op is not None and op < 0:
        verdict = 'ضغط تشغيلي مرتفع'
        tone = 'danger'
    else:
        verdict = opex_basis['status']
        tone = _decision_tone_from_status(verdict)
    exp_parts = [_available_ratio_text('المصاريف التشغيلية', opex_ratio, '%')]
    if admin_ratio is not None:
        exp_parts.append(_available_ratio_text('إدارية', admin_ratio, '%'))
    if sm_ratio is not None:
        exp_parts.append(_available_ratio_text('بيع وتسويق', sm_ratio, '%'))
    decisions.append({
        'icon': '⚙️',
        'title': 'هيكل المصاريف',
        'verdict': verdict,
        'evidence': ' | '.join(exp_parts),
        'benchmark': opex_basis['benchmark'],
        'basis': opex_basis['basis'],
        'action': 'استخرج أكبر بنود المصروفات، ثم افصل البنود المنتجة عن البنود العامة أو غير المرتبطة بالإيراد.',
        'implication': 'إذا بقيت المصاريف أعلى من قدرة الهامش، فإن نمو الإيراد وحده لن يحسن النتيجة.',
        'tone': tone,
    })

    # Liquidity card.
    liq_values = [v for v in [current, qr, cr_cash] if _as_number(v, None) is not None]
    if not liq_values:
        decisions.append({
            'icon': '💧',
            'title': 'السيولة القابلة للحكم',
            'verdict': 'غير متاحة من المصادر الحالية',
            'evidence': 'لم تُقرأ نسب سيولة صالحة من الحسابات المصنفة.',
            'benchmark': 'يُقارن Current / Quick / Cash Ratio عند توفرها',
            'basis': 'نسب سيولة عامة + تصنيف المركز المالي',
            'action': 'راجع تصنيف النقد والبنوك والالتزامات المتداولة أو أضف كشف بنك/تقرير سيولة.',
            'implication': 'لا تعرض النسبة كصفر عند غياب المدخلات؛ الصفر حكم مالي مختلف عن عدم التوفر.',
            'tone': 'warning',
        })
    else:
        weakest_code, weakest_value = ('current_ratio', current)
        for code, val in [('quick_ratio', qr), ('cash_ratio', cr_cash), ('current_ratio', current)]:
            if _as_number(val, None) is not None and (weakest_value is None or _as_number(val, 0) < _as_number(weakest_value, 0)):
                weakest_code, weakest_value = code, val
        liq_basis = _basis_for_decision(weakest_code, weakest_value, profile)
        decisions.append({
            'icon': '💧',
            'title': 'السيولة المحاسبية',
            'verdict': liq_basis['status'],
            'evidence': ' | '.join([_available_ratio_text('Current', current, 'x'), _available_ratio_text('Quick', qr, 'x'), _available_ratio_text('Cash', cr_cash, 'x')]),
            'benchmark': liq_basis['benchmark'],
            'basis': liq_basis['basis'],
            'action': 'اربط قراءة الميزان بكشف البنك وأعمار العملاء عند تقييم توقيت السداد والتحصيل.',
            'implication': 'نسب الميزان تقيس القدرة المحاسبية، ولا تكشف وحدها توقيت النقد اليومي.',
            'tone': _decision_tone_from_status(liq_basis['status']),
        })

    # Funding / obligations safety.
    if dr is not None:
        debt_basis = _basis_for_decision('debt_ratio', dr, profile)
        decisions.append({
            'icon': '🧱',
            'title': 'ضغط الالتزامات',
            'verdict': debt_basis['status'],
            'evidence': _available_ratio_text('الالتزامات إلى الأصول', dr, '%'),
            'benchmark': debt_basis['benchmark'],
            'basis': debt_basis['basis'],
            'action': 'قارن الالتزامات قصيرة الأجل بخطة التحصيل والسداد قبل إضافة أي التزام مالي جديد.',
            'implication': 'ارتفاع الالتزامات مع خسارة تشغيلية يضغط رأس المال العامل حتى لو كان الإيراد موجوداً.',
            'tone': _decision_tone_from_status(debt_basis['status']),
        })

    # Data quality as separate control card only if it changes confidence.
    gaps = []
    if isinstance(guarded_df, pd.DataFrame) and not guarded_df.empty and 'حالة المؤشر' in guarded_df.columns:
        gaps = guarded_df[guarded_df['حالة المؤشر'].astype(str).eq('غير قابل للحساب')]['المؤشر'].astype(str).head(3).tolist()
    if gaps:
        decisions.append({
            'icon': '🧭',
            'title': 'موثوقية القرار',
            'verdict': 'تحتاج مصادر داعمة',
            'evidence': '، '.join(gaps),
            'benchmark': 'ليست نسبة مالية؛ هي جودة بيانات',
            'basis': 'حارس المؤشرات ومصادر البيانات',
            'action': 'أضف المصدر الذي يفتح المؤشر المطلوب بدلاً من تحويل المؤشر غير المتاح إلى صفر.',
            'implication': 'كلما زادت المؤشرات غير القابلة للحساب، انخفضت صلاحية القرار التنفيذي النهائي.',
            'tone': 'warning',
        })
    return decisions[:5]

def _ratio_meaning(code: str, metric_name: str = "") -> str:
    meanings = {
        "gross_margin": "هل يترك المنتج أو الخدمة هامشًا قبل مصاريف الإدارة والبيع؟",
        "cogs_ratio": "كم تستهلك تكلفة البضاعة أو الخدمة من كل ريال مبيعات؟",
        "operating_margin": "هل يبقى ربح بعد تكلفة الإيراد والمصاريف التشغيلية؟",
        "net_margin": "ما النتيجة النهائية بعد تحميل كل التكاليف؟",
        "quick_ratio": "هل تستطيع الشركة السداد دون الاعتماد على المخزون؟",
        "cash_ratio": "هل النقد الفوري يكفي لمواجهة الالتزامات القريبة؟",
        "current_ratio": "هل الأصول المتداولة تغطي الالتزامات القصيرة؟",
        "debt_ratio": "كم من الأصول ممول بالالتزامات؟",
        "debt_to_equity": "ما مستوى الرافعة المالية مقارنة بحقوق الملكية؟",
        "working_capital": "هل لدى الشركة مساحة تشغيل قصيرة الأجل؟",
        "runway": "كم شهر يغطي النقد المتاح المصاريف النقدية؟",
        "dso": "كم يوم تحتاج المبيعات لتتحول إلى نقد؟",
        "ccc": "كم يوم يبقى النقد محبوسًا داخل دورة التشغيل؟",
        "asset_turnover": "ما كفاءة الأصول في توليد الإيراد؟",
    }
    return meanings.get(code, f"ما الذي يكشفه مؤشر {metric_name} لصاحب العمل؟")


def _ratio_action(code: str, result: str = "") -> str:
    actions = {
        "gross_margin": "ثبّت تكلفة البضاعة أو الخدمة أولًا، ثم راجع التسعير والهامش حسب المنتج أو الفرع.",
        "cogs_ratio": "تحقق من مخزون أول وآخر الفترة أو حساب تكلفة المبيعات قبل اعتماد الهامش.",
        "operating_margin": "راجع المصاريف التشغيلية حسب علاقتها بالإيراد، ولا تبدأ بخفض عشوائي.",
        "net_margin": "افصل البنود غير المتكررة ثم حدد هل الخسارة تشغيلية أم مؤقتة.",
        "quick_ratio": "لا تعتمد على المخزون في السداد؛ جهز خطة تحصيل أو تمويل قصير الأجل.",
        "cash_ratio": "راجع جدول السداد القريب واحتياج النقد خلال 30 يومًا.",
        "current_ratio": "افحص مكونات الأصول المتداولة؛ قد تكون النسبة جيدة لكن النقد ضعيف.",
        "debt_ratio": "لا تدخل التزامات جديدة قبل تحسين الهامش والسيولة.",
        "debt_to_equity": "راجع هيكل التمويل وحدود الالتزامات مقارنة برأس المال.",
        "runway": "ارفع تقرير سيولة أو كشف بنك مصنف حتى لا يبقى القرار ناقصًا.",
        "dso": "ارفع أعمار العملاء أو تقرير العملاء لتحديد التحصيل الحقيقي.",
        "ccc": "لا يحسب قبل اكتمال DSO/DIO/DPO؛ لا تعرضه كصفر.",
    }
    return actions.get(code, "اربط المؤشر بسبب مالي واضح ثم حدد إجراء متابعة قابل للقياس.")


def _pretty_ratio_table(guarded_df: pd.DataFrame, group: str | None = None, max_rows: int = 12, full_model: dict | None = None, profile: dict | None = None):
    if guarded_df is None or guarded_df.empty:
        st.info("لا توجد نسب قابلة للعرض.")
        return
    df = guarded_df.copy()
    if group and "المجموعة" in df.columns:
        df = df[df["المجموعة"].astype(str).eq(group)]
    if df.empty:
        st.info("لا توجد مؤشرات ضمن هذا المجال.")
        return
    profile = profile or refresh_business_profile()
    full_model = full_model or (st.session_state.models.get("comprehensive_model", {}) if st.session_state.get("models") else {})
    rows = []
    for _, r in df.head(max_rows).iterrows():
        code = str(r.get("الكود", ""))
        metric = str(r.get("المؤشر", ""))
        val = _metric_current_value(full_model, r.to_dict(), code)
        b = _benchmark_for_metric(code, profile)
        status, note = _benchmark_status_for_value(code, val, profile)
        rows.append({
            "المؤشر": metric,
            "النتيجة": r.get("النتيجة", "—"),
            "المعيار بجانب النسبة": _benchmark_range_text(b),
            "مقارنة بالمعيار": status,
            "الحكم": r.get("الحكم", "—"),
            "المعنى لصاحب العمل": _ratio_meaning(code, metric),
            "الإجراء المقترح": _ratio_action(code, str(r.get("النتيجة", ""))),
            "مصدر الرقم": r.get("مصدر الحساب", r.get("المصدر الأساسي", "—")),
            "ثقة القراءة": r.get("درجة الثقة", "—"),
            "ملاحظة المعيار": note,
        })
    _render_lux_table(pd.DataFrame(rows), max_rows=max_rows)


def render_ratio_decision_dashboard(ratio_df: pd.DataFrame, health: dict | None = None, findings_df: pd.DataFrame | None = None):
    profile = refresh_business_profile()
    full_model = st.session_state.models.get("comprehensive_model", {}) if st.session_state.get("models") else {}
    guarded_df = build_metric_guard_report(ratio_df, full_model.get("metric_pack", {}), profile, st.session_state.files, full_model)
    layers = _confidence_layers(full_model, guarded_df)
    health = health or full_model.get('financial_health_score', {}) or {}
    decisions = _build_decisions(full_model, guarded_df)
    danger_cards = [d for d in decisions if d.get('tone') == 'danger']
    primary = danger_cards[0] if danger_cards else (decisions[0] if decisions else {'title':'—','verdict':'—','tone':'warning'})

    st.markdown("""
    <div class="v140-page-note">
      هذه الصفحة لا تعطي قائمة مؤشرات منفصلة؛ بل تربط الربحية والمصاريف والسيولة في حكم واحد قابل للتنفيذ.
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        _summary_tile('🩺', 'الصحة المالية', f"{health.get('score','—')}/100", health.get('label', ''), 'danger' if 'خطر' in str(health.get('label','')) else 'warning')
    with c2:
        _summary_tile('🎯', 'الأولوية التنفيذية', primary.get('title','—'), primary.get('verdict',''), primary.get('tone','warning'))
    with c3:
        _summary_tile('🧠', 'ثقة القراءة', layers['diagnosis'], layers['diagnosis_note'], 'ok' if layers['diagnosis']=='مرتفعة' else 'warning')

    st.markdown("#### بطاقات الحكم المالي")
    cols = st.columns(2)
    for i, d in enumerate(decisions):
        with cols[i % 2]:
            _decision_card(d['icon'], d['title'], d['verdict'], d['evidence'], d['action'], d['tone'], d.get('benchmark',''), d.get('basis',''), d.get('implication',''))

    gaps = guarded_df[guarded_df["حالة المؤشر"].astype(str).eq("غير قابل للحساب")] if isinstance(guarded_df, pd.DataFrame) and not guarded_df.empty and "حالة المؤشر" in guarded_df.columns else pd.DataFrame()
    if not gaps.empty:
        with st.expander("مصادر إضافية مؤثرة على ثقة الحكم"):
            gap_rows = []
            for _, r in gaps.head(10).iterrows():
                gap_rows.append({
                    "المؤشر": r.get("المؤشر", "—"),
                    "سبب عدم الاعتماد": r.get("ملاحظة CMA", "مدخلات غير مكتملة"),
                    "البيان المطلوب": r.get("المطلوب للحساب", "—"),
                    "المصدر المقترح": r.get("المصدر الأساسي", "—"),
                })
            _render_lux_table(pd.DataFrame(gap_rows), max_rows=10)

def _analysis_card(title: str, value: str, note: str, tone: str = 'neutral'):
    st.markdown(f"""
    <div class="v136-analysis-card {tone}">
        <span>{_html_escape(title)}</span>
        <strong>{_html_escape(value)}</strong>
        <em>{_html_escape(note)}</em>
    </div>
    """, unsafe_allow_html=True)


def _pct_label(value):
    n = _as_number(value, None)
    return '—' if n is None else f"{n*100:.1f}%"


def _structure_card(title: str, value: str, subtitle: str, reading: str, tone: str = 'neutral'):
    st.markdown(f"""
    <div class="v137-structure-card {tone}">
        <div class="v137-structure-top">
            <span>{_html_escape(title)}</span>
            <strong>{_html_escape(value)}</strong>
        </div>
        <em>{_html_escape(subtitle)}</em>
        <p>{_html_escape(reading)}</p>
    </div>
    """, unsafe_allow_html=True)


def _comparison_story_card(title: str, value: str, note: str, tone: str = 'neutral'):
    st.markdown(f"""
    <div class="v137-story-card {tone}">
        <span>{_html_escape(title)}</span>
        <strong>{_html_escape(value)}</strong>
        <em>{_html_escape(note)}</em>
    </div>
    """, unsafe_allow_html=True)


def _expense_ratio_from_model(full_model: dict):
    mgmt = full_model.get("management_pnl", {}) or {}
    revenue = _as_number(mgmt.get("revenue"), 0.0) or _as_number(_metric_raw_value(full_model, "revenue"), 0.0)
    rows = []
    for key, label in [
        ("cogs", "تكلفة الإيراد"),
        ("selling_marketing_expenses", "البيع والتسويق"),
        ("admin_expenses", "المصاريف الإدارية"),
        ("operating_expenses", "مصاريف التشغيل"),
        ("finance_costs", "تكاليف التمويل"),
        ("tax_zakat", "الزكاة والضريبة"),
    ]:
        val = _as_number(mgmt.get(key), None)
        if val is None:
            continue
        rows.append({
            "البند": label,
            "القيمة": val,
            "النسبة من صافي الإيراد": "—" if not revenue else f"{abs(val)/abs(revenue)*100:.1f}%",
        })
    return pd.DataFrame(rows)


def render_vertical_horizontal_executive(full_model: dict):
    vi = full_model.get("vertical_income", pd.DataFrame())
    vb = full_model.get("vertical_balance", pd.DataFrame())
    hm = full_model.get("horizontal_monthly", pd.DataFrame())
    hb = full_model.get("horizontal_balance", pd.DataFrame())
    comp = full_model.get("comparative_analysis", {}) or {}

    st.caption("يعرض التحليل الرأسي وزن بنود قائمة الدخل من صافي الإيراد، بينما تعرض المقارنة الأفقية تغير السنة الحالية مقابل السنة السابقة عند توفر ميزانين قابلين للمقارنة.")

    cogs = _metric_value(full_model, 'cogs_ratio')
    gm = _metric_value(full_model, 'gross_margin')
    op = _metric_value(full_model, 'operating_margin')
    nm = _metric_value(full_model, 'net_margin')
    opex = _metric_value(full_model, 'opex_ratio')

    st.markdown("#### هيكل قائمة الدخل")
    st.caption("القاعدة المحاسبية هنا: صافي الإيراد هو أساس القياس، وكل بند في قائمة الدخل يُعرض كنسبة منه لفهم الهامش وهيكل التكلفة.")
    cols = st.columns(5)
    with cols[0]:
        _structure_card("صافي الإيراد", "100%", "أساس القياس", "نقطة المقارنة التي تُنسب إليها التكلفة والهوامش والمصاريف.", "base")
    with cols[1]:
        _structure_card("تكلفة الإيراد", _pct_label(cogs), "تكلفة مباشرة", "توضح مقدار ما يستهلكه تقديم الخدمة أو البضاعة قبل الوصول لمجمل الربح.", "warning" if cogs is not None and cogs > 0.70 else "neutral")
    with cols[2]:
        _structure_card("مجمل الربح", _pct_label(gm), "بعد التكلفة المباشرة", "يقيس قوة التسعير وكفاءة التكلفة المباشرة قبل المصاريف التشغيلية.", "ok" if gm is not None and gm >= 0.25 else "warning")
    with cols[3]:
        _structure_card("مصاريف التشغيل", _pct_label(opex), "إدارة وبيع وتشغيل", "توضح العبء التشغيلي المطلوب لإدارة النشاط وتحويل الإيراد إلى ربح.", "warning" if opex is None or opex > 0.25 else "ok")
    with cols[4]:
        _structure_card("صافي النتيجة", _pct_label(nm), "بعد كل البنود", "يبين ما تبقى من الإيراد بعد التكلفة والمصاريف والتمويل والضرائب.", "ok" if nm is not None and nm > 0 else "danger")

    expense_mix = _expense_ratio_from_model(full_model)
    if isinstance(expense_mix, pd.DataFrame) and not expense_mix.empty:
        with st.expander("تحليل مصاريف التشغيل والتكلفة كنسبة من الإيراد"):
            _render_lux_table(expense_mix, max_rows=12)

    st.markdown("#### المقارنة الأفقية")
    if comp.get('available'):
        summary = comp.get('summary', {}) or {}
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            _comparison_story_card("الإيراد", _change_badge(summary.get('revenue_change_pct')), f"{summary.get('previous_label','السابق')} → {summary.get('current_label','الحالي')}", 'ok' if (_as_number(summary.get('revenue_change_pct'), 0) or 0) >= 0 else 'danger')
        with c2:
            _comparison_story_card("مجمل الربح", _change_badge(summary.get('gross_profit_change_pct')), "أثر التسعير والتكلفة المباشرة", 'ok' if (_as_number(summary.get('gross_profit_change_pct'), 0) or 0) >= 0 else 'danger')
        with c3:
            _comparison_story_card("مصاريف التشغيل", _change_badge(summary.get('expense_change_pct'), inverse=True), "يحتاج تفسيرًا عند الارتفاع", 'warning' if (_as_number(summary.get('expense_change_pct'), 0) or 0) > 0 else 'ok')
        with c4:
            _comparison_story_card("صافي الربح", _change_badge(summary.get('net_profit_change_pct')), "النتيجة النهائية بعد كل البنود", 'ok' if (_as_number(summary.get('net_profit_change_pct'), 0) or 0) >= 0 else 'danger')
    elif comp.get('reason'):
        st.info(comp.get('reason'))
    else:
        st.info("لا توجد سنة مقارنة مقروءة بعد. ارفعي ميزان مراجعة سنة سابقة أو بيانات شهرية لإظهار الاتجاه.")

    st.markdown("#### التحليلات التفصيلية")
    st.caption("افتحي الجدول المناسب عند الحاجة للتدقيق. الأسهم تظهر داخل نسبة التغير مباشرة، ولا تُعرض كعمود منفصل.")

    detail_tabs = st.tabs(["قائمة الدخل", "تركيب المركز المالي", "المقارنة السنوية", "حركات الحسابات"])
    with detail_tabs[0]:
        if isinstance(vi, pd.DataFrame) and not vi.empty:
            st.markdown("##### قائمة الدخل — تحليل رأسي")
            st.caption("كل بند يُقاس كنسبة من صافي الإيراد داخل نفس الفترة، لذلك لا تظهر أسهم اتجاه إلا عند وجود فترة مقارنة.")
            _render_lux_table(vi, max_rows=20)
        else:
            st.info("التحليل الرأسي لقائمة الدخل غير متاح قبل بناء قائمة دخل من الميزان أو ملفات التشغيل.")

    with detail_tabs[1]:
        if isinstance(vb, pd.DataFrame) and not vb.empty:
            st.markdown("##### تركيب المركز المالي")
            st.caption("هذا ليس تحليل ربحية. يعرض وزن الأصول والالتزامات وحقوق الملكية من إجمالي الأصول لفهم هيكل التمويل والسيولة.")
            _render_lux_table(vb, max_rows=20)
        else:
            st.info("تركيب المركز المالي غير متاح.")

    with detail_tabs[2]:
        if comp.get('available') and isinstance(comp.get('income'), pd.DataFrame) and not comp.get('income').empty:
            _render_lux_table(comp.get('income'), max_rows=20, title="قائمة الدخل: مقارنة سنة بسنة")
            if isinstance(comp.get('balance'), pd.DataFrame) and not comp.get('balance').empty:
                _render_lux_table(comp.get('balance'), max_rows=25, title="أكبر تغيرات الحسابات في المركز المالي")
        elif isinstance(hm, pd.DataFrame) and not hm.empty:
            st.caption("لم يتم العثور على ميزان سنة سابقة، لذلك يعرض النظام الاتجاه الشهري من ملفات التشغيل المتاحة.")
            _render_lux_table(_add_trend_indicator(hm), max_rows=24)
        else:
            st.warning("لا توجد فترة مقارنة قابلة للقراءة. ارفعي ميزان مراجعة سنة سابقة أو ملف مبيعات/مصروفات شهري للمقارنة.")

    with detail_tabs[3]:
        if isinstance(hb, pd.DataFrame) and not hb.empty:
            st.caption("هذه حركات داخل الفترة وليست تحليلًا أفقيًا سنة بسنة. تُستخدم لتحديد الحسابات الأكثر تأثيرًا داخل الفترة.")
            _render_lux_table(_add_trend_indicator(hb), max_rows=20)
        else:
            st.info("لا توجد حركات حسابات كافية للعرض.")

def render_liquidity_decision_view(full_model: dict, liq_model: dict | None):
    ratio_df = full_model.get("ratios", pd.DataFrame())
    balance = full_model.get("balance_sheet", {})
    metrics = balance.get("metrics", {}) if balance else {}
    profile = refresh_business_profile()
    st.markdown("#### نسب السيولة من ميزان المراجعة")
    st.caption("نسب التداول والسريعة والنقدية تُحسب من المركز المالي ولا تحتاج كشف بنك. لكنها تقيس السيولة المحاسبية لا حركة النقد اليومية. كشف البنك أو تقرير السيولة يضيف Runway والتدفق النقدي الفعلي.")
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("نسبة التداول", _ratio_result(ratio_df, "current_ratio"), _ratio_status(ratio_df, "current_ratio"))
    with c2: kpi_card("النسبة السريعة", _ratio_result(ratio_df, "quick_ratio"), _ratio_status(ratio_df, "quick_ratio"))
    with c3: kpi_card("نسبة النقدية", _ratio_result(ratio_df, "cash_ratio"), _ratio_status(ratio_df, "cash_ratio"))
    with c4: kpi_card("رأس المال العامل", _ratio_result(ratio_df, "working_capital"), "من الميزان")

    explanation_rows = []
    for code, name in [("current_ratio", "نسبة التداول"), ("quick_ratio", "النسبة السريعة"), ("cash_ratio", "نسبة النقدية"), ("working_capital", "رأس المال العامل")]:
        row = _ratio_row(ratio_df, code)
        val = _metric_current_value(full_model, row, code)
        status, note = _benchmark_status_for_value(code, val, profile)
        explanation_rows.append({
            "النسبة": name,
            "النتيجة": row.get("النتيجة", "—") if row else "—",
            "المعيار بجانب النسبة": _benchmark_range_text(_benchmark_for_metric(code, profile)),
            "مقارنة بالمعيار": status,
            "ماذا تعني؟": _ratio_source_note(full_model, code),
            "قراءة لصاحب العمل": note,
        })
    _render_lux_table(pd.DataFrame(explanation_rows), max_rows=8, title="شرح نسب السيولة ومصدرها")

    cash = (liq_model or {}).get("cash", {}) if liq_model else {}
    if cash.get("available"):
        st.markdown("#### حركة النقد من تقرير السيولة")
        cards = cash.get("cards", {})
        c1, c2, c3, c4 = st.columns(4)
        with c1: kpi_card("النقد الداخل", f"{cards.get('total_cash_in',0):,.0f}", "خلال الفترة")
        with c2: kpi_card("النقد الخارج", f"{cards.get('total_cash_out',0):,.0f}", "خلال الفترة")
        with c3: kpi_card("صافي الحركة", f"{cards.get('net_cash_flow',0):,.0f}", "داخل/خارج")
        with c4:
            runway = cards.get("cash_runway_months")
            kpi_card("فترة التغطية", "—" if runway is None else f"{runway:.1f} شهر", "من الحركة النقدية")
        monthly = cash.get("monthly", pd.DataFrame())
        if isinstance(monthly, pd.DataFrame) and not monthly.empty:
            st.dataframe(monthly, use_container_width=True, hide_index=True)
    else:
        st.info("النسب الأساسية أعلاه محسوبة من ميزان المراجعة. لقراءة حركة النقد وRunway بدقة أعلى يمكن إضافة تقرير السيولة أو كشوف البنك لاحقًا، دون أن يتوقف تحليل السيولة المحاسبية.")


def render_collection_turnover_view(full_model: dict, liq_model: dict | None):
    ratio_df = full_model.get("ratios", pd.DataFrame())
    profile = refresh_business_profile()
    has_ar_file = bool((liq_model or {}).get("ar", {}).get("available")) if liq_model else False
    has_ap_file = bool((liq_model or {}).get("ap", {}).get("available")) if liq_model else False
    st.markdown("#### مؤشرات التحصيل والدوران")
    st.caption("أيام التحصيل والسداد من ميزان المراجعة وحده هي قراءة تقديرية لأنها تعتمد غالبًا على رصيد آخر الفترة ومتوسط مبيعات يومي. تصبح قراءة تنفيذية عند رفع أعمار العملاء/الموردين أو أرصدة أول وآخر الفترة.")
    c1, c2, c3, c4 = st.columns(4)
    dso_status = (_ratio_status(ratio_df, "dso") + (" | تقديري" if not has_ar_file else " | مدعوم بأعمار العملاء"))
    dpo_status = (_ratio_status(ratio_df, "dpo") + (" | تقديري" if not has_ap_file else " | مدعوم بأعمار الموردين"))
    with c1: kpi_card("أيام التحصيل DSO", _ratio_result(ratio_df, "dso"), dso_status)
    with c2: kpi_card("دوران الذمم", _ratio_result(ratio_df, "receivables_turnover"), _ratio_status(ratio_df, "receivables_turnover"))
    with c3: kpi_card("أيام السداد DPO", _ratio_result(ratio_df, "dpo"), dpo_status)
    with c4: kpi_card("دورة النقد CCC", _ratio_result(ratio_df, "ccc"), _ratio_status(ratio_df, "ccc"))

    basis_rows = []
    for code, name in [("dso", "أيام التحصيل DSO"), ("receivables_turnover", "دوران الذمم"), ("dpo", "أيام السداد DPO"), ("ccc", "دورة النقد CCC")]:
        row = _ratio_row(ratio_df, code)
        val = _metric_current_value(full_model, row, code)
        status, note = _benchmark_status_for_value(code, val, profile)
        basis_rows.append({
            "المؤشر": name,
            "النتيجة": row.get("النتيجة", "—") if row else "—",
            "المعيار بجانب النسبة": _benchmark_range_text(_benchmark_for_metric(code, profile)),
            "مقارنة بالمعيار": status,
            "مصدر/طريقة الحساب": _ratio_source_note(full_model, code),
            "درجة الاعتماد": "تنفيذي" if ((code in ["dso", "receivables_turnover"] and has_ar_file) or (code == "dpo" and has_ap_file)) else "تقديري من الميزان",
            "ملاحظة": note,
        })
    _render_lux_table(pd.DataFrame(basis_rows), max_rows=8, title="أساس أرقام التحصيل والدوران")

    ar = (liq_model or {}).get("ar", {}) if liq_model else {}
    if ar.get("available"):
        st.markdown("#### أولويات التحصيل بالأسماء")
        st.dataframe(ar.get("detail", pd.DataFrame()).rename(columns={
            "name": "العميل", "balance": "الرصيد", "age_days": "عمر الدين", "last_payment": "آخر سداد", "risk_level": "الخطر", "recommended_action": "الإجراء"
        }), use_container_width=True, hide_index=True)
    else:
        st.info("لا يوجد ملف أعمار عملاء. لذلك نعرض نسب التحصيل من الميزان عند توفر الذمم، لكن خطة التحصيل بالأسماء تحتاج أعمار العملاء.")


def render_cost_structure_view(expense_model: dict | None, full_model: dict):
    mgmt = full_model.get("management_pnl", {}) or {}
    ratio_df = full_model.get("ratios", pd.DataFrame())
    profile = refresh_business_profile()
    revenue = _as_number(mgmt.get("revenue"), 0.0) or _as_number(_metric_raw_value(full_model, "revenue"), 0.0)
    st.markdown("#### هيكل التكلفة من ميزان المراجعة والتصنيف")
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("تكلفة الإيراد", _ratio_result(ratio_df, "cogs_ratio"), "من الإيراد")
    with c2: kpi_card("المصاريف الإدارية", _ratio_result(ratio_df, "admin_ratio"), "من الإيراد")
    with c3: kpi_card("البيع والتسويق", _ratio_result(ratio_df, "sm_ratio"), "من الإيراد")
    with c4: kpi_card("هامش التشغيل", _ratio_result(ratio_df, "operating_margin"), _ratio_status(ratio_df, "operating_margin"))

    cost_ratio_rows = []
    for code, label in [("cogs_ratio", "تكلفة الإيراد"), ("admin_ratio", "المصاريف الإدارية"), ("sm_ratio", "البيع والتسويق"), ("opex_ratio", "إجمالي المصاريف التشغيلية")]:
        row = _ratio_row(ratio_df, code)
        val = _metric_current_value(full_model, row, code)
        status, note = _benchmark_status_for_value(code, val, profile)
        cost_ratio_rows.append({
            "البند": label,
            "النسبة من الإيراد": row.get("النتيجة", "—") if row else "—",
            "المعيار بجانب النسبة": _benchmark_range_text(_benchmark_for_metric(code, profile)),
            "مقارنة بالقطاع": status,
            "ملاحظة": note,
        })
    _render_lux_table(pd.DataFrame(cost_ratio_rows), max_rows=8, title="المصاريف كنسبة من الإيراد مع المعيار بجانبها")

    if mgmt and isinstance(mgmt.get("management_table"), pd.DataFrame) and not mgmt.get("management_table").empty:
        with st.expander("قائمة الدخل الإدارية وهيكل التكلفة", expanded=True):
            mt = mgmt.get("management_table").copy()
            if "القيمة" in mt.columns and revenue:
                mt["نسبة من الإيراد"] = pd.to_numeric(mt["القيمة"], errors="coerce").fillna(0).apply(lambda x: f"{(x/revenue)*100:.1f}%")
            _render_lux_table(mt, max_rows=20)
    segment = full_model.get("segment_analysis", {}) or {}
    if isinstance(segment.get("segment_table"), pd.DataFrame) and not segment.get("segment_table").empty:
        st.markdown("#### مسارات النشاط المكتشفة من الحسابات")
        st.caption("هذه القراءة عامة لكل القطاعات: تفصل المسارات أو المشاريع أو القنوات عندما تظهر في الحسابات، ولا تعتمد على ملف واحد أو اسم ثابت.")
        _render_lux_table(segment.get("segment_table"), max_rows=15)
    warnings = (segment.get("warnings") or []) + ((full_model.get("balance_quality_flags", {}) or {}).get("flags", []) or [])
    if warnings:
        for w in warnings:
            st.warning(w)

    if expense_model:
        notes = expense_model.get("notes") or []
        if notes:
            st.caption(" ".join(notes))
        cat_df = expense_model.get("by_category", pd.DataFrame()).copy()
        top_df = expense_model.get("top_expenses", pd.DataFrame()).copy()
        if isinstance(cat_df, pd.DataFrame) and not cat_df.empty:
            cat_df["نسبة من الإيراد"] = pd.to_numeric(cat_df.get("amount", 0), errors="coerce").fillna(0).apply(lambda x: "—" if not revenue else f"{(x/revenue)*100:.1f}%")
            cat_df["مقارنة بالقطاع"] = cat_df.apply(lambda r: _cost_line_status(r.get("category", ""), (pd.to_numeric(pd.Series([r.get("amount",0)]), errors="coerce").fillna(0).iloc[0] / revenue) if revenue else None, profile), axis=1)
            cat_df = cat_df.rename(columns={"category": "التصنيف", "amount": "القيمة"})
            st.markdown("#### توزيع المصاريف حسب التصنيف")
            _render_lux_table(cat_df, max_rows=20)
        if isinstance(top_df, pd.DataFrame) and not top_df.empty:
            top_df["نسبة من الإيراد"] = pd.to_numeric(top_df.get("amount", 0), errors="coerce").fillna(0).apply(lambda x: "—" if not revenue else f"{(x/revenue)*100:.1f}%")
            top_df["مقارنة بالقطاع"] = top_df.apply(lambda r: _cost_line_status(r.get("category", ""), (pd.to_numeric(pd.Series([r.get("amount",0)]), errors="coerce").fillna(0).iloc[0] / revenue) if revenue else None, profile), axis=1)
            top_df = top_df.rename(columns={"account_name": "الحساب", "category": "التصنيف", "amount": "القيمة"})
            st.markdown("#### أكبر بنود المصاريف التي يجب مراجعتها")
            st.caption("كل بند يظهر بقيمته ونسبته من الإيراد. عند توفر سنة سابقة أو مصروفات شهرية، سيظهر مؤشر زيادة/نقصان بجانب البند بدل الاكتفاء بالقيمة الحالية.")
            _render_lux_table(top_df, max_rows=15)
    else:
        st.info("لا توجد مصاريف قابلة للقراءة من الميزان أو ملف المصروفات.")


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
    """Compact recommendations area: do not let optional uploads dominate the readiness page."""
    recs = build_missing_data_recommendations(profile)
    if recs.empty:
        return
    st.markdown("### مصادر داعمة ترفع دقة التحليل")
    st.caption("هذه المصادر لا توقف التحليل الحالي؛ تظهر هنا لتوضيح ما الذي سيصبح أدق عند إضافتها.")

    compact_rows = []
    for _, row in recs.head(6).iterrows():
        compact_rows.append({
            "المجال": str(row.get("المجال", "—")),
            "المصدر المقترح": str(row.get("المطلوب بلغة بسيطة", "—")),
            "الأثر على القراءة": str(row.get("القيمة المضافة", "—")),
        })
    _render_lux_table(pd.DataFrame(compact_rows), max_rows=6, title="ملفات اختيارية حسب أثرها على القرار")

    with st.expander("إضافة مصادر داعمة للنموذج الحالي"):
        st.caption("ارفعي ملفاً أو أكثر عند توفره؛ سيُضاف للنموذج دون الرجوع لبداية المسار.")
        files = st.file_uploader(
            "رفع ملفات داعمة",
            type=["xlsx", "xls"],
            accept_multiple_files=True,
            key=f"readiness_compact_upload_{st.session_state.uploader_key}",
        )
        if files and st.button("قراءة الملفات ودمجها في التحليل", key="readiness_compact_add_btn", use_container_width=True):
            with st.spinner("يتم قراءة الملفات وإعادة بناء النموذج..."):
                errors = ingest_uploaded_files(files, append=True)
                st.session_state.liquidity_model = build_liquidity_collections_model(st.session_state.files)
                try:
                    build_models_from_session(st.session_state.get("revenue_definition", REVENUE_DEFINITIONS[0]))
                except Exception:
                    st.session_state.pending_rebuild = True
            if errors:
                st.warning("تمت الإضافة مع ملاحظات قراءة لبعض الملفات. راجعي جدول الملفات المقروءة.")
            else:
                st.success("تمت إضافة الملفات وتحديث القراءة الحالية.")
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
        action = "ابدأ بتحليل أكبر بنود المصروفات والتكلفة، ثم افصل البنود الثابتة عن المتغيرة قبل أي التزام مالي جديد."
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



def _record_year(record: dict) -> int | None:
    """Extract a likely fiscal year from file name or sheet cells."""
    name = str(record.get("file_name") or "")
    years = [int(y) for y in re.findall(r"20\d{2}", name)]
    if years:
        return max(years)
    df = record.get("primary_df")
    try:
        sample = " ".join(df.astype(str).head(20).fillna("").values.flatten().tolist())
        years = [int(y) for y in re.findall(r"20\d{2}", sample)]
        return max(years) if years else None
    except Exception:
        return None


def _pick_latest_record(records: list[dict], role: str | None = None, detected_type: str | None = None) -> dict | None:
    """Pick the latest-period file when multiple years are uploaded.
    This prevents prior-year TB/sales files from becoming the active period by accident.
    """
    candidates = []
    for r in records or []:
        if r.get("read_error"):
            continue
        if role and r.get("selected_role") != role:
            continue
        if detected_type and r.get("detected_type") != detected_type:
            continue
        candidates.append(r)
    if not candidates:
        return None
    return sorted(candidates, key=lambda r: (_record_year(r) or 0, float(r.get("confidence") or 0), str(r.get("file_name") or "")), reverse=True)[0]


def _pick_previous_record(records: list[dict], current: dict | None, role: str | None = None, detected_type: str | None = None) -> dict | None:
    current_year = _record_year(current) if current else None
    candidates = []
    for r in records or []:
        if r is current or r.get("read_error"):
            continue
        if role and r.get("selected_role") != role:
            continue
        if detected_type and r.get("detected_type") != detected_type:
            continue
        y = _record_year(r)
        if current_year and y and y < current_year:
            candidates.append(r)
    if not candidates:
        return None
    return sorted(candidates, key=lambda r: (_record_year(r) or 0, float(r.get("confidence") or 0)), reverse=True)[0]


def _records_by_year(records: list[dict], role: str | None = None, detected_type: str | None = None) -> dict[int, list[dict]]:
    out: dict[int, list[dict]] = {}
    for r in records or []:
        if r.get("read_error"):
            continue
        if role and r.get("selected_role") != role:
            continue
        if detected_type and r.get("detected_type") != detected_type:
            continue
        y = _record_year(r)
        if y:
            out.setdefault(y, []).append(r)
    return out


def _pick_record_by_year(records: list[dict], year: int | None, role: str | None = None, detected_type: str | None = None) -> dict | None:
    if not year:
        return None
    candidates = []
    for r in records or []:
        if r.get("read_error"):
            continue
        if role and r.get("selected_role") != role:
            continue
        if detected_type and r.get("detected_type") != detected_type:
            continue
        if _record_year(r) == year:
            candidates.append(r)
    if not candidates:
        return None
    return sorted(candidates, key=lambda r: (float(r.get("confidence") or 0), str(r.get("file_name") or "")), reverse=True)[0]


def _available_years(records: list[dict], role: str | None = None, detected_type: str | None = None) -> list[int]:
    return sorted(_records_by_year(records, role=role, detected_type=detected_type).keys(), reverse=True)


def render_year_control(readable_files: list[dict]):
    """Let the user explicitly choose the analyzed year and base year for comparison."""
    tb_years = _available_years(readable_files, role="validation_source", detected_type="trial_balance")
    revenue_years = _available_years(readable_files, role="official_revenue_source")
    years = sorted(set(tb_years + revenue_years), reverse=True)
    if len(years) < 2:
        if years:
            st.session_state.analysis_year = st.session_state.analysis_year or years[0]
        return

    st.markdown("### فترة المقارنة")
    st.caption("اختاري السنة التي تريدين تحليلها، ثم سنة الأساس التي ستظهر كمقارنة. عند رفع 3 أو 4 سنوات لا يعتمد النظام على التخمين.")
    default_current = st.session_state.get("analysis_year") if st.session_state.get("analysis_year") in years else years[0]
    base_options = [y for y in years if y != default_current]
    default_base = st.session_state.get("base_year") if st.session_state.get("base_year") in base_options else (base_options[0] if base_options else None)
    c1, c2 = st.columns(2)
    with c1:
        current = st.selectbox("السنة محل التحليل", years, index=years.index(default_current), key="analysis_year_select")
    base_options = [y for y in years if y != current]
    with c2:
        if base_options:
            base_idx = base_options.index(default_base) if default_base in base_options else 0
            base = st.selectbox("سنة الأساس للمقارنة", base_options, index=base_idx, key="base_year_select")
        else:
            base = None
            st.info("لا توجد سنة أساس مختلفة متاحة للمقارنة.")
    st.session_state.analysis_year = current
    st.session_state.base_year = base
    if base:
        st.markdown(f'<div class="v141-year-chip">سيتم تحليل <strong>{current}</strong> ومقارنتها بسنة الأساس <strong>{base}</strong>.</div>', unsafe_allow_html=True)

def build_models_from_session(revenue_definition: str | None = None):
    """Build all financial models from the currently selected files.
    Used by the upload page and by the readiness page after adding files directly.
    """
    revenue_definition = revenue_definition or st.session_state.get("revenue_definition", REVENUE_DEFINITIONS[0])
    readable_files = [r for r in st.session_state.files if not r.get("read_error")]

    # File-aware selection: when multiple years are uploaded, use explicit user-selected current/base years when available.
    selected_current_year = st.session_state.get("analysis_year")
    selected_base_year = st.session_state.get("base_year")

    tb_record = _pick_record_by_year(readable_files, selected_current_year, role="validation_source", detected_type="trial_balance") or _pick_latest_record(readable_files, role="validation_source", detected_type="trial_balance")
    revenue_record = _pick_record_by_year(readable_files, selected_current_year, role="official_revenue_source") or _pick_latest_record(readable_files, role="official_revenue_source")
    expense_record = _pick_record_by_year(readable_files, selected_current_year, role="official_expense_source") or _pick_latest_record(readable_files, role="official_expense_source")

    previous_tb_record = _pick_record_by_year(readable_files, selected_base_year, role="validation_source", detected_type="trial_balance") or _pick_previous_record(readable_files, tb_record, role="validation_source", detected_type="trial_balance")
    previous_revenue_record = _pick_record_by_year(readable_files, selected_base_year, role="official_revenue_source") or _pick_previous_record(readable_files, revenue_record, role="official_revenue_source")

    revenue_model = build_revenue_model(revenue_record, revenue_definition) if revenue_record else None

    # Parse TB early. A trial balance alone is enough to build P&L, BS, expenses and liquidity ratios.
    tb_model = parse_trial_balance(tb_record) if tb_record else None
    previous_tb_model = parse_trial_balance(previous_tb_record) if previous_tb_record else None
    previous_revenue_model = build_revenue_model(previous_revenue_record, revenue_definition) if previous_revenue_record else None
    current_year = _record_year(tb_record) if tb_record else None
    previous_year = _record_year(previous_tb_record) if previous_tb_record else None

    # Expense detail files add monthly distribution. If absent, derive cost structure from the Trial Balance.
    preliminary_revenue_total = (revenue_model.get("total_revenue", 0) if revenue_model else 0) or ((tb_model or {}).get("income_statement", {}) or {}).get("total_revenue", 0)
    if expense_record:
        expense_model = build_expense_model(expense_record, preliminary_revenue_total)
    elif tb_model:
        expense_model = build_expense_model_from_trial_balance(tb_model, preliminary_revenue_total, sector_context=str(refresh_business_profile()))
    else:
        expense_model = None

    # Apply saved mapping when available. If the user has not reviewed it, the system still builds with deterministic defaults.
    if expense_model and st.session_state.expense_mapping is not None:
        expense_model = apply_expense_mapping(expense_model, st.session_state.expense_mapping)

    confirmed_months = st.session_state.selected_months
    revenue_model = filter_revenue_model(revenue_model, confirmed_months) if revenue_model and confirmed_months else revenue_model
    # Do not filter TB-derived Total expenses by monthly selections.
    if expense_model and confirmed_months and expense_model.get("source") != "trial_balance":
        expense_model = filter_expense_model(expense_model, confirmed_months)
    revenue_total = (revenue_model.get("total_revenue", 0) if revenue_model else 0) or ((tb_model or {}).get("income_statement", {}) or {}).get("total_revenue", 0)
    if expense_model and revenue_total:
        expense_model["expense_ratio"] = expense_model.get("total_expenses", 0) / revenue_total

    financial_model = build_basic_financial_model(revenue_model, expense_model)
    validation_checks = validate_project(st.session_state.file_rows, revenue_model, expense_model, tb_model)
    pnl_model = build_pnl(revenue_model, expense_model, tb_model)
    monthly_pnl_model = monthly_pnl(revenue_model, expense_model)
    ratio_model = build_ratios(pnl_model, expense_model)
    breakeven_model = build_breakeven(pnl_model, expense_model)
    forecast_model, forecast_note = build_forecast(monthly_pnl_model)
    glossary_model = build_glossary()
    liquidity_model = build_liquidity_collections_model(st.session_state.files)

    # V13.4: build one shared business/period context instead of hard-coding 150 days
    # inside ratio engines. This makes DSO/DPO/DIO and scenario outputs auditable.
    profile_context = refresh_business_profile()
    period_context = infer_period_context(confirmed_months, profile_context, tb_model)
    profile_context.update(period_context)

    comprehensive_model = build_comprehensive_financial_analysis(
        tb_model, pnl_model, expense_model, revenue_model, monthly_pnl_model, liquidity_model, profile_context, breakeven_model, st.session_state.get("ai_narrative_enabled", False)
    )
    source_truth_report = build_source_of_truth_report(tb_model, revenue_model, expense_model, pnl_model, confirmed_months, profile_context)
    comprehensive_model["source_of_truth_report"] = source_truth_report
    comprehensive_model["comparative_analysis"] = _build_prior_tb_comparison(
        tb_model,
        previous_tb_model,
        current_label=str(current_year or "الفترة الحالية"),
        previous_label=str(previous_year or "الفترة السابقة"),
    )

    st.session_state.models = {
        "revenue_model": revenue_model,
        "expense_model": expense_model,
        "tb_model": tb_model,
        "previous_tb_model": previous_tb_model,
        "previous_revenue_model": previous_revenue_model,
        "analysis_year": current_year,
        "base_year": previous_year,
        "active_files": {
            "trial_balance": tb_record.get("file_name") if tb_record else None,
            "revenue": revenue_record.get("file_name") if revenue_record else None,
            "expense": expense_record.get("file_name") if expense_record else None,
            "previous_trial_balance": previous_tb_record.get("file_name") if previous_tb_record else None,
            "previous_revenue": previous_revenue_record.get("file_name") if previous_revenue_record else None,
        },
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
        "source_truth_report": source_truth_report,
        "period_context": period_context,
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
st.markdown('<h1 class="main-title">Wazen CFO Intelligence Agent V14.1</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">من بيانات محاسبية خام إلى تشخيص مالي وتنبيهات تنفيذية وسيناريوهات قرار.</p>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## Wazen V14.1")
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
    st.caption("V14.1: Executive UX + Comparative Year Control")


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

    st.markdown("### كيف سيفكر الإيجنت في هذا القطاع؟")
    render_sector_intelligence_panel(refresh_business_profile())


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
        render_year_control(readable_files)
        revenue_preview_record = _pick_record_by_year(readable_files, st.session_state.get("analysis_year"), role="official_revenue_source") or _pick_latest_record(readable_files, role="official_revenue_source")
        expense_preview_record = _pick_record_by_year(readable_files, st.session_state.get("analysis_year"), role="official_expense_source") or _pick_latest_record(readable_files, role="official_expense_source")
        tb_preview_record = _pick_record_by_year(readable_files, st.session_state.get("analysis_year"), role="validation_source", detected_type="trial_balance") or _pick_latest_record(readable_files, role="validation_source", detected_type="trial_balance")

        revenue_definition = st.selectbox("تعريف الإيراد", REVENUE_DEFINITIONS, index=REVENUE_DEFINITIONS.index(st.session_state.get("revenue_definition", REVENUE_DEFINITIONS[0])) if st.session_state.get("revenue_definition") in REVENUE_DEFINITIONS else 0)
        st.session_state.revenue_definition = revenue_definition
        preview_revenue_model = build_revenue_model(revenue_preview_record, revenue_definition) if revenue_preview_record else None
        preview_tb_model = parse_trial_balance(tb_preview_record) if tb_preview_record else None
        preview_revenue_total = (preview_revenue_model.get("total_revenue", 0) if preview_revenue_model else 0) or ((preview_tb_model or {}).get("income_statement", {}) or {}).get("total_revenue", 0)
        if expense_preview_record:
            preview_expense_model = build_expense_model(expense_preview_record, preview_revenue_total)
        elif preview_tb_model:
            preview_expense_model = build_expense_model_from_trial_balance(preview_tb_model, preview_revenue_total)
        else:
            preview_expense_model = None

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
                    # V13.4 privacy guard: no account names are sent to an external AI unless the user explicitly enables AI mode.
                    initial_mapping = apply_smart_classification(base_mapping, sector_context=industry, use_openai=st.session_state.get("ai_narrative_enabled", False))
                st.session_state.expense_mapping = initial_mapping.copy()
                # Auto classification is accepted as a starting point; user edits can be applied later.
                st.session_state.expense_mapping_saved = True
                st.session_state.mapping_signature = current_signature
            source_label = "من ميزان المراجعة" if preview_expense_model.get("source") == "trial_balance" else "من ملف المصروفات التفصيلي"
            st.info(f"تم بناء خريطة المصاريف {source_label}. ميزان المراجعة يكفي لاستخراج المصاريف وهيكل التكلفة، وملف المصروفات الشهري يضيف التوزيع الشهري فقط. راجعي فقط البنود منخفضة الثقة أو المصنفة بحاجة مراجعة.")
            edited_mapping = render_expense_mapping_editor(st.session_state.expense_mapping, key_prefix="expense_mapping_v12")
            if st.button("حفظ تصنيف المصاريف", type="secondary"):
                st.session_state.expense_mapping = edited_mapping.copy()
                st.session_state.expense_mapping_saved = True
                st.success("تم حفظ التصنيف. يمكنك الآن بناء النموذج المالي.")
        else:
            st.info("لا توجد مصاريف كافية لبناء خريطة تصنيف الآن.")

        min_status = minimum_model_status(st.session_state.files)
        # Do not block model building because mapping was not manually reviewed.
        # Build with deterministic/AI defaults and allow later reclassification + recalculation.
        build_disabled = bool(not min_status["ok"])
        if not min_status["ok"]:
            render_minimum_model_guard(min_status)
        if st.button("بناء النموذج المالي من الملفات المتاحة", disabled=build_disabled, type="primary"):
            with st.spinner("بناء النموذج المالي وطبقة السيولة والتحصيل..."):
                build_models_from_session(revenue_definition)
            go_to("3. جاهزية التحليل")

        if preview_expense_model is not None and not st.session_state.expense_mapping_saved:
            st.warning("توجد تعديلات غير مطبقة على التصنيف. يمكن بناء النموذج بالتصنيف الحالي، أو حفظ التعديلات ثم إعادة البناء.")


# -----------------------------------------------------------------------------
# Readiness
# -----------------------------------------------------------------------------
elif page == "3. جاهزية التحليل":
    section_header("3. قابلية التحليل")
    profile = build_readiness_profile(st.session_state.files, refresh_business_profile(), st.session_state.models)
    active_files = (st.session_state.models or {}).get("active_files", {}) if st.session_state.models else {}

    st.markdown("""
    <div class="v141-readiness-hero">
      <div>
        <span>نطاق التحليل الحالي</span>
        <h2>ماذا يمكن الاعتماد عليه الآن؟</h2>
        <p>هذه الصفحة تلخص مصادر النموذج ودقة القراءة دون تحويل الملفات الناقصة إلى مساحة عمل طويلة.</p>
      </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        kpi_card("قابلية التحليل", f"{profile['score']}%", profile["label"])
    with c2:
        kpi_card("ثقة قراءة الملفات", f"{profile['avg_confidence']*100:.0f}%", "وضوح بنية الملفات")
    with c3:
        years_txt = "—"
        if st.session_state.get("analysis_year"):
            years_txt = str(st.session_state.get("analysis_year"))
            if st.session_state.get("base_year"):
                years_txt += f" / أساس {st.session_state.get('base_year')}"
        kpi_card("فترة المقارنة", years_txt, "السنة الحالية وسنة الأساس")

    status_html = f"""
    <div class="v141-readiness-scope">
      <h3>{_html_escape(profile['label'])}</h3>
      <p>{_html_escape(profile['status'])}</p>
    </div>
    """
    st.markdown(status_html, unsafe_allow_html=True)

    labels = {
        "trial_balance": "ميزان المراجعة الحالي",
        "previous_trial_balance": "سنة الأساس للمقارنة",
        "revenue": "إيرادات تفصيلية",
        "expense": "مصروفات تفصيلية",
        "previous_revenue": "إيرادات سنة أساس",
    }
    source_cards = []
    for key, label in labels.items():
        source_cards.append({"label": label, "file": active_files.get(key)})
    card_parts = []
    for c in source_cards:
        tone = "ok" if c.get("file") else "missing"
        status = "متوفر" if c.get("file") else "غير مرفوع"
        note = c.get("file") or "ليس شرطاً لإيقاف التحليل، لكنه يرفع الدقة عند توفره."
        card_parts.append(f'<div class="v141-source-card {tone}"><span>{_html_escape(c["label"])}</span><strong>{_html_escape(status)}</strong><p>{_html_escape(note)}</p></div>')
    st.markdown(f'<div class="v141-source-grid">{"".join(card_parts)}</div>', unsafe_allow_html=True)

    if st.session_state.get("pending_rebuild"):
        min_status = minimum_model_status(st.session_state.files)
        if not min_status["ok"]:
            render_minimum_model_guard(min_status)
        elif st.button("تحديث النموذج بالملفات المضافة", type="primary"):
            with st.spinner("إعادة بناء النموذج..."):
                build_models_from_session(st.session_state.get("revenue_definition", REVENUE_DEFINITIONS[0]))
            st.success("تم تحديث النموذج بالملفات الجديدة.")
            st.rerun()

    recs = build_missing_data_recommendations(profile)
    if isinstance(recs, pd.DataFrame) and not recs.empty:
        with st.expander("مصادر اختيارية ترفع دقة القراءة"):
            st.caption("تُضاف من صفحة رفع الملفات والمطابقة؛ لا تحتاج مساحة رفع منفصلة هنا.")
            compact = recs.head(5).rename(columns={"المطلوب بلغة بسيطة": "المصدر المقترح", "القيمة المضافة": "الأثر"})
            _render_lux_table(compact, max_rows=5)

    with st.expander("تفاصيل نطاق التحليل"):
        checks_df = profile["checks"].copy()
        if not checks_df.empty:
            checks_df["الحالة"] = checks_df["الحالة"].replace({"متوفر": "✅ متوفر", "غير متوفر": "⚠️ غير متوفر"})
        _render_lux_table(checks_df, max_rows=20)


# -----------------------------------------------------------------------------
# Executive diagnosis
# -----------------------------------------------------------------------------
elif page == "4. التشخيص التنفيذي":
    section_header("4. التشخيص المالي التنفيذي")
    if not st.session_state.models:
        st.warning("ابني النموذج المالي أولًا من صفحة رفع الملفات والمطابقة.")
    else:
        models = st.session_state.models
        pnl_model = models.get("pnl_model", {})
        expense_model = models.get("expense_model")
        liq_model = st.session_state.liquidity_model or build_liquidity_collections_model(st.session_state.files)
        st.session_state.liquidity_model = liq_model
        profile = refresh_business_profile()
        exec_kpis = build_executive_kpis(pnl_model, expense_model)
        liq_diag = liquidity_cfo_narrative(liq_model, pnl_model)
        full_model = models.get("comprehensive_model", {})
        mg = full_model.get("management_pnl", {}) if full_model else {}
        rq = full_model.get("revenue_quality_tb", {}) if full_model else {}

        ai_payload = build_ai_diagnosis_payload(
            models=models,
            profile=profile,
            liquidity_model=liq_model,
            liquidity_diagnosis=liq_diag,
            exec_kpis=exec_kpis,
            files=st.session_state.files,
        )
        ai_sig = payload_signature(ai_payload)
        ai_enabled = bool(st.session_state.get("ai_narrative_enabled", False))
        refresh_ai = st.button("تحديث التشخيص من البيانات الحالية", use_container_width=False)

        if ai_enabled:
            if (refresh_ai or st.session_state.get("ai_exec_diag_signature") != ai_sig or not st.session_state.get("ai_exec_diag_cache")):
                with st.spinner("يتم توليد تشخيص CFO مخصص من بيانات الشركة الحالية..."):
                    st.session_state.ai_exec_diag_cache = generate_ai_executive_diagnosis(ai_payload)
                    st.session_state.ai_exec_diag_signature = ai_sig
            exec_diag = st.session_state.get("ai_exec_diag_cache") or fallback_executive_diagnosis(ai_payload)
            if exec_diag.get("source") == "no_key":
                st.warning("تم تفعيل AI، لكن لا يوجد مفتاح OpenAI في Secrets أو متغيرات البيئة. ستظهر قراءة داخلية بديلة إلى أن يتم ضبط المفتاح.")
            elif exec_diag.get("source") == "error_fallback":
                st.warning("تعذر توليد القراءة عبر AI، لذلك تم استخدام قراءة داخلية بديلة. راجعي إعدادات المفتاح أو سجل الأخطاء.")
        else:
            exec_diag = fallback_executive_diagnosis(ai_payload)

        def _fmt_money(v):
            n = _as_number(v, None)
            return "—" if n is None else f"{n:,.0f}"
        def _fmt_pct(v):
            n = _as_number(v, None)
            return "—" if n is None else f"{n:.1f}%" if abs(n) > 1 else f"{n*100:.1f}%"
        def _ratio_of(v, base):
            a = _as_number(v, None); b = _as_number(base, None)
            return None if a is None or not b else a / b

        revenue = _as_number(mg.get("revenue"), exec_kpis.get("revenue", 0)) or 0
        cogs = _as_number(mg.get("cogs"), 0) or 0
        gross_profit = _as_number(mg.get("gross_profit"), revenue - cogs) or 0
        opex = _as_number(mg.get("opex"), exec_kpis.get("operating_expenses", 0)) or 0
        admin = _as_number(mg.get("admin_opex"), None)
        selling = _as_number(mg.get("selling_marketing"), None)
        ebitda = _as_number(mg.get("ebitda"), gross_profit - opex) or 0
        net_profit = _as_number(mg.get("net_profit"), exec_kpis.get("net_profit", 0)) or 0
        leakage = rq.get("leakage_ratio") if isinstance(rq, dict) else None

        st.markdown("### ملخص تنفيذي رقمي")
        st.caption("الترتيب يعكس انتقال الإيراد من المبيعات إلى الربح النهائي، وليس مجرد عرض أرقام منفصلة.")
        cols = st.columns(4)
        with cols[0]: kpi_card("إجمالي الإيراد", _fmt_money(revenue), "أساس قراءة النشاط")
        with cols[1]: kpi_card("تكلفة الإيراد", _fmt_money(cogs), f"{_fmt_pct(_ratio_of(cogs, revenue))} من الإيراد")
        with cols[2]: kpi_card("مجمل الربح", _fmt_money(gross_profit), f"هامش {_fmt_pct(_ratio_of(gross_profit, revenue))}")
        with cols[3]: kpi_card("المصاريف التشغيلية", _fmt_money(opex), f"{_fmt_pct(_ratio_of(opex, revenue))} من الإيراد")

        cols2 = st.columns(4)
        with cols2[0]: kpi_card("المصاريف الإدارية", _fmt_money(admin), f"{_fmt_pct(_ratio_of(admin, revenue))} من الإيراد")
        with cols2[1]: kpi_card("البيع والتسويق", _fmt_money(selling), f"{_fmt_pct(_ratio_of(selling, revenue))} من الإيراد")
        with cols2[2]: kpi_card("صافي النتيجة", _fmt_money(net_profit), f"هامش {_fmt_pct(_ratio_of(net_profit, revenue))}")
        with cols2[3]: kpi_card("نقاء الإيراد", "—" if leakage is None else f"{(1-leakage)*100:.1f}%", "بعد الخصومات والمردودات")

        headline = exec_diag.get("headline") or "تشخيص مالي غير مكتمل"
        source_label = "مولد بالذكاء الصناعي من مؤشرات الشركة" if exec_diag.get("source") == "ai" else "قراءة داخلية من محرك وازن"
        if not ai_enabled:
            source_label = "قراءة داخلية — يمكن تفعيل AI لصياغة CFO أكثر مرونة"
        tone_class = "danger" if net_profit < 0 or "خس" in str(headline) or "لا يتحول" in str(headline) else "focus"

        def _ul(items):
            if not isinstance(items, list):
                items = [items] if items else []
            return "".join([f"<li>{_html_escape(x)}</li>" for x in items if str(x or '').strip()]) or "<li>لا توجد ملاحظات إضافية من النموذج الحالي.</li>"

        st.markdown(f"""
        <div class="ai-cfo-diagnosis v140-exec-diagnosis">
            <div class="ai-cfo-source">{_html_escape(source_label)}</div>
            <h3>{_html_escape(headline)}</h3>
            <p class="ai-cfo-main {tone_class}">{_html_escape(exec_diag.get('executive_message',''))}</p>
            <div class="ai-cfo-grid">
                <div class="ai-cfo-box"><h4>قراءة نموذج العمل</h4><ul>{_ul(exec_diag.get('business_model_reading', exec_diag.get('evidence', [])))}</ul></div>
                <div class="ai-cfo-box"><h4>مصادر الضغط</h4><ul>{_ul(exec_diag.get('risks', []))}</ul></div>
                <div class="ai-cfo-box"><h4>السيولة ورأس المال العامل</h4><p>{_html_escape(exec_diag.get('cash_and_working_capital',''))}</p></div>
                <div class="ai-cfo-box"><h4>حدود القراءة الحالية</h4><ul>{_ul(exec_diag.get('data_limits', []))}</ul></div>
            </div>
            <div class="ai-cfo-actions"><h4>إجراءات تنفيذية مقترحة</h4><ul>{_ul(exec_diag.get('next_actions', []))}</ul></div>
            <div class="ai-cfo-note">{_html_escape(exec_diag.get('confidence_note',''))}</div>
        </div>
        """, unsafe_allow_html=True)

        health = full_model.get("financial_health_score", {}) if full_model else {}
        warnings = []
        warnings += (health.get("caps", []) if isinstance(health, dict) else [])
        warnings += ((full_model.get("segment_analysis", {}) or {}).get("warnings", []) if full_model else [])
        warnings += ((full_model.get("balance_quality_flags", {}) or {}).get("flags", []) if full_model else [])
        if warnings:
            with st.expander("ملاحظات لتحسين دقة القراءة"):
                for w in warnings:
                    st.markdown(f'<div class="v141-professional-note">{_html_escape(w)}</div>', unsafe_allow_html=True)


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
        profile = refresh_business_profile()
        guarded_for_command = build_metric_guard_report(full_model.get("ratios", pd.DataFrame()), full_model.get("metric_pack", {}), profile, st.session_state.files, full_model)
        st.caption("نبدأ من صفحات التحليل. التشخيص التنفيذي يبنى لاحقًا بعد تثبيت صحة الأرقام وطريقة عرضها.")
        tabs = st.tabs(["مؤشرات القرار", "التحليل الرأسي والأفقي", "جودة الإيراد", "الربحية", "السيولة والنقد", "التحصيل والدوران", "المصاريف", "معايير القطاع", "دليل النسب"])

        with tabs[0]:
            st.subheader("مؤشرات القرار المالي")
            health = full_model.get("financial_health_score", {})
            findings_df = full_model.get("diagnostic_findings", pd.DataFrame())
            ratio_df = full_model.get("ratios", pd.DataFrame())
            render_ratio_decision_dashboard(ratio_df, health, findings_df)

        with tabs[1]:
            st.subheader("التحليل الرأسي والأفقي")
            render_vertical_horizontal_executive(full_model)

        with tabs[2]:
            st.subheader("جودة الإيراد")
            st.caption("جودة الإيراد تقيس مدى قوة المبيعات المسجلة: هل تتحول إلى صافي إيراد قابل للتحصيل والاستمرار، أم تتآكل بالخصومات والمردودات أو تعتمد على عملاء محدودين. من ميزان المراجعة تُقرأ الخصومات والمردودات وصافي المبيعات، أما التحصيل والتكرار وتركيز العملاء فتحتاج ملفات داعمة.")
            rq_tb = full_model.get("revenue_quality_tb", {}) or {}
            if rq_tb.get("available"):
                cards = rq_tb.get("cards", {}) or {}
                gross_sales = _as_number(cards.get('gross_sales'), 0.0)
                discounts = abs(_as_number(rq_tb.get('discounts'), 0.0))
                returns = abs(_as_number(rq_tb.get('returns'), 0.0))
                lr = rq_tb.get("leakage_ratio")
                discount_rate = discounts / gross_sales if gross_sales else None
                return_rate = returns / gross_sales if gross_sales else None
                c1,c2,c3,c4,c5 = st.columns(5)
                with c1: kpi_card("إجمالي المبيعات", f"{gross_sales:,.0f}", "قبل الخصومات والمردودات")
                with c2: kpi_card("الخصومات", f"{discounts:,.0f}", "تآكل قبل الصافي")
                with c3: kpi_card("المردودات", f"{returns:,.0f}", "تآكل قبل الصافي")
                with c4: kpi_card("تآكل الإيراد", "—" if lr is None else f"{lr*100:.1f}%", "خصومات + مردودات")
                with c5: kpi_card("صافي المبيعات", f"{cards.get('net_sales',0):,.0f}", "بعد التآكل")

                quality_rows = pd.DataFrame([
                    {"البند": "إجمالي المبيعات", "القيمة": f"{gross_sales:,.0f}", "النسبة من إجمالي المبيعات": "100.0%", "القراءة": "حجم المبيعات قبل أي تخفيضات أو مردودات.", "الإجراء": "استخدمه كأساس لقياس التآكل قبل الحكم على النمو."},
                    {"البند": "الخصومات", "القيمة": f"{discounts:,.0f}", "النسبة من إجمالي المبيعات": "—" if discount_rate is None else f"{discount_rate*100:.1f}%", "القراءة": "ارتفاعها قد يعني ضغط تسعير أو سياسة خصم غير منضبطة.", "الإجراء": "اربط الخصومات بالعميل أو المنتج أو الفرع عند توفر التفصيل."},
                    {"البند": "المردودات", "القيمة": f"{returns:,.0f}", "النسبة من إجمالي المبيعات": "—" if return_rate is None else f"{return_rate*100:.1f}%", "القراءة": "ارتفاعها قد يشير إلى جودة منتج، تسليم، أو قبول عميل ضعيف.", "الإجراء": "راجع أسباب المرتجعات حسب الصنف أو العميل أو المشروع."},
                    {"البند": "تآكل الإيراد", "القيمة": "—" if lr is None else f"{lr*100:.1f}%", "النسبة من إجمالي المبيعات": "خصومات + مردودات", "القراءة": "كلما انخفض كان صافي الإيراد أقرب للمبيعات المسجلة.", "الإجراء": "حدّد سقف خصومات ومؤشرات قبول للمبيعات التي تتحول إلى إيراد صافٍ."},
                    {"البند": "صافي المبيعات", "القيمة": f"{cards.get('net_sales',0):,.0f}", "النسبة من إجمالي المبيعات": "—" if not gross_sales else f"{_as_number(cards.get('net_sales',0),0)/gross_sales*100:.1f}%", "القراءة": "هذا هو الرقم الأقرب للإيراد القابل للتحليل بعد الاستبعادات التجارية.", "الإجراء": "قارنه بالتحصيل والذمم لتقييم جودة الإيراد نقديًا."},
                ])
                _render_lux_table(quality_rows, max_rows=10, title="تحليل نقاء الإيراد من ميزان المراجعة")
                render_insight_panel("قراءة جودة الإيراد", rq_tb.get("narrative", ""), "خطر" if (lr or 0) >= .20 else "متابعة", "تبدأ القراءة من نقاء الإيراد: إجمالي المبيعات ناقص الخصومات والمردودات. وكلما كان التآكل محدودًا كانت المبيعات المسجلة أقرب إلى صافي إيراد قابل للتحليل. تبقى جودة الإيراد النهائية مرتبطة بالتحصيل، تكرار العملاء، وتركيز الإيرادات عند توفر ملفاتها.", ["ميزان المراجعة يكفي لقياس الخصومات والمردودات وصافي المبيعات عندما تكون حساباتها منفصلة.", "لا يتم الحكم النهائي على الاستدامة أو التحصيل أو تركيز العملاء دون بيانات مبيعات وذمم تفصيلية."])
                _render_lux_table(rq_tb.get("table", pd.DataFrame()), max_rows=20, title="مصادر أرقام الإيراد من الميزان")
            elif revenue_model and not revenue_model.get("monthly_revenue", pd.DataFrame()).empty:
                rev_monthly = revenue_model["monthly_revenue"].copy()
                rev_monthly["revenue"] = pd.to_numeric(rev_monthly["revenue"], errors="coerce").fillna(0)
                rev_quality = build_revenue_quality(rev_monthly)
                c1,c2,c3,c4 = st.columns(4)
                with c1: kpi_card("إجمالي الإيرادات", f"{rev_quality['cards'].get('total',0):,.0f}", "خلال الفترة")
                with c2: kpi_card("متوسط شهري", f"{rev_quality['cards'].get('avg',0):,.0f}", "متوسط محافظ")
                with c3: kpi_card("أعلى شهر", str(rev_quality['cards'].get('best_month','—')), f"{rev_quality['cards'].get('max_share',0)*100:.1f}%")
                with c4: kpi_card("انتظام الإيراد", f"{rev_quality['cards'].get('stability_score',0):.0f}/100", "مؤشر يختبر التذبذب وتركيز أعلى شهر")
                render_insight_panel("قراءة مالية للإيراد", rev_quality["narrative"], rev_quality["risk"], rev_quality["action"], ["انتظام الإيراد يعني: هل الإيراد متوازن عبر الأشهر أم معتمد على شهر أو عقد استثنائي؟"])
                line_chart(rev_monthly, "month", "revenue", "اتجاه الإيرادات")
            else:
                st.info("لا توجد بيانات إيرادات كافية.")

        with tabs[3]:
            st.subheader("الربحية وقائمة الدخل")
            render_executive_income_statement(build_executive_income_statement(pnl_model, expense_model))
            if monthly_pnl_model is not None and not monthly_pnl_model.empty:
                st.markdown("#### الربحية الشهرية")
                render_executive_monthly_profitability(build_executive_monthly_profitability(monthly_pnl_model, pnl_model, expense_model))

        with tabs[4]:
            st.subheader("السيولة والنقد")
            render_liquidity_decision_view(full_model, liq_model)

        with tabs[5]:
            st.subheader("التحصيل والدوران")
            render_collection_turnover_view(full_model, liq_model)

        with tabs[6]:
            st.subheader("المصاريف وهيكل التكلفة")
            render_cost_structure_view(expense_model, full_model)

        with tabs[7]:
            st.subheader("معايير القطاع")
            profile = refresh_business_profile()
            guarded = build_metric_guard_report(full_model.get("ratios", pd.DataFrame()), full_model.get("metric_pack", {}), profile, st.session_state.files, full_model)
            enriched = _enrich_ratios_with_benchmarks(guarded, full_model, profile)
            benchmark = build_benchmark_intelligence(profile, guarded)
            render_insight_panel("كيف تُستخدم المعايير؟", "تم دمج المعيار بجانب كل نسبة داخل صفحات التحليل، لأن صاحب العمل لا يحتاج جدول Benchmarks منفصلًا عن النسبة. هذه الصفحة أصبحت منهجية مراجعة وليست مكان الحكم الأساسي.", "إرشادي", "اعتمد المقارنة الداخلية أولًا، ثم استخدم معيار القطاع كإشارة مساعدة، ولا تجعل المعيار الخارجي حكمًا نهائيًا دون مصدر موثق وفترة مقارنة.", ["المعايير الحالية إرشادية داخلية وليست Benchmark عالمي موثق.", "عند إضافة سنة سابقة أو قاعدة عملاء مجمعة يمكن تحويلها إلى مقارنة داخلية أقوى."])
            if isinstance(enriched, pd.DataFrame) and not enriched.empty:
                cols = [c for c in ["المجموعة", "المؤشر", "النتيجة", "المعيار بجانب النسبة", "مقارنة بالمعيار", "نوع المعيار", "درجة الثقة", "ملاحظة CMA"] if c in enriched.columns]
                _render_lux_table(enriched[cols], max_rows=30, title="النسب الحالية ومعيارها بجانبها")
            if not benchmark.get("internal_priority", pd.DataFrame()).empty:
                st.markdown("#### المقارنة الداخلية أولًا")
                _render_lux_table(benchmark.get("internal_priority"), max_rows=10)

        with tabs[8]:
            st.subheader("دليل النسب")
            render_metric_catalog_reference()


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
            tb_model=models.get("tb_model"),
            source_truth_report=models.get("source_truth_report"),
            comprehensive_model=models.get("comprehensive_model"),
        )
        st.download_button(
            "تحميل Excel CFO Pack",
            data=excel_bytes,
            file_name="wazen_cfo_pack_v13_4.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.info("سيتم لاحقًا إضافة PDF Executive Summary بنفس مسار التشخيص والتنبيهات.")
