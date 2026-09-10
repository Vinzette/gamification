---
title: Gamification Coins Engine - Plan
type: feat
date: 2026-09-09
topic: gamification-coins-engine
artifact_contract: ce-unified-plan/v1
artifact_readiness: implementation-ready
product_contract_source: ce-brainstorm
execution: code
---

## Goal Capsule

- **Objective:** Field reps under a selected base/rep code can see, per day and rolled up by month, whether they qualified for each gamification rule and how many coins they earned, computed automatically from FieldAssist's Summary Sheet exports.
- **Means:** A Streamlit app that ingests uploaded Summary Sheet Excel exports and computes the coin table (KTD1-KTD6).
- **Authority:** This brainstorm dialogue and its session-settled decisions (Key Decisions below); no other upstream source.
- **Stop conditions:** Stop and confirm with the user before changing any coin rule's threshold, coin value, or gate logic — those are product decisions owned by the Product Contract (R3), not implementation choices.
- **Execution profile:** Single-session interactive implementation; no autonomous goal-mode run requested.
- **Tail ownership:** The user runs and demos the app locally; no CI or deployment pipeline is in scope.
- **Open blockers:** None.

## Product Contract

### Summary

A Streamlit tool that ingests FieldAssist's monthly "Summary Sheet PC" Excel exports and computes a per-rep, per-day gamification coin table (Qualified / Target / Achieved per rule, plus Total Coins), with a month-wise coin rollup, for a selected base/rep code (defaulting to `42216697`).

### Problem Frame

FieldAssist wants to reward reps for good field behavior — logging in on time, making enough productive calls, cutting enough lines per call, and keeping out-of-compliance visits low — but today that means manually cross-referencing several columns per rep per day across a monthly export with 100+ columns and thousands of rows. There is no single place that turns the raw export into a coin verdict a rep or manager can read at a glance.

### Requirements

**Data ingestion**

- R1. The app accepts one or more uploaded Excel files matching the FieldAssist "Summary Sheet PC" export format (an `Activity` tab and a `Summary Sheet` tab), reading rep-day rows from the `Summary Sheet` tab.
- R2. The app filters rows to a base/rep code entered by the user, matching any `DSR ErpId` that starts with the entered code (e.g. `42216697` matches `42216697SM03`, `42216697SM27`, ...), defaulting to `42216697`.

**Coin rules**

- R3. For each matched rep-day, the app evaluates four rules against the source columns:
  - **Login gate:** eligible when `Login` is on or before 10:00 AM.
  - **Productive Calls:** qualifies when `PC` >= 15 (20 coins).
  - **LPC:** qualifies when `LPC` > 6 (20 coins).
  - **OVC rate:** qualifies when `OVC / TC` < 40% (40 coins).
- R10. When the denominator for a rate is zero (`PC` = 0 for LPC, or `TC` = 0 for OVC rate), that rule does not qualify rather than raising an error.

**Daily table**

- R4. A rep-day is included in the daily table only when it has a recorded `Login` time or `TC` > 0; a rep-day with neither is excluded entirely.
- R5. When the login gate is not met (late or the `Login` value is missing while `TC` > 0), Total Coins for that rep-day is 0, and the Productive Calls / LPC / OVC rate Target, Achieved, and Qualified cells are shown as NA rather than computed.
- R6. When the login gate is met, Total Coins is the sum of coins from whichever of Productive Calls / LPC / OVC rate the rep qualifies for that day (0-80).
- R7. The daily table has one row per rep per day, with columns for rep identity, date, and — for each of the four rules — Target, Achieved, and Qualified, plus a Total Coins column.
- R8. The three coin-earning rules (Productive Calls, LPC, OVC rate) are represented as a list of rule definitions (name, target, comparison, coin value) rather than as separately hardcoded checks, so an additional rule can be added later without restructuring the daily table or the calc logic. The login gate is a separate boolean check with no coin value of its own — it is not one of these rule-list entries.

**Monthly rollup**

- R9. A month-wise rollup table shows, per rep per calendar month, the sum of Total Coins across that rep's included daily rows for that month.

### Key Decisions

