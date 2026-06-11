# Wazen CFO Agent V12.1 UX Fixes

## Scope
This patch responds to user testing notes on V12 foundation.

## Implemented
- Added more sectors: restaurants/cafes, contracting/projects, healthcare, rental, services, trading, manufacturing, SaaS.
- Added branch analysis context:
  - إجمالي فقط
  - إجمالي + حسب الفروع إذا وجدت في البيانات
  - كل فرع كحالة منفصلة لاحقًا
- Added required/optional/enhancement visual file requirement cards.
- Removed programmer-facing JSON after saving business context.
- Added premium UI polish CSS: hero panels, cards, badges, smoother hover states, improved sidebar styling.
- Fixed Streamlit `multiselect` crash caused by default values not existing in options.
- Added direct file addition from Data Readiness page without returning to upload center.
- Added detection for customer and supplier reports:
  - `customer_report` → `customer_report_source`
  - `supplier_report` → `supplier_report_source`
- Added Data Readiness branch signal detection.
- Improved Executive Diagnosis layout with a “diagnosis before numbers” panel.

## Still Deferred
- Full branch-level financial model by branch.
- Detailed customer/supplier report analytics beyond role detection.
- Revenue Quality parser for gross sales / discounts / returns / net sales.
- Full sector benchmark database from external sources.
- PDF Executive Summary export.
