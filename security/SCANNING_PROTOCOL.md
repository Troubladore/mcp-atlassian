# Security Scanning Protocol

## Overview

This document defines the security scanning workflow for mcp-atlassian. All security findings must follow this protocol for consistent triage, documentation, and remediation.

---

## Scanning Tools

We use a **layered approach** with multiple tools to ensure comprehensive coverage:

### 1. Trivy (Primary Scanner)

**Purpose**: Container image and filesystem vulnerability scanning
**Scope**: Python dependencies (uv.lock), Docker images, configuration files
**Output**: `security/scans/trivy-YYYYMMDD.json`

```bash
# Scan dependencies for HIGH/CRITICAL vulnerabilities
trivy fs --scanners vuln,secret,misconfig --severity HIGH,CRITICAL .

# Detailed scan with all severities
trivy fs --scanners vuln --severity LOW,MEDIUM,HIGH,CRITICAL --format json uv.lock \
  > security/scans/trivy-$(date +%Y%m%d).json
```

**Why Primary**: Fast, comprehensive, regularly updated CVE database

### 2. pip-audit (Python-Specific)

**Purpose**: Python dependency vulnerability scanning using PyPI advisory database
**Scope**: Python packages from requirements/pyproject.toml
**Output**: `security/scans/pip-audit-YYYYMMDD.json`

```bash
# Run via uvx (no installation needed)
uvx pip-audit --format json --output security/scans/pip-audit-$(date +%Y%m%d).json

# Human-readable output
uvx pip-audit --desc
```

**Why Python-Specific**:
- Uses PyPI's advisory database (different source than Trivy)
- Understands Python packaging nuances (wheels, sdists, extras)
- Can detect malicious packages
- Suggests fix versions

**When to use**:
- Primary Python vulnerability check
- Cross-reference with Trivy findings
- Validate transitive dependency risks

### 3. Syft + Grype (Validation)

**Purpose**: Cross-validation and SBOM generation
**Scope**: Python packages, transitive dependencies
**Output**: `security/scans/sbom-YYYYMMDD.json`, `security/scans/grype-YYYYMMDD.json`

```bash
# Generate SBOM
syft packages . -o json > security/scans/sbom-$(date +%Y%m%d).json

# Scan SBOM with Grype
grype sbom:security/scans/sbom-$(date +%Y%m%d).json --only-fixed \
  -o json > security/scans/grype-$(date +%Y%m%d).json
```

**Why Validation**: Different vulnerability databases may catch different issues

### 4. Dependabot (GitHub Integration)

**Purpose**: Automated dependency monitoring
**Scope**: Python dependencies via GitHub security advisories
**Output**: GitHub web UI, API responses

```bash
# Check Dependabot alerts via GitHub CLI
gh api repos/$(gh repo view --json nameWithOwner -q .nameWithOwner)/dependabot/alerts \
  --jq '.[] | select(.state == "open")'
```

**Why Integration**: Automatic alerts, GitHub ecosystem integration

### 5. GitHub Code Scanning

**Purpose**: Static analysis of application code for security vulnerabilities
**Scope**: Python source code (src/, scripts/, tests/)
**Output**: GitHub web UI, API responses

```bash
# Check Code Scanning alerts via GitHub CLI
gh api repos/$(gh repo view --json nameWithOwner -q .nameWithOwner)/code-scanning/alerts \
  --jq '.[] | select(.state == "open") | {number, rule: .rule.id, severity: .rule.severity, location: .most_recent_instance.location.path}'

# Group by rule type
gh api repos/$(gh repo view --json nameWithOwner -q .nameWithOwner)/code-scanning/alerts \
  --jq 'group_by(.rule.id) | .[] | {rule: .[0].rule.id, severity: .[0].rule.severity, count: length}'
```

**Why Critical**: Catches application-level vulnerabilities that dependency scanners miss
- Clear-text logging of sensitive data
- ReDoS (Regular Expression Denial of Service)
- Incomplete URL sanitization (SSRF risks)
- SQL injection, XSS, command injection
- Authentication/authorization flaws

