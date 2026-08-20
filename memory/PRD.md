# ClauseClock — PRD

## Original problem statement
Build ClauseClock (FastAPI + MongoDB + React) in controlled stages from the
provided specification. Prompt 0 = architecture/models/design scaffolding only.
Stage 1 = contract ingestion (auth, upload, extraction, scanned detection,
provenance, hard deletion). Strict server-side user_id isolation; multi-source
provenance model; normalized finding layer; composite-finding support; ISO
YYYY-MM-DD contractual dates; validated-findings vs user-confirmation state;
the Part 5 ClauseClock design system (not a generic AI-SaaS look).

## Architecture
- Backend: FastAPI, Motor (async MongoDB). Files: server.py, models.py, auth.py, ingestion.py.
- DB: MongoDB. Collections: users, contracts, documents, findings, actions, outcomes, reminders (+ GridFS fs.files/fs.chunks for originals).
- Frontend: React + react-router + shadcn/ui + Tailwind. Part 5 design tokens in index.css/tailwind.config.js.
- Auth: JWT access(12h)+refresh(7d) in httpOnly/Secure/SameSite=none cookies; bcrypt hashing.

## User personas
- Operator/solo business owner tracking third-party contract obligations & deadlines.
- Contest voter/judge (read-only /demo — not yet populated).

## Core requirements (static)
- user_id ALWAYS server-derived, never from client; every query scoped by user_id.
- Multi-source provenance (sources[] never empty; document_id resolved from chunk_id).
- Normalized layer + ranking + explanations computed server-side (Stage 2+).
- ISO YYYY-MM-DD calendar strings for contractual dates (no tz conversion).
- Real hard deletion incl. stored originals. No soft-delete flag.
- Part 5 design system applied from the first screen.

## Implemented
### Prompt 0 (2026-08-20)
- All 7 collections + Pydantic models (PyObjectId/BaseDocument); user_id indexes.
- Part 5 design system (palette, Archivo/Archivo Expanded/IBM Plex Mono, two registers).
- Route shells: /app (Dashboard, Contracts, Contract detail, Finding detail, Action Center, Upload), /accuracy, /demo. Auth dependency stub.

### Stage 1 — contract ingestion (2026-08-20)
- Working session auth: register/login/logout/me; bcrypt; JWT httpOnly cookies; seeded test user.
- Strict user_id isolation verified (401 unauth, 404 cross-user, client user_id ignored).
- Add contract / Upload flow: PDF + DOCX; name, counterparty, doc_role, optional annual_value+currency.
- Originals stored in GridFS (storage_key = file id); records sha256/mime_type/size_bytes/filename/file_type/doc_role/page_count/uploaded_at.
- Text extraction: pdfplumber (page markers + tables), python-docx (section/heading/paragraph markers). Stored in documents.raw_text; inspectable on contract detail.
- Scanned detection: <100 chars/page -> extraction_method='failed_no_text' + exact message; no OCR.
- Annual-value provenance: user_entered only; extraction fields left null.
- Real hard deletion: GridFS originals + documents + dependent records cascade; verified.
- Tests: /app/backend/tests/test_clauseclock_stage1.py (11/11 pass).

### Stage 2 — renewal_notice extraction (2026-08-20)
- Two-pass AI pipeline (locate -> extract) over readable docs; model-agnostic LLM layer (`llm.py`, Claude Sonnet 4.6 default, env-swappable via LLM_PROVIDER/LLM_MODEL, Emergent key).
- Transient chunking (~3000/~200) with server-side chunk_id -> document_id/char-range/location binding (`analysis.build_chunks`).
- Strict-JSON extraction; server-side source validation (quote verified verbatim vs resolved document raw_text, whitespace-normalized; char_offset + location resolved server-side; model never sets document identity).
- Required-purpose gating (renewal_term + notice_period), needs_review on missing required source / notice_days_min null / missing effective_date / business-days-without-definition. No deadline shown when needs_review.
- Deterministic server-side date math (next renewal, action_deadline, earliest_action_date, effective_action_deadline, days_remaining); deemed-receipt only when explicitly stated + measured_to received.
- Normalized layer server-side (action_required = automatic; money_amount/currency/kind=contract_value). Annual-value provenance (extracted sets value_source='extracted' with provenance; never overwrites user_entered).
- Endpoints: POST /api/contracts/{id}/analyze, GET /api/contracts/{id}/findings (user-scoped).
- UI: FindingCard (hero deadline Archivo Expanded, days remaining, stamp/pending/neutral tone, key facts, confidence) + signature clause drawer grouping verbatim quotes by purpose with server-resolved locations. No plain-English (Stage 4).
- Tests: /app/backend/tests/test_clauseclock_stage2.py (9/9) + gate regression (7/7); frontend E2E happy + needs_review. iteration_3.json.
- Stage 2 defect fixes (marker-tolerant strict validation Fix A; zero-source invariant; multi-purpose sources): iteration_4/5.
- Stage 2 accuracy repair (2026-08-20): 1:1 typographic normalization in validation (curly quotes/dashes/nbsp; offset-preserving; still strict, no fuzzy), deterministic high-recall locate union (RENEWAL_HINT) + one found:false retry. Verified 89/89 (iteration_6). Live 10-contract re-run: provenance 56/56, #10 computes correct deadline (2028-02-01), all findings carry validated renewal_term; no zero-source findings.

