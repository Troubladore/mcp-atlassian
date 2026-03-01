---
paths:
  - "security/**"
  - "uv.lock"
  - "pyproject.toml"
  - "Dockerfile"
---

# Security Scanning

## Quick scan commands

```bash
# Vulnerability scan (HIGH/CRITICAL only)
trivy fs --scanners vuln --severity HIGH,CRITICAL uv.lock

# Python-specific
uvx pip-audit --desc

# SBOM cross-validation
syft packages . -o json | grype --only-fixed -o table

# GitHub alerts
gh api repos/Troubladore/mcp-atlassian/dependabot/alerts
gh api repos/Troubladore/mcp-atlassian/code-scanning/alerts
gh api repos/Troubladore/mcp-atlassian/secret-scanning/alerts
```

## When to run

- After merging upstream (new dependencies in uv.lock)
- After adding/updating dependencies in pyproject.toml
- Monthly review (1st of each month)

## Scan output

Results go in `security/scans/` (gitignored). Assessments for triaged CVEs go in `security/assessments/`.

## Current status

See `security/README.md` for the latest vulnerability status and dismissed alerts.
