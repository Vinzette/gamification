"""Streamlit app: upload Summary Sheet exports, view the coin tables (U3)."""

import io

import streamlit as st

from tables import build_daily_table, build_monthly_rollup, load_rows

DEFAULT_REP_CODE = "42216697"


@st.cache_data(show_spinner="Loading Summary Sheet data...")
def _cached_pipeline(file_bytes_by_name: dict, rep_code: str):
    files = [io.BytesIO(content) for content in file_bytes_by_name.values()]
    rows = load_rows(files, rep_code)
    daily_table = build_daily_table(rows)
    monthly_rollup = build_monthly_rollup(daily_table)
    return rows, daily_table, monthly_rollup


def main():
    st.title("Gamification Coins")

    uploaded_files = st.file_uploader(
        "Upload Summary Sheet PC export(s)", type="xlsx", accept_multiple_files=True
    )
    rep_code = st.text_input("Base/rep code", value=DEFAULT_REP_CODE)

    if not uploaded_files:
        st.info("Upload one or more Summary Sheet PC Excel exports to get started.")
        return

    file_bytes_by_name = {f.name: f.getvalue() for f in uploaded_files}
    try:
        rows, daily_table, monthly_rollup = _cached_pipeline(file_bytes_by_name, rep_code)
    except Exception:
        st.error("File doesn't match the expected Summary Sheet PC format.")
        return

    if rows.empty:
        st.warning(f"No rows found for base/rep code '{rep_code}'.")
        return

    st.subheader("Daily coin table")
    st.dataframe(daily_table, use_container_width=True)

    st.subheader("Monthly rollup")
    st.dataframe(monthly_rollup, use_container_width=True)


if __name__ == "__main__":
    main()
