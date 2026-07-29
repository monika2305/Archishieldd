import streamlit as st
from textwrap import dedent

st.set_page_config(
    page_title="IFC Semantic Data-Loss Analyzer",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── If already logged in, skip to main app ─────────────────────────────────
if st.session_state.get("logged_in"):
    st.switch_page("pages/0_Home.py")


def render_html_block(html: str) -> None:
    st.markdown("\n".join(line.strip() for line in dedent(html).splitlines()), unsafe_allow_html=True)

# ── Global styles ────────────────────────────────────────────────────────────
render_html_block("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;700;800&display=swap');

*, *::before, *::after { box-sizing: border-box; }

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
.main {
    background-color: #050810 !important;
    color: #e2e8f4 !important;
    font-family: 'Syne', sans-serif !important;
}

.block-container {
    padding: 0 !important;
    max-width: 100% !important;
}

header[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stSidebar"]       { display: none !important; }
[data-testid="collapsedControl"]{ display: none !important; }

/* ── Style ALL Streamlit primary buttons as CTA ── */
div[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #00c8ff 0%, #0055ee 100%) !important;
    color: #fff !important;
    border: none !important;
    font-family: 'Syne', sans-serif !important;
    font-size: 15px !important;
    font-weight: 700 !important;
    letter-spacing: 0.06em !important;
    padding: 14px 40px !important;
    border-radius: 6px !important;
    box-shadow: 0 0 32px rgba(0,136,255,0.4) !important;
    transition: all 0.2s ease !important;
    cursor: pointer !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    box-shadow: 0 0 52px rgba(0,136,255,0.65) !important;
    transform: translateY(-2px) !important;
}

/* Center all buttons */
div[data-testid="stButton"] { text-align: center !important; }

/* Divider */
.divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, #1a2540 30%, #1a2540 70%, transparent);
    margin: 0 48px;
}

/* HERO */
.hero-wrap {
    min-height: 72vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 80px 32px 40px;
    background:
        radial-gradient(ellipse 80% 50% at 50% -5%, rgba(0,200,255,0.13) 0%, transparent 65%),
        radial-gradient(ellipse 40% 30% at 80% 65%, rgba(0,100,255,0.08) 0%, transparent 60%),
        #050810;
    position: relative;
    overflow: hidden;
}

.hero-wrap::before {
    content: '';
    position: absolute; inset: 0;
    background-image:
        linear-gradient(rgba(0,200,255,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,200,255,0.03) 1px, transparent 1px);
    background-size: 48px 48px;
    pointer-events: none;
}

.hero-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(0,200,255,0.08);
    border: 1px solid rgba(0,200,255,0.28);
    border-radius: 100px;
    padding: 6px 18px;
    font-family: 'Space Mono', monospace;
    font-size: 11px;
    letter-spacing: 0.12em;
    color: #00c8ff;
    text-transform: uppercase;
    margin-bottom: 32px;
}

.hero-badge-dot {
    width: 6px; height: 6px;
    background: #00c8ff;
    border-radius: 50%;
    box-shadow: 0 0 8px #00c8ff;
    display: inline-block;
    animation: blink 2s ease infinite;
}

@keyframes blink {
    0%,100% { opacity:1; } 50% { opacity:0.3; }
}

.hero-title {
    font-family: 'Syne', sans-serif;
    font-size: clamp(34px, 5.5vw, 68px);
    font-weight: 800;
    line-height: 1.06;
    letter-spacing: -0.02em;
    color: #f0f4ff;
    margin-bottom: 20px;
}

.hero-title .accent {
    background: linear-gradient(135deg, #00c8ff 0%, #0066ff 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.hero-sub {
    font-size: clamp(14px, 1.8vw, 18px);
    color: #7a8aaa;
    max-width: 100%;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.65;
    margin: 0 auto 0;
}

/* Stats row */
.stats-bg {
    background:
        radial-gradient(ellipse 80% 50% at 50% -5%, rgba(0,200,255,0.07) 0%, transparent 65%),
        #050810;
    padding: 0 32px 64px;
}

.stats-row {
    display: flex;
    gap: 20px;
    justify-content: center;
    flex-wrap: wrap;
    padding-top: 40px;
}

.stat-card {
    background: #0a0f1e;
    border: 1px solid #1a2540;
    border-radius: 10px;
    padding: 22px 32px;
    text-align: center;
    min-width: 140px;
}

.stat-val {
    font-family: 'Space Mono', monospace;
    font-size: 30px;
    font-weight: 700;
    color: #00c8ff;
    margin-bottom: 4px;
}

.stat-label {
    font-size: 12px;
    color: #4a5a7a;
    letter-spacing: 0.04em;
}

/* SECTIONS */
.section-wrap {
    max-width: 1060px;
    margin: 0 auto;
    padding: 90px 32px;
}

.section-eyebrow {

.split-wrap {
    max-width: 1400px;
    margin: 0 auto;
    padding: 0 32px 0;
}

.split-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.08fr) minmax(0, 0.92fr);
    gap: 28px;
    align-items: start;
}

.split-card {
    background: #080d1c;
    border: 1px solid #1a2540;
    border-radius: 16px;
    padding: 34px 30px 30px;
    min-width: 0;
}

.split-card .section-wrap {
    padding: 0;
    margin: 0;
}

.split-card .section-body {
    margin-bottom: 26px;
}

.split-card .bim-canvas {
    margin-top: 8px;
}

.split-card .wf-wrap {
    padding: 30px 24px;
}

.split-card .wf-step {
    min-width: 92px;
    max-width: 130px;
}

.split-card .wf-desc {
    font-size: 10px;
}

.split-card .wf-arrow {
    padding-top: 8px;
}

.svg-stage {
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid #1a2540;
    background: #060c1a;
    margin-bottom: 0;
}

.building-demo {
    padding: 4px 0 0;
}

.building-stage {
    position: relative;
    min-height: 360px;
    border-radius: 16px;
    background:
        radial-gradient(ellipse 65% 55% at 50% 15%, rgba(0,200,255,0.09) 0%, transparent 70%),
        linear-gradient(180deg, rgba(8,13,28,0.95) 0%, rgba(5,8,16,0.98) 100%);
    border: 1px solid #1a2540;
    overflow: hidden;
    padding: 28px 22px 20px;
}

.building-stage::before {
    content: '';
    position: absolute;
    inset: 0;
    background-image:
        linear-gradient(rgba(0,200,255,0.035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,200,255,0.035) 1px, transparent 1px);
    background-size: 28px 28px;
    pointer-events: none;
}

.building-stage::after {
    content: '';
    position: absolute;
    left: 10%;
    right: 10%;
    bottom: 34px;
    height: 18px;
    background: radial-gradient(ellipse at center, rgba(0,0,0,0.5) 0%, transparent 72%);
    filter: blur(5px);
}

.building-labels {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 12px;
    font-family: 'Space Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #2f4166;
}

.building-hint {
    color: #ff4d6d;
}

.building-wrap {
    position: relative;
    width: min(760px, 100%);
    margin: 0 auto;
    height: 290px;
}

.building-shadow {
    position: absolute;
    left: 50%;
    bottom: 10px;
    transform: translateX(-50%);
    width: 88%;
    height: 26px;
    background: radial-gradient(ellipse at center, rgba(0,0,0,0.6) 0%, transparent 72%);
    filter: blur(8px);
}

.building {
    position: absolute;
    left: 50%;
    bottom: 24px;
    transform: translateX(-50%);
    width: 430px;
    height: 250px;
}

.roof {
    position: absolute;
    left: 28px;
    top: 0;
    width: 374px;
    height: 44px;
    background: linear-gradient(180deg, #131d33 0%, #0d1525 100%);
    clip-path: polygon(12% 0%, 88% 0%, 100% 100%, 0% 100%);
    border: 1px solid #223154;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
}

.roof-line {
    position: absolute;
    left: 56px;
    top: 12px;
    width: 318px;
    height: 4px;
    border-radius: 999px;
    background: linear-gradient(90deg, rgba(0,200,255,0.05), rgba(0,200,255,0.5), rgba(0,200,255,0.05));
}

.facade {
    position: absolute;
    left: 20px;
    top: 34px;
    width: 390px;
    height: 206px;
    background: linear-gradient(180deg, #101a2f 0%, #0c1424 100%);
    border: 1px solid #223154;
    border-radius: 8px 8px 4px 4px;
    overflow: visible;
}

.facade::before {
    content: '';
    position: absolute;
    inset: 0;
    background:
        linear-gradient(90deg, transparent 0 14%, rgba(0,200,255,0.06) 14% 15%, transparent 15% 30%, rgba(0,200,255,0.06) 30% 31%, transparent 31% 48%, rgba(0,200,255,0.06) 48% 49%, transparent 49% 66%, rgba(0,200,255,0.06) 66% 67%, transparent 67% 84%, rgba(0,200,255,0.06) 84% 85%, transparent 85% 100%),
        linear-gradient(180deg, transparent 0 23%, rgba(255,255,255,0.02) 23% 24%, transparent 24% 48%, rgba(255,255,255,0.02) 48% 49%, transparent 49% 73%, rgba(255,255,255,0.02) 73% 74%, transparent 74% 100%);
    opacity: 0.6;
}

.podium {
    position: absolute;
    left: 10px;
    bottom: 0;
    width: 410px;
    height: 34px;
    background: linear-gradient(180deg, #0e1729 0%, #0a111e 100%);
    border: 1px solid #223154;
    border-radius: 6px;
}

.entry {
    position: absolute;
    left: 170px;
    bottom: 34px;
    width: 80px;
    height: 72px;
    background: linear-gradient(180deg, #141f36 0%, #0b1220 100%);
    border: 1px solid #2c3c63;
    border-bottom: none;
    border-radius: 8px 8px 0 0;
}

.door {
    position: absolute;
    left: 21px;
    bottom: 0;
    width: 38px;
    height: 52px;
    border-radius: 8px 8px 0 0;
    background: linear-gradient(180deg, #13213a 0%, #08111d 100%);
    border: 1px solid #2a3a5e;
}

.door::after {
    content: '';
    position: absolute;
    left: 17px;
    top: 14px;
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: #00c8ff;
    box-shadow: 0 0 8px rgba(0,200,255,0.75);
}

.floors {
    position: absolute;
    left: 32px;
    right: 32px;
    top: 48px;
    bottom: 42px;
    display: grid;
    grid-template-rows: repeat(3, 1fr);
    gap: 10px;
}

.floor {
    display: grid;
    grid-template-columns: 1.2fr 0.9fr 1.2fr 0.9fr 1.2fr 0.9fr;
    gap: 10px;
}

.window {
    position: relative;
    border-radius: 5px;
    background: linear-gradient(180deg, #1a2a49 0%, #10192b 100%);
    border: 1px solid rgba(76, 107, 160, 0.35);
    box-shadow: inset 0 0 0 1px rgba(255,255,255,0.02);
    overflow: visible;
}

.window.proxy { cursor: pointer; }

.window::before {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(180deg, rgba(120,180,255,0.22) 0%, rgba(120,180,255,0.06) 35%, rgba(0,0,0,0) 100%);
}

.window.proxy {
    border-color: rgba(255, 69, 96, 0.9);
    background: linear-gradient(180deg, rgba(255,69,96,0.30) 0%, rgba(58,9,18,0.9) 100%);
    box-shadow: 0 0 0 1px rgba(255,69,96,0.25), 0 0 22px rgba(255,69,96,0.12);
}

.window.proxy::after {
    content: 'PROXY';
    position: absolute;
    top: 4px;
    right: 4px;
    padding: 2px 5px;
    border-radius: 999px;
    font-family: 'Space Mono', monospace;
    font-size: 7px;
    font-weight: 700;
    color: #fff;
    background: #ff4560;
    letter-spacing: 0.08em;
    pointer-events: none;
}

.window.proxy .win-tip {
    display: none;
    position: absolute;
    bottom: calc(100% + 10px);
    left: 50%;
    transform: translateX(-50%);
    background: #0d1525;
    border: 1px solid rgba(0,200,255,0.35);
    border-radius: 9px;
    padding: 12px 14px;
    width: 190px;
    z-index: 9999;
    box-shadow: 0 8px 32px rgba(0,0,0,0.7), 0 0 20px rgba(0,200,255,0.15);
    pointer-events: none;
    white-space: normal;
}

.window.proxy:hover .win-tip { display: block; }

.win-tip-head {
    font-family: 'Space Mono', monospace;
    font-size: 9px;
    color: #ff4560;
    margin-bottom: 7px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

.win-tip-suggest {
    font-size: 12px;
    color: #c0cce4;
    margin-bottom: 9px;
    line-height: 1.4;
}

.win-tip-suggest strong { color: #e2e8f4; }

.window.glass {
    background: linear-gradient(180deg, rgba(56, 96, 155, 0.7) 0%, rgba(18, 28, 49, 0.95) 100%);
}

.window-wide {
    grid-column: span 2;
}

.building-core {
    position: absolute;
    right: 14px;
    top: 48px;
    width: 42px;
    bottom: 34px;
    background: linear-gradient(180deg, #12203a 0%, #0b1321 100%);
    border: 1px solid #223154;
    border-radius: 6px;
}

.building-core .window {
    width: 20px;
    height: 16px;
    margin: 8px auto 0;
}

.structure-tag {
    position: absolute;
    left: 50%;
    bottom: 2px;
    transform: translateX(-50%);
    font-family: 'Space Mono', monospace;
    font-size: 10px;
    color: #52678f;
    letter-spacing: 0.06em;
}

.legend-row {
    display: flex;
    flex-wrap: wrap;
    gap: 14px;
    justify-content: center;
    margin-top: 14px;
    font-family: 'Space Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.06em;
    color: #3b4f74;
}

.legend-item {
    display: inline-flex;
    align-items: center;
    gap: 6px;
}

.legend-swatch {
    width: 10px;
    height: 10px;
    border-radius: 2px;
    display: inline-block;
}

.swatch-blue { background: #223154; }
.swatch-red { background: #ff4560; }
.swatch-glass { background: #4b7dc4; }

@media (max-width: 1100px) {
    .split-grid {
        grid-template-columns: 1fr;
    }
}
    font-family: 'Space Mono', monospace;
    font-size: 11px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: #00c8ff;
    margin-bottom: 12px;
}

.section-heading {
    font-family: 'Syne', sans-serif;
    font-size: clamp(24px, 3.5vw, 38px);
    font-weight: 800;
    color: #f0f4ff;
    margin-bottom: 14px;
    line-height: 1.15;
}

.section-body {
    font-size: 15px;
    color: #7a8aaa;
    max-width: 100%;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.65;
    margin-bottom: 52px;
}

/* BIM DEMO */
.bim-canvas {
    background: #080d1c;
    border: 1px solid #1a2540;
    border-radius: 14px;
    padding: 28px;
    position: relative;
    overflow: visible;
}

.bim-canvas::before {
    content: '';
    position: absolute; inset: 0;
    border-radius: 14px;
    background-image:
        linear-gradient(rgba(0,200,255,0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,200,255,0.025) 1px, transparent 1px);
    background-size: 22px 22px;
    pointer-events: none;
}

.bim-topbar {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 22px;
}

.dot { width: 10px; height: 10px; border-radius: 50%; }
.dot-r { background: #ff4560; }
.dot-y { background: #ffa500; }
.dot-g { background: #3fb950; }

.bim-filename {
    font-family: 'Space Mono', monospace;
    font-size: 11px;
    color: #2a3a5a;
    margin-left: 10px;
}

.bim-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
}

.bim-el {
    border: 1px solid #1a2540;
    background: #0d1525;
    border-radius: 8px;
    padding: 12px 10px;
    position: relative;
    transition: all 0.18s ease;
    overflow: visible;
}

.bim-el:hover { border-color: #00c8ff40; transform: translateY(-1px); }

.bim-el .el-tag {
    font-family: 'Space Mono', monospace;
    font-size: 9px;
    color: #2a3a5a;
    margin-bottom: 5px;
    letter-spacing: 0.06em;
}

.bim-el .el-name {
    font-size: 12px;
    font-weight: 600;
    color: #8090b0;
}

.bim-el.proxy {
    border-color: rgba(255,69,96,0.4);
    background: rgba(255,69,96,0.05);
}

.bim-el.proxy .el-name { color: #ff4560; }
.bim-el.proxy .el-tag  { color: rgba(255,69,96,0.4); }

.proxy-badge {
    position: absolute;
    top: -1px; right: -1px;
    background: #ff4560;
    color: #fff;
    font-family: 'Space Mono', monospace;
    font-size: 8px;
    padding: 2px 7px;
    border-radius: 0 8px 0 5px;
    letter-spacing: 0.08em;
    font-weight: 700;
}

.bim-el .tip {
    display: none;
    position: absolute;
    bottom: calc(100% + 10px);
    left: 50%;
    transform: translateX(-50%);
    background: #0d1525;
    border: 1px solid #00c8ff55;
    border-radius: 8px;
    padding: 12px 14px;
    width: 190px;
    z-index: 999;
    box-shadow: 0 8px 32px rgba(0,0,0,0.6), 0 0 20px rgba(0,200,255,0.15);
    pointer-events: none;
}

.bim-el:hover .tip { display: block; }

.tip-head {
    font-family: 'Space Mono', monospace;
    font-size: 9px;
    color: #ff4560;
    margin-bottom: 8px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

.tip-suggest {
    font-size: 12px;
    color: #c0cce4;
    margin-bottom: 8px;
}

.tip-suggest strong { color: #e2e8f4; }

.conf-row {
    display: flex;
    align-items: center;
    gap: 8px;
}

.conf-track {
    flex: 1;
    height: 3px;
    background: #1a2540;
    border-radius: 2px;
    overflow: hidden;
}

.conf-fill {
    height: 100%;
    background: linear-gradient(90deg, #00c8ff, #0055ee);
    border-radius: 2px;
}

.conf-pct {
    font-family: 'Space Mono', monospace;
    font-size: 10px;
    color: #00c8ff;
    white-space: nowrap;
}

/* WORKFLOW */
.wf-wrap {
    background: #080d1c;
    border: 1px solid #1a2540;
    border-radius: 14px;
    padding: 48px 36px;
}

.wf-steps {
    display: flex;
    align-items: flex-start;
    justify-content: center;
    gap: 0;
    flex-wrap: wrap;
}

.wf-step {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    flex: 1;
    min-width: 110px;
    max-width: 160px;
    padding: 0 8px;
}

.wf-num {
    width: 42px; height: 42px;
    border-radius: 10px;
    background: rgba(0,200,255,0.07);
    border: 1px solid rgba(0,200,255,0.25);
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'Space Mono', monospace;
    font-size: 13px;
    font-weight: 700;
    color: #00c8ff;
}

.wf-label {
    font-size: 13px;
    font-weight: 700;
    color: #c0cce4;
    text-align: center;
}

.wf-desc {
    font-size: 11px;
    color: #3a4a6a;
    text-align: center;
    line-height: 1.5;
}

.wf-arrow {
    color: #1a2540;
    font-size: 22px;
    padding-top: 10px;
    flex-shrink: 0;
    align-self: flex-start;
}

/* BEFORE / AFTER */
.ba-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
}

.ba-card {
    border-radius: 12px;
    padding: 36px 32px;
    border: 1px solid;
}

.ba-card.before {
    background: rgba(255,69,96,0.04);
    border-color: rgba(255,69,96,0.18);
}

.ba-card.after {
    background: rgba(0,200,255,0.04);
    border-color: rgba(0,200,255,0.18);
}

.ba-pill {
    display: inline-block;
    font-family: 'Space Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 4px 12px;
    border-radius: 100px;
    margin-bottom: 20px;
    font-weight: 700;
}

.before .ba-pill { background: rgba(255,69,96,0.14); color: #ff4560; }
.after  .ba-pill { background: rgba(0,200,255,0.14); color: #00c8ff; }

.ba-title {
    font-size: 20px;
    font-weight: 800;
    margin-bottom: 22px;
    font-family: 'Syne', sans-serif;
}

.before .ba-title { color: #ff4560; }
.after  .ba-title { color: #00c8ff; }

.ba-item {
    display: flex;
    gap: 12px;
    margin-bottom: 16px;
    font-size: 13.5px;
    color: #8090b0;
    line-height: 1.55;
    align-items: flex-start;
}

.ba-icon { flex-shrink: 0; margin-top: 2px; font-size: 15px; }
.ba-item strong { color: #c0cce4; }

/* CTA SECTION */
.cta-wrap {
    text-align: center;
    padding: 100px 32px 56px;
    background:
        radial-gradient(ellipse 60% 50% at 50% 50%, rgba(0,100,255,0.08) 0%, transparent 70%),
        #050810;
    position: relative;
}

.cta-wrap::before {
    content: '';
    position: absolute; inset: 0;
    background-image:
        linear-gradient(rgba(0,200,255,0.02) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,200,255,0.02) 1px, transparent 1px);
    background-size: 48px 48px;
    pointer-events: none;
}

.cta-title {
    font-family: 'Syne', sans-serif;
    font-size: clamp(28px, 4.5vw, 52px);
    font-weight: 800;
    color: #f0f4ff;
    line-height: 1.1;
    margin-bottom: 16px;
    position: relative;
}

.cta-sub {
    font-size: 16px;
    color: #7a8aaa;
    margin-bottom: 0;
    position: relative;
}

/* CTA bottom padding area */
.cta-footer {
    background: #050810;
    padding-bottom: 80px;
}

@media (max-width: 768px) {
    .bim-grid { grid-template-columns: repeat(2, 1fr); }
    .ba-grid  { grid-template-columns: 1fr; }
    .wf-steps { flex-direction: column; align-items: center; }
    .wf-arrow { transform: rotate(90deg); padding-top: 0; }
    .stats-row { gap: 12px; }
}
</style>
""")


# ════════════════════════════════════════════════════════════════════
# HERO
# ════════════════════════════════════════════════════════════════════
render_html_block("""
<div class="hero-wrap">
    <div class="hero-badge">
        <span class="hero-badge-dot"></span>
        BIM Intelligence Platform &nbsp;·&nbsp; IFC Analysis
    </div>
    <h1 class="hero-title">
        IFC <span class="accent">Semantic Data-Loss</span><br>Analyzer
    </h1>
    <p class="hero-sub">Automatically detect proxy elements, missing classifications, and semantic gaps in your BIM models — then fix them with confidence-based suggestions.</p>
</div>
""")

# ── Hero CTA button — proper Streamlit button ──────────────────────────────
_, col_btn, _ = st.columns([3, 2, 3])
with col_btn:
    if st.button("→  Try Now — It's Free", key="btn_hero", type="primary", use_container_width=True):
        st.switch_page("pages/0_Home.py")


 
# ════════════════════════════════════════════════════════════════════
# DEMO SECTION
# ════════════════════════════════════════════════════════════════════
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

render_html_block("""
<div class="section-wrap">
    <div class="section-eyebrow">Live Demo Preview</div>
    <h2 class="section-heading">See Issues. Fix Instantly.</h2>
    <p class="section-body">Hover over the red-highlighted elements to see how the analyzer identifies proxy elements and suggests the correct IFC classification with a confidence score.</p>

    <div class="bim-canvas">
        <div class="bim-topbar">
            <div class="dot dot-r"></div>
            <div class="dot dot-y"></div>
            <div class="dot dot-g"></div>
            <span class="bim-filename">office_building_v3.ifc — 847 elements loaded</span>
        </div>
        <div class="bim-grid">

            <div class="bim-el">
                <div class="el-tag">IFC CLASS</div>
                <div class="el-name">IfcWall</div>
            </div>
            <div class="bim-el">
                <div class="el-tag">IFC CLASS</div>
                <div class="el-name">IfcSlab</div>
            </div>
            <div class="bim-el proxy">
                <div class="proxy-badge">PROXY</div>
                <div class="el-tag">IFC CLASS</div>
                <div class="el-name">IfcBuildingElementProxy</div>
                <div class="tip">
                    <div class="tip-head">⚠ Proxy Detected</div>
                    <div class="tip-suggest">Suggested: <strong>IfcWall</strong></div>
                    <div class="conf-row">
                        <div class="conf-track"><div class="conf-fill" style="width:80%"></div></div>
                        <span class="conf-pct">80%</span>
                    </div>
                </div>
            </div>
            <div class="bim-el">
                <div class="el-tag">IFC CLASS</div>
                <div class="el-name">IfcDoor</div>
            </div>

            <div class="bim-el">
                <div class="el-tag">IFC CLASS</div>
                <div class="el-name">IfcColumn</div>
            </div>
            <div class="bim-el proxy">
                <div class="proxy-badge">PROXY</div>
                <div class="el-tag">IFC CLASS</div>
                <div class="el-name">IfcBuildingElementProxy</div>
                <div class="tip">
                    <div class="tip-head">⚠ Proxy Detected</div>
                    <div class="tip-suggest">Suggested: <strong>IfcBeam</strong></div>
                    <div class="conf-row">
                        <div class="conf-track"><div class="conf-fill" style="width:74%"></div></div>
                        <span class="conf-pct">74%</span>
                    </div>
                </div>
            </div>
            <div class="bim-el">
                <div class="el-tag">IFC CLASS</div>
                <div class="el-name">IfcWindow</div>
            </div>
            <div class="bim-el proxy">
                <div class="proxy-badge">PROXY</div>
                <div class="el-tag">IFC CLASS</div>
                <div class="el-name">IfcBuildingElementProxy</div>
                <div class="tip">
                    <div class="tip-head">⚠ Proxy Detected</div>
                    <div class="tip-suggest">Suggested: <strong>IfcStair</strong></div>
                    <div class="conf-row">
                        <div class="conf-track"><div class="conf-fill" style="width:91%"></div></div>
                        <span class="conf-pct">91%</span>
                    </div>
                </div>
            </div>

        </div>
    </div>
</div>
""")
 

 
# ════════════════════════════════════════════════════════════════════
# WORKFLOW SECTION
# ════════════════════════════════════════════════════════════════════
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
 
render_html_block("""
<div class="section-wrap">
    <div class="section-eyebrow">How It Works</div>
    <h2 class="section-heading">Five Steps to Clean BIM Data</h2>
    <p class="section-body">From raw IFC upload to corrected, semantically-rich output — all in under two seconds.</p>
 
    <div class="wf-wrap">
        <div class="wf-steps">
            <div class="wf-step">
                <div class="wf-num">01</div>
                <div class="wf-label">Upload IFC</div>
                <div class="wf-desc">Drop your .ifc file into the analyzer</div>
            </div>
            <div class="wf-arrow">›</div>
            <div class="wf-step">
                <div class="wf-num">02</div>
                <div class="wf-label">Detect Proxies</div>
                <div class="wf-desc">Scan for IfcBuildingElementProxy instances</div>
            </div>
            <div class="wf-arrow">›</div>
            <div class="wf-step">
                <div class="wf-num">03</div>
                <div class="wf-label">Analyze Context</div>
                <div class="wf-desc">Geometry, properties &amp; placement examined</div>
            </div>
            <div class="wf-arrow">›</div>
            <div class="wf-step">
                <div class="wf-num">04</div>
                <div class="wf-label">Suggest Class</div>
                <div class="wf-desc">Every element gets mapped to the correct IFC type</div>
            </div>
            <div class="wf-arrow">›</div>
            <div class="wf-step">
                <div class="wf-num">05</div>
                <div class="wf-label">Apply Fix</div>
                <div class="wf-desc">Export a corrected, standards-compliant IFC</div>
            </div>
        </div>
    </div>
</div>
""")
 


# ════════════════════════════════════════════════════════════════════
# BEFORE / AFTER SECTION
# ════════════════════════════════════════════════════════════════════
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

render_html_block("""
<div class="section-wrap">
    <div class="section-eyebrow">Impact</div>
    <h2 class="section-heading">Before vs. After</h2>
    <p class="section-body">Semantic data loss costs time, money, and coordination accuracy. Here's exactly what changes after analysis.</p>

    <div class="ba-grid">
        <div class="ba-card before">
            <div class="ba-pill">Before</div>
            <div class="ba-title">Broken BIM Data</div>
            <div class="ba-item">
                <span class="ba-icon">⚠</span>
                <div><strong>Proxy elements everywhere</strong> — generic placeholders with no semantic meaning, invisible to downstream tools</div>
            </div>
            <div class="ba-item">
                <span class="ba-icon">⚠</span>
                <div><strong>Missing classifications</strong> — quantity takeoffs, clash detection, and FM handover all fail silently</div>
            </div>
            <div class="ba-item">
                <span class="ba-icon">⚠</span>
                <div><strong>Manual fixes only</strong> — hours spent hunting proxies element by element in the authoring tool</div>
            </div>
            <div class="ba-item">
                <span class="ba-icon">⚠</span>
                <div><strong>IFC non-compliant exports</strong> — validators flag errors, coordination workflows break</div>
            </div>
        </div>

        <div class="ba-card after">
            <div class="ba-pill">After</div>
            <div class="ba-title">Clean IFC Output</div>
            <div class="ba-item">
                <span class="ba-icon">✓</span>
                <div><strong>Correct IFC classes</strong> — every element carries a meaningful type recognized across all BIM platforms</div>
            </div>
            <div class="ba-item">
                <span class="ba-icon">✓</span>
                <div><strong>Structured, queryable data</strong> — quantity takeoffs, clash detection, and FM import all work correctly</div>
            </div>
            <div class="ba-item">
                <span class="ba-icon">✓</span>
                <div><strong>Automated fixes in seconds</strong> — apply all confidence-based corrections with a single click</div>
            </div>
            <div class="ba-item">
                <span class="ba-icon">✓</span>
                <div><strong>Confidence-scored suggestions</strong> — every fix shows its confidence level so you stay in control</div>
            </div>
        </div>
    </div>
</div>
""")


# ════════════════════════════════════════════════════════════════════
# CTA SECTION
# ════════════════════════════════════════════════════════════════════
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

render_html_block("""
<div class="cta-wrap">
    <p class="section-eyebrow" style="text-align:center; margin-bottom:16px;">Get Started Today</p>
    <h2 class="cta-title">Your BIM data deserves<br>to be understood.</h2>
    <p class="cta-sub">Upload your IFC file and get a full semantic audit in under 2 seconds.</p>
</div>
""")

# ── Bottom CTA button — proper Streamlit button ────────────────────────────
_, col_btn2, _ = st.columns([3, 2, 3])
with col_btn2:
    if st.button("→  Try Now — It's Free", key="btn_cta", type="primary", use_container_width=True):
        st.switch_page("pages/Home.py")

st.markdown("<div class='cta-footer'></div>", unsafe_allow_html=True)