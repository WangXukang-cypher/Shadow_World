from app.normalization import memory_normalized_key, normalize_text


def test_normalize_text_is_deterministic():
    assert normalize_text("  我 喜欢吃！川菜。 ") == "我 喜欢川菜"
    assert memory_normalized_key("fact", "我", "喜欢吃川菜") == memory_normalized_key(
        "fact", "我", "喜欢川菜"
    )
