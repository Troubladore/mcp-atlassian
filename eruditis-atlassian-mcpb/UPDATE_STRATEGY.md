# Update Strategy for MCPB Extension with Pinned Docker Images

## Problem Statement

This extension uses a **pinned Docker image version** (e.g., `v0.11.10`) rather than `:latest` for security reasons. This creates a challenge: how do we deliver updates to users without requiring manual `docker pull` commands?

## Solution: Automatic Image Management

We've implemented **automatic Docker image pulling** in `server/index.js`. Here's how it works:

### Implementation

```javascript
// server/index.js includes:

function imageExists(image) {
  try {
    execSync(`docker image inspect ${image}`, { stdio: 'ignore' });
    return true;
  } catch (err) {
    return false;
  }
}

function pullImage(image) {
  process.stderr.write(`Pulling Docker image ${image}...\n`);
  execSync(`docker pull ${image}`, { stdio: 'inherit' });
}

// Before spawning container:
if (!imageExists(IMAGE)) {
  pullImage(IMAGE);
}
```

### User Experience Flow

#### Scenario 1: First Installation

1. User installs extension via Claude Desktop
2. First time they use it: Extension checks for image, doesn't find it
3. Extension automatically runs `docker pull ghcr.io/sooperset/mcp-atlassian:v0.11.10`
4. Download takes 30-60 seconds (shows progress in Claude Desktop logs)
5. Container starts, extension works
6. Subsequent uses: Instant (image cached)

#### Scenario 2: Extension Update (New Docker Version)

1. You release `v1.1.0` of the extension with Docker image `v0.11.11`
2. **Org upload**: Users get update notification in Claude Desktop, click "Update"
   **OR File share**: Users download new `.mcpb`, double-click to reinstall
3. Next time they use the extension:
   - Extension checks for `v0.11.11` image, doesn't find it
   - Automatically pulls `v0.11.11` (30-60 seconds)
   - Container starts with new version
4. Subsequent uses: Instant

#### Scenario 3: Extension Update (Same Docker Version)

1. You release `v1.0.1` of the extension (bug fix in Node.js code, same Docker image)
2. Users update via Claude Desktop or reinstall `.mcpb`
3. Next use: Instant (image already cached)

## Update Delivery Matrix

| Distribution Method | Update Detection | User Action Required | Docker Image Pull |
|---------------------|------------------|----------------------|-------------------|
| **Org Upload** | Automatic notification | Click "Update" | Automatic on first use |
| **File Share** | Manual (receive new file) | Double-click to reinstall | Automatic on first use |

## Benefits of This Approach

### ✅ Security
- **Version pinning maintained**: Still using specific versions, not `:latest`
- **Supply chain control**: You choose when to update, users don't auto-pull arbitrary code
- **Rollback capability**: Can revert to previous `.mcpb` version if needed

### ✅ User Experience
- **Zero manual steps**: No terminal commands, no `docker pull` needed
- **Transparent progress**: Download progress visible in Claude Desktop logs
- **Graceful fallback**: Clear error message if image pull fails

### ✅ Operational
- **Decoupled updates**: Update `.mcpb` version independently of Docker image
- **Flexible cadence**: Can update Node.js wrapper without changing Docker image
- **Bandwidth efficient**: Only downloads new images when version changes

## Comparison with Alternatives

### Alternative 1: Manual Pull (Original Approach)

**Pros**: User controls download timing
**Cons**:
- Requires terminal knowledge
- High friction for updates
- Users forget to pull, extension breaks
- Support burden increases

**Verdict**: ❌ Not recommended

### Alternative 2: Use `:latest` Tag

**Pros**: No `.mcpb` updates needed for upstream changes
**Cons**:
- **Security risk**: Can't audit what code is running
- **Breaking changes**: Auto-deploy without testing
- **No rollback**: Can't revert if upstream breaks
- **Violates security best practices**

**Verdict**: ❌ Absolutely not recommended

### Alternative 3: Bundle Image in .mcpb (Crazy Idea)

