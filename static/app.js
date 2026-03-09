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
document.getElementById('icon-upload').innerHTML = icon('document');
document.getElementById('icon-insights').innerHTML = icon('pencil');
document.getElementById('icon-annual').innerHTML = icon('chartBar');
document.getElementById('icon-gst').innerHTML = icon('receipt');
document.getElementById('icon-bank').innerHTML = icon('bank');

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

  // ── Document Analysis ──
  if (data.document_analysis) {
    const da = data.document_analysis;
    html += `
      <div class="glass-card">
        <div class="card-header">
          <div class="card-icon blue">${icon('chartBar')}</div>
          <div>
            <div class="card-title">Document Analysis -- ${esc(da.file_name)}</div>
            <div class="card-description">${esc(da.summary || '')}</div>
          </div>
        </div>`;
    const f = da.financials;
    if (f) {
      const metrics = [
        { label: 'Revenue', value: f.revenue }, { label: 'Net Profit', value: f.net_profit },
        { label: 'Total Debt', value: f.total_debt }, { label: 'EBITDA', value: f.ebitda },
        { label: 'Debt/Equity', value: f.debt_to_equity }, { label: 'Current Ratio', value: f.current_ratio },
        { label: 'ICR', value: f.interest_coverage },
      ].filter(m => m.value != null);
      if (metrics.length) {
        html += `<div class="stat-grid">${metrics.map(m => `<div class="stat-item"><div class="stat-value">${typeof m.value === 'number' && m.value > 1000 ? 'INR ' + fmtNum(m.value) : m.value}</div><div class="stat-label">${m.label}</div></div>`).join('')}</div>`;
      }
    }
    if (da.risks) {
      const allRisks = [...(da.risks.key_risks || []).map(r => ({ text: r, type: 'Key Risk' })), ...(da.risks.contingent_liabilities || []).map(r => ({ text: r, type: 'Contingent' })), ...(da.risks.auditor_qualifications || []).map(r => ({ text: r, type: 'Auditor' }))];
      if (allRisks.length) html += `<div class="anomaly-list" style="margin-top:16px;">${allRisks.map(r => `<div class="anomaly-item"><span class="severity-badge medium">${r.type}</span><span class="anomaly-text">${esc(r.text)}</span></div>`).join('')}</div>`;
    }
    html += `</div>`;
  }

  // ── Cross Verification ──
  if (data.cross_verification) {
    const cv = data.cross_verification;
    html += `
      <div class="glass-card">
        <div class="card-header">
          <div class="card-icon amber">${icon('search')}</div>
          <div>
            <div class="card-title">Cross-Verification -- ${cv.risk_level.toUpperCase()} Risk</div>
            <div class="card-description">GST INR ${fmtNum(cv.gst_total_turnover)} vs Bank INR ${fmtNum(cv.bank_total_credits)} -- ${cv.discrepancy_percentage}% discrepancy</div>
          </div>
        </div>`;
    if (cv.anomalies?.length) {
      html += `<div class="anomaly-list">${cv.anomalies.map(a => `<div class="anomaly-item"><span class="severity-badge ${a.severity}">${a.severity}</span><div><div class="anomaly-text" style="font-weight:600;color:var(--text-primary);">${esc(a.anomaly_type.replace(/_/g, ' '))}</div><div class="anomaly-text">${esc(a.description)}</div></div></div>`).join('')}</div>`;
    }
    if (cv.ai_analysis) html += `<div style="margin-top:14px;font-size:13px;color:var(--text-secondary);white-space:pre-wrap;">${esc(cv.ai_analysis)}</div>`;
    html += `</div>`;
  }

  // ── Research Report ──
  if (data.research_report) {
    const rr = data.research_report;
    html += `
      <div class="glass-card">
        <div class="card-header">
          <div class="card-icon green">${icon('globe')}</div>
          <div>
            <div class="card-title">Research Report -- ${rr.overall_sentiment} sentiment</div>
            <div class="card-description">${esc(rr.ai_summary?.substring(0, 200) || '')}</div>
          </div>
        </div>`;
    if (rr.news_items?.length) {
      html += `<div class="news-list">${rr.news_items.slice(0, 8).map(n => `<div class="news-item"><div class="news-title">${esc(n.title)}</div><div class="news-snippet">${esc(n.snippet?.substring(0, 200) || '')}</div><div class="news-meta"><span class="news-tag category">${n.category}</span><span class="news-tag ${n.sentiment}">${n.sentiment}</span></div></div>`).join('')}</div>`;
    }
    if (rr.risk_flags?.length) {
      html += `<div style="margin-top:14px;"><strong style="font-size:13px;color:var(--danger);">Risk Flags:</strong><div class="tag-list">${rr.risk_flags.map(f => `<span class="tag" style="border-color:var(--danger);color:var(--danger);">${esc(f.substring(0, 100))}</span>`).join('')}</div></div>`;
    }
    html += `</div>`;
  }

  // ── Primary Insights ──
  if (data.primary_insights) {
    const pi = data.primary_insights;
    html += `
      <div class="glass-card">
        <div class="card-header">
          <div class="card-icon amber">${icon('pencil')}</div>
          <div>
            <div class="card-title">Primary Insights Analysis</div>
            <div class="card-description">${pi.insights_processed} observation(s) -- risk delta: ${pi.overall_risk_delta > 0 ? '+' : ''}${pi.overall_risk_delta.toFixed(2)}</div>
          </div>
        </div>
        <div style="font-size:13px;color:var(--text-secondary);white-space:pre-wrap;">${esc(pi.ai_interpretation || '')}</div>
      </div>`;
  }

  // ── Credit Appraisal Memo ──
  if (data.credit_memo) {
    const cam = data.credit_memo;
    html += `
      <div class="glass-card">
        <div class="card-header">
          <div class="card-icon indigo">${icon('filePen')}</div>
          <div>
            <div class="card-title">Credit Appraisal Memo</div>
            <div class="card-description">Generated at ${cam.generated_at || 'N/A'}</div>
          </div>
        </div>`;
    if (cam.executive_summary) html += `<div style="margin-bottom:16px;font-size:13px;color:var(--text-secondary);line-height:1.7;white-space:pre-wrap;">${esc(cam.executive_summary)}</div>`;
    if (cam.sections?.length) {
      html += cam.sections.map((s, i) => `
        <div class="cam-section ${i === 0 ? 'open' : ''}">
          <div class="cam-section-header" onclick="this.parentElement.classList.toggle('open')">
            <span>${esc(s.title)}</span>
            <span class="chevron">&#9660;</span>
          </div>
          <div class="cam-section-body"><div class="cam-section-content">${esc(s.content)}</div></div>
        </div>`).join('');
    }
    html += `</div>`;
  }

  // ── GST & Bank Data ──
  if (data.gst_data || data.bank_statement) {
    html += `<div class="glass-card"><div class="card-header"><div class="card-icon blue">${icon('pieChart')}</div><div><div class="card-title">Parsed Financial Data</div></div></div><div class="stat-grid">`;
    if (data.gst_data) {
      const g = data.gst_data;
      html += `<div class="stat-item"><div class="stat-value">INR ${fmtNum(g.total_turnover)}</div><div class="stat-label">GST Turnover</div></div>
        <div class="stat-item"><div class="stat-value">INR ${fmtNum(g.total_tax_paid)}</div><div class="stat-label">Tax Paid</div></div>
        <div class="stat-item"><div class="stat-value">INR ${fmtNum(g.total_itc_claimed)}</div><div class="stat-label">ITC Claimed</div></div>`;
    }
    if (data.bank_statement) {
      const b = data.bank_statement;
      html += `<div class="stat-item"><div class="stat-value">INR ${fmtNum(b.total_credits)}</div><div class="stat-label">Bank Credits</div></div>
        <div class="stat-item"><div class="stat-value">INR ${fmtNum(b.total_debits)}</div><div class="stat-label">Bank Debits</div></div>
        <div class="stat-item"><div class="stat-value">INR ${fmtNum(b.average_balance)}</div><div class="stat-label">Avg Balance</div></div>`;
    }
    html += `</div></div>`;
  }

  const target = document.getElementById('final-results-container') || resultsDiv;
  target.innerHTML = html;
  resultsDiv.classList.add('visible');
  if (!document.getElementById('final-results-container')) {
    resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

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
