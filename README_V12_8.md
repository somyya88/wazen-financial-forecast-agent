# Wazen CFO Intelligence Agent V12.8

نسخة V12.8 تضيف تجربة مستخدم مميزة حول قرار CFO، مع محرك قطاعي مرن وحارس مصادر النسب.

## التشغيل
```bash
pip install -r requirements.txt
streamlit run app.py
```

## ما تغير
- واجهة قرار جديدة: CFO Command Center.
- Sector-aware analysis: المحرك عام، لكن القراءة حسب القطاع ونموذج العمل.
- Metric Source Guard: لا صفر وهمي ولا نسبة بلا مصدر.
- Health Score مع Coverage وConfidence.
- Benchmark Intelligence حذر: المعايير الإرشادية لا تعتبر حقيقة دون مصدر.
