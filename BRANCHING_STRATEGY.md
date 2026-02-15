# Branching Strategy for mcp-atlassian Fork

## Overview

This repository is a fork of `sooperset/mcp-atlassian` with a dual purpose:
1. **Contribute security fixes back upstream** via pull requests
2. **Maintain Eruditis-specific customizations** (MCPB desktop extension)

This document defines the branching strategy that enables both workflows.

---

## Repository Structure

```
upstream (sooperset/mcp-atlassian)
    └── main (original project)

origin (Troubladore/mcp-atlassian - your fork)
    ├── develop (tracks upstream/main, base for all work)
    ├── feature/security-fixes (upstream PR branch)
    └── eruditis/main (Eruditis-specific customizations)
```

---

## Branch Purposes

### `develop`

**Purpose**: Primary development branch that tracks upstream
**Based on**: `upstream/main` (latest from sooperset/mcp-atlassian)
**Never merge to**: Your `origin/main` (stays in sync with upstream via fetch)

**Usage**:
```bash
# Keep develop in sync with upstream
git checkout develop
git fetch upstream
git merge upstream/main --ff-only

# Create new feature branches
git checkout -b feature/my-feature develop
```

### `feature/security-fixes`

**Purpose**: Branch for contributing security fixes back to upstream
**Based on**: `develop`
**PR target**: `upstream/main` (sooperset/mcp-atlassian)

**Contents**:
- Fix for 15 GitHub Code Scanning vulnerabilities
- Fix for devcontainer USER statement (Trivy HIGH)
- Security scanning protocol documentation
- CVE analysis for diskcache

**Current commits**:
1. `0656e37` - Fix all 15 GitHub Code Scanning vulnerabilities
2. `501b319` - Add comprehensive security scanning protocol and CVE analysis

**Merge strategy**: DO NOT merge to origin/main (keep separate for clean PR)

### `eruditis/main`

**Purpose**: Eruditis-specific work and customizations
**Based on**: `develop` (latest upstream)
**Merge target**: NOT upstream (internal use only)

**Contents**:
- Everything in `feature/security-fixes` (all security work)
- PLUS: MCPB desktop extension (`docs/mcpb-extension/`)
- PLUS: Eruditis-specific documentation

**Current commits**:
1. `5ee3cfc` - Add MCPB desktop extension with automatic Docker image management
2. `5ccb76f` - Reorganize repository: move docs and establish security workflow
3. `a4b8ba2` - Add pip-audit to security scanning workflow
4. `40c4c97` - Update security documentation to include Code/Secret Scanning

**Merge strategy**: Deploy from this branch, never PR to upstream

### `feature/mcpb-extension` (OLD - can be deleted)

**Status**: Superseded by `eruditis/main`
**Action**: Can delete after verifying `eruditis/main` has everything

---

## Workflows

### Contributing Security Fixes to Upstream

```bash
# 1. Make sure develop is current
git checkout develop
git fetch upstream
git merge upstream/main --ff-only

# 2. Create feature branch from develop
git checkout -b feature/my-security-fix develop

# 3. Make changes, commit, test
git add -A
git commit -m "fix: security issue XYZ"

# 4. Push to your fork
git push origin feature/my-security-fix

# 5. Create PR to upstream
gh pr create --repo sooperset/mcp-atlassian \
  --base main \
  --head Troubladore:feature/my-security-fix \
  --title "Fix: Security issue XYZ" \
  --body "Fixes security issue..."
```

**Current PR-ready branch**: `feature/security-fixes`

### Maintaining Eruditis Customizations

```bash
# 1. Update develop with latest upstream
git checkout develop
git fetch upstream
git merge upstream/main --ff-only

# 2. Merge upstream changes into eruditis/main
git checkout eruditis/main
git merge develop

# 3. Add Eruditis-specific features
git checkout -b eruditis/feature-xyz eruditis/main
# ... make changes ...
git commit -m "Add Eruditis feature XYZ"

# 4. Merge feature to eruditis/main
git checkout eruditis/main
git merge eruditis/feature-xyz

# 5. Deploy from eruditis/main
# Build MCPB extension, deploy Docker images, etc.
```

### When Upstream Accepts Your PR

```bash
# 1. Fetch updated upstream
git fetch upstream

# 2. Update develop
git checkout develop
git merge upstream/main --ff-only
# Your changes are now in upstream!

# 3. Merge to eruditis/main
git checkout eruditis/main
git merge develop
# This should be clean since eruditis/main already has the changes

# 4. Delete merged feature branch
git branch -d feature/security-fixes
```

---

## What Goes Where

### Upstream-Appropriate (feature/security-fixes → sooperset)

✅ **Security fixes**:
- Code scanning vulnerability fixes
- Dependency vulnerability patches
- Devcontainer security improvements

✅ **Security documentation**:
- `security/SCANNING_PROTOCOL.md` - General security workflow
- `security/README.md` - Vulnerability tracking
- `security/assessments/*.md` - CVE analyses (shows best practices)

✅ **Bug fixes, improvements**:
- Performance improvements
- Test coverage enhancements
- Documentation improvements

### Eruditis-Only (eruditis/main, NEVER upstream)

❌ **MCPB Extension**:
- `docs/mcpb-extension/` - Eruditis-specific deployment
- References to "Eruditis" organization
- Eruditis Atlassian URLs

