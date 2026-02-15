#!/usr/bin/env node

// eruditis-atlassian MCPB server entry point
// Spawns mcp-atlassian in a sandboxed Docker container with network egress filtering.
// Uses a companion Squid proxy container to allow connections ONLY to Atlassian domains.

const { spawn, execSync } = require("child_process");
const path = require("path");
const fs = require("fs");

// --- Configuration ---
const IMAGE = "ghcr.io/troubladore/mcp-atlassian:v0.11.10";
const PROXY_IMAGE = "eruditis/atlassian-proxy:latest";
const PROXY_CONTAINER_NAME = "eruditis-atlassian-proxy";
const PROXY_PORT = 3128;

// Read config from environment (injected by Claude Desktop from user_config)
const ATLASSIAN_URL = process.env.ATLASSIAN_URL || "";
const ATLASSIAN_EMAIL = process.env.ATLASSIAN_EMAIL || "";
const ATLASSIAN_API_TOKEN = process.env.ATLASSIAN_API_TOKEN || "";
const ENABLE_WRITE = (process.env.ENABLE_WRITE_TOOLS || "false").toLowerCase() === "true";
const CONFLUENCE_SPACES_FILTER = process.env.CONFLUENCE_SPACES_FILTER || "";
const JIRA_PROJECTS_FILTER = process.env.JIRA_PROJECTS_FILTER || "";

// --- Validate required config ---
if (!ATLASSIAN_URL || !ATLASSIAN_EMAIL || !ATLASSIAN_API_TOKEN) {
  process.stderr.write(
    "ERROR: Missing required configuration. Please configure your Atlassian URL, email, and API token in the extension settings.\n"
  );
  process.exit(1);
}

// --- Helper Functions ---

/**
 * Check if a Docker image exists locally
 */
function imageExists(image) {
  try {
    execSync(`docker image inspect ${image}`, { stdio: 'ignore' });
    return true;
  } catch (err) {
    return false;
  }
}

/**
 * Pull a Docker image with progress feedback
 */
function pullImage(image) {
  process.stderr.write(`Pulling Docker image ${image}...\n`);
  process.stderr.write("This may take a few moments on first run.\n");
  try {
    execSync(`docker pull ${image}`, { stdio: 'inherit' });
    process.stderr.write(`Successfully pulled ${image}\n`);
    return true;
  } catch (err) {
    process.stderr.write(`ERROR: Failed to pull Docker image: ${err.message}\n`);
    return false;
  }
}

/**
 * Check if proxy container is running
 */
function isProxyRunning() {
  try {
    const result = execSync(`docker ps --filter name=${PROXY_CONTAINER_NAME} --filter status=running --format "{{.Names}}"`,
      { encoding: 'utf-8' });
    return result.trim() === PROXY_CONTAINER_NAME;
  } catch (err) {
    return false;
  }
}

/**
 * Build the proxy Docker image from local Dockerfile
 */
function buildProxyImage() {
  const proxyDir = path.join(__dirname, "proxy");

  if (!fs.existsSync(path.join(proxyDir, "Dockerfile"))) {
    process.stderr.write("ERROR: Proxy Dockerfile not found. The .mcpb package may be corrupted.\n");
    return false;
  }

  process.stderr.write("Building Atlassian filtering proxy image...\n");
  try {
    execSync(`docker build -t ${PROXY_IMAGE} ${proxyDir}`, { stdio: 'inherit' });
    process.stderr.write("Proxy image built successfully.\n");
    return true;
  } catch (err) {
    process.stderr.write(`ERROR: Failed to build proxy image: ${err.message}\n`);
    return false;
  }
}

/**
 * Start the proxy container if not already running
 */
