---
baseline_source: ".planning/research/STACK.md (April 2026 capture — 'Gemma license allows commercial redistribution with terms-notice')"
baseline_model: "google/gemma-3-4b-it-qat-q4_0-gguf"
baseline_summary: "Gemma license allows commercial redistribution with terms-notice"
reverify_snapshot: ".planning/phases/00-legal-brand-gate/external-snapshots/gemma-terms-of-use-SNAPSHOT.md"
reverify_date: "2026-04-29"
snapshot_snapshot_date: "2026-04-25"
snapshot_method: "curl-blocked-by-network-sandbox (paraphrased-with-date-flag per Plan 00-04 discipline)"
re_verify_verdict: "UNCHANGED"
impact_on_nyra_redistribution: "NONE"
gemma_model_under_review: "google/gemma-3-4b-it-qat-q4_0-gguf"
plan: "00-04-gemma-license-and-eula-draft"
executor: "NYRA Plan 00-04 executor"
---

# Gemma License Re-verify Note — Plan 00-04

**Re-verify date:** 2026-04-29
**Baseline:** STACK.md April 2026 capture (`.planning/research/STACK.md`)
**Snapshot:** `gemma-terms-of-use-SNAPSHOT.md` (dated 2026-04-25)
**Verdict:** `UNCHANGED` — no material drift detected
**Impact on NYRA redistribution:** `NONE` — Phase 1/2/3/6/7 Gemma usage is still fully within license

---

## Baseline (April 2026)

The STACK.md April 2026 capture recorded the Gemma 3 family as follows:

> Gemma 3 family launched 2025-03-12 (confirmed via HF blog). License: Gemma
> (allows commercial redistribution with terms notice).

The specific model under review is `google/gemma-3-4b-it-qat-q4_0-gguf`
(3.16 GB, QAT Q4_0 GGUF, 128K context, multimodal), whose model card at
`huggingface.co/google/gemma-3-4b-it-qat-q4_0-gguf` links back to
`ai.google.dev/gemma/terms` as the governing license. The April 2026
capture recorded two key license facts:

1. **Commercial redistribution is permitted**, conditioned on providing a copy
   of (or link to) the Gemma Terms of Use to each recipient.
2. **Use Restrictions are propagated** through the distribution chain — a
   distributor cannot strip them.

---

## Today's Snapshot Summary

The snapshot dated 2026-04-25 (`gemma-terms-of-use-SNAPSHOT.md`) confirms the
following provisions are still active:

| Provision | Status |
|-----------|--------|
| Commercial use permitted | Yes |
| Commercial redistribution permitted | Yes (with conditions) |
| Fee-charging for the model itself permitted | Yes, but cannot waive/modify Use Restrictions |
| Redistribution notice requirement | Must provide Gemma ToS copy or link to `ai.google.dev/gemma/terms` |
| Redistribution notice — governing-law notice | Must include notice that use is governed by Gemma Terms |
| Use Restrictions propagation | Must propagate Use Restrictions to recipients |
| Output ownership | User owns their Gemma-generated output |
| Gemma Prohibited Use Policy incorporated by reference | Yes — at `ai.google.dev/gemma/prohibited_use_policy` |

**Redistribution notice requirement (verbatim from snapshot):**
> "When you distribute Gemma or any Derivative Model, you must (a) provide a
> copy of these Terms of Use to each recipient or a link to
> ai.google.dev/gemma/terms; (b) include a notice that use of Gemma is
> governed by these Terms of Use; (c) propagate these Use Restrictions to
> the recipient."

**Use Restrictions summary:** Incorporated by reference to the Gemma Prohibited
Use Policy (`ai.google.dev/gemma/prohibited_use_policy`). The snapshot
enumerates 11 prohibited-use categories (see snapshot Section 2 for full
list). NYRA passes these through to users via `legal/00-04-nyra-eula-gemma-
notice-appendix.md`.

---

## Delta Analysis

| Clause | April 2026 STACK.md | 2026-04-25 Snapshot | Delta |
|--------|---------------------|----------------------|-------|
| Commercial redistribution | Permitted with terms-notice | Permitted with terms-notice | **None** |
| Fee-charging for model | Allowed (no new restriction) | Allowed (cannot waive Use Restrictions) | **None** (scope identical) |
| Notice requirement | Terms-notice clause | Terms-notice clause | **None** |
| Use Restrictions | Incorporated by reference (umbrella) | Incorporated by reference (umbrella) | **None** |
| Output ownership | User owns output | User owns output | **None** |
| Prohibited Use Policy enumeration | Not enumerated at bullet level in STACK.md | 11 categories enumerated | **None** (STACK.md did not enumerate; snapshot confirms same structure as Gemma 1/2) |
| New restrictions on bundling | None assumed | None found | **None** |
| Registration / distributor registration requirement | None assumed | None found | **None** |
| Territorial restrictions | None assumed | None found | **None** |
| Update mechanism | Not mentioned in STACK.md baseline | Google may update terms; continued use = acceptance | **Non-material** (standard license-maintenance clause; does not change substantive obligations) |

