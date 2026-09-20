# Aftercare

**The support line that already knows what you bought.**

Aftercare is after-sales support over WhatsApp for brands that sell physical products. A sale is registered once, at the point of sale. Months later, when something breaks, the customer sends one message. The agent already knows who they are, which product, and its warranty status. It gives one real step from *that product's own manual*, follows up on the reply, and hands over to a person, with everything already attached, when it should.

Built for **First Commit** (WeMakeDevs × AWS): **Build It** track (open-source AWS stack, no account, no card, no bill), also entered for **Best UI**.

## The problem

Warranty and service is where a brand's promise gets tested, and it is still a phone tree, a hunt for a model number, and explaining the same thing three times to a company that already holds your purchase record. Brands pay for that in call-centre cost and in customers who don't come back. India's WhatsApp-first buyers are the obvious place to fix it.

## What it does

1. **Onboarding:** a brand, or a store selling many brands, uploads its sales CSV. Aftercare files every sale under the brand that owns the product code and reports what it can't place (unknown codes, bad dates, duplicate serials) instead of guessing.
2. **The customer's message:** identified by phone number, product picked if they own several, warranty read from the record.
3. **One real step, from the manual.** A second one if needed. Fixed means no ticket.
4. **A person takes over, and says why.** Six reasons, each decided by code, not by the model: a safety issue, two steps tried and still broken, the manual has nothing more, the problem is not in the manual, the same problem is back within 90 days, or a question that needs a human.
5. **The brand's dashboard:** its own tickets, private to it, with *why customers reach a person* (OpenSearch aggregations) and which manual sections send them there.

**The principle behind all of it: deterministic before model.** A 7B local model phrases a step well and judges a safety call badly. So every decision that matters is a rule, a query or a policy. The model only words the step and reads the reply.

## How the AWS open-source stack is used

