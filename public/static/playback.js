/* playback.js — the Live demo page. Replays a run recorded from the real local stack (public/static/recording.json):
   the order-file check, eight customers' WhatsApp conversations, what Aftercare did, the brand's inbox (a person replies,
   Cedar decides), and the analytics. Every reply, trace line, ticket and Cedar decision is a recorded value; nothing is
   generated here. It mirrors the real /sandbox page, minus anything that needs a running backend. */
"use strict";

const $ = (id) => document.getElementById(id);
const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
const strong = (t) => el("strong", null, t);
const sub = (t) => el("span", "t-sub", t);
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const LINES = { aquaspin: { name: "AquaSpin", initials: "Aq", number: "+91 1800 000 0001", bg: "linear-gradient(135deg,#1f7a5c,#30B0C7)" },
                arcticair: { name: "ArcticAir", initials: "Ar", number: "+91 1800 000 0002", bg: "linear-gradient(135deg,#1a4a8e,#5aa0ff)" } };
const TONE = { arjun: "green", kavya: "orange", rohan: "purple", neha: "blue", imran: "teal", divya: "yellow", sanjay: "pink", meera: "indigo" };

let rec, cur = null, idx = 0, busy = false, run = 0, thread = [], tab = "trace", selected = "";
const played = new Map();      // ticket_id -> { brand, persona, customer, reason, safety, status } (only what has been replayed so far)

fetch("/static/recording.json").then((r) => r.json()).then((j) => { rec = j; init(); });

/* ── setup ── */
function init() {
  $("pb-when").textContent = new Date(rec.recorded_at).toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" });
  $("pb-model").textContent = rec.model;
  initOrders(); initPeople(); initTabs();
  $("pb-composer").addEventListener("submit", (e) => { e.preventDefault(); playCustomer(); });
  $("pb-restart").addEventListener("click", () => { for (const [id, t] of played) if (t.persona === cur.id) played.delete(id); select(cur.id); });
  select(rec.personas[0].id);
}

/* ── 1 · the order file ── */
function initOrders() {
  const files = [
    { name: "orders_croma_sep2026.csv", about: "A store's export: AquaSpin and ArcticAir mixed, plus rows that need fixing.", data: rec.ingest },
    { name: "orders_aquaspin_direct.csv", about: "A brand's own export: clean, one brand.", data: rec.ingest_direct },
  ];
  const box = $("pb-samples");
  files.forEach((f) => {
    const b = el("button", "sb-sample glow"); b.type = "button";
    b.append(el("b", null, f.name), el("span", null, f.about));
    b.addEventListener("click", () => {
      document.querySelectorAll(".sb-sample").forEach((x) => { x.classList.remove("glow"); x.classList.toggle("loaded", x === b); });
      showOrders(f.data);
    });
    box.appendChild(b);
  });
}
function showOrders(d) {
  const out = $("pb-result"); out.textContent = "";
  const p = el("p"); p.append(strong(`${d.rows} rows read.`), ` ${d.accepted} products registered and messaged on WhatsApp, ${d.rejected} rejected.`);
  out.appendChild(p);
  const chips = el("div", "sb-chips-brand");
  d.brands.forEach((b) => chips.appendChild(el("span", null, `${b.brand}: ${b.products} product${b.products === 1 ? "" : "s"}, ${b.customers} customer${b.customers === 1 ? "" : "s"}`)));
  out.appendChild(chips);
  if (d.issues.length) { const ul = el("ul"); d.issues.forEach((i) => ul.appendChild(el("li", null, `Line ${i.line}: ${i.problem}`))); out.appendChild(ul); }
}

/* ── 2 · customers (stories, not a dropdown) ── */
function initPeople() {
  const box = $("pb-people");
  rec.personas.forEach((p) => {
    const b = el("button", "pb-person tone-" + (TONE[p.id] || "blue")); b.type = "button"; b.dataset.id = p.id;
    b.append(el("b", null, p.name), el("small", null, `${LINES[p.brand].name} line · ${p.phone_masked}`), el("span", null, p.blurb), el("span", "pb-out", p.outcome));
    b.addEventListener("click", () => select(p.id));
    box.appendChild(b);
  });
  const hint = $("pb-scrollhint");
  const sync = () => { hint.hidden = box.scrollTop + box.clientHeight >= box.scrollHeight - 12; };
  box.addEventListener("scroll", sync, { passive: true }); window.addEventListener("resize", sync);
  hint.addEventListener("click", () => box.scrollBy({ top: box.clientHeight * 0.8, behavior: REDUCED ? "auto" : "smooth" }));
  sync();
}

