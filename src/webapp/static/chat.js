const lookupPhone = document.getElementById("lookup-phone");
const splitView = document.getElementById("split-view");
const customerList = document.getElementById("customer-list");
const lookupError = document.getElementById("lookup-error");

const chatBodyCustomer = document.getElementById("chat-body-customer");
const messagesCustomer = document.getElementById("messages");
const chatBodyBrand = document.getElementById("chat-body-brand");
const messagesBrand = document.getElementById("messages-brand");

const composer = document.getElementById("composer");
const messageInput = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");

const brandDot = document.getElementById("brand-dot");
const brandName = document.getElementById("brand-name");
const brandDotLeft = document.getElementById("brand-dot-left");
const brandNameLeft = document.getElementById("brand-name-left");
const brandPaneLabel = document.getElementById("brand-pane-label");
const dashboardLink = document.getElementById("dashboard-link");

let phone = null;
let brandSlug = null;
let conversationId = null;
let awaitingFirstComplaint = false;

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Two panes render the SAME conversation, mirrored -- a message the
// customer sends is "mine" on their own phone and "theirs" (received)
// on the brand's side, and vice versa for the agent's reply. That
// mirroring is the entire point of this view: one real conversation,
// shown from both sides, the way an actual WhatsApp exchange would
// look on two separate phones.
function appendBubble(container, scrollHost, text, alignment, modifier) {
  const el = document.createElement("div");
  el.className = `bubble ${alignment}${modifier ? " " + modifier : ""}`;
  el.textContent = text;
  container.appendChild(el);
  scrollHost.scrollTop = scrollHost.scrollHeight;
  return el;
}

function showTyping() {
  const el = document.createElement("div");
  el.className = "bubble theirs typing";
  el.innerHTML = "<span class=\"dot\"></span><span class=\"dot\"></span><span class=\"dot\"></span>";
  messagesCustomer.appendChild(el);
  chatBodyCustomer.scrollTop = chatBodyCustomer.scrollHeight;
  return el;
}

// from: "customer" | "agent" -- who authored the message. modifier is
// an extra class (e.g. "ticket") layered on top of the mine/theirs
// alignment for escalation styling.
async function deliver(text, from, modifier) {
  const senderContainer = from === "customer" ? [messagesCustomer, chatBodyCustomer] : [messagesBrand, chatBodyBrand];
  const receiverContainer = from === "customer" ? [messagesBrand, chatBodyBrand] : [messagesCustomer, chatBodyCustomer];

  appendBubble(senderContainer[0], senderContainer[1], text, "mine", modifier);
  await delay(350); // sells the "sent -> received on the other phone" beat
  appendBubble(receiverContainer[0], receiverContainer[1], text, "theirs", modifier);
}

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
  brandSlug = data.brand.toLowerCase();
  lookupPhone.hidden = true;
  splitView.hidden = false;

  const initials = data.brand.slice(0, 2);
  brandName.textContent = `${data.brand} Support`;
  brandDot.textContent = initials;
  brandNameLeft.innerHTML = `${data.brand}<span class="business-badge">Business</span>`;
  brandDotLeft.textContent = initials;
  brandPaneLabel.textContent = data.brand;
  dashboardLink.href = `/dashboard/${brandSlug}`;

  const productLine = data.products.map((p) => p.product_name).join(", ");
  await deliver(`Hi ${data.customer_name}! I can see your ${productLine}. What can I help with?`, "agent");
  awaitingFirstComplaint = true;
  setComposerEnabled(true);
  messageInput.focus();
}

async function sendMessage() {
  const text = messageInput.value.trim();
  if (!text) return;
  messageInput.value = "";
  setComposerEnabled(false);

  const isFirstComplaint = awaitingFirstComplaint;
  await deliver(text, "customer");

  const typingBubble = showTyping();
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
  typingBubble.remove();

  if (data.error) {
    // Don't flip awaitingFirstComplaint/conversationId on a failed call --
    // a retry needs to hit the same endpoint again, not /api/respond with
    // no valid conversation_id. And don't leave the composer dead: without
    // this, an error here was a permanent dead end.
    appendBubble(messagesCustomer, chatBodyCustomer, data.error, "theirs", "system");
    setComposerEnabled(true);
    messageInput.focus();
    return;
  }

  if (isFirstComplaint) {
    conversationId = data.conversation_id;
    awaitingFirstComplaint = false;
  }

  const modifier = data.status === "escalated" ? "ticket" : undefined;
  await deliver(data.message, "agent", modifier);

  if (data.status === "escalated") {
    dashboardLink.hidden = false;
  }

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
