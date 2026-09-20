# I planned to ship on AWS. My account wasn't verified. So I built the whole thing on AWS's open-source stack

*Draft for AWS Builder Center. First person, written after the build. Author: Harsh (team of one), with Claude Code as a coding partner (disclosed in the README).*

The plan I had on day one was not the plan I submitted. That is the whole story, so I'll tell it in order.

## Days 1 to 4: the wrong idea, and the right constraint

I started with an idea called **GroundTruth**: check whether a candidate's GitHub repo really shows what their resume claims. I spent days on it. I read the hackathon page, looked at the judges' backgrounds, argued with myself about which of two ideas would score better (that one, or a health-insurance estimator called ClaimCast), and built a working three-layer prototype on a local model.

It worked, and I still didn't trust it. The judges have thousands of entries to get through. The idea also had a problem I couldn't argue away: a repo can't prove who wrote it, so the product's central promise was one it couldn't keep.

At the same time I was planning to compete on the **Ship It** track, using deployed AWS services (Bedrock for the model, and so on). On the 17th, when the build window opened, I tried to actually start.

- I opened the Bedrock playground. It failed until I noticed my region was US East and the models I wanted were in Asia Pacific (Mumbai). Switching fixed it. First lesson: model availability is per region.
- I tried to open **CloudShell**. It said: *"Unable to create the environment. Your account verification is in progress. This may take up to two days for new accounts."*
- I gave my user `AWSCloudShellFullAccess` anyway, in case it was a permissions problem. It wasn't. The account simply wasn't verified yet, and the whole build window was only four days long.

I could have faked it: write code against Bedrock that I couldn't run, or wire in a model call that was "swappable later". I decided against that. An AI judge or a human judge would read it as unfinished, a workaround dressed up as design. So I dropped the Ship track and committed to **Build It** (the open-source AWS stack, running on my machine, no account needed) plus **Best UI**.

That decision felt like a loss. It turned out to be the best thing that happened to the project, because it forced a question I'd been dodging: *if I can't lean on a big hosted model, where should the model actually sit in the system?*

## Day 5: throw the idea away, keep the discipline

On the 18th I did something uncomfortable: I archived GroundTruth and started over. I asked for ten ideas people actually want, then picked the one I had lived myself.

Something breaks (a washing machine bangs on every spin, an AC stops cooling in a heatwave). You message the brand. Then you spend fifteen minutes proving that you own the thing: model number off a sticker behind the door, purchase date from an old email, a screenshot of the invoice. The brand sold it to you. They have all of it on file. Nothing connects the person messaging them to the sale.

That became **Aftercare**: a customer is registered once, at the point of sale, from the brand's own order file. Months later they send one WhatsApp message. The agent already knows who they are, which product it is and its warranty. It gives one step from *that product's own manual*, follows up, and hands over to a person, with everything attached, when it should.

I used fictional brands (AquaSpin washing machines, ArcticAir ACs) and fabricated customers, orders and manuals. Only WhatsApp's network is simulated. Everything else runs for real.

## The design lesson that came from the constraint

My first test of the model taught me the rule the whole project is built on. I asked the local model to work out warranty status from a purchase date. It got two of four customers **exactly backwards**: it said the motor warranty had expired when it was active, and it marked a lapsed parts warranty as live. I moved warranty arithmetic into plain Python, and all four came back right.

That became the principle: **deterministic before model.**

- Safety ("burning smell") is a keyword rule, or landing on the manual's own safety section. It skips troubleshooting entirely.
- Which step comes next is read from the manual's numbered list.
- "Two tries, then a person" is a counter.
- "Not in the manual" is a word-overlap test. The agent won't guess.
- "Seen this before" is an OpenSearch time-window query.
- Warranty dates are arithmetic.
- Who may do what is a Cedar policy.

The model has two small jobs: word one manual step, and read an ambiguous reply. I compared five local models on those two jobs (`scripts/eval_model.py`) and picked `gemma2:9b`, which phrased 8 of 8 correctly. The others scored between 2 and 8 out of 8, mostly by opening with a greeting or adding advice. The lesson is not that the model is smart. It's that a small model placed in a narrow job, surrounded by code that can be tested, beats a big model given the whole problem.

