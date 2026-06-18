"""
CDD Predictor — Flask web server
Run:  python3 server.py
Then open:  http://localhost:5050
"""

from flask import Flask, request, render_template_string
from tree_map import generate_result, _e
import json, html

app = Flask(__name__)

# ── Form page ──────────────────────────────────────────────────────────────────

FORM_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>CDD Predictor — New Project</title>
  <style>
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
    body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#F1F5F9;color:#1E293B;min-height:100vh;display:flex;flex-direction:column}
    header{background:#0F172A;padding:14px 32px;display:flex;align-items:baseline;gap:14px}
    .app-title{color:#F8FAFC;font-size:16px;font-weight:700}
    .app-sub{color:#475569;font-size:12px}
    main{flex:1;display:flex;align-items:center;justify-content:center;padding:40px 16px}
    .card{background:#fff;border:1px solid #E2E8F0;border-radius:16px;padding:36px 40px;width:100%;max-width:600px;box-shadow:0 4px 24px rgba(0,0,0,.06)}
    .card-title{font-size:18px;font-weight:700;margin-bottom:4px}
    .card-sub{font-size:12px;color:#64748B;margin-bottom:28px}
    label{display:block;font-size:11px;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:.07em;margin-bottom:5px}
    .field{margin-bottom:20px}
    input,textarea{width:100%;border:1px solid #CBD5E1;border-radius:8px;padding:10px 12px;font-size:13px;color:#1E293B;font-family:inherit;transition:border .15s,box-shadow .15s;background:#F8FAFC}
    input:focus,textarea:focus{outline:none;border-color:#2563EB;box-shadow:0 0 0 3px #2563EB20;background:#fff}
    textarea{resize:vertical;min-height:80px}
    .hint{font-size:11px;color:#94A3B8;margin-top:4px}
    .btn-submit{width:100%;padding:12px;background:#0F172A;color:#F8FAFC;border:none;border-radius:8px;font-size:14px;font-weight:700;cursor:pointer;letter-spacing:.02em;transition:background .15s;margin-top:4px}
    .btn-submit:hover{background:#1E293B}
    .divider{border:none;border-top:1px solid #E2E8F0;margin:24px 0}
  </style>
</head>
<body>
  <header>
    <span class="app-title">CDD Predictor</span>
    <span class="app-sub">GLG Korea · Commercial Due Diligence · Hypothesis Framework</span>
  </header>
  <main>
    <div class="card">
      <div class="card-title">New CDD Project</div>
      <div class="card-sub">Fill in the engagement context — the model will generate a hypothesis tree ordered by keyword signal.</div>
      <hr class="divider">
      <form method="POST" action="/generate">
        <div class="field">
          <label>Project Name</label>
          <input name="proj_name" placeholder="e.g. US Golf Club M&amp;A Assessment" required>
        </div>
        <div class="field">
          <label>Client (Consulting Firm)</label>
          <input name="client" placeholder="e.g. Glenwood Credit" required>
        </div>
        <div class="field">
          <label>Reference Company <span style="font-weight:400;text-transform:none">(industry anchor — not the M&amp;A target)</span></label>
          <input name="reference_company" placeholder="e.g. KSL Capital, Arcis, Concert Golf" required>
        </div>
        <div class="field">
          <label>What the Client Wants to Learn</label>
          <textarea name="client_wants" placeholder="e.g. Understand how pricing and demand dynamics work across private golf club operators..."></textarea>
        </div>
        <div class="field">
          <label>Verify / Screening Questions</label>
          <textarea name="verify_questions" placeholder="e.g. Has the expert worked in club operations? Can they speak to membership dues and initiation fees?"></textarea>
          <div class="hint">Used to detect keyword signals and order scenarios.</div>
        </div>
        <button class="btn-submit" type="submit">Generate Hypothesis Tree →</button>
      </form>
    </div>
  </main>
</body>
</html>"""


# ── Result page ────────────────────────────────────────────────────────────────

RESULT_CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:14px;background:#F1F5F9;color:#1E293B}
header{background:#0F172A;padding:12px 32px;display:flex;align-items:center;justify-content:space-between;gap:14px}
.header-left{display:flex;align-items:baseline;gap:14px}
.app-title{color:#F8FAFC;font-size:16px;font-weight:700}
.app-sub{color:#475569;font-size:12px}
.btn-new{padding:6px 14px;background:#1E293B;color:#94A3B8;border:1px solid #334155;border-radius:6px;font-size:11px;font-weight:600;cursor:pointer;text-decoration:none;transition:all .15s}
.btn-new:hover{background:#334155;color:#E2E8F0}
.content{padding:28px 32px;max-width:1280px;margin:0 auto}
.project-bar{display:flex;align-items:center;gap:10px;margin-bottom:12px;flex-wrap:wrap}
.project-pill{background:#0F172A;color:#94A3B8;font-size:10px;font-weight:700;padding:2px 8px;border-radius:4px;text-transform:uppercase;letter-spacing:.07em}
.project-name{font-size:18px;font-weight:700}
.project-meta{font-size:12px;color:#64748B}
.cdd-warning{display:flex;align-items:flex-start;gap:8px;background:#FFFBEB;border:1px solid #FDE68A;border-radius:8px;padding:10px 14px;margin-bottom:14px;font-size:12px;color:#92400E;line-height:1.5}
.issue-banner{display:flex;align-items:flex-start;gap:10px;background:#0F172A;border-radius:8px;padding:12px 16px;margin-bottom:20px}
.issue-label{flex-shrink:0;background:#1E293B;color:#94A3B8;font-size:9px;font-weight:700;padding:2px 6px;border-radius:3px;text-transform:uppercase;letter-spacing:.1em;margin-top:1px}
.issue-text{color:#E2E8F0;font-size:13px;line-height:1.55}
/* Tree */
.tree-container{background:#fff;border:1px solid #E2E8F0;border-radius:12px;padding:20px;margin-bottom:24px;overflow:hidden}
.tree-label{font-size:11px;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:.07em;margin-bottom:14px}
.hyp-node{cursor:pointer;transition:filter .15s}
.hyp-node:hover{filter:brightness(1.15)}
/* Score bar */
.score-bar-row{display:flex;gap:14px;margin-bottom:20px;flex-wrap:wrap}
.score-pill{display:flex;align-items:center;gap:7px;background:#fff;border:1px solid #E2E8F0;border-radius:8px;padding:8px 12px}
.score-label{font-size:10px;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:.06em}
.score-track{width:80px;height:6px;background:#F1F5F9;border-radius:3px;overflow:hidden}
.score-fill{height:100%;border-radius:3px}
.score-num{font-size:11px;font-weight:700;color:#1E293B}
/* Scenarios */
.scenarios-header-row{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}
.section-label{font-size:11px;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:.07em}
.export-csv-btn{padding:6px 14px;background:#0F172A;color:#94A3B8;border:none;border-radius:6px;font-size:11px;font-weight:600;cursor:pointer;transition:all .15s}
.export-csv-btn:hover{background:#1E293B;color:#E2E8F0}
.mece-gate-error{background:#FEF2F2;border:1px solid #FECACA;border-radius:6px;padding:8px 12px;font-size:12px;color:#DC2626;margin-bottom:10px}
.scenario-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}
.scenario-card{background:#fff;border:1px solid #E2E8F0;border-radius:12px;padding:18px;display:flex;flex-direction:column;gap:12px;transition:opacity .2s,box-shadow .2s;scroll-margin-top:20px}
.scenario-card:hover{box-shadow:0 4px 16px rgba(0,0,0,.08)}
.scenario-card.highlighted{box-shadow:0 0 0 3px #2563EB55;animation:pulse .6s ease}
@keyframes pulse{0%{box-shadow:0 0 0 0 #2563EB55}50%{box-shadow:0 0 0 6px #2563EB22}100%{box-shadow:0 0 0 3px #2563EB55}}
.scenario-card.rejected{opacity:.45}
.scenario-card.deleted{display:none}
.so-what-block{display:flex;align-items:flex-start;gap:8px;background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:10px 12px}
.so-what-label{flex-shrink:0;font-size:9px;font-weight:700;color:#94A3B8;text-transform:uppercase;letter-spacing:.1em;margin-top:2px}
.so-what-text{font-size:13px;font-weight:700;color:#0F172A;line-height:1.4}
.scenario-header{display:flex;flex-direction:column;gap:6px}
.scenario-top-row{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.scenario-badge{font-size:10px;font-weight:700;padding:3px 9px;border-radius:4px;text-transform:uppercase;letter-spacing:.06em;color:#fff}
.rejected-stamp{font-size:10px;color:#EF4444;font-weight:600;background:#FEF2F2;padding:2px 7px;border-radius:4px;border:1px solid #FECACA}
.node-label{display:inline-block;font-size:9px;font-weight:700;padding:2px 6px;border-radius:3px;text-transform:uppercase;letter-spacing:.08em}
.nl-hyp{background:#EFF6FF;color:#1D4ED8}
.nl-sub{background:#F0FDF4;color:#166534}
.nl-confirm{background:#FFF7ED;color:#92400E}
.nl-kill{background:#FEF2F2;color:#DC2626}
.hyp-block{display:flex;flex-direction:column;gap:5px}
.hyp-text{font-size:13px;font-weight:600;line-height:1.5;color:#1E293B}
.rejected .hyp-text{text-decoration:line-through;text-decoration-color:#64748B}
.mece-badge{display:flex;align-items:flex-start;gap:5px;padding:6px 10px;border-radius:6px;font-size:11px}
.mece-ok{background:#F0FDF4;border:1px solid #BBF7D0;color:#166534}
.mece-icon{font-size:12px;flex-shrink:0}
.trigger-row{display:flex;flex-direction:column;gap:5px}
.trigger-label{font-size:10px;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:.06em}
.kw-list{display:flex;flex-wrap:wrap;gap:4px}
.kw{background:#FEF9C3;color:#92400E;font-size:11px;font-weight:500;padding:2px 7px;border-radius:4px;border:1px solid #FDE68A}
.sh-list{display:flex;flex-direction:column;gap:10px;border-top:1px solid #E2E8F0;padding-top:12px}
.sh-block{display:flex;flex-direction:column;gap:6px}
.sh-header{display:flex;align-items:flex-start;gap:8px}
.sh-index{width:22px;height:22px;border-radius:50%;background:#F1F5F9;border:1px solid #E2E8F0;color:#64748B;font-size:11px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:1px}
.sh-content{display:flex;flex-direction:column;gap:4px}
.sh-text{font-size:12px;font-weight:600;color:#1E293B;line-height:1.45}
.sh-leaf{margin-left:30px;display:flex;flex-direction:column;gap:5px;background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:8px 10px}
.sh-kill{background:#FEF2F2;border-color:#FECACA}
.leaf-row{display:flex;align-items:flex-start;gap:6px}
.leaf-evidence{font-size:11px;color:#64748B;line-height:1.45}
.leaf-expert-row{display:flex;align-items:flex-start;gap:8px;flex-wrap:wrap}
.expert-chip{display:inline-block;font-size:11px;font-weight:700;padding:2px 9px;border-radius:4px;white-space:nowrap;flex-shrink:0}
.expert-chip-kill{display:inline-block;font-size:11px;font-weight:700;padding:2px 9px;border-radius:4px;white-space:nowrap;flex-shrink:0;background:#FEF2F2;color:#DC2626;border:1px solid #FECACA}
.why-text{font-size:11px;color:#64748B;line-height:1.45}
.why-label{font-weight:700;color:#94A3B8;font-size:9px;text-transform:uppercase;letter-spacing:.08em;margin-right:2px}
.scenario-actions{display:flex;gap:8px;border-top:1px solid #E2E8F0;padding-top:12px;margin-top:4px}
.btn-reject{flex:1;padding:7px 12px;border:1px solid #CBD5E1;background:white;color:#64748B;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;transition:all .15s}
.btn-reject:hover:not(:disabled){background:#F1F5F9;border-color:#94A3B8}
.btn-reject:disabled{background:#F8FAFC;color:#94A3B8;cursor:default}
.btn-delete-red{padding:7px 14px;border:1px solid #FECACA;background:white;color:#DC2626;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;transition:all .15s}
.btn-delete-red:hover{background:#FEF2F2;border-color:#FCA5A5}
.vd-tag{font-size:10px;font-weight:700;padding:2px 8px;border-radius:4px;text-transform:uppercase;letter-spacing:.06em}
.prob-chip{font-size:11px;font-weight:700;padding:2px 9px;border-radius:4px;background:#F1F5F9;color:#1E293B;border:1px solid #E2E8F0}
.scenario-title{font-size:15px;font-weight:700;color:#0F172A;line-height:1.35;padding:2px 0 4px}
.score-no-signal{font-size:12px;color:#64748B;font-style:italic;padding:8px 12px;background:#fff;border:1px solid #E2E8F0;border-radius:8px}
/* ── Drill-down progressive reveal ─────────────────────────────────── */
.drill-confirm-btn{width:100%;padding:10px 14px;background:#0F172A;color:#F8FAFC;border:none;border-radius:8px;font-size:13px;font-weight:700;cursor:pointer;transition:background .15s}
.drill-confirm-btn:hover{background:#1E293B}
.drill-zone{flex-direction:column;gap:10px;border-top:1px solid #E2E8F0;padding-top:12px;margin-top:2px}
.drill-progress{font-size:10px;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:.07em}
.sub-h-reveal{display:flex;flex-direction:column;gap:6px}
.sub-h-actions{display:flex;gap:8px;margin-top:6px;margin-left:30px}
.btn-remain{flex:1;padding:7px 12px;border:1px solid #BBF7D0;background:#F0FDF4;color:#166534;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;transition:all .15s}
.btn-remain:hover{background:#DCFCE7}
.btn-del-sub{padding:7px 14px;border:1px solid #FECACA;background:#FEF2F2;color:#DC2626;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;transition:all .15s}
.btn-del-sub:hover{background:#FEE2E2}
.expert-choice-row{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:2px}
.expert-card{border:1px solid #E2E8F0;border-radius:8px;padding:12px 14px;display:flex;flex-direction:column;gap:8px;cursor:pointer;transition:box-shadow .15s,border-color .15s;background:#fff}
.expert-card:hover{box-shadow:0 2px 10px rgba(0,0,0,.1)}
.expert-card-label{font-size:9px;font-weight:700;padding:2px 6px;border-radius:3px;text-transform:uppercase;letter-spacing:.08em;display:inline-block;align-self:flex-start}
.kill-label{background:#FEF2F2;color:#DC2626;border:1px solid #FECACA}
.expert-card-title{font-size:12px;font-weight:700;color:#0F172A;line-height:1.35}
.expert-card-evidence{font-size:11px;color:#64748B;line-height:1.5;flex:1}
.expert-card-why{font-size:11px;color:#64748B;line-height:1.45;padding-top:2px}
.btn-choose-expert{width:100%;padding:7px 10px;border:none;border-radius:6px;font-size:11px;font-weight:700;cursor:pointer;transition:opacity .15s;margin-top:auto;color:#fff}
.btn-choose-expert:hover{opacity:.88}
.btn-kill-expert{background:#DC2626}
.drill-done{background:#F0FDF4;border:1px solid #BBF7D0;border-radius:8px;padding:12px 14px;display:flex;flex-direction:column;gap:6px}
.drill-done-title{font-size:10px;font-weight:700;color:#166534;text-transform:uppercase;letter-spacing:.07em;margin-bottom:2px}
.choice-row{display:flex;align-items:center;gap:8px}
.choice-idx{width:20px;height:20px;border-radius:50%;background:#E2E8F0;color:#64748B;font-size:10px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.choice-type{font-size:9px;font-weight:700;padding:2px 6px;border-radius:3px;text-transform:uppercase;letter-spacing:.05em}
.choice-confirm{background:#FFF7ED;color:#92400E;border:1px solid #FDE68A}
.choice-kill{background:#FEF2F2;color:#DC2626;border:1px solid #FECACA}
.choice-name{font-size:12px;color:#1E293B;font-weight:600}
.drill-skip-note{font-size:11px;color:#94A3B8;font-style:italic;margin-top:2px}
"""

RESULT_JS = """
const LOG_KEY = 'cdd_rejection_log';
window.CDD_DATA = {{ cdd_data_json }};

const SCENARIOS = {};
for (const s of window.CDD_DATA.scenarios) { SCENARIOS[s.template_id] = s; }
const drillState = {};

function loadLog(){try{return JSON.parse(localStorage.getItem(LOG_KEY)||'{}');}catch{return{};}}
function saveLog(l){localStorage.setItem(LOG_KEY,JSON.stringify(l));}

function highlightCard(tid){
  const card=document.getElementById('card-'+tid);
  if(!card)return;
  card.classList.remove('highlighted');
  void card.offsetWidth;
  card.classList.add('highlighted');
  card.scrollIntoView({behavior:'smooth',block:'center'});
  setTimeout(()=>card.classList.remove('highlighted'),1500);
}

function rejectScenario(tid,btn){
  const card=document.getElementById('card-'+tid);
  const stamp=document.getElementById('stamp-'+tid);
  const hyp=document.getElementById('hyp-'+tid);
  card.classList.add('rejected');
  if(hyp)hyp.style.textDecoration='line-through';
  stamp.textContent='Rejected · '+new Date().toLocaleString();
  stamp.style.display='inline';
  btn.textContent='Rejected ✓';
  btn.disabled=true;
  const log=loadLog();log[tid]=new Date().toISOString();saveLog(log);
  document.querySelectorAll('.hyp-node[data-id="'+tid+'"]').forEach(n=>n.setAttribute('opacity','0.35'));
}

function deleteScenario(tid){
  if(!confirm('Delete this scenario? No record will be saved.'))return;
  document.getElementById('card-'+tid).classList.add('deleted');
  document.querySelectorAll('.hyp-node[data-id="'+tid+'"]').forEach(n=>{n.style.opacity='0.08';});
}

function exportCSV(){
  const log=loadLog();const rows=[];
  for(const s of window.CDD_DATA.scenarios){
    const card=document.getElementById('card-'+s.template_id);
    const del=card&&card.classList.contains('deleted');
    const rej=Object.prototype.hasOwnProperty.call(log,s.template_id);
    const status=del?'deleted':rej?'rejected':'active';
    for(const sh of s.sub_hypotheses)
      rows.push([s.name,s.value_driver,sh.text,sh.confirm_evidence,sh.confirm_expert,sh.kill_evidence,sh.kill_expert,status]);
  }
  const h=['Scenario','Value_Driver','Sub_Hypothesis','Confirm_Evidence','Confirm_Expert','Kill_Evidence','Kill_Expert','Status'];
  const lines=[h.join(','),...rows.map(r=>r.map(v=>'"'+String(v||'').replace(/"/g,'""')+'"').join(','))];
  const blob=new Blob(['\\uFEFF'+lines.join('\\n')],{type:'text/csv;charset=utf-8;'});
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a');a.href=url;a.download='cdd_output.csv';a.click();
  URL.revokeObjectURL(url);
}

function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}

function confirmHypothesis(tid){
  const btn=document.getElementById('btn-confirm-'+tid);
  if(btn)btn.style.display='none';
  const zone=document.getElementById('drill-'+tid);
  if(zone)zone.style.display='flex';
  drillState[tid]={subIdx:0,phase:'sub',choices:[]};
  renderDrillZone(tid);
}

function renderDrillZone(tid){
  const st=drillState[tid];
  const s=SCENARIOS[tid];
  const zone=document.getElementById('drill-'+tid);
  if(!zone||!st)return;
  const n=st.subIdx+1;
  const total=s.sub_hypotheses.length;

  if(st.phase==='sub'){
    const sh=s.sub_hypotheses[st.subIdx];
    zone.innerHTML=`
<div class="drill-progress">Sub-hypothesis ${n} of ${total}</div>
<div class="sub-h-reveal">
  <div class="sh-header">
    <div class="sh-index">${n}</div>
    <div class="sh-content">
      <span class="node-label nl-sub">Sub-hypothesis</span>
      <p class="sh-text">${esc(sh.text)}</p>
    </div>
  </div>
  <div class="sub-h-actions">
    <button class="btn-remain" onclick="remainSub('${tid}')">Remain</button>
    <button class="btn-del-sub" onclick="deleteSub('${tid}')">Delete</button>
  </div>
</div>`;

  }else if(st.phase==='expert'){
    const sh=s.sub_hypotheses[st.subIdx];
    const cec=sh.confirm_expert_color||'#2563EB';
    const why=sh.rationale?`<div class="expert-card-why"><span class="why-label">WHY&nbsp;</span>${esc(sh.rationale)}</div>`:'';
    zone.innerHTML=`
<div class="drill-progress">Sub-hypothesis ${n} of ${total} · Choose expert</div>
<div class="sub-h-reveal">
  <div class="sh-header">
    <div class="sh-index">${n}</div>
    <div class="sh-content">
      <span class="node-label nl-sub">Sub-hypothesis</span>
      <p class="sh-text">${esc(sh.text)}</p>
    </div>
  </div>
</div>
<div class="expert-choice-row">
  <div class="expert-card expert-card-confirm" style="border-color:${cec}55" onclick="chooseExpert('${tid}','confirm')">
    <span class="expert-card-label" style="background:${cec}18;color:${cec};border:1px solid ${cec}44">Confirm Expert</span>
    <div class="expert-card-title">${esc(sh.confirm_expert)}</div>
    <div class="expert-card-evidence">${esc(sh.confirm_evidence)}</div>
    ${why}
    <button class="btn-choose-expert" style="background:${cec}">Choose Confirm Expert</button>
  </div>
  <div class="expert-card expert-card-kill" onclick="chooseExpert('${tid}','kill')">
    <span class="expert-card-label kill-label">Kill Expert</span>
    <div class="expert-card-title">${esc(sh.kill_expert)}</div>
    <div class="expert-card-evidence">${esc(sh.kill_evidence)}</div>
    <button class="btn-choose-expert btn-kill-expert">Choose Kill Expert</button>
  </div>
</div>`;

  }else if(st.phase==='done'){
    let rows='';
    for(const c of st.choices){
      const sh=s.sub_hypotheses[c.subIdx];
      const label=c.choice==='confirm'?sh.confirm_expert:sh.kill_expert;
      const cls=c.choice==='confirm'?'choice-confirm':'choice-kill';
      const lbl=c.choice==='confirm'?'CONFIRM':'KILL';
      rows+=`<div class="choice-row"><span class="choice-idx">${c.subIdx+1}</span><span class="choice-type ${cls}">${lbl}</span><span class="choice-name">${esc(label)}</span></div>`;
    }
    const skipped=total-st.choices.length;
    const skipNote=skipped>0?`<div class="drill-skip-note">${skipped} sub-hypothesis${skipped>1?'es':''} skipped</div>`:'';
    zone.innerHTML=`
<div class="drill-done">
  <div class="drill-done-title">Expert selection complete</div>
  ${rows}${skipNote}
</div>`;
  }
}

function remainSub(tid){drillState[tid].phase='expert';renderDrillZone(tid);}

function deleteSub(tid){
  const st=drillState[tid];
  const total=SCENARIOS[tid].sub_hypotheses.length;
  st.subIdx++;
  st.phase=st.subIdx>=total?'done':'sub';
  renderDrillZone(tid);
}

function chooseExpert(tid,choice){
  const st=drillState[tid];
  st.choices.push({subIdx:st.subIdx,choice:choice});
  const total=SCENARIOS[tid].sub_hypotheses.length;
  st.subIdx++;
  st.phase=st.subIdx>=total?'done':'sub';
  renderDrillZone(tid);
}

(function(){
  const log=loadLog();
  for(const [tid,ts] of Object.entries(log)){
    const card=document.getElementById('card-'+tid);if(!card)continue;
    card.classList.add('rejected');
    const stamp=document.getElementById('stamp-'+tid);
    if(stamp){stamp.textContent='Rejected · '+new Date(ts).toLocaleString();stamp.style.display='inline';}
    const btn=document.getElementById('btn-reject-'+tid);
    if(btn){btn.textContent='Rejected ✓';btn.disabled=true;}
    const hyp=document.getElementById('hyp-'+tid);
    if(hyp)hyp.style.textDecoration='line-through';
  }
})();
"""


def render_svg_tree(issue, scenarios):
    SVG_W, SVG_H = 960, 240
    ROOT_CX = SVG_W // 2
    ISSUE_Y, ISSUE_W, ISSUE_H = 20, 700, 54
    HYP_Y, HYP_W, HYP_H = 148, 240, 60
    ELBOW_Y = 118

    count = len(scenarios)
    if count > 1:
        gap = (SVG_W - 80 * 2 - HYP_W * count) / (count - 1)
        centers = [80 + HYP_W / 2 + i * (HYP_W + gap) for i in range(count)]
    else:
        centers = [ROOT_CX]

    parts = []

    # Issue node
    ix = ROOT_CX - ISSUE_W // 2
    trunc = _e(issue[:115] + ('…' if len(issue) > 115 else ''))
    parts.append(f'<rect x="{ix}" y="{ISSUE_Y}" width="{ISSUE_W}" height="{ISSUE_H}" rx="10" fill="#0F172A"/>')
    parts.append(f'<text x="{ROOT_CX}" y="{ISSUE_Y+16}" text-anchor="middle" fill="#475569" font-size="9" font-weight="700" letter-spacing="0.1em">ISSUE</text>')
    parts.append(f'<text x="{ROOT_CX}" y="{ISSUE_Y+34}" text-anchor="middle" fill="#E2E8F0" font-size="11.5">{trunc}</text>')

    for i, scenario in enumerate(scenarios):
        if not scenario['mece_valid']:
            continue
        cx = centers[i]
        rx = cx - HYP_W / 2
        color = scenario['color']
        tid = _e(scenario['template_id'])
        kws = scenario['trigger_keywords']
        kw_text = f'↑ {", ".join(kws[:2])}' if kws else ''

        # Connector with elbow
        parts.append(
            f'<path d="M {ROOT_CX} {ISSUE_Y+ISSUE_H} '
            f'L {ROOT_CX} {ELBOW_Y} '
            f'L {cx:.1f} {ELBOW_Y} '
            f'L {cx:.1f} {HYP_Y}" '
            f'fill="none" stroke="#CBD5E1" stroke-width="1.5" stroke-dasharray="0"/>'
        )

        # Scenario node — clicking scrolls to card
        parts.append(
            f'<rect x="{rx:.1f}" y="{HYP_Y}" width="{HYP_W}" height="{HYP_H}" rx="10" '
            f'fill="{color}" class="hyp-node" data-id="{tid}" '
            f'onclick="highlightCard(\'{tid}\')" tabindex="0" role="button" '
            f'aria-label="Go to {_e(scenario["name"])} scenario"/>'
        )
        parts.append(f'<text x="{cx:.1f}" y="{HYP_Y+15}" text-anchor="middle" fill="rgba(255,255,255,.65)" font-size="9" font-weight="700" letter-spacing="0.09em" pointer-events="none">SCENARIO {scenario["id"]}</text>')
        parts.append(f'<text x="{cx:.1f}" y="{HYP_Y+34}" text-anchor="middle" fill="white" font-size="13" font-weight="700" pointer-events="none">{_e(scenario["name"])}</text>')
        if kw_text:
            parts.append(f'<text x="{cx:.1f}" y="{HYP_Y+52}" text-anchor="middle" fill="rgba(255,255,255,.7)" font-size="9.5" pointer-events="none">{_e(kw_text)}</text>')

    parts.append(f'<text x="{SVG_W//2}" y="{SVG_H-5}" text-anchor="middle" fill="#94A3B8" font-size="10">Click a node to jump to that scenario ↓</text>')

    return f'<svg viewBox="0 0 {SVG_W} {SVG_H}" xmlns="http://www.w3.org/2000/svg" style="width:100%;display:block">\n  ' + '\n  '.join(parts) + '\n</svg>'


def render_score_bars(probabilities, zero_signal):
    if zero_signal:
        return '<div class="score-bar-row"><span class="score-no-signal">Insufficient keyword signal — scenarios ranked by default order</span></div>'
    color_map = {'market_dynamics': '#2563EB', 'operational_model': '#059669', 'competitive_movement': '#D97706'}
    label_map = {'market_dynamics': 'Market Dynamics', 'operational_model': 'Operational Model', 'competitive_movement': 'Competitive Movement'}
    parts = []
    for key, prob in sorted(probabilities.items(), key=lambda x: -x[1]):
        color = color_map.get(key, '#64748B')
        parts.append(
            f'<div class="score-pill">'
            f'<div class="score-label">{label_map.get(key, key)}</div>'
            f'<div class="score-track"><div class="score-fill" style="width:{prob}%;background:{color}"></div></div>'
            f'<div class="score-num">{prob}%</div>'
            f'</div>'
        )
    return '<div class="score-bar-row">' + ''.join(parts) + '</div>'


def render_scenarios(scenarios):
    cards = []
    for s in scenarios:
        if not s['mece_valid']:
            mece_fail = '; '.join(_e(i) for i in s['mece_issues'])
            cards.append(f'<div class="mece-gate-error">MECE gate blocked "{_e(s["name"])}": {mece_fail}</div>')
            continue

        trigger_html = ''
        if s['trigger_keywords']:
            tags = ''.join(f'<span class="kw">{_e(kw)}</span>' for kw in s['trigger_keywords'])
            trigger_html = f'<div class="trigger-row"><span class="trigger-label">Keyword signal → Scenario {s["id"]}</span><div class="kw-list">{tags}</div></div>'

        mece_text = 'MECE · ' + ' · '.join(_e(a) for a in s['mece_axes'])
        mece_html = f'<div class="mece-badge mece-ok"><span class="mece-icon">✓</span><span>{mece_text}</span></div>'

        color = s['color']
        tid = _e(s['template_id'])
        vd_label = _e(s.get('value_driver_label', s['value_driver'].replace('_', ' ').title()))
        prob = s.get('probability', 0)
        prob_html = f'<span class="prob-chip">~{prob}%</span>' if prob > 0 else ''

        cards.append(f'''
        <div class="scenario-card" id="card-{tid}" data-template-id="{tid}">
          <div class="so-what-block">
            <span class="so-what-label">SO WHAT</span>
            <p class="so-what-text">{_e(s["so_what"])}</p>
          </div>
          <div class="scenario-header">
            <div class="scenario-top-row">
              <span class="scenario-badge" style="background:{color}">&nbsp;Scenario {s["id"]}&nbsp;</span>
              <span class="vd-tag" style="background:{color}22;color:{color};border:1px solid {color}55">{vd_label}</span>
              {prob_html}
              <span class="rejected-stamp" id="stamp-{tid}" style="display:none"></span>
            </div>
            <p class="scenario-title">{_e(s["name"])}</p>
            <div class="hyp-block">
              <span class="node-label nl-hyp">Hypothesis</span>
              <p class="hyp-text" id="hyp-{tid}">{_e(s["hypothesis"])}</p>
            </div>
            {mece_html}
            {trigger_html}
          </div>
          <button class="drill-confirm-btn" id="btn-confirm-{tid}" onclick="confirmHypothesis('{tid}')">Confirm Hypothesis →</button>
          <div class="drill-zone" id="drill-{tid}" style="display:none"></div>
          <div class="scenario-actions">
            <button class="btn-reject" id="btn-reject-{tid}" onclick="rejectScenario('{tid}', this)">Reject</button>
            <button class="btn-delete-red" onclick="deleteScenario('{tid}')">Delete</button>
          </div>
        </div>''')

    return '<div class="scenario-grid">' + ''.join(cards) + '</div>'


def build_result_page(form_data, result):
    proj = form_data.get('proj_name', 'CDD Project')
    client = form_data.get('client', '')
    ref_co = form_data.get('reference_company', '')
    meta_html = f'<span class="project-meta">{_e(client)} · {_e(ref_co)}</span>' if client and ref_co else ''

    cdd_warn = ''
    if result.get('cdd_warning'):
        cdd_warn = '<div class="cdd-warning">⚠ These inputs don\'t look like a CDD engagement. The hypothesis skeleton is optimized for commercial due diligence — other types may be mis-structured.</div>'

    score_bars = render_score_bars(result.get('probabilities', {}), result.get('zero_signal', False))

    cdd_data = {
        'scenarios': [
            {
                'template_id': s['template_id'],
                'name': s['name'],
                'value_driver': s['value_driver'],
                'sub_hypotheses': [
                    {
                        'text': sh['text'],
                        'confirm_evidence': sh['confirm_evidence'],
                        'confirm_expert': sh['confirm_expert'],
                        'confirm_expert_color': sh.get('confirm_expert_color', '#2563EB'),
                        'kill_evidence': sh['kill_evidence'],
                        'kill_expert': sh['kill_expert'],
                        'rationale': sh.get('rationale', ''),
                    }
                    for sh in s['sub_hypotheses']
                ],
            }
            for s in result['scenarios']
        ]
    }
    js = RESULT_JS.replace('{{ cdd_data_json }}', json.dumps(cdd_data))

    svg = render_svg_tree(result['issue'], result['scenarios'])
    scenarios_html = render_scenarios(result['scenarios'])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>CDD Predictor — {_e(proj)}</title>
  <style>{RESULT_CSS}</style>
</head>
<body>
  <header>
    <div class="header-left">
      <span class="app-title">CDD Predictor</span>
      <span class="app-sub">GLG Korea · Commercial Due Diligence · Hypothesis Framework</span>
    </div>
    <a class="btn-new" href="/">← New Project</a>
  </header>
  <div class="content">
    <div class="project-bar">
      <span class="project-pill">Project</span>
      <strong class="project-name">{_e(proj)}</strong>
      {meta_html}
    </div>
    {cdd_warn}
    <div class="issue-banner">
      <span class="issue-label">Issue</span>
      <span class="issue-text">{_e(result["issue"])}</span>
    </div>
    <div class="tree-container">
      <div class="tree-label">Hypothesis Tree — click a node to jump to its scenario</div>
      {svg}
    </div>
    {score_bars}
    <div class="scenarios-header-row">
      <span class="section-label">Predicted Scenarios · {len(result["scenarios"])} value drivers</span>
      <button class="export-csv-btn" onclick="exportCSV()">↓ Export CSV</button>
    </div>
    {scenarios_html}
  </div>
  <script>{js}</script>
</body>
</html>"""


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return FORM_HTML

@app.route('/generate', methods=['POST'])
def generate():
    form_data = {
        'proj_name':         request.form.get('proj_name', '').strip(),
        'client':            request.form.get('client', '').strip(),
        'reference_company': request.form.get('reference_company', '').strip(),
        'client_wants':      request.form.get('client_wants', '').strip(),
        'verify_questions':  request.form.get('verify_questions', '').strip(),
    }
    result = generate_result(form_data)
    return build_result_page(form_data, result)


if __name__ == '__main__':
    import webbrowser, threading
    url = 'http://localhost:5050'
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    print(f"\n  CDD Predictor running → {url}\n  Press Ctrl+C to stop.\n")
    app.run(port=5050, debug=False)
