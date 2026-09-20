/* landing.js — the one-page story (/)
   nav · reveal · scroll-lit statement · hero phone ·
   customer story (pinned phone, alignment-driven). */
"use strict";

const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

/* rAF-throttled scroll hook: one place, one frame */
const scrollFns = [];
let scrollQueued = false;
function onScroll(fn) { scrollFns.push(fn); }
function runScroll() {
  scrollQueued = false;
  scrollFns.forEach((fn) => fn());
}
function queueScroll() {
  if (scrollQueued) return;
  scrollQueued = true;
  requestAnimationFrame(runScroll);
}
window.addEventListener("scroll", queueScroll, { passive: true });
window.addEventListener("resize", queueScroll, { passive: true });

/* ── Nav: hairline once scrolled ── */
const nav = document.getElementById("l-nav");
const lightBands = Array.from(document.querySelectorAll(".l-band-light, .l-band-white, .l-footer"));
onScroll(() => {
  if (!nav) return;
  nav.classList.toggle("scrolled", window.scrollY > 10);
  const y = nav.offsetHeight / 2;
  nav.classList.toggle("on-light", lightBands.some((b) => {
    const r = b.getBoundingClientRect();
    return r.top <= y && r.bottom >= y;
  }));
});

/* ── Reveal on scroll (Step 0 rows animate off the same `.in` class) ── */
const revealObs = new IntersectionObserver((entries) => {
  entries.forEach((e) => {
    if (!e.isIntersecting) return;
    e.target.classList.add("in");
    revealObs.unobserve(e.target);
  });
}, { threshold: 0.18, rootMargin: "0px 0px -6% 0px" });
document.querySelectorAll(".l-reveal").forEach((el) => revealObs.observe(el));

/* ── Scroll-lit statement: words brighten as you read down the page ── */
(function () {
  const el = document.getElementById("l-lit");
  if (!el) return;
  const words = el.textContent.trim().split(/\s+/);
  el.textContent = "";
  const spans = words.map((w, i) => {
    const s = document.createElement("span");
    s.className = "l-word";
    s.textContent = w;
    el.appendChild(s);
    if (i < words.length - 1) el.appendChild(document.createTextNode(" "));
    return s;
  });
  if (reduceMotion) { spans.forEach((s) => s.classList.add("on")); return; }
  onScroll(() => {
    const r = el.getBoundingClientRect();
    const vh = window.innerHeight;
    const p = clamp((vh * 0.86 - r.top) / (vh * 0.86 - vh * 0.28), 0, 1);
    const lit = Math.round(p * spans.length);
    spans.forEach((s, i) => s.classList.toggle("on", i < lit));
  });
})();

/* ── Bubble helpers (hero phone + story phone) ── */
const BUBBLE_CLASS = {
  agent: "fb agent", cust: "fb cust", sys: "fb sys", source: "fb source",
  ok: "fb ok", warn: "fb warn", pbtn: "fb prod-btn", pbtnsel: "fb prod-btn selected",
  ticket: "fb ticket-box",
};
function buildBubble(m) {
  const el = document.createElement("div");
  el.className = BUBBLE_CLASS[m.type] || "fb";
  if (m.html) el.innerHTML = m.html;   // authored strings in this file only — never user input
  else el.textContent = m.text;
  return el;
}
function playMessages(container, msgs, timers, stepMs) {
  msgs.forEach((m, i) => {
    timers.push(setTimeout(() => {
      const el = buildBubble(m);
      container.appendChild(el);
      requestAnimationFrame(() => requestAnimationFrame(() => el.classList.add("show")));
      container.scrollTop = container.scrollHeight;
    }, reduceMotion ? 0 : stepMs * (i + 1)));
  });
}

