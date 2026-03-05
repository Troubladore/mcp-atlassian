# Eruditis Atlassian MCP Server

Connect Claude to Eruditis Confluence and Jira via the [mcp-atlassian](https://github.com/sooperset/mcp-atlassian) MCP server running in a sandboxed Docker container.

Supports both **Claude Code (CLI)** and **Claude Desktop** with the same security model: container isolation, network egress filtering, and least-privilege defaults.

## Features

- **Network egress filtering**: Container can ONLY connect to Atlassian domains (*.atlassian.net, *.jira.com) - prevents data exfiltration
- **Secure by default**: Runs in a Docker container with no filesystem access and no host network access
- **Read-only by default**: Write operations must be explicitly enabled
- **Configurable toolsets**: Control which tool categories are available via TOOLSETS
- **Delete protection**: Delete operations blocked by default, even when writes are enabled
- **Automatic setup**: Filtering proxy auto-starts on first use, no manual configuration needed

## Prerequisites (Both Clients)

- **Docker Desktop** must be installed and **running**
  - macOS/Windows: [Download Docker Desktop](https://docker.com/products/docker-desktop)
  - Linux/WSL2: Docker Engine with Docker CLI
  - WSL2 users: Enable WSL integration in Docker Desktop > Settings > Resources > WSL integration
- **Atlassian API Token**: Generate at [id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)

---

## Claude Code (CLI) Setup

The launcher script (`claude-code-launcher.sh`) manages the Docker containers directly via shell — no Node.js required.

### Step 1: Create Credentials File

```bash
mkdir -p ~/.config/mcp-atlassian
cat > ~/.config/mcp-atlassian/.env << 'EOF'
ATLASSIAN_URL=https://your-instance.atlassian.net
ATLASSIAN_EMAIL=your.email@example.com
ATLASSIAN_API_TOKEN=your_api_token
TOOLSETS=all
READ_ONLY_MODE=false
ALLOW_DELETE_TOOLS=false
EOF
chmod 600 ~/.config/mcp-atlassian/.env
```

### Step 2: Register the MCP Server

```bash
claude mcp add --scope user atlassian -- /path/to/docs/mcpb-extension/claude-code-launcher.sh
```

This adds the server to `~/.claude.json` at user scope (available in all projects).

### Step 3: Pull the Docker Image

```bash
docker pull ghcr.io/troubladore/mcp-atlassian:v0.11.16
```

### Step 4: Verify

Start a new Claude Code session (or run `/mcp` to reconnect), then ask Claude to list your Jira projects or search Confluence.

### Troubleshooting (Claude Code)

The launcher script performs pre-flight checks and prints diagnostics to stderr. If tools don't appear:

```bash
# 1. Is Docker running?
docker info >/dev/null 2>&1 && echo "OK" || echo "FAIL: Start Docker Desktop"

# 2. Run the launcher manually to see errors
timeout 10 bash /path/to/claude-code-launcher.sh 2>&1

# 3. Is the proxy healthy?
docker ps --filter name=eruditis-atlassian-proxy

# 4. Reconnect without restarting Claude Code
# Type /mcp in your session
```

**Common issue on WSL2**: Docker Desktop must be running on the Windows host. If it's not, the `docker` command resolves (symlink exists) but execution fails silently. The launcher script detects this and prints a clear error.

---

## Claude Desktop Setup

The `.mcpb` extension bundles a Node.js wrapper that manages Docker containers.

### Additional Prerequisites

- **Node.js 18+** installed on your system (`node --version` to check)
- **Disable "Use built-in Node.js for MCP"** in Claude Desktop settings
  - See [Known Issue](#known-issue-built-in-nodejs) below

### Step 1: Generate an Atlassian API Token

1. Go to [id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click "Create API token"
3. Name it "Claude MCP" and copy the token (you'll need it in the next step)

### Step 2: Install the Extension

1. Open Claude Desktop
2. Go to **Settings > Extensions**
3. Find "Eruditis Atlassian" and click **Install** (or double-click the `.mcpb` file if shared directly)
4. Fill in the configuration dialog:
   - **Atlassian Site URL**: `https://eruditis.atlassian.net`
   - **Atlassian Email**: Your email address used for Atlassian
   - **API Token**: Paste the token from Step 1
   - **Enable Write Operations**: Leave as `false` (read-only mode)

### Step 3: Pull the Docker Image (First Time Only)

Open a terminal and run:

```bash
docker pull ghcr.io/troubladore/mcp-atlassian:v0.11.10
```

This ensures the Docker image is available before you try to use the extension.

### Step 4: Test It

Start a conversation with Claude and try:

```
Search Confluence for our onboarding guide
```

or

```
Show me the open Jira issues in the DEV project
```

---

## Configuration Options (Both Clients)

### Toolsets

Control which categories of tools are available:

- **Default** (`default`): Core tools — issues, fields, comments, transitions, pages, page comments
- **All** (`all`): All 72 tools across 21 toolsets
- **Custom**: Comma-separated list, e.g. `default,jira_agile,jira_projects`

### Enable Write Operations

By default, the extension is read-only. To enable create/update operations:

1. Go to extension settings in Claude Desktop
2. Set "Read-Only Mode" to `false`
3. Restart Claude Desktop

### Allow Delete Operations

Delete operations are blocked by default, even when writes are enabled. To allow deletes:

1. Set "Read-Only Mode" to `false`
2. Set "Allow Delete Operations" to `true`
3. Restart Claude Desktop

### Space and Project Filters

To restrict access to specific Confluence spaces or Jira projects:

1. Go to extension settings in Claude Desktop
2. **Confluence Spaces Filter**: Enter comma-separated space keys (e.g., `DEV,TEAM,DOC`)
3. **Jira Projects Filter**: Enter comma-separated project keys (e.g., `PROJ,DEV`)

Leave empty to access all spaces/projects your account has permission to view.

## Security

This extension implements defense-in-depth security:

### Network Egress Filtering

The extension automatically manages a filtering HTTP proxy that allows connections ONLY to Atlassian domains:

- ✅ **Allowed**: `*.atlassian.net`, `*.jira.com`, `*.atlassian.com`
- ❌ **Blocked**: All other domains (api.openai.com, evil.com, etc.)

**How it works**:
1. First time you use the extension, a Squid proxy container auto-starts
2. The mcp-atlassian container routes ALL traffic through this proxy
3. Proxy checks every outbound connection against the allowlist
4. Non-Atlassian domains return 403 Forbidden

**Why this matters**: Even if the mcp-atlassian server or its dependencies are compromised, malicious code cannot exfiltrate your Atlassian data to arbitrary endpoints or download additional malware.

### Container Isolation

- **Container hardening**: Runs in Docker with `--cap-drop=ALL`, `--read-only`, and `no-new-privileges`
- **Resource limits**: 256MB memory limit, 0.5 CPU limit
- **Pinned version**: Uses specific Docker image tags (not `latest`)
- **No host access**: No volume mounts, no host network access

### Credential Security

- **Claude Desktop**: API tokens stored in OS keychain (macOS Keychain or Windows Credential Manager)
- **Claude Code**: API tokens stored in `~/.config/mcp-atlassian/.env` (chmod 600)
- **Never logged**: Credentials masked in all log output
- **Minimal exposure**: Only passed via environment variables to container

## Troubleshooting

### "Docker does not appear to be installed"

Install Docker Desktop and ensure it's running. On WSL2, Docker Desktop must be installed on the Windows side with WSL integration enabled.

### Container exits immediately

Run the Docker command manually to see error output:

```bash
docker run --rm -i \
  -e CONFLUENCE_URL=https://eruditis.atlassian.net/wiki \
  -e CONFLUENCE_USERNAME=you@gmail.com \
  -e CONFLUENCE_API_TOKEN=your_token \
  -e JIRA_URL=https://eruditis.atlassian.net \
  -e JIRA_USERNAME=you@gmail.com \
  -e JIRA_API_TOKEN=your_token \
  ghcr.io/troubladore/mcp-atlassian:v0.11.10
```

### Authentication failures (401)

Verify you're using an API token (not your account password). Generate a fresh one at [id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)

### "Permission denied" or tools not working

Check that your Atlassian account has the necessary permissions for the spaces/projects you're trying to access.

### Proxy container issues

If you see "Failed to start filtering proxy" errors:

```bash
# Check if proxy container is running
docker ps --filter name=eruditis-atlassian-proxy

# View proxy logs
docker logs eruditis-atlassian-proxy

# Restart proxy manually
docker rm -f eruditis-atlassian-proxy
# Extension will rebuild on next use
```

### Connection blocked by proxy

If tools aren't working and you see proxy errors:

1. Verify your Atlassian URL is correct in extension settings
2. Check proxy logs: `docker logs eruditis-atlassian-proxy`
3. The proxy only allows: `*.atlassian.net`, `*.jira.com`, `*.atlassian.com`

If you're using a self-hosted Atlassian instance (Server/Data Center), you may need to modify the proxy allowlist (see BUILD_NOTES.md).

## Known Issue: Built-in Node.js

Claude Desktop includes a built-in Node.js runtime for running extensions. As of
February 2026, this runtime has a known bug that causes many Node.js extensions
to crash immediately after receiving the MCP `initialize` message. stderr output
from the server process is silently swallowed, making the issue impossible to
debug from the extension side.

**Tracked at**: [modelcontextprotocol/mcpb#45](https://github.com/modelcontextprotocol/mcpb/issues/45)

**Affected extensions**: This is not specific to our extension. Postman, Socket,
PDF Filler, and many other published extensions are affected.

**Workaround**: Disable the built-in Node.js and use your system Node.js instead:

1. Open Claude Desktop
2. Go to **Settings > Extensions**
3. Toggle off **"Use built-in Node.js for MCP"**
4. Ensure Node.js 18+ is installed on your system (`node --version`)
5. Restart Claude Desktop

**Status**: The extension is **fully functional** with system Node.js. All features work:
- ✅ Docker setup (pulls image, builds proxy, starts containers)
- ✅ Network egress filtering (only Atlassian domains allowed)
- ✅ MCP protocol handshake and tool loading
- ✅ Confluence and Jira queries

We will re-enable the built-in runtime once Anthropic resolves the upstream issue.

## Updates

When a new version of mcp-atlassian is released:

1. The extension maintainer will release a new `.mcpb` file
2. Reinstall the extension in Claude Desktop
3. Pull the new Docker image:
   ```bash
   docker pull ghcr.io/troubladore/mcp-atlassian:vX.Y.Z
   ```

## Support

- **mcp-atlassian project**: [github.com/sooperset/mcp-atlassian](https://github.com/sooperset/mcp-atlassian)
- **MCP specification**: [modelcontextprotocol.io](https://modelcontextprotocol.io)
- **Claude Desktop help**: [support.claude.com](https://support.claude.com)

## License

This extension wrapper is provided as-is. The underlying mcp-atlassian server is licensed under the MIT License.
