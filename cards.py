import html
import streamlit as st

def _e(value):
    return html.escape("" if value is None else str(value))

def kpi_card(label: str, value: str, note: str = ""):
    label = _e(label)
    value = _e(value) if value else "—"
    note = _e(note)
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-card-accent"></div>
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-note">{note}</div>
    </div>
    """, unsafe_allow_html=True)

def section_header(title: str):
    st.markdown(f'<div class="section-header">{_e(title)}</div>', unsafe_allow_html=True)

def message_box(message: str, level: str = "info"):
    cls = "info-box"
    if level == "warning":
        cls = "warning-box"
    if level == "success":
        cls = "success-box"
    if level == "error":
        cls = "warning-box"
    st.markdown(f'<div class="{cls}">{message}</div>', unsafe_allow_html=True)
