from __future__ import annotations

from typing import Any
import pandas as pd


def _norm(text: Any) -> str:
    s = "" if text is None else str(text).strip().lower()
    repl = {"أ":"ا", "إ":"ا", "آ":"ا", "ة":"ه", "ى":"ي", "ـ":"", "\u200f":"", "\u200e":""}
    for a, b in repl.items():
        s = s.replace(a, b)
    return s


def sector_key(profile: dict | None) -> str:
    profile = profile or {}
    text = _norm(" ".join([str(profile.get(k, "")) for k in ["sector", "activity", "business_model", "sales_channel"]]))
    if any(k in text for k in ["saas", "برمج", "منصه", "منصة", "اشتراك", "تقنيه", "تقنية", "erp"]):
        return "saas"
    if any(k in text for k in ["مطعم", "مقهى", "مقاهي", "مخبز", "تموين", "food", "restaurant", "كافيه"]):
        return "restaurants"
    if any(k in text for k in ["مقاول", "مشروع", "مشاريع", "تشطيب", "انشاء", "construction", "wip"]):
        return "contracting"
    if any(k in text for k in ["صناع", "تصنيع", "مصنع", "انتاج", "تجميع"]):
        return "manufacturing"
    if any(k in text for k in ["تأجير", "تاجير", "ايجار", "معدات", "مركبات", "قاطرات", "مقطورات", "rental"]):
        return "rental"
    if any(k in text for k in ["صحي", "عياد", "طبي", "مختبر", "صيدليه", "صيدلية", "تجميل"]):
        return "healthcare"
    if any(k in text for k in ["تجارة", "تجاري", "تجزئه", "تجزئة", "جمله", "جملة", "استيراد", "توزيع", "e-commerce", "الكترون"]):
        return "trading"
    return "services"


