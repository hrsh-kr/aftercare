# thebestbill — Product Ideation

---

## What Is thebestbill

After-sales infrastructure. Two sides, one platform.

| Side | What they get |
|---|---|
| **Consumers** | One app for all products. Warranty tracking, complaint routing, helpline directory — works for any brand, onboarded or not. |
| **Brands** | Product registration at checkout. Dashboard with warranty analytics, service intake, product feedback data. |

**Core insight**: After-sales is a horizontal infrastructure problem. Every brand reinvents the same stack — warranty tracking, support, service dispatch. This should be a shared platform, not a per-brand build.

**The dual-mode**: Unlike every other player, the app works even if the brand is NOT onboarded. Consumers get value on day 1. Brand onboarding unlocks more value, but isn't required.

---

## The Problem

### Consumer Side

| Problem | Reality |
|---|---|
| Dead support lines | Number on warranty card is disconnected, or rings forever, or is an IVR maze. |
| Non-working support sites | Brand's "Register your product" form is broken, ancient, or asks for 15 fields. |
| Long forms | Warranty registration = serial numbers + invoices + addresses. Most people skip it. |
| Lost documents | Invoice is in email, warranty card is in a drawer, serial number is behind the appliance. |
| No single view | 20 products, 15 brands, no one place to see everything. |
| Repeating yourself | Every support call: re-explain product, purchase date, issue, what you tried. |
| No service memory | Technician came 3 months ago. What was replaced? What did it cost? |

### Brand Side

| Problem | Reality |
|---|---|
| Fragmented systems | Warranty in one system, service in another, support in a third. |
| No ownership visibility | Brand has no idea who owns their products unless the customer calls. |
| Support = cost center | Every call costs ₹50-150. Most are simple things (warranty status, basic troubleshooting). |
| 10-20% registration rates | Paper cards, QR codes nobody scans. |
| Opaque service network | Brand assigns technician. Customer has no tracking. Technician has no product history. |
| No feedback loop | Product defect → customer calls → ticket logged → product team never sees the pattern. |
| D2C brands have nothing | Small brands on Amazon/Flipkart have zero after-sales infra. |

### Our Disadvantages (Honest)

| Consumer side | Brand side |
|---|---|
| Call centres are dirt cheap in India (₹15-20K/seat/month) | "We already have a CRM" (Salesforce/Zoho) |
| Talking to a human is more reassuring | Resistance to API integration (eng teams stretched) |
| WhatsApp/phone habit for everything | Data ownership concerns |
| Low willingness to pay for consumer apps | Enterprise sales cycles (6-12 months) |
| Trust gap with new platforms | Existing service partner contracts |

---

## The Framework

### Consumer

**What we solve**: Ownership memory — the gap between buying a product and being able to get help with it later.

**Who (callout)**: 25-45 year old urban Indian homeowners who own 5+ products across brands, comfortable with apps, tired of the broken support experience.

**Good stuff you get:**
- One app for everything you own
- Warranty tracking with countdown + expiry notifications
- Complaint routing (auto to brand if onboarded, helpline + pre-written email if not)
- Verified helpline directory
- All documents attached to each product

**Bad stuff you avoid:**
- Digging through email for invoices
- Dead support lines
- Filling 15-field registration forms
- Repeating yourself to every agent
- Forgetting warranty expiry
- Losing service history

**Unique mechanism**: Dual-mode — works for onboarded AND non-onboarded brands. You get value regardless.

**One-liner**: *"One app for every product you own. Complaint routing for any brand."*

---

### Brand

**What we solve**: After-sales infrastructure — the system between "customer buys" and "customer is happy."

**Who (callout)**: Indian D2C and mid-market brands (₹10Cr-500Cr revenue) selling appliances/electronics. Engineering team of 5-20. No dedicated after-sales tech.

**Good stuff you get:**
- 100% warranty registration (at checkout, zero friction)
- Complaint intake via conversational form (reduces support calls)
- Service request tracking + resolution data
- Product feedback data (aggregate complaint patterns → product intelligence)
- 15-minute integration (one API call or CSV upload)

**Bad stuff you avoid:**
- Building warranty/service/support systems yourself (6-12 month dev project)
- Call center costs for basic queries
- 10% registration rates
- Post-purchase blind spots
- Customers calling already frustrated

