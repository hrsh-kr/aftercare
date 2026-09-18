# Aftercare — Implementation Checklist

**Purpose of this file:** if this session ends and a different model or person picks this up cold, they should be able to read this one file and know exactly what's done, what's next, and how to verify it — without needing the conversation history. Update the checkboxes as you go, in this file, immediately after finishing each task, not in a batch at the end.

**Read first, in this order:** `README.md` (30 seconds) → `PITCH.md` (why) → `DESIGN.md` (what, layer by layer, what we're NOT building) → `TECHNICAL.md` (how — data model, the agent loop, API sketch) → `SKILL.md` (how we design/write/code, and the build order this checklist follows). This file is the only one that changes constantly; those five are stable unless something real changes.

---

## Environment (done once, reused for the whole build)

- [x] Python virtual environment at `.venv/` (activate with `source .venv/bin/activate`)
- [x] Installed in `.venv`: `strands-agents`, `ollama`, `requests` (see `archive/groundtruth/requirements.txt` for exact versions — same environment, no changes needed)
- [x] Ollama installed and running locally (`curl -s http://localhost:11434/api/tags` should return 200)
- [x] Local model available: `qwen2.5-coder:7b` (confirm with `ollama list`) — this is the model to use unless a de-risking test says otherwise
- [ ] If starting a new session: run the two checks above first. If either fails, fix it before writing any code.

---

## Phase 0 — Groundwork (done)

- [x] `PITCH.md`, `DESIGN.md`, `TECHNICAL.md`, `README.md` written for Aftercare
- [x] `SKILL.md` carried over from the first build, lightly updated (still fully applicable — the four-voice mapping, design modes, build order, dual-audience principle)
- [x] Groundtruth (first idea, candidate-authenticity verification) archived, not deleted, at `archive/groundtruth/` — working code, in case anything is reusable later
- [x] Original product spec preserved at `source/aftercare/` for reference
- [x] Fixtures authored at `fixtures/` — **reworked once already, see decision log:** dropped the ceiling fan (troubleshooting required tools/ladder work nobody does over chat), replaced with washing machine + AC, both genuinely DIY-fixable, researched against real common-fault patterns, not invented:
  - [x] `manual_windmere_washing_machine.md` — drum noise (level + load balance, real DIY steps), foul smell/residue (lint filter, descaling), no-start, safety
  - [x] `manual_windmere_ac.md` — not cooling (filter clean), foul smell (drain + filter), water dripping, safety
  - [x] `terms_windmere.md` — multi-product warranty terms (washing machine: 2yr motor; AC: 5yr compressor; both: 1yr parts)
  - [x] `sales_data_windmere.csv` — 4 customers across both products, mixed warranty states

---

## Phase 1 — De-risk the core mechanism (done)

**Why this is first:** everything else is CRUD and UI. This is the one part we don't yet know works.

- [x] Write `scripts/test_agent_grounding.py`
- [x] Run it, twice — once with a real bug, once fixed (see below)
- [x] Retrieval decision: **keyword overlap, not embeddings.** Grinding vs. clicking — the real test, since they're lexically similar but have different root causes — retrieved the correct manual section both times. No need for embedding infra given this result.

**What actually happened (both runs):**

Run 1 — troubleshooting grounding: **worked correctly, no changes needed.** Grinding correctly traced to "misalignment of blades or loose mounting screw" (manual 5.1). Clicking correctly traced to "bent blade or shifted balancing weight" (manual 5.2) — a genuinely different, correctly-distinguished root cause, not just a reworded version of the grinding answer. Safety case (burning smell) correctly flagged before any model call, zero troubleshooting attempt.

Run 1 — warranty status: **wrong on 2 of 4 customers.** The model was asked to compute motor/parts expiry directly from purchase dates in the prompt. Priya Sharma came back exactly backwards (said motor expired/parts active; the real answer is the reverse). Ananya Iyer came back with parts marked active when the 1-year parts warranty had already lapsed by 29 days. This is the same lesson from the ClaimCast discussion, applied too late the first time: never let the model perform the deterministic calculation.

**Fix:** moved warranty status to plain Python date arithmetic (`compute_warranty_status()` in the script). The model's only job now is phrasing an answer from numbers it's handed, never computing them. Run 2, same 4 customers, all four correct.

**Decision, going into Layer 1:** the registration/warranty lookup (`src/layer1/registration.py`, Phase 2 below) must compute status in Python from the start — this isn't a detail to get right later, it's now a validated requirement.

**Reworked once, for realism (see decision log):** the ceiling fan fixture was dropped — its troubleshooting steps (check blade screws, check down-rod seating) require a ladder and a screwdriver, not something a customer does over chat. Rebuilt around washing machine (drum noise, foul smell) and AC (not cooling, foul smell), researched against real common-fault patterns — both are genuinely hands-only fixable. Re-ran the full test suite against the new fixtures and the new one-step-at-a-time prompt design (see Layer 2's updated spec in `DESIGN.md`/`TECHNICAL.md`): all 5 cases correct on the first run — washing machine drum noise and AC cooling both correctly retrieved from the right manual (not confused with each other despite both mentioning "filter"), each gave exactly one doable step and asked for a reply rather than dumping the whole section, warranty math correct across two different component-warranty lengths (2yr motor, 5yr compressor). No further fixes needed before Phase 2.

---

## Phase 2 — Layer 1: registration + lookup

- [ ] `src/layer1/registration.py`: load `fixtures/sales_data_windmere.csv` into a local store (reuse the JSON-file pattern from `archive/groundtruth/src/layer1/report.py` — same approach, proven to work)
- [ ] Function: look up all registered products for a phone number
- [ ] Function: compute warranty status — **reuse `compute_warranty_status()` from `scripts/test_agent_grounding.py` directly**, already validated per product type (washing machine: 2yr motor + 1yr parts; AC: 5yr compressor + 1yr parts) — don't re-derive this, it's proven
- [ ] Test: look up each of the 4 fixture customers, confirm warranty status matches Phase 1's recorded output above

## Phase 3 — Layer 2: the support agent (the flagship)

- [ ] `src/layer2/agent.py`: implement the **multi-turn** loop from `TECHNICAL.md` section 4 / `DESIGN.md` section 4 — one step at a time, wait for a reply, escalate only after self-service was actually tried (cap: 2 attempts). This is a real state machine now, not a single request/response — reuse the retrieval and prompt patterns validated in `scripts/test_agent_grounding.py`, but that script only tested the *first* step; this phase needs to handle the reply and decide next-step-vs-escalate
- [ ] Safety check runs before any model call (already proven in Phase 1)
- [ ] Source routing: coverage question → `terms_windmere.md`, troubleshooting → the matching product manual (`manual_windmere_washing_machine.md` or `manual_windmere_ac.md` — routing by the registration's `product_id`, not by guessing from the complaint text)
- [ ] Escalation logic: no relevant chunk found, OR two self-service attempts both failed, OR safety-flagged → create a ticket with what was already tried
- [ ] New test needed here, not just a rerun of Phase 1's: simulate a customer reply of "still not working" after the first step, confirm it offers the *second* real step from the manual (not a repeat of the first, not a guess) and only escalates after that one also fails

## Phase 4 — Basic ticket view (smallest complete story)

- [ ] `src/layer3b/tickets.py`: store + retrieve escalated tickets, matching the `tickets` table in `TECHNICAL.md`
- [ ] A plain-text or simple CLI view of one ticket with full context (product, customer, complaint, what was tried)
- [ ] **Milestone: this is "basic working prototype" — run the whole thing end to end once here and confirm it before moving to UI.**

## Phase 5 — Customer-facing chat UI

- [ ] Simulated WhatsApp-style web UI (per `DESIGN.md` — real logic, simulated channel)
- [ ] Apply `SKILL.md`'s product-screen design rules (not the landing-page ones): one hierarchy, restrained type/spacing/color, purposeful motion only
- [ ] Registration confirmation message, the complaint conversation, resolution updates

## Phase 6 — Brand dashboard

- [ ] Ticket queue view
- [ ] Product feedback aggregation ("N complaints about X this period")
- [ ] Warranty overview (active/expiring/expired counts)

## Phase 7 — UI polish (Best UI matters here)

- [ ] Landing page, per `SKILL.md`'s landing-page mode (not the product-screen mode) — the pitch, designed
- [ ] Full pass on both UIs against `SKILL.md`'s design checklist

## Phase 8 — Submission

- [ ] Update `README.md`, `PITCH.md`, `TECHNICAL.md` to match what's actually built, per `SKILL.md`'s "keeping the docs honest" rule
- [ ] Record the 3-minute demo video per `TECHNICAL.md` section 8's script
- [ ] Write the submission writeup: problem, build approach, AWS integration, what was learned, AI tools used (disclose Claude Code / whatever was used)
- [ ] Make the repo public
- [ ] Submit before the deadline

---

## Decisions made along the way (add to this as you go)

- Fictional brand ("Windmere") chosen over real brand names for fixture data.
- Real brand names (well-known AC/washing machine/speaker brands) used only as narrative texture in `PITCH.md`, never named explicitly in the doc itself — generic phrasing ("one of India's best-known AC brands") plus a real screenshot with the logo blacked out for the actual demo video. Real enough to be credible, not attached to a specific trademark.
- Ceiling fan fixture dropped and replaced with washing machine + AC — original troubleshooting wasn't hands-only doable. See Phase 1's rework note above.
- Layer 2 redesigned from a one-shot "here's a suggestion" into a real multi-turn loop: one step, wait for a reply, escalate only after self-service was genuinely tried (capped at 2 attempts) — not a detail, this is now the actual spec in `DESIGN.md`/`TECHNICAL.md`.
- One brand, two products (washing machine + AC), full flow first — scope updated from the original "one product" plan since both were explicitly wanted for the demo; more products only if time remains after Phase 6.
