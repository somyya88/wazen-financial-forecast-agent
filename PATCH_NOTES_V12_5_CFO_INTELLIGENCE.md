# Wazen CFO Intelligence Agent — V12.5 CFO Intelligence Core

## الهدف
تحويل النسخة من عرض نسب وجداول إلى محرك تشخيص مالي يتبع Vision V2.0:
- الحسابات تتم بمحركات deterministic.
- القراءة التنفيذية والنسب تتحول إلى CFO Narrative مرن.
- AI لا يحسب الأرقام، بل يكتب قراءة تنفيذية فوق نتائج موثقة وقواعد تشخيص.

## أهم الإضافات

### 1. Financial Intelligence V2 Engine
تمت إضافة `financial_intelligence_v2.py` ويتضمن:
- Metric Pack كامل.
- Diagnostic Findings.
- Professional Ratio Narratives.
- Financial Health Score من 100.
- Executive Summary مبني على الأسئلة الأربعة.
- Optional AI Summary عند توفر `OPENAI_API_KEY`.

### 2. النسب المالية الموسعة
أضيفت نسب:
- Gross Margin.
- COGS % Revenue.
- Operating Margin.
- EBITDA Margin.
- Net Margin.
- Admin Expenses % Revenue.
- Selling & Marketing % Revenue.
- Current Ratio.
- Quick Ratio.
- Cash Ratio.
- Cash Runway.
- DSO / Receivables Turnover.
- DPO / Payables Turnover.
- DIO / Inventory Turnover.
- CCC.
- Asset Turnover.
- Fixed Asset Turnover.
- ROA / ROE.
- Debt Ratio.
- Debt to Equity.
- OCF / Net Income Proxy.
- Break-even Sales.
- Margin of Safety.

### 3. قراءة النسب أصبحت CFO Narrative
كل مؤشر أصبح يحتوي:
- النتيجة.
- الحكم.
- طريقة الحساب.
- سؤال الإدارة.
- قراءة CFO.
- الإجراء التنفيذي.
- مؤشر المتابعة.

### 4. التشخيص التنفيذي
الملخص التنفيذي أصبح يبدأ من:
- Gross Margin.
- Operating Margin.
- Admin % Revenue.
- S&M % Revenue.
- Cash Runway.
- DSO.
- CCC.
- Health Score.

ويجيب عن:
1. هل الشركة تربح فعلاً؟
2. هل السيولة كافية؟
3. هل العملاء يدفعون بالسرعة المطلوبة؟
4. هل الشركة آمنة للاستمرار والنمو؟

### 5. Diagnostic Rules قبل AI
تمت إضافة طبقة تشخيص قبل الذكاء الصناعي:
- Gross Margin جيد + Operating Margin ضعيف → مشكلة إدارة/تسويق/هيكل تشغيل.
- Gross Margin ضعيف + Operating Margin سلبي → مشكلة نموذج العمل أو التسعير/تكلفة الخدمة.
- Current Ratio جيد + Cash Ratio ضعيف → سيولة محاسبية وليست نقدية.
- DSO مرتفع → مبيعات لا تتحول إلى نقد بسرعة.
- Runway أقل من شهر → ضغط نقدي قريب.
- OCF/Net Income ضعيف → أرباح لا تتحول إلى نقد.

### 6. Performance Fix في تصنيف الحسابات
لم يعد التطبيق يعيد تشغيل AI/Rules عند كل تعديل في جدول التصنيف.
الآن:
- التصنيف يولد مرة واحدة حسب توقيع الحسابات.
- تعديلات المستخدم تبقى Draft.
- يعاد الحساب فقط عند حفظ التصنيف وبناء النموذج.

### 7. إلغاء منطق “مصاريف أخرى” كتصنيف معتمد
تم استبدال التصنيف العام بـ `Needs Review` / `بحاجة مراجعة`.
الهدف: لا تظهر مصاريف أخرى وكأنها بند مالي من ميزان المراجعة.

### 8. السيناريوهات
تمت إضافة متغيرات:
- تغير أيام التحصيل DSO.
- تغير أيام السداد DPO.
- الخصومات والمرتجعات يمكن أن تزيد أو تنخفض حول الصفر.

## ملاحظات
- AI Narrative اختياري ويحتاج `OPENAI_API_KEY`.
- AI لا يحسب ولا يغير النسب.
- كل قراءة AI مبنية على Metric Pack + Diagnostic Findings + Health Score.
