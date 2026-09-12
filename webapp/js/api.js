// Local dev (python -m http.server) talks straight to uvicorn on :8000.
// A real deploy serves both from the same Caddy origin, proxied under /api —
// see deploy/Caddyfile — so same-origin relative calls need no CORS at all.
const API_BASE =
  location.hostname === "localhost" || location.hostname === "127.0.0.1"
    ? "http://127.0.0.1:8000"
    : "/api";

function getToken() {
  return localStorage.getItem("token");
}

function setToken(token) {
  localStorage.setItem("token", token);
}

function clearSession() {
  localStorage.removeItem("token");
  localStorage.removeItem("me");
}

function getMe() {
  const raw = localStorage.getItem("me");
  return raw ? JSON.parse(raw) : null;
}

function setMe(me) {
  localStorage.setItem("me", JSON.stringify(me));
}

class ApiError extends Error {
  constructor(status, detail) {
    super(detail || `خطای ${status}`);
    this.status = status;
  }
}

async function api(path, { method = "GET", body, isForm = false } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (!isForm && body !== undefined) headers["Content-Type"] = "application/json";

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
  });

  if (res.status === 401) {
    clearSession();
    window.location.href = "index.html";
    throw new ApiError(401, "دوباره وارد شوید.");
  }

  if (!res.ok) {
    let detail = `خطای ${res.status}`;
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch (_) {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return null;
  const contentType = res.headers.get("content-type") || "";
  return contentType.includes("application/json") ? res.json() : res.blob();
}

/** Redirect to login unless a valid role's token is present. Call at the top
 * of every protected page. */
function requireRole(role) {
  const me = getMe();
  if (!getToken() || !me) {
    window.location.href = "index.html";
    return null;
  }
  if (me.role !== role) {
    window.location.href = `${me.role}.html`;
    return null;
  }
  return me;
}

function shopPhotoUrl(shopId) {
  return `${API_BASE}/shops/${shopId}/photo`;
}

function toast(message) {
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = message;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 2600);
}

const STATUS_LABELS = {
  registered: "ثبت‌شده",
  awaiting_threshold: "منتظر آستانه امتیاز",
  queued_for_pack: "صف پخش پک",
  pack_delivered: "پک تحویل شد",
  order1_pending_delivery: "منتظر تحویل سفارش ۱",
  order1_done: "سفارش ۱ تحویل شد",
  order2_pending_delivery: "منتظر تحویل سفارش ۲",
  steady_customer: "مشتری دائمی",
  dropped: "کنار گذاشته شده",
};

const STATUS_CHIP_CLASS = {
  registered: "muted",
  awaiting_threshold: "muted",
  queued_for_pack: "scout",
  pack_delivered: "visitor",
  order1_pending_delivery: "money",
  order1_done: "visitor",
  order2_pending_delivery: "money",
  steady_customer: "visitor",
  dropped: "alert",
};

function statusChip(status) {
  const cls = STATUS_CHIP_CLASS[status] || "muted";
  const label = STATUS_LABELS[status] || status;
  return `<span class="chip ${cls}">${label}</span>`;
}

// ---------------- shop phone numbers (list, not a single field — anyone on
// staff can add one, each with its own short note) ----------------

function phonesSectionHtml(shopId) {
  return `
    <div class="phones-section">
      <div class="phones-list" id="phones-list-${shopId}"></div>
      <div class="row" style="margin-top:6px">
        <input class="phone-num-input" data-shop="${shopId}" placeholder="شماره تلفن"
          style="flex:1;min-width:110px;border:1px solid var(--border);border-radius:8px;padding:6px 8px;background:var(--surface);color:var(--ink)" />
        <input class="phone-note-input" data-shop="${shopId}" placeholder="توضیح کوتاه (مثلاً: شماره صاحب مغازه)"
          style="flex:1;min-width:150px;border:1px solid var(--border);border-radius:8px;padding:6px 8px;background:var(--surface);color:var(--ink)" />
        <button class="btn secondary add-phone-btn" data-shop="${shopId}">افزودن شماره</button>
      </div>
    </div>`;
}

async function loadPhonesInto(shopId) {
  const el = document.getElementById(`phones-list-${shopId}`);
  if (!el) return;
  const phones = await api(`/shops/${shopId}/phones`);
  el.innerHTML = phones.length
    ? phones
        .map((p) => `<div class="meta"><span class="num">${p.phone}</span>${p.note ? " — " + p.note : ""}</div>`)
        .join("")
    : `<div class="meta">شماره‌ای ثبت نشده.</div>`;
}

// ---------------- modal ----------------

function openModal(bodyHtml) {
  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.innerHTML = `<div class="modal">${bodyHtml}</div>`;
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) overlay.remove();
  });
  document.body.appendChild(overlay);
  return overlay;
}

function closeModal(overlay) {
  overlay.remove();
}

// ---------------- voice recording (visitor's opinion on a pack delivery) ----------------

/** Wires a record/stop button + live preview inside `container`. Call
 * `getBlob()` at submit time to get the recorded audio (or null). */
function setupVoiceRecorder(container) {
  const btn = container.querySelector(".rec-btn");
  const dot = container.querySelector(".rec-dot");
  const audioEl = container.querySelector(".rec-preview");
  let mediaRecorder, chunks = [], blob = null, stream = null;

  btn.addEventListener("click", async () => {
    if (mediaRecorder && mediaRecorder.state === "recording") {
      mediaRecorder.stop();
      return;
    }
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (e) {
      toast("دسترسی به میکروفون داده نشد.");
      return;
    }
    chunks = [];
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = (e) => chunks.push(e.data);
    mediaRecorder.onstop = () => {
      blob = new Blob(chunks, { type: "audio/webm" });
      audioEl.src = URL.createObjectURL(blob);
      audioEl.style.display = "";
      dot.classList.remove("on");
      btn.textContent = "🎙 ضبط دوباره";
      stream.getTracks().forEach((t) => t.stop());
    };
    mediaRecorder.start();
    dot.classList.add("on");
    btn.textContent = "⏹ توقف ضبط";
  });

  return {
    getBlob: () => blob,
  };
}

async function uploadVoiceBlob(blob) {
  const form = new FormData();
  form.append("file", blob, "voice.webm");
  const { url } = await api("/uploads", { method: "POST", body: form, isForm: true });
  return url;
}

/** Call once after injecting any phonesSectionHtml() into the DOM. */
function wirePhoneSections(root = document) {
  root.querySelectorAll(".add-phone-btn").forEach((btn) => {
    if (btn.dataset.wired) return;
    btn.dataset.wired = "1";
    btn.addEventListener("click", async () => {
      const shopId = btn.dataset.shop;
      const numInput = root.querySelector(`.phone-num-input[data-shop="${shopId}"]`);
      const noteInput = root.querySelector(`.phone-note-input[data-shop="${shopId}"]`);
      const phone = numInput.value.trim();
      if (!phone) return;
      await api(`/shops/${shopId}/phones`, { method: "POST", body: { phone, note: noteInput.value.trim() || null } });
      numInput.value = "";
      noteInput.value = "";
      toast("شماره اضافه شد.");
      await loadPhonesInto(shopId);
    });
  });
}
