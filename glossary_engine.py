import pandas as pd

def build_glossary():
    return pd.DataFrame([
        ["الإيرادات", "Revenue", "الدخل الناتج عن النشاط الرئيسي", "Sum of official revenue source", "أساس قياس النمو."],
        ["تكلفة الإيراد", "COGS", "التكاليف المباشرة المرتبطة بتوليد الإيراد", "Direct costs linked to revenue", "تؤثر على مجمل الربح."],
        ["مجمل الربح", "Gross Profit", "الإيرادات بعد خصم التكلفة المباشرة", "Revenue - COGS", "يقيس كفاءة تقديم الخدمة."],
        ["هامش مجمل الربح", "Gross Margin", "نسبة مجمل الربح إلى الإيرادات", "Gross Profit / Revenue", "يوضح قوة التسعير والتكلفة."],
        ["EBITDA", "EBITDA", "الربح قبل الفوائد والضرائب والإهلاك", "Gross Profit - Opex", "يقيس ربحية التشغيل قبل البنود غير النقدية والتمويل."],
        ["هامش EBITDA", "EBITDA Margin", "نسبة EBITDA إلى الإيرادات", "EBITDA / Revenue", "مهم لقياس كفاءة التشغيل."],
        ["نقطة التعادل", "Break-even Revenue", "الإيراد المطلوب لتغطية التكاليف", "Fixed Costs / Contribution Margin", "يحدد الحد الأدنى الآمن للمبيعات."],
        ["هامش الأمان", "Margin of Safety", "المسافة بين الإيراد الحالي ونقطة التعادل", "(Revenue - Break-even) / Revenue", "يقيس مدى تحمل انخفاض الإيرادات."],
        ["فترة التحليل", "Analysis Period", "الشهور المعتمدة في الحساب", "Selected months", "تمنع دخول شهر غير مكتمل في التحليل."],
    ], columns=["العربي", "English", "المعنى المبسط", "المعادلة", "لماذا يهم؟"])
