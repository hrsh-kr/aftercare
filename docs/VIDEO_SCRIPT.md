# Demo video: 3:00 hard cap

Screen: /demo and the landing page, one terminal for `sam local`. Voice over; no music needed.

| Time | Show | Say |
|---|---|---|
| 0:00–0:20 | Landing hero, then the scroll-lit problem line | "When something breaks, you hunt for a model number, wait on hold, and explain it three times to a company that already has your purchase on file. Aftercare is the support line that already knows what you bought." |
| 0:20–0:50 | Step 0 CSV: click "Check a messy store file". Then the six-step story, pause on step 5 | "A brand or a store uploads one sales file. It's checked row by row: unknown codes and duplicates are reported, not guessed. The agent answers from that product's own manual, and it hands over to a person for six different reasons, not just safety." |
| 0:50–1:50 | /demo. Run "Fixed in one step", then "It's back", then "Not in the manual". Point at the trace tags | "This is the real agent. The trace beside the chat is built only from what the API returned. Here OpenSearch found the manual section; Strands worded one step. Here Ananya's problem is back within 90 days, found by an OpenSearch time-window query, so it doesn't repeat the fix. Here the complaint isn't in the manual, so it won't guess." |
| 1:50–2:30 | Dashboard: sign in as AquaSpin agent, show insights panel, click a status button (refused), click "Try ArcticAir's dashboard" (refused, policy named) | "Every decision that matters is code, not the model: a small local model words a step well and judges safety badly. Cedar decides who sees what, and every answer names the policy. OpenSearch aggregations tell the brand why customers reach a person." |
| 2:30–2:50 | Terminal: `run_scenarios.py` against sam local, all PASS. Then the demo page with `?api=` pill "AWS Lambda (SAM Local) · DynamoDB Local" | "The same handlers run as Lambdas in SAM Local on DynamoDB Local, with Powertools logging and idempotency. Five scenarios, five endings, through the Lambdas." |
| 2:50–3:00 | Under the hood chapter | "Learning: a shared Strands agent leaks context between customers, structured output needs a tool-calling model, and running in Lambda found a bug the laptop never showed. Not deployed; no AWS account. Thank you." |

Rehearse once with the stopwatch. Reset demo data before recording (`Reset demo data` button); run `ollama run qwen2.5-coder:7b ""` first so the model is warm.
