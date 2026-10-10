import json, html, os, re
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(ROOT, 'data.json')))
e = lambda s: html.escape(str(s))

def links(value):
    if not value:
        return ''
    urls = value if isinstance(value, list) else [value]
    return ''.join(
        f'<a class="src" href="{e(u)}" target="_blank" rel="noopener">{e(urlparse(u).netloc.replace("www.", ""))}</a>'
        for u in urls
    )

def importance(item):
    level = str(item.get('importance') or 'routine').lower()
    return level if level in ('very-important', 'breaking', 'important', 'routine') else 'routine'

def clock_minutes(text):
    found = []
    for m in re.finditer(r'(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)|\bnoon\b', text, re.I):
        if m.group(0).lower() == 'noon':
            found.append(12 * 60)
            continue
        hh = int(m.group(1))
        mm = int(m.group(2) or 0)
        ap = m.group(3).lower().replace('.', '')
        if ap == 'pm' and hh != 12:
            hh += 12
        if ap == 'am' and hh == 12:
            hh = 0
        found.append(hh * 60 + mm)
    return max(found) if found else -1

def feed_sort_key(pair):
    idx, item = pair
    day = re.search(r'(\d+)\s*Oct', item.get('t', ''), re.I)
    # Latest clock time already written in the entry. Untimed entries sort before timed ones that day.
    return (int(day.group(1)) if day else 0, clock_minutes(item.get('t', '')), idx)

def status_chip(status):
    low = status.lower()
    if low.startswith('released'):
        kind, label = 'rel', 'Released'
    elif low.startswith('held'):
        kind, label = 'held', 'Detained'
    else:
        kind, label = 'unk', 'Unknown'
    return f'<span class="chip {kind}">{label}</span>'

def badge(level):
    labels = {'very-important': 'Very important', 'breaking': 'Breaking', 'important': 'Important'}
    if level not in labels:
        return ''
    return f'<span class="badge {level}">{labels[level]}</span>'

# Presentation only: these recorded detentions are the owner's top priority.
VIP_NAMES = (
    'dhruv rathee', 'abhijeet dipke', 'saurav das', 'ashutosh ranka', 'ratna singh',
    'neha bora', 'yogendra yadav', 'mamata banerjee', 'arvind kejriwal', 'manish sisodia',
    'pinarayi vijayan', 'john brittas',
    'k.n. balagopal', 'm.a. baby', 'brinda karat', 'manik sarkar', 'jitendra chaudhury',
    'elamaram kareem',
)

def is_vip(name):
    low = name.lower()
    return any(part in low for part in VIP_NAMES)

ordered = [item for _, item in sorted(enumerate(d['timeline']), key=feed_sort_key, reverse=True)]
top = [item for item in ordered if importance(item) == 'very-important']

def feed_item(item, pinned=False):
    level = importance(item)
    cls = 'pin' if pinned else 'item'
    return (
        f'<article class="{cls} {level}">'
        f'<div class="meta">{badge(level)}<time>{e(item["t"])}</time><span class="tz">IST</span></div>'
        f'<p>{e(item["e"])}</p>'
        f'<div class="srcs">{links(item.get("src"))}</div>'
        f'</article>'
    )

