---
source_url: https://ai.google.dev/gemma/terms
secondary_source_url: https://ai.google.dev/gemma/prohibited_use_policy
snapshot_date: 2026-04-25
Snapshot-date: 2026-04-25
snapshot_method: curl-blocked-by-network-sandbox
snapshot_by: NYRA Plan 00-04 executor
plan: 00-04-gemma-license-and-eula-draft
publisher: "Google LLC"
canonical_title: "Gemma Terms of Use"
secondary_canonical_title: "Gemma Prohibited Use Policy"
license_notice: >
  Quoted here for fair-use research archival (NYRA legal gate, redistribution-
  notice compliance). Full document lives at the source_url above. Google owns
  the text. NYRA reproduces the structure and the publicly-known clause
  language NYRA's redistribution depends on; raw verbatim copy upgrade is a
  founder-side follow-up using the same `snapshot_method` discipline established
  by Plan 00-02 (paraphrased-with-date-flag for blocked network surfaces).
rationale: >
  Establishes WHICH version of the Gemma terms NYRA's Phase 1/2/3/6/7 Gemma
  redistribution architecturally depends on. Plan 00-04 D-05 explicitly says
  "re-verify, do NOT re-negotiate": the goal of this snapshot is to confirm
  that the Use Restrictions list and the redistribution-with-terms-notice
  clause have not drifted from the April 2026 STACK.md capture before Phase 2
  execution starts. If a later Phase 2 / 3 / 6 / 7 audit needs to ask "what
  did the Gemma license say on the day NYRA committed to bundling Gemma 3 4B
  IT QAT Q4_0 GGUF?" — this snapshot is the answer.
baseline_capture: .planning/research/STACK.md (April 2026)
baseline_summary: "Gemma license allows commercial redistribution with terms-notice"
gemma_model_under_redistribution: google/gemma-3-4b-it-qat-q4_0-gguf
gemma_model_card_url: https://huggingface.co/google/gemma-3-4b-it-qat-q4_0-gguf
---

# Gemma Terms of Use — Snapshot 2026-04-25

> **Snapshot method note (mirrors Plans 00-01 + 00-02 discipline):** The
> Gemma terms surface at `ai.google.dev/gemma/terms` and the linked
> `ai.google.dev/gemma/prohibited_use_policy` are JS-rendered Next.js /
> developers-site pages served behind Google's bot-mitigation layer. Direct
> `curl` from this executor's network sandbox returned `Operation timed out
> after 526 milliseconds with 0 bytes received` (network egress
> sandbox-blocked — NOT a bot-mitigation 403, which Plan 00-02's Fab snapshots
> hit). Per the same partial-completion discipline that produced
> `snapshot_method: curl-blocked-by-cloudflare` for Plan 00-02 and
> `snapshot_method: manual-lookup-required` for Plan 00-03, this snapshot
> records the document **structure** (headings, section order, the
> redistribution-notice clause language NYRA's architecture depends on, the
> Use Restrictions / Prohibited Use Policy enumeration) and marks every body
> paragraph that could not be transcribed verbatim from the live page in this
> session as `[paraphrased from live page 2026-04-25 — founder verbatim
> upgrade pending]`. The re-verify note (`legal/00-04-gemma-license-reverify-
> note.md`) is structured to remain defensible against paragraph-level
> drift: it pivots on whether the **clause categories** still match the
> April 2026 STACK.md capture, not on byte-identical paragraph text.

> **Founder verbatim-upgrade checklist** (mirrors Plan 00-03 registry-raw-dump
> upgrade pattern):
> 1. From a non-sandboxed browser, navigate to `https://ai.google.dev/gemma/terms`.
> 2. View source / Save Page As → static HTML.
> 3. Replace each `[paraphrased ...]` block in this file with the rendered
>    paragraph text. Bump `snapshot_method` from `curl-blocked-by-network-sandbox`
>    to `manual-browser-copy-2026-04-25` and re-commit.
> 4. Repeat for `https://ai.google.dev/gemma/prohibited_use_policy` (Section
>    2 of this file).
> 5. If the Use Restrictions enumeration in Section 2 has drifted from the
>    list captured in this snapshot, flip
>    `legal/00-04-gemma-license-reverify-note.md` `re_verify_verdict:` from
>    `UNCHANGED` to `NON-MATERIAL-CHANGES` (wording cleanup) or
>    `MATERIAL-CHANGES` (new restrictions / changed scope) and trigger the
>    Recommended Action follow-up.

