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

### Stage 7A — price_increase (2026-06)
- New finding type price_increase, reusing Stage 2 chunking / provenance
  validation / ranking / needs_review / Confirm-Correct-Dismiss / /accuracy.
- llm.py: locate_price + extract_price (strict JSON, verbatim sources, server
  resolves document identity). EXPLAIN generalized to "contract finding".
- analysis.compute_price (deterministic, server-side only): fixed_automatic may
  compute next_term_amount + estimated annual increase (money_kind=cost); capped
  shows max_permitted_amount + "maximum permitted, not guaranteed" (never a
  guaranteed increase); formula shows the formula until its external index is
  known (no projection); unspecified/missing amount/bare formula/objection
  window without a reference date -> needs_review. Objection deadline computed
  from price_change_date - objection_window (object before it takes effect) or
  an explicitly stated deadline. run_price_increase_analysis persists findings;
  analyze endpoint now runs renewal + price and ranks together.
- Correct is type-aware: PriceCorrectionInput + recompute_price_derived (also
  updates money_amount/kind). FindingCard + CorrectFindingDialog branch on type;
  ContractDetail shows both renewal + price findings ("What matters").
- Checks: tests/check_stage7a.py (happy +3% -> $103k next term + objection
  deadline; cap 5% -> $105k max not guaranteed; 3 ambiguity cases -> needs_review)
  PASS. Live e2e via analyze endpoint: validated fixed_automatic finding with
  sources, computed money, plain-English, rank=urgent. No Rate Shock composite /
  termination rights / other types built (out of scope).

### Stage 6D — Finish Stage 6 extras (2026-06)
- Deadline Reminders (in-app, no scheduler): reuses reminders collection.
  POST/GET /findings/{id}/reminders (fire_date = deadline - days_before),
  DELETE /reminders/{id}, GET /reminders (marks `due` when fire_date<=today &
  not sent & deadline not passed). UI: RemindersBlock on actionable FindingCards
  + "Reminders due" list on Dashboard.
- Value By Contract: GET /dashboard/value-by-contract -> per-contract confirmed
  vs pending using analysis.outcome_protected_value. UI: dashboard table.
- Outcome Timeline: GET /contracts/{id}/timeline merges findings/actions/
  evidence/outcomes chronologically. UI: Timeline section on ContractDetail.
- Savings Report: GET /reports/savings -> headline confirmed_value_protected
  (CONFIRMED ONLY; pending reported separately, never in headline) + per-line
  contract/outcome detail. UI: "Savings report" button downloads a CSV.
- Verified one path each (login as test user): reminder create/list/all/delete,
  value-by-contract (10 rows), timeline (5 events), savings report (confirmed vs
  pending split). Screenshots confirmed dashboard + finding card + timeline. No
  new clause extraction / refactors.

### Stage 7A — real-contract accuracy repair (2026-06)
- analysis.py: (1) _strip_unsupported_objection — objection fields survive only
  with a validated `objection` source, else cleared (no deadline/action; never
  inferred from a percentage/number); (2) refine_increase_semantics — precise
  regex floor/ceiling detection: "higher of X%/index" (floor) & collars ->
  formula (floor preserved, no projection); "lesser of"/pure ceiling -> capped;
  index-only -> formula. Wired into run_price_increase_analysis before
  compute_price. Strict quote validation unchanged; no fuzzy matching.
- Re-ran the same 10 SEC EDGAR contracts through the fixed pipeline: 10/10 PASS.

### Stage 7B — Rate Shock Composite (2026-06)
- New derived finding type `renewal_with_escalation` (models.FindingType).
  analysis.refresh_rate_shock_composite: builds it ONLY when a validated,
  non-dismissed renewal AND price_increase both exist; unions their already-
  validated sources (deduped, no new quotes); server-derived, no LLM. fixed ->
  next-term value + delta; capped -> max permitted (no projection); formula/
  collar/floor -> grounded formula only. Deterministic plain_english.
- Wired into analyze (rebuild + re-list) and confirm/correct/dismiss via
  _refresh_composite_for (recompute/remove when a constituent changes);
  correcting a composite is blocked (400). Uses is_composite/composite_of.
- FindingCard renders the composite; ContractDetail (What Matters) shows it.
- Verified: fixed (next-term $104k, +$4k), capped ($210k max, no projection),
  constituent-invalid (ambiguous price -> needs_review -> no composite), and
  removal on constituent dismiss. 4/4 pass.

### Stage 7C — Termination Rights (2026-06)
- New finding type termination_right, reusing extraction/provenance/review/
  ranking/explanation/What Matters. llm.locate_termination + extract_termination
  (strict: only explicit early-exit / termination-for-convenience rights; never
  inferred from generic notice/non-renewal/expiry). analysis.compute_termination
  + run_termination_analysis + recompute_termination_derived: normalizes notice
  period, computes earliest exit (explicit or effective_date + min-term lock-in),
  money = explicit termination fee only (never projected from a %), action_required
  False (standing right). Missing/ambiguous required terms (unclear type or notice
  period, or a fee stated with no amount) -> needs_review.
- server.py: analyze runs termination too; correct branch (TerminationCorrectionInput
  + recompute_termination_derived). FindingCard + CorrectFindingDialog + ContractDetail
  (What Matters) render termination_right.
- Verified: valid (for_convenience, 60d notice, earliest exit 2028-01-01, $10k fee,
  rank money); negative (non-renewal only -> no finding); ambiguous (early_exit,
  no notice period -> needs_review). 3/3 pass.

