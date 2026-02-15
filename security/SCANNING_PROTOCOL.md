# Security Scanning Protocol

## Overview

This document defines the security scanning workflow for mcp-atlassian. All security findings must follow this protocol for consistent triage, documentation, and remediation.

---

## Scanning Tools

We use a **layered approach** with multiple tools to ensure comprehensive coverage:

### 1. Trivy (Primary Scanner)

**Purpose**: Container image and filesystem vulnerability scanning
**Scope**: Python dependencies (uv.lock), Docker images, configuration files

```bash
# Scan dependencies for HIGH/CRITICAL vulnerabilities
trivy fs --scanners vuln,secret,misconfig --severity HIGH,CRITICAL .

# Detailed scan with all severities
trivy fs --scanners vuln --severity LOW,MEDIUM,HIGH,CRITICAL uv.lock
```

**Why Primary**: Fast, comprehensive, regularly updated CVE database

### 2. Syft + Grype (Validation)

**Purpose**: Cross-validation and SBOM generation
**Scope**: Python packages, transitive dependencies

```bash
# Generate SBOM
syft packages . -o json > security/scans/sbom-$(date +%Y%m%d).json

# Scan SBOM with Grype
grype sbom:security/scans/sbom-*.json --only-fixed
```

**Why Validation**: Different vulnerability databases may catch different issues

### 3. Dependabot (GitHub Integration)

**Purpose**: Automated dependency monitoring
**Scope**: Python dependencies via GitHub security advisories

```bash
# Check Dependabot alerts via GitHub CLI
gh api repos/$(gh repo view --json nameWithOwner -q .nameWithOwner)/dependabot/alerts \
  --jq '.[] | select(.state == "open")'
```

**Why Integration**: Automatic alerts, GitHub ecosystem integration

---

## Scanning Workflow

### Step 1: Run Trivy Scan

```bash
# Quick scan for HIGH/CRITICAL
trivy fs --scanners vuln --severity HIGH,CRITICAL uv.lock

# Full scan with context
trivy fs --scanners vuln --severity LOW,MEDIUM,HIGH,CRITICAL --format json uv.lock \
  > security/scans/trivy-$(date +%Y%m%d).json
```

**Record findings**: Note CVE IDs, packages, and severity levels

### Step 2: Cross-Validate with Syft/Grype

```bash
# Generate fresh SBOM
syft packages . -o json > security/scans/sbom-$(date +%Y%m%d).json

# Scan with Grype
grype sbom:security/scans/sbom-$(date +%Y%m%d).json --only-fixed \
  -o json > security/scans/grype-$(date +%Y%m%d).json
```

**Compare**: Check if Grype identifies same vulnerabilities as Trivy

### Step 3: Check Dependabot Alerts

```bash
# List open alerts
gh api repos/$(gh repo view --json nameWithOwner -q .nameWithOwner)/dependabot/alerts \
  --jq '.[] | select(.state == "open") | {number, package: .dependency.package.name, severity: .security_advisory.severity, cve: .security_advisory.cve_id}'
```

**Correlate**: Match Dependabot alerts with Trivy/Grype findings

### Step 4: Triage and Document

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
