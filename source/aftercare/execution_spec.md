# thebestbill — Execution Spec

> **What this is**: Product-aware WhatsApp support for brands that sell physical products. When a customer messages, we already know who they are, what they bought, warranty status, and service history.

> **One-liner to brands**: "Your customers message WhatsApp when something breaks. We make sure the conversation already has their product info, warranty status, and history — so your team fixes the problem instead of playing detective."

---

## The Product (One Sentence)

Register products at checkout → customer gets WhatsApp confirmation → when they message with an issue → bot greets them with full product context → structured complaint intake → clean ticket to brand → resolution tracking.

---

## How It Works (End to End)

### Phase 1: Product Registration

```
Brand sells product (online or offline)
    │
    ├── V1: Brand sends you CSV of orders (weekly/daily)
    ├── V2: Shopify plugin auto-triggers
    ├── V3: API call at checkout
    │
    ▼
You create records:
    ├── Product: Atomberg Gorilla 1200mm Ceiling Fan
    ├── Serial: ATM-GOR-1200-78234
    ├── Customer: Priya Sharma, +91 98765 43210
    ├── Purchase: Jun 5, 2025, ₹3,499, Amazon.in
    ├── Warranty: 3 years → expires Jun 5, 2028
    │
    ▼
Customer gets WhatsApp (from brand's number):
    "Hi Priya! 👋
     Your Atomberg Gorilla 1200mm is registered.
     Warranty valid until Jun 5, 2028 ✅
     Reply here anytime if you need help."
```

### Phase 2: Customer Messages With Issue

```
Customer (months later): "My fan is making a grinding noise"
    │
    ▼
System looks up customer by phone number
    ├── Found: Priya Sharma
    ├── Products: 1 registered (Gorilla 1200mm)
    ├── Warranty: Active (expires Jun 2028)
    ├── Previous complaints: None
    │
    ▼
Bot responds (branded as Atomberg):
    "Hi Priya! I can see your Atomberg Gorilla 1200mm.
     Warranty active until Jun 2028 ✅

     Let me help you quickly —
     What kind of noise?
     1️⃣ Grinding
     2️⃣ Clicking
     3️⃣ Humming
     4️⃣ Other"

Customer: "1"

Bot: "When did the grinding start?
     1️⃣ Today
     2️⃣ Few days ago
     3️⃣ Last week
     4️⃣ Longer"

Customer: "2"

Bot: "Got it. Anything else you'd like to mention?"

Customer: "It happens mostly at speed 3 and above"

Bot: "Thanks Priya. Here's your complaint summary:

     ┌───────────────────────────────┐
     │ 📋 Complaint #TBB-0042       │
     │                               │
     │ Product: Gorilla 1200mm       │
     │ Serial: ATM-GOR-1200-78234    │
     │ Issue: Grinding noise         │
     │ Started: Few days ago         │
     │ Detail: At speed 3 and above  │
     │ Warranty: Active ✅            │
     │ → Service visit covered free  │
     └───────────────────────────────┘

     I've sent this to Atomberg's service team.
     You'll hear back within 24 hours. 🔧"
```

### Phase 3: Brand Receives Complaint

```
Brand's service email / dashboard receives:

    Subject: [TBB-0042] Grinding noise — Gorilla 1200mm — Warranty Active

    Customer: Priya Sharma (+91 98765 43210)
    Product: Gorilla 1200mm (ATM-GOR-1200-78234)
    Purchased: Jun 5, 2025 (Amazon.in)
    Warranty: Active until Jun 2028

    Issue: Grinding noise, started few days ago, occurs at speed 3+

    Customer location: [from profile or asked]

    ---
    Reply with resolution status:
    → "assigned" / "scheduled [date]" / "resolved"
```

### Phase 4: Resolution Tracking

```
Brand replies: "scheduled Jun 10"
    │
    ▼
Customer gets WhatsApp:
    "Update on your complaint #TBB-0042:
     Technician visit scheduled for Jun 10.
     We'll confirm the time slot soon."

Brand replies: "resolved"
    │
    ▼
Customer gets WhatsApp:
    "Your complaint #TBB-0042 has been resolved! ✅
     Was the issue fixed to your satisfaction?
     1️⃣ Yes, all good
     2️⃣ Partially fixed
     3️⃣ Not fixed"
```

---

## What You Build (Layer by Layer)

### Layer 1: Manual Core (Week 1-2)

No code. Just you + WhatsApp Business + a spreadsheet.

