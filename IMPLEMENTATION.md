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
  - [x] `manual_aquaspin.md` — drum noise (level + load balance, real DIY steps), foul smell/residue (lint filter, descaling), no-start, safety
  - [x] `manual_arcticair.md` — not cooling (filter clean), foul smell (drain + filter), water dripping, safety
  - [x] `terms_aquaspin.md`, `terms_arcticair.md` — per-brand warranty terms (washing machine: 2yr motor; AC: 5yr compressor; both: 1yr parts)
  - [x] `sales_data.csv` — 4 customers across both products, mixed warranty states

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

- [x] `src/layer1/registration.py`: loads `fixtures/sales_data.csv` into memory as `Registration` records (kept simple — a list, not the JSON-file-per-record pattern from the first build, since this is one small CSV, not per-candidate reports; revisit if it needs to grow)
- [x] `lookup_by_phone()`: returns all registered products for a phone number, `[]` for an unknown one — no fabrication, matches the honesty rule
- [x] `compute_warranty_status()` **moved here from the test script** and made canonical — the test script now imports it instead of keeping its own copy, so the date math can't drift out of sync between the two
- [x] Verified: loaded all 4 registrations, looked up a known phone (correct product + serial returned) and an unknown one (empty list, not an error or a guess), warranty status for all 4 matches Phase 1's recorded output exactly

## Phase 3 — Layer 2: the support agent (the flagship) (done)

- [x] `src/layer2/agent.py`: the multi-turn loop — `start()` + `respond()`, a real `Conversation` state machine
- [x] Safety check runs before any model call
- [x] Source routing: coverage question → the matching brand's terms file (`terms_aquaspin.md` / `terms_arcticair.md`), troubleshooting → the matching manual, both by `product_id` prefix (`WM-` / `AC-`), not by guessing from complaint text
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
- [x] **Fixed a real product-logic inconsistency, caught after Phase 5's first pass:** the lookup screen asked the customer to type their own phone number, which makes no sense for a WhatsApp simulation — a real integration already knows the sender from the incoming message, nothing is ever typed. Replaced the phone-number text field with an explicit "pick who you're simulating" selector (`/api/customers`, honestly labeled as a demo stand-in, not pretending to be the real mechanism).
- [x] **Naming correction:** "Windmere" (the earlier parent-brand name) was never a name the user gave — it was invented mid-build and got flagged as such. Removed entirely, everywhere (fixtures, code, templates, docs). AC line is "ArcticAir," washing-machine line is "AquaSpin" — now two fully independent brands, not one parent with two product lines. Each has its own manual, its own terms file (`terms_arcticair.md` / `terms_aquaspin.md`, split out of the old combined `terms_windmere.md`), and its own chat header, set dynamically per customer (`brand_for()` in `src/layer2/agent.py`, returned by `/api/lookup`, applied client-side in `chat.js`). The dashboard is no longer branded to one company — it's Aftercare's own cross-brand ops view (`Aftercare — Ops Dashboard`), which fits the actual pitch better: Aftercare is the platform, brands are its clients. Fixture files renamed accordingly (`manual_arcticair.md`, `manual_aquaspin.md`, `sales_data.csv`); confirmed both brands render correctly (distinct header text, correct manual/terms retrieval) through a live test.
- [x] `.claude/launch.json` added so the dev server runs via the Browser pane tool properly

**Tested live in the browser, not just described:** ran the full Priya (washing machine) conversation through the real UI — lookup → complaint → step 1 (level check) → "still broken" → step 2 (load balance, genuinely different) → "fixed it" → resolved, composer correctly disabled. Separately ran Sameer's safety-flagged AC complaint through the real UI — immediate ticket (TBB-0003), correct amber styling, no troubleshooting attempted.

**Two real bugs found and fixed while testing in the browser:**
1. `[hidden]` elements (the composer, before lookup) were showing anyway — my own `.composer { display: flex }` rule was beating the browser's default `[hidden]` behavior in the cascade. Fixed with an explicit `[hidden] { display: none !important; }` rule.
2. The phone-frame had a fixed `height: 720px` that overflowed short viewports. Changed to `height: min(720px, 92vh)`.

**One cosmetic fix, not a bug:** the model occasionally wraps its answer in quote marks despite being asked not to add anything extra. Added `_clean()` in `app.py` to strip them before display, rather than fight the model's phrasing further.

