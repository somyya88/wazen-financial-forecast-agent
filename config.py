"""Global configuration for Wazen CFO Intelligence Agent.

V13.5 hardens the app so UI constants live in one place instead of being
implicitly expected by app.py. Keep this file small and deterministic.
"""

APP_NAME = "Wazen CFO Intelligence Agent V13.6"
APP_VERSION = "13.5"
DEFAULT_CURRENCY = "SAR"

# Wazen brand/theme constants used by theme.py and UI components.
WAZEN_BLUE = "#17479E"
WAZEN_ORANGE = "#FAA61A"
WAZEN_LIGHT_BG = "#F7F9FC"
WAZEN_TEXT = "#1F2D3D"
WAZEN_BORDER = "#E6EAF0"
WAZEN_SOFT_BLUE = "#EAF2FF"
WAZEN_GREEN = "#EAF8F0"
WAZEN_RED = "#FDECEC"


SOURCE_ROLES = [
    "validation_source",          # Trial balance / source of truth for statements
    "official_revenue_source",    # Sales / revenue report
    "official_expense_source",    # Expense report
    "cash_source",                # Bank statement / cash movement report
    "ar_aging_source",            # Customer aging / receivables
    "ap_aging_source",            # Supplier aging / payables
    "customer_report_source",
    "supplier_report_source",
    "revenue_detail_source",
    "expense_detail_source",
    "supporting_source",
]

REVENUE_DEFINITIONS = [
    "Net sales excluding VAT / صافي المبيعات بدون ضريبة",
    "Sales including VAT / المبيعات شامل ضريبة القيمة المضافة",
    "Gross sales before discount / إجمالي المبيعات قبل الخصم",
    "Net sales after discount / صافي المبيعات بعد الخصم",
]

# Conservative advisory defaults. These are not external benchmarks; they are
# internal guardrails used only when a sector-specific source is unavailable.
BENCHMARK_BASIS_NOTE = (
    "Internal advisory guardrail - replace with country/sector benchmarks "
    "when reliable benchmark data is attached."
)
