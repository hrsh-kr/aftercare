# Putting a small model in its place: building WhatsApp after-sales support on AWS's open-source stack

*By Harsh · First Commit hackathon (WeMakeDevs × AWS) · Build It track · solo build*

**TL;DR.** I built Aftercare, a WhatsApp support line that already knows what you bought, using Strands Agents, OpenSearch, Cedar, SAM (API Gateway + Lambda) and DynamoDB, all running locally with no AWS account. The design rule that made it work: a small model may only *word* things; code, queries and policy *decide* things. I lost my first plan (deploying on AWS) to an unverified account, replaced my first idea, threw away three versions of the demo, and ended with a system whose claims are backed by tests and recorded runs. This post is the reasoning, the decisions and the bugs.

Code: `github.com/hrsh-kr/aftercare` · Architecture: [`ARCHITECTURE.md`](ARCHITECTURE.md) · Run it: [`SANDBOX_RUNBOOK.md`](SANDBOX_RUNBOOK.md)

---

## 1. Start with the data problem, not the chatbot

When a washing machine starts banging on every spin, the customer messages the brand and the first fifteen minutes go on proving ownership: the model number off a sticker behind the door, the purchase date from an old email, an invoice screenshot. I have lived this.

Most people frame it as a support-quality problem. I framed it as a **missing join**. The brand sold the product, so it holds every fact the agent is asking for. Nothing connects the person on WhatsApp to that sale. Fix the join and the conversation gets short by itself.

That gave me the product in four decisions:

1. Register each sale **once, at the point of sale**, from the brand's own order file. Never make the customer do it.
2. Use **the WhatsApp number as the identity.** The sender is already authenticated, so I removed the "enter your phone number" step from my first flow.
3. Answer from **that product's own manual and warranty terms**, never from model memory.
4. Make the **handover to a person** a designed path with everything attached, not a failure mode.

## 2. The mistake that defined the architecture

I did what everyone does first: give the model the job. I asked a local model to work out warranty status from a purchase date, on four customers.

It got **two of the four exactly backwards.** An active motor warranty came back expired; a lapsed parts warranty came back live. The answers were fluent and confident, which is the dangerous part.

I did not respond by prompting harder. I asked a different question: *for each decision in this system, is it a language task?* Most were not.

| Decision | Made by |
|---|---|
| Is this a safety issue? | A keyword rule with negation, or retrieval landing on the manual's own safety section |
| Which step is next? | A regex over the manual's numbered list |
| Two failed attempts, then a person | A counter |
| Is this even in the manual? | A word-overlap gate |
| Has this product had this problem before? | An OpenSearch query: same serial, `range now-90d` |
| Warranty status | Date arithmetic |
| Who may view, reply or resolve | A Cedar policy |
| **Word one manual step; read a vague reply** | **The model** |

I call this *deterministic before model*. The model has two small jobs. Everything else can be tested without it (my tests use a stub model) and fails safe. One consequence I like: **anything short of a clear "yes, fixed" counts as "still broken"**, because a false "resolved" leaves a broken product with an unhappy customer and no ticket.

I compared five local models on those two jobs (`scripts/eval_model.py`). `gemma2:9b` phrased 8 of 8 correctly. The others ranged from 2 to 8, mostly failing by opening with a greeting or adding advice nobody asked for. Reply-reading is rules first, and only the ambiguous middle reaches the model. It scored 18/18 on the set I developed against and 22/23 on a held-out set I wrote afterwards. The one miss is conservative ("Done. Smells fresh now" read as not-fixed).

## 3. The stack, and the trade-off I accepted with each piece

I wanted every component to have a job that only it could do well, and I wanted to be able to say what each one cost me.

- **API Gateway + Lambda (SAM CLI).** The whole site, pages and all 26 routes, is *one* Lambda behind API Gateway, using Powertools' resolver. It is stateless by construction, since chat state lives in DynamoDB. *Cost:* cold starts, and a code change needs a roughly one-minute `sam build`.
- **Strands Agents.** A thin agent layer over a local Ollama model. I use a **fresh agent per call** and a `HookProvider` on model-call events for exact latency. *Cost:* a local model is slower, and Strands' structured output needs a tool-calling model, so I use plain text with a strict parser.
- **OpenSearch.** One engine does three things: BM25 manual retrieval through a custom analyzer (synonym filter, stop, stemmer), the recurrence window, and the `terms` aggregations behind the dashboard's "why did people need a person?". *Cost:* heavier than a database, and keyword relevance rather than semantic.
- **Cedar.** Six schema-validated policies. The principal comes from a signed server-side session, never from anything the browser claims, and every decision names the policy that made it. There is also a `forbid` across brands, which beats any future `permit`. *Cost:* another language, and no Python binding.
- **DynamoDB.** A single table with twelve access patterns designed *first* and keys second, an overloaded GSI, an atomic ticket counter and TTL. *Cost:* every query is designed up front; anything ad hoc goes to OpenSearch.

And one rule across all of it: **no fallbacks.** My first version ran on Flask with a keyword-search fallback, which meant the app worked even when the AWS pieces did not. I removed both. Now a dead OpenSearch or DynamoDB returns `503` naming the service. A fallback turns *broken* into *plausible*, and plausible is the thing you cannot debug.

