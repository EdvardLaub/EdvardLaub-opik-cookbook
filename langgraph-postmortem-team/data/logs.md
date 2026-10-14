# Log excerpts: Brightloom production, 2026-10-02 (UTC)

## ledger-api, 13:52 to 13:54
13:52:07 INFO  ledger-api-7f9c rollout started, release r4411, 12 pods
13:52:41 INFO  config loaded: db.pool.maxConnections=10 db.pool.minIdle=10 db.pool.timeoutMs=30000
13:53:12 INFO  ledger-api-7f9c readiness probe passed (GET /healthz 200, no database call)
13:54:30 INFO  rollout complete, 12/12 pods ready, canary stage skipped (config-only change)

## ledger-api, 13:58 to 14:03
13:58:44 WARN  HikariPool-1 - pool at 10/10 active, 23 threads waiting
13:59:58 WARN  request GET /v2/invoices slow: 4120 ms (p95 baseline 180 ms)
14:01:15 ERROR HikariPool-1 - Connection is not available, request timed out after 30000ms
14:02:02 ERROR POST /v2/payments/capture failed: 503 upstream timeout (ledger-api)
14:03:20 ERROR checkout-web: ledger-api returned 503 for 61 of the last 100 requests

## database cluster, 14:00 to 14:30
14:00:00 INFO  pg-ledger-primary connections: 118 of 800 used, CPU 14%, replication lag 0.2 s
14:15:00 INFO  pg-ledger-primary connections: 120 of 800 used, CPU 12%, replication lag 0.1 s
14:26:00 INFO  pg-ledger-primary healthy, no failover events in the last 24 h

## invoice-worker, 14:05 to 14:50
14:05:30 WARN  invoice-worker retrying capture for 212 invoices, ledger-api unavailable
14:30:00 WARN  invoice-worker retry queue depth 1,940 invoices
14:48:10 INFO  invoice-worker retry queue draining, depth 1,100
14:55:00 INFO  invoice-worker retry queue empty, 2,310 invoices captured late, 0 lost

## ledger-api, 14:44 to 14:52
14:44:50 INFO  rollout started, release r4410 (rollback), 12 pods
14:46:35 INFO  config loaded: db.pool.maxConnections=100 db.pool.minIdle=20 db.pool.timeoutMs=30000
14:49:10 INFO  HikariPool-1 - pool at 38/100 active, 0 threads waiting
14:52:00 INFO  checkout-web: ledger-api error rate 0.2% (baseline 0.2%)
