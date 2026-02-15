#!/usr/bin/env node

// eruditis-atlassian MCPB server entry point
// Spawns mcp-atlassian in a sandboxed Docker container with network egress filtering.
// Uses a companion Squid proxy container to allow connections ONLY to Atlassian domains.

// CRITICAL: Wrap everything in try/catch with immediate stderr output
// Console.error may be buffered and not flushed before exit
try {

const { spawn, execSync } = require("child_process");
const path = require("path");
const fs = require("fs");

// --- Logging helper ---
// Uses BOTH console.error and process.stderr.write for maximum visibility
// Flushes stderr after each write to ensure output appears immediately
function log(msg) {
  const line = `[eruditis-atlassian] ${msg}`;
  try {
    process.stderr.write(line + "\n");
    // Force flush on Windows (fd 2 is stderr)
    if (process.platform === "win32" && fs.fsyncSync) {
      try { fs.fsyncSync(2); } catch (_) {}
    }
  } catch (_) { /* ignore */ }
  try { console.error(line); } catch (_) { /* ignore */ }
}

// --- Version and startup diagnostics ---
let extensionVersion = "unknown";
try {
  const manifest = JSON.parse(
    fs.readFileSync(path.join(__dirname, "..", "manifest.json"), "utf-8")
  );
  extensionVersion = manifest.version || "unknown";
} catch (e) {
  log(`Warning: Could not read manifest.json: ${e.message}`);
}

log(`========================================`);
log(`STARTING v${extensionVersion}`);
log(`Node: ${process.version}`);
log(`Platform: ${process.platform} ${process.arch}`);
log(`CWD: ${process.cwd()}`);
log(`Script: ${__dirname}`);
log(`========================================`);

// --- Configuration ---
const IMAGE = "ghcr.io/troubladore/mcp-atlassian:v0.11.15";
const PROXY_IMAGE = "eruditis/atlassian-proxy:latest";
const PROXY_CONTAINER_NAME = "eruditis-atlassian-proxy";
const MCP_CONTAINER_NAME = "eruditis-atlassian-mcp";
const NETWORK_NAME = "eruditis-atlassian-net";
const PROXY_PORT = 3128;

// --- Check Docker availability early ---
log("Checking Docker availability...");
let dockerPath = "docker";
try {
  const whichCmd = process.platform === "win32" ? "where docker" : "which docker";
  log(`Running: ${whichCmd}`);
  dockerPath = execSync(whichCmd, { encoding: "utf-8", timeout: 5000 }).trim().split("\n")[0];
  log(`✓ Docker found at: ${dockerPath}`);

  log(`Checking Docker version...`);
  const dockerVersion = execSync(`"${dockerPath}" version --format "{{.Client.Version}}"`,
    { encoding: "utf-8", timeout: 10000 }).trim();
  log(`✓ Docker version: ${dockerVersion}`);
} catch (err) {
  log(`========================================`);
  log(`ERROR: Docker not found or not working`);
  log(`PATH: ${process.env.PATH || "(empty)"}`);
  log(`Error message: ${err.message}`);
  if (err.code) log(`Error code: ${err.code}`);
  if (err.stderr) log(`Stderr: ${err.stderr}`);
  log(`========================================`);
  log(`Please ensure Docker Desktop is installed and running.`);
  log(`Download from: https://docker.com/products/docker-desktop`);
  process.exit(1);
}

// Read config from environment (injected by Claude Desktop from user_config)
const ATLASSIAN_URL = process.env.ATLASSIAN_URL || "";
const ATLASSIAN_EMAIL = process.env.ATLASSIAN_EMAIL || "";
const ATLASSIAN_API_TOKEN = process.env.ATLASSIAN_API_TOKEN || "";
const ENABLE_WRITE = (process.env.ENABLE_WRITE_TOOLS || "false").toLowerCase() === "true";
const CONFLUENCE_SPACES_FILTER = process.env.CONFLUENCE_SPACES_FILTER || "";
const JIRA_PROJECTS_FILTER = process.env.JIRA_PROJECTS_FILTER || "";

// --- Validate required config ---
if (!ATLASSIAN_URL || !ATLASSIAN_EMAIL || !ATLASSIAN_API_TOKEN) {
  log("ERROR: Missing required configuration. Please configure your Atlassian URL, email, and API token in the extension settings.");
  log(`  ATLASSIAN_URL: ${ATLASSIAN_URL ? "set" : "MISSING"}`);
  log(`  ATLASSIAN_EMAIL: ${ATLASSIAN_EMAIL ? "set" : "MISSING"}`);
  log(`  ATLASSIAN_API_TOKEN: ${ATLASSIAN_API_TOKEN ? "set" : "MISSING"}`);
  process.exit(1);
}

// --- Helper Functions ---

/**
 * Check if a Docker image exists locally
 */
function imageExists(image) {
  try {
    execSync(`docker image inspect ${image}`, { stdio: "ignore" });
    return true;
  } catch (err) {
    return false;
  }
}

/**
 * Run a Docker command synchronously, logging output via log().
 * Replaces stdio:'inherit' which may not work in Claude Desktop's Node.js.
 */
function dockerExec(args, { ignoreErrors = false, timeout = 120000 } = {}) {
  const cmd = `docker ${args}`;
  try {
    const output = execSync(cmd, { encoding: "utf-8", timeout, stdio: ["ignore", "pipe", "pipe"] });
    if (output.trim()) log(output.trim());
    return output;
  } catch (err) {
    if (!ignoreErrors) {
      const stderr = err.stderr ? err.stderr.toString().trim() : "";
      if (stderr) log(`docker stderr: ${stderr}`);
      throw err;
    }
    return "";
  }
}

/**
 * Clean up old versions of our Docker images to prevent accumulation
 */
function cleanupOldImages() {
  try {
    log("Cleaning up old Docker images...");

    // Remove old mcp-atlassian images (keep only current version)
    const mcpImages = execSync(
      `docker images ghcr.io/troubladore/mcp-atlassian --format "{{.Repository}}:{{.Tag}}"`,
      { encoding: "utf-8", timeout: 10000 }
    ).trim().split("\n").filter(Boolean);

    for (const img of mcpImages) {
      if (img !== IMAGE && img.startsWith("ghcr.io/troubladore/mcp-atlassian:")) {
        log(`  Removing old image: ${img}`);
        execSync(`docker rmi ${img}`, { stdio: "ignore", timeout: 30000 });
      }
    }

    // Remove old proxy images that aren't the current tag
    // (there should only be one :latest, but stale tags can accumulate)
    const proxyImages = execSync(
      `docker images eruditis/atlassian-proxy --format "{{.Repository}}:{{.Tag}}"`,
      { encoding: "utf-8", timeout: 10000 }
    ).trim().split("\n").filter(Boolean);

    for (const img of proxyImages) {
      if (img !== PROXY_IMAGE && img !== "<none>:<none>") {
        log(`  Removing old proxy image: ${img}`);
        execSync(`docker rmi ${img}`, { stdio: "ignore", timeout: 30000 });
      }
    }

    // Clean up dangling images (orphaned layers from rebuilds)
    execSync(`docker image prune -f`, { stdio: "ignore", timeout: 30000 });

    log("Cleanup complete.");
  } catch (err) {
    // Don't fail startup if cleanup fails
    log(`Warning: Image cleanup failed (non-fatal): ${err.message}`);
  }
}

/**
 * Pull a Docker image with progress feedback
 */
function pullImage(image) {
  log(`Pulling Docker image ${image}...`);
  log("This may take a few moments on first run.");
  try {
    dockerExec(`pull ${image}`, { timeout: 300000 });
    log(`Successfully pulled ${image}`);
    return true;
  } catch (err) {
    log(`ERROR: Failed to pull Docker image: ${err.message}`);
    return false;
  }
}

/**
 * Check if proxy container is running
 */
function isProxyRunning() {
  try {
    const result = execSync(
      `docker ps --filter name=${PROXY_CONTAINER_NAME} --filter status=running --format "{{.Names}}"`,
      { encoding: "utf-8", timeout: 10000 }
    );
    return result.trim() === PROXY_CONTAINER_NAME;
  } catch (err) {
    return false;
  }
}

/**
 * Build the proxy Docker image from local Dockerfile
 */
function buildProxyImage() {
  // proxy/ is a sibling of server/, so go up one level
  const proxyDir = path.join(__dirname, "..", "proxy");
  const dockerfilePath = path.join(proxyDir, "Dockerfile");

  if (!fs.existsSync(dockerfilePath)) {
    log(`ERROR: Proxy Dockerfile not found at: ${dockerfilePath}`);
    log(`__dirname is: ${__dirname}`);
    log(`Looking for proxy in: ${proxyDir}`);
    log("The .mcpb package may be corrupted.");
    return false;
  }

  log("Building Atlassian filtering proxy image...");
  try {
    dockerExec(`build -t ${PROXY_IMAGE} "${proxyDir}"`, { timeout: 300000 });
    log("Proxy image built successfully.");
    return true;
  } catch (err) {
    log(`ERROR: Failed to build proxy image: ${err.message}`);
    return false;
  }
}

/**
 * Start the proxy container if not already running
 */
function ensureProxyRunning() {
  // Check if proxy is already running
  if (isProxyRunning()) {
    log("Atlassian filtering proxy already running.");
    return true;
  }

  // Check if old proxy container exists (stopped or running but unhealthy)
  try {
    const existingContainer = execSync(
      `docker ps -a --filter name=${PROXY_CONTAINER_NAME} --format "{{.Names}}"`,
      { encoding: "utf-8", timeout: 10000 }
    ).trim();

    if (existingContainer === PROXY_CONTAINER_NAME) {
      log("Removing existing proxy container...");
      execSync(`docker rm -f ${PROXY_CONTAINER_NAME}`, { stdio: "ignore", timeout: 10000 });
    }
  } catch (err) {
    // Container doesn't exist, that's fine
  }

  // Build proxy image if it doesn't exist
  if (!imageExists(PROXY_IMAGE)) {
    log("Proxy image not found locally. Building...");
    if (!buildProxyImage()) {
      return false;
    }
  }

  // Create Docker network for proxy and mcp-atlassian
  try {
    execSync(`docker network inspect ${NETWORK_NAME}`, { stdio: "ignore", timeout: 10000 });
  } catch (err) {
    // Network doesn't exist, create it
    log("Creating Docker network...");
    execSync(`docker network create ${NETWORK_NAME}`, { stdio: "ignore", timeout: 10000 });
  }

  // Start proxy container
  log("Starting Atlassian filtering proxy...");
  try {
    dockerExec(
      `run -d --name ${PROXY_CONTAINER_NAME} ` +
      `--restart=unless-stopped ` +
      `--network=${NETWORK_NAME} ` +
      `--cap-drop=ALL ` +
      `--security-opt no-new-privileges:true ` +
      `--read-only ` +
      `--tmpfs /var/cache/squid:noexec,nosuid,size=64m,uid=31,gid=31 ` +
      `--tmpfs /var/log/squid:noexec,nosuid,size=16m,uid=31,gid=31 ` +
      `--tmpfs /var/run/squid:noexec,nosuid,size=8m,uid=31,gid=31 ` +
      PROXY_IMAGE
    );
    log("Proxy started successfully.");

    // Wait for proxy to be ready (use Node.js sleep, not shell 'sleep' which may not exist on Windows)
    log("Waiting for proxy to be ready...");
    let attempts = 0;
    while (attempts < 10) {
      try {
        execSync(`docker exec ${PROXY_CONTAINER_NAME} nc -z 127.0.0.1 3128`, { stdio: "ignore", timeout: 5000 });
        log("Proxy is ready.");
        return true;
      } catch (err) {
        attempts++;
        // Cross-platform sleep: busy-wait 500ms via Node.js
        const end = Date.now() + 500;
        while (Date.now() < end) { /* spin */ }
      }
    }

    log("WARNING: Proxy may not be fully ready, but continuing...");
    return true;
  } catch (err) {
    log(`ERROR: Failed to start proxy container: ${err.message}`);
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
  "confluence_get_page_ancestors",
  "confluence_list_spaces",
  "confluence_get_space_page_tree",
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
  "confluence_move_page_position",
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

// 1. Remove any leftover containers FIRST so their images can be cleaned up.
//    Containers hold references to images, preventing `docker rmi`.
log("Removing stale containers from previous runs...");
for (const name of [MCP_CONTAINER_NAME, PROXY_CONTAINER_NAME]) {
  try {
    const exists = execSync(
      `docker ps -a --filter name=${name} --format "{{.Names}}"`,
      { encoding: "utf-8", timeout: 10000 }
    ).trim();
    if (exists === name) {
      log(`  Removing container: ${name}`);
      execSync(`docker rm -f ${name}`, { stdio: "ignore", timeout: 10000 });
    }
  } catch (err) {
    // Container doesn't exist, that's fine
  }
}

// 2. Pull the latest MCP server image
// ALWAYS pull to get updates when extension version changes
log(`Checking for updates to ${IMAGE}...`);
if (!pullImage(IMAGE)) {
  log("Failed to pull Docker image. Please check your internet connection and Docker installation.");
  process.exit(1);
}

// 3. Clean up old image versions to prevent accumulation
cleanupOldImages();

// 4. Ensure proxy container is running (network egress filtering)
if (!ensureProxyRunning()) {
  log("Failed to start filtering proxy. Extension cannot run without network restrictions.");
  process.exit(1);
}

log("Docker setup complete. Launching MCP server...");

// --- Build Docker args ---
const dockerArgs = [
  "run",
  "--rm",           // Remove container on exit
  "-i",             // Interactive (for stdio transport)
  "--name", MCP_CONTAINER_NAME, // Named container for easier debugging
  `--network=${NETWORK_NAME}`, // Isolated network with proxy (no published ports)
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
log(`Spawning: docker ${dockerArgs.slice(0, 5).join(" ")} ... ${IMAGE}`);
const child = spawn("docker", dockerArgs, {
  stdio: ["pipe", "pipe", "pipe"], // stdin: pipe, stdout: pipe, stderr: pipe
});

// Bridge stdin from Claude Desktop to Docker container
process.stdin.pipe(child.stdin);

// Bridge stdout from Docker container to Claude Desktop
child.stdout.pipe(process.stdout);

// Forward container stderr to our log (so Claude Desktop captures it)
child.stderr.on("data", (data) => {
  const lines = data.toString().split("\n").filter(Boolean);
  for (const line of lines) {
    log(`[container] ${line}`);
  }
});

// Handle process lifecycle
child.on("error", (err) => {
  log(`ERROR: Failed to start Docker container: ${err.message}`);
  if (err.code === "ENOENT") {
    log("Docker does not appear to be installed or is not in your PATH.");
    log("Install Docker Desktop from https://docker.com/products/docker-desktop");
  }
  process.exit(1);
});

child.on("exit", (code, signal) => {
  if (signal) {
    log(`Docker container killed by signal ${signal}`);
  } else if (code !== 0 && code !== null) {
    log(`Docker container exited with code ${code}`);
  } else {
    log("Docker container exited normally.");
  }
  process.exit(code || 0);
});

// Forward termination signals to the container
for (const sig of ["SIGINT", "SIGTERM", "SIGHUP"]) {
  process.on(sig, () => {
    log(`Received ${sig}, forwarding to container...`);
    child.kill(sig);
  });
}

// Handle stdin close (Claude Desktop disconnects)
process.stdin.on("end", () => {
  log("stdin closed (Claude Desktop disconnected).");
  child.stdin.end();
});

} catch (topLevelError) {
  // CRITICAL: Top-level catch for any synchronous errors during initialization
  // This ensures errors are visible even if they occur before event loop starts
  const msg = `[eruditis-atlassian] FATAL ERROR during initialization: ${topLevelError.message}`;
  const stack = `[eruditis-atlassian] Stack: ${topLevelError.stack}`;

  // Write directly to stderr file descriptor (most reliable)
  try {
    process.stderr.write(msg + "\n");
    process.stderr.write(stack + "\n");
    process.stderr.write("[eruditis-atlassian] ========================================\n");
  } catch (_) {}

  // Also try console.error
  try {
    console.error(msg);
    console.error(stack);
    console.error("[eruditis-atlassian] ========================================");
  } catch (_) {}

  process.exit(1);
}
