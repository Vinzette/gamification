from coins import evaluate_day, login_qualifies


def row(TC=0, PC=0, LPC=0.0, OVC=0, Login=None):
    return {"TC": TC, "PC": PC, "LPC": LPC, "OVC": OVC, "Login": Login}


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


def test_boundary_lpc_exactly_6_does_not_qualify():
    result = evaluate_day(row(TC=20, PC=10, LPC=6.0, OVC=0, Login="09:00"))
    assert result["lpc_qualified"] is False


def test_boundary_ovc_rate_exactly_40_percent_does_not_qualify():
    result = evaluate_day(row(TC=10, PC=0, LPC=0, OVC=4, Login="09:00"))  # 4/10 = 40%
    assert result["ovc_rate_qualified"] is False


def test_boundary_login_exactly_10_00_qualifies():
    assert login_qualifies(row(TC=1, PC=0, LPC=0, OVC=0, Login="10:00")) is True


def test_missing_login_with_calls_fails_the_gate():
    result = evaluate_day(row(TC=20, PC=20, LPC=10, OVC=0, Login=None))
    assert result["login_qualified"] is False
    assert result["total_coins"] == 0
