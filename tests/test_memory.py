from src.memory.db import MemoryStore


def test_memory_store_operations(tmp_path):
    db_file = tmp_path / "test_memory.db"
    store = MemoryStore(db_path=db_file)

    # Test set and get
    store.set_memory("client_rule", "acme_corp", {"billing": "annual", "approver": "Dana"})
    data = store.get_memory("client_rule", "acme_corp")
    assert data == {"billing": "annual", "approver": "Dana"}

    # Test list
    mems = store.list_memories("client_rule")
    assert len(mems) == 1
    assert mems[0]["key"] == "acme_corp"

    # Test messages history
    store.add_message("session_1", "user", "Hello bot")
    store.add_message("session_1", "assistant", "Hello! How can I help?", agent_name="Chief of Staff")
    history = store.get_messages("session_1")
    assert len(history) == 2
    assert history[0]["content"] == "Hello bot"
    assert history[1]["agent_name"] == "Chief of Staff"
