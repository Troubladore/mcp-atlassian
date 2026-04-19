# Releases

This fork maintains its own release cadence on `community/main`, distinct from upstream `sooperset/mcp-atlassian`. Each release is a git tag on `community/main` (semver, `vX.Y.Z`), a GHCR image (`ghcr.io/troubladore/mcp-atlassian:<version>`), and a GitHub Release with notes drawn from the merged PR.

## Versioning

Semver against the `community/main` branch line.

- **Patch** (`vX.Y.Z+1`) — small bug fixes, regression fixes, documentation-only changes.
- **Minor** (`vX.Y+1.0`) — backward-compatible features, non-breaking dependency-floor bumps, meaningful observable-behavior shifts that users should notice.
- **Major** (`vX+1.0.0`) — breaking changes to the tool surface or configuration contract.

Releases on `community/main` aren't coupled to upstream release numbers. `main` tracks upstream exactly; `community/main` diverges.

## Release triggers

- **Immediate release** for any CVE remediation or security fix, regardless of batching schedule. Contributors pinning `:X.Y` can pull the patch without waiting on unrelated work.
- **On-merge release** for major feature PRs, ports, or architectural changes — ship under a tag that makes the change discoverable.
- **Batched release** for small community PRs and bug fixes — weekly or bi-weekly cadence, cut whenever the accumulated diff is worth a tag.

## Release notes

GitHub Releases. Body of each release is the description of the PR that landed, plus any cross-references to related issues. There is no separate `CHANGELOG.md` — the PR description is written well enough the first time to be the authoritative release note, and duplicating it is churn.

## Pinning guidance for consumers

For production or scripted deployments, pin `:MAJOR.MINOR`:

```
ghcr.io/troubladore/mcp-atlassian:0.22
```

This gets you patch-level security updates automatically while shielding you from behavior shifts that bump `MINOR`.

`:latest` tracks the most recent non-prerelease tag and is fine for eval / demos, but is **not** a stable contract.

`:MAJOR.MINOR.PATCH` pins are for reproducibility — CI jobs, lockfiles, incident-response rollbacks.

## Branch cascade

Releases on `community/main` should flow to `team/main` as soon as practical. `team/main` may carry additional team-specific tools and features; its releases are a superset of `community/main` at the same point in time. Keep the cascade current so `team/main`'s release line doesn't drift too far from the community line.

## What a release looks like (ops)

1. PR merges to `community/main`.
2. Maintainer tags the merge commit: `git tag -as vX.Y.Z -m "Release vX.Y.Z"`.
3. Push: `git push origin vX.Y.Z`.
4. `docker-publish.yml` builds and pushes the image to GHCR under `:X.Y.Z`, `:X.Y`, `:X`, and (if non-prerelease) `:latest`.
5. `gh release create vX.Y.Z --notes-from-pr <PR>` creates the GitHub Release with the PR description as the body.

Cascade to `team/main` (merge, tag) happens on its own cadence.
