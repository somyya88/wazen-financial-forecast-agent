# Patch Notes V13.4 — Source of Truth, Mapping Guard, Period Context

## الهدف

تطوير النسخة السابقة بناءً على نقد V13.3، مع التركيز على إصلاحات مالية جوهرية لا على تحسين الواجهة فقط.

## التغييرات

### 1. إصلاح تشغيل التطبيق
- أضيفت المتغيرات الناقصة إلى `config.py`:
  - `SOURCE_ROLES`
  - `REVENUE_DEFINITIONS`
  - `APP_VERSION`

### 2. إضافة طبقة CFO Core
ملف جديد:

```text
cfo_core_v13_4.py
```

يوفر:
- `infer_period_context`
- `build_account_mapping_audit`
- `build_source_of_truth_report`

### 3. إصلاح قائمة الدخل من ميزان المراجعة
تم تعديل `trial_balance_engine.py` حتى يفصل:
- Operating Expenses
- EBITDA
- Depreciation & Amortization
- EBIT
- Finance Costs
- Profit Before Tax/Zakat
- Tax/Zakat
- Net Profit

### 4. تحديث محرك قائمة الدخل
تم تعديل `financial_statement_engine.py` ليستخدم قيم ميزان المراجعة المفصّلة بدلاً من وضع `depreciation = 0` و `finance_costs = 0` دائماً.

### 5. إلغاء 150 يوم ثابت
- `financial_intelligence_v2.py`: fallback أصبح 365.25 يوم بدلاً من 150.
- `app.py`: يتم حقن `period_days` من الشهور المختارة.

### 6. حوكمة AI والخصوصية
- في `app.py` لم يعد `apply_smart_classification` يستخدم OpenAI افتراضياً.
- الاستخدام الخارجي يتم فقط عند تفعيل خيار AI من الواجهة.

### 7. تطوير التصدير
تم تعديل `excel_pack.py` لإضافة:
- Source of Truth
- Account Mapping Audit
- TB Normalized
- CFO Ratios Guarded

## اختبارات تمت

- `python -m py_compile *.py` نجح.
- اختبار synthetic Trial Balance نجح.
- تم التحقق أن EBITDA لا يساوي Net Profit عند وجود إهلاك وتمويل وزكاة.
- تم إنشاء Excel Pack تجريبي بنجاح.

## ملاحظة تشغيل

لم يتم تشغيل Streamlit داخل بيئة الاختبار الحالية لأن حزمة `streamlit` غير مثبتة في الحاوية، لكن الاعتمادية موجودة في `requirements.txt`.
