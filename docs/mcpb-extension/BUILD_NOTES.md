# MCPB Extension Build Notes

## What We've Built

This directory contains a complete `.mcpb` (Model Context Protocol Bundle) extension that enables one-click installation of the mcp-atlassian server for Claude Desktop with network egress filtering.

### Files Created

1. **manifest.json** - Extension metadata and configuration schema
2. **server/index.js** - Node.js wrapper that manages Docker containers
3. **proxy/Dockerfile** - Atlassian-only filtering HTTP proxy (Squid)
4. **proxy/squid.conf** - Proxy allowlist configuration
5. **tests/static.test.js** - Static analysis tests (no Docker needed)
6. **tests/integration.test.js** - Docker integration tests
7. **README.md** - End-user installation and usage instructions
8. **BUILD_NOTES.md** - This file (developer notes)

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

## Running Tests

Tests must pass before building or releasing. There are two test suites:

### Static Analysis (fast, no Docker)

```bash
node --test tests/static.test.js
```

Validates squid.conf, server/index.js, and manifest.json for known pitfalls
including Squid 6.6 compatibility, security hardening flags, image references,
and tmpfs mount configuration. **21 tests, runs in <1 second.**

### Integration Tests (requires Docker)

```bash
node --test tests/integration.test.js
```

Builds the proxy image, starts it with full security hardening, and runs an
end-to-end MCP initialize handshake through the proxy. **7 tests, ~20 seconds.**

### Run Both

```bash
node --test tests/*.test.js
```

## Known Pitfalls (Lessons Learned)

These are bugs we've hit and fixed. The test suite catches all of them:

1. **Squid 6.6 rejects redundant ACL domains.** If `.atlassian.com` is in an
   ACL, adding `atlassian.com` or `api.atlassian.com` to the same ACL is a
   FATAL error — Squid considers them already covered by the wildcard. Only
   use the `.domain.com` form (with leading dot).

2. **Squid PID file must be on writable tmpfs.** With `--read-only` filesystem,
   the default PID path `/var/run/squid.pid` is unwritable. Set `pid_filename`
   in squid.conf to a path under a tmpfs mount (e.g., `/var/run/squid/squid.pid`).

3. **tmpfs mounts need uid/gid for non-root containers.** Docker `--tmpfs`
   mounts default to root ownership. Squid runs as uid 31 on Alpine, so all
   proxy tmpfs mounts need `uid=31,gid=31` or Squid can't write to them.

4. **Squid has a built-in `localhost` ACL.** Don't redefine `acl localhost src
   127.0.0.1/32 ::1` — it causes warnings and is redundant.

5. **GHCR requires a classic PAT.** Fine-grained GitHub tokens don't support
   the `write:packages` scope. You must use a classic Personal Access Token.

## How to Build and Release

### Prerequisites

1. **Docker** installed and running
2. **Node.js 18+** and **npm** installed
3. **@anthropic-ai/mcpb** CLI tool:
   ```bash
   npm install -g @anthropic-ai/mcpb
   ```
4. **GitHub Classic PAT** with `write:packages` scope (for GHCR push)
   - Generate at: https://github.com/settings/tokens/new
   - Fine-grained tokens do NOT support packages — must be classic

### Step 1: Build the Docker Image from Source

We build our own image from the audited fork rather than pulling the upstream
pre-built image. This gives us full supply-chain control over what runs on
team members' machines.

From the **repo root** (`mcp-atlassian/`):

```bash
# Build from our audited Dockerfile
docker build -t ghcr.io/troubladore/mcp-atlassian:v0.11.10 .
```

### Step 2: Push the Image to GHCR

```bash
# Authenticate (requires classic PAT with write:packages scope)
echo "YOUR_CLASSIC_PAT" | docker login ghcr.io -u Troubladore --password-stdin

# Push
docker push ghcr.io/troubladore/mcp-atlassian:v0.11.10
```

After the first push, make the package public at:
https://github.com/users/Troubladore/packages/container/mcp-atlassian/settings

### Step 3: Run Tests

```bash
cd docs/mcpb-extension
node --test tests/*.test.js
```

All 28 tests must pass before packaging.

### Step 4: Build the `.mcpb` Extension

From this directory (`docs/mcpb-extension/`):

```bash
# Build the .mcpb archive with explicit output name
mcpb pack . eruditis-atlassian-1.0.0.mcpb
```

The resulting `.mcpb` file is a ZIP archive containing all the files in this directory.

### Step 5: Upload to Claude Team Settings

1. Go to Claude team settings > Connectors > Desktop tab
2. Under "Custom team extensions", click "Add custom extension"
3. Upload the `eruditis-atlassian-<version>.mcpb` file
4. Team members will see it in their Extensions list

## Alternative Distribution

If team upload isn't available, share the `.mcpb` file via Slack/email/Drive.
Users double-click to install.

## Testing Before Distribution

### 1. Verify the Docker image

```bash
# Image should already exist from the build step
docker images ghcr.io/troubladore/mcp-atlassian:v0.11.10
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
docker inspect $(docker ps -q --filter ancestor=ghcr.io/troubladore/mcp-atlassian:v0.11.10) \
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

1. Merge upstream changes into `eruditis/main` branch
2. Review changes for security (check `security/SCANNING_PROTOCOL.md`)
3. Build new Docker image: `docker build -t ghcr.io/troubladore/mcp-atlassian:vX.Y.Z .`
4. Push to GHCR: `docker push ghcr.io/troubladore/mcp-atlassian:vX.Y.Z`
5. Update `IMAGE` constant in `server/index.js` to the new tag
6. Update `"version"` in `manifest.json` (bump semver)
7. Rebuild: `mcpb pack . eruditis-atlassian-X.Y.Z.mcpb`
8. Re-upload to Claude team settings

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
- Image built from our audited fork at `ghcr.io/troubladore/mcp-atlassian`
- We do NOT pull pre-built images from upstream — we build from source
- All code changes are reviewed and security-scanned before image builds

## Security Checklist

Before distributing any version:

```bash
# Automated checks (covers all items below)
node --test tests/static.test.js
node --test tests/integration.test.js
```

The test suite verifies:
- [ ] Docker image tag pinned to specific version (not `:latest`)
- [ ] Image references `ghcr.io/troubladore/` (not upstream `sooperset`)
- [ ] `--cap-drop=ALL` on both proxy and mcp-atlassian containers
- [ ] `--security-opt no-new-privileges:true` on both containers
- [ ] `--read-only` filesystem on both containers
- [ ] No `-v` volume mounts
- [ ] No `--network=host`
- [ ] Proxy tmpfs mounts have `uid=31,gid=31`
- [ ] Delete operations not in tool arrays
- [ ] `atlassian_api_token` has `"sensitive": true` in manifest
- [ ] `enable_write_tools` defaults to `"false"`
- [ ] squid.conf has no redundant ACL entries (Squid 6.6 compat)
- [ ] squid.conf PID file on writable tmpfs path
- [ ] Proxy builds, starts, and listens on port 3128
- [ ] MCP initialize handshake works end-to-end

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