❌ **Internal tooling**:
- Custom scripts for Eruditis workflows
- Internal CI/CD configurations
- Organization-specific documentation

---

## Current Branch Status

### feature/security-fixes (Ready for Upstream PR)

```
upstream/main (33720b5)
  ↓
develop
  ↓
feature/security-fixes (2 commits)
  ├── 0656e37 - Fix all 15 GitHub Code Scanning vulnerabilities
  └── 501b319 - Add comprehensive security scanning protocol
```

**Status**: ✅ Ready to PR to `sooperset/mcp-atlassian`
**Command**:
```bash
git push origin feature/security-fixes
gh pr create --repo sooperset/mcp-atlassian --base main --head Troubladore:feature/security-fixes
```

### eruditis/main (Internal Deployment)

```
upstream/main (33720b5)
  ↓
develop
  ↓
eruditis/main (4 commits)
  ├── 5ee3cfc - Add MCPB desktop extension
  ├── 5ccb76f - Reorganize repository
  ├── a4b8ba2 - Add pip-audit integration
  └── 40c4c97 - Update security docs (Code/Secret Scanning)
```

**Status**: ✅ Ready for internal use
**Contains**: All security fixes PLUS Eruditis-specific MCPB extension
**Deploy from**: This branch

---

## Keeping Branches in Sync

### Weekly: Update from Upstream

```bash
# Get latest from sooperset/mcp-atlassian
git fetch upstream

# Update develop
git checkout develop
git merge upstream/main --ff-only

# Propagate to eruditis/main
git checkout eruditis/main
git merge develop
# Resolve any conflicts (usually none if Eruditis work is in docs/)

# Push to your fork
git push origin develop eruditis/main
```

### When Upstream Releases New Version

```bash
# After sooperset releases v0.14.0
git fetch upstream --tags
git checkout develop
git merge upstream/main  # Gets v0.14.0

# Update eruditis/main
git checkout eruditis/main
git merge develop

# Update MCPB extension Docker tag
cd docs/mcpb-extension
# Edit server/index.js: IMAGE = "ghcr.io/sooperset/mcp-atlassian:v0.14.0"
# Edit manifest.json: "version": "1.1.0"
git commit -am "chore: update to mcp-atlassian v0.14.0"
```

---

## Branch Protection

### What NOT to Do

❌ **Never merge eruditis/main to develop**
- Keeps Eruditis-specific work isolated
- Prevents MCPB extension from contaminating upstream branches

❌ **Never merge feature/security-fixes to origin/main**
- Keep main in sync with upstream
- Prevents divergence

❌ **Never push develop to origin/main**
- main should track upstream
- Use eruditis/main for deployments

### What TO Do

✅ **Always branch from develop**
- Ensures latest upstream code
- Prevents conflicts

✅ **Keep eruditis/main current with develop**
- Regularly merge develop → eruditis/main
- Get upstream improvements

✅ **PR from feature/* to upstream/main**
- Clean, focused contributions
- Easy for upstream to review

---

## FAQ

### Q: Where do I make changes?

**For upstream contribution**:
```bash
git checkout -b feature/fix-xyz develop
# Make changes, commit, PR to upstream
```

**For Eruditis-specific work**:
```bash
git checkout -b eruditis/feature-xyz eruditis/main
# Make changes, commit, merge to eruditis/main
```

### Q: How do I deploy the MCPB extension?

```bash
git checkout eruditis/main
git pull origin eruditis/main
cd docs/mcpb-extension
mcpb pack
# Deploy eruditis-atlassian.mcpb to users
```

### Q: What if upstream releases break my MCPB extension?

```bash
# Test before merging
git checkout eruditis/main
git fetch upstream
git merge upstream/main --no-commit
# Test MCPB extension
cd docs/mcpb-extension && mcpb pack && test...

# If broken:
git merge --abort
# Fix compatibility issues, then merge

# If working:
git commit
```

### Q: Can I delete feature/mcpb-extension?

Yes, after verifying `eruditis/main` has everything:

```bash
git log eruditis/main --oneline
# Verify all 4 commits are present

git branch -D feature/mcpb-extension
```

### Q: Should security documentation go to upstream?

**Yes!** The security protocol we created is valuable to the entire community:
- Shows best practices
- Provides example CVE analysis
- Benefits all users

However, **wait to see if upstream wants it** - some maintainers prefer minimal docs.

---

## Summary

**Branching Model**:
```
upstream/main → develop → feature/* (for upstream PRs)
                       → eruditis/main (for Eruditis deployment)
```

**Key Principles**:
1. All work starts from `develop` (latest upstream)
2. Upstream contributions via `feature/*` branches
3. Eruditis work in `eruditis/main`
4. Regular sync: upstream/main → develop → eruditis/main

**Current State**:
- ✅ `develop` = upstream/main (latest)
- ✅ `feature/security-fixes` = 2 commits, ready for upstream PR
- ✅ `eruditis/main` = 4 commits, ready for deployment
- 🗑️ `feature/mcpb-extension` = can be deleted (superseded)

---

**Created**: 2026-02-15
**Maintainer**: Troubladore
**Upstream**: https://github.com/sooperset/mcp-atlassian
