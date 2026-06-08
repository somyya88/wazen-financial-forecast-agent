import streamlit as st

def kpi_card(label: str, value: str, note: str = ""):
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-note">{note}</div>
    </div>
    """, unsafe_allow_html=True)

def section_header(title: str):
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)

def message_box(message: str, level: str = "info"):
    cls = "info-box"
    if level == "warning":
        cls = "warning-box"
    if level == "success":
        cls = "success-box"
    if level == "error":
        cls = "warning-box"
    st.markdown(f'<div class="{cls}">{message}</div>', unsafe_allow_html=True)