### UI implementation pass — dark canonical (2026-06)
- Flipped design tokens to DARK canonical (index.css :root + tailwind.config).
  --document stays LIGHT (#E6E1D6) = the only paper surface, reserved for
  contract evidence/requirements; added document-ink/soft/rule tokens. .cc-clause
  / .cc-section-ref now use document-ink/soft. Decorative bg-document -> bg-card;
  genuine evidence panels keep bg-document with document-ink text. Generated
  draft uses light mono on card.
- Action Center reworked to 38/62 master-detail (queue left, inline
  ChecklistPanel right; replaced the modal). Dashboard stays attention-first.
- CTA respects state: unconfirmed -> "Confirm deadline"; confirmed/corrected +
  action_required -> "Prepare notice" (-> Action Center); else Confirmed badge.
- /demo inherits the restyle automatically; Synthetic demo workspace label kept.
- Verified: Dashboard, Action Center (list + selected detail), mobile viewport
  render; one real finding's rendered clause == stored sources[].quote EXACTLY
  (incl. quote marks/dashes/spacing). No new controls added; backend untouched.

### First-use clarity (2026-06) — frontend only, no backend/data changes
- Empty Dashboard: orientation copy ("Know what matters before the deadline
  does." + 3 steps + Add a contract / See a sample workspace -> /demo). No
  onboarding state; disappears once contracts exist.
- Upload.jsx: "Start with the complete contract set" guidance + PDF/DOCX
  text-based-only note.
- ContractDetail.jsx: analysis progress shows 3 real stages (Reading / Locating /
  Verifying) with the "we don't estimate missing terms" note; no-findings state
  uses "Nothing actionable found" copy pointing to the extracted text below.
- FindingCard: unconfirmed findings show "ClauseClock won't track this deadline
  until you've checked it against the source clause."
- Public: new Home.jsx at / (dark, reuses design; Get started + See it working).
  /login gains a product line + "See it working ->" /demo. /demo gains a one-line
  hint that opening a finding reveals the exact contract language.
- Verified: /, empty dashboard, upload guidance, no-findings state all render.

### Stage 9 — Multi-document re-analysis (2026-06)
- Adding an amendment/order-form/exhibit/SLA + re-analyze now supersedes rather
  than overwrites reviewed findings. run_*_analysis delete_many now preserves
  confirmed/corrected findings (only regenerates unconfirmed/dismissed).
- analyze endpoint reconciles: if a preserved reviewed finding differs from the
  regenerated one, it keeps the old (state unchanged) and sets
  superseded_by_finding_id -> the new UNCONFIRMED replacement; if identical, the
  duplicate replacement is dropped. Returns superseded_changes.
- list_findings excludes superseded findings and returns superseded_count.
  _composite_qualifies now ignores superseded findings (composites recompute).
- ContractDetail: banner when superseded_count>0 ("a new document changed N
  previously reviewed findings…") + single-document warning that amendments may
  change the analysis. Provenance still resolves via chunk_id mapping across the
  full set.
- Sanity check passed: primary (60d notice) -> confirm -> add amendment (90d) ->
  re-analyze: old finding preserved (confirmed, superseded_by set), new
  unconfirmed replacement (90d) shown; superseded_count=1.

## Next tasks
- Await user's Stage 1 gate test (5 difficult contracts). Do not start Stage 2 until instructed.

### Anchor provenance + legacy banner patch (2026-06)
- Manual anchor override: correcting notice_anchor_type now records
  notice_anchor_origin="user", preserves the original extracted
  type/quote/location as notice_anchor_extracted_* (audit), clears the current
  notice_anchor_quote, and demotes the extracted source purpose "notice_anchor"
  -> "notice_anchor_prior" so the clause drawer no longer treats it as support
  for the user-selected anchor (still shown, clearly labelled "prior extraction
  — not applied"). Anchor-unchanged corrects keep document-derived provenance.
  Server helper _apply_anchor_provenance (server.py); Correct dialog shows a
  concise note; FindingCard shows a "Notice counts back from" fact tagged
  "set by you"/"from contract".
- Legacy banner: reusable reason-driven FindingBanner (Primitives.jsx, neutral
  info tone). Legacy renewal findings (anchor_version is None) with a stored
  deadline keep the deadline (no recompute) and show "Computed before anchor
  classification — review recommended." Component accepts a message so it can
  later render other reasons (missing effective date, unknown anchor).
- Verified statically (no LLM): anchor-change demotes source + preserves prior
  quote + recomputes (renewal_start 2028-02-01); unchanged-anchor keeps document
  provenance (term_end 90d -> 2028-01-01); legacy keeps 2028-01-31 + banner;
  classified findings unchanged. Termination inspected only (separate path).

### Notice-anchor defect fix (2026-06) — term_end vs renewal_start
- Root cause: compute_dates subtracted the notice period from next_renewal_date
  (renewal START) for every renewal, so clauses anchored to the TERM END (which
  is one day earlier) failed UNSAFE by one day (e.g. term end 2028-03-31 gave
  2028-02-01 instead of 2028-01-31).
- Fix keeps the pipeline text -> extraction/classification -> stored anchor +
  provenance -> deterministic Python math. Added notice_anchor_type
  {term_end, renewal_start, unknown} (closed set, NO default). Vocabulary
  profiles (config, not calculator branching) + LLM semantic classification
  resolve the anchor from a validated verbatim anchor quote (purpose
  "notice_anchor"); ambiguous/no-quote -> unknown. compute_dates consumes the
  classified value only; current_term_end = next_renewal_date - 1 day; unknown/
  unsupported/absent anchor REFUSES (needs_review, reason "notice_anchor_unknown")
  — never guesses. Safety invariant documented beside the enum/calculator.
- Legacy vs unknown do not collapse: Finding.anchor_version (None = legacy/never
  classified; >=1 = classified). No bulk recompute performed; legacy deadlines
  untouched. Correcting a renewal sets anchor_version and lets the user pick the
  anchor. Refusal reasons are per-reason notes (effective-date-missing vs
  anchor-unknown), preserving the future UI distinction.
- Files: backend/models.py (anchor_version), backend/analysis.py (NOTICE_ANCHORS,
  ANCHOR_VERSION, NOTICE_ANCHOR_PROFILES, resolve_notice_anchor, compute_dates,
  run_renewal_analysis, EDITABLE_FIELDS), backend/llm.py (EXTRACT_SYSTEM anchor
  schema+examples+purpose), backend/server.py (CorrectionInput.notice_anchor_type
  + anchor_version on correct), frontend FindingCard PURPOSE_LABEL + Correct
  dialog anchor select, tests/verify_notice_anchor.py, typography test fixture.
- Verified (focused only, no testing_agent/regression): DealMaker term_end
  2028-03-31 -> 2028-01-31 (leap Feb); Meridian term_end 2028-11-30 -> 2028-10-01;
  InvoiceCloud renewal_start -> 2028-02-01 (two semantics -> two anchors -> two
  deadlines); unknown/absent -> refuse. Live e2e extraction classified both
  clause types correctly. typography suite 38/38.
- Legacy impact (preview DB): 9 renewal_notice findings lack anchor_version;
  only 1 currently shows a tracked deadline (the other 8 are needs_review / no
  deadline). Recommendation reported to user; recomputation decided separately.

### Stage 8/10 — Action Center: termination + price_increase (2026-06)
- /action-center eligibility $or extended to also include termination_right and
  price_increase under the SAME generic rule (confirmed/corrected, validated,
  action_required, deterministic extracted.effective_action_deadline, not
  dismissed, not superseded). renewal branch still identical. Composite
  renewal_with_escalation intentionally NOT added (it is a derived insight, not
  an independent action).
- price_increase already produces effective_action_deadline + action_required
  from an objection window + reference date, so it qualifies with no compute
  change. termination_right was a standing right (action_required always False);
  added a tightly-gated deterministic notice deadline in compute_termination:
  when an early-exit right (for_convenience|early_exit) has BOTH a notice period
  AND a concrete earliest-exit date, effective_action_deadline = earliest exit -
  notice period and action_required=True. Otherwise unchanged (no deadline).
- ActionCenter.jsx: TYPE_LABEL entries for termination_right / price_increase;
  both reuse the existing non-renewal detail workflow (deadline, plain-English,
  suggested action, provenance, Log Action, Record Outcome) — no new UI path.
- Sanity (no testing_agent): corrected termination (for_convenience, 60d notice,
  earliest exit 2026-12-19 -> deadline 2026-10-20) APPEARS; corrected
  price_increase (3% fixed, 30d objection, price change 2026-11-19 -> objection
  deadline 2026-10-20) APPEARS; renewal preserved; composite not listed.

### Stage 8/10 — Action Center wiring for obligation types (2026-06)
- /action-center now surfaces the 6 obligation types alongside renewals, via a
  generic eligibility rule (single query extended with $or; renewal branch left
  byte-for-byte identical). An obligation joins ONLY when: state confirmed/
  corrected, action_required True, validation_status validated, a computed
  extracted.effective_action_deadline exists, and it is not superseded. This
  naturally covers "notice_requirement only when materially actionable" (a
  notice_requirement is action_required only when a deadline was computed).
  needs_review / dismissed / superseded / informational / no-deadline findings
  are excluded. Existing grouping (urgent/next_30_days/later), ranking, and
  Stage 9 supersession behaviour preserved.
- ActionCenter.jsx: per-type queue labels; the renewal Notice Checklist + non-
  renewal draft remain renewal-only; obligation findings reuse the SAME detail
  workflow (deadline, plain-English, suggested action, validated-source
  provenance, Log Action, Record Outcome, Evidence) — no parallel workflow.
- Sanity (no testing_agent, per user): corrected invoice_dispute (trigger +
  30d window -> validated deadline) APPEARS in Action Center; confirmed-but-
  needs_review warranty_claim does NOT; renewal still appears. UI verified.

### Stage 8/10 — Final build pass: 6 obligation finding types (2026-06)
- Added service_credit, invoice_dispute, notice_requirement, fee_or_penalty,
  rebate_or_refund, warranty_claim via ONE shared "obligations" pipeline
  (smallest change set; reuses chunking / provenance validation / ranking /
  review / explanations / Confirm-Correct-Dismiss).
- llm.py: locate_obligations + extract_obligations (strict JSON, returns a LIST
  of findings each tagged finding_type; verbatim quotes, server-resolved
  identity; drops clauses that fit none of the 6 types).
- analysis.py: GENERIC_TYPES, OBLIGATION_HINT, compute_generic (deterministic,
  server-side only — money from explicit amount only [credit for service_credit/
  rebate_or_refund, cost for fee_or_penalty]; deadline tracked from an explicit
  calendar date OR trigger_date + relative window; a relative window with no
  verified trigger date -> preserve the rule, mark timing needs_review, NEVER
  invent a date), run_obligations_analysis (persists 0-N findings, Stage-9-safe
  delete), recompute_generic_derived for Correct, generic fact-keys in
  generate_explanation.
- server.py: /analyze runs the obligations pass; 6 types added to the Stage 9
  reconcile loop; GenericCorrectionInput + generic branch in /correct.
- Frontend: FindingCard generic headline/subhead + key facts + purpose labels;
  CorrectFindingDialog generic fields (incl. trigger_date to compute a deadline);
  ContractDetail "What matters" filter includes the 6 types.
- Verified (sanity only, per user — NO testing_agent): live analyze over a DOCX
  with all 6 clause types produced 6 validated/needs_review findings + renewal,
  each with validated sources; needs_review windows show no invented date;
  Correct with trigger_date 2026-08-01 + 30d window computed 2026-08-31 and
  promoted to validated; frontend cards render (generic headline/type/window
  test-ids present). compute_generic unit cases pass.

### Original next tasks

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

### Stage 11 — /demo Redesign (2026-08)
- Redesigned the public, read-only synthetic sandbox workspace `/demo`.
- **Demo Overview**: Rebuilt with a prominent Top Banner, high-density stats cards (Contracts, Value, Actionable Risks, Pending Reviews) using the canonical Part 5 color family, and a bento-style responsive split grid layout (left area displays ranked alerts / What Matters, right area displays the interactive contract checklist/sidebar).
- **Demo Contract Detail**: Rebuilt as a split-screen layout proving the "Calm vs Verbatim" design system. The Left Panel displays a dark-canonical calm human summary with active-finding highlights, while the Right Panel displays a warm light document ground (`--document`) with verbatim, typewriter-style legal evidence supporting the selected finding. Fully interactive finding-selection.
- **Verification**: Fully validated and tested using Playwright browser automation, asserting 100% correctness of test IDs (`demo-synthetic-banner`, `demo-contract-detail`), contract list loading, navigation, split-panel rendering, and back-button functionality.

### Stage 12 — Mobile Layout & Navigation Fixes (2026-08)
- **Compact Mobile Navigation**: Configured `AppShell.jsx` to wrap navigation links cleanly below the ClauseClock branding on viewports smaller than 768px, ensuring full brand visibility and button accessibility without horizontal screen overflow. Left desktop navigation untouched.
- **Title Wrapping In Action Center**: Updated `ChecklistPanel` inside `ActionCenter.jsx` to use `break-words whitespace-pre-wrap` classes for contract names/titles, ensuring they wrap cleanly without causing horizontal overflow.
- **Queue/Detail Mobile Viewport State Preservation**: Preserved queue-only view when nothing is selected, detail-only full-width view when selected, and returning back via the `← Back to actions` mobile button.
- **QA Verification**: Verified successfully on mobile viewports (320px, 375px, 430px) using Playwright browser automation, confirming 100% happy paths and zero regressions.

### Stage 13 — Mobile Dashboard Redesign (2026-08)
- **Mobile Section Ordering**: Configured mobile Dashboard to render sections in the following priority order: 1. Due/Urgent Reminders, 2. Compact Watch Summary (metrics directly on the ground), 3. Confirmed Outcomes, 4. Value by contract stack. Left desktop dashboard untouched.
- **Compact Ground Typography**: Removed large bordered cards on mobile, displaying contracts monitored, value under tracking, pending value, and missed windows as a clean, solid, flat typography list.
- **$0 Outcome Line**: If confirmed value protected is $0, hides the massive $0 display and renders one muted, graceful line: "$0 confirmed value protected & recovered".
- **Reminder Wrapping & Stamp Red**: Handled flex-row wrapping inside reminders to prevent overflow and enable clean text scaling. Deadlines under 14 days use `text-stamp` red.
- **Value by Contract Stack**: Replaced wide tables on mobile with a compact card list that highlights name, confirmed/pending amounts, and hides automatically when no rows exist.
- **QA Verification**: Verified successfully using Playwright automation. 100% of Mobile layout constraints, element visibility, and no horizontal scroll assertions passed with zero defects.

### Stage 14 — Pluralization & Duplicate Disclaimer Polish (2026-08)
- **Monitored Count Pluralization**: Configured the mobile compact watch summary to pluralize monitored contracts correctly: `"1 contract"`, otherwise `"{n} contracts"`.
- **Deduplicated Legal Footers**: Removed all local redundant `LegalFooter` instances in both desktop and mobile wrappers inside `Dashboard.jsx`, allowing the legal disclaimer to render exactly once via the global `AppShell` container.
- **QA Verification**: Formally verified using Playwright browser automation on mobile and desktop viewports, confirming 100% correct pluralization logic and zero duplicate legal footers on all screen sizes.

### Stage 15 — Public Homepage Redesign (2026-08)
- **1:1 Homepage Mockup Adherence**: Replaced `/` completely with the exact structure, copy, and styles of the approved `clauseclock-homepage-1.html` as the sole source of truth.
- **Copy Adjustment**: Replaced `"Nine kinds of obligation and right..."` with `"Nine kinds of contract terms ClauseClock watches."` in the section 2 catches heading.
- **Grounded CTA Routing**: Wired all primary CTAs (`"Upload a contract"`) to the existing `/signup` destination, header sign-in link to `/login`, and product tour links to `/demo` perfectly.
- **Responsive & Scoped Animation**: Integrated the IntersectionObserver lamp-reveal scroll animation for the verbatim paper evidence section (`.paper.lit`), scoped uniquely inside the page wrapper.
- **Disclosures**: Kept only the required synthetic data disclosure inside the primary action closing footer.
- **QA Verification**: Formally linted with zero warnings and verified visually via Playwright browser screenshots.

### Stage 16 — Mobile Contracts Rebuild (2026-08)
- **Rebuilt Mobile Contracts List**: Redesigned `/contracts` lists on mobile viewports to render directly on the ground background (no bordering bg-card list background), creating an airy, solid text-first aesthetic. Left desktop layout untouched.
- **Name Wrapping & Flex-Row Overflow Fixed**: Wrapped contract titles inside `break-all sm:break-words line-clamp-2` with `min-w-0 flex-1` styling to prevent horizontal flex layout overflow.
- **In-Page Button Removal**: Hid the in-page "Add a contract" button next to the title on mobile viewports, leaving only the global header button to add agreements.
- **Tabular Numeral Styling**: Rendered annual values with `font-mono tabular-nums text-xs` formatting underneath.
- **QA Verification**: Formally verified using Playwright browser automation on mobile and desktop viewports, confirming 100% correct wrapping, button visibility, and list formatting on all screen sizes.

### Stage 17 — Lapsed Deadline Semantics & Calculations (2026-08)
- **Local Date Deadline Calculations**: Recomputed all deadline days remaining on the client side using the local browser calendar date to resolve UTC timezone offset issues (ensuring August 31, 2026 displays exactly 8 days remaining on August 23, 2026, regardless of UTC midnight).
- **Lapsed Wording & Neutral Disclaimer**: Format negative days as "X days past deadline". Displays a prominent, neutral disclaimer panel when a non-renewal window has elapsed, rather than rendering bright warning colors.
- **Action Suppression**: Completely suppresses the "Prepare notice" primary notice button once the calculated deadline date has passed.
- **Dynamic Derivation Math**: Mapped a mathematically correct subtraction formula using the Unicode minus symbol (September 10, 2026 − 10 calendar days = August 31, 2026) within `renderAnchorFact`.
- **Deduplicated Disclaimers**: Removed redundant local disclaimers in `FindingCard.jsx`, allowing Contract Detail to rely entirely on the single global AppShell disclaimer.
- **Neutral UI Buttons**: Shifted the Re-analyze, Delete contract, and disclosure toggles on mobile viewports to use standard text-ink-soft links with underline hovers, leaving stamp-red reserved strictly for urgent active deadlines.
- **Desktop Hiding & QA Verification**: Added CSS overrides to completely force-hide the desktop layout on mobile, and formally verified all corrections with 100% success using browser testing agents.

### Stage 18 — Read-Only Amendment Diff & Metadata Resolution (2026-08)
- **Resolved Document Metadata**: Augmented `/contracts/{id}/findings` and `/contracts/{id}/superseded-history` response payloads to include fully resolved source document metadata (document id, filename, document role, and location) for every citation in the `sources` list.
- **Superseded Finding History API**: Added a new user-scoped endpoint `GET /api/contracts/{contract_id}/superseded-history` returning preserved superseded findings, full completed sources with document metadata, and clear, nested replacement relationship fields (`replacement_finding`).
- **Deduplicated Source Rows**: Integrated deep row-deduplication inside both endpoints to automatically prune identical purpose/quote/document/location citations, keeping the evidence ledger lightweight.
- **Normal Findings Invariants Preserved**: Kept standard `/contracts/{id}/findings` list query untouched, ensuring superseded elements do not leak or compete with active findings. No backend schema migration or LLM calls triggered.
- **Lapsed Deadline Semantics Polish**: Fixed edge case bugs inside `FindingCard.jsx` to render urgent warning blocks and `"Prepare notice"` actions only when local days remaining evaluates as positive (`dr >= 0`). Format negative countdown values cleanly as `"X days past deadline"`.
- **QA Verification**: Formally linted with zero warnings and verified responsiveness using Playwright browsers.

### Stage 20 — Current Effective Terms + Amendment Diff (2026-08)
- **Current Effective Terms Ledger** (`CurrentEffectiveTerms.jsx`, NEW): Typography-only factual ledger (no card/paper surface, no urgency color) placed directly under contract identity, above "What matters," on both desktop and mobile Contract Detail. Rows: Current term ends, Renewal starts, Non-renewal notice period, Notice anchor, Current deadline, Notice method, Notice recipient, Annual value — each shows the resolved governing-source filename ONLY when a matching `finding.sources` purpose exists (no invented attribution). Shows "Latest amendment changes are awaiting your review." when the active finding is unconfirmed AND replaces a preserved reviewed finding.
- **Amendment Diff** (`AmendmentDiff.jsx`, NEW): `buildAmendmentDiff()` compares old (superseded) vs new (active) finding's stored `extracted` fields per-type (renewal_notice/price_increase/termination_right/generic obligations) and renders ONLY changed rows via a "Review amendment changes" disclosure (desktop + mobile). A nested "Show the evidence" toggle reveals the original + amendment verbatim quotes (paper surface) labeled with filename + doc role + location, picked from the first changed field with both a validated before/after source.
- **Mobile FindingCard Simplification**: Removed the renewal-specific "Term ends X − N days = Y" math sentence (now owned by the Ledger), replaced with a universal deadline-state line + per-type factual-consequence subhead (mirrors desktop's needsReview/termination/price/generic branching). Added previously-missing Correct + Dismiss buttons to mobile (only Confirm/Prepare-notice existed before).
- **Lapsed Tone Bug Fix**: `tone`/`urgent` computation in `FindingCard.jsx` now requires `days_remaining >= 0` before applying stamp-red styling — lapsed deadlines render neutrally on both mobile and desktop, hide "Prepare notice," and hide the reminders block for that finding.
- **Clause Drawer Dedup**: Presentation-level dedup by purpose+quote+location collapses repeated source rows (e.g. a `renewal_term` clause tagged for both initial term and renewal period).
- **No backend changes**: entirely additive frontend consuming already-enhanced `/contracts/{id}/findings` and `/contracts/{id}/superseded-history` responses.
- **QA Verification**: `testing_agent` — 11/11 acceptance criteria passed on desktop (1440x1000) + mobile (390x844), including a real end-to-end amendment scenario (10-day notice amended to 30-day notice) and a synthesised lapsed-deadline case. Zero defects, zero action items.

### Stage 21 — Contract Detail Cleanup Corrections (2026-08)
- **False Recipient Diff Fix**: `AmendmentDiff.jsx` — `notice_recipient` diff now compares normalized lowercase email-address sets (sorted) instead of raw text; reordered/re-cased but identical recipient lists no longer show a false diff row. No other field got this normalization.
- **Duplicate Notice Requirement Suppression**: `analysis.py` `_is_duplicate_notice_requirement()` — a generic `notice_requirement` finding is skipped at persist-time in `run_obligations_analysis()` when its day-count matches the CURRENT renewal_notice finding's `notice_days_min` AND its source document overlaps the renewal's own `notice_period`/`notice_anchor` source documents (i.e. it restates the same amendment clause). Unrelated/older notice_requirement findings (different day count or document) are untouched; supersession/history reconciliation unaffected.
- **Mobile Duplicate Cleanup**: Removed the inline duplicate Annual Value text from the mobile Contract Detail identity header (now shown only in the CET ledger row). Confirmed mobile FindingCard already had no standalone renewal/notice/value fact rows (that data lives only in CET).
- **Lapsed Explanation Safety**: `FindingCard.jsx` — the "Suggested action" explanation subsection (desktop + mobile) is now hidden whenever the deadline is lapsed (`days_remaining < 0`), preventing stale "act by [past date]" text; "Why it matters" and the neutral lapsed disclaimer still show.
- **QA Verification**: `testing_agent` — all 4 corrections verified against real re-analyzed contracts (10→30 day amendment with case/order-shuffled but identical recipient emails; a manually lapsed deadline). Zero defects. Two low-priority hardening notes logged (email regex edge cases; notice_basis not compared alongside day-count in dup-detection) — deferred, not blocking.

### Stage 22 — Notice Requirement Dedup Hardening (2026-08)
- **Refined `_is_duplicate_notice_requirement()`** (`analysis.py`): now also requires `notice_basis` to match when both sides have it stated, AND that the notice_requirement's own text actually references non-renewal/term-end topic wording (`_shares_renewal_topic()`) before suppressing — prevents a coincidental day-count + document match on an unrelated notice clause from being wrongly suppressed. Verified with 5 targeted unit cases (exact duplicate / different days / basis mismatch / unrelated topic / no doc overlap) — all correct.
- **Re-confirmed** (code inspection + live re-analyze + mobile screenshot, no code change needed): mobile Contract Detail already has no standalone Annual Value card and no duplicate renewal fact rows on the FindingCard (both scoped to the desktop-only `hidden md:block` wrapper since Stage 20/21) — CET is the sole owner of those facts on mobile.
- **Note**: user-referenced contract "ClauseClock_Action_Center_Test_Contract" does not exist in the preview database — likely viewed on production (not yet redeployed with Stage 20/21 fixes). No preview code change was needed for items 2/3.

### Stage 23 — Amendment Diff Persistence Across Repeated Re-analysis (2026-08)
- **Root cause**: `analyze_contract()`'s reconciliation loop (`server.py`) queried for the reviewed (confirmed/corrected) finding with `superseded_by_finding_id: None` — once that pointer was set after the FIRST post-review re-analysis, the reviewed finding was permanently excluded from future reconciliation. Any 2nd/3rd re-analysis regenerated a fresh unconfirmed finding that never got linked back, silently killing "Review amendment changes" and the CET "awaiting your review" note.
- **Fix**: the reconciliation query now finds the MOST RECENT confirmed/corrected finding of that type (sorted `created_at` desc, no pointer filter) and unconditionally refreshes its `superseded_by_finding_id` to the CURRENT unconfirmed replacement each analyze call (or resets it to `None` when the fresh replacement now matches the reviewed baseline exactly — no real change). This always compares against the nearest prior reviewed ancestor, never a stale/orphaned intermediate.
- **QA Verification**: `testing_agent` — ran 3 consecutive re-analyses without re-confirming in between; pointer correctly refreshed to a fresh id each time, amendment diff ("Notice period 10→30 days", deadline change) and CET note remained visible throughout. Zero defects, zero action items.

### Stage 24 — Action Hierarchy / Button Affordance Pass (2026-08)
- **New shared vocabulary** (`Primitives.jsx`): `BTN_PRIMARY` (filled seal-green), `BTN_SECONDARY` (outlined ink/border), `BTN_TERTIARY` (ghost text + chevron via new `DisclosureToggle`), `BTN_DESTRUCTIVE` (outlined stamp-red), `BTN_DISMISS` (lowest-emphasis text, underline on hover).
- **Primary actions** now filled seal-green instead of off-white/ink across the board: Confirm deadline, Prepare notice, Set reminder, Save corrections, Log action, Record outcome, Generate non-renewal draft, Add a contract/Add contract, Upload Document.
- **Secondary actions** (Correct, Add Document, Re-analyze, Savings report, Attach evidence, Go to Action Center) standardized to outlined ink/border pills.
- **Tertiary disclosures** (Review amendment changes, Show the evidence, Show/Hide the contract language, Show explanation details, Show contract evidence, Show extracted text) all fixed to render in sans-serif (were accidentally inheriting `.cc-section-ref`'s IBM Plex Mono — evidence-only font) with a real rotating `ChevronDown` icon replacing unicode ⌄/⌃ glyphs.
- **Destructive**: Delete contract (desktop + mobile) now consistently outlined stamp-red only, never filled at rest.
- **Dismiss**: recolored from stamp-red-on-hover to neutral ink-on-hover (dismissing a finding isn't destructive) on both mobile and desktop.
- **Bug fix**: several `variant="outline"`/`"ghost"` shadcn buttons leaked the variant's default `hover:text-accent-foreground` (near-black) over a dark hover background, making hover text nearly invisible — added explicit `hover:text-ink` overrides everywhere this occurred (Correct, Delete contract, Cancel, Savings report, Go to Action Center).
- **Scope**: styling/affordance only — no behavior, copy, routes, or backend changes. Self-tested via screenshots (desktop + mobile Contract Detail, Action Center) per explicit user instruction to skip the testing agent.
- **Reported, not fixed** (out of scope per user's explicit "styling only" instruction): `ActionCenter.jsx`'s local `urgent` computation is missing the `days_remaining >= 0` guard fixed elsewhere in `FindingCard.jsx`/`analysis.py` — a lapsed action-center item could still render with stamp-red urgency styling. Flagged for a future fix.

### Stage 25 — Action Center Lapsed Urgency Fix (2026-08)
- **Fix**: `ActionCenter.jsx` had two local `urgent` computations (`dr != null && dr <= 14`) missing the `dr >= 0` guard — one drove the detail-view stamp-red urgent-alert banner/hero date, the other drove list-row stamp-red date/day-count text. Both now require `dr >= 0 && dr <= 14`, aligning with the server-side bucketing (`server.py` already gates its "urgent" bucket by `0 <= dr <= 14`).
- **QA Verification**: `testing_agent` — lapsed item (dr=-277) confirmed neutral in both list row and detail view (no urgent-alert banner, no stamp-red classes); future urgent item (dr=7/8) still correctly shows stamp-red in both; ranking/bucketing unchanged. Zero defects, zero action items. Test data temporarily patched and fully restored.

### Stage 27 — Re-analysis Persistence Safety / Deployment Blocker Fix (2026-08)
- **Root cause**: `run_renewal_analysis`, `run_termination_analysis`, `run_price_increase_analysis`, `run_obligations_analysis` in `analysis.py` each ran `db.findings.delete_many(...unconfirmed/dismissed...)` UPFRONT, before extraction. If a later re-analysis returned early (no chunks/candidates/nothing found/no validated sources), the old unconfirmed finding was already deleted with no replacement — orphaning a reviewed finding's `superseded_by_finding_id` pointer, which made `/contracts/{id}/findings` silently treat that reviewed finding as superseded and hide it.
- **Fix**: moved each `delete_many` to run only immediately before its `insert_one`, once a genuine replacement is ready (generic obligations loop tracks a `cleared_types` set to clear each type at most once per call). Early-return paths now delete nothing, so reviewed findings/pointers are never orphaned. The derived `renewal_with_escalation` composite's delete_many (never user-reviewed, fully rebuilt every call) was untouched.
- **Verification**: manual only, per explicit user instruction (no `testing_agent`, no real LLM calls). Directly invoked the real `/analyze` endpoint logic with `llm.*` functions monkeypatched (deterministic, no network calls) against the real "Amendment Diff Test Contract" 3-link chain: (1) re-analyze → reviewed ancestor preserved, pointer set to new replacement; (2) re-analyze again without confirming → pointer refreshed to newest replacement, exactly one unconfirmed finding (no duplicates); (3) confirm + re-analyze again → history intact, exactly one current (non-superseded) finding. All assertions passed; test artifacts removed and original DB state restored afterward.
- **Scope respected**: no PDF extraction/UI/reminders/ranking changes; no schema migration; no second history system introduced.

### Stage 28 — Action Center Lapsed-State Clarity (2026-08)
- **Fix** (`ActionCenter.jsx`, renewal detail panel only): when `localDaysRemaining(effective_action_deadline) < 0`, shows a neutral status box directly under the title — "Notice window elapsed · N days past deadline" plus, when `extracted.next_renewal_date` is available, "Contract is scheduled to renew [date]." No urgency styling, no Generate/Prepare notice action (already gated by the existing `lapsed` flag from Stage 26). Log Action and Record Outcome remain available. Frontend-only, reuses `localDaysRemaining`; no backend/LLM changes.
- **Verification**: manual only, per explicit instruction (no testing_agent, no broad regression). Temporarily patched a real reviewed finding ("Amendment Diff Test Contract") with a past deadline + future renewal date, confirmed via Playwright screenshot: neutral box text exact match, `generate-draft-btn` count 0, `log-action`/`outcome-form` present. Test data fully reverted.
- **Data-integrity note**: found and fixed a stale test-data artifact left over from Stage 27's verification cleanup (a supersession pointer on the same contract pointed at a finding that had been legitimately deleted during that test run) — cleared the dangling pointer so the contract's real active finding count is coherent again. Not a code bug; was leftover test data.

### Stage 29 — Amendment-Review UI Clears After Confirmation (2026-08)
- **Root cause**: `AmendmentDiffDisclosure` (`AmendmentDiff.jsx`), rendered from `FindingCard.jsx` whenever `supersededRecord` exists (i.e. this finding once replaced a prior reviewed one), always showed the label "Review amendment changes" — with no check for whether the CURRENT finding had since been confirmed/corrected. Since supersession history is permanent, this pending-review label persisted forever, even long after the user reviewed and confirmed the replacement. (The separate CET note "Latest amendment changes are awaiting your review" was already correctly gated on `renewalFinding.state === "unconfirmed"` — no bug there.)
- **Fix**: `AmendmentDiffDisclosure` now computes `reviewed = newFinding?.state !== "unconfirmed"` and shows the neutral label "Amendment changes" when reviewed, keeping "Review amendment changes" unchanged for a still-unconfirmed replacement. No styling/color treatment existed beyond the label text (button was already a neutral `BTN_TERTIARY` ghost control), so this is a pure label swap — same collapse/expand behavior, same evidence panel, same test ids.
- **Verification**: manual only, per explicit instruction (no testing_agent, no LLM calls, no redeploy). Used a real diff pair on "Amendment Diff Test Contract" (temporarily varied `notice_days_max` to produce a genuine diff row), confirmed live on preview: reviewed (`corrected`) state → "Amendment changes" + CET pending note hidden; flipping the same finding to `unconfirmed` → "Review amendment changes" + CET pending note visible, unchanged from prior behavior. Test data fully reverted after.

### Stage 19 — Lapsed Ranking Score Correction (2026-08)
- **Central Rank Fix**: `analysis.compute_rank()` no longer grants a time-urgency score bonus for lapsed deadlines (`days_remaining < 0`). The bonus (`100_000 - days*100`) now applies only when `days_remaining >= 0`, so lapsed items no longer outrank genuinely urgent/future actionable ones.
- **Category Semantics Preserved**: `urgent` category still requires `action_required` AND `0 <= days_remaining <= 30`. Lapsed action items fall into the existing `risk` category (never `urgent`).
- **Scope**: Backend-only, single function change. No schema/UI/LLM changes. Action Center bucketing (lapsed -> "later") was already correct and untouched.
- **Verification**: Direct unit check via `analysis.compute_rank()` confirmed lapsed score (1,100,000) < urgent (1,199,100) and < future (1,187,800), with category `risk` for lapsed. Backend hot-reloaded cleanly with no errors.

### Stage 26 — Action Center Supersession Safety (2026-08)
- **Root cause**: `/api/action-center` had two divergent, both-wrong behaviors: `renewal_notice` findings had NO `superseded_by_finding_id` filter at all (a stale confirmed finding stayed fully actionable — urgency, Generate draft, Log action — even while a newer unconfirmed replacement existed), while generic/termination/price_increase types filtered `superseded_by_finding_id: None` unconditionally (silently vanishing from the queue with no signal, even when the "replacement" was itself still unconfirmed).
- **Fix** (`server.py` `action_center()`): removed the blanket filter; for any fetched finding with `superseded_by_finding_id` set, the endpoint now looks up the replacement's state — if the replacement is still `unconfirmed`, the old finding is kept and flagged `review_required: true` + `replacement_finding_id`; if the replacement is `confirmed`/`corrected`, the old finding is dropped (fully resolved, the replacement is its own queue entry). Read-only, reuses existing `superseded_by_finding_id` relationships — no schema change.
- **Fix** (`ActionCenter.jsx`): imports the shared `localDaysRemaining` from `src/lib/dates.js` (replacing server `days_remaining`) in both the queue list and detail panel. `review_required` items render a neutral panel — "Contract terms changed — review the updated finding before acting" + "Review changes" link to `/app/contracts/{contract_id}` — hiding urgency, Generate draft, Log action, Record outcome. Queue list shows "Review needed" instead of a day-count for these. Separately, any current (non-superseded) confirmed/corrected renewal finding that is lapsed (`dr < 0`) now also hides the Generate draft button (urgency already hid via existing `dr >= 0` guard); Log action/Record outcome remain available for lapsed items.
- **Verification**: manual only, per explicit user instruction (no `testing_agent`). Reproduced both scenarios against real DB data (`Amendment Diff Test Contract`'s existing 3-link supersession chain — confirmed only the finding pointing to the genuinely-unconfirmed head surfaced as review-required, older resolved links correctly dropped; then temporarily confirmed the chain head with a past deadline via direct DB edit — confirmed it alone appears, neutral/lapsed, no `review_required`) and confirmed live via Playwright screenshots on preview (queue "Review needed" label, neutral detail panel, "Review changes" navigates to Contract Detail). Verified `localDaysRemaining('2026-08-31')` from Aug 24 = 7 days. All test DB mutations reverted after verification. Deployment-blocking destructive DB deletes (`analysis.py`) and pdfplumber column interleaving remain unaddressed, per explicit user instruction to skip.