## How AWS's open-source stack shows up

- **API Gateway + Lambda (SAM CLI).** The whole site, pages and every API route, is *one* Lambda behind API Gateway on SAM Local, using Lambda Powertools' API Gateway resolver.
- **Strands Agents** with a local Ollama model. A fresh agent per call; hooks time each model call.
- **OpenSearch.** Manual retrieval (BM25 with a synonym analyzer), the recurring-problem window (`now-90d`), and aggregations that answer "why do people need a person?".
- **Cedar.** Six policies and a schema, and a session-derived principal. Agents can reply; only managers can resolve; nobody crosses brands. Every decision names its policy.
- **DynamoDB Local** on Amazon Corretto, single-table design, several access patterns, an atomic ticket counter, TTL.

I was firm about one rule: **no fallbacks.** At one point the app ran on Flask with a keyword-search fallback. I ripped both out. Now if OpenSearch or DynamoDB is down, the API returns `503` naming the service. That one decision paid for itself almost immediately (see below).

## The bugs that taught me the most

1. **A silent OpenSearch fallback.** Documents were indexed with an absolute file path as a filter key. Inside the Lambda container the path was `/var/task/...`, so every search matched nothing and quietly fell back to keyword search. Nothing failed. I only noticed because each response reports which engine answered. Fix: key by file name. Then I deleted the fallback so it could never hide again.
2. **A shared Strands `Agent` remembers everything.** I used one agent for all requests. Inspecting `agent.messages` showed customer B's prompt being answered with customer A's complaint in context. An `Agent` is a *conversation*, not a function. Fix: a fresh agent per self-contained call.
3. **Strands structured output on a small local model** fails ("model failed to invoke the structured output tool"), and the deprecated fallback said "resolved" for *"Still blowing warm air"*, which is worse than failing. I kept plain text with a strict parser that defaults to "still broken".
4. **SAM Local surprises.** `--static-dir` must be an absolute path (a relative one 404s silently). The static catch-all shadows a `/{proxy+}` route, so every route is declared explicitly. `sam build` copies the whole repo including `.venv`, so I stage a clean package first. And an environment variable from my shell (`DYNAMODB_ENDPOINT=localhost`) leaked into the Lambda, where `localhost` means the container.
5. **Cedar has no Python binding** (the PyPI package is an empty placeholder), so I shell out to the real Rust CLI. It works and costs a process spawn per decision.
6. **LocalStack needs an account token**, which contradicts "no account, no card". I used SAM Local and DynamoDB Local instead.
7. **Malformed JSON gave a 502.** Fix: 400 for bad bodies, 401 before validation for unauthenticated calls, and one generic 500 handler that logs without leaking.
8. **A regex edit deleted the phone animation from my own landing page.** I noticed only because the story section had cards and no phone. Restored, and I now check the page in a browser after every edit.

## Redesigning the demo, three times

The demo is where I changed my mind most. First it was scripted, and I didn't like that it was simulated. Then I built a **sandbox** where everything runs for real: load a fabricated order file, message as a customer, watch the agent work, reply as a person from the brand's inbox, see the analytics move. That's the honest demo, but it needs Docker, SAM and Ollama on your machine, so a judge can't click it.

The fix was not to fake it. I wrote a recorder that drives the real stack through its real webhook and staff endpoints and stores every response. The deployed website then *replays* those recorded, real responses through the same UI. The landing page tells you it is a recording, and shows the command to run the real thing. A test fails the build if the deployed pages drift from the templates.

## What I would tell another builder

- **A blocked door can be a design brief.** No verified AWS account pushed me to put the model where it belonged instead of where it was convenient.
- **Remove your fallbacks.** They turn "broken" into "plausible", and plausible is what you can't debug.
- **Don't let a model do arithmetic.** Give it numbers; ask it to phrase them.
- **Record real behaviour rather than simulating it**, and say clearly that it's a recording.
- **Be honest about limits.** Nothing is deployed to AWS. WhatsApp is simulated. Chat is polled. A code change needs a one-minute `sam build`. It's all written in the README.

The code, the recorded demo and the runbook to run it yourself are in the repository.
