from __future__ import annotations

import re
import pandas as pd
from utils import normalize_text, to_number, find_column, month_label, detect_month_columns

MONTHS_AR = ["يناير","فبراير","مارس","إبريل","أبريل","ابريل","ماي","مايو","يونيو","يوليو","أغسطس","اغسطس","سبتمبر","أكتوبر","اكتوبر","نوفمبر","ديسمبر"]


def _number(x) -> float:
    try:
        return float(to_number(pd.Series([x])).iloc[0] or 0)
    except Exception:
        try:
            return float(x or 0)
        except Exception:
            return 0.0


def _is_liquidity_total_row(row) -> bool:
    text = " ".join([str(x) for x in row.values if str(x).lower() != "nan"])
    return "الأموال الجاهزة" in text or "الاموال الجاهزة" in text or "cash" in normalize_text(text)


def parse_cash_liquidity_report(file_record: dict | None) -> dict:
    if not file_record:
        return {"available": False, "monthly": pd.DataFrame(), "accounts": pd.DataFrame(), "cards": {}, "notes": ["تقرير السيولة غير متوفر."]}
    df = file_record.get("primary_df", pd.DataFrame()).copy()
    if df.empty:
        return {"available": False, "monthly": pd.DataFrame(), "accounts": pd.DataFrame(), "cards": {}, "notes": ["تقرير السيولة فارغ أو غير قابل للقراءة."]}

    # Handles raw layout: row 0 headers, rows triplets: debit/credit/balance.
    work = df.copy()
    # If the first row looks like headers, promote it.
    first = [str(x).strip() for x in work.iloc[0].tolist()] if len(work) else []
    if any("يناير" in x or "فبراير" in x or "الإجمالي" in x for x in first):
        work.columns = first
        work = work.iloc[1:].reset_index(drop=True)

    cols = list(work.columns)
    month_cols = [c for c in cols if any(m == str(c).strip() or m in str(c) for m in MONTHS_AR)]
    total_col = next((c for c in cols if "إجمالي" in str(c) or "اجمالي" in str(c) or "total" in str(c).lower()), None)

    # Try identify type/movement column.
    type_col = None
    for c in cols:
        vals = " ".join(work[c].astype(str).head(12).tolist())
        if any(x in vals for x in ["مدين", "دائن", "الباقي"]):
            type_col = c
            break

    # Find the row group for total cash.
    cash_idx = None
    for i, row in work.iterrows():
        if _is_liquidity_total_row(row):
            cash_idx = i
            break

    monthly_rows = []
    notes = []
    if cash_idx is not None and type_col is not None:
        # In Smart-like liquidity reports, the account name appears on the middle row
        # of a 3-row group: Debit / Credit / Balance. Start one row earlier when needed.
        start_idx = max(0, cash_idx - 1)
        group = work.iloc[start_idx: start_idx + 3].copy()
        for m in month_cols:
            cash_in = cash_out = net = 0.0
            for _, r in group.iterrows():
                t = str(r.get(type_col, "")).strip()
                if "مدين" in t:
                    cash_in = _number(r.get(m))
                elif "دائن" in t:
                    cash_out = _number(r.get(m))
                elif "الباقي" in t or "باقي" in t:
                    net = _number(r.get(m))
            if cash_in or cash_out or net:
                if not net:
                    net = cash_in - cash_out
                monthly_rows.append({"month": month_label(m), "cash_in": cash_in, "cash_out": cash_out, "net_cash_flow": net})
        notes.append("تم استخدام صف الأموال الجاهزة كمصدر تنفيذي لحركة السيولة الشهرية.")
    else:
        notes.append("لم يتم تحديد صف الأموال الجاهزة بدقة؛ يمكن استخدام كشوف البنك كبديل.")

    monthly = pd.DataFrame(monthly_rows)
    if not monthly.empty:
        monthly["ending_cash_proxy"] = monthly["net_cash_flow"].cumsum()
        total_in = float(monthly["cash_in"].sum())
        total_out = float(monthly["cash_out"].sum())
        total_net = float(monthly["net_cash_flow"].sum())
        avg_out = float(monthly.loc[monthly["cash_out"] > 0, "cash_out"].mean() or 0)
        ending_cash = float(monthly["ending_cash_proxy"].iloc[-1])
        runway = ending_cash / avg_out if avg_out else None
    else:
        total_in = total_out = total_net = avg_out = ending_cash = 0.0
        runway = None

    # Account-level summary if available.
    account_rows = []
    code_col = cols[0] if cols else None
    name_col = cols[1] if len(cols) > 1 else None
    if type_col is not None and total_col is not None:
        for i, r in work.iterrows():
            t = str(r.get(type_col, ""))
            if "الباقي" in t or "باقي" in t:
                account_rows.append({
                    "account_code": str(r.get(code_col, "")),
                    "account_name": str(r.get(name_col, "")),
                    "ending_balance": _number(r.get(total_col)),
                })
    accounts = pd.DataFrame(account_rows)

    return {
        "available": not monthly.empty,
        "monthly": monthly,
        "accounts": accounts,
        "cards": {
            "total_cash_in": total_in,
            "total_cash_out": total_out,
            "net_cash_flow": total_net,
            "ending_cash": ending_cash,
            "avg_monthly_cash_out": avg_out,
            "cash_runway_months": runway,
        },
        "notes": notes,
        "source_file": file_record.get("file_name"),
    }


