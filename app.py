import io
import math
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sklearn.linear_model import LinearRegression

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

# ============================================================
# WAZEN CFO INTELLIGENCE AGENT - V3
# ============================================================

WAZEN_BLUE = "#17479E"
WAZEN_ORANGE = "#FAA61A"
TEXT = "#1F2937"
MUTED = "#6B7280"
BG = "#F7F9FC"
CARD = "#FFFFFF"
BORDER = "#E5E7EB"
RISK = "#DC2626"
WATCH = "#D97706"
HEALTHY = "#059669"

st.set_page_config(
    page_title="Wazen CFO Intelligence Agent",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
}}

.main {{
    background: {BG};
}}

.block-container {{
    padding-top: 2.1rem;
    padding-bottom: 3rem;
    max-width: 1280px;
}}

.hero {{
    background: linear-gradient(135deg, rgba(23,71,158,0.10), rgba(250,166,26,0.10));
    border: 1px solid {BORDER};
    border-radius: 28px;
    padding: 30px 34px;
    margin-bottom: 24px;
    box-shadow: 0 10px 35px rgba(15, 23, 42, 0.06);
}}

.hero-title {{
    font-size: 38px;
    font-weight: 800;
    letter-spacing: -0.04em;
    color: {TEXT};
    margin: 0;
}}

.hero-subtitle {{
    color: {MUTED};
    margin-top: 8px;
    font-size: 15px;
}}

.section-title {{
    font-size: 24px;
    font-weight: 800;
    color: {TEXT};
    margin: 28px 0 12px 0;
}}

.card {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 22px;
    padding: 20px 22px;
    box-shadow: 0 10px 30px rgba(15, 23, 42, 0.045);
    min-height: 116px;
}}

.kpi-label {{
    color: {MUTED};
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .04em;
}}

.kpi-value {{
    color: {TEXT};
    font-size: 28px;
    font-weight: 800;
    margin-top: 6px;
}}

.kpi-note {{
    color: {MUTED};
    font-size: 12px;
    margin-top: 4px;
}}

.badge-healthy {{
    background: rgba(5,150,105,.11);
    color: {HEALTHY};
    border: 1px solid rgba(5,150,105,.22);
    padding: 5px 10px;
    border-radius: 999px;
    font-weight: 700;
    font-size: 12px;
}}
.badge-watch {{
    background: rgba(217,119,6,.12);
    color: {WATCH};
    border: 1px solid rgba(217,119,6,.22);
    padding: 5px 10px;
    border-radius: 999px;
    font-weight: 700;
    font-size: 12px;
}}
.badge-risk {{
    background: rgba(220,38,38,.10);
    color: {RISK};
    border: 1px solid rgba(220,38,38,.22);
    padding: 5px 10px;
    border-radius: 999px;
    font-weight: 700;
    font-size: 12px;
}}

.sidebar-logo {{
    background: {WAZEN_BLUE};
    color: white;
    font-weight: 800;
    font-size: 30px;
    text-align: center;
    border-radius: 16px;
    padding: 18px;
    letter-spacing: .10em;
    margin-bottom: 20px;
}}

.small-muted {{ color: {MUTED}; font-size: 13px; }}

[data-testid="stMetricValue"] {{
    font-size: 26px;
}}

.stTabs [data-baseweb="tab-list"] {{ gap: 10px; }}
.stTabs [data-baseweb="tab"] {{
    border-radius: 999px;
    background: white;
    border: 1px solid {BORDER};
    padding: 10px 16px;
}}
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# Helper formatting
# ============================================================

def fmt_money(x):
    try:
        x = float(x)
    except Exception:
        return "-"
    if abs(x) >= 1_000_000:
        return f"{x/1_000_000:,.2f}M"
    return f"{x:,.0f}"


def fmt_pct(x):
    try:
        return f"{float(x):.1%}"
    except Exception:
        return "-"


def safe_div(a, b):
    try:
        if b == 0 or pd.isna(b):
            return 0
        return a / b
    except Exception:
        return 0


def normalize_columns(df):
    df = df.copy()
    df.columns = [str(c).strip().replace("\n", " ") for c in df.columns]
    return df


def find_column(df, possible_names):
    for col in df.columns:
        clean_col = str(col).strip().lower()
        for name in possible_names:
            if name.lower() in clean_col:
                return col
    return None


