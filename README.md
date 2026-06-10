# Wazen CFO Intelligence Agent V9.8

Streamlit-based CFO Intelligence Agent for reading multiple financial Excel files, assigning source roles, preventing duplicated revenue, analyzing expenses, validating data quality, and preparing the foundation for a professional CFO dashboard and Excel Pack.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Main workflow

1. Company setup
2. Upload multiple Excel files
3. Detect file types
4. Confirm source roles
5. Select revenue definition
6. Validate data quality
7. Build preliminary financial model
8. Display dashboard
9. Export CFO Pack

## Important V7 rule

The agent never sums multiple revenue files automatically.  
Only one file can be selected as the official revenue source.


## V8 additions

- Analysis period confirmation.
- P&L page.
- Ratio Analysis page.
- Break-even Analysis page.
- Forecast scenarios page.
- Financial Glossary.
- Enhanced Excel CFO Pack.


## V8.1 additions

- Expense Mapping step before final modeling.
- User-editable expense category.
- User-editable cost behavior: Fixed / Variable / Semi-variable.
- P&L and Break-even now depend on approved mapping.


## V8.2 additions

- Trial Balance net purchases extraction.
- Adds 'صافي المشتريات' from Trial Balance into COGS when it is not already in the expense report.
- Break-even includes TB purchases adjustment as variable/direct cost.
- Data Quality shows a note when purchases are detected in Trial Balance.


## V8.3 additions

- Stable Expense Mapping editor using a form.
- Mapping changes are not used until the user clicks "حفظ Expense Mapping".
- Prevents Streamlit reruns from reverting user edits.
- Adds a reset button to regenerate suggested mapping only when explicitly requested.


## V8.4 additions

- Removes forced rerun from Expense Mapping save/reset actions.
- Prevents Streamlit frontend "Bad message format / SessionInfo" errors while editing data_editor.
- Clarifies that "إعادة توليد التصنيف المقترح" resets user edits intentionally.


## V8.5 additions

- Fixes Streamlit uploader state by using a dynamic uploader key.
- Reset button now also resets the upload widget state.
- Shows selected file names before processing.
- Uses a newer Streamlit frontend range to reduce file uploader/data editor UI issues.


## V8.6 additions

- Trial Balance is now the primary source for the official income statement.
- Monthly sales and monthly expense files are used for analysis and monthly trends only.
- P&L reads net sales, other revenues, opening inventory, net purchases, ending inventory, COGS, operating expenses, and net profit from Trial Balance.
- COGS formula: Opening Inventory + Net Purchases - Ending Inventory.
- If inventory accounts are missing, inventory is assumed to be zero and net purchases are used as COGS proxy.


## V8.6.1 hotfix

- Fixes app.py to call:
  build_pnl(revenue_model, expense_model, tb_model)
- This enables the P&L page and dashboard to use the Trial Balance as the primary income statement source.


## V8.7 additions

- Redesigned KPI cards with Wazen visual identity.
- Added professional HTML financial tables.
- Redesigned P&L as a statement-style financial table with highlighted totals.
- Rebuilt monthly profitability table:
  month, revenue, net purchases, operating profit margin, expenses, net profit, net profit margin.
- Fixed revenue trend chart with robust numeric conversion, month sorting, and Wazen colors.
- Standardized number and percentage formatting across analytical tables.


## V8.8 additions

- Aligns all table headers to the right for RTL consistency.
- Improves income statement visual hierarchy with stronger statement-style subtotal sections.
- Adds an Operating Expenses drill-down expander directly under P&L.
- Makes Operating Expenses row visually clickable with an anchor to the drill-down section.
- Adds hover tooltips on monthly profitability rows showing operating profit amount.


## V8.8.1 hotfix

- Fixed theme.py CSS block causing NameError at app startup.
- Rewrote theme.py using a safe CSS string instead of injected raw CSS.


## V8.9 additions

