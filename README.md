# Wazen CFO Intelligence Agent V7

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
