# Log excerpts - Brightwharf Ledger, incident INC-2291 (2026-03-12, all times UTC)

## checkout-api, 14:02-14:09
14:02:11 INFO  checkout-api v4.18.0 started, pool.max_connections=8 (read from env LEDGER_DB_POOL)
14:03:40 INFO  request POST /v1/charges 201 in 212ms
14:06:52 WARN  db pool wait time 1.9s (waiters=14)
14:07:30 ERROR db pool exhausted: timeout after 5000ms acquiring connection (waiters=61)
14:07:31 ERROR POST /v1/charges 503 in 5004ms
14:08:15 ERROR POST /v1/charges 503 in 5002ms (error rate 38% over last 60s)

## ledger-db, 14:05-14:12
14:05:02 INFO  active connections 8/200 from checkout-api (previously 96/200)
14:09:44 INFO  cpu 11%, replication lag 0.2s, no slow queries above 300ms
14:11:03 INFO  database healthy; no failover events

## checkout-api, 14:31-14:44 (after rollback)
14:31:20 INFO  rollback to v4.17.3 complete, pool.max_connections=96
14:33:05 INFO  db pool wait time 0.03s (waiters=0)
14:44:00 INFO  error rate 0.1% over last 60s
