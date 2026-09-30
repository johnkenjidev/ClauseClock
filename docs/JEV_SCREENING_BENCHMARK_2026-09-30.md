# Jev screening benchmark — 2026-09-30

Status: **shadow/advisory benchmark only**. No production extraction, finding, deadline, reminder, or action behavior is changed.

## Source of truth reconciled first

Implementation base: `clauseclock-clean-superseded-history`.

Current `main` is still behind the richer ClauseClock implementation. Draft PR #7 and PR #8 add planning/architecture notes only; neither implements semantic screening. Contest PRs/issues remain unmerged and are not used as the implementation base for this experiment.

## Goal

Evaluate whether Jev can help with bounded semantic screening around ClauseClock's existing extraction pipeline without taking authority away from deterministic code or user review.

Allowed role:
- classify whether a chunk is relevant to a requested finding family;
- score/rerank candidate chunks;
- later screen ambiguity, overlap, or evidence support in shadow mode.

Never owned by Jev:
- exact dates/deadlines/notice arithmetic;
- money calculations;
- document or user identity;
- quote/hash/offset validation;
- finding state transitions;
- legal conclusions/recommendations;
- Confirm / Correct / Dismiss;
- persistence, publication, deployment, or external action.

## Existing pipeline preserved

ClauseClock currently:
1. deterministically chunks documents;
2. uses the existing LLM locator;
3. unions locator output with deterministic regex/hint candidates;
4. extracts only from those candidates;
5. validates every source quote server-side against the original document;
6. derives dates/money/action state deterministically.

This experiment does **not** replace any of those gates.

## Smoke benchmark

Model exposed by the private Jev gateway during the run: `jev-1.13.0` through `jev-latest`.

### 1. Naive generic yes/no relevance is not safe

A generic "is this relevant?" Noul profile over-triggered on cross-family language:

| Requested family | Chunk | Jev probability |
| --- | --- | ---: |
| renewal_notice | general notice clause only | 0.69 |
| termination_right | non-renewal clause only | 0.75 |

A generic relevance profile must therefore **not** be used as a production filter.

### 2. Closed-set family choice is useful for triage

A bounded Choice profile over the ten current ClauseClock families plus `none` classified 12/12 simple smoke cases correctly:
- automatic renewal → renewal_notice
- general formal notice → notice_requirement
- annual 3% uplift → price_increase
- termination for convenience → termination_right
- invoice dispute → invoice_dispute
- SLA credit → service_credit
- warranty claim window → warranty_claim
- late charge → fee_or_penalty
- volume rebate → rebate_or_refund
- NDA confidentiality clause → none
- manual renewal → renewal_notice
- non-renewal notice → renewal_notice

Limitation: Choice returns one best family, while one real contract chunk can legitimately support multiple finding families. It is therefore suitable for triage/primary-family hints, **not authoritative filtering**.

### 3. Generic relevance Score also needs family-specific exclusions

Without narrow exclusions:
- termination_right on a non-renewal-only clause scored 1.74 / 2;
- price_increase on a late-fee clause scored 1.44 / 2.

This confirms that a broad semantic ranker can confuse neighboring contract concepts.

### 4. Explicit positive/negative family profiles are promising

After adding narrow family-specific definitions and hard negatives:

| Profile | Hard negative | Negative probability | Positive probability |
| --- | --- | ---: | ---: |
| termination_right | non-renewal/ordinary expiry only | 0.12 | 0.97 |
| price_increase | late charge/default interest only | 0.09 | 0.97 |
| renewal_notice | general notice clause only | 0.13 | 0.94 |

These profiles are materially better, but the sample is too small for production promotion.

## Decision

**Do not wire Jev into production candidate filtering yet.**

Next safe slice:
1. keep Jev shadow-only;
2. benchmark family-specific Noul/Score profiles against reviewed ClauseClock examples, including multi-family clauses and amendment language;
3. record false negatives separately from false positives;
4. preserve the deterministic hint union and existing LLM locator regardless of Jev output;
5. consider reranking only after evidence shows it improves precision without dropping relevant candidates.

No production hard-filter gate should be introduced from this smoke test.

## Promotion gate

Before any candidate is dropped because of Jev:
- benchmark against a materially larger reviewed corpus;
- include adversarial overlaps (non-renewal vs termination, late fee vs price increase, service credit vs refund, general notice vs type-specific notice);
- require zero observed loss of known relevant candidates in the evaluated set;
- retain deterministic provenance validation and user review as authority;
- promote only with an explicit separate decision.

The immediate implementation target is therefore a **reproducible shadow benchmark**, not a production dependency.