SECTOR_PROFILES = {
    "saas": {
        "title": "SaaS / برمجيات واشتراكات",
        "mindset": "يركز التحليل على اقتصاد الباقة: تكلفة تقديم الخدمة، الدعم، التنفيذ، الاحتفاظ بالعملاء، وجودة الإيراد المتكرر.",
        "core_metrics": ["Gross Margin", "Operating Margin", "Admin %", "S&M %", "Runway", "DSO", "CAC لاحقًا", "Churn لاحقًا"],
        "cost_logic": "رواتب الدعم والتنفيذ والاستضافة وخدمات التشغيل المباشرة تُعامل كتكلفة إيراد إذا كانت مرتبطة بتقديم الخدمة.",
        "special_files": ["مبيعات اشتراكات أو MRR/ARR", "قائمة العملاء والاشتراكات", "Churn", "تكلفة اكتساب العملاء"],
        "watchouts": ["لا تجعل كل الرواتب إدارية؛ رواتب الدعم قد تغيّر هامش الربح الإجمالي.", "نمو الإيراد لا يكفي إذا كان التحصيل بطيئًا أو الخصومات عالية."],
        "inventory_relevance": "conditional",
        "health_weights": {"profitability": 25, "liquidity": 20, "working_capital": 15, "solvency": 10, "cash_quality": 30},
    },
    "trading": {
        "title": "تجارة / توزيع / تجزئة",
        "mindset": "يركز التحليل على الهامش بعد تكلفة البضاعة، سرعة دوران المخزون، الخصومات والمرتجعات، وتركيز العملاء والموردين.",
        "core_metrics": ["Gross Margin", "Inventory Turnover", "DIO", "DSO", "DPO", "CCC", "Discounts", "Returns"],
        "cost_logic": "تكلفة البضاعة والمشتريات والشحن المباشر والجمارك تدخل في تكلفة الإيراد عند ارتباطها بالبيع.",
        "special_files": ["تقرير أصناف", "مخزون أول وآخر", "مرتجعات وخصومات", "مبيعات العملاء"],
        "watchouts": ["ارتفاع المبيعات مع ارتفاع الخصومات أو المخزون قد يعني نموًا يستهلك النقد.", "نسبة التداول قد تبدو جيدة إذا كان المخزون كبيرًا، لكنها لا تعني نقدًا جاهزًا."],
        "inventory_relevance": "core",
        "health_weights": {"profitability": 22, "liquidity": 18, "working_capital": 30, "solvency": 10, "cash_quality": 20},
    },
    "restaurants": {
        "title": "مطاعم ومقاهي",
        "mindset": "يركز التحليل على تكلفة المواد، العمالة، الهدر، أداء الفروع، ومتوسط المبيعات اليومية، لأن الربحية تتآكل بسرعة من التشغيل اليومي.",
        "core_metrics": ["Food Cost %", "Labor %", "Gross Margin", "Daily Sales", "Waste", "Branch Margin", "Inventory Turnover"],
        "cost_logic": "المواد الغذائية، التغليف، رواتب التشغيل المباشر، وتكاليف التوصيل المرتبطة بالطلب تُقرأ كتكلفة مباشرة أو تشغيلية حسب التفصيل.",
        "special_files": ["مبيعات يومية", "مبيعات حسب الفرع", "مخزون ومواد", "هدر/توالف", "توصيل وعمولات التطبيقات"],
        "watchouts": ["ملف المبيعات الشهري وحده لا يكشف مشكلة الهدر أو اختلاف الفروع.", "الخصومات والتطبيقات قد ترفع المبيعات وتخفض الهامش في نفس الوقت."],
        "inventory_relevance": "core",
        "health_weights": {"profitability": 27, "liquidity": 18, "working_capital": 20, "solvency": 10, "cash_quality": 25},
    },
    "contracting": {
        "title": "مقاولات ومشاريع",
        "mindset": "يركز التحليل على هامش المشروع، المستخلصات، الأعمال تحت التنفيذ، الاحتجازات، والضغط النقدي بين التنفيذ والتحصيل.",
        "core_metrics": ["Project Margin", "WIP", "DSO", "Retention", "DPO", "Cash Gap", "Gross Margin"],
        "cost_logic": "مواد المشروع، أجور العمالة المباشرة، مقاولون فرعيون، معدات المشروع، ومصاريف الموقع تُقرأ كتكلفة مشروع لا كمصاريف إدارية.",
        "special_files": ["كشف مشاريع", "مستخلصات", "احتجازات", "تكلفة مشروع", "دفعات مقدمة"],
        "watchouts": ["الربح المحاسبي قد يكون جيدًا والسيولة سيئة بسبب تأخر المستخلصات.", "تحليل الشركة ككل قد يخفي مشروعًا خاسرًا داخل محفظة المشاريع."],
        "inventory_relevance": "conditional",
        "health_weights": {"profitability": 20, "liquidity": 25, "working_capital": 35, "solvency": 10, "cash_quality": 10},
    },
    "manufacturing": {
        "title": "صناعة / إنتاج",
        "mindset": "يركز التحليل على تكلفة المواد والعمل المباشر والتكاليف الصناعية غير المباشرة، الطاقة الإنتاجية، الهدر، والمخزون.",
        "core_metrics": ["COGS %", "Gross Margin", "Inventory Turnover", "DIO", "Production Overhead", "Capacity"],
        "cost_logic": "المواد الخام، العمل المباشر، الطاقة، الصيانة الصناعية، والتكاليف الصناعية غير المباشرة يجب ربطها بتكلفة الإنتاج.",
        "special_files": ["مخزون خام وتام", "أوامر إنتاج", "تكلفة إنتاج", "توالف وهدر", "طاقة إنتاجية"],
        "watchouts": ["تضخم المخزون قد يجمّل الربح مؤقتًا لكنه يحبس النقد.", "خلط المصاريف الصناعية مع الإدارية يضلل هامش التشغيل."],
        "inventory_relevance": "core",
        "health_weights": {"profitability": 25, "liquidity": 18, "working_capital": 27, "solvency": 15, "cash_quality": 15},
    },
    "rental": {
        "title": "تأجير / أصول مؤجرة",
        "mindset": "يركز التحليل على إيراد الأصل، معدل الإشغال، الصيانة، التحصيل، والعائد على الأصول الثابتة.",
        "core_metrics": ["Revenue per Asset", "Utilization", "Maintenance %", "Fixed Asset Turnover", "DSO", "Cash Runway"],
        "cost_logic": "الصيانة والتشغيل والتأمين المرتبط بالأصول المؤجرة تُقرأ كتكلفة تشغيل مباشرة أو تكلفة إيراد حسب النشاط.",
        "special_files": ["قائمة الأصول المؤجرة", "عقود التأجير", "إشغال/استخدام", "صيانة", "تحصيل العملاء"],
        "watchouts": ["الأصل قد يحقق مبيعات لكنه لا يغطي الصيانة والتمويل.", "العائد على الأصول مهم أكثر من نمو الإيراد وحده."],
        "inventory_relevance": "low",
        "health_weights": {"profitability": 22, "liquidity": 23, "working_capital": 20, "solvency": 20, "cash_quality": 15},
    },
    "healthcare": {
        "title": "صحة / عيادات / مختبرات",
        "mindset": "يركز التحليل على هامش الخدمة، تحصيل شركات التأمين، إنتاجية الطبيب/الخدمة، والإشغال.",
        "core_metrics": ["Service Margin", "Insurance AR", "DSO", "Revenue per Doctor", "Utilization", "Discounts"],
        "cost_logic": "تكلفة الطبيب أو الفني أو المواد الطبية المباشرة تُقرأ كتكلفة خدمة عند ارتباطها بالخدمة المقدمة.",
        "special_files": ["إيراد حسب خدمة", "إيراد حسب طبيب", "مطالبات التأمين", "أعمار التأمين", "نسب الإشغال"],
        "watchouts": ["التأمين قد يرفع الإيراد ويؤخر النقد.", "الخصومات والحملات يجب قراءتها مع هامش الخدمة لا مع المبيعات فقط."],
        "inventory_relevance": "conditional",
        "health_weights": {"profitability": 25, "liquidity": 20, "working_capital": 25, "solvency": 10, "cash_quality": 20},
    },
    "services": {
        "title": "خدمات عامة / مهنية",
        "mindset": "يركز التحليل على إنتاجية الفريق، هامش الخدمة أو المشروع، الرواتب كنسبة من الإيراد، والتحصيل.",
        "core_metrics": ["Gross Margin", "Payroll %", "Operating Margin", "DSO", "Revenue per Employee", "Project Margin"],
        "cost_logic": "رواتب الفريق المنفذ للخدمة تُقرأ كتكلفة إيراد، أما الإدارة العامة فتُقرأ كمصاريف إدارية.",
        "special_files": ["ساعات أو مشاريع", "رواتب حسب الوظيفة", "مبيعات حسب عميل", "أعمار العملاء"],
        "watchouts": ["الخدمات قد تبدو مربحة إذا صنفت رواتب التنفيذ كإدارة بالخطأ.", "التحصيل الطويل يمول العميل من سيولة الشركة."],
        "inventory_relevance": "low",
        "health_weights": {"profitability": 27, "liquidity": 22, "working_capital": 20, "solvency": 10, "cash_quality": 21},
    },
}


