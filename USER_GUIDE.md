# Aftercare — User Guide

How to install it, run it, and click through it. For how it works inside, see
`FLOW.md`; for where the project stands and what's next, see `CONTEXT.md` and
`TARGET.md`.

> **Latest (sandbox pass): the real, free-form demo is `/sandbox`; see `docs/SANDBOX_RUNBOOK.md` for exactly what to click and say.** The model is now gemma2:9b (`dev.sh` pulls it). Text below about qwen2.5-coder is historical.
>
> **What is real (2026-09-20).** The agent, manual search (OpenSearch), Cedar, tickets, storage and dashboards are real, and **`/demo` runs the real agent** (Ollama must be running). WhatsApp itself is simulated. Dashboard sign-ins: `meera.nair` / `aqua-manager`, `dev.patel` / `aqua-agent` (AquaSpin); `sara.thomas` / `arctic-manager`, `ben.dsouza` / `arctic-agent` (ArcticAir). Managers can change ticket status; agents are refused by Cedar. **Run it with `bash scripts/dev.sh`, then open http://127.0.0.1:3000** (everything is Lambda under SAM Local; needs Docker and Ollama). Ports and commands below that mention Flask or 5001 are historical.

---

## 1. What you need

| Tool | Why | Check |
|---|---|---|
| Python 3.11+ | runs the app | `python3 --version` |
| [Ollama](https://ollama.com) | local model | `ollama --version` |
| Docker Desktop | OpenSearch (and SAM Local) — optional for the basic run | `docker --version` |
| Homebrew (macOS) | SAM CLI — optional | `brew --version` |

## 2. One-time setup (from the repo root)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
ollama pull qwen2.5-coder:7b          # the model the agent uses today
./scripts/install_cedar_cli.sh        # real Cedar CLI (the PyPI package is an empty placeholder)
./scripts/start_opensearch.sh         # optional; without it retrieval silently uses keyword overlap
```

## 3. Start it

```bash
ollama serve                          # skip if already running: curl -s localhost:11434/api/tags
.venv/bin/python src/webapp/app.py    # http://localhost:5001
```

## 4. What you can click

| URL | What you'll see | Real? |
|---|---|---|
| `/` | the whole story in one scroll: problem → **Step 0** (a brand or store uploads a sales CSV → it's sorted into the right brand → the WhatsApp line is connected; rows and counts come from `fixtures/sales_data.csv`) → the customer's six steps (a pinned phone, left, level with each card, right; step 5 is the human handoff), then **Under the hood** with live status chips → "Live demo" | data-driven (Step 0) + illustrative story |
| `/demo` | five scenarios you play as the customer, a trace of what Aftercare did, the ticket the brand receives | **real agent** |
| `/dashboard` | pick which brand's staff you are (simulated login) | real Cedar underneath |
| `/dashboard/aquaspin`, `/dashboard/arcticair` | that brand's tickets, registered products + QR codes, warranty ring | **real data** |

**See Cedar enforce tenancy for real:** at `/dashboard`, log in as one brand, then
edit the URL to the other brand's dashboard. You get an "Access denied" screen —
a genuine Cedar evaluation (403 from `/api/dashboard/<brand>`). *(Caveat: the staff
identity is asserted by the browser today; making it server-verified is item A1 in
`TARGET.md`.)*

## 5. Talk to the real agent (until `/demo` is rewired)

Fixture customers: **Priya Sharma** `+919876543210` (two AquaSpin machines:
`WM-FC-700`, `WM-FL-900`), **Ananya Iyer** `+919845098450` (`WM-FC-700`),
**Ravi Kumar** `+919812345678` and **Sameer Khan** `+919900112233` (ArcticAir `AC-CB-15T`).

```bash
# 1) who is on this brand's line
curl 'localhost:5001/api/customers?brand=arcticair'

# 2) look up a customer on that brand (returns products + warranty status)
curl -s localhost:5001/api/lookup -H 'content-type: application/json' \
  -d '{"phone":"+919812345678","brand":"arcticair"}'

# 3) start a conversation — product_id is REQUIRED (400 without it)
curl -s localhost:5001/api/start -H 'content-type: application/json' \
  -d '{"phone":"+919812345678","product_id":"AC-CB-15T","complaint":"AC is not cooling at all"}'
# -> {conversation_id, status:"waiting", message:"<one step from the manual>"}

# 4) reply; repeat "still broken" twice -> escalates with a ticket
curl -s localhost:5001/api/respond -H 'content-type: application/json' \
  -d '{"conversation_id":"<id from step 3>","reply":"cleaned the filter, still not cooling"}'
```

Try these complaints to see each path:
- *"washing machine banging on spin"* (Priya/Ananya) — one step: level the machine.
- *"AC isn't cooling"* (Ravi) — filter, then outdoor unit, then a ticket if still broken.
- *"burning smell from the AC"* (Sameer) — skips troubleshooting, immediate safety ticket.

Then open `/dashboard/<brand>` (log in as that brand) to see the ticket with its
full thread.

## 6. Reset to a clean state (e.g. before recording)

```bash
curl -X POST localhost:5001/api/demo/reset   # or the 'Reset demo data' link on /demo
```
Generated files only; fixtures are untouched.

## 7. Optional: SAM Local (the same API as Lambda functions)

```bash
brew install aws-sam-cli
sam build --use-container
sam local start-api --warm-containers LAZY     # http://127.0.0.1:3000
curl 'http://127.0.0.1:3000/api/customers?brand=aquaspin'
```
`--use-container` (host Python ≠ Lambda's 3.12) and `--warm-containers LAZY`
(`/api/start` and `/api/respond` share one function's `/tmp`) both matter — see
`FLOW.md` §5. *Not re-verified since the brand/`product_id` API changes (A8 in `TARGET.md`).*

## 8. If something's off

| Symptom | Cause | Fix |
|---|---|---|
| `/api/start` hangs or errors | Ollama not running | `ollama serve` |
| Dashboard: "Authorization check unavailable" | Cedar binary missing | `./scripts/install_cedar_cli.sh` |
| Answers feel less precise | OpenSearch down (silent fallback) | `open -a Docker && ./scripts/start_opensearch.sh` |
| `Address already in use` :5001 | old instance | `pkill -f "python.*app.py"` |
| Dashboard "Access denied" unexpectedly | logged in as the other brand | go to `/dashboard`, pick the right one |
| Dashboard empty | no tickets yet | run an escalating conversation (§5) |
| QR codes blank offline | QR library loads from a CDN today | connect to the internet (fix is P0.4 in `TARGET.md`) |
