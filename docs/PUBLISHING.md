# Publishing Fetch2Gmail (maintainer only)

This doc is for you as the maintainer: how to publish to PyPI.

## PyPI API token (where to add it)

1. Log in at [pypi.org](https://pypi.org).
2. Click your **username** (top right) → **Account settings**.
3. Scroll to **API tokens**.
4. Click **Add API token**.
5. Name it (e.g. `fetch2gmail-github`) and choose scope:
   - **Entire account** (simplest), or
   - **Project: fetch2gmail** (only after the project exists on PyPI).
6. Copy the token **once** (it's shown only at creation). You'll use it in GitHub.

For the **first** publish you may need to upload once manually so the project exists, then you can use a project-scoped token. Or create an account-wide token first, use it in GitHub, then create a project-scoped token and update the secret.

## Publishing from GitHub (easiest)

1. In your GitHub repo: **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.
2. Name: **`PYPI_API_TOKEN`**, Value: the token you copied from PyPI.
3. Create a **release** (e.g. tag `v1.0.0`): **Releases** → **Create a new release** → choose a tag (or create one like `v1.0.0`) → publish.
4. The workflow **Publish to PyPI** runs, builds the package, and uploads it. After a minute or two, `pip install fetch2gmail` works.

No need to run `build` or `twine` on your machine. For new versions, bump `version` in `pyproject.toml`, commit, then create a new release with a new tag (e.g. `v1.0.1`).

## What PyPI gives you

- The **code** (the `fetch2gmail` package). Two use cases:
  - **Laptop:** `pip install fetch2gmail` → run **`fetch2gmail auth`** → get `token.json` (and have `credentials.json`) → copy both to the headless machine.
  - **Headless (e.g. Odroid):** `pip install fetch2gmail` → put `config.json`, `credentials.json`, `token.json`, and `.env` (or set `IMAP_PASSWORD`) in a **data directory** → run **`fetch2gmail serve`** or **`fetch2gmail run`** (e.g. via systemd). See README "Where to put config and secrets on the server".

**What is *not* in the package**

- `state.db`, `.env`, `credentials.json`, `token.json`, `config.json`, `.cookie_secret` are **runtime/data** files. They are **not** packaged in PyPI. They live in the data directory on the machine. On the laptop you only need the app to run `fetch2gmail auth` and then copy the two files. On the headless machine you create a folder with config, credentials, token, and optional .env; the app creates `state.db` and `.cookie_secret` when it runs.

**Recommendation:** Publish to PyPI and use the GitHub Action so `pip install fetch2gmail` works. The README describes pip install and running on the server (data directory + systemd).