## 4. The pivot I did not want, and the one I chose

My plan was to compete on the **Ship It** track: deployed AWS services, Bedrock for the model. On the day the build window opened I sat down to start.

- The Bedrock playground failed until I noticed the console was set to US East while the models I wanted were available in Asia Pacific (Mumbai). Lesson: model availability is per region.
- CloudShell would not start: *"Your account verification is in progress. This may take up to two days for new accounts."* I added `AWSCloudShellFullAccess` in case it was IAM. It was not; the block was on the account.

In a four-day event, two days is half the window. My options were to wait, or to write Bedrock code I could not run and call it "swappable later". I chose neither. Code I cannot run is a claim, not a feature, and a reader would see it as a workaround dressed up as design. I dropped Ship It and committed to **Build It plus Best UI**.

That forced the question I had been dodging: if I cannot lean on a big hosted model, where does a small one belong in a system? Section 2 is the answer. The constraint improved the design.

I made a second cut a day later. My first idea, **GroundTruth**, checked whether a candidate's repository backs their resume claims. I built a working prototype, then found the flaw I could not argue around: *a repository cannot prove who wrote it.* Its central promise was one the product could not keep. I archived it and built the problem I had actually lived.

## 5. Bugs that taught me something

1. **A silent OpenSearch fallback, visible only inside Lambda.** I filtered documents by absolute file path. In the Lambda container the path is `/var/task/...`, so every search matched nothing and quietly fell back to keyword matching. Nothing failed. I noticed only because every response reports which engine answered. Fix: key by file name. Then I deleted the fallback so it could never hide again.
2. **A shared Strands `Agent` remembers everything.** Printing `agent.messages` showed customer B's prompt being answered with customer A's complaint in context. An `Agent` is a *conversation*, not a function. Fix: a fresh agent per self-contained call.
3. **Structured output on a small model.** Strands' newer path is a forced tool call and fails on a local model; the deprecated method returned "resolved" for *"Still blowing warm air"*, which is worse than failing. I kept plain text and a strict parser that defaults to "still broken".
4. **SAM Local surprises.** `--static-dir` must be an *absolute* path or it 404s silently. Its static catch-all shadows a `/{proxy+}` route, so every route is declared explicitly. `sam build` copies the whole repo including `.venv`, so I stage a clean package first. And a host `DYNAMODB_ENDPOINT=localhost` leaked into the Lambda, where `localhost` is the container, and it looked exactly like the database being down.
5. **Cedar has no Python binding** (the PyPI package is an empty placeholder), so I call the real Rust CLI. It works and costs a process spawn per decision.
6. **LocalStack now needs an auth token**, which contradicts "no account, no card", so I used SAM Local and DynamoDB Local instead.
7. **Malformed JSON gave a 502.** I fuzzed the API, then fixed it properly: `400` for bad bodies, auth checked before validation, and one generic handler that logs the request id and returns a bare `500` with no stack trace.
8. **My own regex deleted the phone animation from my landing page.** I caught it because I check the rendered page, not the diff, after every UI edit.

## 6. The demo, redesigned three times

The demo taught me the most about honesty. First it was scripted, and I disliked that it was simulated. Then I built a **sandbox** where everything is real: load a fabricated order file, message as a customer, watch the agent work, reply as a person from the brand's inbox, see the analytics move. It was honest, but a judge cannot open it without Docker, SAM and Ollama.

I refused to fake the difference. Instead I wrote a recorder that drives the real stack through its real webhook and staff endpoints and stores every response, and the deployed website *replays those recorded responses* through the same UI. Every page says it is a recording. A test fails the build if the deployed pages drift from the templates or leak a local URL. The site can show nothing the system did not do.

## 7. How I worked with AI

I used Claude Code as a pair-programmer for implementation, refactors and test scaffolding, and reviewed and directed everything it produced. The decisions in this post are mine: the missing-join framing, the phone-number-as-identity call, the deterministic-before-model rule, dropping Ship It, archiving GroundTruth, the per-brand dashboards (I corrected an early design that put every brand on one page), removing Flask and every fallback, and replacing a simulated demo with a recorded real one. That division worked because I knew what I wanted the system to guarantee. The tests and evals are how I checked that it did.

## 8. What I would tell another builder

- **Frame the problem as data before you frame it as conversation.** Mine was a missing join.
- **Classify each decision by kind.** If it is not a language task, do not give it to a model.
- **Delete your fallbacks.** They make failures look like successes.
- **A blocked path is a design brief.** Losing Bedrock taught me where the model belonged.
- **Record real behaviour instead of simulating it, and say so.**
- **State your limits.** Nothing is deployed, WhatsApp is simulated, chat is polled, and it is all written down in the README.

---

*Numbers, for the record: 26 routes in one Lambda · 6 Cedar policies · 12 DynamoDB access patterns · 5 models compared · 41 routing phrasings correct · 8 end-to-end personas, 25 checks against the real model · 2 fictional brands. Everything is reproducible from the repository.*
