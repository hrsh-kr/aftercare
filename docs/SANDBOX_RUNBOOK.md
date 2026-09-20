# Sandbox runbook: how to run and record the real demo

`/sandbox` is the whole flow running for real on **fabricated orders**. Only WhatsApp's network is simulated:
the phone talks to a Meta-shaped webhook on this server, every message is stored in DynamoDB, and the brand's
inbox reads the same log. The agent, manual search, tickets, Cedar and analytics are the real components.

(`/demo` is the *recorded* version of this: the deployed site's live-demo page replays eight of these conversations from `public/static/recording.json`, captured by `scripts/record_playback.py`. This runbook is for the real, free-form one.)

## Start it

```bash
ollama serve                      # its own terminal; leave running
bash scripts/dev.sh               # containers, tables/indices, sam build, sam local start-api
```

When it prints `Running on http://127.0.0.1:3000`, open **http://127.0.0.1:3000/sandbox**. The pill under the
title should show four green dots (DynamoDB, OpenSearch, Cedar, Ollama). If one is amber, that service is down:
the app will say so instead of pretending (there are no fallbacks).

Before each take: click **Reset sandbox** (bottom of column 1). It clears chats, tickets, cases and the orders
you uploaded, and leaves the baseline customers.

## Where to click (the glowing ring)

A pulsing blue ring marks the next thing to do: first the order-file buttons, then the message box and send button, then (after a hand-over) the Inbox tab and the reply box. It switches off once you've done that step. Chips send immediately.

## The screen

| Column | What it is |
|---|---|
| **1 · The order file** | Two fabricated order exports. Click one: rows are checked, customers registered, and each gets a WhatsApp registration message. |
| **2 · The customer's WhatsApp** | Pick **Message as** (a customer) and the brand line (AquaSpin / ArcticAir). Type, or click a **Try saying** chip: chips send immediately. |
| **3 · The brand** | *What Aftercare did* (the trace of the last message), *Inbox* (handed-over chats; reply here), *Analytics* (the dashboard's numbers, live). |

## The takes (each is one short clip; order is up to you)

**0. Onboard (30 s).** Click `orders_croma_sep2026.csv`. Say: a store uploads its export; 9 products registered, 2 rows
rejected (an unknown TV code, a malformed phone) and named. Switch to Arjun: the first message in his chat is his
registration message.

| # | Message as | Click / type | What you'll see | Say |
|---|---|---|---|---|
| 1 | **Arjun Mehta** · AquaSpin | chip *My washing machine bangs loudly when it spins*, then *That fixed it, thank you!* | One step from manual §4.1, then "Resolved. No ticket needed." Trace: OpenSearch → Strands (timed). | Grounded in that product's manual; fixed means no ticket. |
| 2 | **Kavya Nair** · ArcticAir | chip *My AC isn't cooling the room*, then *Still blowing warm air*, then *Still blowing warm air, no change* | Step 1 (filters), step 2 (outdoor unit), then a hand-over: "Two steps tried". | Two tries, then a person, with both attached. |
| 3 | **Rohan Desai** · AquaSpin | chip *Hi*; then *My clothes smell bad after washing*; tap **FC-700 Washing Machine** | Greeting with buttons; "Which product is this about?"; then **Recurring issue** hand-over (his FC-700 had the same problem 38 days ago). Repeat and tap **FL-900** to get a normal step instead. | It found the earlier case with an OpenSearch time-window query, so it doesn't repeat the fix. |
| 4 | **Neha Kulkarni** · AquaSpin | chip *Is my machine still under warranty?* | Deterministic answer: motor active until 01 Jul 2027, other parts expired 01 Jul 2026, plus the Terms wording. No model call. | Warranty is arithmetic on the purchase date, not the model. |
| 5 | **Imran Sheikh** · ArcticAir | chip *Is my AC compressor covered under warranty?* then *Water is dripping from my AC* | Compressor active to 10 Aug 2027; then a step from §4.3. | |
| 6 | **Divya Rao** · AquaSpin | chip *Is my machine still under warranty?* (both expired), then *The touch panel flickers and won't respond* | "Not in the manual" hand-over: it won't guess. | Honest about what it can't diagnose. |
| 7 | **Sanjay Iyer** · ArcticAir | chip *There's a burning smell coming from my AC* | The manual's own "Stop use immediately", a safety ticket, no troubleshooting. | Safety is a rule, never left to the model. |
| 8 | **Meera Pillai** · AquaSpin | chip *I want to talk to a person* | Hand-over "Asked for a person". Open **Inbox** (red badge), click the chat, type a reply, **Send**: it appears on the phone as a person's message. Click **Resolve ticket** (as the manager); the customer is told. | A person takes over, in the same chat. |

**Cedar moment (20 s).** On the **AquaSpin** line, in *Inbox*, click **Switch to an agent**, then **Resolve ticket**: refused, naming the
policy. (ArcticAir has a single manager account; the manager/agent contrast is shown on AquaSpin.) Switch back to the manager and it works. Then open *Analytics*: handled-without-a-person %, why people
escalated, which manual sections send them to a person (OpenSearch aggregations). **Open the full dashboard**
signs you in already: a blue header, complaints with a red/yellow/green status, a products table and an AI analytics bar at the bottom. Click a row to read the chat and reply; click the dots to change status.

## Say your own words

Free text works. It handles: greetings, warranty questions (any phrasing with "warranty/covered/expire/claim"),
noise/smell/cooling/drain/door/remote/leak problems for both products, "talk to a person", safety words,
and things it can't diagnose. Anything else that shares no meaningful word with the manual is handed over as
"Not in the manual" (by design).

## Recording tips

- Warm the model: the first reply after `dev.sh` starts can take several seconds; send one throwaway message first.
- A reply takes 2–6 s (the typing dots show). Talk over it: name what's happening in the trace.
- If a take goes odd, **Reset sandbox** and start the persona again.
- Keep the browser at ~1440 px wide so all three columns fit; the page is responsive but the demo reads best wide.

## If something looks wrong

| Symptom | Cause |
|---|---|
| Amber banner "X isn't reachable" | That service is down. Ollama: `ollama serve`. OpenSearch/DynamoDB: `bash scripts/dev.sh` restarts them. |
| No customers in the dropdown but the baseline ones | You haven't loaded an order file, or you just reset. Click a sample. |
| A persona doesn't behave (e.g. Rohan isn't "recurring") | Earlier runs count as history. **Reset sandbox** (it also re-seeds the history). |
| Slow first page | Cold Lambda container; refresh once. `dev.sh` uses `--warm-containers EAGER`. |

## Verifying without a browser

```bash
.venv/bin/python scripts/run_sandbox_scenarios.py -v     # all eight personas through the webhook, with transcripts
PYTHONPATH=. .venv/bin/python scripts/eval_routing.py    # 41 phrasings route to the right thing
PYTHONPATH=. .venv/bin/python scripts/eval_model.py      # how the local model does its two jobs
```
