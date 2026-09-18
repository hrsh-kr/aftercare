# thebestbill — Problem Mapping & Messaging Framework

---

## Part 1: Mapping the Problem

### Consumer Side — The Problem

**What's broken today:**

| Problem | Reality |
|---|---|
| Dead support lines | You call the number on the warranty card. It's disconnected, or rings forever, or goes to a generic IVR maze. |
| Non-working support sites | Brand website says "Register your product" — the form is broken, the portal is from 2012, or it asks for 15 fields you don't have. |
| Long forms to fill | Warranty registration means entering serial numbers, uploading invoices, filling addresses — most people just don't do it. |
| Lost documents | Invoice is in email, warranty card is in a drawer, serial number is on a sticker behind the appliance. When you need them, you can't find them. |
| No single view | You own 20 products from 15 brands. There's no one place to see everything. |
| Repeating yourself | Every time you call support, you re-explain: what product, when purchased, what's wrong, what was already tried. |
| No service memory | Technician came 3 months ago. What did he replace? What was the cost? Nobody remembers. |

**Where we're at a disadvantage (honest mapping):**

| Disadvantage | Why it matters |
|---|---|
| Call centres are dirt cheap in India | Brands can staff a 24/7 helpline for ₹15-20K/seat/month. "Just call us" is the default answer. |
| Talking to a human is more reassuring | Especially for older demographics and tier-2/3 cities — people trust a voice over an app/chatbot. |
| Habit of WhatsApp/phone for everything | People already forward invoices on WhatsApp, call their "AC guy" directly. Why change behavior? |
| Brands don't see after-sales as a priority | "We sell products, not support. Support is a cost center." Hard to get budget allocation. |
| Low willingness to pay for consumer apps | Indian consumers rarely pay for utility apps. Free is the expectation. |
| Trust gap with new platforms | "Why should I give my purchase data to some startup?" |

---

### Brand Side — The Problem

**What's broken today:**

| Problem | Reality |
|---|---|
| Fragmented systems | Warranty is in one system, service in another, support in a third. CRM doesn't talk to service desk. |
| No visibility into ownership | Brand has no idea who owns their products, when they were bought, or what issues they face — unless the customer calls. |
| Support = cost center | Every support call costs ₹50-150. Most calls are for simple things (warranty status, troubleshooting steps) that don't need a human. |
| Manual warranty registration | Paper cards, forms, QR codes that nobody scans. Registration rates are 10-20% at best. |
| Service network is opaque | Brand assigns a technician. Customer has no tracking, no ETA, no visibility. Technician has no product history. |
| No feedback loop | Product is defective → customer calls → support logs a ticket → but the product team never sees the pattern. Months pass before anyone notices a batch issue. |
| D2C brands have nothing | Small D2C brands selling on Amazon/Flipkart have zero after-sales infra. When a customer has an issue, they email and pray. |

**Where we're at a disadvantage (brand side):**

| Disadvantage | Why it matters |
|---|---|
| "We already have a CRM" | Large brands use Salesforce/Zoho. They don't want another tool. |
| Resistance to API integration | Engineering teams are stretched. "Add one more API call at checkout" sounds simple but gets deprioritized. |
| Data ownership concerns | "You want our customer data flowing through your system?" Brands are protective. |
| Enterprise sales cycles | Large brands take 6-12 months to onboard anything. Long sales cycles = cash burn. |
| Existing relationships with service partners | Brands have contracts with Jeeves, OnSiteGo, etc. Switching costs are real. |

---

## Part 2: The Framework

### For Consumers

#### 1. What are we solving?

The post-purchase chaos. After you buy something, you're on your own. Warranty cards get lost, support lines don't work, you forget when you bought what, and when something breaks — you spend more time finding the invoice than fixing the product.

We're solving **ownership memory** — the gap between buying a product and being able to get help with it later.

#### 2. Who are we solving for?

