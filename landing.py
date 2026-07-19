"""
FraudLens AI — Landing Page (Streamlit)
=========================================
Drop this file into your project as `landing.py` (replacing the old one).
Self-contained: the full animated HTML/CSS/JS landing page lives inside
this .py file as a string and is rendered via st.components.v1.html, so
there is nothing else to copy/paste or wire up separately.

Usage from app.py:

    from landing import render_landing
    render_landing()   # shows the landing page and st.stop()s if page == "landing"

Or just run this file directly for a quick look:
    streamlit run landing.py
"""

import streamlit as st
from pathlib import Path


LANDING_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FraudLens AI — Empowering Fraud Investigations</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root{
    --bg:#0B0A0A;
    --bg-2:#111010;
    --card:#171513;
    --card-2:#1C1917;
    --border:rgba(255,255,255,0.08);
    --border-hi:rgba(255,138,0,0.35);
    --orange:#FF6A1A;
    --orange-2:#FF8A3D;
    --text-1:#F5F1EC;
    --text-2:#A8A19A;
    --text-3:#6E6862;
    --radius-lg:20px;
    --radius-md:14px;
    --radius-sm:10px;
    --sans:"Inter", system-ui, sans-serif;
    --mono:"JetBrains Mono", monospace;
  }
  *{box-sizing:border-box; margin:0; padding:0;}
  html{scroll-behavior:smooth;}
  body{
    background:var(--bg); color:var(--text-1); font-family:var(--sans);
    -webkit-font-smoothing:antialiased; overflow-x:hidden;
  }
  a{color:inherit; text-decoration:none;}
  ::selection{background:var(--orange); color:#160b03;}

  .wrap{ max-width:1180px; margin:0 auto; padding:0 40px; }

  /* ---------- reveal ---------- */
  .rv{ opacity:0; transform:translateY(22px); transition:opacity .7s cubic-bezier(.2,.7,.3,1), transform .7s cubic-bezier(.2,.7,.3,1); }
  .rv.in{ opacity:1; transform:translateY(0); }

  /* ---------- nav ---------- */
  nav{
    position:sticky; top:0; z-index:100;
    display:flex; align-items:center; justify-content:space-between;
    padding:18px 40px; background:rgba(11,10,10,0.7); backdrop-filter:blur(16px);
    border-bottom:1px solid var(--border);
  }
  .brand{ display:flex; align-items:center; gap:10px; font-weight:700; font-size:16.5px; letter-spacing:-.01em; }
  .brand .mark{
    width:26px; height:26px; border-radius:7px; background:var(--orange);
    display:flex; align-items:center; justify-content:center;
  }
  .brand .mark svg{ width:14px; height:14px; }
  .navlinks{ display:flex; gap:34px; font-size:13.5px; color:var(--text-2); }
  .navlinks a{ transition:color .2s; }
  .navlinks a:hover{ color:var(--text-1); }
  .navright{ display:flex; align-items:center; gap:20px; font-size:13.5px; }
  .navright .signin{ color:var(--text-2); transition:color .2s; }
  .navright .signin:hover{ color:var(--text-1); }
  .btn-pill{
    background:#fff; color:#0B0A0A; font-weight:600; font-size:13px;
    padding:9px 20px; border-radius:999px; border:none; cursor:pointer; transition:transform .2s, box-shadow .2s;
  }
  .btn-pill:hover{ transform:translateY(-1px); box-shadow:0 8px 20px rgba(255,255,255,0.15); }

  /* ---------- hero ---------- */
  #hero{
    position:relative; min-height:82vh; display:flex; flex-direction:column; align-items:center;
    justify-content:center; text-align:center; padding:80px 24px 40px; overflow:hidden;
  }
  #hero-glow{
    position:absolute; inset:0; z-index:0;
    background:
      radial-gradient(ellipse 55% 55% at 50% 38%, rgba(255,106,26,0.30) 0%, rgba(255,106,26,0.10) 35%, transparent 68%);
  }
  #hero-rays{ position:absolute; inset:0; z-index:0; opacity:.55; }
  #hero canvas{ position:absolute; inset:0; z-index:1; }
  .hero-content{ position:relative; z-index:2; max-width:760px; }
  .hero-eyebrow{
    display:inline-flex; align-items:center; gap:8px; font-family:var(--mono); font-size:11px;
    letter-spacing:.08em; text-transform:uppercase; color:var(--text-2); margin-bottom:22px;
    border:1px solid var(--border); padding:6px 14px; border-radius:999px; background:rgba(255,255,255,0.02);
  }
  .hero-eyebrow i{ width:6px; height:6px; border-radius:50%; background:var(--orange-2); display:inline-block; }
  .hero-content h1{
    font-size:clamp(34px, 5vw, 54px); font-weight:800; letter-spacing:-.03em; line-height:1.08; color:#fff;
    animation:fadeUp .8s ease-out .1s both;
  }
  .hero-content p{
    margin:20px auto 0; max-width:520px; color:var(--text-2); font-size:15.5px; line-height:1.65;
    animation:fadeUp .8s ease-out .22s both;
  }
  @keyframes fadeUp{ from{opacity:0; transform:translateY(16px);} to{opacity:1; transform:translateY(0);} }

  .hero-form{
    display:flex; align-items:center; gap:0; max-width:420px; margin:32px auto 0;
    background:#141210; border:1px solid var(--border); border-radius:999px; padding:5px;
    animation:fadeUp .8s ease-out .32s both;
  }
  .hero-form input{
    flex:1; background:transparent; border:none; outline:none; padding:10px 16px;
    color:var(--text-1); font-family:var(--sans); font-size:13.5px;
  }
  .hero-form input::placeholder{ color:var(--text-3); }
  .hero-form button{
    background:linear-gradient(135deg, var(--orange), var(--orange-2)); color:#1a0d00; font-weight:700;
    font-size:13.5px; border:none; padding:11px 22px; border-radius:999px; cursor:pointer;
    transition:box-shadow .2s, transform .2s; white-space:nowrap;
  }
  .hero-form button:hover{ box-shadow:0 0 26px rgba(255,106,26,.5); transform:translateY(-1px); }

  .hero-meta{
    margin-top:26px; font-family:var(--mono); font-size:11.5px; color:var(--text-3);
    display:flex; gap:10px; align-items:center; justify-content:center; flex-wrap:wrap;
    animation:fadeUp .8s ease-out .4s both;
  }
  .hero-meta span:not(:last-child)::after{ content:'·'; margin-left:10px; color:var(--text-3); }

  .hero-note{
    margin-top:22px; display:inline-flex; align-items:center; gap:8px;
    border:1px solid var(--border); border-radius:999px; padding:8px 16px 8px 8px;
    font-size:12.5px; color:var(--text-2); animation:fadeUp .8s ease-out .48s both;
  }
  .hero-note .tag{
    background:rgba(255,106,26,0.12); color:var(--orange-2); font-family:var(--mono); font-size:10px;
    padding:3px 9px; border-radius:999px; text-transform:uppercase; letter-spacing:.04em;
  }
  .hero-note svg{ width:11px; height:11px; margin-left:2px; }

  /* trust row */
  .trust-row{ text-align:center; margin-top:70px; padding-bottom:10px; }
  .trust-row .lbl{ font-size:11.5px; color:var(--text-3); font-family:var(--mono); letter-spacing:.06em; text-transform:uppercase; margin-bottom:26px; }
  .trust-logos{ display:flex; justify-content:center; align-items:center; gap:52px; flex-wrap:wrap; opacity:.75; }
  .trust-logos .tl{ font-size:14px; font-weight:600; color:var(--text-2); letter-spacing:-.01em; display:flex; align-items:center; gap:7px; }
  .trust-logos .tl svg{ width:16px; height:16px; opacity:.8; }

  /* ---------- section shell ---------- */
  section{ padding:120px 40px; position:relative; }
  .section-inner{ max-width:1180px; margin:0 auto; }
  .center{ text-align:center; }
  .eyebrow-pill{
    display:inline-block; font-family:var(--mono); font-size:11px; letter-spacing:.08em; text-transform:uppercase;
    color:var(--orange-2); background:rgba(255,106,26,0.08); border:1px solid rgba(255,106,26,0.25);
    padding:6px 16px; border-radius:999px; margin-bottom:20px;
  }
  h2.h{ font-size:clamp(26px,3.6vw,38px); font-weight:800; letter-spacing:-.02em; line-height:1.2; color:#fff; }
  p.sub{ color:var(--text-2); font-size:15px; line-height:1.65; max-width:520px; margin:16px auto 0; }

  /* ---------- benefit cards ---------- */
  .benefit-grid{ display:grid; grid-template-columns:1fr 1fr; gap:24px; margin-top:60px; }
  .benefit-card{
    background:var(--card); border:1px solid var(--border); border-radius:var(--radius-lg);
    padding:28px; text-align:left; transition:border-color .3s, transform .3s;
  }
  .benefit-card:hover{ border-color:var(--border-hi); transform:translateY(-4px); }
  .benefit-card h3{ font-size:18px; font-weight:700; margin:22px 0 8px; letter-spacing:-.01em; }
  .benefit-card p{ font-size:13.5px; color:var(--text-2); line-height:1.6; }
  .mock{
    background:var(--card-2); border:1px solid var(--border); border-radius:var(--radius-md);
    padding:20px; height:190px; position:relative; overflow:hidden;
  }

  /* mock 1: risk score chat card */
  .mock-risk .row1{ display:flex; align-items:center; gap:10px; margin-bottom:16px; }
  .mock-risk .avatar{ width:26px; height:26px; border-radius:50%; background:linear-gradient(135deg,var(--orange),var(--orange-2)); flex-shrink:0; }
  .mock-risk .who{ font-size:11.5px; color:var(--text-2); }
  .mock-risk .who b{ color:var(--text-1); display:block; font-size:12px; }
  .mock-risk .amt{ margin-left:auto; font-family:var(--mono); font-size:11px; color:var(--text-3); }
  .mock-risk .card2{
    background:#0F0D0C; border:1px solid var(--border); border-radius:10px; padding:14px 16px; margin-bottom:10px;
  }
  .mock-risk .card2 .lbl{ font-size:10.5px; color:var(--text-3); font-family:var(--mono); text-transform:uppercase; letter-spacing:.05em; }
  .mock-risk .card2 .val{ font-size:20px; font-weight:700; color:#fff; margin-top:4px; }
  .mock-risk .bar{ height:5px; border-radius:4px; background:#26201b; margin-top:10px; overflow:hidden; }
  .mock-risk .bar i{ display:block; height:100%; width:78%; background:linear-gradient(90deg,var(--orange),var(--orange-2)); border-radius:4px; }
  .mock-risk .flagline{ display:flex; justify-content:space-between; font-family:var(--mono); font-size:10.5px; color:var(--text-3); margin-top:8px;}

  /* mock 2: network graph */
  .mock-net{ display:flex; align-items:center; justify-content:center; }
  .mock-net svg{ width:100%; height:100%; }
  .mock-net .lbl-top{ position:absolute; top:16px; left:16px; font-size:11px; color:var(--text-3); font-family:var(--mono); }
  .mock-net .lbl-bottom{
    position:absolute; bottom:16px; left:16px; right:16px;
    display:flex; justify-content:space-between; font-family:var(--mono); font-size:10.5px; color:var(--text-3);
  }

  /* ---------- world / network section ---------- */
  #network-section{ text-align:center; padding-top:0; }
  .net-grid{ display:grid; grid-template-columns:0.85fr 1.15fr; gap:60px; align-items:center; text-align:left; margin-top:20px; }
  .net-grid h2{ font-size:clamp(26px,3.4vw,36px); font-weight:800; letter-spacing:-.02em; line-height:1.22; color:#fff; }
  .net-grid p{ color:var(--text-2); font-size:14.5px; line-height:1.7; margin-top:16px; max-width:420px; }
  .net-stats{ display:flex; gap:34px; margin-top:30px; }
  .net-stats .st b{ display:block; font-size:24px; font-weight:800; color:#fff; }
  .net-stats .st span{ font-size:11.5px; color:var(--text-3); font-family:var(--mono); text-transform:uppercase; letter-spacing:.04em; }
  .map-card{
    background:var(--card); border:1px solid var(--border); border-radius:var(--radius-lg);
    padding:10px; position:relative; overflow:hidden; height:400px;
  }
  #mapCanvas{ width:100%; height:100%; display:block; }

  /* ---------- how it works ---------- */
  #how{ text-align:center; }
  .steps{ display:grid; grid-template-columns:repeat(4,1fr); gap:20px; margin-top:60px; text-align:left; counter-reset:step; }
  .step{
    background:var(--card); border:1px solid var(--border); border-radius:var(--radius-md); padding:26px 22px;
    position:relative; transition:border-color .3s, transform .3s;
  }
  .step:hover{ border-color:var(--border-hi); transform:translateY(-3px); }
  .step .num{
    font-family:var(--mono); font-size:11px; color:var(--orange-2); letter-spacing:.06em; margin-bottom:18px;
    display:flex; align-items:center; gap:8px;
  }
  .step .num::before{ content:''; width:6px; height:6px; border-radius:50%; background:var(--orange-2); display:inline-block; }
  .step h4{ font-size:15px; font-weight:700; margin-bottom:8px; }
  .step p{ font-size:12.5px; color:var(--text-2); line-height:1.6; }
  .step-line{ position:relative; height:1px; background:var(--border); margin:0 -11px; }

  /* ---------- CTA ---------- */
  #cta{
    text-align:center;
    background:radial-gradient(ellipse 70% 90% at 50% 100%, rgba(255,106,26,0.22) 0%, transparent 70%);
  }
  #cta h2{ margin-bottom:14px; }
  .cta-row{ display:flex; gap:14px; justify-content:center; margin-top:32px; }
  .btn-primary{
    background:linear-gradient(135deg, var(--orange), var(--orange-2)); color:#1a0d00; font-weight:700;
    font-size:13.5px; border:none; padding:13px 26px; border-radius:999px; cursor:pointer; transition:box-shadow .2s, transform .2s;
  }
  .btn-primary:hover{ box-shadow:0 0 28px rgba(255,106,26,.5); transform:translateY(-1px); }
  .btn-outline{
    background:transparent; color:var(--text-1); font-weight:600; font-size:13.5px;
    border:1px solid var(--border); padding:13px 26px; border-radius:999px; cursor:pointer; transition:border-color .2s;
  }
  .btn-outline:hover{ border-color:var(--border-hi); color:var(--orange-2); }

  /* ---------- footer ---------- */
  footer{ border-top:1px solid var(--border); padding:50px 40px 34px; }
  .foot-row{ max-width:1180px; margin:0 auto; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px; }
  .foot-row .fbrand{ display:flex; align-items:center; gap:10px; font-weight:700; font-size:14.5px; }
  .foot-links{ display:flex; gap:26px; font-size:12.5px; color:var(--text-2); }
  .foot-links a:hover{ color:var(--text-1); }
  .foot-copy{ font-size:11.5px; color:var(--text-3); margin-top:20px; text-align:center; }

  @media (max-width:960px){
    .navlinks{ display:none; }
    .benefit-grid{ grid-template-columns:1fr; }
    .net-grid{ grid-template-columns:1fr; }
    .steps{ grid-template-columns:1fr 1fr; }
    section{ padding:80px 22px; }
  }
</style>
</head>
<body>

<nav>
  <div class="brand">
    <span class="mark"><svg viewBox="0 0 24 24" fill="none"><circle cx="11" cy="11" r="7" stroke="#1a0d00" stroke-width="2.2"/><line x1="16.2" y1="16.2" x2="21" y2="21" stroke="#1a0d00" stroke-width="2.2" stroke-linecap="round"/></svg></span>
    FraudLens AI
  </div>
  <div class="navlinks">
    <a href="#network-section">Investigators</a>
    <a href="#how">How it works</a>
    <a href="#benefits">Product</a>
    <a href="#cta">Docs</a>
  </div>
  <div class="navright">
    <a class="signin" href="#" onclick="window.open(window.parent.location.origin + window.parent.location.pathname + '?page=login', '_blank'); return false;">Sign In</a>
    <a class="btn-pill" href="#" onclick="window.open(window.parent.location.origin + window.parent.location.pathname + '?page=login', '_blank'); return false;" style="display:inline-block;">Explore Demo</a>
  </div>
</nav>

<section id="hero">
  <div id="hero-glow"></div>
  <canvas id="hero-particles"></canvas>
  <div class="hero-content">
    <div class="hero-eyebrow rv in"><i></i> AI Data Analyst Agent · Hackathon 2026</div>
    <h1>Empowering Fraud<br>Investigations</h1>
    <p>Ask a question the way you'd ask a colleague. FraudLens AI writes the SQL, runs the fraud checks, traces the money, and explains exactly what it found — grounded in real computed evidence, never a guess.</p>
    <div class="hero-form">
      <input type="text" placeholder="Ask: which accounts show circular transfers?">
      <a href="#" onclick="window.open(window.parent.location.origin + window.parent.location.pathname + '?page=login', '_blank'); return false;" style="display:inline-block; background:linear-gradient(135deg, var(--orange), var(--orange-2)); color:#1a0d00; font-weight:700; font-size:13.5px; padding:11px 22px; border-radius:999px; white-space:nowrap;">Get Started</a>
    </div>
    <div class="hero-meta">
      <span>v0.9.0 beta</span>
      <span>7‑agent pipeline</span>
      <span>Install via GitHub</span>
    </div>
    <a class="hero-note" href="#how">
      <span class="tag">New</span> See the full agent pipeline
      <svg viewBox="0 0 24 24" fill="none"><path d="M9 6l6 6-6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
    </a>
  </div>

  <div class="trust-row rv">
    <div class="lbl">Built on trusted, transparent data &amp; tooling</div>
    <div class="trust-logos">
      <span class="tl"><svg viewBox="0 0 24 24" fill="none"><rect x="3" y="3" width="18" height="18" rx="4" stroke="currentColor" stroke-width="1.6"/></svg> PaySim Dataset</span>
      <span class="tl"><svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.6"/></svg> IBM Fraud Set</span>
      <span class="tl"><svg viewBox="0 0 24 24" fill="none"><path d="M4 17l6-10 4 6 3-4 3 8H4z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg> NetworkX</span>
      <span class="tl"><svg viewBox="0 0 24 24" fill="none"><path d="M12 3v18M3 12h18" stroke="currentColor" stroke-width="1.6"/></svg> Plotly</span>
      <span class="tl"><svg viewBox="0 0 24 24" fill="none"><rect x="4" y="4" width="16" height="16" rx="3" stroke="currentColor" stroke-width="1.6"/></svg> Claude</span>
    </div>
  </div>
</section>

<section id="benefits">
  <div class="section-inner center">
    <div class="eyebrow-pill rv">Next‑level fraud tooling</div>
    <h2 class="h rv">Featured Capabilities FraudLens<br>Has To Offer</h2>
    <p class="sub rv">Every claim on screen is grounded in a number an agent actually computed — nothing is narrated from a guess.</p>

    <div class="benefit-grid">
      <div class="benefit-card rv">
        <div class="mock mock-risk">
          <div class="row1">
            <div class="avatar"></div>
            <div class="who"><b>ACC‑10229</b>Flagged transfer</div>
            <div class="amt">$182,400</div>
          </div>
          <div class="card2">
            <div class="lbl">Risk Score</div>
            <div class="val">0.92 / 1.00</div>
            <div class="bar"><i></i></div>
          </div>
          <div class="flagline"><span>Rule: velocity + cycle</span><span>High risk</span></div>
        </div>
        <h3>Score Fraud With Explainable Risk</h3>
        <p>Rule‑based checks for laundering rings, velocity fraud, and mule accounts, combined into one score you can trace back to its evidence.</p>
      </div>

      <div class="benefit-card rv">
        <div class="mock mock-net">
          <span class="lbl-top">Network trace</span>
          <svg viewBox="0 0 260 160">
            <line x1="60" y1="40" x2="130" y2="80" stroke="#3a2c20" stroke-width="1.4"/>
            <line x1="200" y1="40" x2="130" y2="80" stroke="#3a2c20" stroke-width="1.4"/>
            <line x1="60" y1="120" x2="130" y2="80" stroke="#FF8A3D" stroke-width="1.8"/>
            <line x1="200" y1="120" x2="130" y2="80" stroke="#3a2c20" stroke-width="1.4"/>
            <line x1="60" y1="40" x2="60" y2="120" stroke="#FF8A3D" stroke-width="1.8" stroke-dasharray="4 3"/>
            <circle cx="130" cy="80" r="9" fill="#1C1917" stroke="#FF8A3D" stroke-width="1.8"/>
            <circle cx="60" cy="40" r="6" fill="#0F0D0C" stroke="#5b5348" stroke-width="1.4"/>
            <circle cx="200" cy="40" r="6" fill="#0F0D0C" stroke="#5b5348" stroke-width="1.4"/>
            <circle cx="60" cy="120" r="6" fill="#0F0D0C" stroke="#FF8A3D" stroke-width="1.6"/>
            <circle cx="200" cy="120" r="6" fill="#0F0D0C" stroke="#5b5348" stroke-width="1.4"/>
          </svg>
          <span class="lbl-bottom"><span>4 accounts</span><span>1 cycle found</span></span>
        </div>
        <h3>Trace Money Movement Visually</h3>
        <p>A live transaction graph with cycle detection — the exact 3‑hop laundering loop the Explanation Agent describes, made visible.</p>
      </div>
    </div>
  </div>
</section>

<section id="network-section">
  <div class="section-inner">
    <div class="net-grid">
      <div class="rv">
        <div class="eyebrow-pill">Built to scale</div>
        <h2>Connecting Investigators And Data From Every Institution</h2>
        <p>The same seven‑agent pipeline runs against a regional fintech's ledger or a multinational bank's full transaction volume — no architecture change required.</p>
        <div class="net-stats">
          <div class="st"><b>7</b><span>Specialised agents</span></div>
          <div class="st"><b>200</b><span>Row cap per query</span></div>
          <div class="st"><b>0</b><span>Invented claims</span></div>
        </div>
      </div>
      <div class="map-card rv">
        <canvas id="mapCanvas"></canvas>
      </div>
    </div>
  </div>
</section>

<section id="how">
  <div class="section-inner">
    <div class="eyebrow-pill rv">Unsure about the flow? Here's the breakdown</div>
    <h2 class="h rv">How FraudLens AI Works</h2>
    <p class="sub rv" style="margin-left:auto; margin-right:auto;">One question in, one grounded, explainable answer out.</p>

    <div class="steps">
      <div class="step rv"><div class="num">STEP 01</div><h4>Ask a question</h4><p>Type a question in plain English — the way you'd ask a fellow investigator, not a database.</p></div>
      <div class="step rv"><div class="num">STEP 02</div><h4>Agents run</h4><p>Intent → SQL → Fraud Detection → Network Analysis hand off cleanly, each stage visible on screen.</p></div>
      <div class="step rv"><div class="num">STEP 03</div><h4>Evidence surfaces</h4><p>A risk score, a highlighted transaction cycle, and the exact SQL that was executed — nothing hidden.</p></div>
      <div class="step rv"><div class="num">STEP 04</div><h4>Report generated</h4><p>A plain‑English explanation and a downloadable investigation report, ready for a compliance review.</p></div>
    </div>
  </div>
</section>

<section id="cta">
  <div class="section-inner">
    <div class="eyebrow-pill rv">Ready when you are</div>
    <h2 class="h rv">See It Investigate A Fraud Ring Live</h2>
    <p class="sub rv" style="margin-left:auto; margin-right:auto;">Ask a real question, watch the SQL run, and read the explanation — grounded in evidence, every time.</p>
    <div class="cta-row rv">
      <a class="btn-primary" href="#" onclick="window.open(window.parent.location.origin + window.parent.location.pathname + '?page=login', '_blank'); return false;" style="display:inline-block;">Enter the console →</a>
      <a class="btn-outline" href="https://github.com/millyshreenp-ship-it/FraudLens" target="_blank" style="display:inline-block;">View on GitHub</a>
    </div>
  </div>
</section>

<footer>
  <div class="foot-row">
    <div class="fbrand">
      <span class="mark" style="width:22px;height:22px;"><svg viewBox="0 0 24 24" fill="none"><circle cx="11" cy="11" r="7" stroke="#1a0d00" stroke-width="2.2"/><line x1="16.2" y1="16.2" x2="21" y2="21" stroke="#1a0d00" stroke-width="2.2" stroke-linecap="round"/></svg></span>
      FraudLens AI
    </div>
    <div class="foot-links">
      <a href="#benefits">Product</a>
      <a href="#network-section">Architecture</a>
      <a href="#how">How it works</a>
      <a href="#">GitHub</a>
    </div>
  </div>
  <div class="foot-copy">© 2026 FraudLens AI · Hackathon build · Synthetic data only, no real customer data.</div>
</footer>

<script>
/* reveal on scroll */
const io = new IntersectionObserver((entries)=>{
  entries.forEach(e=>{ if(e.isIntersecting){ e.target.classList.add('in'); io.unobserve(e.target); } });
}, {threshold:0.12});
document.querySelectorAll('.rv').forEach(el=>io.observe(el));

/* hero particles */
(function(){
  const canvas = document.getElementById('hero-particles');
  const stage = document.getElementById('hero');
  const ctx = canvas.getContext('2d');
  function resize(){ canvas.width = stage.clientWidth; canvas.height = stage.clientHeight; }
  resize(); window.addEventListener('resize', resize);
  const particles = Array.from({length:55}, ()=>({
    x:Math.random()*canvas.width, y:Math.random()*canvas.height,
    r:Math.random()*1.3+0.3, vy:-(Math.random()*0.12+0.03), a:Math.random()*0.4+0.1
  }));
  function tick(){
    ctx.clearRect(0,0,canvas.width,canvas.height);
    for(const p of particles){
      p.y += p.vy;
      if(p.y < 0){ p.y = canvas.height; p.x = Math.random()*canvas.width; }
      ctx.beginPath(); ctx.arc(p.x,p.y,p.r,0,Math.PI*2);
      ctx.fillStyle = `rgba(255,150,80,${p.a})`; ctx.fill();
    }
    requestAnimationFrame(tick);
  }
  tick();
})();

/* connecting world map */
(function(){
  const canvas = document.getElementById('mapCanvas');
  const wrap = canvas.parentElement;
  const ctx = canvas.getContext('2d');
  let W,H;
  function resize(){ W = canvas.width = wrap.clientWidth; H = canvas.height = wrap.clientHeight; }
  resize(); window.addEventListener('resize', resize);

  const land = [
    [15,72,-170,-50],[-55,12,-82,-34],[36,71,-10,40],
    [-35,37,-18,52],[5,77,40,180],[-44,-10,112,154]
  ];
  function isLand(lat,lon){ for(const [a,b,c,d] of land){ if(lat>=a&&lat<=b&&lon>=c&&lon<=d) return true; } return false; }
  const dots = [];
  for(let lat=-70; lat<=75; lat+=3.2){
    for(let lon=-180; lon<180; lon+=3.2){
      if(isLand(lat,lon)) dots.push([lon,lat]);
    }
  }
  function project(lon,lat){
    const x = (lon+180)/360 * W;
    const y = (90-lat)/180 * H * 1.35 - H*0.18;
    return [x,y];
  }
  // connection nodes (approx city coords)
  const nodes = [
    [-74,40.7], [-0.12,51.5], [77.1,28.6], [103.8,1.35], [151.2,-33.9], [-46.6,-23.5], [31.2,30.0]
  ];
  const links = [[0,1],[1,2],[2,3],[3,4],[0,5],[1,6]];
  let t = 0;
  function tick(){
    ctx.clearRect(0,0,W,H);

    // dot matrix
    for(const [lon,lat] of dots){
      const [x,y] = project(lon,lat);
      ctx.beginPath(); ctx.arc(x,y,0.9,0,Math.PI*2);
      ctx.fillStyle = 'rgba(160,150,140,0.45)'; ctx.fill();
    }

    // animated arcs between nodes
    links.forEach(([a,b], i)=>{
      const [x1,y1] = project(nodes[a][0], nodes[a][1]);
      const [x2,y2] = project(nodes[b][0], nodes[b][1]);
      const mx = (x1+x2)/2, my = Math.min(y1,y2) - 40 - (i%3)*8;
      ctx.beginPath();
      ctx.moveTo(x1,y1);
      ctx.quadraticCurveTo(mx,my,x2,y2);
      ctx.strokeStyle = 'rgba(255,138,61,0.35)';
      ctx.lineWidth = 1.2;
      ctx.stroke();

      // moving dot along curve
      const p = (t*0.25 + i*0.15) % 1;
      const qx = (1-p)*(1-p)*x1 + 2*(1-p)*p*mx + p*p*x2;
      const qy = (1-p)*(1-p)*y1 + 2*(1-p)*p*my + p*p*y2;
      ctx.beginPath(); ctx.arc(qx,qy,2.4,0,Math.PI*2);
      ctx.fillStyle = '#FF8A3D'; ctx.shadowColor='#FF6A1A'; ctx.shadowBlur=8;
      ctx.fill(); ctx.shadowBlur=0;
    });

    // node markers
    nodes.forEach(([lon,lat],i)=>{
      const [x,y] = project(lon,lat);
      const pulse = 3 + Math.sin(t*2+i)*1.4;
      ctx.beginPath(); ctx.arc(x,y,pulse+4,0,Math.PI*2);
      ctx.fillStyle = 'rgba(255,138,61,0.15)'; ctx.fill();
      ctx.beginPath(); ctx.arc(x,y,2.6,0,Math.PI*2);
      ctx.fillStyle = '#fff'; ctx.fill();
    });

    t += 0.012;
    requestAnimationFrame(tick);
  }
  tick();
})();
</script>
</body>
</html>
"""


# =====================================================================
# DESIGN SYSTEM — shared across landing / login / console so all three
# screens read as one product instead of three different tools bolted
# together.
# =====================================================================

_DESIGN_TOKENS = """
:root{
    --bg:#0A0908;
    --surface:#141210;
    --surface-2:#1A1714;
    --surface-user:#241606;
    --border:rgba(255,255,255,0.07);
    --border-hi:rgba(255,138,61,0.4);
    --orange:#FF6A1A;
    --orange-2:#FF8A3D;
    --text-1:#F5F1EC;
    --text-2:#A8A19A;
    --text-3:#6E6862;
    --radius-lg:18px;
    --radius-md:12px;
    --shadow-card:0 20px 50px rgba(0,0,0,0.35);
}
"""

# Applied on EVERY page (landing / login / console): strips Streamlit's
# default chrome (header bar, hamburger menu, footer) and the large top
# padding it normally reserves for that chrome.
_BASE_CSS = f"""
<style>
{_DESIGN_TOKENS}
header[data-testid="stHeader"]{{ height:0; min-height:0; background:transparent; }}
div[data-testid="stToolbar"]{{ display:none; }}
#MainMenu{{ visibility:hidden; }}
footer{{ visibility:hidden; }}
.stApp{{
    background:
        radial-gradient(ellipse 60% 40% at 15% 0%, rgba(255,106,26,0.05) 0%, transparent 60%),
        var(--bg);
}}
.stApp, .stApp p, .stApp span, .stApp label, .stApp li{{
    color:var(--text-1); font-family:"Inter","Source Sans Pro",sans-serif;
}}
.stApp h1, .stApp h2, .stApp h3{{ color:#fff; letter-spacing:-0.02em; }}
.stApp a{{ color:var(--orange-2); }}
::selection{{ background:var(--orange); color:#160b03; }}

/* belt-and-suspenders: some Streamlit-internal wrapper divs around the
   bottom chat-input bar paint a hardcoded white background that isn't
   reachable by data-testid, so force every ancestor of it dark too. */
html, body{{ background:var(--bg) !important; }}
div:has(> [data-testid="stBottom"]){{ background:var(--bg) !important; }}
[data-testid="stBottom"], [data-testid="stBottomBlockContainer"],
[data-testid="stAppScrollToBottomContainer"]{{ background:var(--bg) !important; }}
[data-testid="stBottom"] > div{{ background:var(--bg) !important; border-top:1px solid var(--border); }}

/* scrollbar */
::-webkit-scrollbar{{ width:10px; height:10px; }}
::-webkit-scrollbar-track{{ background:var(--bg); }}
::-webkit-scrollbar-thumb{{ background:#2a2420; border-radius:8px; }}
::-webkit-scrollbar-thumb:hover{{ background:#3a322b; }}
</style>
"""

_LANDING_TOP_CSS = """
<style>.block-container{ padding-top:0rem !important; padding-bottom:0rem; }</style>
"""

_CONSOLE_TOP_CSS = """
<style>.block-container{ padding-top:5.2rem !important; padding-bottom:3rem; max-width:920px; }</style>
"""

_LOGIN_TOP_CSS = """
<style>.block-container{ padding-top:0rem !important; padding-bottom:0rem; max-width:100% !important; }</style>
"""

# Widget-level restyle: inputs, buttons, alerts, chat, sidebar, expanders.
_WIDGET_CSS = """
<style>
/* text inputs */
.stTextInput>div>div>input{
    background:#0F0D0C; border:1px solid var(--border); color:var(--text-1);
    border-radius:10px; padding:12px 14px; font-size:14px;
}
.stTextInput>div>div>input:focus{ border-color:var(--border-hi); box-shadow:0 0 0 3px rgba(255,138,61,0.12); }
.stTextInput label{ color:var(--text-2) !important; font-size:12px !important; font-weight:600; text-transform:uppercase; letter-spacing:.04em; }

/* primary buttons */
.stButton>button, .stFormSubmitButton>button{
    background:linear-gradient(135deg, var(--orange), var(--orange-2));
    color:#1a0d00; font-weight:700; border:none; border-radius:999px;
    padding:11px 22px; transition:box-shadow .2s, transform .2s; width:100%;
}
.stButton>button:hover, .stFormSubmitButton>button:hover{
    box-shadow:0 0 24px rgba(255,106,26,.5); transform:translateY(-1px); color:#1a0d00;
}
.secondary-btn .stButton>button{
    background:transparent; color:var(--text-2); border:1px solid var(--border); box-shadow:none; font-weight:500;
}
.secondary-btn .stButton>button:hover{ border-color:var(--border-hi); color:var(--orange-2); transform:none; box-shadow:none; }

/* login card */
[data-testid="stForm"]{
    background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-lg);
    padding:36px 34px 26px; box-shadow:var(--shadow-card);
}

/* sidebar */
section[data-testid="stSidebar"]{ background:#0D0B0A; border-right:1px solid var(--border); }
section[data-testid="stSidebar"] *{ color:var(--text-1); }
section[data-testid="stSidebar"] .stMarkdown p{ color:var(--text-2); font-size:13px; line-height:1.6; }
section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"]{
    background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-md);
    padding:4px 4px;
}

/* chat messages: differentiate user vs assistant without touching app logic */
[data-testid="stChatMessage"]{
    border-radius:var(--radius-md); padding:14px 16px; margin-bottom:14px;
    border:1px solid var(--border); background:var(--surface-2);
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]){
    background:var(--surface-user); border-color:rgba(255,138,61,0.22);
}
[data-testid="stChatMessageAvatarUser"]{ background:linear-gradient(135deg,var(--orange),var(--orange-2)) !important; }
[data-testid="stChatMessageAvatarAssistant"]{ background:var(--surface) !important; border:1px solid var(--border-hi) !important; }

/* expanders (Intent JSON / Generated SQL) get distinct accent + icon-ish left edge */
[data-testid="stExpander"]{
    background:var(--surface-2); border:1px solid var(--border); border-radius:var(--radius-md);
    margin-bottom:8px; overflow:hidden;
}
[data-testid="stExpander"] summary{ color:var(--text-1); font-size:13.5px; font-weight:600; padding:4px 2px; }
[data-testid="stExpander"] summary:hover{ color:var(--orange-2); }

/* dataframes */
[data-testid="stDataFrame"]{ border:1px solid var(--border); border-radius:var(--radius-md); overflow:hidden; }

/* chat input */
[data-testid="stChatInput"]{
    background:var(--surface-2); border:1px solid var(--border); border-radius:16px;
    box-shadow:0 10px 30px rgba(0,0,0,0.25);
}
[data-testid="stChatInput"] textarea{ color:var(--text-1) !important; }

/* alerts (st.warning / st.info / st.error) -- selectors doubled up
   (data-testid + class + a *= fallback) because Streamlit has renamed
   this element's testid across versions before. */
[data-testid="stAlert"], .stAlert, div[class*="stAlert"], div[data-testid*="Alert"]{
    background:var(--surface-2) !important; border:1px solid var(--border) !important;
    border-left:3px solid var(--orange-2) !important; border-radius:var(--radius-md) !important;
    color:var(--text-1) !important; padding:16px 18px !important;
}
/* Streamlit sometimes paints the warning/info/error color on an inner
   div rather than the outer container -- force every descendant div
   transparent so the outer dark background always wins. */
[data-testid="stAlert"] *, .stAlert *{ background-color:transparent !important; }
[data-testid="stAlert"] p, [data-testid="stAlert"] span, [data-testid="stAlert"] li,
.stAlert p, .stAlert span, .stAlert li{ color:var(--text-1) !important; }
[data-testid="stAlert"] code, .stAlert code{
    background:#0F0D0C !important; color:var(--orange-2) !important;
    border:1px solid var(--border); border-radius:5px; padding:1px 6px;
}

/* inline + block code, everywhere */
code{ background:#0F0D0C; color:var(--orange-2); border-radius:5px; padding:1px 6px; font-size:12.5px; }
pre code{ background:transparent; color:inherit; padding:0; }
[data-testid="stCodeBlock"]{ border:1px solid var(--border); border-radius:var(--radius-md); overflow:hidden; }

/* metric-ish pills used in sidebar helper below */
.fl-pill{
    display:inline-flex; align-items:center; gap:6px; background:#0F0D0C; border:1px solid var(--border);
    border-radius:999px; padding:5px 12px; font-size:11.5px; color:var(--text-2); font-family:monospace;
    margin:2px 4px 2px 0;
}
.fl-pill b{ color:var(--text-1); }
</style>
"""


def render_console_header(title: str = "FraudLens", subtitle: str | None = None):
    """Sticky branded top bar + heading for the console page.

    Replaces `st.title("🔍 FraudLens")` + `st.caption(...)`. Call this
    right after `apply_console_theme()`.
    """
    investigator = st.session_state.get("investigator_id", "investigator")
    st.markdown(
        f"""
        <div style="position:fixed; top:0; left:0; right:0; z-index:999;
                    display:flex; align-items:center; justify-content:space-between;
                    padding:14px 32px; background:rgba(10,9,8,0.82); backdrop-filter:blur(14px);
                    border-bottom:1px solid rgba(255,255,255,0.07);">
          <div style="display:flex; align-items:center; gap:10px; font-weight:700; font-size:15px; color:#fff;">
            <span style="width:26px; height:26px; border-radius:8px; flex-shrink:0;
                         background:linear-gradient(135deg,#FF6A1A,#FF8A3D);
                         display:inline-flex; align-items:center; justify-content:center; font-size:13px;">🔍</span>
            FraudLens AI
          </div>
          <div style="display:flex; align-items:center; gap:8px; font-family:monospace; font-size:11.5px; color:#7FE0C4;">
            <span style="width:6px;height:6px;border-radius:50%;background:#3DFDBB; display:inline-block;
                         box-shadow:0 0 6px #3DFDBB;"></span>
            LIVE &middot; {investigator}
          </div>
        </div>
        <div style="height:6px;"></div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:14px; margin-bottom:2px;">
          <div style="width:42px; height:42px; border-radius:12px; flex-shrink:0;
                      background:linear-gradient(135deg,#FF6A1A,#FF8A3D);
                      display:flex; align-items:center; justify-content:center; font-size:19px;
                      box-shadow:0 8px 24px rgba(255,106,26,.3);">🔍</div>
          <h1 style="margin:0; font-size:27px;">{title}</h1>
        </div>
        {f'<p style="color:var(--text-2); font-size:14px; margin:6px 0 24px; max-width:640px;">{subtitle}</p>' if subtitle else '<div style="margin-bottom:18px;"></div>'}
        """,
        unsafe_allow_html=True,
    )


def render_landing(height: int = 4200):
    """Render the FraudLens marketing landing page.

    Reads st.query_params to decide what to show:
      - no ?page param  -> the animated marketing landing page
      - ?page=login      -> a branded investigator login screen
      - ?page=console    -> returns without rendering anything, so the
                            caller's own console code runs

    Call this at the very top of app.py, before any other st.* calls.
    """
    page = st.query_params.get("page", "landing")

    if page == "landing":
        st.set_page_config(page_title="FraudLens AI", layout="wide")
        st.markdown(_BASE_CSS, unsafe_allow_html=True)
        st.markdown(_LANDING_TOP_CSS, unsafe_allow_html=True)
        st.components.v1.html(LANDING_HTML, height=height, scrolling=True)
        st.stop()

    if page == "login":
        st.set_page_config(page_title="FraudLens AI - Sign In", layout="wide")
        st.markdown(_BASE_CSS, unsafe_allow_html=True)
        st.markdown(_LOGIN_TOP_CSS, unsafe_allow_html=True)
        st.markdown(_WIDGET_CSS, unsafe_allow_html=True)
        _render_login()
        st.stop()

    # page == "console" -> fall through, let app.py render the real console
    return


def apply_console_theme():
    """Call once at the top of app.py, right after st.set_page_config(),
    to reskin the existing console UI (sidebar, chat bubbles, buttons,
    inputs, alerts, expanders) to match the landing page's brand -
    without changing any of your app logic. Follow with
    render_console_header() for the branded title/top bar.
    """
    st.markdown(_BASE_CSS, unsafe_allow_html=True)
    st.markdown(_CONSOLE_TOP_CSS, unsafe_allow_html=True)
    st.markdown(_WIDGET_CSS, unsafe_allow_html=True)


def _render_login():
    left, right = st.columns([1.1, 1], gap="large")

    with left:
        st.markdown(
            """
            <div style="position:relative; min-height:520px; border-radius:22px; overflow:hidden;
                        background:radial-gradient(ellipse 80% 60% at 30% 20%, rgba(255,106,26,0.16) 0%, transparent 60%), #0D0B0A;
                        border:1px solid var(--border); padding:44px 40px; display:flex; flex-direction:column; justify-content:space-between;">
              <div style="position:absolute; width:260px; height:260px; border-radius:50%; top:-60px; right:-60px;
                          background:radial-gradient(circle, rgba(255,106,26,0.18) 0%, transparent 70%); filter:blur(10px);
                          animation:flFloat 7s ease-in-out infinite;"></div>
              <div style="position:absolute; width:180px; height:180px; border-radius:50%; bottom:20px; left:-40px;
                          background:radial-gradient(circle, rgba(255,138,61,0.12) 0%, transparent 70%); filter:blur(10px);
                          animation:flFloat 9s ease-in-out infinite reverse;"></div>
              <div style="position:relative; z-index:2;">
                <div style="display:flex; align-items:center; gap:10px; font-weight:700; font-size:16px; color:#fff; margin-bottom:40px;">
                  <span style="width:28px;height:28px;border-radius:8px; background:linear-gradient(135deg,#FF6A1A,#FF8A3D);
                               display:inline-flex; align-items:center; justify-content:center; font-size:14px;">🔍</span>
                  FraudLens AI
                </div>
                <h2 style="font-size:30px; line-height:1.25; max-width:380px; margin-bottom:16px;">
                  Every claim, grounded in evidence you can see.
                </h2>
                <p style="color:var(--text-2); font-size:14.5px; line-height:1.7; max-width:360px;">
                  Sign in to ask questions in plain English and get back the SQL, the fraud pattern, and the
                  plain-English explanation — never a guess.
                </p>
              </div>
              <div style="position:relative; z-index:2; display:flex; gap:28px; font-family:monospace; font-size:11px; color:var(--text-3);">
                <div><b style="color:var(--text-1); font-size:18px; display:block; font-family:Inter,sans-serif;">7</b>AGENTS</div>
                <div><b style="color:var(--text-1); font-size:18px; display:block; font-family:Inter,sans-serif;">0</b>INVENTED CLAIMS</div>
                <div><b style="color:var(--text-1); font-size:18px; display:block; font-family:Inter,sans-serif;">200</b>ROW CAP</div>
              </div>
            </div>
            <style>
            @keyframes flFloat{ 0%,100%{ transform:translateY(0) scale(1);} 50%{ transform:translateY(-14px) scale(1.05);} }
            </style>
            """,
            unsafe_allow_html=True,
        )

    with right:
        st.markdown('<div style="padding-top:40px;">', unsafe_allow_html=True)
        st.markdown(
            """
            <p style="color:var(--text-2); font-size:12px; text-transform:uppercase; letter-spacing:.08em;
                      font-family:monospace; margin-bottom:6px;">Investigator access</p>
            <h3 style="margin-bottom:26px;">Sign in to continue</h3>
            """,
            unsafe_allow_html=True,
        )

        with st.form("login_form"):
            investigator_id = st.text_input("Investigator ID", placeholder="agent_007")
            access_code = st.text_input("Access Code", type="password")
            submitted = st.form_submit_button("Enter Console →", use_container_width=True)

        if submitted:
            st.session_state["investigator_id"] = investigator_id or "investigator"
            st.query_params["page"] = "console"
            st.rerun()

        st.markdown('<div class="secondary-btn" style="margin-top:10px;">', unsafe_allow_html=True)
        if st.button("← Back to site", use_container_width=True):
            st.query_params.clear()
            st.rerun()
        st.markdown("</div></div>", unsafe_allow_html=True)


def sidebar_pill(label: str, value: str):
    """Small helper for prettier sidebar key/value rows than raw st.markdown."""
    st.markdown(f'<span class="fl-pill">{label} <b>{value}</b></span>', unsafe_allow_html=True)


if __name__ == "__main__":
    # allows `streamlit run landing.py` for a standalone preview
    render_landing()
    st.write("You're on the console page. Wire your real console UI here.")