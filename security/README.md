# Security Vulnerability Tracking

This directory contains security vulnerability assessments, scan results, and triage documentation for mcp-atlassian.

---

## Directory Structure

```
security/
├── README.md                 # This file - tracking and guidance
├── SCANNING_PROTOCOL.md      # Detailed scanning and triage workflow
├── assessments/              # Individual CVE analyses
│   └── CVE-YYYY-NNNNN-{package}.md
└── scans/                    # Historical scan results (gitignored)
    ├── trivy-YYYYMMDD.json
    ├── grype-YYYYMMDD.json
    └── sbom-YYYYMMDD.json
```

---

## Quick Start

### Running a Security Scan

```bash
# 1. Trivy - Quick scan for HIGH/CRITICAL issues
trivy fs --scanners vuln --severity HIGH,CRITICAL uv.lock

# 2. pip-audit - Python-specific vulnerability check
uvx pip-audit --desc

# 3. Trivy - Full vulnerability assessment with JSON output
trivy fs --scanners vuln --severity LOW,MEDIUM,HIGH,CRITICAL --format json uv.lock \
  > security/scans/trivy-$(date +%Y%m%d).json

# 4. pip-audit - JSON output for tracking
uvx pip-audit --format json --output security/scans/pip-audit-$(date +%Y%m%d).json

# 5. Cross-validate with Syft/Grype
syft packages . -o json > security/scans/sbom-$(date +%Y%m%d).json
grype sbom:security/scans/sbom-$(date +%Y%m%d).json --only-fixed \
  -o json > security/scans/grype-$(date +%Y%m%d).json

# 6. Check Dependabot alerts
gh api repos/$(gh repo view --json nameWithOwner -q .nameWithOwner)/dependabot/alerts \
  --jq '.[] | select(.state == "open")'
```

See `SCANNING_PROTOCOL.md` for complete workflow and tool comparison.

---

## Current Status

### Open Vulnerabilities

**Last Scan**: 2026-02-15

| CVE | Package | Severity | Detected By | Status | Assessment |
|-----|---------|----------|-------------|--------|------------|
| *No open vulnerabilities* | - | - | - | - | - |

**Tool Detection Legend**:
- 🔍 **T** = Trivy
- 🐍 **P** = pip-audit
- 📦 **G** = Grype
- 🤖 **D** = Dependabot

### Dismissed Alerts

| CVE | Package | Severity | Detected By | Reason | Date | Assessment |
|-----|---------|----------|-------------|--------|------|------------|
| CVE-2025-69872 | diskcache v5.6.3 | MEDIUM | T, P, G, D | Not exploitable | 2026-02-15 | [CVE-2025-69872-diskcache.md](assessments/CVE-2025-69872-diskcache.md) |

**Why track detection source**:
- **All tools agree** (T+P+G+D): High confidence finding
- **Trivy + pip-audit** (T+P): Strong finding (primary tools agree)
- **pip-audit only** (P): Python-specific, trust PyPI advisory
- **Trivy only** (T): General CVE, may not be Python-specific
- **Dependabot only** (D): GitHub advisory, cross-check with tools

### Scan Result Files

All scan results are stored in `security/scans/` (gitignored):

| Tool | Output File | Purpose |
|------|-------------|---------|
| Trivy | `trivy-YYYYMMDD.json` | Primary vulnerability scan |
| pip-audit | `pip-audit-YYYYMMDD.json` | Python-specific vulnerabilities |
| Syft | `sbom-YYYYMMDD.json` | Software Bill of Materials |
| Grype | `grype-YYYYMMDD.json` | SBOM-based vulnerability scan |

**Regenerate scans**: Run commands in "Quick Start" section above

---

## Triage Guidance

### Decision Tree

```
Found vulnerability?
│
├─→ Is vulnerable code used in our codebase?
│   ├─→ NO: Document as "Not Exploitable" → Dismiss as tolerable_risk
│   └─→ YES: Continue ↓
│
├─→ Is the vulnerable feature enabled?
│   ├─→ NO: Document as "Feature Not Used" → Dismiss as tolerable_risk
│   └─→ YES: Continue ↓
│
├─→ Is there a patch available?
│   ├─→ YES: Apply patch → Test → Deploy
│   └─→ NO: Continue ↓
│
├─→ What are the attack requirements?
│   ├─→ Remote, no auth, RCE: P0 - Fix immediately
│   ├─→ Low privilege, significant impact: P1 - Fix in 1-3 days
│   ├─→ Elevated privilege required: P2 - Fix in 1-2 weeks
│   ├─→ Requires user interaction: P2 - Fix in 1-2 weeks
│   └─→ Theoretical only: P4 - Monitor for patch
│
└─→ Document in security/assessments/ and update this README
```

### Priority Levels

| Priority | Response Time | Criteria |
|----------|--------------|----------|
| **P0** | Same day | Remote exploit, no auth, RCE/data breach possible |
| **P1** | 1-3 days | Exploitable with low privileges, high impact |
| **P2** | 1-2 weeks | Requires elevated access or user interaction |
| **P3** | Next sprint | Low impact, mitigations available |
| **P4** | Monitor | Not exploitable in practice, no patch available |

---

## Assessment Workflow

### 1. Discover Vulnerability

From Trivy, Grype, or Dependabot:

```bash
# Collect details
CVE_ID="CVE-2025-69872"
PACKAGE="diskcache"
VERSION="5.6.3"
```

### 2. Analyze Usage

```bash
# Check if package is used
rg "from.*${PACKAGE}|import.*${PACKAGE}" src/

# Check dependency chain
uv tree | rg "${PACKAGE}" -B 5

# Search for vulnerable APIs
rg "vulnerable_function_name" src/
```

