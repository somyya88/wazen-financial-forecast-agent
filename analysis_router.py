def tabs_for_mode(mode: str) -> list[str]:
    mapping = {
        "تحليل شامل": ["Dashboard", "P&L", "Ratios", "Expense Mapping", "Expenses", "Break-even", "Forecast", "Glossary", "Export"],
        "تحليل ربحية": ["Dashboard", "Revenue", "Margins", "Break-even"],
        "تحليل مصاريف": ["Expenses", "Top Expenses", "Cost Structure", "Export"],
        "تحليل سيولة": ["Cash", "Working Capital", "Runway", "Forecast"],
        "تحليل نقطة التعادل": ["Break-even", "Scenarios"],
        "تحليل توقعات": ["Forecast", "Scenario Assumptions"],
    }
    return mapping.get(mode, ["Dashboard"])
