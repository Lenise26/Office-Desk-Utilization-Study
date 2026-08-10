const state = {
  layouts: [],
  desks: [],
  selectedLayout: null,
};

const $ = (id) => document.getElementById(id);

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const payload = await response.json();
      message = payload.detail || message;
    } catch (_) {}
    throw new Error(message);
  }
  return response.json();
}

function showToast(message, isError = false) {
  const toast = $("toast");
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.classList.add("show");
  window.setTimeout(() => toast.classList.remove("show"), 2800);
}

function titleCase(value) {
  return String(value).replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatPercent(value) {
  return `${Number(value).toFixed(1)}%`;
}

function populateLayoutSelects() {
  const options = state.layouts
    .map((layout) => `<option value="${layout.id}">${escapeHtml(layout.name)}</option>`)
    .join("");
  $("layoutSelect").innerHTML = options;
  $("beforeLayout").innerHTML = options;
  $("afterLayout").innerHTML = options;

  if (state.layouts.length) {
    const latest = state.layouts[state.layouts.length - 1];
    $("layoutSelect").value = String(latest.id);
    state.selectedLayout = latest.id;
  }
  if (state.layouts.length >= 2) {
    $("beforeLayout").value = String(state.layouts[0].id);
    $("afterLayout").value = String(state.layouts[state.layouts.length - 1].id);
  }
}

function renderMetrics(data) {
  $("overallRate").textContent = formatPercent(data.overall_utilization_rate);
  $("observationCount").textContent = data.observations.toLocaleString();
  $("averageDuration").textContent = `${Math.round(data.average_occupied_duration_minutes)} min`;

  const lowest = [...data.zone_utilization].sort((a, b) => a.utilization_rate - b.utilization_rate)[0];
  $("lowestZone").textContent = lowest ? lowest.zone : "—";
  $("lowestZoneDetail").textContent = lowest ? `${formatPercent(lowest.utilization_rate)} utilization` : "No observations";
}

function renderZoneBars(items) {
  const container = $("zoneBars");
  if (!items.length) {
    container.innerHTML = '<div class="empty-state">No zone observations for this period.</div>';
    return;
  }
  container.innerHTML = items
    .sort((a, b) => b.utilization_rate - a.utilization_rate)
    .map((item) => `
      <div class="bar-item">
        <div class="bar-label">
          <strong>${escapeHtml(item.zone)}</strong>
          <small>${item.observations.toLocaleString()} observations</small>
        </div>
        <div class="bar-track" aria-hidden="true"><div class="bar-fill" style="width:${Math.min(100, item.utilization_rate)}%"></div></div>
        <div class="bar-value">${formatPercent(item.utilization_rate)}</div>
      </div>
    `).join("");
}

function renderPeaks(items) {
  const container = $("peakPeriods");
  if (!items.length) {
    container.innerHTML = '<div class="empty-state">No peak periods available.</div>';
    return;
  }
  container.innerHTML = items.map((item, index) => `
    <div class="rank-item">
      <span class="rank-number">${index + 1}</span>
      <div class="rank-main">
        <strong>${escapeHtml(titleCase(item.period))}</strong>
        <small>${item.observations.toLocaleString()} checks</small>
      </div>
      <span class="rank-rate">${formatPercent(item.utilization_rate)}</span>
    </div>
  `).join("");
}

function heatClass(rate) {
  if (rate >= 70) return "heat-4";
  if (rate >= 55) return "heat-3";
  if (rate >= 40) return "heat-2";
  if (rate >= 20) return "heat-1";
  return "heat-0";
}

function renderHeatmap(items) {
  const periods = ["morning", "midday", "afternoon", "late"];
  const zones = [...new Set(items.map((item) => item.zone))].sort();
  const lookup = new Map(items.map((item) => [`${item.zone}|${item.period}`, item]));
  const cells = [
    '<div class="heat-cell heat-header heat-label">Zone</div>',
    ...periods.map((period) => `<div class="heat-cell heat-header">${titleCase(period)}</div>`),
  ];
  for (const zone of zones) {
    cells.push(`<div class="heat-cell heat-label"><strong>${escapeHtml(zone)}</strong></div>`);
    for (const period of periods) {
      const item = lookup.get(`${zone}|${period}`) || { utilization_rate: 0, observations: 0 };
      cells.push(`<div class="heat-cell ${heatClass(item.utilization_rate)}" title="${item.observations} observations">${formatPercent(item.utilization_rate)}</div>`);
    }
  }
  $("heatmap").innerHTML = cells.join("");
}

function renderUnused(items) {
  const container = $("unusedAreas");
  if (!items.length) {
    container.innerHTML = `
      <div class="insight-item good">
        <div><strong>No zones below 35%</strong><small>All observed zones show meaningful use in this period.</small></div>
      </div>`;
    return;
  }
  container.innerHTML = items.map((item) => `
    <div class="insight-item warning">
      <div>
        <strong>${escapeHtml(item.zone)}</strong>
        <small>Consider layout, amenity proximity, or desk-type changes.</small>
      </div>
      <span class="rank-rate">${formatPercent(item.utilization_rate)}</span>
    </div>
  `).join("");
}

async function loadDashboard() {
  const layoutId = Number($("layoutSelect").value);
  const period = $("periodSelect").value;
  state.selectedLayout = layoutId;
  try {
    const data = await api(`/api/dashboard?layout_id=${layoutId}&period=${encodeURIComponent(period)}`);
    renderMetrics(data);
    renderZoneBars(data.zone_utilization);
    renderPeaks(data.peak_periods);
    renderHeatmap(data.heatmap);
    renderUnused(data.unused_areas);
    await loadDesks(layoutId);
  } catch (error) {
    showToast(error.message, true);
  }
}

async function loadComparison() {
  const before = Number($("beforeLayout").value);
  const after = Number($("afterLayout").value);
  if (!before || !after || before === after) {
    $("comparisonNarrative").textContent = "Choose two different layouts to compare.";
    $("comparisonRows").innerHTML = "";
    $("overallChange").textContent = "—";
    return;
  }
  try {
    const data = await api(`/api/compare?before_layout_id=${before}&after_layout_id=${after}`);
    const delta = data.overall_change_points;
    $("overallChange").textContent = `${delta > 0 ? "+" : ""}${delta.toFixed(1)} pts`;
    $("overallChange").className = delta >= 0 ? "delta-positive" : "delta-negative";
    $("comparisonNarrative").textContent = data.summary;
    $("comparisonRows").innerHTML = data.zone_changes.map((item) => `
      <div class="comparison-row">
        <strong>${escapeHtml(item.zone)}</strong>
        <div class="comparison-bars" title="Before ${item.before_rate}%, after ${item.after_rate}%">
          <div class="compare-track"><div class="compare-before" style="width:${Math.min(100, item.before_rate)}%"></div></div>
          <div class="compare-track"><div class="compare-after" style="width:${Math.min(100, item.after_rate)}%"></div></div>
        </div>
        <strong class="${item.change_points >= 0 ? "delta-positive" : "delta-negative"}">${item.change_points > 0 ? "+" : ""}${item.change_points.toFixed(1)} pts</strong>
      </div>
    `).join("");
  } catch (error) {
    showToast(error.message, true);
  }
}

async function loadDesks(layoutId) {
  try {
    state.desks = await api(`/api/desks?layout_id=${layoutId}`);
    $("deskSelect").innerHTML = state.desks.map((desk) => `
      <option value="${desk.id}">${escapeHtml(desk.desk_code)} · ${escapeHtml(desk.zone)} · ${escapeHtml(titleCase(desk.desk_type))}</option>
    `).join("");
    renderDeskContext();
  } catch (error) {
    showToast(error.message, true);
  }
}

function renderDeskContext() {
  const desk = state.desks.find((item) => item.id === Number($("deskSelect").value));
  if (!desk) {
    $("deskContext").textContent = "Desk details unavailable.";
    return;
  }
  $("deskContext").innerHTML = `<strong>${escapeHtml(desk.zone)}</strong> · ${escapeHtml(titleCase(desk.desk_type))}<br>Nearby facilities: ${desk.nearby_facilities.map(escapeHtml).join(", ") || "None listed"}`;
}

function setCurrentLocalTime() {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  $("observedAt").value = now.toISOString().slice(0, 16);
}

function openObservationDialog() {
  setCurrentLocalTime();
  $("observationDialog").showModal();
}

async function submitObservation(event) {
  event.preventDefault();
  const occupied = document.querySelector('input[name="occupied"]:checked').value === "true";
  const durationValue = $("durationSelect").value;
  const payload = {
    desk_id: Number($("deskSelect").value),
    observed_at: $("observedAt").value,
    occupied,
    approximate_duration_minutes: occupied && durationValue ? Number(durationValue) : null,
  };
  try {
    const result = await api("/api/observations", { method: "POST", body: JSON.stringify(payload) });
    $("observationDialog").close();
    showToast(`${result.desk_code}: observation saved`);
    await loadDashboard();
  } catch (error) {
    showToast(error.message, true);
  }
}

function bindEvents() {
  $("layoutSelect").addEventListener("change", loadDashboard);
  $("periodSelect").addEventListener("change", loadDashboard);
  $("beforeLayout").addEventListener("change", loadComparison);
  $("afterLayout").addEventListener("change", loadComparison);
  $("deskSelect").addEventListener("change", renderDeskContext);
  $("openObservation").addEventListener("click", openObservationDialog);
  $("closeObservation").addEventListener("click", () => $("observationDialog").close());
  $("cancelObservation").addEventListener("click", () => $("observationDialog").close());
  $("observationForm").addEventListener("submit", submitObservation);
  $("exportButton").addEventListener("click", () => {
    window.location.href = `/api/export.csv?layout_id=${state.selectedLayout}`;
  });

  document.querySelectorAll('input[name="occupied"]').forEach((radio) => {
    radio.addEventListener("change", () => {
      const occupied = document.querySelector('input[name="occupied"]:checked').value === "true";
      $("durationSelect").disabled = !occupied;
      if (!occupied) $("durationSelect").value = "";
    });
  });
}

async function init() {
  bindEvents();
  try {
    state.layouts = await api("/api/layouts");
    populateLayoutSelects();
    await Promise.all([loadDashboard(), loadComparison()]);
  } catch (error) {
    showToast(error.message, true);
  }
}

document.addEventListener("DOMContentLoaded", init);
