import pandas as pd
from utils import find_column, to_number, normalize_text

ACCOUNT_RULES = {
    "Assets": ["نقد", "بنك", "صندوق", "ذمم مدينة", "عملاء", "اصل", "أصل", "assets", "cash", "bank", "receivable", "مخزون"],
    "Liabilities": ["ذمم دائنة", "مورد", "قرض", "التزام", "مقبوض مقدما", "مقدمة", "liabilities", "payable", "loan", "unearned"],
    "Equity": ["رأس المال", "راس المال", "حقوق", "ارباح مبقاة", "equity", "capital"],
    "Net Purchases": ["صافي المشتريات"],
    "Purchases": ["المشتريات"],
    "Purchase Returns": ["مردودات المشتريات"],
    "Purchase Discounts": ["خصم مكتسب"],
    "Net Sales": ["صافي المبيعات"],
    "Sales": ["المبيعات"],
    "Sales Returns": ["مردودات المبيعات"],
    "Sales Discounts": ["خصم ممنوح"],
    "Other Revenue": ["ايرادات", "إيرادات", "ايراد", "إيراد", "other income"],
    "Operating Expenses": ["مصروف", "مصاريف", "expenses", "opex"],
    "Depreciation": ["اهلاك", "إهلاك", "depreciation"],
    "Finance Costs": ["فوائد", "تمويل", "رسوم بنكية", "interest", "finance"],
    "Tax/Zakat": ["زكاة", "ضريبة", "tax", "zakat"],
}

def _code_str(value) -> str:
    if pd.isna(value):
        return ""
    try:
        # 40101.0 -> 40101
        return str(int(float(value)))
    except Exception:
        return str(value).strip().replace(".0", "")

def _is_parent_code(code: str, all_codes: list[str]) -> bool:
    if not code:
        return False
    return any(other != code and other.startswith(code) and len(other) > len(code) for other in all_codes)

def classify_account(name: str) -> str:
    text = normalize_text(name)

    if any(k in text for k in ["مقبوض مقدما", "مستحقة", "ضريبة القيمة المضافة للمبيعات"]):
        return "Liabilities"

    for category, keys in ACCOUNT_RULES.items():
        if any(normalize_text(k) in text for k in keys):
            return category
    return "Unclassified"

def _amount_from_row(row, debit_field="debit", credit_field="credit", natural="debit") -> float:
    debit = float(row.get(debit_field, 0) or 0)
    credit = float(row.get(credit_field, 0) or 0)
    if natural == "credit":
        return credit - debit
    return debit - credit

def _explicit_amount(work: pd.DataFrame, exact_names: list[str], natural="debit") -> float | None:
    names = work["account_name"].astype(str).str.strip()
    for exact in exact_names:
        mask = names.eq(exact)
        if mask.any():
            row = work.loc[mask].iloc[0]
            val = _amount_from_row(row, natural=natural)
            return abs(float(val))
    return None

def _leaf_sum_by_code(work: pd.DataFrame, prefixes: list[str], natural="debit", exclude_names: list[str] | None = None) -> float:
    exclude_names = exclude_names or []
    all_codes = work["account_code_norm"].tolist()
    mask = pd.Series(False, index=work.index)
    for prefix in prefixes:
        mask = mask | work["account_code_norm"].str.startswith(prefix, na=False)

    subset = work[mask].copy()
    if subset.empty:
        return 0.0

    # Avoid double counting parent and child rows.
    subset = subset[~subset["account_code_norm"].apply(lambda c: _is_parent_code(c, all_codes))]
    if exclude_names:
        ex = "|".join([re.escape(x) for x in exclude_names])
        subset = subset[~subset["account_name"].astype(str).str.contains(ex, case=False, na=False)]

    if natural == "credit":
        return abs(float((subset["credit"] - subset["debit"]).sum()))
    return abs(float((subset["debit"] - subset["credit"]).sum()))

def _inventory_values(work: pd.DataFrame) -> tuple[float, float, str]:
    """
    Returns opening_inventory, ending_inventory, note.
    It searches inventory accounts if they exist.
    """
    inv_mask = work["account_name"].astype(str).str.contains("مخزون|بضاعة", case=False, na=False)
    inv = work[inv_mask].copy()
    if inv.empty:
        return 0.0, 0.0, "لم يتم العثور على حسابات مخزون في ميزان المراجعة؛ تم اعتبار المخزون = صفر."

    all_codes = work["account_code_norm"].tolist()
    inv = inv[~inv["account_code_norm"].apply(lambda c: _is_parent_code(c, all_codes))]

    opening = float((inv["begin_debit"] - inv["begin_credit"]).sum())
    ending = float((inv["current_debit"] - inv["current_credit"]).sum())
    return max(0.0, opening), max(0.0, ending), "تم استخراج مخزون أول وآخر المدة من حسابات المخزون في ميزان المراجعة."

