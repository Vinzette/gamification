"""Excel loading, filtering, and table assembly (R1, R2, R4, R7, R9)."""

import pandas as pd

from coins import RULES, evaluate_day, rule_key

DATE_FORMAT = "%d/%m/%Y"  # KTD3: confirmed against both sample files.


def load_rows(files, rep_code: str) -> pd.DataFrame:
    """R1, R2: read each file's Summary Sheet tab, filter by rep-code prefix."""
    frames = [pd.read_excel(f, sheet_name="Summary Sheet") for f in files]
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    combined["DSR ErpId"] = combined["DSR ErpId"].astype(str)
    matched = combined[combined["DSR ErpId"].str.startswith(rep_code)].copy()
    matched["Date"] = pd.to_datetime(matched["Date"], format=DATE_FORMAT)
    return matched


def _is_active(rows: pd.DataFrame) -> pd.Series:
    """R4: keep a rep-day only when it has a Login value or TC > 0."""
    has_login = rows["Login"].notna() & (rows["Login"].astype(str).str.strip() != "")
    return has_login | (rows["TC"] > 0)


def build_daily_table(rows: pd.DataFrame) -> pd.DataFrame:
    """R7: one wide row per rep-day with each rule's Target/Achieved/Qualified plus Total Coins."""
    if rows.empty:
        return pd.DataFrame()
    active = rows[_is_active(rows)]
    if active.empty:
        return pd.DataFrame()

    needed_columns = ["Date", "DSR ErpId", "TC", "PC", "LPC", "OVC", "Login"]
    records = []
    for _, row in active[needed_columns].iterrows():
        evaluated = evaluate_day(row.to_dict())
        record = {
            "Rep": row["DSR ErpId"],
            "Date": row["Date"].date(),
            "Login Target": evaluated["login_target"],
            "Login Achieved": evaluated["login_achieved"],
            "Login Qualified": evaluated["login_qualified"],
        }
        for rule in RULES:
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
    working["Month"] = pd.to_datetime(working["Date"]).dt.to_period("M").astype(str)
    return working.groupby(["Rep", "Month"], as_index=False)["Total Coins"].sum()