### 6. GitHub Secret Scanning

**Purpose**: Detect accidentally committed secrets and credentials
**Scope**: All files in repository, commit history
**Output**: GitHub web UI, API responses

```bash
# Check Secret Scanning alerts via GitHub CLI
gh api repos/$(gh repo view --json nameWithOwner -q .nameWithOwner)/secret-scanning/alerts \
  --jq '.[] | select(.state == "open") | {number, secret_type, location: .locations[0].details.path}'
```

**Why Critical**: Prevents credential leakage
- API keys, tokens, passwords in code
- AWS credentials, private keys
- Database connection strings
- OAuth secrets

---

## Scanning Workflow

### Step 1: Run Trivy Scan

```bash
# Quick scan for HIGH/CRITICAL
trivy fs --scanners vuln --severity HIGH,CRITICAL uv.lock

# Full scan with JSON output
trivy fs --scanners vuln --severity LOW,MEDIUM,HIGH,CRITICAL --format json uv.lock \
  > security/scans/trivy-$(date +%Y%m%d).json
```

**Record findings**: Note CVE IDs, packages, and severity levels
**Output location**: `security/scans/trivy-YYYYMMDD.json`

### Step 2: Run pip-audit (Python-Specific)

```bash
# Scan with JSON output
uvx pip-audit --format json --output security/scans/pip-audit-$(date +%Y%m%d).json

# Human-readable scan with descriptions
uvx pip-audit --desc
```

**Why run both Trivy and pip-audit**:
- Different vulnerability databases (Trivy: general CVE, pip-audit: PyPI advisory)
- pip-audit may catch Python-specific issues Trivy misses
- Provides suggested fix versions

**Output location**: `security/scans/pip-audit-YYYYMMDD.json`

### Step 3: Cross-Validate with Syft/Grype

```bash
# Generate fresh SBOM
syft packages . -o json > security/scans/sbom-$(date +%Y%m%d).json

# Scan with Grype
grype sbom:security/scans/sbom-$(date +%Y%m%d).json --only-fixed \
  -o json > security/scans/grype-$(date +%Y%m%d).json
```

**Compare**: Check if Grype identifies same vulnerabilities as Trivy/pip-audit
**Output locations**:
- `security/scans/sbom-YYYYMMDD.json`
- `security/scans/grype-YYYYMMDD.json`

### Step 4: Check Dependabot Alerts

```bash
# List open alerts with key details
gh api repos/$(gh repo view --json nameWithOwner -q .nameWithOwner)/dependabot/alerts \
  --jq '.[] | select(.state == "open") | {number, package: .dependency.package.name, severity: .security_advisory.severity, cve: .security_advisory.cve_id}'
```

**Correlate**: Match Dependabot alerts with Trivy/pip-audit/Grype findings
**Output location**: GitHub web UI, no file output

### Step 5: Check GitHub Code Scanning

```bash
# List all open code scanning alerts
gh api repos/$(gh repo view --json nameWithOwner -q .nameWithOwner)/code-scanning/alerts \
  --jq '.[] | select(.state == "open") | {number, rule: .rule.id, severity: .rule.severity, description: .rule.description, location: .most_recent_instance.location.path}'

# Group by severity
gh api repos/$(gh repo view --json nameWithOwner -q .nameWithOwner)/code-scanning/alerts \
  --jq '.[] | select(.state == "open")' | jq -s 'group_by(.rule.severity) | .[] | {severity: .[0].rule.severity, count: length}'
```

**Priority**: Fix ERROR severity first, then WARNING
**Common issues**:
- Clear-text logging of secrets
- Regular expression DoS (ReDoS)
- URL validation bypass
- Injection vulnerabilities

**Output location**: GitHub web UI, no file output

### Step 6: Check GitHub Secret Scanning

```bash
# List open secret scanning alerts
gh api repos/$(gh repo view --json nameWithOwner -q .nameWithOwner)/secret-scanning/alerts \
  --jq '.[] | select(.state == "open") | {number, secret_type, state, created_at, location: .locations[0].details.path}'
```

