# Jev decision layer for ClauseClock

Status: planning only; no extraction, finding, deadline, reminder, or action behavior changes.

## Fit

ClauseClock already has a strong split between model-assisted extraction and deterministic provenance/date logic. Jev is a candidate for small semantic decisions **around** that boundary.

## Candidate profiles

### Clause / finding family
- Choice: bounded finding family or `none`.
- Noul: enough context exists to attempt extraction.

### Chunk relevance
After deterministic chunking:
- Noul per chunk: relevant to the requested finding type.
- Score: relevance.

Chunk IDs, document IDs, offsets, and source identity remain server-owned.

### Ambiguity / missing context
- Noul: language is ambiguous.
- Noul: a required concept is missing.
- Noul: stronger review is needed.

### Duplicate / overlap candidate
Given existing findings:
- Noul: likely duplicate/overlap.
- Choice: best candidate or `none`.

No automatic merge or state transition.

### Candidate-value selection
Only after deterministic parsers/extractors have found explicit candidates:
- Choice: which supplied candidate best maps to a requested semantic field or `none`.

Jev must never invent the value.

### Result support
Given a finding/draft and validated excerpts:
- Noul: supplied excerpts support the statement.
- Score: support quality.

This does not replace quote validation or user review.

### QA friction
Classify corrections/extraction misses into bounded categories to improve prompts/routing later.

## Hard boundaries

Jev must not:
- calculate dates, deadlines, notice periods, amounts, formulas, or savings;
- set user_id or resolve document identity;
- validate hashes/quotes/offsets;
- create a confirmed/corrected/dismissed finding state;
- make legal/favorability recommendations;
- bypass Confirm/Correct/Dismiss;
- convert an unverified candidate into an authoritative finding.

Confidence requires calibration on ClauseClock reviewed examples.
