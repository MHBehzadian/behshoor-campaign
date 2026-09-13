(function () {
  const me = requireRole("visitor");
  if (!me) return;
  document.getElementById("who").textContent = `${me.full_name}${me.visitor_subteam ? " — زیرتیم " + me.visitor_subteam : ""}`;
  document.getElementById("logout-btn").addEventListener("click", () => {
    clearSession();
    window.location.href = "index.html";
  });

  let packMap, packLayer, packBoundaryLayer;
  let followupMap, followupLayer;

  document.querySelectorAll(".tabs button").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tabs button").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(`panel-${btn.dataset.tab}`).classList.add("active");
      if (btn.dataset.tab === "pack" && packMap) setTimeout(() => packMap.invalidateSize(), 0);
      if (btn.dataset.tab === "followup") {
        if (followupMap) setTimeout(() => followupMap.invalidateSize(), 0);
        loadFollowupQueue();
      }
    });
  });

  // ---------------- pack delivery queue ----------------

  async function loadPackQueue() {
    const region = await api("/pack-deliveries/region");
    document.getElementById("pack-region-label").textContent = region
      ? `ناحیه‌ی امروز: ${region.name}`
      : "امروز ناحیه‌ای برای پخش پک تعیین نشده.";

    if (!packMap) packMap = createMap("pack-map");
    if (region?.boundary_geojson) {
      if (packBoundaryLayer) packMap.removeLayer(packBoundaryLayer);
      packBoundaryLayer = renderRegionBoundaries(packMap, [region], region.id);
    }
    const shops = await api("/pack-deliveries/queue");
    packLayer = renderShopLayer(packMap, packLayer, shops, (s) => `<b>${s.name}</b><br/>${s.address_text}`);

    document.getElementById("pack-list").innerHTML = shops.length
      ? shops
          .map(
            (s) => `
      <div class="card">
        <h3>${s.name}</h3>
        <div class="meta">${s.address_text}</div>
        <div class="meta">امتیاز در‌آور: ${"⭐️".repeat(s.scout_score)}</div>
        ${phonesSectionHtml(s.id)}
        <button class="btn" style="margin-top:8px" onclick="openDeliverModal(${s.id}, ${JSON.stringify(s.name).replace(/"/g, "&quot;")})">ثبت تحویل پک</button>
      </div>`
          )
          .join("")
      : `<div class="empty-state">امروز پکی برای تحویل نداری. 🎉</div>`;
    wirePhoneSections();
    shops.forEach((s) => loadPhonesInto(s.id));
  }

  window.openDeliverModal = function (shopId, shopName) {
    const overlay = openModal(`
      <h3>ثبت تحویل پک — ${shopName}</h3>
      <div class="field">
        <label>امتیاز احتمال خرید</label>
        <div class="score-picker" id="pd-score">
          ${[1, 2, 3, 4, 5].map((v) => `<button type="button" data-v="${v}">${v}</button>`).join("")}
        </div>
      </div>
      <div class="field"><label>نظر شما درباره‌ی مغازه</label><textarea id="pd-opinion" rows="3"></textarea></div>
      <div class="field">
        <label>ویس (اختیاری)</label>
        <div class="rec-row">
          <button type="button" class="btn secondary rec-btn">🎙 شروع ضبط</button>
          <span class="rec-dot"></span>
          <audio class="rec-preview" controls style="display:none;height:32px"></audio>
        </div>
      </div>
      <div class="error-msg" id="pd-error"></div>
      <div class="modal-actions">
        <button class="btn secondary" id="pd-cancel">انصراف</button>
        <button class="btn" id="pd-submit">ثبت</button>
      </div>
    `);
    let selectedScore = null;
    overlay.querySelectorAll("#pd-score button").forEach((b) =>
      b.addEventListener("click", () => {
        overlay.querySelectorAll("#pd-score button").forEach((x) => x.classList.remove("selected"));
        b.classList.add("selected");
        selectedScore = Number(b.dataset.v);
      })
    );
    const recorder = setupVoiceRecorder(overlay);
    overlay.querySelector("#pd-cancel").addEventListener("click", () => closeModal(overlay));
    overlay.querySelector("#pd-submit").addEventListener("click", async () => {
      const errEl = overlay.querySelector("#pd-error");
      if (!selectedScore) {
        errEl.textContent = "امتیاز رو انتخاب کن.";
        return;
      }
      try {
        let voice_note_url = null;
        const blob = recorder.getBlob();
        if (blob) voice_note_url = await uploadVoiceBlob(blob);
        await api("/pack-deliveries", {
          method: "POST",
          body: {
            shop_id: shopId,
            opinion_text: overlay.querySelector("#pd-opinion").value.trim() || null,
            voice_note_url,
            score_1_5: selectedScore,
          },
        });
        closeModal(overlay);
        toast("تحویل پک ثبت شد.");
        loadPackQueue();
      } catch (e) {
        errEl.textContent = e.message;
      }
    });
  };

  // ---------------- followup queue ----------------

  const ORDER_LABEL = { pack_delivered: "سفارش ۱", order1_done: "سفارش ۲" };

  async function loadFollowupQueue() {
    const shops = await api("/followups/queue");
    if (!followupMap) followupMap = createMap("followup-map");
    followupLayer = renderShopLayer(
      followupMap,
      followupLayer,
      shops,
      (s) => `<b>${s.name}</b><br/>${s.address_text}<br/>پیگیری ${ORDER_LABEL[s.status] || ""}`,
      () => true // everything in this queue is due for follow-up right now
    );

    document.getElementById("followup-list").innerHTML = shops.length
      ? shops
          .map(
            (s) => `
      <div class="card">
        <h3>${s.name}</h3>
        <div class="meta">${s.address_text}</div>
        <div class="row" style="align-items:center;margin:6px 0">
          <span class="chip visitor">پیگیری ${ORDER_LABEL[s.status] || ""}</span>
        </div>
        ${phonesSectionHtml(s.id)}
        <div class="row" style="margin-top:8px">
          <button class="btn" onclick="openCloseModal(${s.id}, ${JSON.stringify(s.name).replace(/"/g, "&quot;")})">بستن سفارش</button>
          <button class="btn secondary" onclick="openRejectModal(${s.id}, ${JSON.stringify(s.name).replace(/"/g, "&quot;")})">رد کردن</button>
        </div>
      </div>`
          )
          .join("")
      : `<div class="empty-state">امروز پیگیری‌ای نداری.</div>`;
    wirePhoneSections();
    shops.forEach((s) => loadPhonesInto(s.id));
  }

  window.openCloseModal = function (shopId, shopName) {
    const overlay = openModal(`
      <h3>بستن سفارش — ${shopName}</h3>
      <div class="field"><label>نام محصول</label><input id="cl-product" placeholder="مثلاً: روغن زیتون ۱ لیتری" /></div>
      <div class="error-msg" id="cl-error"></div>
      <div class="modal-actions">
        <button class="btn secondary" id="cl-cancel">انصراف</button>
        <button class="btn" id="cl-submit">ثبت سفارش</button>
      </div>
    `);
    overlay.querySelector("#cl-cancel").addEventListener("click", () => closeModal(overlay));
    overlay.querySelector("#cl-submit").addEventListener("click", async () => {
      const product = overlay.querySelector("#cl-product").value.trim();
      const errEl = overlay.querySelector("#cl-error");
      if (!product) {
        errEl.textContent = "نام محصول رو بنویس.";
        return;
      }
      try {
        await api("/followups", { method: "POST", body: { shop_id: shopId, closed: true, product_name: product } });
        closeModal(overlay);
        toast("سفارش ثبت شد — منتظر تحویل پخش.");
        loadFollowupQueue();
      } catch (e) {
        errEl.textContent = e.message;
      }
    });
  };

  window.openRejectModal = function (shopId, shopName) {
    const overlay = openModal(`
      <h3>رد کردن — ${shopName}</h3>
      <div class="field"><label>دلیل</label><textarea id="rj-reason" rows="2"></textarea></div>
      <div class="field"><label>روز پیگیری بعدی (اختیاری — پیش‌فرض ۳ روز دیگه)</label><input type="date" id="rj-date" /></div>
      <div class="error-msg" id="rj-error"></div>
      <div class="modal-actions">
        <button class="btn secondary" id="rj-cancel">انصراف</button>
        <button class="btn danger" id="rj-submit">ثبت</button>
      </div>
    `);
    overlay.querySelector("#rj-cancel").addEventListener("click", () => closeModal(overlay));
    overlay.querySelector("#rj-submit").addEventListener("click", async () => {
      const errEl = overlay.querySelector("#rj-error");
      try {
        await api("/followups", {
          method: "POST",
          body: {
            shop_id: shopId,
            closed: false,
            reject_reason: overlay.querySelector("#rj-reason").value.trim() || null,
            rescheduled_to: overlay.querySelector("#rj-date").value || null,
          },
        });
        closeModal(overlay);
        toast("ثبت شد.");
        loadFollowupQueue();
      } catch (e) {
        errEl.textContent = e.message;
      }
    });
  };

  loadPackQueue();
})();
