/**
 * chat.js — Three-phase demo flow.
 *
 * Phase 0  ROUTER CHAT
 *          A WhatsApp phone frame. A routing bot asks "Which brand's line?"
 *          via native-feeling WA button replies. Selecting a brand fires
 *          the bot's confirmation message, then transitions to Phase 1.
 *
 * Phase 1  SCENARIO SELECTION
 *          Curated scenario cards — each a named, real support conversation.
 *          No abstract "pick a customer" list. Judges choose a narrative.
 *          Each card shows a mini WhatsApp preview of the conversation.
 *
 * Phase 2  SPLIT VIEW (the product)
 *          LEFT  = Brand's WhatsApp Business WEB (laptop, one business number)
 *          RIGHT = Customer's personal WhatsApp phone
 *          Two completely separate people, two completely separate devices.
 *
 * Greeting design:
 *   After scenario selection the agent sends a personalised greeting immediately
 *   (client-side — we already know the customer and product from the scenario).
 *   The customer types their actual issue. That triggers /api/start so the LLM
 *   gets a real complaint, not the word "Hi".
 */

"use strict";

// ── Phase DOM refs ─────────────────────────────────────────────────────────────

const phaseRouter    = document.getElementById("phase-router");
const phaseScenarios = document.getElementById("phase-scenarios");
const splitView      = document.getElementById("split-view");

const routerMessages = document.getElementById("router-messages");
const routerBody     = document.getElementById("router-body");

const scenariosBrandDot = document.getElementById("scenarios-brand-dot");
const scenariosTitle    = document.getElementById("scenarios-title");
const scenarioGrid      = document.getElementById("scenario-grid");
const scenarioBack      = document.getElementById("scenario-back");

const restartBtn = document.getElementById("restart-btn");

// Split-view refs
const chatBodyCustomer    = document.getElementById("chat-body-customer");
const messagesCustomer    = document.getElementById("messages");
const messagesBrand       = document.getElementById("messages-brand");
const waConvoPreview      = document.getElementById("wa-convo-preview");
const composer            = document.getElementById("composer");
const messageInput        = document.getElementById("message-input");
const sendBtn             = document.getElementById("send-btn");
const brandDot            = document.getElementById("brand-dot");
const brandName           = document.getElementById("brand-name");
const waBizAvatar         = document.getElementById("wa-biz-avatar");
const waBizName           = document.getElementById("wa-biz-name");
const waBizNumber         = document.getElementById("wa-biz-number");
const waCustAvatarSidebar = document.getElementById("wa-cust-avatar-sidebar");
const waCustNameSidebar   = document.getElementById("wa-cust-name-sidebar");
const waCustAvatarHeader  = document.getElementById("wa-cust-avatar-header");
const waCustNameHeader    = document.getElementById("wa-cust-name-header");
const waCustPhone         = document.getElementById("wa-cust-phone");
const brandPaneLabel      = document.getElementById("brand-pane-label");
const dashboardLink       = document.getElementById("dashboard-link");

// ── Brand metadata ─────────────────────────────────────────────────────────────

const BRANDS = {
  aquaspin: {
    slug:    "aquaspin",
    name:    "AquaSpin",
    product: "Washing machine brand",
    color:   "#1f7a5c",
    number:  "+91 1800 000 0001",
    emoji:   "🌊",
  },
  arcticair: {
    slug:    "arcticair",
    name:    "ArcticAir",
    product: "Split AC brand",
    color:   "#1a4a8e",
    number:  "+91 1800 000 0002",
    emoji:   "❄️",
  },
};

/**
 * SCENARIOS — curated demo conversations.
 *
 * Each scenario maps to real registration/product data in the DB.
 * phone + productId must match an actual registration record.
 * The preview bubbles are the literal first 2 exchanges so judges
 * know exactly what they're clicking into.
 */