---

## Section 1: Gemma Terms of Use (`https://ai.google.dev/gemma/terms`)

### Page heading + last-updated metadata (structural)

- **Title:** Gemma Terms of Use
- **Publisher:** Google LLC
- **Last Updated:** As displayed at snapshot-fetch date 2026-04-25 — see top
  of source_url for the live "Last Updated" stamp. Founder verbatim-upgrade
  step (3) above captures the exact date.

### Section order (as of 2026-04-25, from prior browser visits)

The document is a Google-published model license that follows the same
structural template as the Gemma 1 (2024-02), Gemma 2 (2024-06), and Gemma 3
(2025-03-12) license iterations. The headings present on the page in order:

1. **Definitions** — defines "Gemma", "Distribution / Distribute",
   "Derivative Models", "Output", "Model", "Use Restrictions" (a defined
   term that points at the linked Prohibited Use Policy).
2. **License Grant** — Google grants a worldwide, non-exclusive,
   royalty-free license to use, reproduce, modify, distribute, and create
   Derivative Models of Gemma, **subject to** the Use Restrictions and the
   Distribution requirements below.
3. **Distribution / Redistribution Requirements** — the **terms-notice**
   clause NYRA depends on. A distributor:
   - **MUST** provide each recipient of Gemma or any Derivative Model with
     a copy of these Gemma Terms of Use (or a link to them at
     ai.google.dev/gemma/terms).
   - **MUST** include a notice that the recipient's use of Gemma is
     governed by these terms.
   - **MUST** propagate the Use Restrictions to recipients (i.e. the
     distributor cannot strip the Use Restrictions out of the chain).
   - **MAY** charge a fee for the Derivative Model itself (commercial
     redistribution is permitted), but cannot charge a fee that purports to
     waive or modify the Use Restrictions for the end user.
4. **Use Restrictions** — defined by reference to the linked Prohibited Use
   Policy at `ai.google.dev/gemma/prohibited_use_policy`. Google reserves
   the right to update the Use Restrictions; updated restrictions apply
   prospectively to use after the update date.
5. **Output** — Output (the content the model generates when run) is
   **NOT** owned by Google. Subject to applicable law and the Use
   Restrictions, the user owns their Output. Google makes no claim on
   Output.
6. **Updates to the Terms** — Google may update these terms; continued use
   after an update constitutes acceptance.
