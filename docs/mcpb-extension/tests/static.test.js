#!/usr/bin/env node
// Static analysis tests for the mcpb-extension.
// These validate config files and scripts for known pitfalls
// without requiring Docker. Run with: node --test tests/

const { describe, it } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const ROOT = path.resolve(__dirname, "..");

// --- Helper: read file relative to extension root ---
function readFile(relPath) {
  return fs.readFileSync(path.join(ROOT, relPath), "utf-8");
}

// =============================================================================
// squid.conf tests
// =============================================================================
describe("proxy/squid.conf", () => {
  const conf = readFile("proxy/squid.conf");

  it("has no redundant domain entries that Squid 6.6 rejects", () => {
    // Squid 6.6 treats '.example.com' as covering 'example.com' and
    // 'sub.example.com'. Having both '.example.com' and 'example.com'
    // in the same ACL is a FATAL error.
    const domainLines = conf
      .split("\n")
      .filter((line) => line.match(/^\s*acl\s+\S+\s+dstdomain\s+/))
      .map((line) => {
        const parts = line.trim().split(/\s+/);
        return { acl: parts[1], domain: parts[3] };
      });

    // Group by ACL name
    const aclGroups = {};
    for (const { acl, domain } of domainLines) {
      if (!aclGroups[acl]) aclGroups[acl] = [];
      aclGroups[acl].push(domain);
    }

    // For each ACL, check that no wildcard domain (starting with '.')
    // has a redundant bare or sub-domain entry
    for (const [acl, domains] of Object.entries(aclGroups)) {
      const wildcards = domains.filter((d) => d.startsWith("."));
      for (const wildcard of wildcards) {
        const baseDomain = wildcard.slice(1); // '.atlassian.com' -> 'atlassian.com'
        for (const domain of domains) {
          if (domain === wildcard) continue;
          // Check if this domain is covered by the wildcard
          if (domain === baseDomain || domain.endsWith(baseDomain)) {
            assert.fail(
              `ACL '${acl}': domain '${domain}' is redundant — already covered by wildcard '${wildcard}'. ` +
                `Squid 6.6 treats this as a fatal error.`
            );
          }
        }
      }
    }
  });

  it("sets pid_filename to a path under /var/run/squid/ (writable tmpfs)", () => {
    const pidLine = conf
      .split("\n")
      .find((line) => line.match(/^\s*pid_filename\s+/));
    assert.ok(pidLine, "squid.conf must set pid_filename explicitly");
    const pidPath = pidLine.trim().split(/\s+/)[1];
    assert.ok(
      pidPath.startsWith("/var/run/squid/"),
      `pid_filename must be under /var/run/squid/ (writable tmpfs), got: ${pidPath}`
    );
  });

  it("does not define a custom localhost ACL (uses Squid built-in)", () => {
    // Squid has a built-in 'localhost' ACL. Redefining it causes warnings.
    const localhostAcl = conf
      .split("\n")
      .find((line) => line.match(/^\s*acl\s+localhost\s+src\s+/));
    assert.equal(
      localhostAcl,
      undefined,
      `squid.conf should not redefine 'acl localhost src ...' — Squid has a built-in localhost ACL. ` +
        `Found: ${localhostAcl}`
    );
  });

  it("listens on port 3128", () => {
    assert.match(conf, /http_port\s+3128/, "Must listen on port 3128");
  });

  it("denies all traffic by default", () => {
    assert.match(
      conf,
      /http_access\s+deny\s+all/,
      "Must have a default deny rule"
    );
  });

  it("only allows Atlassian domains", () => {
    // Collect all 'http_access allow' rules (excluding localhost)
    const allowRules = conf
      .split("\n")
      .filter((line) => line.match(/^\s*http_access\s+allow\s+/))
      .filter((line) => !line.includes("localhost"));

    assert.equal(
      allowRules.length,
      1,
      `Expected exactly 1 non-localhost allow rule, got ${allowRules.length}: ${allowRules.join(", ")}`
    );
    assert.match(
      allowRules[0],
      /atlassian_cloud/,
      "The only allow rule must reference atlassian_cloud ACL"
    );
  });

  it("blocks direct IP access", () => {
    assert.match(
      conf,
      /http_access\s+deny\s+numeric_IPs/,
      "Must block direct IP access to prevent domain filter bypass"
    );
  });
});

