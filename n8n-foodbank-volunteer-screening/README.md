<div align="center">

# 🥫 n8n-foodbank-volunteer-screening

*A no-code sign-up screener for a food bank, with every run traced in Opik by hooks rather than nodes.*

[![n8n](https://img.shields.io/badge/n8n-2.41.7-ea4b71?style=flat)](https://n8n.io)
[![model](https://img.shields.io/badge/model-gpt--4o--mini-10a37f?style=flat)](https://platform.openai.com/docs/models/gpt-4o-mini)
[![tracing](https://img.shields.io/badge/tracing-OpenTelemetry-f5a800?style=flat)](https://opentelemetry.io)
[![runs in](https://img.shields.io/badge/runs%20in-Docker-2496ed?style=flat)](https://docs.docker.com/compose/)

</div>

Volunteer coordinators at small food banks get sign-ups from a web form at all hours, and each one needs the same judgement call: which shift fits this person, and is anything missing before we can say yes? An n8n workflow with one LLM node can make that call in a couple of seconds. The hard part comes a month later, when someone asks why a 16-year-old was offered a warehouse shift or why a would-be driver got a phone call instead of a slot. Nobody wrote code, so there is no log to read. This example makes every execution of the workflow a trace in Opik without touching the workflow itself.

## What you'll build

A self-hosted n8n with a six-node workflow for the fictional **Millbrook Community Pantry**:

**Sign-up webhook → Screen sign-up (gpt-4o-mini) → Needs follow-up? → Offer a shift *or* Queue for coordinator call → Reply to form**

The model picks one role (warehouse sorting, front-desk intake, delivery driving, or none) against the pantry's rules: minimum ages of 16, 18 and 21, and an explicitly mentioned driving licence for deliveries. It also sets `needs_followup` when something required is missing. The IF node routes the sign-up down one of two branches, and the webhook replies with the result.

Opik is wired in below the canvas. The Docker image installs the `n8n-observability` package and sets `EXTERNAL_HOOK_FILES`, so n8n emits an OpenTelemetry span for each execution and for each node that ran. The exporter in `docker-compose.yml` sends them to Opik's OTLP endpoint with a `projectName` header. The workflow JSON contains no tracing nodes at all.

## See it in Opik

Open the **`n8n-foodbank-volunteer-screening`** project. After one `./demo.sh` it holds **4 traces**, all named `Food bank volunteer screening`, one per sign-up. Each took between 1.3 and 2.1 seconds.

Open any trace and the span tree is the path that sign-up took through the canvas: the execution root, then `Sign-up webhook`, `Screen sign-up (gpt-4o-mini)`, `Needs follow-up?`, one branch node, and `Reply to form`. Branches that did not run have no span. Three traces (Rosa, Owen and Sam) go through `Offer a shift`. Priya's trace goes through `Queue for coordinator call`, because she asked to drive but gave neither her age nor a licence. That routing decision is the first thing you can audit without opening n8n.

Click `Screen sign-up (gpt-4o-mini)`. Its input panel holds the node's attributes: the system prompt (`n8n.node.parameters.messages.values.0.content`), the resolved user message built from the form fields, the request payload (`n8n.node.input`), and the model's JSON verdict (`n8n.node.output`). For Rosa that verdict is `{"role": "delivery", "needs_followup": false, ...}`.

The run also shows two judgement calls worth questioning, which is what the trace is for:

- **Owen (16, warehouse):** the verdict's reason says he "can lift 20 kg". His sign-up only says he is "fine with lifting boxes". The model filled in a requirement it was told never to assume.
- **Sam (front desk):** his availability ends "at the end of the month", which the prompt lists as a follow-up case, but he was offered a shift with `needs_followup: false`.

What you will *not* find here is token usage, cost, or a trace-level output. Those are covered under Gotchas below.

## Run it yourself

You need Docker, `curl`, `python3`, an OpenAI key, and an Opik instance. By default the container sends spans to a local Opik at `http://localhost:5173` through `host.docker.internal`.

1. Put `OPENAI_API_KEY` in the repo-root `.env` (see `.env.example`), or export it in your shell.
2. `./setup.sh` builds the image and starts n8n on `localhost:5678`. It then creates the owner account, mints an API key, creates the OpenAI credential from your environment, and imports and activates the workflow. No browser is involved.
3. `./demo.sh` posts four sign-ups and prints each reply.
4. Open the `n8n-foodbank-volunteer-screening` project in Opik.

To use Opik Cloud instead, set `OPIK_OTLP_ENDPOINT=https://www.comet.com/opik/api/v1/private/otel`, `OPIK_API_KEY` and `OPIK_WORKSPACE` before `./setup.sh`. To tear everything down, run `docker compose down -v`.

## Poke around

- **Fix Owen's assumption.** In the n8n editor (`localhost:5678`, `coordinator@example.com` / `Pantry-demo-42`), tighten the system prompt so lifting capacity must be stated. Re-send his sign-up and compare the two `n8n.node.output` values in Opik.
- **Send an edge case.** `curl -X POST localhost:5678/webhook/volunteer-signup -H 'Content-Type: application/json' -d '{"name":"Lee","age":20,"availability":"Sundays","about":"I have my licence and want to drive"}'`. A 20-year-old with a licence is one year short for deliveries; see which branch the trace takes.
- **Break the IF node.** Change its condition to compare against the string `"true"`. Every trace will then take the same branch, and the `Needs follow-up?` span's output shows why.
- **Diff two prompt versions.** The prompt is captured on every execution, so editing it on the canvas leaves a before-and-after record in Opik without any versioning setup.

## Gotchas

- **Token usage and cost columns are empty.** The OpenAI node's span carries no `gen_ai.*` usage attributes: the hooks record each node's parameters, input and output, but not the token counts, so Opik has nothing to price. Cause: in this run the OpenAI node span had no `gen_ai.*` attributes at all. Fix: none in this setup; read the model's verdict from the span's `n8n.node.output`, and measure usage on the OpenAI side if you need it.
- **The trace-level output column is empty.** Cause: the root execution span carries only workflow ids, and the answer sits on the `Reply to form` span's `n8n.node.output`. Fix: open the trace and read that span instead.
- **No traces arrive from the container, or the exporter cannot connect.** Cause: inside the container, `localhost` is the container itself, not the host running Opik. Fix: the compose file adds `extra_hosts: ["host.docker.internal:host-gateway"]` and defaults `OTEL_EXPORTER_OTLP_ENDPOINT` to `http://host.docker.internal:5173/api/v1/private/otel`; keep that host name for a local Opik, or set `OPIK_OTLP_ENDPOINT` for Opik Cloud.

## How it's put together

- `Dockerfile`: the official `n8nio/n8n` image plus `n8n-observability`, with `EXTERNAL_HOOK_FILES` pointing at its hooks.
- `docker-compose.yml`: runs the image on `127.0.0.1:5678` and sets the OTLP endpoint, the `Comet-Workspace` and `projectName` headers, and an optional auth header.
- `workflow/volunteer-screening.json`: the six-node workflow. The credential id is a placeholder that `setup.sh` fills in at import time.
- `setup.sh`: headless bootstrap (compose up, owner account, API key, credential from the environment, import, activate).
- `demo.sh`: four sample sign-ups sent to the live webhook.
- `.env.example`: the variables `setup.sh` reads.

---

<sub>built with [Opik](https://github.com/comet-ml/opik) · inspired by Opik's examples and [documentation](https://www.comet.com/docs/opik/)</sub>