**One red herring, worth recording so it isn't re-investigated later:** the browser automation tool's synthetic "Return" keypress didn't reliably trigger the Enter-to-send handlers, and rapid batched click/type sequences occasionally raced ahead of React-free vanilla-JS state updates, producing a couple of confusing false negatives (an empty input value read immediately after a click). Confirmed the actual code is correct by dispatching a real `KeyboardEvent` via `javascript_tool` and by re-running each step with an explicit value-check in between. Not a product bug — a testing-tool artifact. Don't waste time chasing this again if it resurfaces; verify with a direct value check instead.

## Phase 6 — Brand dashboard (done)

- [x] Ticket queue view (`/dashboard`, `templates/dashboard.html`, `/api/dashboard`) — every ticket, full context, safety-flagged ones visually distinct
- [x] Product feedback aggregation — real counts grouped by product from actual ticket data, no placeholder numbers
- [x] Warranty overview — active/expired counts across all registered items, computed from Phase 2's real data, not invented

**Verified live:** 4 registered products, 3 open tickets (1 washing-machine smell after 2 real attempts, 2 AC safety escalations correctly badged), 4 warranty items active — all numbers traced back to real fixture data and real conversations run earlier in this session, nothing hand-typed into the dashboard itself.

**Superseded by Phase 6.5 below** — this was a single dashboard aggregating all brands. Corrected once it became clear that's not how Aftercare actually works: Aftercare is a service provider, each brand it serves gets its own independent dashboard.

## Phase 6.5 — Multi-brand correction: per-brand dashboards + Cedar authorization (done)

**Why:** caught a real architecture mistake — Aftercare is a platform serving multiple brands, each brand's WhatsApp support and dashboard should be independent, not one shared cross-brand view. Also the point where the AWS OSS stack requirement (`Strands, Cedar, SAM Local, PartyRock, OpenSearch — no account, no card, no bill`) got checked against what was actually being used, which at that point was Strands alone.

- [x] **Cedar CLI, the real thing, not the PyPI package.** `pip install cedar-policy` resolves to an empty 0.0.1 placeholder with no actual bindings — checked by importing it and inspecting `dir()`, confirmed empty. Used the real open-source Cedar CLI instead: prebuilt binary from `cedar-policy/cedar`'s GitHub releases (v4.13.0), downloaded via `scripts/install_cedar_cli.sh` to `tools/cedar/cedar` (gitignored — a 15MB platform binary, not vendored).
- [x] `policies/dashboard.cedar` — one real policy: `permit(principal, action == Action::"viewDashboard", resource) when { principal.brand == resource.brand };`. Generic across brands, not one hardcoded permit per brand.
- [x] `src/authz/cedar_authz.py` — shells out to the real Cedar CLI (`subprocess`), builds entities for both brands, returns the actual ALLOW/DENY decision. Fails closed (raises `CedarUnavailable`, which the route turns into a 503) if the binary is missing, rather than silently granting access — same honesty rule as the rest of the system.
- [x] `src/layer3b/tickets.py`: added `product_id` to `Ticket` (was missing — tickets had no way to know which brand they belonged to) so dashboards can filter by brand.
- [x] `src/layer2/agent.py`: added `BRAND_BY_PREFIX`, `BRAND_SLUGS`, `brand_for()`, `TERMS_BY_PREFIX` (replacing the old single `TERMS_PATH`) — coverage questions now route to the correct brand's terms file.
- [x] Backend (`src/webapp/app.py`): `/dashboard` is now a brand-staff login picker (mirrors the customer picker's honesty pattern — a real system would already know who's logged in). `/dashboard/<brand>` renders that brand's dashboard. `/api/dashboard/<brand>` reads the claimed `X-Staff-Brand` session header, asks Cedar whether that principal may view this brand's resource, and only then filters registrations/tickets to that brand. A 403 with a plain-language reason on denial, not a silent empty result.
- [x] Frontend: `dashboard_login.html` (new), `dashboard.html` rebuilt with a real "access denied" state, `dashboard.js` rewritten to send the staff-brand header and handle both the allow and deny paths honestly.

