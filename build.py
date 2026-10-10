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
  --bg:#101719;--card:#182124;--header:#101719;--ink:#edf0e9;--muted:#acb8b6;
  --line:#344245;--accent:#ffab75;--link:#ffb98d;--link-hover:#ffd7bb;
  --vip:#ffab75;--vip-bg:#251f1b;--break:#f1ca7b;--break-ink:#251d0d;--break-bg:#28251b;
  --imp:#b5d3ce;--imp-ink:#142d29;--imp-bg:#192b2a;
  --held-bg:#3b2425;--held-ink:#ffb2ac;--rel-bg:#20372e;--rel-ink:#abd9ba;
  --unk-bg:#352f20;--unk-ink:#e5cc91;--shadow:0 2px 8px #0000000d;
}
body:has(#light:checked){
  color-scheme:light;
  --bg:#f5f3ed;--card:#fffefb;--header:#f5f3ed;--ink:#202c2c;--muted:#596967;
  --line:#d7dcd3;--accent:#a54219;--link:#93401f;--link-hover:#63290e;
  --vip:#a54219;--vip-bg:#fff8ef;--break:#e9c778;--break-ink:#443210;--break-bg:#fffbee;
  --imp:#c1dad3;--imp-ink:#20433d;--imp-bg:#f1f7f4;
  --held-bg:#fce9e5;--held-ink:#9c332a;--rel-bg:#e5f1e8;--rel-ink:#286341;
  --unk-bg:#f3ecd9;--unk-ink:#75601f;--shadow:0 2px 8px #25382b05;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth;scroll-padding-top:210px}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.7 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;-webkit-font-smoothing:antialiased}
a{color:var(--link);text-underline-offset:4px;text-decoration-thickness:1px}
a:hover{color:var(--link-hover)}
a:focus-visible{outline:2px solid var(--accent);outline-offset:5px;border-radius:2px}
.sr{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
.bar{position:sticky;top:0;z-index:30;display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:8px 20px;padding:22px max(28px,calc((100vw - 1184px)/2));background:var(--header);border-top:4px solid var(--accent);border-bottom:1px solid var(--line)}
.live{display:inline-flex;align-items:center;gap:8px;align-self:start;margin-top:8px;padding:4px 9px;border:1px solid var(--line);border-radius:4px;color:var(--accent);font-size:.65rem;font-weight:800;letter-spacing:.15em;text-transform:uppercase}
.dot{width:6px;height:6px;border-radius:50%;background:var(--accent)}
h1{grid-column:2;margin:0;max-width:850px;font:500 clamp(1.3rem,2.2vw,1.85rem)/1.2 Georgia,"Times New Roman",serif;letter-spacing:-.035em;text-wrap:balance}
.updated{grid-column:2;margin:0;color:var(--muted);font-size:.7rem;letter-spacing:.02em}
.updated time{color:var(--ink);font-weight:600}
.theme{grid-column:3;grid-row:1 / 3;align-self:center;border:1px solid var(--line);border-radius:4px;padding:7px 12px;color:var(--muted);font-size:.75rem;font-weight:600;cursor:pointer}
.theme:hover{border-color:var(--accent);color:var(--ink)}
.theme .on{display:none}
body:has(#light:checked) .theme .off{display:none}
body:has(#light:checked) .theme .on{display:inline}
body:has(#light:focus-visible) .theme{outline:2px solid var(--accent);outline-offset:4px}
.section-nav{grid-column:1 / -1;display:flex;gap:6px;min-width:0;overflow-x:auto;overscroll-behavior-x:contain;scrollbar-width:thin;padding:12px 3px 5px;margin-top:8px;border-top:1px solid var(--line)}
.section-nav a{flex:0 0 auto;padding:6px 10px;border-radius:3px;color:var(--muted);font-size:.73rem;font-weight:600;text-decoration:none;white-space:nowrap}
.section-nav a:hover,.section-nav a:focus-visible{background:var(--card);color:var(--accent)}
h2:target{border-top-color:var(--accent)}
.back-top{position:fixed;right:20px;bottom:20px;z-index:20;padding:9px 14px;border:1px solid var(--line);border-radius:4px;background:var(--header);color:var(--ink);font-size:.73rem;font-weight:600;text-decoration:none;box-shadow:var(--shadow)}
.back-top:hover{border-color:var(--accent)}
.wrap{max-width:1184px;margin:auto;padding:32px 28px 64px}
.disclaimer{margin:0 0 42px;padding:16px 20px;border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:4px;color:var(--muted);font-size:.78rem;line-height:1.7;background:var(--card)}
.disclaimer strong{color:var(--ink)}
h2{display:flex;align-items:baseline;flex-wrap:wrap;gap:10px;margin:52px 0 12px;padding-top:22px;border-top:1px solid var(--line);font:500 clamp(1.65rem,2.8vw,2.1rem)/1.2 Georgia,"Times New Roman",serif;letter-spacing:-.035em;text-wrap:balance}
.disclaimer+h2{margin-top:0;border-top:2px solid var(--accent)}
h2 small{font:400 .75rem/1.6 ui-sans-serif,system-ui,sans-serif;letter-spacing:0;color:var(--muted)}
.section-note{margin:0 0 22px;color:var(--muted);font-size:.8rem}
.top,.people,.stats,.two{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
.top{gap:12px}
.pin:last-child:nth-child(odd){grid-column:1 / -1}
.pin,.person,.stat,.court,.box{min-width:0;border:1px solid var(--line);border-radius:6px;background:var(--card);box-shadow:var(--shadow)}
.pin{position:relative;padding:22px 24px;border-top:3px solid var(--accent);background:var(--vip-bg)}
.pin p,.item p{margin:12px 0 0;overflow-wrap:anywhere}
.pin p{font:400 1.08rem/1.6 Georgia,"Times New Roman",serif}
.meta,.chips{display:flex;flex-wrap:wrap;align-items:center;gap:8px}
.meta{color:var(--muted);font-size:.73rem;font-weight:600;line-height:1.6}
.tz{font-size:.65rem;letter-spacing:.08em;color:var(--muted)}
.badge{display:inline-flex;padding:3px 7px;border-radius:3px;font-size:.6rem;font-weight:800;letter-spacing:.07em;line-height:1.5;text-transform:uppercase}
.badge.very-important{background:var(--accent);color:var(--bg)}
.badge.breaking{background:var(--break);color:var(--break-ink)}
.badge.important{background:var(--imp);color:var(--imp-ink)}
.feed{position:relative;border:1px solid var(--line);border-radius:6px;background:var(--card);padding:0 28px}
.item{position:relative;margin-left:8px;padding:24px 0 24px 28px;border-left:1px solid var(--line)}
.item:before{content:"";position:absolute;left:-5px;top:30px;width:9px;height:9px;border-radius:50%;background:var(--muted);border:2px solid var(--card)}
.item:not(:last-child):after{content:"";position:absolute;left:28px;right:0;bottom:0;height:1px;background:var(--line)}
.item.very-important:before{background:var(--accent)}
.item.breaking:before{background:var(--break)}
.item.important:before{background:var(--imp)}
.item p{max-width:88ch;font-size:.94rem;line-height:1.8}
.srcs{display:flex;flex-wrap:wrap;gap:6px 14px;margin-top:14px}
.src{display:inline-block;max-width:100%;overflow-wrap:anywhere;font-size:.7rem;font-weight:600;line-height:1.7}
.src:before{content:""}
.lede{max-width:85ch;margin:0;font:400 1.15rem/1.8 Georgia,"Times New Roman",serif;color:var(--ink)}
.stats{gap:0;border:1px solid var(--line);border-radius:6px;overflow:hidden;background:var(--card)}
.stat{padding:24px;border:0;border-radius:0;box-shadow:none}
.stat:nth-child(odd){border-right:1px solid var(--line)}
.stat:nth-child(n+3){border-top:1px solid var(--line)}
.stat .v{margin:0;color:var(--accent);font:500 clamp(1.8rem,3vw,2.6rem)/1.15 Georgia,"Times New Roman",serif;letter-spacing:-.045em;overflow-wrap:anywhere}
.stat h3{margin:10px 0 6px;font-size:.8rem;font-weight:650}
.stat p{margin:0;color:var(--muted);font-size:.77rem}
.person{padding:24px}
.person.very-important{border-top:3px solid var(--accent)}
.person-id{display:flex;flex-direction:column;gap:10px}
.person h3{margin:0;font:500 1.35rem/1.3 Georgia,"Times New Roman",serif;letter-spacing:-.02em;overflow-wrap:anywhere}
.chip{display:inline-flex;padding:3px 8px;border-radius:3px;font-size:.65rem;font-weight:700;line-height:1.5}
.chip.held{background:var(--held-bg);color:var(--held-ink)}
.chip.rel{background:var(--rel-bg);color:var(--rel-ink)}
.chip.unk{background:var(--unk-bg);color:var(--unk-ink)}
.who{margin:12px 0 18px;padding-bottom:16px;border-bottom:1px solid var(--line);color:var(--muted);font-size:.8rem}
.where{margin:6px 0;font-size:.78rem;overflow-wrap:anywhere}
.where span{display:inline-block;min-width:44px;color:var(--muted);font-size:.64rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em}
.detail,.reason{font-size:.8rem;margin:12px 0 0}
.reason{color:var(--muted)}
.two{gap:28px;align-items:start}
.two>div{min-width:0}
.two h2{font-size:1.65rem;min-height:84px}
.box{padding:8px 24px}
.box ul{margin:0;padding-left:17px}
.box li{padding:14px 0;font-size:.84rem;overflow-wrap:anywhere}
.box li+li{border-top:1px solid var(--line)}
.box li::marker{color:var(--accent);font-size:.75em}
.by{display:block;margin:7px 0 4px;color:var(--muted);font-size:.72rem;font-weight:600}
.court{padding:20px 24px;margin-bottom:12px}
.court p{margin:8px 0 0;font-size:.84rem}
.court .cd{margin:0;color:var(--accent);font-size:.72rem;font-weight:700}
.sources li{font-size:.75rem}
footer{margin-top:48px;padding-top:24px;border-top:1px solid var(--line);max-width:85ch;color:var(--muted);font-size:.73rem}
footer code{font-size:.7rem;color:var(--ink)}
@media(min-width:1000px){
  .item{display:grid;grid-template-columns:205px minmax(0,1fr);gap:0 24px}
  .item .meta{align-content:start;align-items:baseline;flex-direction:column;gap:6px;padding-top:4px}
  .item p{margin:0}
  .item .srcs{grid-column:2}
}
@media(max-width:700px){
  html{scroll-padding-top:250px}
  .bar{grid-template-columns:auto 1fr auto;padding:16px;gap:8px 12px}
  h1{font-size:1.24rem}
  .live{margin-top:3px;padding:4px 6px;font-size:.55rem;gap:5px}
  .updated{grid-column:1 / 3;font-size:.64rem}
  .theme{grid-row:2;padding:5px 8px;font-size:.68rem}
  .wrap{padding:22px 16px 40px}
  .disclaimer{padding:14px 16px;margin-bottom:30px}
  .top,.people,.stats,.two{grid-template-columns:minmax(0,1fr)}
  .top,.people{gap:12px}
  h2{margin-top:36px;padding-top:18px}
  .pin,.person,.stat,.court{padding:20px}
  .feed{padding:0 16px}
  .item{padding-left:20px;margin-left:4px}
  .item:not(:last-child):after{left:20px}
  .stat:nth-child(odd){border-right:0}
  .stat+.stat{border-top:1px solid var(--line)}
  .two{gap:0}
  .two h2{min-height:0}
  .box{padding:4px 20px}
  .lede{font-size:1.05rem}
}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
@media print{
  :root{--bg:#fff;--card:#fff;--header:#fff;--ink:#111;--muted:#444;--line:#ccc;--accent:#823616;--link:#823616;--vip-bg:#fff}
  .bar{position:static}.theme,.section-nav,.back-top{display:none}.pin,.person,.stat,.court{break-inside:avoid;box-shadow:none}
}
'''

page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(d["title"])}</title><style>{CSS}</style></head><body id="page-top">
<input id="light" class="sr" type="checkbox" aria-label="Switch to light mode">
<header class="bar"><span class="live"><span class="dot" aria-hidden="true"></span>Live</span><h1>{e(d["title"])}</h1>
<p class="updated">Last updated <time>{e(d["last_updated_ist"])}</time></p>
<label class="theme" for="light"><span class="off">Light</span><span class="on">Dark</span></label>
<nav class="section-nav" aria-label="Page sections">
<a href="#highlights">Highlights</a><a href="#live-updates">Live updates</a><a href="#background">Background</a><a href="#at-a-glance">At a glance</a><a href="#detainees">Detainees</a><a href="#supporters">Supporters</a><a href="#courts">Courts</a><a href="#allegations">Allegations</a><a href="#government">Government</a><a href="#legal-context">Legal context</a><a href="#caveats">Caveats</a><a href="#sources">Sources</a>
</nav></header>
<main class="wrap">
<div class="disclaimer"><strong>Disclaimer:</strong> This data is auto-generated by a Grok bot. The bot compiled this dashboard while publishing the site, from news reports, official statements, and labelled social-media posts. It is not an official record and has not been checked by a human editor. Names, counts, times, and detention status can be incomplete or wrong. Check the linked sources before relying on it.</div>
<h2 id="highlights">Very important</h2>
<p class="section-note">Key leader detentions, pinned newest first. Each one is also in the feed below.</p>
<div class="top">{pins}</div>
<h2 id="live-updates">Live updates</h2>
<p class="section-note">Newest first. Times are IST.</p>
<div class="feed">{feed}</div>
<h2 id="background">Background</h2>
<p class="lede">{e(d["summary"])}</p>
<h2 id="at-a-glance">At a glance</h2>
<div class="stats">{stats}</div>
<h2 id="detainees">Key people detained</h2>
<p class="section-note">Status chip, then the recorded time and place.</p>
<div class="people">{people}</div>
<div class="two"><div><h2 id="supporters">Notable people who joined / backed it</h2><div class="box"><ul>{joined}</ul></div></div>
<div><h2 id="courts">Court updates</h2>{courts}</div></div>
<h2 id="allegations">Alleged govt failures &amp; rules broken <small>(these are allegations, not findings)</small></h2>
<div class="box"><ul>{allegations}</ul></div>
<div class="two"><div><h2 id="government">Government / police position</h2><div class="box"><ul>{govt}</ul></div></div>
<div><h2 id="legal-context">Legal context (reference)</h2><div class="box"><ul>{legal}</ul></div></div></div>
<h2 id="caveats">Caveats</h2><div class="box"><ul>{caveats}</ul></div>
<h2 id="sources">Sources</h2><div class="box"><ul class="sources">{sources}</ul></div>
<footer>Auto-generated by a Grok bot from mainstream media, official statements and labelled social-media posts. Not an official record. To refresh: edit data.json, then run <code>python3 build.py</code>.</footer>
</main><a class="back-top" href="#page-top" aria-label="Back to top of page">Back to top</a></body></html>'''

open(os.path.join(ROOT, 'index.html'), 'w').write(page)
print('built', len(ordered), 'updates;', len(top), 'pinned')
