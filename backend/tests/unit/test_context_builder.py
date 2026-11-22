from app.agent.context import TokenBudget, TokenEstimator


def test_token_budget_reserves_output_and_sections_are_bounded():
    budget = TokenBudget(context_window=1000)
    assert budget.input_budget == 800
    assert budget.section_budget(budget.recent_messages_ratio) == 280
    assert budget.section_budget(budget.memories_ratio) == 80


def test_token_estimator_counts_chinese_more_densely_than_ascii():
    estimator = TokenEstimator()
    assert estimator.estimate("abcd") == 1
    assert estimator.estimate("你好世界") == 4
