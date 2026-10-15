# genetic_opt instructions for Codex and OpenCode

This file adapts the project's Claude Code guidance for Codex and OpenCode. It
is a routing adapter, not a second copy of the rules: the canonical sources are
`CLAUDE.md` and the files under `.claude/rules/`. Read them before acting, and
change them there rather than here.

User instructions take precedence over these files. Project rules take
precedence over the global conventions in `/home/carlos/.claude/CLAUDE.md` and
`/home/carlos/.claude/rules/`, which also apply.

## Read first

`CLAUDE.md` holds the core rules, the commands for the Python package and the
Rust crate `crates/genetic_opt`, and what to do when a change here breaks
`downstream`.

`backlog.md` holds the open work. `roadmap.md` sets no phase yet; its
"What NOT to do" section still applies.

## Read the applicable project rules

| Task | Read before acting |
| --- | --- |
| Any commit | `committing.md` |
| A version bump or changelog entry | `versioning.md` |
| Writing or changing tests | `testing.md` |
| Timing the tests or the Rust build | `testing-areas.md` |

Paths are relative to `.claude/rules/`. Several rules can apply at once.

## Instruction surfaces

The project has no skills, hooks or plugins of its own; `.claude/` holds only
the rules above, their index `00-rule-index.md`, and `settings.json`, which
denies Claude Code reads of secret files. Any change to an agent instruction,
rule, skill, hook or configuration follows the global
`/home/carlos/.claude/rules/claude-opencode-sync.md`, which keeps Claude Code,
Codex and OpenCode aligned in the same session.
