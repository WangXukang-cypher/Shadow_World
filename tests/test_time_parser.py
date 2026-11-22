from app.time_parser import parse_mock_reminder


def test_mock_parser_accepts_tomorrow_time():
    result = parse_mock_reminder("明天 10:00 交周报", "Asia/Shanghai")
    assert result is not None
    assert result.endswith("+00:00")


def test_mock_parser_rejects_missing_time():
    assert parse_mock_reminder("明天交周报", "Asia/Shanghai") is None
