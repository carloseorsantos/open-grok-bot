import asyncio
import logging
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo
from src.memory.db import memory_store
from src.routines.manager import routine_manager

logger = logging.getLogger("OpenGrokBot.Scheduler")


class RoutineScheduler:
    """
    Motor de agendamento em segundo plano para rotinas salvas.
    Verifica rotinas com `schedule_time` e dispara a execução no fuso horário
    configurado (padrão: America/Sao_Paulo / UTC-3), enviando o resultado para o Telegram via chat_id.
    """
    def __init__(self, check_interval_seconds: int = 30):
        self.check_interval = check_interval_seconds
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.bot = None

    def set_bot(self, bot):
        """Configura a instância do Telegram Bot para envio de mensagens proativas."""
        self.bot = bot

    async def start(self, bot=None):
        if bot:
            self.set_bot(bot)
        if self.running:
            return
        self.running = True
        self.task = asyncio.create_task(self._loop())
        logger.info("⏰ Motor de agendamento de rotinas iniciado (America/Sao_Paulo).")

    def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
        logger.info("⏰ Motor de agendamento de rotinas finalizado.")

    async def _loop(self):
        while self.running:
            try:
                await self.check_and_run_scheduled_routines()
            except Exception as e:
                logger.error(f"Erro no ciclo do agendador de rotinas: {e}")
            await asyncio.sleep(self.check_interval)

    async def check_and_run_scheduled_routines(self):
        routines = memory_store.list_routines()
        for routine in routines:
            if not routine.get("enabled"):
                continue
            sched_time = routine.get("schedule_time")
            if not sched_time:
                continue

            tz_name = routine.get("timezone") or "America/Sao_Paulo"
            try:
                tz = ZoneInfo(tz_name)
            except Exception:
                tz = ZoneInfo("America/Sao_Paulo")

            now = datetime.now(tz)
            current_hm = now.strftime("%H:%M")
            today_str = now.strftime("%Y-%m-%d")

            # Verifica se o horário atual bate com o agendamento e se ainda não rodou hoje
            if current_hm == sched_time and routine.get("last_run") != today_str:
                routine_name = routine["name"]
                logger.info(f"⏰ Disparando rotina agendada '{routine_name}' às {current_hm} ({tz_name})...")
                
                # Marca como executada hoje imediatamente para evitar duplicidade
                memory_store.update_routine_last_run(routine_name, today_str)

                # Executa em thread separada para não travar o loop assíncrono
                try:
                    result = await asyncio.to_thread(routine_manager.run_routine, routine_name, None)
                    logger.info(f"✅ Rotina '{routine_name}' executada com sucesso.")

                    chat_id = routine.get("chat_id")
                    if chat_id and self.bot:
                        from src.interfaces.telegram_bot import send_clean_reply
                        header = f"⏰ <b>Rotina Automática: {routine_name}</b>\n<i>Executada às {current_hm}</i>\n\n"
                        await send_clean_reply(
                            update=None,
                            text=header + result,
                            bot_instance=self.bot,
                            chat_id=int(chat_id)
                        )
                except Exception as err:
                    logger.error(f"❌ Erro ao executar rotina agendada '{routine_name}': {err}")


routine_scheduler = RoutineScheduler()
