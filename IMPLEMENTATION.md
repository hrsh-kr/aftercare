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

## Phase 2 — Layer 1: registration + lookup (done)

- [x] `src/layer1/registration.py`: loads `fixtures/sales_data_windmere.csv` into memory as `Registration` records (kept simple — a list, not the JSON-file-per-record pattern from the first build, since this is one small CSV, not per-candidate reports; revisit if it needs to grow)
- [x] `lookup_by_phone()`: returns all registered products for a phone number, `[]` for an unknown one — no fabrication, matches the honesty rule
- [x] `compute_warranty_status()` **moved here from the test script** and made canonical — the test script now imports it instead of keeping its own copy, so the date math can't drift out of sync between the two
- [x] Verified: loaded all 4 registrations, looked up a known phone (correct product + serial returned) and an unknown one (empty list, not an error or a guess), warranty status for all 4 matches Phase 1's recorded output exactly

## Phase 3 — Layer 2: the support agent (the flagship) (done)

- [x] `src/layer2/agent.py`: the multi-turn loop — `start()` + `respond()`, a real `Conversation` state machine
- [x] Safety check runs before any model call
- [x] Source routing: coverage question → `terms_windmere.md`, troubleshooting → the matching manual by `product_id` prefix (`WM-` / `AC-`), not by guessing from complaint text
- [x] Escalation logic + `src/layer3b/tickets.py` (built now, not deferred to Phase 4 — escalation needs somewhere real to write to)
- [x] `scripts/test_agent_multiturn.py`: 4 paths tested through the real agent, not just direct model calls

**A second real bug found and fixed, same lesson as Phase 1's warranty math, in a new place:** the first version asked the model to judge "does a further self-service step exist" in free text. It didn't follow the requested format at all (returned its own made-up labels, "NO_FURTHER_STEPS" / "ELEVATE_TO_TECHNICIAN"), and its judgment was also wrong — it said there was no further step for the AC cooling case when the manual clearly has a second one (check the outdoor unit). Root cause: this is a structural fact the document already states outright (the manuals write troubleshooting as explicit numbered lists), not something to ask a model to infer.

**Fix:** added `_parse_numbered_steps()` — parses the numbered list directly from each section with a regex, deterministically, capped at `MAX_ATTEMPTS`. The model's only remaining job is phrasing a step as a friendly message; it no longer decides which step or whether one exists. Re-ran all 4 paths: all correct, including the AC case now correctly offering the outdoor-unit check as attempt 2 before resolving.

**Pattern worth naming, now that it's happened twice:** whenever a manual/terms document already states something as a fact or a structure (a date, a numbered list, a yes/no policy rule), parse or compute it directly — ask the model only to explain or phrase, never to re-derive something the source document already settled. Check any new prompt against this before writing it, not after a bug shows up.

## Phase 4 — Basic ticket view (smallest complete story) (done)

- [x] `src/layer3b/tickets.py` — built during Phase 3, since escalation needed somewhere real to write to. `Ticket.load_all()` already retrieves everything needed for a view.
- [x] `scripts/view_tickets.py` — plain CLI view, every ticket with full context (customer, product, issue, exactly what was already tried, safety flag)
- [x] **Milestone reached: basic working prototype, confirmed end to end.** Registration lookup (Phase 2) → multi-turn agent conversation, real grounding, real escalation logic (Phase 3) → ticket, viewable with full context (Phase 4). Ran the whole chain for real, not simulated at any layer except the WhatsApp channel itself.

## Phase 5 — Customer-facing chat UI (done)

- [x] `src/webapp/app.py` (Flask) + `templates/index.html` + `static/style.css` + `static/chat.js` — simulated chat UI, real logic underneath (calls straight into `src/layer1` and `src/layer2`, nothing mocked at this layer)
- [x] Applied `SKILL.md`'s product-screen rules: one accent color, restrained type/spacing, motion only for new messages arriving
- [x] Registration lookup screen, the complaint conversation, resolution/escalation states — all three visually distinct (white = waiting on agent, green = customer, amber = escalated to a ticket)
- [x] `.claude/launch.json` added so the dev server runs via the Browser pane tool properly

**Tested live in the browser, not just described:** ran the full Priya (washing machine) conversation through the real UI — lookup → complaint → step 1 (level check) → "still broken" → step 2 (load balance, genuinely different) → "fixed it" → resolved, composer correctly disabled. Separately ran Sameer's safety-flagged AC complaint through the real UI — immediate ticket (TBB-0003), correct amber styling, no troubleshooting attempted.

**Two real bugs found and fixed while testing in the browser:**
1. `[hidden]` elements (the composer, before lookup) were showing anyway — my own `.composer { display: flex }` rule was beating the browser's default `[hidden]` behavior in the cascade. Fixed with an explicit `[hidden] { display: none !important; }` rule.
2. The phone-frame had a fixed `height: 720px` that overflowed short viewports. Changed to `height: min(720px, 92vh)`.

**One cosmetic fix, not a bug:** the model occasionally wraps its answer in quote marks despite being asked not to add anything extra. Added `_clean()` in `app.py` to strip them before display, rather than fight the model's phrasing further.

**One red herring, worth recording so it isn't re-investigated later:** the browser automation tool's synthetic "Return" keypress didn't reliably trigger the Enter-to-send handlers, and rapid batched click/type sequences occasionally raced ahead of React-free vanilla-JS state updates, producing a couple of confusing false negatives (an empty input value read immediately after a click). Confirmed the actual code is correct by dispatching a real `KeyboardEvent` via `javascript_tool` and by re-running each step with an explicit value-check in between. Not a product bug — a testing-tool artifact. Don't waste time chasing this again if it resurfaces; verify with a direct value check instead.

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
