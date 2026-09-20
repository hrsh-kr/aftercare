/* demo.js — /demo. A real client of the same /api/* the SAM Lambdas serve:
   /api/lookup, /api/start, /api/respond. Nothing in a conversation is scripted
   except the customer's suggested words, which you can edit before sending.
   The "what Aftercare did" trace is built only from fields the API returns. */
"use strict";

const BRAND = {
  aquaspin:  { name: "AquaSpin",  initials: "Aq", bg: "linear-gradient(135deg,#1f7a5c,#30B0C7)" },
  arcticair: { name: "ArcticAir", initials: "Ar", bg: "linear-gradient(135deg,#1a4a8e,#5aa0ff)" },
};

/* Each scenario is tied to a fixture person + product (fixtures/sales_data.csv).
   ④ relies on fixtures/history_seed.json; the others on there being no earlier case. */
const SCENARIOS = [
  { id: "fixed", num: "01", brand: "aquaspin", phone: "+919876543210", productId: "WM-FC-700",
    title: "Fixed in one step", badge: ["Resolved · no ticket", "green"],
    desc: "Priya's washing machine bangs on spin. Two products on file, so it asks which. One step from the manual fixes it.",
    complaint: "My washing machine bangs loudly when it spins", replies: ["That fixed it, thank you!"] },
  { id: "tried", num: "02", brand: "arcticair", phone: "+919812345678", productId: "AC-CB-15T",
    title: "Two steps, still broken", badge: ["Handed to a person", "blue"],
    desc: "Ravi's AC isn't cooling. Two steps from the manual don't help, so the agent stops trying and passes it on with both attached.",
    complaint: "My AC is on but the room isn't cooling", replies: ["Still blowing warm air", "Still not cooling, no change"] },
  { id: "unmatched", num: "03", brand: "aquaspin", phone: "+919876543210", productId: "WM-FC-700",
    title: "Not in the manual", badge: ["Handed to a person", "teal"],
    desc: "Priya describes something the manual never mentions. The agent won't invent a fix, so it hands the case over as she described it.",
    complaint: "The touch panel flickers and won't respond", replies: [] },
  { id: "recurring", num: "04", brand: "aquaspin", phone: "+919845098450", productId: "WM-FC-700",
    title: "It's back", badge: ["Recurring issue", "violet"],
    desc: "Ananya's machine was fixed for this same noise 34 days ago. The agent recognises it and doesn't repeat the fix.",
    complaint: "My washing machine bangs loudly when it spins", replies: [] },
  { id: "safety", num: "05", brand: "arcticair", phone: "+919900112233", productId: "AC-CB-15T",
    title: "Safety first", badge: ["Emergency visit", "red"],
    desc: "Sameer smells burning from his AC. No troubleshooting: the manual's own stop-use warning, and a technician, free of charge.",
    complaint: "There's a burning smell coming from my AC", replies: [] },
];

/* Which backend answers: same origin (Flask) by default, or ?api=http://127.0.0.1:3000 to run
   the identical page against the SAM Local Lambdas. */
const API = (new URLSearchParams(location.search).get("api") || "").replace(/\/$/, "");

const $ = (id) => document.getElementById(id);
const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const chat = $("d-chat"), trace = $("d-trace"), input = $("d-input"), sendBtn = $("d-send"),
      hint = $("d-hint"), ticketBox = $("d-ticket"), doneBox = $("d-done"), banner = $("d-banner");

let scenario = null;   // selected scenario
let run = 0;           // bumps on restart so a stale async flow stops writing
let state = null;      // { phase, products, product, conversationId, replyIdx }

/* ── API ── */
async function api(path, body, headers = {}) {
  const res = await fetch(API + path, { method: "POST", headers: { "Content-Type": "application/json", ...headers }, body: JSON.stringify(body) });
  let data = {};
  try { data = await res.json(); } catch (_) { /* non-JSON error page */ }
  if (!res.ok) { const e = new Error(data.error || `HTTP ${res.status}`); e.status = res.status; throw e; }
  return data;
}
function showError(err) {
  banner.hidden = false;
  banner.textContent = "";
  banner.append("The agent didn't answer. It needs a local model server: start it with ");
  banner.append(el("code", null, "ollama serve"));
  banner.append(` (and pull qwen2.5-coder:7b once), then press Restart. (${err.message})`);
}

