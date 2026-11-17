"""Builds four design-direction mockups of the same Steelman screens, for choosing a visual identity.
Run: python3 build.py  ->  a-*.html ... d-*.html (open in a browser)."""

BODY = """
<header class="top">
  <a class="mark" href="#"><span class="logo">{logo}</span>Steelman</a>
  <nav><a class="nav-btn on" href="#">Debate</a><a class="nav-btn" href="#">Judge report card</a></nav>
</header>
<main>
  <section class="hero">
    <p class="eyebrow">AI debate practice</p>
    <h1>Argue your side. The AI argues the other. <em>A judge you can audit</em> scores you both.</h1>
    <p class="lede">Three rounds: opening, rebuttal, closing. Every score comes with the exact lines behind it, and code checks each quote is real.</p>
  </section>

  <section class="panel start">
    <h2>Start a debate</h2>
    <label>Your motion</label>
    <div class="motion-row">
      <input value="Smartphones should be banned in schools." aria-label="Motion">
      <button class="btn ghost">Surprise me</button>
    </div>
    <p class="hint">Type any motion, or pick one below.</p>
    <div class="cats"><span class="cat on">All</span><span class="cat">Tech</span><span class="cat">Education</span><span class="cat">Cities</span><span class="cat">Work</span><span class="cat">Culture</span><span class="cat">Sport</span></div>
    <div class="chips"><span class="chip on">Smartphones should be banned in schools.</span><span class="chip">A four-day work week should be the standard.</span><span class="chip">Public transport should be free.</span><span class="chip">Zoos should be closed.</span></div>
    <div class="choices">
      <div><label>Your side</label><div class="seg"><span class="on">For · you open</span><span>Against · AI opens</span></div></div>
      <div><label>Opponent</label><div class="seg"><span>Friendly</span><span class="on">Sharp</span></div></div>
    </div>
    <button class="btn primary">Start the debate</button>
  </section>

  <section class="preview">
    <p class="eyebrow">What a debate looks like</p>
    <div class="round-label">Rebuttal</div>
    <div class="pair">
      <article class="cell pro"><div class="cell-head"><span class="tag">For</span><span class="who">You</span></div>
        <p>My opponent says phones help in emergencies, but <mark>schools already have phones in every office</mark>. Locking devices in pouches during lessons keeps that safety net while removing the distraction.</p></article>
      <article class="cell con"><div class="cell-head"><span class="tag">Against</span><span class="who">AI · sharp</span></div>
        <p>A ban teaches avoidance, not judgement. <mark>Students will meet phones in every job they ever have</mark>; school is where they should learn to put one down on purpose.</p></article>
    </div>
    <div class="verdict">
      <div><p class="eyebrow">The judge's verdict</p><h3>For wins, 31 to 26.</h3></div>
      <div class="bars">
        <div class="bar-row"><span>For</span><div class="bar"><i style="width:77%"></i></div><b>31</b></div>
        <div class="bar-row"><span>Against</span><div class="bar con"><i style="width:65%"></i></div><b>26</b></div>
      </div>
    </div>
  </section>

  <section class="recorded">
    <h2>Recorded debates</h2>
    <div class="cards">
      <a class="card" href="#"><span class="card-motion">Museums should be free to enter.</span><span class="card-meta">For wins 32–23 · friendly AI</span></a>
      <a class="card" href="#"><span class="card-motion">Public transport should be free.</span><span class="card-meta">Against wins 31–21 · sharp AI</span></a>
    </div>
  </section>
</main>
<footer class="foot">Steelman is a practice tool. The AI's arguments are not fact-checked; the judge scores how well a case is argued, not whether it is true.</footer>
"""

