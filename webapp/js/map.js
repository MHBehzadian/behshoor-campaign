const ZANJAN_CENTER = [36.6736, 48.4787];

const STATUS_COLORS = {
  registered: "#8b98a3",
  awaiting_threshold: "#8b98a3",
  queued_for_pack: "#3E6491",
  pack_delivered: "#2F6F62",
  order1_pending_delivery: "#A9761F",
  order1_done: "#2F6F62",
  order2_pending_delivery: "#A9761F",
  steady_customer: "#2F6F62",
  dropped: "#AE4E37",
};

function createMap(elementId, { center = ZANJAN_CENTER, zoom = 13 } = {}) {
  const map = L.map(elementId).setView(center, zoom);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);
  return map;
}

// Shop statuses where the visitor still owes this shop a follow-up visit —
// used to pulse the marker so it stands out from shops just sitting there.
const NEEDS_FOLLOWUP_STATUSES = ["pack_delivered", "order1_done"];

function shopMarker(shop, { blink = false } = {}) {
  const color = STATUS_COLORS[shop.status] || "#8b98a3";
  return L.circleMarker([shop.location_lat, shop.location_lng], {
    radius: blink ? 11 : 9,
    color: "#fff",
    weight: 2,
    fillColor: color,
    fillOpacity: 1,
    className: blink ? "blink-marker" : "",
  });
}

/** Renders shop pins on `map`, replacing any previous layer this function
 * added. Returns the new layer group so callers can remove it later.
 * `isUrgent(shop)` — when given, shops it returns true for get a pulsing
 * marker instead of a plain one; defaults to NEEDS_FOLLOWUP_STATUSES. */
function renderShopLayer(map, previousLayer, shops, onPopupHtml, isUrgent) {
  if (previousLayer) map.removeLayer(previousLayer);
  const urgentCheck = isUrgent || ((s) => NEEDS_FOLLOWUP_STATUSES.includes(s.status));
  const layer = L.layerGroup();
  for (const shop of shops) {
    const marker = shopMarker(shop, { blink: urgentCheck(shop) });
    marker.bindPopup(onPopupHtml(shop));
    layer.addLayer(marker);
  }
  layer.addTo(map);
  return layer;
}

/** Draws every region that has a saved boundary; `targetRegionId` (today's
 * distribution region, if any) gets a stronger highlight than the rest.
 * Returns the layer group so callers can toggle it on/off. */
function renderRegionBoundaries(map, regions, targetRegionId) {
  const layer = L.layerGroup();
  for (const region of regions) {
    if (!region.boundary_geojson) continue;
    const isTarget = region.id === targetRegionId;
    const poly = L.geoJSON(region.boundary_geojson, {
      style: {
        color: isTarget ? "#A9761F" : "#3E6491",
        weight: isTarget ? 3 : 1.5,
        fillOpacity: isTarget ? 0.22 : 0.05,
        fillColor: isTarget ? "#A9761F" : "#3E6491",
        dashArray: isTarget ? null : "4 4",
      },
    });
    poly.bindTooltip(region.name, { sticky: true });
    layer.addLayer(poly);
  }
  layer.addTo(map);
  return layer;
}
