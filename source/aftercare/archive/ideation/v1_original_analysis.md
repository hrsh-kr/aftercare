# After-Sales Infrastructure Platform — Ideation Document

> **One-liner**: The Stripe for after-sales — an API-first platform that powers warranty registration, service management, and AI-driven customer support for any brand, while giving consumers a single app to manage everything they own.

---

## 1. The Core Thesis

### The Analogy

| Before Stripe | Before [This Product] |
|---|---|
| Every company built its own payment system | Every company builds its own after-sales system |
| Fragmented, unreliable, expensive | Fragmented, unreliable, expensive |
| Stripe said: "Integrate our API, payments just work" | You say: "Integrate our API, after-sales just works" |
| Consumers got seamless checkout everywhere | Consumers get a unified ownership experience everywhere |

### Why After-Sales Is Broken Today

**For brands/companies:**
- Building after-sales systems is expensive and non-core (CRM, warranty tracking, service dispatch, call centers)
- Most D2C and mid-market brands have terrible post-purchase experiences
- Even large brands have fragmented systems — warranty is one team, service is another, support is another
- No standard exists. Every brand reinvents the wheel.

**For consumers:**
- Warranty registration is manual (fill forms, keep cards)
- Support means calling a number, waiting on hold, explaining everything from scratch
- Service history is lost between technician visits
- No single view of "everything I own and its status"

### The Insight

> After-sales is a **horizontal infrastructure problem**, not a vertical app problem. Just like payments, it should be abstracted into a platform that any company can plug into.

---

## 2. Two-Sided Architecture

```
┌─────────────────────────────────────────────────────┐
│                    YOUR PLATFORM                        │
│                                                         │
│  ┌──────────────────┐       ┌────────────────────────┐  │
│  │   BRAND SIDE     │       │    CONSUMER SIDE       │  │
│  │   (B2B API)      │       │    (B2C App)           │  │
│  │                  │       │                        │  │
│  │  • Dashboard     │◄─────►│  • Product passbook    │  │
│  │  • API / SDK     │       │  • Warranty status     │  │
│  │  • Webhooks      │       │  • AI assistant        │  │
│  │  • Analytics     │       │  • Service booking     │  │
│  │  • Service mgmt  │       │  • Support chat        │  │
│  └──────────────────┘       └────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │              SHARED LAYER                        │   │
│  │  • AI/Voice bots  • Warranty engine              │   │
│  │  • Service network • Notification system         │   │
│  │  • Document store  • Identity & auth             │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Product Breakdown

### 3A. Brand Side (B2B — the "Stripe Dashboard + API")

#### API & SDK
- **Warranty Registration API**: Brand calls `POST /warranty/register` at point of sale → customer auto-enrolled
- **Product Catalog API**: Brands upload product SKUs, warranty terms, service manuals
- **Service Ticket API**: Create, update, close service requests programmatically
- **Customer Lookup API**: Look up a customer's ownership + service history by phone/email
- **Webhooks**: Real-time events (warranty expiring, service completed, customer contacted)
- **Embeddable Widgets**: Drop-in warranty registration and support widgets for brand websites

#### Brand Dashboard
- **Warranty analytics**: Active warranties, expiry curves, claim rates
- **Service management**: Assign technicians, track SLAs, manage parts
- **Customer insights**: Product-wise NPS, repeat service rates, common issues
- **AI bot configuration**: Customize the AI assistant's knowledge base per brand (product manuals, FAQs, troubleshooting guides)
- **Communication hub**: Branded notifications to customers (service reminders, recalls, tips)

#### Integration Modes
1. **API-first**: Full programmatic control (for large brands with existing systems)
2. **Dashboard-only**: No-code setup for D2C brands (manually add products + warranties)
3. **POS Integration**: Plugin for Shopify, WooCommerce, retail POS systems — auto-register warranty at checkout
4. **Retailer Integration**: Amazon/Flipkart order sync → auto-registration

---

### 3B. Consumer Side (B2C — the "Ownership App")

#### Product Passbook
- **Automatic registration**: Buy from an integrated brand → product appears in your app instantly (linked by phone number/email)
- **Manual add**: Scan invoice / enter serial number for non-integrated brands
- **Product card**: Photo, brand, model, purchase date, warranty status, serial number, documents
- **Warranty timeline**: Visual countdown — green (active), yellow (expiring soon), red (expired)
- **Document vault**: Invoice, warranty card, service receipts — all attached to the product

#### AI Assistant (The Core Differentiator)
- **Troubleshooting**: "My AC is making a buzzing noise" → AI walks through diagnostics using the brand's product manual
- **Voice bot**: Call a single number → AI identifies you, knows your products, handles the issue or routes to a human
- **Smart booking**: "Book AC service" → AI checks warranty status, finds nearest authorized technician, books a slot
- **Proactive alerts**: "Your water purifier filter is due for replacement" (based on brand-defined schedules)
- **Multilingual**: Hindi, Tamil, Telugu, etc. — critical for India

#### Service Management
- **One-tap service booking**: Select product → describe issue → get a slot
- **Live tracking**: Technician en route, ETA, technician profile
- **Service history**: Full log of every service call, parts replaced, technician notes
- **Ratings & feedback**: Rate the service, automatically shared with brand

#### Ownership Features
- **Ownership transfer**: Selling a product? Transfer the record (with full history) to the buyer
- **Resale value**: "Your 2-year-old MacBook with full service history is worth ₹X"
- **Family sharing**: Shared household view — all family members' products in one place
- **Insurance integration**: Ownership proof for insurance claims

---

## 4. User Journeys

### Journey 1: Brand Integrates the Platform

```
Brand signs up → Gets API keys
    → Uploads product catalog + warranty terms
    → Integrates API at checkout (or uses Shopify plugin)
    → Configures AI bot (uploads manuals, FAQs)
    → Goes live

