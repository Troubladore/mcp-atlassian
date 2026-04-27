# Scripts

Helper scripts for OAuth setup and tooling.

## `oauth_authorize.py` — interactive OAuth authorization flow

Runs Atlassian's OAuth 2.0 (3LO) authorization code flow: opens a browser to
the authorization URL, hosts a localhost callback server, exchanges the
authorization code for tokens, and (by default) saves the tokens to the OS
keyring with a JSON backup at `~/.mcp-atlassian/oauth-<client_id>.json`.

```bash
uv run python scripts/oauth_authorize.py \
    --client-id YOUR_CLIENT_ID \
    --client-secret YOUR_CLIENT_SECRET \
    --redirect-uri http://localhost:8080/callback \
    --scope "read:jira-work offline_access ..."
```

### `--no-persist` mode (BYO secret store)

Add `--no-persist` to suppress all on-disk and keyring writes. On success the
script emits a JSON token block to stdout — the caller is responsible for
storing it (e.g. piping into `op item edit`). Nothing is written to
`~/.mcp-atlassian/` or the OS keyring.

```bash
uv run python scripts/oauth_authorize.py \
    --client-id ... --client-secret ... --redirect-uri ... --scope ... \
    --no-persist > /tmp/tokens.json
```

The JSON block has the shape:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "expires_at": 1234567890.0,
  "cloud_id": "..."        // or "base_url" for Server/DC
}
```

## `oauth_refresh.py` — refresh access token from stored refresh_token

Mints a fresh access token using a long-lived refresh token, without
persisting anything. Used to wrap pytest invocations of the BYO OAuth E2E
suite so each run gets a token within Atlassian's ~1-hour expiry window.

Required environment variables:

- `ATLASSIAN_OAUTH_CLIENT_ID`
- `ATLASSIAN_OAUTH_CLIENT_SECRET`
- `CLOUD_E2E_OAUTH_REFRESH_TOKEN`
- `CLOUD_E2E_OAUTH_CLOUD_ID`

Two output modes:

- **Default (stdout JSON)**: prints `{access_token, refresh_token, cloud_id, expires_at}` to stdout.
- **`--exec CMD ARG...`**: sets `CLOUD_E2E_OAUTH_ACCESS_TOKEN` and `CLOUD_E2E_OAUTH_CLOUD_ID` in the child environment, then execs the given command.

Run the BYO OAuth E2E tests with a fresh token:

```bash
op run --env-file=.env -- \
    uv run python scripts/oauth_refresh.py \
        --exec uv run pytest tests/e2e/cloud/ -k byo_oauth --cloud-e2e -W error
```

The `op run` wrapper substitutes `op://...` references in `.env` to literal
values before this script sees them. Without 1Password, populate the
`CLOUD_E2E_OAUTH_*` and `ATLASSIAN_OAUTH_*` vars directly.

---

## Operational notes (collected from the PR #327 verification)

These details were learned the hard way during the FastMCP 3.x port end-to-end
verification. They apply when registering an Atlassian OAuth app and storing
its credentials in 1Password for use with the scripts above.

### Atlassian OAuth app configuration

- Register the redirect URI in the developer console **exactly** as
  `http://localhost:8080/callback`.
- The app's **Permissions** page is authoritative for which scopes the OAuth
  flow can request. Both **classic** and **granular** Confluence scopes must
  be registered for the v2 REST endpoints this codebase uses to work — the
  underlying `atlassian-python-api` library still hits some v1 endpoints
  (`/rest/api/space`, `/rest/api/content/search`) which only honor classic
  scopes, while v2 endpoints require granular `<verb>:<resource>:confluence`
  scopes.

Scopes used successfully for the full BYO OAuth E2E matrix:

```
read:jira-work write:jira-work read:jira-user
read:page:confluence write:page:confluence delete:page:confluence
read:space:confluence read:attachment:confluence write:attachment:confluence
read:comment:confluence write:comment:confluence read:user:confluence
read:confluence-space.summary read:confluence-content.all
offline_access
```

### 1Password item layout

If storing credentials in 1Password, a two-section login item works well:

- **Atlassian Credentials**: `client_id` (text), `client_secret` (concealed) — set once from the developer console, filled manually.
- **OAuth Credentials**: `cloud_id` (text), `access_token` (concealed), `refresh_token` (concealed) — empty until the authorize/refresh scripts populate them.

For `op://` references in `.env`, **always use UUIDs** (from `op vault list`
and `op item get <name> --format json`). Display names with parens or
em-dashes break the parser with `invalid character in secret reference`.

### `op item edit` scripting gotchas

- When invoking `op item edit` from a subprocess, pass `stdin=subprocess.DEVNULL` (or `< /dev/null` in shell). Otherwise op tries to parse the parent's stdin as a JSON template and fails with `invalid JSON provided`.
- Section prefix is required for `op item edit` field assignments: `op item edit <id> "OAuth Credentials.access_token=<value>"`.
- Field labels are unique across sections, so reading via `op://vault/item/<field>` does not need a section prefix.

### Behavior notes for `oauth_authorize.py`

- In WSL the script can't `webbrowser.open()` (`gio` fails with `Operation not supported`) — the auth URL is logged to stderr, open it manually. The callback server still listens on localhost:8080.
- The authorization URL has `prompt=consent` hard-coded, so the consent screen appears on every run, even after first approval.
- Token exchange failures return generic `401 access_denied` regardless of root cause. Most common causes: (a) `client_secret` mismatch (rotated in console without updating storage), (b) redirect URI mismatch, (c) authorization code already consumed (single-use).
