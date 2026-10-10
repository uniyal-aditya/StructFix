/**
 * StructFix — Interactive Frontend Application Logic (Vanilla JS)
 */

document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const jsonInput = document.getElementById("json-input");
  const schemaInput = document.getElementById("schema-input");
  const repairBtn = document.getElementById("repair-submit-btn");
  const btnSpinner = document.getElementById("btn-spinner");
  const btnText = document.getElementById("btn-text");
  const clearBtn = document.getElementById("clear-input-btn");
  const copyBtn = document.getElementById("copy-result-btn");
  const copyBtnText = document.getElementById("copy-btn-text");
  const downloadBtn = document.getElementById("download-result-btn");
  const presetsContainer = document.getElementById("presets-container");

  const enableAiToggle = document.getElementById("enable-ai-toggle");
  const modelSelect = document.getElementById("model-select");
  const retriesSelect = document.getElementById("retries-select");

  const ollamaDot = document.getElementById("ollama-dot");
  const ollamaStatusText = document.getElementById("ollama-status-text");
  const diagOllamaStatus = document.getElementById("diag-ollama-status");

  // Telemetry & Alerts
  const statusPill = document.getElementById("status-pill");
  const tierPill = document.getElementById("tier-pill");
  const aiCallsPill = document.getElementById("ai-calls-pill");
  const latencyPill = document.getElementById("latency-pill");
  const jsonOutput = document.getElementById("json-output");

  const unrecoverableAlert = document.getElementById("unrecoverable-alert");
  const unrecoverableMessage = document.getElementById("unrecoverable-message");
  const validationErrorsAlert = document.getElementById("validation-errors-alert");
  const validationErrorsList = document.getElementById("validation-errors-list");
  const strategiesTagsContainer = document.getElementById("strategies-tags-container");
  const diagAttempts = document.getElementById("diag-attempts");

  let lastRepairedData = null;
  let examplesCache = [];

  // 1. Initial Health Check
  async function checkHealth() {
    try {
      const res = await fetch("/api/health");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      
      const ollama = data.ollama || {};
      if (ollama.reachable) {
        ollamaDot.className = "dot dot-online";
        ollamaStatusText.textContent = `Ollama Online (${ollama.configured_model || "qwen3:1.7b"})`;
        diagOllamaStatus.textContent = `Connected at ${ollama.base_url} (Found ${ollama.models ? ollama.models.length : 0} models)`;
        enableAiToggle.checked = true;
      } else {
        ollamaDot.className = "dot dot-offline";
        ollamaStatusText.textContent = "Ollama Offline (Tier 1 Active)";
        diagOllamaStatus.textContent = "Ollama server not detected at localhost:11434. Instant Tier 1 deterministic repairs are fully operational.";
        enableAiToggle.checked = false;
      }
    } catch (err) {
      ollamaDot.className = "dot dot-offline";
      ollamaStatusText.textContent = "Offline (Tier 1 Active)";
      diagOllamaStatus.textContent = `Health check info: ${err.message}`;
      enableAiToggle.checked = false;
    }
  }

  // 2. Fetch & Render Examples
  async function loadExamples() {
    try {
      const res = await fetch("/api/examples");
      if (!res.ok) throw new Error("Failed to load presets");
      const data = await res.json();
      examplesCache = data.examples || [];

      presetsContainer.innerHTML = "";
      examplesCache.forEach((ex, idx) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = `preset-btn ${idx === 1 ? "active" : ""}`;
        btn.textContent = ex.title;
        btn.title = ex.description;
        btn.addEventListener("click", () => selectExample(ex, btn));
        presetsContainer.appendChild(btn);
      });

      // Select fenced example by default if available
      if (examplesCache.length > 1) {
        selectExample(examplesCache[1], presetsContainer.children[1]);
      } else if (examplesCache.length > 0) {
        selectExample(examplesCache[0], presetsContainer.children[0]);
      }
    } catch (err) {
      presetsContainer.innerHTML = '<span class="preset-loading">Could not load presets</span>';
    }
  }

  function selectExample(example, targetBtn) {
    document.querySelectorAll(".preset-btn").forEach(b => b.classList.remove("active"));
    if (targetBtn) targetBtn.classList.add("active");

    jsonInput.value = example.input || "";
    schemaInput.value = example.schema ? JSON.stringify(example.schema, null, 2) : "";
    resetOutputState();
  }

  function resetOutputState() {
    statusPill.className = "status-pill status-ready";
    statusPill.textContent = "READY";
    tierPill.textContent = "-";
    aiCallsPill.textContent = "0";
    latencyPill.textContent = "-";
    unrecoverableAlert.style.display = "none";
    validationErrorsAlert.style.display = "none";
    strategiesTagsContainer.innerHTML = '<span class="diag-empty">None</span>';
    diagAttempts.textContent = "-";
    jsonOutput.textContent = "// Click 'Repair JSON' to process...";
    lastRepairedData = null;
  }

  // 3. Execute Repair
  async function executeRepair() {
    const rawInput = jsonInput.value;
    const rawSchema = schemaInput.value;

    if (!rawInput.trim()) {
      alert("Please enter malformed JSON or select a test fixture.");
      jsonInput.focus();
      return;
    }

    // Set Loading State
    repairBtn.disabled = true;
    btnSpinner.style.display = "inline-block";
    btnText.textContent = "Repairing...";
    unrecoverableAlert.style.display = "none";
    validationErrorsAlert.style.display = "none";

    const payload = {
      input: rawInput,
      schema: rawSchema.trim() ? rawSchema : null,
      model: modelSelect.value,
      enable_ai: enableAiToggle.checked,
      max_retries: parseInt(retriesSelect.value, 10),
    };

    try {
      const res = await fetch("/api/repair", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || `Server returned error ${res.status}`);
      }

      renderResult(data);
    } catch (err) {
      statusPill.className = "status-pill status-failed";
      statusPill.textContent = "ERROR";
      validationErrorsAlert.style.display = "block";
      validationErrorsList.innerHTML = "";
      const li = document.createElement("li");
      li.textContent = err.message;
      validationErrorsList.appendChild(li);
      jsonOutput.textContent = `// Error: ${err.message}`;
    } finally {
      repairBtn.disabled = false;
      btnSpinner.style.display = "none";
      btnText.textContent = "Repair JSON";
    }
  }

  function renderResult(result) {
    lastRepairedData = result.data;

    // Status Pill
    const status = (result.status || "failed").toLowerCase();
    if (status === "valid" || (result.is_valid && status !== "unrecoverable")) {
      statusPill.className = "status-pill status-valid";
      statusPill.textContent = "VALID";
    } else if (status === "unrecoverable") {
      statusPill.className = "status-pill status-unrecoverable";
      statusPill.textContent = "UNRECOVERABLE";
    } else {
      statusPill.className = "status-pill status-failed";
      statusPill.textContent = "FAILED";
    }

    // Tier
    if (result.tier_used === 0) {
      tierPill.textContent = "Tier 0 (Valid)";
    } else if (result.tier_used === 1) {
      tierPill.textContent = "Tier 1 (Deterministic)";
    } else if (result.tier_used === 2) {
      tierPill.textContent = `Tier 2 (AI - ${modelSelect.value})`;
    } else {
      tierPill.textContent = "None";
    }

    // Telemetry
    aiCallsPill.textContent = `${result.ai_calls || 0} call${result.ai_calls === 1 ? "" : "s"}`;
    latencyPill.textContent = `${result.latency_ms || 0} ms`;
    diagAttempts.textContent = `${result.attempts || 0} attempt(s)`;

    // Output JSON
    if (result.data !== null && result.data !== undefined) {
      jsonOutput.textContent = JSON.stringify(result.data, null, 2);
    } else {
      jsonOutput.textContent = "// Output could not be parsed into a valid structure.";
    }

    // Unrecoverable Alert
    if (result.unrecoverable_fields && result.unrecoverable_fields.length > 0) {
      unrecoverableAlert.style.display = "block";
      unrecoverableMessage.innerHTML = `Zero-hallucination policy applied: The following required field(s) were missing in the source and set to <code>null</code>: <strong>${result.unrecoverable_fields.join(", ")}</strong>`;
    } else {
      unrecoverableAlert.style.display = "none";
    }

    // Validation Errors Alert
    if (result.errors && result.errors.length > 0) {
      validationErrorsAlert.style.display = "block";
      validationErrorsList.innerHTML = "";
      result.errors.forEach(err => {
        const li = document.createElement("li");
        li.textContent = err;
        validationErrorsList.appendChild(li);
      });
    } else {
      validationErrorsAlert.style.display = "none";
    }

    // Strategies Tags
    strategiesTagsContainer.innerHTML = "";
    if (result.strategies_applied && result.strategies_applied.length > 0) {
      result.strategies_applied.forEach(strat => {
        const span = document.createElement("span");
        span.className = "diag-tag";
        span.textContent = strat;
        strategiesTagsContainer.appendChild(span);
      });
    } else {
      strategiesTagsContainer.innerHTML = '<span class="diag-empty">None</span>';
    }
  }

  // 4. Clipboard & Download
  copyBtn.addEventListener("click", async () => {
    const text = jsonOutput.textContent;
    if (!text || text.startsWith("//")) return;

    try {
      await navigator.clipboard.writeText(text);
      copyBtnText.textContent = "Copied!";
      setTimeout(() => { copyBtnText.textContent = "Copy JSON"; }, 1800);
    } catch (e) {
      // Fallback
      copyBtnText.textContent = "Copied";
      setTimeout(() => { copyBtnText.textContent = "Copy JSON"; }, 1800);
    }
  });

  downloadBtn.addEventListener("click", () => {
    const text = jsonOutput.textContent;
    if (!text || text.startsWith("//")) return;

    const blob = new Blob([text], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "repaired_output.json";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });

  clearBtn.addEventListener("click", () => {
    jsonInput.value = "";
    resetOutputState();
    jsonInput.focus();
  });

  // 5. Submit Event & Shortcut
  repairBtn.addEventListener("click", executeRepair);

  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      executeRepair();
    }
  });

  // Init
  checkHealth();
  loadExamples();
});
