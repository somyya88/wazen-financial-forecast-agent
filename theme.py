import streamlit as st
from config import WAZEN_BLUE, WAZEN_ORANGE, WAZEN_LIGHT_BG, WAZEN_TEXT

def apply_theme():
    css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap');

    :root {
        --wazen-blue: #17479E;
        --wazen-orange: #FAA61A;
        --wazen-bg: #F7F9FC;
        --wazen-text: #1F2D3D;
        --wazen-border: #E6EAF0;
        --wazen-soft-blue: #EAF2FF;
        --wazen-green: #EAF8F0;
        --wazen-red: #FDECEC;
    }

    html, body, [class*="css"] {
        font-family: 'Tajawal', sans-serif;
        direction: rtl;
        color: var(--wazen-text);
    }

    .stApp {
        background: #F7F9FC;
    }

    section[data-testid="stSidebar"] {
        direction: rtl;
        background: #FFFFFF;
        border-left: 1px solid #E5E7EB;
    }

    .main-title {
        font-size: 34px;
        font-weight: 800;
        color: var(--wazen-blue);
        margin-bottom: 0;
        letter-spacing: -0.4px;
    }

    .sub-title {
        color: #4B5563;
        font-size: 17px;
        margin-top: 4px;
        margin-bottom: 22px;
    }

    .section-header {
        font-size: 27px;
        font-weight: 800;
        color: #111827;
        margin: 28px 0 16px;
        padding-right: 14px;
        border-right: 6px solid var(--wazen-orange);
        line-height: 1.35;
    }

    .kpi-card {
        position: relative;
        background: linear-gradient(180deg, #FFFFFF 0%, #FBFCFF 100%);
        border: 1px solid var(--wazen-border);
        border-radius: 20px;
        padding: 22px 24px 20px;
        min-height: 188px;
        box-shadow: 0 14px 34px rgba(23, 71, 158, 0.07);
        overflow: hidden;
        margin-bottom: 18px;
        direction: rtl;
    }

    .kpi-card-accent {
        position: absolute;
        top: 0;
        right: 0;
        width: 8px;
        height: 100%;
        background: linear-gradient(180deg, var(--wazen-orange), rgba(250,166,26,0.18));
    }

    .kpi-label {
        font-size: 18px;
        font-weight: 800;
        color: #111827;
        min-height: 42px;
        line-height: 1.35;
    }

    .kpi-value {
        color: var(--wazen-blue);
        font-size: 38px;
        line-height: 1.05;
        font-weight: 800;
        letter-spacing: -0.8px;
        margin-top: 16px;
        text-align: left;
        direction: ltr;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .kpi-note {
        margin-top: 16px;
        color: #4B5563;
        font-size: 14px;
        line-height: 1.55;
        min-height: 36px;
    }

    .info-box, .warning-box, .success-box {
        border-radius: 14px;
        padding: 14px 18px;
        margin: 12px 0;
        line-height: 1.8;
        font-size: 15px;
    }

    .info-box {
        background: #EAF4FF;
        color: #0B4A8B;
        border: 1px solid #CFE7FF;
    }

    .warning-box {
        background: #FFF7ED;
        color: #9A3412;
        border: 1px solid #FED7AA;
    }

    .success-box {
        background: #ECFDF5;
        color: #065F46;
        border: 1px solid #A7F3D0;
    }

    .wazen-table-title {
        font-size: 24px;
        font-weight: 800;
        color: #111827;
        margin: 22px 0 12px;
    }

    .wazen-table-wrap {
        background: #FFFFFF;
        border: 1px solid var(--wazen-border);
        border-radius: 18px;
        overflow: hidden;
        box-shadow: 0 12px 28px rgba(17, 24, 39, 0.045);
        margin: 12px 0 24px;
    }

    table.wazen-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        direction: rtl;
        font-size: 15.5px;
    }

    .wazen-table thead th {
        background: #F2F5FA;
        color: #667085;
        font-weight: 700;
        padding: 14px 16px;
        border-bottom: 1px solid #D8DEE8;
        text-align: right !important;
        direction: rtl !important;
    }

    .wazen-table tbody td {
        padding: 13px 16px;
        border-bottom: 1px solid #EEF1F5;
        color: #1F2937;
        vertical-align: middle;
        background: #FFFFFF;
        line-height: 1.45;
        text-align: right;
    }

    .wazen-table tbody tr:nth-child(even) td {
        background: #FCFDFF;
    }

    .wazen-table td.num {
        direction: ltr;
        text-align: left !important;
        font-variant-numeric: tabular-nums;
        color: #111827;
        white-space: nowrap;
    }

    .wazen-table tr.total-row td,
    .wazen-table tr.revenue-total td,
    .wazen-table tr.cogs-total td,
    .wazen-table tr.gross-profit td {
        background: #EAF2FF !important;
        font-weight: 850;
        color: #123A7A;
        border-top: 2px solid #C8D8F5;
    }

    .wazen-table tr.gross-profit td {
        border-top: 3px double #B7CDF4;
        color: #17479E;
    }

    .wazen-table tr.opex-row td {
        background: #FFF7E8 !important;
        color: #7A4B00;
        font-weight: 850;
        border-top: 2px solid #FFDFA3;
    }

    .wazen-table tr.strong-row td,
    .wazen-table tr.net-profit-row td {
        background: #EAF8F0 !important;
        color: #065F46 !important;
        font-weight: 900 !important;
        border-top: 3px double #7BD6A5;
        border-bottom: 2px solid #7BD6A5;
        font-size: 17px;
    }

    .table-link {
        color: inherit;
        text-decoration: none;
        border-bottom: 1px dashed currentColor;
        cursor: pointer;
    }

    .table-link:hover {
        color: #17479E;
        background: rgba(23,71,158,0.06);
    }

    .tooltip-note {
        color: #667085;
        font-size: 14px;
        margin-top: -6px;
        margin-bottom: 12px;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        direction: rtl;
    }

    .stTabs [data-baseweb="tab"] {
        font-weight: 700;
        color: #344054;
    }

    .stTabs [aria-selected="true"] {
        color: var(--wazen-blue) !important;
        border-bottom-color: var(--wazen-orange) !important;
    }

    div[data-testid="stDataFrame"] {
        direction: rtl;
    }

    .js-plotly-plot {
        background: #FFFFFF;
        border-radius: 16px;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
