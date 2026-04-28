from typing import Any

# Italian is canonical; English mirrors it. Missing keys fall back to Italian.

_IT: dict[str, str] = {
    "welcome": (
        "Ciao! Sono il bot di staging. Comandi:\n"
        "/nuova - inizia un nuovo upload\n"
        "/conferma - finalizza l'upload attivo\n"
        "/annulla - scarta l'upload attivo\n"
        "/rinomina <nome> - rinomina l'upload attivo\n"
        "/rinomina <id|nome> <nome> - rinomina un upload qualsiasi\n"
        "/contesto <testo> - imposta il contesto sull'upload attivo\n"
        "/contesto <id|nome> [testo] - contesto su un upload qualsiasi (vuoto = pulisce)\n"
        "/lista - elenca gli upload\n"
        "/info <id|nome> - dettagli di un upload\n"
        "/pulizia - pulizia interattiva\n"
        "/pulizia <N>g - elimina upload più vecchi di N giorni\n"
        "/pulizia <id|nome> - elimina un upload specifico"
    ),
    "not_authorized": "Non sei autorizzato a usare questo bot.",
    "session_started": (
        "Nuovo upload avviato. Inviami i file (documenti, foto, video, audio, voice).\n"
        "Quando hai finito, usa /conferma."
    ),
    "session_already_active": (
        "C'è già un upload attivo (ID: {id}).\n"
        "Usa /conferma per finalizzarlo o /annulla per scartarlo."
    ),
    "no_active_session": "Nessun upload attivo. Usa /nuova per iniziarne uno.",
    "file_received": "✓ {filename} ({size}) - totale: {count} file, {total_size}",
    "file_too_big": "✗ File troppo grande ({size}). Limite: {limit}.",
    "disk_full": "✗ Spazio esaurito su Host. Usa /pulizia per liberare spazio.",
    "session_confirmed": (
        "✅ Upload confermato.\n"
        "ID: {id}\n"
        "Nome: {name}\n"
        "Contesto: {context}\n"
        "File: {count} ({size} totali)\n\n"
        "Per usarlo con Hermes:\n"
        "\"Bozza email a [destinatario]. ID: {id}\""
    ),
    "session_cancelled": "Upload annullato.",
    "rename_done": "Rinominato a: {name}",
    "rename_taken": "Il nome \"{name}\" è già in uso. Scegline un altro.",
    "rename_blocked_after_use": (
        "Questo upload è già stato usato da Hermes - rinominarlo non è permesso."
    ),
    "context_set": "Contesto impostato: {context}",
    "context_cleared": "Contesto rimosso.",
    "context_usage": "Uso: /contesto <testo> oppure /contesto <id|nome> [testo]",
    "list_empty": "Nessun upload.",
    "list_header": "📁 I tuoi upload:\n",
    "list_row": "{idx}. [{status}] {ref} - {size} - {age}{context_snippet}",
    "info_not_found": "Upload non trovato: {ref}",
    "info_block": (
        "ID: {id}\n"
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
    "pulizia_header": "🧹 Top 10 più vecchi e più grandi.\nUsa /pulizia <id|nome> per eliminare.",
    "pulizia_confirm": "Confermi l'eliminazione di {n} upload?",
    "pulizia_done": "Eliminati {n} upload, liberati {size}.",
    "disk_warning": (
        "⚠️ Spazio staging al {pct}% ({used} / {total}). "
        "Usa /pulizia per liberare spazio."
    ),
}

_EN: dict[str, str] = {
    "welcome": (
        "Hi! I'm the staging bot. Commands:\n"
        "/nuova - start a new upload\n"
        "/conferma - finalize the active upload\n"
        "/annulla - discard the active upload\n"
        "/rinomina <name> - rename the active upload\n"
        "/rinomina <id|name> <name> - rename any upload\n"
        "/contesto <text> - set context on the active upload\n"
        "/contesto <id|name> [text] - context on any upload (empty = clear)\n"
        "/lista - list your uploads\n"
        "/info <id|name> - upload details\n"
        "/pulizia - interactive cleanup\n"
        "/pulizia <N>g - delete uploads older than N days\n"
        "/pulizia <id|name> - delete a specific upload"
    ),
    "not_authorized": "You are not authorized to use this bot.",
    "session_started": (
        "New upload started. Send me files (documents, photos, video, audio, voice).\n"
        "When done, use /conferma."
    ),
    "session_already_active": (
        "An upload is already active (ID: {id}).\n"
        "Use /conferma to finalize or /annulla to discard."
    ),
    "no_active_session": "No active upload. Use /nuova to start one.",
    "file_received": "✓ {filename} ({size}) - total: {count} files, {total_size}",
    "file_too_big": "✗ File too big ({size}). Limit: {limit}.",
    "disk_full": "✗ Storage full. Run /pulizia to free space.",
    "session_confirmed": (
        "✅ Upload confirmed.\n"
        "ID: {id}\n"
        "Name: {name}\n"
        "Context: {context}\n"
        "Files: {count} ({size} total)\n\n"
        "To use it with Hermes:\n"
        "\"Draft email to [recipient]. ID: {id}\""
    ),
    "session_cancelled": "Upload cancelled.",
    "rename_done": "Renamed to: {name}",
    "rename_taken": "The name \"{name}\" is already taken. Pick another.",
    "rename_blocked_after_use": (
        "This upload has already been used by Hermes - renaming is not allowed."
    ),
    "context_set": "Context set: {context}",
    "context_cleared": "Context cleared.",
    "context_usage": "Usage: /contesto <text> or /contesto <id|name> [text]",
    "list_empty": "No uploads.",
    "list_header": "📁 Your uploads:\n",
    "list_row": "{idx}. [{status}] {ref} - {size} - {age}{context_snippet}",
    "info_not_found": "Upload not found: {ref}",
    "info_block": (
        "ID: {id}\n"
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
    "pulizia_header": "🧹 Top 10 oldest and biggest.\nUse /pulizia <id|name> to delete.",
    "pulizia_confirm": "Confirm deletion of {n} uploads?",
    "pulizia_done": "Deleted {n} uploads, freed {size}.",
    "disk_warning": (
        "⚠️ Staging at {pct}% ({used} / {total}). Run /pulizia to free space."
    ),
}

MESSAGES: dict[str, dict[str, str]] = {"it": _IT, "en": _EN}


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
