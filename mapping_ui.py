import pandas as pd
import streamlit as st

CATEGORY_OPTIONS = [
    "Cost of Revenue",
    "Purchases",
    "Payroll",
    "Rent",
    "Utilities",
    "Maintenance",
    "Fuel",
    "Spare Parts",
    "Depreciation",
    "Finance Costs",
    "Bank Charges",
    "Selling & Marketing",
    "Administrative Expenses",
    "Other Opex",
]
COST_BEHAVIOR_OPTIONS = ["Fixed", "Variable", "Semi-variable"]

def _numeric(series):
    return pd.to_numeric(series, errors="coerce").fillna(0)

def render_expense_mapping_editor(mapping_df: pd.DataFrame, key_prefix: str = "expense_mapping"):
    if mapping_df is None or mapping_df.empty:
        st.info("لا توجد بنود مصاريف للتصنيف.")
        return mapping_df

    required = ["account_name", "current_category", "user_category", "cost_behavior", "amount"]
    base = mapping_df.copy()
    for col in required:
        if col not in base.columns:
            base[col] = "" if col != "amount" else 0
    base["amount"] = _numeric(base["amount"])

    st.markdown("#### فلاتر التصنيف")

    c1, c2, c3, c4 = st.columns([1.3, 1, 1, 1])
    with c1:
        search_text = st.text_input("بحث باسم الحساب", value="", key=f"{key_prefix}_search")
    with c2:
        current_options = ["الكل"] + sorted([x for x in base["current_category"].dropna().astype(str).unique() if x])
        current_filter = st.selectbox("التصنيف الحالي", current_options, key=f"{key_prefix}_current")
    with c3:
        approved_options = ["الكل"] + sorted([x for x in base["user_category"].dropna().astype(str).unique() if x])
        approved_filter = st.selectbox("التصنيف المعتمد", approved_options, key=f"{key_prefix}_approved")
    with c4:
        behavior_filter = st.selectbox("نوع التكلفة", ["الكل"] + COST_BEHAVIOR_OPTIONS, key=f"{key_prefix}_behavior")

    c5, c6, c7, c8 = st.columns([1, 1, 1, 1])
    with c5:
        only_other = st.checkbox("Other Opex فقط", value=False, key=f"{key_prefix}_other")
    with c6:
        only_large = st.checkbox("البنود الكبيرة فقط", value=False, key=f"{key_prefix}_large")
    with c7:
        min_amount = st.number_input("حد أدنى للمبلغ", min_value=0.0, value=0.0, step=1000.0, key=f"{key_prefix}_min")
    with c8:
        max_rows = st.number_input("عدد الصفوف", min_value=10, max_value=500, value=120, step=10, key=f"{key_prefix}_rows")

    filtered = base.copy()
    if search_text:
        filtered = filtered[filtered["account_name"].astype(str).str.contains(search_text, case=False, na=False)]
    if current_filter != "الكل":
        filtered = filtered[filtered["current_category"].astype(str) == current_filter]
    if approved_filter != "الكل":
        filtered = filtered[filtered["user_category"].astype(str) == approved_filter]
    if behavior_filter != "الكل":
        filtered = filtered[filtered["cost_behavior"].astype(str) == behavior_filter]
    if only_other:
        filtered = filtered[
            filtered["current_category"].astype(str).str.contains("Other", case=False, na=False)
            | filtered["user_category"].astype(str).str.contains("Other", case=False, na=False)
        ]
    if only_large:
        threshold = base["amount"].quantile(0.75) if len(base) else 0
        filtered = filtered[filtered["amount"] >= threshold]
    if min_amount > 0:
        filtered = filtered[filtered["amount"] >= min_amount]

    filtered = filtered.sort_values("amount", ascending=False).head(int(max_rows))

    total_amount = base["amount"].sum()
    shown_amount = filtered["amount"].sum()
    other_amount = base.loc[base["user_category"].astype(str).str.contains("Other", case=False, na=False), "amount"].sum()
    other_pct = (other_amount / total_amount * 100) if total_amount else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("إجمالي البنود", f"{len(base):,}")
    m2.metric("البنود المعروضة", f"{len(filtered):,}")
    m3.metric("قيمة البنود المعروضة", f"{shown_amount:,.0f}")
    m4.metric("Other Opex", f"{other_pct:.1f}%")

    st.caption("التعديلات تتم على الصفوف المعروضة فقط، ثم تُدمج تلقائياً مع كامل جدول التصنيف عند الحفظ.")

    edited = st.data_editor(
        filtered[[c for c in ["account_name", "current_category", "user_category", "cost_behavior", "amount", "classification_confidence", "classification_source", "classification_reason"] if c in filtered.columns]],
        use_container_width=True,
        hide_index=False,
        column_config={
            "account_name": st.column_config.TextColumn("الحساب", disabled=True),
            "current_category": st.column_config.TextColumn("التصنيف المقترح", disabled=True),
            "user_category": st.column_config.SelectboxColumn("التصنيف المعتمد", options=CATEGORY_OPTIONS, required=True),
            "cost_behavior": st.column_config.SelectboxColumn("نوع التكلفة", options=COST_BEHAVIOR_OPTIONS, required=True),
            "amount": st.column_config.NumberColumn("المبلغ", format="%.2f", disabled=True),
            "classification_confidence": st.column_config.NumberColumn("الثقة", disabled=True, format="%d"),
            "classification_source": st.column_config.TextColumn("المصدر", disabled=True),
            "classification_reason": st.column_config.TextColumn("سبب التصنيف", disabled=True),
        },
        key=f"{key_prefix}_editor",
        num_rows="fixed",
    )

    updated = base.copy()
    for idx, row in edited.iterrows():
        if idx in updated.index:
            updated.at[idx, "user_category"] = row["user_category"]
            updated.at[idx, "cost_behavior"] = row["cost_behavior"]

    return updated
