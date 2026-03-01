# systemd setup

- **fetch2gmail.service**: oneshot service that runs one fetch cycle. Use with a timer or trigger from the web UI.
- **fetch2gmail.timer**: runs the service every 5 minutes.

## Install (Debian / Odroid)

1. Copy units (adjust user/paths as needed):
   ```bash
   sudo cp fetch2gmail.service fetch2gmail.timer /etc/systemd/system/
   ```
2. Edit the service for your user and paths:
   ```bash
   sudo systemctl edit --full fetch2gmail.service
   ```
   Set `User=` and `Group=` to the user that owns the data directory. Set `WorkingDirectory=` to your **data directory** (the folder that contains `config.json`, `credentials.json`, `token.json`, and optionally `.env`). Set `Environment=FETCH2GMAIL_CONFIG=` to the full path to `config.json` (e.g. `/opt/fetch2gmail/config.json`). Set `ExecStart=` to the path to `fetch2gmail run` (global install e.g. `/usr/local/bin/fetch2gmail run`, or venv e.g. `/opt/fetch2gmail/.venv/bin/fetch2gmail run`). See main README "Where to put config and secrets on the server" and "systemd".

3. Enable and start the timer:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable fetch2gmail.timer
   sudo systemctl start fetch2gmail.timer
   ```
4. Check:
   ```bash
   systemctl list-timers fetch2gmail*
   journalctl -u fetch2gmail.service -f
   ```

## Run as specific user (e.g. pi or odroid)

Using an instance unit: `fetch2gmail@odroid.service` and `fetch2gmail@odroid.timer` with `User=odroid` and paths under `/home/odroid/fetch2gmail`. Copy to `/etc/systemd/system/` as `fetch2gmail@.service` and `fetch2gmail@.timer`, then:

```bash
sudo systemctl enable fetch2gmail@odroid.timer
sudo systemctl start fetch2gmail@odroid.timer
```
