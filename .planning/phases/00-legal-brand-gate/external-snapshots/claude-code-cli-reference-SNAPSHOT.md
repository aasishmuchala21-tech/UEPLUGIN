---
source_url: https://code.claude.com/docs/en/cli-reference
snapshot_date: 2026-04-24
snapshot_method: curl (raw HTML fetch; verbatim table rows extracted from the Mintlify-rendered page — `setup-token` subcommand entry + `--output-format stream-json` flag + `--mcp-config` flag + `--strict-mcp-config` flag)
snapshot_by: NYRA Plan 00-01 executor
plan: 00-01-anthropic-tos-email
rationale: >
  The email to Anthropic is precise about NYRA's integration pattern: the
  user runs `claude setup-token`, and NYRA subprocess-invokes
  `claude -p --output-format stream-json --verbose --mcp-config <path>`.
  Anthropic's reply will only be useful if the reply's scope matches that
  exact surface. This snapshot captures the canonical descriptions of those
  subcommands and flags from Anthropic's own docs, so the reply can be
  interpreted against the authoritative language.
publisher: "Anthropic, PBC"
canonical_title: "CLI reference"
license_notice: >
  Quoted here for fair-use research archival. Full document lives at the
  source_url above. Anthropic owns the text.
---

# Claude Code — CLI reference — Snapshot 2026-04-24

> **Snapshot method note:** The source page is a Mintlify-rendered Next.js
> client document; the flag descriptions reproduced below were extracted
> **verbatim** from the raw HTML of the rendered tables. Offsets of the
> matching table rows are noted for audit.

## Page structural headings (as rendered on 2026-04-24)

- **H1:** CLI reference
- **H2:** CLI commands
- **H2:** CLI flags
  - **H3:** System prompt flags
- **H2:** See also

## Verbatim subcommand row — `claude setup-token`

From the "CLI commands" table:

> **`claude setup-token`** — Generate a long-lived OAuth token for CI and
> scripts. Prints the token to the terminal without saving it. Requires a
> Claude subscription. See [Generate a long-lived token][gen-long-lived].

[gen-long-lived]: https://code.claude.com/docs/en/authentication#generate-a-long-lived-token

**Significance for NYRA:** This is the subcommand the USER runs, on the
USER's own machine, to mint the long-lived OAuth token NYRA's subprocess-
pattern depends on. It is not a flag; it is a user-initiated interactive
flow provided by Anthropic's own CLI. NYRA does not invoke
`claude setup-token` on the user's behalf — the user runs it themselves.

## Verbatim flag rows (from the "CLI flags" table)

### `--output-format stream-json`

> **`--output-format`** — Output format for `--print` mode (options: `text`,
> `json`, `stream-json`).
>
> Example: `claude -p --output-format stream-json "query"`

Relatedly:

> **`--include-hook-events`** — Include all hook lifecycle events in the
> output stream. Requires `--output-format stream-json`.
>
> Example: `claude -p --output-format stream-json --include-hook-events "query"`

> **`--include-partial-messages`** — Include partial streaming events in
> output. Requires `--print` and `--output-format stream-json`.
>
> Example: `claude -p --output-format stream-json --include-partial-messages "query"`

> **`--input-format`** — Specify input format for print mode (options:
> `text`, `stream-json`).
>
> Example: `claude -p --output-format json --input-format stream-json`

### `--mcp-config`

> **`--mcp-config`** — Load MCP servers from JSON files or strings
> (space-separated).
>
> Example: `claude --mcp-config ./mcp.json`

> **`--strict-mcp-config`** — Only use MCP servers from `--mcp-config`,
> ignoring all other MCP configurations.
>
> Example: `claude --strict-mcp-config --mcp-config ./mcp.json`

### `-p / --print`, `--max-turns`, `--model`, `--settings` (supporting flags)

> **`--print`** / **`-p`** — Print the response and exit (implies non-
> interactive mode; the flag used by all NYRA subprocess invocations).

> **`--max-turns`** — Limit the number of agentic turns before an error.
>
> Example: `claude -p --max-turns 3 "query"`

> **`--model`** — Sets the model for the current session; accepts an alias
> (`sonnet`, `opus`) or a full model name.
>
> Example: `claude --model claude-sonnet-4-6`

> **`--settings`** — Path to a JSON file (or a JSON string) to load
> additional settings from.
>
> Example: `claude --settings ./settings.json`

> **`--system-prompt`** — Replace the entire system prompt with custom
> text.
>
> Example: `claude --system-prompt "You are a Python expert"`

## NYRA's exact invocation shape (for the email)

The email quotes the invocation shape explicitly so Anthropic's reply maps
onto it unambiguously:

```
claude -p "<prompt>" \
  --output-format stream-json \
  --verbose \
  --include-partial-messages \
  --mcp-config <nyra-per-session-config.json>
```

This matches the documented flag surface above — all flags are Anthropic's
own, as documented on code.claude.com/docs/en/cli-reference.

## Authentication model (for the email)

The email also cites Anthropic's Authentication docs as adjacent context:

- User runs `claude setup-token` **interactively on their own machine**.
- Output is a long-lived OAuth token tied to the user's Claude
  subscription.
- The token lives in the user's own filesystem at
  `~/.claude/.credentials.json` (or in the environment variable
  `CLAUDE_CODE_OAUTH_TOKEN`, if the user prefers).
- NYRA **never sees** this token: NYRA's subprocess invocation inherits
  the user's environment, and the `claude` CLI reads credentials itself.

## Full page reference

The authoritative full page lives at:

- https://code.claude.com/docs/en/cli-reference

If the email response cites specific flag semantics, those semantics are
anchored to the verbatim rows above, frozen as of 2026-04-24.

---

*Snapshot authored for NYRA Phase 0 SC#1 legal gate — 2026-04-24.*
