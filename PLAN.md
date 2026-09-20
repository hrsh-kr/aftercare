# PLAN: 10-hour build, Build It track (written 2026-09-20)

Supersedes the priority list in TARGET.md where they differ. Source of the deliverables: `submission.txt`.

## 0. What is being judged (from submission.txt)

| Form field | What it demands | Where it's satisfied |
|---|---|---|
| Public repo, README, **commit history** | Judges read how it came together | Commit after every phase, small and honest (§4) |
| Video ≤3 min | About · tech stack + architecture · how AWS was used · learning | Script in §6; the architecture chapter and the live trace are the shots |
| "Build it": AWS open-source stack, tool names | Real use, not decorative | Strands, OpenSearch, Cedar, SAM CLI (+ DynamoDB Local, Lambda Powertools) |
| "Ship it": AWS services, names | Not our track | One honest sentence + short README table (§2). Not deployed. |
| Feedback: dislikes / likes, per service | Specific, named | `docs/AWS_FEEDBACK_LOG.md`, appended as friction happens (§5) |
| Team leader's contributions, blog | Written | §6 |

Design principle to show everywhere: **deterministic before model.** Safety, recurrence, attempt cap, warranty maths and authorization are code and policy; the model phrases and classifies.

## 1. Target architecture

```
Browser ─▶ API Gateway ─▶ Lambda (SAM Local)  ◀── same handlers ──▶  Flask dev server
                              │  Powertools: structured logs, EMF metrics, idempotency
                          api_core (pure logic)
      ┌───────────────┬───────────┴───────────┬─────────────────────┐
  Strands Agent    OpenSearch            Cedar (schema,         DynamoDB Local
  Ollama qwen2.5   manual_sections       server-side principal) single table:
  typed outcome    tickets, cases        + Verified Permissions  CONV#, TICKET#, CASE#, CTR
  hooks → trace    BM25 + aggregations   mapping in docs         GSI1: brand+time
```

DynamoDB single-table design: `PK=BRAND#<slug>`, `SK=TICKET#<id>` / `CASE#<serial>#<ts>`; `PK=CONV#<id>`, `SK=STATE`; `PK=CTR`, `SK=TICKET` with atomic `ADD` for ticket IDs. GSI1 (`serial`, `created_at`) for recurrence. Access patterns are listed in the doc before any code.

## 2. Ship it: deliberately out of scope
We submit on Build It; no AWS account, nothing deployed. The form's "Ship it" line gets one honest sentence ("not used; `template.yaml` is written to deploy with `sam deploy`") plus a short README table, "Where each piece goes in production" (Ollama→Bedrock, OpenSearch container→OpenSearch Serverless, Cedar CLI→Verified Permissions, DynamoDB Local→DynamoDB, SAM Local→API Gateway+Lambda, Powertools→CloudWatch). Only two code seams are kept because they cost minutes: `MODEL_PROVIDER` and `DYNAMODB_ENDPOINT`. No hours go to Ship it.

## 3. Phases (hours are budgets, cut lines in §7)

| # | Time | Work | Done when |
|---|---|---|---|
| A | 0:00–0:45 | Branch `hackathon`, commit current work in chunks, `.gitignore` (`framework.txt`, `data/`), Docker up, OpenSearch up, `GET /api/health` (live probes) | Health green; demo trace says "OpenSearch BM25" |
| B | –2:15 | OpenSearch: `tickets` + `cases` indices, recurrence as query (serial filter + time range + text match), brand aggregations (`terms` on reason and section), honest fallback kept | Container stopped → "keyword fallback"; started → "OpenSearch" |
| C | –3:45 | Cedar: schema, signed-cookie server-side principal (staff passcode fixture), actions `viewDashboard`/`viewTicket`/`updateTicketStatus`/`viewPhoneUnmasked`, `forbid` cross-brand, `cedar validate` + matrix test; UI shows the deciding rule and a live cross-brand denial | Forged header rejected; matrix passes |
| D | –6:15 | Serverless: repository interface (file + DynamoDB Local), single-table design, atomic ticket counter; Lambda Powertools (Logger, Metrics, idempotency on `/api/start`); Lambdas for ingest/health/reset; frontend `API_BASE`; **all five scenarios verified through `sam local`** | SAM run recorded; duplicate `/api/start` is idempotent |
| E | –7:00 | Strands: Pydantic structured outcome (replaces string match); hooks feed the trace with tool/latency; `@tool` wrappers behind a flag, kept only if the 7B model is reliable | 5 scenarios pass on the shipped path |
| F | –8:15 | Product truth + visuals: CSV upload calls `/api/ingest`; registration message from the API; safety negation tests; output guard; "Under the hood" landing chapter with live health chips; trace component tags; brand insights panel; runtime pill; honest-stack footer | Screens verified desktop + mobile |
| G | –8:45 | Tests (Cedar matrix, escalation, repository contract on both backends, safety negations, SAM smoke); README; docs | `pytest`-style run green |
| H | –10:00 | Deliverables (§6) and 45 min buffer | Form filled, video unlisted-published |

