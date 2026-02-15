# Eruditis Atlassian Extension for Claude Desktop

Connect Claude to Eruditis Confluence and Jira via the [mcp-atlassian](https://github.com/sooperset/mcp-atlassian) MCP server running in a sandboxed Docker container.

## Features

- **Secure by default**: Runs in a Docker container with no filesystem access and no host network access
- **Read-only by default**: Write operations must be explicitly enabled
- **Curated tool list**: Only safe operations are exposed (no delete operations)
- **Encrypted credentials**: API tokens stored in OS keychain (macOS Keychain or Windows Credential Manager)

## Prerequisites

- **Docker Desktop** must be installed and running on your machine
  - macOS/Windows: [Download Docker Desktop](https://docker.com/products/docker-desktop)
  - Linux/WSL2: Docker Engine with Docker CLI
- **Claude Desktop** (latest version)
  - Download from [claude.ai/download](https://claude.ai/download)

## Installation

### Step 1: Generate an Atlassian API Token

1. Go to [id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click "Create API token"
3. Name it "Claude MCP" and copy the token (you'll need it in the next step)

### Step 2: Pull the Docker Image (First Time Only)

Open a terminal and run:

```bash
docker pull ghcr.io/sooperset/mcp-atlassian:v0.11.10
```

This ensures the Docker image is available before you try to use the extension.

### Step 3: Install the Extension

1. Open Claude Desktop
2. Go to **Settings > Extensions**
3. Find "Eruditis Atlassian" and click **Install** (or double-click the `.mcpb` file if shared directly)
4. Fill in the configuration dialog:
   - **Atlassian Site URL**: `https://eruditis.atlassian.net`
   - **Atlassian Email**: Your Gmail address used for Atlassian
   - **API Token**: Paste the token from Step 1
   - **Enable Write Operations**: Leave as `false` (read-only mode)

### Step 4: Test It

Start a conversation with Claude and try:

```
Search Confluence for our onboarding guide
```

or

```
Show me the open Jira issues in the DEV project
```

## Configuration Options

### Enable Write Operations

By default, the extension is read-only. To enable create/update operations:

1. Go to extension settings in Claude Desktop
2. Set "Enable Write Operations" to `true`
3. Restart Claude Desktop

**Note**: Delete operations are never exposed, regardless of this setting.

### Space and Project Filters

To restrict access to specific Confluence spaces or Jira projects:

1. Go to extension settings in Claude Desktop
2. **Confluence Spaces Filter**: Enter comma-separated space keys (e.g., `DEV,TEAM,DOC`)
3. **Jira Projects Filter**: Enter comma-separated project keys (e.g., `PROJ,DEV`)

Leave empty to access all spaces/projects your account has permission to view.

## Security

This extension follows security best practices:

- **Container isolation**: Runs in Docker with `--cap-drop=ALL`, `--read-only`, and `no-new-privileges`
- **Network restrictions**: No host network access, only outbound HTTPS to `*.atlassian.net`
- **Resource limits**: 256MB memory limit, 0.5 CPU limit
- **Pinned version**: Uses a specific Docker image tag (not `latest`)
- **Credential encryption**: API tokens stored encrypted in OS keychain

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
  ghcr.io/sooperset/mcp-atlassian:v0.11.10
```

### Authentication failures (401)

Verify you're using an API token (not your account password). Generate a fresh one at [id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)

### "Permission denied" or tools not working

Check that your Atlassian account has the necessary permissions for the spaces/projects you're trying to access.

## Updating

When a new version of mcp-atlassian is released:

1. The extension maintainer will release a new `.mcpb` file
2. Reinstall the extension in Claude Desktop
3. Pull the new Docker image:
   ```bash
   docker pull ghcr.io/sooperset/mcp-atlassian:vX.Y.Z
   ```

## Support

- **mcp-atlassian project**: [github.com/sooperset/mcp-atlassian](https://github.com/sooperset/mcp-atlassian)
- **MCP specification**: [modelcontextprotocol.io](https://modelcontextprotocol.io)
- **Claude Desktop help**: [support.claude.com](https://support.claude.com)

## License

This extension wrapper is provided as-is. The underlying mcp-atlassian server is licensed under the MIT License.
