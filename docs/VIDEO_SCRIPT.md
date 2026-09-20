# Demo video script (3:00 hard cap)

Three parts, one screen recording, one voice. About 395 spoken words (roughly 150 words a minute, so about 2:40 of speech), which leaves 20 seconds for clicking and pauses.

| Part | Time | Job | Screen |
|---|---|---|---|
| 1. The idea | 0:00 – 0:55 | Say who it's for, make them feel the pain, show the fix | Landing page (top, problem, the six steps) |
| 2. The architecture | 0:55 – 1:50 | What is built with which AWS tool, why, and the trade-off | Landing page, blueprint section (`#architecture`) |
| 3. The live demo | 1:50 – 3:00 | Prove it: real flow, human takeover, analytics | The Live demo page |

The structure borrows from Alex Hormozi's framework (`framework.txt`, kept out of the repo):

- **Call out the person** (Part 1 opens on the avatar, not on the product). He calls this the "call out" that describes the person back to themselves.
- **Pain first, in their words**, then the fix. He says the pain should "bring out your inner feelings".
- **The four parts of the value equation**, all present in the words (mapped below): the dream outcome, how likely it is to work (proof), how fast (time delay), how little effort (sacrifice).
- **Narrow beats broad**: one product type, one channel, one job. Say it as a strength.
- **"Best bad idea"**: say the pivot honestly and briefly. It builds trust and covers the optional "learning and growth" point.

The form asks the video to cover: *about the project, tech stack and architecture, how you used AWS, learning and growth*. Parts 1, 2, 3 and the pivot line cover all four.

---

## Part 1: The idea (0:00 – 0:55) · ~135 words

**SHOW** Landing page hero (headline and tagline), then scroll the problem line and the six-step phone story. Don't stop; the phone animation in the story carries you.

**SAY**

> If you've ever tried to get a washing machine or an AC fixed in India, this is for you.
>
> Something breaks. You message the brand. And before you've said what's wrong, you're hunting for a model number behind the door, digging up an invoice from last year, proving you own the thing they sold you. Fifteen minutes gone. And the brand already has all of it.
>
> So I built Aftercare. The sale registers the customer once. Months later you send one WhatsApp message, and it already knows who you are, what you bought, and whether you're under warranty.
>
> One step at a time, from that product's own manual. If it's unsafe, or not in the manual, or two steps fail, it hands you to a person with everything attached.

**Where the value equation lands** (all four are in the words above, no jargon needed):

- *Dream outcome*: "it already knows who you are, what you bought, and whether you're under warranty."
- *Likelihood it works*: "one step at a time, from that product's own manual" and "hands you to a person".
- *Time delay*: "Fifteen minutes gone" (the pain) against one WhatsApp message (the fix).
- *Effort and sacrifice*: the pain names the effort today (model number, invoice); the fix removes it, because the sale already registered you.

---

## Part 2: The architecture (0:55 – 1:50) · ~145 words

**SHOW** Scroll to the blueprint section. Hold on the flow strip first (Customer → API Gateway → Lambda → four services), then move your cursor across the five cards left to right as you name them. Don't read the cards; say the *why*.

**SAY**

> Here's how it's built. I planned to ship on AWS, but my account wasn't verified in time. So I built on AWS's open-source stack, and it made the design better.
>
> One rule: deterministic before model. A message hits API Gateway, and one Lambda serves everything. Strands runs a small local model, only to word one manual step. OpenSearch finds the right manual section and spots repeat faults. Cedar decides who can reply or resolve, and names the policy every time. DynamoDB holds customers, chats and tickets in one table.
>
> Each has a trade-off, and I chose them on purpose. The local model is slower, so rules do the rest. Cedar is one more language. DynamoDB wants its queries designed up front.
>
> And no fallbacks. If a service is down, the API says which one.

---

## Part 3: The live demo (1:50 – 3:00) · ~140 words

**SHOW** Click **Open live demo** at the end of the landing page. Then, in this order (each click is on screen; don't narrate the clicking):

1. **Order file** → click `orders_croma_sep2026.csv`. Rows scan; green rows register, two red rows show their reason. (~10 s)
2. **Try a customer** → click **Kavya Nair** → click the highlighted chips one by one: *My AC isn't cooling the room* → *Still blowing warm air* → *No change, still not cooling*. The right-hand ledger fills. (~25 s)
3. Click **Meera Pillai** → *I want to talk to a person*. The Inbox tab opens. Click the chips in the Inbox: **Reply as Dev**, then **Resolve ticket as Dev Patel (agent)** (Cedar refuses and names the policy), then **Resolve ticket as Meera Nair (manager)** (allowed). (~25 s)
4. Click **Analytics**. Then scroll to the dashboard for two seconds. (~8 s)
5. Stop on the **Run it yourself** band. (~2 s)

**SAY**

> This is the live demo, recorded from the running tool. Start with the brand's order file. Every row is checked. Green registers the customer; red is rejected, with the reason.
>
> Kavya's AC isn't cooling. Step one, from the manual. Still warm. Step two. Still warm. It stops, and hands her to a person. On the right is everything Aftercare did: registry, OpenSearch, Strands, DynamoDB.
>
> Meera asks for a human. Dev, an agent, replies in the same WhatsApp chat. He tries to resolve it. Cedar refuses, and names the policy. The manager resolves.
>
> Analytics shows why people needed a person. Only WhatsApp's network is simulated. Run it yourself, the link is below.

**Close (last 4 seconds, on screen: the landing headline or repo)**

> Aftercare. Support that already knows what you bought.

---

## Recording checklist

- Use the deployed site (or `python3 -m http.server` in `public/`), so the recording matches what judges will open. Say "recorded" out loud once (it is in the Part 3 script).
- Browser at 1440 × 800, zoom 100%, bookmarks bar hidden, notifications off. Record at 1080p or better.
- Do a dry run to time it. The script is written to land at about 2:55. If you're over, use the cut lines.
- Before recording the live demo, hard refresh (Cmd+Shift+R) so the run starts clean.
- Upload as **unlisted** on YouTube, and paste the URL into the form.

## Cut lines (if you run long)

1. In Part 1, drop "Fifteen minutes gone." (3 s)
2. In Part 2, drop the trade-offs sentence for Cedar and DynamoDB, keep the local model. (6 s)
3. In Part 3, skip the dashboard scroll. (4 s)

## Common failure points

- The phone animation in the six-step story can look empty for a second on first paint. Scroll slowly.
- The architecture status chips say "recorded" on the deployed site. That's correct and honest; don't call them live.
- If a chip doesn't seem to work in the live demo, it's already been played for that customer. Use **Restart this customer**.
- Running the real thing locally instead? Click-by-click steps for eight customers are in [`SANDBOX_RUNBOOK.md`](SANDBOX_RUNBOOK.md).
