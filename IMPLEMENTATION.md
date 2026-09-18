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
- [x] Fixtures authored at `fixtures/`:
  - [x] `manual_windmere_cyclone1200.md` — product manual, fictional brand, real troubleshooting depth
  - [x] `terms_windmere.md` — warranty terms & conditions, same fictional brand
  - [x] `sales_data_windmere.csv` — 4 customers, mixed warranty states (active / partially expired / fully expired)

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

---

## Phase 2 — Layer 1: registration + lookup

- [ ] `src/layer1/registration.py`: load `fixtures/sales_data_windmere.csv` into a local store (reuse the JSON-file pattern from `archive/groundtruth/src/layer1/report.py` — same approach, proven to work)
- [ ] Function: look up all registered products for a phone number
- [ ] Function: compute warranty status (active / expiring within 30 days / expired) from purchase date + warranty rules in `terms_windmere.md` (motor 3yr, parts 1yr — two different expiry dates per product)
- [ ] Test: look up each of the 4 fixture customers, confirm warranty status matches what you'd compute by hand

## Phase 3 — Layer 2: the support agent (the flagship)

- [ ] `src/layer2/agent.py`: implement the loop from `TECHNICAL.md` section 4, using whatever retrieval approach Phase 1 validated
- [ ] Safety check runs before any model call (see Phase 1, item 4)
- [ ] Source routing: coverage question → `terms_windmere.md`, troubleshooting → `manual_windmere_cyclone1200.md`
- [ ] Escalation logic: no relevant chunk found, OR suggestion doesn't resolve it, OR safety-flagged → create a ticket
- [ ] Test against all cases from Phase 1's script, now through the full agent loop, not just direct model calls

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

- Fictional brand ("Windmere") chosen over real brand names for fixture data — see commit history and `PITCH.md` for the real-brand pain examples used in narrative only.
- One brand, one product, full flow first — per explicit scope decision, more products only if time remains after Phase 6.