Customer buys from brand's website
    → Platform API called at checkout
    → Customer gets SMS: "Your [Product] is registered. Download the app to manage it."
    → Warranty, documents, support — all live instantly
```

### Journey 2: Consumer Warranty Claim

```
User opens app → Sees AC warranty expires in 2 months
    → AC stops cooling
    → Opens AI chat: "My AC isn't cooling"
    → AI: Asks model (already known), walks through basic checks
    → AI: "This looks like a compressor issue. Your warranty covers this. Shall I book a service visit?"
    → User confirms → Technician assigned → Slot booked
    → Technician arrives, fixes issue, logs parts replaced
    → User gets service summary in app
    → Brand sees the resolved ticket in their dashboard
```

### Journey 3: Non-Integrated Brand (Manual Add)

```
User buys a mixer from a local store
    → Opens app → "Add Product" → Scans invoice with camera
    → AI extracts: Brand, model, price, date, serial number
    → Product card created with warranty countdown
    → Generic AI support available (based on public product info)
    → If brand later integrates → record auto-enriched with official data
```

---

## 5. Competitive Landscape

| Player | What They Do | Why You're Different |
|---|---|---|
| **Onsitego** | Sells extended warranties at checkout | Point-of-sale only. Not infrastructure. No brand-side tools. |
| **OneAssist** | Extended warranties via bank partnerships | B2B distribution play. No consumer app. No AI support. |
| **Urban Company** | On-demand home services | Service marketplace, not warranty/ownership infra. No brand integration. |
| **Salesforce Service Cloud** | Enterprise service CRM | Massive, expensive, not built for product ownership. No consumer side. |
| **Zendesk/Freshdesk** | Support ticketing | Generic support tools. No warranty logic, no product awareness. |
| **Brand apps** (Samsung, LG) | Own ecosystem | Siloed. Only works for one brand. |

### Your Unique Position

**None of these are infrastructure.** They're either point solutions (sell a warranty), service marketplaces (send a technician), or generic CRM tools.

You are the **only player building the horizontal layer** that connects brands, consumers, and service providers around the concept of product ownership.

---

## 6. Business Model

### Revenue Streams

| Stream | How It Works | Potential |
|---|---|---|
| **SaaS fees (primary)** | Brands pay per registered product or monthly platform fee | ₹1-5 per warranty registration, or ₹10K-1L/mo tiered plans |
| **AI bot usage** | Per-conversation or per-resolution pricing for AI support | ₹5-20 per AI interaction |
| **Extended warranty commission** | Sell extended warranties at expiry → 25-40% commission | ₹500-2,000 per policy |
| **Service network commission** | Take 10-15% cut on service bookings routed through platform | Per-transaction |
| **Data & insights** | Anonymized product lifecycle data sold to brands/insurers | Enterprise tier |
| **Premium consumer tier** | Priority support, extended features for power users | ₹199-499/year |

### Pricing Philosophy

> **Free for consumers. Always.** The consumer app is the distribution moat — the more consumers use it, the more brands *must* integrate.

> **Freemium for brands.** Free tier for small D2C brands (up to 500 registrations/month). Paid tiers scale with usage.

### Unit Economics Target (Per Registered Product)

```
Average warranty registration fee:        ₹3
AI interactions over product lifetime:     ₹15 (3 interactions × ₹5)
Extended warranty conversion (10% rate):   ₹150 (₹1,500 premium × 40% commission × 10%)
Service booking commission (20% rate):     ₹100 (₹2,500 service × 10% commission × 40%)
────────────────────────────────────────────
Lifetime value per product:               ~₹268

