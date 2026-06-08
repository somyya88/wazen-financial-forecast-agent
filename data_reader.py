import pandas as pd
from io import BytesIO
import zipfile
import re
from utils import normalize_columns

def _repair_invalid_xlsx_styles(raw: bytes) -> bytes:
    """
    Some exported XLSX files contain invalid style colors, e.g. rgb="FF000"
    instead of a valid aRGB value like rgb="FFFF0000".
    openpyxl refuses to read these files. This function repairs styles.xml only.
    """
    source = BytesIO(raw)
    target = BytesIO()

    with zipfile.ZipFile(source, "r") as zin, zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "xl/styles.xml":
                text = data.decode("utf-8", errors="replace")

                def fix_rgb(match):
                    val = match.group(1)
                    if re.fullmatch(r"[0-9A-Fa-f]{8}", val):
                        return match.group(0)
                    if re.fullmatch(r"[0-9A-Fa-f]{6}", val):
                        new_val = "FF" + val.upper()
                    elif val.upper() == "FF000":
                        new_val = "FFFF0000"
                    else:
                        new_val = "FF000000"
                    return f'rgb="{new_val}"'

                text = re.sub(r'rgb="([^"]*)"', fix_rgb, text)
                data = text.encode("utf-8")

            zout.writestr(item, data)

    return target.getvalue()

def _read_sheets(raw: bytes, engine: str | None):
    bio = BytesIO(raw)
    excel = pd.ExcelFile(bio, engine=engine) if engine else pd.ExcelFile(bio)
    sheets = {}

    for sheet in excel.sheet_names:
        try:
            # First try normal header mode.
            df_normal = pd.read_excel(BytesIO(raw), sheet_name=sheet, engine=excel.engine)
            df_normal = normalize_columns(df_normal)
            df_normal = df_normal.dropna(how="all")
            df_normal = df_normal.loc[:, ~df_normal.columns.astype(str).str.contains("^Unnamed", case=False, regex=True)]

            # Also keep raw no-header mode for non-standard reports.
            df_raw = pd.read_excel(BytesIO(raw), sheet_name=sheet, engine=excel.engine, header=None)
            df_raw = df_raw.dropna(how="all")

            # If normal mode loses many columns or headers are mostly Unnamed, use raw layout.
            normal_cols_before_clean = pd.read_excel(BytesIO(raw), sheet_name=sheet, engine=excel.engine, nrows=1).columns.astype(str)
            unnamed_ratio = sum(c.startswith("Unnamed") for c in normal_cols_before_clean) / max(len(normal_cols_before_clean), 1)

            if unnamed_ratio > 0.45 or df_normal.shape[1] < max(3, df_raw.shape[1] * 0.6):
                sheets[sheet] = df_raw
            else:
                sheets[sheet] = df_normal

        except Exception:
            continue

    return sheets

def read_excel_file(uploaded_file):
    """
    Defensive Excel reader for real client files:
    - reads .xlsx/.xls
    - repairs invalid XLSX style XML when possible
    - keeps non-standard no-header reports readable
    - returns a friendly error instead of crashing Streamlit
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
    engine = "openpyxl" if suffix == "xlsx" else "xlrd" if suffix == "xls" else None

    repaired = False

    try:
        try:
            sheets = _read_sheets(raw, engine)
        except Exception as first_error:
            if suffix == "xlsx":
                raw = _repair_invalid_xlsx_styles(raw)
                repaired = True
                sheets = _read_sheets(raw, engine)
            else:
                raise first_error

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
            "repaired": repaired,
        }

    except Exception as e:
        return {
            "file_name": file_name,
            "sheets": {},
            "primary_df": pd.DataFrame(),
            "error": f"تعذر قراءة الملف كملف Excel صالح. السبب التقني: {type(e).__name__}: {str(e)}",
        }
