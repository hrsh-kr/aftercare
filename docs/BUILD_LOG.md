# Build log

> **Historical.** The chronological record of how Aftercare was built, phase by phase, including approaches later
> replaced (a Flask server, keyword and file fallbacks, a scripted demo, a `layer1/layer2/layer3b` layout, a
> checklist that pointed at documents since deleted). Names, paths and counts in early phases are from their time.
> References to `CONTEXT.md`, `TARGET.md` and `PLAN.md` are to internal working notes that are not part of this repository.
> **The current design is in [`ARCHITECTURE.md`](ARCHITECTURE.md).**

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

**Decision, going into Layer 1:** the registration/warranty lookup (`src/domain/registration.py`, Phase 2 below) must compute status in Python from the start — this isn't a detail to get right later, it's now a validated requirement.

**Reworked once, for realism (see decision log):** the ceiling fan fixture was dropped — its troubleshooting steps (check blade screws, check down-rod seating) require a ladder and a screwdriver, not something a customer does over chat. Rebuilt around washing machine (drum noise, foul smell) and AC (not cooling, foul smell), researched against real common-fault patterns — both are genuinely hands-only fixable. Re-ran the full test suite against the new fixtures and the new one-step-at-a-time prompt design (see Layer 2's updated spec in `DESIGN.md`/`TECHNICAL.md`): all 5 cases correct on the first run — washing machine drum noise and AC cooling both correctly retrieved from the right manual (not confused with each other despite both mentioning "filter"), each gave exactly one doable step and asked for a reply rather than dumping the whole section, warranty math correct across two different component-warranty lengths (2yr motor, 5yr compressor). No further fixes needed before Phase 2.

---

## Phase 2 — Layer 1: registration + lookup (done)

- [x] `src/domain/registration.py`: loads `fixtures/sales_data.csv` into memory as `Registration` records (kept simple — a list, not the JSON-file-per-record pattern from the first build, since this is one small CSV, not per-candidate reports; revisit if it needs to grow)
- [x] `lookup_by_phone()`: returns all registered products for a phone number, `[]` for an unknown one — no fabrication, matches the honesty rule
- [x] `compute_warranty_status()` **moved here from the test script** and made canonical — the test script now imports it instead of keeping its own copy, so the date math can't drift out of sync between the two
- [x] Verified: loaded all 4 registrations, looked up a known phone (correct product + serial returned) and an unknown one (empty list, not an error or a guess), warranty status for all 4 matches Phase 1's recorded output exactly

## Phase 3 — Layer 2: the support agent (the flagship) (done)

- [x] `src/agent/agent.py`: the multi-turn loop — `start()` + `respond()`, a real `Conversation` state machine
- [x] Safety check runs before any model call
- [x] Source routing: coverage question → the matching brand's terms file (`terms_aquaspin.md` / `terms_arcticair.md`), troubleshooting → the matching manual, both by `product_id` prefix (`WM-` / `AC-`), not by guessing from complaint text
- [x] Escalation logic + `src/records/tickets.py` (built now, not deferred to Phase 4 — escalation needs somewhere real to write to)
- [x] `scripts/test_agent_multiturn.py`: 4 paths tested through the real agent, not just direct model calls

**A second real bug found and fixed, same lesson as Phase 1's warranty math, in a new place:** the first version asked the model to judge "does a further self-service step exist" in free text. It didn't follow the requested format at all (returned its own made-up labels, "NO_FURTHER_STEPS" / "ELEVATE_TO_TECHNICIAN"), and its judgment was also wrong — it said there was no further step for the AC cooling case when the manual clearly has a second one (check the outdoor unit). Root cause: this is a structural fact the document already states outright (the manuals write troubleshooting as explicit numbered lists), not something to ask a model to infer.

**Fix:** added `_parse_numbered_steps()` — parses the numbered list directly from each section with a regex, deterministically, capped at `MAX_ATTEMPTS`. The model's only remaining job is phrasing a step as a friendly message; it no longer decides which step or whether one exists. Re-ran all 4 paths: all correct, including the AC case now correctly offering the outdoor-unit check as attempt 2 before resolving.

**Pattern worth naming, now that it's happened twice:** whenever a manual/terms document already states something as a fact or a structure (a date, a numbered list, a yes/no policy rule), parse or compute it directly — ask the model only to explain or phrase, never to re-derive something the source document already settled. Check any new prompt against this before writing it, not after a bug shows up.

## Phase 4 — Basic ticket view (smallest complete story) (done)

- [x] `src/records/tickets.py` — built during Phase 3, since escalation needed somewhere real to write to. `Ticket.load_all()` already retrieves everything needed for a view.
- [x] `scripts/view_tickets.py` — plain CLI view, every ticket with full context (customer, product, issue, exactly what was already tried, safety flag)
- [x] **Milestone reached: basic working prototype, confirmed end to end.** Registration lookup (Phase 2) → multi-turn agent conversation, real grounding, real escalation logic (Phase 3) → ticket, viewable with full context (Phase 4). Ran the whole chain for real, not simulated at any layer except the WhatsApp channel itself.

## Phase 5 — Customer-facing chat UI (done)

- [x] `src/webapp/app.py` (Flask) + `templates/index.html` + `static/style.css` + `static/chat.js` — simulated chat UI, real logic underneath (calls straight into `src/domain` and `src/agent`, nothing mocked at this layer)
- [x] Applied `SKILL.md`'s product-screen rules: one accent color, restrained type/spacing, motion only for new messages arriving
- [x] Registration lookup screen, the complaint conversation, resolution/escalation states — all three visually distinct (white = waiting on agent, green = customer, amber = escalated to a ticket)
- [x] **Fixed a real product-logic inconsistency, caught after Phase 5's first pass:** the lookup screen asked the customer to type their own phone number, which makes no sense for a WhatsApp simulation — a real integration already knows the sender from the incoming message, nothing is ever typed. Replaced the phone-number text field with an explicit "pick who you're simulating" selector (`/api/customers`, honestly labeled as a demo stand-in, not pretending to be the real mechanism).
- [x] **Naming correction:** "Windmere" (the earlier parent-brand name) was never a name the user gave — it was invented mid-build and got flagged as such. Removed entirely, everywhere (fixtures, code, templates, docs). AC line is "ArcticAir," washing-machine line is "AquaSpin" — now two fully independent brands, not one parent with two product lines. Each has its own manual, its own terms file (`terms_arcticair.md` / `terms_aquaspin.md`, split out of the old combined `terms_windmere.md`), and its own chat header, set dynamically per customer (`brand_for()` in `src/agent/agent.py`, returned by `/api/lookup`, applied client-side in `chat.js`). The dashboard is no longer branded to one company — it's Aftercare's own cross-brand ops view (`Aftercare — Ops Dashboard`), which fits the actual pitch better: Aftercare is the platform, brands are its clients. Fixture files renamed accordingly (`manual_arcticair.md`, `manual_aquaspin.md`, `sales_data.csv`); confirmed both brands render correctly (distinct header text, correct manual/terms retrieval) through a live test.
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
- [x] `src/records/tickets.py`: added `product_id` to `Ticket` (was missing — tickets had no way to know which brand they belonged to) so dashboards can filter by brand.
- [x] `src/agent/agent.py`: added `BRAND_BY_PREFIX`, `BRAND_SLUGS`, `brand_for()`, `TERMS_BY_PREFIX` (replacing the old single `TERMS_PATH`) — coverage questions now route to the correct brand's terms file.
- [x] Backend (`src/webapp/app.py`): `/dashboard` is now a brand-staff login picker (mirrors the customer picker's honesty pattern — a real system would already know who's logged in). `/dashboard/<brand>` renders that brand's dashboard. `/api/dashboard/<brand>` reads the claimed `X-Staff-Brand` session header, asks Cedar whether that principal may view this brand's resource, and only then filters registrations/tickets to that brand. A 403 with a plain-language reason on denial, not a silent empty result.
- [x] Frontend: `dashboard_login.html` (new), `dashboard.html` rebuilt with a real "access denied" state, `dashboard.js` rewritten to send the staff-brand header and handle both the allow and deny paths honestly.

**Tested live, the actual point of the exercise:** logged in as ArcticAir staff, viewed `/dashboard/arcticair` — correct data. Navigated directly to `/dashboard/aquaspin` while still logged in as ArcticAir — **Cedar denied it**, real 403, real "Access denied" panel, not a designed-away edge case. Logged in as AquaSpin staff properly — correct, isolated data. Ran a real safety-flagged AC complaint (Sameer Khan, burning smell) end to end — ticket TBB-0001 appeared on ArcticAir's dashboard, confirmed absent from AquaSpin's. Full tenant isolation, enforced by Cedar's actual evaluator, not a Python `if`.

**Also fixed while in here:** same-letter brand initials — "ArcticAir" and "AquaSpin" both start with "A", so single-letter avatar badges (`brand-dot`, customer picker, login picker) were indistinguishable. Changed to two-letter slices (`Ar` / `Aq`) everywhere a brand initial is shown.

**Design pass done at the same time, not deferred:** rebuilt both UIs' visual language rather than fixing the plumbing now and redesigning later — refined the color tokens (deeper accent, soft/strong variants, a real shadow scale), added the WhatsApp-style dotted chat background, avatar chips on the customer/brand pickers, a gradient chat header, bar-chart-style product feedback rows, and a left-accent-bar ticket card style (amber for safety). Still the restrained "product screen" mode from `SKILL.md`, not the landing page's drama — one accent, one hierarchy per screen, motion only on state change.

**Not done as part of this phase, flagged honestly:** PartyRock needs a personal Amazon.com sign-in, which isn't something that can be done without the user directly — proposed either the user builds a small playground themselves (a few minutes, exact spec would be handed over) or it's noted as a deliberate skip in the submission writeup. Awaiting a call on this, not blocking anything else.

## Phase 7 — UI polish (Best UI matters here)

- [x] Full visual pass on the chat UI and both dashboard screens (folded into Phase 6.5 above, since redoing the same templates twice would've been wasted work)
- [x] Landing page (`/`) — full narrative pitch, Apple marketing register. Hero with big expressive type + subtle grid + radial glow, pain section with the real triage-chat illustration, stats row with scroll-triggered number counters, 6-card how-it-works section, before/after compare grid, AWS stack section (all four tools), CTA. `landing.css` (separate from product-screen CSS per SKILL.md's two-modes rule) + `landing.js` (Intersection Observer reveals, counter animations, passive scroll listener, pain-chat blink). Chat UI moved from `/` to `/demo`, back-to-landing pill on both the demo screen and dashboard login.

**Additional polish done at this stage:**
- Cedar authorization now shown as a green badge ("✓ Authorized by Cedar") on the dashboard session line — the real authorization is visible, not just implied in prose.
- Ticket timestamps (`created_at`) now rendered on every ticket card in the dashboard — the data was always stored, just not surfaced in the UI.

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
- [x] `src/domain/opensearch_retrieval.py` — indexes every manual/terms section (all brands, once per process) into a single `aftercare-sections` index, `{path, heading, body}`. Retrieval is a `bool` query: `filter` on the exact source path (same document boundary `keyword_retrieve()` always respected — never cross-brand), `must` a `multi_match` (`heading^2`, `body`) for real BM25 ranking instead of hand-scored word overlap.
- [x] `retrieve(query, doc_path)` tries OpenSearch first, falls back to the original `keyword_retrieve()` if unreachable — and returns which one actually answered (`"opensearch"` / `"keyword_fallback"`) rather than pretending OpenSearch always ran. `Conversation` gained a `retrieval_method` field to carry this honestly through the rest of the system.
- [x] `src/agent/agent.py`'s `start()` now calls `opensearch_retrieval.retrieve()` instead of `load_sections()` + `keyword_retrieve()` directly

**Verified live, both paths:** ran the same three cases Phase 1 validated (washing machine drum noise, washing machine foul smell, AC not cooling) directly against `opensearch_retrieval.retrieve()` — all three correctly retrieved the right section, `method == "opensearch"` confirmed each time, not a silent fallback. Then pointed `OPENSEARCH_HOST` at a nonexistent port and re-ran the drum-noise case — correctly fell back, `method == "keyword_fallback"`, same correct section returned. Then re-ran the full Phase 3 multi-turn test suite (`scripts/test_agent_multiturn.py`) against the real OpenSearch-backed path end to end — all 4 paths still correct (resolved-on-step-1, resolved-on-step-2, escalate-after-2-attempts, safety-immediate-escalation). No regression from the Phase 1-validated behavior; the scoring mechanism changed, the grounding claim didn't.

## Phase 7.9 — Deep audit, simplification, `FLOW.md` (done)

**Why:** everything through Phase 7.6 was built fast, across several large architecture changes in quick succession (the Windmere naming fix, the multi-brand split, SAM Local, OpenSearch). That's exactly the condition under which real bugs and doc drift hide — asked for explicitly: read everything, fix what's wrong, simplify what's duplicated, write down how it actually works.

**Real bugs found and fixed, not stylistic nitpicks:**
- [x] **Stored XSS in the dashboard.** `dashboard.js` rendered `issue_summary` and `attempts_tried` — both containing raw customer-typed complaint text — via `innerHTML` with no escaping. A complaint like `<img src=x onerror=...>` would execute in the brand-staff viewer's browser. Added `escapeHtml()`, applied to every ticket-derived field rendered that way. Verified live: submitted exactly that payload as a complaint, confirmed it renders as literal text on the dashboard, no console errors, nothing executes.
- [x] **Dead-end composer on error.** `chat.js`'s `sendMessage()` disabled the composer before the fetch and never re-enabled it if the response had an `error` field — a failed call left the customer permanently unable to type again. Also, `conversationId`/`awaitingFirstComplaint` were updated even when `/api/start` failed, so a retry would've hit `/api/respond` with an invalid id. Fixed both: re-enable on error, only advance state on success.
- [x] **`retrieval_method` silently lost on every reload.** `api_core._load_conversation()` reconstructed `Conversation` from its saved JSON but never restored `retrieval_method` — since the dataclass field has a default, this didn't crash, it just quietly reset to `""` after the very first save/load round trip (i.e. on every `respond()` call). Fixed; verified the field now survives a start → respond → start → respond round trip intact.
- [x] **Cedar's allow/deny check was a substring match on stdout** (`"ALLOW" in result.stdout`) rather than the CLI's actual exit code (confirmed empirically: 0 = allow, non-zero = deny or error). Fragile in theory — an error message containing the word "ALLOW" would've misread as a grant. Switched to `result.returncode == 0`.
- [x] **`compute_warranty_status()` silently misclassified unknown product prefixes** as AC/compressor (`if product_id.startswith("WM-"): ... else: compressor, 5`) instead of failing the way every other prefix lookup in the codebase does. Not a live bug today (only two prefixes exist), but inconsistent with the fail-closed pattern used everywhere else. Fixed via the new catalog module below.

**Simplification — one real source of truth for brand/product routing:** `MANUAL_BY_PREFIX`/`TERMS_BY_PREFIX`/`BRAND_BY_PREFIX` were defined once in `agent.py`; `cedar_authz.py` had its own separate hardcoded `KNOWN_BRANDS` list; `opensearch_retrieval.py` had its own separate hardcoded `ALL_DOCS` list. Three copies of the same underlying fact, exactly the kind of thing that quietly drifts when a brand gets added or renamed. Consolidated into `src/domain/catalog.py` — `agent.py`, `cedar_authz.py`, `opensearch_retrieval.py`, and `registration.py` all import from it now. A third brand is a one-file change.

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

## Phase 7.11 — System design audit (done)

**Why this pass:** The demo worked end-to-end but had compounding design errors that weren't obvious individually — each fine in isolation, each reasonable at its original scope — but that together contradicted the system's own stated properties ("brands are independent", "each customer gets support for the right product"). A surgical audit, not a style pass.

**Bugs found:**

1. **`regs[0]` always picked the wrong product silently** (Critical). `api_core.start_conversation()` used `all_regs[0]` — whichever registration happened to come first in the CSV. A customer with two AquaSpin products would always get support for the first one registered, regardless of which machine they asked about. No error, no indication. Fixed: `start_conversation()` now requires `product_id`. Returns HTTP 400 without it. The exact registration is found by product_id match, not by position.

2. **No product picker when a customer has multiple products** (Critical). The UI went straight from phone lookup → "What's the issue?" without ever asking *which* product. Fixed: after lookup, if the customer has >1 product on this brand's line, a product picker screen appears. Each card shows product name, serial, and warranty status. The chosen `product_id` is sent to `/api/start`.

3. **Greeting announced product name before customer selected it** (Critical). The greeting was constructed from the first registration before the customer had asked about anything. Fixed: greeting now comes only after product selection, says "your AquaSpin FL-900 Front Loader (still under warranty ✓)", cites what the customer just chose.

4. **Demo mixed all brands in one customer picker** (Major architectural). ArcticAir and AquaSpin customers appeared together in a single list. The pitch is that each brand runs its own independent WhatsApp line. Fixed: **brand picker is now the first screen** — pick which brand's support line to simulate. Customer list is then filtered to that brand's customers only (`/api/customers?brand=aquaspin`). ArcticAir staff never sees AquaSpin's customers and vice versa.

5. **`/api/customers` had no brand filter** (Major). Fixed: accepts `?brand=` query param. Verified: `?brand=aquaspin` → `[Priya Sharma, Ananya Iyer]`, `?brand=arcticair` → `[Ravi Kumar, Sameer Khan]`.

6. **`/api/lookup` re-derived brand from `regs[0]`** (Major). Fixed: accepts `brand` in the POST body. Brand comes from the session (which line the customer is messaging on), never guessed from data order.

7. **No customer had two products to test with** (Major). Added Priya's second AquaSpin FL-900 Front Loader to `fixtures/sales_data.csv` and the `WM-FL-` prefix to `catalog.py`. The regs[0] bug is now demonstrably and visibly wrong without the fix, and demonstrably correct with it.

8. **QR codes were described but never implemented** (Medium). Added a "Registered products" section to the brand dashboard — each product has a generated QR code that encodes `/demo?brand=<slug>&serial=<serial>`. In production this would be a `wa.me` WhatsApp URL on the physical warranty card. In the demo, clicking or scanning it opens `/demo?brand=aquaspin&serial=WM-FL-90012` and goes straight into that customer's conversation without any picker — simulating "customer scans their card months later, WhatsApp opens knowing exactly which product."

9. **Dashboard showed registration count but not the actual registrations** (Medium). Fixed: `dashboard_data()` now includes the full `registrations` list with customer name, product name, serial, purchase date, retailer, warranty status, and QR content. The count stat remains, and the full list is in the new "Registered products" section.

10. **`lambda_handlers.py` still used old signatures** (Medium). Updated to pass `brand` from query params (`customers()`), `brand` from POST body (`lookup()`), and `product_id` from POST body (`conversation()`). The SAM Local proof stays consistent with the Flask adapter.

**Verified live, all in one pass:**
```
Routes:   / → 200, /demo → 200, /dashboard → 200, /dashboard/aquaspin → 200
Customers: ?brand=aquaspin → [Priya Sharma, Ananya Iyer]
           ?brand=arcticair → [Ravi Kumar, Sameer Khan]
Lookup:    +919876543210 + brand=aquaspin → found, 2 products: [FC-700, FL-900]
Start:     no product_id → 400 (enforced at API level)
Catalog:   WM-FC-700 → AquaSpin, WM-FL-900 → AquaSpin, AC-CB-15T → ArcticAir
```
Browser-verified flow: brand picker → AquaSpin customers only → Priya's two products → pick FL-900 → chat opens "your AquaSpin FL-900 Front Loader (still under warranty ✓)".
QR deep-link (`/demo?brand=aquaspin&serial=WM-FL-90012`) → skips all pickers → opens FL-900 conversation directly.
Dashboard: "Registered products — QR codes go on warranty cards at point of sale" → each product has a real QR image, customer name, serial, purchase date, retailer, and warranty status badge.

**Files changed in this pass:**
- `fixtures/sales_data.csv` — added Priya's FL-900 product row
- `src/domain/catalog.py` — added `WM-FL-` prefix
- `src/webapp/api_core.py` — brand filter + product_id required + registrations in dashboard
- `src/webapp/app.py` — routes pass brand and product_id
- `src/webapp/templates/index.html` — three-step entry: brand → customer → product
- `src/webapp/static/chat.js` — full rewrite: brand/customer/product flow + QR deep-link handler
- `src/webapp/templates/dashboard.html` — registered products section
- `src/webapp/static/dashboard.js` — QR code generation, registration list
- `src/webapp/static/dashboard.css` — .reg-card, .reg-qr, .reg-status, .section-hint
- `src/lambda_handlers.py` — updated signatures to match api_core

## Phase 7.12 — Handoff audit (2026-09-20) — corrections to the record above

A read-through of the folder as it stands on disk, done so a fresh session can pick up cold. Full detail in `CONTEXT.md` §4–6; the plan is `TARGET.md`. What this changes about the record:

- **The routed `/demo` is a scripted animation.** `demo.js` (`SCENARIOS`, `DASH_DATA`) makes no API calls and uses invented data (products `AC-900`/`WB-500`/`DW-300`, ticket `#AR-0047`, manual `§6.1`, "1,247 warranties", "93% resolved", "fraud 3") that matches nothing in `fixtures/`. The **real-backend chat UI (`index.html` + `chat.js`, described in Phase 7.11 as the three-step entry) is not routed** (`/index.html` → 404). Phase 7.10's two-pane real chat and Phase 7.11's brand/customer/product flow therefore exist in code but not in the page a visitor reaches.
- **Phase 7.11's QR claim is only half true.** The dashboard does render QR codes encoding `/demo?brand=…&serial=…`, but the routed `/demo` never reads those parameters (only the orphaned `chat.js` did), so the deep-link doesn't work end to end. `api_core.dashboard_data()` also still returns an unused placeholder `qr_content` (`wa.me/message/<brand>?serial=…`).
- **New content added by the UI rebuild but not in fixtures:** `WM-FL-900` (Priya's second machine) has no manual section; the "E4 drain error" scenario has no manual section; "Ananya — 2 products" is wrong (she owns one).
- **Unsubstantiated marketing claims** on `landing/brand/customer/demo`: 93% resolved, ₹0/week and ₹2/product/month pricing, "ROI within the first month", a "fraud" metric.
- **Verified still working (Flask test client, 2026-09-20):** all routes 200; `/api/start` without `product_id` → 400; `/api/lookup` brand-scoped (Priya → `WM-FC-700`, `WM-FL-900`); real conversation via API resolves/escalates/safety-escalates (Ravi ×2 → `TBB-0001`; Sameer burning smell → immediate ticket); dashboard allow 200 / cross-brand deny 403. Ollama up; OpenSearch/Docker down (keyword fallback active).
- **Not verified:** SAM Local after the brand/`product_id` API changes; any UI in a browser this pass.
- **Docs brought in line:** `README.md`, `USER_GUIDE.md` rewritten; `FLOW.md` given a status banner + API deltas; new `CONTEXT.md` (state, rules, audit) and `TARGET.md` (plan).
- **Open items unchanged:** demo video, write-up, public repo (repo is still named `GroundTruth`), submission, PartyRock decision, PAT rotation, deadline confirmation.
- **Working tree is uncommitted** since `2b32e20` (see `git status`); `framework.txt` (third-party transcript) is untracked and should not be committed.

## Phase 7.13 — Flow reorganisation: one landing page, Step 0, theme toggle (done, 2026-09-20 — the theme toggle and the CSV/AWS card layout were superseded by Phase 7.14)

**Why:** the user is shifting the repo from "pitching a business" to a hackathon submission. The business version lives in a separate copy; this repo can be cut and re-narrated freely. Requested order of work: (A) reorganise the flow → (B) implementation/visual improvements → (C) technical soundness + the audit's inconsistencies, including making the demo real. This entry is **A**.

**New narrative (`/`):** hero → ticker → problem hook → **Step 0: the brand plugs in** (a brand or the electronics retailer that sold its products uploads a sales CSV; Aftercare on the open-source AWS stack is assumed integrated in the backend) → **Steps 1–5: the customer's side** (the sticky-phone story, unchanged in content) → **"Now see it run" CTA → `/demo`**. The dashboard is reached from the demo, not the landing.

- [x] `landing.html` rebuilt as one page; nav is a theme toggle + one **"Live demo" pill** (the dashboard link is gone; the hook CTA became a "See how it works ↓" pill anchoring to Step 0).
- [x] **Step 0 is data-driven.** `app.py` `landing()` reads `load_registrations()` and passes real rows (phone masked to `+91 98765 ·····`), plus real counts (5 products / 4 customers / 2 brands), to the template — a CSV card, an "Aftercare on the open-source AWS stack" card (Strands, OpenSearch, Cedar, SAM·Lambda, each with one true sentence), and a "Live for support" card. Nothing on it is invented.
- [x] **Dark/light mode.** `landing.css` rebuilt on semantic tokens (`:root[data-theme="dark|light"]`); new shared `theme.js` (applied in `<head>` to avoid a flash; default dark; choice saved in `localStorage` inside try/catch; sun/moon icon + `aria-label`/`aria-pressed` kept in sync). Story cards stay vibrant and the phone stays white in both themes.
- [x] `prefers-reduced-motion`: animations/transitions off, carousel autoplay off, count-up skipped.
- [x] **Cut, on purpose (moved, not deleted — `archive/business-pages/`):** `brand.html/css/js` (B2B pitch with unsubstantiated "93% resolved" and pricing); `customer.html/css/js` (its hero and bento duplicated the landing hook; the story was kept; the "request a brand" form only `console.info`'d, so it was dropped). Routes `/brand` and `/customer` now 404. Links to them removed from `demo.html` (nav, sidebar "See plans & pricing", footer) and `dashboard_login.html`.
- [x] Real bug caught by the mobile pass: at 390px the page was 685px wide (the CSV table forced its grid cell open, which also pushed the nav pill/toggle off-screen). Fixed with `min-width:0` on the flow grid items; re-measured 390/390, no element past the viewport.

**Verified live (Browser pane):** Step 0 renders the 5 real rows and counts up to 5/4/2; toggle click flips `data-theme`, persists in `localStorage`, swaps sun↔moon and the `aria-label`; light and dark both checked at hero, hook carousel, Step 0, all five story steps (sticky phone types the right bubbles per step) and CTA/footer; mobile 390px checked. Flask test client: `/`, `/demo`, `/dashboard`, `/dashboard/aquaspin` 200; `/brand`, `/customer` and their static files 404; landing hrefs are only `#step-0`, `/`, `/demo`; `POST /api/start` without `product_id` still 400.

**Deliberately not touched (Phase B/C):** `/demo` is still the scripted animation; the story's illustrative bubbles still contradict the fixtures (cross-brand AC-900 picker, wrong serial/warranty date/manual sections) — listed in `TARGET.md`; theme toggle/tokens exist only on the landing; Google Fonts still load from a CDN; nothing committed.

## Phase 7.14 — Landing redesign: Apple-style chapters, Step 0 as a flow, story alignment fix (done, 2026-09-20)

**Asked for:** (1) the pinned phone and the step cards didn't line up while scrolling; (2) Step 0 should be clearer — brand uploads a CSV, *a store that sells many brands* gets auto-sorted into brand buckets in between, then the WhatsApp line is connected; (3) study Apple's iPhone 18 Pro / AirPods 5 / AirPods Pro / Watch Series 12 pages and apply their design strategy, noting they have no light/dark mode yet stay balanced.

**Study (all four pages inspected in the Browser pane):** chapters alternate `#000` / `#111`–`#1d1d1f` with `#f5f5f7` / `#fff`; one idea per chapter, 25–28px kicker over 56–96px weight-600 headline; 112–160px section padding; pinned sticky visuals with scrolling copy; a "Get the highlights" scroll-snap card gallery; slim 52px translucent nav; blue pill (radius 120px) + text link. Full notes in `TARGET.md`.

- [x] **Story alignment (the bug).** Cause: steps were `min-height:60vh` inside a column with 40px/80px padding while the phone sat centred in a 100svh sticky box, so their centres only coincided by accident (first card came early, step 5 drifted as the sticky box hit the grid's bottom). Fix — an explicit contract: every step is exactly `100svh` with its card centred, the left column has no top/bottom padding, the phone is `sticky; top:0; height:100svh` centred. Activation is now geometric, not an IntersectionObserver band: `tickStory()` measures each step's centre against the viewport centre; the animation starts only within 14% of the viewport height of coincidence, and proximity drives the card's `--p` (opacity/scale). **Measured: 0px centre difference at all five steps** (the pane throttles animation frames, so I called `tickStory()` directly for the activation check: only the aligned step activates, own opacity ≈1, others 0.16).
- [x] **Progress cue** under the pinned phone: five bars + "Step n of 5 · Label".
- [x] **Step 0 rewritten as a three-step flow:** ① Upload the sales file → ② *Sorted into the right brand, automatically* (tagged "Multi-brand stores only"; mechanism is real — `catalog.py` maps product-code prefixes to brands) → ③ Connect the WhatsApp line. Each step has a visual: the CSV (5 real rows, all columns), the five products each landing in an AquaSpin/ArcticAir chip with per-brand bucket counts (3 products·2 customers / 2 products·2 customers — computed in `app.py` `landing()` from the fixtures), and one line-card per brand (WhatsApp line / agent grounded in that brand's manuals / dashboard private to that brand). Then a "What runs behind it" strip (Strands, OpenSearch, Cedar, SAM·Lambda, one true sentence each) and a fine-print line: the open-source AWS stack runs locally with no AWS account; the WhatsApp line is simulated here, the agent/manual search/access control are real.
- [x] **Apple-style composition:** five full-bleed chapters — hero (black, phone rising from the bottom edge playing one exchange taken from the real AquaSpin manual §4.1), problem (light: a scroll-lit statement + a 5-card scroll-snap gallery with prev/next/dots/arrow keys), Step 0 (black), customer story (black, pinned phone), CTA (white) + grey footer. Type is weight 600–700 with a 60–132px hero scale; buttons are gradient pills and blue text links; the fixed nav is slim, translucent and turns light over light chapters.
- [x] **Decision: the dark/light toggle is dropped** (it fights a page whose balance comes from alternating chapters, and the user pointed at Apple's pages having none). The v1 landing with the toggle + `theme.js` is kept in `archive/landing-v1/`. `SKILL.md` updated ("one theme, chosen per chapter").
- [x] **Cut for calm:** the ticker tape (also removed its unmeasured "Free for customers, always" / "Analytics for every brand" claims), the centred 3D carousel (replaced by the native scroll-snap gallery), the hook copy's "millions of people" and "under 10 seconds" claims.
- [x] `reduced-motion`: autoplay, reveals, count/scroll-lit and the story scaling are all disabled cleanly.

**Verified live:** hero, problem statement lighting (29/29 words), gallery stepping 452 → 904 → 1122 with dots and disabled states, Step 0 rows 1–3 with animation, all five story steps aligned (0px), step 1 and step 5 screenshots showing phone and card level with the bubbles/ticket playing, CTA + footer, nav flipping to light over the white chapter (`rgba(245,245,247,.78)`, dark wordmark), mobile 390px (sw = iw = 390, hero phone plays). Flask test client: `/`, `/demo`, `/dashboard`, `/dashboard/aquaspin` 200; `/brand`, `/customer`, `/static/theme.js` 404; landing hrefs only `#step-0`, `#top`, `/`, `/demo`.

**Still open (Phase B/C):** the story bubbles remain illustrative and inconsistent with fixtures (`TARGET.md`); Google Fonts still load from a CDN; `/demo` is scripted; demo/dashboard haven't adopted the landing's design language; the mobile story shows stacked cards without the phone (the phone is hidden below 900px); nothing committed.

## Phase 7.15 — Human handoff for more than safety; the demo runs the real agent (done, 2026-09-20)

**Why.** The landing story showed a human only for safety. The honest question was whether the product *could* escalate for "the agent can't diagnose it" or "it keeps coming back". Audit answer: no. Retrieval always returns some section, and there was no history. So these were built, not just depicted.

**Escalation reasons (every ticket now carries `reason_code`).** `safety`, `attempts_exhausted` (two steps, still broken), `no_more_steps`, `no_steps`, `unmatched`, `recurring`. Labels in `agent.ESCALATION_LABELS`.
- *unmatched*: the complaint shares no meaningful word (stop-words, generic words like "machine" dropped, crude stemming) with the section retrieval returned. Escalate, don't guess. The word logic is in `layer1/retrieval.py` (`content_words`), shared by the keyword fallback and this gate. The fallback scorer now uses it too, and breaks ties in manual order instead of alphabetically. OpenSearch index is `aftercare-sections-v2` with the English analyzer.
- *recurring*: same serial + same manual section handled (resolved or escalated) within 90 days. History = saved conversations + `fixtures/history_seed.json` (relative ages, so the demo scenario doesn't expire). Only checked for manual answers, never for coverage questions.
- *safety*: now sends the manual's own stop-use text verbatim and says the emergency visit is free regardless of warranty (Terms §5). Previously the customer got a generic ticket message.
- Customer messages, and a `meta` block (source, section, retrieval method, attempt, escalation code/label/detail, warranty) come from `api_core._conversation_state`. Dashboard tickets show a reason chip.

**Landing.** "Five things you never do again" is now a static bento grid (no arrows, dots or keyboard handling). The story is 6 steps; new step 5 "Not fixed? A person takes over". Story bubbles now match the fixtures (Priya, FC-700, WM-FC-78234, manual §4.1/§4.4); invented ticket numbers and the cross-brand picker are gone.

**Demo (`/demo`, rewritten; v1 in `archive/demo-v1/`).** A real client of `/api/lookup|start|respond`. Five fixture-tied scenarios, each ending differently: fixed, two steps then handoff, not in the manual, recurring, safety. The customer's words are pre-filled and editable. Beside the phone: a trace built only from API fields, then the ticket the brand receives, then a link into the brand dashboard. `POST /api/demo/reset` (Flask only) clears runs so earlier ones don't count as history.

**Tests.** `tests/test_escalation.py` (8, stub model, no Ollama): `.venv/bin/python -m tests.test_escalation`. All five demo scenarios also run end to end against qwen2.5-coder:7b.

**Known gaps.** Coverage questions with no numbered steps still escalate as `no_steps`. FL-900 has no manual of its own (it reuses the FC manual). `lambda_handlers.py` gets the new fields through `api_core` but has no reset route. Recurrence matches on heading, so a different complaint that lands on the same section counts as the same problem.

## Phase 7.16 — AWS depth: OpenSearch cases, Cedar sessions, DynamoDB, Powertools, SAM proof (done, 2026-09-20)

Plan and cut lines: `PLAN.md`. Access patterns: `docs/DYNAMODB_DESIGN.md`. Frictions and likes: `docs/AWS_FEEDBACK_LOG.md`.

- **Health (A):** `GET /api/health` probes Ollama, OpenSearch and Cedar (`cedar validate`) on every call; also a Lambda.
- **OpenSearch (B):** two more indices. Recurrence is a filter on serial + source + `range now-90d`. Insights are `terms` aggregations (outcome, reason, section). Ticket text search. Fallbacks answer from the storage backend and report the engine. Bug found later, only under Lambda: index documents were keyed by absolute path, so nothing matched in the container; keyed by file name now (`aftercare-sections-v3`).
- **Cedar (C):** the old header-asserted principal is gone. Staff sign in (`fixtures/staff.json`, PBKDF2), the server issues a signed HttpOnly cookie, the principal is built from it. Schema + five `@id`-tagged policies; actions `viewDashboard`, `viewTicket`, `updateTicketStatus` (managers), `viewPhoneUnmasked` (safety tickets), `forbid` across brands. Decisions name the policy. Dashboard: ticket status buttons (agents refused live), masked phones, cross-brand try-link.
- **Storage (D):** `src/storage` interface with a file store and a DynamoDB single-table store; atomic ticket counter replaces `len(files)+1`. `tests/test_store_contract.py` runs the same assertions on both.
- **Powertools (D):** Logger (no phones/complaint text), EMF metrics, `Idempotency-Key` on `POST /api/start` (retry returns the same conversation; a changed body gets 422).
- **SAM (D):** template declares both tables, CORS, auth/ingest/health/reset Lambdas. All five scenarios pass through `sam local` on DynamoDB Local with OpenSearch retrieval (`scripts/run_scenarios.py`). `/demo?api=http://127.0.0.1:3000` runs the same page against it.
- **Strands (E):** found and fixed cross-customer context bleed (a shared Agent replays every prompt). `StatelessAgent` + latency `HookProvider`. `structured_output` tried and rejected on the 7B model.
- **Product truth (F):** real CSV check (`POST /api/ingest`), safety negation ("no burning smell") biased toward escalating, model-output guard, "Under the hood" chapter with live chips, component tags in the demo trace.

**Known gaps:** the sales-file check doesn't yet write the registry; `sam build` copies the whole repo into each function; recurrence still matches on manual section, not on the wording of the complaint; the shared latency sink in `StatelessAgent` is not safe under concurrent requests; Ship it (a real account) is out of scope.

### 7.16 addendum: a regression, and the responsive story layout
- **Regression (mine):** the cleanup that removed Step 0's old "What runs behind it" block used a lazy regex that also deleted the customer-story section header and the pinned phone column, so the landing showed only cards (the phone animation had vanished). Caught by the user, restored, and the story is now "Steps 1-6". Lesson: after any structural edit, check the rendered page (element counts, geometry) rather than trusting the diff; template edits by regex need a balance check.
- **Layout:** phone on the left, cards on the right; two-column down to 700px; below that the phone is pinned compactly at the top and the cards scroll beneath it (phone and cards share one grid cell so `position: sticky` can travel the whole story; a sticky grid item is confined to its own grid area).
- **Docs sweep:** FLOW, USER_GUIDE, TECHNICAL, DESIGN, README brought in line (real `/demo`, cookie sessions, `aftercare.cedar`, storage interface, six escalation codes).

## Phase 7.17 — All AWS, no Flask, no fallbacks (done, 2026-09-20)

**Why:** the app ran on Flask with Lambda as a side proof, and degraded silently to a keyword scorer or files when a service was down. Neither is "using AWS for real".

- **One Lambda serves everything.** `src/lambda_app.py` (Lambda Powertools API Gateway resolver) serves the pages (`src/pages.py`, Jinja) and all API routes; `template.yaml` has 17 explicit API Gateway routes (a catch-all proxy is shadowed by sam local's static route). Static files are `public/static/`, served by `sam local start-api --static-dir` (absolute path required). Flask, `app.py` and the per-route handlers are deleted.
- **Packaging:** `scripts/stage_lambda.sh` stages `lambda_pkg/` (src, fixtures, policies, requirements, arm64 Cedar) as `CodeUri`, because `sam build` copies the CodeUri folder wholesale (it choked on `.venv`).
- **No fallbacks.** `opensearch_retrieval.retrieve` has no keyword scorer; recurrence, insights, ticket search and case recording require OpenSearch; storage is DynamoDB only. A missing or unreachable service raises `DependencyUnavailable`, which the resolver turns into `503 {"error", "service"}`. The file store and keyword scorer remain only as unit-test doubles (`AFTERCARE_STORE=file`).
- **No infrastructure created at request time.** `scripts/bootstrap_local.py` creates the DynamoDB tables (read from `template.yaml`, so they cannot drift) and the OpenSearch indices + seed history. In an account CloudFormation creates the tables.
- **Corretto:** DynamoDB Local now runs from `docker/dynamodb-local/Dockerfile` (`amazoncorretto:21`).
- **One command:** `scripts/dev.sh` (containers -> bootstrap -> stage -> `sam build --use-container` -> `sam local start-api`). All five scenarios verified through it; stopping OpenSearch or DynamoDB gives a 503 naming it.
- **Tests:** call the handler with API Gateway proxy events (`tests/lambda_client.py`); no web framework anywhere.
- **Mistake caught by the tests:** a slice edit while removing fallbacks silently deleted `ingest_preview` and `update_ticket_status` from `api_core.py`; the Lambda route tests failed on the missing attribute and the functions were restored. Lesson: after bulk edits, import-check and run the suite before moving on.
- **Not used (and why):** LocalStack (needs an auth token; verified it exits with code 55 without one), PartyRock (personal Amazon sign-in), Finch/EKS-D/EKS-A/Firecracker (no natural role; Docker runs the containers).

## Phase 7.18 — Model quality, and a real sandbox demo (done, 2026-09-20)

**Brief:** orders/manuals/customers may be fabricated; everything else must be real; the live demo's five scenarios are the quality bar; build a separate free-form demo where the flow runs for real (warranty check, support from a manual, ticket, human intervention, analytics).

**Model quality (`scripts/eval_model.py`, `scripts/eval_routing.py`).**
- Five local models compared on phrasing and reply-reading: gemma2:9b phrases best (8/8), the others ranged 2/8 to 8/8, mostly failing by opening with a greeting or adding advice. Default is now `gemma2:9b` (`AFTERCARE_MODEL`).
- Reading the customer's reply is **rules first** (a clear negative always wins, a clear positive with no negative resolves) and only the ambiguous middle goes to the model; anything but a clear yes is STILL_BROKEN. 18/18 on the development set, 22/23 on a held-out set written afterwards (the miss is a conservative "Done. Smells fresh now").
- Prompt bans greetings, emoji, section numbers and extra advice; `_tidy` strips a greeting the model adds anyway.
- Routing: 41 phrasings across both products, all correct. Getting there needed (a) numbered steps for every troubleshooting section (fabricated manuals extended with drain, door, remote and noise sections), (b) **one synonym list** used by the OpenSearch analyzer (`aftercare_english`: standard tokenizer, synonym filter, stop, stemmer) and by the Python "is this in the manual at all?" gate, so "won't turn on" finds "won't start" and both layers agree, (c) a rule that landing on the manual's own safety section is a safety case even with no keyword ("water is leaking").
- New intents, all deterministic: **warranty questions** are answered from arithmetic on the purchase date plus Terms wording OpenSearch finds (outcome `answered`, no model call); **"talk to a person"** escalates immediately with its own reason (`human_requested`).

**The registry and the channel.**
- Order files now register customers for real: DynamoDB registry (brand partition + phone GSI); `ingest_commit` validates every row, files it under its brand, saves accepted rows, reports rejected ones, and sends each customer a registration message.
- `src/channel/bot.py` is the WhatsApp channel, server-side: a Meta-shaped webhook (`POST /api/wa/webhook`) in; greeting, product picker (buttons), warranty answers, step-by-step support, hand-over; every message appended to a per-(brand line, phone) log in DynamoDB (`/api/wa/messages` is what the customer's phone shows). Chat state machine: idle / awaiting_product / bot / human. While a chat is with a person the bot stays quiet; the ticket being resolved returns it to idle.
- **Human intervention is real:** the brand's inbox (`/api/inbox/<brand>`, Cedar-gated) lists handed-over chats; `POST /api/tickets/<id>/reply` (new Cedar action `replyToCustomer`) appends a person's message to the same log, so it appears on the customer's phone; resolving the ticket messages the customer.
- **`/sandbox`** (separate from `/demo`, which is untouched): fabricated order files (`fixtures/sandbox/`: a multi-brand Croma export with two deliberately bad rows, and a clean brand-direct export), eight personas, click-to-send chips, a trace per message, the inbox with reply, live analytics. `docs/SANDBOX_RUNBOOK.md` is the recording click-through.
- Verification: `scripts/run_sandbox_scenarios.py` drives all eight personas through the webhook against the real model (25 checks pass); the /demo scenarios still pass 5/5; unit tests (channel, storage contract on both backends, Cedar matrix incl. the new action) pass.

**Submission hygiene.** Clean-clone test (fresh venv, Cedar installer, `scripts/dev.sh`, full suite, both scenario scripts) passed; `--warm-containers EAGER` and a model warm-up in `dev.sh` remove the cold first request (15-40 ms after start). Removed the old GroundTruth project, ideation notes, the retired chat UI and superseded phase-1 scripts from the tracked tree.

**Known gaps.** Chat polling is 1.1 s (a real deployment would push); the phone UI has no authentication (it stands in for the customer's device; staff endpoints are Cedar-gated); a busy chat can race the two Lambda containers only in theory (state is one item per chat); `sam build` still needs ~1 min after a code change; multi-language ("abhi bhi garam hawa") only works where the rules or model catch it.

## Phase 7.19 — Entry points, "press here" cues, and a plainer, bluer dashboard (done, 2026-09-20)
- **Sandbox demo button** beside every Live demo button on the landing page (nav, hero, closing call to action, footer). A quiet glass pill next to the blue one; on the white band and the light nav it flips to a light grey pill.
- **"This is where you act" cues.** One CSS class (`.glow`, a pulsing blue ring) marks the next thing to do and turns itself off once done: on the sandbox the order-file buttons pulse until one is loaded, then the message box and send button pulse until the first message, the Inbox tab pulses when a chat needs a person, and the staff reply box pulses when a chat is opened. On `/demo` (CSS only, no logic change) the message box and send button pulse while they are live; the dashboard login's passcode field and the landing's "Check a messy store file" button pulse. `prefers-reduced-motion` gets a static outline instead.
- **Dashboard redesign (deliberately simple).** The old white-on-white page (785 lines of CSS, keyword-guessed complaint categories) is replaced: one Apple-blue rounded header (brand, who is signed in, the Cedar policy, links), four KPI tiles, a **Complaints** list where each row has a **three-dot status** (red waiting, yellow being handled, green resolved; clicking a dot changes it, managers only, Cedar refuses agents with the policy named) and opens to the WhatsApp chat with a reply box, a **Registered products** table with warranty dots, and a fixed blue **AI analytics** bar at the bottom whose sentences are built from the OpenSearch aggregations (handled-without-a-person %, most common reason, the manual section that sends most people to a person) with a Details panel of two bar lists. No animations. The old QR-code section and product-health/keyword-breakdown cards were dropped; the analytics bar replaces them. Old `style.css` removed.
- Screens verified at 1280 and 430 px; no horizontal overflow.
