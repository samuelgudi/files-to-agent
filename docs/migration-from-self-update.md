# Migrating from the self-update mechanism

If you installed `files-to-agent` before v0.2.0, you may have:
- The host watcher systemd service (`files-to-agent-update-host`) running
- A `./update-flag/` directory in your compose folder
- A `/var/lib/files-to-agent/update.requested` flag file
- An `UPDATE_CHECK_DAILY` env var in your `.env`

These are all obsolete. Clean them up:

```bash
sudo systemctl disable --now files-to-agent-update-host 2>/dev/null || true
sudo rm -f /usr/local/bin/files-to-agent-update-host \
           /etc/systemd/system/files-to-agent-update-host.service
sudo systemctl daemon-reload
rm -rf ./update-flag/
sed -i '/^UPDATE_CHECK_DAILY=/d' .env
```

The new update flow is in [deployment.md](deployment.md#updating).

The `/update` command and the daily upstream-check DM no longer exist. `/version`
now just reports the current version and commit SHA. To trigger an update,
pull the new image at the orchestrator layer (or let Watchtower do it).
