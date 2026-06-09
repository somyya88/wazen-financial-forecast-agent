# Wazen CFO Intelligence Agent V8.6

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
