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

function shopMarker(shop) {
  const color = STATUS_COLORS[shop.status] || "#8b98a3";
  return L.circleMarker([shop.location_lat, shop.location_lng], {
    radius: 9,
    color: "#fff",
    weight: 2,
    fillColor: color,
    fillOpacity: 1,
  });
}

/** Renders shop pins on `map`, replacing any previous layer this function
 * added. Returns the new layer group so callers can remove it later. */
function renderShopLayer(map, previousLayer, shops, onPopupHtml) {
  if (previousLayer) map.removeLayer(previousLayer);
  const layer = L.layerGroup();
  for (const shop of shops) {
    const marker = shopMarker(shop);
    marker.bindPopup(onPopupHtml(shop));
    layer.addLayer(marker);
  }
  layer.addTo(map);
  return layer;
}
