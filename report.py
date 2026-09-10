"""Downloadable Excel report: Daily + Monthly sheets, light styling."""

import io

import pandas as pd
from openpyxl.styles import Font


def build_excel_report(daily_table: pd.DataFrame, monthly_rollup: pd.DataFrame) -> bytes:
    """Two-sheet .xlsx: bold header row, frozen header, autofilter.

    Deliberately light polish only -- no merged multi-row headers or color
    banding (declined in favor of a simpler build; see the sample Nivea
    report for that heavier style).
    """
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        daily_table.to_excel(writer, sheet_name="Daily", index=False)
        monthly_rollup.to_excel(writer, sheet_name="Monthly", index=False)
        for sheet_name in ("Daily", "Monthly"):
            worksheet = writer.sheets[sheet_name]
            for cell in worksheet[1]:
                cell.font = Font(bold=True)
            worksheet.freeze_panes = "A2"
            worksheet.auto_filter.ref = worksheet.dimensions
    return buffer.getvalue()