stats = ''.join(
    f'<article class="stat"><p class="v">{e(s["value"])}</p><h3>{e(s["label"])}</h3><p>{e(s["note"])} {links(s["src"])}</p></article>'
    for s in d['stats']
)
feed = ''.join(feed_item(item) for item in ordered)
pins = ''.join(feed_item(item, pinned=True) for item in top)
# Detainees stay in the order stored in data.json.
people = ''.join(
    f'<article class="person{" very-important" if is_vip(x["name"]) else ""}"><div class="person-main"><div class="person-id"><h3>{e(x["name"])}</h3><span class="chips">{badge("very-important") if is_vip(x["name"]) else ""}{status_chip(x["status"])}</span></div>'
    f'<p class="who">{e(x["who"])}</p>'
    f'<p class="where"><span>Time</span> {e(x["when"])}</p>'
    f'<p class="where"><span>Place</span> {e(x["where"])}</p>'
    f'<p class="detail">{e(x["status"])}</p>'
    f'<p class="reason">{e(x["reason"])}</p>'
    f'<div class="srcs">{links(x.get("src"))}</div></div></article>'
    for x in d['detainees']
)
joined = ''.join(f'<li><b>{e(x["name"])}</b> — {e(x["role"])}</li>' for x in d['joined'])
allegations = ''.join(
    f'<li>{e(x["claim"])} <span class="by">Alleged by: {e(x["by"])}</span> {links(x["src"])}</li>'
    for x in d['allegations']
)
govt = ''.join(f'<li>{e(x["point"])} {links(x["src"])}</li>' for x in d['govt_position'])
legal = ''.join(f'<li>{e(x)}</li>' for x in d['legal_context'])
courts = ''.join(
    f'<article class="court"><p class="cd">{e(x["date"])} · {e(x["court"])}</p><p>{e(x["action"])} {links(x["src"])}</p></article>'
    for x in d['courts']
)
caveats = ''.join(f'<li>{e(x)}</li>' for x in d['caveats'])
sources = ''.join(f'<li><a href="{e(u)}" target="_blank" rel="noopener">{e(u)}</a></li>' for u in d['sources'])