def detect_columns(df):
    df = normalize_columns(df)
    return {
        "month": find_column(df, ["month", "date", "period", "الشهر", "التاريخ", "الفترة"]),
        "revenue": find_column(df, ["revenue", "sales", "income", "الإيرادات", "ايرادات", "المبيعات", "الدخل"]),
        "cogs": find_column(df, ["cogs", "cost of sales", "direct cost", "تكلفة المبيعات", "تكلفة", "تكلفة مباشرة"]),
        "payroll": find_column(df, ["payroll", "salary", "salaries", "رواتب", "الأجور", "اجور"]),
        "marketing": find_column(df, ["marketing", "ads", "advertising", "تسويق", "إعلانات", "اعلان"]),
        "opex": find_column(df, ["opex", "operating expenses", "admin", "general", "مصاريف", "إدارية", "تشغيلية"]),
        "cash": find_column(df, ["cash", "bank", "النقد", "البنك", "رصيد"]),
        "clients": find_column(df, ["clients", "customers", "العملاء", "عدد العملاء"]),
        "depreciation": find_column(df, ["depreciation", "إهلاك", "اهلاك"]),
        "vat_input": find_column(df, ["vat input", "input vat", "ضريبة مدخلات", "مدخلات"]),
        "vat_output": find_column(df, ["vat output", "output vat", "ضريبة مخرجات", "مخرجات"]),
    }


def to_number_series(df, col):
    if not col or col not in df.columns:
        return pd.Series([0] * len(df), index=df.index, dtype="float64")
    return pd.to_numeric(df[col], errors="coerce").fillna(0).astype(float)


def prepare_data(df, cols):
    data = normalize_columns(df)
    if cols["month"]:
        data["Month"] = data[cols["month"]].astype(str)
    else:
        data["Month"] = [f"Month {i+1}" for i in range(len(data))]

    data["Revenue"] = to_number_series(data, cols["revenue"])
    data["COGS"] = to_number_series(data, cols["cogs"])
    data["Payroll"] = to_number_series(data, cols["payroll"])
    data["Marketing"] = to_number_series(data, cols["marketing"])
    data["Opex"] = to_number_series(data, cols["opex"])
    data["Cash"] = to_number_series(data, cols["cash"])
    data["Clients"] = to_number_series(data, cols["clients"])
    data["Depreciation"] = to_number_series(data, cols["depreciation"])
    data["VAT Input"] = to_number_series(data, cols["vat_input"])
    data["VAT Output"] = to_number_series(data, cols["vat_output"])

    # Avoid treating a summary row as a monthly point when source includes Total / Latest
    data["_is_total_row"] = data["Month"].str.lower().str.contains("total|latest|الإجمالي|اجمالي|المجموع", regex=True, na=False)
    monthly = data[~data["_is_total_row"]].copy()
    if monthly.empty:
        monthly = data.copy()

    monthly["Gross Profit"] = monthly["Revenue"] - monthly["COGS"]
    monthly["Variable Cost"] = monthly["COGS"]
    monthly["Fixed Costs"] = monthly["Payroll"] + monthly["Marketing"] + monthly["Opex"]
    monthly["EBITDA"] = monthly["Gross Profit"] - monthly["Fixed Costs"]
    monthly["EBIT"] = monthly["EBITDA"] - monthly["Depreciation"]
    monthly["Net Profit"] = monthly["EBIT"]

    monthly["Gross Margin %"] = monthly.apply(lambda r: safe_div(r["Gross Profit"], r["Revenue"]), axis=1)
    monthly["EBITDA Margin %"] = monthly.apply(lambda r: safe_div(r["EBITDA"], r["Revenue"]), axis=1)
    monthly["Net Margin %"] = monthly.apply(lambda r: safe_div(r["Net Profit"], r["Revenue"]), axis=1)
    monthly["Payroll Ratio %"] = monthly.apply(lambda r: safe_div(r["Payroll"], r["Revenue"]), axis=1)
    monthly["Marketing Ratio %"] = monthly.apply(lambda r: safe_div(r["Marketing"], r["Revenue"]), axis=1)
    monthly["Opex Ratio %"] = monthly.apply(lambda r: safe_div(r["Opex"], r["Revenue"]), axis=1)
    monthly["ARPU"] = monthly.apply(lambda r: safe_div(r["Revenue"], r["Clients"]), axis=1)
    monthly["VAT Payable"] = monthly["VAT Output"] - monthly["VAT Input"]

    return monthly.reset_index(drop=True)


