import pandas as pd
from io import BytesIO
from core.utils import normalize_columns

def read_excel_file(uploaded_file):
    """
    Reads all sheets from an uploaded Excel file and returns:
    {
      "file_name": str,
      "sheets": {sheet_name: DataFrame},
      "primary_df": DataFrame
    }
    """
    raw = uploaded_file.read()
    excel = pd.ExcelFile(BytesIO(raw))
    sheets = {}
    for sheet in excel.sheet_names:
        try:
            df = pd.read_excel(BytesIO(raw), sheet_name=sheet)
            df = normalize_columns(df)
            df = df.dropna(how="all")
            df = df.loc[:, ~df.columns.astype(str).str.contains("^Unnamed", case=False, regex=True)]
            sheets[sheet] = df
        except Exception:
            continue

    primary_df = max(sheets.values(), key=lambda x: x.shape[0] * max(x.shape[1], 1)) if sheets else pd.DataFrame()
    return {
        "file_name": uploaded_file.name,
        "sheets": sheets,
        "primary_df": primary_df,
    }
