/**
 * Intelli-Credit — Frontend Logic (v2.0)
 *
 * Uses SVG icons from icons.js — no emojis.
 * Renders: decision, financial ratios, Five Cs, fraud alerts,
 * regulatory checks, promoter risk, research, CAM, and more.
 */

// ── Inject Static Icons ─────────────────────────
document.getElementById('logo-icon').innerHTML = icon('bolt');
document.getElementById('icon-company').innerHTML = icon('building');
const iconLoan = document.getElementById('icon-loan');
if (iconLoan) iconLoan.innerHTML = icon('pieChart');
document.getElementById('icon-upload').innerHTML = icon('document');
document.getElementById('icon-insights').innerHTML = icon('pencil');
document.getElementById('icon-annual').innerHTML = icon('chartBar');
document.getElementById('icon-gst').innerHTML = icon('receipt');
document.getElementById('icon-bank').innerHTML = icon('bank');
const almIcon = document.getElementById('icon-alm');
if (almIcon) almIcon.innerHTML = icon('shield');
const shIcon = document.getElementById('icon-shareholding');
if (shIcon) shIcon.innerHTML = icon('users');
const pfIcon = document.getElementById('icon-portfolio');
if (pfIcon) pfIcon.innerHTML = icon('chartBar');

// ── Wizard Navigation ───────────────────────────
function wizardNext(step) {
  document.querySelectorAll('.wizard-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.wizard-step').forEach(s => {
    s.classList.remove('active');
    if (parseInt(s.dataset.step) <= step) s.classList.add('active');
  });
  const panel = document.getElementById('step-' + step);
  if (panel) { panel.classList.add('active'); panel.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
}
window.wizardNext = wizardNext;

// ── DOM References ──────────────────────────────
const runBtn = document.getElementById('run-analysis-btn');
const btnText = document.getElementById('btn-text');
const btnSpinner = document.getElementById('btn-spinner');
const skeleton = document.getElementById('skeleton-loader');
const resultsDiv = document.getElementById('results-section');
const insightList = document.getElementById('insights-list');
const addInsight = document.getElementById('add-insight-btn');

// ── File Upload Handling ────────────────────────
document.querySelectorAll('.upload-zone').forEach(zone => {
  const input = zone.querySelector('input[type="file"]');
  const fnameEl = zone.querySelector('.upload-filename');

  ['dragover', 'dragenter'].forEach(e => {
    zone.addEventListener(e, ev => { ev.preventDefault(); zone.classList.add('drag-over'); });
  });
  ['dragleave', 'drop'].forEach(e => {
    zone.addEventListener(e, () => zone.classList.remove('drag-over'));
  });
  zone.addEventListener('drop', ev => {
    ev.preventDefault();
    if (ev.dataTransfer.files.length) {
      input.files = ev.dataTransfer.files;
      input.dispatchEvent(new Event('change'));
    }
  });

  input.addEventListener('change', () => {
    if (input.files.length) {
      zone.classList.add('has-file');
      fnameEl.textContent = input.files[0].name;
    } else {
      zone.classList.remove('has-file');
      fnameEl.textContent = '';
    }
  });
});

// ── Primary Insights ────────────────────────────
let insightCounter = 0;

function addInsightRow(type = 'general', observation = '') {
  const id = ++insightCounter;
  const row = document.createElement('div');
  row.className = 'insight-entry';
  row.id = `insight-${id}`;
  row.innerHTML = `
    <textarea class="form-textarea" placeholder="Describe your observation..." data-role="observation">${observation}</textarea>
    <select class="form-input" data-role="type">
      <option value="general" ${type === 'general' ? 'selected' : ''}>General</option>
      <option value="factory_visit" ${type === 'factory_visit' ? 'selected' : ''}>Factory Visit</option>
      <option value="management_interview" ${type === 'management_interview' ? 'selected' : ''}>Management Interview</option>
    </select>
    <button class="btn btn-danger btn-sm" onclick="document.getElementById('insight-${id}').remove()" type="button">&times;</button>
  `;
  insightList.appendChild(row);
}

addInsight.addEventListener('click', () => addInsightRow());
addInsightRow();

function collectInsights() {
  const entries = [];
  insightList.querySelectorAll('.insight-entry').forEach(row => {
    const obs = row.querySelector('[data-role="observation"]').value.trim();
    const type = row.querySelector('[data-role="type"]').value;
    if (obs) entries.push({ type, observation: obs, severity: 'neutral' });
  });
  return entries;
}

// ── Run Analysis ────────────────────────────────
runBtn.addEventListener('click', async () => {
  const companyName = document.getElementById('company_name').value.trim();
  if (!companyName) { shakeElement(document.getElementById('company_name')); return; }

  const fd = new FormData();
  fd.append('company_name', companyName);
  fd.append('sector', document.getElementById('sector').value.trim());
  fd.append('requested_amount', document.getElementById('requested_amount').value || '0');

  const promoters = document.getElementById('promoter_names').value.split(',').map(s => s.trim()).filter(Boolean);
  fd.append('promoter_names', JSON.stringify(promoters));
  fd.append('primary_notes', JSON.stringify(collectInsights()));

  // ── Entity Onboarding API call (fire-and-forget) ─────
  try {
    const onboardPayload = {
      company_name: companyName,
      cin: (document.getElementById('cin')?.value || '').trim(),
      pan: (document.getElementById('pan')?.value || '').trim(),
      sector: document.getElementById('sector').value.trim(),
      sub_sector: (document.getElementById('sub_sector')?.value || '').trim(),
      annual_turnover: parseFloat(document.getElementById('annual_turnover')?.value || '0'),
      headquarters: (document.getElementById('headquarters')?.value || '').trim(),
      loan_type: (document.getElementById('loan_type')?.value || '').trim(),
      requested_amount: parseFloat(document.getElementById('requested_amount').value || '0'),
      tenure_months: parseInt(document.getElementById('tenure_months')?.value || '0', 10),
      proposed_rate: parseFloat(document.getElementById('proposed_rate')?.value || '0'),
      promoter_names: promoters.join(', '),
    };
    fetch('/onboarding', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(onboardPayload) }).catch(() => { });
  } catch (_e) { /* non-blocking */ }

  const annualFile = document.getElementById('file-annual');
  if (annualFile.files.length) fd.append('annual_report', annualFile.files[0]);
  const gstFile = document.getElementById('file-gst');
  if (gstFile.files.length) fd.append('gst_file', gstFile.files[0]);
  const bankFile = document.getElementById('file-bank');
  if (bankFile.files.length) fd.append('bank_file', bankFile.files[0]);

  setLoading(true);
  try {
    const resp = await fetch('/pipeline/investigate', { method: 'POST', body: fd });
    if (!resp.ok) throw new Error(`Server error ${resp.status}: ${await resp.text()}`);

    resultsDiv.innerHTML = `
      <div class="glass-card" id="timeline-card">
        <div class="card-header">
          <div class="card-icon blue">${icon('bolt')}</div>
          <div>
            <div class="card-title">Live Investigation Timeline</div>
            <div class="card-description">Extracting intelligence from all available modules...</div>
          </div>
        </div>
        <div id="investigation-timeline" class="timeline"></div>
      </div>
      <div id="final-results-container"></div>
    `;
    resultsDiv.classList.add('visible');
    skeleton.classList.remove('visible');
    resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let partial = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      partial += decoder.decode(value, { stream: true });
      const lines = partial.split('\n\n');
      partial = lines.pop() || '';

      for (const line of lines) {
        if (line.trim().startsWith('data: ')) {
          try {
            const payload = JSON.parse(line.trim().substring(6));
            if (['in_progress', 'completed', 'error'].includes(payload.status)) {
              updateTimelineUI(payload);
            }
            if (payload.result) {
              renderResults(payload.result);
            }
          } catch (e) { console.error('SSE parse error:', e, line); }
        }
      }
    }
  } catch (err) {
    resultsDiv.innerHTML = `
      <div class="glass-card" style="border-color:var(--danger);">
        <div class="card-header">
          <div class="card-icon red">${icon('alertTriangle')}</div>
          <div>
            <div class="card-title" style="color:var(--danger);">Analysis Failed</div>
            <div class="card-description">${esc(err.message)}</div>
          </div>
        </div>
      </div>`;
    resultsDiv.classList.add('visible');
  } finally { setLoading(false); }
});

