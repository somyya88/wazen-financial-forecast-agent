import streamlit as st

def _split_label(label: str):
    if "/" in label:
        left, right = [x.strip() for x in label.split("/", 1)]
        # Existing app labels are usually English / Arabic. Display Arabic first.
        return right, left
    return label, ""

def kpi_card(label: str, value: str, note: str = ""):
    main_label, sub_label = _split_label(label)
    value_html = f'<div class="kpi-value">{value}</div>' if value else ''
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-accent"></div>
        <div class="kpi-label-main">{main_label}</div>
        <div class="kpi-label-sub">{sub_label}</div>
        {value_html}
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
