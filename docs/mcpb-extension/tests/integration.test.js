#!/usr/bin/env node
// Integration tests for the mcpb-extension.
// These require Docker to be running. Run with:
//   node --test tests/integration.test.js
//
// Tests are ordered: proxy build -> proxy runtime -> mcp-atlassian e2e

const { describe, it, before, after } = require("node:test");
const assert = require("node:assert/strict");
const { execSync, spawn } = require("node:child_process");
const path = require("node:path");

const ROOT = path.resolve(__dirname, "..");
const PROXY_DIR = path.join(ROOT, "proxy");
const PROXY_IMAGE = "eruditis/atlassian-proxy:test";
const PROXY_CONTAINER = "mcpb-test-proxy";
const NETWORK = "mcpb-test-net";
const MCP_IMAGE = "ghcr.io/troubladore/mcp-atlassian:v0.11.10";

function exec(cmd, opts = {}) {
  return execSync(cmd, { encoding: "utf-8", timeout: 120000, ...opts }).trim();
}

function execQuiet(cmd) {
  try {
    return exec(cmd, { stdio: "pipe" });
  } catch (e) {
    return e.stderr || e.stdout || e.message;
  }
}

// =============================================================================
// Proxy Docker build
// =============================================================================
describe("proxy Docker image", () => {
  it("builds successfully from proxy/Dockerfile", () => {
    const output = exec(
      `docker build -t ${PROXY_IMAGE} ${PROXY_DIR} 2>&1`
    );
    assert.ok(
      output.includes("naming to") || output.includes("exporting to image"),
      `Docker build did not complete successfully:\n${output.slice(-500)}`
    );
  });
});

// =============================================================================
// Proxy container runtime
// =============================================================================
describe("proxy container runtime", () => {
  before(() => {
    // Clean up any leftover test containers/networks
    execQuiet(`docker rm -f ${PROXY_CONTAINER}`);
    execQuiet(`docker network rm ${NETWORK}`);
    exec(`docker network create ${NETWORK}`);
  });

  after(() => {
    execQuiet(`docker rm -f ${PROXY_CONTAINER}`);
    execQuiet(`docker network rm ${NETWORK}`);
  });

  it("starts and stays running with read-only filesystem and hardened tmpfs", () => {
    exec(
      `docker run -d --name ${PROXY_CONTAINER} \
        --network=${NETWORK} \
        --cap-drop=ALL \
        --security-opt no-new-privileges:true \
        --read-only \
        --tmpfs /var/cache/squid:noexec,nosuid,size=64m,uid=31,gid=31 \
        --tmpfs /var/log/squid:noexec,nosuid,size=16m,uid=31,gid=31 \
        --tmpfs /var/run/squid:noexec,nosuid,size=8m,uid=31,gid=31 \
        ${PROXY_IMAGE}`
    );

    // Wait for container to stabilize
    execSync("sleep 3");

    const status = exec(
      `docker inspect ${PROXY_CONTAINER} --format "{{.State.Status}}"`
    );
    assert.equal(status, "running", `Proxy container is not running (status: ${status})`);
  });

  it("listens on port 3128", () => {
    const result = exec(
      `docker exec ${PROXY_CONTAINER} nc -z 127.0.0.1 3128 && echo OK`
    );
    assert.equal(result, "OK", "Proxy not listening on port 3128");
  });

  it("runs as non-root user", () => {
    const user = exec(
      `docker exec ${PROXY_CONTAINER} whoami 2>/dev/null || docker exec ${PROXY_CONTAINER} id -un`
    );
    assert.notEqual(user, "root", "Proxy must not run as root");
  });

  it("has security hardening applied", () => {
    const inspect = exec(
      `docker inspect ${PROXY_CONTAINER} --format "{{json .HostConfig.SecurityOpt}} {{json .HostConfig.CapDrop}} {{json .HostConfig.ReadonlyRootfs}}"`
    );
    assert.ok(inspect.includes("no-new-privileges"), "Missing no-new-privileges");
    assert.ok(inspect.includes("ALL"), "Missing cap-drop ALL");
    assert.ok(inspect.includes("true"), "Missing read-only rootfs");
  });
});