def aggregate_metrics(monthly):
    revenue = monthly["Revenue"].sum()
    cogs = monthly["COGS"].sum()
    gross_profit = monthly["Gross Profit"].sum()
    fixed = monthly["Fixed Costs"].sum()
    ebitda = monthly["EBITDA"].sum()
    depreciation = monthly["Depreciation"].sum()
    ebit = monthly["EBIT"].sum()
    net = monthly["Net Profit"].sum()
    cash = monthly["Cash"].iloc[-1] if "Cash" in monthly.columns and len(monthly) else 0
    clients = monthly["Clients"].iloc[-1] if "Clients" in monthly.columns and len(monthly) else 0
    avg_monthly_burn = max(0, -monthly["Net Profit"].mean()) if len(monthly) else 0
    runway = safe_div(cash, avg_monthly_burn) if avg_monthly_burn else np.inf
    variable_ratio = safe_div(cogs, revenue)
    cm_ratio = 1 - variable_ratio
    breakeven = safe_div(fixed, cm_ratio) if cm_ratio > 0 else 0
    gap = revenue - breakeven

    return {
        "Revenue": revenue,
        "COGS": cogs,
        "Gross Profit": gross_profit,
        "Fixed Costs": fixed,
        "EBITDA": ebitda,
        "EBIT": ebit,
        "Net Profit": net,
        "Cash": cash,
        "Clients": clients,
        "Gross Margin %": safe_div(gross_profit, revenue),
        "EBITDA Margin %": safe_div(ebitda, revenue),
        "EBIT Margin %": safe_div(ebit, revenue),
        "Net Margin %": safe_div(net, revenue),
        "Payroll Ratio %": safe_div(monthly["Payroll"].sum(), revenue),
        "Marketing Ratio %": safe_div(monthly["Marketing"].sum(), revenue),
        "Opex Ratio %": safe_div(monthly["Opex"].sum(), revenue),
        "ARPU": safe_div(revenue, monthly["Clients"].replace(0, np.nan).mean() if len(monthly) else 0),
        "Variable Cost Ratio": variable_ratio,
        "Contribution Margin Ratio": cm_ratio,
        "Break-even Revenue": breakeven,
        "Break-even Gap": gap,
        "Cash Runway": runway,
        "VAT Payable": monthly["VAT Payable"].sum(),
    }


BENCHMARKS = {
    "خدمات عامة": {
        "Gross Margin %": (0.30, ">="),
        "EBITDA Margin %": (0.12, ">="),
        "Net Margin %": (0.08, ">="),
        "Payroll Ratio %": (0.30, "<="),
        "Marketing Ratio %": (0.10, "<="),
        "Opex Ratio %": (0.18, "<="),
        "Cash Runway": (3.0, ">="),
    },
    "SaaS / خدمات تقنية": {
        "Gross Margin %": (0.65, ">="),
        "EBITDA Margin %": (0.15, ">="),
        "Net Margin %": (0.10, ">="),
        "Payroll Ratio %": (0.35, "<="),
        "Marketing Ratio %": (0.25, "<="),
        "Opex Ratio %": (0.25, "<="),
        "Cash Runway": (6.0, ">="),
    },
    "تأجير ومعدات": {
        "Gross Margin %": (0.35, ">="),
        "EBITDA Margin %": (0.20, ">="),
        "Net Margin %": (0.08, ">="),
        "Payroll Ratio %": (0.20, "<="),
        "Marketing Ratio %": (0.08, "<="),
        "Opex Ratio %": (0.15, "<="),
        "Cash Runway": (3.0, ">="),
    },
    "تجارة": {
        "Gross Margin %": (0.25, ">="),
        "EBITDA Margin %": (0.08, ">="),
        "Net Margin %": (0.04, ">="),
        "Payroll Ratio %": (0.15, "<="),
        "Marketing Ratio %": (0.07, "<="),
        "Opex Ratio %": (0.12, "<="),
        "Cash Runway": (2.0, ">="),
    },
}


def assess_benchmarks(metrics, industry):
    rows = []
    for metric, (benchmark, rule) in BENCHMARKS[industry].items():
        actual = metrics.get(metric, 0)
        if rule == ">=":
            status = "Healthy" if actual >= benchmark else ("Watch" if actual >= benchmark * 0.75 else "Risk")
        else:
            status = "Healthy" if actual <= benchmark else ("Watch" if actual <= benchmark * 1.25 else "Risk")
        rows.append({
            "Metric": metric,
            "Actual": actual,
            "Benchmark": benchmark,
            "Rule": rule,
            "Status": status,
            "Gap": actual - benchmark,
        })
    return pd.DataFrame(rows)


