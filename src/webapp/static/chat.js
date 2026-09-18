const lookupScreen = document.getElementById("lookup-screen");
const customerList = document.getElementById("customer-list");
const lookupError = document.getElementById("lookup-error");
const chatBody = document.getElementById("chat-body");
const messagesEl = document.getElementById("messages");
const composer = document.getElementById("composer");
const messageInput = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
const brandDot = document.getElementById("brand-dot");
const brandName = document.getElementById("brand-name");

let phone = null;
let conversationId = null;
let awaitingFirstComplaint = false;

async function loadCustomerPicker() {
  const res = await fetch("/api/customers");
  const people = await res.json();
  customerList.innerHTML = people
    .map(
      (p) => `
      <button class="customer-btn" data-phone="${p.phone}">
        <span class="customer-avatar">${p.name[0]}</span>
        <span>${p.name}</span>
      </button>`
    )
    .join("");
  customerList.querySelectorAll(".customer-btn").forEach((btn) => {
    btn.addEventListener("click", () => selectCustomer(btn.dataset.phone));
  });
}
loadCustomerPicker();

function addBubble(text, cls) {
  const el = document.createElement("div");
  el.className = `bubble ${cls}`;
  el.textContent = text;
  messagesEl.appendChild(el);
  chatBody.scrollTop = chatBody.scrollHeight;
}

function setComposerEnabled(enabled) {
  messageInput.disabled = !enabled;
  sendBtn.disabled = !enabled;
}

async function selectCustomer(selectedPhone) {
  lookupError.hidden = true;

  const res = await fetch("/api/lookup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ phone: selectedPhone }),
  });
  const data = await res.json();

  if (!data.found) {
    lookupError.textContent = "We don't have a registration for this number.";
    lookupError.hidden = false;
    return;
  }

  phone = selectedPhone;
  lookupScreen.hidden = true;
  messagesEl.hidden = false;
  composer.hidden = false;

  brandName.textContent = `${data.brand} Support`;
  brandDot.textContent = data.brand.slice(0, 2);

  const productLine = data.products.map((p) => p.product_name).join(", ");
  addBubble(`Hi ${data.customer_name}! I can see your ${productLine}. What can I help with?`, "agent");
  awaitingFirstComplaint = true;
  setComposerEnabled(true);
  messageInput.focus();
}

async function sendMessage() {
  const text = messageInput.value.trim();
  if (!text) return;
  addBubble(text, "customer");
  messageInput.value = "";
  setComposerEnabled(false);

  const isFirstComplaint = awaitingFirstComplaint;
  let data;
  if (isFirstComplaint) {
    const res = await fetch("/api/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone, complaint: text }),
    });
    data = await res.json();
  } else {
    const res = await fetch("/api/respond", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ conversation_id: conversationId, reply: text }),
    });
    data = await res.json();
  }

  if (data.error) {
    // Don't flip awaitingFirstComplaint/conversationId on a failed call --
    // a retry needs to hit the same endpoint again, not /api/respond with
    // no valid conversation_id. And don't leave the composer dead: without
    // this, an error here was a permanent dead end.
    addBubble(data.error, "system");
    setComposerEnabled(true);
    messageInput.focus();
    return;
  }

  if (isFirstComplaint) {
    conversationId = data.conversation_id;
    awaitingFirstComplaint = false;
  }

  const cls = data.status === "escalated" ? "ticket" : "agent";
  addBubble(data.message, cls);

  if (data.status === "resolved" || data.status === "escalated") {
    setComposerEnabled(false);
  } else {
    setComposerEnabled(true);
    messageInput.focus();
  }
}

sendBtn.addEventListener("click", sendMessage);
messageInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendMessage();
});
