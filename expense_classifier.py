import os
import json
import pandas as pd

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

def _norm(text):
    text = "" if text is None else str(text)
    text = text.strip().lower()
    repl = {
        "أ": "ا", "إ": "ا", "آ": "ا", "ة": "ه", "ى": "ي",
        "ـ": "", "\u200f": "", "\u200e": "",
    }
    for a, b in repl.items():
        text = text.replace(a, b)
    return text

def _contains_any(text, keywords):
    return any(k in text for k in keywords)

DIRECT_COST_KEYWORDS = [
    "مشتريات", "شراء", "بضاعه", "بضاعة", "تكلفه البضاعه", "تكلفة البضاعة",
    "تكلفه المبيعات", "تكلفة المبيعات", "تكلفه الايراد", "تكلفة الايراد",
    "مواد", "مواد خام", "خامات", "قطع غيار", "اسبير", "spare",
    "فحم", "وقود تشغيل", "ديزل", "بنزين", "زيوت", "تشغيل مباشر",
    "تكاليف تشغيل", "تكلفة تشغيل", "خدمات مباشره", "خدمات مباشرة",
    "مصروفات تشغيل", "مصاريف تشغيل", "cost of revenue", "cogs", "purchases",
]
PAYROLL_KEYWORDS = ["رواتب", "اجور", "أجور", "مرتبات", "مكافات", "مكافآت", "تامينات اجتماعيه", "التامينات الاجتماعيه", "تأمينات اجتماعية", "gosi", "payroll", "salary", "wages"]
RENT_KEYWORDS = ["ايجار", "إيجار", "اجار", "rent"]
UTILITIES_KEYWORDS = ["كهرباء", "مياه", "ماء", "هاتف", "انترنت", "الاتصالات", "utility", "utilities"]
MAINTENANCE_KEYWORDS = ["صيانة", "صيانه", "repair", "maintenance"]
FUEL_KEYWORDS = ["وقود", "بنزين", "ديزل", "محروقات", "fuel"]
DEPRECIATION_KEYWORDS = ["اهلاك", "إهلاك", "استهلاك", "depreciation"]
FINANCE_KEYWORDS = ["فوائد", "فائده", "تمويل", "قرض", "قروض", "finance cost", "interest"]
BANK_KEYWORDS = ["عموله بنك", "عمولات بنك", "رسوم بنكيه", "البنك", "bank charges", "bank fees"]
MARKETING_KEYWORDS = ["تسويق", "اعلان", "إعلان", "اعلانات", "دعايه", "دعاية", "ترويج", "عموله", "عمولة", "مبيعات", "سمسرة", "sales commission", "marketing", "advertising", "selling"]
ADMIN_KEYWORDS = ["تجديد رخصه", "رخصه", "رخصة", "اقامه", "إقامة", "تجديد الاقامه", "بلديه", "الشهادات الصحيه", "رسوم", "اشتراك", "النظام المحاسبي", "مكتب", "قرطاسيه", "قرطاسية", "ضيافه", "نظافه", "نظافة", "بلاستيك", "ادوات", "ادوات النظافه", "وجبات العمال", "منصه", "منصة", "اداري", "administrative", "admin"]