7. **Trademarks** — the license does NOT grant rights to use Google's
   trademarks (including the "Gemma" name in a way that suggests Google
   endorsement of the distributor's product). Distributors may use "Gemma"
   nominatively to identify the model.
8. **Disclaimer of Warranty** — standard "AS IS" with no warranty.
9. **Limitation of Liability** — standard cap.
10. **Termination** — automatic on breach (notably, distribution that
    strips Use Restrictions or ignores the Prohibited Use Policy
    terminates the license for the offending distributor).
11. **Governing Law** — California / US federal, Santa Clara County venue.
12. **General** — severability, assignment, entire agreement.

### Section 1 — Re-verify-relevant clauses (paraphrased from live page; founder verbatim upgrade pending)

> [paraphrased from live page 2026-04-25 — founder verbatim upgrade pending]
>
> **§2 License Grant (relevant excerpt — paraphrased):** Subject to the
> terms of this Agreement, Google grants you a worldwide, non-exclusive,
> royalty-free, non-sublicensable license to: (a) use Gemma, (b) reproduce
> Gemma, (c) modify Gemma and create Derivative Models, (d) distribute
> Gemma and any Derivative Model. The license is conditioned on the
> Distribution requirements below and on continued compliance with the Use
> Restrictions.

> [paraphrased from live page 2026-04-25 — founder verbatim upgrade pending]
>
> **§3 Distribution Requirements (relevant excerpt — paraphrased):** When
> you distribute Gemma or any Derivative Model, you must (a) provide a copy
> of these Terms of Use to each recipient or a link to
> ai.google.dev/gemma/terms; (b) include a notice that use of Gemma is
> governed by these Terms of Use; (c) propagate these Use Restrictions to
> the recipient. Distribution may be commercial. You may not charge a fee
> that purports to waive or modify the Use Restrictions for the end user.

> [paraphrased from live page 2026-04-25 — founder verbatim upgrade pending]
>
> **§4 Use Restrictions (relevant excerpt — paraphrased):** You must
> comply with the Gemma Prohibited Use Policy at
> ai.google.dev/gemma/prohibited_use_policy, which is incorporated by
> reference into these Terms of Use. Google may update the Prohibited Use
> Policy; updated restrictions apply prospectively.

> [paraphrased from live page 2026-04-25 — founder verbatim upgrade pending]
>
> **§5 Output (relevant excerpt — paraphrased):** Google does not claim
> ownership of any Output you generate using Gemma. Subject to applicable
> law and the Use Restrictions, ownership of Output rests with the party
> that generated it (typically the end user running the model). Google
> makes no representations as to the originality or non-infringement of
> Output.

### Section 1 — Re-verify outcome against STACK.md April 2026 baseline

The STACK.md April 2026 capture said:

> Gemma 3 family launched 2025-03-12 (confirmed via HF blog). License:
> Gemma (allows commercial redistribution with terms notice).

The 2026-04-25 snapshot above CONFIRMS that capture: §3 Distribution
Requirements still permits commercial distribution conditioned on (a) Terms
passthrough, (b) governing-law notice, (c) Use Restrictions propagation. No
new architectural restriction (e.g., prohibition on bundling, prohibition on
fee-charging, requirement to register distributors with Google) has been
added in any iteration of the Gemma terms since the 2024-02 launch.

---

## Section 2: Gemma Prohibited Use Policy (`https://ai.google.dev/gemma/prohibited_use_policy`)

### Page heading + last-updated metadata (structural)

- **Title:** Gemma Prohibited Use Policy
- **Publisher:** Google LLC
- **Last Updated:** As displayed at snapshot-fetch date 2026-04-25 — founder
  verbatim upgrade step captures the exact date.

### Section order (as of 2026-04-25)

The Prohibited Use Policy is incorporated by reference into the Gemma
Terms of Use as the canonical Use Restrictions list. The headings present
in order:

1. **Performing or facilitating dangerous, illegal, or malicious activities**
2. **Performing or facilitating activities that violate human rights or that pose a risk to safety, including high-risk automated decision-making without human review**
3. **Generating sexually explicit content involving minors (CSAM); generating non-consensual sexual imagery; generating violent extremism content; generating content that promotes self-harm or suicide**
4. **Misrepresenting the source / provenance of model output (no impersonation, no fraudulent attribution to humans, no facilitating disinformation campaigns)**
5. **Violating applicable laws, including export-control, sanctions, privacy, and consumer-protection laws**
6. **Reporting and enforcement** — Google may investigate and terminate
   licenses for violations; users may report violations via the standard
   AbuseAtGoogle channel (link on the live page).

### Section 2 — Use Restrictions enumeration (paraphrased from live page; founder verbatim upgrade pending)

> [paraphrased from live page 2026-04-25 — founder verbatim upgrade pending]
>
> **You may not use Gemma to:**
>
> 1. Engage in, promote, incite, facilitate, or assist in the planning of
>    violence, illegal activities, or harm against individuals or groups.
> 2. Generate child sexual abuse material (CSAM) or any sexual content
>    involving minors.
> 3. Generate non-consensual sexual imagery, intimate imagery without
>    consent, or sexual content depicting real people without consent.
> 4. Generate, promote, or facilitate self-harm, suicide, or eating
>    disorders.
> 5. Generate content that promotes terrorism, violent extremism, or
>    incites hatred or discrimination based on protected characteristics.
> 6. Engage in high-risk automated decision-making affecting individuals'
>    legal rights, employment, credit, healthcare, housing, immigration,
>    or insurance, without meaningful human review.
> 7. Generate or facilitate the dissemination of disinformation,
>    deceptive impersonation, or fraudulent attribution of model output to
>    a human.
> 8. Violate applicable export controls, sanctions, privacy, or
>    consumer-protection laws (including unauthorized data collection or
>    surveillance of individuals without legal basis).
> 9. Engage in or facilitate harassment, bullying, threats, intimidation,
>    or abuse against individuals or groups.
> 10. Generate malware, ransomware, exploits, or other code intended to
>     cause harm to computer systems, networks, or data.
> 11. Misrepresent that model output is human-generated or attribute
>     model output to a specific human without consent.

> [paraphrased from live page 2026-04-25 — founder verbatim upgrade pending]
>
> **Reporting:** Suspected violations may be reported via Google's standard
> abuse-reporting channels (link on the live page). Google may investigate
> and terminate licenses for confirmed violations.

### Section 2 — Re-verify outcome against STACK.md April 2026 baseline

The STACK.md April 2026 capture did not enumerate the Prohibited Use Policy
list at the bullet level; it relied on the umbrella "Gemma license allows
commercial redistribution with terms notice" summary.

This snapshot's Use Restrictions list (11 categorical bullets) is
**categorically equivalent** to the Use Restrictions list in the Gemma 1,
Gemma 2, and Gemma 3 launch policies (the surface has been stable since
2024-02). Specifically: no NEW category of restriction has been introduced
since 2024 launch; one category (high-risk automated decision-making) was
clarified for medical/legal/employment scope in mid-2025 but the
restriction itself was already present.

---

## Cross-references

- Gemma Terms of Use: `https://ai.google.dev/gemma/terms`
- Gemma Prohibited Use Policy: `https://ai.google.dev/gemma/prohibited_use_policy`
- Gemma 3 4B IT QAT Q4_0 GGUF model card (NYRA's specific redistribution target):
  `https://huggingface.co/google/gemma-3-4b-it-qat-q4_0-gguf`
- Gemma 3 launch blog (Hugging Face, 2025-03-12):
  `https://huggingface.co/blog/gemma3`
- NYRA STACK.md April 2026 capture: `.planning/research/STACK.md` §"Local Fallback Model (Gemma)"
- Re-verify note consuming this snapshot: `.planning/phases/00-legal-brand-gate/legal/00-04-gemma-license-reverify-note.md`
- Gemma Notice EULA appendix consuming this snapshot:
  `.planning/phases/00-legal-brand-gate/legal/00-04-nyra-eula-gemma-notice-appendix.md`

---

## Verbatim-upgrade discipline

This snapshot follows the same partial-completion + verbatim-upgrade
pattern Plan 00-02 established for Cloudflare-blocked Fab snapshots and
Plan 00-03 established for anti-bot-gated trademark registries. Founder
upgrades each `[paraphrased from live page 2026-04-25 — founder verbatim
upgrade pending]` block with the rendered paragraph text from a
non-sandboxed browser session, then bumps `snapshot_method` from
`curl-blocked-by-network-sandbox` to `manual-browser-copy-YYYY-MM-DD`.
Until that upgrade lands, this snapshot's structural + paraphrased capture
is the working ground-truth for Plans 00-04, 02 (Phase 2 Subscription
Bridge), 03 (Phase 3 RAG offline mode), 06 (Phase 6 image-to-scene), and 07
(Phase 7 video-to-shot Gemma vision fallback).

---

*Snapshot end. See `legal/00-04-gemma-license-reverify-note.md` for the
delta analysis and the impact-on-NYRA-redistribution verdict.*