function ensureProxyRunning() {
  // Check if proxy is already running
  if (isProxyRunning()) {
    process.stderr.write("Atlassian filtering proxy already running.\n");
    return true;
  }

  // Check if old proxy container exists (stopped)
  try {
    const existingContainer = execSync(
      `docker ps -a --filter name=${PROXY_CONTAINER_NAME} --format "{{.Names}}"`,
      { encoding: 'utf-8' }
    ).trim();

    if (existingContainer === PROXY_CONTAINER_NAME) {
      process.stderr.write("Removing stopped proxy container...\n");
      execSync(`docker rm ${PROXY_CONTAINER_NAME}`, { stdio: 'ignore' });
    }
  } catch (err) {
    // Container doesn't exist, that's fine
  }

  // Build proxy image if it doesn't exist
  if (!imageExists(PROXY_IMAGE)) {
    process.stderr.write("Proxy image not found locally. Building...\n");
    if (!buildProxyImage()) {
      return false;
    }
  }

  // Create Docker network for proxy and mcp-atlassian
  const networkName = "eruditis-atlassian-net";
  try {
    execSync(`docker network inspect ${networkName}`, { stdio: 'ignore' });
  } catch (err) {
    // Network doesn't exist, create it
    process.stderr.write("Creating Docker network...\n");
    execSync(`docker network create ${networkName}`, { stdio: 'ignore' });
  }

  // Start proxy container
  process.stderr.write("Starting Atlassian filtering proxy...\n");
  try {
    execSync(
      `docker run -d --name ${PROXY_CONTAINER_NAME} \
        --restart=unless-stopped \
        --network=${networkName} \
        --cap-drop=ALL \
        --security-opt no-new-privileges:true \
        --read-only \
        --tmpfs /var/cache/squid:noexec,nosuid,size=64m,uid=31,gid=31 \
        --tmpfs /var/log/squid:noexec,nosuid,size=16m,uid=31,gid=31 \
        --tmpfs /var/run/squid:noexec,nosuid,size=8m,uid=31,gid=31 \
        ${PROXY_IMAGE}`,
      { stdio: 'inherit' }
    );
    process.stderr.write("Proxy started successfully.\n");

    // Wait for proxy to be ready
    process.stderr.write("Waiting for proxy to be ready...\n");
    let attempts = 0;
    while (attempts < 10) {
      try {
        execSync(`docker exec ${PROXY_CONTAINER_NAME} nc -z 127.0.0.1 3128`, { stdio: 'ignore' });
        process.stderr.write("Proxy is ready.\n");
        return true;
      } catch (err) {
        attempts++;
        execSync("sleep 0.5", { stdio: 'ignore' });
      }
    }

    process.stderr.write("WARNING: Proxy may not be fully ready, but continuing...\n");
    return true;
  } catch (err) {
    process.stderr.write(`ERROR: Failed to start proxy container: ${err.message}\n`);
    return false;
  }
}

// Normalize URL: strip trailing slash
const baseUrl = ATLASSIAN_URL.replace(/\/+$/, "");
const confluenceUrl = baseUrl.includes("/wiki") ? baseUrl : `${baseUrl}/wiki`;
const jiraUrl = baseUrl.replace(/\/wiki\/?$/, "");

// --- Build the tool allowlist ---
// Read-only tools (always enabled)
const READ_TOOLS = [
  "confluence_search",
  "confluence_get_page",
  "confluence_get_page_children",
  "confluence_get_comments",
  "confluence_get_labels",
  "confluence_search_user",
  "jira_search",
  "jira_get_issue",
  "jira_get_all_projects",
  "jira_get_project_issues",
  "jira_get_transitions",
  "jira_search_fields",
  "jira_get_agile_boards",
  "jira_get_board_issues",
  "jira_get_sprints_from_board",
  "jira_get_sprint_issues",
  "jira_get_worklog",
  "jira_get_user_profile",
];

// Write tools (only if explicitly enabled — never includes delete operations)
const WRITE_TOOLS = [
  "confluence_create_page",
  "confluence_update_page",
  "confluence_add_label",
  "confluence_add_comment",
  "jira_create_issue",
  "jira_update_issue",
  "jira_add_comment",
  "jira_transition_issue",
  "jira_add_worklog",
  "jira_link_to_epic",
];

// NEVER exposed, regardless of config:
// jira_delete_issue, confluence_delete_page, jira_batch_create_issues

const enabledTools = ENABLE_WRITE
  ? [...READ_TOOLS, ...WRITE_TOOLS]
  : READ_TOOLS;

