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

    # Test clear session
    deleted = store.clear_session("session_1")
    assert deleted == 2
    assert len(store.get_messages("session_1")) == 0


def test_routine_store_operations(tmp_path):
    db_file = tmp_path / "test_routines.db"
    store = MemoryStore(db_path=db_file)

    store.save_routine(
        name="daily-crypto",
        description="Monitora crypto",
        prompt_template="Preço do BTC",
        schedule_time="09:00",
        timezone="America/Sao_Paulo",
        chat_id="998877"
    )

    routine = store.get_routine("daily-crypto")
    assert routine is not None
    assert routine["name"] == "daily-crypto"
    assert routine["schedule_time"] == "09:00"
    assert routine["chat_id"] == "998877"
    assert routine["last_run"] is None

    store.update_routine_last_run("daily-crypto", "2026-09-16")
    updated = store.get_routine("daily-crypto")
    assert updated["last_run"] == "2026-09-16"

    routines = store.list_routines()
    assert len(routines) >= 1
    assert any(r["name"] == "daily-crypto" for r in routines)
