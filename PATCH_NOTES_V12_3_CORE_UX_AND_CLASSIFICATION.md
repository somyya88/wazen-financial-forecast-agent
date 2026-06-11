# Wazen CFO Agent V12.3 — Core UX & Classification Fixes

## What changed

1. Fixed Streamlit navigation state errors by separating the sidebar radio from the internal navigation state.
2. Added a minimum model guard: the financial model is not built unless Trial Balance + Sales + Expenses are available.
3. Improved SaaS/software expense classification:
   - Operational/support/service-delivery salaries are treated as Cost of Revenue when the company sector is SaaS/software and the account name indicates operations/service delivery.
   - Sales salaries/commissions are treated as Selling & Marketing.
   - Administrative salaries are treated as Administrative Expenses.
   - Payment gateway fees such as Tamara/Tabby/payment portal are classified as Bank Charges.
4. Fixed OpenAI confidence scaling when the model returns 0–1 instead of 0–100.
5. Changed readiness language from generic “score” language to decision-scope language:
   - What can be analyzed now?
   - What is missing for cash/collections/forecast accuracy?
6. Reworked suggested file uploads into a side recommendation column instead of a separate basic section.
7. Translated key navigation/tabs to Arabic and reduced English labels in owner-facing UI.
8. Improved expense mapping UX labels and made “needs review only” optional instead of default.

## Still pending for Phase 2

- Full Revenue Quality Engine: gross sales, discounts, returns, net sales, leakage rate.
- Sector benchmark alerts for returns, discounts, margin, payroll, and operating cost.
- Interactive action center based on real customers/items/branches.
- Deeper AI narrative engine for CFO-grade owner messages.
