# MCPB Extension Build Notes

## What We've Built

This directory contains a complete `.mcpb` (Model Context Protocol Bundle) extension that enables one-click installation of the mcp-atlassian server for Claude Desktop with network egress filtering.

### Files Created

1. **manifest.json** - Extension metadata and configuration schema
2. **server/index.js** - Node.js wrapper that manages Docker containers
3. **proxy/Dockerfile** - Atlassian-only filtering HTTP proxy (Squid)
4. **proxy/squid.conf** - Proxy allowlist configuration
5. **README.md** - End-user installation and usage instructions
6. **BUILD_NOTES.md** - This file (developer notes)

### Security Architecture

**Network Egress Filtering** (Defense-in-Depth):
- Companion Squid HTTP proxy container allows connections ONLY to Atlassian domains
- mcp-atlassian container routes ALL traffic through proxy
- Prevents data exfiltration even if container or dependencies are compromised

**Allowed Domains**:
- `*.atlassian.net` (Atlassian Cloud)
- `*.jira.com` (Jira-specific endpoints)
- `*.atlassian.com` (API endpoints)
- Direct IP access is BLOCKED (forces DNS resolution for domain checking)

**Container Hardening**:
- Both containers run as non-root users
- Read-only filesystems with restricted tmpfs
- All capabilities dropped
- Memory and CPU limits enforced
- No volume mounts or host network access

### Repository Security Improvements

We also fixed security issues in the repository:

- **`.devcontainer/Dockerfile`**: Added `USER vscode` statement (Trivy HIGH)
- **15 GitHub Code Scanning alerts**: Fixed clear-text logging, ReDoS, URL validation
- **Security documentation**: Comprehensive scanning protocol and CVE analysis

## How to Build the `.mcpb` File

### Prerequisites

1. **Node.js 18+** and **npm** installed on your build machine
2. **@anthropic-ai/mcpb** CLI tool:
   ```bash
   npm install -g @anthropic-ai/mcpb
   ```

### Build Steps

From this directory (`eruditis-atlassian-mcpb/`):

```bash
# Build the .mcpb archive
mcpb pack

# This will create: eruditis-atlassian.mcpb
```

The resulting `.mcpb` file is a ZIP archive containing all the files in this directory.

## Distribution Options

### Option A: Org Upload (Team/Enterprise Plan)

1. Go to Claude Desktop Settings > Connectors > Desktop tab
2. Under "Custom team extensions", click "Add custom extension"
3. Upload the `.mcpb` file
4. Team members will see it in their Extensions list

### Option B: Direct File Sharing

Share the `.mcpb` file via Slack/email/Drive. Users double-click to install.

## Testing Before Distribution

### 1. Pull the Docker image

```bash
docker pull ghcr.io/sooperset/mcp-atlassian:v0.11.10
```

### 2. Install in Claude Desktop

1. Open Claude Desktop
2. Go to Settings > Extensions
3. Click "Install Extension..." and select the `.mcpb` file
4. Fill in your Atlassian credentials (see README.md for details)

### 3. Test read operations

Ask Claude to search Confluence or fetch a Jira issue.

### 4. Verify container security

```bash
docker inspect $(docker ps -q --filter ancestor=ghcr.io/sooperset/mcp-atlassian:v0.11.10) \
  --format '{{json .HostConfig.SecurityOpt}} {{json .HostConfig.CapDrop}} {{json .HostConfig.ReadonlyRootfs}}'

# Expected output: ["no-new-privileges:true"] ["ALL"] true
```

### 5. Test write operations (optional)

1. Go to extension settings and set "Enable Write Operations" to `true`
2. Restart Claude Desktop
3. Ask Claude to create a test page in a sandbox Confluence space
4. Verify the page content is correct (no mangling)

## Updating the Extension

When mcp-atlassian releases a new version:

1. Update `IMAGE` constant in `server/index.js` to the new tag (e.g., `v0.11.11`)
2. Update `"version"` in `manifest.json` (bump semver)
3. Run `mcpb pack` to rebuild
4. Re-distribute to users

## Security Posture

This extension implements defense-in-depth security:

### Network Egress Filtering

**Architecture**:
```
Claude Desktop
    ↓ stdio
server/index.js (Node.js)
    ↓ manages
    ├── atlassian-proxy container (Squid HTTP proxy)
    │     └── Allows ONLY: *.atlassian.net, *.jira.com, *.atlassian.com
    └── mcp-atlassian container
          └── Routes ALL traffic through proxy
```

**How it works**:
1. Extension starts proxy container on first use
2. Proxy listens on 127.0.0.1:3128 (localhost only, not exposed to network)
3. mcp-atlassian container configured with `HTTP_PROXY` and `HTTPS_PROXY`
4. Squid proxy checks every outbound connection against allowlist
5. Non-Atlassian domains are blocked (returns 403 Forbidden)

