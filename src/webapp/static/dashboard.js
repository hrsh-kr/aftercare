const brand = window.__BRAND__;
const staffBrand = sessionStorage.getItem("staffBrand") || "";

// Ticket fields include raw customer-typed complaint text (issue_summary,
// attempts_tried) -- rendered via innerHTML below for the bar-chart/badge
// markup, so it must be escaped. Otherwise a complaint like
// "<img src=x onerror=...>" would execute in the dashboard viewer's browser.
function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = String(value);
  return div.innerHTML;
}

const sessionLine = document.getElementById("session-line");
const deniedPanel = document.getElementById("denied-panel");
const deniedCopy = document.getElementById("denied-copy");
const dashContent = document.getElementById("dash-content");

async function loadDashboard() {
  if (!staffBrand) {
    window.location.href = "/dashboard";
    return;
  }

  const res = await fetch(`/api/dashboard/${brand}`, {
    headers: { "X-Staff-Brand": staffBrand },
  });
  const data = await res.json();

  if (res.status === 403) {
    sessionLine.textContent = `Denied`;
    deniedCopy.textContent = data.error;
    deniedPanel.hidden = false;
    return;
  }
  if (!res.ok) {
    sessionLine.textContent = "Error";
    deniedCopy.textContent = data.error || "Something went wrong loading this dashboard.";
    deniedPanel.hidden = false;
    return;
  }

  sessionLine.textContent = `Logged in as ${staffBrand} staff · authorized by Cedar`;
  dashContent.hidden = false;

  const statRow = document.getElementById("stat-row");
  statRow.innerHTML = `
    <div class="stat-card"><div class="stat-value">${data.registered_count}</div><div class="stat-label">Registered products</div></div>
    <div class="stat-card"><div class="stat-value">${data.tickets.length}</div><div class="stat-label">Open tickets</div></div>
    <div class="stat-card"><div class="stat-value">${data.warranty_counts.active}</div><div class="stat-label">Warranty items active</div></div>
  `;

  const ticketList = document.getElementById("ticket-list");
  if (data.tickets.length === 0) {
    ticketList.innerHTML = `<p class="empty-state">No escalated tickets yet.</p>`;
  } else {
    ticketList.innerHTML = data.tickets
      .map(
        (t) => `
      <div class="ticket-card ${t.safety_flag ? "safety" : ""}">
        <div class="ticket-top">
          <span class="ticket-id">${escapeHtml(t.ticket_id)}</span>
          ${t.safety_flag ? '<span class="ticket-safety-badge">SAFETY</span>' : ""}
        </div>
        <div class="ticket-meta">${escapeHtml(t.customer_name)} · ${escapeHtml(t.product_name)}</div>
        <div class="ticket-issue">${escapeHtml(t.issue_summary)}</div>
        ${
          t.attempts_tried.length
            ? `<div class="ticket-attempts">Already tried:<ol>${t.attempts_tried.map((a) => `<li>${escapeHtml(a)}</li>`).join("")}</ol></div>`
            : `<div class="ticket-attempts">Escalated immediately, no self-service attempted.</div>`
        }
      </div>`
      )
      .join("");
  }

  const feedbackList = document.getElementById("feedback-list");
  if (data.product_feedback.length === 0) {
    feedbackList.innerHTML = `<p class="empty-state">No recurring issues yet.</p>`;
  } else {
    const max = Math.max(...data.product_feedback.map((f) => f.count));
    feedbackList.innerHTML = data.product_feedback
      .map(
        (f) => `
      <div class="feedback-row">
        <span class="feedback-name">${escapeHtml(f.product_name)}</span>
        <span class="feedback-bar-track"><span class="feedback-bar" style="width:${(f.count / max) * 100}%"></span></span>
        <span class="feedback-count">${f.count} ticket${f.count === 1 ? "" : "s"}</span>
      </div>`
      )
      .join("");
  }
}

loadDashboard();
