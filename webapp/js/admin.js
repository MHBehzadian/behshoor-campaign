(function () {
  const me = requireRole("admin");
  if (!me) return;
  document.getElementById("who").textContent = me.full_name;
  document.getElementById("logout-btn").addEventListener("click", () => {
    clearSession();
    window.location.href = "index.html";
  });

  // ---------------- tabs ----------------
  // Leaflet maps created inside a display:none panel initialize at 0x0 and
  // never recompute — every projection on them is garbage until told
  // otherwise, so invalidateSize() whenever a map's tab becomes visible.
  document.querySelectorAll(".tabs button").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tabs button").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(`panel-${btn.dataset.tab}`).classList.add("active");
      if (btn.dataset.tab === "dashboard" && dashMap) setTimeout(() => dashMap.invalidateSize(), 0);
      if (btn.dataset.tab === "regions" && regionMap) setTimeout(() => regionMap.invalidateSize(), 0);
    });
  });

  let regionsCache = [];

  async function loadRegions() {
    regionsCache = await api("/regions");
    return regionsCache;
  }

  function regionOptionsHtml(selectedId) {
    return regionsCache
      .map((r) => `<option value="${r.id}" ${r.id === selectedId ? "selected" : ""}>${r.name}</option>`)
      .join("");
  }

  // ---------------- dashboard ----------------
  let dashMap, dashLayer;

  async function initDashboard() {
    await loadRegions();
    document.getElementById("dash-region-filter").innerHTML +=
      regionsCache.map((r) => `<option value="${r.id}">${r.name}</option>`).join("");
    document.getElementById("dash-status-filter").innerHTML += Object.entries(STATUS_LABELS)
      .map(([k, v]) => `<option value="${k}">${v}</option>`)
      .join("");

    dashMap = createMap("dash-map");
    document.getElementById("dash-region-filter").addEventListener("change", refreshDashboard);
    document.getElementById("dash-status-filter").addEventListener("change", refreshDashboard);
    await refreshDashboard();
  }

  async function refreshDashboard() {
    const regionId = document.getElementById("dash-region-filter").value;
    const status = document.getElementById("dash-status-filter").value;
    const params = new URLSearchParams();
    if (regionId) params.set("region_id", regionId);
    if (status) params.set("status", status);
    const shops = await api(`/shops?${params.toString()}`);

    dashLayer = renderShopLayer(dashMap, dashLayer, shops, (shop) => `
      <b>${shop.name}</b><br/>${shop.address_text}<br/>
      امتیاز: ${"⭐️".repeat(shop.scout_score)}<br/>${STATUS_LABELS[shop.status] || shop.status}
    `);

    document.getElementById("dash-list").innerHTML = shops.length
      ? shops
          .map(
            (s) => `
      <div class="card">
        <h3>${s.name}</h3>
        <div class="meta">${s.address_text}</div>
        <div class="row" style="align-items:center; margin:6px 0">
          ${statusChip(s.status)} <span class="meta">امتیاز: ${"⭐️".repeat(s.scout_score)}</span>
        </div>
        ${phonesSectionHtml(s.id)}
        ${s.status !== "dropped" ? `<button class="btn danger drop-btn" data-shop="${s.id}" style="margin-top:8px">کنار گذاشتن</button>` : ""}
      </div>`
          )
          .join("")
      : `<div class="empty-state">مغازه‌ای با این فیلتر نیست.</div>`;

    wirePhoneSections();
    shops.forEach((s) => loadPhonesInto(s.id));

    document.querySelectorAll(".drop-btn").forEach((btn) =>
      btn.addEventListener("click", async () => {
        if (!confirm("این مغازه از چرخه‌ی پیگیری کنار گذاشته بشه؟")) return;
        await api(`/shops/${btn.dataset.shop}/drop`, { method: "PATCH" });
        toast("کنار گذاشته شد.");
        refreshDashboard();
      })
    );
  }

  // ---------------- regions ----------------
  let regionMap, regionDrawnLayer, drawControl, selectedRegionId = null;

  async function initRegions() {
    regionMap = createMap("region-map", { zoom: 12 });
    regionDrawnLayer = new L.FeatureGroup().addTo(regionMap);
    drawControl = new L.Control.Draw({
      draw: { polygon: true, marker: false, circle: false, circlemarker: false, polyline: false, rectangle: false },
      edit: { featureGroup: regionDrawnLayer },
    });
    regionMap.addControl(drawControl);

    regionMap.on(L.Draw.Event.CREATED, (e) => {
      regionDrawnLayer.clearLayers();
      regionDrawnLayer.addLayer(e.layer);
      document.getElementById("save-boundary-btn").disabled = false;
    });
    regionMap.on(L.Draw.Event.EDITED, () => {
      document.getElementById("save-boundary-btn").disabled = false;
    });

    document.getElementById("clear-boundary-btn").addEventListener("click", () => {
      regionDrawnLayer.clearLayers();
      document.getElementById("save-boundary-btn").disabled = false;
    });

    document.getElementById("save-boundary-btn").addEventListener("click", async () => {
      if (!selectedRegionId) return;
      const layers = regionDrawnLayer.getLayers();
      const geojson = layers.length ? layers[0].toGeoJSON().geometry : null;
      await api(`/regions/${selectedRegionId}`, { method: "PATCH", body: { boundary_geojson: geojson } });
      toast("مرز ذخیره شد.");
      document.getElementById("save-boundary-btn").disabled = true;
      await renderRegionList();
    });

    document.getElementById("add-region-btn").addEventListener("click", async () => {
      const name = document.getElementById("new-region-name").value.trim();
      const errEl = document.getElementById("region-error");
      errEl.textContent = "";
      if (!name) return;
      try {
        await api("/regions", { method: "POST", body: { name } });
        document.getElementById("new-region-name").value = "";
        await loadRegions();
        await renderRegionList();
      } catch (e) {
        errEl.textContent = e.message;
      }
    });

    await loadRegions();
    await renderRegionList();
  }

  async function renderRegionList() {
    document.getElementById("region-list").innerHTML = regionsCache
      .map(
        (r) => `<div class="card" data-region="${r.id}" style="cursor:pointer">
        <h3>${r.name}</h3>
        <div class="meta">${r.boundary_geojson ? "مرز ثبت شده" : "بدون مرز"}</div>
      </div>`
      )
      .join("");
    document.querySelectorAll("#region-list [data-region]").forEach((card) =>
      card.addEventListener("click", () => selectRegion(Number(card.dataset.region)))
    );
  }

  function selectRegion(id) {
    selectedRegionId = id;
    const region = regionsCache.find((r) => r.id === id);
    regionDrawnLayer.clearLayers();
    if (region.boundary_geojson) {
      const layer = L.geoJSON(region.boundary_geojson);
      layer.eachLayer((l) => regionDrawnLayer.addLayer(l));
      regionMap.fitBounds(regionDrawnLayer.getBounds(), { maxZoom: 15 });
    }
    document.getElementById("save-boundary-btn").disabled = true;
    document.getElementById("clear-boundary-btn").disabled = false;
  }

  // ---------------- day schedule ----------------
  const DAY_TYPE_LABELS = { distribution: "پخش", followup: "پیگیری", holiday: "تعطیل" };

  async function initSchedule() {
    const from = new Date();
    const to = new Date();
    to.setDate(to.getDate() + 13);
    const fmt = (d) => d.toISOString().slice(0, 10);
    const existing = await api(`/day-schedules?date_from=${fmt(from)}&date_to=${fmt(to)}`);
    const byDate = Object.fromEntries(existing.map((s) => [s.date, s]));

    const rows = [];
    for (let i = 0; i < 14; i++) {
      const d = new Date(from);
      d.setDate(d.getDate() + i);
      const dateStr = fmt(d);
      const sched = byDate[dateStr];
      rows.push(`
        <tr data-date="${dateStr}">
          <td>${formatJalaliLong(d)}</td>
          <td>
            <select class="day-type">
              ${Object.entries(DAY_TYPE_LABELS)
                .map(([k, v]) => `<option value="${k}" ${sched?.day_type === k ? "selected" : ""}>${v}</option>`)
                .join("")}
            </select>
          </td>
          <td>
            <select class="day-region" ${sched?.day_type !== "distribution" ? "disabled" : ""}>
              <option value="">—</option>
              ${regionOptionsHtml(sched?.target_region_id)}
            </select>
          </td>
          <td><button class="btn secondary save-day-btn">ذخیره</button></td>
        </tr>`);
    }
    document.getElementById("schedule-body").innerHTML = rows.join("");

    document.querySelectorAll("#schedule-body tr").forEach((tr) => {
      const typeSel = tr.querySelector(".day-type");
      const regionSel = tr.querySelector(".day-region");
      typeSel.addEventListener("change", () => {
        regionSel.disabled = typeSel.value !== "distribution";
      });
      tr.querySelector(".save-day-btn").addEventListener("click", async () => {
        const day_type = typeSel.value;
        const target_region_id = day_type === "distribution" ? Number(regionSel.value) || null : null;
        if (day_type === "distribution" && !target_region_id) {
          toast("برای روز پخش، ناحیه رو انتخاب کن.");
          return;
        }
        await api(`/day-schedules/${tr.dataset.date}`, { method: "PUT", body: { day_type, target_region_id } });
        toast("ذخیره شد.");
      });
    });
  }

  // ---------------- settings ----------------
  async function initSettings() {
    const s = await api("/settings");
    document.getElementById("s-threshold").value = s.score_threshold;
    document.getElementById("s-dual-team").checked = s.visitor_dual_team_enabled;
    document.getElementById("s-scout-fee").value = s.scout_fixed_fee;
    document.getElementById("s-visitor-fee").value = s.visitor_fixed_fee;
    document.getElementById("s-visitor-pct").value = s.visitor_commission_pct;
    document.getElementById("s-dist-pct").value = s.distributor_commission_pct;
    document.getElementById("s-checkup-days").value = s.checkup_interval_days;

    document.getElementById("save-settings-btn").addEventListener("click", async () => {
      const msg = document.getElementById("settings-msg");
      msg.textContent = "";
      try {
        await api("/settings", {
          method: "PATCH",
          body: {
            score_threshold: Number(document.getElementById("s-threshold").value),
            visitor_dual_team_enabled: document.getElementById("s-dual-team").checked,
            scout_fixed_fee: Number(document.getElementById("s-scout-fee").value),
            visitor_fixed_fee: Number(document.getElementById("s-visitor-fee").value),
            visitor_commission_pct: Number(document.getElementById("s-visitor-pct").value),
            distributor_commission_pct: Number(document.getElementById("s-dist-pct").value),
            checkup_interval_days: Number(document.getElementById("s-checkup-days").value),
          },
        });
        toast("تنظیمات ذخیره شد.");
      } catch (e) {
        msg.textContent = e.message;
      }
    });
  }

  // ---------------- users ----------------
  let usersCache = [];

  function updateUserFormVisibility() {
    const role = document.getElementById("u-role").value;
    document.getElementById("u-telegram-field").style.display = role === "scout" ? "" : "none";
    document.getElementById("u-username-field").style.display = role === "scout" ? "none" : "";
    document.getElementById("u-password-field").style.display = role === "scout" ? "none" : "";
    document.getElementById("u-subteam-field").style.display = role === "visitor" ? "" : "none";
  }

  async function initUsers() {
    document.getElementById("u-role").addEventListener("change", updateUserFormVisibility);
    updateUserFormVisibility();

    document.getElementById("add-user-btn").addEventListener("click", async () => {
      const errEl = document.getElementById("user-error");
      errEl.textContent = "";
      const role = document.getElementById("u-role").value;
      const payload = {
        role,
        full_name: document.getElementById("u-name").value.trim(),
        phone: document.getElementById("u-phone").value.trim() || null,
      };
      if (role === "scout") {
        payload.telegram_id = Number(document.getElementById("u-telegram").value) || null;
      } else {
        payload.username = document.getElementById("u-username").value.trim();
        payload.password = document.getElementById("u-password").value;
        if (role === "visitor") {
          payload.visitor_subteam = Number(document.getElementById("u-subteam").value) || null;
        }
      }
      try {
        await api("/users", { method: "POST", body: payload });
        toast("کاربر افزوده شد.");
        ["u-name", "u-phone", "u-telegram", "u-username", "u-password"].forEach((id) => (document.getElementById(id).value = ""));
        await renderUsers();
      } catch (e) {
        errEl.textContent = e.message;
      }
    });

    await renderUsers();
  }

  const ROLE_LABELS = { admin: "ادمین", scout: "در‌آور", visitor: "ویزیتور", distributor: "پخش" };

  async function renderUsers() {
    usersCache = await api("/users");
    document.getElementById("users-body").innerHTML = usersCache
      .map(
        (u) => `<tr>
        <td>${u.full_name}</td>
        <td>${ROLE_LABELS[u.role] || u.role}</td>
        <td class="num">${u.username || u.telegram_id || "—"}</td>
        <td>${u.visitor_subteam || "—"}</td>
      </tr>`
      )
      .join("");
  }

  // ---------------- commissions ----------------
  async function initCommissions() {
    if (!usersCache.length) usersCache = await api("/users");
    document.getElementById("comm-user-filter").innerHTML +=
      usersCache.map((u) => `<option value="${u.id}">${u.full_name}</option>`).join("");
    document.getElementById("comm-user-filter").addEventListener("change", renderCommissions);
    await renderCommissions();
  }

  async function renderCommissions() {
    const userId = document.getElementById("comm-user-filter").value;
    const entries = await api(`/commissions${userId ? `?user_id=${userId}` : ""}`);
    const userName = (id) => usersCache.find((u) => u.id === id)?.full_name || `#${id}`;
    document.getElementById("commissions-body").innerHTML = entries.length
      ? entries
          .map(
            (e) => `<tr>
        <td>${userName(e.user_id)}</td>
        <td>${ROLE_LABELS[e.role] || e.role}</td>
        <td class="num">#${e.shop_id}</td>
        <td class="num">${Number(e.amount).toLocaleString("en-US")}</td>
        <td>${formatJalaliDateTime(e.computed_at)}</td>
      </tr>`
          )
          .join("")
      : `<tr><td colspan="5" class="empty-state">هنوز کمیسیونی ثبت نشده.</td></tr>`;
  }

  // ---------------- boot ----------------
  (async function boot() {
    await initDashboard();
    await initRegions();
    await initSchedule();
    await initSettings();
    await initUsers();
    await initCommissions();
  })();
})();
