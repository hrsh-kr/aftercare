# AGENTS.md: orientation for AI coding agents and reviewers

**What this is:** Aftercare, WhatsApp after-sales support on the open-source AWS stack, run locally (Build It track). Read
`README.md` (front door) then `docs/ARCHITECTURE.md` (the one current design doc). `docs/BUILD_LOG.md` is history only.

## Run and verify
```bash
bash scripts/dev.sh                      # everything: containers, tables, sam build, sam local start-api on :3000
tests/run_all.sh                         # tests (services from dev.sh must be up)
.venv/bin/python scripts/run_sandbox_scenarios.py   # 8 personas through the WhatsApp webhook, real model
```

## Invariants (please don't break these)
1. **Deterministic before model.** The model only phrases one manual step and reads an ambiguous reply (`src/agent/agent.py`). Safety, routing, attempt counting, warranty maths, recurrence and authorization are code, queries and Cedar policy.
2. **No fallbacks.** A missing OpenSearch / DynamoDB / Ollama is `DependencyUnavailable` → `503` naming the service (`src/errors.py`). The file store and `keyword_retrieve` exist only as unit-test doubles (`AFTERCARE_STORE=file`).
3. **One Lambda, explicit routes.** Add a route in `src/lambda_app.py` **and** an event in `template.yaml` (a catch-all is shadowed by sam local's static route).
4. **Identity comes from the signed session cookie**, never a header or body field. Every staff action is `cedar_authz.authorize(...)`; the response names the deciding policy.
5. **No PII in logs** (phones, complaint text). Use `src/webapp/observability.py`.
6. **One synonym list** (`src/domain/retrieval.py: SYNONYM_GROUPS`) feeds both the OpenSearch analyzer and the Python coverage gate; changing it means a new index name in `opensearch_retrieval.py`.
7. `/demo` (`public/static/demo.*`, `templates/demo.html`) is the separate guided page; `/sandbox` is the free-form real demo.

## Where to change what
| To change | Edit |
|---|---|
| What the agent decides / says | `src/agent/agent.py` (then `scripts/eval_routing.py`, `tests/test_escalation.py`) |
| WhatsApp behaviour (greeting, product picker, hand-over, replies) | `src/channel/bot.py` (`tests/test_channel.py`) |
| A route or its logic | `src/lambda_app.py` + `template.yaml` + `src/webapp/api_core.py` |
| Manuals / terms / order files | `fixtures/` (re-run `scripts/bootstrap_local.py` to re-index) |
| Who may do what | `policies/aftercare.cedar` + `.cedarschema` (`tests/test_cedar.py`) |
| A DynamoDB access pattern | `src/storage/dynamodb_store.py` + `docs/DYNAMODB_DESIGN.md` (`tests/test_store_contract.py`) |
| UI | `public/static/*.{css,js}`, `src/webapp/templates/*.html` (static files are live; templates need a rebuild) |

Names: `domain/` (catalog, registration, retrieval), `agent/`, `records/` (tickets, cases), `storage/`, `authz/`, `channel/`. Everything in `fixtures/` is fabricated.
