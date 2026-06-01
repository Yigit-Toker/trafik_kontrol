import threading
import logging
import json
import os
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, jsonify, render_template_string, request, session, redirect, url_for
from ayarlar import Ayarlar

# ─── AUTH CONFIG ──────────────────────────────────────────────────────────────
# Add users here: {"username": "sha256_hash"}
# To generate hash in terminal: python3 -c "import hashlib; print(hashlib.sha256(b'password').hexdigest())"
AUTH_USERS = {
    Ayarlar.WEB_KULLANICI: Ayarlar.WEB_SIFRE_HASH,
}

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            if request.path.startswith('/api'):
                return jsonify({"error": "Unauthorized access", "code": 401}), 401
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

# ─── LOGIN PAGE HTML ───────────────────────────────────────────────────────
LOGIN_HTML = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Login · Smart Traffic</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Syne:wght@700;800&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { margin:0; padding:0; box-sizing:border-box; }
  :root {
    --bg: #050609; --surface: #0a0c12; --border: rgba(255,255,255,0.07);
    --blue: #3d8bff; --green: #1aff8c; --red: #ff4757;
    --text-1: #f0f2f8; --text-2: #8891aa; --text-3: #444d66;
    --mono: 'DM Mono', monospace; --sans: 'Syne', sans-serif;
  }
  body {
    background: var(--bg); color: var(--text-1);
    font-family: var(--mono);
    min-height: 100vh; display: flex; align-items: center; justify-content: center;
    overflow: hidden;
  }
  .bg-grid {
    position: fixed; inset: 0; pointer-events: none;
    background-image:
      linear-gradient(rgba(61,139,255,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(61,139,255,0.03) 1px, transparent 1px);
    background-size: 48px 48px;
    mask-image: radial-gradient(ellipse 80% 80% at 50% 50%, black, transparent);
  }
  .bg-glow {
    position: fixed; top: 50%; left: 50%; transform: translate(-50%,-60%);
    width: 600px; height: 600px;
    background: radial-gradient(ellipse, rgba(61,139,255,0.07) 0%, transparent 70%);
    pointer-events: none;
  }
  .card {
    position: relative; z-index: 1;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 48px 44px;
    width: 100%; max-width: 400px;
    box-shadow: 0 32px 80px rgba(0,0,0,0.5);
  }
  .logo {
    display: flex; align-items: center; gap: 12px;
    margin-bottom: 36px;
  }
  .logo-icon {
    width: 44px; height: 44px; border-radius: 12px;
    background: linear-gradient(135deg, rgba(61,139,255,0.2), rgba(61,139,255,0.05));
    border: 1px solid rgba(61,139,255,0.25);
    display: flex; align-items: center; justify-content: center; font-size: 1.4em;
  }
  .logo-text { font-family: var(--sans); font-size: 1.1em; font-weight: 800; }
  .logo-sub  { font-size: 0.65em; color: var(--text-3); letter-spacing: 0.1em; text-transform: uppercase; display: block; margin-top: 2px; }

  h1 { font-family: var(--sans); font-size: 1.3em; font-weight: 800; margin-bottom: 6px; }
  .subtitle { font-size: 0.78em; color: var(--text-3); margin-bottom: 32px; letter-spacing: 0.04em; }

  .field { margin-bottom: 16px; }
  label { display: block; font-size: 0.7em; letter-spacing: 0.1em; text-transform: uppercase; color: var(--text-3); margin-bottom: 8px; }
  input {
    width: 100%; background: rgba(0,0,0,0.4); border: 1px solid var(--border);
    border-radius: 10px; padding: 12px 16px;
    font-family: var(--mono); font-size: 0.92em; color: var(--text-1);
    outline: none; transition: border-color 0.3s, box-shadow 0.3s;
  }
  input:focus {
    border-color: rgba(61,139,255,0.5);
    box-shadow: 0 0 0 3px rgba(61,139,255,0.08);
  }
  button {
    width: 100%; margin-top: 8px;
    background: var(--blue); color: #fff;
    border: none; border-radius: 10px;
    padding: 13px; font-family: var(--sans); font-size: 0.95em; font-weight: 700;
    cursor: pointer; letter-spacing: 0.04em;
    transition: opacity 0.2s, transform 0.15s;
  }
  button:hover  { opacity: 0.9; transform: translateY(-1px); }
  button:active { transform: translateY(0); }
  .error {
    background: rgba(255,71,87,0.08); border: 1px solid rgba(255,71,87,0.25);
    border-radius: 10px; padding: 12px 16px;
    font-size: 0.8em; color: var(--red); margin-bottom: 20px; letter-spacing: 0.03em;
    display: flex; align-items: center; gap: 8px;
  }
  .footer-note {
    text-align: center; margin-top: 24px;
    font-size: 0.68em; color: var(--text-3); letter-spacing: 0.06em;
  }
  @keyframes shake {
    0%,100%{ transform:translateX(0); }
    20%,60%{ transform:translateX(-6px); }
    40%,80%{ transform:translateX(6px); }
  }
  .shake { animation: shake 0.4s ease; }
</style>
</head>
<body>
<div class="bg-grid"></div>
<div class="bg-glow"></div>
<div class="card" id="card">
  <div class="logo">
    <div class="logo-icon">🚦</div>
    <div>
      <div class="logo-text">Smart Traffic</div>
      <span class="logo-sub">Control Panel</span>
    </div>
  </div>
  <h1>Login</h1>
  <p class="subtitle">Authentication required to continue.</p>
  {% if hata %}
  <div class="error">⚠ {{ hata }}</div>
  {% endif %}
  <form method="POST" action="/login">
    <div class="field">
      <label>Username</label>
      <input type="text" name="kullanici" autocomplete="username" autofocus required placeholder="username">
    </div>
    <div class="field">
      <label>Password</label>
      <input type="password" name="sifre" autocomplete="current-password" required placeholder="••••••••">
    </div>
    <button type="submit">Login →</button>
  </form>
  <div class="footer-note">Raspberry Pi · YOLO11 · v3.0</div>
</div>
<script>
  {% if hata %}
  const card = document.getElementById('card');
  card.classList.add('shake');
  {% endif %}
</script>
</body>
</html>"""

logging.getLogger("werkzeug").setLevel(logging.ERROR)

# ─── HTML / CSS / JS ──────────────────────────────────────────────────────────

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Smart Traffic Control</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Syne:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
/* ══════════════════════════════════════════
   DESIGN TOKENS
══════════════════════════════════════════ */
:root {
  --bg:        #050609;
  --surface:   #0a0c12;
  --elevated:  #0e1119;
  --border:    rgba(255,255,255,0.06);
  --border-hi: rgba(255,255,255,0.12);

  --green:  #1aff8c;
  --yellow: #ffca28;
  --red:    #ff4757;
  --blue:   #3d8bff;
  --cyan:   #00e5ff;
  --purple: #9c77ff;

  --text-1: #f0f2f8;
  --text-2: #8891aa;
  --text-3: #444d66;

  --mono: 'DM Mono', monospace;
  --sans: 'Syne', sans-serif;

  --r-sm:  8px;
  --r-md:  14px;
  --r-lg:  20px;
  --r-xl:  28px;

  --shadow-green:  0 0 40px rgba(26,255,140,0.15);
  --shadow-yellow: 0 0 40px rgba(255,202,40,0.15);
  --shadow-red:    0 0 40px rgba(255,71,87,0.12);
  --shadow-blue:   0 0 40px rgba(61,139,255,0.15);
}

/* ══════════════════════════════════════════
   RESET + BASE
══════════════════════════════════════════ */
*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

html { scroll-behavior: smooth; }

body {
  background: var(--bg);
  color: var(--text-1);
  font-family: var(--sans);
  min-height: 100vh;
  overflow-x: hidden;
  line-height: 1.5;
}

/* ══════════════════════════════════════════
   BACKGROUND EFFECTS
══════════════════════════════════════════ */
.bg-grid {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  background-image:
    linear-gradient(rgba(61,139,255,0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(61,139,255,0.025) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: radial-gradient(ellipse 80% 60% at 50% 20%, black, transparent);
}

.bg-glow {
  position: fixed;
  top: -200px;
  left: 50%;
  transform: translateX(-50%);
  width: 900px;
  height: 500px;
  background: radial-gradient(ellipse, rgba(61,139,255,0.06) 0%, transparent 70%);
  pointer-events: none;
  z-index: 0;
}

.content-wrap { position: relative; z-index: 1; }

/* ══════════════════════════════════════════
   KEYFRAMES
══════════════════════════════════════════ */
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: none; }
}
@keyframes fadeIn {
  from { opacity: 0; }
  to   { opacity: 1; }
}
@keyframes pulse-ring {
  0%   { box-shadow: 0 0 0 0 currentColor; opacity: 0.6; }
  70%  { box-shadow: 0 0 0 8px currentColor; opacity: 0; }
  100% { box-shadow: 0 0 0 0 currentColor; opacity: 0; }
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.3; }
}
@keyframes ticker {
  from { transform: translateX(0); }
  to   { transform: translateX(-50%); }
}
@keyframes countPop {
  0%   { transform: scale(1); }
  40%  { transform: scale(1.08); }
  100% { transform: scale(1); }
}
@keyframes shimmer {
  0%   { background-position: -200% center; }
  100% { background-position:  200% center; }
}
@keyframes slideDown {
  from { opacity: 0; transform: translateY(-12px); }
  to   { opacity: 1; transform: none; }
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
@keyframes progress-glow {
  0%,100% { opacity: 0.8; }
  50%      { opacity: 1; }
}

/* ══════════════════════════════════════════
   OFFLINE BANNER
══════════════════════════════════════════ */
#offline-banner {
  display: none;
  position: fixed;
  top: 0; left: 0; right: 0;
  z-index: 9999;
  background: linear-gradient(90deg, var(--red), #ff6b35);
  color: #fff;
  text-align: center;
  padding: 10px 20px;
  font-family: var(--mono);
  font-size: 0.8em;
  letter-spacing: 0.08em;
  font-weight: 500;
}

/* ══════════════════════════════════════════
   TOAST
══════════════════════════════════════════ */
#toast-stack {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 9998;
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: flex-end;
}

.toast {
  background: var(--elevated);
  border: 1px solid var(--border-hi);
  border-radius: var(--r-md);
  padding: 12px 18px;
  font-family: var(--mono);
  font-size: 0.82em;
  color: var(--text-1);
  display: flex;
  align-items: center;
  gap: 10px;
  animation: slideDown 0.3s ease both;
  max-width: 320px;
  backdrop-filter: blur(12px);
}
.toast-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.toast.green  .toast-dot { background: var(--green); }
.toast.yellow .toast-dot { background: var(--yellow); }
.toast.red    .toast-dot { background: var(--red); }
.toast.blue   .toast-dot { background: var(--blue); }

/* ══════════════════════════════════════════
   HEADER
══════════════════════════════════════════ */
header {
  position: sticky;
  top: 0;
  z-index: 100;
  border-bottom: 1px solid var(--border);
  background: rgba(5,6,9,0.85);
  backdrop-filter: blur(20px) saturate(1.4);
  -webkit-backdrop-filter: blur(20px) saturate(1.4);
}

.header-inner {
  max-width: 1480px;
  margin: 0 auto;
  padding: 0 28px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 14px;
  cursor: pointer;
  flex-shrink: 0;
}
.logo-mark {
  position: relative;
  width: 38px;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.logo-icon-bg {
  position: absolute;
  inset: 0;
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(61,139,255,0.2), rgba(61,139,255,0.05));
  border: 1px solid rgba(61,139,255,0.25);
}
.logo-emoji {
  position: relative;
  font-size: 1.4em;
  filter: drop-shadow(0 0 8px rgba(61,139,255,0.5));
}
.logo-text {
  line-height: 1.1;
}
.logo-title {
  font-family: var(--sans);
  font-weight: 800;
  font-size: 1em;
  color: var(--text-1);
  letter-spacing: 0.02em;
}
.logo-subtitle {
  font-family: var(--mono);
  font-size: 0.65em;
  color: var(--text-3);
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

/* Ticker band */
.ticker-wrap {
  flex: 1;
  overflow: hidden;
  height: 32px;
  mask-image: linear-gradient(90deg, transparent, black 80px, black calc(100% - 80px), transparent);
  display: flex;
  align-items: center;
}
.ticker-track {
  display: flex;
  gap: 0;
  white-space: nowrap;
  animation: ticker 20s linear infinite;
}
.ticker-item {
  font-family: var(--mono);
  font-size: 0.72em;
  color: var(--text-3);
  padding: 0 32px;
  letter-spacing: 0.08em;
  border-right: 1px solid var(--border);
  height: 32px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.ticker-item .hi { color: var(--text-2); }

/* Header meta */
.header-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}
.meta-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border-radius: 100px;
  font-family: var(--mono);
  font-size: 0.72em;
  letter-spacing: 0.05em;
  border: 1px solid var(--border);
  color: var(--text-2);
  background: var(--surface);
  white-space: nowrap;
}
.meta-chip.live {
  border-color: rgba(26,255,140,0.3);
  background: rgba(26,255,140,0.05);
  color: var(--green);
}
.live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--green);
  animation: blink 1.2s ease-in-out infinite;
}

/* ══════════════════════════════════════════
   MAIN LAYOUT
══════════════════════════════════════════ */
main {
  max-width: 1480px;
  margin: 0 auto;
  padding: 32px 28px 48px;
}

/* ══════════════════════════════════════════
   SECTION HEADING
══════════════════════════════════════════ */
.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}
.section-title {
  font-family: var(--sans);
  font-size: 0.72em;
  font-weight: 600;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--text-3);
}
.section-line {
  flex: 1;
  height: 1px;
  background: var(--border);
  margin-left: 16px;
}

/* ══════════════════════════════════════════
   KPI STRIP
══════════════════════════════════════════ */
.kpi-strip {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  margin-bottom: 32px;
  animation: fadeUp 0.5s ease both;
}

.kpi-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  padding: 20px 22px;
  position: relative;
  overflow: hidden;
  cursor: default;
  transition: border-color 0.3s, transform 0.25s;
}
.kpi-card:hover {
  border-color: var(--border-hi);
  transform: translateY(-2px);
}
.kpi-card::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(255,255,255,0.02), transparent 60%);
  pointer-events: none;
}

.kpi-label {
  font-family: var(--mono);
  font-size: 0.65em;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-3);
  margin-bottom: 10px;
}
.kpi-value {
  font-family: var(--mono);
  font-size: 2.1em;
  font-weight: 500;
  color: var(--text-1);
  line-height: 1;
  letter-spacing: -0.02em;
}
.kpi-value.accent { color: var(--blue); }
.kpi-value.green  { color: var(--green); }
.kpi-value.yellow { color: var(--yellow); }

.kpi-icon {
  position: absolute;
  top: 18px;
  right: 18px;
  font-size: 1.4em;
  opacity: 0.35;
}

.kpi-bar {
  margin-top: 14px;
  height: 2px;
  background: var(--border);
  border-radius: 2px;
  overflow: hidden;
}
.kpi-bar-fill {
  height: 100%;
  background: var(--blue);
  border-radius: 2px;
  transition: width 1s ease;
}

/* ══════════════════════════════════════════
   ROAD GRID
══════════════════════════════════════════ */
.road-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
  margin-bottom: 32px;
}

/* ══════════════════════════════════════════
   ROAD CARD
══════════════════════════════════════════ */
.road-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  overflow: hidden;
  animation: fadeUp 0.4s ease both;
  transition: border-color 0.4s, box-shadow 0.4s, transform 0.25s;
  position: relative;
}
.road-card:hover {
  transform: translateY(-3px);
}

/* State-based accent borders */
.road-card.st-green  { border-color: rgba(26,255,140,0.2);  box-shadow: var(--shadow-green); }
.road-card.st-yellow { border-color: rgba(255,202,40,0.2);  box-shadow: var(--shadow-yellow); }
.road-card.st-red    { border-color: rgba(255,71,87,0.1);   box-shadow: var(--shadow-red); }

/* Active badge */
.active-badge {
  position: absolute;
  top: 14px;
  right: 14px;
  z-index: 10;
  font-family: var(--mono);
  font-size: 0.68em;
  font-weight: 500;
  letter-spacing: 0.06em;
  padding: 4px 10px;
  border-radius: 100px;
  background: rgba(26,255,140,0.12);
  border: 1px solid rgba(26,255,140,0.3);
  color: var(--green);
}

/* Card header stripe */
.card-stripe {
  height: 3px;
  width: 100%;
  transition: background 0.5s;
}
.st-green  .card-stripe { background: var(--green); }
.st-yellow .card-stripe { background: var(--yellow); }
.st-red    .card-stripe { background: var(--red); }

.card-body { padding: 22px 24px; }

/* ── Top row: road title + light ── */
.card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
}

.road-id {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: var(--mono);
  font-size: 0.72em;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-3);
  margin-bottom: 4px;
}
.road-id-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--border);
  font-weight: 700;
  font-size: 0.9em;
  color: var(--text-2);
}

.road-status-text {
  font-family: var(--sans);
  font-size: 1.05em;
  font-weight: 700;
  color: var(--text-1);
  letter-spacing: 0.01em;
}
.st-green  .road-status-text { color: var(--green); }
.st-yellow .road-status-text { color: var(--yellow); }
.st-red    .road-status-text { color: var(--red); }

/* Traffic light widget */
.tl-widget {
  display: flex;
  align-items: center;
  gap: 7px;
  background: rgba(0,0,0,0.4);
  border: 1px solid var(--border);
  border-radius: 100px;
  padding: 7px 12px;
}
.tl-bulb {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  transition: all 0.5s ease;
}
.tl-bulb.r { background: rgba(255,71,87,0.15); }
.tl-bulb.y { background: rgba(255,202,40,0.15); }
.tl-bulb.g { background: rgba(26,255,140,0.15); }

.st-red    .tl-bulb.r { background: var(--red);    box-shadow: 0 0 10px var(--red),   0 0 20px rgba(255,71,87,0.4); }
.st-yellow .tl-bulb.y { background: var(--yellow); box-shadow: 0 0 10px var(--yellow),0 0 20px rgba(255,202,40,0.4); }
.st-green  .tl-bulb.g { background: var(--green);  box-shadow: 0 0 10px var(--green), 0 0 20px rgba(26,255,140,0.4); }

/* ── Vehicle count ── */
.count-area {
  text-align: center;
  margin: 4px 0 20px;
  position: relative;
}

.count-ring {
  position: relative;
  display: inline-block;
}

.count-svg {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 120px;
  height: 120px;
  overflow: visible;
}

.count-ring-track {
  fill: none;
  stroke: var(--border);
  stroke-width: 2;
}
.count-ring-fill {
  fill: none;
  stroke-width: 2;
  stroke-linecap: round;
  transform: rotate(-90deg);
  transform-origin: 50% 50%;
  transition: stroke-dashoffset 1s ease, stroke 0.5s;
}
.st-green  .count-ring-fill { stroke: var(--green); }
.st-yellow .count-ring-fill { stroke: var(--yellow); }
.st-red    .count-ring-fill { stroke: var(--red); }

.vehicle-count {
  font-family: var(--mono);
  font-size: 3.4em;
  font-weight: 500;
  color: var(--text-1);
  line-height: 1;
  letter-spacing: -0.04em;
  display: block;
  transition: color 0.4s;
}
.st-green  .vehicle-count { color: var(--green); }
.st-yellow .vehicle-count { color: var(--yellow); }
.st-red    .vehicle-count { color: var(--red); }

.count-label {
  font-family: var(--mono);
  font-size: 0.72em;
  color: var(--text-3);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  margin-top: 4px;
  display: block;
}

/* ── Timer progress ── */
.timer-area {
  margin-bottom: 16px;
}

.timer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.timer-label {
  font-family: var(--mono);
  font-size: 0.68em;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-3);
}
.timer-value {
  font-family: var(--mono);
  font-size: 0.88em;
  font-weight: 500;
  color: var(--text-1);
  transition: color 0.3s;
}
.st-green  .timer-value { color: var(--green); }
.st-yellow .timer-value { color: var(--yellow); }

.progress-track {
  height: 4px;
  background: var(--border);
  border-radius: 4px;
  overflow: hidden;
  position: relative;
}
.progress-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.9s linear;
  position: relative;
  background: var(--blue);
  animation: progress-glow 2s ease infinite;
}
.st-green  .progress-fill { background: linear-gradient(90deg, var(--green),  rgba(26,255,140,0.6)); }
.st-yellow .progress-fill { background: linear-gradient(90deg, var(--yellow), rgba(255,202,40,0.6)); }
.st-red    .progress-fill { width: 0 !important; }

/* ── Stats grid ── */
.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.stat-cell {
  background: rgba(0,0,0,0.3);
  border: 1px solid var(--border);
  border-radius: var(--r-sm);
  padding: 10px 12px;
  transition: border-color 0.3s;
}
.stat-cell:hover { border-color: var(--border-hi); }

.stat-label {
  font-family: var(--mono);
  font-size: 0.6em;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-3);
  margin-bottom: 4px;
}
.stat-val {
  font-family: var(--mono);
  font-size: 1em;
  color: var(--text-1);
  font-weight: 500;
}
.stat-val.green  { color: var(--green); }
.stat-val.yellow { color: var(--yellow); }
.stat-val.red    { color: var(--red); }
.stat-val.blue   { color: var(--blue); }
.stat-val.purple { color: var(--purple); }
.stat-val.cyan   { color: var(--cyan); }

/* ══════════════════════════════════════════
   BOTTOM ROW
══════════════════════════════════════════ */
.bottom-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 32px;
}

/* ── History Chart ── */
.panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: 22px 24px;
  animation: fadeUp 0.6s ease both;
}
.panel-title {
  font-family: var(--sans);
  font-size: 0.88em;
  font-weight: 700;
  color: var(--text-1);
  margin-bottom: 18px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.panel-title-icon {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: rgba(61,139,255,0.1);
  border: 1px solid rgba(61,139,255,0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1em;
}

/* Bar chart */
.bar-chart-area {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  height: 110px;
  padding-bottom: 4px;
}
.bar-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  height: 100%;
  justify-content: flex-end;
}
.bar-fill {
  width: 100%;
  min-height: 3px;
  border-radius: 4px 4px 0 0;
  transition: height 0.8s cubic-bezier(0.34,1.56,0.64,1);
  background: var(--blue);
  position: relative;
  overflow: hidden;
}
.bar-fill::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(255,255,255,0.15), transparent);
}
.bar-fill.st-green  { background: var(--green); }
.bar-fill.st-yellow { background: var(--yellow); }
.bar-fill.st-red    { background: var(--red); }
.bar-fill.st-blue   { background: var(--blue); }

.bar-col-label {
  font-family: var(--mono);
  font-size: 0.65em;
  color: var(--text-3);
  letter-spacing: 0.05em;
}
.bar-col-val {
  font-family: var(--mono);
  font-size: 0.75em;
  color: var(--text-2);
  font-weight: 500;
}

/* Activity Log */
.log-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 180px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--border) transparent;
}
.log-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-family: var(--mono);
  font-size: 0.78em;
  color: var(--text-2);
  animation: fadeIn 0.3s ease;
  line-height: 1.5;
}
.log-time {
  color: var(--text-3);
  flex-shrink: 0;
  font-size: 0.9em;
}
.log-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-top: 5px;
  flex-shrink: 0;
}
.log-dot.green  { background: var(--green); }
.log-dot.yellow { background: var(--yellow); }
.log-dot.red    { background: var(--red); }
.log-dot.blue   { background: var(--blue); }

/* ══════════════════════════════════════════
   FOOTER
══════════════════════════════════════════ */
footer {
  border-top: 1px solid var(--border);
  padding: 20px 28px;
  max-width: 1480px;
  margin: 0 auto;
}
.footer-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.footer-left {
  font-family: var(--mono);
  font-size: 0.72em;
  color: var(--text-3);
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}
.footer-sep { color: var(--border-hi); }
.footer-right {
  font-family: var(--mono);
  font-size: 0.72em;
  color: var(--text-3);
}
.footer-right span { color: var(--blue); }

/* ══════════════════════════════════════════
   RESPONSIVE
══════════════════════════════════════════ */
@media (max-width: 1100px) {
  .kpi-strip { grid-template-columns: repeat(3, 1fr); }
  .bottom-row { grid-template-columns: 1fr; }
}
@media (max-width: 768px) {
  main { padding: 20px 16px 40px; }
  .header-inner { padding: 0 16px; }
  .kpi-strip { grid-template-columns: repeat(2, 1fr); }
  .ticker-wrap { display: none; }
  .kpi-strip .kpi-card:nth-child(5) { grid-column: span 2; }
  footer { padding: 16px; }
  .footer-inner { flex-direction: column; gap: 8px; align-items: flex-start; }
}
@media (max-width: 480px) {
  .kpi-strip { grid-template-columns: 1fr 1fr; }
  .road-grid  { grid-template-columns: 1fr; }
  .header-meta .meta-chip:not(.live) { display: none; }
}
</style>
</head>
<body>
<div class="bg-grid"></div>
<div class="bg-glow"></div>
<div id="offline-banner">⚠ Server connection lost — reconnecting…</div>
<div id="toast-stack"></div>

<!-- ══════════ HEADER ══════════ -->
<header>
  <div class="header-inner">
    <div class="logo" onclick="location.reload()">
      <div class="logo-mark">
        <div class="logo-icon-bg"></div>
        <span class="logo-emoji">🚦</span>
      </div>
      <div class="logo-text">
        <div class="logo-title">Smart Traffic</div>
        <div class="logo-subtitle">Raspberry Pi · YOLO11</div>
      </div>
    </div>

    <div class="ticker-wrap">
      <div class="ticker-track" id="ticker">
        <span class="ticker-item">TOTAL VEHICLES <span class="hi" id="t-toplam">—</span></span>
        <span class="ticker-item">ACTIVE PHASE <span class="hi" id="t-faz">—</span></span>
        <span class="ticker-item">FPS <span class="hi" id="t-fps">—</span></span>
        <span class="ticker-item">UPTIME <span class="hi" id="t-uptime">—</span></span>
        <span class="ticker-item">UPDATE <span class="hi" id="t-zaman">—</span></span>
        <!-- Duplicate for seamless loop -->
        <span class="ticker-item">TOTAL VEHICLES <span class="hi" id="t-toplam2">—</span></span>
        <span class="ticker-item">ACTIVE PHASE <span class="hi" id="t-faz2">—</span></span>
        <span class="ticker-item">FPS <span class="hi" id="t-fps2">—</span></span>
        <span class="ticker-item">UPTIME <span class="hi" id="t-uptime2">—</span></span>
        <span class="ticker-item">UPDATE <span class="hi" id="t-zaman2">—</span></span>
      </div>
    </div>

    <div class="header-meta">
      <div class="meta-chip live">
        <span class="live-dot"></span>LIVE
      </div>
      <div class="meta-chip" id="chip-aktif">LANE —</div>
      <div class="meta-chip" id="chip-zaman">—</div>
    </div>
  </div>
</header>

<!-- ══════════ MAIN ══════════ -->
<div class="content-wrap">
<main>

  <!-- KPI Strip -->
  <div class="section-head">
    <span class="section-title">Summary</span>
    <div class="section-line"></div>
  </div>

  <div class="kpi-strip" id="kpi-strip">
    <div class="kpi-card">
      <div class="kpi-label">Total Vehicles</div>
      <div class="kpi-value accent" id="k-toplam">0</div>
      <span class="kpi-icon">🚗</span>
      <div class="kpi-bar"><div class="kpi-bar-fill" id="k-toplam-bar" style="width:0%"></div></div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Active Phase</div>
      <div class="kpi-value" id="k-faz" style="font-size:1.3em;margin-top:4px">WAIT</div>
      <span class="kpi-icon">⚡</span>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Lane Count</div>
      <div class="kpi-value" id="k-serit">—</div>
      <span class="kpi-icon">🛣️</span>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">System Uptime</div>
      <div class="kpi-value green" id="k-uptime">00:00:00</div>
      <span class="kpi-icon">⏱️</span>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">FPS</div>
      <div class="kpi-value" id="k-fps">—</div>
      <span class="kpi-icon">📷</span>
      <div class="kpi-bar"><div class="kpi-bar-fill" id="k-fps-bar" style="background:var(--green);width:0%"></div></div>
    </div>
  </div>

  <!-- Road Cards -->
  <div class="section-head">
    <span class="section-title">Lane Status</span>
    <div class="section-line"></div>
  </div>

  <div class="road-grid" id="road-grid"></div>

  <!-- Bottom Row -->
  <div class="section-head" style="margin-top:4px">
    <span class="section-title">Analysis</span>
    <div class="section-line"></div>
  </div>

  <div class="bottom-row">
    <!-- Bar chart -->
    <div class="panel">
      <div class="panel-title">
        <div class="panel-title-icon">📊</div>
        Vehicle Distribution
      </div>
      <div class="bar-chart-area" id="bar-chart"></div>
    </div>

    <!-- Activity Log -->
    <div class="panel">
      <div class="panel-title">
        <div class="panel-title-icon">📋</div>
        Activity Log
      </div>
      <div class="log-list" id="log-list">
        <div class="log-item">
          <span class="log-time">—</span>
          <span class="log-dot blue"></span>
          <span>System started</span>
        </div>
      </div>
    </div>
  </div>

</main>

<footer>
  <div class="footer-inner">
    <div class="footer-left">
      <span>Raspberry Pi</span>
      <span class="footer-sep">·</span>
      <span>YOLO11</span>
      <span class="footer-sep">·</span>
      <span>Flask</span>
      <span class="footer-sep">·</span>
      <span>OpenCV</span>
    </div>
    <div class="footer-right">Smart Traffic Control System <span>v3.0</span></div>
  </div>
</footer>
</div>

<script>
/* ══════════════════════════════════════════
   STATE
══════════════════════════════════════════ */
const STATE = {
  startTime:    Date.now(),
  errorCount:    0,
  prevActive:    -1,
  prevCounts:  [],
  logItems:     [],
  initialized:  false,
  MAX_VEHICLE:     20,
  MAX_LOG:      40,
};

/* ══════════════════════════════════════════
   UTILS
══════════════════════════════════════════ */
function uptimeStr() {
  const s  = Math.floor((Date.now() - STATE.startTime) / 1000);
  const hh = String(Math.floor(s / 3600)).padStart(2, '0');
  const mm = String(Math.floor((s % 3600) / 60)).padStart(2, '0');
  const ss = String(s % 60).padStart(2, '0');
  return `${hh}:${mm}:${ss}`;
}

const CLS_MAP  = ['st-red', 'st-yellow', 'st-green'];
const TXT_MAP  = ['RED', 'YELLOW', 'GREEN'];
const DCLS_MAP = ['red', 'yellow', 'green'];

function stateColor(state) {
  return ['red','yellow','green'][state] ?? 'blue';
}

function ringDasharray(pct, r = 46) {
  const circ = 2 * Math.PI * r;
  const fill = circ * Math.max(0, Math.min(1, pct / 100));
  return `${fill} ${circ - fill}`;
}

/* ══════════════════════════════════════════
   TOAST
══════════════════════════════════════════ */
function toast(msg, type = 'blue') {
  const stack = document.getElementById('toast-stack');
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span class="toast-dot"></span>${msg}`;
  stack.prepend(el);
  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transform = 'translateX(20px)';
    el.style.transition = 'opacity .3s, transform .3s';
    setTimeout(() => el.remove(), 300);
  }, 3200);
  // Keep max 4 toasts
  while (stack.children.length > 4) stack.lastChild.remove();
}

/* ══════════════════════════════════════════
   LOG
══════════════════════════════════════════ */
function addLog(msg, type = 'blue') {
  const now = new Date().toLocaleTimeString('tr', { hour:'2-digit', minute:'2-digit', second:'2-digit' });
  STATE.logItems.unshift({ time: now, msg, type });
  if (STATE.logItems.length > STATE.MAX_LOG) STATE.logItems.pop();
  renderLog();
}

function renderLog() {
  const el = document.getElementById('log-list');
  el.innerHTML = STATE.logItems.slice(0, 20).map(item => `
    <div class="log-item">
      <span class="log-time">${item.time}</span>
      <span class="log-dot ${item.type}"></span>
      <span>${item.msg}</span>
    </div>
  `).join('');
}

/* ══════════════════════════════════════════
   ROAD CARD BUILDER
══════════════════════════════════════════ */
function buildCard(s, active, delay = 0) {
  const isActive = active === s.id - 1;
  const cls      = CLS_MAP[s.state];
  const dcls     = DCLS_MAP[s.state];
  const remaining    = s.remaining || 0;
  const calculated    = s.calculated || 0;
  const pct      = calculated > 0 ? Math.min(100, (remaining / calculated) * 100) : 0;
  const vehiclePct  = Math.min(100, (s.vehicles / STATE.MAX_VEHICLE) * 100);
  const circ     = 2 * Math.PI * 46;
  const fill     = circ * (vehiclePct / 100);

  const elapsed  = (Date.now() - STATE.startTime) / 60000;
  const eff      = s.passages > 0 ? (s.passages / Math.max(elapsed, 0.1)).toFixed(1) : '—';

  return `
  <div class="road-card ${cls}" id="rc-${s.id}" style="animation-delay:${delay}s">
    ${isActive ? '<div class="active-badge">⚡ Active</div>' : ''}
    <div class="card-stripe"></div>
    <div class="card-body">
      <div class="card-top">
        <div>
          <div class="road-id">
            <span class="road-id-num">${s.id}</span>
            LANE
          </div>
          <div class="road-status-text">${TXT_MAP[s.state]}${isActive ? ' · Right of Way' : ''}</div>
        </div>
        <div class="tl-widget">
          <span class="tl-bulb r"></span>
          <span class="tl-bulb y"></span>
          <span class="tl-bulb g"></span>
        </div>
      </div>

      <div class="count-area">
        <svg class="count-svg" viewBox="0 0 100 100">
          <circle class="count-ring-track" cx="50" cy="50" r="46"/>
          <circle class="count-ring-fill" id="ring-${s.id}"
            cx="50" cy="50" r="46"
            stroke-dasharray="${fill} ${circ - fill}"
            stroke-dashoffset="0"/>
        </svg>
        <span class="vehicle-count" id="vc-${s.id}">${s.vehicles}</span>
        <span class="count-label">vehicles</span>
      </div>

      <div class="timer-area">
        <div class="timer-header">
          <span class="timer-label">Remaining Time</span>
          <span class="timer-value" id="tv-${s.id}">${remaining.toFixed(1)}s</span>
        </div>
        <div class="progress-track">
          <div class="progress-fill" id="pf-${s.id}" style="width:${pct}%"></div>
        </div>
      </div>

      <div class="stats-grid">
        <div class="stat-cell">
          <div class="stat-label">Calculated Time</div>
          <div class="stat-val cyan" id="st-calc-${s.id}">${calculated > 0 ? calculated.toFixed(0) + 's' : '—'}</div>
        </div>
        <div class="stat-cell">
          <div class="stat-label">Total Passages</div>
          <div class="stat-val purple" id="st-pass-${s.id}">${s.passages ?? 0}</div>
        </div>
        <div class="stat-cell">
          <div class="stat-label">Efficiency</div>
          <div class="stat-val green" id="st-eff-${s.id}">${eff !== '—' ? eff + '/min' : '—'}</div>
        </div>
        <div class="stat-cell">
          <div class="stat-label">Waiting</div>
          <div class="stat-val ${dcls}" id="st-wait-${s.id}">${(s.waiting ?? 0).toFixed(1)}s</div>
        </div>
      </div>
    </div>
  </div>`;
}

/* ══════════════════════════════════════════
   BAR CHART
══════════════════════════════════════════ */
function updateBarChart(lanes) {
  const el  = document.getElementById('bar-chart');
  const max = Math.max(...lanes.map(s => s.vehicles), 1);
  const colors = ['st-red','st-yellow','st-green','st-blue'];

  el.innerHTML = lanes.map((s, i) => {
    const h = Math.max(3, (s.vehicles / max) * 100);
    return `
      <div class="bar-col">
        <div class="bar-col-val">${s.vehicles}</div>
        <div class="bar-fill ${CLS_MAP[s.state]}" style="height:${h}%"></div>
        <div class="bar-col-label">Lane ${s.id}</div>
      </div>`;
  }).join('');
}

/* ══════════════════════════════════════════
   TICKER UPDATE
══════════════════════════════════════════ */
function updateTicker(d) {
  const activeTxt = d.active >= 0 ? `Lane ${d.active + 1}` : '—';
  [
    ['t-toplam','t-toplam2', d.total],
    ['t-faz',   't-faz2',   (d.phase || 'WAIT').toUpperCase()],
    ['t-fps',   't-fps2',   d.fps ?? '—'],
    ['t-uptime','t-uptime2', uptimeStr()],
    ['t-zaman', 't-zaman2', d.time],
  ].forEach(([id1, id2, val]) => {
    const a = document.getElementById(id1);
    const b = document.getElementById(id2);
    if (a) a.textContent = val;
    if (b) b.textContent = val;
  });
}

/* ══════════════════════════════════════════
   DIFF UPDATE (no full re-render)
══════════════════════════════════════════ */
function diffUpdate(lanes, active) {
  const elapsed = (Date.now() - STATE.startTime) / 60000;

  lanes.forEach((s, i) => {
    const card = document.getElementById('rc-' + s.id);
    if (!card) return;

    const isActive = active === s.id - 1;
    const cls      = CLS_MAP[s.state];

    // State class
    if (!card.classList.contains(cls)) {
      card.className = `road-card ${cls}`;
    }

    // Active badge
    let badge = card.querySelector('.active-badge');
    if (isActive && !badge) {
      card.insertAdjacentHTML('afterbegin', '<div class="active-badge">⚡ Active</div>');
    } else if (!isActive && badge) {
      badge.remove();
    }

    // Vehicle count
    const vcEl = document.getElementById('vc-' + s.id);
    if (vcEl && vcEl.textContent != s.vehicles) {
      vcEl.textContent = s.vehicles;
      vcEl.style.animation = 'none';
      vcEl.offsetHeight;
      vcEl.style.animation = 'countPop .35s ease';
    }

    // Ring
    const ring = document.getElementById('ring-' + s.id);
    if (ring) {
      const circ = 2 * Math.PI * 46;
      const vehiclePct = Math.min(100, (s.vehicles / STATE.MAX_VEHICLE) * 100);
      const fill = circ * (vehiclePct / 100);
      ring.setAttribute('stroke-dasharray', `${fill} ${circ - fill}`);
    }

    // Progress & timer
    const remaining  = s.remaining || 0;
    const calculated  = s.calculated || 0;
    const pct    = calculated > 0 ? Math.min(100, (remaining / calculated) * 100) : 0;
    const tvEl   = document.getElementById('tv-' + s.id);
    const pfEl   = document.getElementById('pf-' + s.id);
    if (tvEl) tvEl.textContent = remaining.toFixed(1) + 's';
    if (pfEl) pfEl.style.width = pct + '%';

    // Status text
    const stEl = card.querySelector('.road-status-text');
    if (stEl) stEl.textContent = TXT_MAP[s.state] + (isActive ? ' · Right of Way' : '');

    // Stats
    const eff = s.passages > 0 ? (s.passages / Math.max(elapsed, 0.1)).toFixed(1) + '/min' : '—';
    const vals = {
      [`st-pass-${s.id}`]: [s.passages ?? 0, 'purple'],
      [`st-eff-${s.id}`]:   [eff, 'green'],
      [`st-wait-${s.id}`]:   [(s.waiting ?? 0).toFixed(1) + 's', DCLS_MAP[s.state]],
      [`st-calc-${s.id}`]: [calculated > 0 ? calculated.toFixed(0) + 's' : '—', 'cyan'],
    };
    for (const [id, [val, color]] of Object.entries(vals)) {
      const el = document.getElementById(id);
      if (el) { el.textContent = val; el.className = `stat-val ${color}`; }
    }
  });
}

/* ══════════════════════════════════════════
   MAIN FETCH + RENDER
══════════════════════════════════════════ */
async function update() {
  try {
    const r = await fetch('/api', { signal: AbortSignal.timeout(3000) });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const d = await r.json();

    STATE.errorCount = 0;
    document.getElementById('offline-banner').style.display = 'none';

    // ── Header chips
    document.getElementById('chip-aktif').textContent =
      d.active >= 0 ? `Lane ${d.active + 1}` : 'Waiting';
    document.getElementById('chip-zaman').textContent = d.time;
    document.getElementById('k-uptime').textContent   = uptimeStr();

    // ── Ticker
    updateTicker(d);

    // ── KPI
    document.getElementById('k-toplam').textContent  = d.total;
    document.getElementById('k-faz').textContent     = (d.phase || 'WAIT').toUpperCase();
    document.getElementById('k-serit').textContent   = d.lanes.length;
    document.getElementById('k-fps').textContent     = d.fps ?? '—';

    const fpsBarPct = Math.min(100, ((d.fps || 0) / 60) * 100);
    document.getElementById('k-fps-bar').style.width    = fpsBarPct + '%';
    document.getElementById('k-toplam-bar').style.width =
      Math.min(100, (d.total / (d.lanes.length * STATE.MAX_VEHICLE)) * 100) + '%';

    // ── Active road change event
    if (d.active !== STATE.prevActive && d.active >= 0) {
      const msg = `Lane ${d.active + 1} received right of way`;
      toast(msg, 'green');
      addLog(msg, 'green');
      STATE.prevActive = d.active;
    }

    // ── Vehicle count change logs
    d.lanes.forEach((s, i) => {
      const prev = STATE.prevCounts[i] ?? -1;
      if (prev >= 0 && s.vehicles !== prev) {
        const diff = s.vehicles - prev;
        if (Math.abs(diff) >= 3) {
          const type = diff > 0 ? 'yellow' : 'green';
          addLog(
            `Lane ${s.id}: vehicle count ${prev} → ${s.vehicles} (${diff > 0 ? '+' : ''}${diff})`,
            type
          );
        }
      }
      STATE.prevCounts[i] = s.vehicles;
    });

    // ── Bar chart
    updateBarChart(d.lanes);

    // ── Road cards
    const grid = document.getElementById('road-grid');
    if (!STATE.initialized || grid.children.length !== d.lanes.length) {
      grid.innerHTML = d.lanes.map((s, i) => buildCard(s, d.active, i * 0.08)).join('');
      STATE.initialized = true;
      if (!STATE._loggedStart) {
        addLog(`System started. ${d.lanes.length} lanes active.`, 'blue');
        STATE._loggedStart = true;
      }
    } else {
      diffUpdate(d.lanes, d.active);
    }

  } catch (e) {
    STATE.errorCount++;
    if (STATE.errorCount >= 3) {
      document.getElementById('offline-banner').style.display = 'block';
    }
    if (STATE.errorCount === 3) {
      toast('Server connection lost!', 'red');
      addLog('Server connection lost', 'red');
    }
    console.debug('[traffic] API error:', e.message);
  }
}

/* ══════════════════════════════════════════
   POLLING + VISIBILITY
══════════════════════════════════════════ */
let interval = setInterval(update, 1200);

document.addEventListener('visibilitychange', () => {
  clearInterval(interval);
  if (document.hidden) {
    interval = setInterval(update, 6000);
  } else {
    update();
    interval = setInterval(update, 1200);
  }
});

// Initial fetch
update();
</script>
</body>
</html>"""


class WebPanel:
    def __init__(self, light_thread, data):
        self.light = light_thread
        self.data = data
        self.app = Flask(__name__)
        self.app.secret_key = secrets.token_hex(32)  # Session resets on every restart
        self.start_time = datetime.now()
        self._cache = {}
        self._cache_time = datetime.min
        self._register_routes()

    def _get_cached_snapshot(self):
        """Cache snapshot for 100ms for performance"""
        now = datetime.now()
        if (now - self._cache_time).total_seconds() < 0.1:
            return self._cache
        self._cache = {
            'snap': self.light.snapshot(),
            'full':  self.data.read_full(),
            'time': now,
        }
        self._cache_time = now
        return self._cache

    def _register_routes(self):

        @self.app.route("/login", methods=["GET", "POST"])
        def login():
            if request.method == "POST":
                username = request.form.get("kullanici", "").strip()
                password     = request.form.get("sifre", "")
                expected  = AUTH_USERS.get(username)
                if expected and secrets.compare_digest(expected, hash_password(password)):
                    session['logged_in'] = True
                    session['username'] = username
                    return redirect('/')
                return render_template_string(LOGIN_HTML, hata="Incorrect username or password.")
            if session.get('logged_in'):
                return redirect('/')
            return render_template_string(LOGIN_HTML, hata=None)

        @self.app.route("/logout")
        def logout():
            session.clear()
            return redirect('/login')

        @self.app.route("/")
        @login_required
        def index():
            return HTML_PAGE

        @self.app.route("/api")
        @login_required
        def api():
            cached  = self._get_cached_snapshot()
            snap    = cached['snap']
            full     = cached['full']
            counts = full["counts"]
            n       = len(counts)

            total_time = (datetime.now() - self.start_time).total_seconds() / 60

            lanes = []
            for i in range(n):
                efficiency = snap["passages"][i] / max(total_time, 0.1)
                lanes.append({
                    "id":          i + 1,
                    "vehicles":        counts[i],
                    "state":       snap["state"][i],
                    "state_text":  ["RED", "YELLOW", "GREEN"][snap["state"][i]],
                    "remaining":       round(snap["remaining"][i], 1),
                    "calculated":       round(snap["calculated"][i], 1),
                    "passages":       snap["passages"][i],
                    "waiting":     round(snap["waiting"][i], 1),
                    "efficiency":  round(efficiency, 1),
                })

            response = jsonify({
                "lanes": lanes,
                "total":   full["total"],
                "active":    snap["active"],
                "phase":      snap["phase"],
                "fps":      full["fps"],
                "time":    datetime.now().strftime("%H:%M:%S"),
                "uptime":   str(datetime.now() - self.start_time).split('.')[0],
            })
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            return response

        @self.app.route("/api/settings")
        @login_required
        def api_settings():
            return jsonify({
                "model":        Ayarlar.MODEL,
                "confidence":        Ayarlar.GUVEN_ESIGI,
                "min_green":    Ayarlar.MIN_YESIL,
                "max_green":    Ayarlar.MAX_YESIL,
                "yellow_duration":    Ayarlar.SARI_SURE,
                "adaptive_mode":  Ayarlar.ADAPTIF_MOD,
                "gpio_active":   Ayarlar.GPIO_AKTIF,
                "lane_count": len(Ayarlar.GPIO_PINLER),
                "web_port":     Ayarlar.WEB_PORT,
            })

        @self.app.route("/api/status")
        @login_required
        def api_status():
            """Detailed system status"""
            cached  = self._get_cached_snapshot()
            snap    = cached['snap']
            full     = cached['full']
            return jsonify({
                "system": {
                    "uptime":      str(datetime.now() - self.start_time).split('.')[0],
                    "fps":         full["fps"],
                    "total_vehicles": full["total"],
                    "active_phase":   snap["phase"],
                },
                "lanes": {
                    f"lane_{i+1}": {
                        "vehicles":          full["counts"][i],
                        "state":         ["RED", "YELLOW", "GREEN"][snap["state"][i]],
                        "passage_count":  snap["passages"][i],
                        "total_waiting": round(snap["waiting"][i], 1),
                    }
                    for i in range(len(full["counts"]))
                },
            })

        @self.app.errorhandler(404)
        def not_found(e):
            return jsonify({"error": "Page not found", "code": 404}), 404

        @self.app.errorhandler(500)
        def server_error(e):
            return jsonify({"error": "Server error", "code": 500}), 500

    def start(self):
        """Start Flask server in a separate thread"""
        def run_flask():
            try:
                self.app.run(
                    host=Ayarlar.WEB_HOST,
                    port=Ayarlar.WEB_PORT,
                    debug=False,
                    use_reloader=False,
                    threaded=True,
                )
            except Exception as e:
                logging.getLogger("traffic").error(f"Web server error: {e}")

        t = threading.Thread(target=run_flask, daemon=True, name="WebPanel")
        t.start()
        logging.getLogger("traffic").info(
            f"🌐 Web panel started: http://{Ayarlar.WEB_HOST}:{Ayarlar.WEB_PORT}"
        )
