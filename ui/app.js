/**
 * app.js — SentinelRAG Dashboard Logic
 * Gurugram University B.Tech Project 2026
 * Authors: Akshu Grewal · Ishantnu · Anish Singh Rawat
 *
 * Connects to: FastAPI api_server.py at http://localhost:8000
 */

'use strict';

// ─── CONFIG ──────────────────────────────────────────────────────────────────
const API_BASE = 'http://localhost:8000';
const WS_BASE  = 'ws://localhost:8000';

// ─── DOM REFS ─────────────────────────────────────────────────────────────────
const queryInput    = document.getElementById('query-input');
const btnAsk        = document.getElementById('btn-ask');
const charCount     = document.getElementById('char-count');
const answerCard    = document.getElementById('answer-card');
const answerBody    = document.getElementById('answer-body');
const answerBadges  = document.getElementById('answer-badges');
const skeletonWrap  = document.getElementById('skeleton-wrap');
const logDrawer     = document.getElementById('log-drawer');
const logHandle     = document.getElementById('log-handle');
const logHandleLabel= document.getElementById('log-handle-label');
const logContent    = document.getElementById('log-content');
const btnEval       = document.getElementById('btn-eval');
const evalResult    = document.getElementById('eval-result');
const btnRefresh    = document.getElementById('btn-refresh-status');
const toast         = document.getElementById('ingest-toast');
const toastMsg      = document.getElementById('toast-msg');

// Metric value elements
const valTtft      = document.getElementById('val-ttft');
const valTokensIn  = document.getElementById('val-tokens-in');
const valTokensOut = document.getElementById('val-tokens-out');
const valCost      = document.getElementById('val-cost');
const valRoute     = document.getElementById('val-route');
const valGrade     = document.getElementById('val-grade');

// Pipeline step badges (header)
const stepRetrieve = document.getElementById('step-retrieve');
const stepGrade    = document.getElementById('step-grade');
const stepGenerate = document.getElementById('step-generate');
const stepMeasure  = document.getElementById('step-measure');
const pipelineStatusText = document.getElementById('pipeline-status-text');

// Pipeline visualizer nodes
const pvRetrieve   = document.getElementById('pv-retrieve');
const pvGrade      = document.getElementById('pv-grade');
const pvGenerate   = document.getElementById('pv-generate');
const pvWeb        = document.getElementById('pv-web');
const pvForkYes    = document.getElementById('pv-fork-yes');
const pvForkNo     = document.getElementById('pv-fork-no');
const pvRetrieveSub= document.getElementById('pv-retrieve-sub');
const pvGradeSub   = document.getElementById('pv-grade-sub');
const pvRetrieveBadge = document.getElementById('pv-retrieve-badge');
const pvGradeBadge    = document.getElementById('pv-grade-badge');

// Gauge
const gaugeFill       = document.getElementById('gauge-fill');
const gaugeScoreText  = document.getElementById('gauge-score-text');

// Status
const statusOllama   = document.getElementById('status-ollama');
const statusChroma   = document.getElementById('status-chroma');
const statusPhoenix  = document.getElementById('status-phoenix');
const statusOllamaVal= document.getElementById('status-ollama-val');
const statusChromaVal= document.getElementById('status-chroma-val');
const statusPhoenixVal=document.getElementById('status-phoenix-val');


// ─── STATE ────────────────────────────────────────────────────────────────────
let isQuerying = false;
let queryHistory = JSON.parse(localStorage.getItem('sentinel_history') || '[]');


// ─── INIT ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  checkStatus();
  setupEventListeners();

  // Animate pipeline badge on load
  animateHeaderPipeline();
});