// =============================================================================
// server/index.js tests
// =============================================================================
describe("server/index.js", () => {
  const serverJs = readFile("server/index.js");

  it("references troubladore image (not upstream sooperset)", () => {
    assert.match(
      serverJs,
      /ghcr\.io\/troubladore\/mcp-atlassian/,
      "IMAGE must reference ghcr.io/troubladore/mcp-atlassian"
    );
    assert.doesNotMatch(
      serverJs,
      /ghcr\.io\/sooperset\/mcp-atlassian/,
      "Must NOT reference upstream ghcr.io/sooperset/mcp-atlassian"
    );
  });

  it("pins image to a specific version tag (not :latest)", () => {
    const imageMatch = serverJs.match(
      /const\s+IMAGE\s*=\s*"([^"]+)"/
    );
    assert.ok(imageMatch, "IMAGE constant must be defined");
    const image = imageMatch[1];
    assert.ok(
      !image.endsWith(":latest"),
      `IMAGE must be pinned to a specific version, got: ${image}`
    );
    assert.match(
      image,
      /:\S+$/,
      `IMAGE must include a version tag, got: ${image}`
    );
  });

  it("drops all capabilities (--cap-drop=ALL)", () => {
    // Must appear in both proxy and mcp-atlassian container commands
    const capDropCount = (serverJs.match(/--cap-drop=ALL/g) || []).length;
    assert.ok(
      capDropCount >= 2,
      `Expected --cap-drop=ALL at least twice (proxy + main container), found ${capDropCount}`
    );
  });

  it("sets no-new-privileges on all containers", () => {
    const secOptCount = (
      serverJs.match(/no-new-privileges:true/g) || []
    ).length;
    assert.ok(
      secOptCount >= 2,
      `Expected no-new-privileges:true at least twice, found ${secOptCount}`
    );
  });

  it("uses read-only filesystem on all containers", () => {
    const readOnlyCount = (serverJs.match(/--read-only/g) || []).length;
    assert.ok(
      readOnlyCount >= 2,
      `Expected --read-only at least twice, found ${readOnlyCount}`
    );
  });

  it("has no volume mounts (-v)", () => {
    // Look for docker run with -v flag (but not inside comments)
    const codeLines = serverJs
      .split("\n")
      .filter((line) => !line.trim().startsWith("//"));
    const volumeMounts = codeLines.filter((line) =>
      line.match(/\s-v\s+\S+:\S+/)
    );
    assert.equal(
      volumeMounts.length,
      0,
      `Found volume mounts that expose host filesystem: ${volumeMounts.join(", ")}`
    );
  });

  it("has no host network mode", () => {
    const codeLines = serverJs
      .split("\n")
      .filter((line) => !line.trim().startsWith("//"));
    const hostNet = codeLines.filter((line) =>
      line.includes("--network=host")
    );
    assert.equal(
      hostNet.length,
      0,
      "Must not use --network=host (breaks proxy isolation)"
    );
  });

  it("sets uid/gid on proxy tmpfs mounts (squid runs as uid 31)", () => {
    // All proxy tmpfs lines must include uid=31,gid=31
    const proxyTmpfsLines = serverJs
      .split("\n")
      .filter(
        (line) =>
          line.includes("--tmpfs /var/") && line.includes("squid")
      );
    assert.ok(
      proxyTmpfsLines.length >= 3,
      `Expected at least 3 proxy tmpfs mounts, found ${proxyTmpfsLines.length}`
    );
    for (const line of proxyTmpfsLines) {
      assert.match(
        line,
        /uid=31/,
        `Proxy tmpfs mount missing uid=31: ${line.trim()}`
      );
      assert.match(
        line,
        /gid=31/,
        `Proxy tmpfs mount missing gid=31: ${line.trim()}`
      );
    }
  });

  it("never exposes delete operations in tool arrays", () => {
    // Filter out comment lines — the comment documenting what's excluded is fine
    const codeLines = serverJs
      .split("\n")
      .filter((line) => !line.trim().startsWith("//"))
      .join("\n");
    assert.doesNotMatch(
      codeLines,
      /jira_delete_issue/,
      "jira_delete_issue must never appear in tool arrays"
    );
    assert.doesNotMatch(
      codeLines,
      /confluence_delete_page/,
      "confluence_delete_page must never appear in tool arrays"
    );
  });

  it("defaults write tools to disabled", () => {
    assert.match(
      serverJs,
      /["']false["']/,
      "ENABLE_WRITE must default to 'false'"
    );
  });

  it("has a log() helper that writes to both stderr and console.error", () => {
    assert.match(
      serverJs,
      /function\s+log\s*\(/,
      "Must define a log() helper function"
    );
    assert.match(
      serverJs,
      /console\.error/,
      "log() must use console.error (reliably captured by Claude Desktop)"
    );
  });

  it("has global uncaughtException handler", () => {
    assert.match(
      serverJs,
      /process\.on\s*\(\s*["']uncaughtException["']/,
      "Must register uncaughtException handler for diagnostic visibility"
    );
  });

  it("reads version from manifest.json on startup", () => {
    assert.match(
      serverJs,
      /manifest\.json/,
      "Must read manifest.json for version logging"
    );
    assert.match(
      serverJs,
      /extensionVersion/,
      "Must extract and log extension version"
    );
  });

  it("checks Docker availability before proceeding", () => {
    // Must check for docker binary before attempting any docker operations
    assert.match(
      serverJs,
      /where docker|which docker/,
      "Must check if docker is in PATH (cross-platform)"
    );
  });

  it("does not use stdio inherit for execSync (breaks in Claude Desktop)", () => {
    // stdio: 'inherit' in execSync doesn't work in Claude Desktop's headless Node.js.
    // All execSync calls should use 'ignore', 'pipe', or the dockerExec helper.
    const codeLines = serverJs
      .split("\n")
      .filter((line) => !line.trim().startsWith("//"));
    const inheritLines = codeLines.filter((line) =>
      line.includes("execSync") && line.includes("'inherit'")
    );
    assert.equal(
      inheritLines.length,
      0,
      `Found execSync with stdio:'inherit' which breaks in Claude Desktop: ${inheritLines.join("; ")}`
    );
  });

  it("does not use shell sleep command (not available on Windows)", () => {
    const codeLines = serverJs
      .split("\n")
      .filter((line) => !line.trim().startsWith("//"));
    const sleepLines = codeLines.filter((line) =>
      line.match(/execSync\s*\(\s*["']sleep/)
    );
    assert.equal(
      sleepLines.length,
      0,
      `Found shell 'sleep' command which is not available on Windows: ${sleepLines.join("; ")}`
    );
  });
});

// =============================================================================
// manifest.json tests
// =============================================================================
describe("manifest.json", () => {
  const manifest = JSON.parse(readFile("manifest.json"));

  it("marks API token as sensitive", () => {
    assert.ok(
      manifest.user_config?.atlassian_api_token?.sensitive === true,
      "atlassian_api_token must have sensitive: true"
    );
  });

  it("defaults write tools to false", () => {
    assert.equal(
      manifest.user_config?.enable_write_tools?.default,
      "false",
      "enable_write_tools must default to 'false'"
    );
  });

  it("has a pinned version (not 0.0.0)", () => {
    assert.ok(
      manifest.version && manifest.version !== "0.0.0",
      `manifest version must be set, got: ${manifest.version}`
    );
  });

  it("uses correct extension name", () => {
    assert.equal(
      manifest.name,
      "eruditis-atlassian",
      "Extension name must be eruditis-atlassian"
    );
  });
});