| Tool | What it does here | Where |
|---|---|---|
| **Strands Agents** | Words one manual step and classifies the reply, on a local Ollama model. A fresh agent per call (a shared one leaked context between customers); `HookProvider` times every model call for the demo's trace. | `src/layer2/agent.py` |
| **OpenSearch** | Manual retrieval (BM25, English analyzer); recurrence as a serial + `now-90d` range query; brand insights as `terms` aggregations; ticket text search. Required: no keyword fallback. | `src/layer1/opensearch_retrieval.py`, `src/layer3b/case_index.py` |
| **Cedar** | Schema-checked policies (`cedar validate` in tests) for `viewDashboard`, `viewTicket`, `updateTicketStatus` (managers only), `viewPhoneUnmasked` (safety tickets only) and a `forbid` across brands. The principal comes from a signed server-side session, and every decision names the policy that made it. | `policies/`, `src/authz/` |
| **SAM CLI (SAM Local) + API Gateway + Lambda** | The whole site is one Lambda (Lambda Powertools' API Gateway resolver) serving the pages and every `/api` route; static files via `sam local --static-dir`. `template.yaml` declares the function, 17 explicit routes and both tables. | `template.yaml`, `src/lambda_app.py`, `src/pages.py` |
| **DynamoDB Local on Amazon Corretto** | Single-table design with an overloaded GSI and an atomic ticket counter; the only storage backend. Runs in a Corretto (AWS's OpenJDK) image. DynamoDB Local is not in the Build It table; it is AWS's own emulator, so we say so. | `src/storage/`, `docker/dynamodb-local/`, `docs/DYNAMODB_DESIGN.md` |
| **Lambda Powertools** | Structured JSON logs (never a phone number or complaint text), CloudWatch EMF metrics, `Idempotency-Key` on `POST /api/start`. | `src/webapp/observability.py`, `src/webapp/idempotency.py` |

**Ship it:** not used. There is no AWS account behind this, and nothing here is deployed. `template.yaml` is written to deploy with `sam deploy`. Where each piece goes in production: Ollama → Bedrock, OpenSearch container → OpenSearch Serverless, Cedar CLI → Amazon Verified Permissions, DynamoDB Local → DynamoDB, SAM Local → API Gateway + Lambda, Powertools → CloudWatch.

**Not used, and why:** LocalStack needs a LocalStack auth token (their account), so S3/SQS/Cognito/SES are not used; PartyRock needs a personal Amazon sign-in; Finch, EKS Distro/Anywhere and Firecracker have no natural role here (Docker runs the containers).

**Real vs simulated.** Real: the agent, manual search, escalation rules, tickets, Cedar policies, DynamoDB, Lambda handlers. Simulated: WhatsApp itself, the QR sticker, the customer's typing. The sales-file check is real but a preview; the registry is still `fixtures/sales_data.csv`.

## Architecture

```
Browser ─▶ API Gateway (SAM Local) ─▶ one Lambda: pages (Jinja) + /api routes
                              │   Powertools: resolver, logs, EMF, idempotency
                          api_core  (pure logic)
      ┌───────────────┬───────┴───────┬─────────────────┐
  Strands Agent    OpenSearch        Cedar           DynamoDB Local
  Ollama qwen2.5   manual, cases,    schema + 5      (Corretto image)
  hooks: latency   tickets, aggs     policies        single table
```

Agent loop: safety keywords (with negation) → coverage vs troubleshooting → retrieve one section from that product's manual → **regex-parse the numbered steps** → gate: *not in the manual?* → gate: *seen this before?* → model words step 1 → customer replies → model reads the reply → step 2 or hand over. Two tries, then a person.

## Run it

Everything runs as AWS Lambda under SAM Local: pages and API are one function behind API Gateway. There is no other web server and no fallback path; if OpenSearch, DynamoDB or the model is down, the API answers `503` naming the service.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
bash scripts/install_cedar_cli.sh            # the real Cedar CLI (the PyPI package is an empty placeholder)
ollama pull qwen2.5-coder:7b && ollama serve # the local model, in another terminal
bash scripts/dev.sh                          # OpenSearch + DynamoDB Local (Corretto) -> create tables/indices -> sam build -> sam local start-api
# open http://127.0.0.1:3000   (landing, /demo, /dashboard)
```

`scripts/dev.sh` needs Docker. Set `SKIP_BUILD=1` to reuse the last `sam build`. After editing code, re-run it (a rebuild takes about a minute; static files in `public/` are served live).

Dashboard sign-ins (demo passcodes, also shown on the login page): `meera.nair` / `aqua-manager`, `dev.patel` / `aqua-agent` (AquaSpin); `sara.thomas` / `arctic-manager`, `ben.dsouza` / `arctic-agent` (ArcticAir). Managers can change ticket status; agents are refused by Cedar. While signed in as AquaSpin staff, "Try ArcticAir's dashboard" shows the cross-brand refusal.

```bash
.venv/bin/python scripts/run_scenarios.py http://127.0.0.1:3000   # the five demo scenarios, five endings, through the Lambda
tests/run_all.sh                                                   # unit + integration tests (needs the services up)
```

## What we learned, honestly

See [`docs/AWS_FEEDBACK_LOG.md`](docs/AWS_FEEDBACK_LOG.md): a shared Strands `Agent` silently remembers every prompt (cross-customer context bleed); Strands' structured output needs a tool-calling model and fails on a local 7B; an OpenSearch filter keyed on an absolute path made every Lambda query silently fall back; Powertools idempotency ignores a changed body unless told to validate it.

## Docs

[`DESIGN.md`](DESIGN.md) what we build and don't · [`TECHNICAL.md`](TECHNICAL.md) how, in AWS terms · [`FLOW.md`](FLOW.md) request by request · [`docs/DYNAMODB_DESIGN.md`](docs/DYNAMODB_DESIGN.md) access patterns and keys · [`IMPLEMENTATION.md`](IMPLEMENTATION.md) the build log · [`USER_GUIDE.md`](USER_GUIDE.md) click-through · [`PITCH.md`](PITCH.md) why it matters.