> [!NOTE]
> **The Callout (Consumer)**
>
> You own a bunch of appliances and electronics. Your AC, water purifier, washing machine, laptop, phone. You bought them from different places — Amazon, Croma, the local dealer. Every purchase came with a paper invoice, a warranty card you never registered, and a support number you can't find anymore.
>
> Now something breaks. The AC stops cooling, the water purifier flow drops. You dig through your email for the invoice. You Google the brand's support number — the first one is disconnected, the second puts you on hold for 20 minutes. When someone finally picks up, they ask for your model number, serial number, purchase date — you have none of it handy.
>
> You've been here before. Multiple times. With different products. And every single time, it's the same frustrating experience from scratch.

**Who specifically**: 25-45 year old urban Indian homeowners who own 5+ products across multiple brands, are comfortable with apps, and are tired of the broken support experience.

#### 3. How are we solving?

**The good stuff you get:**

| What you get | Details |
|---|---|
| ✅ One app for everything you own | Every product, every brand — one place. Like Splitwise for your stuff. |
| ✅ Automatic registration | Buy from an integrated brand → product appears in your app. No forms, no QR codes. |
| ✅ Warranty tracking that actually works | Visual countdown. Notifications before expiry. Never get caught off-guard. |
| ✅ AI that knows your products | "My RO has low flow" → AI knows which RO, when you bought it, last filter change, warranty status. No repeating yourself. |
| ✅ Service booking in 2 taps | AI diagnoses → books a technician who's serviced your unit before. No phone tag. |
| ✅ Helpline numbers that actually work | For brands not on our platform — verified, tested toll-free numbers. Not the dead ones from Google. |
| ✅ All your documents, always findable | Invoice, warranty card, service receipts — attached to each product. Search by product, not by folder. |

**The bad stuff you avoid:**

| What you avoid | Details |
|---|---|
| 🚫 Digging through email for invoices | Never search "Amazon invoice refrigerator 2023" again. |
| 🚫 Dead support lines | No more calling a number that rings forever or is disconnected. |
| 🚫 Filling long registration forms | No more 15-field warranty registration forms that ask for your blood type. |
| 🚫 Repeating yourself to every support agent | No more "what model? what serial number? when did you buy it?" |
| 🚫 Forgetting warranty expiry | No more discovering your warranty expired 2 weeks ago when you need it most. |
| 🚫 Losing service history | No more "the technician came last time and did something, I don't remember what." |
| 🚫 Guessing who to call | No more Googling "Daikin support number India" and trying 3 different numbers. |

#### 4. Unique Mechanism / Differentiator

**The mechanism**: Dual-mode AI — works whether the brand is on our platform or not.

- **Registered brands**: AI has full product context, warranty status, service history. It diagnoses issues, creates service requests automatically, and books technicians who know your unit.
- **Unregistered brands**: AI still helps. It scans your invoice, tracks your warranty, runs diagnostic questions, and gives you the verified helpline number with pre-formatted details to mention on the call.

**Promise**: "Open one app. Get help with any product. Whether the brand is on our platform or not."

**Proof**: [Demo at localhost:5173/app — show both AI chat flows]

**Plan** (steps for the consumer):
1. Download app / open web app
2. Products from integrated brands appear automatically (linked by phone number)
3. For other products — scan invoice, AI extracts everything
4. When something breaks — open AI chat, describe the issue
5. AI handles the rest (books service or gives you the right number + details)

---

### For Brands

#### 1. What are we solving?

The after-sales stack. You sell great products. But your post-purchase experience is held together with duct tape — a CRM that doesn't know warranty status, a call center that costs more than your margins, registration rates below 20%, and zero visibility into what your customers actually experience after they buy.

We're solving **after-sales infrastructure** — the entire system between "customer buys product" and "customer is happy with product."

#### 2. Who are we solving for?

> [!NOTE]
> **The Callout (Brand)**
>
> You're a D2C or mid-market brand selling appliances or electronics in India. You've figured out how to build great products and sell them online. But the moment a customer buys, your visibility ends.
>
> You don't know if they registered the warranty (they probably didn't — your registration rate is 10-15%). You don't know if they had a problem (unless they called your overloaded support line). You don't know if the technician actually showed up, or what was done.
>
> Your support team spends 60% of their time on calls that don't need a human — "is my warranty still valid?", "when was my last service?", "what's the model number for filters?". Your service costs are eating into your margins. And your NPS is lower than you'd like because customers feel abandoned after the sale.
>
> You've thought about building something in-house. But your engineering team is already stretched. You'd need warranty logic, a customer portal, a service dispatch system, a chatbot, notifications — that's 6-12 months of dev time you don't have.