const SCENARIOS = {
  aquaspin: [
    {
      id:        "aq-1",
      name:      "Priya — Drainage error, warranty active",
      desc:      "Priya's FC-700 is throwing E4 and not draining. She's within warranty. A common failure with a defined fix in the manual.",
      phone:     "+919876543210",
      productId: "WM-FC-700",
      issue:     "My washing machine is showing error E4 and won't drain the water",
      tags:      ["✓ Warranty active", "Single product", "AquaSpin"],
      tagClasses:["warranty-ok",       "brand",          "brand"],
      preview: [
        { side: "agent",   text: "Hi Priya! I can see your AquaSpin FC-700 (warranty active ✓). What's the issue?" },
        { side: "mine",    text: "My washing machine is showing error E4 and won't drain the water" },
        { side: "agent",   text: "E4 is a drain error — let's check the filter first…" },
      ],
    },
    {
      id:        "aq-2",
      name:      "Ananya — Bad smell, 2 products",
      desc:      "Ananya has two AquaSpin machines. She must first say which one needs support — demonstrating the product picker experience.",
      phone:     "+919845098450",
      productId: null, // triggers product picker in-conversation
      issue:     "My clothes still smell bad after washing even though I cleaned the drum",
      tags:      ["✓ Warranty active", "2 products — picks one", "AquaSpin"],
      tagClasses:["warranty-ok",       "multi-prod",             "brand"],
      preview: [
        { side: "agent",   text: "Hi Ananya! You have 2 products with us — which one needs support today?" },
        { side: "mine",    text: "The front loader, WM-FL-900" },
        { side: "agent",   text: "Got it — your FL-900 (warranty active). Describe the issue…" },
      ],
    },
  ],
  arcticair: [
    {
      id:        "ac-1",
      name:      "Sameer — Burning smell ⚠ SAFETY",
      desc:      "Sameer reports a burning smell from his AC. Aftercare flags this as a safety issue immediately and escalates — no troubleshooting attempted.",
      phone:     "+919900112233",
      productId: "AC-CB-15T",
      issue:     "There's a burning smell coming from my AC unit",
      tags:      ["⚠ Safety flag", "Instant escalation", "ArcticAir"],
      tagClasses:["safety",          "brand",              "brand"],
      preview: [
        { side: "agent",   text: "Hi Sameer! I see your ArcticAir 1.5T AC (warranty active). What's wrong?" },
        { side: "mine",    text: "There's a burning smell coming from my AC unit" },
        { side: "agent",   text: "⚠ Safety concern detected — escalating immediately, no DIY steps." },
      ],
    },
  ],
};

// ── State ──────────────────────────────────────────────────────────────────────

let currentBrand     = null;
let selectedScenario = null;
let conversationId   = null;
let awaitingComplaint = true; // true until customer sends their actual issue

// ── Helpers ────────────────────────────────────────────────────────────────────

function delay(ms) { return new Promise((r) => setTimeout(r, ms)); }

function scrollWaBg() {
  const bg = messagesBrand && messagesBrand.parentElement;
  if (bg) bg.scrollTop = bg.scrollHeight;
}

function appendBubble(container, scrollHost, text, alignment, modifier) {
  const el = document.createElement("div");
  el.className = `bubble ${alignment}${modifier ? " " + modifier : ""}`;
  el.textContent = text;
  container.appendChild(el);
  if (scrollHost) scrollHost.scrollTop = scrollHost.scrollHeight;
  return el;
}

function showTypingOnPhone() {
  const el = document.createElement("div");
  el.className = "bubble theirs typing";
  el.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
  messagesCustomer.appendChild(el);
  if (chatBodyCustomer) chatBodyCustomer.scrollTop = chatBodyCustomer.scrollHeight;
  return el;
}

async function deliver(text, from, modifier) {
  if (from === "customer") {
    appendBubble(messagesCustomer, chatBodyCustomer, text, "mine", modifier);
    await delay(200);
    appendBubble(messagesBrand, null, text, "theirs", modifier);
    scrollWaBg();
    if (waConvoPreview) waConvoPreview.textContent = text;
  } else {
    appendBubble(messagesBrand, null, text, "mine", modifier);
    scrollWaBg();
    await delay(320);
    appendBubble(messagesCustomer, chatBodyCustomer, text, "theirs", modifier);
    if (waConvoPreview)
      waConvoPreview.textContent = "↩ " + text.slice(0, 38) + (text.length > 38 ? "…" : "");
  }
}

