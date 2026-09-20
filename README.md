# Aftercare

**The support line that already knows what you bought.**

After-sales support over WhatsApp for brands that sell physical products, built on AWS's open-source stack (Strands Agents, OpenSearch, Cedar, SAM with API Gateway and Lambda, DynamoDB) and designed around one rule: **a small model words things; code decides things.**

Built solo for **First Commit** (WeMakeDevs × AWS), **Build It** track, also entered for **Best UI**. It runs entirely on a laptop with no AWS account. Customers, orders and manuals are fabricated, and only WhatsApp's network is simulated; everything else is the real thing.

| | |
|---|---|
| **Website (a recording of the real tool)** | deployed from `public/` on Vercel |
| **Run the real thing** | [`docs/SANDBOX_RUNBOOK.md`](docs/SANDBOX_RUNBOOK.md) |
| **The story, bugs included** | [`docs/BLOG.md`](docs/BLOG.md) |
| **Architecture, in depth** | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |

---

## 1. The problem, from first principles

Something breaks: a washing machine bangs on every spin, an AC stops cooling in a heatwave. You message the brand and the first fifteen minutes go on proving that you own the thing. Model number off a sticker behind the door. Purchase date from an old email. A screenshot of the invoice.

That is a data problem, not a conversation problem. The brand sold you the product and holds every fact the agent asks for. What is missing is a **join** between the person typing and the sale. Everything downstream (slow support, angry customers, agents starting from zero) follows from that missing join.

So the design starts there:

1. **Register the sale once, at the point of sale**, from the brand's own order file, and never depend on the customer to do it.
2. Make **the phone number itself the key**. On WhatsApp the sender is already authenticated, so asking for it is absurd.
3. Ground every answer in **that product's own manual and terms**, not in what a model remembers.
4. Treat the human handover as a **first-class feature** with everything attached, not a failure state.

## 2. The one idea that shaped the architecture

My first prototype let the model do everything. It went wrong immediately, and in a way I could measure. Asked to compute warranty status from a purchase date, the local model got **two of four customers exactly backwards**: it called an active motor warranty expired, and a lapsed parts warranty live. Confident, fluent, wrong.

So I split the system by *what kind of decision it is*:

| Decision | Who makes it | Why not the model |
|---|---|---|
| Is this a safety issue? | Keyword rule with negation, or retrieval landing on the manual's own safety section | A missed safety case must not depend on sampling |
| Which step is next? | A regex over the manual's numbered list | The manual is the source of truth |
| Two failed steps, then a person | A counter (`MAX_ATTEMPTS = 2`) | Counting is not a language task |
| Is it in the manual at all? | Word-overlap gate that shares one synonym list with the search analyzer | Otherwise the two layers disagree |
| Has this product had this problem before? | OpenSearch: serial + `range now-90d` | A query, not an opinion |
| Warranty status | Date arithmetic; the Terms wording is quoted | The bug above |
| Fixed, or still broken? | **Rules first**; the model sees only the ambiguous middle; anything but a clear yes is "still broken" | A false "resolved" hides a broken product |
| Who may see, reply, resolve | Cedar policy; the decision names the policy | Authorization must be auditable |
| **Word one manual step; read a vague reply** | **The model** | This is what it is good at |

The model does two small jobs, and a small local one (`gemma2:9b`, chosen by an eval of five models) is enough. Everything that matters can be tested without it, using a stub model, and fails safe.

## 3. Architecture

```
                     WhatsApp (simulated at Meta's webhook boundary)
                                        │
                        API Gateway  ─▶  ONE Lambda   (26 routes: pages + API, Powertools resolver)
                                        │
      ┌───────────────┬─────────────────┼──────────────────┬──────────────────┐
  Strands Agent    OpenSearch         Cedar CLI        DynamoDB Local      Lambda Powertools
  local Ollama     manual sections,   schema + 6       (Amazon Corretto)   JSON logs, EMF metrics,
  gemma2:9b        cases, tickets,    policies         one table,          idempotency
  latency hook     aggregations       named decisions  12 access patterns
```

A message enters exactly as Meta delivers one, at `POST /api/wa/webhook`. The chat state machine (`idle → awaiting_product → bot → human`) decides what happens next, every message lands in a per-chat log in DynamoDB, and a hand-over creates a ticket with a reason code. A person replies from the brand's inbox into the *same* chat; Cedar decides who may.

### Why each AWS tool, and what it costs