def parse_aging_report(file_record: dict | None, kind: str = "ar") -> dict:
    if not file_record:
        return {"available": False, "detail": pd.DataFrame(), "cards": {}, "notes": ["ملف الأعمار غير متوفر."]}
    df = file_record.get("primary_df", pd.DataFrame()).copy()
    if df.empty:
        return {"available": False, "detail": pd.DataFrame(), "cards": {}, "notes": ["ملف الأعمار فارغ."]}

    # Promote first row if it contains headers.
    if len(df):
        first = [str(x).strip() for x in df.iloc[0].tolist()]
        if any(x in first for x in ["عميل", "مورد", "الرصيد", "عمر الدين"]):
            df.columns = first
            df = df.iloc[1:].reset_index(drop=True)

    name_col = find_column(df, ["عميل", "مورد", "customer", "supplier", "vendor", "name"])
    bal_col = find_column(df, ["الرصيد", "balance", "amount"])
    age_col = find_column(df, ["عمر الدين", "age", "days"])
    total_col = find_column(df, ["الإجمالي", "اجمالي", "total"])
    last_pay_col = find_column(df, ["آخر سداد", "اخر سداد", "last payment"])

    if not name_col:
        # maybe raw columns numbers after header promotion failed
        name_col = df.columns[2] if df.shape[1] > 2 else None
    if not bal_col:
        bal_col = df.columns[4] if df.shape[1] > 4 else None
    if not age_col:
        age_col = df.columns[5] if df.shape[1] > 5 else None

    if not name_col or not bal_col:
        return {"available": False, "detail": pd.DataFrame(), "cards": {}, "notes": ["لم يتم تحديد اسم العميل/المورد أو الرصيد."]}

    work = df.copy()
    work["name"] = work[name_col].astype(str).str.strip()
    # Remove total/subtotal rows even when the word appears in a different column.
    row_text = work.astype(str).apply(lambda r: " ".join(r.values), axis=1)
    work = work[~row_text.str.contains("الإجمالي|اجمالي|total", case=False, na=False)]
    work = work[~work["name"].str.contains("الإجمالي|اجمالي|total|nan", case=False, na=False)]
    work["balance"] = to_number(work[bal_col])
    work["age_days"] = to_number(work[age_col]) if age_col is not None else 0
    if last_pay_col:
        work["last_payment"] = work[last_pay_col].astype(str)
    else:
        work["last_payment"] = ""
    work = work[work["balance"].abs() > 0].copy()

    def risk(row):
        age = float(row.get("age_days") or 0)
        bal = float(row.get("balance") or 0)
        if age > 60 or bal >= 100000:
            return "عالي"
        if age > 30 or bal >= 25000:
            return "متوسط"
        return "منخفض"

    work["risk_level"] = work.apply(risk, axis=1)
    work["recommended_action"] = work["risk_level"].map({
        "عالي": "اتصال مباشر وجدولة تحصيل خلال 7 أيام",
        "متوسط": "إرسال كشف ومطالبة ومتابعة خلال 14 يوم",
        "منخفض": "متابعة عادية",
    })
    detail = work[["name", "balance", "age_days", "last_payment", "risk_level", "recommended_action"]].copy()
    detail = detail.sort_values(["risk_level", "balance"], ascending=[True, False])
    # Re-sort risk custom
    order = {"عالي": 0, "متوسط": 1, "منخفض": 2}
    detail["_risk_order"] = detail["risk_level"].map(order).fillna(9)
    detail = detail.sort_values(["_risk_order", "balance"], ascending=[True, False]).drop(columns=["_risk_order"])

    total = float(detail["balance"].sum()) if not detail.empty else 0.0
    overdue = float(detail.loc[detail["age_days"] > 30, "balance"].sum()) if not detail.empty else 0.0
    top5 = float(detail.head(5)["balance"].sum()) if not detail.empty else 0.0
    concentration = top5 / total if total else 0.0

    return {
        "available": True,
        "detail": detail,
        "cards": {
            "total_balance": total,
            "overdue_balance": overdue,
            "overdue_pct": overdue / total if total else 0.0,
            "top5_concentration": concentration,
            "count": int(len(detail)),
        },
        "notes": ["تم استخراج قائمة أولويات التحصيل/الدفع من ملف الأعمار."],
        "source_file": file_record.get("file_name"),
    }


