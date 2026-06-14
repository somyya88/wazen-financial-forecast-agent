from __future__ import annotations

import hashlib
import json
import os
from typing import Any

import pandas as pd


def _num(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or pd.isna(value):
            return default
    except Exception:
        pass
    try:
        return float(value)
    except Exception:
        return default


def _pct_value(value: Any) -> float | None:
    n = _num(value, None)
    return None if n is None else round(n * 100, 2)


def _money_value(value: Any) -> float | None:
    n = _num(value, None)
    return None if n is None else round(n, 2)


def _df_records(df: Any, limit: int = 8) -> list[dict[str, Any]]:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return []
    safe = df.head(limit).copy()
    for col in safe.columns:
        if pd.api.types.is_numeric_dtype(safe[col]):
            safe[col] = safe[col].apply(lambda x: None if pd.isna(x) else round(float(x), 4))
        else:
            safe[col] = safe[col].astype(str)
    return safe.to_dict("records")


def _safe_get(d: dict | None, *keys: str, default=None):
    cur = d or {}
    for key in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key, default)
    return cur


def _openai_key() -> str | None:
    key = os.getenv("OPENAI_API_KEY") or os.getenv("openai_api_key")
    if key:
        return key
    try:
        import streamlit as st
        return st.secrets.get("OPENAI_API_KEY") or st.secrets.get("openai_api_key")
    except Exception:
        return None


def openai_available() -> bool:
    return bool(_openai_key())


