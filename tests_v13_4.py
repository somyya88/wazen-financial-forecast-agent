"""Small deterministic checks for V13.4 core financial logic.
Run with: python tests_v13_4.py
"""
import pandas as pd
from trial_balance_engine import parse_trial_balance
from financial_statement_engine import build_pnl
from expense_engine import build_expense_model_from_trial_balance
from cfo_core_v13_4 import build_source_of_truth_report
from excel_pack import build_excel_pack


def test_tb_income_statement_separates_ebitda_and_net_profit():
    raw = pd.DataFrame({
        "رقم الحساب": ["101", "10201", "201", "301", "401", "501", "502", "503", "504"],
        "اسم الحساب": ["بنك", "عملاء", "موردين", "مشتريات", "مبيعات", "رواتب", "إهلاك معدات", "فوائد تمويل", "زكاة"],
        "مدين": [0, 0, 0, 30000, 0, 20000, 5000, 2000, 1000],
        "دائن": [0, 0, 0, 0, 100000, 0, 0, 0, 0],
        "الرصيد الحالي(مدين)": [50000, 20000, 0, 0, 0, 0, 0, 0, 0],
        "الرصيد الحالي(دائن)": [0, 0, 10000, 0, 0, 0, 0, 0, 0],
    })
    tb = parse_trial_balance({"primary_df": raw, "file_name": "sample.xlsx"})
    exp = build_expense_model_from_trial_balance(tb, 100000)
    pnl = build_pnl(None, exp, tb)
    assert pnl["revenue"] == 100000
    assert pnl["cogs"] == 30000
    assert pnl["opex"] == 20000
    assert pnl["ebitda"] == 50000
    assert pnl["depreciation"] == 5000
    assert pnl["finance_costs"] == 2000
    assert pnl["tax_zakat"] == 1000
    assert pnl["net_profit"] == 42000


def test_export_pack_includes_audit_layers():
    raw = pd.DataFrame({
        "رقم الحساب": ["401", "501"],
        "اسم الحساب": ["مبيعات", "رواتب"],
        "مدين": [0, 1000],
        "دائن": [5000, 0],
    })
    tb = parse_trial_balance({"primary_df": raw, "file_name": "sample.xlsx"})
    exp = build_expense_model_from_trial_balance(tb, 5000)
    pnl = build_pnl(None, exp, tb)
    report = build_source_of_truth_report(tb, None, exp, pnl, ["Jan", "Feb"], {})
    out = build_excel_pack([], None, exp, {}, [], pnl_model=pnl, tb_model=tb, source_truth_report=report)
    assert len(out) > 10000


if __name__ == "__main__":
    test_tb_income_statement_separates_ebitda_and_net_profit()
    test_export_pack_includes_audit_layers()
    print("V13.4 checks passed")