def score_company(benchmarks):
    weights = {
        "Gross Margin %": 18,
        "EBITDA Margin %": 20,
        "Net Margin %": 20,
        "Payroll Ratio %": 12,
        "Marketing Ratio %": 8,
        "Opex Ratio %": 10,
        "Cash Runway": 12,
    }
    score = 0
    for _, r in benchmarks.iterrows():
        w = weights.get(r["Metric"], 10)
        if r["Status"] == "Healthy":
            score += w
        elif r["Status"] == "Watch":
            score += w * 0.55
        else:
            score += w * 0.15
    return min(100, round(score, 1))


def generate_recommendations(metrics, benchmarks):
    recs = []
    severity_map = {"Risk": 3, "Watch": 2, "Healthy": 1}
    for _, r in benchmarks.iterrows():
        status = r["Status"]
        if status == "Healthy":
            continue
        metric = r["Metric"]
        if metric == "Net Margin %":
            recs.append((severity_map[status], "الربحية الصافية", "صافي الربح أقل من معيار السلامة. يجب فصل أثر الإهلاك/التكاليف غير النقدية عن الأداء التشغيلي ومراجعة التسعير والتكاليف الثابتة."))
        elif metric == "EBITDA Margin %":
            recs.append((severity_map[status], "الكفاءة التشغيلية", "هامش EBITDA دون المستوى المستهدف. راجعي تكلفة التشغيل، الطاقة غير المستغلة، وشروط العقود مع العملاء."))
        elif metric == "Gross Margin %":
            recs.append((severity_map[status], "هامش الربح الإجمالي", "الهامش الإجمالي منخفض. يلزم إعادة تقييم تكلفة الخدمة/المبيعات والتأكد من أن الأسعار تغطي التكلفة المباشرة."))
        elif metric == "Payroll Ratio %":
            recs.append((severity_map[status], "عبء الرواتب", "نسبة الرواتب إلى الإيرادات مرتفعة. راجعي الإنتاجية لكل موظف وربط التوظيف بالنمو الفعلي في الإيرادات."))
        elif metric == "Marketing Ratio %":
            recs.append((severity_map[status], "كفاءة التسويق", "الإنفاق التسويقي مرتفع مقارنة بالإيرادات. يلزم قياس CAC، معدل التحويل، وفترة استرداد تكلفة العميل."))
        elif metric == "Cash Runway":
            recs.append((severity_map[status], "السيولة", "مدى السيولة أقل من معيار السلامة. يجب وضع خطة تحصيل وتمويل قصير الأجل وخفض المصاريف غير الحرجة."))
        else:
            recs.append((severity_map[status], metric, f"المؤشر {metric} يحتاج متابعة لأنه في حالة {status}."))

    if metrics["Break-even Gap"] < 0:
        recs.append((3, "نقطة التعادل", f"الإيرادات أقل من نقطة التعادل بفجوة تقارب {fmt_money(abs(metrics['Break-even Gap']))}. الأولوية: رفع الإيراد أو خفض التكاليف الثابتة أو تحسين الهامش."))
    else:
        recs.append((1, "نقطة التعادل", "الإيرادات أعلى من نقطة التعادل، لكن يجب مراقبة الهامش لأن أي ارتفاع في التكاليف الثابتة قد يضغط الربحية."))

    recs = sorted(recs, reverse=True, key=lambda x: x[0])
    return pd.DataFrame([{"Priority": p, "Area": a, "Recommendation": t} for p, a, t in recs])


def forecast_scenarios(monthly, months_ahead=6):
    if len(monthly) < 2:
        return pd.DataFrame()
    x = np.arange(len(monthly)).reshape(-1, 1)
    y = monthly["Revenue"].values.reshape(-1, 1)
    model = LinearRegression().fit(x, y)
    future_x = np.arange(len(monthly), len(monthly) + months_ahead).reshape(-1, 1)
    base_rev = np.maximum(model.predict(future_x).flatten(), 0)

    avg_cogs_ratio = safe_div(monthly["COGS"].sum(), monthly["Revenue"].sum())
    avg_payroll_ratio = safe_div(monthly["Payroll"].sum(), monthly["Revenue"].sum())
    avg_marketing_ratio = safe_div(monthly["Marketing"].sum(), monthly["Revenue"].sum())
    avg_opex_ratio = safe_div(monthly["Opex"].sum(), monthly["Revenue"].sum())

    rows = []
    scenarios = {
        "Base": 1.00,
        "Optimistic": 1.15,
        "Pessimistic": 0.85,
    }
    for i in range(months_ahead):
        for scenario, mult in scenarios.items():
            rev = base_rev[i] * mult
            cogs = rev * avg_cogs_ratio
            payroll = rev * avg_payroll_ratio
            marketing = rev * avg_marketing_ratio
            opex = rev * avg_opex_ratio
            gp = rev - cogs
            ebitda = gp - payroll - marketing - opex
            rows.append({
                "Month": f"Month +{i+1}",
                "Scenario": scenario,
                "Revenue": rev,
                "COGS": cogs,
                "Gross Profit": gp,
                "Payroll": payroll,
                "Marketing": marketing,
                "Opex": opex,
                "EBITDA": ebitda,
                "EBITDA Margin %": safe_div(ebitda, rev),
            })
    return pd.DataFrame(rows)


