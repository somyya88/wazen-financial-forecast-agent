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

    h1, h2, h3, h4, h5, h6,
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4,
    div[data-testid="stMarkdownContainer"] h1,
    div[data-testid="stMarkdownContainer"] h2,
    div[data-testid="stMarkdownContainer"] h3,
    div[data-testid="stMarkdownContainer"] h4 {
        text-align: right !important;
        direction: rtl !important;
    }

    .wazen-table-title,
    .js-plotly-plot .gtitle {
        text-align: right !important;
        direction: rtl !important;
    }

    .insight-panel {
        background: linear-gradient(180deg, #FFFFFF 0%, #FBFCFF 100%);
        border: 1px solid #E6EAF0;
        border-radius: 20px;
        padding: 22px 24px;
        box-shadow: 0 14px 34px rgba(23,71,158,0.07);
        margin: 16px 0 26px;
        direction: rtl;
    }

    .insight-title {
        font-size: 22px;
        font-weight: 900;
        color: #111827;
        margin-bottom: 8px;
    }

    .insight-status {
        display: inline-block;
        color: #17479E;
        background: #EAF2FF;
        border: 1px solid #C8D8F5;
        border-radius: 999px;
        padding: 6px 14px;
        font-weight: 800;
        margin: 4px 0 16px;
    }

    .insight-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 14px;
        margin: 10px 0 14px;
    }

    .insight-box {
        background: #F7F9FC;
        border: 1px solid #E6EAF0;
        border-radius: 14px;
        padding: 14px 16px;
    }

    .insight-box-label {
        color: #667085;
        font-size: 13px;
        font-weight: 800;
        margin-bottom: 6px;
    }

    .insight-box-text {
        color: #1F2D3D;
        line-height: 1.75;
        font-size: 15px;
    }

    .insight-bullets {
        margin: 10px 18px 0 0;
        padding: 0;
        line-height: 1.9;
        color: #344054;
    }

    @media (max-width: 900px) {
        .insight-grid {
            grid-template-columns: 1fr;
        }
    }


    .insight-title {
        color: #17479E !important;
        letter-spacing: -0.2px;
    }

    .insight-status {
        background: #F3F7FF !important;
        color: #17479E !important;
        border-color: #BFD2F4 !important;
    }

    .insight-bullets li {
        margin-bottom: 8px;
    }


    .executive-statement th {
        text-align: right !important;
    }

    .executive-statement td.ar {
        width: 42%;
        text-align: right !important;
        font-weight: 650;
    }

    .executive-statement td.en {
        width: 36%;
        direction: ltr;
        text-align: left !important;
        color: #475467;
    }

    .executive-statement td.num {
        width: 22%;
        text-align: left !important;
        direction: ltr;
        font-weight: 750;
        color: #111827;
    }

    .executive-statement tr.statement-section td {
        background: #F5F7FB !important;
        color: #17479E;
        font-weight: 900;
        font-size: 17px;
        border-top: 2px solid #D8E2F3;
        padding-top: 16px;
        padding-bottom: 10px;
    }

    .executive-statement tr.statement-total td {
        background: #EAF2FF !important;
        color: #123A7A;
        font-weight: 900;
        border-top: 2px solid #BFD2F4;
    }

    .executive-statement tr.statement-net td {
        background: #EAF8F0 !important;
        color: #065F46;
        font-weight: 950;
        border-top: 3px double #7BD6A5;
        border-bottom: 2px solid #7BD6A5;
        font-size: 17px;
    }

    .kpi-label {
        direction: rtl;
        text-align: right;
    }

    .kpi-value {
        text-align: right !important;
        direction: ltr;
    }


    /* V9.8 Arabic-first layout hardening */
    .stApp, .main, section.main, div[data-testid="stAppViewContainer"] { direction: rtl !important; text-align: right !important; }
    div[data-testid="stMarkdownContainer"], div[data-testid="stMarkdownContainer"] p, div[data-testid="stMarkdownContainer"] li, div[data-testid="stCaptionContainer"], .stAlert, .stAlert p { direction: rtl !important; text-align: right !important; }
    .kpi-card, .insight-panel, .insight-box { direction: rtl !important; text-align: right !important; }
    .kpi-label, .kpi-note { text-align: right !important; direction: rtl !important; }
    .kpi-value { text-align: right !important; direction: ltr !important; unicode-bidi: plaintext !important; }
    .wazen-table, .wazen-table th, .wazen-table td { direction: rtl !important; text-align: right !important; }
    .wazen-table td.num { text-align: right !important; direction: ltr !important; unicode-bidi: plaintext !important; }
    .wazen-table td.en { text-align: right !important; direction: ltr !important; color:#667085; }
    .stDataFrame, div[data-testid="stDataFrame"] { direction: rtl !important; }
    ul.insight-bullets { list-style-position: inside !important; padding-right:0 !important; margin-right:0 !important; text-align:right !important; }


    .executive-diagnosis {
        direction: rtl;
        text-align: right;
        background: #FFFFFF;
        border: 1px solid #D9E2F0;
        border-radius: 20px;
        padding: 24px 28px;
        margin: 18px 0 26px 0;
        box-shadow: 0 18px 45px rgba(16, 24, 40, 0.06);
        border-right: 6px solid #17479E;
    }
    .executive-diagnosis h3 {
        color: #17479E;
        font-size: 24px;
        margin-bottom: 16px;
        font-weight: 900;
    }
    .executive-diagnosis p {
        font-size: 16px;
        line-height: 2;
        color: #101828;
        margin-bottom: 14px;
    }
    .executive-diagnosis strong {
        color: #0B2E63;
    }


    .executive-brief.compact {
        direction: rtl;
        text-align: right;
        background: #FFFFFF;
        border: 1px solid #D9E2F0;
        border-right: 6px solid #17479E;
        border-radius: 18px;
        padding: 18px 22px;
        margin: 18px 0 12px 0;
        box-shadow: 0 14px 32px rgba(16, 24, 40, 0.05);
    }
    .executive-brief.compact .brief-title {
        color: #17479E;
        font-size: 19px;
        font-weight: 900;
        margin-bottom: 8px;
    }
    .executive-brief.compact .brief-text {
        font-size: 15.5px;
        line-height: 1.9;
        color: #101828;
        margin-bottom: 8px;
    }
    .executive-brief.compact .brief-action {
        font-size: 15px;
        line-height: 1.8;
        color: #0B2E63;
        background: #F5F8FF;
        border-radius: 12px;
        padding: 10px 12px;
        margin: 8px 0;
    }
    .executive-brief.compact .brief-subtext {
        font-size: 14px;
        color: #475467;
    }



    /* V12.1 premium UX polish */
    .block-container { padding-top: 2.0rem !important; max-width: 1280px !important; }
    [data-testid="stSidebar"] .stRadio label { direction: rtl !important; text-align: right !important; }
    [data-testid="stSidebar"] [role="radiogroup"] label {
        border-radius: 14px; padding: 7px 8px; margin-bottom: 3px;
        transition: all .18s ease-in-out;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:hover {
        background: #F3F7FF;
        transform: translateX(-2px);
    }
    .main-title {
        color: #111827 !important;
        font-size: 38px !important;
        text-align: right !important;
    }
    .sub-title { color:#475467 !important; font-size:16px !important; }
    .wazen-hero {
        background: radial-gradient(circle at 10% 0%, rgba(250,166,26,.14), transparent 28%),
                    linear-gradient(135deg, #FFFFFF 0%, #F6F9FF 62%, #EEF5FF 100%);
        border: 1px solid #DCE7F7;
        border-radius: 28px;
        padding: 26px 30px;
        box-shadow: 0 24px 70px rgba(23,71,158,.10);
        margin: 0 0 22px 0;
        position: relative;
        overflow: hidden;
    }
    .wazen-hero:before {
        content:""; position:absolute; right:-60px; top:-60px; width:180px; height:180px;
        background: rgba(23,71,158,.08); border-radius: 50%;
    }
    .wazen-hero h2 { margin:0; color:#0B2E63; font-size:30px; font-weight:900; }
    .wazen-hero p { margin:10px 0 0; color:#475467; line-height:1.9; font-size:16px; }
    .ux-card-grid { display:grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap:14px; margin: 14px 0 24px; }
    .ux-card {
        background:#fff; border:1px solid #E1E8F3; border-radius:20px; padding:18px 18px;
        box-shadow: 0 16px 36px rgba(16,24,40,.055); transition: all .18s ease-in-out;
        min-height:132px;
    }
    .ux-card:hover { transform: translateY(-2px); box-shadow: 0 20px 46px rgba(23,71,158,.11); }
    .ux-card-title { font-weight:900; color:#0B2E63; font-size:17px; margin-bottom:8px; }
    .ux-card-text { color:#475467; line-height:1.8; font-size:14.5px; }
    .required-badge, .optional-badge, .enhance-badge {
        display:inline-block; border-radius:999px; padding:4px 10px; font-weight:800; font-size:12px; margin-bottom:8px;
    }
    .required-badge { background:#FFF1F2; color:#B42318; border:1px solid #FECDD3; }
    .optional-badge { background:#F2F4F7; color:#475467; border:1px solid #EAECF0; }
    .enhance-badge { background:#FFFAEB; color:#B54708; border:1px solid #FEDF89; }
    .readiness-strip { display:grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap:14px; margin:14px 0 20px; }
    .readiness-item { background:#fff; border:1px solid #E6EAF0; border-radius:18px; padding:16px; box-shadow:0 12px 30px rgba(16,24,40,.045); }
    .readiness-item strong { color:#17479E; font-size:18px; }
    .wazen-action-box {
        background: linear-gradient(135deg,#0B2E63,#17479E); color:#fff; border-radius:22px;
        padding:22px 24px; box-shadow: 0 22px 55px rgba(23,71,158,.22); margin:18px 0;
    }
    .wazen-action-box h3 { color:#fff !important; margin:0 0 8px; font-size:22px; }
    .wazen-action-box p { color:#EEF5FF; line-height:1.9; margin:0; }
    @media(max-width: 1000px){ .ux-card-grid, .readiness-strip{ grid-template-columns: 1fr; } }

    .file-request-card {
        background:#FFFFFF; border:1px solid #DFE7F3; border-right:6px solid #FAA61A;
        border-radius:18px; padding:16px 18px; margin:14px 0 8px;
        box-shadow:0 14px 34px rgba(16,24,40,.055);
    }
    .file-request-domain {
        display:inline-block; background:#F3F7FF; color:#17479E; border:1px solid #C8D8F5;
        border-radius:999px; padding:4px 12px; font-weight:900; font-size:12px; margin-bottom:8px;
    }
    .file-request-title { color:#0B2E63; font-size:18px; font-weight:900; margin-bottom:6px; }
    .file-request-text { color:#475467; line-height:1.8; font-size:14.5px; }
    .cfo-brief-pro {
        background:linear-gradient(135deg,#FFFFFF 0%,#F7FAFF 100%); border:1px solid #D9E6F8;
        border-radius:24px; padding:24px 26px; box-shadow:0 20px 56px rgba(23,71,158,.10);
        margin:18px 0 24px; border-right:7px solid #17479E;
    }
    .cfo-brief-pro h3 { color:#0B2E63 !important; font-size:24px; font-weight:950; margin:0 0 12px; }
    .cfo-brief-pro p { color:#1F2937; line-height:2; font-size:16px; margin:8px 0; }
    .cfo-brief-pro .danger { color:#B42318; font-weight:900; }
    .cfo-brief-pro .ok { color:#067647; font-weight:900; }
    .cfo-brief-pro .focus { color:#17479E; font-weight:900; }


    /* V12.8 decision-first UX */
    .v128-sector-panel {
        background: radial-gradient(circle at 4% 10%, rgba(250,166,26,.16), transparent 24%),
                    linear-gradient(135deg,#081E42 0%,#17479E 70%,#245DBE 100%);
        border-radius: 28px;
        padding: 28px 30px;
        color: white;
        margin: 18px 0 22px;
        box-shadow: 0 28px 80px rgba(23,71,158,.24);
        border: 1px solid rgba(255,255,255,.22);
    }
    .v128-sector-panel h3 { color:white !important; font-size:29px; margin:5px 0 8px; font-weight:950; }
    .v128-sector-panel p { color:#EAF2FF; line-height:1.9; font-size:16px; margin:0; }
    .v128-eyebrow { color:#FAA61A; font-weight:950; letter-spacing:.3px; font-size:13px; text-transform:uppercase; }
    .v128-badges { display:flex; gap:8px; flex-wrap:wrap; margin-top:15px; }
    .v128-badge { display:inline-block; border-radius:999px; padding:6px 12px; font-weight:900; font-size:12px; }
    .v128-badge.blue { background:rgba(255,255,255,.15); color:#fff; border:1px solid rgba(255,255,255,.24); }
    .v128-badge.orange { background:#FFF1D6; color:#8A4B00; border:1px solid #FFD891; }
    .v128-badge.gray { background:#F2F4F7; color:#344054; border:1px solid #EAECF0; }

    .v128-command-center {
        background: linear-gradient(135deg,#FFFFFF 0%, #F7FAFF 56%, #EDF5FF 100%);
        border:1px solid #D7E5F8;
        border-radius:30px;
        padding:28px 30px;
        margin:8px 0 28px;
        box-shadow:0 26px 70px rgba(23,71,158,.13);
        border-right:8px solid #FAA61A;
    }
    .v128-command-center h2 { color:#0B2E63 !important; font-weight:950; font-size:30px; margin:8px 0 10px; line-height:1.35; }
    .v128-command-center p { color:#344054; line-height:1.95; font-size:16px; margin:0 0 12px; }
    .v128-command-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px; margin:18px 0; }
    .v128-command-grid div { background:#fff; border:1px solid #E3EAF6; border-radius:20px; padding:16px; box-shadow:0 12px 30px rgba(16,24,40,.05); }
    .v128-command-grid span { display:block; color:#667085; font-weight:800; font-size:13px; }
    .v128-command-grid strong { display:block; color:#17479E; font-size:28px; line-height:1.2; margin:8px 0 2px; direction:ltr; text-align:left; }
    .v128-command-grid em { color:#475467; font-style:normal; font-size:13px; }
    .v128-next-action { background:#FFF7E8; border:1px solid #FFDD9A; border-radius:16px; padding:12px 14px; color:#7A4B00 !important; }
    .v128-mini-card { background:#fff; border:1px solid #E3EAF6; border-radius:22px; padding:18px 20px; box-shadow:0 16px 40px rgba(16,24,40,.055); min-height:118px; margin-bottom:14px; }
    .v128-mini-card div { color:#667085; font-weight:900; font-size:14px; }
    .v128-mini-card strong { display:block; color:#17479E; font-size:34px; margin:8px 0 2px; font-weight:950; }
    .v128-mini-card span { color:#475467; font-size:13px; }
    @media(max-width: 1000px){ .v128-command-grid{ grid-template-columns:1fr; } }



    /* V13.1 - decision-first analysis pages */
    .v131-audit-card {
        background:#fff; border:1px solid #E3EAF6; border-radius:22px;
        padding:18px 20px; min-height:135px; box-shadow:0 16px 42px rgba(16,24,40,.055);
        border-right:6px solid #17479E; margin-bottom:16px;
    }
    .v131-audit-card span { display:block; color:#667085; font-weight:900; font-size:14px; margin-bottom:8px; }
    .v131-audit-card strong { display:block; color:#17479E; font-weight:950; font-size:31px; margin-bottom:8px; }
    .v131-audit-card em { display:block; color:#475467; font-style:normal; line-height:1.7; font-size:13.5px; }
    .v131-decision-card {
        display:flex; gap:14px; align-items:flex-start; background:#fff; border:1px solid #E3EAF6;
        border-radius:22px; padding:18px 18px; margin:10px 0 14px; min-height:170px;
        box-shadow:0 18px 48px rgba(16,24,40,.06); position:relative; overflow:hidden;
    }
    .v131-decision-card:before { content:""; position:absolute; right:0; top:0; height:100%; width:7px; background:#FAA61A; }
    .v131-decision-card.danger:before { background:#D92D20; }
    .v131-decision-card.warning:before { background:#FAA61A; }
    .v131-decision-card.ok:before { background:#12B76A; }
    .v131-decision-icon {
        width:48px; min-width:48px; height:48px; border-radius:16px; display:flex; align-items:center; justify-content:center;
        background:#F3F7FF; color:#17479E; font-size:24px; font-weight:900; margin-right:8px;
    }
    .v131-decision-title { color:#0B2E63; font-size:18px; font-weight:950; margin-bottom:6px; }
    .v131-decision-verdict { color:#111827; font-size:16px; font-weight:900; margin-bottom:8px; }
    .v131-decision-card.danger .v131-decision-verdict { color:#B42318; }
    .v131-decision-card.warning .v131-decision-verdict { color:#B54708; }
    .v131-decision-card.ok .v131-decision-verdict { color:#067647; }
    .v131-decision-evidence, .v131-decision-action { color:#475467; line-height:1.75; font-size:14px; margin-top:5px; }
    .v131-waterfall {
        display:grid; grid-template-columns: repeat(5, minmax(0,1fr)); gap:12px; margin:14px 0 18px;
    }
    .wf-step {
        background:#fff; border:1px solid #E3EAF6; border-radius:22px; padding:18px 16px;
        box-shadow:0 16px 42px rgba(16,24,40,.055); min-height:145px; position:relative; overflow:hidden;
    }
    .wf-step:before { content:""; position:absolute; right:0; top:0; width:7px; height:100%; background:#FAA61A; }
    .wf-step.base:before { background:#17479E; }
    .wf-step.cost:before { background:#FAA61A; }
    .wf-step.danger:before { background:#D92D20; }
    .wf-step.ok:before { background:#12B76A; }
    .wf-step span { display:block; color:#344054; font-weight:900; font-size:15px; min-height:36px; }
    .wf-step strong { display:block; direction:ltr; color:#17479E; font-size:34px; font-weight:950; margin-top:10px; }
    .wf-step.danger strong { color:#B42318; }
    .wf-step.ok strong { color:#067647; }
    .wf-step em { color:#667085; font-style:normal; font-size:13px; }
    @media(max-width: 1050px){ .v131-waterfall{ grid-template-columns:1fr; } }



    /* V13.2 - refined three pages UX */
    .v132-summary-tile {
        background:#fff; border:1px solid #E3EAF6; border-radius:24px; padding:20px 22px;
        min-height:155px; box-shadow:0 18px 50px rgba(16,24,40,.065); position:relative; overflow:hidden; margin-bottom:16px;
        display:flex; gap:15px; align-items:flex-start;
    }
    .v132-summary-tile:before { content:""; position:absolute; right:0; top:0; width:7px; height:100%; background:#CBD5E1; }
    .v132-summary-tile.ok:before { background:#12B76A; }
    .v132-summary-tile.warning:before { background:#FAA61A; }
    .v132-summary-tile.danger:before { background:#D92D20; }
    .v132-summary-icon { width:46px; min-width:46px; height:46px; border-radius:16px; background:#F3F7FF; display:flex; align-items:center; justify-content:center; font-size:22px; }
    .v132-summary-content span { display:block; color:#667085; font-weight:900; font-size:14px; margin-bottom:8px; }
    .v132-summary-content strong { display:block; color:#17479E; font-weight:950; font-size:30px; line-height:1.2; margin-bottom:8px; }
    .v132-summary-content em { display:block; color:#475467; font-style:normal; font-size:13.5px; line-height:1.75; }
    .v132-summary-tile.danger strong { color:#B42318; }
    .v132-summary-tile.warning strong { color:#B54708; }
    .v132-summary-tile.ok strong { color:#067647; }

    .v132-formula-card {
        background:#fff; border:1px solid #E3EAF6; border-radius:22px; padding:18px 20px; margin:14px 0 18px;
        box-shadow:0 16px 42px rgba(16,24,40,.055); border-right:7px solid #CBD5E1;
    }
    .v132-formula-card.ok { border-right-color:#12B76A; background:linear-gradient(90deg, rgba(236,253,243,.75), #fff 38%); }
    .v132-formula-card.warning { border-right-color:#FAA61A; background:linear-gradient(90deg, rgba(255,247,232,.78), #fff 38%); }
    .v132-formula-card.danger { border-right-color:#D92D20; background:linear-gradient(90deg, rgba(254,243,242,.76), #fff 38%); }
    .v132-formula-card div { display:inline-block; min-width:260px; margin:0 0 10px 18px; vertical-align:top; }
    .v132-formula-card span { display:block; color:#667085; font-size:13px; font-weight:900; margin-bottom:6px; }
    .v132-formula-card strong { display:block; color:#17479E; font-size:22px; font-weight:950; }
    .v132-formula-card p { color:#475467; line-height:1.85; margin:6px 0 0; }

    .v132-table-card {
        background:#fff; border:1px solid #D8E4F5; border-radius:24px; padding:0; margin:14px 0 20px;
        box-shadow:0 18px 55px rgba(16,24,40,.07); overflow:hidden;
    }
    .v132-table-title { padding:15px 20px; color:#0B2E63; font-size:16px; font-weight:950; border-bottom:1px solid #E8EEF8; background:linear-gradient(90deg,#F8FBFF,#FFFFFF); }
    .v132-table-scroll { overflow-x:auto; max-height:560px; }
    table.v132-table { width:100%; border-collapse:separate; border-spacing:0; direction:rtl; font-size:13.5px; }
    .v132-table th { position:sticky; top:0; z-index:1; background:#17479E; color:#fff; font-weight:950; text-align:right; padding:14px 15px; border-bottom:1px solid #123A82; white-space:nowrap; }
    .v132-table td { padding:14px 15px; color:#1D2939; border-bottom:1px solid #EEF2F7; vertical-align:top; line-height:1.85; background:#fff; }
    .v132-table tr:nth-child(even) td { background:#FBFDFF; }
    .v132-table tr:hover td { background:#F3F7FF; }
    .v132-table td:nth-child(1) { font-weight:900; color:#0B2E63; }
    .v132-table td:nth-child(2), .v132-table td:nth-child(3) { font-weight:850; color:#17479E; }
    .v132-badge { display:inline-block; border-radius:999px; padding:5px 11px; font-size:12px; font-weight:900; white-space:nowrap; }
    .v132-badge.ok { background:#ECFDF3; color:#067647; border:1px solid #ABEFC6; }
    .v132-badge.warning { background:#FFFAEB; color:#B54708; border:1px solid #FEDF89; }
    .v132-badge.danger { background:#FEF3F2; color:#B42318; border:1px solid #FECDCA; }
    .v132-badge.neutral { background:#F2F4F7; color:#475467; border:1px solid #EAECF0; }



    /* V13.6 decision rationale and comparison cards */
    .v131-decision-benchmark, .v131-decision-basis {
        color:#344054; line-height:1.75; font-size:13.5px; margin-top:5px;
        background:#F8FBFF; border:1px solid #E6EEF9; border-radius:12px; padding:7px 10px;
    }
    .v131-decision-basis { background:#FFFCF5; border-color:#FFE6B8; }
    .v136-method-card {
        background:#fff; border:1px solid #E3EAF6; border-radius:22px; padding:18px 20px;
        margin:14px 0 20px; box-shadow:0 16px 42px rgba(16,24,40,.055); border-right:7px solid #CBD5E1;
    }
    .v136-method-card.ok { border-right-color:#12B76A; }
    .v136-method-card.warning { border-right-color:#FAA61A; }
    .v136-method-card.danger { border-right-color:#D92D20; }
    .v136-method-title { color:#0B2E63; font-size:18px; font-weight:950; margin-bottom:6px; }
    .v136-method-status { display:inline-block; color:#17479E; background:#F3F7FF; border:1px solid #C8D8F5; border-radius:999px; padding:5px 12px; font-weight:900; margin-bottom:8px; }
    .v136-method-card p { color:#475467; line-height:1.9; margin:8px 0 0; }
    .v136-analysis-card {
        background:#fff; border:1px solid #E3EAF6; border-radius:22px; padding:18px 20px; min-height:130px;
        margin:10px 0 16px; box-shadow:0 16px 42px rgba(16,24,40,.055); border-right:7px solid #CBD5E1;
    }
    .v136-analysis-card.ok { border-right-color:#12B76A; }
    .v136-analysis-card.warning { border-right-color:#FAA61A; }
    .v136-analysis-card.danger { border-right-color:#D92D20; }
    .v136-analysis-card span { display:block; color:#667085; font-weight:900; font-size:14px; margin-bottom:8px; }
    .v136-analysis-card strong { display:block; color:#17479E; font-weight:950; font-size:28px; line-height:1.25; margin-bottom:8px; }
    .v136-analysis-card.ok strong { color:#067647; }
    .v136-analysis-card.warning strong { color:#B54708; }
    .v136-analysis-card.danger strong { color:#B42318; }
    .v136-analysis-card em { display:block; color:#475467; font-style:normal; line-height:1.7; font-size:13.5px; }

    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
