import pandas as pd
from utils import detect_month_columns, to_number, month_label, find_column, normalize_text

REVENUE_KEYWORDS = ["مبيعات", "ايراد", "إيراد", "revenue", "sales", "income", "صافي"]

MONTHS_AR = ["يناير", "فبراير", "مارس", "إبريل", "ابريل", "ماي", "مايو", "يونيو", "يوليو", "أغسطس", "اغسطس", "سبتمبر", "أكتوبر", "اكتوبر", "نوفمبر", "ديسمبر"]

def build_revenue_model(file_record: dict, revenue_definition: str) -> dict:
    df = file_record["primary_df"].copy()
    file_type = file_record["detected_type"]

    if file_type in ["monthly_sales_wide", "invoice_sales", "item_sales", "unknown"]:
        result = _revenue_from_sales_file(df, revenue_definition)
    elif file_type == "trial_balance":
        result = _revenue_from_trial_balance(df)
    else:
        result = {"monthly_revenue": pd.DataFrame(columns=["month", "revenue"]), "total_revenue": 0, "notes": ["Unsupported revenue source"]}

    result["source_file"] = file_record["file_name"]
    result["revenue_definition"] = revenue_definition
    return result

def _target_metric_keywords(revenue_definition: str) -> list[str]:
    rd = normalize_text(revenue_definition)
    if "including vat" in rd or "شامل" in rd:
        return ["شامل الضريبة", "including vat", "gross sales"]
    if "before discount" in rd:
        return ["قبل الخصم", "gross before discount"]
    if "after discount" in rd:
        return ["بدون ضريبة", "صافي", "after discount", "net sales"]
    # Default for analysis: net/excluding VAT
    return ["بدون ضريبة", "صافي المبيعات", "excluding vat", "net sales"]

def _try_metric_block_layout(df: pd.DataFrame, revenue_definition: str) -> dict | None:
    """
    Handles reports shaped like:
    Row 1: Jan | NaN | Feb | NaN ...
    Row 2: amount | discount | amount | discount ...
    Row 4: amount | Net sales excluding VAT | amount | Net sales excluding VAT ...
    """
    if df is None or df.empty:
        return None

    work = df.copy()
    month_positions = []

    # Find cells that contain month names.
    for r in range(min(len(work), 8)):
        for c in range(work.shape[1]):
            val = str(work.iat[r, c]).strip()
            if any(m == val or m in val for m in MONTHS_AR):
                month_positions.append((r, c, val))

    if len(month_positions) < 2:
        return None

    keywords = _target_metric_keywords(revenue_definition)
    monthly = []
    notes = ["تمت قراءة ملف المبيعات بتخطيط خاص: كل شهر له عمود مبلغ وعمود وصف مجاور."]

    for month_row, amount_col, month_name in month_positions:
        label_col = amount_col + 1 if amount_col + 1 < work.shape[1] else None
        found_value = None

        # Search below the month row for the target metric label in adjacent label column.
        for r in range(month_row + 1, min(len(work), month_row + 12)):
            label_text = ""
            if label_col is not None:
                label_text += " " + str(work.iat[r, label_col])
            # Some exports may put label and amount in same or nearby cells.
            label_text += " " + " ".join(str(work.iat[r, cc]) for cc in range(max(0, amount_col-1), min(work.shape[1], amount_col+3)))
            nlabel = normalize_text(label_text)

            if any(normalize_text(k) in nlabel for k in keywords):
                value = to_number(pd.Series([work.iat[r, amount_col]])).iloc[0]
                found_value = float(value)
                break

        if found_value is not None:
            monthly.append({"month": month_label(month_name), "revenue": found_value})

    if monthly:
        out = pd.DataFrame(monthly)
        return {"monthly_revenue": out, "total_revenue": float(out["revenue"].sum()), "notes": notes}

    return None

def _revenue_from_sales_file(df: pd.DataFrame, revenue_definition: str) -> dict:
    notes = []

    # First handle non-standard monthly metric blocks.
    block_result = _try_metric_block_layout(df, revenue_definition)
    if block_result is not None:
        return block_result

    month_cols = detect_month_columns(list(df.columns))

    if month_cols:
        # Try to exclude duplicated total rows if they exist.
        text_cols = [c for c in df.columns if df[c].dtype == "object"]
        mask_total = pd.Series(False, index=df.index)
        for c in text_cols:
            mask_total = mask_total | df[c].astype(str).str.contains("الإجمالي|اجمالي|total", case=False, na=False)
        detail_df = df[~mask_total].copy()
        if mask_total.any():
            notes.append("تم استبعاد صفوف إجمالي محتملة لمنع التكرار.")

        monthly = []
        for col in month_cols:
            monthly.append({"month": month_label(col), "revenue": float(to_number(detail_df[col]).sum())})
        out = pd.DataFrame(monthly)
        return {"monthly_revenue": out, "total_revenue": float(out["revenue"].sum()), "notes": notes}

    # Long sales file
    amount_col = find_column(df, ["net sales", "صافي المبيعات", "amount", "المبلغ", "total", "الإجمالي", "sales"])
    date_col = find_column(df, ["date", "التاريخ", "month", "الشهر"])
    if amount_col:
        df["_amount"] = to_number(df[amount_col])
        if date_col:
            dates = pd.to_datetime(df[date_col], errors="coerce")
            df["_month"] = dates.dt.strftime("%b").fillna(df[date_col].astype(str))
        else:
            df["_month"] = "Total"
        out = df.groupby("_month", as_index=False)["_amount"].sum().rename(columns={"_month": "month", "_amount": "revenue"})
        return {"monthly_revenue": out, "total_revenue": float(out["revenue"].sum()), "notes": notes}

    return {"monthly_revenue": pd.DataFrame(columns=["month", "revenue"]), "total_revenue": 0, "notes": ["لم يتم العثور على عمود إيراد واضح. قد يكون الملف بتخطيط غير قياسي يحتاج Mapping خاص."]}

def _revenue_from_trial_balance(df: pd.DataFrame) -> dict:
    account_col = find_column(df, ["اسم الحساب", "account name", "account", "الحساب", "البيان"])
    debit_col = find_column(df, ["debit", "مدين", "الحركة المدينة", "closing debit"])
    credit_col = find_column(df, ["credit", "دائن", "الحركة الدائنة", "closing credit"])
    notes = ["تم استخراج الإيرادات من ميزان المراجعة بناءً على كلمات مفتاحية. يفضل استخدامه للتحقق إذا توفر ملف مبيعات رسمي."]

    if not account_col:
        return {"monthly_revenue": pd.DataFrame([{"month": "Total", "revenue": 0}]), "total_revenue": 0, "notes": ["لم يتم تحديد عمود الحساب."]}

    rev_mask = df[account_col].astype(str).apply(lambda x: any(k in normalize_text(x) for k in REVENUE_KEYWORDS))
    subset = df[rev_mask].copy()

    if credit_col:
        total = float(to_number(subset[credit_col]).sum())
    elif debit_col:
        total = abs(float(to_number(subset[debit_col]).sum()))
    else:
        total = 0
        notes.append("لم يتم العثور على أعمدة مدين/دائن.")

    return {"monthly_revenue": pd.DataFrame([{"month": "Total", "revenue": total}]), "total_revenue": total, "notes": notes}
