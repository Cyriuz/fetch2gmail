# Fetch2Gmail

Self-hosted email fetcher: **IMAP (ISP mailbox) → Gmail API import**. Replaces Gmail’s deprecated POP3 fetch. Runs on Debian (e.g. Odroid HC4) or any Linux/macOS with Python 3.11+.

- Polls an ISP mailbox via **IMAPS** (port 993).
- Imports messages with **Gmail API `users.messages.import`** (not SMTP).
- Applies a Gmail label (e.g. **"ISP Mail"**), preserves headers and date.
- **Deletes from ISP only after** Gmail confirms import (keeps limited ISP storage clear).
- **Idempotent**: tracks by IMAP UID and SHA256 message hash; safe across crashes and UIDVALIDITY changes.

**Two ways to get started:**

- **Headless server (e.g. Odroid, Raspberry Pi):** [Part 1](#part-1-get-the-oauth-token-on-a-computer-windows-or-linux) — get the OAuth token on a Windows or Linux computer; [Part 2](#part-2-install-on-the-server-odroid-raspberry-pi-etc-and-run-as-a-system-service) — install on the server, put config and token there, run as a system service.
- **All on one machine:** [Try locally first](#try-locally-first-step-by-step) — run everything (UI and fetch) on your laptop or desktop.

## Requirements

- **Python 3.11+**
- IMAP credentials (ISP mailbox).
- Google Cloud project with Gmail API and OAuth2 credentials (refresh token after one-time consent).

---

## Part 1: Get the OAuth token on a computer (Windows or Linux)

Do this on a **laptop or desktop** that has a browser. You’ll get **credentials.json** (from Google) and **token.json** (from one-time sign-in). You’ll copy both to your server later. Google OAuth does not allow redirect URIs that use an IP address, so the token must be obtained on a machine where the app can use `http://127.0.0.1:8765`.

### Step 1. Install Python 3.11+ and pipx (recommended) or venv

- **Windows**: Install [Python 3.11+](https://www.python.org/downloads/) (check “Add Python to PATH”). Then install **pipx** (needed for Option A below): open Command Prompt or PowerShell and run `pip install pipx` then `pipx ensurepath`. Close and reopen the terminal so `fetch2gmail` will be on your PATH. (Alternatively, use Option B and a venv.)
- **Linux (Debian/Ubuntu, etc.)**: Many distros use an “externally managed” system Python, so **`pip install fetch2gmail`** will fail. Use **pipx** (recommended) or a venv:
  ```bash
  sudo apt install pipx
  pipx ensurepath   # then reopen your terminal so `fetch2gmail` is on PATH
  ```
  Or install Python and venv: `sudo apt install python3 python3-venv` (for Option B below).

### Step 2. Install fetch2gmail

**Option A — from PyPI with pipx (recommended on Linux/macOS/Windows):**

pipx installs the app in an isolated environment and puts the `fetch2gmail` command on your PATH. It works even when system Python is externally managed (e.g. Debian/Ubuntu).

```bash
pipx install fetch2gmail
```

After that, run `fetch2gmail auth` from any directory (e.g. the folder where you saved **credentials.json**).

**Option B — from source (e.g. to try unreleased changes):**
```bash
git clone https://github.com/yourusername/fetch2gmail.git
cd fetch2gmail
python3 -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows (PowerShell):
# .venv\Scripts\Activate.ps1
# Windows (Command Prompt):
# .venv\Scripts\activate.bat
pip install -e .
```
Then use that terminal (with venv active) when you run `fetch2gmail auth`.

### Step 3. Create Google OAuth credentials (Web application)

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → create or select a project.
2. Enable **Gmail API**: APIs & Services → Library → search “Gmail API” → Enable.
3. **OAuth consent screen**: APIs & Services → OAuth consent screen → External → add app name, add scope `https://www.googleapis.com/auth/gmail.modify`, add yourself as **Test user**.
4. **Credentials**: APIs & Services → Credentials → Create credentials → **OAuth client ID** → Application type **Web application**.
5. Under **Authorized redirect URIs** add: `http://127.0.0.1:8765/auth/gmail/callback` and `http://localhost:8765/auth/gmail/callback`.
6. Create → download the JSON. Save it as **credentials.json** in a folder you’ll use for the next step (e.g. your desktop or `~/fetch2gmail-auth`).

### Step 4. Run the auth command to get token.json

Open a terminal in the **same folder** where you saved **credentials.json**. Then run:

```bash
fetch2gmail auth
```

(If you installed from source with a venv, activate the venv first, then run `fetch2gmail auth`.)

- A browser will open at http://127.0.0.1:8765. Sign in with the **Gmail account that should receive the imported mail**.
- Click “Allow” when asked for permission.
- **token.json** is saved in that same folder. You can stop the auth server with **Ctrl+C**.

You can optionally specify paths:  
`fetch2gmail auth --credentials /path/to/credentials.json --token /path/to/token.json`

### Step 5. Keep these two files for the server

You now have:

- **credentials.json** — from Google Cloud (Step 3).
- **token.json** — from `fetch2gmail auth` (Step 4).

Copy both to your server and put them in the **data directory** where the app will run (see Part 2). Do not commit them to git; keep them private.

### Uninstall on this computer (optional)

Once you’ve copied **credentials.json** and **token.json** to the server, you can remove fetch2gmail from this machine if you don’t need it here anymore.

- **If you used pipx:**  
  `pipx uninstall fetch2gmail`
- **If you installed from source in a venv:** delete the project folder (e.g. `rm -rf ~/fetch2gmail`); the venv and app go with it.

You can reinstall later (e.g. with pipx) if you need to run `fetch2gmail auth` again (for example to reconnect a different Gmail account or refresh the token).

---

## Part 2: Install on the server (Odroid, Raspberry Pi, etc.) and run as a system service

Do this on the **headless server** (e.g. Odroid, Raspberry Pi) where fetch2gmail will run. You need **config.json**, **credentials.json**, and **token.json** in one directory; the app will create **state.db** and (if you use the UI) **.cookie_secret** there.

### Step 1. Create a data directory

Pick one directory that will hold all config and secrets (e.g. `/opt/fetch2gmail` or `/home/odroid/fetch2gmail`). Create it and go there:

```bash
sudo mkdir -p /opt/fetch2gmail
sudo chown "$USER" /opt/fetch2gmail
cd /opt/fetch2gmail
```

(Replace `/opt/fetch2gmail` with your choice; use the same path in the steps below.)

### Step 2. Put config and token files in that directory

- **config.json** — Create from the example in the repo: copy `config.example.json` to `config.json` and edit **imap** (host, username, mailbox) and **gmail** (label, `credentials_path`, `token_path`). Use paths relative to this directory, e.g. `credentials.json` and `token.json`.
- **credentials.json** — Copy from the computer where you ran Part 1 (Step 4).
- **token.json** — Copy from the same place.
- **.env** (optional) — If you don’t set the IMAP password in the systemd unit, create `.env` here with:  
  `IMAP_PASSWORD=your_imap_password`

So this directory should contain at least: **config.json**, **credentials.json**, **token.json**, and optionally **.env**.

### Step 3. Install fetch2gmail on the server

On Debian/Ubuntu and similar, system Python is often “externally managed”, so **`pip install fetch2gmail`** can fail. Use **pipx** or a **venv** instead.

**Option A — pipx (recommended):**
```bash
sudo apt install pipx   # if needed
pipx ensurepath        # then log out/in or source your shell rc so PATH includes ~/.local/bin
pipx install fetch2gmail
```
The binary is at **`~/.local/bin/fetch2gmail`**. In systemd use e.g. `ExecStart=/home/odroid/.local/bin/fetch2gmail run` (replace `odroid` with your service user).

**Option B — venv in the data directory (isolated):**
```bash
cd /opt/fetch2gmail
python3 -m venv .venv
.venv/bin/pip install fetch2gmail
```
Use in systemd: `ExecStart=/opt/fetch2gmail/.venv/bin/fetch2gmail run`.

### Step 4. Install and edit the systemd units

Copy the timer and service into systemd:

```bash
sudo cp /path/to/fetch2gmail/systemd/fetch2gmail.service /path/to/fetch2gmail/systemd/fetch2gmail.timer /etc/systemd/system/
```

Edit the service (replace paths and user with yours):

```bash
sudo systemctl edit --full fetch2gmail.service
```

Set at least:

| Setting | Example |
|--------|---------|
| **User=** | `odroid` (user that owns the data directory) |
| **Group=** | `odroid` |
| **WorkingDirectory=** | `/opt/fetch2gmail` (your data directory) |
| **Environment=FETCH2GMAIL_CONFIG=** | `/opt/fetch2gmail/config.json` |
| **ExecStart=** | `/usr/local/bin/fetch2gmail run` (global) or `/opt/fetch2gmail/.venv/bin/fetch2gmail run` (venv) |
| **Environment=IMAP_PASSWORD=** | (optional) your IMAP password if you don’t use `.env` |

Save and exit.

### Step 5. Enable and start the timer

```bash
sudo systemctl daemon-reload
sudo systemctl enable fetch2gmail.timer
sudo systemctl start fetch2gmail.timer
```

The timer runs the fetch every 5 minutes. To watch logs:

```bash
journalctl -u fetch2gmail.service -f
```

### Step 6. (Optional) Run the web UI on the server

If you want the dashboard on the server (e.g. at http://192.168.1.38:8765), run the UI there with the same data directory:

```bash
cd /opt/fetch2gmail
FETCH2GMAIL_CONFIG=/opt/fetch2gmail/config.json fetch2gmail serve --host 0.0.0.0
```

You can run this in a separate systemd service or in a terminal. You don’t need to sign in with Google on the device; **token.json** is already there.

---

## Try locally first (step-by-step)

Follow these steps if you want to run fetch2gmail **on one machine** (laptop or desktop) with the web UI and manual or scheduled fetch. You’ll use a **virtual environment** so the project’s dependencies don’t touch your system Python.

*If you’re setting up a **headless server** (Odroid, Raspberry Pi, etc.) instead, use [Part 1](#part-1-get-the-oauth-token-on-a-computer-windows-or-linux) to get the token on a PC, then [Part 2](#part-2-install-on-the-server-odroid-raspberry-pi-etc-and-run-as-a-system-service) to install and run as a system service on the server.*

### 1. Open a terminal

- **Linux / macOS**: Open “Terminal” (or any terminal app).
- **Windows**: Open “Command Prompt” or “PowerShell”, or use the terminal inside your editor.

### 2. Go to the project folder

```bash
cd /path/to/fetch2gmail
```

Use the real path where you cloned or unpacked Fetch2Gmail (e.g. `cd ~/dev/fetch2gmail` or `cd C:\Users\You\fetch2gmail`).

### 3. Create a virtual environment

A virtual environment is an isolated Python environment for this project.

```bash
python3 -m venv .venv
```

If that fails, try:

```bash
python -m venv .venv
```

You should see no errors. A folder named `.venv` will appear in the project.

### 4. Activate the virtual environment

- **Linux / macOS**:
  ```bash
  source .venv/bin/activate
  ```
- **Windows (Command Prompt)**:
  ```cmd
  .venv\Scripts\activate.bat
  ```
- **Windows (PowerShell)**:
  ```powershell
  .venv\Scripts\Activate.ps1
  ```

When it’s active, your prompt usually starts with `(.venv)`.

### 5. Install the project

Still in the same terminal, with the venv active:

```bash
pip install -e .
```

Wait until it finishes. You should see “Successfully installed fetch2gmail…”.

### 6. Create Google OAuth credentials (Web application)

Do this once (see [OAuth setup](#oauth-setup) below):

- Create a Google Cloud project, enable Gmail API, then set up the **OAuth consent screen** (add the Gmail scope and yourself as a **Test user** so you can sign in without publishing the app).
- Create **OAuth client ID** with application type **Web application** (not Desktop — only Web application has the redirect URI field).
- Add **Authorized redirect URIs**: **`http://127.0.0.1:8765/auth/gmail/callback`** and **`http://localhost:8765/auth/gmail/callback`** (so either URL works).
- Download the JSON and save it in the project folder as **`credentials.json`**.

### 7. Start the web UI and finish setup there (recommended)

```bash
fetch2gmail serve
```

Open **http://127.0.0.1:8765** in your browser.  
**If the app will run on a headless device** (e.g. Odroid): use **`fetch2gmail auth`** on a laptop/PC to get **token.json**, then copy **credentials.json** and **token.json** to the device — see [Headless or LAN-only (e.g. Odroid)](#headless-or-lan-only-eg-odroid).

- **If you see “Initial setup”**: enter your IMAP host, username, password, mailbox, and Gmail label, then click **Create config**. Your password is stored **encrypted** in a `.env` file next to the config (not plain text, not in the config file).
- **If you already have `config.json`**: you’ll see the dashboard. You can enter or change your IMAP password in the **Config** section and click **Save config** (it’s stored encrypted in `.env`).
- Click **Connect Gmail (OAuth)** to sign in with Google in the browser. After you allow access, you’re connected and don’t need to do it again.
- Use **Run fetch now** or **Dry run** to test.

So: sign in with Google first, then create config (or use the dashboard if config already exists).

### 8. Or create config by hand (alternative to step 7)

Create your config file:

```bash
cp config.example.json config.json
```

Edit `config.json`: set **imap.host**, **imap.username**, **imap.mailbox**, **gmail.credentials_path**, **gmail.token_path**. Do not put your IMAP password in the file. Set it in the environment (next step) or later in the UI.

### 9. Set your IMAP password (if not using the UI)

In the same terminal (venv still active):

- **Linux / macOS**:
  ```bash
  export IMAP_PASSWORD='your_actual_imap_password'
  ```
- **Windows (Command Prompt)**:
  ```cmd
  set IMAP_PASSWORD=your_actual_imap_password
  ```
- **Windows (PowerShell)**:
  ```powershell
  $env:IMAP_PASSWORD = 'your_actual_imap_password'
  ```

Replace `your_actual_imap_password` with the real password. This only applies to that terminal session. (If you used the UI in step 7, you already set the password there and can skip this.)

### 10. One-time Gmail sign-in (if you didn’t use “Connect Gmail” in the UI)

If you didn’t connect Gmail in the web UI, run a fetch once so the app can open a browser and get a refresh token:

```bash
fetch2gmail run
```

- A browser window should open.
- Sign in with the **Gmail account that should receive the imported mail**.
- Click “Allow” when asked for permission.
- After that, **`token.json`** is created. You won’t need to sign in again.

If you see “Environment variable IMAP_PASSWORD is not set”, set it (step 9) or set it in the UI and save config.

### 11. Try a dry run (recommended)

A dry run connects to your ISP and would import mail, but **does not** send anything to Gmail and **does not** delete anything from the ISP:

```bash
fetch2gmail run --dry-run
```

Check the output for errors. If it lists “Would import …”, the connection and config are working.

### 12. Run a real fetch

When you’re ready to actually import mail into Gmail:

```bash
fetch2gmail run
```

Messages are imported into Gmail with the label you set in `config.json` (e.g. “ISP Mail”), and only then deleted from the ISP mailbox.

### 13. Use the web UI anytime

Whenever you want to change settings or trigger a fetch from the browser, start the UI (with venv active):

```bash
fetch2gmail serve
```

Open **http://127.0.0.1:8765**. You can change IMAP/Gmail settings (including password, stored encrypted in `.env`), connect Gmail, run fetch or dry run, and see recent logs. Stop the server with **Ctrl+C** when you’re done.

---

## Quick start (reference)

If you already use virtual environments and know the basics:

1. **Install**: **`pipx install fetch2gmail`** (recommended), or clone and use a venv:
   ```bash
   cd fetch2gmail
   python3 -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
   pip install -e .
   ```

2. **Create Google OAuth credentials** (see [OAuth setup](#oauth-setup)).

3. **Config**: `cp config.example.json config.json`, edit it, and set `IMAP_PASSWORD` in the environment.

4. **One-time OAuth**: `fetch2gmail run` (browser opens; then `token.json` is saved).

5. **Run**: `fetch2gmail run` or `fetch2gmail serve` for the UI at http://127.0.0.1:8765.

6. **Dry-run**: `fetch2gmail run --dry-run`.

---

## OAuth setup

Use a **Web application** OAuth client (not Desktop) so you can set the redirect URI for the web UI’s “Connect Gmail” flow.

### 1. Google Cloud project and Gmail API

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project (or select one) → **APIs & Services** → **Library**.
3. Search for **Gmail API** → **Enable**.

### 2. OAuth consent screen (do this before creating credentials)

1. **APIs & Services** → **OAuth consent screen**.
2. Choose **External** (so you can use your personal Gmail). Click **Create**.
3. **App information**: fill App name, User support email, Developer contact. Save.
4. **Scopes** (Data access): click **Add or remove scopes**. Search for “Gmail API” and add:
   - **`https://www.googleapis.com/auth/gmail.modify`**  
   (View and modify but not delete your email.)
   Save.
5. **Test users** (so you can sign in without publishing the app):
   - Under **Test users**, click **Add users**.
   - Add the Gmail address that will receive the imported mail (e.g. yourself).
   - Only these addresses can sign in while the app is in **Testing**.
6. Leave the app in **Testing** — you do **not** need to publish it. Up to 100 test users can sign in.

### 3. OAuth client (Web application) and redirect URI

1. **APIs & Services** → **Credentials** → **Create credentials** → **OAuth client ID**.
2. **Application type**: choose **Web application** (not Desktop).  
   (Desktop apps don’t show a redirect URI field; the web UI needs a fixed callback URL.)
3. **Name**: e.g. “Fetch2Gmail”.
4. **Authorized redirect URIs** → **Add URI** and add:
   - **`http://127.0.0.1:8765/auth/gmail/callback`**
   - **`http://localhost:8765/auth/gmail/callback`**  
   Google does **not** allow redirect URIs that use an IP address (e.g. `http://192.168.1.38:8765/...`). For a **headless or LAN-only** device (e.g. Odroid) that you access at `http://<ip>:8765`, see [Headless or LAN-only (e.g. Odroid)](#headless-or-lan-only-eg-odroid) below: you do the one-time Gmail sign-in on a computer with a browser, then copy `token.json` (and `credentials.json`) to the device.
5. Click **Create**.
6. Download the JSON (click the download icon for the new client) and save it as **`credentials.json`** in your project folder (same place as `config.json`).

### 4. Refresh token (one-time)

Either use the web UI (“Connect Gmail”) or the CLI:

- **Web UI**: Put `credentials.json` in the project folder, add the redirect URI above, then run `fetch2gmail serve`, open http://127.0.0.1:8765, and click **Connect Gmail (OAuth)**. Sign in with the Gmail account you added as a test user; after you allow access, `token.json` is saved.
- **CLI**: Put `credentials.json` in place and set paths in `config.json`. Run `fetch2gmail run`; a browser opens → sign in (with a test user) → allow access → `token.json` is written.

Keep `token.json` and `credentials.json` **private** (do not commit; they are in `.gitignore`).

---

## Configuration

- **config.json** (see `config.example.json`):
  - **imap**: `host`, `port` (993), `username`, `password_env` (e.g. `IMAP_PASSWORD`), `mailbox`, `use_ssl: true`.
  - **gmail**: `label`, `credentials_path`, `token_path`.
  - **state**: `db_path` (SQLite path).
  - **ui**: `host`, `port` for the web UI.
  - **poll_interval_minutes**: used by the UI/documentation; actual polling is via systemd timer or manual/UI trigger.

- **Secrets**: Put IMAP password in environment (e.g. `IMAP_PASSWORD`) or set it in the UI (stored encrypted in `.env`). Do not put OAuth tokens or passwords in config.

---

## Deployment

### Where to put config and secrets on the server

Use **one directory** as your app data directory (e.g. `/opt/fetch2gmail` or `/home/odroid/fetch2gmail`). Put everything there:

| File | Purpose |
|------|--------|
| **config.json** | IMAP/Gmail settings (paths below are relative to this file’s directory) |
| **credentials.json** | Google OAuth client (from GCP) |
| **token.json** | Gmail refresh token (from `fetch2gmail auth` on a machine with a browser) |
| **.env** | Optional: `IMAP_PASSWORD=...` or set via systemd `Environment=` |

When the app runs, it will create in that same directory:

- **state.db** — SQLite state (last UID, message hashes)
- **.cookie_secret** — Web UI session signing (if you use `fetch2gmail serve`)

So: **same folder as `config.json`** is the single place for config, credentials, token, and generated state. Run the app with that directory as the **working directory** and set **`FETCH2GMAIL_CONFIG`** to the full path to `config.json` (e.g. `/opt/fetch2gmail/config.json`).

### Install on the server: venv vs global

- **pipx (recommended on Debian/Ubuntu):** `pipx install fetch2gmail` — installs in an isolated env and avoids “externally managed” errors. Binary at `~/.local/bin/fetch2gmail`. Use that path in systemd `ExecStart`.
- **Venv (isolated):** Create a venv inside your data directory so the app and its deps don’t touch system Python:
  ```bash
  mkdir -p /opt/fetch2gmail && cd /opt/fetch2gmail
  python3 -m venv .venv
  .venv/bin/pip install fetch2gmail
  ```
  Put `config.json`, `credentials.json`, `token.json` (and optionally `.env`) in `/opt/fetch2gmail`. Run with `/opt/fetch2gmail/.venv/bin/fetch2gmail run` and set `WorkingDirectory=/opt/fetch2gmail` in systemd.

Either way, **WorkingDirectory** must be that data directory so the app finds config and writes `state.db` and `.cookie_secret` there.

### systemd (Debian / Odroid)

- **Service**: oneshot run per cycle.
- **Timer**: every 5 minutes.

1. Copy units and edit the service for your paths and user:
   ```bash
   sudo cp systemd/fetch2gmail.service systemd/fetch2gmail.timer /etc/systemd/system/
   sudo systemctl edit --full fetch2gmail.service
   ```
   Set:
   - **User=** and **Group=** — user that owns the data directory (e.g. `odroid`).
   - **WorkingDirectory=** — your data directory (e.g. `/opt/fetch2gmail` or `/home/odroid/fetch2gmail`).
   - **Environment=FETCH2GMAIL_CONFIG=** — full path to `config.json` (e.g. `/opt/fetch2gmail/config.json`).
   - **ExecStart=** — path to `fetch2gmail run`:
     - **pipx:** `ExecStart=/home/odroid/.local/bin/fetch2gmail run` (replace `odroid` with your User).
     - **Venv in data dir:** `ExecStart=/opt/fetch2gmail/.venv/bin/fetch2gmail run`.
   - Optionally **Environment=IMAP_PASSWORD=** if you don’t use `.env`.

2. Reload, enable and start the timer:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable fetch2gmail.timer
   sudo systemctl start fetch2gmail.timer
   ```

Logs go to the **systemd journal**:
```bash
journalctl -u fetch2gmail.service -f
```

See **systemd/README.md** for instance units (e.g. one service per user).

### Headless or LAN-only (e.g. Odroid)

Google OAuth **does not accept redirect URIs that use an IP address** (e.g. `http://192.168.1.38:8765/auth/gmail/callback`). So you cannot complete “Sign in with Google” when the only way to reach the app is via a LAN IP (e.g. **http://192.168.1.38:8765** on a headless Odroid).

**Use the `auth` command on a machine with a browser (like rclone’s authorize flow):**

1. **On any Linux or Windows machine** (laptop, desktop) where you can open a browser:
   - **Get the app**: **`pipx install fetch2gmail`** (recommended; works on externally-managed Python). Or clone and use a venv: **`git clone <repo-url> && cd fetch2gmail && python3 -m venv .venv && source .venv/bin/activate && pip install -e .`**
   - In GCP, create an OAuth **Web application** client and add **only** **`http://127.0.0.1:8765/auth/gmail/callback`** (and optionally `http://localhost:8765/auth/gmail/callback`). Download the JSON and save as **credentials.json** in a folder (e.g. your desktop or home).
   - In that folder, run: **`fetch2gmail auth`**  
     A browser will open at http://127.0.0.1:8765. Sign in with Google; when done, **token.json** is saved in the same folder. Press Ctrl+C to stop the auth server.
   - Optional: **`fetch2gmail auth --credentials /path/to/credentials.json --token /path/to/token.json`** to choose paths.
2. **Copy to the Odroid** (or other headless device):
   - **credentials.json**
   - **token.json**  
   Put them in the **data directory** where the app runs (same folder as `config.json`; see [Where to put config and secrets on the server](#where-to-put-config-and-secrets-on-the-server)).
3. **On the Odroid**, run Fetch2Gmail (e.g. systemd timer for fetch, and optionally `fetch2gmail serve` for the UI). Open the UI at **http://192.168.1.38:8765** (if the UI is bound to that host). Use the dashboard (config, fetch, logs) as usual. No “Sign in with Google” on the device; **token.json** is used for Gmail. If you ever click “Reconnect Gmail”, run **`fetch2gmail auth`** again on the laptop and copy **token.json** back.

So: **On a laptop/PC run `pipx install fetch2gmail` (or install from source in a venv), then `fetch2gmail auth`; copy credentials.json and token.json to the headless device.**

---

## Web UI and CLI

- **Web UI** (`fetch2gmail serve`): localhost only. **OAuth only** (no username/password). Flow:
  1. **Add credentials.json first**: Get it from Google Cloud (OAuth client, Web application). If you open the UI without it, you’ll see a message asking you to add **credentials.json** to the app folder, then refresh.
  2. **Sign in with Google**: Once credentials exist, opening the UI sends you to **Sign in with Google**. That **one sign-in** both logs you into the app and connects your Gmail account (saves `token.json`). No second step.
  3. **Configure ISP email**: After sign-in, if you don’t have a config yet you’ll see the **Configure your ISP email** form (IMAP host, username, password, mailbox, Gmail label). Create config, then run fetch or dry run.
  - If you already have **config.json**, after sign-in you see the dashboard. Use **Reconnect Gmail** only to switch to a different Google account.
  - **No database for auth**: UI session is a signed cookie; `.cookie_secret` stores the signing secret.
  - **Redirect URI**: In your Google Cloud OAuth client, add both `http://127.0.0.1:8765/auth/gmail/callback` and `http://localhost:8765/auth/gmail/callback`.
- **CLI**:
  - `fetch2gmail run` — one fetch cycle.
  - `fetch2gmail run --dry-run` — fetch from ISP only, no import/delete.
  - **`fetch2gmail auth`** — get **token.json** on a machine with a browser (for headless setup). Opens http://127.0.0.1:8765, you sign in with Google, token is saved; then copy **credentials.json** and **token.json** to the Odroid.
  - `fetch2gmail config --init` — create `config.json` from template.
  - `fetch2gmail config --validate` — validate config.
  - `fetch2gmail wizard` — interactive config wizard.

---

## Switching Gmail account and multiple accounts

### Signing in with a different Google account

Each config has **one** `token.json` (path set in `config.json`). If you already have a Gmail account connected and you **Reconnect Gmail** (or run OAuth again), the app **overwrites** that token with the new account. All future fetches will go to the **new** account; the previous account is no longer used.

- The UI shows **Connected as you@gmail.com** and, when you click **Reconnect Gmail (switch account)**, asks for confirmation before starting OAuth.
- **State** (last UID, message hashes) is stored per config directory, not per Gmail account. So after switching, the same IMAP mailbox is still “resumed” from the same UID; messages are imported into the new Gmail account. If you switch back later, you’d need to run OAuth again and the old account would receive only **new** messages (from the current UID onward).

### Multiple Gmail accounts or multiple ISP mailboxes

The app is **one config = one IMAP mailbox → one Gmail account**. To use multiple combinations (e.g. ISP1 → Gmail A, ISP2 → Gmail B):

- **Run multiple instances**, each with its own directory and config:
  - Directory 1: `config.json` (IMAP for ISP1, `token_path`: `token_a.json`), `credentials.json`, `token_a.json`, `state.db`.
  - Directory 2: `config.json` (IMAP for ISP2, `token_path`: `token_b.json`), same or different `credentials.json`, `token_b.json`, `state.db`.
- Use **different config file paths** (e.g. `FETCH2GMAIL_CONFIG=/path/to/config_a.json` and `FETCH2GMAIL_CONFIG=/path/to/config_b.json`) and run two systemd services/timers.
- You can use the **same** Google Cloud OAuth client and `credentials.json` for all; each instance has its own `token_*.json` so each can be connected to a different Google account.

---

## Idempotency and safety

- **UID + UIDVALIDITY**: State is stored per mailbox and per IMAP `UIDVALIDITY`. If the server resets UIDs (new UIDVALIDITY), we do not reuse old `last_processed_uid`; we still avoid duplicates via hashes.
- **Message hash**: Before import, we compute **SHA256(raw message)** and store it. If a message is seen again (same or different UID after reset), we skip import and can still delete from ISP to free space.
- **Order**: For each message: (1) fetch, (2) check hash → skip if already imported, (3) import to Gmail, (4) record hash + UID → Gmail ID in DB, (5) update `last_processed_uid`, (6) delete from ISP and expunge. **We only delete after** a successful Gmail import (or after confirming duplicate by hash).
- **Crashes**: If the process dies after import but before delete, the next run will see the same UID again; the hash is already in the DB, so we skip import and can delete from ISP. No duplicate in Gmail.
- **Network/API failures**: On Gmail API failure we do not update state and do not delete; the same message will be retried next run. Exponential backoff is used for transient API errors.

---

## Security considerations

- **Secrets**: Store IMAP password in environment variables or set it in the UI (stored encrypted in `.env` using the same key as session cookies). Never commit `config.json` with passwords, or `credentials.json` / `token.json`.
- **Web UI**: Bind to **127.0.0.1** only so the UI is not exposed on the network.
- **Gmail scope**: Only `gmail.modify` is requested (read and modify labels/messages); no send or full account access.
- **Files**: Restrict permissions on `config.json`, `token.json`, `credentials.json`, `.cookie_secret`, and `state.db` to the user running the service.

---

## Project layout

```
fetch2gmail/
├── src/fetcher/
│   ├── __init__.py
│   ├── cli.py          # CLI entrypoint
│   ├── config.py       # Config load
│   ├── gmail_client.py # Gmail API import, backoff
│   ├── imap_client.py  # IMAPS fetch, delete
│   ├── log_buffer.py   # In-memory logs for UI
│   ├── run.py          # Main run loop, dry-run
│   ├── state.py        # SQLite state (UID, hash)
│   └── web_ui.py       # FastAPI UI
├── systemd/
│   ├── fetch2gmail.service
│   ├── fetch2gmail.timer
│   └── README.md
├── config.example.json
├── pyproject.toml
├── requirements.txt
├── README.md
├── LICENSE
└── .gitignore
```

---

## Fork and run on your own Debian / Odroid

1. Clone: `git clone https://github.com/yourusername/fetch2gmail.git && cd fetch2gmail`
2. Install: **`pipx install fetch2gmail`** (recommended), or create a venv and `pip install -e .`.
3. Create Google Cloud project, enable Gmail API, create OAuth **Web application** credentials → save as `credentials.json` in your data directory.
4. Run once to get refresh token: from the directory that has `config.json`, run `fetch2gmail run` (browser opens for sign-in; then `token.json` is created there). Or use `fetch2gmail auth` on a laptop and copy `credentials.json` and `token.json` to the server (see [Headless or LAN-only](#headless-or-lan-only-eg-odroid)).
5. Copy and edit systemd units from `systemd/`; set `User`, `Group`, `WorkingDirectory` (your data directory), `FETCH2GMAIL_CONFIG`, and `ExecStart` (path to `fetch2gmail run`). See [Deployment](#deployment).
6. Enable timer: `sudo systemctl enable fetch2gmail.timer && sudo systemctl start fetch2gmail.timer`
7. Optional: run the web UI with `fetch2gmail serve` (e.g. via SSH tunnel) to change settings and trigger fetches.

---

## License

MIT. See **LICENSE**.
