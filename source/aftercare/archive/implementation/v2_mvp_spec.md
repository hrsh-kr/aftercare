# thebestbill — MVP Spec (Decisions Locked)

All open questions answered. This is the build plan.

---

## Decisions Summary

| Decision | Answer |
|---|---|
| Platform | Mobile app (React Native / Flutter) for consumers. Web dashboard for brands. |
| Product add | Auto-register via API + Photo OCR with manual correction + manual form fallback |
| Warranty data | Brand uploads per SKU. If unknown SKU → manual lookup (person checks web, enters warranty info). Handle ALL warranties. |
| Support flow | Per-brand/product decision trees. Conversational complaint form → generates email or API payload to brand. |
| Chat channel | In-app only. No WhatsApp bot (friction, multi-brand conflict). |
| Helpline directory | 50-100 brands, manually verified. After user calls → ask "did this number work?" |
| Document storage | OCR + structured. As brands onboard, invoices will be platform-generated. |
| Auth | WhatsApp OTP first, SMS OTP fallback. |
| Brand integration | Manual/concierge first. Observe patterns → build API. Shopify plugin first when ready. |
| Brand catalog | CSV upload + dashboard form. Semi-automatic with manual intervention. |
| Dashboard | Day 1. Track service requests + resolutions for product feedback data. |
| Service dispatch | We collect intake, notify brand. Brand handles assignment. Technician app later. |
| AI knowledge | RAG for onboarded brands (PDF upload). Generic fallback for unregistered. Not a V1 priority — people do basic checks themselves before calling. |
| GTM | Cold outreach + inbound + concierge. Email brands when users register their unregistered products. |
| Notifications | Push + in-app first. WhatsApp second. SMS third. Mechanical turk everything initially. |
| Infra | Free tier. Minimal spend until scale. |
| Team | Solo founder. Can code. Can design. |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│  CONSUMER                                           │
│  Mobile App (React Native)                          │
│                                                     │
│  • Product passbook     • Warranty tracking         │
│  • Invoice scan (OCR)   • In-app chat (complaint)   │
│  • Document vault       • Helpline directory        │
└────────────────────────┬────────────────────────────┘
                         │
              WhatsApp OTP / SMS OTP
                         │
┌────────────────────────▼────────────────────────────┐
│  BACKEND (single codebase)                          │
│                                                     │
│  • Auth (WhatsApp OTP → SMS fallback)               │
│  • Product registry + warranty engine               │
│  • Complaint intake + decision trees                │
│  • OCR pipeline (Google Vision)                     │
│  • Helpline directory                               │
│  • Notification service (push → WhatsApp → SMS)     │
│  • File storage (invoices, documents)               │
│                                                     │
│  Stack: Supabase (Postgres + Auth + Storage)        │
│         + Edge Functions / small Node server        │
│         + Google Vision API (OCR)                   │
│         Free tier everything.                       │
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│  BRAND                                              │
│  Web Dashboard (Next.js or plain React)             │
│                                                     │
│  • Overview metrics     • Service request inbox     │
│  • Product catalog      • Registration log          │
│  • CSV upload           • Resolution tracking       │
│                                                     │
│  + API (built later, once patterns observed)        │
│  + Shopify plugin (first integration)               │
└─────────────────────────────────────────────────────┘
```

**Why Supabase**: Free Postgres, free Auth (50K MAU), free Storage (1GB), Edge Functions. You can code, so you don't need Firebase hand-holding. Supabase gives you raw SQL access when you need it.

---

## Subproblem Specs

---

### C1. Adding a Product

#### Path A: Auto-registration (brand integrated)

```
Brand's system (Shopify / custom)
    │
    ├── [V1: manual] Brand sends CSV / you do it for them
    ├── [V2: API] POST /v1/products/register
    └── [V3: plugin] Shopify app triggers on order
    │
    ▼
Backend creates product record
    ├── Lookup SKU → get warranty duration from brand catalog
    ├── Create warranty record (purchase_date + duration → expiry)
    ├── Link to customer phone
    │
    ▼
Push notification to customer
    "Your [Product] is registered. Warranty valid until [date]."
    │
    ▼
Product appears in app on next open
```

#### Path B: Manual add (consumer initiated)

```
User taps "Add Product"
    │
    ├── Option 1: Take photo of invoice
    │     ▼
    │   Google Vision API OCR
    │     ▼
    │   Extract: brand, product, serial, date, price, retailer
    │     ▼
    │   Show extracted fields → user corrects any mistakes
    │
    ├── Option 2: Manual form
    │     Brand (dropdown/search), Product name, Serial number,
    │     Purchase date, Price, Retailer
    │
    ▼
