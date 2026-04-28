import contextlib
import logging
import re
import tempfile
from pathlib import Path

from telegram import InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from files_to_agent.bot import keyboards as kb
from files_to_agent.bot.auth import require_allowed_user, require_owner
from files_to_agent.bot.format import human_age, human_size
from files_to_agent.core import (
    ActiveDraftExists,
    Core,
    NameAlreadyTaken,
    NoActiveDraft,
    RenameBlockedAfterUse,
    UploadNotFound,
)
from files_to_agent.messages import HINT_COUNT, t
from files_to_agent.updater import (
    detect_mode,
    mode_description,
    run_git_update,
    schedule_self_exit,
    write_docker_flag,
)
from files_to_agent.version import get_version_info

log = logging.getLogger(__name__)

# Keys used in context.user_data["awaiting"] for the button → text-input flow.
AWAITING_RENAME = "rename"
AWAITING_CONTEXT = "context"


# ---------- helpers ----------


def _core(context: ContextTypes.DEFAULT_TYPE) -> Core:
    return context.bot_data["core"]


def _default_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.bot_data.get("default_lang", "it")


def _lang(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    """Resolve language for the current chat, with chat_data caching.

    Param is `ctx` (not `context`) so callers can safely pass a `context=` kwarg
    when formatting message templates (e.g. session_confirmed.context).
    """
    cached = (ctx.chat_data or {}).get("lang")
    if cached:
        return cached
    chat = update.effective_chat
    if chat is None:
        return _default_lang(ctx)
    stored = _core(ctx).get_chat_lang(chat.id)
    lang = stored or _default_lang(ctx)
    if ctx.chat_data is not None:
        ctx.chat_data["lang"] = lang
    return lang


def _tr(update: Update, ctx: ContextTypes.DEFAULT_TYPE, key: str, **kwargs: object) -> str:
    return t(key, _lang(update, ctx), **kwargs)


async def _reply_html(
    update: Update,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """Send a message in HTML mode. Works for both /command and callback origins."""
    if update.message:
        await update.message.reply_text(
            text, parse_mode=ParseMode.HTML, reply_markup=reply_markup,
            disable_web_page_preview=True,
        )
    elif update.callback_query and update.callback_query.message:
        await update.callback_query.message.reply_text(
            text, parse_mode=ParseMode.HTML, reply_markup=reply_markup,
            disable_web_page_preview=True,
        )


def _state_keyboard(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
) -> InlineKeyboardMarkup:
    """Pick the right keyboard for the current draft state."""
    lang = _lang(update, context)
    chat = update.effective_chat
    if chat is None:
        return kb.kb_idle(lang)
    draft = _core(context).get_active_draft(chat_id=chat.id)
    if draft is None:
        return kb.kb_idle(lang)
    if draft.file_count == 0:
        return kb.kb_draft_empty(lang)
    return kb.kb_draft_with_files(lang)


def _clear_awaiting(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Drop any pending button-prompt state. Call from every command handler so
    a stale `awaiting` flag from an abandoned button prompt cannot misroute the
    user's next plain-text message.
    """
    if context.user_data is not None:
        context.user_data.pop("awaiting", None)


# ---------- /start /help ----------


@require_allowed_user
async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _clear_awaiting(context)
    await _reply_html(update, _tr(update, context, "welcome"), _state_keyboard(update, context))


@require_allowed_user
async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _clear_awaiting(context)
    await _reply_html(update, _tr(update, context, "help"), _state_keyboard(update, context))


# ---------- /new /confirm /cancel ----------


@require_allowed_user
async def handle_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _clear_awaiting(context)
    chat = update.effective_chat
    if chat is None:
        return
    core = _core(context)
    try:
        upload = core.create_upload(chat_id=chat.id)
    except ActiveDraftExists:
        active = core.get_active_draft(chat_id=chat.id)
        active_id = active.id if active else "?"
        await _reply_html(
            update,
            _tr(update, context, "session_already_active", id=active_id),
            _state_keyboard(update, context),
        )
        return
    await _reply_html(
        update,
        _tr(update, context, "session_started"),
        kb.kb_draft_empty(_lang(update, context)),
    )
    log.info("session_started chat_id=%s id=%s", chat.id, upload.id)


@require_allowed_user
async def handle_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _clear_awaiting(context)
    chat = update.effective_chat
    if chat is None:
        return
    core = _core(context)
    draft = core.get_active_draft(chat_id=chat.id)
    if draft is None:
        await _reply_html(
            update,
            _tr(update, context, "no_active_session"),
            kb.kb_idle(_lang(update, context)),
        )
        return
    confirmed = core.confirm_upload(draft.id)
    msg = _tr(
        update, context, "session_confirmed",
        id=confirmed.id,
        name=confirmed.name or "—",
        context=confirmed.context or "—",
        count=confirmed.file_count,
        size=human_size(confirmed.size_bytes),
    )
    await _reply_html(update, msg, kb.kb_confirmed(_lang(update, context)))


@require_allowed_user
async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if chat is None:
        return
    # Also clears any pending text-input state — /cancel doubles as input cancel.
    if context.user_data is not None and context.user_data.get("awaiting"):
        context.user_data.pop("awaiting", None)
        await _reply_html(
            update,
            _tr(update, context, "awaiting_cancelled"),
            _state_keyboard(update, context),
        )
        return
    core = _core(context)
    try:
        core.cancel_active_draft(chat_id=chat.id)
    except NoActiveDraft:
        await _reply_html(
            update,
            _tr(update, context, "no_active_session"),
            kb.kb_idle(_lang(update, context)),
        )
        return
    await _reply_html(
        update,
        _tr(update, context, "session_cancelled"),
        kb.kb_idle(_lang(update, context)),
    )


# ---------- media ----------


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


def _next_hint_key(context: ContextTypes.DEFAULT_TYPE) -> str:
    if context.chat_data is None:
        return "hint_1"
    idx = context.chat_data.get("hint_idx", 0)
    context.chat_data["hint_idx"] = idx + 1
    return f"hint_{(idx % HINT_COUNT) + 1}"


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
        await _reply_html(
            update,
            _tr(update, context, "file_too_big", size=human_size(size), limit=human_size(max_size)),
        )
        return

    draft = core.get_active_draft(chat_id=chat.id)
    if draft is None:
        await _reply_html(
            update,
            _tr(update, context, "no_active_session"),
            kb.kb_idle(_lang(update, context)),
        )
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
    confirmation = _tr(
        update, context, "file_received",
        filename=filename,
        size=human_size(size),
        count=updated.file_count,
        total_size=human_size(updated.size_bytes),
    )
    hint = _tr(update, context, _next_hint_key(context))
    body = f"{confirmation}\n\n{hint}"
    await _reply_html(update, body, kb.kb_draft_with_files(_lang(update, context)))


# ---------- /rename /context ----------


@require_allowed_user
async def handle_rename(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _clear_awaiting(context)
    chat = update.effective_chat
    if chat is None:
        return
    core = _core(context)
    args: list[str] = context.args or []

    if len(args) == 1:
        new_name = args[0]
        draft = core.get_active_draft(chat_id=chat.id)
        if draft is None:
            await _reply_html(
                update,
                _tr(update, context, "no_active_session"),
                kb.kb_idle(_lang(update, context)),
            )
            return
        target_ref = draft.id
    elif len(args) == 2:
        target_ref, new_name = args[0], args[1]
    else:
        await _reply_html(update, _tr(update, context, "rename_usage"))
        return

    await _do_rename(update, context, target_ref, new_name)


async def _do_rename(
    update: Update, context: ContextTypes.DEFAULT_TYPE, target_ref: str, new_name: str,
) -> None:
    core = _core(context)
    try:
        renamed = core.rename_upload(target_ref, new_name)
    except UploadNotFound:
        await _reply_html(update, _tr(update, context, "info_not_found", ref=target_ref))
        return
    except NameAlreadyTaken:
        await _reply_html(update, _tr(update, context, "rename_taken", name=new_name))
        return
    except RenameBlockedAfterUse:
        await _reply_html(update, _tr(update, context, "rename_blocked_after_use"))
        return
    await _reply_html(
        update,
        _tr(update, context, "rename_done", name=renamed.name),
        _state_keyboard(update, context),
    )


@require_allowed_user
async def handle_context(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _clear_awaiting(context)
    chat = update.effective_chat
    if chat is None:
        return
    core = _core(context)
    args: list[str] = context.args or []

    if not args:
        await _reply_html(update, _tr(update, context, "context_usage"))
        return

    # Heuristic: if the first arg resolves to an existing upload, treat it as a ref.
    # Otherwise it's the start of the context text for the active draft.
    first = args[0]
    target_upload = None
    with contextlib.suppress(UploadNotFound):
        target_upload = core.find_by_ref(first)

    if target_upload is not None and target_upload.chat_id == chat.id:
        text = " ".join(args[1:]).strip() or None
        await _do_set_context(update, context, target_upload.id, text)
        return

    draft = core.get_active_draft(chat_id=chat.id)
    if draft is None:
        await _reply_html(
            update,
            _tr(update, context, "no_active_session"),
            kb.kb_idle(_lang(update, context)),
        )
        return
    text = " ".join(args).strip() or None
    await _do_set_context(update, context, draft.id, text)


async def _do_set_context(
    update: Update, context: ContextTypes.DEFAULT_TYPE, upload_id: str, text: str | None,
) -> None:
    updated = _core(context).set_context(upload_id, text)
    if updated.context is None:
        await _reply_html(
            update,
            _tr(update, context, "context_cleared"),
            _state_keyboard(update, context),
        )
    else:
        await _reply_html(
            update,
            _tr(update, context, "context_set", context=updated.context),
            _state_keyboard(update, context),
        )


# ---------- /list /info ----------


@require_allowed_user
async def handle_list_uploads(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _clear_awaiting(context)
    chat = update.effective_chat
    if chat is None:
        return
    core = _core(context)
    rows = core.list_uploads(chat_id=chat.id)
    if not rows:
        await _reply_html(
            update,
            _tr(update, context, "list_empty"),
            kb.kb_idle(_lang(update, context)),
        )
        return
    now = core._now()  # type: ignore[attr-defined]
    lines = [_tr(update, context, "list_header")]
    for i, r in enumerate(rows, 1):
        ref = r.name or r.id
        context_snippet = f" | {r.context[:30]}" if r.context else ""
        lines.append(
            _tr(
                update, context, "list_row",
                idx=i, status=r.status.value, ref=ref,
                size=human_size(r.size_bytes), age=human_age(r.created_at, now),
                context_snippet=context_snippet,
            )
        )
    await _reply_html(update, "\n".join(lines), kb.kb_list(_lang(update, context)))


@require_allowed_user
async def handle_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _clear_awaiting(context)
    args: list[str] = context.args or []
    if not args:
        await _reply_html(update, _tr(update, context, "info_usage"))
        return
    core = _core(context)
    try:
        u = core.find_by_ref(args[0])
    except UploadNotFound:
        await _reply_html(update, _tr(update, context, "info_not_found", ref=args[0]))
        return
    usage_log = core.usage_log(u.id)
    if usage_log:
        usage_lines = "\n".join(
            f"  {e.used_at.isoformat()} - {e.action}" for e in usage_log[-10:]
        )
    else:
        usage_lines = _tr(update, context, "info_no_usage")
    await _reply_html(
        update,
        _tr(
            update, context, "info_block",
            id=u.id, name=u.name or "—", status=u.status.value,
            context=u.context or "—", count=u.file_count, size=human_size(u.size_bytes),
            created=u.created_at.isoformat(),
            confirmed=u.confirmed_at.isoformat() if u.confirmed_at else "—",
            last_used=u.last_used_at.isoformat() if u.last_used_at else "—",
            usage=usage_lines,
        ),
    )


# ---------- /cleanup ----------


@require_allowed_user
async def handle_cleanup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _clear_awaiting(context)
    chat = update.effective_chat
    if chat is None:
        return
    core = _core(context)
    args: list[str] = context.args or []

    if not args:
        oldest = core.oldest_uploads(chat_id=chat.id, limit=10)
        biggest = core.biggest_uploads(chat_id=chat.id, limit=10)
        if not oldest and not biggest:
            await _reply_html(
                update,
                _tr(update, context, "list_empty"),
                kb.kb_idle(_lang(update, context)),
            )
            return
        lines = [_tr(update, context, "cleanup_header"), _tr(update, context, "cleanup_oldest")]
        for r in oldest:
            ref = r.name or r.id
            lines.append(f"  - {ref}  ({r.status.value}, {human_size(r.size_bytes)})")
        lines.append(_tr(update, context, "cleanup_biggest"))
        for r in biggest:
            ref = r.name or r.id
            lines.append(f"  - {ref}  ({r.status.value}, {human_size(r.size_bytes)})")
        await _reply_html(
            update,
            "\n".join(lines),
            kb.kb_cleanup_items(oldest, biggest, _lang(update, context)),
        )
        return

    arg = args[0]
    m = re.fullmatch(r"(\d+)g", arg)
    if m:
        days = int(m.group(1))
        rows = core.uploads_older_than(chat_id=chat.id, days=days)
        freed = sum(r.size_bytes for r in rows)
        for r in rows:
            core.delete_upload(r.id)
        await _reply_html(
            update,
            _tr(update, context, "cleanup_done", n=len(rows), size=human_size(freed)),
            kb.kb_idle(_lang(update, context)),
        )
        return

    try:
        u = core.find_by_ref(arg)
    except UploadNotFound:
        await _reply_html(update, _tr(update, context, "info_not_found", ref=arg))
        return
    if u.chat_id != chat.id:
        await _reply_html(update, _tr(update, context, "info_not_found", ref=arg))
        return
    freed = u.size_bytes
    core.delete_upload(u.id)
    await _reply_html(
        update,
        _tr(update, context, "cleanup_done", n=1, size=human_size(freed)),
        kb.kb_idle(_lang(update, context)),
    )


# ---------- /language ----------


@require_allowed_user
async def handle_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _clear_awaiting(context)
    await _reply_html(update, _tr(update, context, "language_prompt"), kb.kb_language())


def _set_chat_lang(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str,
) -> None:
    chat = update.effective_chat
    if chat is None:
        return
    _core(context).set_chat_lang(chat.id, lang)
    if context.chat_data is not None:
        context.chat_data["lang"] = lang


# ---------- /version /update ----------


@require_owner
async def handle_version(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _clear_awaiting(context)
    info = get_version_info(check_upstream=True)
    if info.behind is None:
        status = _tr(update, context, "version_unknown")
        markup = kb.kb_idle(_lang(update, context))
    elif info.behind == 0:
        status = _tr(update, context, "version_up_to_date")
        markup = kb.kb_idle(_lang(update, context))
    else:
        status = _tr(update, context, "version_behind", n=info.behind)
        markup = kb.kb_update_confirm(_lang(update, context))
    await _reply_html(
        update,
        _tr(
            update, context, "version_block",
            version=info.version, sha=info.sha, mode=mode_description(detect_mode()),
            status=status,
        ),
        markup,
    )


@require_owner
async def handle_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry from /update command — show confirm prompt with current state."""
    _clear_awaiting(context)
    info = get_version_info(check_upstream=True)
    if info.behind == 0:
        await _reply_html(update, _tr(update, context, "update_no_changes"))
        return
    await _reply_html(
        update,
        _tr(update, context, "update_confirm"),
        kb.kb_update_confirm(_lang(update, context)),
    )


async def _run_update_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Actually perform the update. Called from the callback handler."""
    mode = detect_mode()
    if mode == "docker":
        if write_docker_flag():
            await _reply_html(update, _tr(update, context, "update_docker_triggered"))
        else:
            await _reply_html(update, _tr(update, context, "update_docker_instructions"))
        return
    if mode == "bare_git":
        await _reply_html(update, _tr(update, context, "update_no_supervisor"))
        return
    if mode == "supervised_git":
        result = run_git_update()
        if not result.ok:
            await _reply_html(update, _tr(update, context, "update_failed", error=result.message))
            return
        await _reply_html(update, _tr(update, context, "update_starting"))
        schedule_self_exit()
        return
    await _reply_html(update, _tr(update, context, "update_no_supervisor"))


# ---------- callback dispatcher ----------


@require_allowed_user
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cq = update.callback_query
    if cq is None:
        return
    data = cq.data or ""
    await cq.answer()  # always ack so the loading spinner stops

    if data == "new":
        await handle_new(update, context)
    elif data == "list":
        await handle_list_uploads(update, context)
    elif data == "cleanup":
        # synthesize empty args so the list view is shown
        context.args = []
        await handle_cleanup(update, context)
    elif data == "confirm":
        await handle_confirm(update, context)
    elif data == "cancel":
        await handle_cancel(update, context)
    elif data == "rename":
        if context.user_data is not None:
            context.user_data["awaiting"] = AWAITING_RENAME
        await _reply_html(update, _tr(update, context, "awaiting_rename"))
    elif data == "context":
        if context.user_data is not None:
            context.user_data["awaiting"] = AWAITING_CONTEXT
        await _reply_html(update, _tr(update, context, "awaiting_context"))
    elif data == "language":
        await handle_language(update, context)
    elif data == "lang:it":
        _set_chat_lang(update, context, "it")
        await _reply_html(
            update, _tr(update, context, "language_set_it"),
            kb.kb_idle(_lang(update, context)),
        )
    elif data == "lang:en":
        _set_chat_lang(update, context, "en")
        await _reply_html(
            update, _tr(update, context, "language_set_en"),
            kb.kb_idle(_lang(update, context)),
        )
    elif data == "help":
        await handle_help(update, context)
    elif data == "update:go":
        # Only the owner can actually run the update.
        allowed: list[int] = context.bot_data["allowed_user_ids"]
        owner_id = allowed[0] if allowed else None
        user = update.effective_user
        if user is None or owner_id is None or user.id != owner_id:
            await _reply_html(update, _tr(update, context, "owner_only"))
            return
        await _run_update_flow(update, context)
    elif data == "update:skip":
        await _reply_html(
            update, _tr(update, context, "update_no_changes"),
            kb.kb_idle(_lang(update, context)),
        )
    else:
        log.warning("unknown callback_data: %r", data)


# ---------- pending-text dispatcher ----------


@require_allowed_user
async def handle_pending_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Catch-all for plain text messages — only acts if user_data['awaiting'] is set."""
    if update.message is None:
        return
    awaiting = (context.user_data or {}).get("awaiting")
    if not awaiting:
        return  # plain text without a pending prompt is ignored

    text = (update.message.text or "").strip()
    if not text:
        return
    if context.user_data is not None:
        context.user_data.pop("awaiting", None)

    chat = update.effective_chat
    core = _core(context)
    draft = core.get_active_draft(chat_id=chat.id) if chat else None

    if awaiting == AWAITING_RENAME:
        if draft is None:
            await _reply_html(
                update, _tr(update, context, "no_active_session"),
                kb.kb_idle(_lang(update, context)),
            )
            return
        await _do_rename(update, context, draft.id, text)
    elif awaiting == AWAITING_CONTEXT:
        if draft is None:
            await _reply_html(
                update, _tr(update, context, "no_active_session"),
                kb.kb_idle(_lang(update, context)),
            )
            return
        await _do_set_context(update, context, draft.id, text)