BASE = """
*{box-sizing:border-box} body{margin:0} main,.top,.foot{max-width:72rem;margin:0 auto;padding-left:1rem;padding-right:1rem}
.top{display:flex;justify-content:space-between;align-items:center;padding-top:1.1rem;padding-bottom:1.1rem}
.mark{display:flex;align-items:center;gap:.55rem;text-decoration:none} nav{display:flex;gap:.5rem}
.nav-btn{text-decoration:none;white-space:nowrap} h1,h2,h3,p{margin:0} .hero{padding:3rem 0 2rem;max-width:50rem}
.hero h1{margin:.6rem 0 1rem} .panel{padding:1.4rem;margin-bottom:2.5rem} .panel h2{margin-bottom:1rem}
label{display:block;margin:0 0 .4rem} .motion-row{display:flex;gap:.6rem} .motion-row input{flex:1;min-width:0}
.hint{margin:.5rem 0 1rem} .cats,.chips{display:flex;flex-wrap:wrap;gap:.4rem;margin-bottom:.7rem}
.choices{display:grid;grid-template-columns:repeat(auto-fit,minmax(16rem,1fr));gap:1rem;margin:1.2rem 0 1.4rem}
.seg{display:flex} .seg span{flex:1;text-align:center;cursor:pointer} .btn{cursor:pointer;border:0;white-space:nowrap}
.preview{margin-bottom:2.5rem} .round-label{margin:.8rem 0 .6rem} .pair{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
.cell{padding:1.1rem} .cell-head{display:flex;justify-content:space-between;margin-bottom:.6rem} mark{color:inherit}
.verdict{display:grid;grid-template-columns:1fr 1.3fr;gap:1.5rem;align-items:center;margin-top:1rem;padding:1.2rem}
.bar-row{display:grid;grid-template-columns:4.5rem 1fr 2rem;gap:.6rem;align-items:center;margin:.35rem 0}
.bar{height:10px;overflow:hidden} .bar i{display:block;height:100%} .recorded h2{margin-bottom:1rem}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(18rem,1fr));gap:.8rem;margin-bottom:3rem}
.card{display:flex;flex-direction:column;gap:.3rem;padding:1.1rem;text-decoration:none} .foot{padding-top:1.2rem;padding-bottom:2.5rem}
@media(max-width:720px){.pair,.verdict{grid-template-columns:1fr}.motion-row{flex-direction:column} nav .nav-btn:first-child{display:none}}
"""