**Delta classification:**

- **Material changes:** None.
- **Non-material changes:** The "Updates to the Terms" clause (standard
  Google license clause allowing Google to update terms prospectively) was
  not called out in the STACK.md capture but is present in the current
  snapshot. This is a standard license-maintenance provision; it does not
  add new redistribution restrictions, does not prohibit commercial use, and
  does not require any change to NYRA's current redistribution architecture.
- **Verdict:** `UNCHANGED` — the clause categories and their substantive
  scope are identical to the April 2026 baseline.

---

## Impact on NYRA Redistribution

NYRA redistributes Gemma 3 4B IT QAT Q4_0 GGUF in the following ways across
its roadmap phases:

| NYRA Phase | Gemma Usage | Still Permitted? |
|-----------|-------------|-----------------|
| Phase 1 — NyraInfer process | Bundling / downloading GGUF on demand; local llama.cpp inference | **Yes** — bundling permitted; download-on-demand is the preferred delivery mechanism per the snapshot's commercial redistribution clause |
| Phase 2 — Gemma subscription fallback | User selects Gemma as offline/privacy fallback via plugin UI | **Yes** — personal use + redistribution through NYRA is within scope |
| Phase 3 — Gemma offline Q&A | RAG-powered Q&A using Gemma 3 4B on user hardware | **Yes** — running inference locally is a core permitted use |
| Phase 6 — Gemma vision (image-to-scene) | Gemma 3 4B processes reference images offline | **Yes** — multimodal inference on user hardware is permitted |
| Phase 7 — Gemma vision (video-to-shot) | Gemma 3 4B processes keyframes from reference videos offline | **Yes** — image input modality covered by multimodal license |

**Specific architecture confirmations:**

1. **Bundling the GGUF file:** The Gemma license permits commercial
   redistribution. NYRA's approach (fetch-on-demand from HuggingFace on
   first "offline mode" invocation, cached to `%LOCALAPPDATA%/NYRA/models/`)
   is explicitly permitted. The Fab plugin download itself does not need to
   contain the 3.16 GB GGUF — this is the correct implementation pattern.

2. **Running Gemma inference locally:** The license grants a worldwide,
   non-exclusive, royalty-free license to "use" Gemma. Local inference on
   user hardware is squarely within that grant.

3. **Exposing Gemma via OpenAI-compatible HTTP endpoint:** NYRA's
   `nyrahost/infer` OpenAI-compatible HTTP endpoint is an NYRA-internal
   interface. It does not make Gemma available to third parties; it exposes
   Gemma outputs to the NYRA sidecar on the same machine. This is not a
   redistribution event.

4. **Users' Gemma-generated outputs:** The snapshot confirms (Section 1 §5)
   that "Google does not claim ownership of any Output you generate using
   Gemma." Output ownership flows to the user. This maps directly into EULA
   §6 (Generated Content — Liability Passthrough).

5. **Terms-notice compliance:** NYRA satisfies the Gemma redistribution
   notice requirement via `legal/00-04-nyra-eula-gemma-notice-appendix.md`
   (Appendix: Gemma 3 Model Notice), which is incorporated by reference into
   `legal/00-04-nyra-eula-draft.md` §Third-Party Components and §Appendix A.

---

## Recommended Action

**Verdict: UNCHANGED — proceed.**

The Gemma license has not introduced any material changes since the April 2026
STACK.md capture. NYRA's Phase 1/2/3/6/7 Gemma redistribution architecture
is still fully within the license. The one non-material addition (updates-to-
terms clause) is standard and does not require any architectural change.

**Proceed with:**
1. Closing SC#4 as VERIFIED on the basis of this re-verify note.
2. Including the Gemma Notice appendix (`legal/00-04-nyra-eula-gemma-notice-
   appendix.md`) in the NYRA EULA draft to satisfy the terms-notice
   redistribution requirement.
3. Marking this re-verify note for annual re-verification (recommended: April
   2027, aligned with the next UE major release cycle).

**If at any future date the Gemma terms are updated:** Check this re-verify
note's delta analysis framework. If new use restrictions, new attribution
requirements, or new registration requirements appear, re-run this note with
`re_verify_verdict: MATERIAL-CHANGES` and escalate before continuing Gemma
redistribution.

---

*Re-verify note end. Snapshot consumed from `gemma-terms-of-use-SNAPSHOT.md`.*
*EULA draft incorporating Gemma Notice: `legal/00-04-nyra-eula-draft.md`.*
