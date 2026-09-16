import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch
from zoneinfo import ZoneInfo
from src.routines.scheduler import RoutineScheduler
from src.memory.db import memory_store


@pytest.mark.anyio
async def test_routine_scheduler_triggers_matching_time(tmp_path, monkeypatch):
    # Usa banco temporário
    test_db = tmp_path / "test_scheduler.db"
    monkeypatch.setattr(memory_store, "db_path", test_db)
    memory_store.init_db()

    now_sp = datetime.now(ZoneInfo("America/Sao_Paulo"))
    current_time_str = now_sp.strftime("%H:%M")

    # Cadastra rotina agendada para o minuto atual
    memory_store.save_routine(
        name="euro-test-routine",
        description="Rotina de teste do euro",
        prompt_template="Enviar cotação do euro",
        schedule_time=current_time_str,
        chat_id="12345678"
    )

    scheduler = RoutineScheduler(check_interval_seconds=1)
    mock_bot = AsyncMock()
    scheduler.set_bot(mock_bot)

    # Mock da execução da rotina
    with patch("src.routines.manager.routine_manager.run_routine", return_value="Euro: R$ 5,95") as mock_run:
        await scheduler.check_and_run_scheduled_routines()

        # Verifica que a rotina rodou
        mock_run.assert_called_once_with("euro-test-routine", None)

        # Verifica que o last_run foi atualizado no banco
        routine = memory_store.get_routine("euro-test-routine")
        today_str = now_sp.strftime("%Y-%m-%d")
        assert routine["last_run"] == today_str

        # Se rodar novamente hoje, NÃO deve disparar de novo
        mock_run.reset_mock()
        await scheduler.check_and_run_scheduled_routines()
        mock_run.assert_not_called()
