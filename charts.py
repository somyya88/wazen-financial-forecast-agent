import plotly.express as px
import streamlit as st

def line_chart(df, x, y, title):
    if df is None or df.empty:
        st.info("لا توجد بيانات كافية للرسم.")
        return
    fig = px.line(df, x=x, y=y, markers=True, title=title)
    fig.update_layout(height=360, margin=dict(l=20, r=20, t=55, b=20))
    st.plotly_chart(fig, use_container_width=True)

def bar_chart(df, x, y, title):
    if df is None or df.empty:
        st.info("لا توجد بيانات كافية للرسم.")
        return
    fig = px.bar(df, x=x, y=y, title=title)
    fig.update_layout(height=360, margin=dict(l=20, r=20, t=55, b=20))
    st.plotly_chart(fig, use_container_width=True)

def pie_chart(df, names, values, title):
    if df is None or df.empty:
        st.info("لا توجد بيانات كافية للرسم.")
        return
    fig = px.pie(df, names=names, values=values, title=title, hole=0.45)
    fig.update_layout(height=360, margin=dict(l=20, r=20, t=55, b=20))
    st.plotly_chart(fig, use_container_width=True)
