# Deploy history: ledger-api, 2026-10-01 to 2026-10-02

## r4409, 2026-10-01 16:10 UTC
Type: code change. Author: payments team. Change: add idempotency key to /v2/payments/capture.
Pipeline: unit tests, integration tests, canary at 5% for 15 minutes, full rollout. Result: success.

## r4410, 2026-10-02 09:30 UTC
Type: code change. Author: invoicing team. Change: paginate /v2/invoices for large accounts.
Pipeline: unit tests, integration tests, canary at 5% for 15 minutes, full rollout. Result: success.
Config at this release: db.pool.maxConnections=100, db.pool.minIdle=20.

## r4411, 2026-10-02 13:52 UTC
Type: config-only change, PR #2208 "Reduce idle database connections overnight".
Intent: lower db.pool.minIdle from 20 to 10 to save connections during the quiet hours.
Actual diff: db.pool.maxConnections changed from 100 to 10, minIdle left at 20 then clamped to 10.
Review: one approval, reviewer saw only the title and a two-line diff, no rendered config.
Pipeline: config validation (syntax only), canary skipped because config-only changes bypass canary
by the rule "skip_canary: true for files under /config". Result: success, full rollout in 2.5 minutes.

## r4410 rollback, 2026-10-02 14:44 UTC
Type: rollback to r4410 using `deployctl rollback`. Approval policy: production rollbacks need a second
approver. The incident commander requested approval at 14:38; the secondary approver was reached by phone
at 14:43 and approved at 14:44. Result: success, full rollout in 2 minutes.

## r4412, 2026-10-03 10:05 UTC
Type: config fix, PR #2214 "Restore maxConnections=100 and add config schema bounds".
Pipeline: canary now runs for config changes touching db.pool.*. Result: success.
