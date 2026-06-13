from __future__ import annotations

import pandas as pd
from sector_benchmarks import get_sector_config


def build_benchmark_intelligence(profile: dict | None, guarded_ratios: pd.DataFrame | None = None) -> dict:
    profile = profile or {}
    sector = profile.get("sector", "خدمي")
    country = profile.get("country", "غير محدد")
    city = profile.get("city", "")
    cfg = get_sector_config(sector)
    rows = []
    for key, b in (cfg.get("benchmarks") or {}).items():
        rows.append({
            "المؤشر": b.get("label", key),
            "المفتاح": key,
            "النطاق/الحد الإرشادي": f"آمن: {b.get('safe', 0):.1%} | مراقبة: {b.get('watch', 0):.1%}",
            "نوع المعيار": "قاعدة قطاعية إرشادية داخلية",
            "درجة الثقة": "متوسطة/منخفضة خارجيًا",
            "محدودية الاستخدام": "لا يُعرض كمعيار عالمي موثق؛ يستخدم كبوصلة أولية حتى ربط مصادر خارجية أو بيانات داخلية مجمعة.",
        })
    df = pd.DataFrame(rows)

    internal = []
    if guarded_ratios is not None and not guarded_ratios.empty:
        for _, r in guarded_ratios.head(6).iterrows():
            internal.append({
                "المقارنة": str(r.get("المؤشر", "")),
                "القيمة الحالية": str(r.get("النتيجة", "")),
                "أفضل معيار حالي": "مقارنة داخلية بالفترة السابقة عند توفر ميزان/مبيعات سنة سابقة",
                "سبب الأولوية": "المقارنة الداخلية أكثر عدالة من معيار خارجي عام لأنها تعكس نفس الشركة ونفس السوق.",
            })
    internal_df = pd.DataFrame(internal)

    narrative = (
        f"سيتم استخدام قطاع {sector} في {country}{' - ' + city if city else ''} لتوجيه القراءة، لكن المعايير الخارجية لا تُعامل كحقيقة قطعية. "
        "الأولوية للمقارنة الداخلية بالشركة نفسها، ثم المقارنة مع السنة السابقة، ثم القواعد القطاعية الإرشادية، وبعدها مصادر خارجية موثقة عند توفرها. "
        "أي رقم Benchmarks لا يحمل مصدرًا وفترة وثقة لا يدخل في الحكم النهائي، بل يظهر كإشارة مساعدة فقط."
    )
    return {"narrative": narrative, "advisory_table": df, "internal_priority": internal_df}
