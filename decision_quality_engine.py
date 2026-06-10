import pandas as pd

def sf(x):
    try:
        return float(x)
    except Exception:
        return 0.0

def money(x):
    v = sf(x)
    if v < 0:
        return f"({abs(v):,.0f})"
    return f"{v:,.0f}"

def pct(x):
    v = sf(x)
    if abs(v) <= 1.5:
        v *= 100
    return f"{v:.1f}%"

def core_metrics(pnl_model, breakeven_model=None):
    revenue = sf(pnl_model.get("revenue", 0))
    gross_profit = sf(pnl_model.get("gross_profit", 0))
    net_profit = sf(pnl_model.get("net_profit", 0))
    cogs = sf(pnl_model.get("cogs", 0))
    opex = sf(pnl_model.get("opex", 0))
    be = sf((breakeven_model or {}).get("break_even_revenue", (breakeven_model or {}).get("breakeven_revenue", 0)))
    return {
        "revenue": revenue,
        "gross_profit": gross_profit,
        "net_profit": net_profit,
        "cogs": cogs,
        "opex": opex,
        "gross_margin": gross_profit / revenue if revenue else 0,
        "net_margin": net_profit / revenue if revenue else 0,
        "opex_ratio": opex / revenue if revenue else 0,
        "direct_cost_ratio": cogs / revenue if revenue else 0,
        "break_even_revenue": be,
        "margin_of_safety": ((revenue - be) / revenue) if revenue else 0,
    }

def data_visibility_status(models=None):
    models = models or {}
    # We intentionally flag missing cash/AR/AP because P&L files cannot answer liquidity questions.
    return pd.DataFrame([
        {"المجال": "الربحية", "الحالة": "محسوبة", "الأثر": "يمكن قراءة الهوامش والربح من قائمة الدخل."},
        {"المجال": "السيولة", "الحالة": "غير محسوبة", "الأثر": "لا يمكن معرفة قدرة الشركة على دفع الالتزامات دون كشف بنك."},
        {"المجال": "التحصيل", "الحالة": "غير محسوب", "الأثر": "لا يمكن تقدير خطر العملاء دون أعمار ذمم أو فواتير العملاء."},
        {"المجال": "الموردون", "الحالة": "غير محسوب", "الأثر": "لا يمكن بناء توقع نقدي دون أعمار الموردين أو جدول المدفوعات."},
    ])

def build_formula_table(pnl_model, breakeven_model=None, sector="خدمي"):
    m = core_metrics(pnl_model, breakeven_model)
    return pd.DataFrame([
        {
            "المؤشر": "هامش مجمل الربح",
            "طريقة الحساب": f"مجمل الربح ÷ الإيرادات = {money(m['gross_profit'])} ÷ {money(m['revenue'])}",
            "القيمة": pct(m["gross_margin"]),
            "المعيار القطاعي": "جيد إذا كان أعلى من 45% للقطاع الخدمي",
            "الفجوة": pct(m["gross_margin"] - 0.45),
            "القراءة": "قوي" if m["gross_margin"] >= 0.45 else "يحتاج معالجة",
        },
        {
            "المؤشر": "هامش صافي الربح",
            "طريقة الحساب": f"صافي الربح ÷ الإيرادات = {money(m['net_profit'])} ÷ {money(m['revenue'])}",
            "القيمة": pct(m["net_margin"]),
            "المعيار القطاعي": "جيد إذا كان أعلى من 12% للقطاع الخدمي",
            "الفجوة": pct(m["net_margin"] - 0.12),
            "القراءة": "قوي" if m["net_margin"] >= 0.12 else "مراقبة",
        },
        {
            "المؤشر": "نسبة المصاريف التشغيلية",
            "طريقة الحساب": f"المصاريف التشغيلية ÷ الإيرادات = {money(m['opex'])} ÷ {money(m['revenue'])}",
            "القيمة": pct(m["opex_ratio"]),
            "المعيار القطاعي": "تحت السيطرة إذا لم تتجاوز 40% تقريباً",
            "الفجوة": pct(m["opex_ratio"] - 0.40),
            "القراءة": "مراقبة" if m["opex_ratio"] > 0.40 else "جيد",
        },
        {
            "المؤشر": "نسبة تكلفة الإيراد",
            "طريقة الحساب": f"تكلفة الإيراد ÷ الإيرادات = {money(m['cogs'])} ÷ {money(m['revenue'])}",
            "القيمة": pct(m["direct_cost_ratio"]),
            "المعيار القطاعي": "تحت السيطرة إذا لم تتجاوز 45% تقريباً",
            "الفجوة": pct(m["direct_cost_ratio"] - 0.45),
            "القراءة": "جيد" if m["direct_cost_ratio"] <= 0.45 else "مراقبة",
        },
        {
            "المؤشر": "هامش الأمان",
            "طريقة الحساب": f"(الإيرادات - إيراد التعادل) ÷ الإيرادات = ({money(m['revenue'])} - {money(m['break_even_revenue'])}) ÷ {money(m['revenue'])}",
            "القيمة": pct(m["margin_of_safety"]),
            "المعيار القطاعي": "جيد إذا كان أعلى من 25%",
            "الفجوة": pct(m["margin_of_safety"] - 0.25),
            "القراءة": "جيد" if m["margin_of_safety"] >= 0.25 else "مراقبة",
        },
    ])