function setComposerEnabled(enabled) {
  messageInput.disabled = !enabled;
  sendBtn.disabled = !enabled;
  if (enabled) messageInput.focus();
}

// ── Phase 0: Router chat ───────────────────────────────────────────────────────

/** Append a bubble into the router phone frame. */
function appendRouterBubble(text, side, extraClass) {
  const el = document.createElement("div");
  el.className = `bubble ${side}${extraClass ? " " + extraClass : ""}`;
  el.textContent = text;
  routerMessages.appendChild(el);
  routerBody.scrollTop = routerBody.scrollHeight;
  return el;
}

async function startRouterChat() {
  await delay(400);

  // Typing indicator
  const t1 = document.createElement("div");
  t1.className = "bubble theirs typing";
  t1.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
  routerMessages.appendChild(t1);
  routerBody.scrollTop = routerBody.scrollHeight;

  await delay(1100);
  t1.remove();

  appendRouterBubble(
    "Hi! Welcome to Aftercare support. 👋\nWhich brand's service line do you need?",
    "theirs"
  );

  await delay(300);

  // Render brand buttons inside the router chat (WhatsApp-native feel)
  const btnGroup = document.createElement("div");
  btnGroup.className = "wa-btn-group";

  Object.values(BRANDS).forEach((b) => {
    const btn = document.createElement("button");
    btn.className = `wa-btn ${b.slug === "arcticair" ? "arctic" : ""}`;
    btn.innerHTML = `
      <span class="wa-btn-dot" style="background:${b.color};">${b.name.slice(0, 2)}</span>
      <span class="wa-btn-body">
        <span class="wa-btn-name">${b.name}</span>
        <span class="wa-btn-sub">${b.product}</span>
      </span>`;
    btn.addEventListener("click", () => selectBrandFromRouter(b.slug, btn, btnGroup));
    btnGroup.appendChild(btn);
  });

  routerMessages.appendChild(btnGroup);
  routerBody.scrollTop = routerBody.scrollHeight;
}

async function selectBrandFromRouter(brandSlug, clickedBtn, btnGroup) {
  const brand = BRANDS[brandSlug];
  currentBrand = brand;

  // Disable all brand buttons
  btnGroup.querySelectorAll(".wa-btn").forEach((b) => {
    b.disabled = true;
    b.style.opacity = b === clickedBtn ? "1" : "0.4";
  });

  // Customer's reply bubble
  appendRouterBubble(`${brand.name} — ${brand.product}`, "mine");
  await delay(500);

  // Typing
  const t2 = document.createElement("div");
  t2.className = "bubble theirs typing";
  t2.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
  routerMessages.appendChild(t2);
  routerBody.scrollTop = routerBody.scrollHeight;

  await delay(900);
  t2.remove();

  appendRouterBubble(
    `Got it — connecting you to ${brand.name}'s support line ${brand.emoji}. Choose your scenario below.`,
    "theirs"
  );

  await delay(600);

  // Transition to scenario phase
  phaseRouter.hidden = true;
  phaseScenarios.hidden = false;
  showScenarios(brandSlug);
}

// ── Phase 1: Scenario selection ────────────────────────────────────────────────

function showScenarios(brandSlug) {
  const brand = BRANDS[brandSlug];
  const scenarios = SCENARIOS[brandSlug] || [];
  const isArctic = brandSlug === "arcticair";

  // Header
  scenariosBrandDot.textContent = brand.name.slice(0, 2);
  scenariosBrandDot.style.background = brand.color;
  scenariosTitle.textContent = `${brand.name} Support`;

  // Build cards
  scenarioGrid.innerHTML = "";
  scenarios.forEach((s) => {
    const card = document.createElement("div");
    card.className = `scenario-card ${isArctic ? "arctic" : ""}`;

    // Mini WhatsApp preview
    const preview = document.createElement("div");
    preview.className = "scenario-preview";
    s.preview.forEach((p) => {
      const b = document.createElement("div");
      b.className = `sp-bubble ${p.side}`;
      b.textContent = p.text;
      preview.appendChild(b);
    });

    // Body
    const body = document.createElement("div");
    body.className = "scenario-body";

    const name = document.createElement("div");
    name.className = "scenario-name";
    name.textContent = s.name;

    const desc = document.createElement("div");
    desc.className = "scenario-desc";
    desc.textContent = s.desc;

    const tags = document.createElement("div");
    tags.className = "scenario-tags";
    s.tags.forEach((t, i) => {
      const tag = document.createElement("span");
      tag.className = `scenario-tag ${s.tagClasses[i] || "brand"}`;
      tag.textContent = t;
      tags.appendChild(tag);
    });

    const launch = document.createElement("div");
    launch.className = "scenario-launch";
    launch.innerHTML = `<span>Start this scenario</span><span>→</span>`;

    body.append(name, desc, tags, launch);
    card.append(preview, body);

    card.addEventListener("click", () => launchScenario(s));
    scenarioGrid.appendChild(card);
  });
}

