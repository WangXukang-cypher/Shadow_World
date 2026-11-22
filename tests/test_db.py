from app.db import DEFAULT_USER_ID, Database


def test_messages_use_strict_sequence(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.initialize()
    conversation = db.create_conversation(DEFAULT_USER_ID)
    first = db.add_message(conversation["id"], DEFAULT_USER_ID, "user", "one")
    second = db.add_message(conversation["id"], DEFAULT_USER_ID, "assistant", "two")
    assert (first["seq"], second["seq"]) == (1, 2)
    assert [item["content"] for item in db.list_messages(conversation["id"], DEFAULT_USER_ID)] == [
        "one",
        "two",
    ]


def test_memory_is_deduplicated_by_normalized_key(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.initialize()
    one = db.create_memory(DEFAULT_USER_ID, "喜欢吃川菜")
    two = db.create_memory(DEFAULT_USER_ID, "喜欢川菜")
    assert one["id"] == two["id"]
    assert len(db.list_memories(DEFAULT_USER_ID)) == 1


class _ClosableConnection:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def test_readonly_context_always_closes_connection(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    connection = _ClosableConnection()
    db.connect = lambda: connection  # type: ignore[method-assign]
    with db.readonly() as opened:
        assert opened is connection
    assert connection.closed is True
