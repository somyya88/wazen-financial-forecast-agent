import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from openai import OpenAI
from sklearn.linear_model import LinearRegression

st.set_page_config(
    page_title="Wazen Financial Forecast Agent",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Wazen Financial Forecast Agent")
st.caption("Financial analysis, KPI engine, forecasting, and CFO-style insights")

st.markdown("""
ارفع ملف Excel يحتوي على بيانات مالية شهرية، وسيقوم النظام بـ:

- قراءة البيانات المالية.
- حساب المؤشرات الأساسية.
- بناء توقع مالي مبسط.
- إنشاء سيناريوهات.
- توليد تقرير CFO تنفيذي باستخدام الذكاء الاصطناعي.
""")

# -----------------------------
# Helper Functions
# -----------------------------

def normalize_columns(df):
    df.columns = [str(c).strip() for c in df.columns]
    return df


def find_column(df, possible_names):
    for col in df.columns:
        clean_col = str(col).strip().lower()
        for name in possible_names:
            if name.lower() in clean_col:
                return col
    return None


def prepare_financial_data(df):
    df = normalize_columns(df)

    month_col = find_column(df, ["month", "date", "period", "الشهر", "التاريخ", "الفترة"])
    revenue_col = find_column(df, ["revenue", "sales", "income", "الإيرادات", "المبيعات", "الدخل"])
    cogs_col = find_column(df, ["cogs", "cost of sales", "direct cost", "تكلفة", "تكلفة مباشرة"])
    payroll_col = find_column(df, ["payroll", "salary", "salaries", "رواتب", "الأجور"])
    marketing_col = find_column(df, ["marketing", "ads", "advertising", "تسويق", "إعلانات"])
    opex_col = find_column(df, ["opex", "operating expenses", "admin", "general", "مصاريف", "إدارية", "تشغيلية"])
    cash_col = find_column(df, ["cash", "bank", "النقد", "البنك", "رصيد"])
    clients_col = find_column(df, ["clients", "customers", "العملاء", "عدد العملاء"])

    required = {
        "month": month_col,
        "revenue": revenue_col,
        "cogs": cogs_col,
        "payroll": payroll_col,
        "marketing": marketing_col,
        "opex": opex_col,
        "cash": cash_col,
        "clients": clients_col
    }

    return required


def calculate_kpis(df, cols):
    data = df.copy()

    revenue = pd.to_numeric(data[cols["revenue"]], errors="coerce").fillna(0)
    cogs = pd.to_numeric(data[cols["cogs"]], errors="coerce").fillna(0) if cols["cogs"] else 0
    payroll = pd.to_numeric(data[cols["payroll"]], errors="coerce").fillna(0) if cols["payroll"] else 0
    marketing = pd.to_numeric(data[cols["marketing"]], errors="coerce").fillna(0) if cols["marketing"] else 0
    opex = pd.to_numeric(data[cols["opex"]], errors="coerce").fillna(0) if cols["opex"] else 0
    cash = pd.to_numeric(data[cols["cash"]], errors="coerce").fillna(0) if cols["cash"] else 0
    clients = pd.to_numeric(data[cols["clients"]], errors="coerce").fillna(0) if cols["clients"] else 0

    data["Revenue"] = revenue
    data["COGS"] = cogs
    data["Payroll"] = payroll
    data["Marketing"] = marketing
    data["Opex"] = opex
    data["Cash"] = cash
    data["Clients"] = clients

    data["Gross Profit"] = data["Revenue"] - data["COGS"]
    data["EBITDA"] = data["Gross Profit"] - data["Payroll"] - data["Marketing"] - data["Opex"]
    data["Net Profit"] = data["EBITDA"]

    data["Gross Margin %"] = np.where(data["Revenue"] != 0, data["Gross Profit"] / data["Revenue"], 0)
    data["EBITDA Margin %"] = np.where(data["Revenue"] != 0, data["EBITDA"] / data["Revenue"], 0)
    data["Net Margin %"] = np.where(data["Revenue"] != 0, data["Net Profit"] / data["Revenue"], 0)
    data["Payroll Ratio %"] = np.where(data["Revenue"] != 0, data["Payroll"] / data["Revenue"], 0)
    data["Marketing Ratio %"] = np.where(data["Revenue"] != 0, data["Marketing"] / data["Revenue"], 0)

    data["ARPU"] = np.where(data["Clients"] != 0, data["Revenue"] / data["Clients"], 0)

    return data


def forecast_revenue(data, months_ahead=6):
    y = data["Revenue"].values.reshape(-1, 1)
    x = np.arange(len(y)).reshape(-1, 1)

    if len(data) < 2:
        return pd.DataFrame()

    model = LinearRegression()
    model.fit(x, y)

    future_x = np.arange(len(y), len(y) + months_ahead).reshape(-1, 1)
    forecast = model.predict(future_x).flatten()

    forecast = np.maximum(forecast, 0)

    return pd.DataFrame({
        "Forecast Month": [f"Month +{i}" for i in range(1, months_ahead + 1)],
        "Base Case Revenue": forecast,
        "Optimistic Revenue": forecast * 1.15,
        "Pessimistic Revenue": forecast * 0.85
    })


def generate_ai_report(summary_text):
    try:
        api_key = st.secrets.get("OPENAI_API_KEY", None)

        if not api_key:
            return "لم يتم إضافة OpenAI API Key بعد. أضيفيه لاحقاً من إعدادات Streamlit Secrets حتى يظهر تقرير CFO الذكي."

        client = OpenAI(api_key=api_key)

        prompt = f"""
أنت CFO محترف ومستشار مالي تنفيذي.

حلل البيانات التالية واكتب تقريراً مالياً تنفيذياً باللغة العربية.

المطلوب:
1. ملخص تنفيذي.
2. قراءة الإيرادات.
3. قراءة الربحية.
4. قراءة المصاريف.
5. قراءة السيولة إن وجدت.
6. المخاطر الرئيسية.
7. توصيات عملية للإدارة.
8. أسئلة يجب طرحها على الإدارة قبل اتخاذ القرار.

اكتب بأسلوب مهني مباشر، غير إنشائي، وغير عام.

البيانات:
{summary_text}
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a senior CFO financial analysis agent."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"حدث خطأ أثناء توليد تقرير الذكاء الاصطناعي: {e}"


# -----------------------------
# Upload File
# -----------------------------

uploaded_file = st.file_uploader(
    "ارفعي ملف Excel للبيانات المالية الشهرية",
    type=["xlsx", "xls", "csv"]
)

st.info("""
صيغة الملف المقترحة:

Month | Revenue | COGS | Payroll | Marketing | Opex | Cash | Clients

يمكن أن تكون أسماء الأعمدة بالعربية أو الإنجليزية.
""")

if uploaded_file is not None:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.subheader("1. البيانات المرفوعة")
    st.dataframe(df, use_container_width=True)

    cols = prepare_financial_data(df)

    st.subheader("2. قراءة الأعمدة")
    st.write(cols)

    if cols["revenue"] is None:
        st.error("لم أستطع تحديد عمود الإيرادات. يجب أن يحتوي الملف على عمود Revenue أو Sales أو الإيرادات.")
        st.stop()

    data = calculate_kpis(df, cols)

    st.subheader("3. المؤشرات المالية")
    latest = data.iloc[-1]

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Revenue", f"{latest['Revenue']:,.0f}")
    col2.metric("Gross Margin", f"{latest['Gross Margin %']:.1%}")
    col3.metric("EBITDA Margin", f"{latest['EBITDA Margin %']:.1%}")
    col4.metric("Net Profit", f"{latest['Net Profit']:,.0f}")

    st.dataframe(data, use_container_width=True)

    st.subheader("4. اتجاه الإيرادات")

    month_display = cols["month"] if cols["month"] else data.index

    chart_df = data.copy()
    if cols["month"]:
        chart_df["Month_Display"] = chart_df[cols["month"]].astype(str)
    else:
        chart_df["Month_Display"] = chart_df.index.astype(str)

    fig = px.line(
        chart_df,
        x="Month_Display",
        y="Revenue",
        markers=True,
        title="Revenue Trend"
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("5. التوقع المالي")

    forecast_df = forecast_revenue(data, months_ahead=6)

    if forecast_df.empty:
        st.warning("نحتاج شهرين على الأقل لبناء توقع مالي.")
    else:
        st.dataframe(forecast_df, use_container_width=True)

        fig2 = px.line(
            forecast_df,
            x="Forecast Month",
            y=["Base Case Revenue", "Optimistic Revenue", "Pessimistic Revenue"],
            markers=True,
            title="Revenue Forecast Scenarios"
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("6. تقرير CFO Agent")

    summary_text = f"""
Total Revenue: {data['Revenue'].sum():,.2f}
Average Revenue: {data['Revenue'].mean():,.2f}
Latest Revenue: {latest['Revenue']:,.2f}
Latest Gross Margin: {latest['Gross Margin %']:.2%}
Latest EBITDA Margin: {latest['EBITDA Margin %']:.2%}
Latest Net Profit: {latest['Net Profit']:,.2f}
Latest Payroll Ratio: {latest['Payroll Ratio %']:.2%}
Latest Marketing Ratio: {latest['Marketing Ratio %']:.2%}
Latest Cash: {latest['Cash']:,.2f}
Latest Clients: {latest['Clients']:,.0f}
Latest ARPU: {latest['ARPU']:,.2f}

Forecast:
{forecast_df.to_string(index=False) if not forecast_df.empty else "No forecast available"}
"""

    if st.button("Generate CFO Report"):
        report = generate_ai_report(summary_text)
        st.markdown(report)

    st.subheader("7. تحميل النتائج")

    output = data.copy()
    csv = output.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        label="Download analyzed data as CSV",
        data=csv,
        file_name="wazen_financial_analysis.csv",
        mime="text/csv"
    )

else:
    st.warning("ارفعي ملف Excel أو CSV للبدء.")
