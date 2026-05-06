# Scripts

Helper scripts for OAuth setup and BYO OAuth E2E test workflows.

## TL;DR for maintainers running the cloud E2E suite

Set up your `.env` once with credentials in your secret store of choice, then:

```bash
op run --env-file=.env -- \
    uv run python scripts/oauth_refresh.py \
        --store 1password \
        --exec uv run pytest tests/e2e/cloud/ -k byo_oauth --cloud-e2e -W error
```

That's it. The helper reads credentials from the configured store, refreshes
the access token, persists the rotated refresh token back to the same store,
and exec's pytest with the fresh credentials in its environment. No shell
incantations to memorize, no manual cleanup after rotation, no token files
to delete from `~/.mcp-atlassian/`.

If the stored refresh token has gone stale (Atlassian invalidated it because
something else consumed it), the helper falls back to the interactive
authorize flow — open the URL it prints, click consent, and the new tokens
are persisted to the store before pytest runs.

---

## Per-script reference

### `oauth_authorize.py` — initial token mint

Bootstrap path. Run this **once** when registering a new Atlassian OAuth
app to mint the initial `access_token` / `refresh_token` / `cloud_id`. After
that, `oauth_refresh.py` handles everything.

```bash
uv run python scripts/oauth_authorize.py \
    --client-id YOUR_CLIENT_ID \
    --client-secret YOUR_CLIENT_SECRET \
    --redirect-uri http://localhost:8080/callback \
    --scope "read:jira-work offline_access ..." \
    --no-persist
```

`--no-persist` suppresses on-disk and keyring writes; the JSON token block
goes to stdout for the caller to capture into a secret store. Without
`--no-persist`, tokens are saved to `~/.mcp-atlassian/oauth-<client_id>.json`
plus the OS keyring (the upstream default — useful for local-only runs but
not for the BYO secret-store workflow).

### `oauth_refresh.py` — refresh + persist + exec

The maintainer-facing entry point. Reads credentials from a configured
secret store, refreshes the access token, persists the rotated refresh token,
and either prints JSON to stdout or execs a child command.

#### `--store` (env | 1password)

Default `env`. Also configurable via the `CLOUD_E2E_OAUTH_BACKEND`
environment variable.

- **`env`** — reads literal env vars, no write-back. Suitable for CI runs
  where the CI system injects credentials per-job, or for one-off runs
  where the rotated token can be captured from the JSON stdout. If the
  refresh token has gone stale, the script reports the error and exits
  non-zero (no automatic re-auth, since there's nowhere to write the new
  token).
- **`1password`** — reads + writes via the `op` CLI. The script owns `op`
  invocations directly with a list argv (no `shell=True`), so the rotated
  refresh token never passes through a shell string. Required additional
  flags: `--op-vault VAULT_UUID` and `--op-item-id ITEM_UUID` (or the
  `ATLASSIAN_OAUTH_OP_VAULT` / `ATLASSIAN_OAUTH_OP_ITEM` env vars). On
  refresh failure, falls back to the interactive authorize flow and
  persists the new tokens to the store.

Adding a new backend (Vault, AWS Secrets Manager, GCP Secret Manager, etc.)
is a matter of adding a class to `_oauth_stores.py` that implements the
same `read()` / `write()` / `writable()` surface; `oauth_refresh.py` will
pick it up via the `--store` flag.

#### `--exec CMD ARG...`

After a successful refresh + persist, exec the given command with
`CLOUD_E2E_OAUTH_ACCESS_TOKEN` and `CLOUD_E2E_OAUTH_CLOUD_ID` set in the
child environment. Designed to wrap pytest invocations of the
`byo_oauth`-parametrized tests in `tests/e2e/cloud/`, which read those
two env vars via `CloudInstanceInfo.from_env()`.

#### Default mode (no `--exec`)

Prints the refreshed `{access_token, refresh_token, cloud_id, expires_at}`
JSON block to stdout. Useful for piping into a different secrets store, for
debugging, or when the test runner is invoked separately from a CI step.

---

## Operational notes

These details applied when registering an Atlassian OAuth app and storing
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

For the `1password` store, the item must have two sections with these
field labels (label-only — no section prefix in op:// references for read):

- **Atlassian Credentials**: `client_id` (text), `client_secret` (concealed)
- **OAuth Credentials**: `cloud_id` (text), `access_token` (concealed), `refresh_token` (concealed)

Use **vault and item UUIDs** (not display names) in your `.env` —
display names with parens, em-dashes, or other punctuation break the
`op://` parser with `invalid character in secret reference`. Get UUIDs
from `op vault list` and `op item get <name> --format json`.

`.env` template (gitignored — fill in the real UUIDs from your environment):

```
CLOUD_E2E_OAUTH_BACKEND=1password
ATLASSIAN_OAUTH_OP_VAULT=<your-vault-uuid>
ATLASSIAN_OAUTH_OP_ITEM=<your-item-uuid>

# For automatic re-authorization when the stored refresh token has gone stale,
# set the same scope and redirect URI you used at initial registration:
ATLASSIAN_OAUTH_SCOPE=read:jira-work write:jira-work ... offline_access
ATLASSIAN_OAUTH_REDIRECT_URI=http://localhost:8080/callback
```

The `1password` store invokes `op` directly via subprocess (not through a
shell), passes secrets as discrete arg-list elements, and pipes
`stdin=DEVNULL` into `op item edit` so op does not try to parse the
parent's stdin as a JSON template.

### Behavior notes for `oauth_authorize.py`

- In WSL the script can't `webbrowser.open()` (`gio` fails with `Operation
  not supported`) — the auth URL is logged to stderr, open it manually. The
  callback server still listens on localhost:8080.
- The authorization URL has `prompt=consent` hard-coded, so the consent
  screen appears on every run, even after first approval.
- Token exchange failures return generic `401 access_denied` regardless of
  root cause. Most common causes: (a) `client_secret` mismatch (rotated in
  console without updating storage), (b) redirect URI mismatch, (c)
  authorization code already consumed (single-use).
