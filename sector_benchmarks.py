import pandas as pd

SECTOR_OPTIONS = {
    "تجاري": {
        "en": "Trading",
        "activities": ["تجارة جملة", "تجارة تجزئة", "استيراد وتوزيع", "تجارة إلكترونية", "مواد غذائية أو استهلاكية", "معارض وبيع مباشر", "تجارة أخرى"],
        "benchmarks": {
            "gross_margin": {"safe": 0.25, "watch": 0.15, "label": "هامش مجمل الربح"},
            "net_margin": {"safe": 0.07, "watch": 0.03, "label": "هامش صافي الربح"},
            "opex_ratio": {"safe": 0.22, "watch": 0.35, "label": "نسبة المصاريف التشغيلية"},
            "direct_cost_ratio": {"safe": 0.75, "watch": 0.85, "label": "نسبة تكلفة البضاعة"},
            "return_rate": {"safe": 0.05, "watch": 0.10, "label": "نسبة المرتجعات"},
            "discount_rate": {"safe": 0.07, "watch": 0.12, "label": "نسبة الخصومات"},
            "margin_of_safety": {"safe": 0.20, "watch": 0.10, "label": "هامش الأمان"},
        },
        "notes": ["في القطاع التجاري، الأرقام الأكثر حساسية هي الهامش، الخصومات، المرتجعات، المخزون والتحصيل.", "ارتفاع المبيعات مع ارتفاع الخصومات أو المرتجعات قد يعني نموًا ضعيف الجودة."],
    },
    "مطاعم ومقاهي": {
        "en": "Restaurants & Cafes",
        "activities": ["مطعم", "مقهى", "مخبز وحلويات", "وجبات سريعة", "مطابخ سحابية", "تموين وإعاشة", "فروع متعددة"],
        "benchmarks": {
            "gross_margin": {"safe": 0.55, "watch": 0.40, "label": "هامش مجمل الربح"},
            "net_margin": {"safe": 0.10, "watch": 0.04, "label": "هامش صافي الربح"},
            "opex_ratio": {"safe": 0.45, "watch": 0.60, "label": "نسبة المصاريف التشغيلية"},
            "direct_cost_ratio": {"safe": 0.35, "watch": 0.45, "label": "تكلفة المواد/المبيعات"},
            "return_rate": {"safe": 0.01, "watch": 0.03, "label": "مرتجعات/إلغاءات"},
            "discount_rate": {"safe": 0.05, "watch": 0.10, "label": "خصومات"},
            "margin_of_safety": {"safe": 0.25, "watch": 0.12, "label": "هامش الأمان"},
        },
        "notes": ["في المطاعم، أي مرتجعات أو إلغاءات مرتفعة غالبًا تعني مشكلة جودة أو تجهيز أو توصيل.", "يجب تحليل الأداء حسب الفرع والوردية والمنتج عند توفر البيانات."],
    },
    "مقاولات ومشاريع": {
        "en": "Contracting & Projects",
        "activities": ["مقاولات عامة", "تشطيبات", "صيانة وتشغيل", "مشاريع توريد وتركيب", "مقاولات فرعية", "خدمات هندسية", "مشاريع أخرى"],
        "benchmarks": {
            "gross_margin": {"safe": 0.22, "watch": 0.12, "label": "هامش مجمل الربح"},
            "net_margin": {"safe": 0.08, "watch": 0.03, "label": "هامش صافي الربح"},
            "opex_ratio": {"safe": 0.18, "watch": 0.30, "label": "نسبة المصاريف التشغيلية"},
            "direct_cost_ratio": {"safe": 0.78, "watch": 0.88, "label": "تكلفة المشاريع"},
            "return_rate": {"safe": 0.00, "watch": 0.02, "label": "استبعادات/مرتجعات"},
            "discount_rate": {"safe": 0.03, "watch": 0.08, "label": "خصومات وتسويات"},
            "margin_of_safety": {"safe": 0.20, "watch": 0.10, "label": "هامش الأمان"},
        },
        "notes": ["في المقاولات، الخطر غالبًا في التدفق النقدي وليس الربح الظاهر: مستخلصات، احتجاز، دفعات مقدمة، وتكاليف منفذة غير مفوترة.", "يجب إضافة تقارير مشاريع/WIP لاحقًا لرفع دقة التحليل."],
    },
    "صحي": {
        "en": "Healthcare",
        "activities": ["عيادة", "مجمع طبي", "مختبر", "صيدلية", "مركز تجميل", "مركز علاج طبيعي", "خدمات صحية أخرى"],
        "benchmarks": {
            "gross_margin": {"safe": 0.45, "watch": 0.30, "label": "هامش مجمل الربح"},
            "net_margin": {"safe": 0.12, "watch": 0.06, "label": "هامش صافي الربح"},
            "opex_ratio": {"safe": 0.42, "watch": 0.58, "label": "نسبة المصاريف التشغيلية"},
            "direct_cost_ratio": {"safe": 0.50, "watch": 0.65, "label": "تكلفة الخدمة/المواد"},
            "return_rate": {"safe": 0.01, "watch": 0.04, "label": "استردادات/إلغاءات"},
            "discount_rate": {"safe": 0.08, "watch": 0.15, "label": "خصومات"},
            "margin_of_safety": {"safe": 0.25, "watch": 0.12, "label": "هامش الأمان"},
        },
        "notes": ["في النشاط الصحي، الخصومات والحملات قد ترفع المبيعات لكنها تضعف الهامش إذا لم ترتبط بإشغال فعلي.", "ينبغي لاحقًا ربط الإيراد بالطبيب/الخدمة/الفرع عند توفر البيانات."],
    },
    "خدمي": {
        "en": "Services",
        "activities": ["خدمات مهنية واستشارية", "خدمات تشغيل وصيانة", "خدمات لوجستية", "تأجير معدات أو مركبات", "خدمات تعليمية أو تدريبية", "خدمات تقنية", "خدمات أخرى"],
        "benchmarks": {
            "gross_margin": {"safe": 0.45, "watch": 0.30, "label": "هامش مجمل الربح"},
            "net_margin": {"safe": 0.12, "watch": 0.06, "label": "هامش صافي الربح"},
            "opex_ratio": {"safe": 0.40, "watch": 0.55, "label": "نسبة المصاريف التشغيلية"},
            "direct_cost_ratio": {"safe": 0.45, "watch": 0.60, "label": "نسبة تكلفة الإيراد"},
            "return_rate": {"safe": 0.00, "watch": 0.03, "label": "استردادات/مرتجعات"},
            "discount_rate": {"safe": 0.05, "watch": 0.12, "label": "خصومات"},
            "margin_of_safety": {"safe": 0.25, "watch": 0.15, "label": "هامش الأمان"},
        },
        "notes": ["في القطاع الخدمي، أكبر خطر غالبًا هو تضخم الرواتب والمصاريف الثابتة مقارنة بالإيراد.", "يجب ربط المصاريف التشغيلية بالطاقة الإنتاجية أو عدد العملاء أو ساعات الخدمة."],
    },
    "تأجير": {
        "en": "Rental",
        "activities": ["تأجير مركبات", "تأجير معدات", "تأجير عقارات", "تأجير قاطرات ومقطورات", "تأجير قصير الأجل", "تأجير طويل الأجل"],
        "benchmarks": {
            "gross_margin": {"safe": 0.38, "watch": 0.25, "label": "هامش مجمل الربح"},
            "net_margin": {"safe": 0.10, "watch": 0.04, "label": "هامش صافي الربح"},
            "opex_ratio": {"safe": 0.35, "watch": 0.50, "label": "نسبة المصاريف التشغيلية"},
            "direct_cost_ratio": {"safe": 0.55, "watch": 0.70, "label": "تكلفة التشغيل والصيانة"},
            "return_rate": {"safe": 0.00, "watch": 0.02, "label": "إلغاءات/مرتجعات"},
            "discount_rate": {"safe": 0.05, "watch": 0.10, "label": "خصومات"},
            "margin_of_safety": {"safe": 0.25, "watch": 0.12, "label": "هامش الأمان"},
        },
        "notes": ["في التأجير، الإشغال، الصيانة، التحصيل، والدفعات المقدمة أهم من المبيعات وحدها.", "ينبغي لاحقًا قراءة الأصول المؤجرة والعقود ومعدلات الإشغال عند توفرها."],
    },
    "صناعي": {
        "en": "Manufacturing",
        "activities": ["تصنيع غذائي", "تصنيع مواد بناء", "تصنيع خفيف", "تصنيع ثقيل", "تجميع وتعبئة", "تصنيع آخر"],
        "benchmarks": {
            "gross_margin": {"safe": 0.30, "watch": 0.20, "label": "هامش مجمل الربح"},
            "net_margin": {"safe": 0.08, "watch": 0.03, "label": "هامش صافي الربح"},
            "opex_ratio": {"safe": 0.25, "watch": 0.40, "label": "نسبة المصاريف التشغيلية"},
            "direct_cost_ratio": {"safe": 0.70, "watch": 0.82, "label": "نسبة تكلفة الإنتاج"},
            "return_rate": {"safe": 0.02, "watch": 0.06, "label": "مرتجعات"},
            "discount_rate": {"safe": 0.05, "watch": 0.10, "label": "خصومات"},
            "margin_of_safety": {"safe": 0.25, "watch": 0.12, "label": "هامش الأمان"},
        },
        "notes": ["في القطاع الصناعي، يجب التفريق بين تكلفة الإنتاج والمصاريف الإدارية والبيعية.", "المرتجعات قد تشير إلى عيوب جودة أو مشاكل مواصفات أو توريد."],
    },
    "SaaS": {
        "en": "SaaS",
        "activities": ["اشتراكات برمجية", "منصة SaaS B2B", "منصة SaaS B2C", "إضافات ERP أو محاسبة", "خدمات تقنية متكررة", "SaaS آخر"],
        "benchmarks": {
            "gross_margin": {"safe": 0.70, "watch": 0.55, "label": "هامش مجمل الربح"},
            "net_margin": {"safe": 0.10, "watch": 0.00, "label": "هامش صافي الربح"},
            "opex_ratio": {"safe": 0.65, "watch": 0.85, "label": "نسبة المصاريف التشغيلية"},
            "direct_cost_ratio": {"safe": 0.30, "watch": 0.45, "label": "تكلفة تقديم الخدمة"},
            "return_rate": {"safe": 0.01, "watch": 0.04, "label": "Refund Rate"},
            "discount_rate": {"safe": 0.10, "watch": 0.20, "label": "خصومات"},
            "margin_of_safety": {"safe": 0.20, "watch": 0.10, "label": "هامش الأمان"},
        },
        "notes": ["في SaaS، ارتفاع المصاريف التشغيلية قد يكون مقبولًا في مرحلة النمو إذا كان هناك إيراد متكرر واحتفاظ جيد بالعملاء.", "يجب لاحقًا إضافة ARR/MRR وChurn وCAC وLTV حتى يصبح التحليل كاملًا لهذا القطاع."],
    },
}

