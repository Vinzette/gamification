"""Coin rule evaluation (Product Contract R3, R5, R6, R8, R10)."""

from dataclasses import dataclass
from datetime import datetime, time
from typing import Callable, Optional

LOGIN_CUTOFF = time(10, 0)
LOGIN_TARGET_LABEL = "on or before 10:00"


@dataclass(frozen=True)
class Rule:
    name: str
    metric: Callable[[dict], Optional[float]]
    comparison: Callable[[float], bool]
    target_label: str
    coins: int


def _productive_calls_metric(row: dict) -> Optional[float]:
    return row["PC"]


def _lpc_metric(row: dict) -> Optional[float]:
    return row["LPC"] if row["PC"] > 0 else None


def _ovc_rate_metric(row: dict) -> Optional[float]:
    return row["OVC"] / row["TC"] if row["TC"] > 0 else None


# R8: the three coin-earning rules as a plain, extensible list (KTD1).
# Adding Physical PC / Physical LPC later means appending entries here.
RULES = [
    Rule("Productive Calls", _productive_calls_metric, lambda v: v >= 15, ">= 15", 20),
    Rule("LPC", _lpc_metric, lambda v: v > 6, "> 6", 20),
    Rule("OVC rate", _ovc_rate_metric, lambda v: v < 0.40, "< 40%", 40),
]


def rule_key(rule: Rule) -> str:
    return rule.name.lower().replace(" ", "_")


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


def evaluate_day(row: dict) -> dict:
    """R5/R6: the login gate runs first (KTD2); the rule list only runs when it passes."""
    login_time = _parse_login(row.get("Login"))
    gate_open = _gate_open(login_time)

    result = {
        "login_target": LOGIN_TARGET_LABEL,
        "login_achieved": login_time.strftime("%H:%M") if login_time else None,
        "login_qualified": gate_open,
    }

    total_coins = 0
    for rule in RULES:
        key = rule_key(rule)
        value = rule.metric(row) if gate_open else None
        qualified = value is not None and rule.comparison(value) if gate_open else None
        if qualified:
            total_coins += rule.coins
        result[f"{key}_target"] = rule.target_label if gate_open else None
        result[f"{key}_achieved"] = value
        result[f"{key}_qualified"] = qualified
    result["total_coins"] = total_coins
    return result