def build_income_statement_from_trial_balance(tb_model: dict) -> dict:
    work = tb_model.get("tb", pd.DataFrame()) if tb_model else pd.DataFrame()
    if work.empty:
        return {"available": False, "pnl": pd.DataFrame(), "notes": ["ميزان المراجعة غير متاح أو غير قابل للقراءة."]}

    net_sales = _explicit_amount(work, ["صافي المبيعات"], natural="credit")
    if net_sales is None:
        # Fallback: net sales from class 4 excluding class 6.
        sales = _leaf_sum_by_code(work, ["4"], natural="credit")
        net_sales = sales

    other_revenue = _explicit_amount(work, ["الإيرادات"], natural="credit")
    if other_revenue is None:
        other_revenue = _leaf_sum_by_code(work, ["6"], natural="credit")

    net_purchases = _explicit_amount(work, ["صافي المشتريات"], natural="debit")
    if net_purchases is None:
        purchases = _leaf_sum_by_code(work, ["301"], natural="debit")
        returns = _leaf_sum_by_code(work, ["302"], natural="credit")
        discounts = _leaf_sum_by_code(work, ["303"], natural="credit")
        net_purchases = max(0.0, purchases - returns - discounts)

    opening_inventory, ending_inventory, inv_note = _inventory_values(work)
    cogs = opening_inventory + net_purchases - ending_inventory
    cogs = max(0.0, cogs)

    operating_expenses = _explicit_amount(work, ["المصروفات"], natural="debit")
    if operating_expenses is None:
        operating_expenses = _leaf_sum_by_code(work, ["5"], natural="debit")

    total_revenue = net_sales + other_revenue
    gross_profit = total_revenue - cogs
    ebitda = gross_profit - operating_expenses
    net_profit = ebitda

    pnl = pd.DataFrame([
        ["Net Sales", "صافي المبيعات", net_sales],
        ["Other Revenue", "إيرادات أخرى", other_revenue],
        ["Total Revenue", "إجمالي الإيرادات", total_revenue],
        ["Opening Inventory", "مخزون أول المدة", opening_inventory],
        ["Net Purchases", "صافي المشتريات", net_purchases],
        ["Ending Inventory", "مخزون آخر المدة", ending_inventory],
        ["COGS", "تكلفة المبيعات", cogs],
        ["Gross Profit", "مجمل الربح", gross_profit],
        ["Operating Expenses", "المصروفات", operating_expenses],
        ["Net Profit", "صافي الربح", net_profit],
    ], columns=["English", "العربي", "Amount"])

    return {
        "available": True,
        "pnl": pnl,
        "net_sales": net_sales,
        "other_revenue": other_revenue,
        "total_revenue": total_revenue,
        "opening_inventory": opening_inventory,
        "net_purchases": net_purchases,
        "ending_inventory": ending_inventory,
        "cogs": cogs,
        "gross_profit": gross_profit,
        "operating_expenses": operating_expenses,
        "ebitda": ebitda,
        "net_profit": net_profit,
        "notes": [
            "تم بناء قائمة الدخل من ميزان المراجعة كمصدر أساسي.",
            inv_note,
            "ملفات المبيعات والمصاريف الشهرية تستخدم للتحليل والتوزيع الشهري، وليست المصدر الأساسي لصافي الربح."
        ]
    }

def parse_trial_balance(file_record: dict) -> dict:
    df = file_record["primary_df"].copy()
    account_col = find_column(df, ["اسم الحساب", "account name", "account", "الحساب", "البيان"])
    code_col = find_column(df, ["رقم الحساب", "account code", "code"])
    begin_debit_col = find_column(df, ["بداية المدة(مدين)", "opening debit", "begin debit"])
    begin_credit_col = find_column(df, ["بداية المدة(دائن", "opening credit", "begin credit"])
    debit_col = find_column(df, ["مدين", "debit", "الحركة المدينة"])
    credit_col = find_column(df, ["دائن", "دائن ", "credit", "الحركة الدائنة"])
    current_debit_col = find_column(df, ["الرصيد الحالي(مدين)", "closing debit", "current debit"])
    current_credit_col = find_column(df, ["الرصيد الحالي(دائن", "closing credit", "current credit"])

    if not account_col:
        return {
            "tb": pd.DataFrame(),
            "summary": pd.DataFrame(),
            "metrics": {},
            "income_statement": {"available": False, "pnl": pd.DataFrame()},
            "notes": ["لم يتم تحديد عمود اسم الحساب في ميزان المراجعة."]
        }

    work = df.copy()
    work["account_name"] = work[account_col].astype(str)
    work["account_code"] = work[code_col].astype(str) if code_col else ""
    work["account_code_norm"] = work[code_col].apply(_code_str) if code_col else ""
    work["category"] = work["account_name"].apply(classify_account)

    work["begin_debit"] = to_number(work[begin_debit_col]) if begin_debit_col else 0
    work["begin_credit"] = to_number(work[begin_credit_col]) if begin_credit_col else 0
    work["debit"] = to_number(work[debit_col]) if debit_col else 0
    work["credit"] = to_number(work[credit_col]) if credit_col else 0
    work["current_debit"] = to_number(work[current_debit_col]) if current_debit_col else 0
    work["current_credit"] = to_number(work[current_credit_col]) if current_credit_col else 0
    work["net"] = work["credit"] - work["debit"]

    summary = work.groupby("category", as_index=False)[["debit", "credit", "net"]].sum()

    tb_model = {"tb": work, "summary": summary, "metrics": {}, "notes": []}
    income_statement = build_income_statement_from_trial_balance(tb_model)

    metrics = {
        "net_sales": income_statement.get("net_sales"),
        "other_revenue": income_statement.get("other_revenue"),
        "total_revenue": income_statement.get("total_revenue"),
        "net_purchases": income_statement.get("net_purchases"),
        "opening_inventory": income_statement.get("opening_inventory"),
        "ending_inventory": income_statement.get("ending_inventory"),
        "cogs": income_statement.get("cogs"),
        "operating_expenses": income_statement.get("operating_expenses"),
        "net_profit": income_statement.get("net_profit"),
        "net_sales_basis": "ميزان المراجعة / صافي المبيعات",
        "net_purchases_basis": "ميزان المراجعة / صافي المشتريات",
    }

    return {
        "tb": work,
        "summary": summary,
        "metrics": metrics,
        "income_statement": income_statement,
        "notes": income_statement.get("notes", []),
    }
