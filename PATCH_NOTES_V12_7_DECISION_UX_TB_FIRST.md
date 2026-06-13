# V12.7 — Decision-first UX + TB Expense/Liquidity/Turnover Fixes

## Core fixes
- Trial Balance is now recognized as Trial Balance even when it contains many expense/payroll keywords.
- Trial Balance alone now builds P&L, Balance Sheet, expense structure, liquidity ratios, solvency ratios and turnover ratios where balances exist.
- Monthly expense files are no longer required for expense analysis; they add monthly distribution only.
- Expense classification can be generated from TB expense accounts directly.
- Building the model is no longer blocked by manual expense mapping review; default classification is used, and manual edits can be applied later.

## UX fixes
- Removed duplicate CFO narrative from the analysis workspace. Executive diagnosis stays on the Executive page; analysis workspace shows source trust and drill-down.
- Replaced long ratio table-first view with decision cards, top findings, and expandable ratio groups.
- Reworked vertical/horizontal analysis into insight-first cards and collapsible detailed tables.
- Liquidity page now shows Current Ratio, Quick Ratio, Cash Ratio, and Working Capital from TB even without bank/cash report.
- Collection/turnover page now shows DSO, Receivables Turnover, DPO, CCC from TB when AR/AP balances exist; AR Aging adds customer-level actions.
- Expenses page now shows cost structure from TB if no monthly expense file exists.

## Principle
Analyze with available data. Do not stop because an enhancement file is missing. Use extra files only to increase precision, detail, and forecasting.