**Action Required**: ALL secret scanning alerts must be addressed immediately
- Rotate compromised credentials
- Remove secrets from code
- Update to use environment variables or secret management

**Output location**: GitHub web UI, no file output

### Step 7: Consolidate Findings

Create a consolidated view of all unique vulnerabilities:

```bash
# Extract CVEs from each tool
jq -r '.Results[].Vulnerabilities[]?.VulnerabilityID' security/scans/trivy-*.json | sort -u > /tmp/trivy-cves.txt
jq -r '.[].vulnerabilities[]?.id' security/scans/pip-audit-*.json | sort -u > /tmp/pip-audit-cves.txt
jq -r '.matches[]?.vulnerability.id' security/scans/grype-*.json | sort -u > /tmp/grype-cves.txt

# Find unique and overlapping CVEs
comm -12 /tmp/trivy-cves.txt /tmp/pip-audit-cves.txt  # Both found
comm -23 /tmp/trivy-cves.txt /tmp/pip-audit-cves.txt  # Trivy only
comm -13 /tmp/trivy-cves.txt /tmp/pip-audit-cves.txt  # pip-audit only
```

**Track findings by tool**:
- If all tools agree: High confidence finding
- If only one tool reports: May be false positive, investigate further
- If pip-audit finds but Trivy doesn't: Python-specific issue, trust pip-audit

### Step 8: Triage and Document

For each unique vulnerability:

1. **Assess exploitability** (see Triage Checklist below)
2. **Document findings** in `security/assessments/CVE-YYYY-NNNNN-{package}.md`
3. **Determine action** (remediate, monitor, accept risk)
4. **Update tracking** (see `security/README.md`)

---

## Triage Checklist

For each vulnerability, answer these questions:

### 1. Is the vulnerable code reachable?

```bash
# Search for package usage in codebase
rg "from.*{package}|import.*{package}" src/

# Check if package is imported indirectly
uv tree | rg "{package}" -B 5
```

**If NO imports found**: Likely not exploitable (document why)

### 2. Does the application use the vulnerable feature?

Example: A caching library with pickle vulnerability is only exploitable if:
- Application instantiates the cache
- Application uses disk-based caching (not in-memory)
- Application deserializes untrusted data

**Check**:
- Read package documentation
- Search for feature-specific APIs (e.g., `DiskStore`, `pickle`, etc.)

### 3. What are the attack requirements?

- **Local vs Remote**: Can attacker trigger remotely or need local access?
- **Authentication**: Does attacker need valid credentials?
- **Privileges**: Does attacker need elevated permissions?
- **User Interaction**: Does vulnerability require user action?

### 4. What is the impact in our context?

Consider:
- **Deployment environment**: Docker containers are isolated
- **Network exposure**: Services behind firewalls, API gateways
- **Data sensitivity**: What data could be compromised?
- **Blast radius**: Single container vs entire cluster

### 5. Is there a patch available?

```bash
# Check if newer version fixes the issue
uv lock --upgrade-package {package}
uv tree | rg "{package}"
```

**If YES**: Apply patch and test
**If NO**: Document and monitor (set calendar reminder)

---

## Documentation Template

When creating `security/assessments/CVE-YYYY-NNNNN-{package}.md`:

```markdown
# CVE-YYYY-NNNNN: {Package Name} - {Vulnerability Title}

## Executive Summary

**Status**: ✅ NOT EXPLOITABLE | ⚠️ MONITOR | 🔴 REQUIRES ACTION
**Risk Level**: LOW | MEDIUM | HIGH | CRITICAL
**Action Required**: {brief description}

---

## Vulnerability Details

- **CVE**: CVE-YYYY-NNNNN
- **Package**: {package} v{version}
- **Dependency Type**: Direct | Transitive (via {parent})
- **Severity**: {CVSS score} ({rating})
- **Type**: {vulnerability type}
- **Patched Version**: {version} | None available

## Dependency Chain

\`\`\`
{show full dependency path}
\`\`\`

## Exploitability Analysis

### Code Usage

{Show grep results, explain if/how package is used}

### Attack Requirements

{Document what attacker needs to exploit}

### Risk Assessment

{Explain actual risk in deployment context}

## Recommended Action

{Clear action items with timeline}

## References

- CVE: {link}
- Advisory: {link}
- Trivy scan: `security/scans/trivy-YYYYMMDD.json`
- Dependabot: {link if applicable}
```