### 3. Create Assessment

```bash
# Create new assessment file
cp security/assessments/TEMPLATE.md \
   security/assessments/${CVE_ID}-${PACKAGE}.md

# Edit with findings
$EDITOR security/assessments/${CVE_ID}-${PACKAGE}.md
```

### 4. Update Tracking

Add entry to this README under appropriate section:
- **Open Vulnerabilities** - Requires action
- **Dismissed Alerts** - Documented and accepted risk

### 5. Close Dependabot Alert (if applicable)

```bash
# Get alert number
ALERT_NUM=$(gh api repos/$(gh repo view --json nameWithOwner -q .nameWithOwner)/dependabot/alerts \
  --jq ".[] | select(.security_advisory.cve_id == \"${CVE_ID}\") | .number")

# Dismiss with documented reason
gh api -X PATCH repos/$(gh repo view --json nameWithOwner -q .nameWithOwner)/dependabot/alerts/${ALERT_NUM} \
  -f state=dismissed \
  -f dismissed_reason="tolerable_risk" \
  -f dismissed_comment="Not exploitable. See security/assessments/${CVE_ID}-${PACKAGE}.md for analysis."
```

---

## Common Scenarios

### Scenario 1: Transitive Dependency, Not Used

**Example**: Library A depends on Library B, but we only use features from A that don't touch B

**Action**:
1. Document that vulnerable code is unreachable
2. Create assessment explaining dependency chain and usage
3. Dismiss Dependabot alert as `tolerable_risk`
4. Monitor for patch (set calendar reminder)

**See**: `assessments/CVE-2025-69872-diskcache.md`

### Scenario 2: Vulnerable Feature Disabled by Default

**Example**: Caching library has unsafe serialization, but we use in-memory mode only

**Action**:
1. Document which features are enabled/disabled
2. Verify configuration doesn't enable vulnerable feature
3. Create assessment with configuration evidence
4. Dismiss as `tolerable_risk`
5. Add note to prevent future enablement

### Scenario 3: Requires Local Access in Containerized Environment

**Example**: Vulnerability requires filesystem write access, but containers are read-only

**Action**:
1. Document container security posture
2. Explain why attack requirements aren't met
3. Note defense-in-depth protections
4. Dismiss as `tolerable_risk`
5. Include in threat model review

### Scenario 4: Patch Available

**Example**: New version fixes vulnerability

**Action**:
1. Review changelog for breaking changes
2. Update dependency: `uv lock --upgrade-package {package}`
3. Run full test suite
4. Deploy and monitor
5. Close Dependabot alert (auto-closes when dependency updated)

---

## Defense-in-Depth Controls

Even when vulnerabilities exist, these controls reduce effective risk:

### Container Security

- **Read-only root filesystem**: Limits write access for exploits
- **No volume mounts**: Prevents host filesystem access
- **Dropped capabilities** (`--cap-drop=ALL`): Reduces privilege escalation risk
- **No new privileges** (`--security-opt no-new-privileges:true`)
- **Resource limits**: Memory and CPU constraints prevent DoS

### Network Security

- **Default bridge network**: No host network access
- **Outbound-only**: No inbound connections to container
- **HTTPS only**: All Atlassian API calls over TLS

### Application Security

- **Principle of least privilege**: Services run as non-root users
- **Input validation**: Sanitize user inputs
- **Output encoding**: Prevent injection attacks
- **Error handling**: Don't leak sensitive info in errors

### Operational Security

- **Dependency pinning**: Explicit version control
- **SBOM generation**: Track all components
- **Regular scanning**: Automated vulnerability detection
- **Incident response**: Documented remediation procedures

---

## Monthly Review Checklist

On the 1st of each month:

- [ ] Run full Trivy scan: `trivy fs --scanners vuln --severity LOW,MEDIUM,HIGH,CRITICAL --format json uv.lock > security/scans/trivy-$(date +%Y%m%d).json`
- [ ] Run pip-audit scan: `uvx pip-audit --format json --output security/scans/pip-audit-$(date +%Y%m%d).json`
- [ ] Generate SBOM: `syft packages . -o json > security/scans/sbom-$(date +%Y%m%d).json`
- [ ] Cross-validate with Grype: `grype sbom:security/scans/sbom-$(date +%Y%m%d).json --only-fixed -o json > security/scans/grype-$(date +%Y%m%d).json`
- [ ] Check Dependabot alerts: `gh api repos/.../dependabot/alerts --jq '.[] | select(.state == "open")'`
- [ ] Consolidate findings: Compare CVEs across all tools (see SCANNING_PROTOCOL.md Step 5)
- [ ] Review all P3/P4 items: Check if patches are now available
- [ ] Update this README with current status and "Detected By" columns
- [ ] Archive monthly scans: Keep most recent 3 months, delete older scans

---

## References

- **Scanning Protocol**: `SCANNING_PROTOCOL.md` - Detailed workflow
- **Assessment Template**: `assessments/TEMPLATE.md` - Standardized format
- **Trivy Docs**: https://trivy.dev/
- **Grype Docs**: https://github.com/anchore/grype
- **Syft Docs**: https://github.com/anchore/syft
- **CVSS Calculator**: https://nvd.nist.gov/vuln-metrics/cvss/v3-calculator
- **CWE Database**: https://cwe.mitre.org/

---

## Questions?

For security concerns or questions about this process:

1. Review `SCANNING_PROTOCOL.md` for detailed procedures
2. Check existing assessments in `assessments/` for examples
3. If still unclear, create a GitHub issue with the `security` label

---

**Last Updated**: 2026-02-15
**Maintained By**: Repository Security Team