UNIVERSAL_CORE = [
    "قائمة الدخل", "المركز المالي", "Gross Margin", "Operating Margin", "Net Margin", "Current Ratio", "Quick Ratio", "Cash Ratio", "Debt Ratio", "Debt to Equity", "تحليل رأسي", "تحليل أفقي عند توفر مقارنة"
]


def get_sector_intelligence_profile(profile: dict | None) -> dict:
    key = sector_key(profile)
    cfg = SECTOR_PROFILES.get(key, SECTOR_PROFILES["services"]).copy()
    cfg["key"] = key
    cfg["universal_core"] = UNIVERSAL_CORE
    cfg["company_context"] = profile or {}
    return cfg


def metric_applicability(metric_key: str, profile: dict | None, evidence: dict | None = None) -> dict:
    cfg = get_sector_intelligence_profile(profile)
    inv_rel = cfg.get("inventory_relevance", "conditional")
    evidence = evidence or {}
    has_inventory = bool(evidence.get("has_inventory"))

    universal = {"gross_margin", "cogs_ratio", "operating_margin", "net_margin", "admin_ratio", "sm_ratio", "current_ratio", "quick_ratio", "cash_ratio", "working_capital", "debt_ratio", "debt_to_equity", "asset_turnover", "roa", "roe"}
    cash_specific = {"runway", "ocf_net_income"}
    inventory_metrics = {"inventory_turnover", "dio"}
    wc_metrics = {"dso", "dpo", "ccc", "receivables_turnover", "payables_turnover"}

    if metric_key in universal:
        return {"state": "أساسي", "display": "summary", "reason": "مؤشر مالي عام ينطبق على معظم القطاعات."}
    if metric_key in cash_specific:
        return {"state": "مهم عند توفر البيانات", "display": "detail", "reason": "يحتاج تقرير سيولة أو قائمة تدفقات أو بيانات نقدية موثوقة."}
    if metric_key in inventory_metrics:
        if inv_rel == "core":
            return {"state": "أساسي", "display": "summary", "reason": "المخزون عنصر جوهري في هذا القطاع."}
        if has_inventory or inv_rel == "conditional":
            return {"state": "مهم عند توفر البيانات", "display": "detail", "reason": "يعرض إذا ظهرت حسابات مخزون أو ملفات مخزون."}
        return {"state": "غير قابل للتطبيق غالبًا", "display": "hide", "reason": "النشاط لا يعتمد عادة على مخزون جوهري ما لم تظهر بيانات تثبت العكس."}
    if metric_key in wc_metrics:
        return {"state": "مهم عند توفر البيانات", "display": "summary", "reason": "رأس المال العامل يتغير أثره حسب نموذج البيع والتحصيل والموردين."}
    if metric_key in {"break_even_sales", "margin_of_safety"}:
        return {"state": "تقديري", "display": "detail", "reason": "يحتاج فصل ثابت/متغير حتى يصبح دقيقًا."}
    return {"state": "ثانوي", "display": "detail", "reason": "يعرض في التفاصيل إذا توفرت مدخلاته."}


def sector_profile_table(profile: dict | None) -> pd.DataFrame:
    cfg = get_sector_intelligence_profile(profile)
    rows = [
        ["عقلية التحليل", cfg["mindset"]],
        ["منطق التكلفة", cfg["cost_logic"]],
        ["المؤشرات العامة دائمًا", "، ".join(cfg["universal_core"][:8])],
        ["مؤشرات هذا القطاع", "، ".join(cfg["core_metrics"])],
        ["ملفات ترفع الدقة", "، ".join(cfg["special_files"])],
        ["مناطق الخطر", " | ".join(cfg["watchouts"])],
    ]
    return pd.DataFrame(rows, columns=["العنصر", "كيف يستخدمه الإيجنت"])
