# quarkus-langchain4j-pharmacy-faq

*A Quarkus + LangChain4j pharmacy FAQ bot whose every LLM call shows up in Opik, prompt text, token counts and cost included, over plain OpenTelemetry.*

![Java](https://img.shields.io/badge/java-17-ED8B00?style=flat&logo=openjdk&logoColor=white)
![Quarkus](https://img.shields.io/badge/quarkus-3.33-4695EB?style=flat&logo=quarkus&logoColor=white)
![Quarkus LangChain4j](https://img.shields.io/badge/quarkus--langchain4j-1.14-4695EB?style=flat)
[![Opik](https://img.shields.io/badge/Opik-OTLP-2f54eb?style=flat)](https://github.com/comet-ml/opik)

## The problem

Opik has no Java SDK, and on the JVM you rarely want one: Quarkus already emits OpenTelemetry spans, and Opik accepts OTLP. The catch is what lands on those spans. By default Quarkus LangChain4j records *that* a model call happened, but not what was said. You get timing and an operation name, and when the bot gives a bad answer you cannot see the prompt that caused it.

This example is a small FAQ bot for a made-up shop, Larkspur Community Pharmacy. It answers from four short leaflets (storage, missed doses, opening hours, refills) and is told to hand anything clinical to the pharmacist. It exists to show the two config flags that put the content on the spans, and what Opik does with the `gen_ai.*` attributes once they arrive.

## What you'll build

- `GET /ask?q=...` on `127.0.0.1:5304`, a Quarkus REST endpoint.
- A keyword retriever (`LeafletStore`) that picks the 2 best-matching leaflets from `docs/` and records itself as a `retrieve_leaflets` span.
- A LangChain4j `@RegisterAiService` (`PharmacyBot`) on `gpt-4o-mini`. The system prompt restricts it to the leaflets and tells it to defer to the pharmacist for dosing or treatment questions.
- OTLP export to Opik, configured entirely in `application.properties`, with no Opik code or dependency in the `pom.xml`.
- `run.sh`: builds in JVM mode, starts the app, asks four scripted questions with curl, then sends SIGTERM so the batch span processor flushes.

## See it in Opik

Open the project **quarkus-langchain4j-pharmacy-faq** and the Traces tab. A clean run gives **4 traces**, one per question, each named `GET /ask` and each with **5 spans** (20 in total):

1. `GET /ask` (root, type general). The trace Output column holds the bot's answer. The Input column holds the HTTP request attributes, with the question sitting inside as `input` and also in `url.query`. Quarkus owns this span, so Opik shows its attributes.
2. `retrieve_leaflets`, input `{question, top_k: 2}`, output the chosen files, for example `hours-and-services.md` and `missed-doses.md` for the Sunday question.
3. `langchain4j.aiservices.PharmacyBot.answer`, the AI-service method span. It carries no content of its own.
4. `completion gpt-4o-mini`, the one that matters. Its type is **llm**, provider `openai`, model `gpt-4o-mini-2024-07-18`. The input holds the full system prompt with the leaflet text and the user question (`gen_ai.prompt`), and the output is the completion (`gen_ai.completion`). Usage is filled in, and so is **estimated cost**, for example 624 prompt + 36 completion = 660 tokens, about $0.000115.
5. `POST /chat/completions`, the outgoing HTTP client span to OpenAI, nested under the LLM span. It is noise, but Quarkus gives no way to drop it without also dropping the server span.

Across the four questions the run used 2,602 tokens and an estimated $0.00047 in total. Cost does land here: Opik recognizes `gen_ai.system`/model from the span and prices it, so no workaround was needed.

The fourth question ("Can I raise my Tormisal dose since my cough is getting worse?") is the safety check. Open its `completion gpt-4o-mini` span and you can read the refusal next to the prompt that asked for it.

## Run it yourself

Needs Java 17+ (Maven is bundled through `./mvnw`), an OpenAI key, and Opik running locally at `http://localhost:5173`.

1. Put `OPENAI_API_KEY=...` in a `.env` (this folder, or one level up; `run.sh` reads `../.env` first, then `./.env`). `.env.example` lists the optional Opik settings, including how to point at Opik Cloud.
2. Run `./run.sh`. The first run downloads dependencies, so expect a minute. After that the whole thing takes about 11 seconds.
3. Open `http://localhost:5173`, pick the project `quarkus-langchain4j-pharmacy-faq`, and open any trace.

Dev Services are switched off (`quarkus.devservices.enabled=false`), so nothing starts a container.

## Poke around

- **Hide the content.** Run `INCLUDE_CONTENT=false ./run.sh`. The LLM span keeps its model, usage and cost, but the input prompt and the output are gone. That is the default behavior of the extension, and the reason this example exists.
- **Break the retriever.** Change `top_k` in `AskResource` from 2 to 1, ask the "Sunday and private question" again, and compare the `retrieve_leaflets` output with the answer. A missing leaflet shows up as "the leaflets do not cover this".
- **Try to jailbreak the guardrail.** Add a question to `run.sh` that begs for a dose recommendation, then read the system prompt and the completion side by side.
- **Change the model.** Set `quarkus.langchain4j.openai.chat-model.model-name` to `gpt-4.1-mini` and watch the cost column change.

## Gotchas we hit

**Nothing arrives in Opik and no project appears.** The app runs fine and the log shows nothing but a FINE-level `Exporter failed` line. The cause is an endpoint that already ends in `/v1/traces`: Quarkus appends that suffix itself, so the request goes to `.../otel/v1/traces/v1/traces`, which Opik does not serve. Use the bare base URL, `quarkus.otel.exporter.otlp.traces.endpoint=http://localhost:5173/api/v1/private/otel` (a local sink on this build received `POST /api/v1/private/otel/v1/traces`).

**The `completion gpt-4o-mini` span has model, usage and cost, but empty input and output.** Quarkus LangChain4j leaves prompt and completion text off the spans by default. Set `quarkus.langchain4j.tracing.include-prompt=true` and `quarkus.langchain4j.tracing.include-completion=true`.

**A stray extra trace appears for every startup check.** Any HTTP request to the app, even to a path that does not exist, is exported as its own `GET ...` trace. Do not poll the app with curl while waiting for it to start; `run.sh` uses a bash `/dev/tcp` connection check, which opens a socket but sends no HTTP request.

## How it's put together

- `pom.xml`: Quarkus 3.33 and Quarkus LangChain4j 1.14 BOMs; `quarkus-rest-jackson`, `quarkus-opentelemetry`, `quarkus-langchain4j-openai`.
- `src/main/resources/application.properties`: model, port, Dev Services off, the OTLP endpoint and Opik headers, and the two tracing flags.
- `src/main/java/dev/opikexamples/pharmacy/AskResource.java`: the endpoint; puts question and answer on the server span.
- `.../LeafletStore.java`: loads `docs/*.md`, keyword-scores them, emits the `retrieve_leaflets` span.
- `.../PharmacyBot.java`: the AI service interface and its prompt.
- `docs/`: four fictional leaflets (invented drugs: Veldrine, Mirrowan, Quillavet, Tormisal).
- `run.sh`: build, start (waiting with a `/dev/tcp` check so no probe trace appears), ask four questions, stop gracefully.
- No test files: this example is Java and has none; `./mvnw -q -DskipTests package` is the build check.
- `mvnw`, `.mvn/`: Maven wrapper.

### The Opik-specific settings

```properties
quarkus.otel.exporter.otlp.protocol=http/protobuf
quarkus.otel.exporter.otlp.traces.endpoint=http://localhost:5173/api/v1/private/otel
quarkus.otel.exporter.otlp.traces.headers=Comet-Workspace=default,projectName=quarkus-langchain4j-pharmacy-faq
quarkus.langchain4j.tracing.include-prompt=true
quarkus.langchain4j.tracing.include-completion=true
```

Two things worth knowing. Quarkus appends `/v1/traces` to the endpoint itself; if you add it, spans silently vanish (the export fails with nothing but a FINE-level "Exporter failed" line). And there is no Authorization header on a local Opik; for Opik Cloud add `Authorization=<key>` to the same headers line.

*built with Opik · inspired by Opik's examples and documentation*
