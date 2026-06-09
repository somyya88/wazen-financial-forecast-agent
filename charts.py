import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

WAZEN_BLUE = "#17479E"
WAZEN_ORANGE = "#FAA61A"
MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def _prepare_xy(df, x, y):
    out = df.copy()
    if x not in out.columns or y not in out.columns:
        return pd.DataFrame()
    out[y] = pd.to_numeric(out[y], errors="coerce")
    out = out.dropna(subset=[x, y])
    if x == "month":
        out["_order"] = out[x].map(lambda m: MONTH_ORDER.index(str(m)) if str(m) in MONTH_ORDER else 99)
        out = out.sort_values("_order").drop(columns=["_order"])
    return out

def line_chart(df, x, y, title):
    if df is None or df.empty:
        st.info("لا توجد بيانات كافية للرسم.")
        return
    out = _prepare_xy(df, x, y)
    if out.empty:
        st.info("لا توجد بيانات رقمية صالحة للرسم.")
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=out[x].astype(str),
        y=out[y],
        mode="lines+markers+text",
        line=dict(color=WAZEN_BLUE, width=3),
        marker=dict(color=WAZEN_ORANGE, size=9, line=dict(color="white", width=1.5)),
        text=[f"{v:,.0f}" for v in out[y]],
        textposition="top center",
        hovertemplate="%{x}<br>%{y:,.0f}<extra></extra>",
        name=title,
    ))
    fig.update_layout(
        title=dict(text=title, x=1, xanchor="right"),
        height=380,
        margin=dict(l=20, r=25, t=60, b=40),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Tajawal, Arial", color="#344054"),
        xaxis=dict(showgrid=False, title=""),
        yaxis=dict(showgrid=True, gridcolor="#E6EAF0", title=""),
    )
    st.plotly_chart(fig, use_container_width=True)

def bar_chart(df, x, y, title):
    if df is None or df.empty:
        st.info("لا توجد بيانات كافية للرسم.")
        return
    out = _prepare_xy(df, x, y)
    if out.empty:
        st.info("لا توجد بيانات رقمية صالحة للرسم.")
        return
    fig = px.bar(out, x=x, y=y, title=title, text_auto=".2s")
    fig.update_traces(marker_color=WAZEN_BLUE)
    fig.update_layout(
        height=360,
        margin=dict(l=20, r=20, t=55, b=20),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Tajawal, Arial", color="#344054"),
        xaxis=dict(showgrid=False, title=""),
        yaxis=dict(showgrid=True, gridcolor="#E6EAF0", title=""),
    )
    st.plotly_chart(fig, use_container_width=True)

def pie_chart(df, names, values, title):
    if df is None or df.empty:
        st.info("لا توجد بيانات كافية للرسم.")
        return
    out = df.copy()
    out[values] = pd.to_numeric(out[values], errors="coerce")
    out = out.dropna(subset=[names, values])
    if out.empty:
        st.info("لا توجد بيانات رقمية صالحة للرسم.")
        return
    fig = px.pie(out, names=names, values=values, title=title, hole=0.45)
    fig.update_layout(
        height=360,
        margin=dict(l=20, r=20, t=55, b=20),
        font=dict(family="Tajawal, Arial", color="#344054"),
    )
    st.plotly_chart(fig, use_container_width=True)
