---
paths:
  - "docs/mcpb-extension/**"
---

# MCPB Extension Build Rules

When modifying or building the MCPB extension, ALWAYS read `docs/mcpb-extension/BUILD_NOTES.md` first. It contains the documented build process.

## Quick reference

```bash
# Build the extension (from docs/mcpb-extension/)
mcpb pack . eruditis-atlassian.mcpb

# Run tests before packaging
node --test tests/*.test.js
```

## Upload to Claude Desktop

After building, remind the user:

1. The built file is at `docs/mcpb-extension/eruditis-atlassian.mcpb`
2. Go to **Organization Settings → Libraries → Connectors → Desktop**
3. Find the "Eruditis Atlassian" extension, click the **"..." menu**
4. Upload the new `.mcpb` file
5. Team members will get the update automatically

## Key facts

- `.mcpb` files are built with `mcpb pack`, NOT `zip`
- `mcpb` is installed globally via `npm install -g @anthropic-ai/mcpb`
- Version in `manifest.json` must increment from the last uploaded version
- The MCPB version is independent of the Python package version (v0.x.x)
- Check current published version before bumping — don't assume
