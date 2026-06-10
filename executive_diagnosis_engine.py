import pandas as pd

def sf(x):
    try:
        return float(x)
    except Exception:
        return 0.0

def money(x):
    return f"{sf(x):,.0f}"

def pct(x):
    return f"{sf(x)*100:.1f}%"

def get_sector_thresholds(sector):
    # Practical sector thresholds used for narrative diagnosis, not absolute universal truth.
    defaults = {
        "خدمي": {"gross_margin": .45, "net_margin": .12, "opex_ratio": .40, "direct_cost_ratio": .45, "margin_safety": .25},
        "تجاري": {"gross_margin": .25, "net_margin": .07, "opex_ratio": .22, "direct_cost_ratio": .75, "margin_safety": .20},
        "صناعي": {"gross_margin": .30, "net_margin": .08, "opex_ratio": .25, "direct_cost_ratio": .70, "margin_safety": .25},
        "SaaS": {"gross_margin": .70, "net_margin": .10, "opex_ratio": .65, "direct_cost_ratio": .30, "margin_safety": .20},
    }
    return defaults.get(sector, defaults["خدمي"])

def extract_core_metrics(pnl_model, breakeven_model=None):
    revenue = sf(pnl_model.get("revenue", 0))
    gross_profit = sf(pnl_model.get("gross_profit", 0))
    net_profit = sf(pnl_model.get("net_profit", 0))
    cogs = sf(pnl_model.get("cogs", 0))
    opex = sf(pnl_model.get("opex", 0))
    gross_margin = gross_profit / revenue if revenue else 0
    net_margin = net_profit / revenue if revenue else 0
    opex_ratio = opex / revenue if revenue else 0
    direct_cost_ratio = cogs / revenue if revenue else 0
    margin_safety = sf((breakeven_model or {}).get("margin_of_safety", 0))
    break_even_revenue = sf((breakeven_model or {}).get("break_even_revenue", (breakeven_model or {}).get("breakeven_revenue", 0)))
    break_even_gap = sf((breakeven_model or {}).get("breakeven_gap", revenue - break_even_revenue))
    return {
        "revenue": revenue,
        "gross_profit": gross_profit,
        "net_profit": net_profit,
        "cogs": cogs,
        "opex": opex,
        "gross_margin": gross_margin,
        "net_margin": net_margin,
        "opex_ratio": opex_ratio,
        "direct_cost_ratio": direct_cost_ratio,
        "margin_safety": margin_safety,
        "break_even_revenue": break_even_revenue,
        "break_even_gap": break_even_gap,
    }

def identify_main_issue(metrics, sector):
    th = get_sector_thresholds(sector)
    gaps = []

    # Positive gap = issue severity.
    gaps.append(("نسبة المصاريف التشغيلية", metrics["opex_ratio"] - th["opex_ratio"], "opex"))
    gaps.append(("نسبة تكلفة الإيراد", metrics["direct_cost_ratio"] - th["direct_cost_ratio"], "direct_cost"))
    gaps.append(("هامش صافي الربح", th["net_margin"] - metrics["net_margin"], "net_margin"))
    gaps.append(("هامش مجمل الربح", th["gross_margin"] - metrics["gross_margin"], "gross_margin"))
    gaps.append(("هامش الأمان", th["margin_safety"] - metrics["margin_safety"], "safety"))

    gaps = sorted(gaps, key=lambda x: x[1], reverse=True)
    top = gaps[0]
    if top[1] <= 0:
        return ("لا توجد فجوة حادة مقابل معيار القطاع", "stability")
    return (top[0], top[2])