/* ── Hero phone: one exchange, taken from the real AquaSpin manual (§4.1) ── */
(function () {
  const box = document.getElementById("hero-messages");
  if (!box) return;
  playMessages(box, [
    { type: "cust",   text: "My washing machine bangs on every spin" },
    { type: "agent",  text: "Rock it gently from each corner. If it moves, turn the feet until all four sit flat — then run it again." },
    { type: "source", text: "📄 AquaSpin manual · 4.1 Drum wobbling or banging noise" },
    { type: "cust",   text: "That fixed it — thank you!" },
    { type: "ok",     text: "✓ Resolved · no ticket" },
  ], [], 900);
})();

/* ══════════════════════════════════════════════════════════════
   CUSTOMER STORY
   Bubbles use the fixtures' own people, products and manual sections
   (Priya Sharma, AquaSpin FC-700 WM-FC-78234, manual §4.1, §4.4). The
   live demo runs the same scenarios against the real agent.
══════════════════════════════════════════════════════════════ */
const AV = "linear-gradient(135deg,#1f7a5c,#30B0C7)";
const STEPS = [
  {
    avatarBg: AV, glow: "rgba(48,176,199,0.32)", label: "Registration",
    msgs: [
      { type: "sys",   text: "AquaSpin FC-700 · point-of-sale registration" },
      { type: "agent", html: `Hi Priya! Your <strong>AquaSpin FC-700</strong> is registered.<br><br>Serial: WM-FC-78234<br>Bought: 5 Jun 2025 · Amazon.in<br>Motor warranty: 2 years, active<br><br>Save this chat — no receipt to hunt for.` },
      { type: "sys",   text: "A QR sticker goes on the product at the counter" },
    ],
  },
  {
    avatarBg: AV, glow: "rgba(0,122,255,0.28)", label: "Lookup",
    msgs: [
      { type: "cust",  text: "My washing machine bangs when it spins" },
      { type: "sys",   text: "+91 98765 ····· → 1 AquaSpin product on file" },
      { type: "agent", text: "Hi Priya! Which product is this about?" },
      { type: "pbtn",  text: "AquaSpin FC-700 Washing Machine · Warranty active" },
      { type: "pbtn",  text: "AquaSpin FL-900 Front Loader · Warranty active" },
      { type: "pbtnsel", text: "AquaSpin FC-700 Washing Machine · Warranty active" },
    ],
  },
  {
    avatarBg: "linear-gradient(135deg,#1f7a5c,#FF9F0A)", glow: "rgba(255,159,10,0.26)", label: "Manual",
    msgs: [
      { type: "cust",   text: "My washing machine bangs loudly when it spins" },
      { type: "agent",  text: "Rock the machine gently from each corner. If it rocks, adjust the feet until it doesn't — then run a spin again." },
      { type: "source", text: "📄 AquaSpin manual · 4.1 Drum wobbling or banging noise" },
    ],
  },
  {
    avatarBg: "linear-gradient(135deg,#1f7a5c,#5E5CE6)", glow: "rgba(94,92,230,0.26)", label: "Back & forth",
    msgs: [
      { type: "cust",  text: "Levelled it. It still bangs" },
      { type: "agent", text: "Next check from the manual: pause it, open the door and spread the clothes around the drum so they aren't bunched on one side." },
      { type: "source", text: "📄 AquaSpin manual · 4.1 Drum wobbling or banging noise" },
      { type: "cust",  text: "Spread them out — quiet now, thank you!" },
      { type: "ok",    text: "✓ Resolved · no ticket" },
    ],
  },
  {
    avatarBg: "linear-gradient(135deg,#0E6B7D,#30B0C7)", glow: "rgba(48,176,199,0.3)", label: "Human handoff",
    msgs: [
      { type: "cust",  text: "The touch panel flickers and won't respond" },
      { type: "warn",  text: "Not in the manual — the agent won't guess" },
      { type: "agent", text: "I couldn't find this in your product manual, and I won't guess at it. I've handed it to our service team with your description as written." },
      { type: "ticket", html: `<span class="tk-title">Handed to a person · Not in the manual</span><span class="tk-row">Priya Sharma · AquaSpin FC-700 (WM-FC-78234)</span><span class="tk-row">Issue: touch panel flickers and won't respond</span><span class="tk-row">Tried: nothing — no manual step applies</span>` },
      { type: "sys",   text: "Also hands over: two steps tried and still broken · same problem back within 90 days" },
    ],
  },
  {
    avatarBg: "linear-gradient(135deg,#FF375F,#FF9F0A)", glow: "rgba(255,55,95,0.3)", label: "Safety",
    msgs: [
      { type: "cust", text: "There's a burning smell coming from my machine" },
      { type: "warn", text: "⚠ Safety keyword — skipping troubleshooting" },
      { type: "agent", text: "Stop use immediately. Switch off power at the socket, not just the machine's own power button. Do not attempt any troubleshooting yourself." },
      { type: "ticket", html: `<span class="tk-title">Emergency visit · Safety</span><span class="tk-row">Priya Sharma · AquaSpin FC-700 (WM-FC-78234)</span><span class="tk-row">Issue: burning smell</span><span class="tk-row">Free of charge, whatever the warranty status</span>` },
    ],
  },
];

