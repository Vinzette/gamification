import pandas as pd

from tables import build_daily_table, build_monthly_rollup, build_physical_metrics, load_rows, load_visits

COLUMNS = ["Date", "DSR ErpId", "TC", "PC", "LC", "LPC", "OVC", "Login"]
VISIT_COLUMNS = ["DSR ERP ID", "Order Date", "Outlets Erp Id", "Outlets", "LinesCut", "OVC", "Telephonic"]


def make_workbook(path, rows):
    df = pd.DataFrame(rows, columns=COLUMNS)
    with pd.ExcelWriter(path) as writer:
        df.to_excel(writer, sheet_name="Summary Sheet", index=False)
    return path


def make_visit_workbook(path, rows):
    df = pd.DataFrame(rows, columns=VISIT_COLUMNS)
    with pd.ExcelWriter(path) as writer:
        df.to_excel(writer, sheet_name="Visit DumpReport(V4)", index=False)
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


def test_load_visits_renames_dsr_erp_id(tmp_path):
    wb = make_visit_workbook(
        tmp_path / "july_visits.xlsx",
        [["42216697SM03", "2026-07-01", "Out-1", "Store One", 6, "No", "No"]],
    )
    visits = load_visits([wb])
    assert "DSR ErpId" in visits.columns
    assert visits.iloc[0]["DSR ErpId"] == "42216697SM03"


def test_build_physical_metrics_counts_only_qualifying_visits(tmp_path):
    wb = make_visit_workbook(
        tmp_path / "july_visits.xlsx",
        [
            ["42216697SM03", "2026-07-01", "Out-1", "Store One", 6, "No", "No"],
            ["42216697SM03", "2026-07-01", "Out-2", "Store Two", 10, "Yes", "No"],  # OVC excludes it
            ["42216697SM03", "2026-07-01", "Out-3", "Store Three", 5, "No", "Yes"],  # Telephonic excludes it
        ],
    )
    visits = load_visits([wb])
    metrics, covered_months = build_physical_metrics(visits, "42216697")
    row = metrics.iloc[0]
    assert row["Physical PC"] == 1
    assert row["Physical Lines Cut"] == 6
    assert row["Physical Outlets"] == 1
    assert covered_months == {"2026-07"}


def test_build_physical_metrics_denominator_is_distinct_outlets(tmp_path):
    wb = make_visit_workbook(
        tmp_path / "july_visits.xlsx",
        [
            ["42216697SM03", "2026-07-01", "Out-1", "Store One", 4, "No", "No"],
            ["42216697SM03", "2026-07-01", "Out-1", "Store One", 6, "No", "No"],  # same store, twice
        ],
    )
    visits = load_visits([wb])
    metrics, _ = build_physical_metrics(visits, "42216697")
    row = metrics.iloc[0]
    assert row["Physical PC"] == 2  # counts visits
    assert row["Physical Outlets"] == 1  # distinct stores, not visit count


def test_build_physical_metrics_falls_back_to_outlet_name_when_id_missing(tmp_path):
    wb = make_visit_workbook(
        tmp_path / "july_visits.xlsx",
        [["42216697SM03", "2026-07-01", None, "Store One", 6, "No", "No"]],
    )
    visits = load_visits([wb])
    metrics, _ = build_physical_metrics(visits, "42216697")
    assert metrics.iloc[0]["Physical Outlets"] == 1


def test_build_physical_metrics_covered_months_derived_before_rep_filter(tmp_path):
    wb = make_visit_workbook(
        tmp_path / "july_visits.xlsx",
        [["99999999SM01", "2026-07-01", "Out-1", "Store One", 6, "No", "No"]],
    )
    visits = load_visits([wb])
    metrics, covered_months = build_physical_metrics(visits, "42216697")
    assert metrics.empty
    assert covered_months == {"2026-07"}


def test_daily_table_without_visit_files_omits_physical_columns():
    rows = pd.DataFrame(
        [{"Date": pd.Timestamp("2026-07-01"), "DSR ErpId": "42216697SM03", "TC": 31, "PC": 14, "LC": 59, "LPC": 4.21, "OVC": 0, "Login": "08:41"}]
    )
    daily = build_daily_table(rows)
    assert "Physical PC Achieved" not in daily.columns


def test_daily_table_uncovered_month_shows_na_for_physical_rules(tmp_path):
    rows = pd.DataFrame(
        [{"Date": pd.Timestamp("2026-08-01"), "DSR ErpId": "42216697SM03", "TC": 31, "PC": 14, "LC": 59, "LPC": 4.21, "OVC": 0, "Login": "08:41"}]
    )
    wb = make_visit_workbook(
        tmp_path / "july_visits.xlsx",
        [["42216697SM03", "2026-07-01", "Out-1", "Store One", 6, "No", "No"]],
    )
    visits = load_visits([wb])
    physical_metrics, covered_months = build_physical_metrics(visits, "42216697")
    daily = build_daily_table(rows, physical_metrics, covered_months)
    assert daily.iloc[0]["Physical PC Achieved"] is None
    assert daily.iloc[0]["Physical PC Qualified"] is None


def test_daily_table_covered_month_zero_visits_is_real_zero_not_na(tmp_path):
    rows = pd.DataFrame(
        [{"Date": pd.Timestamp("2026-07-02"), "DSR ErpId": "42216697SM03", "TC": 31, "PC": 14, "LC": 59, "LPC": 4.21, "OVC": 0, "Login": "08:41"}]
    )
    wb = make_visit_workbook(
        tmp_path / "july_visits.xlsx",
        [["42216697SM03", "2026-07-01", "Out-1", "Store One", 6, "No", "No"]],  # different day, same month
    )
    visits = load_visits([wb])
    physical_metrics, covered_months = build_physical_metrics(visits, "42216697")
    daily = build_daily_table(rows, physical_metrics, covered_months)
    assert daily.iloc[0]["Physical PC Achieved"] == 0
    assert daily.iloc[0]["Physical PC Qualified"] == False  # noqa: E712 (may be numpy bool_, not Python bool)


def test_daily_table_includes_tc_positive_without_login():
    rows = pd.DataFrame(
        [{"Date": pd.Timestamp("2026-07-01"), "DSR ErpId": "42216697SM03", "TC": 20, "PC": 10, "LC": 0, "LPC": 0.0, "OVC": 0, "Login": None}]
    )
    daily = build_daily_table(rows)
    assert len(daily) == 1
    assert daily.iloc[0]["Login Qualified"] == False  # noqa: E712 (may be numpy bool_, not Python bool)
    assert daily.iloc[0]["Total Coins"] == 0


def test_build_physical_metrics_empty_visits_returns_empty_frame():
    metrics, covered_months = build_physical_metrics(pd.DataFrame(), "42216697")
    assert metrics.empty
    assert covered_months == set()


def test_load_rows_deduplicates_reuploaded_rows(tmp_path):
    wb = make_workbook(tmp_path / "july.xlsx", [["01/07/2026", "42216697SM03", 31, 14, 59, 4.21, 0, "08:41"]])
    # Same rep-day uploaded twice, as if the same file were selected twice.
    result = load_rows([wb, wb], "42216697")
    assert len(result) == 1


def test_load_visits_deduplicates_reuploaded_rows(tmp_path):
    wb = make_visit_workbook(
        tmp_path / "july_visits.xlsx",
        [["42216697SM03", "2026-07-01", "Out-1", "Store One", 6, "No", "No"]],
    )
    result = load_visits([wb, wb])
    assert len(result) == 1