**Why this matters**:
- Even if mcp-atlassian or its dependencies are compromised
- Malicious code CANNOT exfiltrate data to arbitrary endpoints
- CANNOT download additional malware from internet
- CANNOT participate in botnet/C2 communication
- CAN ONLY talk to Atlassian APIs (intended functionality)

**Proxy security**:
- Runs as non-root user (`squid`)
- Read-only filesystem with restricted tmpfs
- All capabilities dropped
- No caching (just a filtering proxy)
- Blocks direct IP access (forces DNS for domain validation)

**Lifecycle management**:
- Proxy container runs persistently (`--restart=unless-stopped`)
- Shared across all extension invocations (efficient)
- Automatically started if not running
- Built from source on first use (no pre-built image download)

### Container Hardening

Both mcp-atlassian and proxy containers:
- `--cap-drop=ALL` - Drops all Linux capabilities
- `--security-opt no-new-privileges:true` - Prevents privilege escalation
- `--read-only` - Read-only root filesystem
- `--tmpfs /tmp:noexec,nosuid,size=64m` - Writable tmp with restrictions
- `--memory=256m` - Memory limit
- `--cpus=0.5` - CPU limit
- No volume mounts (`-v`) - No host filesystem access
- `--network=bridge` - Default bridge network (no host network access)

### Access Control
- **Pinned image version**: Uses `v0.11.10`, not `latest`
- **Read-only by default**: Write tools require explicit opt-in
- **Tool allowlist**: Only curated operations are exposed
- **Delete operations never exposed**: `jira_delete_issue`, `confluence_delete_page` are hardcoded to be disabled
- **Credential encryption**: API tokens marked `"sensitive": true` in manifest

### Supply Chain
- Uses official image from `ghcr.io/sooperset/mcp-atlassian`
- For maximum control, fork the repo, audit the code, and build your own image

## Security Checklist

Before distributing any version, verify:

- [ ] Docker image tag is pinned to a specific version (never `:latest`)
- [ ] `--cap-drop=ALL` is in server/index.js:258
- [ ] `--security-opt no-new-privileges:true` is in server/index.js:259
- [ ] `--read-only` is in server/index.js:260
- [ ] No `-v` volume mounts exist in server/index.js
- [ ] No `--network=host` in server/index.js
- [ ] `ENABLED_TOOLS` explicitly lists allowed tools (server/index.js:97-98)
- [ ] Delete operations NOT in any tool list (server/index.js:71-72 comment)
- [ ] `atlassian_api_token` has `"sensitive": true` in manifest.json:216
- [ ] Default for `enable_write_tools` is `"false"` in manifest.json:224
- [ ] No secrets hardcoded in any files

## Architecture Decisions

### Why Docker-in-Node (not `uv` or bare Python)?

**Sandboxing**: The container provides OS-level isolation. Without it, a compromised dependency could access `~/.ssh`, browser cookies, etc.

**Trade-off**: Requires Docker to be installed on every team member's machine. For a data engineering team, this is acceptable.

### Why API tokens (not OAuth)?

The `.mcpb` `user_config` system doesn't support interactive browser-based OAuth flows. API tokens are simpler: generate once, paste in the install dialog, stored encrypted in OS keychain.

OAuth can be implemented later for the HTTP server deployment (Phase 3).

### Why read-only by default?

Principle of least privilege. Users must explicitly opt into write operations. This reduces the risk of accidental data modification.

## Next Steps (Future Work)

### Phase 3: HTTP Server for Claude Web

For Claude web (`claude.ai`), you'll need mcp-atlassian running as an HTTP service. The planned architecture:

```
Tailscale network
  └── Host machine (workstation, NAS, or VPS)
        └── Docker: mcp-atlassian --transport sse --port 9000
        └── Caddy reverse proxy
              └── mcp.eruditis.com → localhost:9000
                  - TLS via Let's Encrypt
                  - OAuth authentication
                  - Access logging
                  - Rate limiting
```

This is a separate project. The `.mcpb` bundle is self-contained.

## Troubleshooting

See the main README.md for common issues and solutions.

## References

- [MCPB README](https://github.com/modelcontextprotocol/mcpb/blob/main/README.md)
- [MCPB Manifest Spec](https://github.com/modelcontextprotocol/mcpb/blob/main/MANIFEST.md)
- [Building Desktop Extensions](https://support.claude.com/en/articles/12922929-building-desktop-extensions-with-mcpb)
- [MCP Security Best Practices](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices)
- [mcp-atlassian GitHub](https://github.com/sooperset/mcp-atlassian)
