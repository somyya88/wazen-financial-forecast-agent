import html
import pandas as pd
import streamlit as st

WAZEN_BLUE = "#17479E"
WAZEN_ORANGE = "#FAA61A"
WAZEN_BG = "#F7F9FC"
WAZEN_BORDER = "#E6EAF0"
TEXT_DARK = "#1F2D3D"

MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTH_AR = {
    "Jan": "يناير",
    "Feb": "فبراير",
    "Mar": "مارس",
    "Apr": "أبريل",
    "May": "مايو",
    "Jun": "يونيو",
    "Jul": "يوليو",
    "Aug": "أغسطس",
    "Sep": "سبتمبر",
    "Oct": "أكتوبر",
    "Nov": "نوفمبر",
    "Dec": "ديسمبر",
}

def sort_month_df(df: pd.DataFrame, month_col: str = "month") -> pd.DataFrame:
    if df is None or df.empty or month_col not in df.columns:
        return df if df is not None else pd.DataFrame()
    out = df.copy()
    out["_month_order"] = out[month_col].map(lambda x: MONTH_ORDER.index(str(x)) if str(x) in MONTH_ORDER else 99)
    out = out.sort_values("_month_order").drop(columns=["_month_order"])
    return out

def fmt_money(value, decimals: int = 0) -> str:
    try:
        v = float(value)
    except Exception:
        return "—"
    if abs(v) < 0.000001:
        v = 0
    if v < 0:
        return f"({abs(v):,.{decimals}f})"
    return f"{v:,.{decimals}f}"

def fmt_percent(value, decimals: int = 1) -> str:
    try:
        v = float(value)
    except Exception:
        return "—"
    if abs(v) <= 1.5:
        v *= 100
    return f"{v:.{decimals}f}%"

def e(value) -> str:
    return html.escape("" if value is None else str(value))

def render_html_table(
    df: pd.DataFrame,
    columns: list[str],
    money_cols: list[str] | None = None,
    percent_cols: list[str] | None = None,
    title: str | None = None,
    total_markers: list[str] | None = None,
    strong_markers: list[str] | None = None,
    tooltip_map: dict[str, str] | None = None,
    expense_drilldown: bool = False,
):
    if df is None or df.empty:
        st.info("لا توجد بيانات كافية للعرض.")
        return

    money_cols = money_cols or []
    percent_cols = percent_cols or []
    total_markers = total_markers or []
    strong_markers = strong_markers or []
    tooltip_map = tooltip_map or {}

    show = df.copy()
    show = show[[c for c in columns if c in show.columns]]

    if title:
        st.markdown(f'<div class="wazen-table-title">{e(title)}</div>', unsafe_allow_html=True)

    thead = "".join([f"<th>{e(c)}</th>" for c in show.columns])
    rows = []
    for _, row in show.iterrows():
        joined = " ".join([str(row.get(c, "")) for c in show.columns])
        row_class = ""
        if any(marker in joined for marker in strong_markers):
            row_class = " strong-row"
        elif any(marker in joined for marker in total_markers):
            row_class = " total-row"

        # Add visual separators for statement blocks.
        if "Total Revenue" in joined or "إجمالي الإيرادات" in joined:
            row_class += " revenue-total"
        if "COGS" in joined or "تكلفة المبيعات" in joined:
            row_class += " cogs-total"
        if "Gross Profit" in joined or "مجمل الربح" in joined:
            row_class += " gross-profit"
        if "Operating Expenses" in joined or "المصروفات" in joined:
            row_class += " opex-row"
        if "Net Profit" in joined or "صافي الربح" in joined:
            row_class += " net-profit-row"

        row_tooltip = ""
        for marker, tip in tooltip_map.items():
            if marker in joined:
                row_tooltip = f' title="{e(tip)}"'
                break

        cells = []
        for c in show.columns:
            val = row.get(c, "")
            cls = ""
            if c in money_cols:
                cls = "num"
                val = fmt_money(val, 0)
            elif c in percent_cols:
                cls = "num pct"
                val = fmt_percent(val, 1)

            # Make operating expense row visually actionable.
            if expense_drilldown and c in ["العربي", "English"] and ("Operating Expenses" in joined or "المصروفات" in joined):
                val = f'<a href="#expense-drilldown" class="table-link">{e(val)}</a>'
                cells.append(f'<td class="{cls}"{row_tooltip}>{val}</td>')
            else:
                cells.append(f'<td class="{cls}"{row_tooltip}>{e(val)}</td>')

        rows.append(f'<tr class="{row_class}"{row_tooltip}>' + "".join(cells) + "</tr>")

    html_table = f"""
    <div class="wazen-table-wrap">
        <table class="wazen-table">
            <thead><tr>{thead}</tr></thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    </div>
    """
    st.markdown(html_table, unsafe_allow_html=True)