def top_expense_evidence(expense_model):
    if not expense_model:
        return []
    df = expense_model.get("by_category", pd.DataFrame())
    if df is None or df.empty:
        df = expense_model.get("top_expenses", pd.DataFrame())
    if df is None or df.empty:
        return []
    out = []
    amount_col = "amount" if "amount" in df.columns else None
    name_col = "category" if "category" in df.columns else ("account_name" if "account_name" in df.columns else None)
    if not amount_col or not name_col:
        return []
    tmp = df.copy()
    tmp[amount_col] = pd.to_numeric(tmp[amount_col], errors="coerce").fillna(0)
    tmp = tmp.sort_values(amount_col, ascending=False).head(3)
    for _, r in tmp.iterrows():
        out.append(f"{r.get(name_col)}: {money(r.get(amount_col))}")
    return out

def build_decision_action_plan(pnl_model, breakeven_model=None, expense_model=None, revenue_monthly=None):
    m = core_metrics(pnl_model, breakeven_model)
    top_exp = top_expense_evidence(expense_model)
    evidence_exp = "؛ ".join(top_exp) if top_exp else f"إجمالي المصاريف التشغيلية {money(m['opex'])}"

    rows = []

    if m["opex_ratio"] > 0.40:
        rows.append({
            "الأولوية": 1,
            "الموضوع": "المصاريف التشغيلية فوق مستوى الراحة",
            "الدليل الرقمي": f"النسبة {pct(m['opex_ratio'])} مقابل حد مراقبة 40%؛ {evidence_exp}",
            "الأثر على صاحب العمل": "الربح الحالي جيد، لكن أي نمو في المصاريف الثابتة سيجعل الربح أكثر حساسية لهبوط الإيرادات.",
            "القرار المطلوب": "تجميد أي مصروف ثابت جديد حتى مراجعة أكبر البنود وربطها بالإيراد أو التحصيل.",
            "المسؤول": "المالية + التشغيل",
            "KPI": "Opex ≤ 40% من الإيرادات",
        })
    else:
        rows.append({
            "الأولوية": 1,
            "الموضوع": "المصاريف التشغيلية تحت السيطرة",
            "الدليل الرقمي": f"النسبة {pct(m['opex_ratio'])}؛ {evidence_exp}",
            "الأثر على صاحب العمل": "الوضع مقبول حالياً، لكن يجب منع نمو المصاريف أسرع من الإيرادات.",
            "القرار المطلوب": "اعتماد سقف مصروفات شهري وربط أي بند جديد بزيادة متوقعة في الإيراد.",
            "المسؤول": "المالية",
            "KPI": "ثبات Opex كنسبة من الإيراد",
        })

    rows.append({
        "الأولوية": 2,
        "الموضوع": "جودة الربح لا تُقاس بصافي الربح فقط",
        "الدليل الرقمي": f"هامش صافي الربح {pct(m['net_margin'])} وهامش مجمل الربح {pct(m['gross_margin'])}",
        "الأثر على صاحب العمل": "الربح جيد محاسبياً، لكنه يحتاج اختباراً أمام التحصيل والسيولة قبل اعتباره آمناً بالكامل.",
        "القرار المطلوب": "طلب كشف البنك وأعمار العملاء والموردين لبناء توقع سيولة 13 أسبوعاً.",
        "المسؤول": "المالية",
        "KPI": "Cash Forecast خلال 10 أيام",
    })

    rows.append({
        "الأولوية": 3,
        "الموضوع": "تفسير تذبذب الإيرادات قبل التوسع",
        "الدليل الرقمي": "يوجد اختلاف واضح بين الأشهر؛ يجب معرفة هل أعلى شهر متكرر أم استثنائي.",
        "الأثر على صاحب العمل": "الاعتماد على متوسط مضخم قد يؤدي إلى التزام بمصاريف ثابتة أعلى من قدرة الإيراد المعتاد.",
        "القرار المطلوب": "تحليل سبب أعلى شهر وأقل شهر وربطهما بالعقود أو العملاء أو الفروع.",
        "المسؤول": "المبيعات + المالية",
        "KPI": "تحديد الإيراد المتكرر مقابل الاستثنائي",
    })

    rows.append({
        "الأولوية": 4,
        "الموضوع": "هامش الأمان جيد لكنه ليس نقداً متاحاً",
        "الدليل الرقمي": f"هامش الأمان {pct(m['margin_of_safety'])} وإيراد التعادل {money(m['break_even_revenue'])}",
        "الأثر على صاحب العمل": "الشركة بعيدة محاسبياً عن التعادل، لكن ذلك لا يضمن توفر النقد في موعد الرواتب والموردين.",
        "القرار المطلوب": "لا يتم اعتماد توسع أو زيادة رواتب قبل اختبار أثر القرار على السيولة الأسبوعية.",
        "المسؤول": "الإدارة + المالية",
        "KPI": "اختبار أثر أي قرار على 13 أسبوعاً",
    })

    rows.append({
        "الأولوية": 5,
        "الموضوع": "ثقة التحليل تحتاج بيانات تشغيلية",
        "الدليل الرقمي": "المتوفر يكفي للربحية، لكنه لا يكفي للسيولة والتحصيل والمخزون/الذمم.",
        "الأثر على صاحب العمل": "القرارات الكبيرة تحتاج رؤية نقدية لا توفرها قائمة الدخل وحدها.",
        "القرار المطلوب": "إضافة كشف بنك، أعمار العملاء، أعمار الموردين، وتفصيل الإيرادات حسب عميل/خدمة.",
        "المسؤول": "المالية",
        "KPI": "رفع درجة ثقة التحليل من متوسطة إلى عالية",
    })

    return pd.DataFrame(rows)