def build_owner_diagnosis(pnl_model, breakeven_model=None, expense_model=None, sector="خدمي", country="السعودية", activity=""):
    m = extract_core_metrics(pnl_model, breakeven_model)
    th = get_sector_thresholds(sector)
    issue_label, issue_key = identify_main_issue(m, sector)

    if issue_key == "opex":
        situation = (
            f"النشاط يحقق ربحاً حالياً، لكن المصاريف التشغيلية تستهلك {pct(m['opex_ratio'])} من الإيرادات. "
            f"هذا يعني أن جزءاً كبيراً من المبيعات يذهب إلى مصاريف الإدارة والتشغيل قبل أن يتحول إلى ربح صافٍ."
        )
        risk = (
            "الخطر ليس في رقم الربح الحالي فقط، بل في قابلية هذا الربح للاستمرار. "
            "إذا زادت الرواتب أو الإيجارات أو المصاريف الإدارية بنفس الوتيرة دون نمو مماثل في الإيرادات، سيبدأ الضغط بالظهور في السيولة والالتزامات الشهرية حتى لو بقيت المبيعات جيدة ظاهرياً."
        )
        action = (
            "الإجراء العملي: لا تبدأ بخفض عشوائي. ابدأ بمراجعة أكبر 5 بنود مصاريف تشغيلية، وحدد أيها مرتبط مباشرة بالإيراد وأيها ثابت لا يتحرك مع المبيعات. "
            "أي بند ثابت لا يخدم الإيراد أو التحصيل يجب إيقاف نموه أو إعادة التفاوض عليه قبل أي التزام جديد."
        )
        next_kpi = f"إبقاء المصاريف التشغيلية دون {pct(th['opex_ratio'])} من الإيرادات خلال الشهر القادم."
        owner = "الإدارة المالية + التشغيل"
    elif issue_key == "direct_cost":
        situation = (
            f"تكلفة الإيراد تمثل {pct(m['direct_cost_ratio'])} من الإيرادات. "
            "هذا يعني أن جزءاً مهماً من المبيعات يخرج مباشرة في المشتريات أو تكلفة تقديم الخدمة قبل الوصول إلى مجمل الربح."
        )
        risk = (
            "إذا لم تكن تكلفة الإيراد مضبوطة، فإن زيادة المبيعات قد لا تعني بالضرورة زيادة الربح. "
            "قد يبيع النشاط أكثر لكنه يربح أقل بسبب تسعير غير كافٍ أو مشتريات مرتفعة أو هدر في التشغيل."
        )
        action = (
            "الإجراء العملي: راجع تسعير الخدمة أو المنتج مقابل تكلفة تقديمه. افصل المشتريات والتكاليف المباشرة عن المصاريف الإدارية، ثم حدد هامش الربح لكل خدمة أو منتج رئيسي. "
            "لا تعتمد قرار نمو المبيعات قبل معرفة أي الخدمات أو المنتجات فعلاً مربحة."
        )
        next_kpi = f"خفض تكلفة الإيراد باتجاه حد القطاع الآمن {pct(th['direct_cost_ratio'])} أو تبريرها بعقود ذات هامش واضح."
        owner = "الإدارة المالية + المشتريات/التشغيل"
    elif issue_key == "net_margin":
        situation = (
            f"هامش صافي الربح يبلغ {pct(m['net_margin'])}. "
            "هذا هو الجزء الذي يبقى فعلياً من الإيرادات بعد تكلفة الإيراد والمصاريف."
        )
        risk = (
            "هامش صافي الربح المحدود يجعل النشاط حساساً لأي خطأ بسيط: تأخر تحصيل، خصم إضافي، زيادة رواتب، أو ارتفاع تكلفة شراء. "
            "عندها قد تبدو المبيعات جيدة بينما الربح الفعلي لا يكفي لتغطية الالتزامات أو تمويل النمو."
        )
        action = (
            "الإجراء العملي: لا تركز على زيادة المبيعات فقط. راجع مزيج الإيرادات: أي عميل أو خدمة تعطي هامشاً أعلى؟ وأي بند يستهلك الربح؟ "
            "ابدأ بتحسين التسعير أو تقليل الخصومات أو خفض البنود التي لا تؤثر على الإيراد مباشرة."
        )
        next_kpi = f"رفع هامش صافي الربح تدريجياً باتجاه {pct(th['net_margin'])} على الأقل."
        owner = "الإدارة المالية + المبيعات"
    elif issue_key == "gross_margin":
        situation = (
            f"هامش مجمل الربح يبلغ {pct(m['gross_margin'])}. "
            "هذا المؤشر يوضح قدرة الإيرادات على تغطية تكلفة الإيراد المباشرة قبل المصاريف الإدارية والتسويقية."
        )
        risk = (
            "ضعف مجمل الربح يعني أن المشكلة تقع غالباً قبل المصاريف الإدارية: في السعر، تكلفة الشراء، تكلفة التشغيل، أو طريقة احتساب تكلفة الخدمة. "
            "عندها لن يحل خفض المصاريف الإدارية المشكلة وحده."
        )
        action = (
            "الإجراء العملي: افصل تكلفة كل نشاط أو خدمة، وحدد أين يتآكل الهامش. "
            "راجع الأسعار والمشتريات والهدر التشغيلي قبل اتخاذ قرار خفض عام للمصاريف."
        )
        next_kpi = f"رفع هامش مجمل الربح باتجاه معيار القطاع {pct(th['gross_margin'])}."
        owner = "الإدارة المالية + التشغيل"
    elif issue_key == "safety":
        situation = (
            f"هامش الأمان من نقطة التعادل يبلغ {pct(m['margin_safety'])}. "
            f"فجوة التعادل الحالية تعادل {money(m['break_even_gap'])}، وهي المسافة بين الإيرادات الحالية وإيراد التعادل."
        )
        risk = (
            "كلما انخفض هامش الأمان، اقترب النشاط من مستوى لا يحقق ربحاً. "
            "الخطر هنا أن أي تراجع في المبيعات أو زيادة في التكاليف الثابتة قد يحول الربحية إلى خسارة بسرعة."
        )
        action = (
            "الإجراء العملي: امنع إضافة تكاليف ثابتة جديدة حتى يرتفع هامش الأمان. "
            "ركز على رفع الإيراد المتكرر أو خفض التكاليف الثابتة أو تحسين هامش المساهمة."
        )
        next_kpi = f"رفع هامش الأمان إلى {pct(th['margin_safety'])} على الأقل."
        owner = "الإدارة المالية + الإدارة العامة"
    else:
        situation = (
            f"الأرقام الحالية تظهر أداءً جيداً مقارنة بمعايير قطاع {sector}. "
            f"هامش صافي الربح {pct(m['net_margin'])} وهامش الأمان {pct(m['margin_safety'])} يعطيان مساحة تشغيل مريحة نسبياً."
        )
        risk = (
            "الخطر في هذه الحالة ليس وجود مشكلة حادة الآن، بل فقدان الانضباط مع زيادة حجم النشاط. "
            "كثير من الشركات تبدأ مربحة ثم يتراجع هامشها عندما تزيد المصاريف الثابتة أسرع من الإيراد."
        )
        action = (
            "الإجراء العملي: ثبّت قواعد الإنفاق والتحصيل قبل أي توسع. "
            "ضع سقفاً للمصاريف التشغيلية، وراجع أثر كل التزام جديد على نقطة التعادل."
        )
        next_kpi = f"الحفاظ على هامش صافي ربح فوق {pct(th['net_margin'])} ومصاريف تشغيلية ضمن {pct(th['opex_ratio'])}."
        owner = "الإدارة المالية"

    return {
        "title": "التشخيص التنفيذي",
        "issue": issue_label,
        "situation": situation,
        "risk": risk,
        "action": action,
        "next_kpi": next_kpi,
        "owner": owner,
        "sector": sector,
        "country": country,
        "activity": activity,
    }

