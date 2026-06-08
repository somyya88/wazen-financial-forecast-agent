from utils import find_column, detect_month_columns

def default_mapping(df):
    return {
        "account_code": find_column(df, ["رقم الحساب", "account code", "code", "account no"]),
        "account_name": find_column(df, ["اسم الحساب", "account name", "account", "الحساب", "البيان"]),
        "date": find_column(df, ["date", "التاريخ", "تاريخ"]),
        "amount": find_column(df, ["amount", "المبلغ", "قيمة", "value"]),
        "debit": find_column(df, ["debit", "مدين"]),
        "credit": find_column(df, ["credit", "دائن"]),
        "customer": find_column(df, ["customer", "client", "العميل", "اسم العميل"]),
        "item": find_column(df, ["item", "product", "الصنف", "اسم الصنف"]),
        "vat": find_column(df, ["vat", "ضريبة", "tax"]),
        "discount": find_column(df, ["discount", "خصم"]),
        "month_columns": detect_month_columns(list(df.columns)),
    }
