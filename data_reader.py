import pandas as pd
from io import BytesIO
from utils import normalize_columns

def read_excel_file(uploaded_file):
    """
    Reads all sheets from an uploaded Excel file and returns:
    {
      "file_name": str,
      "sheets": {sheet_name: DataFrame},
      "primary_df": DataFrame,
      "error": str | None
    }

    This reader is intentionally defensive because real client files may be:
    - .xlsx
    - .xls
    - protected/corrupted
    - renamed with a wrong extension
    - empty
    """
    file_name = getattr(uploaded_file, "name", "uploaded_file")
    raw = uploaded_file.read()

    if not raw:
        return {
            "file_name": file_name,
            "sheets": {},
            "primary_df": pd.DataFrame(),
            "error": "الملف فارغ أو لم يتم رفعه بشكل صحيح.",
        }

    suffix = file_name.lower().split(".")[-1] if "." in file_name else ""

    try:
        bio = BytesIO(raw)

        # Pick engine explicitly to avoid pandas ambiguity on Streamlit Cloud.
        if suffix == "xlsx":
            excel = pd.ExcelFile(bio, engine="openpyxl")
        elif suffix == "xls":
            excel = pd.ExcelFile(bio, engine="xlrd")
        else:
            # Fallback: let pandas try, but return a clear error if it fails.
            excel = pd.ExcelFile(bio)

        sheets = {}
        for sheet in excel.sheet_names:
            try:
                df = pd.read_excel(BytesIO(raw), sheet_name=sheet, engine=excel.engine)
                df = normalize_columns(df)
                df = df.dropna(how="all")
                df = df.loc[:, ~df.columns.astype(str).str.contains("^Unnamed", case=False, regex=True)]
                sheets[sheet] = df
            except Exception:
                continue

        if not sheets:
            return {
                "file_name": file_name,
                "sheets": {},
                "primary_df": pd.DataFrame(),
                "error": "تم فتح الملف لكن لم يتم العثور على شيت قابل للقراءة.",
            }

        primary_df = max(sheets.values(), key=lambda x: x.shape[0] * max(x.shape[1], 1))
        return {
            "file_name": file_name,
            "sheets": sheets,
            "primary_df": primary_df,
            "error": None,
        }

    except Exception as e:
        return {
            "file_name": file_name,
            "sheets": {},
            "primary_df": pd.DataFrame(),
            "error": f"تعذر قراءة الملف كملف Excel صالح. السبب التقني: {type(e).__name__}: {str(e)}",
        }