CSS = r'''
:root{
  color-scheme:dark;
  --ink:#f4f7fb;--muted:#c5cedd;--link:#c7d2fe;--link-hover:#fff;
  --card:rgba(17,24,43,.72);--line:rgba(255,255,255,.12);
  --shadow:0 18px 40px rgba(0,0,0,.35);
  --header:rgba(7,11,22,.78);
  --vip:#fb7185;--vip-bg:rgba(251,113,133,.16);
  --break:#fbbf24;--break-ink:#1c1408;--break-bg:rgba(251,191,36,.14);
  --imp:#7dd3fc;--imp-ink:#082f49;--imp-bg:rgba(125,211,252,.12);
  --accent:#8b7cff;
  --grad:radial-gradient(1100px 520px at 0% -8%, rgba(124,92,255,.42), transparent 55%),radial-gradient(820px 420px at 100% 0%, rgba(251,113,133,.22), transparent 48%),linear-gradient(180deg,#10162a,#070b16);
}
body:has(#light:checked){
  color-scheme:light;
  --ink:#0f172a;--muted:#334155;--link:#1e40af;--link-hover:#1e3a8a;
  --card:rgba(255,255,255,.88);--line:rgba(15,23,42,.1);
  --shadow:0 14px 34px rgba(15,23,42,.08);
  --header:rgba(255,255,255,.84);
  --vip-bg:#fff1f2;--break-bg:#fffbeb;--imp-bg:#f0f9ff;
  --grad:radial-gradient(1000px 480px at 0% -8%, rgba(124,92,255,.16), transparent 55%),radial-gradient(760px 380px at 100% 0%, rgba(251,113,133,.12), transparent 48%),linear-gradient(180deg,#f8fafc,#eef2f7);
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;font:17px/1.6 Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;background:var(--grad);background-attachment:fixed;color:var(--ink)}
a{color:var(--link);text-underline-offset:3px;transition:color .16s ease}
a:hover{color:var(--link-hover)}
a:focus-visible,.theme:focus-visible,.sr:focus-visible{outline:3px solid var(--accent);outline-offset:3px}
.sr{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);border:0}
.bar{position:sticky;top:0;z-index:30;display:flex;flex-wrap:wrap;align-items:center;gap:12px 18px;padding:14px 22px;background:var(--header);backdrop-filter:blur(18px);border-bottom:1px solid var(--line);box-shadow:0 8px 30px rgba(0,0,0,.18)}
.live{display:inline-flex;align-items:center;gap:8px;color:#fff;background:linear-gradient(90deg,#e11d48,#7c3aed);border-radius:999px;padding:6px 12px 6px 10px;font-weight:800;letter-spacing:.14em;font-size:.72rem}
.dot{width:9px;height:9px;border-radius:50%;background:#fff;box-shadow:0 0 0 0 rgba(255,255,255,.7);animation:pulse 1.6s ease-out infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(255,255,255,.65)}100%{box-shadow:0 0 0 10px rgba(255,255,255,0)}}
h1{margin:0;flex:1 1 220px;font-size:clamp(1.05rem,2vw,1.35rem);line-height:1.25;letter-spacing:-.02em;font-weight:750}
.updated{margin:0;color:var(--muted);font-weight:600;font-size:.95rem}
.updated time{color:var(--ink);font-weight:800}
.theme{margin-left:auto;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:999px;padding:6px 12px;font-weight:700;font-size:.82rem;cursor:pointer;box-shadow:var(--shadow)}
.theme .on{display:none}
body:has(#light:checked) .theme .off{display:none}
body:has(#light:checked) .theme .on{display:inline}
.wrap{max-width:1040px;margin:auto;padding:28px 22px 72px}
.disclaimer{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--break);border-radius:18px;padding:16px 18px;margin:0 0 28px;box-shadow:var(--shadow);backdrop-filter:blur(16px)}
.lede{font-size:1.05rem;margin:0}
h2{font-size:1.35rem;line-height:1.25;letter-spacing:-.02em;margin:40px 0 8px}
.section-note{margin:0 0 16px;color:var(--muted);font-size:.95rem}
.top,.feed,.people,.stats{display:flex;flex-direction:column;gap:16px}
.stats,.two{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.pin,.item,.stat,.court,.box,.person{background:var(--card);border:1px solid var(--line);border-radius:20px;box-shadow:var(--shadow);backdrop-filter:blur(16px);transition:transform .18s ease,border-color .18s ease,box-shadow .18s ease}
.pin,.item,.person,.stat{padding:18px 20px}
.pin:hover,.item:hover,.person:hover,.stat:hover{transform:translateY(-2px);border-color:rgba(139,124,255,.45)}
.pin p,.item p{margin:8px 0 0}
.meta,.chips{display:flex;flex-wrap:wrap;align-items:center;gap:8px}
.meta{font-weight:700;font-size:.86rem}
.tz{color:var(--muted)}
.badge{display:inline-block;border-radius:999px;padding:4px 10px;letter-spacing:.04em;text-transform:uppercase;font-size:.72rem;font-weight:800}
.badge.very-important{color:#fff;background:linear-gradient(90deg,#be123c,#6d28d9);box-shadow:0 0 18px rgba(190,18,60,.4)}
.badge.breaking{color:var(--break-ink);background:var(--break)}
.badge.important{color:var(--imp-ink);background:var(--imp)}
.item.very-important,.pin,.person.very-important{border-color:rgba(251,113,133,.45);background:linear-gradient(180deg,var(--vip-bg),var(--card));box-shadow:0 0 0 1px rgba(251,113,133,.2),var(--shadow),0 0 28px rgba(251,113,133,.16)}
.item.breaking{background:linear-gradient(180deg,var(--break-bg),var(--card));border-color:rgba(251,191,36,.4)}
.item.important{background:linear-gradient(180deg,var(--imp-bg),var(--card))}
.srcs{display:flex;flex-wrap:wrap;gap:10px;margin-top:10px}
.src{font-weight:700;font-size:.82rem;white-space:nowrap}
.src:before{content:"↗ "}
.stat .v{margin:0;font-weight:800;font-size:2rem;letter-spacing:-.03em;background:linear-gradient(90deg,#fb7185,#8b7cff);-webkit-background-clip:text;background-clip:text;color:transparent}
.stat h3{margin:6px 0;font-size:1rem}
.stat p,.court p,.box li,.who,.where,.detail,.reason{font-size:.95rem}
.person-id{display:flex;flex-wrap:wrap;align-items:flex-start;justify-content:space-between;gap:10px}
.person h3{margin:0;font-size:1.12rem;letter-spacing:-.02em}
.where span{font-weight:800}
.detail{color:var(--muted)}
.chip{display:inline-block;border-radius:999px;padding:4px 10px;font-weight:800;font-size:.75rem;color:#fff}
.chip.held{background:#9f1239}
.chip.rel{background:#166534}
.chip.unk{background:#b45309}
.box{padding:8px 18px 14px}
.box ul{margin:10px 0;padding-left:18px}
.box li{margin:10px 0}
.by{display:block;margin-top:4px;color:#fbbf24;font-weight:700;font-size:.82rem}
body:has(#light:checked) .by{color:#92400e}
.court{padding:16px 18px}
.cd{margin:0 0 6px;font-weight:800;color:#fb7185}
.sources li{word-break:break-word;font-size:.88rem}
footer{color:var(--muted);margin-top:36px;font-size:.92rem}
@media(prefers-reduced-motion:reduce){
  .dot{animation:none}
  .pin:hover,.item:hover,.person:hover,.stat:hover{transform:none}
}
@media(max-width:760px){
  .bar{padding:12px 14px}
  .theme{margin-left:0}
  .wrap{padding:20px 14px 56px}
  .stats,.two{grid-template-columns:1fr}
  h1{flex-basis:100%}
}
'''

