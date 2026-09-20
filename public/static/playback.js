/* playback.js — plays back the recorded sandbox run (static site). Every bubble, trace line and Cedar decision
   comes from /static/recording.json, captured from the real local stack; nothing is generated here. */
"use strict";

const $ = (id) => document.getElementById(id);
const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
const strong = (t) => el("strong", null, t);
const sub = (t) => el("span", "t-sub", t);
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const LINES = { aquaspin: { name: "AquaSpin", initials: "Aq", number: "+91 1800 000 0001", bg: "linear-gradient(135deg,#1f7a5c,#30B0C7)" },
                arcticair: { name: "ArcticAir", initials: "Ar", number: "+91 1800 000 0002", bg: "linear-gradient(135deg,#1a4a8e,#5aa0ff)" } };

let rec, cur = null, idx = 0, busy = false, run = 0, thread = [];

fetch("/static/recording.json").then((r) => r.json()).then((j) => { rec = j; init(); });

function init() {
  const d = new Date(rec.recorded_at);
  $("pb-when").textContent = d.toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" });
  $("pb-model").textContent = rec.model;
  const box = $("pb-people");
  rec.personas.forEach((p) => {
    const b = el("button", "pb-person"); b.type = "button"; b.dataset.id = p.id;
    b.append(el("b", null, p.name), el("small", null, `${LINES[p.brand].name} line · ${p.phone_masked}`), el("span", null, p.blurb),
             el("span", "pb-out " + (/Resolved|Answered/.test(p.outcome) ? "ok" : /Safety/.test(p.outcome) ? "safety" : ""), p.outcome));
    b.addEventListener("click", () => select(p.id));
    box.appendChild(b);
  });
  $("pb-send").addEventListener("click", step);
  $("pb-restart").addEventListener("click", () => select(cur.id));
  select(rec.personas[0].id);
}

function select(id) {
  run++;
  cur = rec.personas.find((p) => p.id === id); idx = 0; busy = false; thread = [];
  document.querySelectorAll(".pb-person").forEach((b) => b.classList.toggle("on", b.dataset.id === id));
  const L = LINES[cur.brand];
  $("pb-avatar").textContent = L.initials; $("pb-avatar").style.background = L.bg;
  $("pb-linename").textContent = `${L.name} Support`; $("pb-linesub").textContent = `Business account · ${L.number}`;
  $("pb-trace").textContent = ""; $("pb-trace").appendChild(el("li", "d-trace-empty", "Press Send and each step Aftercare takes appears here."));
  $("pb-inbox").textContent = ""; $("pb-inbox").hidden = true;
  cur.registration.forEach((m) => thread.push(m));
  render(); ready();
}

function ready() {
  const nextStep = cur.steps[idx];
  const input = $("pb-input"), send = $("pb-send");
  const cue = !!nextStep && !busy;                     // the glow and rings say "press Send" whenever a next message is waiting
  send.classList.toggle("glow", cue); input.classList.toggle("glow", cue);
  $("pb-over").hidden = !!nextStep || thread.length === 0 || idx === 0;
  if (!nextStep) { input.value = ""; input.placeholder = "Example run over"; send.disabled = true; input.disabled = true; return; }
  input.disabled = false; send.disabled = busy;
  if (nextStep.who === "customer") { input.value = nextStep.text; send.textContent = "Send"; input.placeholder = "Message"; }
  else { input.value = ""; input.placeholder = nextStep.who === "staff" ? `${nextStep.actor}: replies from the brand's inbox` : `${nextStep.actor}: ${nextStep.action}`; send.textContent = nextStep.who === "staff" ? "Play reply" : "Play action"; }
}

function bubble(m, last) {
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
  thread.forEach((m, i) => box.appendChild(bubble(m, i === thread.length - 1)));
  if (typing) box.appendChild(el("div", "sb-msg typing", "•••"));
  box.scrollTop = box.scrollHeight;
}

async function step() {
  const s = cur.steps[idx]; if (!s || busy) return;
  const my = run; busy = true; $("pb-send").disabled = true; $("pb-send").classList.remove("glow"); $("pb-input").classList.remove("glow"); $("pb-over").hidden = true;
  if (s.who === "customer") {
    if (s.button) { const b = [...thread].reverse().find((m) => m.kind === "buttons"); if (b) b.chosen = s.text; }
    thread.push({ sender: "customer", kind: "text", text: s.text }); render(true);
    await wait(REDUCED ? 0 : 1100); if (my !== run) return;
    for (const m of s.replies) { thread.push(m); render(); await wait(REDUCED ? 0 : 450); if (my !== run) return; }
    traceFor(s.replies);
  } else if (s.who === "staff") {
    inboxLine(s.actor, `replies from the inbox: “${s.text}”`, s.result.startsWith("Allowed") ? "yes" : "no", s.result);
    thread.push({ sender: "human", kind: "text", text: s.text, meta: { staff: s.actor.split(" (")[0] } }); render();
  } else {
    inboxLine(s.actor, `tries: ${s.action}`, s.ok ? "yes" : "no", s.ok ? `Allowed. ${s.result}` : `Refused. ${s.result}`);
    for (const m of s.replies) { thread.push(m); render(); await wait(300); }
  }
  idx++; busy = false; ready();
  if ($("pb-auto").checked && cur.steps[idx]) { await wait(1300); if (my === run) step(); }
}

function inboxLine(who, what, cls, note) {
  const box = $("pb-inbox"); box.hidden = false;
  if (!box.children.length) box.appendChild(el("h4", null, "Brand inbox"));
  const r = el("div", "row"); r.append(strong(who), " " + what);
  box.append(r, el("div", "row " + cls, note));
}

/* the trace: built only from the fields the real API returned */
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
      const box = $("pb-inbox"); box.hidden = false; box.textContent = ""; box.appendChild(el("h4", null, "Brand inbox"));
      const r = el("div", "row"); r.append(strong(`${meta.ticket_id} · ${esc.label}`), ` · ${cur.name}: the chat and everything tried is attached.`); box.appendChild(r);
    }
  });
}
