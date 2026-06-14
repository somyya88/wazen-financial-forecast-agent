# Wazen CFO Intelligence Agent V13.6

نسخة V13.6 تركز على توضيح أساس قرارات البطاقات، دمج معيار الحكم داخل القرار، وتحسين التحليل الرأسي/الأفقي مع دعم مقارنة ميزان مراجعة حالي وسابق.

## تشغيل التطبيق

```bash
pip install -r requirements.txt
streamlit run app.py
```

## أهم جديد V13.6
- بطاقات القرار تعرض معيار الحكم ومصدره.
- حذف التكرار بين إعداد النشاط وجاهزية التحليل.
- مقارنة أفقية سنة بسنة عند رفع ميزاني مراجعة لفترتين.
- تكلفة الإيراد تستخدم كمنهجية تحقق لا كمعادلة بدائية في الواجهة.
- الجداول التفصيلية تظهر خلف بطاقات تحليلية وExpander احترافي.

# Wazen CFO Intelligence Agent V13.5

نسخة V13.5 تركّز على تحويل الإيجنت من واجهة تحليل جميلة إلى نموذج مالي أكثر قابلية للتدقيق والاعتماد.

## طريقة التشغيل

```bash
pip install -r requirements.txt
streamlit run app.py
```

## أهم ما أضيف في V13.5

1. **إصلاح تشغيلي في `config.py`**
   - إضافة `SOURCE_ROLES` و `REVENUE_DEFINITIONS` حتى لا يفشل التطبيق عند الاستيراد.

2. **مصدر حقيقة مالي واحد**
   - إضافة `cfo_core_v13_4.py` لتجميع سياق الفترة، خريطة الحسابات، وملاحظات التدقيق.
   - كل تحليل يجب أن يكون قابلاً للتتبع إلى مصدره: ميزان مراجعة، ملف مبيعات، ملف مصاريف، أو افتراض.

3. **فصل EBITDA / EBIT / Finance / Tax-Zakat**
   - لم يعد صافي الربح يساوي EBITDA عندما توجد إهلاكات أو تكاليف تمويل أو زكاة/ضريبة.
   - قائمة الدخل من ميزان المراجعة تفصل:
     - EBITDA
     - Depreciation & Amortization
     - EBIT
     - Finance Costs
     - Profit Before Tax/Zakat
     - Tax/Zakat
     - Net Profit

4. **إلغاء افتراض 150 يوم ثابت**
   - يتم استنتاج أيام الفترة من الشهور المختارة.
   - عند غياب الشهور، يظهر الافتراض صراحة في تقارير التدقيق بدلاً من إخفائه.

5. **Account Mapping Audit**
   - توليد خريطة تصنيف حسابات مبدئية من ميزان المراجعة.
   - كل حساب يحصل على تصنيف CFO ودرجة ثقة: high/medium/low/needs_review.

6. **خصوصية البيانات**
   - التصنيف الذكي لا يرسل أسماء الحسابات إلى OpenAI إلا عند تفعيل خيار AI من الواجهة.
   - الوضع الافتراضي: قواعد محلية deterministic rules فقط.

7. **Excel Audit Pack**
   - إضافة صفحات تدقيق إلى ملف التصدير:
     - Source of Truth
     - Account Mapping Audit
     - TB Normalized
     - CFO Ratios Guarded

## ملاحظات مهمة

هذه النسخة ما زالت Prototype متقدم وليست منتجاً نهائياً لعميل حقيقي قبل:

- اعتماد خريطة الحسابات يدوياً لأول عميل تجريبي.
- اختبارها على 3 إلى 5 ملفات ميزان مراجعة فعلية من قطاعات مختلفة.
- مطابقة أرقام القوائم مع تقرير محاسبي معتمد.
- تطوير السيناريوهات لتكون driver-based أكثر من average-based.

## الملفات الأساسية

- `app.py` — واجهة Streamlit.
- `trial_balance_engine.py` — قراءة ميزان المراجعة وبناء قائمة دخل أولية.
- `financial_statement_engine.py` — مصدر قائمة الدخل المعتمدة.
- `cfo_core_v13_4.py` — طبقة الفترة، مصدر الحقيقة، وخريطة الحسابات.
- `excel_pack.py` — تصدير CFO Pack مع صفحات تدقيق.


## V13.5 - Decision Ratio Benchmark UX
- Removed duplicated ratio details from the Decision Indicators page.
- Integrated advisory sector benchmarks beside each relevant ratio.
- Reworked Revenue Quality to clarify that leakage is one sub-indicator, not the full definition of revenue quality.
- Added explanation tables for liquidity ratios and collection/turnover ratios.
- Marked DSO/DPO/CCC as estimated when calculated from trial balance only.
- Added expense value as percentage of revenue and advisory benchmark status.
- Added trend indicators to horizontal analysis tables when comparative columns exist.