page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(d["title"])}</title><style>{CSS}</style></head><body>
<input id="light" class="sr" type="checkbox" aria-label="Switch to light mode">
<header class="bar"><span class="live"><span class="dot" aria-hidden="true"></span>Live</span><h1>{e(d["title"])}</h1>
<p class="updated">Last updated <time>{e(d["last_updated_ist"])}</time></p>
<label class="theme" for="light"><span class="off">Light</span><span class="on">Dark</span></label></header>
<main class="wrap">
<div class="disclaimer"><strong>Disclaimer:</strong> This data is auto-generated by a Grok bot. The bot compiled this dashboard while publishing the site, from news reports, official statements, and labelled social-media posts. It is not an official record and has not been checked by a human editor. Names, counts, times, and detention status can be incomplete or wrong. Check the linked sources before relying on it.</div>
<h2>Very important</h2>
<p class="section-note">Key leader detentions, pinned newest first. Each one is also in the feed below.</p>
<div class="top">{pins}</div>
<h2>Live updates</h2>
<p class="section-note">Newest first. Times are IST.</p>
<div class="feed">{feed}</div>
<h2>Background</h2>
<p class="lede">{e(d["summary"])}</p>
<h2>At a glance</h2>
<div class="stats">{stats}</div>
<h2>Key people detained</h2>
<p class="section-note">Status chip, then the recorded time and place.</p>
<div class="people">{people}</div>
<div class="two"><div><h2>Notable people who joined / backed it</h2><div class="box"><ul>{joined}</ul></div></div>
<div><h2>Court updates</h2>{courts}</div></div>
<h2>Alleged govt failures &amp; rules broken <small>(these are allegations, not findings)</small></h2>
<div class="box"><ul>{allegations}</ul></div>
<div class="two"><div><h2>Government / police position</h2><div class="box"><ul>{govt}</ul></div></div>
<div><h2>Legal context (reference)</h2><div class="box"><ul>{legal}</ul></div></div></div>
<h2>Caveats</h2><div class="box"><ul>{caveats}</ul></div>
<h2>Sources</h2><div class="box"><ul class="sources">{sources}</ul></div>
<footer>Auto-generated by a Grok bot from mainstream media, official statements and labelled social-media posts. Not an official record. To refresh: edit data.json, then run <code>python3 build.py</code>.</footer>
</main></body></html>'''

open(os.path.join(ROOT, 'index.html'), 'w').write(page)
print('built', len(ordered), 'updates;', len(top), 'pinned')