**Tested live, the actual point of the exercise:** logged in as ArcticAir staff, viewed `/dashboard/arcticair` — correct data. Navigated directly to `/dashboard/aquaspin` while still logged in as ArcticAir — **Cedar denied it**, real 403, real "Access denied" panel, not a designed-away edge case. Logged in as AquaSpin staff properly — correct, isolated data. Ran a real safety-flagged AC complaint (Sameer Khan, burning smell) end to end — ticket TBB-0001 appeared on ArcticAir's dashboard, confirmed absent from AquaSpin's. Full tenant isolation, enforced by Cedar's actual evaluator, not a Python `if`.

**Also fixed while in here:** same-letter brand initials — "ArcticAir" and "AquaSpin" both start with "A", so single-letter avatar badges (`brand-dot`, customer picker, login picker) were indistinguishable. Changed to two-letter slices (`Ar` / `Aq`) everywhere a brand initial is shown.

**Design pass done at the same time, not deferred:** rebuilt both UIs' visual language rather than fixing the plumbing now and redesigning later — refined the color tokens (deeper accent, soft/strong variants, a real shadow scale), added the WhatsApp-style dotted chat background, avatar chips on the customer/brand pickers, a gradient chat header, bar-chart-style product feedback rows, and a left-accent-bar ticket card style (amber for safety). Still the restrained "product screen" mode from `SKILL.md`, not the landing page's drama — one accent, one hierarchy per screen, motion only on state change.

**Not done as part of this phase, flagged honestly:** PartyRock needs a personal Amazon.com sign-in, which isn't something that can be done without the user directly — proposed either the user builds a small playground themselves (a few minutes, exact spec would be handed over) or it's noted as a deliberate skip in the submission writeup. Awaiting a call on this, not blocking anything else.

## Phase 7 — UI polish (Best UI matters here)