function select(id) {
  run++;
  cur = rec.personas.find((p) => p.id === id); idx = 0; busy = false; thread = [...cur.registration]; selected = "";
  document.querySelectorAll(".pb-person").forEach((b) => b.classList.toggle("on", b.dataset.id === id));
  const L = LINES[cur.brand];
  $("pb-avatar").textContent = L.initials; $("pb-avatar").style.background = L.bg;
  $("pb-linename").textContent = `${L.name} Support`; $("pb-linesub").textContent = `Business account · ${L.number}`;
  $("pb-trace").textContent = ""; $("pb-trace").appendChild(el("li", "d-trace-empty", "Send a message and each step Aftercare takes appears here."));
  $("pb-input").value = "";
  render(); refresh();
  $("pb-staff").hidden = true;
}

/* everything that depends on how far along the current customer is */
function refresh() {
  renderChips(); renderInbox(); renderStats();
  $("pb-over").hidden = !(cur.steps.length && idx >= cur.steps.length);
  if (selected) renderStaff();
}

function renderChips() {
  const box = $("pb-chips"); box.textContent = "";
  cur.steps.forEach((s, i) => {
    if (s.who !== "customer") return;
    const state = i < idx ? "done" : i === idx ? "next" : "later";
    const b = el("button", "sb-chip pb-chip " + state, s.text); b.type = "button";
    b.disabled = state !== "next" || busy;
    b.addEventListener("click", playCustomer);
    box.appendChild(b);
  });
  const nxt = cur.steps[idx];
  if (nxt && nxt.who !== "customer") box.appendChild(el("p", "sb-empty", "Now the brand takes over. Open the Inbox."));
}

/* ── the phone ── */
function bubble(m) {
  if (m.kind === "note") return el("div", "sb-msg note", m.text);
  const wrap = el("div", "sb-msg " + m.sender);
  if (m.sender === "human") wrap.appendChild(el("span", "who", `${(m.meta && m.meta.staff) || "Team"} · ${LINES[cur.brand].name} team`));
  wrap.appendChild(document.createTextNode(m.text));
  if (m.kind !== "buttons") return wrap;
  const holder = el("div", "sb-btns"); holder.appendChild(wrap);
  (m.buttons || []).forEach((bt) => { const b = el("button", "sb-btn", bt.title); b.type = "button"; b.disabled = true; if (m.chosen === bt.title) b.style.borderColor = "#30B0C7"; holder.appendChild(b); });
  return holder;
}
function render(typing) {
  const box = $("pb-thread"); box.textContent = "";
  thread.forEach((m) => box.appendChild(bubble(m)));
  if (typing) box.appendChild(el("div", "sb-msg typing", "•••"));
  box.scrollTop = box.scrollHeight;
}

async function playCustomer() {
  const s = cur.steps[idx]; if (!s || s.who !== "customer" || busy) return;
  const my = run; busy = true; renderChips();
  $("pb-input").value = s.text; await wait(REDUCED ? 0 : 450); if (my !== run) return;   // the message "types" itself, then sends
  $("pb-input").value = "";
  if (s.button) { const b = [...thread].reverse().find((m) => m.kind === "buttons"); if (b) b.chosen = s.text; }
  thread.push({ sender: "customer", kind: "text", text: s.text }); render(true);
  await wait(REDUCED ? 0 : 1000); if (my !== run) return;
  for (const m of s.replies) { thread.push(m); render(); await wait(REDUCED ? 0 : 420); if (my !== run) return; }
  traceFor(s.replies);
  s.replies.forEach((m) => {                       // a hand-over creates a ticket that now exists in the brand's inbox
    const meta = m.meta || {};
    if (meta.ticket_id && meta.escalation && !played.has(meta.ticket_id))
      played.set(meta.ticket_id, { brand: cur.brand, persona: cur.id, customer: cur.name, reason: meta.escalation.label, safety: meta.escalation.code === "safety", status: "new" });
  });
  idx++; busy = false; refresh();
  const nxt = cur.steps[idx];
  if (nxt && nxt.who !== "customer") { const t = ticketOf(cur.id); if (t) { showTab("inbox"); openTicket(t[0]); } }
}

