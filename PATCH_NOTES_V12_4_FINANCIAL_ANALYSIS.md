# V12.4 — Professional Financial Analysis Core

## Why this patch exists
The previous versions had a UX foundation but did not yet deliver the minimum expected CFO/financial analyst output: profitability ratios, liquidity ratios, leverage ratios, horizontal analysis, vertical analysis, and a clear reading of the underlying data.

## Added
- Comprehensive Financial Analysis Engine.
- Management P&L snapshot that reclassifies Cost of Revenue based on expense mapping, especially for SaaS/software companies.
- Profitability ratios:
  - Gross Margin
  - Operating Margin
  - Net Margin
  - OPEX Ratio
- Liquidity ratios:
  - Working Capital
  - Current Ratio
  - Quick Ratio
  - Cash Ratio
  - Cash Runway
- Leverage ratios:
  - Liabilities to Assets
  - Liabilities to Equity
- Efficiency ratios:
  - DSO
  - DPO
- Vertical analysis:
  - Income statement as % of revenue
  - Balance sheet as % of total assets
- Horizontal analysis:
  - Monthly revenue/expenses/profit change
  - Biggest balance sheet movements from beginning to ending balances
- Data reading table:
  - What was read
  - Value
  - Source
  - Why it matters
- Stronger CFO reading based on financial structure, not only dashboard cards.

## Improved
- Expense classification for SaaS/software: operational salaries, support, implementation, project/client costs are treated as Cost of Revenue when context supports it.
- OpenAI expense classification no longer overrides a strong rule-based classification into low-confidence Other Opex.
- Analysis Workspace now starts with professional data reading, ratios, and horizontal/vertical analysis before revenue quality and other tabs.

## Still pending
- External sector benchmark database with verified sources and city/country adjustment.
- Detailed revenue quality from item-level invoices: gross sales, discounts, returns, net sales.
- Product/customer/branch profitability when detailed files are available.
- Fully linked interactive scenario model based on the new management P&L.
