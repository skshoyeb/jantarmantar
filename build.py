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
    return level if level in ('breaking', 'important', 'routine') else 'routine'

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
    if level == 'routine':
        return ''
    label = 'Breaking' if level == 'breaking' else 'Important'
    return f'<span class="badge {level}">{label}</span>'

ordered = [item for _, item in sorted(enumerate(d['timeline']), key=feed_sort_key, reverse=True)]
top = [item for item in ordered if importance(item) == 'breaking'][:4]

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
    f'<article class="person"><div class="person-main"><div class="person-id"><h3>{e(x["name"])}</h3>{status_chip(x["status"])}</div>'
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
:root{--bg:#f4f0e6;--ink:#1c1917;--muted:#3f4750;--card:#fffdf8;--line:#e3d9c8;--breaking:#9f1239;--breaking-bg:#fff1f2;--important:#92400e;--important-bg:#fffbeb;--ok:#166534;--ok-bg:#f0fdf4;--unk:#92400e;--unk-bg:#fffbeb;--link:#1e3a8a;--chip-line:#fecdd3}
@media(prefers-color-scheme:dark){:root{--bg:#101418;--ink:#f5f2ea;--muted:#c9d0d7;--card:#1a2129;--line:#313a44;--breaking:#fecdd3;--breaking-bg:#3f121c;--important:#fde68a;--important-bg:#3a2c0c;--ok:#bbf7d0;--ok-bg:#052e16;--unk:#fde68a;--unk-bg:#3a2c0c;--link:#bfdbfe;--chip-line:#9f1239}}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;font:18px/1.6 "Iowan Old Style",Palatino,"Palatino Linotype",Georgia,serif;background:var(--bg);color:var(--ink)}
a{color:var(--link);text-underline-offset:2px}
a:focus-visible,button:focus-visible{outline:3px solid var(--link);outline-offset:2px}
.wrap{max-width:980px;margin:auto;padding:28px 20px 48px}
.mast{border-bottom:3px solid var(--ink);padding-bottom:14px;margin-bottom:16px}
.kicker{display:flex;flex-wrap:wrap;align-items:center;gap:8px;font:700 .78rem/1.2 system-ui,sans-serif;letter-spacing:.08em;text-transform:uppercase}
.live{background:var(--breaking);color:#fff;border-radius:4px;padding:3px 8px}
h1{font-size:clamp(1.8rem,4vw,2.5rem);line-height:1.15;margin:8px 0 10px;letter-spacing:-.02em}
.updated{margin:0;font:600 1.05rem/1.4 system-ui,sans-serif}
.updated time{font-weight:800}
.disclaimer{background:var(--important-bg);border:1px solid var(--important);border-radius:10px;padding:12px 14px;margin:16px 0;font:600 .95rem/1.45 system-ui,sans-serif}
.disclaimer strong{color:var(--important)}
.lede{font-size:1.08rem;margin:0 0 22px}
h2{font:700 1.35rem/1.3 system-ui,sans-serif;margin:34px 0 12px}
.section-note{margin:-6px 0 12px;color:var(--muted);font: .92rem/1.45 system-ui,sans-serif}
.top{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}
.pin,.item,.stat,.court,.box{background:var(--card);border:1px solid var(--line);border-radius:12px}
.pin{padding:12px 14px;border-left:6px solid var(--breaking);background:var(--breaking-bg)}
.pin p,.item p{margin:6px 0}
.meta{display:flex;flex-wrap:wrap;align-items:center;gap:8px;font:700 .82rem/1.3 system-ui,sans-serif}
.tz{color:var(--muted);font-weight:700}
.badge{color:#fff;border-radius:999px;padding:2px 8px;letter-spacing:.04em;text-transform:uppercase;font-size:.72rem}
.badge.breaking{background:#9f1239}
.badge.important{background:#92400e}
.feed{display:flex;flex-direction:column;gap:10px}
.item{padding:14px 16px;border-left:6px solid var(--line)}
.item.breaking{border-left-color:#9f1239;background:var(--breaking-bg)}
.item.important{border-left-color:#b45309;background:var(--important-bg)}
.srcs{display:flex;flex-wrap:wrap;gap:8px}
.src{font:600 .8rem/1.3 system-ui,sans-serif;white-space:nowrap}
.src:before{content:"↗ "}
.stats{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}
.stat{padding:14px 16px}
.stat .v{margin:0;font:800 1.8rem/1.1 system-ui,sans-serif;color:#9f1239}
.stat h3{margin:4px 0;font:700 1rem/1.3 system-ui,sans-serif}
.stat p,.court p,.box li{font: .95rem/1.5 system-ui,sans-serif}
.people{display:flex;flex-direction:column;gap:10px}
.person{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.person-id{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:8px}
.person h3{margin:0;font:700 1.12rem/1.3 system-ui,sans-serif}
.who,.where,.detail,.reason{margin:4px 0;font: .95rem/1.45 system-ui,sans-serif}
.where span{font-weight:700}
.detail{color:var(--muted)}
.chip{display:inline-block;border-radius:999px;padding:3px 10px;font:700 .75rem/1.3 system-ui,sans-serif;letter-spacing:.02em}
.chip.held{background:#ffe4e6;color:#9f1239}
.chip.rel{background:#dcfce7;color:#166534}
.chip.unk{background:#fef3c7;color:#92400e}
.two{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.box{padding:8px 16px 12px}
.box ul{margin:8px 0;padding-left:18px}
.box li{margin:8px 0}
.by{display:block;color:var(--important);font:600 .82rem/1.4 system-ui,sans-serif}
.court{padding:12px 14px;margin-bottom:8px}
.cd{margin:0 0 4px;font:700 .92rem/1.35 system-ui,sans-serif;color:#9f1239}
.sources li{word-break:break-all;font: .85rem/1.45 system-ui,sans-serif}
footer{color:var(--muted);font: .9rem/1.45 system-ui,sans-serif;margin-top:28px}
@media(prefers-color-scheme:dark){
  .badge.breaking{background:#fb7185;color:#4c0519}
  .badge.important{background:#fbbf24;color:#451a03}
  .live{background:#fb7185;color:#4c0519}
  .stat .v,.cd{color:#fda4af}
  .chip.held{background:#4c0519;color:#fecdd3}
  .chip.rel{background:#052e16;color:#bbf7d0}
  .chip.unk{background:#451a03;color:#fde68a}
}
@media(max-width:760px){
  body{font-size:17px}
  .wrap{padding:18px 14px 36px}
  .top,.stats,.two{grid-template-columns:1fr}
}
'''

page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark"><title>{e(d["title"])}</title><style>{CSS}</style></head><body><div class="wrap">
<header class="mast"><p class="kicker"><span class="live">Live</span> Protest desk</p><h1>{e(d["title"])}</h1>
<p class="updated">Last updated <time>{e(d["last_updated_ist"])}</time></p></header>
<div class="disclaimer"><strong>Disclaimer:</strong> This data is auto-generated by a Grok bot. The bot compiled this dashboard while publishing the site, from news reports, official statements, and labelled social-media posts. It is not an official record and has not been checked by a human editor. Names, counts, times, and detention status can be incomplete or wrong. Check the linked sources before relying on it.</div>
<h2>Top updates</h2>
<p class="section-note">Latest breaking entries. Each one is also in the feed below.</p>
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
</div></body></html>'''

open(os.path.join(ROOT, 'index.html'), 'w').write(page)
print('built', len(ordered), 'updates;', len(top), 'pinned')