- [x] Full visual pass on the chat UI and both dashboard screens (folded into Phase 6.5 above, since redoing the same templates twice would've been wasted work)
- [ ] Landing page, per `SKILL.md`'s landing-page mode (not the product-screen mode) — the pitch, designed

## Phase 7.5 — SAM Local (done)

- [x] Extracted `src/webapp/api_core.py` — the actual route logic (lookup, start/respond conversation, brand dashboard), framework-agnostic. Both adapters call into this; neither has its own copy.
- [x] `src/webapp/app.py` slimmed to a thin Flask adapter over `api_core` (no behavior change, verified live before/after)
- [x] `template.yaml` + `src/lambda_handlers.py` — Lambda-proxy adapters over the same `api_core`, `Runtime: python3.12`, `Architectures: [arm64]`
- [x] `sam build --use-container` (needed — host is Python 3.14/macOS, Lambda is 3.12/Linux; container build gets correct native wheels) + `sam local start-api`, genuinely running, not an unused template

**Two real, non-obvious problems found by actually running it, not by inspection — both fixed for real reasons, not worked around:**

1. **Cedar's CLI binary is platform-specific.** The macOS binary at `tools/cedar/cedar` can't execute inside the Lambda container's Amazon Linux runtime (`exec format error`). Fixed by downloading a second binary, `tools/cedar-lambda/cedar` (linux/aarch64), bundled into the Lambda package and pointed to via a `CEDAR_BIN` env var the SAM template sets (`cedar_authz.py` now reads `CEDAR_BIN` instead of a hardcoded path). `scripts/install_cedar_cli.sh` fetches both. Verified: the dashboard endpoint's Cedar ALLOW/DENY through `sam local start-api` matched the Flask/host-binary results exactly, cross-brand denial included.
2. **`/var/task` (the Lambda code mount) is read-only.** `_save_conversation()` tried to `mkdir` a `data/conversations/` folder next to the code and crashed with `OSError: [Errno 30] Read-only file system`. This is real Lambda behavior, not a SAM Local quirk — only `/tmp` is writable. Fixed by making the data directory configurable (`AFTERCARE_DATA_DIR` env var, read by both `tickets.py` and `api_core.py`; defaults to the repo's `data/` for Flask, set to `/tmp/aftercare-data` for Lambda).
3. **Found while fixing #2, more fundamental:** `/api/start` and `/api/respond` were two separate Lambda functions, each its own process with its own `/tmp` — an in-memory-turned-file-backed conversation store still never actually shared state between them, every single call, not just on a cold start. Merged them into one `ConversationFunction` (`src/lambda_handlers.py`'s `conversation()`, dispatching on `event["path"]`; `template.yaml` binds both `/api/start` and `/api/respond` to it) and ran `sam local start-api --warm-containers LAZY` so that one function's container — and its `/tmp` — actually persists across the start→respond turns of a conversation. **Documented honestly, not oversold:** this works because SAM Local's warm container happens to stay up for the session; real AWS Lambda never guarantees warm reuse across a genuine production conversation's turns (which could be minutes or hours apart), so a real deployment would back this with DynamoDB instead — same "plain Python stands in for the real AWS service" pattern already named in `TECHNICAL.md` for the rest of this build.

**Verified live, full chain, through `sam local start-api`:** `/api/customers` (real data) → `/api/lookup` → `/api/start` (real Ollama call via `host.docker.internal`, real manual grounding) → `/api/respond` twice (step 2 offered, then resolved) → `/api/dashboard/arcticair` as arcticair staff (correct data) → `/api/dashboard/aquaspin` as arcticair staff (real Cedar 403). Every one of these is the same code path Flask runs, exercised through an actual emulated Lambda + API Gateway, not asserted to work.

**Which server is which:** Flask (`src/webapp/app.py`, port 5001) is what the live demo runs — faster iteration, serves the HTML/JS too. SAM Local (`sam build --use-container && sam local start-api --warm-containers LAZY`, port 3000) is the serverless-readiness proof — JSON API only, no templates. Both real, different jobs, same `api_core.py` underneath.

## Phase 7.6 — OpenSearch-backed retrieval (done)

- [x] Local single-node OpenSearch container (`scripts/start_opensearch.sh` — security plugin disabled, local dev only, mirrors the Ollama/Cedar setup-script pattern)
- [x] `src/layer1/opensearch_retrieval.py` — indexes every manual/terms section (all brands, once per process) into a single `aftercare-sections` index, `{path, heading, body}`. Retrieval is a `bool` query: `filter` on the exact source path (same document boundary `keyword_retrieve()` always respected — never cross-brand), `must` a `multi_match` (`heading^2`, `body`) for real BM25 ranking instead of hand-scored word overlap.
- [x] `retrieve(query, doc_path)` tries OpenSearch first, falls back to the original `keyword_retrieve()` if unreachable — and returns which one actually answered (`"opensearch"` / `"keyword_fallback"`) rather than pretending OpenSearch always ran. `Conversation` gained a `retrieval_method` field to carry this honestly through the rest of the system.
- [x] `src/layer2/agent.py`'s `start()` now calls `opensearch_retrieval.retrieve()` instead of `load_sections()` + `keyword_retrieve()` directly

**Verified live, both paths:** ran the same three cases Phase 1 validated (washing machine drum noise, washing machine foul smell, AC not cooling) directly against `opensearch_retrieval.retrieve()` — all three correctly retrieved the right section, `method == "opensearch"` confirmed each time, not a silent fallback. Then pointed `OPENSEARCH_HOST` at a nonexistent port and re-ran the drum-noise case — correctly fell back, `method == "keyword_fallback"`, same correct section returned. Then re-ran the full Phase 3 multi-turn test suite (`scripts/test_agent_multiturn.py`) against the real OpenSearch-backed path end to end — all 4 paths still correct (resolved-on-step-1, resolved-on-step-2, escalate-after-2-attempts, safety-immediate-escalation). No regression from the Phase 1-validated behavior; the scoring mechanism changed, the grounding claim didn't.

## Phase 7.9 — Deep audit, simplification, `FLOW.md` (done)

**Why:** everything through Phase 7.6 was built fast, across several large architecture changes in quick succession (the Windmere naming fix, the multi-brand split, SAM Local, OpenSearch). That's exactly the condition under which real bugs and doc drift hide — asked for explicitly: read everything, fix what's wrong, simplify what's duplicated, write down how it actually works.

**Real bugs found and fixed, not stylistic nitpicks:**
- [x] **Stored XSS in the dashboard.** `dashboard.js` rendered `issue_summary` and `attempts_tried` — both containing raw customer-typed complaint text — via `innerHTML` with no escaping. A complaint like `<img src=x onerror=...>` would execute in the brand-staff viewer's browser. Added `escapeHtml()`, applied to every ticket-derived field rendered that way. Verified live: submitted exactly that payload as a complaint, confirmed it renders as literal text on the dashboard, no console errors, nothing executes.
- [x] **Dead-end composer on error.** `chat.js`'s `sendMessage()` disabled the composer before the fetch and never re-enabled it if the response had an `error` field — a failed call left the customer permanently unable to type again. Also, `conversationId`/`awaitingFirstComplaint` were updated even when `/api/start` failed, so a retry would've hit `/api/respond` with an invalid id. Fixed both: re-enable on error, only advance state on success.
- [x] **`retrieval_method` silently lost on every reload.** `api_core._load_conversation()` reconstructed `Conversation` from its saved JSON but never restored `retrieval_method` — since the dataclass field has a default, this didn't crash, it just quietly reset to `""` after the very first save/load round trip (i.e. on every `respond()` call). Fixed; verified the field now survives a start → respond → start → respond round trip intact.
- [x] **Cedar's allow/deny check was a substring match on stdout** (`"ALLOW" in result.stdout`) rather than the CLI's actual exit code (confirmed empirically: 0 = allow, non-zero = deny or error). Fragile in theory — an error message containing the word "ALLOW" would've misread as a grant. Switched to `result.returncode == 0`.
- [x] **`compute_warranty_status()` silently misclassified unknown product prefixes** as AC/compressor (`if product_id.startswith("WM-"): ... else: compressor, 5`) instead of failing the way every other prefix lookup in the codebase does. Not a live bug today (only two prefixes exist), but inconsistent with the fail-closed pattern used everywhere else. Fixed via the new catalog module below.

**Simplification — one real source of truth for brand/product routing:** `MANUAL_BY_PREFIX`/`TERMS_BY_PREFIX`/`BRAND_BY_PREFIX` were defined once in `agent.py`; `cedar_authz.py` had its own separate hardcoded `KNOWN_BRANDS` list; `opensearch_retrieval.py` had its own separate hardcoded `ALL_DOCS` list. Three copies of the same underlying fact, exactly the kind of thing that quietly drifts when a brand gets added or renamed. Consolidated into `src/layer1/catalog.py` — `agent.py`, `cedar_authz.py`, `opensearch_retrieval.py`, and `registration.py` all import from it now. A third brand is a one-file change.

**Smaller consistency fixes:** `scripts/test_agent_multiturn.py` was missing the `sys.path` setup `test_agent_grounding.py` has, so it silently required an undocumented `PYTHONPATH=.` to run directly — added the same setup, now runs the same way as the other test script. Removed `src/authz/__init__.py` (no other `src/` subpackage has one — Python's implicit namespace packages make it unnecessary; kept for consistency, not because it was broken). Reordered `agent.py`'s imports (an `os.environ.get()` call had been sitting between two import statements). Fixed a couple of stale docstrings (`tickets.py` referencing "Phase 6" after the dashboard became per-brand in Phase 6.5; `retrieval.py` describing itself as what `agent.py` calls directly, when it's now `opensearch_retrieval.py`'s fallback).

**Verified nothing regressed:** re-ran both test scripts and the live Flask flow after every fix above — all still correct (Phase 1's grounding cases, Phase 3's four multi-turn paths, Cedar's allow/deny in both directions, OpenSearch retrieval and its fallback).

**New doc:** [`FLOW.md`](FLOW.md) — the as-built reference. Request-by-request walkthrough of both the customer and brand-staff sides, the agent loop's exact steps, the catalog consolidation, exactly where each AWS OSS tool lives in the code and how to run it, the real data model (replacing `TECHNICAL.md`'s stale pre-build sketch), what's real vs. simulated, run instructions, and an honest "known limitations" section. `README.md`, `DESIGN.md`, and `TECHNICAL.md` updated to match reality and point to it — `TECHNICAL.md`'s data-model and API-sketch sections were pure pre-build fiction (a `chunk_id`/`brand_id` schema and `/register`/`/message` routes that were never built) and now say so plainly instead of leaving it implied. `PITCH.md`'s opening also still described the original ceiling-fan fixture ("A fan starts grinding. A geyser stops heating") dropped back in Phase 1 — fixed to match what's actually demoed (washing machine, AC).

## Phase 7.10 — Two-pane WhatsApp demo view (done)

**Why:** the chat UI was one phone frame with the "agent" replying inline, in the same window as the customer. That's not what actually happens — each brand runs its own WhatsApp line, and the point being demonstrated is a real back-and-forth between two separate parties, not one window narrating both sides. Rebuilt the customer-facing screen (`/`) as two mirrored phone frames: the customer's WhatsApp on the right, that brand's WhatsApp Business inbox on the left, both rendering the same underlying conversation from their own side.

- [x] `index.html` restructured: a single centered "pick who you're simulating" phone frame, then (once picked) a `.split-view` of two phone frames — `messages` (customer) and `messages-brand` (brand), each with its own header, brand pane read-only with a note that Aftercare's agent is replying automatically, no human typing.
- [x] `chat.js` rewritten around `deliver(text, from, modifier)`: a message is "mine" on the sending pane, appended instantly, then "theirs" on the receiving pane after a ~350ms staged delay — sells "sent, then arrived on the other phone" instead of both panes updating in the same tick. A typing indicator (three bouncing dots) shows on the customer's pane while the real Ollama call is in flight.
- [x] Bubble CSS classes generalized from `agent`/`customer` to `mine`/`theirs`, since which one applies now depends on which pane is rendering, not who authored the message. `ticket`/`system` kept as color modifiers layered on top of the alignment class.
- [x] An "Open dashboard →" link appears on the brand pane once a ticket is escalated, pointing at that brand's `/dashboard/<slug>` — a deliberate separate click into a separate page, not merged into the chat view, matching the request not to couple the two into a single page.
- [x] Kept the same backend contract throughout (`/api/lookup`, `/api/start`, `/api/respond`) — this was a frontend rebuild only, no route or agent logic changed.

**Verified live:** picked a customer, confirmed both panes repaint to that brand correctly (initials, name); ran a full AC troubleshooting conversation through to escalation via direct JS invocation (`window.sendMessage()` — the `computer` tool's synthetic click/type on this form raced ahead of the just-updated DOM again, the same documented artifact from Phase 5; verified the real logic directly instead of chasing it, per that existing note) — confirmed every message appears as `mine` on its sender's pane and `theirs` on the receiver's pane, in both directions, throughout a 4-turn conversation ending in a ticket; confirmed the dashboard link appears only on escalation and correctly opens that exact brand's dashboard, which then correctly shows the same ticket. Re-ran both automated test scripts (`test_agent_grounding.py`, `test_agent_multiturn.py`) afterward — untouched, still passing, since none of this touched agent logic.

## Phase 8 — Submission

- [x] Update `README.md`, `PITCH.md`, `TECHNICAL.md` to match what's actually built, per `SKILL.md`'s "keeping the docs honest" rule — done as part of Phase 7.9's audit
- [ ] Record the 3-minute demo video per `TECHNICAL.md` section 8's script
- [ ] Write the submission writeup: problem, build approach, AWS integration, what was learned, AI tools used (disclose Claude Code / whatever was used)
- [ ] Make the repo public
- [ ] Submit before the deadline

---

## Decisions made along the way (add to this as you go)

- Fictional brand names chosen over real brand names for fixture data — originally one invented parent brand ("Windmere") with two product lines, later corrected to two fully independent brands (ArcticAir, AquaSpin) once it turned out the parent name had never actually been requested. See Phase 5's naming-correction note.
- Real brand names (well-known AC/washing machine/speaker brands) used only as narrative texture in `PITCH.md`, never named explicitly in the doc itself — generic phrasing ("one of India's best-known AC brands") plus a real screenshot with the logo blacked out for the actual demo video. Real enough to be credible, not attached to a specific trademark.
- Ceiling fan fixture dropped and replaced with washing machine + AC — original troubleshooting wasn't hands-only doable. See Phase 1's rework note above.
- Layer 2 redesigned from a one-shot "here's a suggestion" into a real multi-turn loop: one step, wait for a reply, escalate only after self-service was genuinely tried (capped at 2 attempts) — not a detail, this is now the actual spec in `DESIGN.md`/`TECHNICAL.md`.
- Two brands, one product each (AquaSpin washing machine, ArcticAir AC), full flow first — scope updated from the original "one product" plan since both were explicitly wanted for the demo; more brands/products only if time remains after Phase 6.
- Aftercare corrected from "one dashboard aggregating every brand" to "one backend, independent dashboards per brand" — this is the actual product shape (a service provider serving several brand clients), not a detail. See Phase 6.5.
- Cedar's real integration is the CLI binary, not the `cedar-policy` PyPI package (confirmed empty). Vendoring the binary in git was rejected in favor of an install script (`scripts/install_cedar_cli.sh`) — it's a 15MB platform-specific artifact, a download step is more honest than committing a Mac ARM64 binary and pretending it's portable.
