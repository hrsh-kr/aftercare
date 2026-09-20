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