At 1M registered products/year:           ~₹26.8 Cr (~$3.2M ARR)
```

---

## 7. Technical Architecture (High Level)

```
┌─────────────────────────────────────────────────────────────┐
│                      CLIENT LAYER                           │
│                                                             │
│  Consumer App          Brand Dashboard       Embeddable     │
│  (React Native)        (React/Next.js)       Widgets (JS)   │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                      API GATEWAY                            │
│           (REST + GraphQL, Rate Limiting, Auth)             │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    CORE SERVICES                            │
│                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │
│  │ Product  │ │ Warranty │ │ Service  │ │ Notification │  │
│  │ Registry │ │ Engine   │ │ Manager  │ │ Service      │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘  │
│                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │
│  │ Identity │ │ Document │ │ AI/Bot   │ │ Analytics    │  │
│  │ Service  │ │ Store    │ │ Engine   │ │ Engine       │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    DATA LAYER                               │
│                                                             │
│  PostgreSQL    Redis    S3/GCS     Vector DB    Pub/Sub     │
│  (core data)   (cache)  (docs)    (AI/RAG)     (events)    │
└─────────────────────────────────────────────────────────────┘
```

### Key Technical Bets

- **AI/RAG for product support**: Ingest brand manuals + FAQs → AI can troubleshoot per-product. This is the moat — the more brands upload docs, the smarter the AI gets.
- **Voice AI**: Telephony integration (e.g., via Twilio/Exotel) for voice-based support in regional languages. Critical for India's tier-2/3 market.
- **OCR + Document AI**: For manual invoice scanning — extract structured data from messy Indian invoices (GST bills, handwritten receipts).
- **Event-driven architecture**: Warranty expiry, service reminders, proactive maintenance — all powered by a robust event/scheduling system.

---

## 8. Go-to-Market Strategy

### Phase 1: Nail the Wedge (Month 1-6)

**Target**: 10-20 D2C appliance brands in India (water purifiers, kitchen appliances, home electronics)

**Why D2C?**
- They're already selling direct → easy API integration at checkout
- They lack after-sales infrastructure (no service centers, thin support teams)
- They're desperate to differentiate on experience
- Examples: Aquaguard (Eureka Forbes), Havells, Crompton, Cello, Prestige

**Playbook**:
1. Build the core platform (warranty registration API + consumer app + AI bot)
2. Offer free pilot to 5 brands → "We'll handle your entire after-sales for free for 3 months"
3. Prove value: reduced support tickets, higher NPS, warranty claim automation
4. Convert to paid plans

### Phase 2: Expand Categories (Month 6-12)

- Consumer electronics (headphones, speakers, wearables)
- Furniture / mattresses (long warranty, service-heavy)
- EV / e-bikes (emerging category, complex after-sales)

### Phase 3: Retailer Integration (Month 12-18)

- Integrate at the retailer level (Croma, Reliance Digital, Vijay Sales)
- Every product sold through integrated retailers → auto-registered
- This is the "Stripe is everywhere" moment

### Phase 4: Platform Effects (Month 18+)

- Service provider marketplace (authorized + independent technicians)
- Extended warranty / insurance marketplace
- Ownership transfer / resale verification
- Open API for third-party integrations (insurance companies, resale platforms)

---

## 9. YC Pitch Framing

### The Pitch (2 minutes)

> "After-sales is a $X billion industry, and it runs on the same infrastructure as 2005 — call centers, paper warranties, and spreadsheets.
>
> We're building the Stripe for after-sales. Brands integrate our API at checkout, and their customers automatically get warranty registration, AI-powered support, service booking, and a complete ownership record — all through one app.
>
> For brands, we replace their entire after-sales stack — CRM, warranty tracking, call center, service management — with a single API.
>
> For consumers, we're building the app where you manage everything you own. Every product, every warranty, every service call — one place.
>
> We're starting with home appliances in India — a market where 500M+ appliances are sold annually, and after-sales is completely broken.
>
> We're live with [X] brands, [Y] products registered, and our AI bot has resolved [Z]% of support queries without human intervention."

### Why Now?

1. **AI is finally good enough** for multilingual voice + text support — this wasn't possible 2 years ago
2. **D2C explosion in India** — thousands of new brands with zero after-sales infra
3. **India's smartphone penetration** — consumers ready for app-based ownership management
4. **UPI/digital payments proved** consumers will adopt infrastructure platforms (just like they adopted UPI over cash)

---

## 10. Risks & Open Questions

### Critical Risks

| Risk | Mitigation |
|---|---|
| **Cold start problem**: Need brands for consumer value and consumers for brand value | Start B2B-first. Brands get immediate value (AI support, warranty automation) even with zero consumer app users. |
| **Brands won't share customer data** | You're not taking their customers — you're powering their experience. Position as infrastructure, not intermediary. |
| **Large brands build in-house** | Target mid-market / D2C who can't afford to build. By the time large brands notice, you have the network. |
| **Consumer app adoption** | Make it auto-register (SMS link at purchase). Don't require app download for basic features (web-based). |

### Open Questions to Resolve

> [!IMPORTANT]
> **1. What's the product name / brand?** The name matters a lot for a B2B2C play. It needs to feel trustworthy to consumers AND professional to brands.

> [!IMPORTANT]
> **2. Do you own the service network or partner?** Owning technicians = high quality but capital intensive. Partnering = faster scale but less control. Recommendation: Start with brand-authorized technicians (brands already have them), then expand.

> [!IMPORTANT]
> **3. Regulatory considerations?** If you sell/facilitate extended warranties, you may need IRDAI (insurance regulator) compliance in India. Warranty management (without selling insurance products) is likely fine.

> [!IMPORTANT]
> **4. How do you handle non-integrated brands?** Pure OCR/manual add? Or do you proactively onboard brands when consumers add their products? (This could be a powerful inbound sales signal — "50 of your customers already added your products manually, let us automate this.")

> [!IMPORTANT]
> **5. What's your founding team composition?** This needs strong full-stack engineering (API platform), AI/ML (bot, OCR, RAG), and someone who can sell to brands (B2B sales). What do you have today?

---

## 11. The Moat (Long-Term Defensibility)

```
Year 1: Build the infrastructure. Get 50 brands live.
         → You have the best product ownership dataset in India.

