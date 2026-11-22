from app.agent.normalization import memory_normalized_key, normalize_text


def test_normalization_is_deterministic():
    assert normalize_text(" 我喜欢吃！川菜。") == "我喜欢川菜"
    assert memory_normalized_key("fact", "我", "喜欢吃川菜") == memory_normalized_key(
        "fact", "我", "喜欢川菜"
    )
