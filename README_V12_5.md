# Wazen CFO Intelligence Agent V12.5

هذه النسخة تضيف طبقة CFO Intelligence فوق محركات الحسابات المالية.

## التشغيل
```bash
pip install -r requirements.txt
streamlit run app.py
```

## مبدأ التصميم
الحسابات والنسب تتم عبر محركات ثابتة، والذكاء الصناعي يستخدم فقط لصياغة الملخص التنفيذي والقراءات الاحترافية عند توفر مفتاح OpenAI.

## لا تستخدم AI للحساب
AI لا يحسب Gross Margin أو DSO أو Current Ratio. هذه النسب تأتي من الكود فقط.

## أهم الملفات الجديدة
- `financial_intelligence_v2.py`
- `PATCH_NOTES_V12_5_CFO_INTELLIGENCE.md`
