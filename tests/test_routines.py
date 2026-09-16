from src.memory.db import MemoryStore
from src.routines.manager import RoutineManager


def test_routine_manager(tmp_path, monkeypatch):
    db_file = tmp_path / "test_routines.db"
    store = MemoryStore(db_path=db_file)
    monkeypatch.setattr("src.routines.manager.memory_store", store)

    mgr = RoutineManager()
    mgr.create_routine(
        name="custom-check",
        description="Rotina de teste",
        prompt_template="Analisar a empresa {company}"
    )

    routines = mgr.list_routines()
    names = [r["name"] for r in routines]
    assert "custom-check" in names

    # Test delete routine
    del_msg = mgr.delete_routine("custom-check")
    assert "sucesso" in del_msg
    routines_after = mgr.list_routines()
    assert "custom-check" not in [r["name"] for r in routines_after]

