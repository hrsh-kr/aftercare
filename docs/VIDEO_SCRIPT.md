# Demo video script (3:00 cap), section by section

Read it top to bottom while you scroll. Each block says **where you are on the page**, **what to do**, and **what to say**. About 400 spoken words, so about 2:40 of speech plus clicking. Times are targets, not rules.

Structure (after Alex Hormozi): call out the person, make the pain real, show the fix, prove it works, end on the result. The value equation is inside the words: the outcome (support that knows what you bought), the proof (steps come from the manual, unknowns go to a person), the speed (seconds, not a hold queue), the effort (nothing to type or find).

| Part | Time | Page |
|---|---|---|
| 1. The idea | 0:00 – 0:55 | Landing page: hero, problem, customer story |
| 2. The architecture | 0:55 – 1:45 | Landing page: architecture screen |
| 3. The live demo | 1:45 – 3:00 | Live demo page: order file, customers, dashboard |

---

## PART 1 · The idea (0:00 – 0:55) · landing page `/`

### 1a. Hero: "Support. Redefined." (0:00 – 0:10)
**Screen:** landing page loaded at the top. Don't scroll yet.
**Say:**
> If you've ever tried to get a washing machine or an AC fixed in India, this is for you.

### 1b. The problem (0:10 – 0:25)
**Scroll:** slowly to **"The problem"**. The sentence lights up word by word as you scroll; scroll at the speed you talk so it lights up while you speak.
**Say:**
> Something breaks. You message the brand, and before you've said what's wrong you're hunting for a model number behind the door, digging up an invoice, proving you own the thing they sold you. Fifteen minutes gone. And they already have all of it.

### 1c. The fix (0:25 – 0:40)
**Scroll:** past "Five things you never do again" without stopping, to **"Months later, something breaks. One message is all it takes."** (the phone on the left, step cards on the right).
**Say:**
> So I built Aftercare. The sale registers the customer once. Months later, one WhatsApp message, and it already knows who you are, what you bought, and whether you're under warranty.

### 1d. The six steps (0:40 – 0:55)
**Scroll:** down through the steps (**Registration, Lookup, Manual, Back and forth, Human handoff, Safety**). Let the phone animate. Keep moving.
**Say:**
> One step at a time, from that product's own manual. If it's unsafe, not in the manual, or two steps fail, it hands you to a person with everything attached.

---

## PART 2 · The architecture (0:55 – 1:45) · landing page, blueprint screen

### 2a. The blueprint (0:55 – 1:05)
**Scroll:** to **"Five AWS tools. One job each."** (the dark navy blueprint). Stop so the whole screen is in frame. Point at the flow strip: Customer, API Gateway, Lambda, Four services.
**Say:**
> Here's how it's built. I planned to ship on AWS, but my account wasn't verified in time, so I built on AWS's open-source stack, and it made the design better. One rule: deterministic before model.

### 2b. The five cards (1:05 – 1:40)
**Do:** move the cursor across the cards left to right as you name each one. Don't read the cards; say the why.
**Say:**
> One Lambda behind API Gateway serves everything. Strands runs a small local model, only to word one manual step. OpenSearch finds the right manual section and spots repeat faults. Cedar decides who can reply or resolve, and names the policy every time. DynamoDB holds customers, chats and tickets in one table.
>
> Every tool has a trade-off I chose on purpose. The local model is slower, so rules do the rest. Cedar is one more language. DynamoDB wants its queries designed up front. And no fallbacks: if a service is down, the API says which one.

### 2c. The button (1:40 – 1:45)
**Scroll:** to **"Now see it run."** and click **Open live demo**.
**Say:**
> Let me show you.

---

## PART 3 · The live demo (1:45 – 3:00) · page `/demo`

### 3a. Hero (1:45 – 1:50)
**Screen:** "Eight customers. One real agent." Don't linger; scroll down.
**Say:**
> This is a recording of the running tool. Real replies.

### 3b. The order file (1:50 – 2:10) · section **"Start with an order file."**
**Do:**
1. Click the first card, **`orders_croma_sep2026.csv`**. A spreadsheet appears and each row is checked in turn.
2. When it finishes, point at the **green rows** (registered under their brand) and the **two red rows**. Move the cursor to the reason on each red row.

**Say:**
> The brand starts with its order file. Every row is checked. Green rows are registered, filed under the right brand. The red ones are errors: this one has a product code no brand owns, and this one has a phone number in the wrong format. Nine registered, two rejected, each with its reason.

### 3c. The customers (2:10 – 2:45) · section **"Try a customer."**
**Scroll:** down to the three columns (people, phone, brand). Run **three** scenarios only. In each, click the highlighted chip under **"Try saying"** to send it.

1. **Arjun Mehta** (~8 s): click *My washing machine bangs loudly when it spins*, then *That fixed it, thank you!*.
   **Say:** "So this is what a customer says. One step from the manual. Fixed. No ticket."
2. **Kavya Nair** (~15 s): click *My AC isn't cooling the room*, then *Still blowing warm air*, then *No change, still not cooling*. On the right, the ledger under **What Aftercare did** fills up.
   **Say:** "Kavya's AC still isn't cooling after two steps, so it stops guessing and hands her to a person. On the right is everything Aftercare did: registry, OpenSearch, the model, DynamoDB."
3. **Sanjay Iyer** (~6 s): click *There's a burning smell coming from my AC*.
   **Say:** "A burning smell: no troubleshooting at all. Safety goes straight to a person."

(Optional if time allows, ~10 s: **Meera Pillai**, "I want to talk to a person", then in the Inbox tab click *Resolve ticket as Dev Patel (agent)* to show Cedar refusing, and the manager's resolve being allowed.)

### 3d. The dashboard (2:45 – 2:57) · section **"What the brand sees."**
**Scroll:** down past the three coloured cards to the dashboard below them. Let it fill the screen. Point at the red, yellow and green dots, then the AI analytics bar at the bottom.
**Say:**
> And this is what the brand sees. Every complaint, red, yellow or green. Open one to read the chat and reply. And an AI analytics bar on why people needed a person.

### 3e. Close (2:57 – 3:00)
**Stay on the dashboard.**
**Say:**
> Aftercare. Support that already knows what you bought.

*Stop the recording. Don't scroll to "Run it yourself"; put the repo link and `docs/SANDBOX_RUNBOOK.md` in the video description instead.*

---

## Before you record
- Browser 1440 × 800, zoom 100%, bookmarks hidden, notifications off, record at 1080p.
- Use the deployed Vercel site (or `python3 -m http.server` inside `public/`). Hard refresh (Cmd+Shift+R) the demo page so no customer is already played.
- Do one dry run with a timer. Aim for 2:50.
- Upload as **unlisted**. Put the repo link and the runbook in the description.

## If you run long, cut in this order
1. Sanjay (the safety scenario), 6 s.
2. In 2b, the trade-offs paragraph down to one: "The local model is slower, so rules do the rest." 8 s.
3. In 1c, "Fifteen minutes gone." 3 s.

## If something looks wrong on screen
- A customer's chips are used up: click **Restart this customer** under the phone.
- The architecture chips say "recorded". That's correct on the deployed site; don't call them live.
- The story phone can look empty for a second on first paint; scroll slowly.