function updateTimelineUI(data) {
  const tl = document.getElementById('investigation-timeline');
  if (!tl) return;
  const safeId = data.step.replace(/[^a-zA-Z0-9]/g, '-');
  let stepEl = document.getElementById(`step-${safeId}`);
  if (!stepEl) {
    stepEl = document.createElement('div');
    stepEl.id = `step-${safeId}`;
    stepEl.className = `timeline-step ${data.status}`;
    stepEl.innerHTML = `
      <div class="step-indicator"></div>
      <div class="step-content">
        <div class="step-title">${esc(data.step)}</div>
        <div class="step-detail">${data.status === 'in_progress' ? 'Processing...' : data.status === 'error' ? esc(data.detail || 'Error occurred') : 'Completed'}</div>
      </div>
    `;
    tl.appendChild(stepEl);
  } else {
    stepEl.className = `timeline-step ${data.status}`;
    stepEl.querySelector('.step-detail').textContent = data.status === 'completed' ? 'Completed' : data.status === 'error' ? esc(data.detail || 'Error occurred') : 'Processing...';
  }
}


function setLoading(on) {
  runBtn.disabled = on;
  btnText.textContent = on ? 'Analyzing...' : 'Run Full Analysis';
  btnSpinner.style.display = on ? 'block' : 'none';
  skeleton.classList.toggle('visible', on);
  if (on) { resultsDiv.classList.remove('visible'); resultsDiv.innerHTML = ''; skeleton.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
}

// ── Render Results ──────────────────────────────
function renderResults(data) {
  _lastAnalysisData = data;
  let html = '';

  // Steps bar
  html += `<div class="steps-bar">`;
  (data.steps_completed || []).forEach(s => { html += `<span class="step-badge">${formatStepName(s)}</span>`; });
  (data.errors || []).forEach(e => { html += `<span class="step-badge error">${esc(e)}</span>`; });
  html += `</div>`;

  // ── Decision Banner ──
  if (data.loan_decision) {
    const d = data.loan_decision;
    const dIcon = d.decision === 'APPROVE' ? icon('checkCircle') : d.decision === 'REJECT' ? icon('xCircle') : icon('minusCircle');
    html += `
      <div class="decision-banner ${d.decision}">
        <div class="decision-label">Credit Decision</div>
        <div class="decision-verdict">${dIcon} ${d.decision}</div>
        <div class="decision-explanation">${esc(d.explanation)}</div>
        <div class="decision-meta">
          <div class="meta-item"><div class="meta-value">${d.risk_grade || '--'}</div><div class="meta-label">Risk Grade</div></div>
          <div class="meta-item"><div class="meta-value">INR ${fmtNum(d.recommended_amount)}</div><div class="meta-label">Recommended Amount</div></div>
          <div class="meta-item"><div class="meta-value">${d.interest_rate}%</div><div class="meta-label">Interest Rate</div></div>
          <div class="meta-item"><div class="meta-value">${d.risk_premium} bps</div><div class="meta-label">Risk Premium</div></div>
          <div class="meta-item"><div class="meta-value">${(d.confidence_score * 100).toFixed(0)}%</div><div class="meta-label">Confidence</div></div>
        </div>
      </div>`;

    // Rejection reasons
    if (d.rejection_reasons?.length) {
      html += `<div class="glass-card"><div class="card-header"><div class="card-icon red">${icon('alertTriangle')}</div><div><div class="card-title">Decision Reasons</div><div class="card-description">Why this decision was made — each factor cites specific data</div></div></div>`;
      html += `<div class="reasons-list">${d.rejection_reasons.map(r => `<div class="reason-item">${icon('xCircle')}<span>${esc(r)}</span></div>`).join('')}</div></div>`;
    }

    // Key factors & conditions
    if (d.key_factors?.length || d.conditions?.length) {
      html += `<div class="glass-card">`;
      if (d.key_factors?.length) {
        html += `<div class="card-header"><div class="card-icon indigo">${icon('key')}</div><div><div class="card-title">Key Factors</div></div></div>`;
        html += `<div class="tag-list">${d.key_factors.map(f => `<span class="tag">${esc(f)}</span>`).join('')}</div>`;
      }
      if (d.conditions?.length) {
        html += `<div class="card-header" style="margin-top:16px;"><div class="card-icon amber">${icon('clipboard')}</div><div><div class="card-title">Conditions</div></div></div>`;
        html += `<div class="tag-list">${d.conditions.map(c => `<span class="tag">${esc(c)}</span>`).join('')}</div>`;
      }
      html += `</div>`;
    }
  }

  // ── Financial Ratios ──
  if (data.loan_decision?.financial_ratios) {
    const fr = data.loan_decision.financial_ratios;
    const ratios = [fr.dscr, fr.icr, fr.leverage, fr.current_ratio, fr.debt_to_equity, fr.ebitda_margin].filter(r => r);
    if (ratios.length) {
      html += `
        <div class="glass-card">
          <div class="card-header">
            <div class="card-icon purple">${icon('gauge')}</div>
            <div>
              <div class="card-title">Financial Ratio Analysis <span class="health-badge ${fr.overall_health}">${fr.overall_health}</span></div>
              <div class="card-description">Banking-standard financial ratios with pass/watch/fail assessment</div>
            </div>
          </div>
          <div class="ratio-grid">
            ${ratios.map(r => {
        const cls = (r.assessment || 'N/A').toLowerCase().replace('/', '');
        const val = r.value != null ? (r.name.includes('Margin') ? r.value + '%' : r.value + 'x') : '--';
        return `<div class="ratio-card ${cls}">
                <div class="ratio-name">${esc(r.name)}</div>
                <div class="ratio-value">${val}</div>
                <div class="ratio-bench">Benchmark: ${esc(r.benchmark)}</div>
                <div class="ratio-assessment">${esc(r.assessment)}</div>
                <div class="ratio-detail">${esc(r.detail)}</div>
              </div>`;
      }).join('')}
          </div>
        </div>`;
    }
  }

  // ── Five Cs ──
  if (data.five_cs_scores?.scores?.length) {
    const cs = data.five_cs_scores;
    html += `
      <div class="glass-card">
        <div class="card-header">
          <div class="card-icon purple">${icon('scales')}</div>
          <div>
            <div class="card-title">Five Cs of Credit -- ${cs.weighted_total.toFixed(1)}/100 (${cs.risk_grade})</div>
            <div class="card-description">${esc(cs.ai_commentary || '')}</div>
          </div>
        </div>
        <div class="scores-grid">
          ${cs.scores.map(s => {
      const cls = s.score >= 65 ? 'high' : s.score >= 40 ? 'medium' : 'low';
      return `
              <div class="score-row">
                <div class="score-label">${s.category}</div>
                <div class="score-bar-track"><div class="score-bar-fill ${cls}" style="width:${s.score}%"></div></div>
                <div class="score-value">${s.score.toFixed(0)}</div>
              </div>
              ${s.explanation ? `<div class="score-explanation">${esc(s.explanation)}</div>` : ''}`;
    }).join('')}
        </div>
      </div>`;
  }

  // ── Fraud Report ──
  if (data.fraud_report && data.fraud_report.total_alerts > 0) {
    const fr = data.fraud_report;
    html += `
      <div class="glass-card" style="border-color:${fr.overall_fraud_risk === 'critical' ? 'var(--danger)' : 'var(--border)'};">
        <div class="card-header">
          <div class="card-icon red">${icon('scanEye')}</div>
          <div>
            <div class="card-title">Fraud Detection -- ${fr.overall_fraud_risk.toUpperCase()} Risk (Score: ${fr.fraud_score}/100)</div>
            <div class="card-description">${fr.total_alerts} alert(s) detected: ${fr.critical_count} critical, ${fr.high_count} high</div>
          </div>
        </div>
        <div class="anomaly-list">
          ${fr.alerts.map(a => `
            <div class="anomaly-item">
              <span class="severity-badge ${a.severity}">${a.severity}</span>
              <div>
                <div class="anomaly-text" style="font-weight:600;color:var(--text-primary);">${esc(a.title)}</div>
                <div class="anomaly-text">${esc(a.description)}</div>
                ${a.evidence ? `<div class="anomaly-text" style="font-size:11px;color:var(--text-muted);margin-top:4px;">Evidence: ${esc(a.evidence)}</div>` : ''}
              </div>
            </div>`).join('')}
        </div>
      </div>`;
  }

  // ── Regulatory Checks ──
  if (data.regulatory_checks) {
    const rc = data.regulatory_checks;
    html += `
      <div class="glass-card">
        <div class="card-header">
          <div class="card-icon blue">${icon('landmark')}</div>
          <div>
            <div class="card-title">Indian Regulatory Checks -- ${rc.overall_regulatory_risk.toUpperCase()} Risk</div>
            <div class="card-description">CIBIL, GSTR-2A/3B mismatch, MCA director status</div>
          </div>
        </div>`;

    // CIBIL
    if (rc.cibil) {
      const c = rc.cibil;
      const cClass = c.score >= 750 ? 'good' : c.score >= 650 ? 'moderate' : 'poor';
      html += `
        <div class="cibil-gauge">
          <div class="cibil-score-circle ${cClass}">${c.score}</div>
          <div class="cibil-details">
            <div class="cibil-rating">CIBIL: ${esc(c.rating)}</div>
            <div class="cibil-meta">
              Credit Age: ${c.credit_age_years} yrs | Active: ${c.active_accounts} | Overdue: ${c.overdue_accounts} | Enquiries (6m): ${c.enquiry_count_6m}
            </div>
            <div class="cibil-meta" style="margin-top:4px;">${esc(c.assessment)}</div>
          </div>
        </div>`;
      if (c.default_history?.length) {
        html += `<div class="anomaly-list" style="margin-bottom:12px;">${c.default_history.map(d => `<div class="anomaly-item"><span class="severity-badge high">Default</span><span class="anomaly-text">${esc(d)}</span></div>`).join('')}</div>`;
      }
    }

    // GSTR mismatch
    if (rc.gstr_mismatch && rc.gstr_mismatch.mismatch_percentage > 0) {
      const g = rc.gstr_mismatch;
      html += `
        <div style="padding:12px;background:var(--bg-glass);border:1px solid var(--border);border-radius:var(--radius-sm);margin-bottom:12px;">
          <div style="font-size:13px;font-weight:600;color:var(--text-primary);margin-bottom:6px;">GSTR-2A vs 3B Mismatch</div>
          <div style="font-size:12px;color:var(--text-muted);">
            ITC Claimed (3B): INR ${fmtNum(g.itc_claimed_3b)} | ITC Eligible (2A): INR ${fmtNum(g.itc_eligible_2a)} | Gap: ${g.mismatch_percentage.toFixed(1)}%
          </div>
          <div style="font-size:12px;color:var(--text-secondary);margin-top:6px;">${esc(g.risk_flag)}</div>
        </div>`;
    }

    // Director checks
    if (rc.director_checks?.length) {
      html += `<div style="font-size:13px;font-weight:600;color:var(--text-primary);margin-bottom:8px;">MCA Director Status</div>`;
      html += `<div class="promoter-list">${rc.director_checks.map(d => `
        <div class="promoter-item">
          ${icon('users')}
          <div class="promoter-name">${esc(d.director_name)}</div>
          <div class="promoter-linked">DIN: ${d.din} | ${d.companies_linked} co.</div>
          <span class="risk-badge ${d.defaulter_flag || d.status === 'Disqualified' ? 'high' : 'low'}">${d.status}</span>
        </div>`).join('')}</div>`;
    }

    // Flags
    if (rc.flags?.length) {
      html += `<div class="tag-list" style="margin-top:12px;">${rc.flags.map(f => `<span class="tag" style="border-color:var(--warning);color:var(--warning);">${esc(f)}</span>`).join('')}</div>`;
    }
    html += `</div>`;
  }

  // ── Promoter Risk ──
  if (data.promoter_risk && data.promoter_risk.promoters_analyzed > 0) {
    const pr = data.promoter_risk;
    html += `
      <div class="glass-card">
        <div class="card-header">
          <div class="card-icon amber">${icon('users')}</div>
          <div>
            <div class="card-title">Promoter Risk Analysis -- ${pr.overall_promoter_risk.toUpperCase()}</div>
            <div class="card-description">${pr.promoters_analyzed} promoter(s) analyzed</div>
          </div>
        </div>`;

    if (pr.details?.length) {
      html += `<div class="promoter-list">${pr.details.map(d => `
        <div class="promoter-item">
          ${icon('fingerprint')}
          <div class="promoter-name">${esc(d.name)}</div>
          <div class="promoter-linked">${d.num_linked} linked co.</div>
          <span class="risk-badge ${d.risk_level}">${d.risk_level}</span>
        </div>`).join('')}</div>`;
    }

    if (pr.litigation_flags?.length) {
      html += `<div class="anomaly-list" style="margin-top:12px;">${pr.litigation_flags.map(l => `<div class="anomaly-item"><span class="severity-badge high">Litigation</span><span class="anomaly-text">${esc(l)}</span></div>`).join('')}</div>`;
    }

    if (pr.risk_flags?.length) {
      html += `<div class="tag-list" style="margin-top:12px;">${pr.risk_flags.map(f => `<span class="tag" style="border-color:var(--danger);color:var(--danger);">${esc(f)}</span>`).join('')}</div>`;
    }

    // Graph container
    if (pr.graph_structure && pr.graph_structure.nodes) {
      html += `<div id="network-graph-container"></div>`;
      setTimeout(() => {
        const container = document.getElementById('network-graph-container');
        if (container && window.vis) {
          const data = {
            nodes: new vis.DataSet(pr.graph_structure.nodes),
            edges: new vis.DataSet(pr.graph_structure.edges)
          };
          const options = {
            nodes: { shape: 'dot', font: { color: '#f1f5f9' }, scaling: { max: 20 } },
            edges: { color: '#64748b' },
            physics: { barnesHut: { gravitationalConstant: -3000 } }
          };
          new vis.Network(container, data, options);
        }
      }, 300);
    }

    html += `</div>`;
  }

  // ── Sector Risk Intelligence ──
  if (data.sector_risk) {
    const sr = data.sector_risk;
    html += `
      <div class="glass-card">
        <div class="card-header">
          <div class="card-icon blue">${icon('globe')}</div>
          <div>
            <div class="card-title">Sector Risk Intelligence -- ${esc(sr.sector)}</div>
            <div class="card-description">Risk Score: ${sr.sector_risk_score.toFixed(0)}/100 | ${esc(sr.risk_level).toUpperCase()}</div>
          </div>
        </div>
        <div style="font-size:13px;color:var(--text-secondary);margin-bottom:12px;">${esc(sr.sector_summary)}</div>`;
    if (sr.sector_headwinds?.length) {
      html += `<div class="tag-list">${sr.sector_headwinds.map(h => `<span class="tag" style="border-color:var(--warning);color:var(--warning);">${esc(h.risk_factor)}</span>`).join('')}</div>`;
    }
    html += `</div>`;
  }

  // ── Early Warning Signals ──
  if (data.early_warning) {
    const ew = data.early_warning;
    html += `
      <div class="glass-card" style="border-color:${ew.risk_level === 'HIGH' ? 'var(--danger)' : 'var(--border)'};">
        <div class="card-header">
          <div class="card-icon red">${icon('alertTriangle')}</div>
          <div>
            <div class="card-title">Early Warning System (EWS)</div>
            <div class="card-description">Score: ${(ew.early_warning_score * 100).toFixed(0)}/100 | ${ew.active_warnings} Active Triggers</div>
          </div>
        </div>`;
    if (ew.triggers?.length) {
      html += `<div class="anomaly-list">${ew.triggers.map(t => `<div class="anomaly-item"><span class="severity-badge ${t.severity}">${t.severity}</span><div><div class="anomaly-text" style="font-weight:600;color:var(--text-primary);">${esc(t.signal)}</div><div class="anomaly-text">${esc(t.description)}</div></div></div>`).join('')}</div>`;
    }
    html += `</div>`;
  }

  // ── Working Capital Stress ──
  if (data.working_capital) {
    const wc = data.working_capital;
    const riskCls = wc.liquidity_risk_level === 'CRITICAL' ? 'danger' : wc.liquidity_risk_level === 'HIGH' ? 'danger' : wc.liquidity_risk_level === 'MODERATE' ? 'warning' : 'success';
    html += `
      <div class="glass-card" style="border-color:${wc.liquidity_risk_level === 'CRITICAL' || wc.liquidity_risk_level === 'HIGH' ? 'var(--danger)' : 'var(--border)'};">
        <div class="card-header">
          <div class="card-icon amber">${icon('gauge')}</div>
          <div>
            <div class="card-title">Working Capital Stress Analysis</div>
            <div class="card-description">Liquidity: <span class="risk-badge ${riskCls}">${wc.liquidity_risk_level}</span> | Score: ${wc.working_capital_score.toFixed(0)}/100 | ${wc.data_completeness}</div>
          </div>
        </div>`;

    // CCC Gauge
    if (wc.cash_conversion_cycle != null) {
      const cccVal = wc.cash_conversion_cycle;
      const cccCls = cccVal < 60 ? 'good' : cccVal < 120 ? 'moderate' : 'poor';
      html += `
        <div class="wc-ccc-gauge">
          <div class="ccc-circle ${cccCls}">${cccVal.toFixed(0)}<span class="ccc-unit">days</span></div>
          <div class="ccc-label">Cash Conversion Cycle</div>
        </div>`;
    }

    // Metric cards
    const wcMetrics = [
      { label: 'Receivable Days', value: wc.receivable_days, suffix: 'd' },
      { label: 'Inventory Days', value: wc.inventory_days, suffix: 'd' },
      { label: 'Payable Days', value: wc.payable_days, suffix: 'd' },
    ].filter(m => m.value != null);
    if (wcMetrics.length) {
      html += `<div class="wc-metrics">${wcMetrics.map(m => `
        <div class="wc-metric-card">
          <div class="wc-metric-value">${m.value.toFixed(0)}${m.suffix}</div>
          <div class="wc-metric-label">${m.label}</div>
        </div>`).join('')}</div>`;
    }

    // Stress indicators
    if (wc.stress_indicators?.length) {
      html += `<div class="anomaly-list" style="margin-top:12px;">${wc.stress_indicators.map(s => `
        <div class="anomaly-item">
          <span class="severity-badge ${s.severity}">${s.severity}</span>
          <div>
            <div class="anomaly-text" style="font-weight:600;color:var(--text-primary);">${esc(s.signal)}</div>
            <div class="anomaly-text">${esc(s.description)}</div>
          </div>
        </div>`).join('')}</div>`;
    }

    if (wc.explanation) {
      html += `<div style="margin-top:12px;font-size:13px;color:var(--text-secondary);line-height:1.6;">${esc(wc.explanation)}</div>`;
    }
    html += `</div>`;
  }

  // ── Historical Borrower Trust ──
  if (data.historical_trust) {
    const ht = data.historical_trust;
    const trustCls = ht.historical_trust_score >= 70 ? 'good' : ht.historical_trust_score >= 50 ? 'moderate' : ht.historical_trust_score > 0 ? 'poor' : 'unknown';
    html += `
      <div class="glass-card">
        <div class="card-header">
          <div class="card-icon indigo">${icon('history')}</div>
          <div>
            <div class="card-title">Borrower Historical Trust</div>
            <div class="card-description">${ht.number_of_previous_applications} previous application(s) on record</div>
          </div>
        </div>`;

    if (ht.number_of_previous_applications > 0) {
      // Trust score badge
      html += `
        <div class="ht-trust-badge">
          <div class="trust-circle ${trustCls}">${ht.historical_trust_score.toFixed(0)}<span class="trust-unit">/100</span></div>
          <div class="trust-label">Historical Trust Score</div>
        </div>`;

      // Trend indicators
      const trendIcon = (t) => t === 'improving' ? '↗' : t === 'worsening' ? '↘' : t === 'stable' ? '→' : '—';
      const trendCls = (t) => t === 'improving' ? 'success' : t === 'worsening' ? 'danger' : 'neutral';
      html += `
        <div class="ht-trends">
          <div class="ht-trend-item ${trendCls(ht.risk_score_trend)}">
            <span class="trend-arrow">${trendIcon(ht.risk_score_trend)}</span>
            <span>Risk Score: ${ht.risk_score_trend}</span>
          </div>
          <div class="ht-trend-item ${trendCls(ht.fraud_risk_trend)}">
            <span class="trend-arrow">${trendIcon(ht.fraud_risk_trend)}</span>
            <span>Fraud Risk: ${ht.fraud_risk_trend}</span>
          </div>
          <div class="ht-trend-item ${trendCls(ht.financial_stability_trend)}">
            <span class="trend-arrow">${trendIcon(ht.financial_stability_trend)}</span>
            <span>Financial Stability: ${ht.financial_stability_trend}</span>
          </div>
        </div>`;

      // Previous applications table
      if (ht.previous_applications?.length) {
        html += `
          <div class="ht-table-wrapper">
            <table class="ht-table">
              <thead><tr>
                <th>Date</th><th>Decision</th><th>Risk</th><th>Requested</th><th>Approved</th><th>Five Cs</th>
              </tr></thead>
              <tbody>${ht.previous_applications.map(a => `
                <tr>
                  <td>${esc(a.date)}</td>
                  <td><span class="decision-pill ${a.decision}">${a.decision}</span></td>
                  <td>${a.risk_score}</td>
                  <td>${a.amount_requested > 0 ? 'INR ' + fmtNum(a.amount_requested) : '--'}</td>
                  <td>${a.amount_approved > 0 ? 'INR ' + fmtNum(a.amount_approved) : '--'}</td>
                  <td>${a.five_cs}</td>
                </tr>`).join('')}</tbody>
            </table>
          </div>`;
      }
    } else {
      html += `<div style="padding:16px;font-size:13px;color:var(--text-muted);text-align:center;">${esc(ht.trend_summary)}</div>`;
    }

    html += `</div>`;
  }
  // ── SWOT Analysis ──
  if (data.swot_analysis) {
    const sw = data.swot_analysis;
    html += `
      <div class="glass-card">
        <div class="card-header">
          <div class="card-icon purple">${icon('search')}</div>
          <div>
            <div class="card-title">SWOT Analysis</div>
            <div class="card-description">${esc(sw.summary || '')}</div>
          </div>
        </div>
        <div class="swot-grid">
          <div class="swot-quadrant swot-s"><div class="swot-label">Strengths</div>${(sw.strengths || []).map(s => '<div class="swot-item">' + esc(s) + '</div>').join('')}</div>
          <div class="swot-quadrant swot-w"><div class="swot-label">Weaknesses</div>${(sw.weaknesses || []).map(s => '<div class="swot-item">' + esc(s) + '</div>').join('')}</div>
          <div class="swot-quadrant swot-o"><div class="swot-label">Opportunities</div>${(sw.opportunities || []).map(s => '<div class="swot-item">' + esc(s) + '</div>').join('')}</div>
          <div class="swot-quadrant swot-t"><div class="swot-label">Threats</div>${(sw.threats || []).map(s => '<div class="swot-item">' + esc(s) + '</div>').join('')}</div>
        </div>
      </div>`;
  }

  // ── Portfolio Risk ──
  if (data.portfolio_risk && data.portfolio_risk.risk_level !== 'NOT_APPLICABLE') {
    const pr = data.portfolio_risk;
    const prColor = pr.risk_level === 'LOW' ? 'var(--success)' : pr.risk_level === 'MODERATE' ? 'var(--warning)' : 'var(--danger)';
    html += `
      <div class="glass-card">
        <div class="card-header">
          <div class="card-icon green">${icon('chartBar')}</div>
          <div>
            <div class="card-title">Portfolio Performance Analysis</div>
            <div class="card-description">${esc(pr.summary)}</div>
          </div>
        </div>
        <div class="stat-grid">
          <div class="stat-item"><div class="stat-value" style="color:${prColor}">${pr.portfolio_risk_score.toFixed(0)}/100</div><div class="stat-label">Portfolio Score (${pr.risk_level})</div></div>`;
    const pm = pr.metrics || {};
    if (pm.gross_npa_ratio != null) html += `<div class="stat-item"><div class="stat-value">${pm.gross_npa_ratio.toFixed(1)}%</div><div class="stat-label">GNPA Ratio</div></div>`;
    if (pm.default_rate != null) html += `<div class="stat-item"><div class="stat-value">${pm.default_rate.toFixed(1)}%</div><div class="stat-label">Default Rate</div></div>`;
    if (pm.recovery_rate != null) html += `<div class="stat-item"><div class="stat-value">${pm.recovery_rate.toFixed(0)}%</div><div class="stat-label">Recovery Rate</div></div>`;
    if (pm.portfolio_yield != null) html += `<div class="stat-item"><div class="stat-value">${pm.portfolio_yield.toFixed(1)}%</div><div class="stat-label">Portfolio Yield</div></div>`;
    if (pm.provision_coverage != null) html += `<div class="stat-item"><div class="stat-value">${pm.provision_coverage.toFixed(0)}%</div><div class="stat-label">Provision Coverage</div></div>`;
    html += `</div>`;
    if (pr.risk_signals?.length) {
      html += `<div class="anomaly-list" style="margin-top:14px;">${pr.risk_signals.map(s => `<div class="anomaly-item"><span class="severity-badge ${s.severity}">${s.severity}</span><div><div class="anomaly-text" style="font-weight:600;">${esc(s.signal)}</div><div class="anomaly-text">${esc(s.detail)}</div></div></div>`).join('')}</div>`;
    }
    html += `</div>`;
  }

  // ── Risk Heatmap Dashboard ──
  {
    const hm = [];
    if (data.loan_decision) hm.push({ label: 'Financial', score: data.loan_decision.final_credit_risk_score || 50, max: 100 });
    if (data.sector_risk) hm.push({ label: 'Sector', score: data.sector_risk.sector_risk_score || 0, max: 100 });
    if (data.fraud_report) hm.push({ label: 'Fraud', score: data.fraud_report.fraud_score || 0, max: 100 });
    if (data.promoter_risk) hm.push({ label: 'Promoter', score: data.promoter_risk.promoter_risk_score || 0, max: 100 });
    if (data.portfolio_risk && data.portfolio_risk.risk_level !== 'NOT_APPLICABLE') {
      hm.push({ label: 'Portfolio', score: 100 - (data.portfolio_risk.portfolio_risk_score || 50), max: 100 });
    }
    if (hm.length) {
      html += `
        <div class="glass-card">
          <div class="card-header">
            <div class="card-icon red">${icon('shield')}</div>
            <div>
              <div class="card-title">Risk Heatmap Dashboard</div>
              <div class="card-description">Composite risk view across all dimensions</div>
            </div>
          </div>
          <div class="heatmap-grid">${hm.map(h => {
        const pct = Math.min(h.score, 100);
        const clr = pct < 30 ? '#22c55e' : pct < 60 ? '#f59e0b' : pct < 80 ? '#f97316' : '#ef4444';
        return `<div class="heatmap-cell" style="--hm-color:${clr}">
              <div class="heatmap-value">${pct.toFixed(0)}</div>
              <div class="heatmap-label">${h.label}</div>
            </div>`;
      }).join('')}</div>
        </div>`;
    }
  }

  // ── Credit Committee Simulation ──
  if (data.loan_decision) {
    const ld = data.loan_decision;
    html += `
      <div class="glass-card cc-panel">
        <div class="card-header">
          <div class="card-icon indigo">${icon('users')}</div>
          <div>
            <div class="card-title">Credit Committee Simulation</div>
            <div class="card-description">AI-generated panel view for committee review</div>
          </div>
        </div>
        <div class="cc-tabs">
          <button class="cc-tab active" onclick="switchCCTab(this, 'cc-rec')">Recommendation</button>
          <button class="cc-tab" onclick="switchCCTab(this, 'cc-risk')">Risk Factors</button>
          <button class="cc-tab" onclick="switchCCTab(this, 'cc-evidence')">Evidence</button>
        </div>
        <div class="cc-content" id="cc-rec">
          <div class="cc-verdict ${ld.decision === 'APPROVE' ? 'approve' : ld.decision === 'REJECT' ? 'reject' : 'refer'}">
            <div class="cc-verdict-label">Committee Verdict</div>
            <div class="cc-verdict-value">${ld.decision}</div>
          </div>
          <div class="stat-grid">
            <div class="stat-item"><div class="stat-value">INR ${fmtNum(ld.recommended_amount)}</div><div class="stat-label">Approved Amount</div></div>
            <div class="stat-item"><div class="stat-value">${ld.interest_rate?.toFixed(2) || '0'}%</div><div class="stat-label">Interest Rate</div></div>
            <div class="stat-item"><div class="stat-value">${ld.risk_grade || 'N/A'}</div><div class="stat-label">Risk Grade</div></div>
            <div class="stat-item"><div class="stat-value">${ld.confidence_score?.toFixed(0) || 0}%</div><div class="stat-label">Confidence</div></div>
          </div>
          ${ld.explanation ? '<div style="margin-top:14px;font-size:13px;color:var(--text-secondary);white-space:pre-wrap;">' + esc(ld.explanation) + '</div>' : ''}
        </div>
        <div class="cc-content" id="cc-risk" style="display:none;">
          ${(ld.rejection_reasons || []).length ? '<div class="anomaly-list">' + ld.rejection_reasons.map(r => '<div class="anomaly-item"><span class="severity-badge high">Risk</span><span class="anomaly-text">' + esc(r) + '</span></div>').join('') + '</div>' : ''}
          ${(ld.conditions || []).length ? '<div style="margin-top:12px;"><strong style="font-size:13px;">Conditions:</strong>' + ld.conditions.map(c => '<div style="font-size:13px;color:var(--text-secondary);padding:4px 0;">• ' + esc(c) + '</div>').join('') + '</div>' : ''}
        </div>
        <div class="cc-content" id="cc-evidence" style="display:none;">
          ${(ld.key_factors || []).length ? '<div class="tag-list">' + ld.key_factors.map(f => '<span class="tag">' + esc(f) + '</span>').join('') + '</div>' : '<div style="font-size:13px;color:var(--text-muted);">No key factors available.</div>'}
        </div>
      </div>`;
  }

  // ── Financial Trend Analysis ──
  if (data.financial_trends) {
    const ft = data.financial_trends;
    const stabColor = ft.stability_score >= 75 ? 'var(--success)' : ft.stability_score >= 55 ? 'var(--warning)' : 'var(--danger)';
    html += `
      <div class="glass-card">
        <div class="card-header">
          <div class="card-icon purple">${icon('chartBar')}</div>
          <div>
            <div class="card-title">Financial Trend Analysis</div>
            <div class="card-description">Stability: <span style="color:${stabColor};font-weight:700;">${ft.stability_assessment}</span> | Score: ${ft.stability_score.toFixed(0)}/100 | ${ft.num_metrics_analyzed} metrics | Data: ${ft.data_quality}</div>
          </div>
        </div>`;
    if (ft.trends?.length) {
      html += `<div class="stat-grid">`;
      ft.trends.forEach(t => {
        const severityColor = t.severity === 'positive' ? 'var(--success)' : t.severity === 'critical' ? 'var(--danger)' : t.severity === 'warning' ? 'var(--warning)' : 'var(--text-secondary)';
        html += `
          <div class="stat-item" style="border-left:3px solid ${severityColor};padding-left:12px;">
            <div class="stat-value" style="color:${severityColor}">${esc(t.value)}</div>
            <div class="stat-label">${esc(t.metric)} — ${esc(t.direction)}</div>
            ${t.detail ? `<div style="font-size:11px;color:var(--text-muted);margin-top:4px;">${esc(t.detail)}</div>` : ''}
          </div>`;
      });
      html += `</div>`;
    }
    if (ft.trend_signals?.length) {
      html += `<div class="anomaly-list" style="margin-top:14px;">${ft.trend_signals.map(s => `<div class="anomaly-item"><span class="severity-badge ${s.severity}">${s.severity}</span><div><div class="anomaly-text" style="font-weight:600;">${esc(s.signal)}</div><div class="anomaly-text">${esc(s.detail)}</div></div></div>`).join('')}</div>`;
    }
    html += `</div>`;
  }

  // ── CAM Report Download ──
  if (data.credit_memo) {
    const cm = data.credit_memo;
    html += `
      <div class="glass-card" style="text-align:center;">
        <div class="card-header" style="justify-content:center;">
          <div class="card-icon green">${icon('document')}</div>
          <div>
            <div class="card-title">Credit Appraisal Memo</div>
            <div class="card-description">${esc(cm.recommendation || '')} | Risk: ${esc(cm.risk_grade || 'N/A')} | Amount: INR ${fmtNum(cm.recommended_amount)}</div>
          </div>
        </div>
        <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;">
          ${cm.docx_path ? `<a class="btn btn-primary" href="${cm.docx_path}" download style="text-decoration:none;">Download DOCX</a>` : ''}
          ${cm.pdf_path ? `<a class="btn btn-primary" href="${cm.pdf_path}" download style="text-decoration:none;background:var(--danger);">Download PDF</a>` : ''}
        </div>
      </div>`;
  }

  // ── Schema Mapping Builder ──
  {
    html += `
      <div class="glass-card" id="schema-builder-card">
        <div class="card-header">
          <div class="card-icon blue">${icon('key')}</div>
          <div>
            <div class="card-title">Schema Mapping Builder</div>
            <div class="card-description">Select fields to map and export in custom format</div>
          </div>
        </div>
        <div id="schema-fields-container" style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px;"></div>
        <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;">
          <button class="btn btn-primary" onclick="runSchemaMap('json')">Export JSON</button>
          <button class="btn btn-ghost" onclick="runSchemaMap('csv')">Export CSV</button>
          <span id="schema-status" style="font-size:12px;color:var(--text-muted);"></span>
        </div>
        <pre id="schema-output" style="display:none;margin-top:14px;font-size:12px;background:var(--bg-glass);padding:12px;border-radius:var(--radius-sm);overflow-x:auto;max-height:300px;color:var(--text-secondary);"></pre>
      </div>`;
  }

  // ── Data Export Buttons ──
  html += `
    <div class="glass-card" style="text-align:center;">
      <div class="card-header" style="justify-content:center;">
        <div class="card-icon blue">${icon('document')}</div>
        <div>
          <div class="card-title">Export Analysis Data</div>
          <div class="card-description">Download structured data for schema mapping</div>
        </div>
      </div>
      <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;">
        <button class="btn btn-primary" onclick="exportJSON()">Export JSON</button>
        <button class="btn btn-ghost" onclick="exportCSV()">Export CSV</button>
      </div>
    </div>`;

  const target = document.getElementById('final-results-container') || resultsDiv;
  target.innerHTML = html;
  resultsDiv.classList.add('visible');
  if (!document.getElementById('final-results-container')) {
    resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  // Populate schema builder fields from flat data
  setTimeout(() => {
    const container = document.getElementById('schema-fields-container');
    if (container && _lastAnalysisData) {
      const flat = flattenObj(_lastAnalysisData);
      const keys = Object.keys(flat).slice(0, 50);
      container.innerHTML = keys.map(k => `<label style="display:flex;align-items:center;gap:4px;font-size:12px;color:var(--text-secondary);cursor:pointer;"><input type="checkbox" value="${esc(k)}" class="schema-field-cb" checked> ${esc(k)}</label>`).join('');
    }
  }, 200);

  // Animate score bars
  requestAnimationFrame(() => {
    document.querySelectorAll('.score-bar-fill').forEach(bar => {
      const w = bar.style.width; bar.style.width = '0%';
      requestAnimationFrame(() => { bar.style.width = w; });
    });
  });
}

// ── Utilities ───────────────────────────────────
function esc(text) { const el = document.createElement('span'); el.textContent = text || ''; return el.innerHTML; }
function fmtNum(n) { if (n == null || isNaN(n)) return '0'; return Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 }); }
function formatStepName(s) { return s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()); }