Year 2: 500+ brands, millions of registered products.
         → Consumer app becomes the default "ownership" app.
         → Brands MUST be on your platform because consumers expect it.

Year 3: You ARE the ownership layer of commerce.
         → Insurance companies use your data for underwriting.
         → Resale platforms use your records for verification.
         → Service providers list on your marketplace.
         → New brands integrate on day one, like they do with Razorpay.

The moat is the network: More brands → more consumer value → more consumers → more brand value.
This is the same flywheel as Stripe, Razorpay, and UPI.
```

---

## 12. Comparable Companies (for YC Reference)

| Company | Analogy | Valuation |
|---|---|---|
| **Stripe** | "Infra for payments" → You are "Infra for after-sales" | $50B+ |
| **Razorpay** | India's payment infra | $7.5B |
| **Asurion** | Extended warranty provider (US) | $10B+ |
| **Extend** (YC W19) | Extended warranty API for e-commerce | Raised $260M+ |
| **Clyde** | Warranty-as-a-service for e-commerce | Acquired by Assurant |

> [!NOTE]
> **Extend** (extend.com) is the closest US comparable — they sell extended warranties via API for e-commerce. But they're purely a warranty sales tool, not a full after-sales platform. Your vision is significantly broader: warranty + support + service + AI + consumer app.
