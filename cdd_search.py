"""
CDD Predictor — Flask web server
Run:  python3 server.py
Then open:  http://localhost:5050
"""

from flask import Flask, request, render_template_string, jsonify
from tree_map import generate_result, generate_sub_sub, _e
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
    .btn-submit:disabled{background:#64748B;cursor:not-allowed}
    .divider{border:none;border-top:1px solid #E2E8F0;margin:24px 0}
    .loading-overlay{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(15,23,42,.85);z-index:999;flex-direction:column;align-items:center;justify-content:center;gap:20px}
    .loading-overlay.active{display:flex}
    .loading-spinner{width:48px;height:48px;border:4px solid #334155;border-top-color:#2563EB;border-radius:50%;animation:spin 1s linear infinite}
    @keyframes spin{to{transform:rotate(360deg)}}
    .loading-text{color:#E2E8F0;font-size:16px;font-weight:700}
    .loading-sub{color:#94A3B8;font-size:12px;margin-top:-12px}
    .loading-timer{color:#64748B;font-size:11px;font-family:monospace}
  </style>
</head>
<body>
  <div class="loading-overlay" id="loading">
    <div class="loading-spinner"></div>
    <div class="loading-text">Generating Hypothesis Tree</div>
    <div class="loading-sub">Building scenarios with Claude — this takes 20-40 seconds</div>
    <div class="loading-timer" id="loading-timer">0s</div>
  </div>
  <header>
    <span class="app-title">CDD Predictor</span>
    <span class="app-sub">GLG Korea · Commercial Due Diligence · Hypothesis Framework</span>
  </header>
  <main>
    <div class="card">
      <div class="card-title">New CDD Project</div>
      <div class="card-sub">Fill in the engagement context — the model will generate a hypothesis tree ordered by keyword signal.</div>
      <hr class="divider">
      <form method="POST" action="/generate" onsubmit="showLoading()">
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
        <button class="btn-submit" type="submit" id="btn-submit">Generate Hypothesis Tree &rarr;</button>
      </form>
    </div>
  </main>
  <script>
    function showLoading(){
      document.getElementById('loading').classList.add('active');
      document.getElementById('btn-submit').disabled=true;
      document.getElementById('btn-submit').textContent='Generating...';
      var start=Date.now();
      setInterval(function(){
        var s=Math.floor((Date.now()-start)/1000);
        document.getElementById('loading-timer').textContent=s+'s';
      },1000);
    }
  </script>
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
/* Tree — rendered dynamically by JS */
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
.scenario-grid{display:flex;gap:16px;overflow-x:auto;padding-bottom:12px;scroll-snap-type:x mandatory}
.scenario-grid::-webkit-scrollbar{height:6px}
.scenario-grid::-webkit-scrollbar-track{background:#F1F5F9;border-radius:3px}
.scenario-grid::-webkit-scrollbar-thumb{background:#CBD5E1;border-radius:3px}
.scenario-grid::-webkit-scrollbar-thumb:hover{background:#94A3B8}
.scenario-card{background:#fff;border:1px solid #E2E8F0;border-radius:12px;padding:18px;display:flex;flex-direction:column;gap:12px;transition:opacity .2s,box-shadow .2s;scroll-margin-top:20px;min-width:380px;max-width:420px;flex-shrink:0;scroll-snap-align:start}
.scenario-card:hover{box-shadow:0 4px 16px rgba(0,0,0,.08)}
.scenario-card.highlighted{box-shadow:0 0 0 3px #2563EB55;animation:pulse .6s ease}
@keyframes pulse{0%{box-shadow:0 0 0 0 #2563EB55}50%{box-shadow:0 0 0 6px #2563EB22}100%{box-shadow:0 0 0 3px #2563EB55}}
.scenario-card.rejected{opacity:.45}
.scenario-card.deleted{display:none}
.so-what-toggle{padding:5px 10px;background:transparent;border:1px solid #E2E8F0;border-radius:5px;font-size:10px;font-weight:600;color:#94A3B8;cursor:pointer;transition:all .15s;align-self:flex-start}
.so-what-toggle:hover{background:#F8FAFC;color:#64748B;border-color:#CBD5E1}
.so-what-block{display:none;align-items:flex-start;gap:8px;background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:10px 12px;animation:fadeIn .2s ease}
.so-what-block.visible{display:flex}
@keyframes fadeIn{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:translateY(0)}}
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
/* ── Custom hypothesis input ─────────────────────────────────── */
.custom-hyp-section{background:#fff;border:1px solid #E2E8F0;border-radius:12px;padding:18px;margin-top:20px}
.custom-hyp-title{font-size:13px;font-weight:700;color:#1E293B;margin-bottom:12px}
.custom-hyp-row{display:flex;gap:10px;margin-bottom:10px;flex-wrap:wrap}
.custom-hyp-input{flex:1;min-width:200px;border:1px solid #CBD5E1;border-radius:6px;padding:8px 10px;font-size:12px;font-family:inherit;background:#F8FAFC;color:#1E293B}
.custom-hyp-input:focus{outline:none;border-color:#2563EB;box-shadow:0 0 0 3px #2563EB20;background:#fff}
.custom-hyp-input::placeholder{color:#94A3B8}
.btn-add-hyp{padding:8px 16px;background:#0F172A;color:#F8FAFC;border:none;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;transition:background .15s;white-space:nowrap}
.btn-add-hyp:hover{background:#1E293B}
/* ── Dynamic tree ─────────────────────────────────── */
.tree-container{background:#fff;border:1px solid #E2E8F0;border-radius:12px;padding:20px;margin-bottom:24px;overflow-x:auto}
.tree-label{font-size:11px;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:.07em;margin-bottom:14px}
/* ── Exploration panel (full-width drill-down) ────── */
.explore-panel{display:none;background:#fff;border:1px solid #E2E8F0;border-radius:12px;padding:24px 28px;margin-top:16px;overflow:auto}
.explore-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;padding-bottom:14px;border-bottom:1px solid #E2E8F0}
.explore-title{font-size:15px;font-weight:700;color:#0F172A}
.explore-subtitle{font-size:11px;color:#94A3B8;margin-top:2px}
.btn-close-explore{padding:5px 12px;background:transparent;border:1px solid #E2E8F0;border-radius:5px;font-size:11px;font-weight:600;color:#64748B;cursor:pointer;transition:all .15s}
.btn-close-explore:hover{background:#F1F5F9;border-color:#94A3B8}
.explore-tree{display:flex;flex-direction:row;gap:16px;overflow-x:auto;padding-bottom:16px;scroll-snap-type:x proximity}
.explore-tree::-webkit-scrollbar{height:6px}
.explore-tree::-webkit-scrollbar-thumb{background:#CBD5E1;border-radius:3px}
.explore-tree>.tree-node{scroll-snap-align:start}
/* Tree nodes */
.tree-node{position:relative;padding:14px 16px;margin:6px 0;border-left:4px solid #CBD5E1;border-radius:0 8px 8px 0;background:#FAFBFC;transition:all .2s;min-width:340px;max-width:400px;flex-shrink:0}
.tree-node:hover{background:#F1F5F9}
.tree-node.remained{border-left-color:#059669;background:#F0FDF9}
.tree-node.deleted{opacity:.4;border-left-color:#E2E8F0;pointer-events:none}
.tree-node-header{margin-bottom:6px}
.tree-node-label{display:inline-block;font-size:8px;font-weight:700;padding:2px 6px;border-radius:3px;text-transform:uppercase;letter-spacing:.08em;background:#F0FDF4;color:#166534;margin-bottom:4px}
.tree-node-label-deep{background:#EFF6FF;color:#1D4ED8}
.tree-node-text{font-size:13px;font-weight:600;color:#1E293B;line-height:1.5;margin:0}
.tree-node-text-deleted{font-size:13px;color:#94A3B8;text-decoration:line-through;line-height:1.5}
.tree-node-experts{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:10px 0 6px}
.expert-mini{display:flex;flex-direction:column;gap:3px;padding:8px 10px;border:1px solid #E2E8F0;border-radius:6px;background:#fff}
.expert-mini-kill{border-color:#FECACA;background:#FFFBFB}
.expert-mini-label{font-size:8px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:#64748B}
.expert-mini-kill .expert-mini-label{color:#DC2626}
.expert-mini-name{font-size:11px;font-weight:700;color:#1E293B}
.expert-mini-evidence{font-size:10px;color:#64748B;line-height:1.4;margin-top:2px}
.tree-node-actions{display:flex;gap:8px;margin-top:10px}
.btn-remain{padding:7px 14px;border:1px solid #BBF7D0;background:#F0FDF4;color:#166534;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;transition:all .15s}
.btn-remain:hover{background:#DCFCE7}
.btn-del-sub{padding:7px 14px;border:1px solid #FECACA;background:#FEF2F2;color:#DC2626;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;transition:all .15s}
.btn-del-sub:hover{background:#FEE2E2}
.tree-node-children{margin-top:10px;display:flex;flex-direction:row;gap:12px;overflow-x:auto;padding:10px 0 8px 0;border-top:2px solid #93C5FD}
.tree-node-children .tree-node{border-left:4px solid #3B82F6;min-width:300px;max-width:360px;background:#EFF6FF}
.tree-node-children .tree-node.remained{border-left-color:#059669;background:#F0FDF9}
.tree-node-children .tree-node-children{border-top-color:#7C3AED}
.tree-node-children .tree-node-children .tree-node{border-left-color:#7C3AED;background:#F5F3FF;min-width:280px}
.tree-node-loading{font-size:12px;color:#2563EB;font-weight:600;padding:12px 16px;margin:6px 0 6px 24px;background:#EFF6FF;border-radius:6px;border:1px dashed #93C5FD;animation:loadPulse 1.5s ease infinite}
@keyframes loadPulse{0%,100%{opacity:1}50%{opacity:.5}}
.tree-depth-badge{display:inline-block;font-size:8px;font-weight:700;color:#94A3B8;background:#F1F5F9;padding:1px 5px;border-radius:3px;margin-left:6px}
/* Expert chips with confirm/delete */
.expert-chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.expert-chip-card{display:flex;align-items:center;gap:6px;padding:6px 10px;border:1px solid #E2E8F0;border-radius:6px;background:#fff;font-size:11px;transition:all .2s}
.expert-chip-card.confirmed{border-color:#059669;background:#F0FDF9}
.expert-chip-card.deleted{display:none}
.expert-chip-name{font-weight:700;color:#1E293B}
.expert-chip-evidence{font-size:10px;color:#64748B;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.btn-chip-confirm{padding:2px 6px;border:1px solid #BBF7D0;background:#F0FDF4;color:#166534;border-radius:3px;font-size:9px;font-weight:700;cursor:pointer;transition:all .15s}
.btn-chip-confirm:hover{background:#DCFCE7}
.btn-chip-delete{padding:2px 6px;border:1px solid #FECACA;background:#FEF2F2;color:#DC2626;border-radius:3px;font-size:9px;font-weight:700;cursor:pointer;transition:all .15s}
.btn-chip-delete:hover{background:#FEE2E2}
.confirmed-badge{font-size:8px;font-weight:700;color:#059669;background:#F0FDF4;border:1px solid #BBF7D0;padding:1px 5px;border-radius:3px}
"""

RESULT_JS = """
const LOG_KEY = 'cdd_rejection_log';
window.CDD_DATA = {{ cdd_data_json }};

const SCENARIOS = {};
for (const s of window.CDD_DATA.scenarios) { SCENARIOS[s.template_id] = s; }
const drillState = {};
let customCounter = 0;

function loadLog(){try{return JSON.parse(localStorage.getItem(LOG_KEY)||'{}');}catch{return{};}}
function saveLog(l){localStorage.setItem(LOG_KEY,JSON.stringify(l));}
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}

/* ── Dynamic SVG tree ──────────────────────────────────────── */
function buildTree(){
  const container=document.getElementById('tree-svg');
  if(!container)return;
  const scenarios=window.CDD_DATA.scenarios.filter(s=>{
    const card=document.getElementById('card-'+s.template_id);
    return !card||!card.classList.contains('deleted');
  });
  const count=scenarios.length;
  if(count===0){container.innerHTML='';return;}

  const HYP_W=260,HYP_H=56,PAD=60,GAP=20;
  const SVG_W=Math.max(900,PAD*2+count*HYP_W+(count-1)*GAP);
  const ISSUE_W=Math.min(SVG_W-100,800),ISSUE_H=50;
  const ROOT_CX=SVG_W/2;
  const ISSUE_Y=16;
  const ELBOW_Y=ISSUE_Y+ISSUE_H+28;
  const HYP_Y=ELBOW_Y+20;

  const centers=[];
  const totalW=count*HYP_W+(count-1)*GAP;
  const startX=(SVG_W-totalW)/2+HYP_W/2;
  for(let i=0;i<count;i++) centers.push(startX+i*(HYP_W+GAP));

  let parts=[];
  const issue=window.CDD_DATA.issue||'';
  const issueX=ROOT_CX-ISSUE_W/2;
  const issueShort=issue.length>100?issue.slice(0,97)+'…':issue;
  parts.push('<rect x="'+issueX+'" y="'+ISSUE_Y+'" width="'+ISSUE_W+'" height="'+ISSUE_H+'" rx="10" fill="#0F172A"/>');
  parts.push('<text x="'+ROOT_CX+'" y="'+(ISSUE_Y+16)+'" text-anchor="middle" fill="#475569" font-size="9" font-weight="700" letter-spacing="0.1em">ISSUE</text>');
  parts.push('<text x="'+ROOT_CX+'" y="'+(ISSUE_Y+34)+'" text-anchor="middle" fill="#E2E8F0" font-size="11">'+esc(issueShort)+'</text>');

  const log=loadLog();

  function collectBranches(nodes,depth,parentTid){
    let items=[];
    for(let i=0;i<nodes.length;i++){
      const n=nodes[i];
      if(n.status==='remained'){
        const short=n.text.length>24?n.text.slice(0,21)+'…':n.text;
        const experts=(n.confirmedExperts||[]).map(function(ce){return ce.length>22?ce.slice(0,19)+'…':ce;});
        items.push({label:short,experts:experts,depth:depth,tid:parentTid,subIdx:i});
        if(n.children&&n.children.length>0){
          items=items.concat(collectBranches(n.children,depth+1,parentTid));
        }
      }
    }
    return items;
  }

  let allBranches=[];
  for(let i=0;i<scenarios.length;i++){
    const s=scenarios[i];
    const tid=s.template_id;
    let branches=[];
    const ms=mainExpertState[tid];
    if(ms){
      const mainExperts=ms.filter(function(e){return e.status==='confirmed';}).map(function(e){return e.name.length>22?e.name.slice(0,19)+'…':e.name;});
      if(mainExperts.length>0){
        branches.push({label:'Main Hypothesis',experts:mainExperts,depth:0,tid:tid,subIdx:-1});
      }
    }
    const st=drillState[tid];
    if(st&&st.nodes) branches=branches.concat(collectBranches(st.nodes,0,tid));
    allBranches.push(branches);
  }

  const SUB_Y=HYP_Y+HYP_H+24;
  const SUB_W=220,SUB_GAP=6;
  var maxColH=0;
  for(var bi=0;bi<allBranches.length;bi++){
    var colH=0;
    for(var bj=0;bj<allBranches[bi].length;bj++){
      var ne=allBranches[bi][bj].experts?allBranches[bi][bj].experts.length:0;
      colH+=32+(ne>0?(4+ne*14):0)+SUB_GAP;
    }
    maxColH=Math.max(maxColH,colH);
  }
  const SVG_H=maxColH>0?SUB_Y+maxColH+20:HYP_Y+HYP_H+50;

  for(let i=0;i<scenarios.length;i++){
    const s=scenarios[i];
    const cx=centers[i];
    const rx=cx-HYP_W/2;
    const color=s.color||'#64748B';
    const tid=s.template_id;
    const isRejected=Object.prototype.hasOwnProperty.call(log,tid);
    const opacity=isRejected?'0.35':'1';
    const nameShort=s.name.length>28?s.name.slice(0,25)+'…':s.name;

    parts.push('<path d="M '+ROOT_CX+' '+(ISSUE_Y+ISSUE_H)+' L '+ROOT_CX+' '+ELBOW_Y+' L '+cx+' '+ELBOW_Y+' L '+cx+' '+HYP_Y+'" fill="none" stroke="#CBD5E1" stroke-width="1.5"/>');
    parts.push('<rect x="'+rx+'" y="'+HYP_Y+'" width="'+HYP_W+'" height="'+HYP_H+'" rx="10" fill="'+color+'" opacity="'+opacity+'" style="cursor:pointer" onclick="highlightCard(\\''+tid+'\\')"/>');
    parts.push('<text x="'+cx+'" y="'+(HYP_Y+16)+'" text-anchor="middle" fill="rgba(255,255,255,.65)" font-size="9" font-weight="700" letter-spacing="0.09em" pointer-events="none">SCENARIO '+s.id+'</text>');
    parts.push('<text x="'+cx+'" y="'+(HYP_Y+36)+'" text-anchor="middle" fill="white" font-size="12" font-weight="700" pointer-events="none">'+esc(nameShort)+'</text>');

    var branches=allBranches[i];
    if(branches.length>0){
      var curY=SUB_Y;
      var armX=cx-SUB_W/2-10;
      parts.push('<path d="M '+cx+' '+(HYP_Y+HYP_H)+' L '+cx+' '+(SUB_Y-8)+' L '+armX+' '+(SUB_Y-8)+'" fill="none" stroke="#94A3B8" stroke-width="1.5"/>');
      for(let j=0;j<branches.length;j++){
        const b=branches[j];
        const numExperts=b.experts?b.experts.length:0;
        const nodeH=32+(numExperts>0?(4+numExperts*14):0);
        const indent=b.depth*16;
        const sx=armX+6+indent;
        const bw=SUB_W-indent;
        var midY=curY+nodeH/2;
        parts.push('<path d="M '+armX+' '+(SUB_Y-8)+' L '+armX+' '+midY+' L '+sx+' '+midY+'" fill="none" stroke="#94A3B8" stroke-width="1.2"/>');
        var depthColors=['#64748B','#3B82F6','#7C3AED'];
        var dc=depthColors[Math.min(b.depth,2)];
        parts.push('<rect x="'+sx+'" y="'+curY+'" width="'+bw+'" height="'+nodeH+'" rx="6" fill="#fff" stroke="'+dc+'" stroke-width="1.5" style="cursor:pointer" onclick="scrollToExplore(\\''+b.tid+'\\')"/>');
        var depthLabels=['SUB-HYPOTHESIS','DEPTH 2','DEPTH 3'];
        parts.push('<text x="'+(sx+8)+'" y="'+(curY+12)+'" fill="'+dc+'" font-size="7" font-weight="700" letter-spacing="0.06em">'+depthLabels[Math.min(b.depth,2)]+'</text>');
        parts.push('<text x="'+(sx+8)+'" y="'+(curY+25)+'" fill="#1E293B" font-size="9" font-weight="'+(b.depth>0?'700':'600')+'">'+esc(b.label)+'</text>');
        if(numExperts>0){
          for(let ei=0;ei<b.experts.length;ei++){
            var ey=curY+34+ei*14;
            parts.push('<circle cx="'+(sx+10)+'" cy="'+(ey+4)+'" r="3" fill="#059669"/>');
            parts.push('<text x="'+(sx+16)+'" y="'+(ey+7)+'" fill="#059669" font-size="8" font-weight="700">'+esc(b.experts[ei])+'</text>');
          }
        }
        curY+=nodeH+SUB_GAP;
      }
    }
  }

  container.innerHTML='<svg viewBox="0 0 '+SVG_W+' '+SVG_H+'" xmlns="http://www.w3.org/2000/svg" style="width:100%;min-width:'+SVG_W+'px;display:block">'+parts.join('')+'</svg>';
}

function scrollToExplore(tid){
  var panel=document.getElementById('explore-'+tid);
  if(panel&&panel.style.display==='block'){
    panel.scrollIntoView({behavior:'smooth',block:'center'});
    return;
  }
  var card=document.getElementById('card-'+tid);
  if(card){
    card.scrollIntoView({behavior:'smooth',block:'center'});
    var btn=document.getElementById('btn-confirm-'+tid);
    if(btn&&btn.style.display!=='none') btn.click();
  }
}

/* ── Card interactions ──────────────────────────────────────── */
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
  buildTree();
}

function deleteScenario(tid){
  if(!confirm('Delete this scenario?'))return;
  document.getElementById('card-'+tid).classList.add('deleted');
  buildTree();
}

function toggleSoWhat(tid){
  const block=document.getElementById('sowhat-'+tid);
  const btn=document.getElementById('btn-sowhat-'+tid);
  if(!block)return;
  block.classList.toggle('visible');
  btn.textContent=block.classList.contains('visible')?'Hide logic':'Why this hypothesis?';
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

/* ── Exploration tree (drill-down) ─────────────────────────── */
function confirmHypothesis(tid){
  const btn=document.getElementById('btn-confirm-'+tid);
  if(btn)btn.style.display='none';
  const s=SCENARIOS[tid];
  drillState[tid]={
    active:true,
    nodes:s.sub_hypotheses.map(function(sh){return{
      text:sh.text,
      experts:(sh.experts||[]).map(function(e){return{name:e.name,evidence:e.evidence||'',rationale:e.rationale||'',status:'pending'};}),
      confirmedExperts:[],
      status:'pending',children:[],loading:false
    };})
  };
  renderExploration(tid);
}

function closeExploration(tid){
  const panel=document.getElementById('explore-'+tid);
  if(panel)panel.style.display='none';
  const btn=document.getElementById('btn-confirm-'+tid);
  if(btn)btn.style.display='';
}

function renderExploration(tid,doScroll){
  const panel=document.getElementById('explore-'+tid);
  if(!panel)return;
  var wasHidden=panel.style.display!=='block';
  panel.style.display='block';
  const s=SCENARIOS[tid];
  const st=drillState[tid];
  let html='<div class="explore-header"><div><div class="explore-title">'+esc(s.name)+'</div>'+
    '<div class="explore-subtitle">Click Remain to dig deeper into any branch — the model will generate sub-sub-hypotheses with experts</div></div>'+
    '<button class="btn-close-explore" onclick="closeExploration(\\''+tid+'\\')">Close</button></div>';
  html+='<div class="explore-tree">'+renderNodeTree(tid,st.nodes,[],0)+'</div>';
  panel.innerHTML=html;
  if(wasHidden||doScroll) panel.scrollIntoView({behavior:'smooth',block:'nearest'});
  buildTree();
}

function renderNodeTree(tid,nodes,path,depth){
  let html='';
  for(let i=0;i<nodes.length;i++){
    const node=nodes[i];
    const curPath=path.concat(i);
    const pathStr=JSON.stringify(curPath);
    const cls='tree-node'+(node.status==='remained'?' remained':'')+(node.status==='deleted'?' deleted':'');
    const depthColors=['#059669','#3B82F6','#7C3AED'];
    const depthColor=depthColors[Math.min(depth,2)];
    const depthNames=['Sub-hypothesis','Depth 2','Depth 3'];
    const depthName=depthNames[Math.min(depth,2)];
    const textSize=depth===0?'13px':depth===1?'14px':'15px';
    const textWeight=depth===0?'600':'700';

    html+='<div class="'+cls+'">';
    html+='<div class="tree-node-header">';
    html+='<span style="font-size:9px;font-weight:800;color:'+depthColor+';text-transform:uppercase;letter-spacing:.08em;padding:2px 6px;background:'+depthColor+'12;border-radius:3px;border:1px solid '+depthColor+'33">'+depthName+'</span>';
    if(node.status==='deleted'){
      html+='<p class="tree-node-text-deleted">'+esc(node.text)+'</p>';
    }else{
      html+='<p style="font-size:'+textSize+';font-weight:'+textWeight+';color:#1E293B;line-height:1.5;margin:4px 0 0">'+esc(node.text)+'</p>';
    }
    html+='</div>';

    if(node.status!=='deleted'&&node.experts&&node.experts.length>0){
      html+='<div class="expert-chips">';
      for(let ei=0;ei<node.experts.length;ei++){
        const ex=node.experts[ei];
        if(ex.status==='deleted')continue;
        const cls='expert-chip-card'+(ex.status==='confirmed'?' confirmed':'');
        html+='<div class="'+cls+'" title="'+esc(ex.evidence)+'">';
        html+='<span class="expert-chip-name">'+esc(ex.name)+'</span>';
        if(ex.status==='pending'){
          html+='<button class="btn-chip-confirm" onclick="nodeExpertAction(\\''+tid+'\\','+pathStr+','+ei+',\\'confirm\\')">Confirm</button>';
          html+='<button class="btn-chip-delete" onclick="nodeExpertAction(\\''+tid+'\\','+pathStr+','+ei+',\\'delete\\')">Delete</button>';
        }else{
          html+='<span class="confirmed-badge">Confirmed</span>';
        }
        html+='</div>';
      }
      html+='</div>';
    }

    if(node.status==='pending'){
      html+='<div class="tree-node-actions">'+
        '<button class="btn-remain" onclick="remainNode(\\''+tid+'\\','+pathStr+')">Remain — Dig Deeper ▸</button>'+
        '<button class="btn-del-sub" onclick="deleteNode(\\''+tid+'\\','+pathStr+')">Delete</button></div>';
    }

    if(node.loading){
      html+='<div class="tree-node-loading">Generating deeper hypotheses with expert recommendations...</div>';
    }

    if(node.children&&node.children.length>0){
      html+='<div class="tree-node-children">'+renderNodeTree(tid,node.children,curPath,depth+1)+'</div>';
    }
    html+='</div>';
  }
  return html;
}

function getNodeByPath(tid,path){
  let nodes=drillState[tid].nodes;
  let node=null;
  for(let p=0;p<path.length;p++){
    node=nodes[path[p]];
    if(p<path.length-1)nodes=node.children;
  }
  return node;
}

function remainNode(tid,path){
  const node=getNodeByPath(tid,path);
  node.status='remained';
  node.loading=true;
  renderExploration(tid);

  const s=SCENARIOS[tid];
  fetch('/api/expand',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({
      sub_hypothesis:node.text,
      hypothesis:s.hypothesis||s.name,
      reference_company:window.CDD_DATA.context.reference_company,
      client:window.CDD_DATA.context.client,
      client_wants:window.CDD_DATA.context.client_wants,
      proj_name:window.CDD_DATA.context.proj_name
    })
  })
  .then(function(r){return r.json();})
  .then(function(data){
    node.loading=false;
    node.children=(data||[]).map(function(sh){
      var experts=(sh.experts||[]).map(function(e){return{name:e.name||'',evidence:e.evidence||'',rationale:e.rationale||'',status:'pending'};});
      if(!experts.length&&sh.confirm_expert){
        experts=[{name:sh.confirm_expert,evidence:sh.confirm_evidence||'',rationale:'',status:'pending'},{name:sh.kill_expert||'',evidence:sh.kill_evidence||'',rationale:'',status:'pending'}];
      }
      return{text:sh.text||'',experts:experts,confirmedExperts:[],status:'pending',children:[],loading:false};
    });
    renderExploration(tid);
  })
  .catch(function(){
    node.loading=false;
    renderExploration(tid);
  });
}

function deleteNode(tid,path){
  const node=getNodeByPath(tid,path);
  node.status='deleted';
  renderExploration(tid);
}

function nodeExpertAction(tid,path,expertIdx,action){
  const node=getNodeByPath(tid,path);
  node.experts[expertIdx].status=action==='confirm'?'confirmed':'deleted';
  node.confirmedExperts=node.experts.filter(function(e){return e.status==='confirmed';}).map(function(e){return e.name;});
  renderExploration(tid);
  renderChosenExperts();
}

/* ── Main hypothesis expert selection ──────────────────────── */
const mainExpertState={};

function initMainExperts(tid){
  const s=SCENARIOS[tid];
  if(!s||!s.sub_hypotheses||!s.sub_hypotheses.length)return;
  const experts=s.sub_hypotheses[0].experts||[];
  if(!mainExpertState[tid]){
    mainExpertState[tid]=experts.map(function(e){return{name:e.name,evidence:e.evidence||'',status:'pending'};});
  }
}

function renderMainExpert(tid){
  const zone=document.getElementById('main-expert-'+tid);
  if(!zone)return;
  initMainExperts(tid);
  const state=mainExpertState[tid];
  if(!state||!state.length)return;
  let html='<div class="expert-chips">';
  for(let i=0;i<state.length;i++){
    const e=state[i];
    if(e.status==='deleted')continue;
    const cls='expert-chip-card'+(e.status==='confirmed'?' confirmed':'');
    html+='<div class="'+cls+'">';
    html+='<span class="expert-chip-name">'+esc(e.name)+'</span>';
    if(e.status==='pending'){
      html+='<button class="btn-chip-confirm" onclick="mainExpertAction(\\''+tid+'\\','+i+',\\'confirm\\')">Confirm</button>';
      html+='<button class="btn-chip-delete" onclick="mainExpertAction(\\''+tid+'\\','+i+',\\'delete\\')">Delete</button>';
    }else{
      html+='<span class="confirmed-badge">Confirmed</span>';
    }
    html+='</div>';
  }
  html+='</div>';
  zone.innerHTML=html;
  renderChosenExperts();
}

function mainExpertAction(tid,idx,action){
  mainExpertState[tid][idx].status=action==='confirm'?'confirmed':'deleted';
  renderMainExpert(tid);
  buildTree();
}

function renderChosenExperts(){
  const container=document.getElementById('chosen-experts-list');
  if(!container)return;
  let items=[];
  for(const s of window.CDD_DATA.scenarios){
    const tid=s.template_id;
    const ms=mainExpertState[tid];
    if(ms){
      for(const e of ms){
        if(e.status==='confirmed')items.push({scenario:s.name,expert:e.name});
      }
    }
    const st=drillState[tid];
    if(st&&st.nodes){
      (function collect(nodes,scenarioName){
        for(const n of nodes){
          if(n.confirmedExperts){
            for(const ce of n.confirmedExperts) items.push({scenario:scenarioName,expert:ce});
          }
          if(n.children)collect(n.children,scenarioName);
        }
      })(st.nodes,s.name);
    }
  }
  if(items.length===0){
    container.innerHTML='<span style="font-size:12px;color:#94A3B8;font-style:italic">No experts selected yet</span>';
    return;
  }
  let html='';
  for(const it of items){
    html+='<div style="display:flex;align-items:center;gap:8px;padding:8px 12px;background:#fff;border:1px solid #BBF7D0;border-radius:6px">'+
      '<span style="font-size:8px;font-weight:700;padding:2px 6px;border-radius:3px;color:#059669;background:#F0FDF4;border:1px solid #BBF7D0">CONFIRMED</span>'+
      '<span style="font-size:12px;font-weight:700;color:#0F172A">'+esc(it.expert)+'</span>'+
      '<span style="font-size:10px;color:#94A3B8;margin-left:auto">'+esc(it.scenario)+'</span></div>';
  }
  container.innerHTML=html;
}

/* ── Custom hypothesis ──────────────────────────────────────── */
function addCustomHypothesis(){
  const nameEl=document.getElementById('custom-hyp-name');
  const textEl=document.getElementById('custom-hyp-text');
  const name=nameEl.value.trim();
  const text=textEl.value.trim();
  if(!name){alert('Please enter a scenario name.');return;}
  if(!text){alert('Please enter a hypothesis.');return;}

  customCounter++;
  const tid='custom_'+customCounter;
  const newScenario={
    template_id:tid,id:window.CDD_DATA.scenarios.length+1,
    name:name,color:'#475569',value_driver:'custom',
    hypothesis:text,so_what:'User-defined hypothesis',
    sub_hypotheses:[],confirm_expert:'',kill_expert:''
  };
  window.CDD_DATA.scenarios.push(newScenario);
  SCENARIOS[tid]=newScenario;

  const grid=document.querySelector('.scenario-grid');
  const card=document.createElement('div');
  card.className='scenario-card';
  card.id='card-'+tid;
  card.setAttribute('data-template-id',tid);
  card.innerHTML=
'<div class="scenario-header"><div class="scenario-top-row">'+
'<span class="scenario-badge" style="background:#475569">&nbsp;Custom&nbsp;</span>'+
'<span class="rejected-stamp" id="stamp-'+tid+'" style="display:none"></span></div>'+
'<p class="scenario-title">'+esc(name)+'</p>'+
'<div class="hyp-block"><span class="node-label nl-hyp">Hypothesis</span>'+
'<p class="hyp-text" id="hyp-'+tid+'">'+esc(text)+'</p></div>'+
'<div class="main-expert-zone" id="main-expert-'+tid+'"></div></div>'+
'<button class="drill-confirm-btn" id="btn-confirm-'+tid+'" onclick="confirmHypothesis(\\''+tid+'\\')">Explore & Expand ▸</button>'+
'<div class="scenario-actions">'+
'<button class="btn-reject" id="btn-reject-'+tid+'" onclick="rejectScenario(\\''+tid+'\\',this)">Reject</button>'+
'<button class="btn-delete-red" onclick="deleteScenario(\\''+tid+'\\')">Delete</button></div>';
  grid.appendChild(card);

  var exploreDiv=document.createElement('div');
  exploreDiv.className='explore-panel';
  exploreDiv.id='explore-'+tid;
  grid.parentNode.insertBefore(exploreDiv,grid.nextSibling);

  card.innerHTML+='<div class="tree-node-loading" id="custom-loading-'+tid+'">Generating sub-hypotheses and experts...</div>';
  nameEl.value='';textEl.value='';
  buildTree();
  card.scrollIntoView({behavior:'smooth',block:'center'});

  fetch('/api/expand',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({
      sub_hypothesis:text,
      hypothesis:name,
      reference_company:window.CDD_DATA.context.reference_company,
      client:window.CDD_DATA.context.client,
      client_wants:window.CDD_DATA.context.client_wants,
      proj_name:window.CDD_DATA.context.proj_name
    })
  })
  .then(function(r){return r.json();})
  .then(function(data){
    var loadEl=document.getElementById('custom-loading-'+tid);
    if(loadEl)loadEl.remove();
    var subs=(data||[]).map(function(sh){
      var experts=(sh.experts||[]).map(function(e){return{name:e.name||'',evidence:e.evidence||'',rationale:e.rationale||''};});
      if(!experts.length&&sh.confirm_expert){
        experts=[{name:sh.confirm_expert,evidence:sh.confirm_evidence||'',rationale:''},{name:sh.kill_expert||'',evidence:sh.kill_evidence||'',rationale:''}];
      }
      return{text:sh.text||'',experts:experts};
    });
    newScenario.sub_hypotheses=subs;
    SCENARIOS[tid]=newScenario;
    if(subs.length>0){
      renderMainExpert(tid);
    }
  })
  .catch(function(){
    var loadEl=document.getElementById('custom-loading-'+tid);
    if(loadEl)loadEl.textContent='Could not generate sub-hypotheses.';
  });
}

/* ── Init ──────────────────────────────────────────────────── */
(function(){
  localStorage.removeItem(LOG_KEY);
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
  for(const s of window.CDD_DATA.scenarios){
    renderMainExpert(s.template_id);
  }
  buildTree();
  renderChosenExperts();
})();
"""


def render_svg_tree(issue, scenarios):
    SVG_W, SVG_H = 1100, 240
    ROOT_CX = SVG_W // 2
    ISSUE_Y, ISSUE_W, ISSUE_H = 20, 800, 54
    HYP_Y, HYP_W, HYP_H = 148, 310, 60
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
        short_name = scenario['name'] if len(scenario['name']) <= 30 else scenario['name'][:27] + '…'
        parts.append(f'<text x="{cx:.1f}" y="{HYP_Y+34}" text-anchor="middle" fill="white" font-size="13" font-weight="700" pointer-events="none">{_e(short_name)}</text>')
        if kw_text:
            parts.append(f'<text x="{cx:.1f}" y="{HYP_Y+52}" text-anchor="middle" fill="rgba(255,255,255,.7)" font-size="9.5" pointer-events="none">{_e(kw_text)}</text>')

    parts.append(f'<text x="{SVG_W//2}" y="{SVG_H-5}" text-anchor="middle" fill="#94A3B8" font-size="10">Click a node to jump to that scenario ↓</text>')

    return f'<svg viewBox="0 0 {SVG_W} {SVG_H}" xmlns="http://www.w3.org/2000/svg" style="width:100%;display:block">\n  ' + '\n  '.join(parts) + '\n</svg>'


def render_score_bars(probabilities, zero_signal):
    if zero_signal:
        return '<div class="score-bar-row"><span class="score-no-signal">Insufficient keyword signal — scenarios ranked by default order</span></div>'
    color_map = {'market_dynamics': '#2563EB', 'operational_model': '#059669', 'competitive_movement': '#D97706', 'growth_scalability': '#7C3AED', 'risk_regulatory': '#DC2626'}
    label_map = {'market_dynamics': 'Market Dynamics', 'operational_model': 'Operational Model', 'competitive_movement': 'Competitive Movement', 'growth_scalability': 'Growth & Scalability', 'risk_regulatory': 'Risk & Regulatory'}
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

        main_expert_html = f'<div class="main-expert-zone" id="main-expert-{tid}"></div>'

        cards.append(f'''
        <div class="scenario-card" id="card-{tid}" data-template-id="{tid}">
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
            {main_expert_html}
            {mece_html}
            {trigger_html}
          </div>
          <button class="so-what-toggle" id="btn-sowhat-{tid}" onclick="toggleSoWhat('{tid}')">Why this hypothesis?</button>
          <div class="so-what-block" id="sowhat-{tid}">
            <span class="so-what-label">SO WHAT</span>
            <p class="so-what-text">{_e(s["so_what"])}</p>
          </div>
          <button class="drill-confirm-btn" id="btn-confirm-{tid}" onclick="confirmHypothesis('{tid}')">Explore & Expand ▸</button>
          <div class="scenario-actions">
            <button class="btn-reject" id="btn-reject-{tid}" onclick="rejectScenario('{tid}', this)">Reject</button>
            <button class="btn-delete-red" onclick="deleteScenario('{tid}')">Delete</button>
          </div>
        </div>''')

    # Build exploration panels (one per scenario, shown when user clicks Explore)
    panels = []
    for s in scenarios:
        if s['mece_valid']:
            tid = _e(s['template_id'])
            panels.append(f'<div class="explore-panel" id="explore-{tid}"></div>')

    return '<div class="scenario-grid">' + ''.join(cards) + '</div>' + ''.join(panels)


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
        'issue': result['issue'],
        'context': {
            'reference_company': form_data.get('reference_company', ''),
            'client': form_data.get('client', ''),
            'client_wants': form_data.get('client_wants', ''),
            'proj_name': form_data.get('proj_name', ''),
        },
        'scenarios': [
            {
                'template_id': s['template_id'],
                'id': s['id'],
                'name': s['name'],
                'color': s['color'],
                'value_driver': s['value_driver'],
                'hypothesis': s['hypothesis'],
                'sub_hypotheses': [
                    {
                        'text': sh['text'],
                        'experts': sh.get('experts', []),
                    }
                    for sh in s['sub_hypotheses']
                ],
            }
            for s in result['scenarios']
        ]
    }
    js = RESULT_JS.replace('{{ cdd_data_json }}', json.dumps(cdd_data))

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
      <div class="tree-label">Hypothesis Tree — click a node to jump to its scenario · updates as you confirm</div>
      <div id="tree-svg"></div>
    </div>
    {score_bars}
    <div class="scenarios-header-row">
      <span class="section-label">Predicted Scenarios · {len(result["scenarios"])} value drivers</span>
      <button class="export-csv-btn" onclick="exportCSV()">↓ Export CSV</button>
    </div>
    {scenarios_html}
    <div class="custom-hyp-section">
      <div class="custom-hyp-title">Add Your Own Hypothesis</div>
      <div class="custom-hyp-row">
        <input class="custom-hyp-input" id="custom-hyp-name" placeholder="Scenario name (e.g. Pricing Power Erosion)">
        <input class="custom-hyp-input" id="custom-hyp-text" placeholder="Your hypothesis statement">
        <button class="btn-add-hyp" onclick="addCustomHypothesis()">+ Add</button>
      </div>
    </div>
    <div class="custom-hyp-section" style="margin-top:16px">
      <div class="custom-hyp-title">Chosen Experts</div>
      <div id="chosen-experts-list" style="display:flex;flex-direction:column;gap:6px">
        <span style="font-size:12px;color:#94A3B8;font-style:italic">No experts selected yet</span>
      </div>
    </div>
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

@app.route('/api/expand', methods=['POST'])
def api_expand():
    data = request.get_json()
    result = generate_sub_sub(
        data.get('sub_hypothesis', ''),
        data.get('hypothesis', ''),
        data.get('reference_company', ''),
        data.get('client', ''),
        data.get('client_wants', ''),
        data.get('proj_name', ''),
    )
    return jsonify(result or [])


if __name__ == '__main__':
    import webbrowser, threading
    url = 'http://localhost:5050'
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    print(f"\n  CDD Predictor running → {url}\n  Press Ctrl+C to stop.\n")
    app.run(port=5050, debug=False)
