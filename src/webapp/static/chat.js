const lookupScreen = document.getElementById("lookup-screen");
const phoneInput = document.getElementById("phone-input");
const lookupBtn = document.getElementById("lookup-btn");
const lookupError = document.getElementById("lookup-error");
const chatBody = document.getElementById("chat-body");
const messagesEl = document.getElementById("messages");
const composer = document.getElementById("composer");
const messageInput = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");

let phone = null;
let conversationId = null;
let awaitingFirstComplaint = false;

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

lookupBtn.addEventListener("click", async () => {
  const value = phoneInput.value.trim();
  if (!value) return;
  lookupError.hidden = true;

  const res = await fetch("/api/lookup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ phone: value }),
  });
  const data = await res.json();

  if (!data.found) {
    lookupError.textContent = "We don't have a registration for this number.";
    lookupError.hidden = false;
    return;
  }

  phone = value;
  lookupScreen.hidden = true;
  messagesEl.hidden = false;
  composer.hidden = false;

  const productLine = data.products.map((p) => p.product_name).join(", ");
  addBubble(`Hi ${data.customer_name}! I can see your ${productLine}. What can I help with?`, "agent");
  awaitingFirstComplaint = true;
  setComposerEnabled(true);
  messageInput.focus();
});

phoneInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") lookupBtn.click();
});

async function sendMessage() {
  const text = messageInput.value.trim();
  if (!text) return;
  addBubble(text, "customer");
  messageInput.value = "";
  setComposerEnabled(false);

  let data;
  if (awaitingFirstComplaint) {
    const res = await fetch("/api/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone, complaint: text }),
    });
    data = await res.json();
    conversationId = data.conversation_id;
    awaitingFirstComplaint = false;
  } else {
    const res = await fetch("/api/respond", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ conversation_id: conversationId, reply: text }),
    });
    data = await res.json();
  }

  if (data.error) {
    addBubble(data.error, "system");
    return;
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
