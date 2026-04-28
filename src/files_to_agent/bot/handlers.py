import contextlib
import logging
import re
import tempfile
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from files_to_agent.bot.auth import require_allowed_user
from files_to_agent.bot.format import human_age, human_size
from files_to_agent.core import (
    ActiveDraftExists,
    Core,
    NameAlreadyTaken,
    NoActiveDraft,
    RenameBlockedAfterUse,
    UploadNotFound,
)
from files_to_agent.messages import t

log = logging.getLogger(__name__)


def _t(context: ContextTypes.DEFAULT_TYPE, key: str, **kwargs: object) -> str:
    lang = context.bot_data.get("bot_lang", "it")
    return t(key, lang, **kwargs)


def _core(context: ContextTypes.DEFAULT_TYPE) -> Core:
    return context.bot_data["core"]


@require_allowed_user
async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(_t(context, "welcome"))


@require_allowed_user
async def handle_nuova(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if chat is None or update.message is None:
        return
    core = _core(context)
    try:
        upload = core.create_upload(chat_id=chat.id)
    except ActiveDraftExists:
        active = core.get_active_draft(chat_id=chat.id)
        active_id = active.id if active else "?"
        await update.message.reply_text(_t(context, "session_already_active", id=active_id))
        return
    await update.message.reply_text(_t(context, "session_started"))
    log.info("session_started chat_id=%s id=%s", chat.id, upload.id)


def _extract_media(update: Update) -> tuple[str, str, int] | None:
    """Return (file_id, suggested_filename, size_bytes) for the first media part, or None."""
    msg = update.message
    if msg is None:
        return None
    if msg.document:
        d = msg.document
        return d.file_id, d.file_name or f"document_{d.file_id}", d.file_size or 0
    if msg.photo:
        p = msg.photo[-1]  # largest size
        return p.file_id, f"photo_{p.file_id}.jpg", p.file_size or 0
    if msg.video:
        v = msg.video
        return v.file_id, v.file_name or f"video_{v.file_id}.mp4", v.file_size or 0
    if msg.audio:
        a = msg.audio
        return a.file_id, a.file_name or f"audio_{a.file_id}.mp3", a.file_size or 0
    if msg.voice:
        vo = msg.voice
        return vo.file_id, f"voice_{vo.file_id}.ogg", vo.file_size or 0
    return None


@require_allowed_user
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if chat is None or update.message is None:
        return
    core = _core(context)
    media = _extract_media(update)
    if media is None:
        return
    file_id, filename, size = media

    max_size: int = context.bot_data.get("max_upload_size_bytes", 2_147_483_648)
    if size > max_size:
        await update.message.reply_text(
            _t(context, "file_too_big", size=human_size(size), limit=human_size(max_size))
        )
        return

    draft = core.get_active_draft(chat_id=chat.id)
    if draft is None:
        await update.message.reply_text(_t(context, "no_active_session"))
        return

    file = await context.bot.get_file(file_id)
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        await file.download_to_drive(tmp_path)
        payload = tmp_path.read_bytes()
    finally:
        tmp_path.unlink(missing_ok=True)

    updated = core.add_file_to_upload(draft.id, filename, payload)
    await update.message.reply_text(
        _t(
            context,
            "file_received",
            filename=filename,
            size=human_size(size),
            count=updated.file_count,
            total_size=human_size(updated.size_bytes),
        )
    )


@require_allowed_user
async def handle_conferma(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if chat is None or update.message is None:
        return
    core = _core(context)
    draft = core.get_active_draft(chat_id=chat.id)
    if draft is None:
        await update.message.reply_text(_t(context, "no_active_session"))
        return
    confirmed = core.confirm_upload(draft.id)
    await update.message.reply_text(
        _t(
            context,
            "session_confirmed",
            id=confirmed.id,
            name=confirmed.name or "—",
            context=confirmed.context or "—",
            count=confirmed.file_count,
            size=human_size(confirmed.size_bytes),
        )
    )


@require_allowed_user
async def handle_annulla(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if chat is None or update.message is None:
        return
    core = _core(context)
    try:
        core.cancel_active_draft(chat_id=chat.id)
    except NoActiveDraft:
        await update.message.reply_text(_t(context, "no_active_session"))
        return
    await update.message.reply_text(_t(context, "session_cancelled"))


@require_allowed_user
async def handle_rinomina(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if chat is None or update.message is None:
        return
    core = _core(context)
    args: list[str] = context.args or []

    if len(args) == 1:
        new_name = args[0]
        draft = core.get_active_draft(chat_id=chat.id)
        if draft is None:
            await update.message.reply_text(_t(context, "no_active_session"))
            return
        target_ref = draft.id
    elif len(args) == 2:
        target_ref, new_name = args[0], args[1]
    else:
        await update.message.reply_text(
            "Uso: /rinomina <nome> oppure /rinomina <id|nome> <nuovo_nome>"
        )
        return

    try:
        renamed = core.rename_upload(target_ref, new_name)
    except UploadNotFound:
        await update.message.reply_text(_t(context, "info_not_found", ref=target_ref))
        return
    except NameAlreadyTaken:
        await update.message.reply_text(_t(context, "rename_taken", name=new_name))
        return
    except RenameBlockedAfterUse:
        await update.message.reply_text(_t(context, "rename_blocked_after_use"))
        return

    await update.message.reply_text(_t(context, "rename_done", name=renamed.name))


@require_allowed_user
async def handle_contesto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if chat is None or update.message is None:
        return
    core = _core(context)
    args: list[str] = context.args or []

    if not args:
        await update.message.reply_text(_t(context, "context_usage"))
        return

    # Heuristic: if the first arg resolves to an existing upload, treat it as a ref.
    # Otherwise, it's the start of the context text for the active draft.
    first = args[0]
    target_upload = None
    with contextlib.suppress(UploadNotFound):
        target_upload = core.find_by_ref(first)

    if target_upload is not None:
        if target_upload.chat_id != chat.id:
            await update.message.reply_text(_t(context, "info_not_found", ref=first))
            return
        text = " ".join(args[1:]).strip() or None
        updated = core.set_context(target_upload.id, text)
    else:
        draft = core.get_active_draft(chat_id=chat.id)
        if draft is None:
            await update.message.reply_text(_t(context, "no_active_session"))
            return
        text = " ".join(args).strip() or None
        updated = core.set_context(draft.id, text)

    if updated.context is None:
        await update.message.reply_text(_t(context, "context_cleared"))
    else:
        await update.message.reply_text(_t(context, "context_set", context=updated.context))


@require_allowed_user
async def handle_lista(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if chat is None or update.message is None:
        return
    core = _core(context)
    rows = core.list_uploads(chat_id=chat.id)
    if not rows:
        await update.message.reply_text(_t(context, "list_empty"))
        return
    now = core._now()  # type: ignore[attr-defined]
    lines = [_t(context, "list_header")]
    for i, r in enumerate(rows, 1):
        ref = r.name or r.id
        context_snippet = f" | {r.context[:30]}" if r.context else ""
        lines.append(
            _t(
                context,
                "list_row",
                idx=i,
                status=r.status.value,
                ref=ref,
                size=human_size(r.size_bytes),
                age=human_age(r.created_at, now),
                context_snippet=context_snippet,
            )
        )
    await update.message.reply_text("\n".join(lines))


@require_allowed_user
async def handle_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    args: list[str] = context.args or []
    if not args:
        await update.message.reply_text("Uso: /info <id|nome>")
        return
    core = _core(context)
    try:
        u = core.find_by_ref(args[0])
    except UploadNotFound:
        await update.message.reply_text(_t(context, "info_not_found", ref=args[0]))
        return
    usage_log = core.usage_log(u.id)
    if usage_log:
        usage_lines = "\n".join(
            f"  {e.used_at.isoformat()} - {e.action}" for e in usage_log[-10:]
        )
    else:
        usage_lines = _t(context, "info_no_usage")
    await update.message.reply_text(
        _t(
            context,
            "info_block",
            id=u.id,
            name=u.name or "—",
            status=u.status.value,
            context=u.context or "—",
            count=u.file_count,
            size=human_size(u.size_bytes),
            created=u.created_at.isoformat(),
            confirmed=u.confirmed_at.isoformat() if u.confirmed_at else "—",
            last_used=u.last_used_at.isoformat() if u.last_used_at else "—",
            usage=usage_lines,
        )
    )


@require_allowed_user
async def handle_pulizia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if chat is None or update.message is None:
        return
    core = _core(context)
    args: list[str] = context.args or []

    if not args:
        oldest = core.oldest_uploads(chat_id=chat.id, limit=10)
        biggest = core.biggest_uploads(chat_id=chat.id, limit=10)
        if not oldest and not biggest:
            await update.message.reply_text(_t(context, "list_empty"))
            return
        lines = [_t(context, "pulizia_header"), "\nPiù vecchi:"]
        for r in oldest:
            ref = r.name or r.id
            lines.append(f"  - {ref}  ({r.status.value}, {human_size(r.size_bytes)})")
        lines.append("\nPiù grandi:")
        for r in biggest:
            ref = r.name or r.id
            lines.append(f"  - {ref}  ({r.status.value}, {human_size(r.size_bytes)})")
        await update.message.reply_text("\n".join(lines))
        return

    arg = args[0]
    m = re.fullmatch(r"(\d+)g", arg)
    if m:
        days = int(m.group(1))
        rows = core.uploads_older_than(chat_id=chat.id, days=days)
        freed = sum(r.size_bytes for r in rows)
        for r in rows:
            core.delete_upload(r.id)
        await update.message.reply_text(
            _t(context, "pulizia_done", n=len(rows), size=human_size(freed))
        )
        return

    try:
        u = core.find_by_ref(arg)
    except UploadNotFound:
        await update.message.reply_text(_t(context, "info_not_found", ref=arg))
        return
    if u.chat_id != chat.id:
        await update.message.reply_text(_t(context, "info_not_found", ref=arg))
        return
    freed = u.size_bytes
    core.delete_upload(u.id)
    await update.message.reply_text(_t(context, "pulizia_done", n=1, size=human_size(freed)))
