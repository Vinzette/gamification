from coins import evaluate_day, login_qualifies


def row(
    TC=0, PC=0, LPC=0.0, OVC=0, Login=None,
    physical_pc=None, physical_lines_cut=None, physical_outlets=None,
):
    return {
        "TC": TC, "PC": PC, "LPC": LPC, "OVC": OVC, "Login": Login,
        "Physical PC": physical_pc,
        "Physical Lines Cut": physical_lines_cut,
        "Physical Outlets": physical_outlets,
    }


def test_ae1_full_qualifying_day():
    result = evaluate_day(row(TC=32, PC=18, LPC=7.2, OVC=2, Login="09:45"))
    assert result["login_qualified"] is True
    assert result["productive_calls_qualified"] is True
    assert result["lpc_qualified"] is True
    assert result["ovc_rate_qualified"] is True
    assert result["total_coins"] == 80


def test_ae2_late_login_zeroes_the_day():
    result = evaluate_day(row(TC=30, PC=20, LPC=8, OVC=1, Login="10:20"))
    assert result["login_qualified"] is False
    assert result["productive_calls_target"] is None
    assert result["productive_calls_achieved"] is None
    assert result["productive_calls_qualified"] is None
    assert result["lpc_target"] is None
    assert result["lpc_qualified"] is None
    assert result["ovc_rate_target"] is None
    assert result["ovc_rate_qualified"] is None
    assert result["total_coins"] == 0


def test_ae4_on_time_login_with_zero_calls():
    result = evaluate_day(row(TC=0, PC=0, LPC=0.0, OVC=0, Login="09:10"))
    assert result["login_qualified"] is True
    assert result["productive_calls_qualified"] is False
    assert result["lpc_qualified"] is False
    assert result["ovc_rate_qualified"] is False
    assert result["total_coins"] == 0


def test_boundary_pc_exactly_15_qualifies():
    result = evaluate_day(row(TC=20, PC=15, LPC=0, OVC=0, Login="09:00"))
    assert result["productive_calls_qualified"] is True


def test_boundary_lpc_exactly_6_qualifies():
    result = evaluate_day(row(TC=20, PC=10, LPC=6.0, OVC=0, Login="09:00"))
    assert result["lpc_qualified"] is True


def test_boundary_ovc_rate_exactly_40_percent_does_not_qualify():
    result = evaluate_day(row(TC=10, PC=0, LPC=0, OVC=4, Login="09:00"))  # 4/10 = 40%
    assert result["ovc_rate_qualified"] is False


def test_boundary_login_exactly_10_00_qualifies():
    assert login_qualifies(row(TC=1, PC=0, LPC=0, OVC=0, Login="10:00")) is True


def test_missing_login_with_calls_fails_the_gate():
    result = evaluate_day(row(TC=20, PC=20, LPC=10, OVC=0, Login=None))
    assert result["login_qualified"] is False
    assert result["total_coins"] == 0


def test_boundary_physical_lpc_exactly_6_qualifies():
    result = evaluate_day(row(
        TC=0, PC=0, LPC=0, OVC=0, Login="09:00",
        physical_pc=10, physical_lines_cut=60, physical_outlets=10,
    ))
    assert result["physical_lpc_qualified"] is True


def test_both_physical_rules_qualify_awards_bonus_not_sum():
    result = evaluate_day(row(
        TC=0, PC=0, LPC=0, OVC=0, Login="09:00",
        physical_pc=16, physical_lines_cut=112, physical_outlets=16,  # PC=16, LPC=7
    ))
    assert result["physical_pc_qualified"] is True
    assert result["physical_lpc_qualified"] is True
    assert result["total_coins"] == 110


def test_only_physical_pc_qualifies_no_bonus():
    result = evaluate_day(row(
        TC=0, PC=0, LPC=0, OVC=0, Login="09:00",
        physical_pc=16, physical_lines_cut=16, physical_outlets=16,  # LPC=1, below 6
    ))
    assert result["physical_pc_qualified"] is True
    assert result["physical_lpc_qualified"] is False
    assert result["total_coins"] == 40


def test_both_physical_rules_qualify_but_lpc_disabled_no_bonus():
    result = evaluate_day(
        row(
            TC=0, PC=0, LPC=0, OVC=0, Login="09:00",
            physical_pc=16, physical_lines_cut=112, physical_outlets=16,
        ),
        enabled_rules={"physical_pc"},
    )
    assert result["total_coins"] == 40


def test_uncovered_month_physical_fields_are_na():
    result = evaluate_day(row(TC=20, PC=20, LPC=10, OVC=0, Login="09:00"))
    assert result["physical_pc_target"] is None
    assert result["physical_pc_achieved"] is None
    assert result["physical_pc_qualified"] is None
    assert result["physical_lpc_qualified"] is None


def test_covered_month_zero_qualifying_visits_is_a_real_no_not_na():
    result = evaluate_day(row(
        TC=20, PC=20, LPC=10, OVC=0, Login="09:00",
        physical_pc=0, physical_lines_cut=0, physical_outlets=0,
    ))
    assert result["physical_pc_qualified"] is False
    assert result["physical_lpc_qualified"] is False


def test_late_login_gates_physical_rules_too():
    result = evaluate_day(row(
        TC=0, PC=0, LPC=0, OVC=0, Login="10:20",
        physical_pc=16, physical_lines_cut=112, physical_outlets=16,
    ))
    assert result["physical_pc_qualified"] is None
    assert result["physical_lpc_qualified"] is None
    assert result["total_coins"] == 0


def test_disabling_a_base_rule_keeps_its_columns_but_drops_its_coins():
    result = evaluate_day(
        row(TC=32, PC=18, LPC=7.2, OVC=2, Login="09:45"),
        enabled_rules={"lpc", "ovc_rate"},
    )
    assert result["productive_calls_qualified"] is True
    assert result["total_coins"] == 60
