from __future__ import annotations

import pandas as pd
import streamlit as st

from sector_profile_engine_v12_8 import get_sector_intelligence_profile, sector_profile_table
from metric_source_guard_v12_8 import metric_guard_summary
from metric_catalog_v12_8 import catalog_df


def _badge(text: str, tone: str = "blue") -> str:
    return f'<span class="v128-badge {tone}">{text}</span>'


def render_sector_intelligence_panel(profile: dict | None):
    cfg = get_sector_intelligence_profile(profile)
    st.markdown(f"""
    <div class="v128-sector-panel">
        <div class="v128-eyebrow">Sector-aware CFO Mindset</div>
        <h3>{cfg['title']}</h3>
        <p>{cfg['mindset']}</p>
        <div class="v128-badges">
            {_badge('محرك عام + منطق قطاعي', 'blue')}
            {_badge('لا يوقف التحليل بسبب ملف إضافي', 'orange')}
            {_badge('لا يعرض رقمًا بلا مصدر', 'gray')}
        </div>
    </div>
    """, unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("#### مؤشرات هذا النشاط")
        st.write("، ".join(cfg["core_metrics"]))
    with c2:
        st.markdown("#### منطق التكلفة")
        st.write(cfg["cost_logic"])
    with c3:
        st.markdown("#### ملفات ترفع الدقة")
        st.write("، ".join(cfg["special_files"]))
    with st.expander("خريطة تفكير الإيجنت حسب القطاع"):
        st.dataframe(sector_profile_table(profile), use_container_width=True, hide_index=True)


def render_metric_guard_experience(guarded_df: pd.DataFrame):
    if guarded_df is None or guarded_df.empty:
        st.info("لا توجد نسب لعرضها بعد.")
        return
    summary = metric_guard_summary(guarded_df)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""<div class="v128-mini-card"><div>تغطية المؤشرات</div><strong>{summary['coverage']:.0f}%</strong><span>{summary['available']} من {summary['total']} قابلة للقراءة</span></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="v128-mini-card"><div>ثقة القراءة</div><strong>{summary['confidence']}</strong><span>حسب مصدر كل نسبة</span></div>""", unsafe_allow_html=True)
    with c3:
        gaps = guarded_df[guarded_df["حالة المؤشر"].astype(str).eq("غير قابل للحساب")]
        st.markdown(f"""<div class="v128-mini-card"><div>فجوات البيانات</div><strong>{len(gaps)}</strong><span>تظهر كفجوة لا كصفر</span></div>""", unsafe_allow_html=True)

    top = guarded_df[~guarded_df["حالة المؤشر"].astype(str).isin(["غير قابل للتطبيق"])]
    display_cols = [c for c in ["المؤشر", "النتيجة", "الحكم", "حالة المؤشر", "درجة الثقة", "مصدر الحساب", "قراءة CFO", "الإجراء التنفيذي"] if c in top.columns]
    st.markdown("#### مؤشرات القرار المقروءة")
    st.dataframe(top[display_cols].head(12), use_container_width=True, hide_index=True)

    gaps = guarded_df[guarded_df["حالة المؤشر"].astype(str).eq("غير قابل للحساب")]
    if not gaps.empty:
        with st.expander("مؤشرات لم تُحسب لأن مدخلاتها غير مكتملة"):
            cols = [c for c in ["المؤشر", "المطلوب للحساب", "المصدر الأساسي", "ملاحظة CMA"] if c in gaps.columns]
            st.dataframe(gaps[cols], use_container_width=True, hide_index=True)


def render_cfo_command_center(full_model: dict, guarded_df: pd.DataFrame | None = None):
    health = full_model.get("financial_health_score", {}) or {}
    reading = full_model.get("cfo_reading", {}) or {}
    summary = metric_guard_summary(guarded_df) if guarded_df is not None else {}
    headline = reading.get("headline", "تم بناء نموذج مالي؛ ابدأ من الهامش والسيولة والتحصيل.")
    action = reading.get("action", "راجع أعلى فجوة مالية وحدد إجراء خلال 30 يوم.")
    st.markdown(f"""
    <div class="v128-command-center">
        <div class="v128-eyebrow">CFO Command Center</div>
        <h2>{headline}</h2>
        <p>{reading.get('diagnosis','قراءة الربحية تبدأ من الهامش الإجمالي ثم التشغيلي ثم صافي الربح.')}</p>
        <div class="v128-command-grid">
            <div><span>Health Score</span><strong>{health.get('score','—')}/100</strong><em>{health.get('label','')}</em></div>
            <div><span>Coverage</span><strong>{summary.get('coverage','—')}%</strong><em>{summary.get('available','—')} مؤشرات</em></div>
            <div><span>Confidence</span><strong>{summary.get('confidence','—')}</strong><em>حسب مصادر النسب</em></div>
        </div>
        <p class="v128-next-action"><strong>الإجراء التالي:</strong> {action}</p>
    </div>
    """, unsafe_allow_html=True)


def render_metric_catalog_reference():
    df = catalog_df()
    st.markdown("#### كتالوج النسب ومن أين تستخرج")
    st.caption("هذا المرجع يثبت قاعدة CMA داخل الإيجنت: لا تظهر النسبة إلا إذا عُرف مصدرها ومدخلاتها.")
    show = df.rename(columns={
        "group":"المجموعة", "name":"النسبة", "formula":"المعادلة", "needs":"ماذا تحتاج", "primary":"المصدر الأساسي", "fallback":"البديل", "cma":"قراءة CMA"
    })
    st.dataframe(show[["المجموعة", "النسبة", "المعادلة", "ماذا تحتاج", "المصدر الأساسي", "البديل", "قراءة CMA"]], use_container_width=True, hide_index=True)