/* ── chat helpers ── */
function bubble(type, text) {
  const cls = { agent: "fb agent", cust: "fb cust", sys: "fb sys", source: "fb source", ok: "fb ok", warn: "fb warn" }[type];
  const b = el("div", cls, text);
  chat.appendChild(b);
  requestAnimationFrame(() => requestAnimationFrame(() => b.classList.add("show")));
  chat.scrollTop = chat.scrollHeight;
  return b;
}
function typing() { const t = el("div", "fb typing show", "•••"); chat.appendChild(t); chat.scrollTop = chat.scrollHeight; return t; }
function traceItem(html, cls) {
  trace.querySelector(".d-trace-empty")?.remove();
  const li = el("li", cls || "");
  html.forEach((part) => li.append(typeof part === "string" ? document.createTextNode(part) : part));
  trace.appendChild(li);
  return li;
}
const strong = (t) => el("strong", null, t);
const sub = (t) => el("span", "t-sub", t);
function setComposer(enabled, suggested, hintText) {
  input.disabled = sendBtn.disabled = !enabled;
  input.value = enabled ? (suggested || "") : "";
  hint.textContent = hintText || "";
  if (enabled) input.focus({ preventScroll: true });
}

/* ── cards ── */
function renderCards() {
  const wrap = $("d-cards");
  SCENARIOS.forEach((s) => {
    const b = el("button", "d-card");
    b.type = "button"; b.setAttribute("role", "radio"); b.setAttribute("aria-checked", "false"); b.dataset.id = s.id;
    b.append(el("span", "d-card-num", `${s.num} · ${BRAND[s.brand].name}`), el("span", "d-card-title", s.title),
             el("span", "d-card-desc", s.desc), el("span", `d-badge d-b-${s.badge[1]}`, s.badge[0]));
    b.addEventListener("click", () => select(s));
    wrap.appendChild(b);
  });
}

function select(s) {
  scenario = s;
  document.querySelectorAll(".d-card").forEach((c) => c.setAttribute("aria-checked", String(c.dataset.id === s.id)));
  $("d-stage").hidden = false;
  start();
  $("d-stage").scrollIntoView({ behavior: REDUCED ? "auto" : "smooth", block: "start" });
}

/* ── one conversation ── */
async function start() {
  const my = ++run;
  const b = BRAND[scenario.brand];
  banner.hidden = true; doneBox.hidden = true;
  chat.innerHTML = ""; trace.innerHTML = "";
  trace.appendChild(el("li", "d-trace-empty", "Waiting for the customer's first message."));
  ticketBox.dataset.state = "empty"; ticketBox.replaceChildren(el("p", "d-ticket-empty", "No ticket. Nothing needs a person yet."));
  $("d-dash").hidden = true;
  $("d-avatar").textContent = b.initials; $("d-avatar").style.background = b.bg;
  $("d-brandname").textContent = `${b.name} Support`;
  state = { phase: "complaint", products: [], product: null, conversationId: null, replyIdx: 0 };
  bubble("sys", "Today");
  setComposer(true, scenario.complaint, "Press send. You can change the words first.");
  input.dataset.run = my;
}

$("d-composer").addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text || !state) return;
  const my = run;
  setComposer(false);
  bubble("cust", text);
  try {
    if (state.phase === "complaint") await onComplaint(text, my);
    else if (state.phase === "reply") await onReply(text, my);
  } catch (err) { if (my === run) { showError(err); setComposer(false); } }
});

