# ClauseClock contest-readiness audit — 2026-08-21

## Scope
Only gaps that materially affect the voter/judge path or could waste the next Emergent credits.

## Current contest position
- Public Builder Fest gallery: ClauseClock is at 29 votes as of 2026-08-21.
- Current public gallery shows 640 entries; ClauseClock is tied around the top 15.

## Highest-impact static gap: public demo is behind the product

### Verified from current `main`
- `/demo` is still the Stage 5 synthetic workspace and explicitly contains no Stage 6 actions/evidence/outcomes.
- `App.js` routes `/demo/actions` back to `Demo`, so clicking **Action Center** does not show the real Action Center experience.
- `App.js` routes `/demo/contracts` back to `Demo`, so clicking **Contracts** also returns to the overview rather than a dedicated contracts view.
- `demoWorkspace.js` currently showcases only `renewal_notice` findings, while the production code now supports price increases, termination rights, six obligation types, multi-document re-analysis, actions, evidence, outcomes, and reminders.
- `DemoContractDetail.jsx` still labels the section `What matters — renewals`.
- `Home.jsx` describes the product primarily as renewal and pricing detection, underrepresenting the current broader action workflow.

## Recommendation
First contest-facing build should be a **public demo refresh**, not another backend feature.

Target state:
1. Keep `/demo` synthetic and read-only.
2. Add representative synthetic findings for current capabilities: renewal, price increase, termination right, and one obligation with a deadline.
3. Give `/demo/actions` a real read-only Action Center view using static demo data.
4. Give `/demo/contracts` a real contracts list (or make the navigation intentionally return to a clearly labeled portfolio view rather than pretending it is a separate page).
5. Rename `What matters — renewals` to `What matters`.
6. Broaden the public homepage copy to match the product that actually exists.

## Why this outranks more feature work
The public demo is the path a voter or judge can inspect without creating an account. Right now that path hides much of the product already built. Refreshing it improves presentation without changing extraction, auth, Mongo models, API contracts, or LLM schemas.

## Do not spend the next credits on
- Two-column PDF extraction work
- Dead-code cleanup
- Large refactors
- New finding types
- Broad regression/testing-agent runs unless the live path exposes a failure

## Next runtime check
Before deploying the refresh, manually verify the live public path:
`/` → `/demo` → open finding/source clause → Contracts → contract detail → Action Center.
