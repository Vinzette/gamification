"""Streamlit app: upload Summary Sheet + Visit Dump exports, view the coin tables."""

import io

import streamlit as st

import coins
from report import build_excel_report
from tables import build_daily_table, build_monthly_rollup, build_physical_metrics, load_rows, load_visits

DEFAULT_REP_CODE = "42216697"


@st.cache_data(show_spinner=False)
def _load_and_join(summary_bytes_by_name: dict, visit_bytes_by_name: dict, rep_code: str):
    """Cached: all Excel I/O plus the Visit Dump join -- independent of which
    rules are enabled, so toggling a checkbox never re-parses a file."""
    summary_files = [io.BytesIO(content) for content in summary_bytes_by_name.values()]
    rows = load_rows(summary_files, rep_code)

    if visit_bytes_by_name:
        visit_files = [io.BytesIO(content) for content in visit_bytes_by_name.values()]
        physical_metrics, covered_months = build_physical_metrics(load_visits(visit_files), rep_code)
    else:
        physical_metrics, covered_months = None, None

    return rows, physical_metrics, covered_months


def main():
    st.title("Gamification Coins")

    uploaded_files = st.file_uploader(
        "Upload Summary Sheet PC export(s)", type="xlsx", accept_multiple_files=True
    )
    visit_files = st.file_uploader(
        "Upload Visit Dump Report export(s) (optional -- needed for Physical PC/LPC)",
        type="xlsx", accept_multiple_files=True,
    )
    rep_code = st.text_input("Base/rep code", value=DEFAULT_REP_CODE)

    st.caption("Rules counted toward Total Coins")
    enabled_rules = set()
    columns = st.columns(len(coins.RULES))
    for column, rule in zip(columns, coins.RULES):
        key = coins.rule_key(rule)
        if column.checkbox(rule.name, value=True, key=f"enable_{key}"):
            enabled_rules.add(key)

    # One placeholder for every transient status message, so a new message
    # replaces the last one in place instead of briefly overlapping it.
    status = st.empty()

    if not uploaded_files:
        status.info("Upload one or more Summary Sheet PC Excel exports to get started.")
        return

    summary_bytes_by_name = {f.name: f.getvalue() for f in uploaded_files}
    visit_bytes_by_name = {f.name: f.getvalue() for f in (visit_files or [])}
    try:
        with status, st.spinner("Loading Summary Sheet data..."):
            rows, physical_metrics, covered_months = _load_and_join(
                summary_bytes_by_name, visit_bytes_by_name, rep_code
            )
    except Exception:
        status.error("File doesn't match the expected Summary Sheet PC / Visit Dump format.")
        return

    if rows.empty:
        status.warning(f"No rows found for base/rep code '{rep_code}'.")
        return

    status.empty()
    daily_table = build_daily_table(rows, physical_metrics, covered_months, enabled_rules)
    monthly_rollup = build_monthly_rollup(daily_table)

    st.subheader("Daily coin table")
    st.dataframe(daily_table, use_container_width=True)
    st.download_button(
        "Download daily coin table (CSV)",
        daily_table.to_csv(index=False),
        file_name="daily_coins.csv",
        mime="text/csv",
    )

    st.subheader("Monthly rollup")
    st.dataframe(monthly_rollup, use_container_width=True)
    st.download_button(
        "Download monthly rollup (CSV)",
        monthly_rollup.to_csv(index=False),
        file_name="monthly_rollup.csv",
        mime="text/csv",
    )

    st.download_button(
        "Download full report (Excel)",
        build_excel_report(daily_table, monthly_rollup),
        file_name="gamification_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    main()