async function onComplaint(text, my) {
  state.complaint = text;
  const info = await api("/api/lookup", { phone: scenario.phone, brand: scenario.brand });
  if (my !== run) return;
  if (!info.found) throw new Error("No customer found for this number.");
  state.products = info.products;
  traceItem([strong("Recognised by phone number"), sub(`${info.customer_name} · ${info.products.length} ${info.brand} product${info.products.length > 1 ? "s" : ""} on file`)]);
  if (info.products.length > 1) {
    await sleep(REDUCED ? 0 : 500);
    bubble("agent", `Hi ${info.customer_name.split(" ")[0]}! Which product is this about?`);
    state.phase = "pick";
    info.products.forEach((p) => {
      const btn = el("button", "fb prod-btn", `${p.product_name} · warranty ${p.warranty_component_status}`);
      btn.type = "button";
      btn.addEventListener("click", () => { if (state && state.phase === "pick") pickProduct(p, my, btn); });
      chat.appendChild(btn);
      requestAnimationFrame(() => requestAnimationFrame(() => btn.classList.add("show")));
    });
    chat.scrollTop = chat.scrollHeight;
    setComposer(false, "", "Tap the product it's about.");
  } else {
    await begin(info.products[0], my);
  }
}

async function pickProduct(p, my, btn) {
  state.phase = "busy";
  chat.querySelectorAll(".prod-btn").forEach((b) => { b.disabled = true; if (b !== btn) b.remove(); });
  btn.classList.add("selected");
  await begin(p, my);
}

async function begin(product, my) {
  state.product = product;
  traceItem([strong(`Product: ${product.product_name}`), sub(`Serial ${product.serial_number} · ${product.warranty_component_status === "active" ? "warranty active" : "warranty expired"}`)]);
  const t = typing();
  // One key per customer message: a network retry of *this* request can't open a second conversation.
  const r = await api("/api/start", { phone: scenario.phone, complaint: state.complaint, product_id: scenario.productId || product.product_id },
                      { "Idempotency-Key": crypto.randomUUID() });
  if (my !== run) return;
  t.remove();
  state.conversationId = r.conversation_id;
  await present(r, my);
}

async function onReply(text, my) {
  const t = typing();
  const r = await api("/api/respond", { conversation_id: state.conversationId, reply: text });
  if (my !== run) return;
  t.remove();
  state.replyIdx++;
  await present(r, my);
}

/* Show one API result: chat bubbles, trace entries, ticket, next composer state. */
async function present(r, my) {
  const m = r.meta || {};
  const esc = m.escalation;
  const method = { opensearch: "OpenSearch BM25", keyword_fallback: "keyword search (OpenSearch offline)", safety_rule: "safety rule" }[m.retrieval_method] || m.retrieval_method;

  if (r.status === "waiting") {
    if (m.attempt === 1) traceItem([strong("Searched the product manual"), sub(`${method} → ${m.section_heading}`)]);
    traceItem([strong(`Step ${m.attempt} of ${m.max_attempts} offered`), sub("Worded by the model from one numbered step in that section")]);
    bubble("agent", r.message);
    if (m.section_heading) bubble("source", `📄 ${BRAND[scenario.brand].name} manual · ${m.section_heading}`);
    state.phase = "reply";
    const next = scenario.replies[state.replyIdx];
    setComposer(true, next || "", next ? "Press send: this is how the customer answers." : "Type how the customer would answer.");
    return;
  }

  if (r.status === "resolved") {
    traceItem([strong("Resolved by the customer"), sub("No ticket created")], "t-ok");
    bubble("agent", r.message);
    bubble("ok", "✓ Resolved · no ticket");
    finish("Fixed without a ticket.");
    return;
  }

  /* escalated */
  const code = esc && esc.code;
  if (code === "safety") {
    traceItem([strong("Safety keyword in the message"), sub("Troubleshooting skipped. The manual's own warning is sent as written")], "t-safety");
  } else if (code === "unmatched") {
    traceItem([strong("Nothing in the manual matches"), sub(esc.detail)], "t-handoff");
  } else if (code === "recurring") {
    traceItem([strong("Same product, same problem, seen before"), sub(esc.detail)], "t-handoff");
  } else if (code === "attempts_exhausted") {
    traceItem([strong("Customer says it's still broken"), sub("Both manual steps tried")], "t-handoff");
  } else if (code === "no_more_steps") {
    traceItem([strong("Manual has nothing more to try"), sub("Section has no further self-service step")], "t-handoff");
  }
  traceItem([strong(`Handed to a person: ${esc ? esc.label : "needs a person"}`), sub(`Ticket ${r.ticket_id} created with what was tried`)], code === "safety" ? "t-safety" : "t-handoff");
  bubble(code === "safety" ? "warn" : "sys", code === "safety" ? "⚠ Safety issue: emergency visit" : "A person will take it from here");
  bubble("agent", r.message);
  renderTicket(r, esc);
  finish(code === "safety" ? "A technician is on the way, and the customer wasn't asked to do anything unsafe." : "A person has it, with the full story already attached.");
}