- **Login gate blocks all coins for the day, not just its own line** (session-settled: user-directed — chosen over scoring the four rules independently: a late login zeroes the whole day's coins). Governs R5, R6.
- **Absent rep-days are excluded from the table** (session-settled: user-directed — chosen over showing them as zero-coin rows: keeps the table focused on days with recorded activity). Governs R4.
- **Base/rep code is filterable, defaulting to `42216697`** (session-settled: user-directed — chosen over hardcoding the prototype to one code: filtering is nearly free once the upload already keys off a rep column, and it makes the prototype reusable beyond this demo). Governs R2.
- **Rule set is structured as an extensible list, not fixed to three checks** (session-settled: user-directed — chosen over four separately hardcoded checks: two concrete future rules, Physical PC and Physical LPC, are already planned once location-verification data is available, so the extensibility is not speculative). Governs R8.
- **A zero-denominator rate defaults to "does not qualify."** No rule text covers a rep with zero productive calls or zero total calls; treating it as a non-qualifying result (rather than erroring or showing NA) keeps the daily table always renderable. Governs R10.

### Acceptance Examples

- AE1. **Covers R3, R6.** Given a rep logs in at 09:45 with `PC`=18, `LPC`=7.2, `OVC`=2, `TC`=32. When the day is evaluated. Then Login Qualified=Yes; Productive Calls Qualified=Yes (+20); LPC Qualified=Yes (+20); OVC rate = 6.25%, Qualified=Yes (+40); Total Coins=80.
- AE2. **Covers R5.** Given a rep logs in at 10:20 against a 10:00 target, with `PC`=20, `LPC`=8, `OVC`=1, `TC`=30. When the day is evaluated. Then Login Qualified=No; Productive Calls / LPC / OVC rate Target, Achieved, and Qualified are all NA; Total Coins=0.
- AE3. **Covers R4.** Given a rep has no `Login` value and `TC`=0 for a date. When the daily table is built. Then that rep-date row is omitted entirely.
- AE4. **Covers R4, R6, R10.** Given a rep has a `Login` value at 09:10 but `TC`=0 for that date. When the day is evaluated. Then the row is included (login qualifies); Productive Calls Qualified=No (`PC`=0); LPC Qualified=No (zero-denominator default); OVC rate Qualified=No (zero-denominator default); Total Coins=0.

### Scope Boundaries

**Deferred for later:**

- Physical PC and Physical LPC — location-verified variants of the existing Productive Calls and LPC rules, worth more coins for confirmed on-site presence. Blocked on location-verification data becoming available; the rule-list structure (R8) anticipates them, but neither is built in this prototype.
- Any other coin-earning rules beyond the four named in R3 — same rule-list structure anticipates them, none built now.
- Multi-base-code or org-wide dashboards, historical trend charts, leaderboards.

**Outside this product's identity:**

- Editing or correcting source data inside the app — it is read-only over uploaded files.
- Any write-back to FieldAssist systems — this is a standalone reporting/demo tool.

### Dependencies / Assumptions

- Uploaded Excel files follow the "Summary Sheet PC (New)" format observed in `data/`, with a `Summary Sheet` tab carrying `Date`, `DSR ErpId`, `TC`, `PC`, `LC`, `LPC`, `OVC`, and `Login` columns.
- `LPC` and `OVC` in the source file are already the values needed (`LPC` = `LC`/`PC` per row, `OVC` = a raw out-of-compliance-visit count), not requiring re-derivation from other columns.
- A file's date range may span one or more calendar months; the monthly rollup buckets each included day by its own calendar month.
- `Date` is a plain-text string in `DD/MM/YYYY` format and `Login` is a plain-text `HH:MM` string with no seconds or timezone — confirmed during planning against both sample files (see KTD3, KTD4).

### Sources / Research

- `data/Summary Sheet PC (New)_01-07-26 to 31-07-26_17881676068781628555d496-3395-4418-b360-19d7ba2bb683.xlsx` — `Summary Sheet` tab, confirmed columns and one row per rep per day.
- `data/Summary Sheet PC (New)_01-08-26 to 31-08-26_17883274828781620020cbf0-03cf-41e4-b86f-b1f8792f5661.xlsx` — same format, second month.
- Confirmed `DSR ErpId` values prefixed `42216697` (e.g. `42216697SM03`, `42216697SM27`, `42216697SM33`, ...) resolve to 11 distinct reps in July and 10 in August; filtering to "has `Login` or `TC` > 0" (R4) keeps 251 of the July file's 309 matching rows.

---

## Planning Contract

### Key Technical Decisions

- KTD1. **The rule set is a plain list of `Rule` records** — `name`, `metric` (extracts the achieved value, `None` when its denominator is 0 per R10), `comparison` (the qualifying test), `target label`, and `coin value` — evaluated by one shared loop. Adding Physical PC or Physical LPC later means appending two more records, not touching the loop (session-settled: user-directed — chosen over four separately hardcoded checks: instantiates the Product Contract's extensible-rule-list decision at the code level). Governs R8, R10.
- KTD2. **The login gate runs before the rule loop, as a separate boolean check** — it does not itself earn coins, so it is not a `Rule` list entry. When it fails, the loop does not run and all three rule cells render NA (R5); when it passes, the loop runs and sums qualifying coins (R6). Governs R3, R5, R6.
- KTD3. **`Date` parses with format `%d/%m/%Y`.** Confirmed against both sample files: values run 01-31 with the month fixed to match each file's own date range (`07` in the July file, `08` in the August file), ruling out a month-first reading. Resolves the day/month-order ambiguity for the monthly rollup (R9).
- KTD4. **`Login` parses as `%H:%M`.** Confirmed HH:MM-only (no seconds, no timezone) across both sample files; a missing value parses to null and fails the login gate the same as a late login (R5).
- KTD5. **Wrap the Excel-parsing step in `st.cache_data`, keyed on the uploaded file bytes.** Streamlit reruns the whole script on every widget interaction (e.g. editing the rep-code filter); without caching, a 100+ column workbook would be re-parsed on every keystroke. Addresses the performance concern raised during document review.
- KTD6. **Dependencies are pinned in a plain `requirements.txt`** (`streamlit`, `pandas`, `openpyxl`) rather than a `pyproject.toml` build — no packaging or publishing need for a single-file prototype.

### High-Level Technical Design

```mermaid
flowchart TB
  A[Uploaded Excel file[s]] --> B[Load Summary Sheet tab, filter by rep-code prefix - U2]
  B --> C[Per rep-day: login gate then Rule list - U1]
  C --> D[Daily table: Target/Achieved/Qualified per rule + Total Coins - U2]
  D --> E[Monthly rollup: sum Total Coins by rep + calendar month - U2]
  D --> F[Streamlit: render daily table - U3]
  E --> G[Streamlit: render monthly table - U3]
```

U1 (coin logic) has no dependency on U2 or U3 — it is a pure function of one rep-day row, which is what makes it independently unit-testable.

---

## Implementation Units

### U1. Coin rule evaluation

- **Goal:** Implement the login gate and the extensible `Rule` list (KTD1, KTD2), and evaluate one rep-day row into per-rule Target/Achieved/Qualified plus Total Coins.
- **Requirements:** R3, R5, R6, R8, R10 (KTD1, KTD2)
- **Dependencies:** none — pure logic, no dependency on file I/O or Streamlit.
- **Files:**
  - `coins.py` (create)
  - `tests/test_coins.py` (create)
- **Approach:**
  1. Define a `Rule` record with fields `name`, `metric`, `comparison`, `target_label`, `coins`, per KTD1.
  2. Build the `RULES` list: Productive Calls (`metric` = `PC`, qualifies when >= 15, target label ">= 15", 20 coins), LPC (`metric` = `LPC` when `PC` > 0 else `None`, qualifies when > 6, target label "> 6", 20 coins), OVC rate (`metric` = `OVC / TC` when `TC` > 0 else `None`, qualifies when < 40%, target label "< 40%", 40 coins).
  3. Write `login_qualifies(row)`: true when `Login` parses (KTD4) to a time on or before 10:00, false when late or null.
  4. Write `evaluate_day(row)`: if the login gate fails, return NA for every rule's Target/Achieved/Qualified and Total Coins 0 (R5); otherwise run each `Rule` in `RULES`, sum the `coins` of every qualifying rule into Total Coins (R6).
- **Technical design:** Directional shape only, not literal code:
  ```
  Rule = record(name, metric(row) -> value|None, comparison(value) -> bool, target_label, coins)
  RULES = [productive_calls_rule, lpc_rule, ovc_rate_rule]

  evaluate_day(row):
    if not login_qualifies(row):
      return {login: (10:00, achieved_login, No)} + {each rule: NA, NA, NA} + total=0
    results = []
    total = 0
    for rule in RULES:
      value = rule.metric(row)
      qualified = value is not None and rule.comparison(value)
      if qualified: total += rule.coins
      results.append((rule.name, rule.target_label, value, qualified))
    return {login: (10:00, achieved_login, Yes)} + results + total
  ```
- **Patterns to follow:** none — greenfield module.
- **Test scenarios:**
  - Covers AE1. Login 09:45, `PC`=18, `LPC`=7.2, `OVC`=2, `TC`=32 -> all three rules qualify, Total Coins=80.
  - Covers AE2. Login 10:20 (target 10:00), any `PC`/`LPC`/`OVC`/`TC` -> all three rule cells NA, Total Coins=0.
  - Covers AE4. Login 09:10, `TC`=0 -> login qualifies; Productive Calls, LPC, and OVC rate all not-qualified via the zero-denominator default; Total Coins=0.
  - Boundary: `PC`=15 exactly qualifies (threshold is `>=`, not `>`).
  - Boundary: `LPC`=6.0 exactly does not qualify (threshold is strict `>`).
  - Boundary: OVC rate = 40% exactly does not qualify (threshold is strict `<`).
  - Boundary: `Login`=10:00 exactly qualifies ("on or before" includes the boundary).
  - Missing `Login` value with `TC`>0: gate fails the same as a late login.
- **Verification:** Every scenario above passes as a `pytest` case in `tests/test_coins.py`; the AE1/AE2/AE4 scenarios reproduce the origin doc's Acceptance Examples exactly.

### U2. Data loading and table assembly

- **Goal:** Load the uploaded files' `Summary Sheet` tabs, filter by rep code and by activity, and assemble the daily table and the monthly rollup using U1's per-row evaluation.
- **Requirements:** R1, R2, R4, R7, R9 (KTD3)
- **Dependencies:** U1
- **Files:**
  - `data.py` (create)
  - `tests/test_data.py` (create)
- **Approach:**
  1. `load_rows(files, rep_code)`: read each uploaded file's `Summary Sheet` tab with `pandas`, concatenate, cast `DSR ErpId` to string and filter to rows starting with `rep_code` (R2), parse `Date` per KTD3.
  2. `build_daily_table(rows)`: keep only rows where `Login` is present or `TC` > 0 (R4); for each kept row call U1's `evaluate_day` and flatten the result into one wide row — rep identity, date, the four rules' Target/Achieved/Qualified triplets, Total Coins (R7).
  3. `build_monthly_rollup(daily_table)`: group by rep identity and the calendar month of `Date`, sum Total Coins (R9).
- **Patterns to follow:** none — greenfield module.
- **Test scenarios:**
  - Happy path: one file with rows for the target code and other codes returns only the matching rows.
  - Multiple files: two files (July + August) concatenate into rows for both months.
  - No matching rows: a rep code with zero matches returns an empty daily table, not an error.
  - Covers AE3. A rep-day with no `Login` and `TC`=0 is excluded from the daily table.
  - A rep-day with `Login` present but `TC`=0 is included (per R4's inclusion rule and AE4).
  - Two reps under the same base code produce two separate daily rows for the same date.
  - Monthly rollup: two reps in the same month produce two separate rollup rows.
  - Monthly rollup: one rep's rows spanning two uploaded files (July + August) produce two separate monthly rows.
  - Monthly rollup: a rep with zero included daily rows does not appear in the rollup at all.
- **Verification:** Loading the July sample file with code `42216697` returns 309 rows before the activity filter and 251 after (confirmed during planning research); the monthly rollup for that month equals the sum of the daily table's Total Coins column for the same rep.

### U3. Streamlit app

- **Goal:** Wire U1 and U2 into a single-page Streamlit app: file uploader, rep/base-code text input (default `42216697`), and the daily and monthly tables.
- **Requirements:** R1, R2 (UI-facing); surfaces R4, R7, R9
- **Dependencies:** U1, U2
- **Files:**
  - `app.py` (create)
  - `requirements.txt` (create) — `streamlit`, `pandas`, `openpyxl` (KTD6)
- **Approach:**
  1. `st.file_uploader(..., accept_multiple_files=True)` for the Excel exports.
  2. `st.text_input("Base/rep code", value="42216697")`.
  3. Wrap U2's `load_rows` in `st.cache_data`, keyed on the uploaded files' bytes (KTD5).
  4. Render the daily table with `st.dataframe`, then the monthly rollup with a second `st.dataframe` below it.
  5. Handle the empty-upload state (prompt to upload a file, no tables rendered) and the no-match state (rep code matches no rows -> a message, not an empty table).
- **Patterns to follow:** none — greenfield module.
- **Test scenarios:**
  Test expectation: manual verification only — U1 and U2 already cover the logic with unit tests; `app.py` is thin UI wiring with no pure-function boundary worth a separate automated test. Run `streamlit run app.py`, upload the July sample file, and confirm both tables render.
- **Verification:** `streamlit run app.py` starts without error. Uploading the July sample file with the default rep code `42216697` shows a daily row for `42216697SM03` on 2026-07-01 (`TC`=31, `PC`=14, `LPC`=4.21, `OVC`=0, `Login`=08:41): Login Qualified=Yes, Productive Calls Qualified=No, LPC Qualified=No, OVC rate = 0% Qualified=Yes (+40), Total Coins=40 — and a July monthly total for that rep that includes this day's 40 coins.

---

## Verification Contract

- Unit tests: `pytest tests/` (install `requirements.txt` first, or run via `uv run --with-requirements requirements.txt pytest tests/`) — covers U1 and U2 in full, including every Acceptance Example and boundary case listed above.
- Manual smoke check: `streamlit run app.py`, upload `data/Summary Sheet PC (New)_01-07-26 to 31-07-26_...xlsx`, confirm the daily and monthly tables render with the U3 verification example's values.

## Definition of Done

- U1 and U2's automated test scenarios all pass under `pytest`.
- U3's manual smoke check passes: the app starts, and the upload-and-render flow produces the values named in U3's verification.
- `requirements.txt` lists exactly `streamlit`, `pandas`, `openpyxl` — no unused dependencies.
- No dead-end or experimental code remains from approaches that did not pan out.