def fig_line(df, x, y, title, percent=False):
    fig = go.Figure()
    if isinstance(y, list):
        for col in y:
            fig.add_trace(go.Scatter(x=df[x], y=df[col], mode="lines+markers", name=col))
    else:
        fig.add_trace(go.Scatter(x=df[x], y=df[y], mode="lines+markers", name=y, line=dict(color=WAZEN_BLUE, width=3)))
    fig.update_layout(
        title=title,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=45, b=10),
        height=360,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#E5E7EB", tickformat=".0%" if percent else None)
    return fig


def fig_bar_be(metrics):
    fig = go.Figure()
    fig.add_trace(go.Bar(x=["Actual Revenue"], y=[metrics["Revenue"]], name="Revenue", marker_color=WAZEN_BLUE))
    fig.add_trace(go.Bar(x=["Break-even Revenue"], y=[metrics["Break-even Revenue"]], name="Break-even", marker_color=WAZEN_ORANGE))
    fig.update_layout(
        title="Actual Revenue vs Break-even",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=360,
        margin=dict(l=10, r=10, t=45, b=10),
    )
    fig.update_yaxes(gridcolor="#E5E7EB")
    return fig


def ai_cfo_report(metrics, benchmarks, recommendations, forecast):
    api_key = st.secrets.get("OPENAI_API_KEY", None)
    if not api_key or OpenAI is None:
        return "لم يتم تفعيل مفتاح OpenAI. يمكن استخدام التقرير القاعدي والتوصيات الحالية، أو إضافة المفتاح لتوليد تعليق CFO أكثر عمقاً."
    client = OpenAI(api_key=api_key)
    prompt = f"""
أنت CFO محترف ومستشار مالي تنفيذي. اكتب تقريراً عربياً احترافياً غير عام اعتماداً على البيانات التالية.
ركز على: جودة الربحية، نقطة التعادل، المخاطر، التوصيات، والأسئلة الإدارية.
لا تكرر الأرقام فقط. فسّر معنى الأرقام.

Metrics:
{pd.Series(metrics).to_string()}

Benchmarks:
{benchmarks.to_string(index=False)}

Recommendations:
{recommendations.to_string(index=False)}

Forecast:
{forecast.head(18).to_string(index=False) if not forecast.empty else 'No forecast'}
"""
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a senior CFO intelligence agent. Arabic output only."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.25,
    )
    return res.choices[0].message.content


