# Aftercare — How It Actually Works

This is the as-built reference: every request, every file, every real
decision point, matching the code exactly. `DESIGN.md` and `TECHNICAL.md`
are the plan and the pitch context; this is what's actually running.
Written during a full audit pass — see `IMPLEMENTATION.md`'s Phase 7.9
entry for what that audit found and fixed.

---

## 1. The shape of it, in one paragraph

Aftercare is a Flask app (`src/webapp/app.py`) plus a real Strands
agent (`src/layer2/agent.py`) that grounds every suggestion in an
authored product manual retrieved from a local OpenSearch index. Two
brands run side by side — ArcticAir (AC) and AquaSpin (washing
machine) — each with its own manual, its own warranty terms, and its
own dashboard, the dashboard access enforced by a real Cedar policy
evaluation. Escalations become tickets, stored as JSON files. A second
adapter (`src/lambda_handlers.py` + `template.yaml`) exposes the exact
same core logic as real Lambda functions behind API Gateway, runnable
locally with SAM Local — proof the logic is serverless-ready, not a
separate implementation.

Nothing here talks to a real WhatsApp number or a real AWS account.
Everything else — the agent's reasoning, the retrieval, the
authorization, the escalation logic — is real.

---

## 2. Request-by-request walkthrough

### Customer side (`/`, `index.html` + `chat.js`)

1. **Page load →** `chat.js` calls `GET /api/customers`. This is a
   demo-only stand-in: a real WhatsApp integration never needs a
   picker, the incoming message already carries the sender's phone
   number. The picker exists because a browser has no real phone
   attached to it. (`api_core.list_customers()`)