const storyMessages = document.getElementById("story-messages");
const storyAvatar   = document.getElementById("story-avatar");
const storyGlow     = document.getElementById("story-glow");
const progressBars  = Array.from(document.querySelectorAll("#story-progress i"));
const progressLabel = document.getElementById("story-progress-label");
const storySteps    = Array.from(document.querySelectorAll(".l-story-step"));
const storyCards    = storySteps.map((s) => s.querySelector(".l-sstep-inner"));

let currentStep = -1;
let storyTimers = [];

function showStep(idx) {
  if (idx === currentStep) return;
  currentStep = idx;
  const d = STEPS[idx];
  if (!d) return;

  if (storyAvatar) storyAvatar.style.background = d.avatarBg;
  if (storyGlow) storyGlow.style.background = `radial-gradient(circle, ${d.glow} 0%, transparent 70%)`;
  progressBars.forEach((b, i) => b.classList.toggle("on", i === idx));
  if (progressLabel) progressLabel.textContent = `Step ${idx + 1} of ${STEPS.length} · ${d.label}`;

  storyTimers.forEach(clearTimeout);
  storyTimers = [];
  if (!storyMessages) return;
  storyMessages.innerHTML = "";
  playMessages(storyMessages, d.msgs, storyTimers, 420);
}

/* The sliding window. Each step is one viewport tall with its card centred; the
   phone is pinned centred too. So "aligned" == the card's centre is on the
   viewport's centre line. Closeness to that line drives the card's --p (fade +
   scale), and the phone's animation only kicks in once the two coincide. */
function tickStory() {
  if (!storySteps.length) return;
  const vh = window.innerHeight;
  const mid = vh / 2;
  let best = -1;
  let bestDist = Infinity;
  storySteps.forEach((step, i) => {
    const r = step.getBoundingClientRect();
    const dist = Math.abs(r.top + r.height / 2 - mid);
    const p = 1 - clamp(dist / (vh * 0.5), 0, 1);
    storyCards[i].style.setProperty("--p", (p * p).toFixed(3));
    if (dist < bestDist) { bestDist = dist; best = i; }
  });
  // wide: play only when card and phone are aligned; narrow (stacked): the nearest card always wins
  if (bestDist < vh * 0.14 || window.innerWidth <= 700) showStep(best);
}
onScroll(tickStory);
tickStory();


