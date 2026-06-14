# V13.1 — Analysis Pages UX + Metric Source Guard

## Scope
This release updates only the three pages currently under review:

1. مصادر الأرقام والثقة
2. مؤشرات القرار
3. التحليل الرأسي والأفقي

The executive diagnosis is intentionally not repeated inside the analysis workspace. It should be rebuilt later after all analysis pages are financially validated.

## Page 1 — Sources & Confidence
- Converted the page into an audit layer only.
- Removed repeated executive diagnosis/health-score style content from this page.
- Added three separate confidence layers:
  - ثقة مصدر البيانات
  - ثقة التصنيف
  - ثقة التشخيص
- Added clearer tables for:
  - core numbers and source
  - metric source guard gaps
  - management P&L classification audit
  - analytical balance sheet source

## Page 2 — Decision Indicators
- Rebuilt as a decision board, not a long ratios table.
- Added top cards:
  - Financial Health
  - أخطر قرار الآن
  - ثقة التشخيص
- Added interactive decision cards for:
  - profitability model
  - operating profitability
  - liquidity pressure
  - leverage/debt pressure
  - data gaps
- Detailed ratios are now hidden under expanders.
- Long CFO readings are no longer forced into a wide raw table.

## Page 3 — Vertical & Horizontal Analysis
- Added “من كل 100 ريال مبيعات” view before the detailed table.
- Added warning when inventory/purchase-based sectors need COGS verification.
- Horizontal analysis is no longer presented as complete when no comparative period exists.
- Balance-account movement is renamed as movement analysis, not full horizontal analysis.

## Key Rules Added
- Do not call an analysis horizontal unless there is a comparison period or monthly data.
- Do not treat purchases as final COGS when inventory may exist without inventory beginning/ending validation.
- Do not show one generic confidence score; split source, classification, and diagnostic confidence.
- Decision pages should start from actions and evidence, not raw ratio tables.