function animateHeaderPipeline() {
  const steps = [stepRetrieve, stepGrade, stepGenerate, stepMeasure];
  steps.forEach((s, i) => {
    s.classList.remove('active', 'done');
  });
  stepRetrieve.classList.add('active');

  let i = 1;
  const interval = setInterval(() => {
    steps[i - 1].classList.remove('active');
    steps[i - 1].classList.add('done');
    if (i < steps.length) {
      steps[i].classList.add('active');
      i++;
    } else {
      clearInterval(interval);
      // Reset after a pause
      setTimeout(() => {
        steps.forEach(s => s.classList.remove('active', 'done'));
        animateHeaderPipeline();
      }, 3000);
    }
  }, 700);
}


// ─── EVENT LISTENERS ──────────────────────────────────────────────────────────
function setupEventListeners() {
  // Char counter
  queryInput.addEventListener('input', () => {
    charCount.textContent = queryInput.value.length;
  });

  // Submit on Ctrl+Enter
  queryInput.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      submitQuery();
    }
  });

  // Ask button
  btnAsk.addEventListener('click', submitQuery);

  // Quick question buttons
  document.querySelectorAll('.quick-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      queryInput.value = btn.dataset.q;
      charCount.textContent = btn.dataset.q.length;
      submitQuery();
    });
  });

  // Log drawer toggle
  logHandle.addEventListener('click', toggleLogDrawer);

  // Eval button
  btnEval.addEventListener('click', runEval);

  // Refresh status
  btnRefresh.addEventListener('click', () => {
    btnRefresh.classList.add('spinning');
    checkStatus().finally(() => btnRefresh.classList.remove('spinning'));
  });
}


// ─── STATUS CHECK ─────────────────────────────────────────────────────────────
async function checkStatus() {
  setStatusChecking();
  try {
    const res  = await fetch(`${API_BASE}/status`, { signal: AbortSignal.timeout(5000) });
    const data = await res.json();

    setStatusItem(statusOllama, statusOllamaVal,
      data.ollama.ok,
      data.ollama.ok
        ? (data.ollama.models.length ? data.ollama.models[0] : 'Running')
        : 'Not running'
    );
    setStatusItem(statusChroma, statusChromaVal,
      data.chromadb.ok,
      data.chromadb.ok ? 'Ready' : 'Run ingest.py'
    );
    setStatusItem(statusPhoenix, statusPhoenixVal,
      data.phoenix.ok,
      data.phoenix.ok ? 'localhost:6006' : 'Not running'
    );

  } catch (err) {
    // API not running
    setStatusItem(statusOllama,  statusOllamaVal,  false, 'API offline');
    setStatusItem(statusChroma,  statusChromaVal,  false, 'API offline');
    setStatusItem(statusPhoenix, statusPhoenixVal, false, 'API offline');
  }
}

function setStatusChecking() {
  [statusOllama, statusChroma, statusPhoenix].forEach(el => {
    const dot = el.querySelector('.status-dot');
    dot.className = 'status-dot dot-checking';
  });
}

function setStatusItem(containerEl, valEl, isOk, text) {
  const dot = containerEl.querySelector('.status-dot');
  dot.className = `status-dot ${isOk ? 'dot-ok' : 'dot-err'}`;
  valEl.textContent = text;
}


// ─── QUERY ────────────────────────────────────────────────────────────────────
async function submitQuery() {
  const question = queryInput.value.trim();
  if (!question || isQuerying) return;

  isQuerying = true;
  setQueryLoading(true);
  clearPipelineViz();
  showSkeleton();
  openLogDrawer();
  clearLog();
  pipelineStatusText.textContent = 'Running pipeline…';

  // Animate header steps
  resetHeaderSteps();
  activateHeaderStep('retrieve');

  try {
    // Use WebSocket for streaming if available, else fallback to REST
    await runViaRest(question);
  } catch (err) {
    showAnswerError(err.message || 'Failed to reach API. Is api_server.py running?');
  } finally {
    isQuerying = false;
    setQueryLoading(false);
  }
}