2. **Customer picked →** `POST /api/lookup` with their phone number.
   Returns their name, their brand (`ArcticAir`/`AquaSpin`, derived
   from `product_id`'s prefix — see §4), and every product registered
   to that number. The chat header repaints itself to that brand's
   name and initials right here — there is no static "Aftercare
   Support" header, it's set per customer. (`api_core.lookup()`)
3. **First message →** `POST /api/start` with the phone number and the
   free-typed complaint. This is where the real agent logic starts —
   see §3.
4. **Every message after that →** `POST /api/respond` with the
   `conversation_id` from step 3 and the reply text.

Every response has a `status`: `"waiting"` (agent is expecting a
reply), `"resolved"`, or `"escalated"`. The frontend disables the
composer for the last two.

### Brand staff side (`/dashboard`, `/dashboard/<brand>`)

1. **`/dashboard` →** a brand picker (`dashboard_login.html`). Picking
   a brand writes `sessionStorage.staffBrand` and navigates to
   `/dashboard/<brand>`. Same honesty pattern as the customer picker:
   a real deployment already knows which brand's staff account is
   logged in; this simulates that with a click.
2. **`/dashboard/<brand>` →** renders the shell (`dashboard.html`),
   then `dashboard.js` calls `GET /api/dashboard/<brand>` with an
   `X-Staff-Brand` header set to whatever `sessionStorage` holds.
3. **The backend asks Cedar**, not an `if`: is `Staff::"<staff_brand>"`
   permitted `Action::"viewDashboard"` on `Brand::"<brand>"`? The
   policy (`policies/dashboard.cedar`) is one line: permit when
   `principal.brand == resource.brand`. If `staff_brand` and `brand`
   disagree — e.g. someone edits the URL from `/dashboard/arcticair`
   to `/dashboard/aquaspin` without logging in as AquaSpin — Cedar
   denies it, a real 403, and the page shows an actual "Access denied"
   panel, not a redesigned-away edge case. (`api_core.dashboard_data()`,
   `src/authz/cedar_authz.py`)
4. **On success**, registrations and tickets are filtered to that one
   brand (by `product_id` prefix) and returned: stat counts, the open
   ticket list, and a product-feedback bar chart.

---

## 3. The agent loop, concretely (`src/layer2/agent.py`)

`start(registration, complaint)`:

1. **Safety check first, no model call.** `_check_safety()` scans for
   a fixed keyword list (burning smell, sparking, exposed wire, gas
   smell, ...). If it matches, a ticket is created immediately —
   `available_steps` is never even computed. This check runs before
   anything else in the function, unconditionally.
2. **Coverage or troubleshooting?** A second keyword check
   (`warranty`, `covered`, `claim`, ...) decides whether to retrieve
   from that brand's *terms* file or that product's *manual*
   (`catalog.terms_for()` / `catalog.manual_for()`, keyed by the
   product_id's `WM-`/`AC-` prefix).
3. **Retrieve.** `opensearch_retrieval.retrieve(complaint, doc_path)` —
   real BM25 search against a local OpenSearch index, scoped to that
   one document by an exact-path filter (never cross-brand, never
   cross-manual). Falls back to `retrieval.keyword_retrieve()` (a hand-
   scored word-overlap function, the original Phase 1 implementation)
   if OpenSearch can't be reached. The conversation records which one
   actually answered (`Conversation.retrieval_method`).
4. **Parse the numbered steps.** The manuals write troubleshooting as
   an explicit numbered list (`1. ... 2. ... 3. ...`).
   `_parse_numbered_steps()` regexes that list out directly — the
   model is never asked "does a next step exist," because the document
   already states that as a structural fact. (This was a real bug the
   first time it was built the other way — see IMPLEMENTATION.md
   Phase 3.)
5. **If there's a step, phrase it and stop.** One Strands/Ollama call
   turns the raw manual sentence into a short, friendly message asking
   the customer to try it and report back. The model's only job here
   is phrasing — it never decides *which* step or *whether* one exists.

`respond(conv, customer_reply)`:

1. One model call classifies the reply as `RESOLVED` or `STILL_BROKEN`
   against the step that was just sent.
2. **Resolved** → `conv.resolved = True`, done, no ticket.
3. **Still broken** → if this was attempt 2 already, or there's no
   further parsed step, escalate. Otherwise, phrase and send the next
   parsed step (attempt 2 of the `MAX_ATTEMPTS = 2` cap).

Escalation (`_escalate()`) always creates a `Ticket` with the full
attempt history attached — never a guess dressed up as a third
attempt.

---

## 4. The catalog: one source of truth for brand/product routing

`src/layer1/catalog.py` is the only place `product_id` prefixes
(`WM-`, `AC-`) get mapped to a manual, a terms file, a brand name, or a
warranty component. Everything else imports from here:

| Who imports it | For what |
|---|---|
| `agent.py` | which manual/terms file to retrieve from, the brand name for a lookup response |
| `opensearch_retrieval.py` | the full list of documents to index (`MANUAL_BY_PREFIX` + `TERMS_BY_PREFIX`) |
| `cedar_authz.py` | the list of known brand slugs, to build Cedar's entity set |
| `registration.py` | which warranty component/years apply (`compute_warranty_status()`) |

This was three separately-hardcoded lists before an audit pass
consolidated them (`IMPLEMENTATION.md`, Phase 7.9) — a new brand only
needs adding in `catalog.py` now, not four files.

---

## 5. The AWS stack, concretely — where each piece actually lives

All four run locally. No AWS account, no card, no bill.

**Strands Agents SDK** — `src/layer2/agent.py`'s `_build_agent()`.
Orchestrates a local `qwen2.5-coder:7b` model via Ollama
(`http://localhost:11434`, overridable with `OLLAMA_HOST`). Two calls
per conversation turn: phrase-a-step, classify-the-reply.

**Cedar** — `policies/dashboard.cedar` (the policy) +
`src/authz/cedar_authz.py` (the evaluator). Shells out to the real
Cedar CLI binary (`tools/cedar/cedar`, fetched by
`scripts/install_cedar_cli.sh` — **not** the `cedar-policy` PyPI
package, which is an empty 0.0.1 placeholder with no actual bindings,
confirmed by importing it and finding nothing there). Decides ALLOW by
the CLI's exit code (0 = allow), fails closed — `CedarUnavailable` if
the binary is missing or the call errors, never a silent grant.

**AWS SAM Local** — `template.yaml` + `src/lambda_handlers.py`. Wraps
`src/webapp/api_core.py` (the same logic Flask calls) as real Lambda
functions, run with:

```bash
sam build --use-container   # container build: this host's Python (3.14)
                             # and arch may not match Lambda's (3.12, linux)
sam local start-api --warm-containers LAZY
```

`--warm-containers LAZY` matters: `/api/start` and `/api/respond` are
bound to one merged `ConversationFunction` (not two separate ones —
see `lambda_handlers.py`'s `conversation()`) so a conversation's turns
share one warm container's `/tmp`. **This is an honest local-demo
shortcut, not a production pattern** — real AWS never guarantees warm
container reuse across a genuine conversation's turns, which could be
minutes or hours apart. A real deployment would back this with
DynamoDB instead.

Two real constraints of Lambda surfaced by actually running this
(documented in full in `IMPLEMENTATION.md` Phase 7.5):
- `/var/task` (the code mount) is **read-only** — conversation/ticket
  storage writes to `AFTERCARE_DATA_DIR` instead (`/tmp` under Lambda,
  the repo's `data/` under Flask).
- Cedar's CLI binary is platform-specific — the Lambda package bundles
  a second, linux/aarch64 binary (`tools/cedar-lambda/cedar`) and
  `CEDAR_BIN` points at it inside the container.

**OpenSearch** — `src/layer1/opensearch_retrieval.py`. A local
single-node container (`scripts/start_opensearch.sh`, security plugin
disabled — local dev only). Indexes every manual/terms section from
`catalog.py`'s document list into one `aftercare-sections` index at
first use; retrieval is a `bool` query, `filter`ed to the exact source
document, `multi_match` on `heading^2`/`body` for real BM25 ranking.
Falls back to keyword overlap if unreachable (see §3) — the fallback
is not hidden, `Conversation.retrieval_method` records which path
actually answered.

**PartyRock** — not integrated. It needs a personal Amazon.com
sign-in, which isn't something that can be done on the user's behalf.
Open question, not a silent skip — see `IMPLEMENTATION.md`.

---

## 6. Data, concretely (not the aspirational schema in `TECHNICAL.md` §3 — the real dataclasses)

**`Registration`** (`src/layer1/registration.py`) — one row per
product a customer owns, loaded from `fixtures/sales_data.csv`:
`customer_name, customer_phone, product_id, product_name,
serial_number, purchase_date, retailer, purchase_price,
warranty_component, warranty_component_years,
warranty_component_status, warranty_parts_status`. Warranty status is
computed at load time (`compute_warranty_status()`), never stored
pre-computed, never asked of the model.

**`Conversation`** / **`Turn`** (`src/layer2/agent.py`) — one JSON file
per conversation, `data/conversations/<uuid>.json`. `Conversation`
holds the registration, the original complaint, which source was used
(`"manual"`/`"terms"`), the retrieved section, the parsed steps, the
list of `Turn`s (`attempt_number, step, customer_reply, outcome`), the
safety flag, resolved flag, an optional `Ticket`, and
`retrieval_method`. Saved after every `start()`/`respond()` call
(`api_core._save_conversation()`), reloaded by ID on every `respond()`
call (`_load_conversation()`) — file-based, not an in-memory dict; see
§5's SAM Local note for why that had to change.

**`Ticket`** (`src/layer3b/tickets.py`) — one JSON file per ticket,
`data/tickets/<TBB-NNNN>.json`: `ticket_id, customer_name,
customer_phone, product_name, serial_number, issue_summary,
product_id, attempts_tried, safety_flag, status, created_at`.
`product_id` is what lets a dashboard filter tickets to one brand.
`next_ticket_id()` just counts existing files — fine for a demo,
would need a real counter/UUID if tickets could ever be deleted.

---

## 7. What's real, what's simulated — no ambiguity

**Fully real:** the agent's retrieval-and-grounding logic, the
multi-turn escalation decision, Cedar's authorization decision, the
OpenSearch index and BM25 ranking, the SAM Local Lambda execution, the
full ticket/conversation history.

**Authored for the demo, not fetched from anywhere:** the product
manuals, the brands' terms & conditions, the sales records
(`fixtures/`) — realistic, not real, since there's no public API for
any of this.

**Simulated, on purpose, and said so in the UI itself:** the WhatsApp
channel (a styled web chat stands in for it — the copy on the lookup
screen says this outright), the customer-identity picker, the
brand-staff login picker. All three exist only because a browser demo
has no real phone number or real staff account attached to it.

---

## 8. Running it locally

```bash
# One-time setup
python -m venv .venv && .venv/bin/pip install -r requirements.txt
ollama pull qwen2.5-coder:7b
./scripts/install_cedar_cli.sh          # real Cedar CLI, both binaries
./scripts/start_opensearch.sh           # local OpenSearch container

# The live demo
nohup ollama serve > /tmp/ollama.log 2>&1 &
.venv/bin/python src/webapp/app.py      # http://localhost:5001

# The serverless-readiness proof (separate, optional)
brew install aws-sam-cli
sam build --use-container
sam local start-api --warm-containers LAZY   # http://127.0.0.1:3000
```

`data/tickets/` and `data/conversations/` are gitignored — generated
state, not source data. Delete them to reset the demo to a clean
slate.

---

## 9. Known, honest limitations

- **No real authentication.** Both the customer picker and the brand
  login are simulations, not real accounts. This is deliberate and
  disclosed everywhere it matters, not an oversight.
- **SAM Local's conversation continuity relies on warm-container
  reuse**, which real AWS Lambda never guarantees. See §5.
- **`next_ticket_id()` isn't collision-safe** if tickets were ever
  deleted out of order — not a real risk today (nothing deletes
  tickets), but not a real ID generator either.
- **Only two brands exist today.** The catalog (§4) makes a third one
  a one-file change, but nothing has exercised that path.
