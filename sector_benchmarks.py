import pandas as pd

SECTOR_OPTIONS = {
    "خدمي": {
        "en": "Services",
        "activities": ["خدمات مهنية واستشارية", "خدمات تشغيل وصيانة", "خدمات لوجستية", "تأجير معدات أو مركبات", "خدمات تعليمية أو تدريبية", "خدمات أخرى"],
        "benchmarks": {
            "gross_margin": {"safe": 0.45, "watch": 0.30, "label": "هامش مجمل الربح"},
            "net_margin": {"safe": 0.12, "watch": 0.06, "label": "هامش صافي الربح"},
            "opex_ratio": {"safe": 0.40, "watch": 0.55, "label": "نسبة المصاريف التشغيلية"},
            "direct_cost_ratio": {"safe": 0.45, "watch": 0.60, "label": "نسبة تكلفة الإيراد"},
            "margin_of_safety": {"safe": 0.25, "watch": 0.15, "label": "هامش الأمان"},
        },
        "notes": ["في القطاع الخدمي، أكبر خطر غالباً هو تضخم الرواتب والمصاريف الثابتة مقارنة بالإيراد.", "يجب ربط المصاريف التشغيلية بالطاقة الإنتاجية أو عدد العملاء أو ساعات الخدمة."],
    },
    "تجاري": {
        "en": "Trading",
        "activities": ["تجارة جملة", "تجارة تجزئة", "استيراد وتوزيع", "تجارة إلكترونية", "مواد غذائية أو استهلاكية", "تجارة أخرى"],
        "benchmarks": {
            "gross_margin": {"safe": 0.25, "watch": 0.15, "label": "هامش مجمل الربح"},
            "net_margin": {"safe": 0.07, "watch": 0.03, "label": "هامش صافي الربح"},
            "opex_ratio": {"safe": 0.22, "watch": 0.35, "label": "نسبة المصاريف التشغيلية"},
            "direct_cost_ratio": {"safe": 0.75, "watch": 0.85, "label": "نسبة تكلفة البضاعة"},
            "margin_of_safety": {"safe": 0.20, "watch": 0.10, "label": "هامش الأمان"},
        },
        "notes": ["في القطاع التجاري، هامش الربح عادة أقل من الخدمي، لذلك دوران المخزون والتحصيل أهم من الهامش وحده.", "ارتفاع تكلفة البضاعة طبيعي نسبياً، لكن يجب مراقبة المخزون والخصومات والمرتجعات."],
    },
    "صناعي": {
        "en": "Manufacturing",
        "activities": ["تصنيع غذائي", "تصنيع مواد بناء", "تصنيع خفيف", "تصنيع ثقيل", "تجميع وتعبئة", "تصنيع آخر"],
        "benchmarks": {
            "gross_margin": {"safe": 0.30, "watch": 0.20, "label": "هامش مجمل الربح"},
            "net_margin": {"safe": 0.08, "watch": 0.03, "label": "هامش صافي الربح"},
            "opex_ratio": {"safe": 0.25, "watch": 0.40, "label": "نسبة المصاريف التشغيلية"},
            "direct_cost_ratio": {"safe": 0.70, "watch": 0.82, "label": "نسبة تكلفة الإنتاج"},
            "margin_of_safety": {"safe": 0.25, "watch": 0.12, "label": "هامش الأمان"},
        },
        "notes": ["في القطاع الصناعي، يجب التفريق بين تكلفة الإنتاج والمصاريف الإدارية والبيعية.", "نقطة التعادل حساسة جداً للطاقة الإنتاجية والتكاليف الثابتة والإهلاك."],
    },
    "SaaS": {
        "en": "SaaS",
        "activities": ["اشتراكات برمجية", "منصة SaaS B2B", "منصة SaaS B2C", "إضافات ERP أو محاسبة", "خدمات تقنية متكررة", "SaaS آخر"],
        "benchmarks": {
            "gross_margin": {"safe": 0.70, "watch": 0.55, "label": "هامش مجمل الربح"},
            "net_margin": {"safe": 0.10, "watch": 0.00, "label": "هامش صافي الربح"},
            "opex_ratio": {"safe": 0.65, "watch": 0.85, "label": "نسبة المصاريف التشغيلية"},
            "direct_cost_ratio": {"safe": 0.30, "watch": 0.45, "label": "تكلفة تقديم الخدمة"},
            "margin_of_safety": {"safe": 0.20, "watch": 0.10, "label": "هامش الأمان"},
        },
        "notes": ["في SaaS، ارتفاع المصاريف التشغيلية قد يكون مقبولاً في مرحلة النمو إذا كان هناك إيراد متكرر واحتفاظ جيد بالعملاء.", "يجب لاحقاً إضافة مؤشرات ARR/MRR وChurn وCAC وLTV حتى يصبح التحليل كاملاً لهذا القطاع."],
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
    lower_better = metric_key in ["opex_ratio", "direct_cost_ratio"]
    if lower_better:
        if value <= safe:
            return "جيد", f"أفضل من الحد الآمن للقطاع: {safe:.1%}", "الحفاظ على المستوى الحالي."
        if value <= watch:
            return "يحتاج مراقبة", f"بين الحد الآمن {safe:.1%} وحد المراقبة {watch:.1%}", "مراجعة أكبر البنود المؤثرة."
        return "خطر", f"أعلى من حد المراقبة للقطاع: {watch:.1%}", "إجراء خفض أو إعادة تصنيف فوري."
    else:
        if value >= safe:
            return "جيد", f"أعلى من الحد الآمن للقطاع: {safe:.1%}", "الحفاظ على المستوى الحالي."
        if value >= watch:
            return "يحتاج مراقبة", f"بين حد المراقبة {watch:.1%} والحد الآمن {safe:.1%}", "تحسين الهامش أو ضبط التكلفة."
        return "خطر", f"أقل من حد المراقبة للقطاع: {watch:.1%}", "مراجعة التسعير والتكاليف."

def sector_benchmark_table(sector: str):
    cfg = get_sector_config(sector)
    rows = []
    for key, b in cfg["benchmarks"].items():
        rows.append({
            "المؤشر": b["label"],
            "المفتاح": key,
            "الحد الآمن": b["safe"],
            "حد المراقبة": b["watch"],
            "اتجاه القراءة": "كلما انخفض كان أفضل" if key in ["opex_ratio", "direct_cost_ratio"] else "كلما ارتفع كان أفضل",
        })
    return pd.DataFrame(rows)

def sector_notes_df(sector: str, country: str, activity: str):
    cfg = get_sector_config(sector)
    rows = [
        ["القطاع", sector, f"تم اختيار معايير {sector} كأساس للمقارنة."],
        ["طبيعة النشاط", activity or "غير محددة", "تستخدم لتحسين تفسير المصاريف والتوقعات."],
        ["البلد", country or "غير محدد", "يستخدم لاحقاً في الضرائب والعملة والمتطلبات المحلية."],
    ]
    for n in cfg["notes"]:
        rows.append(["ملاحظة قطاعية", "", n])
    return pd.DataFrame(rows, columns=["العنصر", "القيمة", "الأثر على التحليل"])
