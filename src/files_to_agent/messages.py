from typing import Any

# Italian is canonical; English mirrors it. Missing keys fall back to Italian.

_IT: dict[str, str] = {
    "welcome": (
        "👋 Ciao! Sono il File To Agent Bot.\n\n"
        "Usa i bottoni qui sotto per iniziare, oppure /help per la guida completa."
    ),
    "help": (
        "📖 <b>Guida rapida</b>\n\n"
        "I comandi funzionano sia in italiano che in inglese.\n\n"
        "<b>Upload</b>\n"
        "• /nuova — inizia un nuovo upload\n"
        "  Poi mandami i file (documenti, foto, video, audio).\n"
        "• /conferma — finalizza l'upload attivo e ricevi l'ID\n"
        "• /annulla — scarta l'upload attivo\n\n"
        "<b>Metadati</b>\n"
        "• /rinomina <i>nome</i> — rinomina l'upload attivo\n"
        "  Esempio: <code>/rinomina FattureAprile</code>\n"
        "• /rinomina <i>id|nome</i> <i>nuovo</i> — rinomina un upload qualsiasi\n"
        "• /contesto <i>testo</i> — descrivi l'upload attivo (l'agente lo legge)\n"
        "  Esempio: <code>/contesto Fatture aprile per Marco</code>\n"
        "• /contesto <i>id|nome</i> [testo] — su un upload qualsiasi (vuoto = pulisce)\n\n"
        "<b>Consultazione</b>\n"
        "• /lista — elenca i tuoi upload\n"
        "• /info <i>id|nome</i> — dettagli di un upload\n\n"
        "<b>Pulizia</b>\n"
        "• /pulizia — top 10 più vecchi e più grandi\n"
        "• /pulizia <i>N</i>g — elimina upload più vecchi di N giorni "
        "(es. <code>/pulizia 30g</code>)\n"
        "• /pulizia <i>id|nome</i> — elimina un upload specifico\n\n"
        "<b>Sistema</b>\n"
        "• /lingua — cambia lingua (italiano / english)\n"
        "• /version — versione corrente e aggiornamenti disponibili\n"
        "• /update — aggiorna il bot all'ultima versione (solo proprietario)\n"
        "• /riavvia — riavvia il bot (solo proprietario)"
    ),
    "not_authorized": "Non sei autorizzato a usare questo bot.",
    "owner_only": "Comando riservato al proprietario del bot.",
    "session_started": (
        "📤 Nuovo upload avviato.\n\n"
        "Inviami i file (documenti, foto, video, audio).\n"
        "Quando hai finito, tocca <b>Conferma</b>."
    ),
    "session_already_active": (
        "C'è già un upload attivo (ID: <code>{id}</code>).\n"
        "Tocca <b>Conferma</b> per finalizzarlo o <b>Annulla</b> per scartarlo."
    ),
    "no_active_session": "Nessun upload attivo. Tocca <b>Nuovo upload</b> per iniziare.",
    "file_received": "✓ {filename} ({size}) — totale: {count} file, {total_size}",
    "file_too_big": "✗ File troppo grande ({size}). Limite: {limit}.",
    "disk_full": "✗ Spazio esaurito. Usa /pulizia per liberare spazio.",
    "session_confirmed": (
        "✅ <b>Upload confermato.</b>\n\n"
        "ID: <code>{id}</code>\n"
        "Nome: {name}\n"
        "Contesto: {context}\n"
        "File: {count} ({size} totali)\n\n"
        "💡 Tocca a lungo l'ID per copiarlo."
    ),
    "session_cancelled": "Upload annullato.",
    "rename_done": "✏️ Rinominato a: <b>{name}</b>",
    "rename_taken": "Il nome \"{name}\" è già in uso. Scegline un altro.",
    "rename_blocked_after_use": (
        "Questo upload è già stato usato dall'agente — rinominarlo non è permesso."
    ),
    "rename_usage": (
        "Uso: <code>/rinomina &lt;nome&gt;</code> oppure "
        "<code>/rinomina &lt;id|nome&gt; &lt;nuovo_nome&gt;</code>"
    ),
    "context_set": "🏷️ Contesto impostato: <i>{context}</i>",
    "context_cleared": "Contesto rimosso.",
    "context_usage": (
        "Uso: <code>/contesto &lt;testo&gt;</code> oppure "
        "<code>/contesto &lt;id|nome&gt; [testo]</code>"
    ),
    "list_empty": "Nessun upload.",
    "list_header": "📁 <b>I tuoi upload:</b>\n",
    "list_row": "{idx}. [{status}] {ref} — {size} — {age}{context_snippet}",
    "info_not_found": "Upload non trovato: {ref}",
    "info_usage": "Uso: <code>/info &lt;id|nome&gt;</code>",
    "info_block": (
        "ID: <code>{id}</code>\n"
        "Nome: {name}\n"
        "Stato: {status}\n"
        "Contesto: {context}\n"
        "File: {count} ({size})\n"
        "Creato: {created}\n"
        "Confermato: {confirmed}\n"
        "Ultimo uso: {last_used}\n\n"
        "Storico utilizzi:\n{usage}"
    ),
    "info_no_usage": "(nessun utilizzo registrato)",
    "cleanup_header": (
        "🧹 <b>Top 10 più vecchi e più grandi.</b>\n"
        "Tocca un upload per eliminarlo, o usa <code>/pulizia &lt;id|nome&gt;</code>."
    ),
    "cleanup_oldest": "\n<b>Più vecchi:</b>",
    "cleanup_biggest": "\n<b>Più grandi:</b>",
    "cleanup_done": "🧹 Eliminati {n} upload, liberati {size}.",
    "disk_warning": (
        "⚠️ Spazio staging al {pct}% ({used} / {total}). "
        "Usa /pulizia per liberare spazio."
    ),
    # Buttons
    "btn_new_upload": "📤 Nuovo upload",
    "btn_list": "📋 Lista",
    "btn_cleanup": "🧹 Pulizia",
    "btn_confirm": "✅ Conferma",
    "btn_cancel": "❌ Annulla",
    "btn_rename": "✏️ Rinomina",
    "btn_context": "🏷️ Contesto",
    "btn_language": "🌐 Lingua / Language",
    "btn_help": "📖 Guida",
    "btn_update_now": "⬆️ Aggiorna ora",
    "btn_update_later": "Più tardi",
    # Language
    "language_prompt": "🌐 Scegli la lingua / Choose your language:",
    "language_set_it": "✓ Lingua impostata: <b>Italiano</b>",
    "language_set_en": "✓ Language set: <b>English</b>",
    # Pending text prompts
    "awaiting_rename": (
        "✏️ Mandami il nuovo nome come prossimo messaggio.\n"
        "Per annullare, manda <code>/annulla</code> (non chiude l'upload, solo l'input)."
    ),
    "awaiting_context": (
        "🏷️ Mandami il testo del contesto come prossimo messaggio.\n"
        "Per annullare, manda <code>/annulla</code> (non chiude l'upload, solo l'input)."
    ),
    "awaiting_cancelled": "Input annullato.",
    # Hints (cycled on each file received)
    "hint_1": (
        "💡 Tocca <b>Contesto</b> per descrivere questo upload — "
        "l'agente lo userà per scrivere meglio."
    ),
    "hint_2": (
        "💡 Tocca <b>Rinomina</b> per dare un nome facile da ricordare "
        "invece dell'ID casuale."
    ),
    "hint_3": "💡 Puoi mandare più file in un solo upload, poi tocca <b>Conferma</b>.",
    "hint_4": "💡 Cambi lingua quando vuoi con /lingua.",
    "hint_5": "💡 Dopo la conferma, tocca a lungo l'ID per copiarlo.",
    "hint_6": "💡 Liberi spazio con /pulizia (per età o per nome).",
    "hint_7": "💡 Vedi tutti i tuoi upload con /lista.",
    "hint_8": "💡 Il menu dei comandi è sempre accanto al campo di testo (icona /).",
    # Version / update
    "version_block": (
        "📦 <b>files-to-agent {version}</b>\n"
        "Commit: <code>{sha}</code>\n"
        "Modalità: {mode}\n\n"
        "{status}"
    ),
    "version_up_to_date": "✅ Sei aggiornato.",
    "version_behind": "🆕 {n} nuovi commit su origin/main.",
    "version_unknown": "ℹ️ Impossibile verificare upstream (offline o non in un git checkout).",
    "update_confirm": (
        "Vuoi aggiornare ora?\n"
        "Il bot eseguirà <code>git pull</code> e si riavvierà automaticamente."
    ),
    "update_starting": "⬆️ Aggiornamento in corso… Il bot si riavvierà a breve.",
    "update_no_changes": "Nessun aggiornamento disponibile.",
    "update_failed": "✗ Aggiornamento fallito:\n<pre>{error}</pre>",
    "update_docker_instructions": (
        "🐳 Stai girando in Docker. Il bot non può aggiornarsi da solo.\n\n"
        "Sul server, esegui:\n"
        "<pre>docker compose pull\ndocker compose up -d</pre>\n\n"
        "Oppure abilita lo script <code>scripts/update-host.sh</code> "
        "(vedi README) per aggiornamenti automatici via bottone."
    ),
    "update_docker_triggered": (
        "🐳 Richiesta di aggiornamento inviata all'host.\n"
        "Lo script sull'host eseguirà il pull e il restart entro pochi secondi."
    ),
    "update_no_supervisor": (
        "⚠️ Nessun supervisore rilevato (no Docker, no systemd, no process-compose).\n"
        "Aggiorna manualmente: <code>git pull && uv sync</code> e poi riavvia il bot."
    ),
    "update_notify_daily": (
        "🆕 Sono disponibili {n} nuovi commit su origin/main.\n"
        "Usa /update quando vuoi aggiornare."
    ),
    "restart_starting": "🔄 Riavvio in corso… Il bot tornerà online tra qualche secondo.",
}

