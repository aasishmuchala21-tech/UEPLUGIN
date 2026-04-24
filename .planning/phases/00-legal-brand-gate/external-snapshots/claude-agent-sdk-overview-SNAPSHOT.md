---
source_url: https://code.claude.com/docs/en/agent-sdk/overview
snapshot_date: 2026-04-24
snapshot_method: curl (raw HTML fetch of the docs page; key paragraph extracted verbatim from the embedded JSON content blob of the Mintlify-rendered page)
snapshot_by: NYRA Plan 00-01 executor
plan: 00-01-anthropic-tos-email
rationale: >
  THIS IS THE MOTIVATING DOCUMENT for the entire ToS clarification email.
  The "Anthropic does not allow third party developers to offer claude.ai
  login" paragraph is what triggered the need for written clearance. The
  paragraph's exact wording is preserved below verbatim so that when
  Anthropic replies, the founder can point at a frozen copy of the public
  policy language NYRA's question was issued against. If Anthropic later
  edits this paragraph, the snapshot remains the defensible anchor for the
  Phase 0 SC#1 verdict.
publisher: "Anthropic, PBC"
canonical_title: "Agent SDK overview"
page_section: "Capabilities → Branding guidelines / License and terms (Note callout)"
license_notice: >
  Quoted here for fair-use research archival. Full page lives at the
  source_url above; Anthropic owns the text.
---

# Claude Agent SDK — Overview — Snapshot 2026-04-24

> **Snapshot method note:** The source page is a Mintlify-rendered docs
> page; the page is a Next.js client-rendered document. The paragraph
> immediately below was extracted **verbatim** from the raw HTML by
> searching for the string "Unless previously approved" — this text is the
> body content of the "Note" callout in the SDK overview page and is the
> single load-bearing statement for NYRA's ToS clarification question. The
> rest of this file captures the structural headings present on the page as
> of 2026-04-24 so the snapshot is self-contained as a reference.

## THE paragraph (verbatim — this is why the email was sent)

> **Note:** Unless previously approved, Anthropic does not allow third
> party developers to offer claude.ai login or rate limits for their
> products, including agents built on the Claude Agent SDK. Please use
> the API key authentication methods described in this document instead.

**Source position:** The paragraph appears as a "Note" callout
(aria-label="Note") in the Agent SDK overview page, attached to the
"License and terms" / "Branding guidelines" / authentication-methods
guidance at the tail of the document.

**Character-for-character match check:** The email draft in
`correspondence/00-01-anthropic-tos-email-draft.md` quotes this paragraph
**verbatim** with the exact wording reproduced above. Any change in this
paragraph in a future fetch of the page will show up in a diff of this
snapshot vs. the re-fetch — which is the intended audit trail.

## Page structural headings (as rendered on 2026-04-24)

- **H1:** Agent SDK overview
- **H2:** Quickstart
- **H2:** Example agents
- **H2:** Get started
- **H2:** Capabilities
  - **H3:** Claude Code features
- **H2:** Compare the Agent SDK to other Claude tools
- **H2:** Changelog
- **H2:** Reporting bugs
- **H2:** Branding guidelines
- **H2:** License and terms
- **H2:** Next steps

## How NYRA's pattern is distinct from what the Note paragraph forbids

The email to Anthropic explicitly draws the line along two axes, both of
which matter for whether NYRA falls inside or outside the restriction:

1. **"offer claude.ai login"** — NYRA does not offer a login. The user
   runs `claude setup-token` themselves, on their own machine, in their
   own terminal (or via the Claude CLI's own interactive flow). NYRA's
   plugin does not display a claude.ai-branded login UI, does not
   capture credentials, does not mint tokens, and does not host any
   login page. Any authentication UI the user sees during setup is
   Anthropic's own (shipped with the `claude` CLI), not NYRA's.

2. **"agents built on the Claude Agent SDK"** — NYRA does not embed the
   Agent SDK. NYRA invokes the user's own **already-installed** `claude`
   CLI as a stdio subprocess with
   `claude -p --output-format stream-json --verbose --mcp-config <path>`.
   The `claude` CLI is Anthropic's own binary, authenticated with the
   user's own OAuth token. NYRA is effectively a parent process that
   reads stdout from Anthropic's CLI — it is **not** an Agent SDK
   embedding, because it carries no Anthropic SDK code at all.

**The question to Anthropic** (quoted from the email draft): "Can you
confirm this subprocess-driving pattern is permitted under the Anthropic
Commercial and Consumer Terms for a free third-party product that
interoperates with a user's personal Claude subscription?"

## Why the paragraph was read as gating in the first place

The Note is the closest policy language in Anthropic's public surface to
NYRA's architectural pattern. "Offer claude.ai login" is the specific
third-party conduct Anthropic has said — in writing — they do not permit
without prior approval. If read narrowly, NYRA is outside it (see the two
axes above). If read broadly, any third-party tool that lets a user
consume their own Claude subscription via a different surface might be
captured. The email asks for the narrow reading to be confirmed.

## Additional context — adjacent headings that inform the read

- **"Branding guidelines"** — implies that third-party-to-Anthropic
  branding has its own separate rulebook (Phase 0 Plan 05 captures that
  archive). NYRA is already committed to neutral language ("works with
  your Claude subscription", no Claude logo without written permission).
- **"License and terms"** — the SDK itself has a license; NYRA doesn't
  use the SDK, so the SDK license doesn't bind NYRA directly, but the
  top-level Commercial / Consumer Terms still apply to the end user.

## Full page reference

The authoritative full page lives at:

- https://code.claude.com/docs/en/agent-sdk/overview

If the email response cites this page, the verbatim quote above serves as
the anchor.

---

*Snapshot authored for NYRA Phase 0 SC#1 legal gate — 2026-04-24.*