def create_excel(monthly, metrics, benchmarks, breakeven_df, forecast, recommendations, ai_report_text):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book
        fmt_title = workbook.add_format({"bold": True, "font_size": 20, "font_color": WAZEN_BLUE})
        fmt_header = workbook.add_format({"bold": True, "bg_color": WAZEN_BLUE, "font_color": "white", "border": 1})
        fmt_subheader = workbook.add_format({"bold": True, "bg_color": "#EAF1FF", "font_color": TEXT, "border": 1})
        fmt_num = workbook.add_format({"num_format": "#,##0", "border": 1})
        fmt_pct = workbook.add_format({"num_format": "0.0%", "border": 1})
        fmt_text = workbook.add_format({"text_wrap": True, "valign": "top", "border": 1})
        fmt_note = workbook.add_format({"text_wrap": True, "valign": "top", "font_color": TEXT})
        fmt_risk = workbook.add_format({"bg_color": "#FEE2E2", "font_color": RISK, "bold": True, "border": 1})
        fmt_watch = workbook.add_format({"bg_color": "#FEF3C7", "font_color": WATCH, "bold": True, "border": 1})
        fmt_ok = workbook.add_format({"bg_color": "#DCFCE7", "font_color": HEALTHY, "bold": True, "border": 1})

        # Dashboard
        ws = workbook.add_worksheet("Dashboard")
        writer.sheets["Dashboard"] = ws
        ws.hide_gridlines(2)
        ws.set_column("A:A", 24)
        ws.set_column("B:D", 20)
        ws.write("A1", "Wazen CFO Intelligence Report", fmt_title)
        ws.write("A2", f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", fmt_note)
        kpis = [
            ("Revenue", metrics["Revenue"]),
            ("Gross Margin %", metrics["Gross Margin %"]),
            ("EBITDA Margin %", metrics["EBITDA Margin %"]),
            ("Net Profit", metrics["Net Profit"]),
            ("Break-even Revenue", metrics["Break-even Revenue"]),
            ("Break-even Gap", metrics["Break-even Gap"]),
            ("Cash", metrics["Cash"]),
            ("Cash Runway", metrics["Cash Runway"] if np.isfinite(metrics["Cash Runway"]) else 999),
        ]
        row = 4
        ws.write(row, 0, "Executive KPIs", fmt_header)
        row += 1
        for name, value in kpis:
            ws.write(row, 0, name, fmt_subheader)
            if name.endswith("%"):
                ws.write_number(row, 1, value, fmt_pct)
            else:
                ws.write_number(row, 1, value, fmt_num)
            row += 1

        ws.write(row + 1, 0, "CFO Agent Commentary", fmt_header)
        ws.merge_range(row + 2, 0, row + 14, 3, ai_report_text or "", fmt_note)

        # Data sheets
        monthly.to_excel(writer, sheet_name="Monthly_Data", index=False)
        forecast.to_excel(writer, sheet_name="Forecast", index=False)
        benchmarks.to_excel(writer, sheet_name="Benchmarks", index=False)
        breakeven_df.to_excel(writer, sheet_name="Break_even", index=False)
        recommendations.to_excel(writer, sheet_name="Recommendations", index=False)

        for sheet_name in ["Monthly_Data", "Forecast", "Benchmarks", "Break_even", "Recommendations"]:
            ws2 = writer.sheets[sheet_name]
            ws2.freeze_panes(1, 0)
            ws2.hide_gridlines(2)
            df = {"Monthly_Data": monthly, "Forecast": forecast, "Benchmarks": benchmarks, "Break_even": breakeven_df, "Recommendations": recommendations}[sheet_name]
            for c, col in enumerate(df.columns):
                ws2.write(0, c, col, fmt_header)
                width = min(max(12, len(str(col)) + 4), 38)
                ws2.set_column(c, c, width)
            # Conditional status formatting
            if sheet_name == "Benchmarks" and "Status" in df.columns:
                status_col = list(df.columns).index("Status")
                for r in range(1, len(df) + 1):
                    status = str(df.iloc[r-1]["Status"])
                    cell_fmt = fmt_ok if status == "Healthy" else fmt_watch if status == "Watch" else fmt_risk
                    ws2.write(r, status_col, status, cell_fmt)

        # Add charts on Monthly_Data
        ws_m = writer.sheets["Monthly_Data"]
        if len(monthly) >= 2:
            chart = workbook.add_chart({"type": "line"})
            revenue_col = list(monthly.columns).index("Revenue")
            month_col = list(monthly.columns).index("Month")
            chart.add_series({
                "name": "Revenue",
                "categories": ["Monthly_Data", 1, month_col, len(monthly), month_col],
                "values": ["Monthly_Data", 1, revenue_col, len(monthly), revenue_col],
                "line": {"color": WAZEN_BLUE, "width": 2.5},
            })
            chart.set_title({"name": "Revenue Trend"})
            chart.set_legend({"none": True})
            ws_m.insert_chart("Z2", chart, {"x_scale": 1.3, "y_scale": 1.2})

    return output.getvalue()

# ============================================================
# Sidebar
# ============================================================
with st.sidebar:
    st.markdown('<div class="sidebar-logo">WAZEN</div>', unsafe_allow_html=True)
    st.markdown("### إعدادات التحليل")
    industry = st.selectbox("نوع النشاط / معيار المقارنة", list(BENCHMARKS.keys()), index=0)
    months_ahead = st.slider("عدد أشهر التوقع", min_value=3, max_value=12, value=6, step=1)
    st.divider()
    st.markdown("""
<div class="small-muted">
هذه النسخة تدعم ملفاً شهرياً مختصراً. للنتائج الرسمية يجب ربطها لاحقاً بميزان المراجعة، شجرة الحسابات، وحركة العملاء.
</div>
""", unsafe_allow_html=True)

# ============================================================
# Header
# ============================================================
st.markdown(
    """
<div class="hero">
    <div class="hero-title">📊 Wazen CFO Intelligence Agent</div>
    <div class="hero-subtitle">تحليل مالي تنفيذي، نسب سلامة، نقطة تعادل، توقعات، توصيات، وتصدير Excel احترافي.</div>
</div>
""",
    unsafe_allow_html=True,
)

uploaded = st.file_uploader("ارفعي ملف Excel أو CSV", type=["xlsx", "xls", "csv"])
st.info("الصيغة الحالية المطلوبة: Month | Revenue | COGS | Payroll | Marketing | Opex | Cash | Clients. يمكن أن تكون أسماء الأعمدة بالعربية أو الإنجليزية.")

if uploaded is None:
    st.warning("ارفعي ملفاً للبدء.")
    st.stop()

try:
    if uploaded.name.lower().endswith(".csv"):
        raw = pd.read_csv(uploaded)
        sheet_name = "CSV"
    else:
        xl = pd.ExcelFile(uploaded)
        sheet_name = st.selectbox("اختاري الشيت", xl.sheet_names)
        raw = pd.read_excel(uploaded, sheet_name=sheet_name)
except Exception as e:
    st.error(f"تعذر قراءة الملف: {e}")
    st.stop()

cols = detect_columns(raw)
if cols["revenue"] is None:
    st.error("لم أستطع تحديد عمود الإيرادات. تأكدي من وجود Revenue أو Sales أو الإيرادات.")
    st.stop()

monthly = prepare_data(raw, cols)
metrics = aggregate_metrics(monthly)
benchmarks = assess_benchmarks(metrics, industry)
score = score_company(benchmarks)
recommendations = generate_recommendations(metrics, benchmarks)
forecast = forecast_scenarios(monthly, months_ahead=months_ahead)
breakeven_df = pd.DataFrame([
    {"Metric": "Revenue", "Value": metrics["Revenue"]},
    {"Metric": "Variable Cost Ratio", "Value": metrics["Variable Cost Ratio"]},
    {"Metric": "Contribution Margin Ratio", "Value": metrics["Contribution Margin Ratio"]},
    {"Metric": "Fixed Costs", "Value": metrics["Fixed Costs"]},
    {"Metric": "Break-even Revenue", "Value": metrics["Break-even Revenue"]},
    {"Metric": "Break-even Gap", "Value": metrics["Break-even Gap"]},
])

# ============================================================
# Tabs
# ============================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Executive Dashboard",
    "Financial Ratios",
    "Break-even",
    "Forecast",
    "CFO Recommendations",
    "Export",
])

