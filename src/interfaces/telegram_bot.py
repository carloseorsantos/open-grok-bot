import asyncio
import contextlib
import html
import logging
import re
import time
from pathlib import Path
from typing import Optional

from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update
)
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

from src.config import settings
from src.agents.orchestrator import chief_of_staff
from src.routines.manager import routine_manager
from src.routines.scheduler import routine_scheduler
from src.memory.db import memory_store
from src.tools.filesystem import list_workspace_files
from src.tools.image import generate_image
from src.tools.audio import transcribe_audio
from src.llm.rate_limiter import rate_limiter

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger("OpenGrokBot.Telegram")


@contextlib.asynccontextmanager
async def persistent_typing(bot, chat_id: int, action: str = ChatAction.TYPING, interval: float = 4.0):
    """
    Mantém o indicador de ação (digitando/gravando áudio) ativo continuamente.
    O Telegram descarta o ChatAction após 5 segundos; este loop renova a cada 4s até a conclusão.
    """
    stop_event = asyncio.Event()

    async def _heartbeat():
        while not stop_event.is_set():
            try:
                await bot.send_chat_action(chat_id=chat_id, action=action)
            except Exception:
                pass
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass

    task = asyncio.create_task(_heartbeat())
    try:
        yield
    finally:
        stop_event.set()
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


def convert_tables_to_cards(text: str) -> str:
    """
    Converte tabelas markdown com barras (| col1 | col2 |) em cartões verticais em tópicos.
    Evita que tabelas quebrem e fiquem ilegíveis na tela de smartphones.
    """
    lines = text.split("\n")
    in_table = False
    headers = []
    output_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2:
            parts = [p.strip() for p in stripped[1:-1].split("|")]
            # Linha separadora (| --- | --- |)
            if all(set(p).issubset({"-", ":", " "}) for p in parts if p):
                in_table = True
                continue
            if not in_table:
                headers = parts
                in_table = True
            else:
                card = []
                for i, val in enumerate(parts):
                    if i < len(headers) and headers[i]:
                        card.append(f"• <b>{headers[i]}:</b> {val}")
                    else:
                        card.append(f"• {val}")
                output_lines.append("\n".join(card))
                output_lines.append("")
        else:
            if in_table:
                in_table = False
                headers = []
            output_lines.append(line)

    return "\n".join(output_lines)


def format_for_telegram(text: str) -> str:
    """
    Converte markdown comum em HTML seguro e compatível com a Telegram Bot API.
    Processa títulos (#, ##, ###), blocos de código, inline code, negrito, itálico, links e blockquotes.
    """
    # 0. Converter tabelas markdown em cartões amigáveis para mobile
    text = convert_tables_to_cards(text)

    # 1. Proteger blocos de código ```linguagem\nconteúdo```
    code_blocks = []
    def _save_code_block(match):
        code_blocks.append(match.group(2))
        return f"§§§CODEBLOCK{len(code_blocks)-1}§§§"

    text = re.sub(r"```([a-zA-Z0-9_-]*)\n?(.*?)```", _save_code_block, text, flags=re.DOTALL)

    # 2. Proteger código inline `código`
    inline_codes = []
    def _save_inline_code(match):
        inline_codes.append(match.group(1))
        return f"§§§INLINECODE{len(inline_codes)-1}§§§"

    text = re.sub(r"`([^`]+)`", _save_inline_code, text)

    # 3. Proteger links markdown [texto](url)
    links = []
    def _save_link(match):
        links.append((match.group(1), match.group(2)))
        return f"§§§LINK{len(links)-1}§§§"

    text = re.sub(r"\[([^\]]+)\]\((https?://[^\s\)]+)\)", _save_link, text)

    # 4. Escapar caracteres HTML no texto
    text = html.escape(text)

    # 5. Converter cabeçalhos markdown e divisórias após escape para tags <b> válidas
    text = re.sub(r"^####\s+(.+)$", r"<b>• \1</b>", text, flags=re.MULTILINE)
    text = re.sub(r"^###\s+(.+)$", r"<b>▪️ \1</b>", text, flags=re.MULTILINE)
    text = re.sub(r"^##\s+(.+)$", r"<b>🔹 \1</b>", text, flags=re.MULTILINE)
    text = re.sub(r"^#\s+(.+)$", r"<b>📌 \1</b>", text, flags=re.MULTILINE)
    text = re.sub(r"^(?:---|\*\*\*|___)\s*$", "— — —", text, flags=re.MULTILINE)

    # 6. Citações markdown (> citação, que virou &gt;) -> <blockquote>citação</blockquote>
    text = re.sub(r"^&gt;\s*(.+)$", r"<blockquote>\1</blockquote>", text, flags=re.MULTILINE)

    # 7. Negrito **...** -> <b>...</b>
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)

    # 8. Itálico *...* ou _..._ -> <i>...</i>
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"(?<![a-zA-Z0-9_])_([^_]+)_(?![a-zA-Z0-9_])", r"<i>\1</i>", text)

    # 9. Restaurar links com tags HTML válidas
    for i, (l_text, l_url) in enumerate(links):
        safe_l_text = html.escape(l_text)
        safe_l_url = html.escape(l_url)
        text = text.replace(f"§§§LINK{i}§§§", f'<a href="{safe_l_url}">{safe_l_text}</a>')

    # 10. Restaurar código inline e blocos de código escapados
    for i, code in enumerate(inline_codes):
        text = text.replace(f"§§§INLINECODE{i}§§§", f"<code>{html.escape(code)}</code>")

    for i, block in enumerate(code_blocks):
        text = text.replace(f"§§§CODEBLOCK{i}§§§", f"<pre>{html.escape(block)}</pre>")

    return text