function renderTicket(r, esc) {
  const t = r.ticket;
  ticketBox.dataset.state = "filled";
  const top = el("div", "d-ticket-top");
  top.append(el("span", `d-badge d-b-${{ safety: "red", recurring: "violet", unmatched: "teal" }[esc.code] || "blue"}`, esc.label), el("span", "d-ticket-id", r.ticket_id));
  const body = [top, el("h4", null, "What the brand receives"), el("p", null, "Pre-filled. Nobody has to ask the customer to explain again.")];
  const dl = el("dl");
  const row = (k, v) => { dl.append(el("dt", null, k), el("dd", null, v)); };
  row("Customer", t.customer_name);
  row("Product", `${t.product_name} (${t.serial_number})`);
  row("Their words", t.issue_summary.split(" -- ")[0]);
  if (esc.detail) row("Why", esc.detail);
  const dd = el("dd");
  if (t.attempts_tried.length) { const ol = el("ol"); t.attempts_tried.forEach((a) => ol.appendChild(el("li", null, a))); dd.appendChild(ol); }
  else dd.textContent = t.safety_flag ? "Nothing. Safety issue, no troubleshooting" : "Nothing: no manual step applied";
  dl.append(el("dt", null, "Tried"), dd);
  body.push(dl);
  ticketBox.replaceChildren(...body);
  const dash = $("d-dash");
  dash.hidden = false;
  dash.textContent = `Open the ${BRAND[scenario.brand].name} dashboard`;
  dash.href = `/dashboard/${scenario.brand}`;   // signs in first if needed
}

function finish(text) {
  state.phase = "done";
  setComposer(false, "", "Conversation ended.");
  $("d-done-text").textContent = text;
  doneBox.hidden = false;
}

/* ── controls ── */
$("d-restart").addEventListener("click", () => { if (scenario) start(); });
$("d-reset").addEventListener("click", async () => {
  try { const r = await api("/api/demo/reset", {}); hint.textContent = `Demo data cleared (${r.cleared} saved records).`; }
  catch (e) { hint.textContent = "Reset failed."; }
  if (scenario) start();
});
$("d-next").addEventListener("click", (e) => { e.preventDefault(); $("d-pick").scrollIntoView({ behavior: REDUCED ? "auto" : "smooth" }); });

/* runtime pill: what is actually answering, from a live probe */
(async function () {
  const pill = $("d-runtime");
  if (!pill) return;
  try {
    const h = await (await fetch(API + "/api/health")).json();
    const c = h.components;
    const up = (k) => (c[k] && c[k].ok ? "●" : "○");
    pill.textContent = `Running on ${h.runtime === "lambda" ? "AWS Lambda (SAM Local)" : "Flask"} · ${h.storage === "dynamodb" ? "DynamoDB Local" : "file store"} · OpenSearch ${up("opensearch")} · Cedar ${up("cedar")} · Ollama ${up("ollama")}`;
    pill.hidden = false;
  } catch (_) { pill.hidden = true; }
})();

renderCards();
