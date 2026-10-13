# Incident channel transcript - #inc-2291

## 14:08-14:20
[14:10] Imani Okafor: ack. checkout 503s, looks like DB trouble? checking ledger-db dashboards
[14:13] Imani Okafor: DB cpu and lag are fine. weird.
[14:14] Dev Nakamura: could be the payment-provider sandbox? we had a flaky partner last month
[14:16] Dev Nakamura: partner status page is green, scratch that
[14:18] Priya Raman: ledger-db shows only 8 connections from checkout. that looks wrong, it was ~96
[14:19] Imani Okafor: escalating to sev1, updating status page

## 14:20-14:40
[14:24] Priya Raman: v4.18.0 moved pool config to central config. default is 8. that's it
[14:26] Tomas Lindqvist: oh no, I assumed the central default matched the old value. my bad, I should have checked
[14:28] Imani Okafor: rolling back to 4.17.3
[14:36] Imani Okafor: error rate under 1%. holding rollback in place
[14:40] Priya Raman: let's not blame Tomas, review passed, canary passed, the process let this through

## Follow-ups proposed in channel
- Alert on DB pool waiters and saturation.
- Add config-default diff to the deploy checklist.
- Canary under realistic concurrency, or load-test pool changes.