def balance_html_tags(text: str) -> str:
    """
    Garante que todas as tags HTML suportadas pelo Telegram que foram abertas
    sejam devidamente fechadas no final da string, evitando erros de parse entities.
    """
    supported_tags = ["b", "strong", "i", "em", "code", "pre", "blockquote", "s", "u", "a"]
    tag_pattern = re.compile(r"<\s*(/)?\s*([a-zA-Z0-9_-]+)(?:\s+[^>]*)?>")
    stack = []

    for match in tag_pattern.finditer(text):
        is_closing, tag_name = match.group(1), match.group(2).lower()
        if tag_name not in supported_tags:
            continue
        if not is_closing:
            stack.append(tag_name)
        else:
            if stack and stack[-1] == tag_name:
                stack.pop()
            elif tag_name in stack:
                while stack and stack[-1] != tag_name:
                    stack.pop()
                if stack:
                    stack.pop()

    # Fecha as tags restantes na ordem inversa
    for tag in reversed(stack):
        text += f"</{tag}>"

    return text


def clean_text_fallback(text: str) -> str:
    """
    Remove tags HTML e converte markdown em texto limpo com emojis para fallback elegante,
    garantindo que o usuário nunca veja markdown cru (.md quebrado com asteriscos).
    """
    clean = re.sub(r"<[^>]+>", "", text)
    clean = re.sub(r"^#{1,6}\s*(.+)$", r"📌 \1", clean, flags=re.MULTILINE)
    clean = re.sub(r"\*\*([^*]+)\*\*", r"\1", clean)
    clean = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", clean)
    clean = re.sub(r"\[([^\]]+)\]\((https?://[^\s\)]+)\)", r"\1 (\2)", clean)
    return clean.strip()