with tab1:
    st.markdown('<div class="section-title">1. Executive Dashboard</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="card"><div class="kpi-label">Revenue</div><div class="kpi-value">{fmt_money(metrics["Revenue"])}</div><div class="kpi-note">إجمالي الإيرادات</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="card"><div class="kpi-label">Gross Margin</div><div class="kpi-value">{fmt_pct(metrics["Gross Margin %"])}</div><div class="kpi-note">هامش الربح الإجمالي</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="card"><div class="kpi-label">EBITDA Margin</div><div class="kpi-value">{fmt_pct(metrics["EBITDA Margin %"])}</div><div class="kpi-note">كفاءة التشغيل</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="card"><div class="kpi-label">Financial Health Score</div><div class="kpi-value">{score}/100</div><div class="kpi-note">مبني على معايير السلامة</div></div>', unsafe_allow_html=True)

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        st.markdown(f'<div class="card"><div class="kpi-label">Net Profit</div><div class="kpi-value">{fmt_money(metrics["Net Profit"])}</div><div class="kpi-note">صافي الربح</div></div>', unsafe_allow_html=True)
    with c6:
        st.markdown(f'<div class="card"><div class="kpi-label">Break-even Gap</div><div class="kpi-value">{fmt_money(metrics["Break-even Gap"])}</div><div class="kpi-note">إيراد فعلي ناقص التعادل</div></div>', unsafe_allow_html=True)
    with c7:
        runway_txt = "∞" if not np.isfinite(metrics["Cash Runway"]) else f'{metrics["Cash Runway"]:.1f} mo'
        st.markdown(f'<div class="card"><div class="kpi-label">Cash Runway</div><div class="kpi-value">{runway_txt}</div><div class="kpi-note">مدى السيولة</div></div>', unsafe_allow_html=True)
    with c8:
        st.markdown(f'<div class="card"><div class="kpi-label">ARPU</div><div class="kpi-value">{fmt_money(metrics["ARPU"])}</div><div class="kpi-note">متوسط الإيراد للعميل</div></div>', unsafe_allow_html=True)

    left, right = st.columns(2)
    with left:
        st.plotly_chart(fig_line(monthly, "Month", "Revenue", "Revenue Trend"), use_container_width=True)
    with right:
        st.plotly_chart(fig_line(monthly, "Month", ["Gross Margin %", "EBITDA Margin %", "Net Margin %"], "Margin Trends", percent=True), use_container_width=True)

    with st.expander("عرض البيانات الشهرية"):
        st.dataframe(monthly, use_container_width=True)

