# Aftercare

The support line that already knows what you bought. A product is registered once, quietly, at the point of sale — no app, no form. When a customer messages about a problem, months or years later, the conversation already knows their product, its warranty status, and history. It reads their complaint, grounds a real fix in that exact product's manual, and only escalates to the brand's team when it genuinely can't help — never a guess.

Built for **First Commit** (WeMakeDevs × AWS, Bharat Builds Tour). **Build It track**, also competing for **Best UI**.

---

## Status

Design locked, build starting. See `SKILL.md` for how we work, `DESIGN.md` §9 for the build order.

## The docs

| Doc | Answers |
|---|---|
| [`PITCH.md`](PITCH.md) | Why does this matter, why now |
| [`DESIGN.md`](DESIGN.md) | What we're building, and what we're not |
| [`TECHNICAL.md`](TECHNICAL.md) | How it's built, in AWS terms |
| [`SKILL.md`](SKILL.md) | How we design, write, and code |
| `source/aftercare/` | The original product spec this build is based on — reference only |
| `archive/groundtruth/` | Our first hackathon build (candidate-authenticity verification) — set aside, not discarded, in case any of it is useful later |

## In one sentence

One engine registers products and looks them up by phone number. One agent reads a complaint, grounds a real fix in that product's actual manual, and escalates honestly when it can't help. Two views sit on top — the customer's chat, the brand's dashboard. Full picture in `DESIGN.md`.

## Stack

Strands Agents SDK + a local model (Ollama), plain local Python standing in for Lambda/DynamoDB. No AWS account required. Full mapping in `TECHNICAL.md`.
