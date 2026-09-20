/* dashboard.js — the brand dashboard. Identity is the signed session cookie; every action is a call that
   Cedar decides (a refusal is shown, with the policy that made it). */
"use strict";

const brand = window.__BRAND__;
const $ = (id) => document.getElementById(id);
const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };

const STATUS = [["new", "red", "Open: waiting for a person"], ["in_progress", "yellow", "In progress"], ["resolved", "green", "Resolved"]];
let filter = "all";
let tickets = [];
let canManage = false;

const fmt = (iso) => { const d = new Date(iso); return isNaN(d) ? "" : d.toLocaleString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }); };
const fmtDate = (iso) => { const d = new Date(iso); return isNaN(d) ? iso : d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" }); };
const post = (path, body) => fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then(async (r) => ({ ok: r.ok, data: await r.json() }));

async function load() {
  const res = await fetch(`/api/dashboard/${brand}`);
  if (res.status === 401) { location.href = `/dashboard?brand=${encodeURIComponent(brand)}`; return; }
  const data = await res.json();
  if (!res.ok) {
    $("session-line").textContent = res.status === 403 ? "Not allowed" : "Error";
    $("denied-copy").textContent = data.error || "Something went wrong.";
    $("denied-panel").hidden = false;
    return;
  }
  const who = data.authz.principal;
  canManage = who.role === "manager";
  const line = $("session-line"); line.textContent = "";
  line.append("Signed in as ", el("strong", null, who.name), ` · ${who.role}`, el("span", "db-chip", `Cedar: ${data.authz.decision.policies.join(", ")}`));
  $("dash-content").hidden = false;
  tickets = data.tickets;
  renderKpis(data);
  renderTickets();
  renderProducts(data.registrations);
  renderAi(data.insights);
}

function renderKpis(data) {
  const open = tickets.filter((t) => t.status !== "resolved").length;
  const ins = data.insights; const total = ins.resolved + (ins.answered || 0) + ins.escalated;
  const handled = total ? Math.round(100 * (ins.resolved + (ins.answered || 0)) / total) + "%" : "–";
  const safety = tickets.filter((t) => t.safety_flag).length;
  const box = $("stat-row"); box.textContent = "";
  [[String(open), "open complaints"], [handled, "handled without a person"], [String(data.registered_count), "registered products"], [String(safety), "safety cases"]]
    .forEach(([v, l]) => { const k = el("div", "db-kpi"); k.append(el("b", null, v), el("span", null, l)); box.appendChild(k); });
}

/* ── complaints ── */
const bucket = (t) => (t.status === "resolved" ? "done" : t.status === "in_progress" ? "progress" : "open");
document.querySelectorAll("#db-filter button").forEach((b) => b.addEventListener("click", () => {
  filter = b.dataset.f;
  document.querySelectorAll("#db-filter button").forEach((x) => x.classList.toggle("on", x === b));
  renderTickets();
}));

function renderTickets() {
  const list = $("ticket-list"); list.textContent = "";
  const rank = { open: 0, progress: 1, done: 2 };
  const rows = tickets.filter((t) => filter === "all" || bucket(t) === filter)
    .sort((a, b) => rank[bucket(a)] - rank[bucket(b)] || (b.created_at || "").localeCompare(a.created_at || ""));
  if (!rows.length) { list.appendChild(el("p", "db-empty", tickets.length ? "Nothing in this filter." : "No complaints yet. Run a conversation in the sandbox and it appears here.")); return; }
  rows.forEach((t) => list.appendChild(row(t)));
}

function row(t) {
  const d = el("details", "db-row");
  const sum = el("summary");
  const dots = el("span", "db-status");
  STATUS.forEach(([st, color, title]) => {
    const b = el("button", color + (t.status === st ? " on" : "")); b.type = "button"; b.title = title; b.setAttribute("aria-label", title); b.setAttribute("aria-pressed", String(t.status === st));
    b.addEventListener("click", (e) => { e.preventDefault(); e.stopPropagation(); setStatus(t, st, d); });
    dots.appendChild(b);
  });
  const main = el("div", "db-main");
  const head = el("b", null, t.customer_name); head.appendChild(el("small", null, `${t.product_name} · ${t.ticket_id}`));
  main.append(head, el("p", null, t.issue_summary.split(" -- ")[0]));
  const side = el("div", "db-side");
  side.appendChild(el("span", "db-tag" + (t.safety_flag ? " safety" : ""), t.safety_flag ? "Safety" : t.reason_label || "Ticket"));
  side.appendChild(el("span", null, `${fmt(t.created_at)} · ${t.customer_phone}${t.phone_unmasked ? " (shown: safety case)" : ""}`));
  sum.append(dots, main, side);
  d.appendChild(sum);
  d.appendChild(el("div", "db-msg"));
  d.addEventListener("toggle", () => { if (d.open) openThread(t, d); });
  return d;
}

async function setStatus(t, status, d) {
  const { ok, data } = await post(`/api/tickets/${encodeURIComponent(t.ticket_id)}/status`, { status });
  const msg = d.querySelector(".db-msg");
  if (!ok) { msg.className = "db-msg"; msg.textContent = data.error || "Not allowed"; return; }
  await load();
}

async function openThread(t, d) {
  if (d.querySelector(".db-body")) return;
  const body = el("div", "db-body");
  const thread = el("div", "db-thread");
  const form = el("form", "db-reply"); form.autocomplete = "off";
  const input = el("input"); input.placeholder = "Reply to the customer on WhatsApp"; input.setAttribute("aria-label", "Reply");
  const send = el("button", null, "Send"); send.type = "submit";
  form.append(input, send);
  body.append(thread, form);
  d.appendChild(body);
  const refresh = async () => {
    const res = await fetch(`/api/tickets/${encodeURIComponent(t.ticket_id)}/thread`);
    const data = await res.json();
    thread.textContent = "";
    if (!res.ok) { thread.appendChild(el("p", "db-empty", data.error || "Can't load the chat.")); return; }
    data.messages.forEach((m) => thread.appendChild(el("div", "db-b " + (m.kind === "note" ? "note" : m.sender), (m.sender === "human" && m.meta ? m.meta.staff + ": " : "") + m.text)));
    thread.scrollTop = thread.scrollHeight;
  };
  await refresh();
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = input.value.trim(); if (!text) return;
    const { ok, data } = await post(`/api/tickets/${encodeURIComponent(t.ticket_id)}/reply`, { text });
    const msg = d.querySelector(".db-msg");
    msg.className = "db-msg" + (ok ? " ok" : ""); msg.textContent = ok ? `Sent on WhatsApp. Allowed by ${data.decision.policies.join(", ")}` : data.error;
    if (ok) { input.value = ""; refresh(); }
  });
}

