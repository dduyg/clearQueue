(() => {
  const state = {
    cases: [],
    cutoffs: [0, 0, 0],
    selectedId: null,
  };

  const el = (sel) => document.querySelector(sel);
  const els = (sel) => Array.from(document.querySelectorAll(sel));

  function priorityBand(score) {
    if (score >= 75) return "high";
    if (score >= 50) return "medium";
    return "low"; // covers 0-49; queue rows further distinguish visually by score number
  }

  // Note: bands for coloring follow the same thresholds as recommended_action
  // (>=75 review today, >=50 review this week) so color and text never disagree.

  function showToast(msg) {
    const t = el("#toast");
    t.textContent = msg;
    t.classList.remove("hidden");
    setTimeout(() => t.classList.add("hidden"), 2600);
  }

  // ---------------- Data loading ----------------

  let pendingFile = null;

  async function handleFileSelected(file) {
    if (!file.name.toLowerCase().endsWith(".csv")) {
      showToast("Please choose a .csv file");
      return;
    }
    pendingFile = file;
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch("/api/csv/preview", { method: "POST", body: form });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        showToast(err.detail || "Could not read that file");
        return;
      }
      const preview = await res.json();
      if (preview.needs_mapping) {
        openMappingModal(preview);
      } else {
        scoreFile(file, null);
      }
    } catch (e) {
      showToast("Upload failed — is the backend running?");
    }
  }

  async function scoreFile(file, mapping) {
    const form = new FormData();
    form.append("file", file);
    if (mapping) form.append("mapping", JSON.stringify(mapping));
    try {
      const res = await fetch("/api/score", { method: "POST", body: form });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        showToast(err.detail || "Could not score that file");
        return;
      }
      const data = await res.json();
      state.cases = data.cases;
      state.cutoffs = data.percentile_cutoffs;
      state.selectedId = data.cases.length ? data.cases[0].case_id : null;
      onDataLoaded();
    } catch (e) {
      showToast("Upload failed — is the backend running?");
    }
  }

  // ---------------- Column mapping modal ----------------

  const CANONICAL_LABELS = {
    case_id: "Case ID",
    category: "Category",
    amount: "Amount",
    days_open: "Days open",
    missing_information: "Missing information",
    urgency: "Urgency",
    dependencies: "Dependencies",
  };

  function openMappingModal(preview) {
    const container = el("#mapping-fields");
    container.innerHTML = preview.canonical_fields.map((field) => {
      const required = field === "case_id";
      const suggested = preview.suggested_mapping[field] || "";
      const options = [`<option value="">${required ? "— choose a column —" : "Not present"}</option>`]
        .concat(preview.headers.map((h) =>
          `<option value="${escapeHtml(h)}" ${h === suggested ? "selected" : ""}>${escapeHtml(h)}</option>`
        )).join("");
      return `
        <div class="mapping-row">
          <label>${CANONICAL_LABELS[field]}${required ? ' <span class="req">*</span>' : ""}</label>
          <select data-field="${field}">${options}</select>
        </div>`;
    }).join("");
    el("#mapping-modal").classList.remove("hidden");
  }

  function closeMappingModal() {
    el("#mapping-modal").classList.add("hidden");
    pendingFile = null;
  }

  function confirmMapping() {
    const mapping = {};
    els("#mapping-fields select").forEach((sel) => {
      if (sel.value) mapping[sel.dataset.field] = sel.value;
    });
    if (!mapping.case_id) {
      showToast("You must choose a column for Case ID");
      return;
    }
    const file = pendingFile;
    el("#mapping-modal").classList.add("hidden");
    scoreFile(file, mapping);
    pendingFile = null;
  }

  async function loadSample(datasetId) {
    try {
      const res = await fetch(`/api/sample/${datasetId}`);
      if (!res.ok) throw new Error("not found");
      const blob = await res.blob();
      const file = new File([blob], `${datasetId}.csv`, { type: "text/csv" });
      await scoreFile(file, null);
    } catch (e) {
      showToast("Could not load sample data");
    }
  }

  async function populateSampleMenu() {
    try {
      const res = await fetch("/api/samples");
      const datasets = await res.json();
      const menu = el("#sample-menu");
      menu.innerHTML = datasets.map((d) =>
        `<button class="sample-menu-item" data-id="${d.id}">${escapeHtml(d.label)}</button>`
      ).join("");
      els(".sample-menu-item").forEach((btn) => {
        btn.addEventListener("click", () => {
          menu.classList.add("hidden");
          loadSample(btn.dataset.id);
        });
      });
    } catch (e) { /* upload still works without the menu */ }
  }

  function onDataLoaded() {
    el("#empty-state").classList.add("hidden");
    els(".view").forEach((v) => v.classList.remove("hidden"));
    el("#view-overview").classList.add("hidden");
    el("#view-mlcompare").classList.add("hidden");
    el("#view-responsible").classList.add("hidden");
    renderQueue();
    renderDetail();
    renderOverview();
  }

  // ---------------- Work queue ----------------

  function renderQueue() {
    const list = el("#queue-list");
    el("#queue-count").textContent = `${state.cases.length} cases`;
    list.innerHTML = "";
    state.cases.forEach((c) => {
      const band = priorityBand(c.priority.score);
      const row = document.createElement("div");
      row.className = `queue-row priority-${band}` + (c.case_id === state.selectedId ? " selected" : "");
      row.innerHTML = `
        <div class="queue-score">${c.priority.score}</div>
        <div class="queue-row-main">
          <div class="queue-row-id">${escapeHtml(c.case_id)}${c.category ? " · " + escapeHtml(c.category) : ""}</div>
          <div class="queue-row-action">${escapeHtml(c.priority.recommended_action)}</div>
        </div>
      `;
      row.addEventListener("click", () => {
        state.selectedId = c.case_id;
        renderQueue();
        renderDetail();
      });
      list.appendChild(row);
    });
  }

  function escapeHtml(s) {
    return String(s ?? "").replace(/[&<>"']/g, (m) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    })[m]);
  }

  // ---------------- Detail panel ----------------

  function renderDetail() {
    const panel = el("#detail-panel");
    const c = state.cases.find((c) => c.case_id === state.selectedId);
    if (!c) {
      panel.innerHTML = `<div class="detail-empty muted">Select a case to see its full explanation.</div>`;
      return;
    }
    const band = priorityBand(c.priority.score);

    const factorsHtml = c.priority.factors.map((f) => {
      const pct = f.max_points ? Math.round((f.points / f.max_points) * 100) : 0;
      return `
        <div class="factor-row ${f.available ? "" : "factor-unavailable"}">
          <div class="factor-row-top">
            <span class="factor-name">${escapeHtml(f.label)}</span>
            <span class="factor-points">${f.available ? `+${f.points}` : "n/a"} / ${f.max_points}</span>
          </div>
          <div class="factor-bar-track"><div class="factor-bar-fill" style="width:${pct}%"></div></div>
          <div class="factor-detail">${escapeHtml(f.detail)}</div>
        </div>`;
    }).join("");

    const reductionsHtml = c.priority.reduction_suggestions.map((s) => `<li>${escapeHtml(s)}</li>`).join("");

    panel.innerHTML = `
      <div class="detail-head">
        <div>
          <div class="detail-id">${escapeHtml(c.case_id)}</div>
          <div class="detail-category">${escapeHtml(c.category || "Uncategorized")}</div>
        </div>
        <div class="detail-score-block">
          <div class="detail-score priority-${band}">${c.priority.score}</div>
          <div class="detail-action">${escapeHtml(c.priority.recommended_action)}</div>
          <button class="btn btn-ghost btn-small" id="export-case-pdf" style="margin-top:10px;">Export PDF</button>
        </div>
      </div>

      <div class="factor-list">${factorsHtml}</div>

      <div class="reduction-box">
        <h4>What would reduce this score</h4>
        <ul>${reductionsHtml}</ul>
      </div>

      <div class="sim-block">
        <h4>What if… (score simulation)</h4>
        ${renderSimControls(c)}
        <div class="sim-result hidden" id="sim-result">
          <span class="sim-result-label">Simulated score</span>
          <span class="sim-result-score" id="sim-score"></span>
          <span class="sim-result-delta" id="sim-delta"></span>
        </div>
      </div>
    `;

    bindSimControls(c);
    el("#export-case-pdf").addEventListener("click", () => exportCasePdf(c));
  }

  async function downloadPdf(url, body, fallbackName) {
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        showToast(err.detail || "Could not generate PDF");
        return;
      }
      const blob = await res.blob();
      const disposition = res.headers.get("Content-Disposition") || "";
      const match = disposition.match(/filename="(.+)"/);
      const filename = match ? match[1] : fallbackName;
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      link.click();
      URL.revokeObjectURL(link.href);
    } catch (e) {
      showToast("PDF export failed");
    }
  }

  function exportCasePdf(c) {
    downloadPdf("/api/report/case", { case: c }, `clearqueue_${c.case_id}.pdf`);
  }

  function exportQueuePdf() {
    if (!state.cases.length) return;
    downloadPdf("/api/report/queue", { cases: state.cases }, "clearqueue_work_queue.pdf");
  }

  function renderSimControls(c) {
    const amount = c.amount ?? 0;
    const daysOpen = c.days_open ?? 0;
    const missing = c.missing_information;
    const urgency = (c.urgency || "medium").toLowerCase();
    const deps = c.dependencies ?? 0;

    return `
      <div class="sim-row">
        <label for="sim-amount">Amount (€)</label>
        <input type="range" id="sim-amount" min="0" max="100000" step="500" value="${amount}">
        <span class="sim-val" id="sim-amount-val">€${Math.round(amount).toLocaleString()}</span>
      </div>
      <div class="sim-row">
        <label for="sim-days">Days open</label>
        <input type="range" id="sim-days" min="0" max="90" step="1" value="${daysOpen}">
        <span class="sim-val" id="sim-days-val">${Math.round(daysOpen)}</span>
      </div>
      <div class="sim-row">
        <label for="sim-urgency">Urgency</label>
        <select id="sim-urgency">
          <option value="low" ${urgency === "low" ? "selected" : ""}>Low</option>
          <option value="medium" ${urgency === "medium" ? "selected" : ""}>Medium</option>
          <option value="high" ${urgency === "high" ? "selected" : ""}>High</option>
        </select>
        <span></span>
      </div>
      <div class="sim-row">
        <label for="sim-deps">Dependencies</label>
        <input type="range" id="sim-deps" min="0" max="5" step="1" value="${deps}">
        <span class="sim-val" id="sim-deps-val">${Math.round(deps)}</span>
      </div>
      <div class="sim-row">
        <label for="sim-missing">Missing info</label>
        <div class="sim-toggle">
          <input type="checkbox" id="sim-missing" ${missing ? "checked" : ""}>
          <span class="muted">required documentation missing</span>
        </div>
        <span></span>
      </div>
    `;
  }

  let simTimer = null;
  function bindSimControls(c) {
    const inputs = ["#sim-amount", "#sim-days", "#sim-urgency", "#sim-deps", "#sim-missing"];
    inputs.forEach((sel) => {
      const node = el(sel);
      if (!node) return;
      node.addEventListener("input", () => {
        el("#sim-amount-val").textContent = `€${Number(el("#sim-amount").value).toLocaleString()}`;
        el("#sim-days-val").textContent = el("#sim-days").value;
        el("#sim-deps-val").textContent = el("#sim-deps").value;
        clearTimeout(simTimer);
        simTimer = setTimeout(() => runSimulation(c), 150);
      });
    });
  }

  async function runSimulation(original) {
    const payload = {
      case: {
        amount: Number(el("#sim-amount").value),
        days_open: Number(el("#sim-days").value),
        urgency: el("#sim-urgency").value,
        dependencies: Number(el("#sim-deps").value),
        missing_information: el("#sim-missing").checked,
      },
      percentile_cutoffs: state.cutoffs,
    };
    try {
      const res = await fetch("/api/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = await res.json();
      const resultBox = el("#sim-result");
      resultBox.classList.remove("hidden");
      el("#sim-score").textContent = result.score;
      el("#sim-score").className = "sim-result-score";
      const delta = result.score - original.priority.score;
      const deltaEl = el("#sim-delta");
      deltaEl.textContent = delta === 0 ? "no change" : (delta > 0 ? `+${delta}` : `${delta}`);
      deltaEl.className = "sim-result-delta " + (delta > 0 ? "up" : delta < 0 ? "down" : "");
    } catch (e) {
      showToast("Simulation failed");
    }
  }

  // ---------------- Overview ----------------

  function renderOverview() {
    const cases = state.cases;
    const n = cases.length;
    const high = cases.filter((c) => c.priority.score >= 75).length;
    const medium = cases.filter((c) => c.priority.score >= 50 && c.priority.score < 75).length;
    const low = n - high - medium;
    const avgAge = n ? cases.reduce((s, c) => s + (c.days_open || 0), 0) / n : 0;
    const avgScore = n ? cases.reduce((s, c) => s + c.priority.score, 0) / n : 0;
    const over30 = cases.filter((c) => (c.days_open || 0) > 30).length;
    const missing = cases.filter((c) => c.priority.factors.find(f => f.key === "missing_info")?.points > 0).length;

    el("#stat-cards").innerHTML = `
      ${statCard(n, "Total cases", "")}
      ${statCard(high, "High priority", "high")}
      ${statCard(medium, "Medium priority", "medium")}
      ${statCard(low, "Low priority", "low")}
      ${statCard(avgAge.toFixed(1), "Average case age (days)", "")}
      ${statCard(avgScore.toFixed(1), "Average score", "")}
      ${statCard(over30, "Cases open > 30 days", "")}
      ${statCard(missing, "Missing information", "")}
    `;

    renderHBar("#chart-priority", [
      { label: "High (≥75)", value: high, color: "var(--high)" },
      { label: "Medium (50–74)", value: medium, color: "var(--medium)" },
      { label: "Low (<50)", value: low, color: "var(--low)" },
    ]);

    const byCategory = {};
    cases.forEach((c) => { const k = c.category || "Uncategorized"; byCategory[k] = (byCategory[k] || 0) + 1; });
    renderHBar("#chart-category", Object.entries(byCategory).map(([label, value]) => ({ label, value })));

    const factorTotals = {};
    cases.forEach((c) => c.priority.factors.forEach((f) => {
      factorTotals[f.label] = (factorTotals[f.label] || 0) + f.points;
    }));
    renderHBar("#chart-factors", Object.entries(factorTotals)
      .map(([label, value]) => ({ label, value: Math.round(value) }))
      .sort((a, b) => b.value - a.value));

    const ageBuckets = [
      { label: "0–4 days", value: cases.filter(c => (c.days_open || 0) < 5).length },
      { label: "5–14 days", value: cases.filter(c => (c.days_open || 0) >= 5 && c.days_open < 15).length },
      { label: "15–29 days", value: cases.filter(c => (c.days_open || 0) >= 15 && c.days_open < 30).length },
      { label: "30+ days", value: cases.filter(c => (c.days_open || 0) >= 30).length },
    ];
    renderHBar("#chart-age", ageBuckets);
  }

  function statCard(value, label, band) {
    return `<div class="stat-card ${band}"><div class="stat-value">${value}</div><div class="stat-label">${label}</div></div>`;
  }

  function renderHBar(selector, items) {
    const max = Math.max(1, ...items.map((i) => i.value));
    el(selector).innerHTML = items.map((i) => `
      <div class="hbar-row">
        <div class="hbar-label">${escapeHtml(i.label)}</div>
        <div class="hbar-track"><div class="hbar-fill" style="width:${(i.value / max) * 100}%; ${i.color ? `background:${i.color}` : ""}"></div></div>
        <div class="hbar-value">${i.value}</div>
      </div>
    `).join("");
  }

  // ---------------- Responsible scoring ----------------

  async function loadFairness() {
    try {
      const res = await fetch("/api/fairness");
      const data = await res.json();
      el("#excluded-list").innerHTML = data.excluded_attributes.map((a) => `<li>${escapeHtml(a)}</li>`).join("");
    } catch (e) { /* static page still works without this */ }
  }

  // ---------------- ML comparison ----------------

  async function runMlComparison() {
    const results = el("#mlcompare-results");
    results.innerHTML = `<div class="mlcompare-loading">Training comparison model and computing SHAP values…</div>`;
    try {
      const res = await fetch("/api/ml_compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cases: state.cases }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        results.innerHTML = `<div class="mlcompare-error">${escapeHtml(err.detail || "Comparison failed")}</div>`;
        return;
      }
      const data = await res.json();
      renderMlComparison(data);
    } catch (e) {
      results.innerHTML = `<div class="mlcompare-error">Comparison failed — is the backend running?</div>`;
    }
  }

  function renderMlComparison(data) {
    const results = el("#mlcompare-results");
    const rows = data.cases.map((c) => {
      const diffClass = c.difference > 0 ? "diff-up" : c.difference < 0 ? "diff-down" : "num";
      const topFactors = c.shap_contributions.slice(0, 2)
        .map((f) => `${f.label} (${f.shap_value > 0 ? "+" : ""}${f.shap_value})`).join(", ");
      return `
        <tr>
          <td>${escapeHtml(c.case_id)}</td>
          <td class="num">${c.rule_based_score}</td>
          <td class="num">${c.ml_predicted_score}</td>
          <td class="${diffClass}">${c.difference > 0 ? "+" : ""}${c.difference}</td>
          <td>${escapeHtml(topFactors)}</td>
        </tr>`;
    }).join("");

    results.innerHTML = `
      <div class="mlcompare-note">${escapeHtml(data.note)}</div>
      <div class="chart-block" style="margin-bottom:24px;">
        <h3>Global SHAP feature importance</h3>
        <div id="chart-shap-importance" class="hbar-chart"></div>
      </div>
      <table class="mlcompare-table">
        <thead>
          <tr><th>Case</th><th>Rule score</th><th>ML score</th><th>Difference</th><th>Top SHAP factors</th></tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    `;
    renderHBar("#chart-shap-importance", data.global_feature_importance.map((f) => ({
      label: f.label, value: f.importance_pct,
    })));
  }

  // ---------------- Nav ----------------

  function switchView(view) {
    els(".tab").forEach((t) => t.classList.toggle("active", t.dataset.view === view));
    if (!state.cases.length && view !== "responsible") {
      // still allow browsing responsible-scoring page with no data loaded
    }
    ["queue", "overview", "mlcompare", "responsible"].forEach((v) => {
      const section = el(`#view-${v}`);
      if (!section) return;
      const shouldShow = v === view && (state.cases.length || v === "responsible");
      section.classList.toggle("hidden", !shouldShow);
    });
    if (view === "responsible" && !state.cases.length) {
      el("#empty-state").classList.add("hidden");
    } else if (!state.cases.length) {
      el("#empty-state").classList.remove("hidden");
    }
  }

  // ---------------- Wire up ----------------

  els(".tab").forEach((t) => t.addEventListener("click", () => switchView(t.dataset.view)));
  el("#csv-input").addEventListener("change", (e) => {
    if (e.target.files[0]) handleFileSelected(e.target.files[0]);
  });
  el("#sample-menu-btn").addEventListener("click", (e) => {
    e.stopPropagation();
    el("#sample-menu").classList.toggle("hidden");
  });
  document.addEventListener("click", () => el("#sample-menu").classList.add("hidden"));
  el("#sample-btn-2").addEventListener("click", () => loadSample("insurance"));
  el("#mapping-cancel").addEventListener("click", closeMappingModal);
  el("#mapping-confirm").addEventListener("click", confirmMapping);
  el("#export-queue-pdf").addEventListener("click", exportQueuePdf);
  el("#run-ml-compare").addEventListener("click", runMlComparison);

  loadFairness();
  populateSampleMenu();
})();