function shakeElement(el) {
  el.style.outline = '2px solid var(--danger)';
  el.style.animation = 'none'; el.offsetHeight;
  el.style.animation = 'shake 0.4s ease';
  setTimeout(() => { el.style.outline = ''; el.style.animation = ''; el.focus(); }, 500);
}

const _shakeStyle = document.createElement('style');
_shakeStyle.textContent = `@keyframes shake { 0%,100% { transform: translateX(0); } 25% { transform: translateX(-6px); } 75% { transform: translateX(6px); } }`;
document.head.appendChild(_shakeStyle);

// ── Store last analysis for export ──────────────
let _lastAnalysisData = null;

// ── Credit Committee Tab Switch ─────────────────
function switchCCTab(btn, panelId) {
  const panel = btn.closest('.cc-panel');
  panel.querySelectorAll('.cc-tab').forEach(t => t.classList.remove('active'));
  panel.querySelectorAll('.cc-content').forEach(c => c.style.display = 'none');
  btn.classList.add('active');
  const target = document.getElementById(panelId);
  if (target) target.style.display = 'block';
}
window.switchCCTab = switchCCTab;

// ── Data Export ─────────────────────────────────
function exportJSON() {
  if (!_lastAnalysisData) return alert('No analysis data to export.');
  const blob = new Blob([JSON.stringify(_lastAnalysisData, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = (_lastAnalysisData.company_name || 'analysis') + '_report.json';
  a.click();
}
window.exportJSON = exportJSON;

function exportCSV() {
  if (!_lastAnalysisData) return alert('No analysis data to export.');
  const flat = flattenObj(_lastAnalysisData);
  let csv = 'Field,Value\n';
  for (const [k, v] of Object.entries(flat)) {
    csv += `"${k}","${String(v ?? '').replace(/"/g, '""')}"\n`;
  }
  const blob = new Blob([csv], { type: 'text/csv' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = (_lastAnalysisData.company_name || 'analysis') + '_report.csv';
  a.click();
}
window.exportCSV = exportCSV;

function flattenObj(obj, prefix = '', result = {}) {
  for (const [k, v] of Object.entries(obj || {})) {
    const key = prefix ? prefix + '.' + k : k;
    if (v && typeof v === 'object' && !Array.isArray(v)) {
      flattenObj(v, key, result);
    } else {
      result[key] = Array.isArray(v) ? JSON.stringify(v) : v;
    }
  }
  return result;
}

// ── Schema Builder ──────────────────────────────
function runSchemaMap(format) {
  if (!_lastAnalysisData) return alert('No analysis data available.');
  const checkboxes = document.querySelectorAll('.schema-field-cb:checked');
  const fields = Array.from(checkboxes).map(cb => cb.value);
  if (!fields.length) return alert('Select at least one field.');

  const statusEl = document.getElementById('schema-status');
  const outputEl = document.getElementById('schema-output');
  if (statusEl) statusEl.textContent = 'Mapping...';

  fetch('/ingest/schema-map', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      extracted_data: flattenObj(_lastAnalysisData),
      schema_fields: fields,
      export_format: format,
    }),
  })
    .then(r => r.json())
    .then(data => {
      if (statusEl) statusEl.textContent = `Mapped ${fields.length} fields (${format.toUpperCase()})`;
      if (outputEl) {
        outputEl.style.display = 'block';
        outputEl.textContent = typeof data.data === 'string' ? data.data : JSON.stringify(data.mapped, null, 2);
      }
    })
    .catch(err => {
      if (statusEl) statusEl.textContent = 'Error: ' + err.message;
    });
}
window.runSchemaMap = runSchemaMap;
