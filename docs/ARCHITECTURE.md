# Architecture

The single, current description of how Aftercare works. (`BUILD_LOG.md` is the historical record; where they differ, this file wins.)

## 1. The one idea

**Deterministic before model.** A small local model (gemma2:9b) is good at wording one manual step and bad at judging
safety, counting attempts, or deciding whether a problem is "the same as last time". So the model does exactly two jobs:
*phrase one numbered step from the manual* and *read an ambiguous customer reply*. Everything else is a rule, a query or
a policy, which makes it testable without the model and honest about what it can't do.

| Decision | Made by | Where |
|---|---|---|
| Is this a safety issue? | keyword rule (with negation) **or** retrieval landing on the manual's own safety section | `agent/agent.py` `_check_safety`, `start()` |
| Did the customer ask for a person? | regex | `agent/agent.py` `_HUMAN` |
| Is this a warranty question? What is the status? | keyword + **date arithmetic**; coverage wording quoted from the Terms | `agent/agent.py` `_warranty_answer`, `domain/registration.py` |
| Which manual section, which step is next? | OpenSearch BM25 (custom analyzer) + a regex over the section's numbered list | `domain/opensearch_retrieval.py`, `agent/agent.py` |
| Is it in the manual at all? | word-overlap gate sharing one synonym list with the OpenSearch analyzer | `domain/retrieval.py` |
| Has this product had this problem before? | OpenSearch filter: serial + source + `range now-90d` | `records/case_index.py` |
| Fixed, or still broken? | **rules first** (clear negatives win, clear positives resolve); the model only sees the ambiguous middle; anything but a clear yes is "still broken" | `agent/agent.py` `classify_reply` |
| Two tries then a person | counter (`MAX_ATTEMPTS = 2`) | `agent/agent.py` |
| Who may see / reply / resolve? | Cedar policy, decision names the policy | `policies/`, `authz/cedar_authz.py` |
| Phrase the step, read an ambiguous reply | **the model** | `agent/agent.py` (Strands `Agent`, Ollama) |

## 2. Runtime

```
Browser ─▶ API Gateway (SAM Local) ─▶ ONE Lambda  (src/lambda_app.py: pages + 28 routes, Powertools resolver)
                                          │  api_core.py (logic) · pages.py (Jinja) · channel/bot.py (WhatsApp)
        ┌──────────────┬──────────────────┼───────────────────┬────────────────────┐
   Strands Agent    OpenSearch          Cedar CLI          DynamoDB Local       Powertools
   Ollama gemma2    manual sections,    schema + 6         (Corretto image)     logs, EMF metrics,
   hook: latency    cases, tickets,     policies           one table            idempotency
                    aggregations
```

- **One Lambda serves everything** (`template.yaml`: 28 explicit API Gateway events, two DynamoDB tables). There is no other web server and no fallback: if OpenSearch, DynamoDB or Ollama is unreachable the API answers `503 {"error", "service"}` naming it (`errors.py`, an exception handler in `lambda_app.py`). Explicit routes rather than a catch-all because `sam local`'s static-file route would shadow a `/{proxy+}`.
- `scripts/dev.sh` is the only entry point: checks prerequisites → OpenSearch + DynamoDB Local containers → `scripts/bootstrap_local.py` (tables *read from* `template.yaml`, indices, seed history, baseline registry) → `scripts/stage_lambda.sh` (a clean `lambda_pkg/` as `CodeUri`) → `sam build --use-container` → `sam local start-api --warm-containers EAGER`.
- Static files in `public/` are served by `sam local --static-dir` (in an account: S3 + CloudFront). Pages are rendered inside the Lambda.

## 3. One customer message, end to end (`channel/bot.py`)

A message enters the way Meta's WhatsApp Cloud API delivers one: `POST /api/wa/webhook` with a Meta-shaped payload.

1. `parse_webhook` maps the business number to a brand and the sender to a phone; `handle_inbound` records the customer's message in the chat log.
2. **State per chat** (one DynamoDB item): `idle` / `awaiting_product` / `bot` (a step is out) / `human` (handed over; the bot stays quiet until the ticket is resolved).
3. New message: greeting? → product (only one owned, or the model/serial named, else buttons "which product?") → `agent.start()`:
   safety → asked for a person → warranty question (answered, no model) → retrieve manual section (OpenSearch) → safety section? → not in the manual? → seen before (OpenSearch)? → phrase step 1 (model).
4. Reply to a step: `classify_reply` (rules, then model if ambiguous) → resolved, or step 2, or a hand-over (`attempts_exhausted`).
5. Every outcome is turned into WhatsApp messages by `_deliver` and appended to the log with the trace (`meta`: section, retrieval method, attempt, escalation reason, model ms) that the UI shows.
6. **Hand-over** creates a ticket with a reason code: `safety`, `attempts_exhausted`, `no_more_steps`, `no_steps`, `unmatched`, `recurring`, `human_requested`.
7. **A person replies** from the brand's inbox (`POST /api/tickets/<id>/reply`, Cedar action `replyToCustomer`); it is one more message in the same log, so it appears on the customer's phone. Resolving the ticket (`updateTicketStatus`, managers only) messages the customer and returns the chat to `idle`.