| Tool | Job here | Why this and not something simpler | Trade-off I accepted |
|---|---|---|---|
| **API Gateway + Lambda** (SAM CLI) | One function serves every page and API route | Stateless by construction: chat state lives in DynamoDB, so a restart loses nothing | Cold starts; a code change needs a `sam build` (~1 min) |
| **Strands Agents** | Words one step; reads an ambiguous reply | A thin, hookable agent layer over any model; hooks give exact latency | A local model is slower; structured output needs a tool-calling model, so I use plain text and a strict parser |
| **OpenSearch** | BM25 manual retrieval, recurrence window, dashboard aggregations | Ranked search, a time-window filter and `terms` aggregations in one engine | Heavier than a database; keyword relevance, not semantic |
| **Cedar** | Who may view, reply, resolve; forbid across brands | Policy is data, is schema-validated, and every decision names its rule | One more language; no Python binding, so I call the real CLI per decision |
| **DynamoDB** | Registry, chats, tickets, cases in one table | Access patterns are known and few; atomic ticket counter; TTL for free | Queries must be designed up front; ad-hoc questions go to OpenSearch |
| **Lambda Powertools** | Resolver, logs, metrics, idempotency | Route decorators and structured logging with no client code | Idempotency needs a payload-validation key, or a changed body silently returns the cached result |

**No fallbacks.** An earlier version ran on Flask with a keyword-search fallback. I removed both. If OpenSearch, DynamoDB or the model is down, the API returns `503` naming the service. A fallback turns *broken* into *plausible*, and plausible is what you cannot debug. It paid off at once: the class of bug I had just found (a search that quietly fell back and looked fine) cannot hide in the new design.

## 4. What is real, and what is not

| Real, running on this machine | Simulated or fabricated |
|---|---|
| Order-file validation and the customer registry | WhatsApp's network (the phone talks to a Meta-shaped webhook on the server) |
| The agent, manual search, escalation rules, warranty answers | The customers, orders, manuals and terms (two fictional brands: AquaSpin washing machines, ArcticAir ACs) |
| Tickets, the chat log, the inbox where a person replies | The QR sticker at the counter |
| Cedar policies, DynamoDB, OpenSearch, the Lambda | |

## 5. See it

**The website** is a *recording of the real tool*, and says so on every page. `scripts/record_playback.py` drives the running stack through its real webhook and staff endpoints and stores every response; the deployed pages replay those responses through the same UI. I chose this over a mock: the site cannot show anything the system did not do. A test fails the build if the deployed pages drift from the templates.