**Who specifically**: Indian D2C and mid-market brands (₹10Cr-500Cr revenue) selling home appliances, electronics, or any product with warranty + service needs. Engineering team of 5-20. No dedicated after-sales tech.

#### 3. How are we solving?

**The good stuff you get:**

| What you get | Details |
|---|---|
| ✅ 100% warranty registration | One API call at checkout. Every product registered. No forms, no QR codes, no 10-15% rates. |
| ✅ AI handles 60%+ of support | Trained on your product manuals. Answers warranty questions, troubleshoots issues, books service — without a human. |
| ✅ Service management out of the box | Technician assignment, SLA tracking, customer notifications. No building your own. |
| ✅ Real-time product intelligence | See which products have the most issues, which technicians are underperforming, which regions need attention. |
| ✅ Your customers love the experience | They get an app-based experience with tracking, history, and AI support. Your NPS goes up. |
| ✅ 15-minute integration | One API call at checkout. Shopify plugin. WooCommerce plugin. Not a 6-month project. |

**The bad stuff you avoid:**

| What you avoid | Details |
|---|---|
| 🚫 Building it yourself | No more 6-12 month dev projects for warranty tracking, service dispatch, chatbots. |
| 🚫 Call center costs for basic queries | No more paying ₹50-150/call for "is my warranty valid?" — AI handles it free. |
| 🚫 10% registration rates | No more paper warranty cards and forms nobody fills. |
| 🚫 Blind spots post-purchase | No more guessing what customers experience after the sale. |
| 🚫 Fragmented systems | No more warranty in Excel, service in email, support in Freshdesk. One dashboard. |
| 🚫 Customers calling angry | No more customers calling after 20 minutes on hold, already frustrated. They got help from AI first. |

#### 4. Unique Mechanism / Differentiator

**The mechanism**: One API call replaces your entire after-sales stack.

You don't build a warranty system, a support chatbot, a service dispatch tool, a customer portal, and a notification system. You call one API at checkout — and your customer gets all of it instantly. Like Stripe replaced payment gateways, we replace the after-sales stack.

**Promise**: "One API call at checkout. Your customers get warranty tracking, AI support, and service booking — overnight. Not in 6 months."

**Proof**: [Demo at localhost:5173/dashboard — show the brand dashboard with live metrics]

**Plan** (steps for the brand):
1. Sign up, get API keys (`tbb_live_`, `tbb_test_`)
2. Add product SKUs + warranty terms in dashboard
3. Add one API call at checkout (or install Shopify/WooCommerce plugin)
4. Upload product manuals for AI training
5. Go live — customers start getting auto-registered with AI support

---

## Part 3: The One-Liners

### Consumer One-Liner

> **I help** Indian homeowners who own multiple products across brands
> **get** instant AI support, warranty tracking, and service booking for everything they own
> **without** digging through emails for invoices, calling dead support lines, or filling long registration forms
> **through** a single app that works for every brand — whether they're on our platform or not.

**Short version**: "One app for every product you own. AI support for any brand."

---

### Brand One-Liner

> **I help** D2C and mid-market appliance brands in India
> **get** 100% warranty registration, AI-powered support, and service management
> **without** building it themselves, staffing call centers for basic queries, or spending 6 months on a dev project
> **through** a single API call at checkout that replaces their entire after-sales stack.

**Short version**: "One API call at checkout. After-sales just works."

---

## Part 4: The Combined Pitch

> **thebestbill is the Stripe for after-sales.**
>
> Brands add one API call at checkout — their customers instantly get warranty tracking, AI-powered support, and service booking through a single app.
>
> For brands on the platform: AI auto-diagnoses issues, books technicians, and manages warranty claims.
> For brands NOT on the platform: we still help consumers with verified helpline numbers and product tracking.
>
> **We're not asking consumers to change behavior. We're making the existing behavior work.**
> They already buy products. They already lose invoices. They already call support numbers that don't work. We just make all of it work from one place.
