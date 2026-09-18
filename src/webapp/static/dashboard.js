async function loadDashboard() {
  const res = await fetch("/api/dashboard");
  const data = await res.json();

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
          <span class="ticket-id">${t.ticket_id}</span>
          ${t.safety_flag ? '<span class="ticket-safety-badge">SAFETY</span>' : ""}
        </div>
        <div class="ticket-meta">${t.customer_name} · ${t.product_name}</div>
        <div class="ticket-issue">${t.issue_summary}</div>
        ${
          t.attempts_tried.length
            ? `<div class="ticket-attempts">Already tried:<ol>${t.attempts_tried.map((a) => `<li>${a}</li>`).join("")}</ol></div>`
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
    feedbackList.innerHTML = data.product_feedback
      .map((f) => `<div class="feedback-row"><span>${f.product_name}</span><span class="feedback-count">${f.count} ticket${f.count === 1 ? "" : "s"}</span></div>`)
      .join("");
  }
}

loadDashboard();
