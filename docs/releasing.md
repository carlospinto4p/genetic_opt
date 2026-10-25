# Releasing genetic_opt

genetic_opt ships as a private package to its own GitLab registry,
`gitlab_genetic_opt` (GitLab project `48069240`), which `downstream`
installs from. GitLab CI is off, so the `publish-package` job in
`.gitlab-ci.yml` cannot run: every release is uploaded from a developer
machine. 8.1.0 was uploaded that way on 25th October 2026, so that
`downstream` could pin `genetic_opt>=8.1,<9`; before it the registry held
4.1.0 at most.

When to publish is decided by `~/.claude/rules/publish-on-demand.md`:
the version a consumer is about to install, when it is about to install
it. A version bump alone does not put anything in the registry.

## The command

```bash
uv build --out-dir <dir>
uv publish --index gitlab_genetic_opt \
  <dir>/genetic_opt-<version>.tar.gz \
  <dir>/genetic_opt-<version>-py3-none-any.whl
```

- **Name both files.** `uv publish` takes everything in the folder by
  default, older versions included.
- **Credentials** come from `UV_PUBLISH_USERNAME` and
  `UV_PUBLISH_PASSWORD`, set on the machine. A per-index
  `UV_INDEX_GITLAB_GENETIC_OPT_*` pair authenticates reading only, not
  an upload.
- **`--index gitlab_genetic_opt`** works through the `publish-url` of
  that index entry in `pyproject.toml`. Unchecked: 8.1.0 went up with
  the same upload address passed directly, which also works:
  `--publish-url https://gitlab.com/api/v4/projects/48069240/packages/pypi`.
  Add `--dry-run` to check the address and the credentials without
  uploading.

## What the registry serves

Before repinning a consumer, check that the version it needs is there:

```bash
curl -sS --netrc "https://gitlab.com/api/v4/projects/48069240/packages/pypi/simple/genetic-opt/" \
  | grep -oE 'genetic_opt-[0-9][0-9.]*' | sort -V | tail -5
```

## Version and changelog

See `.claude/rules/versioning.md`. Bump `pyproject.toml` and
`crates/genetic_opt/Cargo.toml` together, add the changelog entry with
`scripts/changelog-add.sh`, and run `uv sync --all-extras` so
`uv.lock` follows.