**Unique mechanism**: One integration point replaces the entire after-sales stack.

**One-liner**: *"One API call at checkout. After-sales just works."*

---

## Core Flows

### Flow 1: Brand Registers a Product at Checkout

```
Brand's checkout system
    │
    ▼
POST /v1/products/register
    { customer_phone, product_sku, serial_number, purchase_price }
    │
    ▼
Backend
    ├── Creates product record
    ├── Creates warranty record (duration from brand's SKU config)
    ├── Links to customer by phone number
    │
    ▼
Customer gets notification
    "Your [Product] is registered. Warranty valid until [date]."
    │
    ▼
Product appears in consumer app
```

### Flow 2: Consumer Reports Issue — Onboarded Brand

```
User opens "Get Help" on a product
    │
    ▼
Conversational complaint form (decision tree)
    ├── Step 1: "What's going on?" → [Not cooling / Leaking / Noise / ...]
    ├── Step 2: "When did this start?" → [Today / Few days / Week / Longer]
    ├── Step 3: Product-specific question
    ├── Step 4: "Anything else?" → Free text
    │
    ▼
Complaint summary generated
    ├── Product details (model, serial, warranty status)
    ├── Issue details (type, duration, specifics)
    ├── Location + purchase date
    │
    ▼
Structured request sent to brand
    ├── Via API (if brand has integration) or email
    ├── Tracked in our system
    ├── User gets: "Request sent. Ref: #SRV-XXXX"
    │
    ▼
Status updates flow back to consumer
```

### Flow 3: Consumer Reports Issue — NOT Onboarded Brand

```
Same conversational complaint form
    │
    ▼
Same complaint summary generated
    │
    ▼
Two options presented:
    │
    ├── 📧 Pre-written complaint email
    │     To: customercare@brand.co.in
    │     Subject: Service Request - [Issue] - [Model]
    │     Body: [All details pre-filled]
    │     [Send Email] [Copy to Clipboard]
    │
    └── 📞 Verified helpline
          Number: 1860-180-XXXX
          Hours: Mon-Sat, 9 AM – 6 PM
          "Mention: Model [X], Serial [Y], Issue: [Z]"
    │
    ▼
After interaction, ask user:
    "Did you reach them?" → [Resolved / Still waiting / Couldn't reach]
    │
    ▼
This data becomes:
    1. Helpline quality signal
    2. Inbound sales ammo to onboard the brand
```

### Flow 4: Consumer Adds Product Manually

```
User taps "Add Product"
    │
    ├── 📸 Take photo of invoice
    │     → OCR extracts: brand, product, serial, date, price
    │     → User reviews + corrects
    │
    └── ✍️ Manual form fallback
          Brand, Product, Serial, Date, Price
    │
    ▼
Warranty lookup
    ├── SKU in our DB? → use stored duration
    └── Unknown? → flagged for manual lookup
        (person checks web, enters warranty info)
    │
    ▼
Product card created with warranty countdown
```

### Flow 5: Warranty Expiry Tracking

```
30 days before → Push notification + card turns yellow
7 days before → Push notification
Expiry day → Notification + card turns red
Post-expiry → Service requests note "warranty expired"
```

### Flow 6: Brand Dashboard

```
Service request lands in dashboard
    ├── Customer, product, issue, diagnosis
    ├── Warranty status
    │
    ▼
Brand handles assignment (their existing process)
    │
    ▼
Status updates → flow back to consumer app
    │
    ▼
Product feedback (auto-generated):
    "RO-2400 — 8 complaints about low flow this month"
```

---

## V1 Scope

### ✅ In V1

| Feature | Approach |
|---|---|
| Product registration | Manual concierge first (CSV/direct setup). API later. Shopify plugin when patterns clear. |
| Consumer product passbook | Mobile app (React Native). Phone OTP login (WhatsApp first, SMS fallback). |
| Manual product add | Photo OCR (Google Vision) + manual form fallback. |
| Warranty tracking | Brand-defined per SKU. Unknown SKUs → manual lookup (mechanical turk). Multi-component supported. |
| Complaint form (onboarded) | Per-product decision tree → structured request to brand (API or email). |
| Complaint form (not onboarded) | Same form → pre-written complaint email + verified helpline. |
| Helpline directory | 50-100 brands, manually verified. Post-call "did this number work?" feedback. |
| Document storage | OCR + structured. Original photo/PDF stored. |
| Brand dashboard | Overview metrics + registrations + service requests + product feedback. Web app. |
| Notifications | Push + in-app. WhatsApp later. SMS last. |

