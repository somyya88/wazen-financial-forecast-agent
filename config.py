APP_NAME = "Wazen CFO Intelligence Agent V9.2"

WAZEN_BLUE = "#17479E"
WAZEN_ORANGE = "#FAA61A"
WAZEN_LIGHT_BG = "#F7F9FC"
WAZEN_TEXT = "#1F2937"

SUPPORTED_FILE_TYPES = [
    "trial_balance",
    "monthly_sales_wide",
    "expense_monthly",
    "item_sales",
    "bank_statement",
    "invoice_sales",
    "payroll",
    "unknown",
]

SOURCE_ROLES = [
    "official_revenue_source",
    "revenue_detail_source",
    "official_expense_source",
    "expense_detail_source",
    "validation_source",
    "cash_source",
    "supporting_source",
    "ignored",
]

REVENUE_DEFINITIONS = [
    "Net sales excluding VAT",
    "Sales including VAT",
    "Sales after discount",
    "Sales before discount",
    "Operating revenue only",
    "Operating + other revenue",
]

ANALYSIS_MODES = [
    "تحليل شامل",
    "تحليل ربحية",
    "تحليل مصاريف",
    "تحليل سيولة",
    "تحليل نقطة التعادل",
    "تحليل توقعات",
]
