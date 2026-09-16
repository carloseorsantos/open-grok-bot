import asyncio
import html
import logging
import re
import time
from pathlib import Path
from telegram import Update
from telegram.constants import ChatAction
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
from src.tools.image import generate_image

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger("OpenGrokBot.Telegram")


def format_for_telegram(text: str) -> str:
    """
    Converte markdown comum do LLM em HTML seguro e compatível com o Telegram.
    Transforma **negrito**, *itálico*, `código` e ```blocos``` em tags HTML.
    """
    # 1. Escapar caracteres HTML básicos
    text = html.escape(text)

    # 2. Blocos de código ```...``` -> <pre>...</pre>
    text = re.sub(r"```([a-zA-Z0-9_-]*)\n?(.*?)```", r"<pre>\2</pre>", text, flags=re.DOTALL)

    # 3. Código inline `...` -> <code>...</code>
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)

    # 4. Negrito **...** -> <b>...</b>
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)

    # 5. Itálico *...* ou _..._ -> <i>...</i>
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"(?<!_)_([^_]+)_(?!_)", r"<i>\1</i>", text)

    return text


async def send_clean_reply(update: Update, text: str):
    """Envia a mensagem formatada em HTML com fallback para texto simples."""
    # Quebrar mensagens muito longas em blocos de até 3800 caracteres
    chunks = []
    remaining = text
    while len(remaining) > 3800:
        split_idx = remaining.rfind("\n", 0, 3800)
        if split_idx == -1:
            split_idx = 3800
        chunks.append(remaining[:split_idx])
        remaining = remaining[split_idx:].strip()
    if remaining:
        chunks.append(remaining)

    for chunk in chunks:
        html_chunk = format_for_telegram(chunk)
        try:
            await update.message.reply_html(html_chunk)
        except Exception as e:
            logger.warning(f"Erro ao enviar mensagem em HTML ({e}), enviando como texto simples.")
            # Envia o chunk original não-escapado como fallback seguro
            await update.message.reply_text(chunk)


def is_authorized(user_id: int) -> bool:
    allowed = settings.allowed_telegram_ids
    if not allowed:
        return True
    return user_id in allowed


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("⛔ Acesso não autorizado a este Open Grok Bot.")
        return

    msg = (
        "🤖 <b>Open Grok Bot</b> — Seus AI Teammates Gratuitos!\n\n"
        "Comandos disponíveis:\n"
        "• <code>/imagine &lt;prompt&gt;</code> — Gerar imagem com Flux.1\n"
        "• <code>/routines</code> — Ver rotinas de automação\n"
        "• <code>/run &lt;nome&gt;</code> — Executar uma rotina\n"
        "• <code>/delroutine &lt;nome&gt;</code> — Remover uma rotina\n"
        "• <code>/memory</code> — Ver memórias salvas\n"
        "• <code>/files</code> — Ver arquivos no workspace\n"
        "• <code>/reset</code> ou <code>/clear</code> — Limpar histórico da conversa\n\n"
        "💡 <i>Ou envie qualquer tarefa, pergunta ou arquivo em linguagem natural!</i>"
    )
    await update.message.reply_html(msg)


async def imagine_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Uso: /imagine <descreva a imagem que deseja gerar>")
        return

    prompt = " ".join(context.args)
    status_msg = await update.message.reply_text(f"🎨 Gerando imagem com Flux.1...\n<i>\"{prompt}\"</i>", parse_mode="HTML")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO)

    start_time = time.time()
    result = await asyncio.to_thread(generate_image, prompt)

    # Procura imagem gerada no workspace
    recent_images = [
        f for f in settings.WORKSPACE_DIR.glob("*")
        if f.suffix.lower() in (".jpg", ".jpeg", ".png") and f.stat().st_mtime >= start_time - 2
    ]

    try:
        await status_msg.delete()
    except Exception:
        pass

    if recent_images:
        latest = max(recent_images, key=lambda f: f.stat().st_mtime)
        with open(latest, "rb") as photo:
            await update.message.reply_photo(photo=photo, caption=f"🎨 <b>Flux.1:</b> {prompt[:200]}", parse_mode="HTML")
    else:
        await send_clean_reply(update, result)


async def routines_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    routines = routine_manager.list_routines()
    lines = ["📋 <b>Rotinas de Automação Salvas:</b>\n"]
    for r in routines:
        lines.append(f"• <code>{r['name']}</code>: {r['description']}")
    lines.append("\nPara executar: <code>/run &lt;nome&gt;</code>")
    await update.message.reply_html("\n".join(lines))