def build_ai_diagnosis_payload(
    models: dict,
    profile: dict,
    liquidity_model: dict | None = None,
    liquidity_diagnosis: dict | None = None,
    exec_kpis: dict | None = None,
    files: list[dict] | None = None,
) -> dict:
    """Build a compact, auditable payload for AI executive diagnosis.

    The payload intentionally sends aggregated metrics and top categories only.
    Raw trial-balance rows are not sent by default.
    """
    models = models or {}
    full_model = models.get("comprehensive_model", {}) or {}
    mg = full_model.get("management_pnl", {}) or {}
    metric_pack = full_model.get("metric_pack", {}) or {}
    metrics = metric_pack.get("metrics", {}) or {}
    health = full_model.get("financial_health_score", {}) or {}
    balance = full_model.get("balance_sheet", {}) or {}
    balance_metrics = balance.get("metrics", {}) or {}
    rq = full_model.get("revenue_quality_tb", {}) or {}
    comparison = full_model.get("comparative_analysis", {}) or {}
    comp_summary = comparison.get("summary", {}) if isinstance(comparison, dict) else {}
    source_truth = full_model.get("source_of_truth_report", {}) or {}
    period = source_truth.get("period", {}) if isinstance(source_truth, dict) else {}
    expense_model = models.get("expense_model") or {}

    cogs = _num(mg.get("cogs"), 0) or 0
    opex = _num(mg.get("opex"), 0) or 0
    revenue = _num(mg.get("revenue"), _num((exec_kpis or {}).get("revenue"), 0)) or 0
    gross_profit = _num(mg.get("gross_profit"), _num((exec_kpis or {}).get("gross_profit"), 0)) or 0
    net_profit = _num(mg.get("net_profit"), _num((exec_kpis or {}).get("net_profit"), 0)) or 0
    ebitda = _num(mg.get("ebitda"), revenue - cogs - opex) or 0

    def ratio(x):
        return round((x / revenue) * 100, 2) if revenue else None

    file_roles = []
    for f in files or []:
        file_roles.append({
            "file_name": f.get("file_name"),
            "selected_role": f.get("selected_role"),
            "detected_type": f.get("detected_type"),
            "confidence": f.get("confidence"),
        })

    data_gaps = []
    if not (liquidity_model or {}).get("cash", {}).get("available"):
        data_gaps.append("لا يوجد تقرير سيولة/كشف بنك مستقل؛ السيولة من الميزان فقط أو غير مكتملة.")
    if not (liquidity_model or {}).get("ar", {}).get("available"):
        data_gaps.append("لا توجد أعمار عملاء؛ التحصيل وDSO لا يثبتان من الميزان وحده.")
    if not (liquidity_model or {}).get("ap", {}).get("available"):
        data_gaps.append("لا توجد أعمار موردين؛ DPO تقديري إن ظهر.")
    if not rq.get("available"):
        data_gaps.append("مؤشرات نقاء الإيراد من الخصومات والمردودات غير متاحة بوضوح.")
    cogs_basis = str(mg.get("cogs_basis") or "")
    if cogs_basis and cogs_basis not in ["direct_cost_accounts", "periodic_inventory_formula"]:
        data_gaps.append("تكلفة الإيراد تحتاج تثبيت/مراجعة تصنيف قبل الحكم النهائي على مجمل الربح.")

    payload = {
        "company_context": {
            "company_name": profile.get("company_name"),
            "sector": profile.get("sector"),
            "activity": profile.get("activity"),
            "country": profile.get("country"),
            "business_model": profile.get("business_model"),
            "period_start": period.get("start_date") or profile.get("period_start"),
            "period_end": period.get("end_date") or profile.get("period_end"),
            "period_days": period.get("period_days") or profile.get("period_days"),
        },
        "data_scope": {
            "files": file_roles,
            "data_gaps": data_gaps,
            "analysis_confidence": health.get("confidence"),
            "health_score": health.get("score"),
            "health_label": health.get("label"),
            "source_period_basis": period.get("period_basis"),
        },
        "financial_metrics": {
            "revenue": _money_value(revenue),
            "cogs": _money_value(cogs),
            "cogs_ratio_pct": ratio(cogs),
            "gross_profit": _money_value(gross_profit),
            "gross_margin_pct": ratio(gross_profit),
            "operating_expenses": _money_value(opex),
            "opex_ratio_pct": ratio(opex),
            "ebitda": _money_value(ebitda),
            "operating_margin_pct": ratio(ebitda),
            "finance_cost": _money_value(mg.get("finance_bank", 0)),
            "tax_zakat": _money_value(mg.get("tax_zakat", 0)),
            "net_profit": _money_value(net_profit),
            "net_margin_pct": ratio(net_profit),
            "admin_opex": _money_value(mg.get("admin_opex")),
            "selling_marketing": _money_value(mg.get("selling_marketing")),
            "other_opex": _money_value(mg.get("other_opex")),
        },
        "revenue_quality": {
            "gross_sales": _money_value(_safe_get(rq, "cards", "gross_sales", default=None)),
            "discounts": _money_value(rq.get("discounts")),
            "returns": _money_value(rq.get("returns")),
            "net_sales": _money_value(_safe_get(rq, "cards", "net_sales", default=None)),
            "leakage_ratio_pct": _pct_value(rq.get("leakage_ratio")),
            "available_from_tb": bool(rq.get("available")),
        },
        "liquidity_and_working_capital": {
            "cash": _money_value(balance_metrics.get("cash")),
            "accounts_receivable": _money_value(balance_metrics.get("ar")),
            "inventory": _money_value(balance_metrics.get("inventory")),
            "current_assets": _money_value(balance_metrics.get("current_assets")),
            "current_liabilities": _money_value(balance_metrics.get("current_liabilities")),
            "working_capital": _money_value(balance_metrics.get("working_capital")),
            "total_liabilities": _money_value(balance_metrics.get("total_liabilities")),
            "equity": _money_value(balance_metrics.get("equity")),
            "current_ratio": _num(metrics.get("current_ratio"), None),
            "quick_ratio": _num(metrics.get("quick_ratio"), None),
            "cash_ratio": _num(metrics.get("cash_ratio"), None),
            "dso": _num(metrics.get("dso"), None),
            "dpo": _num(metrics.get("dpo"), None),
            "runway": _num(metrics.get("runway"), None),
            "liquidity_diagnosis": liquidity_diagnosis or {},
        },
        "expense_structure": {
            "by_category": _df_records(expense_model.get("by_category"), 10),
            "top_expenses": _df_records(expense_model.get("top_expenses"), 10),
            "source": expense_model.get("source"),
            "notes": expense_model.get("notes", []),
        },
        "comparison": {
            "available": bool(comparison.get("available")) if isinstance(comparison, dict) else False,
            "summary": comp_summary,
            "income": _df_records(comparison.get("income") if isinstance(comparison, dict) else None, 10),
        },
        "system_findings": _df_records(full_model.get("diagnostic_findings"), 7),
    }
    return payload


