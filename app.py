import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO
import zipfile, xml.etree.ElementTree as ET, re, math

# =============================
# Page Config
# =============================
st.set_page_config(
    page_title="Wazen CFO Intelligence Agent V5",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

WAZEN_BLUE = "#17479E"
WAZEN_ORANGE = "#FAA61A"
DARK = "#111827"
MUTED = "#6B7280"
LIGHT_BG = "#F8FAFC"
RISK = "#DC2626"
WATCH = "#D97706"
HEALTHY = "#059669"

st.markdown(f"""
<style>
.main .block-container {{padding-top: 2rem; padding-bottom: 2rem; max-width: 1350px;}}
.wazen-hero {{
    background: linear-gradient(135deg, rgba(23,71,158,0.08), rgba(250,166,26,0.10));
    border: 1px solid #E5E7EB;
    padding: 28px 34px;
    border-radius: 24px;
    margin-bottom: 24px;
}}
.wazen-title {{font-size: 36px; font-weight: 800; color: {DARK}; margin: 0;}}
.wazen-subtitle {{font-size: 15px; color: {MUTED}; margin-top: 8px;}}
.kpi-card {{
    background: white; border: 1px solid #E5E7EB; border-radius: 18px; padding: 18px;
    box-shadow: 0 10px 25px rgba(15,23,42,0.05); min-height: 130px;
}}
.kpi-label {{font-size: 13px; color: {MUTED}; margin-bottom: 8px;}}
.kpi-value {{font-size: 26px; font-weight: 800; color: {DARK};}}
.kpi-note {{font-size: 12px; color: {MUTED}; margin-top: 8px; line-height: 1.5;}}
.section-title {{font-size: 24px; font-weight: 800; color: {DARK}; margin-top: 22px; margin-bottom: 14px;}}
.owner-box {{background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 18px; padding: 18px; line-height: 1.9;}}
.status-healthy {{color: {HEALTHY}; font-weight: 700;}}
.status-watch {{color: {WATCH}; font-weight: 700;}}
.status-risk {{color: {RISK}; font-weight: 700;}}
.small-muted {{font-size: 12px; color: {MUTED};}}
[data-testid="stSidebar"] {{background-color: #F8FAFC;}}
</style>
""", unsafe_allow_html=True)

# =============================
# Helpers
# =============================
MONTHS_AR = ["يناير","فبراير","مارس","إبريل","ابريل","ماي","يونيو","يوليو","أغسطس","اغسطس","سبتمبر","أكتوبر","اكتوبر","نوفمبر","ديسمبر"]
MONTH_MAP = {
    "يناير":"Jan", "فبراير":"Feb", "مارس":"Mar", "إبريل":"Apr", "ابريل":"Apr", "ماي":"May", "يونيو":"Jun",
    "يوليو":"Jul", "أغسطس":"Aug", "اغسطس":"Aug", "سبتمبر":"Sep", "أكتوبر":"Oct", "اكتوبر":"Oct", "نوفمبر":"Nov", "ديسمبر":"Dec",
    "jan":"Jan", "january":"Jan", "feb":"Feb", "february":"Feb", "mar":"Mar", "march":"Mar", "apr":"Apr", "april":"Apr",
    "may":"May", "jun":"Jun", "june":"Jun", "jul":"Jul", "july":"Jul", "aug":"Aug", "august":"Aug", "sep":"Sep", "september":"Sep",
    "oct":"Oct", "october":"Oct", "nov":"Nov", "november":"Nov", "dec":"Dec", "december":"Dec"
}
MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def clean_text(x):
    if pd.isna(x): return ""
    s = str(x)
    s = s.replace("\u00a0", " ").replace("ـ", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def norm(x):
    s = clean_text(x).lower()
    s = s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه").replace("ى", "ي")
    return s


def to_num(x):
    if x is None or (isinstance(x, float) and np.isnan(x)): return 0.0
    if isinstance(x, (int, float, np.number)): return float(x)
    s = str(x).strip().replace(",", "")
    s = s.replace("SAR", "").replace("ر.س", "")
    s = re.sub(r"[^0-9\.\-]", "", s)
    try: return float(s) if s not in ["", "-", "."] else 0.0
    except: return 0.0


def fmt_money(x):
    try: return f"{float(x):,.0f}"
    except: return "0"


def fmt_pct(x):
    try: return f"{float(x)*100:.1f}%"
    except: return "0.0%"


def safe_div(a,b):
    try:
        return float(a)/float(b) if abs(float(b))>1e-9 else 0.0
    except: return 0.0

# =============================
# Robust Excel Reader
# =============================
def manual_xlsx_to_sheets(file_bytes):
    """Fallback reader that ignores broken stylesheets and reads raw worksheet XML."""
    ns = {'a':'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
          'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
    sheets = {}
    with zipfile.ZipFile(BytesIO(file_bytes)) as z:
        # shared strings
        sst = []
        if 'xl/sharedStrings.xml' in z.namelist():
            root = ET.fromstring(z.read('xl/sharedStrings.xml'))
            for si in root.findall('a:si', ns):
                texts = [t.text or '' for t in si.findall('.//a:t', ns)]
                sst.append(''.join(texts))
        wb = ET.fromstring(z.read('xl/workbook.xml'))
        rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        rid_to_target = {rel.attrib['Id']: rel.attrib['Target'] for rel in rels}
        sheet_infos = []
        for s in wb.findall('a:sheets/a:sheet', ns):
            name = s.attrib['name']
            rid = s.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
            target = rid_to_target[rid]
            target = 'xl/' + target if not target.startswith('/') else target.lstrip('/')
            target = target.replace('xl//','xl/')
            sheet_infos.append((name, target))
        for name, target in sheet_infos:
            root = ET.fromstring(z.read(target))
            max_col, max_row = 0, 0
            row_data = {}
            for row in root.findall('a:sheetData/a:row', ns):
                r_idx = int(row.attrib.get('r', 0))
                max_row = max(max_row, r_idx)
                row_vals = {}
                for c in row.findall('a:c', ns):
                    ref = c.attrib.get('r', '')
                    m = re.match(r'([A-Z]+)([0-9]+)', ref)
                    if not m: continue
                    letters = m.group(1)
                    col = 0
                    for ch in letters:
                        col = col*26 + ord(ch)-64
                    max_col = max(max_col, col)
                    val = ''
                    v = c.find('a:v', ns)
                    if v is not None:
                        val = v.text or ''
                        if c.attrib.get('t') == 's':
                            try: val = sst[int(val)]
                            except: pass
                    else:
                        is_elem = c.find('a:is', ns)
                        if is_elem is not None:
                            val = ''.join([t.text or '' for t in is_elem.findall('.//a:t', ns)])
                    row_vals[col] = val
                row_data[r_idx] = row_vals
            matrix = []
            for r in range(1, max_row+1):
                matrix.append([row_data.get(r, {}).get(c, '') for c in range(1, max_col+1)])
            sheets[name] = pd.DataFrame(matrix)
    return sheets


def read_uploaded_file(uploaded_file):
    file_bytes = uploaded_file.getvalue()
    name = uploaded_file.name
    try:
        if name.lower().endswith('.csv'):
            return {"CSV": pd.read_csv(BytesIO(file_bytes))}, None
        # First try normal pandas/openpyxl.
        return pd.read_excel(BytesIO(file_bytes), sheet_name=None, header=None), None
    except Exception as e1:
        try:
            return manual_xlsx_to_sheets(file_bytes), f"تمت قراءة الملف عبر قارئ احتياطي بسبب مشكلة في تنسيق Excel: {e1}"
        except Exception as e2:
            return {}, f"تعذر قراءة الملف: {e1} | fallback: {e2}"

# =============================
# Detection + Parsers
# =============================
def sheet_text_blob(df, max_rows=20, max_cols=20):
    if df is None or df.empty: return ""
    subset = df.iloc[:max_rows, :max_cols].astype(str).fillna("")
    return " ".join([norm(x) for x in subset.values.flatten() if str(x).strip()])


def detect_sheet_type(df):
    blob = sheet_text_blob(df, 25, 25)
    score = []
    if "ميزان المراجعه" in blob or ("رقم الحساب" in blob and "الرصيد الحالي" in blob):
        score.append(("trial_balance", 92, "يبدو أنه ميزان مراجعة"))
    if "رقم الحساب" in blob and "اسم الحساب" in blob and any(norm(m) in blob for m in MONTHS_AR) and "الاجمالي" in blob:
        score.append(("expense_monthly", 88, "تقرير مصروفات شهري حسب الحساب"))
    if "المجموع بدون الضريبه" in blob and "مجموع المبيعات شامل الضريبه" in blob:
        score.append(("monthly_sales_wide", 90, "ملف مبيعات شهرية بتنسيق أفقي"))
    if "اسم الصنف" in blob and "سعر الوحده" in blob and "حاله الدفع" in blob:
        score.append(("item_sales", 90, "تقرير مبيعات أصناف/عمليات"))
    # Standard monthly summary
    if ("revenue" in blob or "الايرادات" in blob or "المبيعات" in blob) and ("month" in blob or "الشهر" in blob or "الفتره" in blob):
        score.append(("monthly_summary", 75, "ملف شهري مختصر"))
    if not score:
        return "unknown", 30, "لم يتم التعرف على الملف بدقة"
    score.sort(key=lambda x: x[1], reverse=True)
    return score[0]


def dataframe_with_header(df, header_row=0):
    d = df.copy()
    cols = [clean_text(x) or f"Column_{i+1}" for i, x in enumerate(list(d.iloc[header_row]))]
    out = d.iloc[header_row+1:].copy()
    out.columns = cols
    out = out.dropna(how='all')
    return out


def parse_monthly_sales_wide(df):
    rows = df.astype(str).fillna('').values.tolist()
    # Month row is usually row 2 index 1.
    month_positions = []
    for r_i, row in enumerate(rows[:5]):
        for c_i, val in enumerate(row):
            if norm(val) in [norm(m) for m in MONTHS_AR]:
                month_positions.append((r_i, c_i, clean_text(val)))
    # Use first identified month row.
    if not month_positions:
        return pd.DataFrame()
    month_row = month_positions[0][0]
    positions = [(c, m) for r,c,m in month_positions if r == month_row]
    out=[]
    for c, m_ar in positions:
        month = MONTH_MAP.get(norm(m_ar), clean_text(m_ar))
        discount = no_vat = vat = with_vat = 0.0
        for r in range(month_row+1, min(len(rows), month_row+12)):
            value = to_num(rows[r][c]) if c < len(rows[r]) else 0.0
            label = norm(rows[r][c+1]) if c+1 < len(rows[r]) else ""
            if "الخصم" in label: discount = value
            elif "بدون الضريبه" in label: no_vat = value
            elif label.strip() == "الضريبه" or " الضريبه" in label: vat = value
            elif "شامل الضريبه" in label: with_vat = value
        out.append({"Month": f"{month} 2026", "Revenue": no_vat, "Sales With VAT": with_vat, "VAT Output": vat, "Discounts": discount, "Source": "Monthly Sales Wide"})
    return pd.DataFrame(out)


def parse_expense_monthly(df):
    # detect header row with account columns
    header_row = None
    for i in range(min(10, len(df))):
        row_blob = " ".join([norm(x) for x in df.iloc[i].astype(str).tolist()])
        if "رقم الحساب" in row_blob and "اسم الحساب" in row_blob:
            header_row = i; break
    if header_row is None: return pd.DataFrame(), pd.DataFrame()
    d = dataframe_with_header(df, header_row)
    cols = list(d.columns)
    acct_col = next((c for c in cols if "اسم الحساب" in norm(c)), None)
    month_cols = [c for c in cols if norm(c) in [norm(m) for m in MONTHS_AR]]
    monthly = {MONTH_MAP.get(norm(c), c): {"Payroll":0.0,"Marketing":0.0,"Opex":0.0,"COGS":0.0} for c in month_cols}
    detail_rows=[]
    for _, row in d.iterrows():
        account = clean_text(row.get(acct_col,"")) if acct_col else ""
        n = norm(account)
        if any(k in n for k in ["راتب", "رواتب", "بدل", "مكافات", "نهايه الخدمه", "انتداب"]): category="Payroll"
        elif any(k in n for k in ["تسويق", "اعلان", "اعلاني", "دعايه"]): category="Marketing"
        elif any(k in n for k in ["تكلفه", "تكاليف", "مبيعات"]): category="COGS"
        else: category="Opex"
        for c in month_cols:
            val = to_num(row.get(c,0))
            m = MONTH_MAP.get(norm(c), c)
            monthly[m][category] += val
        detail_rows.append({"Account": account, "Category": category})
    out=[]
    for m in MONTH_ORDER:
        if m in monthly:
            out.append({"Month": f"{m} 2026", **monthly[m], "Source":"Expense Report"})
    return pd.DataFrame(out), pd.DataFrame(detail_rows)


def parse_item_sales(df):
    header_row = 0
    # first row generally header; find row with اسم الصنف
    for i in range(min(5,len(df))):
        blob = " ".join([norm(x) for x in df.iloc[i].astype(str).tolist()])
        if "اسم الصنف" in blob and "المجموع" in blob:
            header_row = i; break
    d = dataframe_with_header(df, header_row)
    cols=list(d.columns)
    date_col = next((c for c in cols if "التاريخ" in norm(c) or "date" in norm(c)), None)
    total_col = next((c for c in cols if norm(c).strip()=="المجموع" or "total" in norm(c)), None)
    item_col = next((c for c in cols if "اسم الصنف" in norm(c)), None)
    qty_col = next((c for c in cols if "الكميه" in norm(c)), None)
    if not total_col: return pd.DataFrame(), pd.DataFrame()
    tmp=d.copy()
    tmp["AmountWithVAT"] = tmp[total_col].apply(to_num)
    tmp["Revenue"] = tmp["AmountWithVAT"] / 1.15
    tmp["VAT Output"] = tmp["AmountWithVAT"] - tmp["Revenue"]
    if date_col:
        tmp["DateParsed"] = pd.to_datetime(tmp[date_col], errors='coerce')
        tmp["Month"] = tmp["DateParsed"].dt.strftime("%b %Y").fillna("Unknown")
    else:
        tmp["Month"] = "Current Period"
    tmp["Quantity"] = tmp[qty_col].apply(to_num) if qty_col else 1
    monthly = tmp.groupby("Month", dropna=False).agg({"Revenue":"sum", "AmountWithVAT":"sum", "VAT Output":"sum", "Quantity":"sum"}).reset_index()
    monthly["Orders"] = tmp.groupby("Month").size().values
    monthly["Source"] = "Item Sales"
    product = pd.DataFrame()
    if item_col:
        product = tmp.groupby(item_col).agg({"Revenue":"sum", "Quantity":"sum"}).reset_index().sort_values("Revenue", ascending=False).head(20)
        product.columns=["Item", "Revenue", "Quantity"]
    return monthly, product


def parse_monthly_summary(df):
    # Find header row with Month/Revenue or Arabic equivalents
    header_row = 0
    for i in range(min(10,len(df))):
        blob=" ".join([norm(x) for x in df.iloc[i].astype(str).tolist()])
        if ("month" in blob or "الشهر" in blob or "الفتره" in blob) and ("revenue" in blob or "ايراد" in blob or "مبيعات" in blob):
            header_row=i; break
    d=dataframe_with_header(df, header_row)
    cols=list(d.columns)
    def find(names):
        for c in cols:
            nc=norm(c)
            if any(n in nc for n in names): return c
        return None
    mapping={
        "Month": find(["month","الشهر","الفتره"]),
        "Revenue": find(["revenue","sales","ايراد","مبيعات"]),
        "COGS": find(["cogs","تكلفه","تكلفة"]),
        "Payroll": find(["payroll","salary","رواتب","اجور"]),
        "Marketing": find(["marketing","تسويق","اعلان"]),
        "Opex": find(["opex","مصاريف","اداري","تشغيل"]),
        "Cash": find(["cash","bank","نقد","بنك","رصيد"]),
        "Clients": find(["clients","customers","عملاء"]),
        "AR": find(["accounts receivable","ar","ذمم مدينه","عملاء"]),
        "AP": find(["accounts payable","ap","ذمم دائنه","مورد"]),
        "Inventory": find(["inventory","مخزون"]),
    }
    out=pd.DataFrame()
    if mapping["Month"]: out["Month"] = d[mapping["Month"]].astype(str)
    else: out["Month"] = [f"Month {i+1}" for i in range(len(d))]
    for k,v in mapping.items():
        if k=="Month": continue
        out[k]=d[v].apply(to_num) if v else 0.0
    out["Source"]="Monthly Summary"
    return out


def parse_trial_balance(df):
    header_row=0
    for i in range(min(10,len(df))):
        blob=" ".join([norm(x) for x in df.iloc[i].astype(str).tolist()])
        if "رقم الحساب" in blob and "اسم الحساب" in blob:
            header_row=i; break
    d=dataframe_with_header(df, header_row)
    cols=list(d.columns)
    name_col=next((c for c in cols if "اسم الحساب" in norm(c)), None)
    debit_col=next((c for c in cols if norm(c).strip()=="مدين"), None)
    credit_col=next((c for c in cols if norm(c).strip()=="دائن"), None)
    current_debit=next((c for c in cols if "الرصيد الحالي" in norm(c) and "مدين" in norm(c)), None)
    current_credit=next((c for c in cols if "الرصيد الحالي" in norm(c) and "دائن" in norm(c)), None)
    totals={"Revenue":0.0,"Other Income":0.0,"COGS":0.0,"Payroll":0.0,"Marketing":0.0,"Opex":0.0,"Depreciation":0.0,"Cash":0.0,"AR":0.0,"AP":0.0,"Inventory":0.0,"Debt":0.0,"Assets":0.0,"Liabilities":0.0,"Equity":0.0}
    detail=[]
    for _, row in d.iterrows():
        name=clean_text(row.get(name_col,"")) if name_col else ""
        n=norm(name)
        debit=to_num(row.get(debit_col,0))
        credit=to_num(row.get(credit_col,0))
        cd=to_num(row.get(current_debit,0))
        cc=to_num(row.get(current_credit,0))
        amt=max(debit,credit,abs(cd-cc),cd,cc)
        category="Unmapped"
        if any(k in n for k in ["ايراد", "مبيعات", "اشتراك"]): category="Revenue"; totals["Revenue"] += max(credit, cc, amt if credit>debit else 0)
        elif any(k in n for k in ["دخل اخر", "ايرادات اخرى"]): category="Other Income"; totals["Other Income"] += max(credit, cc, amt)
        elif any(k in n for k in ["تكلفه", "تكلفة", "تكاليف المبيعات"]): category="COGS"; totals["COGS"] += max(debit, cd, amt)
        elif any(k in n for k in ["راتب", "رواتب", "اجور", "بدل", "مكافات"]): category="Payroll"; totals["Payroll"] += max(debit, cd, amt)
        elif any(k in n for k in ["تسويق", "اعلان", "دعايه"]): category="Marketing"; totals["Marketing"] += max(debit, cd, amt)
        elif any(k in n for k in ["اهلاك", "استهلاك"]): category="Depreciation"; totals["Depreciation"] += max(debit, cd, amt)
        elif any(k in n for k in ["نقد", "بنك", "صندوق"]): category="Cash"; totals["Cash"] += max(cd-cc, cd, 0)
        elif any(k in n for k in ["عملاء", "ذمم مدينه"]): category="AR"; totals["AR"] += max(cd-cc, cd, 0)
        elif any(k in n for k in ["مورد", "ذمم دائنه"]): category="AP"; totals["AP"] += max(cc-cd, cc, 0)
        elif "مخزون" in n: category="Inventory"; totals["Inventory"] += max(cd-cc, cd, 0)
        elif any(k in n for k in ["قرض", "تمويل", "دين"]): category="Debt"; totals["Debt"] += max(cc-cd, cc, 0)
        elif any(k in n for k in ["الاصول", "الموجودات"]): category="Assets"; totals["Assets"] += max(cd-cc, cd, 0)
        elif any(k in n for k in ["الالتزامات", "خصوم"]): category="Liabilities"; totals["Liabilities"] += max(cc-cd, cc, 0)
        elif any(k in n for k in ["راس المال", "حقوق الملكيه", "ارباح مرحله"]): category="Equity"; totals["Equity"] += max(cc-cd, cc, 0)
        elif debit or credit: category="Opex"; totals["Opex"] += max(debit, cd, 0) if debit>credit else 0
        detail.append({"Account Name":name,"Category":category,"Debit":debit,"Credit":credit,"Current Debit":cd,"Current Credit":cc})
    return totals, pd.DataFrame(detail)

# =============================
# Merge + Analytics
# =============================
def combine_monthly(parsed_results):
    frames=[]
    for res in parsed_results:
        if isinstance(res.get("monthly"), pd.DataFrame) and not res["monthly"].empty:
            frames.append(res["monthly"])
    if not frames: return pd.DataFrame()
    # Normalize columns
    all_cols=["Month","Revenue","COGS","Payroll","Marketing","Opex","Cash","Clients","AR","AP","Inventory","Sales With VAT","VAT Output","Discounts","Orders","Quantity"]
    normed=[]
    for f in frames:
        x=f.copy()
        for c in all_cols:
            if c not in x.columns: x[c]=0.0 if c!="Month" else ""
        normed.append(x[all_cols])
    all_df=pd.concat(normed, ignore_index=True)
    # Month sorting
    def month_key(m):
        s=str(m)
        for i,mo in enumerate(MONTH_ORDER):
            if mo.lower() in s.lower(): return i
        return 99
    numeric_cols=[c for c in all_cols if c!="Month"]
    combined=all_df.groupby("Month", as_index=False)[numeric_cols].sum()
    combined["_sort"]=combined["Month"].apply(month_key)
    combined=combined.sort_values("_sort").drop(columns="_sort")
    # Avoid double counting revenue if monthly sales wide and item sales both represent sales.
    # If revenue is massively duplicated, keep the maximum revenue per month from all sources? Current group sum may overstate.
    return combined


def calculate_metrics(monthly, tb_totals=None):
    tb_totals = tb_totals or {}
    if monthly.empty:
        rev=tb_totals.get("Revenue",0)+tb_totals.get("Other Income",0)
        cogs=tb_totals.get("COGS",0)
        payroll=tb_totals.get("Payroll",0)
        marketing=tb_totals.get("Marketing",0)
        opex=tb_totals.get("Opex",0)
        cash=tb_totals.get("Cash",0)
        ar=tb_totals.get("AR",0); ap=tb_totals.get("AP",0); inv=tb_totals.get("Inventory",0)
    else:
        rev=monthly["Revenue"].sum()
        cogs=monthly.get("COGS",pd.Series([0])).sum()
        payroll=monthly.get("Payroll",pd.Series([0])).sum()
        marketing=monthly.get("Marketing",pd.Series([0])).sum()
        opex=monthly.get("Opex",pd.Series([0])).sum()
        cash=monthly.get("Cash",pd.Series([0])).max()
        ar=monthly.get("AR",pd.Series([0])).max()
        ap=monthly.get("AP",pd.Series([0])).max()
        inv=monthly.get("Inventory",pd.Series([0])).max()
        if tb_totals.get("Cash",0)>0: cash=max(cash,tb_totals.get("Cash",0))
        ar=max(ar,tb_totals.get("AR",0)); ap=max(ap,tb_totals.get("AP",0)); inv=max(inv,tb_totals.get("Inventory",0))
    variable_cost = cogs
    fixed_cost = payroll + marketing + opex + tb_totals.get("Depreciation",0)
    gross_profit = rev - cogs
    ebitda = gross_profit - payroll - marketing - opex
    net_profit = ebitda - tb_totals.get("Depreciation",0)
    contribution_margin = 1 - safe_div(variable_cost, rev)
    break_even = safe_div(fixed_cost, contribution_margin) if contribution_margin>0 else 0
    gap = rev - break_even
    months_count = max(len(monthly),1) if not monthly.empty else 1
    avg_monthly_burn = max((payroll+marketing+opex+cogs-rev)/months_count, 0)
    cash_runway = safe_div(cash, avg_monthly_burn) if avg_monthly_burn>0 else 99
    dso = safe_div(ar, rev) * 150 if rev>0 else 0
    dpo = safe_div(ap, max(cogs,1)) * 150 if cogs>0 else 0
    dio = safe_div(inv, max(cogs,1)) * 150 if cogs>0 else 0
    ccc = dso + dio - dpo
    metrics={
        "Revenue":rev,"COGS":cogs,"Payroll":payroll,"Marketing":marketing,"Opex":opex,"Cash":cash,"AR":ar,"AP":ap,"Inventory":inv,
        "Gross Profit":gross_profit,"EBITDA":ebitda,"Net Profit":net_profit,
        "Gross Margin %":safe_div(gross_profit,rev),"EBITDA Margin %":safe_div(ebitda,rev),"Net Margin %":safe_div(net_profit,rev),
        "Payroll Ratio %":safe_div(payroll,rev),"Marketing Ratio %":safe_div(marketing,rev),"Opex Ratio %":safe_div(opex,rev),
        "Variable Cost Ratio %":safe_div(variable_cost,rev),"Contribution Margin %":contribution_margin,
        "Fixed Costs":fixed_cost,"Break-even Revenue":break_even,"Break-even Gap":gap,"Margin of Safety %":safe_div(gap,rev),
        "Cash Runway Months":cash_runway,"DSO":dso,"DPO":dpo,"DIO":dio,"CCC":ccc,
        "Debt":tb_totals.get("Debt",0),"Assets":tb_totals.get("Assets",0),"Liabilities":tb_totals.get("Liabilities",0),"Equity":tb_totals.get("Equity",0)
    }
    return metrics

BENCHMARKS={
    "خدمات تقنية / SaaS": {"Gross Margin %":0.55,"EBITDA Margin %":0.15,"Net Margin %":0.08,"Payroll Ratio %":0.35,"Opex Ratio %":0.30,"Cash Runway Months":3,"DSO":45},
    "خدمات عامة": {"Gross Margin %":0.35,"EBITDA Margin %":0.12,"Net Margin %":0.07,"Payroll Ratio %":0.30,"Opex Ratio %":0.25,"Cash Runway Months":2,"DSO":45},
    "تجارة": {"Gross Margin %":0.20,"EBITDA Margin %":0.08,"Net Margin %":0.04,"Payroll Ratio %":0.15,"Opex Ratio %":0.18,"Cash Runway Months":2,"DSO":45},
    "تأجير ومعدات": {"Gross Margin %":0.30,"EBITDA Margin %":0.18,"Net Margin %":0.06,"Payroll Ratio %":0.25,"Opex Ratio %":0.22,"Cash Runway Months":3,"DSO":60},
}

GLOSSARY = pd.DataFrame([
    ["الإيرادات", "Revenue", "إجمالي المبيعات أو الدخل من النشاط", "Sales / Revenue", "يعرف حجم النشاط"],
    ["هامش مجمل الربح", "Gross Margin", "ما يبقى من كل ريال بعد التكلفة المباشرة", "Gross Profit ÷ Revenue", "يكشف صحة التسعير والتكلفة"],
    ["هامش EBITDA", "EBITDA Margin", "ربحية التشغيل قبل الإهلاك والتمويل", "EBITDA ÷ Revenue", "يقيس قوة التشغيل"],
    ["هامش صافي الربح", "Net Margin", "ما يبقى فعلياً من كل ريال مبيعات", "Net Profit ÷ Revenue", "يكشف الربح النهائي"],
    ["نقطة التعادل", "Break-even Revenue", "الإيراد المطلوب لتغطية التكاليف", "Fixed Costs ÷ Contribution Margin", "يوضح الحد الأدنى الآمن للمبيعات"],
    ["هامش الأمان", "Margin of Safety", "المسافة بين الإيراد الحالي ونقطة التعادل", "(Revenue - Break-even) ÷ Revenue", "كلما زاد كان المشروع أكثر أماناً"],
    ["Cash Runway", "Cash Runway", "عدد الأشهر التي يستطيع النقد تغطية الصرف", "Cash ÷ Monthly Burn", "يقيس مدة البقاء النقدي"],
    ["أيام التحصيل", "DSO", "عدد الأيام اللازمة لتحصيل المبيعات", "AR ÷ Revenue × Days", "يكشف ضغط التحصيل"],
    ["دورة النقد", "Cash Conversion Cycle", "الأيام التي يبقى فيها النقد محبوساً", "DSO + DIO - DPO", "مهم لرأس المال العامل"],
], columns=["المصطلح العربي","English Term","المعنى المبسط","المعادلة","لماذا يهم؟"])


def status_for(metric, actual, benchmarks):
    target=benchmarks.get(metric)
    if target is None: return "غير متوفر", "لا يوجد معيار"
    lower_better = metric in ["Payroll Ratio %","Marketing Ratio %","Opex Ratio %","DSO","DPO","DIO","CCC"]
    if lower_better:
        if actual <= target: return "Healthy", "ضمن أو أفضل من المعيار"
        elif actual <= target*1.25: return "Watch", "قريب من منطقة الخطر"
        else: return "Risk", "أعلى من المعيار ويحتاج إجراء"
    else:
        if actual >= target: return "Healthy", "ضمن أو أفضل من المعيار"
        elif actual >= target*0.75: return "Watch", "أقل من المعيار لكن يمكن تحسينه"
        else: return "Risk", "أقل من المعيار ويحتاج تدخل"


def health_score(metrics, benchmarks):
    keys=["Gross Margin %","EBITDA Margin %","Net Margin %","Payroll Ratio %","Opex Ratio %","Cash Runway Months","DSO"]
    score=0; total=0
    for k in keys:
        if k in metrics and k in benchmarks:
            total+=1
            stt,_=status_for(k, metrics[k], benchmarks)
            score += 1 if stt=="Healthy" else 0.55 if stt=="Watch" else 0.15
    return round((score/max(total,1))*100)


def recommendations(metrics, benchmarks):
    rec=[]
    def add(priority, area, issue, action, impact): rec.append({"الأولوية":priority,"المحور":area,"الملاحظة":issue,"الإجراء المقترح":action,"الأثر المتوقع":impact})
    if metrics["Break-even Gap"] < 0:
        add("عالية","نقطة التعادل",f"الشركة تحت نقطة التعادل بفجوة {fmt_money(abs(metrics['Break-even Gap']))}.","رفع الإيرادات أو تخفيض التكاليف الثابتة أو تحسين هامش المساهمة.","تقليل الخسارة التشغيلية وتحسين الأمان المالي.")
    if metrics["Net Margin %"] < benchmarks.get("Net Margin %",0.05):
        add("عالية","الربحية","صافي الربح أقل من المستوى الآمن.","فصل أثر الإهلاكات والتمويل عن التشغيل، ومراجعة التسعير والمصاريف.","تحديد هل المشكلة تشغيلية أم محاسبية/تمويلية.")
    if metrics["DSO"] > benchmarks.get("DSO",45) and metrics["DSO"]>0:
        add("عالية","التحصيل",f"أيام التحصيل تقدر بحوالي {metrics['DSO']:.0f} يوم.","تفعيل متابعة المتأخرات، شروط دفع أوضح، وربط الخدمة بالتحصيل.","تحسين السيولة وتقليل الضغط النقدي.")
    if metrics["Payroll Ratio %"] > benchmarks.get("Payroll Ratio %",0.30):
        add("متوسطة","الرواتب","نسبة الرواتب مرتفعة مقارنة بالإيرادات.","قياس إنتاجية الفريق وربط التوظيف بنمو الإيراد.","تحسين هامش EBITDA.")
    if metrics["Opex Ratio %"] > benchmarks.get("Opex Ratio %",0.25):
        add("متوسطة","المصاريف","المصاريف التشغيلية تضغط على الربحية.","إعادة تصنيف المصاريف إلى ضرورية/قابلة للتأجيل/غير منتجة.","خفض المصاريف دون التأثير على النمو.")
    if metrics["Cash Runway Months"] < benchmarks.get("Cash Runway Months",2):
        add("عالية","السيولة","فترة الأمان النقدي منخفضة.","تأجيل المصاريف غير الضرورية وتسريع التحصيل.","تجنب عجز نقدي مفاجئ.")
    if not rec:
        add("متابعة","عام","المؤشرات الأساسية ضمن نطاق مقبول.","التركيز على تحسين جودة النمو والتحصيل.","تعزيز الاستدامة المالية.")
    return pd.DataFrame(rec)


def forecast(monthly, base_growth, opt_growth, pess_growth, months_ahead):
    if monthly.empty or "Revenue" not in monthly:
        return pd.DataFrame()
    last_rev=max(float(monthly["Revenue"].iloc[-1]), 0)
    # ignore zero tail if exists
    if last_rev==0 and monthly["Revenue"].sum()>0:
        last_rev=float(monthly.loc[monthly["Revenue"]>0,"Revenue"].iloc[-1])
    ratios={}
    for c in ["COGS","Payroll","Marketing","Opex"]:
        ratios[c]=safe_div(monthly[c].sum(), monthly["Revenue"].sum()) if c in monthly else 0
    rows=[]
    rev_b=last_rev; rev_o=last_rev; rev_p=last_rev
    for i in range(1, months_ahead+1):
        rev_b *= (1+base_growth)
        rev_o *= (1+opt_growth)
        rev_p *= (1+pess_growth)
        for scenario, rev in [("Base Case", rev_b),("Optimistic", rev_o),("Pessimistic", rev_p)]:
            cogs=rev*ratios["COGS"]; payroll=rev*ratios["Payroll"]; marketing=rev*ratios["Marketing"]; opex=rev*ratios["Opex"]
            ebitda=rev-cogs-payroll-marketing-opex
            rows.append({"Month":f"Month +{i}","Scenario":scenario,"Revenue":rev,"COGS":cogs,"Payroll":payroll,"Marketing":marketing,"Opex":opex,"EBITDA":ebitda,"EBITDA Margin %":safe_div(ebitda,rev)})
    return pd.DataFrame(rows)


def build_excel_pack(metrics, ratios_df, monthly, forecast_df, rec_df, detection_df):
    output=BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook=writer.book
        fmt_title=workbook.add_format({"bold":True,"font_size":18,"font_color":WAZEN_BLUE})
        fmt_header=workbook.add_format({"bold":True,"bg_color":WAZEN_BLUE,"font_color":"white","border":1})
        fmt_money=workbook.add_format({"num_format":"#,##0","border":1})
        fmt_pct=workbook.add_format({"num_format":"0.0%","border":1})
        fmt_text=workbook.add_format({"border":1,"text_wrap":True})
        # Executive Summary
        summary=pd.DataFrame([
            ["Revenue", metrics["Revenue"]], ["Gross Margin %", metrics["Gross Margin %"]], ["EBITDA Margin %", metrics["EBITDA Margin %"]],
            ["Net Profit", metrics["Net Profit"]], ["Break-even Revenue", metrics["Break-even Revenue"]], ["Break-even Gap", metrics["Break-even Gap"]],
            ["Cash", metrics["Cash"]], ["Cash Runway Months", metrics["Cash Runway Months"]]
        ], columns=["Metric","Value"])
        summary.to_excel(writer, sheet_name="Executive Summary", index=False, startrow=3)
        ws=writer.sheets["Executive Summary"]
        ws.write("A1","Wazen CFO Intelligence Pack",fmt_title)
        ws.write("A2","ملف تنفيذي مبسط لصاحب العمل مع مؤشرات وتحليل وتوصيات",workbook.add_format({"font_color":MUTED}))
        ws.set_column("A:A",30); ws.set_column("B:B",20)
        for i in range(4,12): ws.set_row(i,22)
        ws.conditional_format("B4:B11", {"type":"data_bar", "bar_color":WAZEN_BLUE})
        # other sheets
        for name, df in [("Monthly Data",monthly),("Ratio Analysis",ratios_df),("Forecast",forecast_df),("Action Plan",rec_df),("Data Quality",detection_df),("Glossary",GLOSSARY)]:
            df.to_excel(writer, sheet_name=name, index=False)
            w=writer.sheets[name]
            for col_num, value in enumerate(df.columns.values): w.write(0,col_num,value,fmt_header)
            w.set_column(0, max(len(df.columns)-1,0), 20)
        # Break-even sheet
        be=pd.DataFrame({"Metric":["Revenue","Variable Cost Ratio","Contribution Margin %","Fixed Costs","Break-even Revenue","Break-even Gap","Margin of Safety %"],
                         "Value":[metrics["Revenue"],metrics["Variable Cost Ratio %"],metrics["Contribution Margin %"],metrics["Fixed Costs"],metrics["Break-even Revenue"],metrics["Break-even Gap"],metrics["Margin of Safety %"]]})
        be.to_excel(writer, sheet_name="Break-even", index=False)
        w=writer.sheets["Break-even"]
        w.set_column("A:A",30); w.set_column("B:B",20)
    return output.getvalue()

# =============================
# Sidebar
# =============================
st.sidebar.markdown(f"<div style='background:{WAZEN_BLUE}; color:white; padding:20px; border-radius:12px; text-align:center; font-size:28px; letter-spacing:4px;'>WAZEN</div>", unsafe_allow_html=True)
st.sidebar.markdown("### إعدادات التحليل")
analysis_goal=st.sidebar.selectbox("ما هدف التحليل؟", ["تحليل شامل", "تحليل ربحية", "تحليل سيولة", "تحليل نقطة التعادل", "تحليل توقعات", "تحليل ملف محدد"])
sector=st.sidebar.selectbox("نوع النشاط / معيار المقارنة", list(BENCHMARKS.keys()), index=0)
months_ahead=st.sidebar.slider("عدد أشهر التوقع", 3, 12, 6)
st.sidebar.markdown("### فرضيات السيناريوهات")
base_growth=st.sidebar.number_input("Base monthly growth", -0.50, 1.00, 0.04, 0.01)
opt_growth=st.sidebar.number_input("Optimistic monthly growth", -0.50, 1.00, 0.10, 0.01)
pess_growth=st.sidebar.number_input("Pessimistic monthly growth", -0.50, 1.00, -0.03, 0.01)

# =============================
# Main UI
# =============================
st.markdown("""
<div class="wazen-hero">
  <div class="wazen-title">📊 Wazen Flexible CFO Intelligence Agent V5</div>
  <div class="wazen-subtitle">ارفع ملفاً أو أكثر: ميزان مراجعة، مبيعات شهرية، مصروفات، مبيعات أصناف. الإيجنت يكتشف نوع الملف، يبني داشبورد، نسب مالية، نقطة تعادل، سيناريوهات، قاموس مصطلحات، وملف Excel تنفيذي.</div>
</div>
""", unsafe_allow_html=True)

uploaded_files=st.file_uploader("ارفع ملف أو أكثر بصيغة Excel أو CSV", type=["xlsx","xls","csv"], accept_multiple_files=True)

if not uploaded_files:
    st.info("ابدأ برفع الملفات. يمكن رفع ميزان المراجعة + المبيعات الشهرية + المصروفات + مبيعات الأصناف معاً.")
    st.stop()

parsed_results=[]; detection=[]; product_details=[]; tb_totals={}
read_warnings=[]
for uf in uploaded_files:
    sheets, warn = read_uploaded_file(uf)
    if warn: read_warnings.append(f"{uf.name}: {warn}")
    if not sheets:
        detection.append({"File":uf.name,"Sheet":"-","Detected Type":"unreadable","Confidence":0,"Notes":warn or "تعذر القراءة","Rows":0,"Columns":0})
        continue
    for sheet_name, df in sheets.items():
        dtype, conf, notes = detect_sheet_type(df)
        detection.append({"File":uf.name,"Sheet":sheet_name,"Detected Type":dtype,"Confidence":conf,"Notes":notes,"Rows":len(df),"Columns":len(df.columns)})
        try:
            if dtype=="monthly_sales_wide":
                monthly=parse_monthly_sales_wide(df)
                parsed_results.append({"type":dtype,"file":uf.name,"sheet":sheet_name,"monthly":monthly})
            elif dtype=="expense_monthly":
                monthly, detail=parse_expense_monthly(df)
                parsed_results.append({"type":dtype,"file":uf.name,"sheet":sheet_name,"monthly":monthly,"detail":detail})
            elif dtype=="item_sales":
                monthly, product=parse_item_sales(df)
                parsed_results.append({"type":dtype,"file":uf.name,"sheet":sheet_name,"monthly":monthly,"product":product})
                if not product.empty: product_details.append(product)
            elif dtype=="monthly_summary":
                monthly=parse_monthly_summary(df)
                parsed_results.append({"type":dtype,"file":uf.name,"sheet":sheet_name,"monthly":monthly})
            elif dtype=="trial_balance":
                totals, detail=parse_trial_balance(df)
                for k,v in totals.items(): tb_totals[k]=tb_totals.get(k,0)+v
                parsed_results.append({"type":dtype,"file":uf.name,"sheet":sheet_name,"tb_totals":totals,"detail":detail})
        except Exception as e:
            detection[-1]["Notes"] += f" | خطأ أثناء التحويل: {e}"

detection_df=pd.DataFrame(detection)
if read_warnings:
    with st.expander("تنبيهات قراءة الملفات", expanded=False):
        for w in read_warnings: st.warning(w)

st.markdown("<div class='section-title'>1. اكتشاف الملفات</div>", unsafe_allow_html=True)
st.dataframe(detection_df, use_container_width=True)

monthly=combine_monthly(parsed_results)
# If there is both monthly sales wide and item sales, summing duplicates may overstate. Prefer monthly_sales_wide revenue when present.
if not monthly.empty:
    # Clean obviously duplicated revenue: if two sources loaded and revenue is too high? Leave visible to user in Data Quality.
    pass

if monthly.empty and not tb_totals:
    st.error("لم يتم استخراج بيانات قابلة للتحليل. الملفات قد تكون بتنسيق مختلف جداً، أو تحتاج Mapping يدوي في النسخة القادمة.")
    st.stop()

metrics=calculate_metrics(monthly, tb_totals)
bench=BENCHMARKS[sector]
score=health_score(metrics, bench)
rec_df=recommendations(metrics, bench)
forecast_df=forecast(monthly, base_growth, opt_growth, pess_growth, months_ahead)

# Ratio table
ratio_rows=[]
for metric in ["Gross Margin %","EBITDA Margin %","Net Margin %","Payroll Ratio %","Marketing Ratio %","Opex Ratio %","Cash Runway Months","DSO","DPO","DIO","CCC","Contribution Margin %","Margin of Safety %"]:
    actual=metrics.get(metric,0)
    target=bench.get(metric, None)
    stt, comment=status_for(metric, actual, bench) if target is not None else ("Info", "مؤشر تحليلي دون معيار ثابت")
    ratio_rows.append({"المؤشر":metric,"Actual":actual,"Benchmark":target if target is not None else "-","Status":stt,"تفسير لصاحب العمل":comment})
ratios_df=pd.DataFrame(ratio_rows)

# Owner Summary
st.markdown("<div class='section-title'>2. ملخص صاحب العمل</div>", unsafe_allow_html=True)
summary_lines=[]
summary_lines.append(f"درجة الصحة المالية التقديرية: {score}/100.")
summary_lines.append(f"الإيرادات المحللة بلغت {fmt_money(metrics['Revenue'])}. هامش مجمل الربح {fmt_pct(metrics['Gross Margin %'])}، وهامش EBITDA {fmt_pct(metrics['EBITDA Margin %'])}.")
if metrics["Break-even Gap"]>=0:
    summary_lines.append(f"الشركة فوق نقطة التعادل بفائض {fmt_money(metrics['Break-even Gap'])}، وهذا يمنحها هامش أمان {fmt_pct(metrics['Margin of Safety %'])}.")
else:
    summary_lines.append(f"الشركة تحت نقطة التعادل بفجوة {fmt_money(abs(metrics['Break-even Gap']))}. يجب معالجة الإيرادات أو التكاليف قبل التوسع.")
if metrics["Cash"]>0:
    summary_lines.append(f"النقد المتاح {fmt_money(metrics['Cash'])}، وفترة الأمان النقدي المقدرة {metrics['Cash Runway Months']:.1f} شهر.")
if metrics["DSO"]>0:
    summary_lines.append(f"أيام التحصيل التقديرية {metrics['DSO']:.0f} يوم، وهي مؤشر حساس على السيولة.")
st.markdown("<div class='owner-box'>" + "<br>".join(["• " + x for x in summary_lines]) + "</div>", unsafe_allow_html=True)

# Tabs
owner_tab, dash_tab, ratios_tab, be_tab, forecast_tab, glossary_tab, export_tab = st.tabs(["Owner Dashboard", "Charts", "Ratios", "Break-even", "Forecast", "Glossary", "Export"])

with owner_tab:
    cols=st.columns(4)
    kpis=[("Revenue", metrics["Revenue"], "إجمالي الإيرادات المحللة"),("Gross Margin", metrics["Gross Margin %"], "هامش بعد التكلفة المباشرة"),("EBITDA Margin", metrics["EBITDA Margin %"], "قوة التشغيل قبل الإهلاك والتمويل"),("Net Profit", metrics["Net Profit"], "الربح أو الخسارة النهائية")]
    for col,(label,val,note) in zip(cols,kpis):
        display=fmt_pct(val) if "%" in label or "Margin" in label else fmt_money(val)
        col.markdown(f"<div class='kpi-card'><div class='kpi-label'>{label}</div><div class='kpi-value'>{display}</div><div class='kpi-note'>{note}</div></div>", unsafe_allow_html=True)
    cols2=st.columns(4)
    kpis2=[("Health Score", score, "درجة من 100"),("Break-even Revenue", metrics["Break-even Revenue"], "الإيراد المطلوب للتعادل"),("Break-even Gap", metrics["Break-even Gap"], "الفائض أو الفجوة"),("Cash Runway", metrics["Cash Runway Months"], "عدد أشهر الأمان النقدي")]
    for col,(label,val,note) in zip(cols2,kpis2):
        display=f"{val}/100" if label=="Health Score" else f"{val:.1f} شهر" if label=="Cash Runway" and val<90 else fmt_money(val)
        col.markdown(f"<div class='kpi-card'><div class='kpi-label'>{label}</div><div class='kpi-value'>{display}</div><div class='kpi-note'>{note}</div></div>", unsafe_allow_html=True)
    st.markdown("### خطة عمل مقترحة")
    st.dataframe(rec_df, use_container_width=True)

with dash_tab:
    if not monthly.empty:
        c1,c2=st.columns(2)
        fig=go.Figure()
        fig.add_trace(go.Bar(x=monthly["Month"], y=monthly["Revenue"], name="Revenue", marker_color=WAZEN_BLUE))
        fig.add_trace(go.Scatter(x=monthly["Month"], y=monthly.get("COGS",0), name="COGS", line=dict(color=WAZEN_ORANGE)))
        fig.update_layout(title="Revenue vs Direct Cost", height=360, template="plotly_white")
        c1.plotly_chart(fig, use_container_width=True)
        margin_df=monthly.copy()
        margin_df["Gross Margin %"]=(margin_df["Revenue"]-margin_df.get("COGS",0))/margin_df["Revenue"].replace(0,np.nan)
        margin_df["EBITDA Margin %"]=(margin_df["Revenue"]-margin_df.get("COGS",0)-margin_df.get("Payroll",0)-margin_df.get("Marketing",0)-margin_df.get("Opex",0))/margin_df["Revenue"].replace(0,np.nan)
        fig2=go.Figure()
        fig2.add_trace(go.Scatter(x=margin_df["Month"], y=margin_df["Gross Margin %"], name="Gross Margin %", line=dict(color=WAZEN_BLUE)))
        fig2.add_trace(go.Scatter(x=margin_df["Month"], y=margin_df["EBITDA Margin %"], name="EBITDA Margin %", line=dict(color=WAZEN_ORANGE)))
        fig2.update_layout(title="Margin Trends", height=360, template="plotly_white", yaxis_tickformat=".0%")
        c2.plotly_chart(fig2, use_container_width=True)
        st.markdown("### البيانات الشهرية المجمعة")
        st.dataframe(monthly, use_container_width=True)
    if product_details:
        st.markdown("### أفضل الأصناف / المنتجات حسب الإيراد")
        prod=pd.concat(product_details).groupby("Item").agg({"Revenue":"sum","Quantity":"sum"}).reset_index().sort_values("Revenue",ascending=False).head(15)
        figp=px.bar(prod, x="Revenue", y="Item", orientation="h", title="Top Items by Revenue")
        st.plotly_chart(figp, use_container_width=True)

with ratios_tab:
    st.dataframe(ratios_df, use_container_width=True)
    fig=go.Figure(go.Indicator(mode="gauge+number", value=score, title={'text':'Financial Health Score'}, gauge={'axis':{'range':[0,100]}, 'bar':{'color':WAZEN_BLUE}, 'steps':[{'range':[0,50],'color':'#FEE2E2'},{'range':[50,75],'color':'#FEF3C7'},{'range':[75,100],'color':'#DCFCE7'}]}))
    fig.update_layout(height=350)
    st.plotly_chart(fig, use_container_width=True)

with be_tab:
    c1,c2=st.columns([1,1])
    be_table=pd.DataFrame({"Metric":["Revenue","Variable Cost Ratio","Contribution Margin %","Fixed Costs","Break-even Revenue","Break-even Gap","Margin of Safety %"],"Value":[metrics["Revenue"],metrics["Variable Cost Ratio %"],metrics["Contribution Margin %"],metrics["Fixed Costs"],metrics["Break-even Revenue"],metrics["Break-even Gap"],metrics["Margin of Safety %"]]})
    c1.dataframe(be_table, use_container_width=True)
    fig=go.Figure(data=[go.Bar(x=["Actual Revenue","Break-even Revenue"], y=[metrics["Revenue"], metrics["Break-even Revenue"]], marker_color=[WAZEN_BLUE, WAZEN_ORANGE])])
    fig.update_layout(title="Actual Revenue vs Break-even", template="plotly_white", height=380)
    c2.plotly_chart(fig, use_container_width=True)

with forecast_tab:
    if forecast_df.empty:
        st.info("لا توجد بيانات شهرية كافية لبناء التوقع.")
    else:
        st.dataframe(forecast_df, use_container_width=True)
        fig=px.line(forecast_df, x="Month", y="Revenue", color="Scenario", markers=True, title="Forecast Scenarios")
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("**قاعدة التوقع المستخدمة:** آخر إيراد فعلي × معدل النمو الشهري لكل سيناريو. سيتم تطويرها لاحقاً لتدمج Drivers مثل العملاء، متوسط الفاتورة، ونسب التحصيل.")

with glossary_tab:
    term=st.selectbox("اختر مصطلحاً", GLOSSARY["المصطلح العربي"].tolist())
    row=GLOSSARY[GLOSSARY["المصطلح العربي"]==term].iloc[0]
    st.markdown(f"### {row['المصطلح العربي']} | {row['English Term']}")
    st.write("**المعنى المبسط:**", row["المعنى المبسط"])
    st.write("**المعادلة:**", row["المعادلة"])
    st.write("**لماذا يهم؟**", row["لماذا يهم؟"])
    st.dataframe(GLOSSARY, use_container_width=True)

with export_tab:
    st.markdown("### تحميل CFO Pack")
    excel_bytes=build_excel_pack(metrics, ratios_df, monthly, forecast_df, rec_df, detection_df)
    st.download_button("Download Professional CFO Excel Pack", data=excel_bytes, file_name="wazen_cfo_pack_v5.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
