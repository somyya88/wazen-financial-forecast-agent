import io
import json
import math
import re
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.linear_model import LinearRegression
from openai import OpenAI

# =============================
# PAGE CONFIG
# =============================
st.set_page_config(
    page_title="Wazen CFO Intelligence Agent",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

WAZEN_BLUE = "#17479E"
WAZEN_ORANGE = "#FAA61A"

st.markdown(
    f"""
    <style>
    .main {{background-color:#FFFFFF;}}
    .block-container {{padding-top: 2rem; padding-bottom: 2rem;}}
    .hero {{
        padding: 28px 34px;
        border-radius: 22px;
        background: linear-gradient(135deg, rgba(23,71,158,0.10), rgba(250,166,26,0.08));
        border: 1px solid rgba(23,71,158,0.12);
        margin-bottom: 22px;
    }}
    .hero h1 {{font-size: 42px; margin-bottom: 6px; color:#1f2430;}}
    .hero p {{color:#5f6675; font-size:16px;}}
    .section-title {{
        font-size: 24px; font-weight: 800; color:#1f2430;
        margin-top: 28px; margin-bottom: 12px;
    }}
    .metric-card {{
        padding: 18px 18px;
        border-radius: 18px;
        background: #FFFFFF;
        border: 1px solid #EEF1F6;
        box-shadow: 0 6px 20px rgba(31,36,48,0.05);
        min-height: 105px;
    }}
    .metric-label {{font-size: 13px; color:#6d7482; margin-bottom: 8px;}}
    .metric-value {{font-size: 28px; font-weight: 800; color:#1f2430;}}
    .metric-note {{font-size: 12px; color:#7d8491; margin-top: 5px;}}
    .good {{color:#0A8F4D; font-weight:700;}}
    .warn {{color:#B7791F; font-weight:700;}}
    .risk {{color:#C53030; font-weight:700;}}
    .small-note {{font-size: 13px; color:#6d7482;}}
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================
# HELPERS
# =============================
def money(x):
    try:
        return f"{float(x):,.0f}"
    except Exception:
        return "0"


def pct(x):
    try:
        return f"{float(x)*100:.1f}%"
    except Exception:
        return "0.0%"


def clean_number_series(s):
    return pd.to_numeric(s.astype(str).str.replace(",", "", regex=False).str.replace("%", "", regex=False), errors="coerce").fillna(0)


def normalize_columns(df):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def find_col(df, names):
    for c in df.columns:
        cl = str(c).strip().lower()
        for n in names:
            if n.lower() in cl:
                return c
    return None


def detect_input_type(df):
    cols_l = " | ".join([str(c).lower() for c in df.columns])
    if any(x in cols_l for x in ["revenue", "sales", "الإيراد", "الايراد", "المبيعات"]):
        return "monthly"
    if any(x in cols_l for x in ["account", "الحساب", "مدين", "دائن", "debit", "credit", "balance", "الرصيد"]):
        return "trial_balance"
    return "unknown"


def read_uploaded_file(uploaded_file):
    if uploaded_file.name.lower().endswith(".csv"):
        return {"CSV": pd.read_csv(uploaded_file)}
    xls = pd.ExcelFile(uploaded_file)
    return {sheet: pd.read_excel(uploaded_file, sheet_name=sheet) for sheet in xls.sheet_names}


def standardize_monthly(df):
    df = normalize_columns(df)
    month_col = find_col(df, ["month", "date", "period", "الشهر", "التاريخ", "الفترة"])
    revenue_col = find_col(df, ["revenue", "sales", "income", "الإيرادات", "الايرادات", "المبيعات", "الدخل"])
    cogs_col = find_col(df, ["cogs", "cost of sales", "direct cost", "تكلفة مباشرة", "تكلفة", "تكاليف"])
    payroll_col = find_col(df, ["payroll", "salary", "salaries", "رواتب", "الأجور", "اجور"])
    marketing_col = find_col(df, ["marketing", "ads", "advertising", "تسويق", "إعلانات", "اعلانات"])
    opex_col = find_col(df, ["opex", "operating expenses", "admin", "general", "مصاريف", "إدارية", "ادارية", "تشغيلية"])
    cash_col = find_col(df, ["cash", "bank", "النقد", "البنك", "رصيد"])
    clients_col = find_col(df, ["clients", "customers", "العملاء", "عدد العملاء"])
    other_income_col = find_col(df, ["other income", "income other", "ايرادات اخرى", "إيرادات أخرى"])
    depreciation_col = find_col(df, ["depreciation", "استهلاك", "اهلاك", "إهلاك"])
    ar_col = find_col(df, ["accounts receivable", "receivable", "ar", "ذمم مدينة", "عملاء"])
    ap_col = find_col(df, ["accounts payable", "payable", "ap", "ذمم دائنة", "موردين"])

    if revenue_col is None:
        raise ValueError("لم أستطع تحديد عمود الإيرادات. استخدمي Revenue أو Sales أو الإيرادات.")

    out = pd.DataFrame()
    out["Month"] = df[month_col].astype(str) if month_col else [f"Period {i+1}" for i in range(len(df))]
    out["Revenue"] = clean_number_series(df[revenue_col])
    out["COGS"] = clean_number_series(df[cogs_col]) if cogs_col else 0
    out["Payroll"] = clean_number_series(df[payroll_col]) if payroll_col else 0
    out["Marketing"] = clean_number_series(df[marketing_col]) if marketing_col else 0
    out["Opex"] = clean_number_series(df[opex_col]) if opex_col else 0
    out["Cash"] = clean_number_series(df[cash_col]) if cash_col else 0
    out["Clients"] = clean_number_series(df[clients_col]) if clients_col else 0
    out["Other Income"] = clean_number_series(df[other_income_col]) if other_income_col else 0
    out["Depreciation"] = clean_number_series(df[depreciation_col]) if depreciation_col else 0
    out["AR"] = clean_number_series(df[ar_col]) if ar_col else 0
    out["AP"] = clean_number_series(df[ap_col]) if ap_col else 0
    return out


def classify_account(account_name):
    name = str(account_name).lower()
    if any(k in name for k in ["ايراد", "إيراد", "مبيعات", "sales", "revenue"]):
        if any(k in name for k in ["اخرى", "أخرى", "other"]):
            return "Other Income"
        return "Revenue"
    if any(k in name for k in ["تكلفة", "تكاليف", "cost of sales", "cogs", "مشتريات"]):
        return "COGS"
    if any(k in name for k in ["راتب", "رواتب", "أجور", "اجور", "salary", "payroll", "wages"]):
        return "Payroll"
    if any(k in name for k in ["تسويق", "اعلان", "إعلان", "marketing", "ads"]):
        return "Marketing"
    if any(k in name for k in ["اهلاك", "إهلاك", "استهلاك", "depreciation"]):
        return "Depreciation"
    if any(k in name for k in ["نقد", "صندوق", "بنك", "bank", "cash"]):
        return "Cash"
    if any(k in name for k in ["عميل", "عملاء", "ذمم مدينة", "receivable"]):
        return "AR"
    if any(k in name for k in ["مورد", "موردين", "ذمم دائنة", "payable"]):
        return "AP"
    if any(k in name for k in ["مصروف", "مصاريف", "expense", "rent", "ايجار", "إيجار", "اتصالات", "رسوم"]):
        return "Opex"
    return "Unmapped"


def standardize_trial_balance(df):
    df = normalize_columns(df)
    account_col = find_col(df, ["account name", "account", "اسم الحساب", "الحساب", "بيان"])
    debit_col = find_col(df, ["debit", "مدين"])
    credit_col = find_col(df, ["credit", "دائن"])
    balance_col = find_col(df, ["balance", "الرصيد", "balance amount"])

    if account_col is None:
        raise ValueError("لم أستطع تحديد عمود اسم الحساب في ميزان المراجعة.")

    tb = pd.DataFrame()
    tb["Account Name"] = df[account_col].astype(str)
    tb["Debit"] = clean_number_series(df[debit_col]) if debit_col else 0
    tb["Credit"] = clean_number_series(df[credit_col]) if credit_col else 0
    if balance_col:
        tb["Balance"] = clean_number_series(df[balance_col])
    else:
        tb["Balance"] = tb["Debit"] - tb["Credit"]
    tb["Category"] = tb["Account Name"].apply(classify_account)
    return tb


def tb_to_single_period(tb):
    # For TB signs vary by system. This approach uses category-side totals conservatively.
    def total(cat):
        part = tb[tb["Category"] == cat]
        if cat in ["Revenue", "Other Income"]:
            return max(part["Credit"].sum(), abs(part["Balance"].sum()))
        return max(part["Debit"].sum(), abs(part["Balance"].sum()))

    out = pd.DataFrame([{
        "Month": "Trial Balance Period",
        "Revenue": total("Revenue"),
        "COGS": total("COGS"),
        "Payroll": total("Payroll"),
        "Marketing": total("Marketing"),
        "Opex": total("Opex"),
        "Cash": total("Cash"),
        "Clients": 0,
        "Other Income": total("Other Income"),
        "Depreciation": total("Depreciation"),
        "AR": total("AR"),
        "AP": total("AP"),
    }])
    return out


def compute_kpis(data):
    data = data.copy()
    for col in ["Revenue", "COGS", "Payroll", "Marketing", "Opex", "Cash", "Clients", "Other Income", "Depreciation", "AR", "AP"]:
        if col not in data.columns:
            data[col] = 0
        data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)

    data["Gross Profit"] = data["Revenue"] - data["COGS"]
    data["Operating Expenses"] = data["Payroll"] + data["Marketing"] + data["Opex"]
    data["EBITDA"] = data["Gross Profit"] - data["Operating Expenses"] + data["Other Income"]
    data["EBIT"] = data["EBITDA"] - data["Depreciation"]
    data["Net Profit"] = data["EBIT"]

    data["Gross Margin %"] = np.where(data["Revenue"] != 0, data["Gross Profit"] / data["Revenue"], 0)
    data["EBITDA Margin %"] = np.where(data["Revenue"] != 0, data["EBITDA"] / data["Revenue"], 0)
    data["Net Margin %"] = np.where(data["Revenue"] != 0, data["Net Profit"] / data["Revenue"], 0)
    data["Payroll Ratio %"] = np.where(data["Revenue"] != 0, data["Payroll"] / data["Revenue"], 0)
    data["Marketing Ratio %"] = np.where(data["Revenue"] != 0, data["Marketing"] / data["Revenue"], 0)
    data["Opex Ratio %"] = np.where(data["Revenue"] != 0, data["Opex"] / data["Revenue"], 0)
    data["COGS Ratio %"] = np.where(data["Revenue"] != 0, data["COGS"] / data["Revenue"], 0)
    data["ARPU"] = np.where(data["Clients"] != 0, data["Revenue"] / data["Clients"], 0)
    data["DSO"] = np.where(data["Revenue"] != 0, data["AR"] / data["Revenue"] * 30, 0)
    data["DPO"] = np.where(data["COGS"] != 0, data["AP"] / data["COGS"] * 30, 0)
    data["Monthly Burn"] = np.where(data["Net Profit"] < 0, abs(data["Net Profit"]), 0)
    data["Cash Runway Months"] = np.where(data["Monthly Burn"] > 0, data["Cash"] / data["Monthly Burn"], np.nan)
    return data


def aggregate_totals(data):
    totals = {}
    sum_cols = ["Revenue", "COGS", "Payroll", "Marketing", "Opex", "Other Income", "Depreciation", "Gross Profit", "Operating Expenses", "EBITDA", "EBIT", "Net Profit"]
    for c in sum_cols:
        totals[c] = float(data[c].sum())
    latest = data.iloc[-1]
    totals["Cash"] = float(latest.get("Cash", 0))
    totals["Clients"] = float(latest.get("Clients", 0))
    totals["AR"] = float(latest.get("AR", 0))
    totals["AP"] = float(latest.get("AP", 0))
    totals["Gross Margin %"] = totals["Gross Profit"] / totals["Revenue"] if totals["Revenue"] else 0
    totals["EBITDA Margin %"] = totals["EBITDA"] / totals["Revenue"] if totals["Revenue"] else 0
    totals["Net Margin %"] = totals["Net Profit"] / totals["Revenue"] if totals["Revenue"] else 0
    totals["Payroll Ratio %"] = totals["Payroll"] / totals["Revenue"] if totals["Revenue"] else 0
    totals["Marketing Ratio %"] = totals["Marketing"] / totals["Revenue"] if totals["Revenue"] else 0
    totals["Opex Ratio %"] = totals["Opex"] / totals["Revenue"] if totals["Revenue"] else 0
    totals["COGS Ratio %"] = totals["COGS"] / totals["Revenue"] if totals["Revenue"] else 0
    totals["ARPU"] = totals["Revenue"] / totals["Clients"] if totals["Clients"] else 0
    avg_burn = data["Monthly Burn"].replace(0, np.nan).mean()
    totals["Cash Runway Months"] = totals["Cash"] / avg_burn if avg_burn and not np.isnan(avg_burn) else np.nan
    totals["DSO"] = totals["AR"] / (totals["Revenue"] / max(len(data), 1)) * 30 if totals["Revenue"] else 0
    totals["DPO"] = totals["AP"] / (totals["COGS"] / max(len(data), 1)) * 30 if totals["COGS"] else 0
    return totals


def break_even_analysis(totals):
    revenue = totals["Revenue"]
    variable_cost_ratio = totals["COGS"] / revenue if revenue else 0
    contribution_margin_ratio = 1 - variable_cost_ratio
    fixed_costs = totals["Payroll"] + totals["Marketing"] + totals["Opex"] + totals["Depreciation"]
    be_revenue = fixed_costs / contribution_margin_ratio if contribution_margin_ratio > 0 else np.nan
    gap = revenue - be_revenue if not np.isnan(be_revenue) else np.nan
    return {
        "Revenue": revenue,
        "Variable Cost Ratio": variable_cost_ratio,
        "Contribution Margin Ratio": contribution_margin_ratio,
        "Fixed Costs": fixed_costs,
        "Break-even Revenue": be_revenue,
        "Break-even Gap": gap,
        "Break-even Status": "Above Break-even" if gap >= 0 else "Below Break-even",
    }


def build_benchmarks(totals, sector):
    # Practical default ranges. They should be editable by management/consultant per sector.
    if sector == "SaaS / خدمات تقنية":
        benchmarks = [
            ("Gross Margin %", totals["Gross Margin %"], 0.50, ">=", "هامش إجمالي قوي في الخدمات التقنية عادة يعكس قابلية التوسع."),
            ("EBITDA Margin %", totals["EBITDA Margin %"], 0.15, ">=", "هامش EBITDA جيد يعكس كفاءة تشغيلية بعد المصاريف."),
            ("Net Margin %", totals["Net Margin %"], 0.10, ">=", "صافي الربح يجب أن يتحول تدريجياً إلى موجب ومستقر."),
            ("Payroll Ratio %", totals["Payroll Ratio %"], 0.35, "<=", "ارتفاع الرواتب فوق هذا المستوى قد يضغط على الربحية."),
            ("Marketing Ratio %", totals["Marketing Ratio %"], 0.20, "<=", "التسويق مقبول إذا كان يقود نمواً قابلاً للقياس."),
            ("Cash Runway Months", totals["Cash Runway Months"], 6, ">=", "سيولة أقل من 6 أشهر ترفع مخاطر التمويل."),
        ]
    else:
        benchmarks = [
            ("Gross Margin %", totals["Gross Margin %"], 0.30, ">=", "هامش إجمالي أقل من 30% يحتاج مراجعة التسعير والتكلفة."),
            ("EBITDA Margin %", totals["EBITDA Margin %"], 0.12, ">=", "EBITDA موجب ومستقر مؤشر على سلامة التشغيل."),
            ("Net Margin %", totals["Net Margin %"], 0.08, ">=", "صافي ربح أقل من 8% يتطلب ضبط مصاريف أو تسعير."),
            ("Payroll Ratio %", totals["Payroll Ratio %"], 0.30, "<=", "نسبة رواتب مرتفعة قد تشير إلى تضخم تشغيلي."),
            ("Marketing Ratio %", totals["Marketing Ratio %"], 0.15, "<=", "التسويق يجب ربطه بالعائد على الإنفاق."),
            ("Cash Runway Months", totals["Cash Runway Months"], 4, ">=", "السيولة يجب أن تكفي عدة أشهر من التشغيل."),
        ]
    rows = []
    for metric, actual, target, op, note in benchmarks:
        if np.isnan(actual):
            status = "N/A"
        elif op == ">=":
            status = "Healthy" if actual >= target else "Risk" if actual < target * 0.75 else "Watch"
        else:
            status = "Healthy" if actual <= target else "Risk" if actual > target * 1.25 else "Watch"
        rows.append({
            "Metric": metric,
            "Actual": actual,
            "Benchmark": target,
            "Rule": op,
            "Status": status,
            "Comment": note,
        })
    return pd.DataFrame(rows)


def generate_recommendations(totals, be, bench_df):
    recs = []
    if totals["Gross Margin %"] < 0.30:
        recs.append(("تسعير وتكلفة مباشرة", "مراجعة التسعير أو تكلفة تقديم الخدمة لأن الهامش الإجمالي منخفض."))
    if totals["EBITDA Margin %"] < 0.10:
        recs.append(("الكفاءة التشغيلية", "خفض المصاريف التشغيلية غير المنتجة وربط كل تكلفة بمؤشر أداء واضح."))
    if totals["Payroll Ratio %"] > 0.35:
        recs.append(("الرواتب والإنتاجية", "قياس إنتاجية الفريق لكل عميل/باقة قبل إضافة توظيف جديد."))
    if totals["Marketing Ratio %"] > 0.20:
        recs.append(("التسويق", "تحويل التسويق إلى CAC/Payback وليس مصروفاً عاماً."))
    if not np.isnan(be["Break-even Revenue"]) and be["Break-even Gap"] < 0:
        recs.append(("نقطة التعادل", f"الإيرادات أقل من نقطة التعادل بفجوة تقارب {money(abs(be['Break-even Gap']))}. يجب رفع الإيراد أو خفض التكلفة الثابتة."))
    if not np.isnan(totals["Cash Runway Months"]) and totals["Cash Runway Months"] < 4:
        recs.append(("السيولة", "رفع سرعة التحصيل وتأجيل المصروفات غير الحرجة لأن Runway منخفض."))
    if len(recs) == 0:
        recs.append(("الوضع العام", "المؤشرات الأساسية مقبولة، لكن يجب متابعة جودة الإيرادات والتحصيل شهرياً."))
    return pd.DataFrame(recs, columns=["Area", "Recommendation"])


def forecast_financials(data, months_ahead=6):
    if len(data) < 2:
        return pd.DataFrame()
    y = data["Revenue"].values.reshape(-1, 1)
    x = np.arange(len(y)).reshape(-1, 1)
    model = LinearRegression().fit(x, y)
    future_x = np.arange(len(y), len(y) + months_ahead).reshape(-1, 1)
    base_rev = np.maximum(model.predict(future_x).flatten(), 0)

    cogs_ratio = data["COGS Ratio %"].replace([np.inf, -np.inf], 0).tail(3).mean()
    payroll_avg = data["Payroll"].tail(3).mean()
    marketing_ratio = data["Marketing Ratio %"].replace([np.inf, -np.inf], 0).tail(3).mean()
    opex_avg = data["Opex"].tail(3).mean()
    dep_avg = data["Depreciation"].tail(3).mean()

    rows = []
    for i, rev in enumerate(base_rev, start=1):
        for case, factor in [("Base", 1.0), ("Optimistic", 1.15), ("Pessimistic", 0.85)]:
            r = rev * factor
            cogs = r * cogs_ratio
            marketing = r * marketing_ratio
            gross_profit = r - cogs
            ebitda = gross_profit - payroll_avg - marketing - opex_avg
            net_profit = ebitda - dep_avg
            rows.append({
                "Month": f"Month +{i}",
                "Scenario": case,
                "Revenue": r,
                "COGS": cogs,
                "Gross Profit": gross_profit,
                "Payroll": payroll_avg,
                "Marketing": marketing,
                "Opex": opex_avg,
                "EBITDA": ebitda,
                "Net Profit": net_profit,
                "Gross Margin %": gross_profit / r if r else 0,
                "EBITDA Margin %": ebitda / r if r else 0,
            })
    return pd.DataFrame(rows)


def ai_cfo_report(totals, be, bench_df, rec_df, forecast_df):
    api_key = st.secrets.get("OPENAI_API_KEY", None)
    if not api_key:
        return "لم يتم تفعيل مفتاح OpenAI في Secrets. التحليل الرقمي والداشبورد يعملان، لكن تقرير CFO الذكي يحتاج المفتاح."
    client = OpenAI(api_key=api_key)
    payload = {
        "totals": totals,
        "break_even": be,
        "benchmarks": bench_df.to_dict(orient="records"),
        "recommendations": rec_df.to_dict(orient="records"),
        "forecast_sample": forecast_df.head(18).to_dict(orient="records") if not forecast_df.empty else [],
    }
    prompt = f"""
أنت CFO تنفيذي ومستشار مالي للشركات الصغيرة والمتوسطة.
اكتب تقريراً احترافياً باللغة العربية بناءً على JSON التالي.

لا تكتب كلاماً عاماً. اربط كل توصية برقم. لا تفترض أن الشركة ناضجة إذا كانت في مرحلة تشغيل أولي.

المطلوب:
1) Executive Summary قوي.
2) تحليل الربحية والهامش.
3) تحليل المصاريف وهيكل التكلفة.
4) تحليل نقطة التعادل.
5) قراءة التوقعات والسيناريوهات.
6) تقييم نسب السلامة.
7) 5 توصيات تنفيذية واضحة.
8) 5 أسئلة يجب أن تسألها الإدارة قبل القرار.