Only Meta's network is simulated. The customer's phone UI polls `GET /api/wa/messages` (it has no login, standing in for the customer's device); staff endpoints are all session + Cedar.

## 4. Data

**DynamoDB** (single table, GSI1 overloaded three ways): registry (`BRAND#b / REG#serial`, phone GSI), conversations, tickets, cases, chat message log (`CHAT#brand#phone / MSG#iso#id`), chat state, inbox index, atomic ticket counter, TTLs. Twelve access patterns are listed with their keys in [`DYNAMODB_DESIGN.md`](DYNAMODB_DESIGN.md). Warranty status is never stored; it is computed on read from the purchase date. `src/storage/` hides it behind one interface; the file implementation exists only as a unit-test double.

**OpenSearch** (`aftercare-sections-v4`, `aftercare-cases-v1`, `aftercare-tickets-v1`): manual/terms sections with the `aftercare_english` analyzer (standard tokenizer, synonym filter, stop words, stemmer); cases for recurrence (range query) and the dashboard's `terms` aggregations; ticket text search.

**Fabricated inputs** (the only non-real part of the data): two manuals and two Terms documents (`fixtures/`), two order files and eight personas (`fixtures/sandbox/`), a seeded history so "it's back" is demonstrable (`fixtures/history_seed.json`), three staff accounts (`fixtures/staff.json`).

## 5. Authorization (Cedar)

`policies/aftercare.cedar` (6 policies, each with an `@id`) is validated against `aftercare.cedarschema` (`cedar validate` runs in tests and in `/api/health`). Actions: `viewDashboard`, `viewTicket`, `updateTicketStatus` (managers), `viewPhoneUnmasked` (safety tickets only), `replyToCustomer` (same brand), plus a `forbid` across brands. The principal is built from a **signed, expiring, HttpOnly session cookie** (`authz/session.py`, PBKDF2-hashed passcodes), never from anything the browser asserts. Every decision returns the policy ids that made it and the UI shows them. The Cedar CLI is a subprocess (the PyPI `cedar-policy` package is an empty placeholder); in production the same policies and schema load into Amazon Verified Permissions.

## 6. The model, and how we chose and checked it

- `scripts/eval_model.py` compares local models on the two jobs the model has (phrasing one step, reading a reply). gemma2:9b phrased best of five; results and the reasons others failed are in `BUILD_LOG.md` (Phase 7.18).
- `scripts/eval_routing.py`: 41 customer phrasings across both products must route to the right section / safety / not-in-manual / warranty / person, with a stub model and real OpenSearch.
- A fresh `Agent` per call (`StatelessAgent`): a shared Strands agent replays every earlier prompt as context (a cross-customer leak we found by printing `agent.messages`). A `HookProvider` times each model call for the trace.
- Strands' structured output needs a tool-calling model and fails on a local 9B; we kept plain text with a strict parser and put every decision that matters in code.

## 7. Observability and safety nets

Lambda Powertools: JSON logs that never contain a phone number or complaint text; CloudWatch EMF metrics (`Escalated`, `ResolvedByAgent`, `AgentLatency`, `AuthzDenied`); `Idempotency-Key` on `POST /api/start` (a retry returns the same conversation; a changed body gets `422`). Request bodies that aren't JSON get `400`; an unexpected exception is logged with the request id and returns a generic `500` (no stack trace).

## 8. Verification map

| Claim | Evidence |
|---|---|
| Escalation reasons, warranty answered without the model, negation-aware safety, reply reading | `tests/test_escalation.py` (stubbed model) |
| Cedar matrix, forged header ignored, agents can't resolve, sessions can't be forged | `tests/test_cedar.py` (real Cedar CLI) |
| Channel end to end: orders → registration message → conversations → hand-over → human reply → resolve | `tests/test_channel.py` |
| Same storage behaviour on files and DynamoDB | `tests/test_store_contract.py` |
| Recurrence window, brand scoping, aggregations | `tests/test_case_index.py` (OpenSearch) |
| Order-file validation | `tests/test_ingest.py` |
| Everything through the Lambda with the real model | `scripts/run_sandbox_scenarios.py` (8 personas, 25 checks), `scripts/run_scenarios.py` (the guided demo's 5) |
| Retrieval and intents | `scripts/eval_routing.py` (41) |
| Model choice | `scripts/eval_model.py` |

`tests/run_all.sh` runs the unit/integration set (needs `bash scripts/dev.sh`'s containers up).

## 9. Local vs production

| Here | In an AWS account |
|---|---|
| Ollama (gemma2:9b) | Amazon Bedrock via Strands `BedrockModel` |
| OpenSearch container | Amazon OpenSearch Service / Serverless |
| Cedar CLI | Amazon Verified Permissions (same policies + schema) |
| DynamoDB Local (Corretto) | Amazon DynamoDB (`template.yaml` already declares the tables) |
| SAM Local + `--static-dir` | API Gateway + Lambda (`sam deploy`), S3 + CloudFront |
| Powertools EMF | CloudWatch metrics |
| Meta-shaped webhook | AWS End User Messaging Social / WhatsApp Cloud API |
| Order file check on demand | S3 upload → event → the same `ingest_commit` |

## 10. Limits, stated plainly

Nothing is deployed and no AWS account is used (Build It track). WhatsApp's network is simulated; customers, orders and manuals are fabricated. Chat is polled every 1.1 s (production would push). "Not in the manual" is a word-overlap test; recurrence matches on manual section, not on wording. A code change needs a ~1 minute `sam build`. Multi-language input only works where the rules or model happen to catch it. The model-timing list in `StatelessAgent` is not concurrency-safe.