_EN: dict[str, str] = {
    "welcome": (
        "👋 Hi! I'm the File To Agent Bot.\n\n"
        "Use the buttons below to start, or /help for the full guide."
    ),
    "help": (
        "📖 <b>Quick guide</b>\n\n"
        "Commands work in both English and Italian.\n\n"
        "<b>Upload</b>\n"
        "• /new — start a new upload\n"
        "  Then send me files (documents, photos, video, audio).\n"
        "• /confirm — finalize the active upload and get the ID\n"
        "• /cancel — discard the active upload\n\n"
        "<b>Metadata</b>\n"
        "• /rename <i>name</i> — rename the active upload\n"
        "  Example: <code>/rename AprilInvoices</code>\n"
        "• /rename <i>id|name</i> <i>new</i> — rename any upload\n"
        "• /context <i>text</i> — describe the active upload (the agent reads it)\n"
        "  Example: <code>/context April invoices for Marco</code>\n"
        "• /context <i>id|name</i> [text] — on any upload (empty = clear)\n\n"
        "<b>Browse</b>\n"
        "• /list — list your uploads\n"
        "• /info <i>id|name</i> — upload details\n\n"
        "<b>Cleanup</b>\n"
        "• /cleanup — top 10 oldest and biggest\n"
        "• /cleanup <i>N</i>g — delete uploads older than N days (e.g. <code>/cleanup 30g</code>)\n"
        "• /cleanup <i>id|name</i> — delete a specific upload\n\n"
        "<b>System</b>\n"
        "• /language — change language (English / italiano)\n"
        "• /version — current version and available updates\n"
        "• /update — update the bot to the latest version (owner only)\n"
        "• /restart — restart the bot (owner only)"
    ),
    "not_authorized": "You are not authorized to use this bot.",
    "owner_only": "Owner-only command.",
    "session_started": (
        "📤 New upload started.\n\n"
        "Send me files (documents, photos, video, audio).\n"
        "When done, tap <b>Confirm</b>."
    ),
    "session_already_active": (
        "An upload is already active (ID: <code>{id}</code>).\n"
        "Tap <b>Confirm</b> to finalize or <b>Cancel</b> to discard."
    ),
    "no_active_session": "No active upload. Tap <b>New upload</b> to start one.",
    "file_received": "✓ {filename} ({size}) — total: {count} files, {total_size}",
    "file_too_big": "✗ File too big ({size}). Limit: {limit}.",
    "disk_full": "✗ Storage full. Run /cleanup to free space.",
    "session_confirmed": (
        "✅ <b>Upload confirmed.</b>\n\n"
        "ID: <code>{id}</code>\n"
        "Name: {name}\n"
        "Context: {context}\n"
        "Files: {count} ({size} total)\n\n"
        "💡 Tap and hold the ID to copy it."
    ),
    "session_cancelled": "Upload cancelled.",
    "rename_done": "✏️ Renamed to: <b>{name}</b>",
    "rename_taken": "The name \"{name}\" is already taken. Pick another.",
    "rename_blocked_after_use": (
        "This upload has already been used by the agent — renaming is not allowed."
    ),
    "rename_usage": (
        "Usage: <code>/rename &lt;name&gt;</code> or "
        "<code>/rename &lt;id|name&gt; &lt;new_name&gt;</code>"
    ),
    "context_set": "🏷️ Context set: <i>{context}</i>",
    "context_cleared": "Context cleared.",
    "context_usage": (
        "Usage: <code>/context &lt;text&gt;</code> or "
        "<code>/context &lt;id|name&gt; [text]</code>"
    ),
    "list_empty": "No uploads.",
    "list_header": "📁 <b>Your uploads:</b>\n",
    "list_row": "{idx}. [{status}] {ref} — {size} — {age}{context_snippet}",
    "info_not_found": "Upload not found: {ref}",
    "info_usage": "Usage: <code>/info &lt;id|name&gt;</code>",
    "info_block": (
        "ID: <code>{id}</code>\n"
        "Name: {name}\n"
        "Status: {status}\n"
        "Context: {context}\n"
        "Files: {count} ({size})\n"
        "Created: {created}\n"
        "Confirmed: {confirmed}\n"
        "Last used: {last_used}\n\n"
        "Usage history:\n{usage}"
    ),
    "info_no_usage": "(no usage recorded)",
    "cleanup_header": (
        "🧹 <b>Top 10 oldest and biggest.</b>\n"
        "Tap an upload to delete, or use <code>/cleanup &lt;id|name&gt;</code>."
    ),
    "cleanup_oldest": "\n<b>Oldest:</b>",
    "cleanup_biggest": "\n<b>Biggest:</b>",
    "cleanup_done": "🧹 Deleted {n} uploads, freed {size}.",
    "disk_warning": (
        "⚠️ Staging at {pct}% ({used} / {total}). Run /cleanup to free space."
    ),
    "btn_new_upload": "📤 New upload",
    "btn_list": "📋 List",
    "btn_cleanup": "🧹 Cleanup",
    "btn_confirm": "✅ Confirm",
    "btn_cancel": "❌ Cancel",
    "btn_rename": "✏️ Rename",
    "btn_context": "🏷️ Context",
    "btn_language": "🌐 Language / Lingua",
    "btn_help": "📖 Help",
    "btn_update_now": "⬆️ Update now",
    "btn_update_later": "Later",
    "language_prompt": "🌐 Choose your language / Scegli la lingua:",
    "language_set_it": "✓ Lingua impostata: <b>Italiano</b>",
    "language_set_en": "✓ Language set: <b>English</b>",
    "awaiting_rename": (
        "✏️ Send the new name as your next message.\n"
        "To cancel, send <code>/cancel</code> (it cancels just this input, not the upload)."
    ),
    "awaiting_context": (
        "🏷️ Send the context text as your next message.\n"
        "To cancel, send <code>/cancel</code> (it cancels just this input, not the upload)."
    ),
    "awaiting_cancelled": "Input cancelled.",
    "hint_1": (
        "💡 Tap <b>Context</b> to describe this upload — "
        "the agent uses it to write better drafts."
    ),
    "hint_2": "💡 Tap <b>Rename</b> for a memorable name instead of the random ID.",
    "hint_3": "💡 You can send several files in one upload, then tap <b>Confirm</b>.",
    "hint_4": "💡 Switch language anytime with /language.",
    "hint_5": "💡 After confirming, tap and hold the ID to copy it.",
    "hint_6": "💡 Free space with /cleanup (by age or by name).",
    "hint_7": "💡 See all your uploads with /list.",
    "hint_8": "💡 The commands menu is always next to the input box (the / icon).",
    "version_block": (
        "📦 <b>files-to-agent {version}</b>\n"
        "Commit: <code>{sha}</code>\n"
        "Mode: {mode}\n\n"
        "{status}"
    ),
    "version_up_to_date": "✅ You're up to date.",
    "version_behind": "🆕 {n} new commits on origin/main.",
    "version_unknown": "ℹ️ Cannot check upstream (offline or not in a git checkout).",
    "update_confirm": (
        "Update now?\n"
        "The bot will run <code>git pull</code> and restart automatically."
    ),
    "update_starting": "⬆️ Updating… The bot will restart in a moment.",
    "update_no_changes": "No update available.",
    "update_failed": "✗ Update failed:\n<pre>{error}</pre>",
    "update_docker_instructions": (
        "🐳 You're running in Docker. The bot can't update itself.\n\n"
        "On the host, run:\n"
        "<pre>docker compose pull\ndocker compose up -d</pre>\n\n"
        "Or enable <code>scripts/update-host.sh</code> "
        "(see README) for one-button updates."
    ),
    "update_docker_triggered": (
        "🐳 Update request sent to the host.\n"
        "The host script will pull and restart within a few seconds."
    ),
    "update_no_supervisor": (
        "⚠️ No supervisor detected (no Docker, no systemd, no process-compose).\n"
        "Update manually: <code>git pull && uv sync</code> then restart the bot."
    ),
    "update_notify_daily": (
        "🆕 {n} new commits available on origin/main.\n"
        "Run /update when you're ready."
    ),
    "restart_starting": "🔄 Restarting… The bot will be back in a few seconds.",
}

MESSAGES: dict[str, dict[str, str]] = {"it": _IT, "en": _EN}

# How many cycling hints exist (must match hint_1..hint_N keys above).
HINT_COUNT = 8


def t(key: str, lang: str, **kwargs: Any) -> str:
    """Resolve a message key in the given language. Falls back to Italian."""
    catalog = MESSAGES.get(lang) or MESSAGES["it"]
    template = catalog.get(key) or MESSAGES["it"].get(key)
    if template is None:
        return f"[missing message: {key}]"
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template
    return template
