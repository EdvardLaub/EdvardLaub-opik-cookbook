# Incident channel transcript: #inc-2026-10-02-payments (UTC)

## 14:11 to 14:20
14:11 on-call: ack'd the 5xx page. ledger-api returning 503s, checking recent deploys and pod health.
14:13 on-call: pods all healthy, restarts 0. Nothing alarming in the pod list.
14:14 ic: declaring SEV2. I'm IC. Need comms and a scribe.
14:16 on-call: I see slow queries in the app logs, wondering if the primary is struggling.
14:18 comms: status page updated to investigating.
14:20 ic: let's treat the database as the lead hypothesis. Can the DB team check the primary?

## 14:21 to 14:35
14:26 dba: primary is fine. 118 of 800 connections, CPU 12%, no failover. It is not the database.
14:28 on-call: then maybe the network between ledger-api and the database? checking.
14:31 on-call: found "Connection is not available, request timed out after 30000ms" from HikariPool. That is the app pool, not the db.
14:33 ic: why would the pool be exhausted at this traffic level? Pool size?
14:35 on-call: checking config, the pool size should be 100.

## 14:36 to 14:55
14:36 on-call: it's 10. maxConnections=10 since r4411 at 13:52. The PR meant to change minIdle.
14:37 ic: roll back r4411. Rollbacks need a second approver, paging the platform lead.
14:38 ic: approval requested in deployctl.
14:41 ic: no answer from the secondary approver in chat, calling by phone.
14:43 platform-lead: on the phone, I can approve from my laptop now.
14:44 platform-lead: approved. Rollback rolling.
14:49 on-call: pool at 38/100, waiting threads at 0.
14:52 ic: error rate back to baseline. Keeping the channel open while invoice-worker drains retries.
14:55 ic: retry queue empty, 2,310 invoices captured late, none lost. Closing SEV2, status page to resolved at 14:56.

## Afterwards, 14:58 to 15:10
15:02 ic: three things stand out for the review: nothing told us the pool was saturated, config skipped canary, and the rollback approval cost 6 minutes.
15:06 scribe: reminder to keep the review blameless. The PR author and the reviewer both followed the process as written.
15:09 on-call: the first 17 minutes went to the database hypothesis; I did not see the pool log line until 14:31.
