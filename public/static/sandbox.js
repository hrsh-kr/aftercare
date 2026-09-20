/* sandbox.js — /sandbox. A client of the real API only: /api/sandbox/*, the Meta-shaped /api/wa/webhook,
   /api/wa/messages (what the customer's phone shows), and the staff endpoints behind Cedar
   (/api/inbox, /api/tickets/*, /api/dashboard). Nothing in a conversation is scripted. */
"use strict";

const LINES = {
  aquaspin:  { name: "AquaSpin",  initials: "Aq", number: "+91 1800 000 0001", bg: "linear-gradient(135deg,#1f7a5c,#30B0C7)" },
  arcticair: { name: "ArcticAir", initials: "Ar", number: "+91 1800 000 0002", bg: "linear-gradient(135deg,#1a4a8e,#5aa0ff)" },
};
/* the same demo sign-ins the dashboard's login page shows */
const STAFF = {
  aquaspin:  { manager: ["meera.nair", "aqua-manager"], agent: ["dev.patel", "aqua-agent"] },
  arcticair: { manager: ["sara.thomas", "arctic-manager"] },   // one account keeps the demo simple; the Cedar manager/agent contrast is shown on AquaSpin
};
const CHIPS = {
  aquaspin: [
    ["Hi", ""], ["Is my machine still under warranty?", ""], ["My washing machine bangs loudly when it spins", ""],
    ["My clothes smell bad after washing", ""], ["Water is not draining from the machine", ""], ["The touch panel flickers and won't respond", ""],
    ["That fixed it, thank you!", "reply"], ["Still the same, no change", "reply"],
    ["There's a burning smell coming from my machine", "risk"], ["I want to talk to a person", "person"],
  ],
  arcticair: [
    ["Hi", ""], ["Is my AC compressor covered under warranty?", ""], ["My AC isn't cooling the room", ""],
    ["Water is dripping from my AC", ""], ["My AC remote is not working", ""], ["Wi-Fi keeps disconnecting on my AC", ""],
    ["That fixed it, thank you!", "reply"], ["Still blowing warm air, no change", "reply"],
    ["There's a burning smell coming from my AC", "risk"], ["I want to talk to a person", "person"],
  ],
};

const $ = (id) => document.getElementById(id);
const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
const strong = (t) => el("strong", null, t);
const sub = (t) => el("span", "t-sub", t);
const REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const S = { loaded: false, sent: false, customers: [], phone: "", brand: "aquaspin", cursor: "", seen: new Set(), messages: [], sending: false,
            role: "manager", signedAs: "", tab: "trace", ticket: "", threadCursor: 0 };

