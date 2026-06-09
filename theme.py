import streamlit as st
from config import WAZEN_BLUE, WAZEN_ORANGE, WAZEN_LIGHT_BG, WAZEN_TEXT

def apply_theme():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800;900&display=swap');

    :root {{
        --wazen-blue: {WAZEN_BLUE};
        --wazen-orange: {WAZEN_ORANGE};
        --wazen-bg: {WAZEN_LIGHT_BG};
        --wazen-text: {WAZEN_TEXT};
        --wazen-muted: #667085;
        --wazen-line: #E6EAF2;
    }}

    html, body, [class*="css"] {{
        font-family: 'Tajawal', sans-serif;
        direction: rtl;
        color: var(--wazen-text);
    }}

    .stApp {{
        background:
            radial-gradient(circle at top left, rgba(250,166,26,0.10), transparent 22%),
            radial-gradient(circle at bottom right, rgba(23,71,158,0.08), transparent 28%),
            {WAZEN_LIGHT_BG};
    }}

    .block-container {{
        padding-top: 2rem;
        max-width: 1380px;
    }}

    section[data-testid="stSidebar"] {{
        direction: rtl;
        background: #FFFFFF;
        border-left: 1px solid var(--wazen-line);
    }}

    .main-title {{
        font-size: 34px;
        font-weight: 900;
        color: var(--wazen-blue);
        margin-bottom: 0;
        letter-spacing: -0.3px;
    }}

    .sub-title {{
        color: #4B5563;
        font-size: 17px;
        margin-top: 4px;
        margin-bottom: 22px;
    }}

    .kpi-card {{
        position: relative;
        overflow: hidden;
        background: linear-gradient(180deg, #FFFFFF 0%, #FBFCFF 100%);
        border: 1px solid rgba(23,71,158,0.10);
        border-radius: 22px;
        padding: 20px 20px 18px 20px;
        box-shadow: 0 14px 34px rgba(17, 24, 39, 0.07);
        min-height: 164px;
        margin-bottom: 16px;
    }}

    .kpi-card::before {{
        content: "";
        position: absolute;
        inset: 0;
        background: linear-gradient(90deg, rgba(23,71,158,0.04), transparent 42%);
        pointer-events: none;
    }}

    .kpi-accent {{
        position: absolute;
        top: 0;
        right: 0;
        width: 7px;
        height: 100%;
        background: linear-gradient(180deg, var(--wazen-orange), rgba(250,166,26,0.18));
    }}

    .kpi-label-main {{
        color: #1F2937;
        font-size: 17px;
        font-weight: 900;
        line-height: 1.35;
        padding-right: 2px;
    }}

    .kpi-label-sub {{
        color: #7A8496;
        font-size: 12px;
        font-weight: 800;
        margin-top: 2px;
        direction: ltr;
        text-align: right;
    }}

    .kpi-value {{
        color: var(--wazen-blue);
        font-size: clamp(26px, 2.45vw, 38px);
        line-height: 1.05;
        font-weight: 900;
        margin-top: 16px;
        letter-spacing: -0.6px;
        direction: ltr;
        text-align: right;
        white-space: nowrap;
    }}

    .kpi-note {{
        color: #4B5563;
        font-size: 13px;
        font-weight: 500;
        line-height: 1.7;
        margin-top: 12px;
    }}

    .section-header {{
        color: var(--wazen-text);
        font-size: 25px;
        font-weight: 900;
        border-right: 7px solid var(--wazen-orange);
        padding-right: 14px;
        margin-top: 26px;
        margin-bottom: 14px;
        letter-spacing: -0.2px;
    }}

    .warning-box, .success-box, .info-box {{
        padding: 14px 16px;
        border-radius: 16px;
        margin: 10px 0;
        font-weight: 600;
        line-height: 1.8;
    }}

    .warning-box {{ background: #FFF7ED; border: 1px solid #FED7AA; color: #9A3412; }}
    .success-box {{ background: #ECFDF5; border: 1px solid #A7F3D0; color: #065F46; }}
    .info-box {{ background: #EFF6FF; border: 1px solid #BFDBFE; color: #1E3A8A; }}

    div.stButton > button:first-child {{
        background: var(--wazen-blue);
        color: white;
        border-radius: 13px;
        border: 0;
        padding: 0.65rem 1.05rem;
        font-weight: 800;
        box-shadow: 0 10px 18px rgba(23,71,158,0.16);
    }}

    div.stDownloadButton > button:first-child {{
        background: var(--wazen-orange);
        color: #111827;
        border-radius: 13px;
        border: 0;
        padding: 0.65rem 1.05rem;
        font-weight: 900;
    }}

    div[data-testid="stDataFrame"] {{
        border: 1px solid var(--wazen-line);
        border-radius: 16px;
        overflow: hidden;
        background: #FFFFFF;
        box-shadow: 0 10px 24px rgba(17, 24, 39, 0.04);
    }}

    div[data-testid="stDataFrame"] * {{
        font-family: 'Tajawal', sans-serif !important;
    }}

    table {{ direction: rtl; }}

    .stTabs [data-baseweb="tab-list"] {{
        gap: 10px;
        border-bottom: 1px solid var(--wazen-line);
    }}
    .stTabs [data-baseweb="tab"] {{
        font-weight: 800;
        color: #344054;
    }}
    .stTabs [aria-selected="true"] {{
        color: var(--wazen-blue) !important;
        border-bottom-color: var(--wazen-orange) !important;
    }}
    </style>
    """, unsafe_allow_html=True)