if (scenarioBack) {
  scenarioBack.addEventListener("click", (e) => {
    e.preventDefault();
    phaseScenarios.hidden = true;
    phaseRouter.hidden = false;
    currentBrand = null;
  });
}

// ── Phase 2: Launch a scenario into the split view ─────────────────────────────

async function launchScenario(scenario) {
  selectedScenario = scenario;
  const brand = currentBrand;

  // If scenario has no productId, we need to do an API lookup to get the
  // right product. For now use the lookup API to get the first product.
  let productId = scenario.productId;
  let lookupData = null;

  if (!productId) {
    // Multi-product scenario — let the conversation start and do a product lookup
    const res = await fetch("/api/lookup", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ phone: scenario.phone, brand: brand.slug }),
    });
    lookupData = await res.json();
    if (!lookupData.found) return;
    // Use first product — scenario description explains this is demo context
    productId = lookupData.products[0].product_id;
  } else {
    // Normal lookup for display info
    const res = await fetch("/api/lookup", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ phone: scenario.phone, brand: brand.slug }),
    });
    lookupData = await res.json();
    if (!lookupData.found) return;
  }

  const product = lookupData.products.find((p) => p.product_id === productId) || lookupData.products[0];

  // Switch phases
  phaseScenarios.hidden = true;
  splitView.hidden      = false;

  // Hydrate WA web panel
  if (waBizAvatar)         waBizAvatar.textContent         = brand.name.slice(0, 2);
  if (waBizName)           waBizName.textContent           = `${brand.name} Business`;
  if (waBizNumber)         waBizNumber.textContent         = brand.number;
  if (waCustAvatarSidebar) waCustAvatarSidebar.textContent = lookupData.customer_name[0];
  if (waCustNameSidebar)   waCustNameSidebar.textContent   = lookupData.customer_name;
  if (waCustAvatarHeader)  waCustAvatarHeader.textContent  = lookupData.customer_name[0];
  if (waCustNameHeader)    waCustNameHeader.textContent    = lookupData.customer_name;
  if (waCustPhone)         waCustPhone.textContent         = scenario.phone;
  if (brandPaneLabel)      brandPaneLabel.textContent      = brand.name;

  // Hydrate customer phone header
  if (brandDot)  { brandDot.textContent = brand.name.slice(0, 2); brandDot.style.background = brand.color; }
  if (brandName) brandName.textContent = `${brand.name} Support`;

  if (dashboardLink) dashboardLink.href = `/dashboard/${brand.slug}`;

  // Send greeting
  const wStatus      = product.warranty_component_status;
  const warrantyLine = wStatus === "active" ? "still under warranty ✓" : "warranty has ended";
  const greeting     = `Hi ${lookupData.customer_name}! I can see your ${product.product_name} (${warrantyLine}). What issue are you facing today?`;

  setComposerEnabled(false);
  const typing = showTypingOnPhone();
  await delay(850);
  typing.remove();
  await deliver(greeting, "agent");

  awaitingComplaint = true;
  // Pre-fill the input with the scenario issue so demo is frictionless
  messageInput.value       = scenario.issue;
  messageInput.placeholder = "Describe your issue…";
  setComposerEnabled(true);
  messageInput.focus();
  messageInput.select();
}

// ── Conversation turns ─────────────────────────────────────────────────────────