def build_owner_ratios_summary(pnl_model, breakeven_model=None, expense_model=None):
    m = core_metrics(pnl_model, breakeven_model)
    if m["net_margin"] >= 0.12 and m["opex_ratio"] <= 0.40:
        title = "الربحية جيدة والإنفاق تحت السيطرة"
        risk = "الخطر الرئيسي ليس الربح الحالي، بل جودة التحصيل والسيولة عند زيادة حجم النشاط."
        action = "ابدأ ببناء توقع سيولة قبل أي توسع."
    elif m["net_margin"] >= 0.12 and m["opex_ratio"] > 0.40:
        title = "الربحية جيدة لكن المصاريف قريبة من منطقة الضغط"
        risk = "إذا استمر نمو المصاريف التشغيلية أسرع من الإيراد، سيظهر الضغط أولاً في السيولة ثم في صافي الربح."
        action = "راجع أكبر بنود المصاريف قبل أي التزام ثابت جديد."
    else:
        title = "الربحية تحتاج معالجة قبل النمو"
        risk = "الهامش لا يترك مساحة كافية لامتصاص ارتفاع التكاليف أو تأخر التحصيل."
        action = "ابدأ بتحسين التسعير أو خفض تكلفة الإيراد والمصاريف غير المرتبطة بالمبيعات."
    return {"title": title, "risk": risk, "action": action}

def build_revenue_decision_table(revenue_monthly):
    if revenue_monthly is None or revenue_monthly.empty or "revenue" not in revenue_monthly.columns:
        return pd.DataFrame()
    df = revenue_monthly.copy()
    df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce").fillna(0)
    total = df["revenue"].sum()
    avg = df["revenue"].mean() if len(df) else 0
    best = df.loc[df["revenue"].idxmax()] if not df.empty else {}
    worst = df.loc[df["revenue"].idxmin()] if not df.empty else {}
    return pd.DataFrame([
        {"المؤشر": "أعلى شهر من إجمالي الإيرادات", "القيمة": pct(sf(best.get("revenue", 0)) / total if total else 0), "القراءة": "إذا كانت النسبة مرتفعة، يجب التأكد هل الشهر استثنائي أم متكرر."},
        {"المؤشر": "الفجوة بين أعلى وأقل شهر", "القيمة": money(sf(best.get("revenue", 0)) - sf(worst.get("revenue", 0))), "القراءة": "الفجوة الكبيرة تعني أن التخطيط على المتوسط وحده قد يكون مضللاً."},
        {"المؤشر": "متوسط الإيراد الشهري", "القيمة": money(avg), "القراءة": "يستخدم كخط أساس محافظ، وليس كضمان للتوسع."},
    ])