def classify_account_rule_based(account_name, amount=0, source_category=None):
    raw = "" if account_name is None else str(account_name)
    text = _norm(raw)
    src = _norm(source_category)

    score = []
    def add(category, behavior, points, reason):
        score.append((points, category, behavior, reason))

    if _contains_any(text, DIRECT_COST_KEYWORDS) or _contains_any(src, ["مشتريات", "cogs", "cost"]):
        behavior = "Variable"
        if _contains_any(text, ["صيانة", "صيانه", "كهرباء", "هاتف", "انترنت"]):
            behavior = "Semi-variable"
        if _contains_any(text, ["مشتريات", "شراء"]):
            add("Purchases", "Variable", 100, "اسم الحساب يشير إلى مشتريات أو تكلفة مباشرة")
        else:
            add("Cost of Revenue", behavior, 92, "اسم الحساب يشير إلى تكلفة تشغيل مباشرة أو تكلفة إيراد")

    if _contains_any(text, PAYROLL_KEYWORDS):
        add("Payroll", "Fixed", 88, "اسم الحساب يشير إلى رواتب أو أجور أو تأمينات")
    if _contains_any(text, RENT_KEYWORDS):
        add("Rent", "Fixed", 86, "اسم الحساب يشير إلى إيجارات")
    if _contains_any(text, UTILITIES_KEYWORDS):
        add("Utilities", "Semi-variable", 82, "اسم الحساب يشير إلى خدمات ومرافق")
    if _contains_any(text, MAINTENANCE_KEYWORDS):
        add("Maintenance", "Semi-variable", 80, "اسم الحساب يشير إلى صيانة")
    if _contains_any(text, FUEL_KEYWORDS):
        add("Fuel", "Variable", 82, "اسم الحساب يشير إلى وقود أو محروقات")
    if _contains_any(text, DEPRECIATION_KEYWORDS):
        add("Depreciation", "Fixed", 90, "اسم الحساب يشير إلى إهلاك")
    if _contains_any(text, FINANCE_KEYWORDS):
        add("Finance Costs", "Fixed", 90, "اسم الحساب يشير إلى فوائد أو تكاليف تمويل")
    if _contains_any(text, BANK_KEYWORDS):
        add("Bank Charges", "Semi-variable", 84, "اسم الحساب يشير إلى رسوم أو عمولات بنكية")
    if _contains_any(text, MARKETING_KEYWORDS):
        add("Selling & Marketing", "Variable", 86, "اسم الحساب يشير إلى تسويق أو مبيعات أو عمولات")
    if _contains_any(text, ADMIN_KEYWORDS):
        add("Administrative Expenses", "Fixed", 80, "اسم الحساب يشير إلى مصاريف إدارية أو رسوم حكومية")

    if not score:
        if source_category and str(source_category).strip() and "Other" not in str(source_category):
            return str(source_category), "Fixed", 45, "تم الحفاظ على التصنيف السابق لعدم وجود كلمات دلالية كافية", "rules"
        return "Other Opex", "Fixed", 25, "لم يتم العثور على مؤشرات كافية للتصنيف", "rules"

    score.sort(reverse=True, key=lambda x: x[0])
    points, category, behavior, reason = score[0]
    return category, behavior, min(points, 100), reason, "rules"

def _get_openai_key():
    key = os.getenv("OPENAI_API_KEY")
    if key:
        return key
    try:
        import streamlit as st
        return st.secrets.get("OPENAI_API_KEY", None) or st.secrets.get("openai_api_key", None)
    except Exception:
        return None

def _get_openai_client():
    key = _get_openai_key()
    if not key:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=key)
    except Exception:
        return None