---

## Remediation Priority

| Priority | Criteria | Timeline |
|----------|----------|----------|
| **P0 (Critical)** | Exploitable remotely, no auth required, RCE/data breach | Immediate (same day) |
| **P1 (High)** | Exploitable with low privileges, significant impact | 1-3 days |
| **P2 (Medium)** | Requires elevated privileges or user interaction | 1-2 weeks |
| **P3 (Low)** | Theoretical risk, not exploitable in practice | Next maintenance window |
| **P4 (Monitor)** | Vulnerable code not used, no patch available yet | Monitor for patch |

---

## Closing Dependabot Alerts

When dismissing a Dependabot alert:

### 1. Document First

Create assessment in `security/assessments/` with full analysis

### 2. Dismiss with Reason

```bash
# Get alert number
gh api repos/$(gh repo view --json nameWithOwner -q .nameWithOwner)/dependabot/alerts \
  --jq '.[] | select(.state == "open") | {number, cve: .security_advisory.cve_id}'

# Dismiss with documented reason
gh api -X PATCH repos/$(gh repo view --json nameWithOwner -q .nameWithOwner)/dependabot/alerts/{number} \
  -f state=dismissed \
  -f dismissed_reason="{reason}" \
  -f dismissed_comment="See security/assessments/CVE-YYYY-NNNNN-{package}.md for full analysis."
```

**Valid dismissal reasons**:
- `no_bandwidth` - Will address later (P3/P4)
- `tolerable_risk` - Risk accepted (P4, not exploitable)
- `inaccurate` - False positive
- `fix_started` - Patch in progress

**For not exploitable vulnerabilities**: Use `tolerable_risk` with detailed comment

### 3. Update Security Tracker

Add entry to `security/README.md` under "Dismissed Alerts"

---

## Scan Schedule

| Scan Type | Frequency | Trigger |
|-----------|-----------|---------|
| **Trivy Quick** | Before each commit | Manual |
| **Full Trivy + Grype** | Weekly | Automated (GitHub Actions) |
| **Dependabot** | Continuous | Automatic |
| **SBOM Generation** | On release | Automated (CI/CD) |

---

## Tool Installation

### uv (Required for uvx)

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version
```

**Note**: `uvx` is included with `uv` and requires no separate installation.

### pip-audit (via uvx - No Installation Needed)

```bash
# pip-audit runs via uvx automatically
uvx pip-audit --version

# No pip install needed - uvx handles it
```

**Why uvx**:
- No global installation required
- Isolated execution environment
- Always uses latest version
- No dependency conflicts

### Trivy

```bash
# Ubuntu/Debian
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | sudo tee -a /etc/apt/sources.list.d/trivy.list
sudo apt update && sudo apt install trivy

# macOS
brew install trivy
```

### Syft + Grype

```bash
# Ubuntu/Debian
curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin
curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin

# macOS
brew install syft grype
```

### GitHub CLI (gh)

```bash
# Ubuntu/Debian
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list
sudo apt update && sudo apt install gh

# macOS
brew install gh
```

---

## Best Practices

1. **Scan early, scan often**: Run Trivy before committing changes with new dependencies
2. **Context matters**: CVSS scores don't tell the full story - assess actual risk
3. **Document everything**: Future you will thank present you
4. **Monitor, don't panic**: Not every CVE requires immediate action
5. **Defense in depth**: Multiple scanners catch different issues
6. **Track dismissals**: Keep record of why alerts were closed

---

## See Also

- `security/README.md` - Vulnerability tracking and triage guidance
- `security/assessments/` - Individual CVE analyses
- `security/scans/` - Historical scan results (not committed to git)