def payload_signature(payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def fallback_executive_diagnosis(payload: dict) -> dict:
    m = payload.get("financial_metrics", {})
    lq = payload.get("liquidity_and_working_capital", {})
    rq = payload.get("revenue_quality", {})
    gaps = payload.get("data_scope", {}).get("data_gaps", [])
    ctx = payload.get("company_context", {})

    revenue = _num(m.get("revenue"), 0) or 0
    cogs = _num(m.get("cogs"), 0) or 0
    gp_value = _num(m.get("gross_profit"), 0) or 0
    opex_value = _num(m.get("operating_expenses"), 0) or 0
    admin = _num(m.get("admin_opex"), None)
    selling = _num(m.get("selling_marketing"), None)
    net_profit = _num(m.get("net_profit"), 0) or 0
    gm = _num(m.get("gross_margin_pct"), None)
    cogs_ratio = _num(m.get("cogs_ratio_pct"), None)
    om = _num(m.get("operating_margin_pct"), None)
    nm = _num(m.get("net_margin_pct"), None)
    opex_ratio = _num(m.get("opex_ratio_pct"), None)
    leakage = _num(rq.get("leakage_ratio_pct"), None)
    current_ratio = _num(lq.get("current_ratio"), None)
    sector = ctx.get("sector") or "النشاط"

    def money(v):
        return f"{v:,.0f}"
    def pct(v):
        return "غير متاح" if v is None else f"{v:.1f}%"
    def ratio_of(v):
        return None if not revenue or v is None else (v / revenue) * 100

    if om is not None and om < 0:
        headline = "الهامش الأولي لا يتحول إلى ربح تشغيلي."
        msg = (
            f"سجلت الشركة إيراداً قدره {money(revenue)}، ومجمل ربح {money(gp_value)} بهامش {pct(gm)}. "
            f"لكن هامش التشغيل {pct(om)} وصافي الهامش {pct(nm)}؛ وهذا يعني أن نقطة الضعف ليست في وجود الإيراد فقط، "
            f"بل في قدرة هيكل التكلفة والمصاريف على الاحتفاظ بالربح بعد مجمل الربح."
        )
        risks = [
            "استمرار خسارة التشغيل يجعل زيادة الإيراد وحدها غير كافية إذا بقيت المصاريف أو تكلفة التنفيذ بنفس النمط.",
            "وجود مجمل ربح موجب مع نتيجة تشغيلية سالبة يشير إلى ضغط بعد تكلفة الإيراد: مصاريف إدارية، بيع وتسويق، أو تصنيف يحتاج تدقيقاً.",
        ]
    elif nm is not None and nm < 0:
        headline = "النشاط يخسر صافياً رغم وجود إيراد."
        msg = (
            f"الإيراد المسجل {money(revenue)}، ومجمل الربح {money(gp_value)}، لكن صافي النتيجة {money(net_profit)} بهامش {pct(nm)}. "
            "الأولوية هي تتبع انتقال الإيراد من المبيعات إلى مجمل الربح ثم التشغيل ثم الصافي لتحديد نقطة التآكل."
        )
        risks = [
            "تحمل التزامات مالية جديدة قبل تثبيت التكلفة والمصاريف قد يزيد الضغط على رأس المال العامل.",
            "القرار المالي سيبقى ناقصاً إذا لم تُفصل البنود غير المتكررة عن المصاريف التشغيلية المتكررة.",
        ]
    elif nm is not None and nm < 5:
        headline = "الربح موجود لكنه حساس لتغيرات التكلفة والتحصيل."
        msg = (
            f"صافي الهامش {pct(nm)}، وهذا يترك هامش أمان محدوداً أمام أي ارتفاع في تكلفة الإيراد أو تأخر في التحصيل. "
            f"ينبغي مراقبة المصاريف ونقاء الإيراد شهرياً قبل اعتماد أي التزام مالي جديد."
        )
        risks = ["الخصومات أو المرتجعات أو تأخر التحصيل قد تمتص الربح بسرعة."]
    else:
        headline = "القراءة الربحية مقبولة مبدئياً مع ضرورة ربطها بالنقد والتحصيل."
        msg = (
            f"الإيراد {money(revenue)} ومجمل الربح {money(gp_value)} بهامش {pct(gm)}. "
            "لا تظهر خسارة تشغيلية حادة من المؤشرات المجمعة، لكن الحكم النهائي يحتاج ربط الربح بالتدفق النقدي والتحصيل."
        )
        risks = ["الخطر قد يظهر من التحصيل أو رأس المال العامل وليس من قائمة الدخل وحدها."]

    evidence = [
        f"إجمالي الإيراد {money(revenue)}.",
        f"مجمل الربح {money(gp_value)}، وهامش مجمل الربح {pct(gm)}.",
        f"تكلفة الإيراد {money(cogs)}، وتعادل {pct(cogs_ratio)} من الإيراد.",
        f"المصاريف التشغيلية {money(opex_value)}، وتعادل {pct(opex_ratio)} من الإيراد.",
        f"صافي النتيجة {money(net_profit)}، وصافي الهامش {pct(nm)}.",
    ]
    if admin is not None:
        evidence.append(f"المصاريف الإدارية {money(admin)}، وتعادل {pct(ratio_of(admin))} من الإيراد.")
    if selling is not None:
        evidence.append(f"البيع والتسويق {money(selling)}، ويعادل {pct(ratio_of(selling))} من الإيراد.")
    if leakage is not None:
        evidence.append(f"تآكل الإيراد من الخصومات والمردودات {pct(leakage)}.")

    if current_ratio is None:
        cash = "لا توجد قراءة سيولة مكتملة من المصادر الحالية؛ لا يصح تحويل غياب المؤشر إلى صفر. يلزم تصنيف النقد والالتزامات المتداولة أو ربط كشف البنك وتقرير السيولة."
    else:
        cash = f"نسبة التداول {current_ratio:.2f}x من الميزان؛ هذه قراءة محاسبية للسيولة وليست إثباتاً لتوقيت النقد اليومي أو قدرة التحصيل."

    sector_actions = [
        "افصل تكلفة الإيراد عن المصاريف الإدارية والبيعية، ثم اربط التكلفة بالمشروع أو الخدمة أو العميل حسب طبيعة النشاط.",
        "استخرج أكبر 10 بنود تكلفة ومصاريف وقيّم هل هي منتجة للإيراد أم عبء ثابت على الهامش.",
        "راجع سياسة التسعير والخصومات والمردودات إذا كان تآكل الإيراد مؤثراً أو إذا كان مجمل الربح لا يغطي المصاريف.",
        "اربط السيولة بكشف البنك وأعمار العملاء قبل أي قرار يتعلق بالسداد أو الالتزامات قصيرة الأجل.",
    ]
    if "مقاول" in str(sector) or "مشاريع" in str(sector):
        sector_actions.insert(0, "في نشاط المقاولات والمشاريع، لا يكفي هامش الشركة الإجمالي؛ يجب تحليل هامش كل مشروع مع المستخلصات والاحتجازات وتكلفة التنفيذ.")

    return {
        "source": "rules",
        "headline": headline,
        "executive_message": msg,
        "evidence": evidence[:8],
        "risks": risks,
        "cash_and_working_capital": cash,
        "data_limits": gaps[:4] or ["القراءة مبنية على مصادر النموذج الحالية فقط."],
        "next_actions": sector_actions[:5],
        "confidence_note": "قراءة داخلية مبنية على قواعد وبيانات النموذج. فعّل AI مع مفتاح API للحصول على صياغة CFO مخصصة أعمق.",
        "decision_label": headline,
    }


def generate_ai_executive_diagnosis(payload: dict, model: str = "gpt-4o-mini") -> dict:
    key = _openai_key()
    if not key:
        out = fallback_executive_diagnosis(payload)
        out["source"] = "no_key"
        out["error"] = "لا يوجد مفتاح OpenAI في متغيرات البيئة أو Streamlit Secrets."
        return out

    system = """
أنت مدير مالي تنفيذي CFO ومحلل استراتيجي. اكتب تشخيصًا مخصصًا لصاحب عمل بناءً فقط على البيانات المرسلة.
قواعد صارمة:
- لا تحسب أرقامًا جديدة ولا تخترع Benchmark خارجيًا. استخدم القيم المرسلة فقط.
- لا تكتب نصًا عامًا يصلح لكل الشركات. اربط كل حكم برقم أو فجوة بيانات محددة.
- ميّز بوضوح بين: مؤكد من الميزان، تقديري، وغير قابل للحكم.
- إذا كان مجمل الربح جيدًا لكن التشغيل أو الصافي سلبي، لا تقل إن نموذج الربح آمن؛ قل إن الهامش الأولي لا يتحول إلى ربح تشغيلي.
- إذا كانت السيولة أو DSO غير متاحة، لا تعرضها كصفر ولا تستنتج أنها جيدة أو سيئة.
- اكتب بالعربية الفصحى المهنية فقط، بأسلوب CFO مباشر، دون عبارات تسويقية أو حشو.
- لا تذكر الالتزام المالي الجديد كإجراء أو تحذير افتراضي؛ ركز على الربحية، السيولة، المصاريف، الالتزامات، والتحصيل.
- يجب أن يتضمن التشخيص صراحة: إجمالي الإيراد، مجمل الربح، هامش مجمل الربح، تكلفة الإيراد ونسبتها، المصاريف التشغيلية ونسبتها، والمصاريف الإدارية/البيع والتسويق إذا كانت متاحة.
- التوصيات يجب أن تكون تنفيذية حسب القطاع، وليست عامة.
أعد الرد JSON صالح فقط بالمفاتيح التالية:
headline, executive_message, evidence, risks, cash_and_working_capital, data_limits, next_actions, confidence_note, decision_label
حيث evidence وrisks وdata_limits وnext_actions قوائم قصيرة من 2 إلى 5 عناصر.
"""
    user = {
        "task": "اكتب تشخيصًا تنفيذيًا ماليًا مخصصًا للشركة الحالية. لا تستخدم قالبًا ثابتًا. اربط الأرقام ببعضها: الإيراد، مجمل الربح، تكلفة الإيراد، المصاريف، صافي النتيجة، السيولة، جودة الإيراد، وفجوات البيانات. لا تذكر الالتزام المالي الجديد كتحذير افتراضي.",
        "payload": payload,
    }
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        resp = client.chat.completions.create(
            model=model,
            temperature=0.28,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
        )
        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
        data.setdefault("source", "ai")
        return data
    except Exception as exc:
        out = fallback_executive_diagnosis(payload)
        out["source"] = "error_fallback"
        out["error"] = str(exc)
        return out