البيانات:
{json.dumps(payload, ensure_ascii=False, default=str)}
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a senior CFO financial analysis agent."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content


def create_excel_report(data, totals, be, bench_df, rec_df, forecast_df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book
        fmt_title = workbook.add_format({"bold": True, "font_size": 18, "font_color": "#17479E"})
        fmt_header = workbook.add_format({"bold": True, "bg_color": "#17479E", "font_color": "#FFFFFF", "border": 1})
        fmt_sub = workbook.add_format({"bold": True, "font_size": 12, "font_color": "#17479E"})
        fmt_money = workbook.add_format({"num_format": "#,##0", "border": 1})
        fmt_pct = workbook.add_format({"num_format": "0.0%", "border": 1})
        fmt_text = workbook.add_format({"border": 1, "text_wrap": True})
        fmt_good = workbook.add_format({"font_color": "#0A8F4D", "bold": True, "border": 1})
        fmt_warn = workbook.add_format({"font_color": "#B7791F", "bold": True, "border": 1})
        fmt_risk = workbook.add_format({"font_color": "#C53030", "bold": True, "border": 1})
        fmt_orange = workbook.add_format({"bold": True, "bg_color": "#FAA61A", "font_color": "#1f2430", "border": 1})

        # Dashboard
        dash = workbook.add_worksheet("Dashboard")
        dash.right_to_left()
        dash.hide_gridlines(2)
        dash.set_column("A:A", 24)
        dash.set_column("B:E", 18)
        dash.write("A1", "Wazen CFO Intelligence Dashboard", fmt_title)
        dash.write("A2", "Generated", fmt_sub)
        dash.write("B2", datetime.now().strftime("%Y-%m-%d %H:%M"), fmt_text)

        kpis = [
            ("Revenue", totals["Revenue"], fmt_money),
            ("Gross Margin %", totals["Gross Margin %"], fmt_pct),
            ("EBITDA Margin %", totals["EBITDA Margin %"], fmt_pct),
            ("Net Profit", totals["Net Profit"], fmt_money),
            ("Break-even Revenue", be["Break-even Revenue"], fmt_money),
            ("Break-even Gap", be["Break-even Gap"], fmt_money),
            ("Cash", totals["Cash"], fmt_money),
            ("Cash Runway Months", totals["Cash Runway Months"], fmt_money),
        ]
        r = 4
        for idx, (label, value, fmt) in enumerate(kpis):
            row = r + (idx // 4) * 3
            col = (idx % 4) + 1
            dash.write(row, col, label, fmt_header)
            dash.write(row+1, col, value if not (isinstance(value, float) and np.isnan(value)) else 0, fmt)

        # Monthly data
        data.to_excel(writer, sheet_name="Monthly Data", index=False)
        ws = writer.sheets["Monthly Data"]
        ws.right_to_left()
        ws.freeze_panes(1, 0)
        for c, col_name in enumerate(data.columns):
            ws.write(0, c, col_name, fmt_header)
            ws.set_column(c, c, max(14, min(24, len(str(col_name)) + 4)))

        # Forecast
        forecast_df.to_excel(writer, sheet_name="Forecast", index=False)
        ws_f = writer.sheets["Forecast"]
        ws_f.right_to_left()
        ws_f.freeze_panes(1, 0)
        for c, col_name in enumerate(forecast_df.columns):
            ws_f.write(0, c, col_name, fmt_header)
            ws_f.set_column(c, c, 18)

        # Break-even
        be_df = pd.DataFrame([be])
        be_df.to_excel(writer, sheet_name="Break-even", index=False)
        ws_be = writer.sheets["Break-even"]
        ws_be.right_to_left()
        for c, col_name in enumerate(be_df.columns):
            ws_be.write(0, c, col_name, fmt_header)
            ws_be.set_column(c, c, 22)

        # Benchmarks
        bench_df.to_excel(writer, sheet_name="Benchmarks", index=False)
        ws_b = writer.sheets["Benchmarks"]
        ws_b.right_to_left()
        ws_b.freeze_panes(1, 0)
        for c, col_name in enumerate(bench_df.columns):
            ws_b.write(0, c, col_name, fmt_header)
            ws_b.set_column(c, c, 24 if col_name != "Comment" else 48)
        status_col = list(bench_df.columns).index("Status")
        for row_num, status in enumerate(bench_df["Status"], start=1):
            fmt = fmt_good if status == "Healthy" else fmt_warn if status == "Watch" else fmt_risk
            ws_b.write(row_num, status_col, status, fmt)

        # Recommendations
        rec_df.to_excel(writer, sheet_name="Recommendations", index=False)
        ws_r = writer.sheets["Recommendations"]
        ws_r.right_to_left()
        ws_r.set_column("A:A", 24)
        ws_r.set_column("B:B", 90)
        ws_r.write(0, 0, "Area", fmt_header)
        ws_r.write(0, 1, "Recommendation", fmt_header)

        # Charts in Dashboard
        chart = workbook.add_chart({"type": "line"})
        # Find row count
        n = len(data)
        if n > 0:
            rev_col = data.columns.get_loc("Revenue")
            month_col = data.columns.get_loc("Month")
            chart.add_series({
                "name": "Revenue",
                "categories": ["Monthly Data", 1, month_col, n, month_col],
                "values": ["Monthly Data", 1, rev_col, n, rev_col],
                "line": {"color": WAZEN_BLUE, "width": 2.25},
            })
            chart.set_title({"name": "Revenue Trend"})
            chart.set_legend({"none": True})
            chart.set_size({"width": 680, "height": 320})
            dash.insert_chart("A12", chart)

        chart2 = workbook.add_chart({"type": "column"})
        chart2.add_series({"name": "Revenue", "values": ["Dashboard", 5, 1, 5, 1], "fill": {"color": WAZEN_BLUE}})
        chart2.add_series({"name": "Break-even", "values": ["Dashboard", 8, 1, 8, 1], "fill": {"color": WAZEN_ORANGE}})
        chart2.set_title({"name": "Revenue vs Break-even"})
        chart2.set_size({"width": 520, "height": 300})
        dash.insert_chart("F12", chart2)

    output.seek(0)
    return output


def status_badge(status):
    cls = "good" if status == "Healthy" else "warn" if status == "Watch" else "risk" if status == "Risk" else "small-note"
    return f"<span class='{cls}'>{status}</span>"

# =============================
# SIDEBAR
# =============================
with st.sidebar:
    st.image("https://dummyimage.com/240x60/17479E/ffffff&text=WAZEN", use_container_width=True)
    st.markdown("### إعدادات التحليل")
    sector = st.selectbox("نوع النشاط / معيار المقارنة", ["خدمات عامة", "SaaS / خدمات تقنية", "تجارة", "تأجير ومعدات"])
    forecast_months = st.slider("عدد أشهر التوقع", min_value=3, max_value=12, value=6)
    st.markdown("---")
    st.caption("هذه النسخة MVP متقدمة: Dashboard + KPIs + Break-even + Benchmarks + Forecast + Excel Report.")

# =============================
# HERO
# =============================
st.markdown(
    """
    <div class="hero">
        <h1>📊 Wazen CFO Intelligence Agent</h1>
        <p>تحليل مالي تنفيذي، نسب سلامة، نقطة تعادل، توقعات، توصيات، وتقرير Excel احترافي قابل للتحميل.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

uploaded_file = st.file_uploader("ارفعي ملف Excel أو CSV", type=["xlsx", "xls", "csv"])

st.info("يدعم حالياً ملف شهري مختصر، ويدعم قراءة مبدئية لميزان المراجعة. للتنبؤ الحقيقي نحتاج بيانات شهرية.")

if not uploaded_file:
    st.stop()

try:
    sheets = read_uploaded_file(uploaded_file)
    sheet_name = st.selectbox("اختاري الشيت", list(sheets.keys())) if len(sheets) > 1 else list(sheets.keys())[0]
    raw_df = sheets[sheet_name]
    raw_df = normalize_columns(raw_df)

    input_type = detect_input_type(raw_df)
    st.caption(f"نوع الملف المكتشف: {input_type}")

    if input_type == "monthly":
        monthly = standardize_monthly(raw_df)
        tb_normalized = None
    elif input_type == "trial_balance":
        tb_normalized = standardize_trial_balance(raw_df)
        monthly = tb_to_single_period(tb_normalized)
        st.warning("تم تحويل ميزان المراجعة إلى فترة واحدة. التوقع المالي يحتاج بيانات شهرية فعلية أو توزيع شهري.")
    else:
        st.error("لم أستطع التعرف على بنية الملف. استخدمي ملف شهري أو ميزان مراجعة واضح الأعمدة.")
        st.stop()

    data = compute_kpis(monthly)
    totals = aggregate_totals(data)
    be = break_even_analysis(totals)
    bench_df = build_benchmarks(totals, sector)
    rec_df = generate_recommendations(totals, be, bench_df)
    forecast_df = forecast_financials(data, months_ahead=forecast_months)

except Exception as e:
    st.error(f"حدث خطأ أثناء قراءة الملف: {e}")
    st.stop()

# =============================
# EXECUTIVE DASHBOARD
# =============================
st.markdown("<div class='section-title'>1. Executive Dashboard</div>", unsafe_allow_html=True)

kpi_cols = st.columns(4)
metrics = [
    ("Revenue", money(totals["Revenue"]), "إجمالي الإيرادات"),
    ("Gross Margin", pct(totals["Gross Margin %"]), "هامش الربح الإجمالي"),
    ("EBITDA Margin", pct(totals["EBITDA Margin %"]), "كفاءة التشغيل قبل الإهلاك"),
    ("Net Profit", money(totals["Net Profit"]), "صافي الربح التقديري"),
]
for col, (label, value, note) in zip(kpi_cols, metrics):
    with col:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>{label}</div><div class='metric-value'>{value}</div><div class='metric-note'>{note}</div></div>", unsafe_allow_html=True)

kpi_cols2 = st.columns(4)
metrics2 = [
    ("Break-even Revenue", money(be["Break-even Revenue"]), "الإيراد المطلوب للتعادل"),
    ("Break-even Gap", money(be["Break-even Gap"]), be["Break-even Status"]),
    ("Cash", money(totals["Cash"]), "آخر رصيد نقدي متاح"),
    ("Runway", "N/A" if np.isnan(totals["Cash Runway Months"]) else f"{totals['Cash Runway Months']:.1f} شهر", "مدة كفاية النقد"),
]
for col, (label, value, note) in zip(kpi_cols2, metrics2):
    with col:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>{label}</div><div class='metric-value'>{value}</div><div class='metric-note'>{note}</div></div>", unsafe_allow_html=True)

# =============================
# CHARTS
# =============================
st.markdown("<div class='section-title'>2. Financial Visuals</div>", unsafe_allow_html=True)
chart_col1, chart_col2 = st.columns(2)
with chart_col1:
    fig = px.line(data, x="Month", y="Revenue", markers=True, title="Revenue Trend")
    fig.update_traces(line=dict(color=WAZEN_BLUE, width=3))
    fig.update_layout(height=380, plot_bgcolor="white", paper_bgcolor="white")
    st.plotly_chart(fig, use_container_width=True)
with chart_col2:
    margin_df = data[["Month", "Gross Margin %", "EBITDA Margin %", "Net Margin %"]].melt(id_vars="Month")
    fig2 = px.line(margin_df, x="Month", y="value", color="variable", markers=True, title="Margin Trends")
    fig2.update_layout(height=380, yaxis_tickformat=".0%", plot_bgcolor="white", paper_bgcolor="white")
    st.plotly_chart(fig2, use_container_width=True)

# =============================
# BENCHMARKS
# =============================
st.markdown("<div class='section-title'>3. Financial Safety Ratios</div>", unsafe_allow_html=True)
bench_display = bench_df.copy()
bench_display["Actual"] = bench_display.apply(lambda r: f"{r['Actual']:.1f}" if "Months" in r["Metric"] else f"{r['Actual']:.1%}", axis=1)
bench_display["Benchmark"] = bench_display.apply(lambda r: f"{r['Benchmark']:.1f}" if "Months" in r["Metric"] else f"{r['Benchmark']:.1%}", axis=1)
st.dataframe(bench_display, use_container_width=True, hide_index=True)

# =============================
# BREAK-EVEN
# =============================
st.markdown("<div class='section-title'>4. Break-even Analysis</div>", unsafe_allow_html=True)
be_col1, be_col2 = st.columns([1, 1])
with be_col1:
    st.table(pd.DataFrame([
        {"Metric": "Revenue", "Value": money(be["Revenue"])},
        {"Metric": "Variable Cost Ratio", "Value": pct(be["Variable Cost Ratio"])},
        {"Metric": "Contribution Margin Ratio", "Value": pct(be["Contribution Margin Ratio"])},
        {"Metric": "Fixed Costs", "Value": money(be["Fixed Costs"])},
        {"Metric": "Break-even Revenue", "Value": money(be["Break-even Revenue"])},
        {"Metric": "Gap", "Value": money(be["Break-even Gap"])},
    ]))
with be_col2:
    fig3 = go.Figure()
    fig3.add_trace(go.Bar(name="Revenue", x=["Actual Revenue"], y=[be["Revenue"]], marker_color=WAZEN_BLUE))
    fig3.add_trace(go.Bar(name="Break-even", x=["Break-even Revenue"], y=[be["Break-even Revenue"]], marker_color=WAZEN_ORANGE))
    fig3.update_layout(height=360, title="Actual Revenue vs Break-even", plot_bgcolor="white", paper_bgcolor="white")
    st.plotly_chart(fig3, use_container_width=True)

# =============================
# FORECAST
# =============================
st.markdown("<div class='section-title'>5. Forecast & Scenarios</div>", unsafe_allow_html=True)
if forecast_df.empty:
    st.warning("لا يمكن بناء توقع مالي لأن البيانات أقل من شهرين.")
else:
    pivot_forecast = forecast_df.pivot(index="Month", columns="Scenario", values="Revenue").reset_index()
    st.dataframe(pivot_forecast, use_container_width=True, hide_index=True)
    fig4 = px.line(forecast_df, x="Month", y="Revenue", color="Scenario", markers=True, title="Revenue Forecast Scenarios")
    fig4.update_layout(height=420, plot_bgcolor="white", paper_bgcolor="white")
    st.plotly_chart(fig4, use_container_width=True)

# =============================
# RECOMMENDATIONS
# =============================
st.markdown("<div class='section-title'>6. CFO Recommendations</div>", unsafe_allow_html=True)
st.dataframe(rec_df, use_container_width=True, hide_index=True)

with st.expander("عرض البيانات المحسوبة"):
    st.dataframe(data, use_container_width=True)
    if tb_normalized is not None:
        st.markdown("#### Trial Balance Mapping")
        st.dataframe(tb_normalized, use_container_width=True)

# =============================
# AI REPORT
# =============================
st.markdown("<div class='section-title'>7. AI CFO Narrative</div>", unsafe_allow_html=True)
if st.button("Generate Advanced CFO Report"):
    with st.spinner("جاري توليد التقرير التنفيذي..."):
        st.markdown(ai_cfo_report(totals, be, bench_df, rec_df, forecast_df))

# =============================
# EXCEL EXPORT
# =============================
st.markdown("<div class='section-title'>8. Professional Excel Output</div>", unsafe_allow_html=True)
excel_file = create_excel_report(data, totals, be, bench_df, rec_df, forecast_df)
st.download_button(
    label="Download Professional CFO Excel Report",
    data=excel_file,
    file_name="wazen_cfo_intelligence_report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
