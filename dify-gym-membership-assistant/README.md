<div align="center">

# 🏋️ dify-gym-membership-assistant

*A gym front-desk chatbot built in Dify, traced in Opik by a single platform setting.*

[![Dify](https://img.shields.io/badge/Dify-1.17.1-1C64F2?style=flat)](https://github.com/langgenius/dify)
[![model](https://img.shields.io/badge/model-gpt--4o--mini-10a37f?style=flat)](https://platform.openai.com/docs/models/gpt-4o-mini)
[![runs in](https://img.shields.io/badge/runs%20in-Docker-2496ED?style=flat)](https://docs.docker.com/compose/)

</div>

Small gyms answer the same five questions all day: which plan fits my schedule, can I take that class, can my kid come, what does it cost? A front-desk chatbot built in a low-code tool like Dify handles those in an afternoon, with no codebase, which also means no obvious place to hook in observability. But a chatbot quoting prices is exactly the kind of app where you need to see what it was told and what it said. This example builds that bot for the fictional **Ironleaf Fitness** and turns on Opik tracing through Dify's own tracing setting, with no instrumentation code anywhere.

## What you'll build

A self-hosted Dify stack, pinned to release 1.17.1 and vendored in `dify-docker/`, running a chat app imported from a committed DSL file (`app/ironleaf-gym-front-desk.yml`). The app's system prompt carries the club's memberships, opening hours, weekly class timetable and house rules. gpt-4o-mini answers from that and sends anything else, such as injuries or billing disputes, to the front desk.

`setup.sh` does through Dify's console API everything you would otherwise click through:

- creates the admin account
- installs the OpenAI provider plugin and stores your key
- imports the app
- writes the Opik tracing config (provider `opik`, project `dify-gym-membership-assistant`, the URL of your Opik) and switches tracing on

`demo.sh` then holds one four-turn conversation through Dify's service API, the way a website chat widget would.

```
member question ─► Dify service API ─► gpt-4o-mini ─► answer
                         │
                         └─► Opik: trace per message, LLM span, token counts, thread
```

## See it in Opik

Open the **`dify-gym-membership-assistant`** project. After one `./demo.sh` it holds **5 traces**:

- four named `message`, one per member question
- one named `generate_conversation_name`, a call Dify makes on its own to title the chat. You never asked for it, but platform-level tracing catches it anyway.

**Threads.** All five traces share one thread id, Dify's conversation id. The Threads tab therefore shows the exchange as a single transcript.

**Message traces.** Open any `message` trace. The trace output is the bot's reply. Inside is one `llm` span holding the full prompt Dify assembled (club information, chat history and question) and the completion. The token counts grow turn by turn as Dify re-sends the history: **661, 736, 794 and 869 prompt tokens** against 31–51 completion tokens. That cost driver is invisible in the Dify UI and obvious here.

**Two answers to inspect:**

- **Turn 2 is wrong in a way only the trace explains.** The member picked Off-Peak ($29, weekday access 09:00–16:00) and asked about Thursday's 19:00 Boxing Fit. The bot said classes aren't included and offered an $8 drop-in. The span shows the rule it missed: Off-Peak members can't be in the building at 19:00 on a weekday at all. Fix the prompt, not the model.
- **Turn 4 behaves well.** Asked about a knee injury, the bot declined and pointed to the desk, as the instructions require.

Two things behave differently from what you might expect; both are covered under Gotchas below.

## Run it yourself

You need Docker (about 4 GB free for the Dify stack), `python3`, an OpenAI key, and an Opik instance. By default Dify's containers reach a local Opik on the host at `http://host.docker.internal:5173/api/`, with no API key.

1. Put `OPENAI_API_KEY` in the repo-root `.env` (see `.env.example`), or export it.
2. `./setup.sh` starts Dify on `http://localhost:8090` and configures it end to end. The first run pulls about 10 images.
3. `./demo.sh` runs the four-question conversation.
4. Open the `dify-gym-membership-assistant` project in Opik and switch to the Threads tab.

To use Opik Cloud, set `DIFY_OPIK_URL=https://www.comet.com/opik/api/`, `OPIK_API_KEY` and `OPIK_WORKSPACE` before `./setup.sh`.

The Dify login is `frontdesk@ironleaf.example` / `IronleafGym2026`; override it in `.env` on a shared machine. To stop everything, run `docker compose -f dify-docker/docker-compose.yaml --project-directory dify-docker down`, adding `-v` to drop the databases.

## Poke around

- **Fix turn 2.** In the Dify studio, add one line to the instructions ("Off-Peak members cannot attend classes outside Off-Peak hours, even as drop-ins"). Re-run `./demo.sh` and put the two `message` traces for that question side by side.
- **Ask something off-script** in the studio's preview pane, for example "do you have a sauna?". Check in the trace that the bot says it doesn't know instead of inventing one.
- **Watch the history tax.** Add three more questions to `demo.sh` and follow the prompt-token column climb in the thread.
- **Turn tracing off** under Monitoring in the Dify app, send a message, and confirm nothing new lands in Opik. The whole integration is that one switch.

## Gotchas

- **The `llm` spans show tokens but no cost.** Cause: Dify sends the model name only as metadata (`ls_model_name: gpt-4o-mini`, `ls_provider: langgenius/openai/openai`), not as the span's own model and provider fields, so Opik has nothing to price. Fix: none on the Dify side; compare turns by token counts, or price them yourself from the metadata.
- **An extra trace you never asked for.** Cause: Dify makes its own `generate_conversation_name` call to title each conversation, and platform-level tracing records it. Fix: expect one such trace per conversation, and filter on the name `message` when you only want member questions.
- **Dify cannot reach Opik, or no traces arrive.** Cause: the Opik URL is called from inside Dify's API container, where `localhost` is the container itself. Fix: use `http://host.docker.internal:5173/api/` for an Opik on your host (the default in `configure_dify.py`), or set `DIFY_OPIK_URL` (for example `https://www.comet.com/opik/api/`) plus `OPIK_API_KEY` and `OPIK_WORKSPACE`. A local Opik takes an empty API key.

## How it's put together

- `app/ironleaf-gym-front-desk.yml`: the Dify app as a DSL export, including the system prompt with the club information.
- `setup.sh`: creates `dify-docker/.env` on first run, starts the stack, then runs `configure_dify.py`.
- `configure_dify.py`: standard-library script that drives Dify's console API (admin account, plugin, credential, import, Opik trace config, service key). It writes `.dify-state.json`, which is git-ignored.
- `demo.sh`: the four-turn conversation over the service API.
- `dify-docker/`: Dify 1.17.1's upstream compose file and config, vendored unchanged.
- `.env.example`: the variables the scripts read.

---

<sub>built with [Opik](https://github.com/comet-ml/opik) · inspired by Opik's examples and [documentation](https://www.comet.com/docs/opik/)</sub>
