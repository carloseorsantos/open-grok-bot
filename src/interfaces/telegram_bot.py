import asyncio
import logging
from pathlib import Path
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)
from src.config import settings
from src.agents.orchestrator import chief_of_staff
from src.routines.manager import routine_manager
from src.memory.db import memory_store
from src.tools.filesystem import list_workspace_files

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger("OpenGrokBot.Telegram")


def is_authorized(user_id: int) -> bool:
    allowed = settings.allowed_telegram_ids
    if not allowed:
        return True # Se não configurou lista, permite quem enviar
    return user_id in allowed


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("⛔ Acesso não autorizado a este Open Grok Bot.")
        return

    msg = (
        "🤖 *Bem-vindo ao Open Grok Bot!*\n\n"
        "Seu time de AI Teammates está online e pronto para executar tarefas.\n\n"
        "Comandos disponíveis:\n"
        "• `/routines` - Ver rotinas de automação\n"
        "• `/run <nome>` - Executar uma rotina\n"
        "• `/memory` - Ver memórias salvas\n"
        "• `/files` - Ver arquivos no workspace\n\n"
        "Ou simplesmente me envie qualquer tarefa em linguagem natural!"
    )
    await update.message.reply_markdown(msg)


async def routines_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    routines = routine_manager.list_routines()
    lines = ["📋 *Rotinas Salvas:*\n"]
    for r in routines:
        lines.append(f"• `{r['name']}`: {r['description']}")
    await update.message.reply_markdown("\n".join(lines))


async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Uso: /run <nome_da_rotina>")
        return
    routine_name = context.args[0]
    await update.message.reply_text(f"⏳ Executando rotina '{routine_name}'...")
    result = await asyncio.to_thread(routine_manager.run_routine, routine_name)
    await update.message.reply_text(result[:4000])


async def memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    mems = memory_store.list_memories()
    if not mems:
        await update.message.reply_text("Nenhuma memória registrada ainda.")
        return
    lines = ["🧠 *Memórias Compartilhadas:*\n"]
    for m in mems:
        lines.append(f"• *[{m['category']}]* `{m['key']}`: {m['value']}")
    await update.message.reply_markdown("\n".join(lines))


async def files_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    output = list_workspace_files()
    await update.message.reply_text(output)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return

    text = update.message.text
    if not text:
        return

    await update.message.reply_text("⏳ Chief of Staff coordenando os bots...")
    session_id = f"telegram_{user_id}"
    response = await asyncio.to_thread(chief_of_staff.run, text, session_id)

    # Verificar se foi gerada alguma captura recente para enviar
    recent_shots = list(settings.SCREENSHOTS_DIR.glob("*.png"))
    if recent_shots:
        latest = max(recent_shots, key=lambda f: f.stat().st_mtime)
        # Se foi gerado nos últimos 30 segundos
        import time
        if time.time() - latest.stat().st_mtime < 30:
            with open(latest, "rb") as photo:
                await update.message.reply_photo(photo=photo, caption="📸 Captura de tela realizada durante a tarefa.")

    # Envia resposta de texto
    await update.message.reply_text(response[:4000])


def run_telegram_bot():
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN não encontrado no arquivo .env.")
        print("Obtenha um token grátis falando com o @BotFather no Telegram e adicione ao .env.")
        return

    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", start_command))
    app.add_handler(CommandHandler("routines", routines_command))
    app.add_handler(CommandHandler("run", run_command))
    app.add_handler(CommandHandler("memory", memory_command))
    app.add_handler(CommandHandler("files", files_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 Open Grok Bot no Telegram iniciado com sucesso!")
    app.run_polling()


if __name__ == "__main__":
    run_telegram_bot()