// =============================================================================
// MCP end-to-end
// =============================================================================
describe("mcp-atlassian end-to-end", () => {
  before(() => {
    // Ensure proxy and network are running from previous suite
    // If previous suite cleaned up, recreate
    execQuiet(`docker network create ${NETWORK}`);
    const proxyRunning = execQuiet(
      `docker ps --filter name=${PROXY_CONTAINER} --filter status=running -q`
    );
    if (!proxyRunning) {
      execQuiet(`docker rm -f ${PROXY_CONTAINER}`);
      exec(
        `docker run -d --name ${PROXY_CONTAINER} \
          --network=${NETWORK} \
          --cap-drop=ALL \
          --security-opt no-new-privileges:true \
          --read-only \
          --tmpfs /var/cache/squid:noexec,nosuid,size=64m,uid=31,gid=31 \
          --tmpfs /var/log/squid:noexec,nosuid,size=16m,uid=31,gid=31 \
          --tmpfs /var/run/squid:noexec,nosuid,size=8m,uid=31,gid=31 \
          ${PROXY_IMAGE}`
      );
      execSync("sleep 3");
    }
  });

  after(() => {
    // Final cleanup
    execQuiet(`docker rm -f ${PROXY_CONTAINER}`);
    execQuiet(`docker network rm ${NETWORK}`);
  });

  it("mcp-atlassian image exists locally", () => {
    const result = execQuiet(`docker image inspect ${MCP_IMAGE} 2>&1`);
    assert.ok(
      !result.includes("No such image"),
      `Image ${MCP_IMAGE} not found locally. Run: docker build -t ${MCP_IMAGE} . from repo root`
    );
  });

  it("responds to MCP initialize with valid protocol response", () => {
    const initMsg = JSON.stringify({
      method: "initialize",
      params: {
        protocolVersion: "2024-11-05",
        capabilities: {},
        clientInfo: { name: "test", version: "0.1.0" },
      },
      jsonrpc: "2.0",
      id: 0,
    });

    const output = exec(
      `echo '${initMsg}' | timeout 15 docker run --rm -i \
        --network=${NETWORK} \
        --cap-drop=ALL \
        --security-opt no-new-privileges:true \
        --read-only \
        --tmpfs /tmp:noexec,nosuid,size=64m \
        --memory=256m \
        --cpus=0.5 \
        -e CONFLUENCE_URL=https://test.atlassian.net/wiki \
        -e CONFLUENCE_USERNAME=test@test.com \
        -e CONFLUENCE_API_TOKEN=fake-token \
        -e JIRA_URL=https://test.atlassian.net \
        -e JIRA_USERNAME=test@test.com \
        -e JIRA_API_TOKEN=fake-token \
        -e ENABLED_TOOLS=confluence_search \
        -e HTTP_PROXY=http://${PROXY_CONTAINER}:3128 \
        -e HTTPS_PROXY=http://${PROXY_CONTAINER}:3128 \
        -e NO_PROXY=localhost,127.0.0.1 \
        ${MCP_IMAGE} 2>/dev/null`,
      { timeout: 30000 }
    );

    // Parse the JSON response
    let response;
    try {
      response = JSON.parse(output.split("\n")[0]);
    } catch (e) {
      assert.fail(`Failed to parse MCP response as JSON: ${output.slice(0, 200)}`);
    }

    assert.equal(response.jsonrpc, "2.0", "Must be JSON-RPC 2.0");
    assert.equal(response.id, 0, "Must respond to id 0");
    assert.ok(response.result, "Must have a result field");
    assert.ok(
      response.result.serverInfo,
      "Must include serverInfo"
    );
    assert.ok(
      response.result.protocolVersion,
      "Must include protocolVersion"
    );
  });
});

// =============================================================================
// Claude Desktop simulation - test with restricted PATH
// =============================================================================
describe("server/index.js startup behavior (Claude Desktop simulation)", () => {
  it("produces diagnostic output even when Docker is missing from PATH", function(t, done) {
    // Simulate Claude Desktop's built-in Node.js which may not have docker in PATH
    // Find where node is, but remove docker paths
    const nodePath = execSync("which node", { encoding: "utf-8" }).trim();
    const nodeDir = path.dirname(nodePath);
    const restrictedPath = `${nodeDir}:/usr/bin:/bin`; // Keep node but remove /usr/local/bin where docker often lives

    const child = spawn(nodePath, [path.join(ROOT, "server/index.js")], {
      env: {
        ...process.env,
        PATH: restrictedPath,
        // Provide required config to pass validation
        ATLASSIAN_URL: "https://test.atlassian.net",
        ATLASSIAN_EMAIL: "test@test.com",
        ATLASSIAN_API_TOKEN: "fake-token",
      },
      stdio: ["ignore", "pipe", "pipe"],
      timeout: 10000,
    });

    let stdout = "";
    let stderr = "";

    child.stdout.on("data", (data) => {
      stdout += data.toString();
    });

    child.stderr.on("data", (data) => {
      stderr += data.toString();
    });

    child.on("close", (code) => {
      // Should exit with error code (Docker not found)
      assert.ok(code !== 0, `Expected non-zero exit code, got ${code}`);

      const output = stderr + stdout;

      // CRITICAL: Must see our diagnostic output
      assert.ok(
        output.includes("[eruditis-atlassian]"),
        `No diagnostic output found. Output:\n${output.slice(0, 500)}`
      );

      // Must see version banner
      assert.ok(
        output.includes("STARTING v1.0.3") || output.includes("STARTING v"),
        `Version banner not found. Output:\n${output.slice(0, 500)}`
      );

      // Must see Docker check step
      assert.ok(
        output.includes("Checking Docker availability") || output.includes("Docker"),
        `Docker check not logged. Output:\n${output.slice(0, 500)}`
      );

      // If Docker is actually missing, should see error
      if (!output.includes("✓ Docker found")) {
        assert.ok(
          output.includes("ERROR") || output.includes("not found"),
          `Missing Docker error message. Output:\n${output.slice(0, 500)}`
        );
      }

      done();
    });

    child.on("error", (err) => {
      assert.fail(`Process spawn failed: ${err.message}`);
    });
  });
});