## Backlog (prioritized)
### Stage 3 — confirmation + accuracy (2026-08-20)
- Confirm/Correct/Dismiss on renewal_notice findings (server-scoped by user_id): confirm sets state+confirmed_at (extracted unchanged); correct edits the 14 extracted fields, snapshots original_values (first time), records exact corrected_fields, recomputes derived dates via deterministic Stage 2 logic (no LLM), state=corrected; dismiss sets state, preserves provenance.
- Internal GET /api/accuracy + /accuracy page: reviewed, confirmed_no_edits, corrected, correction_rate_pct, corrected_field_frequency, by_type (instrumentation only, not learning).
- Files: server.py (CorrectionInput + 3 finding endpoints + accuracy), analysis.py (EDITABLE_FIELDS, recompute_derived), FindingCard.jsx + CorrectFindingDialog.jsx + Accuracy.jsx. Tests: test_clauseclock_stage3.py (14/14) + 89/89 regression. iteration_8.
- Known minor: a no-change Correct still sets state=corrected (corrected_fields stays empty, so no fake fields) — counts as a review in /accuracy; left as-is per minimal-change scope.

- P0 (Stage 2): AI clause extraction pipeline (chunk/locate/extract/validate), findings creation.
- P1 (Stage 3-5): deadline computation, ranking, explanations, Confirm/Correct/Dismiss, composites.
- P1 (Stage 6): reminders (needs verified background scheduling).
- P1 (Stage 7): notice drafting, Action Center, outcomes.
- P2: dashboard metrics, /accuracy metrics, populated /demo synthetic workspace with floating date anchor.
- P2: encryption-at-rest for originals; account deletion cascade; Terms/privacy copy.

## Known limitations (extraction)
- Two-column PDFs read in block order (may interleave); pdfplumber tables are heuristic.
- DOCX has no reliable page_count (paragraph/heading markers used instead).
- Scanned/image PDFs unreadable by design (OCR out of scope).
- No refresh-token auto-rotation route yet (hard 401 after access token expiry).

## Next tasks
- Await user's Stage 1 gate test (5 difficult contracts). Do not start Stage 2 until instructed.

### Stage 6C2 — value accounting + dashboard (2026-06)
- analysis.outcome_protected_value: deterministic per-outcome value.
  terminated -> term_value_avoided (avoided next term only, never annualized);
  renegotiated -> renegotiated_annual_delta (confirmed annual saving, not full
  contract value); credit_received/dispute_resolved -> amount_recovered;
  reviewed_and_kept -> $0 (valid, non-failure); missed -> $0.
- GET /api/dashboard/summary (user-scoped): contracts_monitored,
  value_under_tracking (sum annual_value), confirmed_value_protected (CONFIRMED
  outcomes only = headline), pending_value (unconfirmed outcomes),
  windows_missed (result=missed), outcomes_recorded, currency, by_result.
- Dashboard.jsx: headline "Confirmed value protected & recovered" + 4 stat cards
  (contracts monitored, value under tracking, pending value, windows missed).
  Empty state unchanged when no contracts. Uses existing Part 5 components.
- Focused check: tests/check_stage6c2.py (known set -> confirmed 57000, pending
  9000, missed 1) PASS. Live endpoint verified. No reminders / new extraction
  types added (explicitly out of scope for 6C2).
