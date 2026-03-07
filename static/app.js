/**
 * Intelli-Credit — Frontend Logic
 *
 * Handles form collection, file uploads via FormData,
 * skeleton loading states, and result rendering.
 */

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

    // Drag events
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

    // File selected
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

function addInsightRow(type = 'general', observation = '', severity = 'neutral') {
    const id = ++insightCounter;
    const row = document.createElement('div');
    row.className = 'insight-entry';
    row.id = `insight-${id}`;
    row.innerHTML = `
    <textarea class="form-textarea" placeholder="Describe your observation…" data-role="observation">${observation}</textarea>
    <select class="form-input" data-role="type">
      <option value="general" ${type === 'general' ? 'selected' : ''}>General</option>
      <option value="factory_visit" ${type === 'factory_visit' ? 'selected' : ''}>Factory Visit</option>
      <option value="management_interview" ${type === 'management_interview' ? 'selected' : ''}>Management Interview</option>
    </select>
    <button class="btn btn-danger btn-sm" onclick="document.getElementById('insight-${id}').remove()" type="button">✕</button>
  `;
    insightList.appendChild(row);
}

addInsight.addEventListener('click', () => addInsightRow());

// Add one default row
addInsightRow();

// ── Collect Insights ────────────────────────────
function collectInsights() {
    const entries = [];
    insightList.querySelectorAll('.insight-entry').forEach(row => {
        const obs = row.querySelector('[data-role="observation"]').value.trim();
        const type = row.querySelector('[data-role="type"]').value;
        if (obs) {
            entries.push({ type, observation: obs, severity: 'neutral' });
        }
    });
    return entries;
}

// ── Run Analysis ────────────────────────────────
runBtn.addEventListener('click', async () => {
    const companyName = document.getElementById('company_name').value.trim();
    if (!companyName) {
        shakeElement(document.getElementById('company_name'));
        return;
    }

    // Build FormData
    const fd = new FormData();
    fd.append('company_name', companyName);
    fd.append('sector', document.getElementById('sector').value.trim());
    fd.append('requested_amount', document.getElementById('requested_amount').value || '0');

    // Promoter names → JSON array
    const promoters = document.getElementById('promoter_names').value
        .split(',')
        .map(s => s.trim())
        .filter(Boolean);
    fd.append('promoter_names', JSON.stringify(promoters));

    // Primary notes → JSON array
    const notes = collectInsights();
    fd.append('primary_notes', JSON.stringify(notes));

    // Files
    const annualFile = document.getElementById('file-annual');
    if (annualFile.files.length) fd.append('annual_report', annualFile.files[0]);

    const gstFile = document.getElementById('file-gst');
    if (gstFile.files.length) fd.append('gst_file', gstFile.files[0]);

    const bankFile = document.getElementById('file-bank');
    if (bankFile.files.length) fd.append('bank_file', bankFile.files[0]);

    // UI → loading
    setLoading(true);

    try {
        const resp = await fetch('/pipeline/full-analysis', {
            method: 'POST',
            body: fd,
        });

        if (!resp.ok) {
            const errText = await resp.text();
            throw new Error(`Server error ${resp.status}: ${errText}`);
        }

        const data = await resp.json();
        renderResults(data);
    } catch (err) {
        resultsDiv.innerHTML = `
      <div class="glass-card" style="border-color:var(--danger);">
        <div class="card-header">
          <div class="card-icon" style="background:var(--danger-bg);font-size:20px;">⚠️</div>
          <div>
            <div class="card-title" style="color:var(--danger);">Analysis Failed</div>
            <div class="card-description">${escapeHtml(err.message)}</div>
          </div>
        </div>
      </div>`;
        resultsDiv.classList.add('visible');
    } finally {
        setLoading(false);
    }
});

