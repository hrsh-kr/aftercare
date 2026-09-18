# thebestbill — Product Document (V1)

> **One-liner**: Infrastructure for after-sales. Brands integrate one API at checkout — consumers get warranty tracking, AI support, and service management in one app. For brands not on the platform, we provide trusted helpline numbers and manual product tracking.

---

## What thebestbill Is

Companies don't build payment gateways — they use Stripe/Razorpay. Similarly, companies shouldn't build after-sales systems — they should use thebestbill.

**Two sides, one platform:**

| Side | What they get |
|---|---|
| **Brands** (B2B) | API to register products at checkout. Dashboard with warranty analytics, service management, AI bot config. |
| **Consumers** (B2C) | One app for all products. Warranty tracking, AI support, service booking — regardless of whether the brand is on thebestbill or not. |

---

## V1 Scope — What Ships First

### ✅ In V1

| Feature | Details |
|---|---|
| Product registration API | One API call at checkout → warranty created, customer notified |
| Consumer product passbook | All products in one place with warranty countdown |
| AI chat support | Diagnostic questions, service request creation (registered) or helpline (unregistered) |
| Invoice scanning | Upload photo/PDF → AI extracts product details |
| Trusted helpline directory | Verified toll-free numbers for major unregistered brands |
| Service request creation | AI-assisted issue reporting → technician assignment |
| Brand dashboard | Overview metrics, recent registrations, warranty analytics |
| Webhook events | product.registered, warranty.expiring, service.created, etc. |

### ❌ Not in V1 (future)

- Voice bot / telephony
- Ownership transfer / resale
- Family sharing
- Insurance integration
- Service provider marketplace
- Extended warranty sales
- Retailer-level POS integration (Croma, Flipkart)
- White-label / on-premise
- Multilingual AI (start English + Hindi only)

---

## Core Flows

### Flow 1: Brand Registers a Product at Checkout

```
Brand's checkout system
    │
    ▼
POST /v1/products/register
    {
      customer_phone: "+919876543210",
      product_sku: "RO-GRAND-STAR",
      serial_number: "AP-2024-RO-78234",
      purchase_price: 18500
    }
    │
    ▼
thebestbill backend
    ├── Creates product record
    ├── Creates warranty record (duration from brand's SKU config)
    ├── Links to customer by phone number
    ├── Stores purchase metadata
    │
    ▼
Customer gets SMS
    "Your AquaPure Grand Star RO+UV is registered.
     Warranty valid until Mar 15, 2025.
     Open thebestbill app to manage → [link]"
    │
    ▼
Product appears in consumer app instantly
```

**Brand setup (one-time):**
1. Sign up → get API keys (`tbb_test_`, `tbb_live_`)
2. Add product SKUs with warranty duration, category, manual PDFs
3. Integrate API call at checkout (or use Shopify/WooCommerce plugin)
4. Upload product manuals + FAQs for AI training

---

### Flow 2: Consumer Reports Issue — Registered Brand

```
User opens AI chat
    │
    ▼
User: "My water purifier has low water flow"
    │
    ▼
AI identifies matching products from user's list
    ├── User has 2 water purifiers from AquaPure
    └── AI asks: "Which one — Grand Star or Supreme Star?"
    │
    ▼
User selects: "Grand Star"
    │
    ▼
AI pulls product context
    ├── Serial: AP-2024-RO-78234
    ├── Warranty: EXPIRED (Mar 15, 2025)
    ├── Last filter change: Sep 15, 2025 (8 months ago)
    │
    ▼
AI runs diagnostic flow
    ├── "When did you first notice the low flow?"
    ├── AI already knows: "Your last filter was changed 8 months ago"
    │
    ▼
AI provides diagnosis + offers actions
    ├── [Book technician visit] → ₹350 service charge
    ├── [Order replacement filters] → ₹1,200
    └── [Talk to AquaPure support]
    │
    ▼
AI creates service request via API
    ├── SR #SRV-2026-4521
    ├── Technician: Vikram R. (serviced this unit before)
    ├── Slot: Tomorrow 10 AM – 12 PM
    │
    ▼
Customer + Brand both notified
```

---

### Flow 3: Consumer Reports Issue — Unregistered Brand

```
User opens AI chat
    │
    ▼
User: "My Daikin AC is not cooling properly"
    │
    ▼
AI identifies product
    ├── Daikin Split AC 1.5T (FTKG50TV16U)
    ├── Warranty: ACTIVE until Jan 8, 2026
    ├── Brand status: NOT on thebestbill
    │
    ▼
AI informs user + runs diagnostic questions
    ├── "Is the outdoor unit running?"
    ├── "What temperature is it set to?"
    │
    ▼
AI provides diagnosis + verified helpline info
    ├── 📞 Daikin: 1860-180-3900
    ├── Hours: Mon-Sat, 9 AM – 6 PM
    ├── Pre-formatted details to mention on the call
    │
    ▼
Details copied to clipboard
```

---

### Flow 4: Consumer Adds Product Manually (Invoice Scan)

```
User taps "Add Product"
    │
    ├── 📸 Take photo of invoice
    ├── 📄 Upload PDF
    │
    ▼
AI Document Processing (OCR)
    ├── Brand: Havells
    ├── Product: Fascino 400mm Pedestal Fan
    ├── Serial: HV-FAN-2025-89012
    ├── Purchase Date: May 12, 2025
    ├── Price: ₹3,299
    │
    ▼
User reviews + confirms
    └── Product card created with warranty countdown
```

---

### Flow 5: Warranty Expiry Tracking

```
├── 30 days before → Push notification + card turns yellow
├── 7 days before → Push notification
├── Expiry day → Notification + card turns red
└── Post-expiry → Service requests show charge
```

---

### Flow 6: Brand Receives Service Request

```
Service request lands in brand dashboard
    ├── Customer details + product + issue + AI diagnosis
    │
    ▼
Brand assigns technician
    ├── Auto-assignment based on previous technician / location
    │
    ▼
Both parties notified → Post-service rating
```

---

## Trusted Helpline Directory (V1)

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

---

## Diagnostic Question Trees (V1)

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

## API Surface (V1)

### `POST /v1/products/register`
Registers a product at point of sale.

### `POST /v1/service-requests`
Creates a service request.

### Webhook Events
- `product.registered`, `warranty.expiring`, `warranty.expired`
- `service.created`, `service.completed`, `ai.escalation`

---

## Starting Wedge

**Target**: 10 D2C appliance brands in India

**First pitch**: "We'll handle your entire after-sales for free for 3 months."

**Inbound flywheel**: Consumers manually adding products → demand signal → onboard the brand.