**The real thing** runs locally (Docker, SAM CLI, Ollama; no AWS account):

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
bash scripts/install_cedar_cli.sh     # the real Cedar CLI
ollama serve                          # another terminal: the local model server
bash scripts/dev.sh                   # containers, tables, sam build, sam local start-api
```

Open **http://127.0.0.1:3000/sandbox**. Load an order file, message as a customer (click a chip or type anything), watch the agent work, reply as a person from the inbox, see the analytics update. Click-by-click steps for eight personas, with expected results, are in [`docs/SANDBOX_RUNBOOK.md`](docs/SANDBOX_RUNBOOK.md).

| Page | What it is |
|---|---|
| `/` | The story: problem, onboarding by order file, the customer's six steps, and a one-screen architecture blueprint |
| `/demo` | Live demo (recorded): order file as a live spreadsheet, eight customers, what Aftercare did, the inbox, analytics, the dashboard |
| `/sandbox` | The real thing, local only: free-form, on fabricated orders |
| `/dashboard` | The brand dashboard: complaints with red/yellow/green status, chat and reply, products, AI analytics |

Staff sign-ins (demo passcodes shown on the login page): `meera.nair` / `aqua-manager`, `dev.patel` / `aqua-agent`, `sara.thomas` / `arctic-manager`. An agent may reply but Cedar refuses a resolve; opening ArcticAir while signed in to AquaSpin shows the cross-brand refusal.

To publish the website: import the repo into Vercel (`vercel.json` serves `public/`, no build step). After changing a template or re-recording, run `.venv/bin/python scripts/record_playback.py` (needs `bash scripts/dev.sh` running) and `.venv/bin/python scripts/build_site.py`, then commit.

## 6. Verify the claims

```bash
tests/run_all.sh                                          # unit + integration (stub model; real Cedar, OpenSearch, DynamoDB Local)
.venv/bin/python scripts/run_sandbox_scenarios.py -v      # 8 personas through the webhook, real model, 25 checks
PYTHONPATH=. .venv/bin/python scripts/eval_routing.py     # 41 customer phrasings route correctly
PYTHONPATH=. .venv/bin/python scripts/eval_model.py       # five local models, the two jobs the model has
```

| Claim | Evidence |
|---|---|
| Every escalation reason; warranty answered with no model call; negation-aware safety | `tests/test_escalation.py` |
| Cedar matrix; a forged header is ignored; agents cannot resolve | `tests/test_cedar.py` (real CLI) |
| Orders → registration → conversation → handover → human reply → resolve | `tests/test_channel.py` |
| Identical behaviour on the file store and DynamoDB | `tests/test_store_contract.py` |
| Malformed input gives 400/401, never 502 | `tests/test_api_robustness.py` |
| The deployed site matches the templates and leaks nothing | `tests/test_site_fresh.py` |

## 7. Decisions I made, and where I changed my mind

- **Dropped the Ship It track.** I planned to ship on AWS. On the day the build window opened my new account's verification had not finished (CloudShell would not start, "up to two days"). I could have written Bedrock code I could not run and labelled it "swappable later". I judged that a workaround dressed as design, and committed to Build It instead. It forced the question the whole project answers: where should a small model sit in a system?
- **Dropped my first idea.** GroundTruth (checking whether a repository backs a resume claim) had a flaw I could not argue away: a repository cannot prove who wrote it. I archived it and built the problem I had lived myself.
- **One backend, independent brands.** I first built a single dashboard across brands. That is wrong for the product: Aftercare is a provider serving several brands, so each gets its own line, its own dashboard and Cedar-enforced isolation.
- **Removed the phone-number prompt.** On WhatsApp the sender's number is the identity.
- **Warranty maths moved out of the model** after the two-of-four failure.
- **The demo changed three times:** scripted, then a real sandbox, then a recording of the real sandbox, so a judge can open it without Docker and it still cannot lie.

Bugs found and fixed along the way (a silent OpenSearch fallback that was only visible inside the Lambda, a shared agent leaking one customer's complaint into the next, SAM Local surprises, and more) are written up in [`docs/BLOG.md`](docs/BLOG.md) and, per service, in [`docs/AWS_FEEDBACK_LOG.md`](docs/AWS_FEEDBACK_LOG.md).

## 8. Honest limits

Nothing is deployed to AWS and no account is used. WhatsApp is simulated. Chat is polled every 1.1 s (production would push). "Not in the manual" is a word-overlap test, and recurrence matches on manual section rather than wording. Multi-language input only works where a rule or the model happens to catch it. A code change needs about a minute of `sam build`. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §9 maps every component to its managed service (Bedrock, OpenSearch Service, Verified Permissions, DynamoDB, API Gateway and Lambda) for a real deployment; `template.yaml` is already written for `sam deploy`.

## 9. Repo map

```
src/lambda_app.py         the Lambda: routes and pages       src/agent/agent.py      the support agent (rules + Strands)
src/webapp/api_core.py    logic behind every route           src/channel/bot.py      the WhatsApp channel: state machine, inbox, replies
src/domain/               catalog, registration, retrieval   src/records/            tickets, cases (OpenSearch)
src/storage/              DynamoDB store (+ file test double) src/authz/             Cedar wrapper, signed sessions
policies/                 Cedar policies + schema            public/                 the website Vercel serves (pre-rendered)
fixtures/                 manuals, terms, order files (all fabricated), seeds
scripts/                  dev.sh, bootstrap, evals, recorder, site builder      tests/   docs/   docker/   template.yaml
```

## 10. Built with

I designed the product and the architecture, set the rules above, and made the calls in section 7. I built it with **Claude Code** as a pair-programmer for implementation, refactors and test scaffolding, and I reviewed and steered its work throughout (for example, removing Flask and every fallback was my instruction, not a default). The evals, tests and recorded runs exist so the claims here do not rest on anyone's word.

Docs: [The story](docs/BLOG.md) · [Architecture](docs/ARCHITECTURE.md) · [Sandbox runbook](docs/SANDBOX_RUNBOOK.md) · [DynamoDB design](docs/DYNAMODB_DESIGN.md) · [AWS feedback log](docs/AWS_FEEDBACK_LOG.md) · [Pitch](docs/PITCH.md) · [Build log](docs/BUILD_LOG.md) · [Video script](docs/VIDEO_SCRIPT.md)
