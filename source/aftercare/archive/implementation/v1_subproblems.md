# thebestbill — Subproblems, Approaches & MVP Subset

---

## Consumer Side Subproblems

---

### C1. How does a product get into the app?

Two paths: automatic (brand pushed) and manual (user added).

**Automatic (brand integrated):**
- Brand calls our API at checkout with customer phone + product details
- We create the record and send an SMS with a link
- When user opens app and verifies phone → products show up

**Manual (user added):**

| Approach | Effort | Effectiveness |
|---|---|---|
| **Photo of invoice → manual entry by user** | Low | Works but high friction. Users will drop off. |
| **Photo of invoice → OCR + manual correction** | Medium | Google Vision API / Tesseract extracts text. User fixes mistakes. Good enough for V1. |
| **Forward email to add@thebestbill.dev** | Medium | Parse the email body for order details. Amazon/Flipkart confirmation emails have structured data. |
| **Paste Amazon/Flipkart order link** | Low | Scrape the product page for name, price, image. Won't get serial number though. |
| **Manual form (brand, product, serial, date)** | Low | Boring but reliable fallback. Always need this. |

> [!IMPORTANT]
> **Question C1a**: Are you targeting a mobile app (React Native / Flutter) or web-first? This changes the "scan invoice" UX significantly.

> [!IMPORTANT]
> **Question C1b**: For email forwarding — do you want to build a full email parser from day 1, or is "take photo of invoice" enough for launch?

**MVP subset**: Photo upload + OCR extraction + manual form fallback. Skip email forwarding for now.

---

### C2. How do we track warranty status?

| Approach | Details |
|---|---|
| **Brand defines warranty per SKU** | Clean and authoritative. |
| **User enters warranty duration manually** | For manual adds. User says "2 year warranty." |
| **Default by product category** | Water purifier → 1 year, AC → 1 year, etc. |
| **Extract from invoice** | Unreliable — use as hint, not source of truth. |

> [!IMPORTANT]
> **Question C2a**: Some products have different warranty for different components (e.g., AC: 1 year comprehensive + 5 years compressor). Do we handle this in V1 or keep it simple?

**MVP subset**: One warranty period per product. Three-stage status (active/expiring/expired). Push notifications at 30d/7d/0d.

---

### C3. How do we help when something breaks?

#### C3a. Registered brand — AI-assisted service request

| Approach | Details | Scales? |
|---|---|---|
| **Scripted decision tree** | Pre-built question flows per product type. No actual AI, just branching logic. | No, but works perfectly for V1. |
| **LLM with product context** | Feed GPT-4/Claude the product manual, warranty status, service history as context. | Yes, but costs money per conversation. |
| **Hybrid: decision tree + LLM fallback** | Start with scripted flow for common issues. Fall back to LLM for edge cases. | Best of both. |
| **WhatsApp bot** | Same logic but over WhatsApp. Users already use WhatsApp. | Doesn't scale well but very effective for early users. |

> [!IMPORTANT]
> **Question C3a**: For V1, do you want to use actual LLM calls or keep it as scripted decision trees?

> [!IMPORTANT]
> **Question C3b**: WhatsApp is where Indian consumers live. Do you want to build a WhatsApp bot alongside the in-app chat?

#### C3b. Unregistered brand — helpline + diagnosis

| Approach | Details |
|---|---|
| **Curated helpline directory (manual)** | Manually collect and verify toll-free numbers for top 50-100 brands. |
| **Crowdsourced helpline numbers** | Users submit/verify numbers. Scales but quality varies. |
| **Web scrape brand websites** | Auto-extract support numbers. Unreliable. |
| **Still run diagnostic questions** | Give the user a summary to read out when they call. |

> [!IMPORTANT]
> **Question C3c**: How many brands do you want in the helpline directory at launch? Who maintains it?

**MVP subset**: Scripted decision trees for 4 product types. Curated helpline directory for top 30 brands.

---

### C4. How do we store and retrieve documents?

| Approach | Details |
|---|---|
| **S3/GCS bucket + metadata in DB** | Standard approach. |
| **Just save the photo** | Simplest possible thing. |
| **OCR + structured storage** | Extract text AND keep the original. |

> [!IMPORTANT]
> **Question C4a**: Do users need to view/download original documents, or is the extracted data enough?

---

### C5. How do we identify the user?

| Approach | Details |
|---|---|
| **Phone number as identity** | Simplest. Works in India. |
| **Email as identity** | Secondary identifier. |
| **Phone + OTP login** | Firebase Auth or custom OTP via MSG91. |

> [!IMPORTANT]
> **Question C5a**: Phone OTP costs ₹0.15-0.30 per SMS. Are you okay with this or explore alternatives (WhatsApp OTP, missed call)?

---

## Brand Side Subproblems

---

### B1. How does a brand register products at checkout?

