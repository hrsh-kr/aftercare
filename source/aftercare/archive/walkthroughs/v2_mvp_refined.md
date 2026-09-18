# thebestbill MVP — Walkthrough

## What It Is

**thebestbill** is the "Stripe for After-Sales" — an API-first infrastructure platform where:
- **Brands** integrate one API call at checkout → warranty, AI support, and service management just works
- **Consumers** get one app for all their products — regardless of whether the brand is on the platform

**Live at:** http://localhost:5173

---

## The 4 Surfaces

### 1. Landing Page — `/`

Clean marketing pitch with 4 sections (no pricing — MVP):

- **Hero** with code preview showing a 6-line integration
- **How It Works** — 3 steps: Brand integrates → Customer gets everything → AI handles support
- **For Brands** — 2×2 feature grid (auto-registration, AI support, service management, product intelligence)
- **For Consumers** — two cards explaining the key differentiation:
  - 🟢 **Registered brands** → full AI support, auto-service booking, diagnostics
  - ⚪ **Unregistered brands** → trusted helpline numbers, manual product tracking, auto-linked when brand joins

---

### 2. Consumer App — `/app` ⭐ (Primary demo surface)

**Product Passbook** with 6 products (3 AquaPure registered + 3 unregistered):

- **Product cards** show registered vs unregistered status alongside warranty badge
- **Product detail modal** — click any card:
  - Registered brands: shows "🟢 On thebestbill — AI support, auto-service booking available"
  - Unregistered brands: shows "⚪ Not on thebestbill" + **trusted helpline directory** (toll-free, hours, website)
- **Add Product** — click "+" to see the invoice scanning flow:
  - Upload area (photo/PDF/email forward)
  - AI auto-extracts: Brand, Product, Serial, Purchase Date, Price, Warranty
  - Shows "Brand not yet on thebestbill" info banner
  - Save button

#### AI Chat — Two Demo Flows

Click the 💬 button to open the AI chat. **Two tabs at the top let you switch flows:**

| Flow | Brand | What Happens |
|---|---|---|
| 🟢 **Registered** | AquaPure | AI identifies product → checks warranty → asks diagnostic questions → auto-creates service request with specific technician + time slot |
| ⚪ **Unregistered** | Daikin | AI identifies product → checks warranty → runs diagnostic questions → provides **verified helpline number** + pre-formatted details to mention when calling |

Bot messages have **clickable option buttons** for guided interaction.

---

### 3. Brand Dashboard — `/dashboard`

Overview-only (no sub-tabs — focused for demo):

- **4 metric cards** with count-up animation (Active Warranties, Products Registered, Service Requests, AI Resolution Rate)
- **Bar chart** — monthly product registrations
- **Donut chart** — warranty status breakdown (Active/Expiring/Expired)
- **Recent registrations table** with search

Mock brand: AquaPure India.

---

### 4. API Docs — `/docs`

Stripe-style developer docs with **2 core endpoints**:

| Endpoint | Purpose |
|---|---|
| `POST /v1/products/register` | Register product at point of sale — creates warranty, sends SMS, links to consumer app |
| `POST /v1/service-requests` | Create service request — includes AI diagnosis in response |

Each endpoint has:
- Multi-language code tabs (cURL, Node.js, Python)
- Parameter table with types and descriptions
- Full response schema (note the `ai_diagnosis` field in service request response)
- Copy-to-clipboard button

Plus: Authentication section, Webhooks event table.

---

## Key Technical Details

### Registered vs Unregistered Brand Flow

```
Product registered on thebestbill?
├── YES (e.g., AquaPure)
│   ├── AI maps to specific product via serial number
│   ├── Checks warranty status + service history
│   ├── Asks diagnostic questions specific to product type
│   ├── Auto-creates service request via API
│   └── Assigns known technician + schedules slot
│
└── NO (e.g., Daikin, Samsung, Apple)
    ├── AI still identifies product from user's registered list
    ├── Checks warranty status (from user's stored data)
    ├── Runs diagnostic questions
    ├── Provides verified toll-free helpline number
    ├── Pre-formats details for the customer to mention
    └── Product auto-links when brand joins platform
```

### Trusted Helpline Directory

10 brands maintained with verified toll-free numbers:
Daikin, Apple, Samsung, LG, Whirlpool, Bosch, Philips, Havells, Prestige, Crompton

### API Key Scheme

- `tbb_test_` — sandbox keys
- `tbb_live_` — production keys
- API domain: `api.thebestbill.dev`

---

## Build Stats

| Metric | Value |
|---|---|
| JS bundle | 291 KB (88 KB gzip) |
| CSS bundle | 31.6 KB (5.9 KB gzip) |
| Build time | 85ms |
| Components | 5 |
| Pages | 4 |
| Total files | 14 source files |
