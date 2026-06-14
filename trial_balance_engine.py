import re
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

    # Some TB exports provide only closing balances. If period movement is empty,
    # fall back to current debit/credit so the TB alone can still build statements.
    if abs(debit) + abs(credit) == 0:
        debit = float(row.get("current_debit", 0) or 0)
        credit = float(row.get("current_credit", 0) or 0)

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



def _leaf_subset(work: pd.DataFrame) -> pd.DataFrame:
    if work.empty:
        return work
    all_codes = work["account_code_norm"].tolist() if "account_code_norm" in work.columns else []
    if any(all_codes):
        return work[~work["account_code_norm"].apply(lambda c: _is_parent_code(c, all_codes))].copy()
    return work.copy()


def _row_amounts(subset: pd.DataFrame, natural="debit") -> float:
    if subset.empty:
        return 0.0
    debit = subset["debit"].astype(float) if "debit" in subset.columns else 0
    credit = subset["credit"].astype(float) if "credit" in subset.columns else 0
    if hasattr(debit, "sum") and float(abs(debit).sum() + abs(credit).sum()) == 0:
        debit = subset["current_debit"].astype(float) if "current_debit" in subset.columns else 0
        credit = subset["current_credit"].astype(float) if "current_credit" in subset.columns else 0
    if natural == "credit":
        return abs(float((credit - debit).sum()))
    return abs(float((debit - credit).sum()))


def _sum_by_account_keywords(work: pd.DataFrame, include: list[str], natural="debit", exclude: list[str] | None = None) -> float:
    """Fallback when account codes or exact parent totals are missing.
    It uses account names but avoids parent/child double counting when codes exist.
    """
    exclude = exclude or []
    subset = _leaf_subset(work)
    names = subset["account_name"].astype(str).apply(normalize_text)
    inc_mask = pd.Series(False, index=subset.index)
    for k in include:
        inc_mask = inc_mask | names.str.contains(normalize_text(k), na=False, regex=False)
    for k in exclude:
        inc_mask = inc_mask & ~names.str.contains(normalize_text(k), na=False, regex=False)
    return _row_amounts(subset[inc_mask], natural=natural)


