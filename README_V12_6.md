# Wazen CFO Intelligence Agent V12.6

This version implements file-aware financial analysis. The agent builds the strongest possible analysis from whatever files are available, instead of blocking analysis until every file exists.

## Core principle

- Trial Balance alone is enough for Level A Financial Analysis.
- Sales/expenses files add monthly distribution, trends, and validation.
- Cash, AR aging, AP aging add CFO-level liquidity and working capital analysis.
- Prior-year files are used for comparison, not as the active current period.

## Main files changed

- `app.py`
- `trial_balance_engine.py`
- `financial_statement_engine.py`
- `data_readiness_v12.py`
