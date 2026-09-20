# Demo video: 3:00 hard cap

Screen: the landing page, `/sandbox` (see `docs/SANDBOX_RUNBOOK.md` for the exact clicks), the dashboard, one terminal.
Before recording: `bash scripts/dev.sh`, open `/sandbox`, click **Reset sandbox**, send one throwaway message so the model is warm.

| Time | Show | Say |
|---|---|---|
| 0:00–0:15 | Landing hero, the scroll-lit problem line | "When something breaks you hunt for a model number, wait on hold, and explain it three times to a company that already has your purchase on file. Aftercare is the support line that already knows what you bought." |
| 0:15–0:35 | `/sandbox`: click the Croma order file; show 9 registered, 2 rejected rows named; Arjun's registration message | "A store uploads its order export. Every row is checked, each product filed under its brand, the customers registered in DynamoDB and messaged on WhatsApp. The bad rows are reported, not guessed. Everything here is fabricated; the flow is real." |
| 0:35–1:20 | Arjun: bangs chip → step → fixed. Neha: warranty chip. Rohan: Hi → smell → pick FC-700 → recurring | "The agent answers from that product's own manual, one step at a time, and a fixed problem needs no ticket. Warranty is arithmetic on the purchase date, no model. Rohan's problem came back within 90 days: found by an OpenSearch time-window query, so it doesn't repeat the fix." |
| 1:20–1:55 | Divya: touch panel (not in the manual). Meera: "talk to a person" → Inbox → reply → it appears on the phone → Resolve | "It won't guess: if it isn't in the manual, a person takes over, with everything attached. Here the brand replies from its inbox into the same WhatsApp chat, and the customer is told when it's resolved." |
| 1:55–2:20 | Inbox: switch to an agent, Resolve → refused with the policy named. Analytics tab | "Cedar decides who may reply and who may resolve, and every answer names the policy. OpenSearch aggregations tell the brand why customers reach a person." |
| 2:20–2:45 | Terminal / Under-the-hood chapter: one Lambda behind API Gateway, DynamoDB Local on Corretto, OpenSearch, Cedar, Strands; stop OpenSearch to show the 503 naming it | "The whole site is one Lambda behind API Gateway in SAM Local, on DynamoDB Local running on Amazon Corretto. No fallbacks: stop OpenSearch and it says so. A small model only words a step and reads a reply; every decision that matters is a rule, a query or a policy." |
| 2:45–3:00 | Landing footer | "I compared five local models and measured, not guessed. Running in Lambda found bugs my laptop never showed. Not deployed; built on the open-source AWS stack. Thank you." |

Rehearse once with a stopwatch. Personas and expected results: `docs/SANDBOX_RUNBOOK.md`.
