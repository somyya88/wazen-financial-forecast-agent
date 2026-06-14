# Wazen CFO Agent V13.2 — Refined Three Analysis Pages

## Scope
This update intentionally modifies only three pages before moving to the remaining analysis pages:

1. Sources & Confidence
2. Decision Indicators
3. Vertical & Horizontal Analysis

## Key corrections

### 1. Periodic inventory COGS
For inventory/trading-style trial balances, COGS is calculated as:

Opening Inventory + Net Purchases - Ending Inventory

Branch/operating expenses are no longer mixed into gross margin when inventory COGS is available.

### 2. Better source-confidence logic
The app separates:

- Data source confidence
- Classification confidence
- Diagnostic confidence

When periodic inventory COGS is available from the TB, gross margin and COGS ratio confidence are not automatically downgraded just because inventory exists.

### 3. More professional UX tables
Raw wide Streamlit tables were replaced on the reviewed pages with:

- Card-like summary tiles
- Styled audit tables
- Badges for confidence/status
- Expanders for detailed tables
- A formula card for COGS basis

### 4. Decision Indicators page
The page now prioritizes decision cards before tables. Detailed ratios remain available in expandable sections.

### 5. Vertical & Horizontal Analysis page
The page now starts with “from every 100 riyals of sales” and clarifies whether horizontal analysis is truly available.

## Not changed in this patch
Remaining pages such as profitability, revenue quality, liquidity, collections, expenses, sector benchmarks, scenarios, and final executive diagnosis were not redesigned yet.
