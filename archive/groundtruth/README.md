# Groundtruth

Checks whether a candidate's claims are true — using real evidence, before anyone reaches an interview — then has a short written conversation with them about their own work, so a genuine claim can be told apart from one that only looks good on paper.

Built for **First Commit** (WeMakeDevs × AWS, Bharat Builds Tour). **Build It track**, also competing for **Best UI**.

---

## Status

Design locked. Build started 17 September. Build order is in `DESIGN.md`; how we work is in `SKILL.md`.

## The docs

| Doc | Answers |
|---|---|
| [`PITCH.md`](PITCH.md) | Why does this matter, why now |
| [`DESIGN.md`](DESIGN.md) | What we're building, and what we're not |
| [`TECHNICAL.md`](TECHNICAL.md) | How it's built, in AWS terms |
| [`SKILL.md`](SKILL.md) | How we design, write, and code |
| `RESEARCH.md` | The original research archive — reference only |

## In one sentence

One engine verifies claims against real repo evidence. One layer has an adaptive conversation grounded in that evidence. Two views sit on top — one for the candidate, one for the company. Full picture in `DESIGN.md`.

## Stack

Strands Agents SDK + a local model, SAM CLI + LocalStack (Lambda, API Gateway, Step Functions, DynamoDB, S3), Cedar. No AWS account required. Full mapping in `TECHNICAL.md`.