def get_quick_actions_keyboard() -> InlineKeyboardMarkup:
    """Retorna teclado de ações rápidas para enriquecer a experiência mobile."""
    keyboard = [
        [
            InlineKeyboardButton("🎨 Gerar Imagem", callback_data="quick:imagine"),
            InlineKeyboardButton("📋 Minhas Rotinas", callback_data="quick:routines"),
        ],
        [
            InlineKeyboardButton("⚡ Status do Bot", callback_data="quick:status"),
            InlineKeyboardButton("🧹 Nova Conversa", callback_data="quick:reset"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def send_clean_reply(
    update: Optional[Update] = None,
    text: str = "",
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    bot_instance=None,
    chat_id: Optional[int] = None
):
    """
    Envia mensagem formatada em HTML com suporte a chunks, auto-fechamento de tags,
    e fallback elegante que nunca exibe markdown cru.
    """
    msg_target = None
    if update:
        msg_target = update.message or (update.callback_query.message if update.callback_query else None)

    if not msg_target and not (bot_instance and chat_id):
        logger.warning("send_clean_reply chamado sem destinatário válido.")
        return

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

    total_chunks = len(chunks)
    for idx, chunk in enumerate(chunks):
        html_chunk = balance_html_tags(format_for_telegram(chunk))
        current_markup = reply_markup if (idx == total_chunks - 1) else None

        try:
            if msg_target:
                await msg_target.reply_html(html_chunk, reply_markup=current_markup, disable_web_page_preview=True)
            else:
                await bot_instance.send_message(
                    chat_id=chat_id,
                    text=html_chunk,
                    parse_mode="HTML",
                    reply_markup=current_markup,
                    disable_web_page_preview=True
                )
        except Exception as e:
            logger.warning(f"Erro ao enviar mensagem em HTML ({e}), usando fallback limpo sem .md cru.")
            fallback_text = clean_text_fallback(chunk)
            try:
                if msg_target:
                    await msg_target.reply_text(fallback_text, reply_markup=current_markup)
                else:
                    await bot_instance.send_message(chat_id=chat_id, text=fallback_text, reply_markup=current_markup)
            except Exception as err:
                logger.error(f"Falha definitiva ao enviar mensagem: {err}")


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
        "• <code>/routines</code> — Ver rotinas de automação salvas\n"
        "• <code>/run &lt;nome&gt;</code> — Executar uma rotina\n"
        "• <code>/status</code> — Status do sistema e cota Groq\n"
        "• <code>/memory</code> — Ver memórias compartilhadas\n"
        "• <code>/files</code> — Ver arquivos no workspace\n"
        "• <code>/reset</code> — Limpar histórico da conversa\n\n"
        "⏰ <b>Automações Agendadas:</b> Peça <i>'me envie a cotação do euro todo dia às 10h'</i> e o bot enviará pontualmente!\n"
        "🎙️ <b>Voz:</b> Envie notas de voz e o bot responde diretamente!\n"
        "💡 <i>Ou digite qualquer pergunta ou tarefa em linguagem natural.</i>"
    )
    await update.message.reply_html(msg, reply_markup=get_quick_actions_keyboard())


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return

    mems = memory_store.list_memories()
    routines = memory_store.list_routines()
    workspace_files = list(settings.WORKSPACE_DIR.glob("*"))

    limits = rate_limiter.current_limits
    rem_tokens = limits.get("remaining_tokens", "N/A")
    limit_tokens = limits.get("limit_tokens", "8000")
    reset_sec = limits.get("reset_tokens", 0)

    sched_routines = [r for r in routines if r.get("schedule_time")]

    msg = (
        "⚡ <b>Open Grok Bot — Status do Sistema</b>\n\n"
        f"🤖 <b>Modelo Principal:</b> <code>{settings.GROQ_MODEL}</code>\n"
        f"🎙️ <b>Voz & Transcrição:</b> <code>{settings.GROQ_WHISPER_MODEL}</code>\n"
        f"🎨 <b>Gerador de Imagens:</b> <code>Flux.1 (Pollinations)</code>\n"
        f"⏰ <b>Agendador em Background:</b> <code>Ativo ({len(sched_routines)} rotinas agendadas)</code>\n"
        f"🧠 <b>Memórias Salvas:</b> {len(mems)}\n"
        f"📋 <b>Rotinas Totais:</b> {len(routines)}\n"
        f"📂 <b>Arquivos no Workspace:</b> {len(workspace_files)}\n\n"
        "📊 <b>Quota Groq (Rate Limit):</b>\n"
        f"• Tokens restantes: <code>{rem_tokens} / {limit_tokens} TPM</code>\n"
        f"• Janela de reset: <code>{reset_sec:.1f}s</code>\n\n"
        "🟢 <b>Status:</b> Operacional e 100% Gratuito ($0.00)"
    )
    reply_target = update.message or (update.callback_query.message if update.callback_query else None)
    if reply_target:
        await reply_target.reply_html(msg, reply_markup=get_quick_actions_keyboard())


async def imagine_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Uso: /imagine <descreva a imagem que deseja gerar>")
        return

    prompt = " ".join(context.args)
    status_msg = await update.message.reply_text(f"🎨 Gerando imagem com Flux.1...\n<i>\"{prompt}\"</i>", parse_mode="HTML")

    start_time = time.time()
    async with persistent_typing(context.bot, update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO):
        result = await asyncio.to_thread(generate_image, prompt)

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
        await send_clean_reply(update, result, reply_markup=get_quick_actions_keyboard())


async def routines_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return

    routines = routine_manager.list_routines()
    lines = ["📋 <b>Rotinas de Automação Salvas:</b>\n"]
    keyboard = []

    if not routines:
        lines.append("<i>Nenhuma rotina salva ainda. Diga 'me envie a cotação do euro todo dia às 10h' para criar!</i>")
    else:
        for r in routines:
            sched = f" [⏰ {r.get('schedule_time')}]" if r.get('schedule_time') else ""
            lines.append(f"• <b>{r['name']}</b>{sched}: {r['description']}")
            keyboard.append([
                InlineKeyboardButton(f"▶️ Executar {r['name']}", callback_data=f"run_routine:{r['name']}")
            ])

    keyboard.append([
        InlineKeyboardButton("🎨 Gerar Imagem", callback_data="quick:imagine"),
        InlineKeyboardButton("⚡ Status do Bot", callback_data="quick:status")
    ])

    reply_target = update.message or (update.callback_query.message if update.callback_query else None)
    if reply_target:
        await reply_target.reply_html("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard))


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
    async with persistent_typing(context.bot, update.effective_chat.id, action=ChatAction.TYPING):
        result = await asyncio.to_thread(routine_manager.run_routine, routine_name, params if params else None)

    try:
        await status_msg.delete()
    except Exception:
        pass

    await send_clean_reply(update, result, reply_markup=get_quick_actions_keyboard())


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
    reply_target = update.message or (update.callback_query.message if update.callback_query else None)
    if reply_target:
        await reply_target.reply_html(
            f"🧹 <b>Sessão reiniciada!</b> {deleted} mensagens anteriores foram limpas.\n"
            "Podemos começar um novo assunto do zero.",
            reply_markup=get_quick_actions_keyboard()
        )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa mensagens de voz e arquivos de áudio, transcreve com Groq Whisper e executa no Chief of Staff."""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return

    voice = update.message.voice or update.message.audio
    if not voice:
        return

    chat_id = update.effective_chat.id
    status_msg = await update.message.reply_text("🎙️ <i>Baixando áudio...</i>", parse_mode="HTML")

    ext = ".ogg" if update.message.voice else ".mp3"
    temp_filename = f"voice_{int(time.time())}_{user_id}{ext}"
    audio_path = settings.WORKSPACE_DIR / temp_filename

    try:
        async with persistent_typing(context.bot, chat_id, action=ChatAction.RECORD_VOICE):
            file_obj = await context.bot.get_file(voice.file_id)
            await file_obj.download_to_drive(custom_path=str(audio_path))

        await status_msg.edit_text("🎧 <i>Transcrevendo com Groq Whisper Turbo...</i>", parse_mode="HTML")
        transcription = await asyncio.to_thread(transcribe_audio, str(audio_path), "pt")

        if not transcription or transcription.startswith("Erro:"):
            await status_msg.edit_text(f"❌ Falha ao transcrever áudio:\n<code>{transcription}</code>", parse_mode="HTML")
            return

        escaped_transcription = html.escape(transcription)
        await status_msg.edit_text(
            f"🎙️ <b>Você disse:</b>\n<i>\"{escaped_transcription}\"</i>\n\n"
            f"⏳ <i>Chief of Staff processando...</i>",
            parse_mode="HTML"
        )

        start_time = time.time()
        session_id = f"telegram_{user_id}"
        async with persistent_typing(context.bot, chat_id, action=ChatAction.TYPING):
            response = await asyncio.to_thread(chief_of_staff.run, transcription, session_id)

        try:
            await status_msg.delete()
        except Exception:
            pass

        # Verifica imagens geradas durante o processamento
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

        await send_clean_reply(update, response, reply_markup=get_quick_actions_keyboard())

    except Exception as e:
        logger.error(f"Erro ao processar mensagem de áudio: {e}")
        await status_msg.edit_text(f"❌ Erro ao processar áudio: {str(e)}")


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
        caption = update.message.caption or "Analise o arquivo anexado e resuma seus pontos principais."
        task = f"[Arquivo salvo no workspace: {file_name}]\n{caption}"

        session_id = f"telegram_{user_id}"
        async with persistent_typing(context.bot, update.effective_chat.id, action=ChatAction.TYPING):
            response = await asyncio.to_thread(chief_of_staff.run, task, session_id)

        try:
            await status_msg.delete()
        except Exception:
            pass

        await send_clean_reply(update, response, reply_markup=get_quick_actions_keyboard())

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

    start_time = time.time()
    session_id = f"telegram_{user_id}"
    async with persistent_typing(context.bot, update.effective_chat.id, action=ChatAction.TYPING):
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

    # Envia resposta de texto formatada com ações rápidas
    await send_clean_reply(update, response, reply_markup=get_quick_actions_keyboard())


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gerencia cliques nos botões inline e executa as ações em tempo real."""
    query = update.callback_query
    if not query:
        return

    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await query.answer("⛔ Acesso não autorizado.", show_alert=True)
        return

    await query.answer()
    data = query.data or ""

    if data == "quick:imagine":
        await query.message.reply_html(
            "🎨 <b>Como gerar imagens com Flux.1:</b>\n\n"
            "Basta enviar: <code>/imagine &lt;descrição&gt;</code>\n"
            "<i>Exemplo:</i> <code>/imagine robô futurista em uma biblioteca neon 4k</code>"
        )
    elif data == "quick:routines":
        await routines_command(update, context)
    elif data == "quick:status":
        await status_command(update, context)
    elif data == "quick:reset":
        await reset_command(update, context)
    elif data.startswith("run_routine:"):
        routine_name = data.split(":", 1)[1]
        status_msg = await query.message.reply_text(f"⏳ Executando rotina '{routine_name}'...")
        async with persistent_typing(context.bot, update.effective_chat.id, action=ChatAction.TYPING):
            result = await asyncio.to_thread(routine_manager.run_routine, routine_name, None)
        try:
            await status_msg.delete()
        except Exception:
            pass
        await send_clean_reply(update, result, reply_markup=get_quick_actions_keyboard())


async def post_init_setup(application):
    """Registra comandos nativos no menu do Telegram e inicia o agendador de rotinas."""
    commands = [
        BotCommand("start", "Menu principal e visão geral"),
        BotCommand("imagine", "Gerar imagem com Flux.1"),
        BotCommand("routines", "Ver rotinas de automação"),
        BotCommand("run", "Executar uma rotina salva"),
        BotCommand("status", "Status do sistema e cota Groq"),
        BotCommand("memory", "Ver memórias compartilhadas"),
        BotCommand("files", "Ver arquivos do workspace"),
        BotCommand("reset", "Limpar histórico da conversa"),
        BotCommand("help", "Ajuda e comandos"),
    ]
    try:
        await application.bot.set_my_commands(commands)
        logger.info("✅ Menu de comandos nativo registrado com sucesso no Telegram.")
    except Exception as e:
        logger.warning(f"Não foi possível registrar set_my_commands: {e}")

    # Iniciar motor de agendamento de rotinas com a instância do bot
    try:
        await routine_scheduler.start(bot=application.bot)
    except Exception as e:
        logger.error(f"Erro ao iniciar motor de agendamento de rotinas: {e}")


def run_telegram_bot():
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN não encontrado no arquivo .env.")
        return

    app = ApplicationBuilder().token(token).post_init(post_init_setup).build()

    # Comandos
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", start_command))
    app.add_handler(CommandHandler("imagine", imagine_command))
    app.add_handler(CommandHandler("routines", routines_command))
    app.add_handler(CommandHandler("run", run_command))
    app.add_handler(CommandHandler("delroutine", delroutine_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("memory", memory_command))
    app.add_handler(CommandHandler("files", files_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CommandHandler("clear", reset_command))

    # Callbacks de botões inline
    app.add_handler(CallbackQueryHandler(handle_callback_query))

    # Mensagens de áudio e voz
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))

    # Documentos e Texto
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 Open Grok Bot no Telegram iniciado com sucesso!")
    app.run_polling()


if __name__ == "__main__":
    run_telegram_bot()