/* ── what Aftercare did (built only from the fields the real API returned) ── */
function traceFor(replies) {
  const ol = $("pb-trace"); ol.textContent = "";
  const item = (parts, cls, tag) => { const li = el("li", cls || ""); if (tag) li.appendChild(el("span", "t-tag", tag)); parts.forEach((p) => li.append(typeof p === "string" ? document.createTextNode(p) : p)); ol.appendChild(li); };
  item([strong("Recognised by phone number"), sub(`${cur.name} · registered with ${LINES[cur.brand].name}`)], "", "Registry");
  replies.forEach((m) => {
    const meta = m.meta || {};
    if (m.kind === "buttons") { item([strong("Owns several products: asked which one"), sub("Buttons sent; the customer's message is kept until they answer")], "", "Rule"); return; }
    if (m.kind === "note" || !meta.status) return;
    const esc = meta.escalation; const ms = (meta.model_ms || []).reduce((a, b) => a + b, 0);
    if (meta.status === "answered") { item([strong("Warranty question: answered, not troubleshot"), sub("Dates computed from the purchase date; coverage quoted from " + (meta.section_heading || "the Terms"))], "t-ok", "Rule · OpenSearch"); return; }
    if (meta.status === "waiting") {
      if (meta.attempt === 1) item([strong("Searched the product manual"), sub(`BM25 → ${meta.section_heading}`)], "", "OpenSearch");
      item([strong(`Step ${meta.attempt} of ${meta.max_attempts} offered`), sub("Worded by the model from one numbered step in that section")], "", ms ? `Strands · ${(ms / 1000).toFixed(1)} s` : "Strands"); return;
    }
    if (meta.status === "resolved") { item([strong("Resolved by the customer"), sub("No ticket created")], "t-ok", "Rule"); return; }
    if (esc) {
      const why = { safety: ["Safety keyword or safety section", "Troubleshooting skipped; the manual's own warning is sent as written"], unmatched: ["Nothing in the manual matches", esc.detail],
                    recurring: ["Same product, same problem, seen before", esc.detail], attempts_exhausted: ["Customer says it's still broken", "Both manual steps tried"],
                    human_requested: ["Customer asked for a person", "No troubleshooting attempted"] }[esc.code] || [esc.label, ""];
      item([strong(why[0]), sub((why[1] || "").replace(" -- ", " · "))], esc.code === "safety" ? "t-safety" : "t-handoff", esc.code === "recurring" ? "OpenSearch" : "Rule");
      item([strong(`Handed to a person: ${esc.label}`), sub(`Ticket ${meta.ticket_id || ""} created with what was tried. It is in the brand's inbox now`)], esc.code === "safety" ? "t-safety" : "t-handoff", "DynamoDB");
    }
  });
  if (!ol.children.length) ol.appendChild(el("li", "d-trace-empty", "Nothing to show for that message."));
}

/* ── tabs ── */
function initTabs() {
  document.querySelectorAll(".pb-col .sb-tab").forEach((t) => t.addEventListener("click", () => showTab(t.dataset.tab)));
}
function showTab(name) {
  tab = name;
  document.querySelectorAll(".pb-col .sb-tab").forEach((x) => x.classList.toggle("on", x.dataset.tab === name));
  ["trace", "inbox", "stats"].forEach((n) => ($("pane-" + n).hidden = n !== name));
}