async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Uso: /run <nome_da_rotina> [chave=valor ...]")
        return

    routine_name = context.args[0]
    params = {}
    for arg in context.args[1:]:
        if "=" in arg:
            k, v = arg.split("=", 1)
            params[k.strip()] = v.strip()

    status_msg = await update.message.reply_text(f"⏳ Executando rotina '{routine_name}'...")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    result = await asyncio.to_thread(routine_manager.run_routine, routine_name, params if params else None)

    try:
        await status_msg.delete()
    except Exception:
        pass

    await send_clean_reply(update, result)


async def delroutine_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Uso: /delroutine <nome_da_rotina>")
        return
    routine_name = context.args[0]
    result = routine_manager.delete_routine(routine_name)
    await update.message.reply_text(result)


async def memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    mems = memory_store.list_memories()
    if not mems:
        await update.message.reply_text("Nenhuma memória registrada ainda.")
        return
    lines = ["🧠 <b>Memórias Compartilhadas:</b>\n"]
    for m in mems:
        lines.append(f"• <b>[{m['category']}]</b> <code>{m['key']}</code>: {m['value']}")
    await update.message.reply_html("\n".join(lines))


async def files_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    output = list_workspace_files()
    await update.message.reply_text(output)


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return
    session_id = f"telegram_{user_id}"
    deleted = memory_store.clear_session(session_id)
    await update.message.reply_html(
        f"🧹 <b>Sessão reiniciada!</b> {deleted} mensagens anteriores foram limpas.\n"
        "Podemos começar um novo assunto do zero."
    )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return

    doc = update.message.document
    if not doc:
        return

    file_name = doc.file_name or f"upload_{int(time.time())}.dat"
    save_path = settings.WORKSPACE_DIR / file_name

    status_msg = await update.message.reply_text(f"📥 Recebendo arquivo '{file_name}'...")
    try:
        new_file = await context.bot.get_file(doc.file_id)
        await new_file.download_to_drive(custom_path=str(save_path))

        await status_msg.edit_text(f"⏳ Chief of Staff analisando '{file_name}'...")
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

        caption = update.message.caption or "Analise o arquivo anexado e resuma seus pontos principais."
        task = f"[Arquivo salvo no workspace: {file_name}]\n{caption}"

        session_id = f"telegram_{user_id}"
        response = await asyncio.to_thread(chief_of_staff.run, task, session_id)

        try:
            await status_msg.delete()
        except Exception:
            pass

        await send_clean_reply(update, response)

    except Exception as e:
        logger.error(f"Erro ao processar documento: {e}")
        await status_msg.edit_text(f"❌ Erro ao baixar ou processar arquivo: {str(e)}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return

    text = update.message.text
    if not text:
        return

    status_msg = await update.message.reply_text("⏳ Chief of Staff coordenando os bots...")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    start_time = time.time()
    session_id = f"telegram_{user_id}"
    response = await asyncio.to_thread(chief_of_staff.run, text, session_id)

    try:
        await status_msg.delete()
    except Exception:
        pass

    # Verificar se foi gerada alguma imagem ou screenshot durante a tarefa
    candidate_dirs = [settings.SCREENSHOTS_DIR, settings.WORKSPACE_DIR]
    recent_images = []
    for d in candidate_dirs:
        for f in d.glob("*"):
            if f.suffix.lower() in (".png", ".jpg", ".jpeg"):
                try:
                    if f.stat().st_mtime >= start_time - 1:
                        recent_images.append(f)
                except Exception:
                    pass

    if recent_images:
        latest = max(recent_images, key=lambda f: f.stat().st_mtime)
        try:
            with open(latest, "rb") as photo:
                caption = "📸 Captura de tela" if latest.parent == settings.SCREENSHOTS_DIR else f"🎨 Imagem gerada: {latest.name}"
                await update.message.reply_photo(photo=photo, caption=caption)
        except Exception as e:
            logger.warning(f"Erro ao enviar imagem gerada: {e}")

    # Envia resposta de texto formatada
    await send_clean_reply(update, response)


def run_telegram_bot():
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN não encontrado no arquivo .env.")
        return

    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", start_command))
    app.add_handler(CommandHandler("imagine", imagine_command))
    app.add_handler(CommandHandler("routines", routines_command))
    app.add_handler(CommandHandler("run", run_command))
    app.add_handler(CommandHandler("delroutine", delroutine_command))
    app.add_handler(CommandHandler("memory", memory_command))
    app.add_handler(CommandHandler("files", files_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CommandHandler("clear", reset_command))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 Open Grok Bot no Telegram iniciado com sucesso!")
    app.run_polling()


if __name__ == "__main__":
    run_telegram_bot()
