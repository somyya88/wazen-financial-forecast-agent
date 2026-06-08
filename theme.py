import streamlit as st
from config import WAZEN_BLUE, WAZEN_ORANGE, WAZEN_LIGHT_BG, WAZEN_TEXT

def apply_theme():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Tajawal', sans-serif;
        direction: rtl;
    }}

    .stApp {{
        background: {WAZEN_LIGHT_BG};
    }}

    section[data-testid="stSidebar"] {{
        direction: rtl;
        background: #FFFFFF;
        border-left: 1px solid #E5E7EB;
    }}

    .main-title {{
        font-size: 34px;
        font-weight: 800;
        color: {WAZEN_BLUE};
        margin-bottom: 0;
    }}

    .sub-title {{
        color: #4B5563;
        font-size: 17px;
        margin-top: 4px;
        margin-bottom: 22px;
    }}

    .wazen-card {{
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 20px;
        padding: 20px;
        box-shadow: 0 10px 28px rgba(17, 24, 39, 0.06);
        margin-bottom: 16px;
    }}

    .kpi-card {{
        background: linear-gradient(180deg, #FFFFFF 0%, #FAFBFF 100%);
        border: 1px solid #E5E7EB;
        border-radius: 18px;
        padding: 18px;
        box-shadow: 0 8px 22px rgba(17, 24, 39, 0.05);
        min-height: 125px;
    }}

    .kpi-label {{
        color: #6B7280;
        font-size: 14px;
        font-weight: 700;
    }}

    .kpi-value {{
        color: {WAZEN_BLUE};
        font-size: 28px;
        font-weight: 800;
        margin-top: 8px;
    }}

    .kpi-note {{
        color: #4B5563;
        font-size: 13px;
        margin-top: 6px;
    }}

    .section-header {{
        color: {WAZEN_TEXT};
        font-size: 22px;
        font-weight: 800;
        border-right: 6px solid {WAZEN_ORANGE};
        padding-right: 12px;
        margin-top: 18px;
        margin-bottom: 10px;
    }}

    .warning-box {{
        background: #FFF7ED;
        border: 1px solid #FED7AA;
        color: #9A3412;
        padding: 14px;
        border-radius: 14px;
        margin: 8px 0;
    }}

    .success-box {{
        background: #ECFDF5;
        border: 1px solid #A7F3D0;
        color: #065F46;
        padding: 14px;
        border-radius: 14px;
        margin: 8px 0;
    }}

    .info-box {{
        background: #EFF6FF;
        border: 1px solid #BFDBFE;
        color: #1E3A8A;
        padding: 14px;
        border-radius: 14px;
        margin: 8px 0;
    }}

    div.stButton > button:first-child {{
        background: {WAZEN_BLUE};
        color: white;
        border-radius: 12px;
        border: 0;
        padding: 0.6rem 1rem;
        font-weight: 700;
    }}

    div.stDownloadButton > button:first-child {{
        background: {WAZEN_ORANGE};
        color: #111827;
        border-radius: 12px;
        border: 0;
        padding: 0.6rem 1rem;
        font-weight: 800;
    }}

    table {{
        direction: rtl;
    }}
    </style>
    """, unsafe_allow_html=True)