/* ── 3b · the brand's inbox: a person replies, Cedar decides ── */
const ticketOf = (personaId) => [...played].find(([, t]) => t.persona === personaId);
function renderInbox() {
  const box = $("pb-inbox"); box.textContent = "";
  const p = rec.inbox[cur.brand] && rec.inbox[cur.brand].principal;
  const who = $("pb-who"); who.textContent = "";
  if (p) who.append(`${LINES[cur.brand].name} inbox. `, "Signed in as ", strong(`${p.name} (${p.role})`), ". Recorded.");
  const rows = [...played].filter(([, t]) => t.brand === cur.brand);
  const open = rows.filter(([, t]) => t.status !== "resolved").length;
  const badge = $("pb-inbox-count"); badge.hidden = !open; badge.textContent = open;
  if (!rows.length) { box.appendChild(el("p", "sb-empty", "No chats yet. Someone has to need a person first.")); return; }
  rows.sort((a, b) => (a[1].status === "resolved") - (b[1].status === "resolved"));
  rows.forEach(([id, t]) => {
    const b = el("button", "sb-chat" + (id === selected ? " sel" : "")); b.type = "button";
    const head = el("b", null, t.customer);
    head.appendChild(el("span", "sb-tag" + (t.safety ? " safety" : ""), t.reason));
    if (t.status === "resolved") head.appendChild(el("span", "sb-tag done", "Resolved"));
    b.append(head, el("small", null, id), el("p", null, lastText(id)));
    b.addEventListener("click", () => openTicket(id));
    box.appendChild(b);
  });
}
function lastText(id) {
  const t = played.get(id); const msgs = chatOf(id);
  const m = [...msgs].reverse().find((x) => x.kind !== "note");
  return m ? m.text : t.reason;
}
/* the chat behind a ticket: live for the customer being played, the recorded final chat for the others */
function chatOf(id) {
  const t = played.get(id);
  if (t && t.persona === cur.id) return thread;
  return (rec.threads[id] && rec.threads[id].messages) || [];
}
function openTicket(id) { selected = id; $("pb-staff").hidden = false; renderInbox(); renderStaff(); }
function renderStaff() {
  const t = played.get(selected); if (!t) { $("pb-staff").hidden = true; return; }
  $("pb-staff-title").textContent = `${selected} · ${t.customer}`;
  const badge = $("pb-staff-badge"); badge.textContent = ""; badge.appendChild(el("span", "sb-tag" + (t.safety ? " safety" : ""), t.reason));
  const box = $("pb-staff-thread"); box.textContent = "";
  chatOf(selected).forEach((m) => box.appendChild(el("div", "sb-s " + (m.kind === "note" ? "note" : m.sender), (m.sender === "human" && m.meta ? m.meta.staff + ": " : "") + m.text)));
  box.scrollTop = box.scrollHeight;
  // the next recorded staff step, as a chip (only for the customer being played)
  const acts = $("pb-actions"); acts.textContent = "";
  const s = cur.steps[idx];
  if (t.persona === cur.id && s && s.who !== "customer") {
    const label = s.who === "staff" ? `Reply as ${s.actor.split(" (")[0]}: “${s.text}”` : `${s.action} as ${s.actor}`;
    const b = el("button", "sb-chip pb-chip next", label); b.type = "button"; b.addEventListener("click", playStaff); acts.appendChild(b);
  }
}
function playStaff() {
  const s = cur.steps[idx]; if (!s || s.who === "customer") return;
  const id = ticketOf(cur.id)[0], t = played.get(id);
  const note = $("pb-staff-msg");
  if (s.who === "staff") {
    thread.push({ sender: "human", kind: "text", text: s.text, meta: { staff: s.actor.split(" (")[0] } });
    note.className = "pb-note " + (s.result.startsWith("Allowed") ? "ok" : "no"); note.textContent = `${s.actor}. ${s.result}`;
    t.status = t.status === "new" ? "in_progress" : t.status;
  } else {
    note.className = "pb-note " + (s.ok ? "ok" : "no"); note.textContent = s.ok ? `${s.actor}. Allowed. ${s.result}` : `${s.actor}. Refused. ${s.result}`;
    s.replies.forEach((m) => thread.push(m));
    if (s.ok) t.status = "resolved";
  }
  idx++; render(); refresh();
}

/* ── 3c · analytics (the dashboard's own numbers, recorded) ── */
function renderStats() {
  const d = rec.dashboard[cur.brand]; const box = $("pb-stats"); box.textContent = "";
  if (!d || !d.insights) return;
  const i = d.insights; const total = i.resolved + (i.answered || 0) + i.escalated;
  const k = el("div", "sb-kpis");
  const kpi = (v, l) => { const x = el("div", "sb-kpi"); x.append(el("b", null, v), el("span", null, l)); return x; };
  k.append(kpi(total ? Math.round(100 * (i.resolved + (i.answered || 0)) / total) + "%" : "–", "handled with no person"), kpi(String(total), "conversations"),
           kpi(String(i.escalated), "handed to a person"), kpi(String(d.registered_count), "registered products"));
  box.appendChild(k);
  const bars = (title, rows, cls) => {
    const c = el("div", "sb-bars"); c.appendChild(el("h4", null, title));
    if (!rows.length) c.appendChild(el("p", "sb-empty", "Nothing yet."));
    const max = Math.max(1, ...rows.map((r) => r[1]));
    rows.forEach(([label, n, extra]) => { const r = el("div", "sb-bar " + (cls || "")); const bar = el("span"); const fill = el("i"); fill.style.width = Math.max(6, Math.round(100 * n / max)) + "%"; bar.appendChild(fill);
      r.append(el("span", null, label), bar, el("span", null, extra || String(n))); c.appendChild(r); });
    return c;
  };
  box.appendChild(bars("Why they reached a person", i.by_reason.map((r) => [r.label, r.count])));
  box.appendChild(bars("Manual sections that send people to a person", i.top_sections.filter((s) => s.escalated).sort((a, b) => b.escalated - a.escalated).map((s) => [s.heading, s.escalated, `${s.escalated} of ${s.count}`]), "warn"));
  box.appendChild(el("p", "sb-empty", `Recorded after all eight conversations. Computed by OpenSearch aggregations on the ${LINES[cur.brand].name} line.`));
}