## 4. Commit discipline
One commit per phase minimum, imperative and specific ("Recurrence as an OpenSearch query"), never one giant commit. Do not commit `framework.txt`, `data/`, `.venv`, tokens. Revoke the early leaked GitHub PAT before the repo goes public.

## 5. AWS feedback log (keep as we go; specifics already seen)
- `cedar-policy` on PyPI is an empty placeholder; only the Rust CLI works, so the Python path is subprocess.
- LocalStack now needs an account/token, contradicting "no account".
- SAM Local: `/var/task` read-only, state lives in warm-container `/tmp`; needs `--warm-containers LAZY`; arm64 image needs a matching Cedar binary; `host.docker.internal` for Ollama.
- Strands: 7B-model tool-calling reliability; structured output behaviour (to record in phase E).
- OpenSearch: analyzer change requires a new index (we hit this).
Add likes as they come (Strands hooks, SAM `template.yaml` as a real deploy artifact, Cedar's readable policies, etc.).

## 6. Deliverables checklist (from submission.txt)
- [x] (README done; repo still to be made public by the user) Repo public, README (problem, architecture diagram, run steps for Flask and SAM, honest stack table)
- [ ] Video ≤3:00: 0:00 problem (20s) · 0:20 landing story incl. human handoff (35s) · 0:55 live demo, 2 scenarios + recurring (60s) · 1:55 architecture + AWS: OpenSearch, Cedar deny, SAM (45s) · 2:40 learning + Ship-it path (20s)
- [ ] "What does your project do", "How did you use AWS" (Build it / Ship it), contributions, likes, dislikes: drafted from this file, docs and the log
- [ ] Project title, track (submit to both; only one can win), deployed link left blank
- [ ] Optional blog on AWS Builder Center if time remains
- [ ] Needed from the user: WeMakeDevs username, LinkedIn, resume link, YouTube upload

## 7. Cut lines
Must (A, B, C, D, G, H). Then F visuals items 1–3. E only as structured output + hooks if behind. Never cut: commits, the video, the AWS feedback text.

## 8. Risks
Docker instability (SAM and OpenSearch), qwen tool-calling, DynamoDB Local + SAM networking (`host.docker.internal`), time. Each has a fallback in its phase.

## 9. Status log (updated as work lands)
- 2026-09-20 (latest): model eval + rules-first reply reading; warranty/human intents; registry + channel + `/sandbox` (fabricated data, real flow); clean-clone test passed; repo tidied. See IMPLEMENTATION 7.18 and docs/SANDBOX_RUNBOOK.md.
- 2026-09-20 (later): all-Lambda pass done: Flask removed, single Lambda + API Gateway on SAM Local, no fallbacks, Corretto DynamoDB Local, bootstrap script, `scripts/dev.sh`. See IMPLEMENTATION 7.17.
- 2026-09-20: phases A-F done and committed; G (tests + README + docs sweep) done; H drafted (`docs/VIDEO_SCRIPT.md`, `SUBMISSION_ANSWERS.md`). Story-layout regression fixed.
- Open: video recording, user's details on the form, revoke the leaked GitHub token, make repo public, decide on tracked `archive/groundtruth/`.
