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

### Stage 19 — Lapsed Ranking Score Correction (2026-08)
- **Central Rank Fix**: `analysis.compute_rank()` no longer grants a time-urgency score bonus for lapsed deadlines (`days_remaining < 0`). The bonus (`100_000 - days*100`) now applies only when `days_remaining >= 0`, so lapsed items no longer outrank genuinely urgent/future actionable ones.
- **Category Semantics Preserved**: `urgent` category still requires `action_required` AND `0 <= days_remaining <= 30`. Lapsed action items fall into the existing `risk` category (never `urgent`).
- **Scope**: Backend-only, single function change. No schema/UI/LLM changes. Action Center bucketing (lapsed -> "later") was already correct and untouched.
- **Verification**: Direct unit check via `analysis.compute_rank()` confirmed lapsed score (1,100,000) < urgent (1,199,100) and < future (1,187,800), with category `risk` for lapsed. Backend hot-reloaded cleanly with no errors.