def _has_income_statement_signal(work: pd.DataFrame) -> bool:
    names = " ".join(work.get("account_name", pd.Series(dtype=str)).astype(str).head(500).tolist())
    names_n = normalize_text(names)
    return any(k in names_n for k in ["مبيعات", "ايراد", "إيراد", "مصروف", "مصاريف", "تكلفة", "مشتريات"])

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

    # 1) Revenue: exact net sales > code class > account-name fallback.
    net_sales = _explicit_amount(work, ["صافي المبيعات", "Net Sales"], natural="credit")
    if net_sales is None or net_sales == 0:
        net_sales = _leaf_sum_by_code(work, ["4"], natural="credit")
    if net_sales == 0:
        net_sales = _sum_by_account_keywords(
            work,
            include=["مبيعات", "sales", "revenue"],
            natural="credit",
            exclude=["مردود", "مرتجع", "خصم", "ضريبة", "تكلفة", "مصروف", "مصاريف"],
        )

    # Other revenue should not double-count a parent row named الإيرادات.
    other_revenue = _explicit_amount(work, ["إيرادات أخرى", "ايرادات اخرى", "Other Revenue"], natural="credit")
    if other_revenue is None:
        other_revenue = _leaf_sum_by_code(work, ["6"], natural="credit")
    if other_revenue == 0:
        other_revenue = _sum_by_account_keywords(
            work,
            include=["إيرادات أخرى", "ايرادات اخرى", "other income"],
            natural="credit",
            exclude=["مبيعات", "ضريبة"],
        )

    # 2) Direct cost / COGS.
    net_purchases = _explicit_amount(work, ["صافي المشتريات", "Net Purchases"], natural="debit")
    if net_purchases is None or net_purchases == 0:
        purchases = _leaf_sum_by_code(work, ["301"], natural="debit")
        returns = _leaf_sum_by_code(work, ["302"], natural="credit")
        discounts = _leaf_sum_by_code(work, ["303"], natural="credit")
        net_purchases = max(0.0, purchases - returns - discounts)
    if net_purchases == 0:
        net_purchases = _sum_by_account_keywords(
            work,
            include=["مشتريات", "تكلفة المبيعات", "تكلفة الإيراد", "تكلفة الايراد", "cost of revenue", "cogs"],
            natural="debit",
            exclude=["مردود", "خصم"],
        )

    opening_inventory, ending_inventory, inv_note = _inventory_values(work)
    cogs = opening_inventory + net_purchases - ending_inventory
    cogs = max(0.0, cogs)

    # 3) Expenses split. V13.4 separates operating expenses from depreciation,
    # finance costs, and tax/zakat. The previous implementation treated all
    # expenses as operating, making EBITDA equal to net profit in some cases.
    total_expenses_read = _explicit_amount(work, ["المصروفات", "إجمالي المصروفات", "Total Expenses"], natural="debit")
    if total_expenses_read is None or total_expenses_read == 0:
        total_expenses_read = _leaf_sum_by_code(work, ["5"], natural="debit")
    if total_expenses_read == 0:
        total_expenses_read = _sum_by_account_keywords(
            work,
            include=["مصروف", "مصاريف", "راتب", "رواتب", "ايجار", "إيجار", "أتعاب", "اتعاب", "عمولة", "عمولات", "تسويق", "دعاية", "بدل", "اهلاك", "فوائد", "تمويل", "زكاة", "ضريبة"],
            natural="debit",
            exclude=["تكلفة المبيعات", "تكلفة الإيراد", "تكلفة الايراد"],
        )

    depreciation = _sum_by_account_keywords(
        work,
        include=["اهلاك", "إهلاك", "استهلاك", "depreciation", "amortization"],
        natural="debit",
        exclude=[],
    )
    finance_costs = _sum_by_account_keywords(
        work,
        include=["فوائد", "تمويل", "تكاليف تمويل", "مصروف تمويل", "رسوم بنكية", "bank charges", "interest", "finance cost"],
        natural="debit",
        exclude=[],
    )
    tax_zakat = _sum_by_account_keywords(
        work,
        include=["زكاة", "زكاه", "ضريبة", "ضريبه", "tax", "zakat"],
        natural="debit",
        exclude=["القيمة المضافة للمبيعات", "ضريبة القيمة المضافة للمبيعات"],
    )

    operating_expenses = max(0.0, float(total_expenses_read or 0) - depreciation - finance_costs - tax_zakat)

    total_revenue = float(net_sales or 0) + float(other_revenue or 0)
    gross_profit = total_revenue - cogs
    ebitda = gross_profit - operating_expenses
    ebit = ebitda - depreciation
    profit_before_tax = ebit - finance_costs
    net_profit = profit_before_tax - tax_zakat

    available = _has_income_statement_signal(work) and (abs(total_revenue) + abs(operating_expenses) + abs(cogs) > 0)

    pnl = pd.DataFrame([
        ["Net Sales", "صافي المبيعات", net_sales],
        ["Other Revenue", "إيرادات أخرى", other_revenue],
        ["Total Revenue", "إجمالي الإيرادات", total_revenue],
        ["Opening Inventory", "مخزون أول المدة", opening_inventory],
        ["Net Purchases / Direct Cost", "صافي المشتريات / تكلفة مباشرة", net_purchases],
        ["Ending Inventory", "مخزون آخر المدة", ending_inventory],
        ["COGS", "تكلفة المبيعات", cogs],
        ["Gross Profit", "مجمل الربح", gross_profit],
        ["Operating Expenses", "المصروفات التشغيلية", operating_expenses],
        ["EBITDA", "الربح قبل الإهلاك والتمويل والزكاة/الضريبة", ebitda],
        ["Depreciation & Amortization", "الإهلاك والاستهلاك", depreciation],
        ["EBIT", "الربح التشغيلي بعد الإهلاك", ebit],
        ["Finance Costs", "تكاليف التمويل", finance_costs],
        ["Profit Before Tax/Zakat", "الربح قبل الزكاة/الضريبة", profit_before_tax],
        ["Tax / Zakat", "الزكاة والضريبة", tax_zakat],
        ["Net Profit", "صافي الربح", net_profit],
    ], columns=["English", "العربي", "Amount"])

    notes = [
        "تم بناء قائمة الدخل من ميزان المراجعة كمصدر أساسي عند توفر إشارات الإيراد أو المصروف.",
        inv_note,
        "إذا وُجدت ملفات مبيعات أو مصروفات تفصيلية فهي تستخدم للتوزيع الشهري والتحقق والتفسير، لا لإيقاف التحليل الأساسي.",
    ]
    if total_revenue == 0 and operating_expenses > 0:
        notes.append("تم استخراج مصروفات من الميزان لكن لم تُقرأ الإيرادات؛ راجع أعمدة/أسماء حسابات الإيراد أو أضف ملف المبيعات للتحقق.")

    return {
        "available": bool(available),
        "pnl": pnl,
        "net_sales": float(net_sales or 0),
        "other_revenue": float(other_revenue or 0),
        "total_revenue": float(total_revenue or 0),
        "opening_inventory": float(opening_inventory or 0),
        "net_purchases": float(net_purchases or 0),
        "ending_inventory": float(ending_inventory or 0),
        "cogs": float(cogs or 0),
        "gross_profit": float(gross_profit or 0),
        "operating_expenses": float(operating_expenses or 0),
        "total_expenses_read": float(total_expenses_read or 0),
        "ebitda": float(ebitda or 0),
        "depreciation": float(depreciation or 0),
        "ebit": float(ebit or 0),
        "finance_costs": float(finance_costs or 0),
        "profit_before_tax": float(profit_before_tax or 0),
        "tax_zakat": float(tax_zakat or 0),
        "net_profit": float(net_profit or 0),
        "notes": notes,
    }

def parse_trial_balance(file_record: dict) -> dict:
    df = file_record["primary_df"].copy()
    account_col = find_column(df, ["اسم الحساب", "account name", "account", "الحساب", "البيان"])
    code_col = find_column(df, ["رقم الحساب", "رمز الحساب", "كود الحساب", "account code", "account no", "code", "رقم", "الحساب رقم"])
    begin_debit_col = find_column(df, ["بداية المدة(مدين)", "opening debit", "begin debit"])
    begin_credit_col = find_column(df, ["بداية المدة(دائن", "opening credit", "begin credit"])
    debit_col = find_column(df, ["مدين", "debit", "الحركة المدينة"])
    credit_col = find_column(df, ["دائن", "دائن ", "credit", "الحركة الدائنة"])
    current_debit_col = find_column(df, ["الرصيد الحالي(مدين)", "نهاية المدة(مدين)", "رصيد آخر المدة مدين", "closing debit", "current debit"])
    current_credit_col = find_column(df, ["الرصيد الحالي(دائن", "نهاية المدة(دائن", "رصيد آخر المدة دائن", "closing credit", "current credit"])

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
        "ebitda": income_statement.get("ebitda"),
        "depreciation": income_statement.get("depreciation"),
        "ebit": income_statement.get("ebit"),
        "finance_costs": income_statement.get("finance_costs"),
        "profit_before_tax": income_statement.get("profit_before_tax"),
        "tax_zakat": income_statement.get("tax_zakat"),
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
