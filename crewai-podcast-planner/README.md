# crewai-podcast-planner

![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat&logo=python&logoColor=white)
![CrewAI](https://img.shields.io/badge/crewai-1.15%2B-FF5A50?style=flat)
![Opik](https://img.shields.io/badge/opik-2.2.99-2f54eb?style=flat)

**Three CrewAI agents plan a podcast episode. Opik gives you one trace for the whole planning session, with tokens and dollars per agent.**

A crew hands you a finished artifact and hides the story: which agent did the work, what each one was told, and who ate the token budget. Here a fictional show, *The Lighthouse Hour*, gets an episode planned by a topic researcher, an outline writer and a show-notes editor. A single `track_crewai(...)` call makes each `kickoff` appear in Opik as one trace you can read like a receipt.

## What you'll build

A small Python package, `podcast_planner`, with a CLI. You pass an episode brief (or use the built-in default). The researcher reads `data/episode_notes.md` (an offline, invented notes file, so no web search and only an OpenAI key are needed). The outline writer turns that into a timed outline, and the editor writes a title, description, guest list and highlights. All agents use `gpt-4o-mini`.

## See it in Opik

Open the `crewai-podcast-planner` project, Traces tab. After one run there is exactly **one** trace, named `kickoff`, with 49 spans. Its totals show 2,622 tokens (1,753 prompt, 869 completion) and an estimated cost of about $0.00078.

Expand it. Under the root are three `Task: ...` spans (`Task: Research the topic`, `Task: Draft the outline`, `Task: Write the show notes`), each holding its agent's work and ending in a `chat_completion_create` span of type `llm` on `gpt-4o-mini-2024-07-18`. Click each one for its own tokens and cost:

| Agent / task | Total tokens | Estimated cost |
|---|---|---|
| Researcher | 1,034 | $0.000246 |
| Outline writer | 835 | $0.000319 |
| Show-notes editor | 753 | $0.000220 |

The researcher reads the whole notes file, so it has the largest prompt; the outliner writes the most output and so costs the most. Exact numbers vary slightly between runs.

## Run it yourself

1. `uv sync`
2. Put `OPENAI_API_KEY` in a `.env` (copy `.env.example`; the CLI also finds a `.env` in any parent folder). Point Opik at your instance, e.g. `export OPIK_URL_OVERRIDE=http://localhost:5173/api/ OPIK_WORKSPACE=default`, or run `opik configure`.
3. `uv run podcast-planner` (takes about 30 seconds), or give your own brief: `uv run podcast-planner "A short episode on how fishing crews used horn pitch to navigate"`
4. Optional: `uv run python verify.py` prints the trace, span counts, tokens and cost straight from the Opik SDK.
5. Offline tests (no keys, no Opik, a few seconds): `env -u OPENAI_API_KEY -u ANTHROPIC_API_KEY OPIK_TRACK_DISABLE=true uv run pytest`. `OPIK_TRACK_DISABLE=true` is the SDK switch that turns tracking off.

The run documented above used `uv run podcast-planner` with the default brief.

## Poke around

- Pass a different brief and compare the three LLM spans' costs; which agent grows?
- Edit `data/episode_notes.md` (or pass `--notes other.md`) and watch the researcher's span input change.
- Set `MODEL` in `podcast_planner/agents.py` to a bigger model for only the editor and compare per-span cost.
- Add a fourth agent (a fact-checker) in `agents.py` and `tasks.py`; the trace gains a branch with no Opik changes.

## Gotchas we hit

- **The llm span's usage has extra `original_usage.*` keys next to `prompt_tokens`, `completion_tokens` and `total_tokens`.** `track_crewai` stores the provider's raw usage payload alongside the standard fields. This is harmless: cost is computed from the standard keys and stays correct, so there is nothing to fix. Read `prompt_tokens` / `completion_tokens` / `total_tokens` and ignore the rest.
- **Cost looks missing when you read `usage`.** The dollar figure is not inside `usage`; it is the top-level span field `total_estimated_cost`. `verify.py` prints it for every llm span (`s.total_estimated_cost`), and each one should be non-null. If one is null, check the span's `model` name is one Opik can price.
- **Two systems report on the same run.** CrewAI sends its own anonymous telemetry unless you disable it. The CLI sets `os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")` before the crew is built, so only Opik receives trace data; export the variable yourself if you call `plan_episode` from your own script.

## How it's put together

- `podcast_planner/agents.py` - the three agents.
- `podcast_planner/tasks.py` - the three sequential tasks and their context wiring.
- `podcast_planner/crew.py` - builds the crew, calls `track_crewai`, runs `kickoff`.
- `podcast_planner/cli.py` - argument parsing, `.env` loading, final flush.
- `data/episode_notes.md` - the fictional research notes.
- `verify.py` - reads the project back from Opik and prints tokens and cost per llm span.
- `tests/test_planner.py` - offline tests for CLI parsing, agent and task wiring, notes loading and the tracked crew; no model calls.

*built with Opik · inspired by Opik's examples and documentation*
