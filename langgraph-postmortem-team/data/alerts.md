# Alert timeline: Brightloom, 2026-10-02 (UTC)

## Alert definitions in force that day
ledger-api-5xx-rate: pages the on-call engineer when the 5xx rate is above 5% averaged over 5 minutes, evaluated every 60 s.
ledger-api-latency-p95: ticket only (no page) when p95 latency is above 2 s for 15 minutes.
db-connections-saturation: exists for the database cluster only. There is no alert or dashboard for the application-side connection pool.
Synthetic checkout probe: runs every 5 minutes from three regions, alerts the support channel, not the pager.

## Alert firings
13:58 to 14:08: ledger-api-latency-p95 breached, condition true for 15 minutes only at 14:13, so the ticket opened at 14:13.
14:03: synthetic checkout probe failed in all three regions, message posted to #support-alerts (not paged).
14:09: ledger-api-5xx-rate fired (5-minute average crossed 5% at 14:08), page sent to the on-call engineer.
14:11: on-call engineer acknowledged the page.
14:14: SEV2 declared, incident commander assigned.

## Customer-facing signals
14:02: first customer support ticket about failed payments.
14:10: status page still shows "All systems operational".
14:18: status page updated to "Investigating elevated payment errors".
14:56: status page updated to "Resolved".
Peak 5xx rate on ledger-api: 63% at 14:12. Checkout success rate fell from 99.1% to 31% at the worst point.