COUNTRY_OPTIONS = ["السعودية", "سوريا", "الإمارات", "قطر", "الكويت", "البحرين", "عمان", "الأردن", "مصر", "أخرى"]

def get_sector_config(sector: str):
    return SECTOR_OPTIONS.get(sector, SECTOR_OPTIONS["خدمي"])

def evaluate_metric(metric_key: str, value: float, sector: str):
    cfg = get_sector_config(sector)
    b = cfg["benchmarks"].get(metric_key)
    if not b:
        return "غير محدد", "لا يوجد معيار لهذا المؤشر.", "—"
    safe = b["safe"]
    watch = b["watch"]
    lower_better = metric_key in ["opex_ratio", "direct_cost_ratio", "return_rate", "discount_rate"]
    if lower_better:
        if value <= safe:
            return "جيد", f"ضمن الحد الآمن الأولي للقطاع: {safe:.1%}", "الحفاظ على المستوى الحالي مع متابعة التفاصيل."
        if value <= watch:
            return "يحتاج مراقبة", f"بين الحد الآمن {safe:.1%} وحد المراقبة {watch:.1%}", "افتح التفاصيل وحدد العملاء/الأصناف/الفروع المسببة."
        return "خطر", f"أعلى من حد المراقبة الأولي للقطاع: {watch:.1%}", "تحليل السبب وتشغيل تنبيه إجراء خلال 14 يوم."
    else:
        if value >= safe:
            return "جيد", f"أعلى من الحد الآمن الأولي للقطاع: {safe:.1%}", "الحفاظ على المستوى الحالي."
        if value >= watch:
            return "يحتاج مراقبة", f"بين حد المراقبة {watch:.1%} والحد الآمن {safe:.1%}", "تحسين الهامش أو ضبط التكلفة."
        return "خطر", f"أقل من حد المراقبة الأولي للقطاع: {watch:.1%}", "مراجعة التسعير والتكاليف أو المصاريف."

def sector_benchmark_table(sector: str):
    cfg = get_sector_config(sector)
    rows = []
    for key, b in cfg["benchmarks"].items():
        rows.append({
            "المؤشر": b["label"],
            "المفتاح": key,
            "الحد الآمن": b["safe"],
            "حد المراقبة": b["watch"],
            "اتجاه القراءة": "كلما انخفض كان أفضل" if key in ["opex_ratio", "direct_cost_ratio", "return_rate", "discount_rate"] else "كلما ارتفع كان أفضل",
        })
    return pd.DataFrame(rows)

def sector_notes_df(sector: str, country: str, activity: str):
    cfg = get_sector_config(sector)
    rows = [
        ["القطاع", sector, f"تم اختيار معايير {sector} كأساس أولي للمقارنة."],
        ["طبيعة النشاط", activity or "غير محددة", "تستخدم لتحسين تفسير المصاريف والتوقعات."],
        ["البلد", country or "غير محدد", "يستخدم لاحقًا في الضرائب والعملة والمتطلبات المحلية."],
    ]
    for n in cfg["notes"]:
        rows.append(["ملاحظة قطاعية", "", n])
    return pd.DataFrame(rows, columns=["العنصر", "القيمة", "الأثر على التحليل"])
