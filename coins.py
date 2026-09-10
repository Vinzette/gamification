"""Coin rule evaluation (Product Contract R3, R5, R6, R8, R10)."""

from dataclasses import dataclass
from datetime import datetime, time
from typing import Callable, Iterable, Optional

LOGIN_CUTOFF = time(10, 0)
LOGIN_TARGET_LABEL = "on or before 10:00"
PHYSICAL_BONUS_COINS = 110


@dataclass(frozen=True)
class Rule:
    name: str
    metric: Callable[[dict], Optional[float]]
    comparison: Callable[[float], bool]
    target_label: str
    coins: int
    applicable: Callable[[dict], bool] = lambda row: True
    requires_visits: bool = False


def _is_missing(value) -> bool:
    """True for None or NaN -- covers a plain None (unit tests) and a real
    pandas NaN from an unmatched merge (tables.py), no pandas/math import."""
    return value is None or value != value


def _productive_calls_metric(row: dict) -> Optional[float]:
    return row["PC"]


def _lpc_metric(row: dict) -> Optional[float]:
    return row["LPC"] if row["PC"] > 0 else None


def _ovc_rate_metric(row: dict) -> Optional[float]:
    return row["OVC"] / row["TC"] if row["TC"] > 0 else None


def _physical_pc_metric(row: dict) -> Optional[float]:
    return row["Physical PC"]


def _physical_lpc_metric(row: dict) -> Optional[float]:
    return row["Physical Lines Cut"] / row["Physical Outlets"] if row["Physical Outlets"] > 0 else None


def _has_physical_data(row: dict) -> bool:
    return not _is_missing(row.get("Physical PC"))


_PHYSICAL_PC_RULE = Rule(
    "Physical PC", _physical_pc_metric, lambda v: v >= 15, ">= 15", 40,
    applicable=_has_physical_data, requires_visits=True,
)
_PHYSICAL_LPC_RULE = Rule(
    "Physical LPC", _physical_lpc_metric, lambda v: v >= 6, ">= 6", 40,
    applicable=_has_physical_data, requires_visits=True,
)

# R8: the coin-earning rules as a plain, extensible list (KTD1). Physical PC/LPC
# only apply to a rep-day whose month has a matching Visit Dump upload -- see
# `applicable` and `requires_visits` (tables.py decides column presence from
# `requires_visits`; `applicable` decides NA-vs-computed per row).
RULES = [
    Rule("Productive Calls", _productive_calls_metric, lambda v: v >= 15, ">= 15", 20),
    Rule("LPC", _lpc_metric, lambda v: v >= 6, ">= 6", 20),
    Rule("OVC rate", _ovc_rate_metric, lambda v: v < 0.40, "< 40%", 40),
    _PHYSICAL_PC_RULE,
    _PHYSICAL_LPC_RULE,
]


def rule_key(rule: Rule) -> str:
    return rule.name.lower().replace(" ", "_")


# Tied to the two Rule objects directly, not to a count/filter over RULES --
# stays correct however many more requires_visits=True rules get appended.
_PHYSICAL_PC_KEY = rule_key(_PHYSICAL_PC_RULE)
_PHYSICAL_LPC_KEY = rule_key(_PHYSICAL_LPC_RULE)


def _parse_login(value) -> Optional[time]:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.strptime(value.strip(), "%H:%M").time()
    except ValueError:
        return None


def _gate_open(login_time: Optional[time]) -> bool:
    return login_time is not None and login_time <= LOGIN_CUTOFF


def login_qualifies(row: dict) -> bool:
    return _gate_open(_parse_login(row.get("Login")))


def evaluate_day(
    row: dict,
    enabled_rules: Optional[Iterable[str]] = None,
    rules: Optional[list] = None,
) -> dict:
    """R5/R6: the login gate runs first (KTD2); each rule only runs when the
    gate is open and the rule is applicable to this row (has the data it needs).

    `enabled_rules` (rule keys) controls only which qualifying rules count
    toward Total Coins -- disabled rules still render their Target/Achieved/
    Qualified normally. `None` means every rule counts (today's behavior).
    `rules` lets a caller run a subset (e.g. tables.py drops the Physical
    rules entirely when no Visit Dump data was uploaded this run). `None`
    means the full module-level RULES list.
    """
    rules = rules if rules is not None else RULES
    login_time = _parse_login(row.get("Login"))
    gate_open = _gate_open(login_time)

    result = {
        "login_target": LOGIN_TARGET_LABEL,
        "login_achieved": login_time.strftime("%H:%M") if login_time else None,
        "login_qualified": gate_open,
    }

    coins_by_key = {}
    for rule in rules:
        key = rule_key(rule)
        if not gate_open or not rule.applicable(row):
            target = achieved = qualified = None
        else:
            achieved = rule.metric(row)
            qualified = achieved is not None and rule.comparison(achieved)
            target = rule.target_label
        result[f"{key}_target"] = target
        result[f"{key}_achieved"] = achieved
        result[f"{key}_qualified"] = qualified
        if qualified and (enabled_rules is None or key in enabled_rules):
            coins_by_key[key] = rule.coins

    total_coins = sum(coins_by_key.values())
    # Physical bonus: only fires when both physical rules qualified AND are
    # enabled (both present in coins_by_key). Replaces the sum outright so it
    # stays correct even if the 40/40 coin values are edited later.
    if _PHYSICAL_PC_KEY in coins_by_key and _PHYSICAL_LPC_KEY in coins_by_key:
        total_coins = total_coins - coins_by_key[_PHYSICAL_PC_KEY] - coins_by_key[_PHYSICAL_LPC_KEY] + PHYSICAL_BONUS_COINS
    result["total_coins"] = total_coins
    return result