def build_liquidity_collections_model(files: list[dict]) -> dict:
    files = files or []
    cash_records = [f for f in files if f.get("selected_role") == "cash_source"]
    ar_record = next((f for f in files if f.get("selected_role") == "ar_aging_source"), None)
    ap_record = next((f for f in files if f.get("selected_role") == "ap_aging_source"), None)

    # Prefer cash liquidity report over raw bank statements.
    liquidity_record = next((f for f in cash_records if f.get("detected_type") == "cash_liquidity_report"), None)
    liquidity_record = liquidity_record or (cash_records[0] if cash_records else None)

    cash = parse_cash_liquidity_report(liquidity_record) if liquidity_record and liquidity_record.get("detected_type") == "cash_liquidity_report" else {"available": False, "monthly": pd.DataFrame(), "accounts": pd.DataFrame(), "cards": {}, "notes": ["لم يتم العثور على تقرير سيولة نقدية؛ كشوف البنك تبقى للتفصيل لاحقًا."]}
    ar = parse_aging_report(ar_record, "ar")
    ap = parse_aging_report(ap_record, "ap")

    return {
        "cash": cash,
        "ar": ar,
        "ap": ap,
        "available": cash.get("available") or ar.get("available") or ap.get("available"),
    }


def liquidity_cfo_narrative(model: dict, pnl_model: dict | None = None) -> dict:
    cash = model.get("cash", {}) if model else {}
    ar = model.get("ar", {}) if model else {}
    cards = cash.get("cards", {}) if cash.get("available") else {}
    ar_cards = ar.get("cards", {}) if ar.get("available") else {}
    runway = cards.get("cash_runway_months")
    ending = cards.get("ending_cash", 0) or 0
    net_cash = cards.get("net_cash_flow", 0) or 0
    overdue_pct = ar_cards.get("overdue_pct", 0) or 0
    concentration = ar_cards.get("top5_concentration", 0) or 0

    risk = "متوسط"
    problem = "السيولة والتحصيل بحاجة متابعة"
    action = "بناء خطة تحصيل أسبوعية ومراقبة صافي الحركة النقدية."
    if runway is not None and runway < 1:
        risk = "عالي"
        problem = "النقد لا يغطي شهرًا كاملًا من متوسط الخروج النقدي"
        action = "الأولوية خلال 14 يوم: تحصيل العملاء الأعلى رصيدًا وتأجيل المدفوعات غير الحرجة."
    elif net_cash < 0:
        risk = "متوسط"
        problem = "صافي الحركة النقدية سلبي خلال الفترة الأخيرة"
        action = "راجع أشهر الضغط النقدي وحدد هل السبب تحصيل بطيء أو مصروفات غير متكررة."
    if overdue_pct > 0.35 or concentration > 0.60:
        risk = "عالي" if risk != "عالي" else risk
        problem += " مع تركّز واضح في الذمم أو تأخر التحصيل"
        action = "اعرض جدول أولويات العملاء وابدأ بأكبر أرصدة متأخرة؛ اربط التحصيل بتحسن Runway." 

    return {
        "risk": risk,
        "problem": problem,
        "action": action,
        "monitor": "Cash Runway، صافي الحركة النقدية، نسبة المتأخر من الذمم، وتركيز أكبر العملاء.",
    }