async function sendMessage() {
  const text = messageInput.value.trim();
  if (!text) return;
  messageInput.value = "";
  setComposerEnabled(false);

  await deliver(text, "customer");

  const typingBubble = showTypingOnPhone();
  let data;

  if (awaitingComplaint) {
    const res = await fetch("/api/start", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({
        phone:      selectedScenario.phone,
        complaint:  text,
        product_id: selectedScenario.productId || (await getFirstProductId()),
      }),
    });
    data = await res.json();
    if (!data.error) {
      conversationId    = data.conversation_id;
      awaitingComplaint = false;
      messageInput.placeholder = "Reply…";
    }
  } else {
    const res = await fetch("/api/respond", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ conversation_id: conversationId, reply: text }),
    });
    data = await res.json();
  }

  typingBubble.remove();

  if (data.error) {
    appendBubble(messagesCustomer, chatBodyCustomer, data.error, "theirs", "system");
    setComposerEnabled(true);
    return;
  }

  const modifier = data.status === "escalated" ? "ticket" : undefined;
  await deliver(data.message, "agent", modifier);

  if (data.status === "escalated") {
    if (dashboardLink) dashboardLink.hidden = false;
  }

  if (data.status === "resolved" || data.status === "escalated") {
    setComposerEnabled(false);
  } else {
    setComposerEnabled(true);
  }
}

async function getFirstProductId() {
  // Fallback for multi-product scenarios where productId was null
  const res  = await fetch("/api/lookup", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ phone: selectedScenario.phone, brand: currentBrand.slug }),
  });
  const data = await res.json();
  return data.found ? data.products[0].product_id : null;
}

sendBtn.addEventListener("click", sendMessage);
messageInput.addEventListener("keydown", (e) => { if (e.key === "Enter") sendMessage(); });

// ── Restart / try-another ──────────────────────────────────────────────────────

function resetDemo() {
  // Clear state
  currentBrand = selectedScenario = conversationId = null;
  awaitingComplaint = true;

  // Clear messages
  if (messagesCustomer) messagesCustomer.innerHTML = "";
  if (messagesBrand)    messagesBrand.innerHTML    = "";
  if (routerMessages)   routerMessages.innerHTML   = "";
  if (waConvoPreview)   waConvoPreview.textContent  = "Waiting…";
  if (dashboardLink)    dashboardLink.hidden = true;
  if (messageInput)     messageInput.value   = "";

  // Back to Phase 0
  splitView.hidden      = true;
  phaseScenarios.hidden = true;
  phaseRouter.hidden    = false;

  // Restart the router chat
  startRouterChat();
}

if (restartBtn) restartBtn.addEventListener("click", resetDemo);

// ── QR deep-link entry (/?brand=…&serial=…) ───────────────────────────────────

(async function handleQREntry() {
  const params   = new URLSearchParams(window.location.search);
  const qrBrand  = params.get("brand");
  const qrSerial = params.get("serial");
  if (!qrBrand || !qrSerial) return;

  const brand = BRANDS[qrBrand];
  if (!brand) return;

  // Look through all scenarios for a matching serial, or do a live lookup
  const res    = await fetch(`/api/customers?brand=${qrBrand}`);
  const people = await res.json();

  for (const person of people) {
    const lRes = await fetch("/api/lookup", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ phone: person.phone, brand: qrBrand }),
    });
    const lData = await lRes.json();
    if (!lData.found) continue;

    const match = lData.products.find((p) => p.serial_number === qrSerial);
    if (match) {
      // Jump straight to split-view bypassing router + scenarios
      currentBrand = brand;
      const synthetic = {
        id:        "qr-entry",
        name:      `${lData.customer_name} — ${match.product_name}`,
        phone:     person.phone,
        productId: match.product_id,
        issue:     "",
        tags:      [],
        tagClasses:[],
        preview:   [],
      };
      phaseRouter.hidden    = true;
      phaseScenarios.hidden = true;
      await launchScenario(synthetic);
      // Clear pre-filled issue since it came from QR
      messageInput.value = "";
      return;
    }
  }
})();

// ── Boot the router chat on page load ─────────────────────────────────────────

startRouterChat();
