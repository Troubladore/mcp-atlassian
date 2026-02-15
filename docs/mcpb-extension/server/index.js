#!/usr/bin/env node

// eruditis-atlassian MCPB server entry point
// Spawns mcp-atlassian in a sandboxed Docker container and bridges stdio.

const { spawn } = require("child_process");

// --- Configuration ---
const IMAGE = "ghcr.io/sooperset/mcp-atlassian:v0.11.10";

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

// --- Build Docker args ---
const dockerArgs = [
  "run",
  "--rm",           // Remove container on exit
  "-i",             // Interactive (for stdio transport)
  "--network=bridge", // Default bridge network (outbound only, no host access)
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
