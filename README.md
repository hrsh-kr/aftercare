# Aftercare

The support line that already knows what you bought. A product is registered once, quietly, at the point of sale — no app, no form. When a customer messages about a problem, months or years later, the conversation already knows their product, its warranty status, and history. It reads their complaint, grounds a real fix in that exact product's manual, and only escalates to the brand's team when it genuinely can't help — never a guess.

Built for **First Commit** (WeMakeDevs × AWS, Bharat Builds Tour). **Build It track**, also competing for **Best UI**.

---

## Status

Built and running locally — chat UI, brand dashboards, the full agent loop, and all four AWS OSS tools wired in for real. See `IMPLEMENTATION.md` for the phase-by-phase record, `FLOW.md` for exactly how it works today.

## The docs

| Doc | Answers |
|---|---|
| [`PITCH.md`](PITCH.md) | Why does this matter, why now |
| [`DESIGN.md`](DESIGN.md) | What we're building, and what we're not |
| [`TECHNICAL.md`](TECHNICAL.md) | How it's built, in AWS terms |
| [`FLOW.md`](FLOW.md) | How it actually works, as built — request-by-request, file-by-file |
| [`USER_GUIDE.md`](USER_GUIDE.md) | How to install, run, and click through the demo yourself |
| [`SKILL.md`](SKILL.md) | How we design, write, and code |
| [`IMPLEMENTATION.md`](IMPLEMENTATION.md) | Live task checklist — what's done, what's next |
| `source/aftercare/` | The original product spec this build is based on — reference only |
| `archive/groundtruth/` | Our first hackathon build (candidate-authenticity verification) — set aside, not discarded, in case any of it is useful later |

## In one sentence

One engine registers products and looks them up by phone number. One agent reads a complaint, grounds a real fix in that product's actual manual, and escalates honestly when it can't help. Aftercare is the shared backend; each brand (ArcticAir, AquaSpin) gets its own customer chat and its own Cedar-authorized dashboard, never seeing the other's data. Full picture in `DESIGN.md`, exact mechanics in `FLOW.md`.

## Stack

Strands Agents SDK (the agent) + Cedar (brand-dashboard authorization) + AWS SAM Local (the same core API as real Lambda functions) + OpenSearch (BM25 retrieval) + a local model via Ollama. No AWS account, no card, no bill. Full mapping in `TECHNICAL.md`, exact wiring in `FLOW.md` §5.
