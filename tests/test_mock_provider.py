from app.mock_provider import MockLLMProvider


def test_mock_provider_routes_memory():
    decision = MockLLMProvider().decide("记住我喜欢简短回答")
    assert decision.route == "create_memory"
    assert decision.argument == "我喜欢简短回答"


def test_mock_provider_clarifies_missing_time():
    decision = MockLLMProvider().decide("提醒我交周报")
    assert decision.route == "clarify_task_time"