/* ── Step 0: check a sales file for real (POST /api/ingest) ── */
(function () {
  const out = document.getElementById("l-check-out");
  if (!out) return;
  const HEADER = "customer_name,customer_phone,product_id,product_name,serial_number,purchase_date,retailer,purchase_price\n";
  const MESSY = HEADER + [
    "Asha Rao,+919800000001,WM-FC-700,AquaSpin FC-700 Washing Machine,WM-FC-80001,2026-02-11,Reliance Digital,25999",
    "Karan Shah,+919800000002,AC-CB-15T,ArcticAir 1.5T Split AC,AC-CB-80002,2026-03-02,Reliance Digital,33999",
    "Meena Iyer,+919800000003,TV-55-X,Mystery 55in TV,TV-80003,2026-03-09,Reliance Digital,45999",
    "Rohit Jain,+919800000004,AC-CB-15T,ArcticAir 1.5T Split AC,AC-CB-80002,2026-03-10,Reliance Digital,33999",
    "Sana Ali,98000,WM-FL-900,AquaSpin FL-900 Front Loader,WM-FL-80005,12/03/2026,Reliance Digital,35999",
  ].join("\n");

  function show(data, ok) {
    out.textContent = "";
    const line = (html) => { const p = document.createElement("p"); p.innerHTML = html; out.appendChild(p); };
    if (!ok) { line("<b>Can't read this file.</b> "); out.lastChild.append(data.error || "Unknown error"); return; }
    line(`<b>${data.rows} rows read.</b> ${data.accepted} filed by brand, ${data.rejected} need attention.`);
    if (data.brands.length) {
      const chips = document.createElement("div"); chips.className = "l-check-chips";
      data.brands.forEach((b) => { const s = document.createElement("span"); s.textContent = `${b.brand}: ${b.products} product${b.products === 1 ? "" : "s"}, ${b.customers} customer${b.customers === 1 ? "" : "s"}`; chips.appendChild(s); });
      out.appendChild(chips);
    }
    if (data.issues.length) {
      const ul = document.createElement("ul");
      data.issues.forEach((i) => { const li = document.createElement("li"); li.textContent = `Line ${i.line}: ${i.problem}`; ul.appendChild(li); });
      out.appendChild(ul);
    }
  }
  async function check(text) {
    out.textContent = "Checking…";
    try {
      const r = await fetch("/api/ingest", { method: "POST", headers: { "Content-Type": "text/csv" }, body: text });
      show(await r.json(), r.ok);
    } catch (_) { out.textContent = "Couldn't reach the server."; }
  }
  document.querySelectorAll(".l-check-btn[data-sample]").forEach((b) => b.addEventListener("click", async () => {
    if (b.dataset.sample === "messy") return check(MESSY);
    const rows = Array.from(document.querySelectorAll(".l-csv-table tbody tr")).length;
    // the file shown above is the fixture itself; ask the server to check exactly that file
    const r = await fetch("/api/sample-csv"); check(await r.text());
  }));
  const file = document.getElementById("l-check-file");
  file && file.addEventListener("change", () => { const f = file.files[0]; if (f) f.text().then(check); });
})();

/* ── Under the hood: chips from a live health probe ── */
(async function () {
  const chips = document.querySelectorAll("[data-chip]");
  if (!chips.length) return;
  const set = (name, ok, text) => document.querySelectorAll(`[data-chip="${name}"]`).forEach((c) => { c.textContent = text; c.classList.toggle("up", ok); c.classList.toggle("down", !ok); });
  try {
    const h = await (await fetch("/api/health")).json();
    const c = h.components;
    set("runtime", h.runtime === "lambda", h.runtime === "lambda" ? "● this page was served by a Lambda" : "○ not running in Lambda");
    set("ollama", c.ollama.ok, c.ollama.ok ? `● live · ${c.ollama.ms} ms · ${c.ollama.models.includes("qwen2.5-coder:7b") ? "qwen2.5-coder:7b" : c.ollama.models[0]}` : "○ offline: start ollama");
    set("opensearch", c.opensearch.ok, c.opensearch.ok ? `● live · v${c.opensearch.version} · ${c.opensearch.documents} sections indexed` : "○ OpenSearch unreachable");
    set("cedar", c.cedar.ok, c.cedar.ok ? `● live · policies validated · ${c.cedar.policy_sha}` : "○ Cedar CLI missing");
    set("storage", c.dynamodb.ok, c.dynamodb.ok ? `● live · DynamoDB Local · table ${c.dynamodb.table}` : "○ DynamoDB unreachable");
  } catch (_) { chips.forEach((c) => { c.textContent = "○ status unavailable"; c.classList.add("down"); }); }
})();
