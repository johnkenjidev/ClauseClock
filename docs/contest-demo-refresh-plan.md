# Contest demo refresh plan

This file intentionally contains no production-code changes. The public demo refresh should be prepared on a feature branch before merging/deploying.

## Goals
- Make the unauthenticated demo reflect capabilities already implemented in production.
- Keep all demo content synthetic and read-only.
- Avoid backend, database, auth, extraction, schema, or LLM changes.

## Minimum changes
- Add static demo examples for `price_increase`, `termination_right`, and one deadline-bearing obligation alongside `renewal_notice`.
- Add a read-only demo Action Center route rather than routing `/demo/actions` back to the overview.
- Make `/demo/contracts` intentional and distinct.
- Change `What matters — renewals` to `What matters`.
- Broaden homepage copy without adding unsupported claims.

## Gate
Do not merge until the resulting frontend builds cleanly and the live deployment can be manually clicked through.