// --- Ensure Docker images and proxy are ready ---

// 1. Ensure mcp-atlassian image is available
if (!imageExists(IMAGE)) {
  process.stderr.write(`Docker image ${IMAGE} not found locally.\n`);
  if (!pullImage(IMAGE)) {
    process.stderr.write("Failed to pull Docker image. Please check your internet connection and Docker installation.\n");
    process.exit(1);
  }
}

// 2. Ensure proxy container is running (network egress filtering)
if (!ensureProxyRunning()) {
  process.stderr.write("Failed to start filtering proxy. Extension cannot run without network restrictions.\n");
  process.exit(1);
}

// --- Build Docker args ---
const networkName = "eruditis-atlassian-net";

const dockerArgs = [
  "run",
  "--rm",           // Remove container on exit
  "-i",             // Interactive (for stdio transport)
  `--network=${networkName}`, // Isolated network with proxy (no published ports)
  "--cap-drop=ALL", // Drop all Linux capabilities
  "--security-opt", "no-new-privileges:true", // Prevent privilege escalation
  "--read-only",    // Read-only root filesystem
  "--tmpfs", "/tmp:noexec,nosuid,size=64m", // Writable tmp with restrictions
  "--memory=256m",  // Memory limit
  "--cpus=0.5",     // CPU limit

  // Environment variables (credentials)
  "-e", `CONFLUENCE_URL=${confluenceUrl}`,
  "-e", `CONFLUENCE_USERNAME=${ATLASSIAN_EMAIL}`,
  "-e", `CONFLUENCE_API_TOKEN=${ATLASSIAN_API_TOKEN}`,
  "-e", `JIRA_URL=${jiraUrl}`,
  "-e", `JIRA_USERNAME=${ATLASSIAN_EMAIL}`,
  "-e", `JIRA_API_TOKEN=${ATLASSIAN_API_TOKEN}`,

  // Tool filtering
  "-e", `ENABLED_TOOLS=${enabledTools.join(",")}`,

  // Network egress filtering via proxy (use container name for DNS)
  "-e", `HTTP_PROXY=http://${PROXY_CONTAINER_NAME}:3128`,
  "-e", `HTTPS_PROXY=http://${PROXY_CONTAINER_NAME}:3128`,
  "-e", "NO_PROXY=localhost,127.0.0.1",
];

// Optional space/project filters
if (CONFLUENCE_SPACES_FILTER) {
  dockerArgs.push("-e", `CONFLUENCE_SPACES_FILTER=${CONFLUENCE_SPACES_FILTER}`);
}
if (JIRA_PROJECTS_FILTER) {
  dockerArgs.push("-e", `JIRA_PROJECTS_FILTER=${JIRA_PROJECTS_FILTER}`);
}

// The image
dockerArgs.push(IMAGE);

// --- Spawn Docker and bridge stdio ---
const child = spawn("docker", dockerArgs, {
  stdio: ["pipe", "pipe", "inherit"], // stdin: pipe, stdout: pipe, stderr: inherit to Claude Desktop logs
});

// Bridge stdin from Claude Desktop to Docker container
process.stdin.pipe(child.stdin);

// Bridge stdout from Docker container to Claude Desktop
child.stdout.pipe(process.stdout);

// Handle process lifecycle
child.on("error", (err) => {
  process.stderr.write(`ERROR: Failed to start Docker container: ${err.message}\n`);
  if (err.code === "ENOENT") {
    process.stderr.write(
      "Docker does not appear to be installed or is not in your PATH.\n" +
      "Install Docker Desktop from https://docker.com/products/docker-desktop\n"
    );
  }
  process.exit(1);
});

child.on("exit", (code, signal) => {
  if (code !== 0 && code !== null) {
    process.stderr.write(`Docker container exited with code ${code}\n`);
  }
  process.exit(code || 0);
});

// Forward termination signals to the container
for (const sig of ["SIGINT", "SIGTERM", "SIGHUP"]) {
  process.on(sig, () => {
    child.kill(sig);
  });
}

// Handle stdin close (Claude Desktop disconnects)
process.stdin.on("end", () => {
  child.stdin.end();
});