async function runViaRest(question) {
  const res = await fetch(`${API_BASE}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
    signal: AbortSignal.timeout(120_000),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `HTTP ${res.status}`);
  }

  const data = await res.json();

  // Render node logs step-by-step with animation
  const logs = data.node_log || [];
  for (let i = 0; i < logs.length; i++) {
    await sleep(220);
    const log = logs[i];
    appendLogEntry(log);
    activatePipelineNode(log.node, log);

    // sync header steps
    if (log.node === 'retrieve')       activateHeaderStep('grade');
    else if (log.node === 'grade_relevance') activateHeaderStep('generate');
    else if (log.node === 'generate')  activateHeaderStep('measure');
  }

  await sleep(100);
  hideSkeleton();
  renderAnswer(data);
  renderMetrics(data);
  renderPipelineRoute(data.route, data.grade);

  // Save to history
  queryHistory.unshift({ question, answer: data.answer, ts: Date.now() });
  queryHistory = queryHistory.slice(0, 20);
  localStorage.setItem('sentinel_history', JSON.stringify(queryHistory));

  pipelineStatusText.textContent = `Done in ${data.elapsed_total}s`;
  doneHeaderSteps();
}


// ─── RENDER ANSWER ────────────────────────────────────────────────────────────
function renderAnswer(data) {
  answerBadges.innerHTML = '';

  const routeBadge = document.createElement('span');
  routeBadge.className = `badge ${data.route === 'web_search' ? 'badge-web' : 'badge-local'}`;
  routeBadge.textContent = data.route === 'web_search' ? '🌐 Web Fallback' : '📚 Local Docs';
  answerBadges.appendChild(routeBadge);

  const gradeBadge = document.createElement('span');
  gradeBadge.className = `badge ${data.grade === 'yes' ? 'badge-yes' : 'badge-no'}`;
  gradeBadge.textContent = data.grade === 'yes' ? '✓ Relevant' : '✗ Fell back';
  answerBadges.appendChild(gradeBadge);

  answerBody.innerHTML = '';
  const div = document.createElement('div');
  div.className = 'answer-text';
  div.textContent = data.answer;
  answerBody.appendChild(div);
}

function showAnswerError(msg) {
  hideSkeleton();
  answerBody.innerHTML = `
    <div class="answer-placeholder">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#f43f5e" stroke-width="1.5" opacity="0.6">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="8" x2="12" y2="12"/>
        <line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
      <p style="color:#f43f5e;font-size:13px;">${escapeHtml(msg)}</p>
    </div>
  `;
  pipelineStatusText.textContent = 'Error';
}


// ─── RENDER METRICS ──────────────────────────────────────────────────────────
function renderMetrics(data) {
  animateMetric(valTtft,      `${data.ttft}s`);
  animateMetric(valTokensIn,  `~${data.input_tokens}`);
  animateMetric(valTokensOut, `~${data.output_tokens}`);
  animateMetric(valCost,      `$${data.simulated_cost.toFixed(5)}`);
  animateMetric(valRoute,     data.route === 'web_search' ? 'Web' : 'Local');
  animateMetric(valGrade,     data.grade ? data.grade.toUpperCase() : '—');

  // Animate tile
  document.querySelectorAll('.metric-tile').forEach(t => {
    t.classList.remove('updated');
    void t.offsetWidth;
    t.classList.add('updated');
  });
}

function animateMetric(el, value) {
  el.style.opacity = '0';
  el.style.transform = 'translateY(4px)';
  setTimeout(() => {
    el.textContent = value;
    el.style.transition = 'opacity 0.3s, transform 0.3s';
    el.style.opacity = '1';
    el.style.transform = 'translateY(0)';
  }, 50);
}


// ─── PIPELINE VISUALIZER ─────────────────────────────────────────────────────
function clearPipelineViz() {
  [pvRetrieve, pvGrade, pvGenerate, pvWeb].forEach(n => {
    n.classList.remove('active', 'done', 'web-active');
  });
  [pvForkYes, pvForkNo].forEach(f => f.classList.remove('active'));
  pvRetrieveBadge.textContent = '';
  pvGradeBadge.textContent    = '';
  pvRetrieveSub.textContent   = 'ChromaDB k=3';
  pvGradeSub.textContent      = 'LLM relevance';
}

function activatePipelineNode(nodeName, logData) {
  if (nodeName === 'retrieve') {
    pvRetrieve.classList.add('active');
    if (logData.chunks) {
      pvRetrieveSub.textContent = `${logData.chunks.length} chunks`;
      pvRetrieveBadge.textContent = logData.chunks.length;
      pvRetrieveBadge.className  = 'pv-badge badge-local';
    }
  } else if (nodeName === 'grade_relevance') {
    pvRetrieve.classList.remove('active');
    pvRetrieve.classList.add('done');
    pvGrade.classList.add('active');
    const g = logData.grade;
    pvGradeSub.textContent      = g === 'yes' ? '✓ Relevant' : '✗ Irrelevant';
    pvGradeBadge.textContent    = g ? g.toUpperCase() : '';
    pvGradeBadge.className      = `pv-badge ${g === 'yes' ? 'badge-yes' : 'badge-no'}`;
  } else if (nodeName === 'web_search') {
    pvGrade.classList.remove('active');
    pvGrade.classList.add('done');
    pvForkNo.classList.add('active');
    pvWeb.classList.add('web-active');
  } else if (nodeName === 'generate') {
    pvGrade.classList.remove('active');
    pvGrade.classList.add('done');
    pvGenerate.classList.add('active');
    setTimeout(() => pvGenerate.classList.add('done'), 600);
  }
}

function renderPipelineRoute(route, grade) {
  if (grade === 'yes') {
    pvForkYes.classList.add('active');
    pvForkNo.classList.remove('active');
  } else {
    pvForkNo.classList.add('active');
    pvForkYes.classList.remove('active');
  }
}


// ─── HEADER PIPELINE STEPS ───────────────────────────────────────────────────
function resetHeaderSteps() {
  [stepRetrieve, stepGrade, stepGenerate, stepMeasure].forEach(s => {
    s.classList.remove('active', 'done');
  });
}
function activateHeaderStep(name) {
  const map = {
    retrieve: stepRetrieve,
    grade:    stepGrade,
    generate: stepGenerate,
    measure:  stepMeasure,
  };
  const el = map[name];
  if (!el) return;
  // Mark previous as done
  const all = [stepRetrieve, stepGrade, stepGenerate, stepMeasure];
  const idx = all.indexOf(el);
  all.slice(0, idx).forEach(s => { s.classList.remove('active'); s.classList.add('done'); });
  el.classList.add('active');
}
function doneHeaderSteps() {
  [stepRetrieve, stepGrade, stepGenerate, stepMeasure].forEach(s => {
    s.classList.remove('active');
    s.classList.add('done');
  });
}


// ─── SKELETON / LOADING ───────────────────────────────────────────────────────
function showSkeleton() {
  answerBody.style.display = 'none';
  skeletonWrap.style.display = 'block';
  answerBadges.innerHTML = '';
}
function hideSkeleton() {
  skeletonWrap.style.display = 'none';
  answerBody.style.display = 'block';
}
function setQueryLoading(on) {
  btnAsk.disabled = on;
  btnAsk.classList.toggle('loading', on);
  // Add/remove spinner
  let spinner = btnAsk.querySelector('.spinner');
  if (on && !spinner) {
    spinner = document.createElement('span');
    spinner.className = 'spinner';
    btnAsk.insertBefore(spinner, btnAsk.querySelector('.btn-label'));
  }
  if (!on && spinner) spinner.remove();
}


// ─── EXECUTION LOG ────────────────────────────────────────────────────────────
function clearLog() {
  logContent.innerHTML = '<div class="log-empty">Running pipeline…</div>';
}

function appendLogEntry(log) {
  // Remove empty placeholder
  const empty = logContent.querySelector('.log-empty');
  if (empty) empty.remove();

  const entry = document.createElement('div');
  entry.className = 'log-entry';
  entry.innerHTML = `
    <span class="log-node-badge badge-${log.node}">${log.node}</span>
    <span class="log-msg">${escapeHtml(log.message)}${log.time_ms ? ` · ${log.time_ms}ms` : ''}</span>
    <span class="log-time">${new Date().toLocaleTimeString()}</span>
  `;
  logContent.appendChild(entry);
  logContent.scrollTop = logContent.scrollHeight;
  logHandleLabel.textContent = `Execution Log (${logContent.querySelectorAll('.log-entry').length} steps)`;
}


// ─── LOG DRAWER ───────────────────────────────────────────────────────────────
function openLogDrawer()  { logDrawer.classList.add('open'); }
function closeLogDrawer() { logDrawer.classList.remove('open'); }
function toggleLogDrawer() {
  logDrawer.classList.toggle('open');
}


// ─── EVAL GATE ────────────────────────────────────────────────────────────────
async function runEval() {
  if (btnEval.disabled) return;
  btnEval.disabled = true;
  btnEval.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="animation:spin 0.8s linear infinite"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg> Running RAGAS (be patient…)`;
  evalResult.style.display = 'none';

  // Reset gauge
  animateGauge(0);

  try {
    const res  = await fetch(`${API_BASE}/eval`, { signal: AbortSignal.timeout(900_000) });
    const data = await res.json();

    if (data.error) throw new Error(data.error);

    const score  = data.score || 0;
    const passed = data.passed;

    animateGauge(score);

    evalResult.className = `eval-result ${passed ? 'pass' : 'fail'}`;
    evalResult.textContent = passed
      ? `✅ PASS — Faithfulness ${score.toFixed(4)} ≥ 0.85 — CI Gate: OPEN`
      : `❌ FAIL — Faithfulness ${score.toFixed(4)} < 0.85 — CI Gate: BLOCKED`;

    showToast(
      passed ? `✅ Evaluation PASSED! Score: ${score.toFixed(4)}` : `❌ Evaluation FAILED. Score: ${score.toFixed(4)}`
    );

  } catch (err) {
    evalResult.className = 'eval-result fail';
    evalResult.textContent = `⚠️ Error: ${err.message}`;
    evalResult.style.display = 'block';
  } finally {
    btnEval.disabled = false;
    btnEval.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
      Run Evaluation Gate
    `;
  }
}

function animateGauge(score) {
  const FULL_ARC = 251.2; // circumference of the semi-circle path
  const target   = Math.min(Math.max(score, 0), 1);

  gaugeScoreText.textContent = score === 0 ? '—' : score.toFixed(3);

  // Animate dasharray
  const targetDash = target * FULL_ARC;
  let current = 0;
  const duration = 1200;
  const start = performance.now();

  function tick(now) {
    const t = Math.min((now - start) / duration, 1);
    const eased = t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
    const dash = eased * targetDash;
    gaugeFill.setAttribute('stroke-dasharray', `${dash.toFixed(1)} ${FULL_ARC}`);
    gaugeScoreText.textContent = (eased * target).toFixed(3);
    if (t < 1) requestAnimationFrame(tick);
    else gaugeScoreText.textContent = score === 0 ? '—' : score.toFixed(3);
  }
  requestAnimationFrame(tick);
}


// ─── TOAST ────────────────────────────────────────────────────────────────────
function showToast(msg, duration = 4000) {
  toastMsg.textContent = msg;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), duration);
}


// ─── UTIL ─────────────────────────────────────────────────────────────────────
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function escapeHtml(str = '') {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}


// ─── AUTO STATUS POLL ─────────────────────────────────────────────────────────
// Re-check status every 30s
setInterval(checkStatus, 30_000);