Warranty lookup
    ├── SKU exists in our DB? → use stored warranty duration
    ├── SKU unknown?
    │     ▼
    │   [Mechanical turk] Flag for manual review
    │   A person looks up the product + warranty on brand's website
    │   Enters warranty duration into our DB
    │   (This builds our warranty database over time)
    │
    ▼
Product card created
    ├── Warranty countdown starts
    ├── Invoice photo stored
    ├── Helpline auto-populated (if brand in directory)
    └── If brand not onboarded → "We'll notify [Brand] that
        you're tracking their product on thebestbill"
```

**Warranty database growth loop:**
```
User adds unknown product
  → Person looks up warranty on web
    → Enters into DB
      → Next user with same product gets instant warranty info
        → Over time, DB covers most common products
```

> [!NOTE]
> **Mechanical turk queue**: Build a simple admin panel where you (or a part-time hire) see a queue of "unknown SKU" entries. For each one: Google the product, find warranty info, enter it. Target: <24 hour turnaround per entry. As the DB grows, this queue shrinks.

---

### C2. Warranty Tracking

**Data model:**

```
product {
  id, user_id, brand, name, model, serial_number,
  purchase_date, purchase_price, retailer,
  category (AC / RO / washing_machine / electronics / general),
  brand_registered (boolean),  // is brand on thebestbill?
  documents[] (invoice photo, warranty card, etc.)
}

warranty {
  id, product_id,
  type (comprehensive / component),
  component_name (null for comprehensive, "compressor" etc.),
  duration_months,
  start_date, end_date,
  status (active / expiring / expired)
}
```

**Handle multi-component warranties:**
- One product can have multiple warranty records
- AC example: warranty(comprehensive, 12mo) + warranty(compressor, 60mo)
- Display: show the "worst" status on the card, full breakdown in detail view

**Notification schedule:**
```
30 days before ANY warranty expires → push notification
7 days before → push notification
Expiry day → push notification
All in-app. WhatsApp/SMS later when it's a "good problem to have."
```

---

### C3. Complaint / Service Request Flow

This is the core differentiator. A conversational complaint form, not a chatbot.

**Key insight from your answer**: People already do basic troubleshooting themselves. They don't need AI to tell them "check if it's plugged in." What they need is an easy way to report the issue to the brand — without filling forms, calling dead lines, or navigating broken websites.

#### How it works:

```
User opens "Get Help" for a specific product
    │
    ▼
Conversational complaint form starts
    │
    Step 1: "What's going on with your [Product Name]?"
    │         → Options based on product type (decision tree)
    │         [Not cooling] [Water leaking] [Noise] [Not turning on] [Other]
    │
    Step 2: "When did this start?"
    │         → [Today] [Few days ago] [Last week] [Longer]
    │
    Step 3: Product-type-specific question
    │         AC: "Is the outdoor unit running?"
    │         RO: "When was the last filter change?"
    │         WM: "Any error code on display?"
    │
    Step 4: "Anything else you want to mention?"
    │         → Free text
    │
    ▼