with tab2:
    st.markdown('<div class="section-title">2. Financial Safety Ratios</div>', unsafe_allow_html=True)
    styled = benchmarks.copy()
    display_df = styled.copy()
    for col in ["Actual", "Benchmark", "Gap"]:
        display_df[col] = display_df.apply(lambda r: fmt_pct(r[col]) if r["Metric"].endswith("%") else ("∞" if not np.isfinite(r[col]) else f"{r[col]:,.1f}"), axis=1)
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.markdown("#### Interpretation")
    risks = benchmarks[benchmarks["Status"] == "Risk"]
    watches = benchmarks[benchmarks["Status"] == "Watch"]
    if risks.empty and watches.empty:
        st.success("المؤشرات ضمن نطاق صحي وفق معيار النشاط المختار.")
    else:
        if not risks.empty:
            st.error("مؤشرات خطر: " + ", ".join(risks["Metric"].tolist()))
        if not watches.empty:
            st.warning("مؤشرات تحتاج مراقبة: " + ", ".join(watches["Metric"].tolist()))

with tab3:
    st.markdown('<div class="section-title">3. Break-even Analysis</div>', unsafe_allow_html=True)
    col_a, col_b = st.columns([1, 1])
    with col_a:
        temp = breakeven_df.copy()
        temp["Value"] = temp.apply(lambda r: fmt_pct(r["Value"]) if "Ratio" in r["Metric"] else fmt_money(r["Value"]), axis=1)
        st.dataframe(temp, use_container_width=True, hide_index=True)
    with col_b:
        st.plotly_chart(fig_bar_be(metrics), use_container_width=True)
    if metrics["Break-even Gap"] < 0:
        st.error(f"الشركة دون نقطة التعادل بفجوة تقريبية: {fmt_money(abs(metrics['Break-even Gap']))}.")
    else:
        st.success(f"الشركة أعلى من نقطة التعادل بفائض تقريبي: {fmt_money(metrics['Break-even Gap'])}.")

with tab4:
    st.markdown('<div class="section-title">4. Forecast & Scenarios</div>', unsafe_allow_html=True)
    if forecast.empty:
        st.warning("نحتاج شهرين على الأقل لبناء توقع.")
    else:
        pivot_rev = forecast.pivot(index="Month", columns="Scenario", values="Revenue").reset_index()
        st.dataframe(pivot_rev, use_container_width=True, hide_index=True)
        fig = go.Figure()
        for scenario, color in [("Base", WAZEN_BLUE), ("Optimistic", HEALTHY), ("Pessimistic", RISK)]:
            df_s = forecast[forecast["Scenario"] == scenario]
            fig.add_trace(go.Scatter(x=df_s["Month"], y=df_s["Revenue"], mode="lines+markers", name=scenario, line=dict(width=3, color=color)))
        fig.update_layout(title="Revenue Forecast Scenarios", height=420, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        fig.update_yaxes(gridcolor="#E5E7EB")
        st.plotly_chart(fig, use_container_width=True)

with tab5:
    st.markdown('<div class="section-title">5. CFO Recommendations</div>', unsafe_allow_html=True)
    st.dataframe(recommendations, use_container_width=True, hide_index=True)
    st.markdown("#### AI CFO Commentary")
    if st.button("Generate Advanced CFO Commentary"):
        with st.spinner("Generating CFO commentary..."):
            report = ai_cfo_report(metrics, benchmarks, recommendations, forecast)
            st.session_state["ai_report"] = report
    st.markdown(st.session_state.get("ai_report", "اضغطي الزر لتوليد تعليق CFO متقدم عند تفعيل مفتاح OpenAI."))

with tab6:
    st.markdown('<div class="section-title">6. Export Professional CFO Pack</div>', unsafe_allow_html=True)
    ai_text = st.session_state.get("ai_report", "")
    excel_bytes = create_excel(monthly, metrics, benchmarks, breakeven_df, forecast, recommendations, ai_text)
    st.download_button(
        "Download Professional Excel CFO Pack",
        data=excel_bytes,
        file_name="wazen_professional_cfo_pack.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    st.caption("الملف يحتوي Dashboard، بيانات شهرية، Forecast، Break-even، Benchmarks، Recommendations.")
