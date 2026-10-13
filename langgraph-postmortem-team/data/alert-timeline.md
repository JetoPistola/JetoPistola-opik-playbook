# Alert timeline - INC-2291

## Pages and acknowledgements
14:04 - Deploy marker: checkout-api v4.18.0 rollout finished (all 12 pods).
14:08 - PAGE (sev2) "Checkout 5xx rate above 5% for 60s" fired to on-call Imani Okafor.
14:10 - Imani acknowledged the page.
14:19 - Escalated to sev1 after error rate reached 41% and the status page was updated.
14:36 - Error rate under 1% for five minutes; alert auto-resolved.

## Alerts that did not fire
- "DB pool saturation above 80%" exists in the runbook but was never created in the alerting system; no notification of pool waiters before customer impact.
- "Replication lag" and "DB CPU" alerts stayed green throughout, which sent the first 12 minutes of investigation toward the database.
