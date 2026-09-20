# AWS open-source stack: feedback log (kept as we build; feeds the submission form)

## Frictions (specific)
- **Cedar**: the `cedar-policy` package on PyPI is an empty 0.0.1 placeholder, so Python has no real binding. We shell out to the Rust CLI (`cedar authorize`), which works but pays a process spawn per decision and needs a per-architecture binary (a second arm64-linux build for the SAM container).
- **LocalStack** (named in the Build It table under Serverless) now requires an account and token, which contradicts "no account, no card". We used SAM Local instead.
- **SAM Local**: `/var/task` is read-only, only `/tmp` is writable; conversation state only survives between calls with `--warm-containers LAZY`; the Lambda container reaches the host's Ollama only via `host.docker.internal`. None of this is discoverable until a request fails.
- **OpenSearch**: changing an analyzer means a new index (we moved `aftercare-sections` to `-v2` for the English analyzer). Silent fallback risk: if the client can't connect, an app that swallows the error looks fine but isn't using OpenSearch, so we report the engine on every response.
- **Strands**: (to fill in during the agent phase: structured output and tool-calling with a 7B local model.)

## What worked well
- **OpenSearch aggregations** replaced hand-written counting code: "why customers escalate" and "which manual sections send people to a person" are two `terms` aggregations. The `english` analyzer gave stemming ("bangs"/"banging") with no code.
- **OpenSearch `range` on `now-90d`** made the recurrence window a one-line filter.
- **Cedar** policies read like the requirement ("principal.brand == resource.brand"); fail-closed on any error was easy to build around.
- **SAM**: one `template.yaml` describes the API and functions, and the same handlers run under Flask and `sam local`.
- **Strands**: (to fill in.)

## Added while building the serverless phase
- **SAM Local + OpenSearch (a bug only Lambda revealed):** documents were indexed with the *absolute file path* as the filter key. Inside the Lambda container the path is `/var/task/...`, so every search matched nothing and silently fell back to keyword search. Nothing failed; the engine label on each response is the only reason we noticed. Key by file name.
- **SAM Local**: `sam build` with `CodeUri: .` copies the whole repo (docs, archive, 129 MB) into every function package and there is no ignore file. `Globals` accepts `Api.Cors` but not everything you'd expect for functions.
- **DynamoDB Local** is not in the Build It table but is AWS's own downloadable emulator, and it made the single-table design testable with real `Query`, GSI and atomic `ADD` semantics. Worth naming in the table.
- **Lambda Powertools idempotency**: `event_key_jmespath` alone silently returns the cached result even when the request body differs; you must add `payload_validation_jmespath` to get a validation error. Also warns unless `register_lambda_context` is called.
- **Powertools Metrics/EMF** were a pleasure: one `single_metric` call prints a CloudWatch-EMF JSON line; no client, no API call, works identically under `sam local`.

## Strands, as actually used
- **A shared `Agent` remembers everything.** We kept one Agent for all requests; inspecting `agent.messages` showed 4 messages after 2 calls, i.e. customer B's prompt was answered with customer A's complaint in context, and the context grew forever. Nothing in the docs' quick-start warns that an Agent is a *conversation*, not a function. Fixed with a fresh Agent per self-contained prompt.
- **Structured output needs a model that can call tools.** The current `structured_output_model=` path is implemented as a forced tool call. With `qwen2.5-coder:7b` on Ollama it fails ("model failed to invoke the structured output tool", plus a "ToolChoice not supported" warning). The deprecated `Agent.structured_output()` returned "resolved" for every reply, including "Still blowing warm air", so it is worse than failing. We kept plain text classification with a strict parser that defaults to "still broken", and put every decision that matters (safety, recurrence, attempt cap, warranty, authorization) in code.
- **Hooks were the good part.** `BeforeModelCallEvent` / `AfterModelCallEvent` give exact model latency with ~15 lines and no change to call sites; we surface it in the demo's trace.
- **Design decision, not a gap:** we deliberately do not give the model tools. A tool-calling agent on a 7B local model chooses badly; deterministic gates before the model are more reliable and testable.

## Going all-Lambda (removing Flask and every fallback)
- **`sam local start-api --static-dir`** must be an *absolute* path (a relative one 404s silently: SAM builds its Flask app relative to the SAM package, not your cwd), it mounts at `/` with no URL-prefix option, and its catch-all static route **shadows a `/{proxy+}` API route**. We had to declare every route explicitly in `template.yaml` so exact routes outrank the static handler. None of this is documented in `--help`.
- **`sam build` copies `CodeUri` wholesale**, including `.venv` (it died on a venv symlink). No ignore file exists, so we stage a clean `lambda_pkg/` first (`scripts/stage_lambda.sh`). A custom Makefile build did not avoid the copy.
- **Environment variables leak from your shell into the Lambda.** `sam local` lets a host `DYNAMODB_ENDPOINT=http://localhost:8000` override the template's `host.docker.internal:8000`; inside the container `localhost` is the container. The failure looked like "DynamoDB unreachable".
- **Lambda Powertools' API Gateway resolver** was the good part: one function with real route decorators, exception handlers (a `DependencyUnavailable` becomes a 503 naming the service), and the same `inject_lambda_context` logging.
- **Amazon Corretto image** (`amazoncorretto:21`) has no `gzip` or `which`; DynamoDB Local's download is gzip although served as `application/x-tar`. Once running, DynamoDB Local on Corretto behaved identically to the stock image.
- **LocalStack** (Serverless row of the Build It table) still refuses to start without an auth token (`License activation failed`, exit code 55): usable only with a free LocalStack account, so we did not build on it.
- **Removing fallbacks paid off immediately:** with the Flask server and keyword fallback gone, a stopped OpenSearch or DynamoDB now returns `503 {"error": "OpenSearch is unavailable: ...", "service": "OpenSearch"}` instead of a plausible answer from something else. The earlier "silent fallback" bug (absolute-path filter) could not have hidden in this design.
