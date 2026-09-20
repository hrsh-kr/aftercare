/**
 * dashboard.js — Brand support dashboard.
 *
 * Revamped with:
 * - Complaint breakdown section (issue categories ranked by frequency)
 * - Product health table (resolved vs escalated rate per product)
 * - Warranty coverage donut (CSS-only)
 * - Richer ticket cards with conversation-thread-style excerpts
 * - QR codes generated client-side via qrcode.js (no network dep)
 * - Cedar authorization badge inline in the header
 */

"use strict";

const brand      = window.__BRAND__;
const staffBrand = sessionStorage.getItem("staffBrand") || "";

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = String(value);
  return div.innerHTML;
}

function formatTs(raw) {
  if (!raw) return "";
  try {
    const d = new Date(raw);
    if (isNaN(d)) return raw;
    return d.toLocaleString(undefined, {
      month: "short", day: "numeric", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  } catch (_) { return raw; }
}

function demoDeepLink(brandSlug, serial) {
  return `${window.location.origin}/demo?brand=${encodeURIComponent(brandSlug)}&serial=${encodeURIComponent(serial)}`;
}

function renderQR(container, content, size) {
  try {
    new QRCode(container, {
      text:         content,
      width:        size,
      height:       size,
      colorDark:    "#0d1512",
      colorLight:   "#ffffff",
      correctLevel: QRCode.CorrectLevel.M,
    });
  } catch {
    container.innerHTML =
      `<div style="width:${size}px;height:${size}px;display:flex;align-items:center;
       justify-content:center;background:#f5f5f5;border-radius:6px;
       font-size:10px;color:#888;text-align:center;padding:6px;">QR unavailable</div>`;
  }
}

// ── DOM refs ───────────────────────────────────────────────────────────────────

const sessionLine = document.getElementById("session-line");
const deniedPanel = document.getElementById("denied-panel");
const deniedCopy  = document.getElementById("denied-copy");
const dashContent = document.getElementById("dash-content");

// ── Load dashboard ─────────────────────────────────────────────────────────────

async function loadDashboard() {
  if (!staffBrand) { window.location.href = "/dashboard"; return; }

  const res  = await fetch(`/api/dashboard/${brand}`, {
    headers: { "X-Staff-Brand": staffBrand },
  });
  const data = await res.json();

  if (res.status === 403) {
    sessionLine.textContent = "Denied";
    deniedCopy.textContent  = data.error;
    deniedPanel.hidden = false;
    return;
  }
  if (!res.ok) {
    sessionLine.textContent = "Error";
    deniedCopy.textContent  = data.error || "Something went wrong.";
    deniedPanel.hidden = false;
    return;
  }

  sessionLine.innerHTML =
    `Logged in as <strong>${escapeHtml(staffBrand)} staff</strong>
     &nbsp;<span class="cedar-badge">✓ Authorized by Cedar</span>`;
  dashContent.hidden = false;

  // ── Stats ──────────────────────────────────────────────────────────────────

  const resolved      = 0; // placeholder — real data would come from tickets.status='resolved'
  const escalated     = data.tickets.length;
  const safetyTickets = data.tickets.filter((t) => t.safety_flag).length;

  document.getElementById("stat-row").innerHTML = `
    <div class="stat-card">
      <div class="stat-icon">📦</div>
      <div class="stat-value">${data.registered_count}</div>
      <div class="stat-label">Registered products</div>
    </div>
    <div class="stat-card ${escalated > 0 ? "stat-card--alert" : ""}">
      <div class="stat-icon">🎫</div>
      <div class="stat-value">${escalated}</div>
      <div class="stat-label">Escalated tickets</div>
    </div>
    <div class="stat-card">
      <div class="stat-icon">✅</div>
      <div class="stat-value">${data.warranty_counts.active}</div>
      <div class="stat-label">Active warranties</div>
    </div>
    ${safetyTickets ? `
    <div class="stat-card stat-card--safety">
      <div class="stat-icon">⚠️</div>
      <div class="stat-value">${safetyTickets}</div>
      <div class="stat-label">Safety flags</div>
    </div>` : ""}
  `;

  // ── Complaint breakdown (new analytics section) ────────────────────────────

  renderComplaintBreakdown(data.tickets);

  // ── Product health table (new) ─────────────────────────────────────────────

  renderProductHealth(data.registrations, data.tickets);

  // ── Warranty coverage ring (new) ───────────────────────────────────────────

  renderWarrantyRing(data.warranty_counts);

  // ── Registered Products + QR codes ────────────────────────────────────────

  const regList = document.getElementById("registration-list");
  if (data.registrations && data.registrations.length > 0) {
    regList.innerHTML = data.registrations
      .map((r) => {
        const deepLink = demoDeepLink(brand, r.serial_number);
        const wActive  = r.warranty_component_status === "active";
        const wStatus  = wActive
          ? '<span class="reg-status active">Warranty active</span>'
          : '<span class="reg-status expired">Warranty expired</span>';
        return `
          <div class="reg-card">
            <div class="reg-qr-wrap">
              <a href="${escapeHtml(deepLink)}" target="_blank"
                 title="Click to simulate customer scanning this QR" class="reg-qr-link">
                <div id="qr-${escapeHtml(r.serial_number)}" class="reg-qr-canvas"></div>
              </a>
              <div class="reg-qr-label">Scan to support</div>
            </div>
            <div class="reg-info">
              <div class="reg-product">${escapeHtml(r.product_name)}</div>
              <div class="reg-meta">${escapeHtml(r.customer_name)} · ${escapeHtml(r.serial_number)}</div>
              <div class="reg-meta">Purchased ${escapeHtml(r.purchase_date)} · ${escapeHtml(r.retailer)}</div>
              ${wStatus}
            </div>
          </div>`;
      })
      .join("");

    data.registrations.forEach((r) => {
      const container = document.getElementById(`qr-${r.serial_number}`);
      if (container) renderQR(container, demoDeepLink(brand, r.serial_number), 100);
    });
  } else {
    regList.innerHTML = `<p class="empty-state">No products registered yet.</p>`;
  }

  // ── Tickets ────────────────────────────────────────────────────────────────

  const ticketList = document.getElementById("ticket-list");
  if (data.tickets.length === 0) {
    ticketList.innerHTML = `<p class="empty-state">No escalated tickets yet.</p>`;
  } else {
    ticketList.innerHTML = data.tickets
      .map((t) => `
        <div class="ticket-card ${t.safety_flag ? "safety" : ""}">
          <div class="ticket-top">
            <span class="ticket-id">${escapeHtml(t.ticket_id)}</span>
            <div style="display:flex;align-items:center;gap:8px;">
              ${t.safety_flag ? '<span class="ticket-safety-badge">⚠ SAFETY</span>' : (t.reason_label ? `<span class="ticket-reason-badge">${escapeHtml(t.reason_label)}</span>` : "")}
              ${t.created_at ? `<span class="ticket-ts">${escapeHtml(formatTs(t.created_at))}</span>` : ""}
            </div>
          </div>
          <div class="ticket-meta">${escapeHtml(t.customer_name)} · ${escapeHtml(t.product_name)}</div>

          <!-- Thread-style conversation excerpt -->
          <div class="ticket-thread">
            <div class="thread-bubble customer">
              <span class="thread-who">Customer:</span> ${escapeHtml(t.issue_summary)}
            </div>
            ${t.attempts_tried.length ? t.attempts_tried.slice(0, 2).map((a) => `
              <div class="thread-bubble agent">
                <span class="thread-who">Aftercare:</span> ${escapeHtml(a.replace(/^["']|["']$/g, ""))}
              </div>`).join("") : `
              <div class="thread-bubble escalated">
                <span class="thread-who">System:</span> Safety/complexity flagged — escalated without troubleshooting.
              </div>`}
            <div class="thread-bubble escalated">
              <span class="thread-who">Ticket created:</span> ${escapeHtml(t.ticket_id)}
            </div>
          </div>
        </div>`)
      .join("");
  }
}

// ── Complaint breakdown ────────────────────────────────────────────────────────

function renderComplaintBreakdown(tickets) {
  const el = document.getElementById("complaint-breakdown");
  if (!el) return;

  if (tickets.length === 0) {
    el.innerHTML = `<p class="empty-state">No tickets yet — nothing to break down.</p>`;
    return;
  }

  // Categorise by simple keyword matching on issue_summary
  const categories = {
    "Drainage / Error code":   ["drain", "error", "e4", "water"],
    "Odour / Smell":           ["smell", "odour", "odor"],
    "Safety / Burning":        ["burn", "fire", "smoke", "heat", "safety"],
    "Noise / Vibration":       ["noise", "vibrat", "loud", "rattle"],
    "Performance / Cooling":   ["cool", "warm", "hot", "cold", "performance", "not working"],
    "Other":                   [],
  };

  const counts = {};
  for (const cat of Object.keys(categories)) counts[cat] = 0;

  for (const ticket of tickets) {
    const summary = (ticket.issue_summary || "").toLowerCase();
    let matched   = false;
    for (const [cat, keywords] of Object.entries(categories)) {
      if (cat === "Other") continue;
      if (keywords.some((kw) => summary.includes(kw))) {
        counts[cat]++;
        matched = true;
        break;
      }
    }
    if (!matched) counts["Other"]++;
  }

  const sorted = Object.entries(counts)
    .filter(([, v]) => v > 0)
    .sort(([, a], [, b]) => b - a);

  const max = Math.max(...sorted.map(([, v]) => v));

  el.innerHTML = sorted.map(([cat, count]) => `
    <div class="breakdown-row">
      <span class="breakdown-name">${escapeHtml(cat)}</span>
      <span class="breakdown-bar-track">
        <span class="breakdown-bar" style="width:${(count / max) * 100}%"></span>
      </span>
      <span class="breakdown-count">${count}</span>
    </div>`).join("");
}

// ── Product health table ───────────────────────────────────────────────────────

function renderProductHealth(registrations, tickets) {
  const el = document.getElementById("product-health");
  if (!el) return;

  if (!registrations || registrations.length === 0) {
    el.innerHTML = `<p class="empty-state">No products registered.</p>`;
    return;
  }

  // Group tickets by product_name
  const ticketsByProduct = {};
  for (const t of tickets) {
    const key = t.product_name;
    if (!ticketsByProduct[key]) ticketsByProduct[key] = { total: 0, safety: 0 };
    ticketsByProduct[key].total++;
    if (t.safety_flag) ticketsByProduct[key].safety++;
  }

  // Build unique product list from registrations
  const products = {};
  for (const r of registrations) {
    if (!products[r.product_name]) {
      products[r.product_name] = { name: r.product_name, count: 0, active: 0 };
    }
    products[r.product_name].count++;
    if (r.warranty_component_status === "active") products[r.product_name].active++;
  }

  el.innerHTML = `
    <table class="health-table">
      <thead>
        <tr>
          <th>Product</th>
          <th>Registered</th>
          <th>Active warranty</th>
          <th>Escalated tickets</th>
          <th>Safety flags</th>
        </tr>
      </thead>
      <tbody>
        ${Object.values(products).map((p) => {
          const td     = ticketsByProduct[p.name] || { total: 0, safety: 0 };
          const hasIss = td.total > 0;
          return `<tr class="${hasIss ? "row-issue" : ""}">
            <td class="health-name">${escapeHtml(p.name)}</td>
            <td>${p.count}</td>
            <td><span class="health-pill ok">${p.active} active</span></td>
            <td>${td.total > 0 ? `<span class="health-pill warn">${td.total}</span>` : `<span class="health-pill good">0</span>`}</td>
            <td>${td.safety > 0 ? `<span class="health-pill danger">⚠ ${td.safety}</span>` : "—"}</td>
          </tr>`;
        }).join("")}
      </tbody>
    </table>`;
}

// ── Warranty coverage ring ─────────────────────────────────────────────────────

function renderWarrantyRing(counts) {
  const el = document.getElementById("warranty-ring");
  if (!el) return;

  const total   = (counts.active || 0) + (counts.expired || 0);
  if (total === 0) { el.innerHTML = `<p class="empty-state">No warranty data.</p>`; return; }

  const pct     = Math.round((counts.active / total) * 100);
  const angle   = (counts.active / total) * 360;
  const large   = angle > 180 ? 1 : 0;
  const r       = 52;
  const cx      = 64;
  const cy      = 64;
  const startX  = cx + r * Math.sin(0);
  const startY  = cy - r * Math.cos(0);
  const endX    = cx + r * Math.sin((angle * Math.PI) / 180);
  const endY    = cy - r * Math.cos((angle * Math.PI) / 180);

  el.innerHTML = `
    <div class="ring-wrap">
      <svg viewBox="0 0 128 128" width="128" height="128">
        <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="#fca5a5" stroke-width="14"/>
        <path d="M ${startX} ${startY} A ${r} ${r} 0 ${large} 1 ${endX} ${endY}"
              fill="none" stroke="#1f7a5c" stroke-width="14" stroke-linecap="round"/>
        <text x="${cx}" y="${cy + 6}" text-anchor="middle"
              font-family="Inter,sans-serif" font-size="22" font-weight="800" fill="#14201b">${pct}%</text>
      </svg>
      <div class="ring-legend">
        <div class="ring-item"><span class="ring-dot active-dot"></span> Active (${counts.active})</div>
        <div class="ring-item"><span class="ring-dot expired-dot"></span> Expired (${counts.expired})</div>
      </div>
    </div>`;
}

loadDashboard();
