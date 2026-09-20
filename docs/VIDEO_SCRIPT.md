# Demo video: 3:00 hard cap

Everything is shown from the **deployed website** (the Vercel URL): the landing page, then its **Live demo** page. Nothing needs to be
running locally except one terminal for the "how it's built" beat. The demo page's replies are real responses recorded from the running tool;
say so out loud.

| Time | Show | Say |
|---|---|---|
| 0:00–0:20 | Landing hero, then scroll the problem line | "When something breaks you hunt for a model number, wait on hold, and explain it three times to a company that already has your purchase on file. Aftercare is the support line that already knows what you bought." |
| 0:20–0:55 | Step 0 (click "Check a messy store file"), then scroll the six-step customer story, pause on step 5 (human handoff) | "A brand or store uploads one order file; every row is checked, each product filed under its brand, unknown codes reported. The agent answers from that product's own manual, one step at a time, and hands over to a person for six different reasons, not just safety." |
| 0:55–1:05 | Click **Live demo** | "This is the demo. Everything on it was recorded while I ran the tool: the agent's actual replies, the tickets, the dashboard. Nothing is hard-coded." |
| 1:05–2:00 | Conversations (the customer list scrolls on its own; the Send button pulses): Arjun (bangs → fixed), Neha (warranty), Rohan (Hi → smell → pick FC-700 → recurring), Divya (not in the manual), Meera (person → reply → agent refused → manager resolves). Point at the trace tags | "Press Send and you replay what happened. One step from the manual, fixed means no ticket. Warranty is arithmetic on the purchase date, no model. Rohan's problem was back within 90 days, found by an OpenSearch time-window query, so it doesn't repeat the fix. If it isn't in the manual it won't guess. A person replies in the same chat, and Cedar lets an agent reply but only a manager resolve." |
| 2:00–2:30 | Scroll down to the dashboard (it fits on screen, no inner scrolling): the complaints with red/yellow/green dots, click a row to show the chat, open the AI analytics bar (Details) | "This is what the brand sees: every complaint, its status, the chat behind it, and analytics computed by OpenSearch aggregations. Access is Cedar: who may reply, who may resolve." |
| 2:30–2:50 | The "Run it yourself" section; optionally the terminal with `bash scripts/dev.sh` and the architecture diagram in the README | "The recording can only replay what I recorded. The real thing is one Lambda behind API Gateway in SAM Local, on DynamoDB Local running on Corretto, with OpenSearch, Cedar and Strands, so you can run it and type anything. There are no fallbacks: stop OpenSearch and the API says so." |
| 2:50–3:00 | Landing footer | "A small model only words a step and reads a reply; everything that matters is a rule, a query or a policy. I chose it by measuring five models. Built on the open-source AWS stack, no account. Thank you." |

Rehearse once with a stopwatch. To refresh the recording after any change: `bash scripts/dev.sh`, then `scripts/record_playback.py`, then `scripts/build_site.py`, commit, push.
For a live take of the real, free-form version instead, use `docs/SANDBOX_RUNBOOK.md`.