**Pros**: No network dependency
**Cons**:
- **File size**: ~100MB `.mcpb` files
- **Email/Slack sharing impossible**
- **Org upload limits**: May exceed upload size limits
- **Storage waste**: Every update is full image

**Verdict**: ❌ Impractical

### Alternative 4: Automatic Pull (Our Implementation)

**Pros**:
- Maintains version pinning security
- Zero user friction
- Transparent progress
- Graceful error handling

**Cons**:
- First-use delay (30-60 seconds) when version changes
- Requires internet access on first use

**Verdict**: ✅ **Best balance of security and UX**

## Update Workflow for Maintainers

When upstream releases a new version:

### 1. Evaluate the Update

```bash
# Check release notes
open https://github.com/sooperset/mcp-atlassian/releases

# Review changes
- Security fixes? → High priority
- Bug fixes? → Medium priority
- New features? → Low priority
- Breaking changes? → Test thoroughly
```

### 2. Update the Extension

```bash
cd eruditis-atlassian-mcpb

# Edit server/index.js line 9
# Change: const IMAGE = "ghcr.io/sooperset/mcp-atlassian:v0.11.10";
# To:     const IMAGE = "ghcr.io/sooperset/mcp-atlassian:v0.11.11";

# Edit manifest.json
# Increment version: "1.0.0" -> "1.0.1" (or 1.1.0, 2.0.0 based on changes)

# Rebuild
mcpb pack
```

### 3. Test Locally

```bash
# Remove old image to simulate fresh install
docker rmi ghcr.io/sooperset/mcp-atlassian:v0.11.11

# Install in Claude Desktop
# Use extension, verify it auto-pulls and works
```

### 4. Distribute

**Org upload**:
```
Settings > Connectors > Desktop > Custom team extensions > Upload new version
```

**File share**:
```
Share eruditis-atlassian.mcpb via Slack/email with changelog
```

### 5. Monitor

- Watch for support requests
- Check that users successfully update
- Monitor for any image pull failures

## Versioning Strategy

Follow semantic versioning for the **extension version** (in `manifest.json`):

| Change Type | Example | Semver Bump |
|-------------|---------|-------------|
| New Docker image with security patches | `v0.11.10` → `v0.11.11` | **Patch** (1.0.0 → 1.0.1) |
| New Docker image with bug fixes | `v0.11.10` → `v0.11.11` | **Patch** (1.0.0 → 1.0.1) |
| New Docker image with features | `v0.11.10` → `v0.12.0` | **Minor** (1.0.0 → 1.1.0) |
| New Docker image with breaking changes | `v0.11.10` → `v1.0.0` | **Major** (1.0.0 → 2.0.0) |
| Node.js wrapper bug fix (same Docker) | No change | **Patch** (1.0.0 → 1.0.1) |
| New manifest config option (backward compatible) | No change | **Minor** (1.0.0 → 1.1.0) |

## Monitoring Image Pull Success

To track if users are successfully pulling images, you could:

1. **Slack channel**: Ask users to report first-use experience
2. **Support tickets**: Monitor for "image not found" errors
3. **Analytics** (future): Instrument `server/index.js` to log pull attempts

## Rollback Procedure

If an update causes issues:

1. Revert `server/index.js` to previous Docker image version
2. Revert `manifest.json` version (or increment to next version with old image)
3. Rebuild: `mcpb pack`
4. Re-distribute with "Rollback" in changelog
5. Users update and extension automatically pulls previous working image

## Future Enhancements

### Caching Strategy

Currently, Docker's built-in image cache handles this. In the future, you could:

- Pre-warm image cache on user machines (background task)
- Use registry mirrors for faster downloads
- Implement delta updates (if MCPB supports it)

### Update Notifications

Consider adding a changelog display in the extension:

```javascript
// server/index.js could detect version changes and log:
process.stderr.write("Updated to v1.1.0! New features: ...\n");
```

## Summary

**Problem**: Pinned Docker versions are secure but create update friction
**Solution**: Automatic image pulling in `server/index.js`
**Result**: Security + Zero-friction updates + Graceful UX

This approach is the **best practice** for MCPB extensions that wrap Docker containers.