// ── Loading State ───────────────────────────────
function setLoading(on) {
    runBtn.disabled = on;
    btnText.textContent = on ? 'Analyzing…' : 'Run Full Analysis';
    btnSpinner.style.display = on ? 'block' : 'none';
    skeleton.classList.toggle('visible', on);
    if (on) {
        resultsDiv.classList.remove('visible');
        resultsDiv.innerHTML = '';
        skeleton.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

// ── Render Results ──────────────────────────────
function renderResults(data) {
    let html = '';

    // Steps progress bar
    html += `<div class="steps-bar">`;
    (data.steps_completed || []).forEach(s => {
        html += `<span class="step-badge">${formatStepName(s)}</span>`;
    });
    (data.errors || []).forEach(e => {
        html += `<span class="step-badge error">${escapeHtml(e)}</span>`;
    });
    html += `</div>`;

    // ── Decision Banner ─────────────────────────
    if (data.loan_decision) {
        const d = data.loan_decision;
        html += `
      <div class="decision-banner ${d.decision}">
        <div class="decision-label">Credit Decision</div>
        <div class="decision-verdict">${d.decision}</div>
        <div class="decision-explanation">${escapeHtml(d.explanation)}</div>
        <div class="decision-meta">
          <div class="meta-item">
            <div class="meta-value">${d.risk_grade || '—'}</div>
            <div class="meta-label">Risk Grade</div>
          </div>
          <div class="meta-item">
            <div class="meta-value">₹${formatNumber(d.recommended_amount)}</div>
            <div class="meta-label">Recommended Amount</div>
          </div>
          <div class="meta-item">
            <div class="meta-value">${d.interest_rate}%</div>
            <div class="meta-label">Interest Rate</div>
          </div>
          <div class="meta-item">
            <div class="meta-value">${d.risk_premium} bps</div>
            <div class="meta-label">Risk Premium</div>
          </div>
          <div class="meta-item">
            <div class="meta-value">${(d.confidence_score * 100).toFixed(0)}%</div>
            <div class="meta-label">Confidence</div>
          </div>
        </div>
      </div>`;

        // Key factors & conditions
        if (d.key_factors?.length || d.conditions?.length) {
            html += `<div class="glass-card">`;
            if (d.key_factors?.length) {
                html += `<div class="card-header"><div class="card-icon indigo">🔑</div><div><div class="card-title">Key Factors</div></div></div>`;
                html += `<div class="tag-list">${d.key_factors.map(f => `<span class="tag">${escapeHtml(f)}</span>`).join('')}</div>`;
            }
            if (d.conditions?.length) {
                html += `<div class="card-header" style="margin-top:16px;"><div class="card-icon amber">📋</div><div><div class="card-title">Conditions</div></div></div>`;
                html += `<div class="tag-list">${d.conditions.map(c => `<span class="tag">${escapeHtml(c)}</span>`).join('')}</div>`;
            }
            html += `</div>`;
        }
    }

    // ── Five Cs Scores ──────────────────────────
    if (data.five_cs_scores?.scores?.length) {
        const cs = data.five_cs_scores;
        html += `
      <div class="glass-card">
        <div class="card-header">
          <div class="card-icon purple">📐</div>
          <div>
            <div class="card-title">Five Cs of Credit — ${cs.weighted_total.toFixed(1)}/100 (${cs.risk_grade})</div>
            <div class="card-description">${escapeHtml(cs.ai_commentary || '')}</div>
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
              ${s.explanation ? `<div class="score-explanation">${escapeHtml(s.explanation)}</div>` : ''}`;
        }).join('')}
        </div>
      </div>`;
    }

    // ── Document Analysis ───────────────────────
    if (data.document_analysis) {
        const da = data.document_analysis;
        html += `
      <div class="glass-card">
        <div class="card-header">
          <div class="card-icon blue">📊</div>
          <div>
            <div class="card-title">Document Analysis — ${escapeHtml(da.file_name)}</div>
            <div class="card-description">${escapeHtml(da.summary || '')}</div>
          </div>
        </div>`;

        // Financial metrics
        const f = da.financials;
        if (f) {
            const metrics = [
                { label: 'Revenue', value: f.revenue },
                { label: 'Net Profit', value: f.net_profit },
                { label: 'Total Debt', value: f.total_debt },
                { label: 'EBITDA', value: f.ebitda },
                { label: 'Debt/Equity', value: f.debt_to_equity },
                { label: 'Current Ratio', value: f.current_ratio },
                { label: 'ICR', value: f.interest_coverage },
            ].filter(m => m.value != null);

            if (metrics.length) {
                html += `<div class="stat-grid">${metrics.map(m => `
          <div class="stat-item">
            <div class="stat-value">${typeof m.value === 'number' && m.value > 1000 ? '₹' + formatNumber(m.value) : m.value}</div>
            <div class="stat-label">${m.label}</div>
          </div>`).join('')}</div>`;
            }
        }

        // Risks
        if (da.risks) {
            const allRisks = [
                ...(da.risks.key_risks || []).map(r => ({ text: r, type: 'Key Risk' })),
                ...(da.risks.contingent_liabilities || []).map(r => ({ text: r, type: 'Contingent Liability' })),
                ...(da.risks.auditor_qualifications || []).map(r => ({ text: r, type: 'Auditor Qualification' })),
            ];
            if (allRisks.length) {
                html += `<div class="anomaly-list" style="margin-top:16px;">${allRisks.map(r => `
          <div class="anomaly-item">
            <span class="severity-badge medium">${r.type}</span>
            <span class="anomaly-text">${escapeHtml(r.text)}</span>
          </div>`).join('')}</div>`;
            }
        }
        html += `</div>`;
    }

    // ── Cross Verification ──────────────────────
    if (data.cross_verification) {
        const cv = data.cross_verification;
        html += `
      <div class="glass-card">
        <div class="card-header">
          <div class="card-icon amber">🔍</div>
          <div>
            <div class="card-title">Cross-Verification — ${cv.risk_level.toUpperCase()} Risk</div>
            <div class="card-description">GST ₹${formatNumber(cv.gst_total_turnover)} vs Bank ₹${formatNumber(cv.bank_total_credits)} — ${cv.discrepancy_percentage}% discrepancy</div>
          </div>
        </div>`;

        if (cv.anomalies?.length) {
            html += `<div class="anomaly-list">${cv.anomalies.map(a => `
        <div class="anomaly-item">
          <span class="severity-badge ${a.severity}">${a.severity}</span>
          <div>
            <div class="anomaly-text" style="font-weight:600;color:var(--text-primary);">${escapeHtml(a.anomaly_type.replace(/_/g, ' '))}</div>
            <div class="anomaly-text">${escapeHtml(a.description)}</div>
          </div>
        </div>`).join('')}</div>`;
        }

        if (cv.ai_analysis) {
            html += `<div style="margin-top:14px;font-size:13px;color:var(--text-secondary);white-space:pre-wrap;">${escapeHtml(cv.ai_analysis)}</div>`;
        }
        html += `</div>`;
    }

    // ── Research Report ─────────────────────────
    if (data.research_report) {
        const rr = data.research_report;
        html += `
      <div class="glass-card">
        <div class="card-header">
          <div class="card-icon green">🌐</div>
          <div>
            <div class="card-title">Research Report — ${rr.overall_sentiment} sentiment</div>
            <div class="card-description">${escapeHtml(rr.ai_summary?.substring(0, 200) || '')}</div>
          </div>
        </div>`;

        if (rr.news_items?.length) {
            html += `<div class="news-list">${rr.news_items.slice(0, 8).map(n => `
        <div class="news-item">
          <div class="news-title">${escapeHtml(n.title)}</div>
          <div class="news-snippet">${escapeHtml(n.snippet?.substring(0, 200) || '')}</div>
          <div class="news-meta">
            <span class="news-tag category">${n.category}</span>
            <span class="news-tag ${n.sentiment}">${n.sentiment}</span>
          </div>
        </div>`).join('')}</div>`;
        }

        // Risk flags
        if (rr.risk_flags?.length) {
            html += `<div style="margin-top:14px;"><strong style="font-size:13px;color:var(--danger);">Risk Flags:</strong>
        <div class="tag-list">${rr.risk_flags.map(f => `<span class="tag" style="border-color:var(--danger);color:var(--danger);">${escapeHtml(f.substring(0, 100))}</span>`).join('')}</div></div>`;
        }
        html += `</div>`;
    }

    // ── Primary Insights Response ───────────────
    if (data.primary_insights) {
        const pi = data.primary_insights;
        html += `
      <div class="glass-card">
        <div class="card-header">
          <div class="card-icon amber">✍️</div>
          <div>
            <div class="card-title">Primary Insights Analysis</div>
            <div class="card-description">${pi.insights_processed} observation(s) processed — risk delta: ${pi.overall_risk_delta > 0 ? '+' : ''}${pi.overall_risk_delta.toFixed(2)}</div>
          </div>
        </div>
        <div style="font-size:13px;color:var(--text-secondary);white-space:pre-wrap;">${escapeHtml(pi.ai_interpretation || '')}</div>
      </div>`;
    }

    // ── Credit Appraisal Memo ───────────────────
    if (data.credit_memo) {
        const cam = data.credit_memo;
        html += `
      <div class="glass-card">
        <div class="card-header">
          <div class="card-icon indigo">📝</div>
          <div>
            <div class="card-title">Credit Appraisal Memo</div>
            <div class="card-description">Generated at ${cam.generated_at || 'N/A'}</div>
          </div>
        </div>`;

        // Executive summary
        if (cam.executive_summary) {
            html += `<div style="margin-bottom:16px;font-size:13px;color:var(--text-secondary);line-height:1.7;white-space:pre-wrap;">${escapeHtml(cam.executive_summary)}</div>`;
        }

        // Expandable sections
        if (cam.sections?.length) {
            html += cam.sections.map((s, i) => `
        <div class="cam-section ${i === 0 ? 'open' : ''}">
          <div class="cam-section-header" onclick="this.parentElement.classList.toggle('open')">
            <span>${escapeHtml(s.title)}</span>
            <span class="chevron">▼</span>
          </div>
          <div class="cam-section-body">
            <div class="cam-section-content">${escapeHtml(s.content)}</div>
          </div>
        </div>`).join('');
        }
        html += `</div>`;
    }

    // ── GST & Bank Statement Details ────────────
    if (data.gst_data || data.bank_statement) {
        html += `<div class="glass-card"><div class="card-header"><div class="card-icon blue">📋</div><div><div class="card-title">Parsed Financial Data</div></div></div><div class="stat-grid">`;

        if (data.gst_data) {
            const g = data.gst_data;
            html += `
        <div class="stat-item"><div class="stat-value">₹${formatNumber(g.total_turnover)}</div><div class="stat-label">GST Turnover</div></div>
        <div class="stat-item"><div class="stat-value">₹${formatNumber(g.total_tax_paid)}</div><div class="stat-label">Tax Paid</div></div>
        <div class="stat-item"><div class="stat-value">₹${formatNumber(g.total_itc_claimed)}</div><div class="stat-label">ITC Claimed</div></div>`;
        }
        if (data.bank_statement) {
            const b = data.bank_statement;
            html += `
        <div class="stat-item"><div class="stat-value">₹${formatNumber(b.total_credits)}</div><div class="stat-label">Bank Credits</div></div>
        <div class="stat-item"><div class="stat-value">₹${formatNumber(b.total_debits)}</div><div class="stat-label">Bank Debits</div></div>
        <div class="stat-item"><div class="stat-value">₹${formatNumber(b.average_balance)}</div><div class="stat-label">Avg Balance</div></div>`;
        }
        html += `</div></div>`;
    }

    resultsDiv.innerHTML = html;
    resultsDiv.classList.add('visible');
    resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // Animate score bars after render
    requestAnimationFrame(() => {
        document.querySelectorAll('.score-bar-fill').forEach(bar => {
            const w = bar.style.width;
            bar.style.width = '0%';
            requestAnimationFrame(() => { bar.style.width = w; });
        });
    });
}

// ── Utilities ───────────────────────────────────
function escapeHtml(text) {
    const el = document.createElement('span');
    el.textContent = text || '';
    return el.innerHTML;
}

function formatNumber(n) {
    if (n == null || isNaN(n)) return '0';
    // Indian numbering system
    return Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 });
}

function formatStepName(step) {
    return step.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function shakeElement(el) {
    el.style.outline = '2px solid var(--danger)';
    el.style.animation = 'none';
    el.offsetHeight; // reflow
    el.style.animation = 'shake 0.4s ease';
    setTimeout(() => {
        el.style.outline = '';
        el.style.animation = '';
        el.focus();
    }, 500);
}

// Shake keyframes injected via JS
const style = document.createElement('style');
style.textContent = `@keyframes shake { 0%,100% { transform: translateX(0); } 25% { transform: translateX(-6px); } 75% { transform: translateX(6px); } }`;
document.head.appendChild(style);
