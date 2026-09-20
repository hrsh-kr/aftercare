# Aftercare

**The support line that already knows what you bought.**

After-sales support over WhatsApp for brands that sell physical products. A sale is registered once, at the point of sale.
Months later the customer sends one message; the agent already knows who they are, which product, and its warranty. It
gives one real step from *that product's own manual*, follows up on the reply, answers warranty questions from the
purchase date, and hands over to a person, with everything attached, when it should. The person replies in the same WhatsApp chat.

Built for **First Commit** (WeMakeDevs × AWS) on the **Build It** track: the open-source AWS stack, running locally,
no AWS account, no card, no bill. Also entered for **Best UI**.

> **Design principle: deterministic before model.** A small local model only *words one manual step* and *reads an
> ambiguous reply*. Safety, "not in the manual", "seen this before", attempt counting, warranty maths and who-may-do-what
> are rules, queries and policies. That is what makes it testable and honest. ([Architecture](docs/ARCHITECTURE.md))

## See it (5 minutes)

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
bash scripts/install_cedar_cli.sh     # the real Cedar CLI
ollama serve                          # another terminal: the local model server
bash scripts/dev.sh                   # containers + tables + sam build + sam local start-api (needs Docker, SAM CLI)
```

Open **http://127.0.0.1:3000/sandbox**: the whole flow running for real on **fabricated** orders. Load an order file,
message as a customer (click the chips or type), watch the agent work, reply as a person from the brand's inbox, see
the analytics update. The click-by-click script, with expected results for eight personas, is
[`docs/SANDBOX_RUNBOOK.md`](docs/SANDBOX_RUNBOOK.md).

| Page | What it is |
|---|---|
| `/` | The story: problem, onboarding by order file, the customer's six steps, "under the hood" with live status of each component |
| `/sandbox` | **The real demo.** Order file → WhatsApp → agent → brand inbox → analytics. Only WhatsApp's network is simulated |
| `/demo` | A guided page with five fixed scenarios, five different endings (also the real agent) |
| `/dashboard` | The brand dashboard: complaints with red/yellow/green status, chat + reply, products, an AI analytics bar |

Staff sign-ins (demo passcodes, shown on the login page): `meera.nair` / `aqua-manager` (AquaSpin manager),
`dev.patel` / `aqua-agent` (AquaSpin agent), `sara.thomas` / `arctic-manager` (ArcticAir manager). Agents may reply but
Cedar refuses them a resolve; "Try ArcticAir" while signed in to AquaSpin shows the cross-brand refusal.

## How the AWS open-source stack is used

| Tool | What it does here | Code |
|---|---|---|
| **Strands Agents** | Words one manual step, reads an ambiguous reply (Ollama, gemma2:9b). A fresh agent per call; a `HookProvider` times each model call | `src/agent/agent.py` |
| **OpenSearch** | Manual retrieval (BM25, custom analyzer with a synonym filter); recurrence as a serial + `now-90d` range query; `terms` aggregations for the dashboard; ticket search | `src/domain/opensearch_retrieval.py`, `src/records/case_index.py` |
| **Cedar** | Schema-validated policies for view / reply / resolve / unmask-phone, and a forbid across brands; session-derived principal; every decision names its policy | `policies/`, `src/authz/` |
| **SAM CLI + API Gateway + Lambda** | The whole site is one Lambda (Powertools' API Gateway resolver): pages and 28 routes. `template.yaml` also declares both tables | `template.yaml`, `src/lambda_app.py` |
| **DynamoDB Local on Amazon Corretto** | Single table: registry, conversations, tickets, cases, the WhatsApp message log, inbox, atomic counter, TTL | `src/storage/`, `docker/`, [`docs/DYNAMODB_DESIGN.md`](docs/DYNAMODB_DESIGN.md) |
| **Lambda Powertools** | JSON logs (never phones or complaint text), EMF metrics, `Idempotency-Key` on start | `src/webapp/observability.py`, `idempotency.py` |

**No fallbacks:** if OpenSearch, DynamoDB or Ollama is down the API returns `503` naming the service. **Ship it:** not used; nothing is
deployed. `template.yaml` is written for `sam deploy`; [ARCHITECTURE §9](docs/ARCHITECTURE.md) maps each piece to its managed
service. **Not used, and why:** LocalStack (needs its own auth token), PartyRock (personal sign-in), Finch, EKS Distro/Anywhere and Firecracker (no natural role).

## Verify the claims

```bash
tests/run_all.sh                                                  # unit + integration (stubbed model; real Cedar, OpenSearch, DynamoDB Local)
.venv/bin/python scripts/run_sandbox_scenarios.py -v              # 8 personas through the WhatsApp webhook, real model, 25 checks
.venv/bin/python scripts/run_scenarios.py http://127.0.0.1:3000   # the /demo page's 5 scenarios
PYTHONPATH=. .venv/bin/python scripts/eval_routing.py             # 41 customer phrasings route correctly
PYTHONPATH=. .venv/bin/python scripts/eval_model.py               # how local models do the two jobs the model has
```

## Repo map

```
src/lambda_app.py        the Lambda: routes + pages          src/agent/agent.py     the support agent (rules + Strands)
src/webapp/api_core.py   business logic behind every route   src/channel/bot.py      the WhatsApp channel (state machine, inbox, replies)
src/domain/              catalog, registration, retrieval    src/records/           tickets, cases (OpenSearch)
src/storage/             DynamoDB store (+ file test double) src/authz/             Cedar wrapper, sessions
policies/                Cedar policies + schema             public/static/         CSS/JS (landing, sandbox, demo, dashboard)
fixtures/                manuals, terms, order files (all fabricated), seeds
scripts/                 dev.sh, bootstrap, evals, scenario runners      tests/   docs/   docker/   template.yaml
```

## Honest limits

Nothing deployed, no AWS account. WhatsApp's network is simulated; customers, orders and manuals are fabricated. Chat is
polled (production would push). "Not in the manual" is word overlap; recurrence matches on manual section. A code change
needs a ~1 minute `sam build`. More in [ARCHITECTURE §10](docs/ARCHITECTURE.md).

## Docs

[Architecture](docs/ARCHITECTURE.md) · [Sandbox runbook](docs/SANDBOX_RUNBOOK.md) · [DynamoDB design](docs/DYNAMODB_DESIGN.md) ·
[AWS feedback log](docs/AWS_FEEDBACK_LOG.md) (what worked, what didn't, per service) · [Pitch](docs/PITCH.md) · [Build log](docs/BUILD_LOG.md) · [Video script](docs/VIDEO_SCRIPT.md)
