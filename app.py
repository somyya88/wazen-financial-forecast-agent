# -*- coding: utf-8 -*-
"""
Wazen Flexible CFO Intelligence Agent - V4
------------------------------------------
A Streamlit prototype for SME financial analysis, forecasting, dashboards,
benchmarks, glossary, and professional Excel CFO Pack export.

Core design:
- Multi-file intake
- File type detection: monthly summary, trial balance, bank statement, invoices, unknown
- Manual mapping fallback for monthly summaries
- CFO-style dashboard: owner-readable cards + charts
- Rules-based ratios and risk interpretation
- Forecasting: historical trend + driver-based scenario assumptions
- Bilingual glossary Arabic / English
- Professional Excel pack export with multiple sheets
"""

from __future__ import annotations

import io
import math
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None


# =============================================================================
# Page Config + Styling
# =============================================================================

WAZEN_BLUE = "#17479E"
WAZEN_ORANGE = "#FAA61A"
WAZEN_DARK = "#101828"
WAZEN_MUTED = "#667085"
WAZEN_BG = "#F7F9FC"
WAZEN_GREEN = "#12B76A"
WAZEN_RED = "#D92D20"
WAZEN_AMBER = "#F79009"

st.set_page_config(
    page_title="Wazen CFO Intelligence Agent",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    f"""
    <style>
    .stApp {{ background: #ffffff; }}
    div[data-testid="stSidebar"] {{ background: linear-gradient(180deg, #F8FBFF 0%, #FFFFFF 100%); }}
    .wazen-hero {{
        background: linear-gradient(135deg, rgba(23,71,158,0.10), rgba(250,166,26,0.08));
        border: 1px solid rgba(23,71,158,0.12);
        border-radius: 22px;
        padding: 30px 34px;
        margin: 12px 0 22px 0;
        box-shadow: 0 14px 36px rgba(16,24,40,0.06);
    }}
    .wazen-title {{
        font-size: 36px;
        font-weight: 800;
        color: {WAZEN_DARK};
        margin-bottom: 8px;
        letter-spacing: -0.7px;
    }}
    .wazen-subtitle {{
        font-size: 16px;
        color: {WAZEN_MUTED};
        line-height: 1.9;
    }}
    .metric-card {{
        border-radius: 18px;
        background: #FFFFFF;
        border: 1px solid #EAECF0;
        padding: 18px 18px 16px 18px;
        min-height: 126px;
        box-shadow: 0 10px 24px rgba(16,24,40,0.055);
    }}
    .metric-title {{ font-size: 13px; color: {WAZEN_MUTED}; margin-bottom: 8px; }}
    .metric-value {{ font-size: 27px; color: {WAZEN_DARK}; font-weight: 800; }}
    .metric-note {{ font-size: 12px; color: {WAZEN_MUTED}; margin-top: 8px; line-height: 1.5; }}
    .status-healthy {{ color: {WAZEN_GREEN}; font-weight: 700; }}
    .status-watch {{ color: {WAZEN_AMBER}; font-weight: 700; }}
    .status-risk {{ color: {WAZEN_RED}; font-weight: 700; }}
    .owner-box {{
        background: #F8FAFC;
        border-right: 5px solid {WAZEN_BLUE};
        padding: 18px 22px;
        border-radius: 14px;
        line-height: 1.9;
        color: {WAZEN_DARK};
    }}
    .warn-box {{
        background: #FFF8E6;
        border-right: 5px solid {WAZEN_ORANGE};
        padding: 16px 20px;
        border-radius: 14px;
        line-height: 1.8;
    }}
    .risk-box {{
        background: #FEF3F2;
        border-right: 5px solid {WAZEN_RED};
        padding: 16px 20px;
        border-radius: 14px;
        line-height: 1.8;
    }}
    .small-muted {{ color: {WAZEN_MUTED}; font-size: 13px; }}
    h1, h2, h3 {{ color: {WAZEN_DARK}; }}
    </style>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# Utilities
# =============================================================================

def clean_col(col: Any) -> str:
    return str(col).strip().replace("\n", " ").replace("\r", " ")


def normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [clean_col(c) for c in out.columns]
    return out


def to_num(s: Any) -> pd.Series:
    if isinstance(s, pd.Series):
        return pd.to_numeric(
            s.astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("ريال", "", regex=False)
            .str.replace("SAR", "", regex=False)
            .str.replace(" ", "", regex=False),
            errors="coerce",
        ).fillna(0)
    try:
        return float(str(s).replace(",", ""))
    except Exception:
        return 0.0


def fmt_money(v: float) -> str:
    try:
        if pd.isna(v):
            return "-"
        return f"{v:,.0f}"
    except Exception:
        return "-"


def fmt_pct(v: float) -> str:
    try:
        if pd.isna(v):
            return "-"
        return f"{v:.1%}"
    except Exception:
        return "-"


def safe_div(a: float, b: float, default: float = 0.0) -> float:
    try:
        if b == 0 or pd.isna(b):
            return default
        return float(a) / float(b)
    except Exception:
        return default


def contains_any(cols: List[str], keywords: List[str]) -> bool:
    text = " | ".join(cols).lower()
    return any(k.lower() in text for k in keywords)


def find_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    cols = list(df.columns)
    for col in cols:
        low = str(col).strip().lower()
        for cand in candidates:
            if cand.lower() == low:
                return col
    for col in cols:
        low = str(col).strip().lower()
        for cand in candidates:
            if cand.lower() in low:
                return col
    return None


def status_class(status: str) -> str:
    return {
        "Healthy": "status-healthy",
        "Watch": "status-watch",
        "Risk": "status-risk",
    }.get(status, "")


# =============================================================================
# Glossary + Benchmarks
# =============================================================================

GLOSSARY = pd.DataFrame([
    ["الإيرادات", "Revenue", "إجمالي ما حققته الشركة من بيع خدماتها أو منتجاتها خلال الفترة.", "Sum of sales", "يقيس حجم النشاط لكنه لا يكفي للحكم على الربحية."],
    ["مجمل الربح", "Gross Profit", "الإيرادات بعد خصم التكلفة المباشرة المرتبطة بتقديم الخدمة أو المنتج.", "Revenue - COGS", "يكشف جودة التسعير والسيطرة على التكلفة المباشرة."],
    ["هامش مجمل الربح", "Gross Margin", "نسبة ما يبقى من كل ريال مبيعات بعد التكلفة المباشرة.", "Gross Profit ÷ Revenue", "إذا كان منخفضاً فالمشكلة غالباً في التسعير أو التكلفة المباشرة."],
    ["EBITDA", "EBITDA", "ربح التشغيل قبل الإهلاك والتمويل والضرائب.", "Gross Profit - Operating Expenses", "مفيد لفهم قوة التشغيل بعيداً عن أثر الإهلاك والتمويل."],
    ["هامش EBITDA", "EBITDA Margin", "نسبة EBITDA إلى الإيرادات.", "EBITDA ÷ Revenue", "يقيس قدرة النشاط الأساسي على توليد ربح تشغيلي."],
    ["صافي الربح", "Net Profit", "الربح النهائي بعد جميع المصاريف والإهلاكات والتمويل والضرائب.", "Revenue - All costs", "يكشف النتيجة النهائية للمالك."],
    ["هامش صافي الربح", "Net Margin", "كم يبقى من كل ريال مبيعات كربح نهائي.", "Net Profit ÷ Revenue", "إذا كان سالباً فهذا إنذار يحتاج تفسيراً."],
    ["نقطة التعادل", "Break-even Revenue", "الإيراد المطلوب لتغطية التكاليف دون ربح أو خسارة.", "Fixed Costs ÷ Contribution Margin %", "تحدد الحد الأدنى للإيراد المطلوب للبقاء."],
    ["هامش المساهمة", "Contribution Margin", "الإيراد بعد خصم التكاليف المتغيرة.", "Revenue - Variable Costs", "يوضح كم يساهم كل ريال مبيعات في تغطية التكاليف الثابتة."],
    ["هامش الأمان", "Margin of Safety", "الفرق بين الإيراد الفعلي ونقطة التعادل.", "Actual Revenue - Break-even Revenue", "إذا كان سالباً فالشركة تحت التعادل."],
    ["رأس المال العامل", "Working Capital", "الأصول المتداولة ناقص الالتزامات المتداولة.", "Current Assets - Current Liabilities", "يكشف راحة أو ضغط التشغيل القصير."],
    ["معدل التداول", "Current Ratio", "قدرة الأصول المتداولة على تغطية الالتزامات المتداولة.", "Current Assets ÷ Current Liabilities", "أقل من 1 يشير لضغط سيولة."],
    ["نسبة السيولة السريعة", "Quick Ratio", "قدرة السداد دون الاعتماد على المخزون.", "Cash + AR ÷ Current Liabilities", "مهم للشركات التي لديها مخزون بطيء."],
    ["أيام التحصيل", "DSO", "متوسط عدد الأيام لتحصيل العملاء.", "Accounts Receivable ÷ Revenue × Days", "كلما زاد زاد ضغط الكاش."],
    ["Cash Runway", "Cash Runway", "عدد الأشهر التي يكفيها النقد الحالي لتغطية المصاريف.", "Cash ÷ Average Monthly Cash Burn", "من أهم مؤشرات بقاء الشركات الصغيرة."],
    ["نسبة الرواتب", "Payroll Ratio", "الرواتب كنسبة من الإيرادات.", "Payroll ÷ Revenue", "تكشف هل حجم الفريق مناسب لحجم الإيرادات."],
    ["نسبة المصاريف التشغيلية", "Opex Ratio", "المصاريف التشغيلية كنسبة من الإيرادات.", "Opex ÷ Revenue", "تقيس الانضباط التشغيلي."],
    ["DSCR", "Debt Service Coverage Ratio", "قدرة الشركة على خدمة الدين من أرباح التشغيل.", "EBITDA ÷ Debt Service", "أقل من 1 يعني أن التشغيل لا يغطي خدمة الدين."],
], columns=["المصطلح العربي", "English Term", "المعنى المبسط", "Formula", "لماذا يهم؟"])

BENCHMARKS: Dict[str, Dict[str, Tuple[float, str]]] = {
    "خدمات عامة": {
        "Gross Margin %": (0.35, ">="),
        "EBITDA Margin %": (0.12, ">="),
        "Net Margin %": (0.08, ">="),
        "Payroll Ratio %": (0.30, "<="),
        "Opex Ratio %": (0.35, "<="),
        "Marketing Ratio %": (0.15, "<="),
        "Cash Runway Months": (4.0, ">="),
        "Break-even Gap": (0.0, ">="),
    },
    "SaaS / خدمات تقنية": {
        "Gross Margin %": (0.60, ">="),
        "EBITDA Margin %": (0.10, ">="),
        "Net Margin %": (0.05, ">="),
        "Payroll Ratio %": (0.45, "<="),
        "Opex Ratio %": (0.45, "<="),
        "Marketing Ratio %": (0.30, "<="),
        "Cash Runway Months": (6.0, ">="),
        "Break-even Gap": (0.0, ">="),
    },
    "تأجير ومعدات": {
        "Gross Margin %": (0.30, ">="),
        "EBITDA Margin %": (0.18, ">="),
        "Net Margin %": (0.08, ">="),
        "Payroll Ratio %": (0.22, "<="),
        "Opex Ratio %": (0.30, "<="),
        "Marketing Ratio %": (0.08, "<="),
        "Cash Runway Months": (4.0, ">="),
        "Break-even Gap": (0.0, ">="),
    },
    "تجارة": {
        "Gross Margin %": (0.25, ">="),
        "EBITDA Margin %": (0.08, ">="),
        "Net Margin %": (0.04, ">="),
        "Payroll Ratio %": (0.18, "<="),
        "Opex Ratio %": (0.25, "<="),
        "Marketing Ratio %": (0.10, "<="),
        "Cash Runway Months": (3.0, ">="),
        "Break-even Gap": (0.0, ">="),
    },
}


# =============================================================================
# Data Detection + Mapping
# =============================================================================

@dataclass
class UploadedDataset:
    file_name: str
    sheet_name: str
    df: pd.DataFrame
    detected_type: str
    confidence: int
    notes: str


def detect_file_type(df: pd.DataFrame) -> Tuple[str, int, str]:
    cols = [str(c).strip().lower() for c in df.columns]
    col_text = " | ".join(cols)
    if contains_any(cols, ["account code", "account no", "account name", "رقم الحساب", "اسم الحساب", "الحساب"]) and contains_any(cols, ["debit", "credit", "مدين", "دائن", "balance", "الرصيد"]):
        return "trial_balance", 90, "يبدو أن الملف ميزان مراجعة."
    if contains_any(cols, ["month", "period", "الشهر", "الفترة"]) and contains_any(cols, ["revenue", "sales", "الإيرادات", "المبيعات"]):
        return "monthly_summary", 95, "ملف شهري مختصر مناسب للتحليل والتنبؤ."
    if contains_any(cols, ["date", "التاريخ"]) and contains_any(cols, ["description", "details", "البيان", "الوصف"]) and contains_any(cols, ["debit", "credit", "amount", "مدين", "دائن", "المبلغ"]):
        return "bank_statement", 75, "يبدو أنه كشف بنك."
    if contains_any(cols, ["invoice", "فاتورة", "customer", "عميل", "due", "استحقاق", "amount", "المبلغ"]):
        return "invoices", 75, "يبدو أنه ملف فواتير أو ذمم."
    return "unknown", 30, "لم يتم التعرف على نوع الملف بدقة."


def read_uploaded_files(uploaded_files: List[Any]) -> List[UploadedDataset]:
    datasets: List[UploadedDataset] = []
    for f in uploaded_files:
        name = f.name
        try:
            if name.lower().endswith(".csv"):
                df = pd.read_csv(f)
                df = normalize_cols(df)
                typ, conf, notes = detect_file_type(df)
                datasets.append(UploadedDataset(name, "CSV", df, typ, conf, notes))
            else:
                xls = pd.ExcelFile(f)
                for sheet_name in xls.sheet_names:
                    df = pd.read_excel(xls, sheet_name=sheet_name)
                    if df.dropna(how="all").empty:
                        continue
                    df = normalize_cols(df)
                    typ, conf, notes = detect_file_type(df)
                    datasets.append(UploadedDataset(name, sheet_name, df, typ, conf, notes))
        except Exception as e:
            st.error(f"تعذر قراءة الملف {name}: {e}")
    return datasets


MONTHLY_CANDIDATES = {
    "Month": ["Month", "Date", "Period", "الشهر", "التاريخ", "الفترة"],
    "Revenue": ["Revenue", "Sales", "Income", "الإيرادات", "المبيعات", "الدخل"],
    "COGS": ["COGS", "Cost of Sales", "Direct Cost", "تكلفة", "تكلفة مباشرة", "تكلفة المبيعات"],
    "Payroll": ["Payroll", "Salary", "Salaries", "رواتب", "الأجور", "الرواتب"],
    "Marketing": ["Marketing", "Ads", "Advertising", "تسويق", "إعلانات"],
    "Opex": ["Opex", "Operating Expenses", "Admin", "General", "مصاريف", "إدارية", "تشغيلية"],
    "Cash": ["Cash", "Bank", "النقد", "البنك", "رصيد"],
    "Clients": ["Clients", "Customers", "العملاء", "عدد العملاء"],
    "AR": ["AR", "Accounts Receivable", "Receivables", "عملاء", "ذمم مدينة"],
    "AP": ["AP", "Accounts Payable", "Payables", "موردون", "ذمم دائنة"],
    "Inventory": ["Inventory", "Stock", "مخزون"],
    "Debt Service": ["Debt Service", "Loan Payment", "قسط", "خدمة الدين"],
    "Interest": ["Interest", "Finance Cost", "فوائد", "تمويل"],
    "Depreciation": ["Depreciation", "إهلاك", "استهلاك"],
}


def auto_map_monthly(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    return {k: find_column(df, v) for k, v in MONTHLY_CANDIDATES.items()}


def build_monthly_from_mapping(df: pd.DataFrame, mapping: Dict[str, Optional[str]]) -> pd.DataFrame:
    out = pd.DataFrame()
    n = len(df)
    for key in MONTHLY_CANDIDATES.keys():
        col = mapping.get(key)
        if key == "Month":
            if col:
                out[key] = df[col].astype(str)
            else:
                out[key] = [f"Period {i+1}" for i in range(n)]
        else:
            if col:
                out[key] = to_num(df[col])
            else:
                out[key] = 0.0
    return out


# Trial balance minimal mapping: converts aggregate TB into one period if columns are found.
TB_CANDIDATES = {
    "Account Name": ["Account Name", "Name", "الحساب", "اسم الحساب", "Account"],
    "Debit": ["Debit", "مدين"],
    "Credit": ["Credit", "دائن"],
    "Balance": ["Balance", "الرصيد", "Net"],
}


def classify_account(name: str) -> str:
    n = str(name).lower()
    ar = str(name)
    if any(x in n for x in ["revenue", "sales", "income"]) or any(x in ar for x in ["إيراد", "ايراد", "مبيعات", "دخل"]):
        return "Revenue"
    if any(x in n for x in ["cost of sales", "cogs", "direct cost"]) or any(x in ar for x in ["تكلفة", "كلفة", "مباشرة"]):
        return "COGS"
    if any(x in n for x in ["salary", "payroll", "wages"]) or any(x in ar for x in ["رواتب", "أجور", "اجور"]):
        return "Payroll"
    if any(x in n for x in ["marketing", "advertising", "ads"]) or any(x in ar for x in ["تسويق", "إعلان", "اعلان"]):
        return "Marketing"
    if any(x in n for x in ["cash", "bank"]) or any(x in ar for x in ["نقد", "بنك", "الصندوق"]):
        return "Cash"
    if any(x in n for x in ["depreciation", "amortization"]) or any(x in ar for x in ["إهلاك", "اهلاك", "استهلاك"]):
        return "Depreciation"
    if any(x in n for x in ["receivable", "customers"]) or any(x in ar for x in ["عملاء", "ذمم مدينة"]):
        return "AR"
    if any(x in n for x in ["payable", "vendors", "suppliers"]) or any(x in ar for x in ["مورد", "ذمم دائنة"]):
        return "AP"
    if any(x in n for x in ["inventory", "stock"]) or any(x in ar for x in ["مخزون"]):
        return "Inventory"
    if any(x in n for x in ["loan", "debt", "finance", "interest"]) or any(x in ar for x in ["قرض", "تمويل", "فوائد", "فائدة"]):
        return "Debt/Interest"
    if any(x in n for x in ["expense", "rent", "utilities", "general", "admin"]) or any(x in ar for x in ["مصروف", "إيجار", "ايجار", "كهرباء", "إدارية", "ادارية"]):
        return "Opex"
    return "Other"


def monthly_from_trial_balance(df: pd.DataFrame, period_label: str = "Current Period") -> Tuple[pd.DataFrame, pd.DataFrame]:
    mapping = {k: find_column(df, v) for k, v in TB_CANDIDATES.items()}
    name_col = mapping["Account Name"]
    if not name_col:
        return pd.DataFrame(), pd.DataFrame()
    work = df.copy()
    work["Category"] = work[name_col].apply(classify_account)
    debit = to_num(work[mapping["Debit"]]) if mapping["Debit"] else pd.Series([0] * len(work))
    credit = to_num(work[mapping["Credit"]]) if mapping["Credit"] else pd.Series([0] * len(work))
    balance = to_num(work[mapping["Balance"]]) if mapping["Balance"] else (debit - credit)
    work["Debit_N"] = debit
    work["Credit_N"] = credit
    work["Balance_N"] = balance

    # Revenue often credit; expenses often debit. Use absolute by category to avoid sign chaos.
    revenue = abs(work.loc[work["Category"] == "Revenue", "Credit_N"].sum() or work.loc[work["Category"] == "Revenue", "Balance_N"].sum())
    cogs = abs(work.loc[work["Category"] == "COGS", "Debit_N"].sum() or work.loc[work["Category"] == "COGS", "Balance_N"].sum())
    payroll = abs(work.loc[work["Category"] == "Payroll", "Debit_N"].sum() or work.loc[work["Category"] == "Payroll", "Balance_N"].sum())
    marketing = abs(work.loc[work["Category"] == "Marketing", "Debit_N"].sum() or work.loc[work["Category"] == "Marketing", "Balance_N"].sum())
    opex = abs(work.loc[work["Category"] == "Opex", "Debit_N"].sum() or work.loc[work["Category"] == "Opex", "Balance_N"].sum())
    cash = abs(work.loc[work["Category"] == "Cash", "Balance_N"].sum())
    ar = abs(work.loc[work["Category"] == "AR", "Balance_N"].sum())
    ap = abs(work.loc[work["Category"] == "AP", "Balance_N"].sum())
    dep = abs(work.loc[work["Category"] == "Depreciation", "Debit_N"].sum() or work.loc[work["Category"] == "Depreciation", "Balance_N"].sum())
    interest = abs(work.loc[work["Category"] == "Debt/Interest", "Debit_N"].sum())
    monthly = pd.DataFrame([{
        "Month": period_label,
        "Revenue": revenue,
        "COGS": cogs,
        "Payroll": payroll,
        "Marketing": marketing,
        "Opex": opex,
        "Cash": cash,
        "Clients": 0,
        "AR": ar,
        "AP": ap,
        "Inventory": 0,
        "Debt Service": 0,
        "Interest": interest,
        "Depreciation": dep,
    }])
    return monthly, work


# =============================================================================
# Financial Engine
# =============================================================================

def compute_financials(monthly: pd.DataFrame) -> pd.DataFrame:
    df = monthly.copy()
    required = ["Revenue", "COGS", "Payroll", "Marketing", "Opex", "Cash", "Clients", "AR", "AP", "Inventory", "Debt Service", "Interest", "Depreciation"]
    for c in required:
        if c not in df.columns:
            df[c] = 0.0
        df[c] = to_num(df[c])
    if "Month" not in df.columns:
        df["Month"] = [f"Period {i+1}" for i in range(len(df))]

    df["Gross Profit"] = df["Revenue"] - df["COGS"]
    df["EBITDA"] = df["Gross Profit"] - df["Payroll"] - df["Marketing"] - df["Opex"]
    df["EBIT"] = df["EBITDA"] - df["Depreciation"]
    df["Net Profit"] = df["EBIT"] - df["Interest"]

    df["Gross Margin %"] = np.where(df["Revenue"] != 0, df["Gross Profit"] / df["Revenue"], 0)
    df["EBITDA Margin %"] = np.where(df["Revenue"] != 0, df["EBITDA"] / df["Revenue"], 0)
    df["Net Margin %"] = np.where(df["Revenue"] != 0, df["Net Profit"] / df["Revenue"], 0)
    df["Payroll Ratio %"] = np.where(df["Revenue"] != 0, df["Payroll"] / df["Revenue"], 0)
    df["Marketing Ratio %"] = np.where(df["Revenue"] != 0, df["Marketing"] / df["Revenue"], 0)
    df["Opex Ratio %"] = np.where(df["Revenue"] != 0, df["Opex"] / df["Revenue"], 0)
    df["ARPU"] = np.where(df["Clients"] != 0, df["Revenue"] / df["Clients"], 0)
    df["DSO"] = np.where(df["Revenue"] != 0, df["AR"] / df["Revenue"] * 30, 0)
    df["DPO"] = np.where(df["COGS"] != 0, df["AP"] / df["COGS"] * 30, 0)
    df["DIO"] = np.where(df["COGS"] != 0, df["Inventory"] / df["COGS"] * 30, 0)
    df["CCC"] = df["DSO"] + df["DIO"] - df["DPO"]
    monthly_cash_burn = (df["COGS"] + df["Payroll"] + df["Marketing"] + df["Opex"] + df["Interest"]).replace(0, np.nan)
    df["Cash Runway Months"] = df["Cash"] / monthly_cash_burn
    df["Cash Runway Months"] = df["Cash Runway Months"].replace([np.inf, -np.inf], np.nan).fillna(0)
    df["Contribution Margin %"] = np.where(df["Revenue"] != 0, (df["Revenue"] - df["COGS"]) / df["Revenue"], 0)
    df["Fixed Costs"] = df["Payroll"] + df["Marketing"] + df["Opex"] + df["Interest"] + df["Depreciation"]
    df["Break-even Revenue"] = np.where(df["Contribution Margin %"] > 0, df["Fixed Costs"] / df["Contribution Margin %"], np.nan)
    df["Break-even Gap"] = df["Revenue"] - df["Break-even Revenue"]
    df["Margin of Safety %"] = np.where(df["Revenue"] != 0, df["Break-even Gap"] / df["Revenue"], 0)
    return df


def totals_row(df: pd.DataFrame) -> pd.Series:
    numeric = df.select_dtypes(include=[np.number]).sum()
    row = pd.Series(numeric)
    row["Month"] = "Total / Latest"
    # Latest balance metrics
    for c in ["Cash", "Clients", "AR", "AP", "Inventory"]:
        if c in df.columns:
            row[c] = df[c].iloc[-1]
    # Recompute percentage totals
    revenue = row.get("Revenue", 0)
    row["Gross Profit"] = row.get("Revenue", 0) - row.get("COGS", 0)
    row["EBITDA"] = row.get("Gross Profit", 0) - row.get("Payroll", 0) - row.get("Marketing", 0) - row.get("Opex", 0)
    row["EBIT"] = row.get("EBITDA", 0) - row.get("Depreciation", 0)
    row["Net Profit"] = row.get("EBIT", 0) - row.get("Interest", 0)
    row["Gross Margin %"] = safe_div(row.get("Gross Profit", 0), revenue)
    row["EBITDA Margin %"] = safe_div(row.get("EBITDA", 0), revenue)
    row["Net Margin %"] = safe_div(row.get("Net Profit", 0), revenue)
    row["Payroll Ratio %"] = safe_div(row.get("Payroll", 0), revenue)
    row["Marketing Ratio %"] = safe_div(row.get("Marketing", 0), revenue)
    row["Opex Ratio %"] = safe_div(row.get("Opex", 0), revenue)
    row["ARPU"] = safe_div(row.get("Revenue", 0), row.get("Clients", 0))
    row["DSO"] = safe_div(row.get("AR", 0), revenue) * max(30, len(df) * 30)
    row["DPO"] = safe_div(row.get("AP", 0), row.get("COGS", 0)) * max(30, len(df) * 30)
    row["DIO"] = safe_div(row.get("Inventory", 0), row.get("COGS", 0)) * max(30, len(df) * 30)
    row["CCC"] = row.get("DSO", 0) + row.get("DIO", 0) - row.get("DPO", 0)
    monthly_burn = (df["COGS"] + df["Payroll"] + df["Marketing"] + df["Opex"] + df["Interest"]).mean() if len(df) else 0
    row["Cash Runway Months"] = safe_div(row.get("Cash", 0), monthly_burn)
    row["Contribution Margin %"] = safe_div(row.get("Revenue", 0) - row.get("COGS", 0), revenue)
    row["Fixed Costs"] = row.get("Payroll", 0) + row.get("Marketing", 0) + row.get("Opex", 0) + row.get("Interest", 0) + row.get("Depreciation", 0)
    row["Break-even Revenue"] = safe_div(row.get("Fixed Costs", 0), row.get("Contribution Margin %", 0), np.nan)
    row["Break-even Gap"] = row.get("Revenue", 0) - row.get("Break-even Revenue", 0)
    row["Margin of Safety %"] = safe_div(row.get("Break-even Gap", 0), revenue)
    return row


def evaluate_metric(metric: str, actual: float, benchmark: float, rule: str) -> Tuple[str, str, str]:
    if pd.isna(actual):
        return "Watch", "لا تتوفر بيانات كافية", "استكمل البيانات قبل اتخاذ قرار."
    healthy = actual >= benchmark if rule == ">=" else actual <= benchmark
    # Watch zone within 15% of threshold
    if healthy:
        status = "Healthy"
    else:
        if benchmark == 0:
            status = "Risk"
        else:
            diff = abs(actual - benchmark) / abs(benchmark)
            status = "Watch" if diff <= 0.15 else "Risk"

    explanations = {
        "Gross Margin %": "كل 100 ريال مبيعات يترك هذا الجزء بعد التكلفة المباشرة.",
        "EBITDA Margin %": "يقيس قوة التشغيل قبل الإهلاك والتمويل والضرائب.",
        "Net Margin %": "يكشف الربح النهائي من كل ريال مبيعات.",
        "Payroll Ratio %": "يوضح مدى ضغط الرواتب على الإيرادات.",
        "Marketing Ratio %": "يوضح وزن الإنفاق التسويقي مقارنة بالإيرادات.",
        "Opex Ratio %": "يقيس انضباط المصاريف التشغيلية والإدارية.",
        "Cash Runway Months": "عدد الأشهر التي يغطيها النقد الحالي مقارنة بمعدل الصرف.",
        "Break-even Gap": "الفرق بين الإيراد الفعلي ونقطة التعادل.",
    }
    actions = {
        "Gross Margin %": "راجع التسعير والتكلفة المباشرة وتأكد من تحميل كل التكاليف على الخدمة/المنتج.",
        "EBITDA Margin %": "اضبط المصاريف التشغيلية وراجع الإنتاجية قبل التوسع.",
        "Net Margin %": "افصل أثر الإهلاك والتمويل والضرائب لفهم سبب تآكل الربح النهائي.",
        "Payroll Ratio %": "اربط التوظيف بالطاقة التشغيلية والإيراد المحقق لكل موظف.",
        "Marketing Ratio %": "اربط التسويق بمؤشرات تحويل وCAC قبل زيادة الإنفاق.",
        "Opex Ratio %": "صنف المصاريف إلى حرجة وغير حرجة وأوقف غير المؤثر على الإيراد.",
        "Cash Runway Months": "سرّع التحصيل وأجل المصاريف غير الحرجة وضع حد أدنى للكاش.",
        "Break-even Gap": "ارفع الإيراد أو حسّن هامش المساهمة أو خفّض التكاليف الثابتة للوصول للتعادل.",
    }
    return status, explanations.get(metric, "مؤشر مالي يحتاج قراءة ضمن سياق النشاط."), actions.get(metric, "راجع السبب الجذري للمؤشر.")


def build_ratio_table(total: pd.Series, sector: str) -> pd.DataFrame:
    bm = BENCHMARKS.get(sector, BENCHMARKS["خدمات عامة"])
    rows = []
    for metric, (benchmark, rule) in bm.items():
        actual = float(total.get(metric, 0))
        status, explain, action = evaluate_metric(metric, actual, benchmark, rule)
        rows.append({
            "المؤشر": metric,
            "Actual": actual,
            "Benchmark": benchmark,
            "Rule": rule,
            "Status": status,
            "ماذا يعني لصاحب العمل؟": explain,
            "الإجراء المقترح": action,
        })
    return pd.DataFrame(rows)


def health_score(ratios: pd.DataFrame) -> int:
    scores = {"Healthy": 100, "Watch": 60, "Risk": 25}
    if ratios.empty:
        return 0
    # Weight key areas slightly
    weights = []
    vals = []
    for _, r in ratios.iterrows():
        m = r["المؤشر"]
        w = 1.4 if m in ["Net Margin %", "Cash Runway Months", "Break-even Gap"] else 1.0
        weights.append(w)
        vals.append(scores.get(r["Status"], 50) * w)
    return int(sum(vals) / sum(weights))


def owner_summary(total: pd.Series, ratios: pd.DataFrame, score: int) -> str:
    risk_rows = ratios[ratios["Status"].eq("Risk")]
    watch_rows = ratios[ratios["Status"].eq("Watch")]
    biggest_risk = risk_rows.iloc[0]["المؤشر"] if not risk_rows.empty else (watch_rows.iloc[0]["المؤشر"] if not watch_rows.empty else "لا يوجد إنذار جوهري")
    be_gap = total.get("Break-even Gap", 0)
    runway = total.get("Cash Runway Months", 0)
    net_margin = total.get("Net Margin %", 0)
    lines = []
    lines.append(f"درجة السلامة المالية الحالية: {score}/100.")
    lines.append(f"الإيرادات بلغت {fmt_money(total.get('Revenue', 0))}، وهامش مجمل الربح {fmt_pct(total.get('Gross Margin %', 0))}.")
    if net_margin < 0:
        lines.append("الشركة تحقق خسارة صافية؛ يجب فصل أسباب الخسارة بين تشغيلية وغير تشغيلية قبل اتخاذ قرار توسع.")
    else:
        lines.append(f"هامش صافي الربح {fmt_pct(net_margin)}، وهذا يوضح مقدار ما يبقى للمالك بعد التكاليف.")
    if be_gap < 0:
        lines.append(f"الشركة تحت نقطة التعادل بفجوة تقارب {fmt_money(abs(be_gap))}. الأولوية: رفع الإيراد أو خفض التكلفة الثابتة.")
    else:
        lines.append(f"الشركة فوق نقطة التعادل بهامش أمان يقارب {fmt_money(be_gap)}.")
    lines.append(f"السيولة الحالية تكفي تقريباً {runway:.1f} شهر حسب معدل الصرف الحالي.")
    lines.append(f"أكبر نقطة تستحق الانتباه الآن: {biggest_risk}.")
    return "\n".join([f"- {x}" for x in lines])


def build_recommendations(total: pd.Series, ratios: pd.DataFrame) -> pd.DataFrame:
    recs = []
    priority_order = {"Risk": 1, "Watch": 2, "Healthy": 3}
    for _, r in ratios.iterrows():
        if r["Status"] in ["Risk", "Watch"]:
            recs.append({
                "Priority": "High" if r["Status"] == "Risk" else "Medium",
                "Area": r["المؤشر"],
                "Issue": r["ماذا يعني لصاحب العمل؟"],
                "Action": r["الإجراء المقترح"],
                "Expected Impact": "تحسين الربحية/السيولة وتقليل المخاطر إذا تم تنفيذ الإجراء ومتابعته شهرياً.",
                "Status Rank": priority_order[r["Status"]],
            })
    if not recs:
        recs.append({
            "Priority": "Low",
            "Area": "General",
            "Issue": "لا توجد مؤشرات خطر واضحة وفق البيانات المتاحة.",
            "Action": "استمر في المتابعة الشهرية مع تحسين جودة البيانات وربط الأرباح بالتدفقات النقدية.",
            "Expected Impact": "استدامة الأداء وتجنب المفاجآت.",
            "Status Rank": 3,
        })
    out = pd.DataFrame(recs).sort_values(["Status Rank", "Priority"]).drop(columns=["Status Rank"])
    return out


# =============================================================================
# Forecasting
# =============================================================================

def linear_forecast(series: pd.Series, periods: int) -> np.ndarray:
    y = pd.to_numeric(series, errors="coerce").fillna(0).values.astype(float)
    if len(y) < 2:
        return np.repeat(y[-1] if len(y) else 0, periods)
    x = np.arange(len(y))
    coef = np.polyfit(x, y, 1)
    future_x = np.arange(len(y), len(y) + periods)
    pred = coef[0] * future_x + coef[1]
    return np.maximum(pred, 0)


def build_forecast(df: pd.DataFrame, months: int, base_growth: float, opt_growth: float, pess_growth: float, collection_change: float = 0.0) -> pd.DataFrame:
    last = df.iloc[-1]
    base_trend = linear_forecast(df["Revenue"], months)
    avg_cogs_ratio = safe_div(df["COGS"].sum(), df["Revenue"].sum())
    avg_payroll = df["Payroll"].tail(min(3, len(df))).mean()
    avg_marketing_ratio = safe_div(df["Marketing"].sum(), df["Revenue"].sum())
    avg_opex = df["Opex"].tail(min(3, len(df))).mean()
    avg_interest = df["Interest"].tail(min(3, len(df))).mean() if "Interest" in df else 0
    avg_dep = df["Depreciation"].tail(min(3, len(df))).mean() if "Depreciation" in df else 0

    scenarios = [
        ("Base Case", base_growth),
        ("Optimistic Case", opt_growth),
        ("Pessimistic Case", pess_growth),
    ]
    rows = []
    for scenario, growth in scenarios:
        prev_rev = float(last["Revenue"])
        for i in range(1, months + 1):
            # blend historical trend with driver growth assumption
            trend_val = base_trend[i - 1]
            driver_val = prev_rev * (1 + growth)
            revenue = 0.55 * trend_val + 0.45 * driver_val
            cogs = revenue * avg_cogs_ratio
            marketing = revenue * avg_marketing_ratio
            payroll = avg_payroll * (1 + max(growth, 0) * 0.30)
            opex = avg_opex * (1 + max(growth, 0) * 0.15)
            gross_profit = revenue - cogs
            ebitda = gross_profit - payroll - marketing - opex
            net_profit = ebitda - avg_dep - avg_interest
            rows.append({
                "Month": f"Month +{i}",
                "Scenario": scenario,
                "Revenue": revenue,
                "COGS": cogs,
                "Gross Profit": gross_profit,
                "Payroll": payroll,
                "Marketing": marketing,
                "Opex": opex,
                "EBITDA": ebitda,
                "Net Profit": net_profit,
                "Gross Margin %": safe_div(gross_profit, revenue),
                "EBITDA Margin %": safe_div(ebitda, revenue),
                "Net Margin %": safe_div(net_profit, revenue),
                "Rule Used": "55% historical trend + 45% driver-based growth assumption",
            })
            prev_rev = revenue
    return pd.DataFrame(rows)


# =============================================================================
# Visualization
# =============================================================================

def kpi_card(title: str, value: str, note: str = "", status: Optional[str] = None):
    css = status_class(status or "")
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">{title}</div>
            <div class="metric-value {css}">{value}</div>
            <div class="metric-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def make_gauge(score: int):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"suffix": "/100", "font": {"size": 34}},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": WAZEN_BLUE},
            "steps": [
                {"range": [0, 45], "color": "#FEE4E2"},
                {"range": [45, 70], "color": "#FEF0C7"},
                {"range": [70, 100], "color": "#D1FADF"},
            ],
            "threshold": {"line": {"color": WAZEN_ORANGE, "width": 4}, "thickness": 0.75, "value": score},
        },
        title={"text": "Financial Health Score"},
    ))
    fig.update_layout(height=270, margin=dict(l=20, r=20, t=60, b=20))
    return fig


def line_chart(df: pd.DataFrame, x: str, y: List[str], title: str):
    fig = px.line(df, x=x, y=y, markers=True, title=title)
    fig.update_layout(height=360, legend_title_text="", margin=dict(l=20, r=20, t=55, b=20))
    return fig


def be_chart(total: pd.Series):
    vals = pd.DataFrame({
        "Metric": ["Actual Revenue", "Break-even Revenue"],
        "Value": [total.get("Revenue", 0), total.get("Break-even Revenue", 0)],
    })
    fig = px.bar(vals, x="Metric", y="Value", text="Value", title="Actual Revenue vs Break-even")
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside", marker_color=[WAZEN_BLUE, WAZEN_ORANGE])
    fig.update_layout(height=360, showlegend=False, margin=dict(l=20, r=20, t=55, b=20))
    return fig


# =============================================================================
# Excel Export
# =============================================================================

def export_cfo_pack(monthly: pd.DataFrame, ratios: pd.DataFrame, forecast: pd.DataFrame, recs: pd.DataFrame, total: pd.Series, score: int, summary: str, glossary: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        wb = writer.book
        fmt_title = wb.add_format({"bold": True, "font_size": 18, "font_color": WAZEN_BLUE})
        fmt_subtitle = wb.add_format({"font_color": "#667085", "font_size": 11})
        fmt_header = wb.add_format({"bold": True, "font_color": "white", "bg_color": WAZEN_BLUE, "border": 1})
        fmt_orange = wb.add_format({"bold": True, "font_color": "white", "bg_color": WAZEN_ORANGE, "border": 1})
        fmt_money = wb.add_format({"num_format": '#,##0;[Red](#,##0);-', "border": 1})
        fmt_pct = wb.add_format({"num_format": '0.0%;[Red](0.0%);-', "border": 1})
        fmt_num = wb.add_format({"num_format": '0.0;[Red](0.0);-', "border": 1})
        fmt_text = wb.add_format({"text_wrap": True, "valign": "top", "border": 1})
        fmt_good = wb.add_format({"font_color": "#027A48", "bg_color": "#ECFDF3", "border": 1})
        fmt_warn = wb.add_format({"font_color": "#B54708", "bg_color": "#FFFAEB", "border": 1})
        fmt_risk = wb.add_format({"font_color": "#B42318", "bg_color": "#FEF3F2", "border": 1})

        # Executive Summary
        ws = wb.add_worksheet("Executive Summary")
        writer.sheets["Executive Summary"] = ws
        ws.hide_gridlines(2)
        ws.write("B2", "Wazen CFO Intelligence Pack", fmt_title)
        ws.write("B3", "Owner-readable financial diagnosis, KPIs, benchmarks, break-even, forecast and action plan", fmt_subtitle)
        ws.write("B5", "Financial Health Score", fmt_header)
        ws.write("C5", score)
        ws.write("B7", "Owner Summary", fmt_header)
        ws.merge_range("B8:H14", summary.replace("- ", "• "), fmt_text)
        kpis = [
            ["Revenue", total.get("Revenue", 0)],
            ["Gross Margin %", total.get("Gross Margin %", 0)],
            ["EBITDA Margin %", total.get("EBITDA Margin %", 0)],
            ["Net Profit", total.get("Net Profit", 0)],
            ["Break-even Revenue", total.get("Break-even Revenue", 0)],
            ["Break-even Gap", total.get("Break-even Gap", 0)],
            ["Cash", total.get("Cash", 0)],
            ["Cash Runway Months", total.get("Cash Runway Months", 0)],
        ]
        ws.write_row("B16", ["KPI", "Value"], fmt_header)
        for i, row in enumerate(kpis, start=17):
            ws.write(i-1, 1, row[0], fmt_text)
            ws.write(i-1, 2, row[1], fmt_money if "%" not in row[0] and "Months" not in row[0] else (fmt_pct if "%" in row[0] else fmt_num))
        ws.set_column("B:B", 28)
        ws.set_column("C:H", 18)

        # Owner Dashboard data
        dash = pd.DataFrame(kpis, columns=["KPI", "Value"])
        dash.to_excel(writer, index=False, sheet_name="Owner Dashboard", startrow=1)
        ws2 = writer.sheets["Owner Dashboard"]
        ws2.hide_gridlines(2)
        ws2.write("A1", "Owner Dashboard", fmt_title)
        ws2.set_column("A:A", 26)
        ws2.set_column("B:B", 18)
        ws2.autofilter(1, 0, len(dash)+1, 1)
        for col in range(2):
            ws2.write(1, col, dash.columns[col], fmt_header)
        chart = wb.add_chart({"type": "column"})
        chart.add_series({"name": "KPI Values", "categories": ["Owner Dashboard", 2, 0, len(dash)+1, 0], "values": ["Owner Dashboard", 2, 1, len(dash)+1, 1], "fill": {"color": WAZEN_BLUE}})
        chart.set_title({"name": "Key Values"})
        chart.set_size({"width": 620, "height": 330})
        ws2.insert_chart("D3", chart)

        # Monthly Data
        monthly.to_excel(writer, index=False, sheet_name="Monthly Data")
        ws3 = writer.sheets["Monthly Data"]
        ws3.hide_gridlines(2)
        ws3.freeze_panes(1, 1)
        for col, header in enumerate(monthly.columns):
            ws3.write(0, col, header, fmt_header)
            ws3.set_column(col, col, 16)
        ws3.autofilter(0, 0, len(monthly), len(monthly.columns)-1)

        # Ratios
        ratios.to_excel(writer, index=False, sheet_name="Ratio Analysis")
        ws4 = writer.sheets["Ratio Analysis"]
        ws4.hide_gridlines(2)
        for col, header in enumerate(ratios.columns):
            ws4.write(0, col, header, fmt_header)
            ws4.set_column(col, col, 22 if col < 5 else 42)
        ws4.autofilter(0, 0, len(ratios), len(ratios.columns)-1)
        status_col = list(ratios.columns).index("Status")
        for i, status in enumerate(ratios["Status"], start=1):
            f = fmt_good if status == "Healthy" else (fmt_warn if status == "Watch" else fmt_risk)
            ws4.write(i, status_col, status, f)

        # Break-even
        be_df = pd.DataFrame({
            "Metric": ["Revenue", "Variable Cost Ratio", "Contribution Margin %", "Fixed Costs", "Break-even Revenue", "Break-even Gap", "Margin of Safety %"],
            "Value": [total.get("Revenue", 0), safe_div(total.get("COGS",0), total.get("Revenue",0)), total.get("Contribution Margin %",0), total.get("Fixed Costs",0), total.get("Break-even Revenue",0), total.get("Break-even Gap",0), total.get("Margin of Safety %",0)]
        })
        be_df.to_excel(writer, index=False, sheet_name="Break-even")
        ws5 = writer.sheets["Break-even"]
        ws5.hide_gridlines(2)
        ws5.set_column("A:A", 28)
        ws5.set_column("B:B", 18)
        ws5.write_row("A1", be_df.columns.tolist(), fmt_header)
        be_chart_x = wb.add_chart({"type": "column"})
        # Actual revenue and BE revenue rows: 2 and 6 in Excel 1-indexed? Use zero-based row indices: row 1 and 5
        be_chart_x.add_series({"name": "Revenue vs Break-even", "categories": ["Break-even", 1, 0, 5, 0], "values": ["Break-even", 1, 1, 5, 1], "fill": {"color": WAZEN_ORANGE}})
        be_chart_x.set_title({"name": "Break-even Analysis"})
        be_chart_x.set_size({"width": 620, "height": 330})
        ws5.insert_chart("D3", be_chart_x)

        # Forecast
        forecast.to_excel(writer, index=False, sheet_name="Forecast & Scenarios")
        ws6 = writer.sheets["Forecast & Scenarios"]
        ws6.hide_gridlines(2)
        for col, header in enumerate(forecast.columns):
            ws6.write(0, col, header, fmt_header)
            ws6.set_column(col, col, 18)
        ws6.autofilter(0, 0, len(forecast), len(forecast.columns)-1)

        # Recommendations
        recs.to_excel(writer, index=False, sheet_name="Action Plan")
        ws7 = writer.sheets["Action Plan"]
        ws7.hide_gridlines(2)
        for col, header in enumerate(recs.columns):
            ws7.write(0, col, header, fmt_orange)
            ws7.set_column(col, col, 24 if col < 2 else 48)
        ws7.autofilter(0, 0, len(recs), len(recs.columns)-1)

        # Glossary
        glossary.to_excel(writer, index=False, sheet_name="Glossary")
        ws8 = writer.sheets["Glossary"]
        ws8.hide_gridlines(2)
        for col, header in enumerate(glossary.columns):
            ws8.write(0, col, header, fmt_header)
            ws8.set_column(col, col, 24 if col < 2 else 45)
        ws8.autofilter(0, 0, len(glossary), len(glossary.columns)-1)

        # Data Quality
        dq = pd.DataFrame([
            ["Rows analyzed", len(monthly)],
            ["Has monthly data", "Yes" if len(monthly) >= 2 else "No"],
            ["Forecast reliability", "Medium" if len(monthly) >= 6 else "Low - needs more months"],
            ["Recommendation", "استخدم 12 شهراً على الأقل لتوقعات أدق، واربط ميزان المراجعة بكشف البنك والفواتير."],
        ], columns=["Check", "Result"])
        dq.to_excel(writer, index=False, sheet_name="Data Quality")
        ws9 = writer.sheets["Data Quality"]
        ws9.hide_gridlines(2)
        ws9.write_row("A1", dq.columns.tolist(), fmt_header)
        ws9.set_column("A:A", 30)
        ws9.set_column("B:B", 70)
    output.seek(0)
    return output.getvalue()


# =============================================================================
# AI Narrative (Optional)
# =============================================================================

def ai_cfo_narrative(summary: str, ratios: pd.DataFrame, recs: pd.DataFrame) -> str:
    try:
        api_key = st.secrets.get("OPENAI_API_KEY", None)
        if not api_key or OpenAI is None:
            return "لم يتم تفعيل مفتاح OpenAI. يعمل الإيجنت حالياً بمحرك قواعد وتحليل داخلي، ويمكن تفعيل التعليق الذكي لاحقاً."
        client = OpenAI(api_key=api_key)
        prompt = f"""
أنت CFO محترف للشركات الصغيرة والمتوسطة. اكتب تقريراً تنفيذياً عربياً موجهاً لصاحب المشروع، واضحاً ومباشراً.
لا تكرر الجداول. فسّر ماذا تعني الأرقام وما القرار المطلوب.

ملخص القواعد:
{summary}

النسب:
{ratios.to_string(index=False)}

التوصيات:
{recs.to_string(index=False)}
"""
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are a CFO business-owner financial diagnosis agent."}, {"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return res.choices[0].message.content
    except Exception as e:
        return f"تعذر توليد التعليق الذكي: {e}"


# =============================================================================
# UI
# =============================================================================

with st.sidebar:
    st.markdown(f"<div style='background:{WAZEN_BLUE}; color:white; padding:22px; border-radius:12px; font-size:28px; letter-spacing:4px; text-align:center;'>WAZEN</div>", unsafe_allow_html=True)
    st.markdown("### إعدادات التحليل")
    objective = st.selectbox("ما هدف التحليل؟", ["تحليل شامل", "تحليل ربحية", "تحليل سيولة", "تحليل نقطة تعادل", "تحليل توقعات", "تقرير مالك المشروع"])
    sector = st.selectbox("نوع النشاط / معيار المقارنة", list(BENCHMARKS.keys()), index=0)
    forecast_months = st.slider("عدد أشهر التوقع", 3, 18, 6)
    st.markdown("### فرضيات السيناريوهات")
    base_growth = st.number_input("Base monthly growth", value=0.03, step=0.01, format="%.2f")
    opt_growth = st.number_input("Optimistic monthly growth", value=0.08, step=0.01, format="%.2f")
    pess_growth = st.number_input("Pessimistic monthly growth", value=-0.03, step=0.01, format="%.2f")
    st.markdown("---")
    st.caption("V4: ملفات متعددة + Dashboard + Ratios + Break-even + Forecast + Glossary + Excel CFO Pack")

st.markdown(
    """
    <div class="wazen-hero">
        <div class="wazen-title">📊 Wazen Flexible CFO Intelligence Agent</div>
        <div class="wazen-subtitle">
            ارفع ملفاً أو أكثر، ثم يحصل صاحب العمل على تشخيص مالي واضح: بطاقات أرقام، نسب سلامة، نقطة تعادل، سيناريوهات توقع، قاموس مصطلحات، وخطة عمل قابلة للتنفيذ.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

uploaded_files = st.file_uploader(
    "ارفع ملف أو أكثر: ميزان مراجعة، ملف شهري، كشف بنك، فواتير، أو CSV",
    type=["xlsx", "xls", "csv"],
    accept_multiple_files=True,
)

if not uploaded_files:
    st.info("ابدئي برفع ملف شهري مختصر أو ميزان مراجعة. يدعم التطبيق حالياً التحليل الأقوى عند توفر بيانات شهرية.")
    with st.expander("صيغة الملف الشهري المقترحة"):
        st.code("Month | Revenue | COGS | Payroll | Marketing | Opex | Cash | Clients | AR | AP | Inventory | Debt Service | Interest | Depreciation")
    st.stop()

# Read files
datasets = read_uploaded_files(uploaded_files)
if not datasets:
    st.error("لم يتم العثور على بيانات قابلة للقراءة داخل الملفات.")
    st.stop()

st.subheader("1. اكتشاف الملفات")
file_overview = pd.DataFrame([{
    "File": d.file_name,
    "Sheet": d.sheet_name,
    "Detected Type": d.detected_type,
    "Confidence": d.confidence,
    "Notes": d.notes,
    "Rows": len(d.df),
    "Columns": len(d.df.columns),
} for d in datasets])
st.dataframe(file_overview, use_container_width=True, hide_index=True)

# Choose dataset
monthly_candidates = [d for d in datasets if d.detected_type == "monthly_summary"]
tb_candidates = [d for d in datasets if d.detected_type == "trial_balance"]

selected_dataset: UploadedDataset
if monthly_candidates:
    selected_label = st.selectbox("اختر الملف الأساسي للتحليل", [f"{d.file_name} | {d.sheet_name} | {d.detected_type}" for d in monthly_candidates + tb_candidates + datasets])
else:
    selected_label = st.selectbox("اختر الملف الأساسي للتحليل", [f"{d.file_name} | {d.sheet_name} | {d.detected_type}" for d in tb_candidates + datasets])
selected_dataset = next(d for d in datasets if f"{d.file_name} | {d.sheet_name} | {d.detected_type}" == selected_label)

# Build monthly base
normalized_monthly: pd.DataFrame
normalized_tb: pd.DataFrame = pd.DataFrame()
if selected_dataset.detected_type == "monthly_summary":
    st.subheader("2. Mapping الأعمدة")
    auto_mapping = auto_map_monthly(selected_dataset.df)
    with st.expander("تعديل Mapping الأعمدة يدوياً عند الحاجة", expanded=False):
        cols = [None] + list(selected_dataset.df.columns)
        mapping = {}
        cols_display = st.columns(3)
        keys = list(MONTHLY_CANDIDATES.keys())
        for idx, key in enumerate(keys):
            with cols_display[idx % 3]:
                default = auto_mapping.get(key)
                default_index = cols.index(default) if default in cols else 0
                mapping[key] = st.selectbox(key, cols, index=default_index, key=f"map_{key}")
    normalized_monthly = build_monthly_from_mapping(selected_dataset.df, mapping if 'mapping' in locals() else auto_mapping)
elif selected_dataset.detected_type == "trial_balance":
    period_label = st.text_input("اسم الفترة", value="Current Period")
    normalized_monthly, normalized_tb = monthly_from_trial_balance(selected_dataset.df, period_label=period_label)
    if normalized_monthly.empty:
        st.error("تعذر تحويل ميزان المراجعة. نحتاج أعمدة الحساب والمدين والدائن أو الرصيد.")
        st.stop()
    st.warning("تم تحويل ميزان المراجعة إلى فترة واحدة. التنبؤ يكون محدود الدقة ما لم تتوفر بيانات شهرية.")
else:
    st.warning("نوع الملف غير مدعوم بالكامل. استخدمي Mapping شهري يدوي إذا كان يحتوي بيانات مالية شهرية.")
    auto_mapping = auto_map_monthly(selected_dataset.df)
    cols = [None] + list(selected_dataset.df.columns)
    mapping = {}
    cols_display = st.columns(3)
    for idx, key in enumerate(MONTHLY_CANDIDATES.keys()):
        with cols_display[idx % 3]:
            default = auto_mapping.get(key)
            default_index = cols.index(default) if default in cols else 0
            mapping[key] = st.selectbox(key, cols, index=default_index, key=f"unknown_map_{key}")
    normalized_monthly = build_monthly_from_mapping(selected_dataset.df, mapping)

financials = compute_financials(normalized_monthly)
# Add total row for display but not charts
summary_total = totals_row(financials)
ratios = build_ratio_table(summary_total, sector)
score = health_score(ratios)
recs = build_recommendations(summary_total, ratios)
forecast = build_forecast(financials, forecast_months, base_growth, opt_growth, pess_growth)
summary_text = owner_summary(summary_total, ratios, score)

st.subheader("2. Owner Summary")
col_a, col_b = st.columns([2, 1])
with col_a:
    st.markdown(f"<div class='owner-box'>{summary_text.replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
with col_b:
    st.plotly_chart(make_gauge(score), use_container_width=True)

st.subheader("3. Executive Dashboard")
# Determine statuses for card coloring
status_lookup = dict(zip(ratios["المؤشر"], ratios["Status"]))
cols = st.columns(4)
with cols[0]:
    kpi_card("Revenue | الإيرادات", fmt_money(summary_total.get("Revenue", 0)), "حجم النشاط خلال الفترة")
with cols[1]:
    kpi_card("Gross Margin | هامش مجمل الربح", fmt_pct(summary_total.get("Gross Margin %", 0)), "صحة التسعير والتكلفة المباشرة", status_lookup.get("Gross Margin %"))
with cols[2]:
    kpi_card("EBITDA Margin", fmt_pct(summary_total.get("EBITDA Margin %", 0)), "قوة التشغيل الأساسية", status_lookup.get("EBITDA Margin %"))
with cols[3]:
    kpi_card("Net Profit | صافي الربح", fmt_money(summary_total.get("Net Profit", 0)), "النتيجة النهائية للمالك", status_lookup.get("Net Margin %"))
cols = st.columns(4)
with cols[0]:
    kpi_card("Break-even Revenue", fmt_money(summary_total.get("Break-even Revenue", 0)), "الإيراد المطلوب لتغطية التكاليف")
with cols[1]:
    kpi_card("Break-even Gap", fmt_money(summary_total.get("Break-even Gap", 0)), "فوق/تحت نقطة التعادل", status_lookup.get("Break-even Gap"))
with cols[2]:
    kpi_card("Cash | النقد", fmt_money(summary_total.get("Cash", 0)), "رصيد النقد/البنك المتاح")
with cols[3]:
    kpi_card("Cash Runway", f"{summary_total.get('Cash Runway Months', 0):.1f} شهر", "مدة كفاية النقد", status_lookup.get("Cash Runway Months"))

# Tabs
owner_tab, ratios_tab, be_tab, forecast_tab, glossary_tab, export_tab = st.tabs([
    "📌 Owner View", "📐 النسب المالية", "⚖️ نقطة التعادل", "🔮 التنبؤ والسيناريوهات", "📚 قاموس المصطلحات", "📥 Excel Pack"
])

with owner_tab:
    c1, c2 = st.columns(2)
    with c1:
        chart_df = financials.copy()
        st.plotly_chart(line_chart(chart_df, "Month", ["Revenue"], "Revenue Trend"), use_container_width=True)
    with c2:
        margin_df = financials[["Month", "Gross Margin %", "EBITDA Margin %", "Net Margin %"]].copy()
        st.plotly_chart(line_chart(margin_df, "Month", ["Gross Margin %", "EBITDA Margin %", "Net Margin %"], "Margin Trends"), use_container_width=True)
    st.markdown("### البيانات المالية المحسوبة")
    display_fin = pd.concat([financials, pd.DataFrame([summary_total])], ignore_index=True)
    st.dataframe(display_fin, use_container_width=True, hide_index=True)

with ratios_tab:
    st.markdown("### Financial Safety Ratios | نسب السلامة المالية")
    st.dataframe(ratios, use_container_width=True, hide_index=True)
    st.markdown("### قراءة المؤشرات")
    for _, r in ratios.iterrows():
        box = "risk-box" if r["Status"] == "Risk" else ("warn-box" if r["Status"] == "Watch" else "owner-box")
        st.markdown(
            f"<div class='{box}'><b>{r['المؤشر']}</b> — <span class='{status_class(r['Status'])}'>{r['Status']}</span><br>{r['ماذا يعني لصاحب العمل؟']}<br><b>الإجراء:</b> {r['الإجراء المقترح']}</div><br>",
            unsafe_allow_html=True,
        )

with be_tab:
    st.plotly_chart(be_chart(summary_total), use_container_width=True)
    be_details = pd.DataFrame({
        "Metric": ["Revenue", "Variable Cost Ratio", "Contribution Margin %", "Fixed Costs", "Break-even Revenue", "Break-even Gap", "Margin of Safety %"],
        "Value": [summary_total.get("Revenue", 0), safe_div(summary_total.get("COGS", 0), summary_total.get("Revenue", 0)), summary_total.get("Contribution Margin %", 0), summary_total.get("Fixed Costs", 0), summary_total.get("Break-even Revenue", 0), summary_total.get("Break-even Gap", 0), summary_total.get("Margin of Safety %", 0)],
        "Owner Meaning": [
            "الإيراد الفعلي خلال الفترة.",
            "نسبة التكلفة المتغيرة إلى الإيرادات.",
            "كم يساهم كل ريال مبيعات في تغطية التكاليف الثابتة.",
            "التكاليف التي يجب تغطيتها حتى لو لم ترتفع المبيعات.",
            "الإيراد المطلوب للوصول إلى صفر ربح/خسارة.",
            "إذا كان سالباً فالشركة تحت التعادل.",
            "نسبة الأمان بين المبيعات والتعادل.",
        ]
    })
    st.dataframe(be_details, use_container_width=True, hide_index=True)

with forecast_tab:
    st.markdown("### Forecasting Rules | قواعد التنبؤ")
    st.markdown("""
    <div class='owner-box'>
    التنبؤ هنا لا يعتمد على الذكاء الاصطناعي وحده. القاعدة المستخدمة تجمع بين: <br>
    <b>55%</b> من الاتجاه التاريخي للإيرادات + <b>45%</b> من فرضية النمو التي يحددها المستخدم. <br>
    ثم تُحسب التكاليف بناءً على متوسط نسب التكلفة التاريخية، مع تثبيت جزء من المصاريف الثابتة.
    </div>
    """, unsafe_allow_html=True)
    st.dataframe(forecast, use_container_width=True, hide_index=True)
    fig = px.line(forecast, x="Month", y="Revenue", color="Scenario", markers=True, title="Revenue Forecast by Scenario")
    fig.update_layout(height=380)
    st.plotly_chart(fig, use_container_width=True)
    fig2 = px.line(forecast, x="Month", y="Net Profit", color="Scenario", markers=True, title="Net Profit Forecast by Scenario")
    fig2.update_layout(height=380)
    st.plotly_chart(fig2, use_container_width=True)

with glossary_tab:
    st.markdown("### قاموس المصطلحات المالية | Financial Glossary")
    term = st.selectbox("اختاري مصطلحاً لشرحه", GLOSSARY["المصطلح العربي"].tolist())
    row = GLOSSARY[GLOSSARY["المصطلح العربي"] == term].iloc[0]
    st.markdown(f"""
    <div class='owner-box'>
    <b>{row['المصطلح العربي']} | {row['English Term']}</b><br><br>
    <b>المعنى:</b> {row['المعنى المبسط']}<br>
    <b>المعادلة:</b> {row['Formula']}<br>
    <b>لماذا يهم؟</b> {row['لماذا يهم؟']}
    </div>
    """, unsafe_allow_html=True)
    st.dataframe(GLOSSARY, use_container_width=True, hide_index=True)

with export_tab:
    st.markdown("### Action Plan | خطة العمل")
    st.dataframe(recs, use_container_width=True, hide_index=True)
    if st.button("Generate AI CFO Narrative", type="secondary"):
        st.markdown(ai_cfo_narrative(summary_text, ratios, recs))
    xlsx_bytes = export_cfo_pack(display_fin, ratios, forecast, recs, summary_total, score, summary_text, GLOSSARY)
    st.download_button(
        label="Download Professional CFO Excel Pack",
        data=xlsx_bytes,
        file_name="wazen_flexible_cfo_intelligence_pack.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )

