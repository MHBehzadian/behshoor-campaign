(function () {
  const me = requireRole("distributor");
  if (!me) return;
  document.getElementById("who").textContent = me.full_name;
  document.getElementById("logout-btn").addEventListener("click", () => {
    clearSession();
    window.location.href = "index.html";
  });

  let fulfillMap, fulfillLayer;

  document.querySelectorAll(".tabs button").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tabs button").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(`panel-${btn.dataset.tab}`).classList.add("active");
      if (btn.dataset.tab === "fulfillments" && fulfillMap) setTimeout(() => fulfillMap.invalidateSize(), 0);
      if (btn.dataset.tab === "checkups") loadCheckupQueue();
    });
  });

  // ---------------- order fulfillment queue ----------------

  async function loadFulfillmentQueue() {
    if (!fulfillMap) fulfillMap = createMap("fulfill-map");
    const shops = await api("/fulfillments/queue");
    fulfillLayer = renderShopLayer(fulfillMap, fulfillLayer, shops, (s) => `<b>${s.name}</b><br/>${s.address_text}`);

    document.getElementById("fulfill-list").innerHTML = shops.length
      ? shops
          .map(
            (s) => `
      <div class="card">
        <h3>${s.name}</h3>
        <div class="meta">${s.address_text}</div>
        ${statusChip(s.status)}
        ${phonesSectionHtml(s.id)}
        <button class="btn" style="margin-top:8px" onclick="openFulfillModal(${s.id}, ${JSON.stringify(s.name).replace(/"/g, "&quot;")})">ثبت تحویل و وصول پول</button>
      </div>`
          )
          .join("")
      : `<div class="empty-state">سفارشی برای تحویل نداری.</div>`;
    wirePhoneSections();
    shops.forEach((s) => loadPhonesInto(s.id));
  }

  window.openFulfillModal = function (shopId, shopName) {
    const overlay = openModal(`
      <h3>ثبت تحویل — ${shopName}</h3>
      <div class="field"><label>مبلغ دریافتی (تومان)</label><input type="number" id="fl-amount" /></div>
      <div class="field"><label>توضیح (اختیاری)</label><textarea id="fl-notes" rows="2"></textarea></div>
      <p class="meta">این مبلغ مبنای نهایی محاسبه‌ی کمیسیون شماست و ویزیتور.</p>
      <div class="error-msg" id="fl-error"></div>
      <div class="modal-actions">
        <button class="btn secondary" id="fl-cancel">انصراف</button>
        <button class="btn" id="fl-submit">ثبت</button>
      </div>
    `);
    overlay.querySelector("#fl-cancel").addEventListener("click", () => closeModal(overlay));
    overlay.querySelector("#fl-submit").addEventListener("click", async () => {
      const errEl = overlay.querySelector("#fl-error");
      const amount = Number(overlay.querySelector("#fl-amount").value);
      if (!amount || amount <= 0) {
        errEl.textContent = "مبلغ رو درست وارد کن.";
        return;
      }
      try {
        await api("/fulfillments", {
          method: "POST",
          body: { shop_id: shopId, amount, notes: overlay.querySelector("#fl-notes").value.trim() || null },
        });
        closeModal(overlay);
        toast("تحویل ثبت شد.");
        loadFulfillmentQueue();
      } catch (e) {
        errEl.textContent = e.message;
      }
    });
  };

  // ---------------- weekly check-ups ----------------

  async function loadCheckupQueue() {
    const checkups = await api("/checkups/queue");
    document.getElementById("checkup-list").innerHTML = checkups.length
      ? checkups
          .map(
            (c) => `
      <div class="card">
        <h3>مغازه #${c.shop_id}</h3>
        <div class="meta">تاریخ سرکشی: ${formatJalaliLong ? formatJalaliLong(c.scheduled_for) : c.scheduled_for}</div>
        ${phonesSectionHtml(c.shop_id)}
        <button class="btn" style="margin-top:8px" onclick="openCheckupModal(${c.id}, ${c.shop_id})">تکمیل سرکشی</button>
      </div>`
          )
          .join("")
      : `<div class="empty-state">امروز سرکشی‌ای نداری.</div>`;
    wirePhoneSections();
    checkups.forEach((c) => loadPhonesInto(c.shop_id));
  }

  window.openCheckupModal = function (checkupId, shopId) {
    const overlay = openModal(`
      <h3>تکمیل سرکشی — مغازه #${shopId}</h3>
      <div class="field">
        <label>روش</label>
        <select id="ck-method">
          <option value="in_person">حضوری</option>
          <option value="phone">تماس تلفنی</option>
        </select>
      </div>
      <div class="field"><label>توضیح (اختیاری)</label><textarea id="ck-notes" rows="2"></textarea></div>
      <div class="field"><label>اگر سفارش جدیدی گرفتی، مبلغش رو بنویس (اختیاری)</label><input type="number" id="ck-amount" /></div>
      <div class="error-msg" id="ck-error"></div>
      <div class="modal-actions">
        <button class="btn secondary" id="ck-cancel">انصراف</button>
        <button class="btn" id="ck-submit">ثبت</button>
      </div>
    `);
    overlay.querySelector("#ck-cancel").addEventListener("click", () => closeModal(overlay));
    overlay.querySelector("#ck-submit").addEventListener("click", async () => {
      const errEl = overlay.querySelector("#ck-error");
      const amountRaw = overlay.querySelector("#ck-amount").value;
      try {
        await api(`/checkups/${checkupId}/complete`, {
          method: "POST",
          body: {
            method: overlay.querySelector("#ck-method").value,
            notes: overlay.querySelector("#ck-notes").value.trim() || null,
            resulted_order_amount: amountRaw ? Number(amountRaw) : null,
          },
        });
        closeModal(overlay);
        toast("سرکشی ثبت شد.");
        loadCheckupQueue();
      } catch (e) {
        errEl.textContent = e.message;
      }
    });
  };

  loadFulfillmentQueue();
})();
