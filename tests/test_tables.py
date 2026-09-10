import pandas as pd

from tables import build_daily_table, build_monthly_rollup, load_rows

COLUMNS = ["Date", "DSR ErpId", "TC", "PC", "LC", "LPC", "OVC", "Login"]


def make_workbook(path, rows):
    df = pd.DataFrame(rows, columns=COLUMNS)
    with pd.ExcelWriter(path) as writer:
        df.to_excel(writer, sheet_name="Summary Sheet", index=False)
    return path


def test_load_rows_filters_by_rep_code_prefix(tmp_path):
    wb = make_workbook(
        tmp_path / "july.xlsx",
        [
            ["01/07/2026", "42216697SM03", 31, 14, 59, 4.21, 0, "08:41"],
            ["01/07/2026", "99999999SM01", 20, 10, 20, 2.0, 0, "09:00"],
        ],
    )
    result = load_rows([wb], "42216697")
    assert len(result) == 1
    assert result.iloc[0]["DSR ErpId"] == "42216697SM03"


def test_load_rows_concatenates_multiple_files(tmp_path):
    july = make_workbook(tmp_path / "july.xlsx", [["01/07/2026", "42216697SM03", 31, 14, 59, 4.21, 0, "08:41"]])
    august = make_workbook(tmp_path / "august.xlsx", [["01/08/2026", "42216697SM03", 30, 12, 40, 3.33, 0, "08:50"]])
    result = load_rows([july, august], "42216697")
    assert len(result) == 2
    assert set(result["Date"].dt.month) == {7, 8}


def test_load_rows_no_match_returns_empty(tmp_path):
    wb = make_workbook(tmp_path / "july.xlsx", [["01/07/2026", "99999999SM01", 20, 10, 20, 2.0, 0, "09:00"]])
    result = load_rows([wb], "42216697")
    assert result.empty


def test_daily_table_excludes_no_login_and_zero_tc():
    rows = pd.DataFrame(
        [{"Date": pd.Timestamp("2026-07-01"), "DSR ErpId": "42216697SM03", "TC": 0, "PC": 0, "LC": 0, "LPC": 0.0, "OVC": 0, "Login": None}]
    )
    assert build_daily_table(rows).empty


def test_daily_table_includes_login_present_zero_tc():
    rows = pd.DataFrame(
        [{"Date": pd.Timestamp("2026-07-01"), "DSR ErpId": "42216697SM03", "TC": 0, "PC": 0, "LC": 0, "LPC": 0.0, "OVC": 0, "Login": "09:10"}]
    )
    daily = build_daily_table(rows)
    assert len(daily) == 1
    assert daily.iloc[0]["Total Coins"] == 0


def test_daily_table_two_reps_same_date_two_rows():
    rows = pd.DataFrame(
        [
            {"Date": pd.Timestamp("2026-07-01"), "DSR ErpId": "42216697SM03", "TC": 31, "PC": 14, "LC": 59, "LPC": 4.21, "OVC": 0, "Login": "08:41"},
            {"Date": pd.Timestamp("2026-07-01"), "DSR ErpId": "42216697SM27", "TC": 31, "PC": 6, "LC": 40, "LPC": 6.67, "OVC": 0, "Login": "09:52"},
        ]
    )
    assert len(build_daily_table(rows)) == 2


def test_monthly_rollup_two_reps_same_month():
    daily = pd.DataFrame(
        [
            {"Rep": "A", "Date": pd.Timestamp("2026-07-01").date(), "Total Coins": 40},
            {"Rep": "B", "Date": pd.Timestamp("2026-07-05").date(), "Total Coins": 60},
        ]
    )
    assert len(build_monthly_rollup(daily)) == 2


def test_monthly_rollup_one_rep_two_months():
    daily = pd.DataFrame(
        [
            {"Rep": "A", "Date": pd.Timestamp("2026-07-01").date(), "Total Coins": 40},
            {"Rep": "A", "Date": pd.Timestamp("2026-08-01").date(), "Total Coins": 20},
        ]
    )
    rollup = build_monthly_rollup(daily)
    assert len(rollup) == 2
    assert set(rollup["Total Coins"]) == {40, 20}


def test_monthly_rollup_omits_rep_with_no_included_days():
    daily = pd.DataFrame(columns=["Rep", "Date", "Total Coins"])
    assert build_monthly_rollup(daily).empty