- Forces Streamlit headings and chart titles to align right for Arabic RTL UI.
- Adds CFO insight panels for:
  - Ratio Analysis
  - Break-even Analysis
  - Forecast & Scenarios
- Adds scenario summary table before monthly forecast details.
- Improves value-add by showing:
  - risk interpretation
  - recommended next decision
  - key analytical bullets


## V9.0 additions

- Replaced non-professional insight titles with executive financial labels:
  - التقييم التنفيذي للنسب المالية
  - تحليل التعادل وهامش الأمان
  - تحليل السيناريوهات والتوقعات
- Converted gendered Arabic wording to neutral professional language.
- Fixed break-even key mismatch and rebuilt break-even logic using official P&L values:
  - Trial Balance revenue and COGS
  - Official operating expenses
  - Expense Mapping only for fixed / variable split
- Added more actionable risk and decision language.
- Improved percentage formatting in Arabic text.

## V9.1 additions

- Fixes Break-even percentage display.
- Adds Data Quality & Source Reconciliation.
- Adds Expense Efficiency analysis and Other Opex warning.
- Adds Forecast assumptions table and worst-month KPI cards.
- Improves page naming and executive value-add.

## V9.2 additions

- Rebuilt Expense Mapping with filters:
  - account name search
  - current category
  - approved category
  - cost behavior
  - Other Opex only
  - large items only
  - minimum amount
- Added mapping KPIs and filtered editing workflow.

## V9.3 additions

- Adds smart Arabic/English account classification engine.
- Reduces default Other Opex classification by reading account names.
- Classifies purchases and direct operating costs as Cost of Revenue / Purchases.
- Splits expenses into:
  - Cost of Revenue
  - Administrative Expenses
  - Selling & Marketing
  - Finance Costs
  - Other Opex
- Adds an administrative income statement view separating:
  - Cost of Revenue / COGS
  - Gross Operating Profit
  - G&A
  - Selling & Marketing
  - Operating Profit
  - Net Profit

## V9.4 additions

- Uses the existing OpenAI integration for Expense Mapping classification.
- Sends only account name, amount, and current category for classification.
- Falls back to local rule-based classification when OpenAI is unavailable.
- Adds classification confidence, source, and reason columns to mapping.
- Keeps management P&L category structure from V9.3.

## V9.5 additions

- Preserves audit-friendly expense mapping order.
- Adds display groups:
  - Cost of Revenue / Direct Operations
  - General & Administrative
  - Selling & Marketing
  - Finance & Bank
  - Other Expenses
- Adds sorting options:
  - by management income statement order
  - by original trial balance order
  - by amount
- Adds display group column to Expense Mapping for easier review.

## V9.6 additions

- Replaces duplicated P&L views with one executive income statement.
- Removes EBITDA KPI from the dashboard and replaces it with Gross Profit.
- Dashboard KPIs now focus on:
  - Operating Revenue
  - Gross Profit
  - Operating Expenses
  - Net Profit and Net Margin
  - Break-even and suggested action
- Adds executive monthly profitability table:
  revenue, cost of revenue, gross profit, gross margin, opex, net profit, net margin.
- Improves Arabic-first labels and executive P&L styling.

## V9.7 additions

- Rebuilds ratio analysis into an executive financial performance scorecard.
- Adds rating, threshold, risk interpretation, and decision impact for each ratio.
- Replaces ambiguous Health Score with Financial Performance Index.
- Adds break-even confidence score and sensitivity table.
- Adds forecast decision cards, safe monthly revenue, and loss warning.
- Reduces superficial commentary and links recommendations to numeric thresholds.

## V9.8 additions
- Enforces Arabic-first RTL layout across cards, tables, alerts, captions and insight panels.
- Rebuilds financial ratios into a business explanation: how the score is calculated, why each factor matters, and what internal action is required.
- Replaces expansion-oriented recommendations with internal-control recommendations.
- Adds business explanations for break-even gap and confidence score.
- Adds explanations and actions to sensitivity tests.
- Improves expense efficiency with Arabic categories, ratio to revenue, and diagnosis.