/* ── products ── */
function renderProducts(regs) {
  const tbl = $("db-products"); tbl.textContent = "";
  $("db-prod-count").textContent = `${regs.length} registered`;
  const thead = el("thead"); const hr = el("tr");
  ["Product", "Serial", "Customer", "Bought", "Warranty"].forEach((h) => hr.appendChild(el("th", null, h)));
  thead.appendChild(hr); tbl.appendChild(thead);
  const tb = el("tbody");
  if (!regs.length) { const tr = el("tr"); const td = el("td", null, "No products registered yet."); td.colSpan = 5; tr.appendChild(td); tb.appendChild(tr); }
  regs.forEach((r) => {
    const tr = el("tr");
    const w = el("td");
    [[r.warranty_component, r.warranty_component_status], ["parts", r.warranty_parts_status]].forEach(([label, st], i) => {
      if (i) w.append("   ");
      w.append(el("i", "d " + (st === "active" ? "green" : "red")), `${label} ${st}`);
    });
    tr.append(el("td", null, r.product_name), el("td", "mono", r.serial_number), el("td", null, r.customer_name), el("td", null, fmtDate(r.purchase_date)), w);
    tb.appendChild(tr);
  });
  tbl.appendChild(tb);
}

/* ── the AI analytics bar (numbers from OpenSearch aggregations, sentences built from them) ── */
function renderAi(ins) {
  const total = ins.resolved + (ins.answered || 0) + ins.escalated;
  $("db-ai").hidden = false;
  const text = $("db-ai-text"); const panel = $("db-ai-panel"); panel.textContent = "";
  if (!total) { text.textContent = "No conversations yet. Once customers message, you'll see what the agent handled and where people needed a person."; $("db-ai-toggle").hidden = true; return; }
  $("db-ai-toggle").hidden = false;
  const handled = Math.round(100 * (ins.resolved + (ins.answered || 0)) / total);
  const parts = [`${handled}% of ${total} conversation${total === 1 ? "" : "s"} were handled without a person.`];
  if (ins.by_reason.length) parts.push(`Most common reason for handing over: ${ins.by_reason[0].label} (${ins.by_reason[0].count}).`);
  const top = ins.top_sections.filter((s) => s.escalated).sort((a, b) => b.escalated - a.escalated)[0];
  if (top) parts.push(`${top.heading.split(" ")[0]} ${top.heading.split(" ").slice(1, 5).join(" ")} sends the most people to a person (${top.escalated} of ${top.count}).`);
  text.textContent = parts.join(" ");

  const bars = (title, rows, cls) => {
    const c = el("div"); c.appendChild(el("h3", null, title));
    if (!rows.length) c.appendChild(el("p", "db-muted", "Nothing yet."));
    const max = Math.max(1, ...rows.map((r) => r[1]));
    rows.forEach(([label, n, extra]) => { const b = el("div", "db-bar " + (cls || "")); const track = el("span"); const fill = el("i"); fill.style.width = Math.max(6, Math.round(100 * n / max)) + "%"; track.appendChild(fill);
      b.append(el("span", null, label), track, el("em", null, extra || String(n))); c.appendChild(b); });
    return c;
  };
  panel.append(
    bars("Why people reached a person", ins.by_reason.map((r) => [r.label, r.count])),
    bars("Manual sections that send people to a person", ins.top_sections.filter((s) => s.escalated).sort((a, b) => b.escalated - a.escalated).map((s) => [s.heading, s.escalated, `${s.escalated} of ${s.count}`]), "warn"),
    el("p", "db-ai-foot", "Computed by OpenSearch aggregations over every conversation on this brand's line."),
  );
}
$("db-ai-toggle").addEventListener("click", () => {
  const p = $("db-ai-panel"); p.hidden = !p.hidden; $("db-ai-toggle").setAttribute("aria-expanded", String(!p.hidden)); $("db-ai-toggle").textContent = p.hidden ? "Details" : "Hide";
});

load();
setInterval(() => { if (!document.querySelector(".db-row[open]") && document.activeElement.tagName !== "INPUT") load(); }, 8000);