/* ── API ── */
async function api(path, opts = {}) {
  const res = await fetch(path, { credentials: "same-origin", ...opts });
  let data = null;
  const text = await res.text();
  try { data = JSON.parse(text); } catch (_) { data = text; }
  if (res.status === 503 && data && data.service) showBanner(data.service);
  return { ok: res.ok, status: res.status, data };
}
function showBanner(service) {
  const b = $("sb-banner"); b.hidden = false; b.textContent = "";
  const hints = { Ollama: "ollama serve", OpenSearch: "bash scripts/start_opensearch.sh", DynamoDB: "bash scripts/start_dynamodb.sh" };
  b.append(`${service} isn't reachable, and there is no fallback. Start it with `, el("code", null, hints[service] || "bash scripts/dev.sh"), " and try again.");
}
const json = (body) => ({ method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

/* ── 1 · order file ── */
async function loadSamples() {
  const { data } = await api("/api/sandbox/samples");
  const box = $("sb-samples"); box.textContent = "";
  data.forEach((s) => {
    const b = el("button", "sb-sample"); b.type = "button";
    b.append(el("b", null, s.name), el("span", null, s.about));
    b.addEventListener("click", async () => {
      const csv = await (await fetch(`/api/sandbox/samples/${encodeURIComponent(s.name)}`)).text();
      await ingest(csv, b);
    });
    b.classList.add("glow");
    box.appendChild(b);
  });
}
async function ingest(csv, btn) {
  const out = $("sb-result"); out.textContent = "Checking the file, registering customers, sending WhatsApp messages…";
  const { ok, data } = await api("/api/sandbox/ingest", { method: "POST", headers: { "Content-Type": "text/csv" }, body: csv });
  out.textContent = "";
  if (!ok) { out.append(strong("Can't read this file. "), document.createTextNode(data.error || "Unknown error")); return; }
  if (btn) btn.classList.add("loaded");
  S.loaded = true; document.querySelectorAll(".sb-sample").forEach((b) => b.classList.remove("glow")); hintComposer();
  const p = el("p"); p.append(strong(`${data.rows} rows read.`), ` ${data.registered} customers' products registered and messaged on WhatsApp, ${data.rejected} rejected.`);
  out.appendChild(p);
  const chips = el("div", "sb-chips-brand");
  data.brands.forEach((b) => chips.appendChild(el("span", null, `${b.brand}: ${b.products} product${b.products === 1 ? "" : "s"}, ${b.customers} customer${b.customers === 1 ? "" : "s"}`)));
  out.appendChild(chips);
  if (data.issues.length) { const ul = el("ul"); data.issues.forEach((i) => ul.appendChild(el("li", null, `Line ${i.line}: ${i.problem}`))); out.appendChild(ul); }
  await loadCustomers(true);
}
$("sb-file").addEventListener("change", (e) => { const f = e.target.files[0]; if (f) f.text().then((t) => ingest(t)); });
$("sb-reset").addEventListener("click", async () => {
  await api("/api/sandbox/reset", { method: "POST" });
  $("sb-result").textContent = ""; document.querySelectorAll(".sb-sample").forEach((b) => b.classList.remove("loaded"));
  S.loaded = false; S.sent = false; document.querySelectorAll(".sb-sample").forEach((b) => b.classList.add("glow"));
  S.cursor = ""; S.seen = new Set(); S.messages = []; S.ticket = ""; $("sb-thread").textContent = "";
  $("sb-trace").innerHTML = ""; $("sb-trace").appendChild(el("li", "d-trace-empty", "Send a message and each step Aftercare takes appears here."));
  await loadCustomers(false); renderInbox([]); loadStats();
});

/* the pulse marks the next thing to do: pick an order file, then say something, then (when a chat is handed over) reply */
function hintComposer() {
  const on = S.loaded && !S.sent && !!S.phone;
  $("sb-input").classList.toggle("glow", on);
  document.querySelector("#sb-composer button").classList.toggle("glow", on);
  document.querySelector(".sb-chip-title").classList.toggle("sb-nudge", on);
}

/* ── 2 · the phone ── */
async function loadCustomers(keepSelection) {
  const { data } = await api("/api/sandbox/customers");
  S.customers = data || [];
  const sel = $("sb-customer"); const prev = keepSelection ? S.phone : "";
  sel.textContent = "";
  S.customers.forEach((c) => {
    const brands = [...new Set(c.products.map((p) => LINES[p.brand].name))].join(" + ");
    sel.appendChild(Object.assign(el("option", null, `${c.name} · ${brands}`), { value: c.phone }));
  });
  if (prev && S.customers.some((c) => c.phone === prev)) sel.value = prev;
  selectCustomer(sel.value || (S.customers[0] && S.customers[0].phone) || "");
  hintComposer();
}
function customer() { return S.customers.find((c) => c.phone === S.phone); }
function selectCustomer(phone) {
  const changed = phone !== S.phone;
  S.phone = phone;
  const c = customer();
  const brands = c ? [...new Set(c.products.map((p) => p.brand))] : [];
  if (c && !brands.includes(S.brand)) S.brand = brands[0];
  renderLines(brands);
  if (changed) resetThread();
  renderChips(); applyLine();
}
$("sb-customer").addEventListener("change", (e) => selectCustomer(e.target.value));
function renderLines(brands) {
  const box = $("sb-lines"); box.textContent = "";
  Object.keys(LINES).forEach((k) => {
    const b = el("button", "sb-line" + (S.brand === k ? " on" : ""), LINES[k].name); b.type = "button"; b.disabled = !brands.includes(k);
    b.addEventListener("click", () => { S.brand = k; renderLines(brands); resetThread(); renderChips(); applyLine(); ensureStaff(true); });
    box.appendChild(b);
  });
}
function applyLine() {
  const L = LINES[S.brand];
  $("sb-avatar").textContent = L.initials; $("sb-avatar").style.background = L.bg;
  $("sb-linename").textContent = `${L.name} Support`; $("sb-linesub").textContent = `Business account · ${L.number}`;
  $("sb-dash").href = `/dashboard/${S.brand}`;
  const has = !!customer();
  $("sb-input").disabled = !has; document.querySelectorAll(".sb-chip").forEach((c) => (c.disabled = !has));
}
function resetThread() { S.cursor = ""; S.seen = new Set(); S.messages = []; $("sb-thread").textContent = ""; poll(); }
function renderChips() {
  const box = $("sb-chips"); box.textContent = "";
  (CHIPS[S.brand] || []).forEach(([text, kind]) => {
    const b = el("button", "sb-chip " + kind, text); b.type = "button";
    b.addEventListener("click", () => send(text)); box.appendChild(b);
  });
}

function bubble(m, isLast) {
  if (m.kind === "note") return el("div", "sb-msg note", m.text);
  const wrap = el("div", "sb-msg " + m.sender);
  if (m.sender === "human") wrap.appendChild(el("span", "who", `${(m.meta && m.meta.staff) || "Team"} · ${LINES[S.brand].name} team`));
  wrap.appendChild(document.createTextNode(m.text));
  if (m.kind !== "buttons") return wrap;
  const holder = el("div", "sb-btns");
  holder.appendChild(wrap);
  (m.buttons || []).forEach((bt) => {
    const b = el("button", "sb-btn", bt.title); b.type = "button"; b.disabled = !isLast;
    b.addEventListener("click", () => sendButton(bt));
    holder.appendChild(b);
  });
  return holder;
}
function renderThread() {
  const box = $("sb-thread"); const atBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 60;
  box.textContent = "";
  S.messages.forEach((m, i) => box.appendChild(bubble(m, i === S.messages.length - 1)));
  if (S.sending) box.appendChild(el("div", "sb-msg typing", "•••"));
  if (atBottom || S.sending) box.scrollTop = box.scrollHeight;
}
async function poll() {
  if (!S.phone) return;
  const { ok, data } = await api(`/api/wa/messages?brand=${S.brand}&phone=${encodeURIComponent(S.phone)}&after=${encodeURIComponent(S.cursor)}`);
  if (!ok) return;
  let added = false;
  data.messages.forEach((m) => { if (!S.seen.has(m.cursor)) { S.seen.add(m.cursor); S.messages.push(m); S.cursor = m.cursor; added = true; } });
  if (added) renderThread();
}
setInterval(poll, 1100);

function webhookBody(message) {
  const digits = S.phone.replace(/\D/g, "");
  return { object: "whatsapp_business_account", entry: [{ id: "sandbox", changes: [{ field: "messages", value: {
    messaging_product: "whatsapp", metadata: { display_phone_number: LINES[S.brand].number, phone_number_id: "sandbox-" + S.brand },
    contacts: [{ profile: { name: (customer() || {}).name || "" }, wa_id: digits }],
    messages: [{ from: digits, id: "wamid." + Math.random().toString(36).slice(2), timestamp: String(Math.floor(Date.now() / 1000)), ...message }] } }] }] };
}
async function deliver(message) {
  if (S.sending || !S.phone) return;
  S.sending = true; S.sent = true; hintComposer(); $("sb-input").disabled = true; renderThread();
  const fast = setInterval(poll, 350);                       // the customer's own message shows up straight away
  const { ok, data } = await api("/api/wa/webhook", json(webhookBody(message)));
  clearInterval(fast); S.sending = false; $("sb-input").disabled = false;
  await poll(); renderThread();
  if (ok) renderTrace(data.replies || []);
  loadInbox(); loadStats();
}
function send(text) { $("sb-input").value = ""; return deliver({ type: "text", text: { body: text } }); }
function sendButton(bt) { return deliver({ type: "interactive", interactive: { type: "button_reply", button_reply: { id: bt.id, title: bt.title } } }); }
$("sb-composer").addEventListener("submit", (e) => { e.preventDefault(); const t = $("sb-input").value.trim(); if (t) send(t); });

/* ── 3a · what Aftercare did (built only from the fields the API returned) ── */
function traceItem(list, parts, cls, tag) {
  const li = el("li", cls || "");
  if (tag) li.appendChild(el("span", "t-tag", tag));
  parts.forEach((p) => li.append(typeof p === "string" ? document.createTextNode(p) : p));
  list.appendChild(li);
}
function renderTrace(replies) {
  const ol = $("sb-trace"); ol.textContent = "";
  const c = customer();
  if (c) traceItem(ol, [strong("Recognised by phone number"), sub(`${c.name} · ${c.products.filter((p) => p.brand === S.brand).length} ${LINES[S.brand].name} product(s) on file`)], "", "Registry");
  replies.forEach((m) => {
    const meta = m.meta || {};
    if (m.kind === "buttons") { traceItem(ol, [strong("Owns several products: asked which one"), sub("Buttons sent; the customer's message is kept until they answer")], "", "Rule"); return; }
    if (m.kind === "note" || !meta.status) return;
    const esc = meta.escalation; const ms = (meta.model_ms || []).reduce((a, b) => a + b, 0);
    if (meta.status === "answered") {
      traceItem(ol, [strong("Warranty question: answered, not troubleshot"), sub("Dates computed from the purchase date; coverage quoted from " + (meta.section_heading || "the Terms"))], "t-ok", "Rule · OpenSearch"); return;
    }
    if (meta.status === "waiting") {
      if (meta.attempt === 1) traceItem(ol, [strong("Searched the product manual"), sub(`BM25 → ${meta.section_heading}`)], "", "OpenSearch");
      traceItem(ol, [strong(`Step ${meta.attempt} of ${meta.max_attempts} offered`), sub("Worded by the model from one numbered step in that section")], "", ms ? `Strands · ${(ms / 1000).toFixed(1)} s` : "Strands"); return;
    }
    if (meta.status === "resolved") { traceItem(ol, [strong("Resolved by the customer"), sub("No ticket created")], "t-ok", "Rule"); return; }
    if (esc) {
      const why = { safety: ["Safety keyword or safety section", "Troubleshooting skipped; the manual's own warning is sent as written"],
                    unmatched: ["Nothing in the manual matches", esc.detail], recurring: ["Same product, same problem, seen before", esc.detail],
                    attempts_exhausted: ["Customer says it's still broken", "Both manual steps tried"], no_more_steps: ["Manual has nothing more to try", ""],
                    human_requested: ["Customer asked for a person", "No troubleshooting attempted"], no_steps: ["Needs a person", ""] }[esc.code] || [esc.label, ""];
      traceItem(ol, [strong(why[0]), sub((why[1] || "").replace(" -- ", " · "))], esc.code === "safety" ? "t-safety" : "t-handoff", esc.code === "recurring" ? "OpenSearch" : "Rule");
      traceItem(ol, [strong(`Handed to a person: ${esc.label}`), sub(`Ticket ${m.meta.ticket_id || ""} created with what was tried. It is in the brand's inbox now`)], esc.code === "safety" ? "t-safety" : "t-handoff", "DynamoDB");
    }
  });
  if (!ol.children.length) ol.appendChild(el("li", "d-trace-empty", "Nothing to show for that message."));
}

/* ── 3b · staff: sign-in (real, Cedar-decided), inbox, reply ── */
async function ensureStaff(force) {
  if (!STAFF[S.brand][S.role]) S.role = "manager";        // ArcticAir has only a manager account
  const want = STAFF[S.brand][S.role][0];
  if (!force && S.signedAs === want) return true;
  const [u, p] = STAFF[S.brand][S.role];
  const { ok, data } = await api("/api/login", json({ username: u, passcode: p }));
  if (!ok) return false;
  S.signedAs = u;
  const who = $("sb-who"); who.textContent = "";
  who.append("Signed in as ", strong(`${data.principal.name} (${data.principal.role})`), " · Cedar decides what this person may do.");
  if (STAFF[S.brand].agent) {
    const sw = el("button", null, S.role === "manager" ? "Switch to an agent" : "Switch to the manager"); sw.type = "button";
    sw.addEventListener("click", () => { S.role = S.role === "manager" ? "agent" : "manager"; ensureStaff(true).then(loadInbox); });
    who.appendChild(sw);
  }
  return true;
}
function renderInbox(chats) {
  const box = $("sb-inbox"); box.textContent = "";
  const open = chats.filter((c) => c.mode === "human" && c.ticket_status !== "resolved");
  const badge = $("sb-inbox-count"); badge.hidden = !open.length; badge.textContent = open.length;
  document.querySelector('[data-tab="inbox"]').classList.toggle("glow", open.length > 0 && S.tab !== "inbox");
  if (!chats.length) { box.appendChild(el("p", "sb-empty", "No chats yet.")); return; }
  chats.forEach((c) => {
    const b = el("button", "sb-chat" + (c.ticket_id && c.ticket_id === S.ticket ? " sel" : "")); b.type = "button";
    const head = el("b", null, c.customer_name);
    if (c.reason && c.mode === "human") head.appendChild(el("span", "sb-tag" + (c.safety ? " safety" : ""), c.reason));
    if (c.ticket_status === "resolved") head.appendChild(el("span", "sb-tag done", "Resolved"));
    b.append(head, el("small", null, c.unread ? `${c.unread} new` : c.mode === "human" ? "with a person" : "bot"), el("p", null, c.last_text));
    b.addEventListener("click", () => { if (c.ticket_id) openTicket(c.ticket_id); });
    box.appendChild(b);
  });
}
async function loadInbox() {
  if (!(await ensureStaff(false))) return;
  const { ok, data } = await api(`/api/inbox/${S.brand}`);
  if (ok) renderInbox(data.chats);
  if (S.ticket) refreshTicket();
}
async function openTicket(id) { S.ticket = id; $("sb-staff").hidden = false; $("sb-staff-input").classList.add("glow"); $("sb-staff-msg").textContent = ""; await refreshTicket(true); loadInbox(); }
async function refreshTicket(scroll) {
  const { ok, data } = await api(`/api/tickets/${encodeURIComponent(S.ticket)}/thread`);
  if (!ok) { $("sb-staff-msg").className = "no"; $("sb-staff-msg").textContent = data.error || ""; return; }
  $("sb-staff-title").textContent = `${data.ticket.ticket_id} · ${data.ticket.customer_name} · ${data.ticket.product_name}`;
  const badge = $("sb-staff-badge"); badge.textContent = ""; badge.className = "";
  badge.appendChild(el("span", "sb-tag" + (data.ticket.safety_flag ? " safety" : ""), data.ticket.reason_label || "Ticket"));
  const box = $("sb-staff-thread"); const stick = scroll || box.scrollHeight - box.scrollTop - box.clientHeight < 40;
  box.textContent = "";
  data.messages.forEach((m) => box.appendChild(el("div", "sb-s " + (m.kind === "note" ? "note" : m.sender), (m.sender === "human" && m.meta ? m.meta.staff + ": " : "") + m.text)));
  if (stick) box.scrollTop = box.scrollHeight;
}
$("sb-staff-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const t = $("sb-staff-input").value.trim(); if (!t || !S.ticket) return;
  const { ok, data } = await api(`/api/tickets/${encodeURIComponent(S.ticket)}/reply`, json({ text: t }));
  const msg = $("sb-staff-msg"); msg.className = ok ? "ok" : "no"; msg.textContent = ok ? `Sent. Allowed by ${data.decision.policies.join(", ")}` : data.error;
  if (ok) { $("sb-staff-input").value = ""; $("sb-staff-input").classList.remove("glow"); refreshTicket(true); poll(); }
});
document.querySelectorAll(".sb-staff-actions [data-st]").forEach((b) => b.addEventListener("click", async () => {
  if (!S.ticket) return;
  const { ok, data } = await api(`/api/tickets/${encodeURIComponent(S.ticket)}/status`, json({ status: b.dataset.st }));
  const msg = $("sb-staff-msg"); msg.className = ok ? "ok" : "no"; msg.textContent = ok ? `Done. Allowed by ${data.decision.policies.join(", ")}` : data.error;
  if (ok) { refreshTicket(); loadInbox(); loadStats(); poll(); }
}));
setInterval(() => { if (S.tab === "inbox") loadInbox(); else if (S.tab !== "stats") loadInbox(); }, 2500);

/* ── 3c · analytics (the dashboard's own numbers) ── */
async function loadStats() {
  if (!(await ensureStaff(false))) return;
  const { ok, data } = await api(`/api/dashboard/${S.brand}`);
  const box = $("sb-stats");
  if (!ok) { box.textContent = data.error || ""; return; }
  const i = data.insights; const total = i.resolved + (i.answered || 0) + i.escalated;
  box.textContent = "";
  const k = el("div", "sb-kpis");
  const kpi = (v, l) => { const d = el("div", "sb-kpi"); d.append(el("b", null, v), el("span", null, l)); return d; };
  k.append(kpi(total ? Math.round(100 * (i.resolved + (i.answered || 0)) / total) + "%" : "–", "handled with no person"), kpi(String(total), "conversations"),
           kpi(String(i.escalated), "handed to a person"), kpi(String(data.registered_count), "registered products"));
  box.appendChild(k);
  const bars = (title, rows, cls) => {
    const d = el("div", "sb-bars"); d.appendChild(el("h4", null, title));
    if (!rows.length) d.appendChild(el("p", "sb-empty", "Nothing yet."));
    const max = Math.max(1, ...rows.map((r) => r[1]));
    rows.forEach(([label, n, extra]) => { const r = el("div", "sb-bar " + (cls || "")); const bar = el("span"); const fill = el("i"); fill.style.width = Math.max(6, Math.round(100 * n / max)) + "%"; bar.appendChild(fill);
      r.append(el("span", null, label), bar, el("span", null, extra || String(n))); d.appendChild(r); });
    return d;
  };
  box.appendChild(bars("Why they reached a person", i.by_reason.map((r) => [r.label, r.count])));
  box.appendChild(bars("Manual sections that send people to a person", i.top_sections.filter((s) => s.escalated).sort((a, b) => b.escalated - a.escalated).map((s) => [s.heading, s.escalated, `${s.escalated} of ${s.count}`]), "warn"));
  box.appendChild(el("p", "sb-empty", i.engine === "opensearch" ? "Computed by OpenSearch aggregations." : ""));
}
setInterval(() => { if (S.tab === "stats") loadStats(); }, 5000);

/* tabs */
document.querySelectorAll(".sb-tab").forEach((t) => t.addEventListener("click", () => {
  S.tab = t.dataset.tab; t.classList.remove("glow");
  document.querySelectorAll(".sb-tab").forEach((x) => x.classList.toggle("on", x === t));
  ["trace", "inbox", "stats"].forEach((n) => ($("pane-" + n).hidden = n !== S.tab));
  if (S.tab === "inbox") loadInbox(); if (S.tab === "stats") loadStats();
}));

/* runtime pill */
(async function () {
  const { ok, data } = await api("/api/health");
  if (!ok) return;
  const pill = $("sb-runtime"); pill.textContent = ""; pill.append("Served by AWS Lambda (SAM Local)");
  [["DynamoDB", "dynamodb"], ["OpenSearch", "opensearch"], ["Cedar", "cedar"], ["Ollama", "ollama"]].forEach(([label, k]) => {
    pill.append(" · ", el("span", data.components[k].ok ? "up" : "down", "●"), " " + label);
  });
  pill.hidden = false;
})();

loadSamples(); loadCustomers(false).then(() => { loadInbox(); });
