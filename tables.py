"""Excel loading, filtering, and table assembly (R1, R2, R4, R7, R9)."""

from typing import Iterable, Optional

import pandas as pd

from coins import RULES, evaluate_day, rule_key

DATE_FORMAT = "%d/%m/%Y"  # KTD3: confirmed against both sample files.
VISIT_DUMP_SHEET = "Visit DumpReport(V4)"
SUMMARY_SHEET_COLUMNS = ["Date", "DSR ErpId", "TC", "PC", "LPC", "OVC", "Login"]
VISIT_DUMP_COLUMNS = ["DSR ERP ID", "Order Date", "Outlets Erp Id", "Outlets", "LinesCut", "OVC", "Telephonic"]


def _read_sheet(files, sheet_name: str, usecols: list) -> pd.DataFrame:
    frames = [pd.read_excel(f, sheet_name=sheet_name, usecols=usecols) for f in files]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _month_key(dates: pd.Series) -> pd.Series:
    return dates.dt.to_period("M").astype(str)


def load_rows(files, rep_code: str) -> pd.DataFrame:
    """R1, R2: read each file's Summary Sheet tab, filter by rep-code prefix."""
    combined = _read_sheet(files, "Summary Sheet", SUMMARY_SHEET_COLUMNS)
    if combined.empty:
        return combined
    combined["DSR ErpId"] = combined["DSR ErpId"].astype(str)
    matched = combined[combined["DSR ErpId"].str.startswith(rep_code)].copy()
    matched["Date"] = pd.to_datetime(matched["Date"], format=DATE_FORMAT)
    # One row per rep per day in the source; drop exact re-uploads (the same
    # file, or the same date range under a different filename) so they don't
    # double-count -- pd.concat above has no de-dup of its own.
    return matched.drop_duplicates(subset=["DSR ErpId", "Date"])


def _is_active(rows: pd.DataFrame) -> pd.Series:
    """R4: keep a rep-day only when it has a Login value or TC > 0."""
    has_login = rows["Login"].notna() & (rows["Login"].astype(str).str.strip() != "")
    return has_login | (rows["TC"] > 0)


def load_visits(files) -> pd.DataFrame:
    """Read each file's Visit Dump tab, concat, normalize column name/dtypes.

    Deliberately does NO rep filtering -- which months have a file at all
    must be computed from the full set, before any rep-code filter (see
    build_physical_metrics's covered_months).
    """
    combined = _read_sheet(files, VISIT_DUMP_SHEET, VISIT_DUMP_COLUMNS)
    if combined.empty:
        return combined
    combined = combined.rename(columns={"DSR ERP ID": "DSR ErpId"})
    combined["DSR ErpId"] = combined["DSR ErpId"].astype(str)
    combined["Order Date"] = pd.to_datetime(combined["Order Date"]).dt.normalize()
    # One row per visit in the source; drop exact re-uploads the same way
    # load_rows does (no natural visit key is loaded here, so a full-row
    # match is the re-upload signal).
    return combined.drop_duplicates()


def build_physical_metrics(visits: pd.DataFrame, rep_code: str) -> tuple[pd.DataFrame, set]:
    """Physical PC/LPC inputs per rep-day (Product Contract Physical PC/LPC rules).

    A visit qualifies for "physical" credit when OVC == "No" and
    Telephonic == "No". Returns (per-rep-day Physical PC / Lines Cut /
    Outlets for the matching rep family, set of "YYYY-MM" months present
    anywhere in the uploaded Visit Dump data -- used to distinguish a real
    zero from "no Visit Dump file for this month").
    """
    if visits.empty:
        return (
            pd.DataFrame(columns=["Rep", "Date", "Physical PC", "Physical Lines Cut", "Physical Outlets"]),
            set(),
        )

    covered_months = set(_month_key(visits["Order Date"]))
    filtered = visits[visits["DSR ErpId"].str.startswith(rep_code)].copy()
    filtered["_outlet_key"] = filtered["Outlets Erp Id"].fillna(filtered["Outlets"])
    qualifying = filtered[(filtered["OVC"] == "No") & (filtered["Telephonic"] == "No")]

    metrics = (
        qualifying.groupby(["DSR ErpId", "Order Date"])
        .agg(**{
            "Physical PC": ("_outlet_key", "size"),
            "Physical Lines Cut": ("LinesCut", "sum"),
            "Physical Outlets": ("_outlet_key", "nunique"),
        })
        .reset_index()
        .rename(columns={"DSR ErpId": "Rep", "Order Date": "Date"})
    )
    return metrics, covered_months


def build_daily_table(
    rows: pd.DataFrame,
    physical_metrics: Optional[pd.DataFrame] = None,
    covered_months: Optional[set] = None,
    enabled_rules: Optional[Iterable[str]] = None,
) -> pd.DataFrame:
    """R7: one wide row per rep-day with each rule's Target/Achieved/Qualified plus Total Coins.

    `physical_metrics` is None iff no Visit Dump file was uploaded this run --
    that (not a per-row flag) decides whether the Physical PC/LPC columns
    exist at all. When present, a rep-day whose calendar month has no
    matching Visit Dump data still gets the columns, but as NA.
    """
    if rows.empty:
        return pd.DataFrame()
    active = rows[_is_active(rows)]
    if active.empty:
        return pd.DataFrame()
    active = active.copy()

    rules = RULES if physical_metrics is not None else [r for r in RULES if not r.requires_visits]
    needed_columns = list(SUMMARY_SHEET_COLUMNS)

    if physical_metrics is not None:
        active = active.merge(
            physical_metrics, how="left",
            left_on=["DSR ErpId", "Date"], right_on=["Rep", "Date"],
        )
        month_covered = _month_key(active["Date"]).isin(covered_months)
        physical_cols = ["Physical PC", "Physical Lines Cut", "Physical Outlets"]
        for col in physical_cols:
            # Covered month + no matching visit rows (zero qualifying visits
            # that day) is a real computed zero, not NA. An uncovered month
            # stays NaN, which Rule.applicable reads as "not computable".
            active.loc[month_covered & active[col].isna(), col] = 0
        needed_columns += physical_cols

    records = []
    for row in active[needed_columns].to_dict("records"):
        evaluated = evaluate_day(row, enabled_rules, rules)
        record = {
            "Rep": row["DSR ErpId"],
            "Date": row["Date"].date(),
            "Login Target": evaluated["login_target"],
            "Login Achieved": evaluated["login_achieved"],
            "Login Qualified": evaluated["login_qualified"],
        }
        for rule in rules:
            key = rule_key(rule)
            record[f"{rule.name} Target"] = evaluated[f"{key}_target"]
            record[f"{rule.name} Achieved"] = evaluated[f"{key}_achieved"]
            record[f"{rule.name} Qualified"] = evaluated[f"{key}_qualified"]
        record["Total Coins"] = evaluated["total_coins"]
        records.append(record)
    return pd.DataFrame(records)


def build_monthly_rollup(daily_table: pd.DataFrame) -> pd.DataFrame:
    """R9: sum Total Coins per rep per calendar month."""
    if daily_table.empty:
        return pd.DataFrame(columns=["Rep", "Month", "Total Coins"])
    working = daily_table.copy()
    working["Month"] = _month_key(pd.to_datetime(working["Date"]))
    return working.groupby(["Rep", "Month"], as_index=False)["Total Coins"].sum()
