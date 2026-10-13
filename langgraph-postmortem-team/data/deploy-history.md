# Deploy history - checkout-api

## 2026-03-12
- 13:41 v4.18.0 canary at 5% (1 pod) - low traffic window, canary soaked 15 minutes, no alerts.
- 14:00 v4.18.0 promoted to 100%. Change author: Tomas Lindqvist. Reviewer: Priya Raman.
- 14:02 Change summary: "Move DB settings to central config service; remove hardcoded pool size." The central config default for LEDGER_DB_POOL was 8; the old hardcoded value was 96.
- 14:31 Rollback to v4.17.3 initiated by on-call; completed in 4 minutes.

## Earlier deploys (context)
- 2026-03-05 v4.17.3 - fixed currency rounding bug. No incidents.
- 2026-02-26 v4.17.2 - dependency bumps. No incidents.

## Process notes
The canary ran at 14:00 on only one pod, whose traffic never reached more than 8 concurrent database connections, so the smaller pool was never stressed. The change checklist has no item for configuration defaults.