| Approach | Details |
|---|---|
| **REST API** | Standard. Every developer knows this. |
| **Shopify plugin** | Auto-calls API on order completion. No code. |
| **WooCommerce plugin** | Same for WordPress. |
| **Zapier/Make integration** | No-code. |
| **CSV upload** | Batch-import. Good for onboarding. |
| **Manual entry in dashboard** | For very small brands or demo. |

> [!IMPORTANT]
> **Question B1a**: For your first 5-10 brands, do you even need a public API? You could do the integration FOR them.

> [!IMPORTANT]
> **Question B1b**: Shopify or WooCommerce — which is more common among your target brands?

---

### B2. How does a brand set up their product catalog?

| Approach | Details |
|---|---|
| **Dashboard form** | One by one. |
| **CSV upload** | Bulk import. |
| **You do it for them** | 1-2 hours per brand. |
| **Scrape their product pages** | Auto-extract from website. |

> [!IMPORTANT]
> **Question B2a**: Do your target brands even have clean product catalogs?

---

### B3. How does the brand see what's happening?

| Approach | Details |
|---|---|
| **Simple dashboard with 4 metrics** | Enough to prove value. |
| **Daily email digest** | Zero dashboard needed. |
| **Shared Google Sheet** | Does not scale. Works for 5 brands. |

> [!IMPORTANT]
> **Question B3a**: For your first brands, would a daily email summary be enough?

---

### B4. How does service dispatch work?

| Approach | Details |
|---|---|
| **Brand's own technicians** | We just notify them. |
| **We assign from brand's list** | Auto-assign based on location + product type. |
| **We build a technician marketplace** | Like Urban Company. |
| **Manual — you call the technician** | For first 10 service requests, you personally call. |

> [!IMPORTANT]
> **Question B4a**: Do your target brands have existing service partners/technicians?

> [!IMPORTANT]
> **Question B4b**: OK with brand handling assignment, you just do intake for V1?

---

### B5. How do we train the AI on brand-specific knowledge?

| Approach | Details |
|---|---|
| **Brand uploads PDFs** | RAG with vector database. |
| **Scrape their FAQ page** | Brand doesn't need to do anything. |
| **Manually write knowledge base** | 2-4 hours per product line. |
| **Generic product-type knowledge** | Don't do brand-specific for V1. |

> [!IMPORTANT]
> **Question B5a**: For V1, is generic product-type troubleshooting enough?

---

## Cross-Cutting Subproblems

---

### X1. How do we get the first 5 brands?

| Approach | Details |
|---|---|
| **Cold outreach** | DM founders on LinkedIn. |
| **Inbound via consumer app** | Launch consumer app first. Users add products. Reach out when 50+ products. |
| **Personal network** | Fastest path. |
| **Offer to do their support** | "We will answer your support for 2 weeks for free." |
| **Target brands with bad reviews** | Find brands with 1-2 star reviews about after-sales. |

> [!IMPORTANT]
> **Question X1a**: Personal connections to D2C brand founders?

> [!IMPORTANT]
> **Question X1b**: Willing to do concierge support for 2 weeks?

---

### X2. How do we get consumers to use the app?

| Approach | Details |
|---|---|
| **SMS from brand at purchase** | Primary acquisition channel. |
| **Launch without brands** | Pure consumer play. |
| **WhatsApp bot** | Skip the app entirely. |
| **Word of mouth** | Organic but slow. |

> [!IMPORTANT]
> **Question X2a**: Consumer-first or brand-first launch?

---

### X3. Tech stack?

> [!IMPORTANT]
> **Question X3a**: Your tech comfort level? Solo dev or co-founder?

> [!IMPORTANT]
> **Question X3b**: Budget constraints?

---

### X4. Notifications?

| Channel | Cost | Effectiveness |
|---|---|---|
| **SMS** | ₹0.15-0.30/SMS | High open rate (95%+) |
| **Push** | Free | Medium |
| **WhatsApp** | ₹0.50-1.00/msg | Very high engagement |
| **Email** | Nearly free | Low engagement in India |

> [!IMPORTANT]
> **Question X4a**: How many notifications per product lifecycle are essential?

---

## Open Questions Summary

| # | Question |
|---|---|
| C1a | Mobile app or web-first? |
| C1b | Email forwarding for V1 or skip? |
| C2a | Multi-component warranty in V1? |
| C3a | LLM or scripted decision trees? |
| C3b | WhatsApp bot as a channel? |
| C3c | How many brands in helpline directory? |
| C4a | View original documents or extracted data enough? |
| C5a | OTP cost acceptable? |
| B1a | Do integration FOR first brands manually? |
| B1b | Shopify or WooCommerce first? |
| B2a | How messy are brand catalogs? |
| B3a | Daily email or real-time dashboard? |
| B4a | Brands have existing technicians? |
| B4b | OK with brand handling assignment for V1? |
| B5a | Generic troubleshooting enough? |
| X1a | Personal connections to brand founders? |
| X1b | Willing to do concierge support? |
| X2a | Consumer-first or brand-first? |
| X3a | Tech comfort level? |
| X3b | Monthly infra budget? |
| X4a | How many SMSes per product lifecycle? |