def render_pnl_statement(pnl_df: pd.DataFrame):
    if pnl_df is None or pnl_df.empty:
        st.info("لا توجد قائمة دخل.")
        return
    out = pnl_df.copy()
    if "العربي" in out.columns and "English" in out.columns and "Amount" in out.columns:
        out = out[["العربي", "English", "Amount"]]
    total_markers = ["إجمالي الإيرادات", "تكلفة المبيعات", "مجمل الربح", "المصروفات", "Total Revenue", "COGS", "Gross Profit", "Operating Expenses"]
    strong_markers = ["صافي الربح", "Net Profit"]
    render_html_table(
        out,
        columns=["العربي", "English", "Amount"],
        money_cols=["Amount"],
        total_markers=total_markers,
        strong_markers=strong_markers,
        expense_drilldown=True,
    )

def build_monthly_profitability_table(monthly_pnl_df: pd.DataFrame, pnl_model: dict) -> pd.DataFrame:
    if monthly_pnl_df is None or monthly_pnl_df.empty:
        return pd.DataFrame()

    df = sort_month_df(monthly_pnl_df, "month").copy()
    for col in ["revenue", "expenses"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    total_revenue = df["revenue"].sum()
    tb_net_purchases = float(pnl_model.get("net_purchases", pnl_model.get("cogs", 0)) or 0)

    if total_revenue:
        df["net_purchases_allocated"] = df["revenue"] / total_revenue * tb_net_purchases
    else:
        df["net_purchases_allocated"] = 0

    df["operating_profit_before_opex"] = df["revenue"] - df["net_purchases_allocated"]
    df["operating_profit_margin"] = df.apply(lambda r: r["operating_profit_before_opex"] / r["revenue"] if r["revenue"] else 0, axis=1)
    df["net_profit"] = df["revenue"] - df["net_purchases_allocated"] - df["expenses"]
    df["net_profit_margin"] = df.apply(lambda r: r["net_profit"] / r["revenue"] if r["revenue"] else 0, axis=1)

    return pd.DataFrame({
        "الشهر": df["month"].map(lambda x: MONTH_AR.get(str(x), str(x))),
        "الإيراد": df["revenue"],
        "صافي المشتريات": df["net_purchases_allocated"],
        "هامش الربح التشغيلي": df["operating_profit_margin"],
        "_operating_profit_amount": df["operating_profit_before_opex"],
        "المصاريف": df["expenses"],
        "صافي الربح": df["net_profit"],
        "نسبة صافي الربح": df["net_profit_margin"],
    })

def render_monthly_profitability(monthly_pnl_df: pd.DataFrame, pnl_model: dict):
    table = build_monthly_profitability_table(monthly_pnl_df, pnl_model)
    if table.empty:
        st.info("لا توجد بيانات شهرية كافية.")
        return table
    # Build row-level tooltips for operating profit margin.
    tooltip_map = {}
    for _, r in table.iterrows():
        tip = f"الربح التشغيلي قبل المصاريف: {fmt_money(r.get('_operating_profit_amount', 0), 0)}"
        tooltip_map[str(r.get('الشهر', ''))] = tip

    render_html_table(
        table,
        columns=["الشهر", "الإيراد", "صافي المشتريات", "هامش الربح التشغيلي", "المصاريف", "صافي الربح", "نسبة صافي الربح"],
        money_cols=["الإيراد", "صافي المشتريات", "المصاريف", "صافي الربح"],
        percent_cols=["هامش الربح التشغيلي", "نسبة صافي الربح"],
        tooltip_map=tooltip_map,
    )
    st.caption("ملاحظة: صافي المشتريات الشهري موزع تحليلياً حسب وزن الإيراد الشهري لأن المصدر الرسمي للمشتريات هو ميزان المراجعة.")
    return table

def render_ratios_table(ratios_df: pd.DataFrame):
    if ratios_df is None or ratios_df.empty:
        st.info("لا توجد نسب كافية.")
        return
    out = ratios_df.copy()
    out = out.rename(columns={"Value": "القيمة", "Why it matters": "لماذا يهم؟"})
    render_html_table(
        out,
        columns=["العربي", "English", "القيمة", "لماذا يهم؟"],
        percent_cols=["القيمة"],
    )

def render_simple_financial_table(df: pd.DataFrame, columns: list[str], money_cols=None, percent_cols=None, title=None):
    render_html_table(df, columns=columns, money_cols=money_cols or [], percent_cols=percent_cols or [], title=title)


def render_insight_panel(title: str, status: str, risk: str, decision: str, bullets: list[str] | None = None):
    bullets = bullets or []
    bullet_html = "".join([f"<li>{e(b)}</li>" for b in bullets])
    html_block = f"""
    <div class="insight-panel">
        <div class="insight-title">{e(title)}</div>
        <div class="insight-status">{e(status)}</div>
        <div class="insight-grid">
            <div class="insight-box">
                <div class="insight-box-label">الخطر الأهم</div>
                <div class="insight-box-text">{e(risk)}</div>
            </div>
            <div class="insight-box">
                <div class="insight-box-label">القرار المقترح</div>
                <div class="insight-box-text">{e(decision)}</div>
            </div>
        </div>
        <ul class="insight-bullets">{bullet_html}</ul>
    </div>
    """
    st.markdown(html_block, unsafe_allow_html=True)