### ❌ Not in V1

- Voice bot / telephony
- Ownership transfer / resale
- Family sharing
- Insurance integration
- Service provider marketplace
- Extended warranty sales
- Retailer POS integration
- Technician assignment (brand handles it)
- Multilingual (English + Hindi only)

---

## Diagnostic Question Trees

### Water Purifier
1. What issue? → [Low flow / Bad taste / Leaking / Not turning on / Noise / Other]
2. When noticed? → [Today / Few days / Week / Longer]
3. Last filter change? → [<3mo / 3-6mo / 6-12mo / Don't remember]

### Air Conditioner
1. What issue? → [Not cooling / Water leak / Noise / Bad smell / Not turning on / Other]
2. When noticed? → [Today / Few days / Week / Longer]
3. Outdoor unit running? → [Yes normal / Yes noisy / No / Not sure]

### Washing Machine
1. What issue? → [Not draining / Vibrating / Not spinning / Error code / Leaking / Other]
2. When noticed? → [Today / Few days / Week / Longer]
3. Load size? → [Half / Full / Overloaded / Normal]

### General (fallback)
1. What issue? → [Free text]
2. When noticed? → [Today / Few days / Week / Longer]
3. Any error codes/lights? → [Yes (describe) / No]

---

## Helpline Directory (Starter)

| Brand | Toll-free | Hours | Category |
|---|---|---|---|
| Daikin | 1860-180-3900 | Mon-Sat 9AM-6PM | AC |
| Samsung | 1800-40-7267864 | 24/7 | Electronics |
| Apple | 000-800-040-1966 | 24/7 | Electronics |
| LG | 1800-315-9999 | Mon-Sun 8AM-8PM | Electronics |
| Whirlpool | 1800-208-1800 | Mon-Sun 8AM-8PM | Appliances |
| Bosch | 1800-266-1880 | Mon-Sat 8AM-8PM | Appliances |
| Philips | 1800-102-2929 | Mon-Sat 9AM-6PM | Electronics |
| Havells | 1800-103-1313 | Mon-Sat 9AM-6PM | Electrical |
| Prestige | 1800-425-0505 | Mon-Sat 9AM-6PM | Kitchen |
| Crompton | 1800-419-0505 | Mon-Sat 9AM-6PM | Fans/Pumps |

Growth: User adds product from brand X → we track count → at 50+ products → inbound sales signal to onboard that brand.

---

## Starting Wedge

**Target**: 10 D2C appliance brands in India (water purifiers, kitchen, home electronics).

**Why these**: Selling direct, lack after-sales infra, desperate to differentiate, high service frequency.

**First pitch**: "We'll handle your after-sales for free for 3 months."

**Cold start strategy**:
1. Consumer app works without any brands (scan invoice, track warranty, get helpline, get pre-written complaint email)
2. Users adding unregistered brand products = demand signal
3. Auto-email to brand: "47 of your customers track your products on thebestbill. Let us automate this."
4. Simultaneously cold-outreach D2C founders on LinkedIn
5. Concierge onboard first 5 brands (you set up everything for them)

---

## Competitive Landscape

| Player | What They Do | Gap |
|---|---|---|
| Onsitego | Extended warranties at checkout | Point-of-sale only. No infra. No consumer app. |
| OneAssist | Extended warranties via banks | B2B distribution. No consumer app. No AI. |
| Urban Company | On-demand home services | Marketplace. No warranty/ownership. No brand integration. |
| Brand apps (Samsung, LG) | Own ecosystem | Siloed. One brand only. |
| Salesforce / Zendesk | CRM / Support ticketing | Generic. No warranty logic. No consumer side. |

**Our position**: The only player building the horizontal layer that works across brands. Not a point solution — infrastructure.