| Component | Tool | What you do |
|---|---|---|
| Product database | Google Sheets | Brand gives you CSV of orders. You paste it in. Columns: customer name, phone, product, serial, purchase date, warranty end. |
| Registration message | WhatsApp Business (manual) | You send each customer a welcome message with product + warranty info. |
| Complaint intake | WhatsApp Business (manual) | Customer replies → you look up their phone in the sheet → you have context → you ask the diagnostic questions manually. |
| Complaint ticket | Email | You write a clean complaint email to the brand's service email with all details. |
| Resolution tracking | Google Sheets | Brand tells you status → you update sheet → you message customer. |

**This is the product. You are the product.** Everything you build later just automates what you're doing manually.

### Layer 2: Basic Automation (Week 3-6)

Build only what's drowning you.

| Component | Build | Why |
|---|---|---|
| Product database | Supabase (Postgres) | Sheets gets slow. You need search by phone number. |
| WhatsApp integration | WhatsApp Business API (via Meta Cloud API or Gupshup) | So bot can auto-respond to known customers with product context. |
| Complaint intake bot | Simple flow: greet with context → 3-4 questions → summary → confirm → send to brand | You're sending 50+ messages manually. Automate the repetitive parts. |
| Brand notification | Auto-email to brand when complaint is created | You're copy-pasting emails. Automate it. |
| Customer updates | Auto-message customer when brand updates status | You're the middleman. Automate the pass-through. |

### Layer 3: Dashboard (Month 2-3)

Build only when you have 3+ brands.

| Component | What it shows |
|---|---|
| Brand dashboard (web) | All complaints, resolution status, response times |
| Product feedback | "Top issues this month: Motor noise (8), Remote not working (3)" |
| Warranty overview | Active/expiring/expired breakdown |
| Registration log | Recent registrations, customer details |

### Layer 4: Scale Features (Month 3-6)

Build only when pulled by demand.

| Component | Trigger to build |
|---|---|
| Shopify plugin | When 3+ brands ask "can this be automatic?" |
| Auto-warranty-check | When bot is getting 10+ "is my warranty valid?" messages/day |
| Warranty expiry reminders | When you have 500+ registered products |
| Service dispatch | When a brand says "can you also assign the technician?" |
| Multi-brand consumer view | When customers with products from multiple brands ask "can I see everything in one place?" |

---

## Data Model

```
brand {
  id, name, logo, whatsapp_number,
  support_email, service_email,
  onboarded_date
}

product_catalog {
  id, brand_id, sku, name, category,
  warranty_months, description
}

customer {
  id, phone, name, email, city
}

registered_product {
  id, customer_id, brand_id, catalog_id,
  serial_number, purchase_date, purchase_price,
  retailer, warranty_end_date,
  warranty_status (active/expiring/expired)
}

complaint {
  id, registered_product_id, customer_id, brand_id,
  issue_type, issue_description, additional_notes,
  status (new/assigned/scheduled/resolved/closed),
  created_at, resolved_at,
  resolution_notes, customer_rating
}
```

---

## Tech Stack

| Layer | Choice | Cost |
|---|---|---|
| Database | Supabase (Postgres) | Free (50K rows, 500MB) |
| WhatsApp API | Meta Cloud API (direct) or Gupshup | Free first 1,000 conversations/month |
| Bot logic | Node.js on Supabase Edge Functions or Railway | Free tier |
| Brand dashboard | Next.js on Vercel | Free |
| Email notifications | Resend.com | Free (100/day) |
| File storage | Supabase Storage | Free (1GB) |
| **Total** | | **₹0/month until scale** |

---

## Pricing (to brands)

| Plan | Price | Includes |
|---|---|---|
| **Starter** | ₹5,000/month | Up to 200 registrations/month. WhatsApp bot. Complaint routing. Email notifications. |
| **Growth** | ₹12,000/month | Up to 1,000 registrations/month. Dashboard. Product feedback reports. Warranty reminders. |
| **Custom** | Contact | 1,000+ registrations. API access. Shopify plugin. Dedicated support. |

WhatsApp message costs passed through at cost (₹0.50-1.00/conversation).

**First 3 brands: FREE for 3 months.** You need them more than they need you. The data and learnings are worth more than ₹5K/month.

---

## What This Is NOT

- ❌ Not a consumer app (no app download, ever)
- ❌ Not a generic WhatsApp tool (built specifically for product-based after-sales)
- ❌ Not a chatbot platform (the bot is purpose-built for complaints, not general conversation)
- ❌ Not a CRM (you don't manage marketing or sales, just post-purchase)
- ❌ Not a service marketplace (you don't have technicians)
- ❌ Not AI anything (scripted flows, human fallback, no LLM needed)

## What This IS

- ✅ Product-aware WhatsApp support for brands
- ✅ Warranty registration that happens at checkout with zero customer effort
- ✅ Structured complaint intake that eliminates "what model do you have?"
- ✅ Product feedback data brands can't get anywhere else
- ✅ Infrastructure that makes the brand's existing support team faster
