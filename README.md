# Aftercare

The support line that already knows what you bought. A product is registered once, quietly, at the point of sale — no app, no form. When a customer messages about a problem, months or years later, the conversation already knows their product, its warranty status, and history. It reads their complaint, grounds a real fix in that exact product's manual, and only escalates to the brand's team when it genuinely can't help — never a guess.

Built for **First Commit** (WeMakeDevs × AWS, Bharat Builds Tour). **Build It track** (open-source AWS stack, no account/card/bill), also competing for **Best UI**.

---

## Status (2026-09-20)

Backend is built and verified: the agent loop, warranty math, OpenSearch retrieval with fallback, Cedar-gated per-brand dashboards, and a SAM Local Lambda adapter.

**The story is one page now:** the landing (`/`) runs hero → problem → **Step 0** (a brand *or a store* uploads its sales CSV → Aftercare sorts it into brands → connects the WhatsApp line, on the open-source AWS stack) → the customer's side in five steps → **Live demo** (`/demo`), which hands off to the brand dashboard. The old separate brand and customer pages are archived in `archive/business-pages/`.

**Known gap, stated plainly:** the routed `/demo` page is currently a *scripted animation* with illustrative data — it does not call the real agent. The real-backend chat UI exists but is not routed. Making the demo real is Phase C in `TARGET.md` (order: A flow ✅ → B visuals/implementation → C technical + inconsistencies).

**New session? Read `CONTEXT.md` first, then `TARGET.md`.**

## The docs

| Doc | Answers |
|---|---|
| [`CONTEXT.md`](CONTEXT.md) | **Start here.** Who/what/why, hackathon rules, current state, audit findings, working agreements |
| [`TARGET.md`](TARGET.md) | **What to do next** — prioritized plan to be shortlisted (Build It + Best UI), with simplify/add/subtract notes |
| [`PITCH.md`](PITCH.md) | Why does this matter, why now |
| [`DESIGN.md`](DESIGN.md) | What we're building, and what we're not |
| [`TECHNICAL.md`](TECHNICAL.md) | How it's built, in AWS terms |
| [`FLOW.md`](FLOW.md) | How the backend actually works — request-by-request, file-by-file |
| [`USER_GUIDE.md`](USER_GUIDE.md) | Install, run, and click through it yourself |
| [`SKILL.md`](SKILL.md) | How we design, write, and code |
| [`IMPLEMENTATION.md`](IMPLEMENTATION.md) | Phase-by-phase record and decisions |
| `source/aftercare/` | The original product spec — reference only |
| `archive/groundtruth/` | Our first, abandoned hackathon idea — not maintained |

## In one sentence

One engine registers products and looks them up by phone number. One agent reads a complaint, grounds a real fix in that product's actual manual, and escalates honestly when it can't help. Aftercare is the shared backend; each brand (ArcticAir, AquaSpin) gets its own WhatsApp line and its own Cedar-authorized dashboard, never seeing the other's data.

## Stack

| Tool | Role |
|---|---|
| Strands Agents SDK + Ollama | the support agent (local model) |
| Cedar | per-brand dashboard authorization (real CLI, fail-closed) |
| AWS SAM Local | the same core API as real Lambda functions |
| OpenSearch | BM25 retrieval over manuals/terms (falls back to keyword overlap if down) |

No AWS account, no card, no bill. PartyRock is not used (needs a personal sign-in). Exact wiring in `FLOW.md` §5, honest caveats in `CONTEXT.md` §5.

## Quick start

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
ollama pull qwen2.5-coder:7b
./scripts/install_cedar_cli.sh
./scripts/start_opensearch.sh          # optional (needs Docker)
ollama serve &                         # if not already running
.venv/bin/python src/webapp/app.py     # http://localhost:5001
```

Full walkthrough: `USER_GUIDE.md`.