THEMES = {
"a-courtroom": dict(title="A · Courtroom", logo="§", fonts="family=Playfair+Display:ital,wght@0,600;0,800;1,600&family=Source+Serif+4:wght@400;600&family=JetBrains+Mono:wght@500",
css="""
body{background:#f6f1e7;color:#211a17;font:400 1.02rem/1.6 'Source Serif 4',Georgia,serif}
.top{border-bottom:3px double #211a17} .mark{font:800 1.4rem 'Playfair Display';color:#211a17;letter-spacing:.02em}
.logo{display:grid;place-items:center;width:2rem;height:2rem;background:#7b1e2b;color:#f6f1e7;border-radius:50%;font-size:1.1rem}
.nav-btn{font:600 .9rem 'Source Serif 4';color:#211a17;border:1.5px solid #211a17;padding:.45rem 1rem;border-radius:2px}
.nav-btn.on{background:#211a17;color:#f6f1e7}
.eyebrow{font:500 .72rem 'JetBrains Mono';letter-spacing:.14em;text-transform:uppercase;color:#7b1e2b}
h1{font:800 clamp(2rem,5vw,3.4rem)/1.08 'Playfair Display'} h1 em{color:#7b1e2b;font-style:italic;font-weight:600}
h2{font:800 1.6rem 'Playfair Display'} h3{font:800 1.5rem 'Playfair Display'} .lede{font-size:1.15rem;color:#5a4f47}
.panel{background:#fffdf8;border:1px solid #d9cfbf;box-shadow:6px 6px 0 #211a17}
label{font:500 .72rem 'JetBrains Mono';letter-spacing:.1em;text-transform:uppercase;color:#5a4f47}
input{font:inherit;padding:.75rem .9rem;border:1.5px solid #211a17;background:#fff;border-radius:2px}
.hint{color:#7a6e63;font-style:italic} .cat{font:500 .75rem 'JetBrains Mono';text-transform:uppercase;letter-spacing:.08em;padding:.3rem .6rem;color:#5a4f47}
.cat.on{color:#7b1e2b;border-bottom:2px solid #7b1e2b} .chip{border:1px solid #cdbfa9;padding:.35rem .8rem;font-size:.9rem;border-radius:2px;background:#fff}
.chip.on{border-color:#7b1e2b;color:#7b1e2b} .seg{border:1.5px solid #211a17} .seg span{padding:.6rem}.seg span.on{background:#211a17;color:#f6f1e7}
.btn.primary{background:#7b1e2b;color:#fff;font:600 1.05rem 'Source Serif 4';padding:.85rem 1.6rem;border-radius:2px;box-shadow:4px 4px 0 #211a17}
.btn.ghost{background:transparent;border:1.5px solid #211a17;padding:.7rem 1rem;font:600 .95rem 'Source Serif 4';color:#211a17}
.round-label{font:800 1.2rem 'Playfair Display';font-style:italic;border-bottom:1px solid #d9cfbf;padding-bottom:.4rem}
.cell{background:#fffdf8;border:1px solid #d9cfbf} .cell.pro{border-top:4px solid #1f3a5f}.cell.con{border-top:4px solid #7b1e2b}
.tag{font:500 .72rem 'JetBrains Mono';letter-spacing:.12em;text-transform:uppercase}.who{color:#7a6e63;font-size:.9rem}
mark{background:#efd9a7} .verdict{background:#211a17;color:#f6f1e7} .verdict .eyebrow{color:#e9b8a0}
.bar{background:#4a3f39}.bar i{background:#efd9a7}.bar.con i{background:#c97a7a} .card{background:#fffdf8;border:1px solid #d9cfbf;color:#211a17}
.card-motion{font:800 1.15rem 'Playfair Display'}.card-meta{color:#7a6e63;font-size:.9rem} .foot{border-top:3px double #211a17;color:#7a6e63;font-size:.88rem}
"""),
"b-arena": dict(title="B · Arena (dark)", logo="◐", fonts="family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@500",
css="""
body{background:#0b0d12;color:#e7e9ee;font:400 1rem/1.6 Inter,system-ui,sans-serif;background-image:radial-gradient(60rem 30rem at 15% -10%,rgba(0,229,255,.12),transparent),radial-gradient(50rem 30rem at 95% 10%,rgba(255,61,154,.12),transparent)}
.mark{font:700 1.3rem 'Space Grotesk';color:#fff}.logo{display:grid;place-items:center;width:2rem;height:2rem;border-radius:9px;background:linear-gradient(135deg,#00e5ff,#ff3d9a);color:#0b0d12;font-size:1.1rem}
.nav-btn{font:500 .9rem Inter;color:#cfd3dc;padding:.5rem 1rem;border-radius:999px;border:1px solid #2a2f3a;background:rgba(255,255,255,.03)}
.nav-btn.on{color:#0b0d12;background:#e7e9ee;border-color:#e7e9ee}
.eyebrow{font:500 .72rem 'JetBrains Mono';letter-spacing:.14em;text-transform:uppercase;color:#00e5ff}
h1{font:700 clamp(2rem,5vw,3.5rem)/1.05 'Space Grotesk';letter-spacing:-.02em} h1 em{font-style:normal;background:linear-gradient(90deg,#00e5ff,#ff3d9a);-webkit-background-clip:text;background-clip:text;color:transparent}
h2,h3{font:700 1.5rem 'Space Grotesk'} .lede{color:#9aa1ad;font-size:1.1rem}
.panel{background:rgba(20,23,31,.85);border:1px solid #232834;border-radius:18px;box-shadow:0 0 0 1px rgba(0,229,255,.06),0 30px 60px -30px rgba(0,229,255,.25)}
label{font:500 .75rem 'JetBrains Mono';letter-spacing:.08em;text-transform:uppercase;color:#8b93a1}
input{font:inherit;color:#fff;background:#0f1218;border:1px solid #2a2f3a;border-radius:12px;padding:.8rem 1rem}
.hint{color:#6f7786;font-size:.9rem}.cat{font:500 .8rem Inter;padding:.3rem .75rem;border-radius:999px;color:#8b93a1}
.cat.on{background:#1b2030;color:#00e5ff}.chip{font-size:.88rem;padding:.4rem .85rem;border-radius:999px;border:1px solid #2a2f3a;color:#cfd3dc}
.chip.on{border-color:#00e5ff;color:#00e5ff;box-shadow:0 0 18px -6px #00e5ff}.seg{background:#0f1218;border:1px solid #2a2f3a;border-radius:12px;padding:4px}
.seg span{padding:.55rem;border-radius:9px;color:#8b93a1}.seg span.on{background:#1b2030;color:#fff}
.btn.primary{font:600 1rem Inter;color:#0b0d12;padding:.9rem 1.6rem;border-radius:12px;background:linear-gradient(90deg,#00e5ff,#7c6cff 55%,#ff3d9a);box-shadow:0 10px 30px -10px rgba(124,108,255,.7)}
.btn.ghost{font:600 .9rem Inter;color:#e7e9ee;background:#1b2030;border:1px solid #2a2f3a;border-radius:12px;padding:.7rem 1rem}
.round-label{font:500 .75rem 'JetBrains Mono';letter-spacing:.14em;text-transform:uppercase;color:#8b93a1}
.cell{background:#12151d;border:1px solid #232834;border-radius:16px}.cell.pro{box-shadow:inset 3px 0 0 #00e5ff}.cell.con{box-shadow:inset 3px 0 0 #ff3d9a}
.cell.pro .tag{color:#00e5ff}.cell.con .tag{color:#ff3d9a}.tag{font:500 .75rem 'JetBrains Mono';letter-spacing:.1em;text-transform:uppercase}.who{color:#6f7786;font-size:.85rem}
mark{background:rgba(255,213,74,.18);border-bottom:2px solid #ffd54a;border-radius:3px} .verdict{background:#12151d;border:1px solid #232834;border-radius:16px}
.bar{background:#1b2030;border-radius:99px}.bar i{background:#00e5ff;border-radius:99px}.bar.con i{background:#ff3d9a} .bar-row b{font-family:'JetBrains Mono'}
.card{background:#12151d;border:1px solid #232834;border-radius:16px;color:#e7e9ee}.card-motion{font:700 1.1rem 'Space Grotesk'}.card-meta{color:#6f7786;font-size:.88rem}
.foot{color:#6f7786;font-size:.85rem;border-top:1px solid #1b2030}
"""),
"c-split": dict(title="C · Split stage (bold colour)", logo="⇄", fonts="family=Archivo:wght@500;700;900&family=Archivo+Narrow:wght@500;700&family=IBM+Plex+Mono:wght@500",
css="""
body{background:#fffaf0;color:#121212;font:500 1rem/1.55 Archivo,system-ui,sans-serif}
.top{border-bottom:2px solid #121212}.mark{font:900 1.35rem Archivo;color:#121212;text-transform:uppercase;letter-spacing:-.01em}
.logo{display:grid;place-items:center;width:2.1rem;height:2.1rem;background:linear-gradient(90deg,#2448ff 50%,#ff6a13 50%);color:#fff;border:2px solid #121212;font-size:1rem}
.nav-btn{font:700 .85rem 'Archivo Narrow';text-transform:uppercase;letter-spacing:.06em;color:#121212;padding:.5rem 1rem;border:2px solid #121212;background:#fff;box-shadow:3px 3px 0 #121212}
.nav-btn.on{background:#ffde3b}
.eyebrow{font:700 .78rem 'Archivo Narrow';letter-spacing:.12em;text-transform:uppercase;color:#2448ff}
h1{font:900 clamp(2.1rem,5.6vw,3.9rem)/1 Archivo;letter-spacing:-.03em;text-transform:uppercase} h1 em{font-style:normal;background:#ffde3b;padding:0 .15em}
h2,h3{font:900 1.6rem Archivo;text-transform:uppercase;letter-spacing:-.01em}.lede{font-size:1.1rem;color:#3d3d3d}
.panel{background:#fff;border:2px solid #121212;box-shadow:8px 8px 0 #121212}
label{font:700 .78rem 'Archivo Narrow';text-transform:uppercase;letter-spacing:.08em}
input{font:inherit;padding:.8rem;border:2px solid #121212;background:#fffaf0}.hint{color:#6b6b6b}
.cat{font:700 .78rem 'Archivo Narrow';text-transform:uppercase;padding:.3rem .7rem;border:2px solid transparent}.cat.on{border-color:#121212;background:#121212;color:#fff}
.chip{font-size:.88rem;padding:.4rem .8rem;border:2px solid #121212;background:#fff}.chip.on{background:#ffde3b}
.seg{border:2px solid #121212}.seg span{padding:.6rem;font-weight:700}.seg span.on{background:#121212;color:#fff}
.btn.primary{font:900 1.05rem Archivo;text-transform:uppercase;color:#fff;background:#2448ff;padding:.9rem 1.6rem;border:2px solid #121212;box-shadow:5px 5px 0 #121212}
.btn.ghost{font:700 .9rem 'Archivo Narrow';text-transform:uppercase;background:#ff6a13;color:#fff;border:2px solid #121212;padding:.7rem 1rem;box-shadow:3px 3px 0 #121212}
.round-label{font:900 1.1rem Archivo;text-transform:uppercase}
.pair{gap:0;border:2px solid #121212}.cell.pro{background:#2448ff;color:#fff}.cell.con{background:#ff6a13;color:#121212;border-left:2px solid #121212}
.tag{font:900 .85rem Archivo;text-transform:uppercase;letter-spacing:.05em}.who{font:700 .8rem 'Archivo Narrow';text-transform:uppercase;opacity:.85}
mark{background:#ffde3b;color:#121212} .verdict{background:#121212;color:#fff;border:2px solid #121212}.verdict .eyebrow{color:#ffde3b}
.bar{background:#333;height:14px}.bar i{background:#2448ff}.bar.con i{background:#ff6a13}.bar-row b{font-family:'IBM Plex Mono'}
.card{background:#fff;border:2px solid #121212;box-shadow:4px 4px 0 #121212;color:#121212}.card-motion{font:900 1.1rem Archivo;text-transform:uppercase}.card-meta{color:#555;font-size:.9rem}
.foot{border-top:2px solid #121212;color:#555;font-size:.85rem}
"""),
"d-lab": dict(title="D · Lab instrument", logo="◎", fonts="family=Manrope:wght@400;500;700;800&family=IBM+Plex+Mono:wght@400;500",
css="""
body{background:#f4f6f3;color:#13201b;font:400 1rem/1.6 Manrope,system-ui,sans-serif;background-image:linear-gradient(#e3e8e2 1px,transparent 1px),linear-gradient(90deg,#e3e8e2 1px,transparent 1px);background-size:32px 32px}
.top{background:rgba(244,246,243,.9)}.mark{font:800 1.25rem Manrope;color:#13201b}
.logo{display:grid;place-items:center;width:1.9rem;height:1.9rem;border-radius:50%;border:2px solid #13201b;font-size:1rem;color:#0f8a5f}
.nav-btn{font:500 .85rem 'IBM Plex Mono';color:#13201b;padding:.45rem .9rem;border-radius:8px;border:1px solid #c9d2c8;background:#fff}
.nav-btn.on{background:#13201b;color:#c6f432;border-color:#13201b}
.eyebrow{font:500 .75rem 'IBM Plex Mono';letter-spacing:.06em;color:#0f8a5f}.eyebrow::before{content:"// "}
h1{font:800 clamp(2rem,5vw,3.3rem)/1.08 Manrope;letter-spacing:-.025em} h1 em{font-style:normal;background:linear-gradient(transparent 60%,#c6f432 60%)}
h2,h3{font:800 1.45rem Manrope;letter-spacing:-.01em}.lede{color:#4b5a53;font-size:1.08rem}
.panel{background:#fff;border:1px solid #c9d2c8;border-radius:14px}
label{font:500 .75rem 'IBM Plex Mono';color:#4b5a53}
input{font:inherit;padding:.75rem .9rem;border:1px solid #c9d2c8;border-radius:10px;background:#f9fbf8}.hint{color:#6c7a73;font-size:.9rem}
.cat{font:500 .78rem 'IBM Plex Mono';padding:.25rem .6rem;border-radius:6px;color:#4b5a53}.cat.on{background:#13201b;color:#c6f432}
.chip{font-size:.88rem;padding:.35rem .75rem;border-radius:8px;border:1px solid #c9d2c8;background:#fff}.chip.on{border-color:#0f8a5f;color:#0f8a5f;background:#eefaf3}
.seg{border:1px solid #c9d2c8;border-radius:10px;padding:3px;background:#f9fbf8}.seg span{padding:.5rem;border-radius:7px}.seg span.on{background:#13201b;color:#fff}
.btn.primary{font:700 1rem Manrope;color:#13201b;background:#c6f432;padding:.85rem 1.5rem;border-radius:10px;border:1px solid #13201b}
.btn.ghost{font:500 .85rem 'IBM Plex Mono';background:#fff;border:1px solid #c9d2c8;border-radius:10px;padding:.7rem 1rem;color:#13201b}
.round-label{font:500 .8rem 'IBM Plex Mono';color:#4b5a53}.round-label::before{content:"round 2 / 3 — "}
.cell{background:#fff;border:1px solid #c9d2c8;border-radius:12px}.cell.pro{border-left:4px solid #0f8a5f}.cell.con{border-left:4px solid #5b4bff}
.tag{font:500 .78rem 'IBM Plex Mono'}.cell.pro .tag{color:#0f8a5f}.cell.con .tag{color:#5b4bff}.who{font:400 .78rem 'IBM Plex Mono';color:#6c7a73}
mark{background:#e9fbb0} .verdict{background:#13201b;color:#eef2ee;border-radius:14px}.verdict .eyebrow{color:#c6f432}
.bar{background:#2a3a33;border-radius:4px}.bar i{background:#c6f432}.bar.con i{background:#9a8fff}.bar-row{font-family:'IBM Plex Mono';font-size:.85rem}
.card{background:#fff;border:1px solid #c9d2c8;border-radius:12px;color:#13201b}.card-motion{font:700 1.05rem Manrope}.card-meta{font:400 .8rem 'IBM Plex Mono';color:#6c7a73}
.foot{color:#6c7a73;font-size:.85rem}
"""),
}

for key, t in THEMES.items():
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Steelman mockup {t['title']}</title><link rel="stylesheet" href="https://fonts.googleapis.com/css2?{t['fonts']}&display=swap">
<style>{BASE}{t['css']}</style></head><body>{BODY.format(logo=t['logo'])}</body></html>"""
    open(f"{key}.html", "w").write(html)
    print("wrote", key + ".html")