Complaint summary generated
    ┌─────────────────────────────────────────┐
    │  📋 Service Request Summary             │
    │                                         │
    │  Product: Daikin Split AC 1.5T          │
    │  Serial: DK-2024-AC-91023              │
    │  Issue: Not cooling                     │
    │  Outdoor unit: Running but noisy        │
    │  Started: Few days ago                  │
    │  Warranty: Active (expires Jan 8, 2026) │
    │  Additional: [user's free text]         │
    │                                         │
    │  Location: [from user profile]          │
    │  Purchase date: Jan 8, 2024            │
    └─────────────────────────────────────────┘
    │
    ▼
    ├── Brand IS onboarded?
    │     ▼
    │   Generate API payload / structured request
    │   Send to brand's service system
    │   (or email if no API yet)
    │   Track in our system
    │   Notify user: "Request sent to [Brand]. Ref: #SRV-XXXX"
    │
    └── Brand NOT onboarded?
          ▼
        Generate formatted email/complaint
        ┌─────────────────────────────────────┐
        │  📧 Ready to send to Daikin         │
        │                                     │
        │  To: customercare@daikin.co.in      │
        │  Subject: Service Request - AC Not  │
        │  Cooling - FTKG50TV16U              │
        │                                     │
        │  [Pre-filled complaint body with    │
        │   all details from the form]        │
        │                                     │
        │  [Send Email]  [Copy to Clipboard]  │
        │                                     │
        │  ── OR ──                           │
        │                                     │
        │  📞 Call Daikin: 1860-180-3900      │
        │  Hours: Mon-Sat, 9 AM – 6 PM       │
        │                                     │
        │  💡 Mention: Model FTKG50TV16U,     │
        │  Serial DK-2024-AC-91023,           │
        │  Issue: not cooling, outdoor unit   │
        │  buzzing                            │
        └─────────────────────────────────────┘
        │
        ▼
        After interaction, ask user:
        "Did you reach [Brand]? How was the experience?"
        [Resolved] [Still waiting] [Couldn't reach them]
        │
        ▼
        This data becomes:
        1. Quality signal for helpline directory
        2. Inbound sales ammo ("Your customers are struggling
           to reach you. 23 complaints this month via
           thebestbill. Let us handle this for you.")
```

**Decision tree builder (for future automation):**
- Start by manually building trees for top 10 product categories
- Each tree: 3-5 questions, multiple choice, with a free-text step at the end
- Over time: build a tool/agent that reads a brand's complaint form on their website and generates a decision tree from it

> [!NOTE]
> **The "complaint email for you" approach is killer for unregistered brands.** It's useful even if the brand never joins. The user gets a pre-written, detailed complaint email with all the right info — serial number, model, warranty status, issue details. That alone saves them 20 minutes of form-filling on the brand's broken website.

---

### C4. Helpline Directory

**Data model:**
```
helpline {
  brand_name,
  phone_number,
  hours,
  email,
  website,
  complaint_url (link to brand's complaint form),
  last_verified_date,
  user_ratings {
    total_calls,
    reached_count,
    avg_wait_time (user reported),
    is_working (boolean, based on recent ratings)
  }
}
```

**Initial build:**
- Manually collect for 50-100 brands
- Focus on: appliances, electronics, kitchen, home (your target categories)
- Sources: brand websites, Justdial, Google, customer care aggregator sites
- Verify: actually call each number once to check it works
- Store: brand's complaint form URL as well (many brands have online forms)

**Feedback loop:**
```
User calls helpline from our app
    ▼
After call, prompt appears:
    "Did you reach [Brand] support?"
    [Yes, resolved] [Yes, still pending] [Couldn't reach] [Wrong number]
    │
    ├── "Couldn't reach" / "Wrong number"
    │     → Flag for re-verification
    │     → If 3+ users report → mark as "potentially dead"
    │
    └── "Yes, resolved" / "Yes, pending"
          → "How long did you wait?"
          → [< 5 min] [5-15 min] [15-30 min] [30+ min]
```

This gives you a **crowd-verified helpline directory** over time. Way more valuable than any static listing.

---

### C5. Auth

```
User opens app for first time
    │
    ▼
Enter phone number
    │
    ▼
Send WhatsApp OTP (free/cheap via WhatsApp Business API)
    ├── Success → verify, login
    └── Failed (no WhatsApp / delivery issue)
          ▼
        Fall back to SMS OTP (₹0.15-0.30)
          ▼
        Verify, login
    │
    ▼
Phone number = primary identity
    ├── All auto-registered products linked by this phone
    └── Profile: name, email (optional), city
```

**Implementation**: Supabase Auth supports phone OTP out of the box. For WhatsApp OTP, you'd need a WhatsApp Business API provider (e.g., Gupshup, Wati, or Meta's Cloud API directly — free for first 1,000 conversations/month).

---

## Brand Side Specs

---

### B1. Onboarding a Brand (V1 = Concierge)

```
You find a brand (cold outreach / inbound signal)
    │
    ▼
"We'll handle your after-sales. Free for 3 months."
    │
    ▼
Brand says yes
    │
    ▼
YOU do the setup (not them):
    1. Go to their website → collect product catalog
    2. Enter into your system (CSV or manual)
    3. Get warranty terms from their website / ask them
    4. Get their support email + existing complaint form URL
    5. Upload their product manual PDFs (if available)
    6. Set up their dashboard account
    │
    ▼
Integration:
    ├── V1: Brand sends you a weekly CSV of new orders
    │         (or you get Shopify access and pull it yourself)
    │
    ├── V2: You build a Shopify plugin based on patterns
    │         you observed from manual integrations
    │
    └── V3: Public REST API for custom integrations
    │
    ▼
Go live:
    ├── Their new customers get auto-registered
    ├── Existing customers can scan invoices to add products
    └── All complaints routed through your system
```

> [!NOTE]
> **Pattern observation**: While doing 5-10 brands manually, you'll notice:
> - What data brands actually have vs. what you assumed
> - What format their order exports come in
> - What their existing service process looks like
> - Where the gaps are
>
> This is 100x more valuable than guessing an API spec in advance.

---

### B2. Brand Dashboard

**Day 1 features:**

```
┌─────────────────────────────────────────────────┐
│  [Brand Name] Dashboard                         │
│                                                 │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐          │
│  │ 247  │ │ 189  │ │  12  │ │  8   │          │
│  │Regis-│ │Active│ │Open  │ │Resol-│          │
│  │tered│ │Warr. │ │Req.  │ │ved   │          │
│  └──────┘ └──────┘ └──────┘ └──────┘          │
│                                                 │
│  Recent Registrations                           │
│  ┌─────────────────────────────────────────┐   │
│  │ Name    │ Product  │ Date   │ Warranty  │   │
│  │ Priya S.│ RO+UV    │ Today  │ 1 year   │   │
│  │ Arjun M.│ AC 1.5T  │ Today  │ 2 years  │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
│  Open Service Requests                          │
│  ┌─────────────────────────────────────────┐   │
│  │ #SRV-001 │ Priya S. │ RO low flow      │   │
│  │ Status: Sent to brand │ 2 hours ago     │   │
│  │                                         │   │
│  │ #SRV-002 │ Rahul G. │ AC not cooling   │   │
│  │ Status: Resolved │ Yesterday            │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
│  Product Feedback (auto-generated)              │
│  ┌─────────────────────────────────────────┐   │
│  │ "RO low flow" — 8 complaints this month│   │
│  │ "AC noise" — 3 complaints this month   │   │
│  │ Most affected model: GP-RO-2400        │   │
│  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

**Product feedback is the hidden value prop:**
- Brands don't have this data today
- Aggregate complaint data → "Your RO-2400 has a filter clogging issue. 8 of 247 units reported low flow in the last month."
- This makes you valuable even before you save them support costs

---

### B3. Service Request Lifecycle

```
Complaint created (from consumer app)
    │
    ▼
Status: "New"
    ├── Push to brand dashboard
    ├── Email to brand's service email
    │   (pre-formatted with all details)
    │
    ▼
Brand assigns / acts
    ├── [V1: manual] Brand handles from here
    │   using their existing process
    ├── Brand updates status in our dashboard:
    │   → "Assigned to [technician]"
    │   → "Scheduled [date]"
    │   → "Resolved"
    │
    ▼
Status updates flow back to consumer
    ├── "Your service request has been assigned"
    ├── "Technician visit scheduled for [date]"
    ├── "Service completed"
    │
    ▼
Post-resolution
    ├── Ask consumer: "Was this resolved? Rate the experience."
    ├── Data feeds back into brand dashboard
    └── Complaint pattern analysis auto-updates
```

---

## Cold Start Strategy

This is the biggest question. Both sides need each other.

**Your answer**: "It's both. Cold start problem."

Here's how to break the loop:

### Phase 0: Consumer-useful without ANY brands (Week 1-4)

The app must be useful with **zero brands onboarded.** This is how you break cold start.

```
Consumer downloads app
    ├── Scans invoices → products tracked
    ├── Warranty countdown works
    ├── Helpline directory works (50-100 brands)
    ├── Complaint form generates email/clipboard text
    ├── Document vault works
    │
    └── All of this works WITHOUT the brand being onboarded.
        The brand doesn't even know you exist yet.
        The consumer gets value on day 1.
```

**This is the wedge.** You're not asking brands to do anything. You're giving consumers a useful tool. The brand side comes later.

### Phase 1: Build inbound signal (Week 4-8)

```
Users add products from Brand X
    ▼
You track: "47 users have registered Brand X products"
    ▼
Automated email to Brand X:
    "47 of your customers are using thebestbill to track
    their [Brand X] products and manage warranty.

    Last month:
    - 12 tried to reach your support line (3 reported it as 'not working')
    - 8 filed complaints about [specific product issues]

    We can help you:
    - Auto-register warranties at checkout (100% registration rate)
    - Route support requests directly to your team
    - Give you real-time product feedback data

    Want to see a demo?"
```

**This email writes itself from real data.** That's the inbound flywheel.

### Phase 2: First brand (Week 6-10)

Simultaneously cold-outreach D2C brands:

1. Find brands on LinkedIn / IndiaMART / Amazon with bad after-sales reviews
2. DM founders: "I'll handle your entire after-sales for free for 3 months."
3. Concierge onboard them (you set up everything)
4. First integrated brand → their customers get auto-registration
5. Prove value: "Your support tickets dropped 40%. Your registration rate is 100%. Here's your product feedback dashboard."

### Phase 3: Flywheel (Month 3+)

```
More consumers
  → More inbound signals to brands
    → More brands onboard
      → More auto-registrations
        → Better consumer experience
          → More consumers
```

---

## Tech Stack (Final)

| Layer | Choice | Why |
|---|---|---|
| **Consumer app** | React Native (Expo) | You can code. Cross-platform. Free. Good camera/photo access. |
| **Brand dashboard** | Next.js on Vercel | Free hosting. SSR for SEO. Same JS skills. |
| **Backend/DB** | Supabase (Postgres + Auth + Storage + Edge Functions) | Free tier: 50K MAU, 500MB DB, 1GB storage. Raw SQL access. |
| **OCR** | Google Cloud Vision API | Free tier: 1,000 units/month. Accurate on Indian invoices. |
| **Push notifications** | Expo Push / Firebase Cloud Messaging | Free. |
| **WhatsApp OTP** | Meta Cloud API (direct) | Free for first 1,000 conversations/month. |
| **SMS fallback** | MSG91 | ₹0.15-0.20/SMS. Pay as you go. |
| **File storage** | Supabase Storage (S3-compatible) | Free 1GB. |
| **Hosting** | Vercel (dashboard) + Supabase (API) | Free tiers. |
| **Email sending** | Resend.com | Free 100 emails/day. For brand notifications + complaint emails. |

**Total cost at launch: ₹0/month** (within free tiers for first ~1,000 users)

---

## MVP Feature Checklist (Build Order)

Priority order — build in this sequence:

| # | Feature | What to build | Effort |
|---|---|---|---|
| 1 | Auth | WhatsApp OTP → SMS fallback. Phone = identity. | 2-3 days |
| 2 | Manual product add | Form: brand, product, serial, date, price. Store in DB. | 2-3 days |
| 3 | Invoice OCR | Camera → Google Vision → extract fields → user confirms. | 3-4 days |
| 4 | Product passbook | List of products with warranty countdown (green/yellow/red). | 2-3 days |
| 5 | Product detail | Serial, purchase info, warranty status, documents. | 1-2 days |
| 6 | Document vault | Upload/view invoice photos. Stored in Supabase Storage. | 1-2 days |
| 7 | Helpline directory | 50 brands with verified numbers. Searchable in-app. | 2-3 days (data collection) + 1 day (UI) |
| 8 | Complaint form (unregistered) | Decision tree → summary → pre-written email + helpline. | 3-4 days |
| 9 | Post-call feedback | "Did you reach them?" prompt after calling helpline. | 1 day |
| 10 | Warranty notifications | Push at 30d/7d/0d before expiry. | 1-2 days |
| 11 | Admin panel | Queue of unknown SKUs for manual warranty lookup. | 2-3 days |
| 12 | Brand dashboard (web) | Metrics + registrations + service requests + product feedback. | 4-5 days |
| 13 | Brand onboarding | CSV upload + manual product catalog entry. | 2-3 days |
| 14 | Complaint form (registered) | Same flow but sends structured request to brand + tracks status. | 2-3 days |
| 15 | Service request tracking | Status updates flow from brand dashboard → consumer app. | 2-3 days |
| 16 | Brand inbound email | Auto-email to brand when N users register their products. | 1 day |

**Total estimated: ~5-6 weeks of focused solo work.**

Items 1-11 = consumer app works standalone (no brands needed).
Items 12-16 = brand side (add when first brand is ready to onboard).

---

## What This Is NOT

Keeping this list to avoid scope creep:

- ❌ Not a chatbot. It's a conversational complaint form.
- ❌ Not an AI product. It's a data + workflow product with smart forms.
- ❌ Not a marketplace. We don't have technicians.
- ❌ Not a CRM. We don't manage customer relationships for brands.
- ❌ Not an extended warranty seller. No IRDAI headaches.

**What it IS:**
- ✅ A personal product tracker for consumers (useful alone)
- ✅ A complaint routing layer (makes existing brand support less painful)
- ✅ A product feedback dashboard for brands (valuable data they don't have)
- ✅ An after-sales API (eventually, once patterns are clear)