def build_professional_actions(pnl_model, breakeven_model=None, expense_model=None, sector="خدمي"):
    m = extract_core_metrics(pnl_model, breakeven_model)
    th = get_sector_thresholds(sector)
    actions = []

    if m["opex_ratio"] > th["opex_ratio"]:
        actions.append({
            "الأولوية": 1,
            "المشكلة": "المصاريف التشغيلية تستهلك نسبة مرتفعة من الإيرادات",
            "لماذا يهم؟": f"النسبة الحالية {pct(m['opex_ratio'])} مقابل معيار قطاعي آمن يقارب {pct(th['opex_ratio'])}. هذا يضغط على الربح ويجعل أي نمو غير منضبط أكثر خطورة.",
            "الإجراء العملي": "استخراج أكبر 5 بنود مصاريف، فصل الثابت عن المتغير، وإيقاف أو إعادة تفاوض أي بند ثابت غير مرتبط بالإيراد أو التحصيل.",
            "المسؤول": "الإدارة المالية + التشغيل",
            "مؤشر المتابعة": f"خفض/تثبيت المصاريف التشغيلية دون {pct(th['opex_ratio'])} من الإيرادات.",
        })
    if m["direct_cost_ratio"] > th["direct_cost_ratio"]:
        actions.append({
            "الأولوية": 2,
            "المشكلة": "تكلفة الإيراد مرتفعة مقارنة بطبيعة القطاع",
            "لماذا يهم؟": f"النسبة الحالية {pct(m['direct_cost_ratio'])}. ارتفاعها يعني أن المبيعات قد لا تتحول إلى ربح كافٍ.",
            "الإجراء العملي": "مراجعة التسعير والمشتريات وتكلفة تقديم الخدمة، وتحديد ربحية كل منتج أو خدمة رئيسية.",
            "المسؤول": "الإدارة المالية + المشتريات/التشغيل",
            "مؤشر المتابعة": f"تقريب تكلفة الإيراد من معيار القطاع {pct(th['direct_cost_ratio'])}.",
        })
    if m["margin_safety"] < th["margin_safety"]:
        actions.append({
            "الأولوية": 3,
            "المشكلة": "هامش الأمان من نقطة التعادل غير كافٍ",
            "لماذا يهم؟": f"الهامش الحالي {pct(m['margin_safety'])}. هذا يعني أن النشاط لا يملك مساحة كافية لتحمل انخفاض الإيرادات أو ارتفاع التكاليف.",
            "الإجراء العملي": "عدم إضافة التزامات ثابتة جديدة، ورفع الإيراد المتكرر أو خفض التكاليف الثابتة.",
            "المسؤول": "الإدارة العامة + المالية",
            "مؤشر المتابعة": f"رفع هامش الأمان إلى {pct(th['margin_safety'])} على الأقل.",
        })
    if m["net_margin"] < th["net_margin"]:
        actions.append({
            "الأولوية": 4,
            "المشكلة": "صافي الربح لا يعطي مساحة كافية للمخاطر",
            "لماذا يهم؟": f"الهامش الحالي {pct(m['net_margin'])}. أي تأخر تحصيل أو زيادة تكلفة قد يمتص الربح بسرعة.",
            "الإجراء العملي": "تحليل العملاء أو الخدمات الأعلى ربحية، وتقليل الخصومات أو البنود التي لا تضيف قيمة مباشرة.",
            "المسؤول": "الإدارة المالية + المبيعات",
            "مؤشر المتابعة": f"رفع هامش صافي الربح إلى {pct(th['net_margin'])} أو أعلى.",
        })

    if not actions:
        actions.append({
            "الأولوية": 1,
            "المشكلة": "لا توجد فجوة حادة مقابل معيار القطاع، لكن الانضباط مطلوب",
            "لماذا يهم؟": "الأداء الحالي جيد، لكن غياب حدود إنفاق وتحكم شهري قد يحول النمو إلى ضغط على الهامش لاحقاً.",
            "الإجراء العملي": "اعتماد سقف مصاريف شهري، ومراجعة أي تكلفة ثابتة جديدة قبل الالتزام بها.",
            "المسؤول": "الإدارة المالية",
            "مؤشر المتابعة": "الحفاظ على المصاريف والهوامش ضمن حدود القطاع.",
        })

    return pd.DataFrame(actions)