def classify_accounts_openai_batch(rows, model="gpt-4o-mini"):
    """
    Classifies a batch of account rows with OpenAI.
    Sends only account name, amount, and current category.
    Falls back silently to rules if API is unavailable.
    """
    client = _get_openai_client()
    if client is None:
        return None

    payload = []
    for i, r in enumerate(rows):
        payload.append({
            "id": i,
            "account_name": str(r.get("account_name", "")),
            "amount": float(r.get("amount", 0) or 0),
            "current_category": str(r.get("current_category", "")),
        })

    system_prompt = f"""
You are a professional financial controller and management accountant.
Classify Arabic/English expense account names for a management income statement.

Allowed categories:
{CATEGORY_OPTIONS}

Allowed cost behaviors:
{COST_BEHAVIOR_OPTIONS}

Classification principles:
- Purchases, merchandise, direct materials, direct operating inputs, spare parts, fuel used directly in operations, and cost of service delivery should be Cost of Revenue or Purchases.
- Administrative permits, licenses, government fees, office subscriptions, cleaning supplies, residency renewals, internet/phone unless clearly direct production, and general office costs should be Administrative Expenses or Utilities.
- Advertising, promotion, commissions, sales-related costs should be Selling & Marketing.
- Interest, loans, financing charges should be Finance Costs.
- Bank fees should be Bank Charges.
- Use Other Opex only when no reasonable category can be inferred.
- Choose cost behavior: Fixed, Variable, Semi-variable.
- Return strict JSON only.
"""

    user_prompt = {
        "task": "classify_accounts",
        "accounts": payload,
        "return_schema": {
            "items": [
                {
                    "id": 0,
                    "category": "one allowed category",
                    "cost_behavior": "Fixed|Variable|Semi-variable",
                    "confidence": 0,
                    "reason": "short Arabic reason"
                }
            ]
        }
    }

    try:
        resp = client.chat.completions.create(
            model=model,
            temperature=0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)},
            ],
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content
        data = json.loads(content)
        items = data.get("items", data if isinstance(data, list) else [])
        if not isinstance(items, list):
            return None

        result = {}
        for item in items:
            try:
                idx = int(item.get("id"))
            except Exception:
                continue
            category = item.get("category", "Other Opex")
            behavior = item.get("cost_behavior", "Fixed")
            confidence = int(float(item.get("confidence", 70)))
            reason = str(item.get("reason", "تصنيف بالذكاء الصناعي"))
            if category not in CATEGORY_OPTIONS:
                category = "Other Opex"
            if behavior not in COST_BEHAVIOR_OPTIONS:
                behavior = "Fixed"
            result[idx] = (category, behavior, max(0, min(100, confidence)), reason, "openai")
        return result
    except Exception:
        return None

def apply_smart_classification(mapping_df: pd.DataFrame, use_openai=True, batch_size=40) -> pd.DataFrame:
    if mapping_df is None or mapping_df.empty:
        return mapping_df

    out = mapping_df.copy()
    for col in ["account_name", "current_category", "user_category", "cost_behavior", "amount"]:
        if col not in out.columns:
            out[col] = "" if col != "amount" else 0

    # First apply rules, then override with OpenAI when available.
    categories, behaviors, confidences, reasons, sources = [], [], [], [], []
    row_dicts = []
    for _, row in out.iterrows():
        cat, beh, conf, reason, source = classify_account_rule_based(
            row.get("account_name", ""),
            row.get("amount", 0),
            row.get("current_category", ""),
        )
        categories.append(cat)
        behaviors.append(beh)
        confidences.append(conf)
        reasons.append(reason)
        sources.append(source)
        row_dicts.append({
            "account_name": row.get("account_name", ""),
            "amount": row.get("amount", 0),
            "current_category": row.get("current_category", ""),
        })

    if use_openai:
        for start in range(0, len(row_dicts), batch_size):
            batch = row_dicts[start:start+batch_size]
            ai = classify_accounts_openai_batch(batch)
            if ai:
                for local_idx, result in ai.items():
                    global_idx = start + local_idx
                    if 0 <= global_idx < len(categories):
                        categories[global_idx], behaviors[global_idx], confidences[global_idx], reasons[global_idx], sources[global_idx] = result

    out["current_category"] = categories
    out["user_category"] = categories
    out["cost_behavior"] = behaviors
    out["classification_confidence"] = confidences
    out["classification_reason"] = reasons
    out["classification_source"] = sources
    return out

def normalize_for_pnl_category(category):
    cat = str(category or "")
    if cat in ["Purchases", "Cost of Revenue", "COGS", "Spare Parts", "Fuel"]:
        return "cost_of_revenue"
    if cat in ["Selling & Marketing", "Marketing", "Selling Opex"]:
        return "selling_marketing"
    if cat in ["Administrative Expenses", "Admin Opex", "Rent", "Utilities", "Payroll", "Maintenance", "Depreciation", "Bank Charges"]:
        return "admin_opex"
    if cat in ["Finance Costs"]:
        return "finance_costs"
    return "other_opex"
