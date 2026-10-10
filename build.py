import json, html, os, re
from urllib.parse import urlparse
from urllib.parse import urlencode
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(ROOT, 'data.json')))
e = lambda s: html.escape(str(s))

def header_parts(title):
    parts = re.split(r'\s+[—–]\s+', str(title), maxsplit=1)
    return parts[0], parts[1] if len(parts) > 1 else ''

header_title, header_subtitle = header_parts(d['title'])

SITE_URL = 'https://jantarmantar.sholock.com/'
SITE_NAME = 'Jantar Mantar Updates'
DESCRIPTION = (
    'Follow the Jantar Mantar 2.0 / CJP anti-SIR protest in Delhi: '
    'reported detentions, court developments and source-linked updates compiled by Grok Bot.'
)
SOCIAL_IMAGE = SITE_URL + 'social-preview.png'
SOCIAL_IMAGE_ALT = 'Jantar Mantar 2.0: CJP / anti-SIR protest updates from Delhi, compiled by Grok Bot. Verify linked sources.'

# Use the bot's recorded update time, never the build clock.
try:
    updated_iso = datetime.strptime(d['last_updated_ist'], '%d %b %Y, %I:%M %p IST').replace(
        tzinfo=timezone(timedelta(hours=5, minutes=30))
    ).isoformat()
except (KeyError, ValueError, TypeError):
    updated_iso = None

webpage = {
    '@type': 'WebPage', '@id': SITE_URL + '#webpage', 'url': SITE_URL,
    'name': d['title'], 'description': DESCRIPTION, 'inLanguage': 'en-IN',
    'isPartOf': {'@id': SITE_URL + '#website'},
    'primaryImageOfPage': {'@type': 'ImageObject', 'url': SOCIAL_IMAGE, 'width': 1200, 'height': 630},
}
if updated_iso:
    webpage['dateModified'] = updated_iso
structured_data = json.dumps({
    '@context': 'https://schema.org',
    '@graph': [
        {'@type': 'WebSite', '@id': SITE_URL + '#website', 'url': SITE_URL,
         'name': SITE_NAME, 'inLanguage': 'en-IN'},
        webpage,
    ],
}, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
share_text = d['title'] + ' — source-linked updates compiled by Grok Bot. Verify linked sources.'
share_x = 'https://twitter.com/intent/tweet?' + urlencode({'text': share_text, 'url': SITE_URL})
share_whatsapp = 'https://wa.me/?' + urlencode({'text': share_text + '\n' + SITE_URL})
share_facebook = 'https://www.facebook.com/sharer/sharer.php?' + urlencode({'u': SITE_URL})

SOURCE_LABELS = {
    'barandbench.com': 'Bar & Bench', 'businesstoday.in': 'Business Today',
    'geo.tv': 'Geo News', 'hindustantimes.com': 'Hindustan Times',
    'indianexpress.com': 'Indian Express', 'indiatoday.in': 'India Today',
    'livelaw.in': 'LiveLaw', 'm.thewire.in': 'The Wire', 'thewire.in': 'The Wire',
    'ndtv.com': 'NDTV', 'npr.org': 'NPR', 'scobserver.in': 'Supreme Court Observer',
    'scroll.in': 'Scroll', 'thehindu.com': 'The Hindu', 'theprint.in': 'ThePrint',
    'timesofindia.indiatimes.com': 'Times of India', 'tribuneindia.com': 'The Tribune',
    'x.com': 'X', 'twitter.com': 'X',
}

def source_label(url):
    host = urlparse(url).netloc.removeprefix('www.')
    return SOURCE_LABELS.get(host, host)

# LIVE_JS (below) must emit the same markup as these helpers.
def links(value):
    if not value:
        return ''
    urls = value if isinstance(value, list) else [value]
    return '<span class="source-links" aria-label="Sources">' + ''.join(
        f'<a class="src" href="{e(u)}" target="_blank" rel="noopener" aria-label="Read source {i + 1}: {e(source_label(u))} (opens a new tab)">{i + 1} · {e(source_label(u))}</a>'
        for i, u in enumerate(urls)
    ) + '</span>'

def update_id(item):
    # Content-based IDs survive inserted updates and feed reordering.
    value = 2166136261
    for char in item['t'] + '\n' + item['e']:
        value = ((value ^ ord(char)) * 16777619) & 0xffffffff
    return f'update-{value:08x}'

def card_sharing(item):
    url = SITE_URL + '#' + update_id(item)
    event = item['e']
    excerpt = event if len(event) <= 180 else event[:179] + '…'
    short = f'Jantar Mantar update · {item["t"]} IST\n\n{excerpt}\n\nBot-compiled; verify sources.'
    full = f'Jantar Mantar update · {item["t"]} IST\n\n{event}\n\nBot-compiled; verify linked sources.\n{url}'
    x_url = 'https://twitter.com/intent/tweet?' + urlencode({'text': short, 'url': url})
    whatsapp_url = 'https://wa.me/?' + urlencode({'text': full})
    facebook_url = 'https://www.facebook.com/sharer/sharer.php?' + urlencode({'u': url})
    return (
        '<details class="card-share"><summary>Share update</summary><div class="card-share-options">'
        f'<a href="{e(x_url)}" target="_blank" rel="noopener noreferrer" aria-label="Share this update on X (opens a new tab)">X</a>'
        f'<a href="{e(whatsapp_url)}" target="_blank" rel="noopener noreferrer" aria-label="Share this update on WhatsApp (opens a new tab)">WhatsApp</a>'
        f'<a href="{e(facebook_url)}" target="_blank" rel="noopener noreferrer" aria-label="Share this update on Facebook (opens a new tab)">Facebook</a>'
        f'<a class="update-permalink" href="{e(url)}">Link to update</a>'
        f'<button type="button" class="copy-update" data-url="{e(url)}" hidden>Copy link</button>'
        f'</div><input class="share-url card-share-url" value="{e(url)}" readonly aria-label="Update link to copy" hidden>'
        '<span class="card-share-status" role="status" aria-live="polite"></span></details>'
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

def figure(image, kind):
    if not isinstance(image, dict) or not image.get('url'):
        return ''
    alt = image.get('alt') or ''
    credit = image.get('credit') or ''
    src = image.get('source_url') or ''
    if credit and src:
        cap = f'<figcaption class="credit"><a href="{e(src)}" target="_blank" rel="noopener">{e(credit)}</a></figcaption>'
    elif credit:
        cap = f'<figcaption class="credit">{e(credit)}</figcaption>'
    else:
        cap = ''
    return (
        f'<figure class="{kind}">'
        f'<img src="{e(image["url"])}" alt="{e(alt)}" loading="lazy" decoding="async" referrerpolicy="no-referrer" onerror="this.closest(\'figure\').hidden=true">'
        f'{cap}</figure>'
    )

def feed_item(item, pinned=False):
    level = importance(item)
    cls = 'pin' if pinned else 'item'
    shot = figure(item.get('image'), 'hero' if pinned else 'thumb')
    return (
        f'<article class="{cls} {level}" id="{"pin-" if pinned else ""}{update_id(item)}">'
        f'{shot if pinned else ""}'
        f'<div class="meta">{badge(level)}<time>{e(item["t"])}</time><span class="tz">IST</span></div>'
        f'<p>{e(item["e"])}</p>'
        f'{"" if pinned else shot}'
        f'<div class="srcs">{links(item.get("src"))}</div>'
        f'{card_sharing(item)}'
        f'</article>'
    )

stats = ''.join(
    f'<article class="stat"><p class="v">{e(s["value"])}</p><h3>{e(s["label"])}</h3><details class="stat-note"><summary>Context &amp; sources</summary><p>{e(s["note"])} {links(s["src"])}</p></details></article>'
    for s in d['stats']
)
feed = ''.join(feed_item(item) for item in ordered)
pins = ''.join(feed_item(item, pinned=True) for item in top)
# Detainees stay in the order stored in data.json.
people = ''.join(
    f'<article class="person{" very-important" if is_vip(x["name"]) else ""}"><div class="person-main"><div class="person-id"><h3>{e(x["name"])}</h3><span class="chips">{badge("very-important") if is_vip(x["name"]) else ""}{status_chip(x["status"])}</span></div>'
    f'{figure(x.get("image"), "thumb")}'
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
sources = ''.join(f'<li><a href="{e(u)}" target="_blank" rel="noopener"><span class="source-publisher">{e(source_label(u))}</span><span class="source-address">{e(u)}</span></a></li>' for u in d['sources'])

def picture_cards(rows):
    seen, cards = set(), []
    for row in rows:
        image = row.get('image')
        if not isinstance(image, dict) or not image.get('url') or image['url'] in seen:
            continue
        seen.add(image['url'])
        report = links(image.get('source_url'))
        cards.append(f'<article class="photo-card">{figure(image, "hero")}<p class="photo-caption">{e(image.get("alt") or "Source preview")}</p><div class="srcs">{report}</div></article>')
    return ''.join(cards)

pictures = picture_cards(ordered + d['detainees'])

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
.bar{position:sticky;top:0;z-index:30;display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:12px 20px;padding:22px max(28px,calc((100vw - 1184px)/2));background:var(--header);border-top:4px solid var(--accent);border-bottom:1px solid var(--line)}
.brand{grid-column:1;min-width:0;display:flex;align-items:center;gap:16px}
.brand-mark{display:block;flex:0 0 58px;width:58px;height:58px;object-fit:contain}
.brand-copy{min-width:0}
.subtitle{margin:7px 0 0;color:var(--muted);font-size:.85rem;line-height:1.5;letter-spacing:.02em}
.subtitle:empty{display:none}
.status-row{grid-column:1;display:flex;flex-wrap:wrap;align-items:center;gap:10px}
.live{display:inline-flex;align-items:center;gap:7px;padding:3px 8px;border:1px solid var(--line);border-radius:4px;color:var(--accent);font-size:.6rem;font-weight:800;letter-spacing:.13em;text-transform:uppercase}
.dot{width:6px;height:6px;border-radius:50%;background:var(--accent)}
h1{margin:0;font:500 clamp(1.8rem,3vw,2.45rem)/1.1 Georgia,"Times New Roman",serif;letter-spacing:-.04em;text-wrap:balance}
.brand h1::after{content:"";display:block;width:36px;height:2px;margin-top:9px;background:var(--accent)}
.bar{background-image:linear-gradient(90deg,var(--vip-bg),transparent 42%);border-top-width:3px}
.updated{margin:0;color:var(--muted);font-size:.7rem;letter-spacing:.02em}
.updated time{color:var(--ink);font-weight:600}
.theme{grid-column:2;grid-row:1 / 3;align-self:start;border:1px solid var(--line);border-radius:4px;padding:7px 12px;color:var(--muted);font-size:.75rem;font-weight:600;cursor:pointer}
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
.source-links{display:inline-flex;flex-wrap:wrap;gap:6px;max-width:100%;vertical-align:middle;margin:4px 0}
.source-links .src{padding:4px 8px;border:1px solid var(--line);border-radius:4px;background:var(--bg);font-size:.68rem;line-height:1.5;text-decoration:none}
.source-links .src:hover{border-color:var(--accent)}
.source-publisher{display:block;font-weight:700;color:var(--link);font-size:.82rem}
.source-address{display:block;color:var(--muted);font-size:.7rem;overflow-wrap:anywhere;margin-top:4px}
.sources a{text-decoration:none}
.sources a:hover .source-address{color:var(--ink)}
.card-share{margin-top:12px;grid-column:2 / -1;font-size:.73rem;min-width:0}
.card-share>summary{display:list-item;list-style-position:inside;width:fit-content;color:var(--muted);cursor:pointer;padding:5px 0}
.card-share>summary:hover{color:var(--accent)}
.card-share-options{display:flex;flex-wrap:wrap;gap:8px;padding:10px 0}
.card-share-options a,.card-share-options button{padding:7px 10px;border:1px solid var(--line);border-radius:4px;background:var(--bg);color:var(--ink);font:600 .7rem/1.5 system-ui,sans-serif;text-decoration:none;cursor:pointer}
.card-share-options a:hover,.card-share-options button:hover{border-color:var(--accent);color:var(--accent)}
.card-share-options button:focus-visible{outline:2px solid var(--accent);outline-offset:4px}
.card-share-status{display:block;color:var(--muted);font-size:.7rem}
.item:target,.pin:target{outline:2px solid var(--accent);outline-offset:-2px;border-radius:4px}
@media print{.card-share{display:none!important}}
.hero,.thumb{margin:0;min-width:0;max-width:100%}
.pin>.hero{margin:0 0 16px}
.item>.thumb,.person .thumb{margin:12px 0 0}
.hero img,.thumb img{display:block;width:100%;max-width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:6px;background:var(--line)}
.thumb img{max-width:220px;aspect-ratio:3/2}
.hero img{max-height:440px}
.credit{margin:6px 0 0;color:var(--muted);font-size:.68rem;font-weight:600;line-height:1.4}
.credit a{color:var(--muted)}
.credit a:hover{color:var(--link-hover)}
.lede{max-width:85ch;margin:0;font:400 1.15rem/1.8 Georgia,"Times New Roman",serif;color:var(--ink)}
.stats{gap:0;border:1px solid var(--line);border-radius:6px;overflow:hidden;background:var(--card)}
.stat{padding:24px;border:0;border-radius:0;box-shadow:none}
.stat:nth-child(odd){border-right:1px solid var(--line)}
.stat:nth-child(n+3){border-top:1px solid var(--line)}
.stat .v{margin:0;color:var(--accent);font:500 clamp(1.8rem,3vw,2.6rem)/1.15 Georgia,"Times New Roman",serif;letter-spacing:-.045em;overflow-wrap:anywhere}
.stat h3{margin:10px 0 6px;font-size:.8rem;font-weight:650}
.stat-note{margin-top:12px}
.stat-note>summary{cursor:pointer;font-size:.72rem;color:var(--muted);width:fit-content}
.stat-note>summary:hover{color:var(--accent)}
.stat-note[open]>summary{margin-bottom:10px}
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
.footer-credit{display:block;margin-top:14px;color:var(--ink);font-weight:600}
.pictures{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
.photo-card{min-width:0;padding:12px;border:1px solid var(--line);border-radius:6px;background:var(--card)}
.photo-card .hero img{aspect-ratio:16/9;object-fit:contain;background:var(--bg)}
.photo-caption{font:400 .95rem/1.5 Georgia,serif;margin:12px 0 0}
.photo-card .srcs{margin-top:8px}
.pin .hero img{object-fit:contain;background:var(--bg)}
.person .thumb{width:112px;margin:0;grid-column:2;grid-row:2;align-self:start}
.person .thumb img{aspect-ratio:4/3;object-fit:contain}
.person-main{display:grid;grid-template-columns:minmax(0,1fr) 112px;gap:12px 16px}
.person-main>*{grid-column:1 / -1;min-width:0}
.person-main>.thumb{grid-column:2;grid-row:2}
.person-main>.who{margin:0;padding:0;border:0}
.person-main:has(>.thumb:not([hidden]))>.who{grid-column:1;grid-row:2;align-self:center}
.person-main>.where,.person-main>.detail,.person-main>.reason{margin:0}
.person .credit{overflow-wrap:anywhere}
@media(max-width:400px){
 .person-main{grid-template-columns:minmax(0,1fr) 88px;column-gap:12px}
 .person .thumb{width:88px}
}
.collection-controls{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin:16px 0 24px}
.collection-count{flex:1 1 180px;color:var(--muted);font-size:.75rem}
.collection-controls button{padding:8px 12px;border:1px solid var(--line);border-radius:4px;background:var(--card);color:var(--ink);font:600 .75rem/1.5 system-ui,sans-serif;cursor:pointer}
.collection-controls button:hover{border-color:var(--accent)}
.collection-controls button:focus-visible,summary:focus-visible{outline:2px solid var(--accent);outline-offset:4px}
.section-fold{margin:18px 0;border:1px solid var(--line);border-radius:6px;background:var(--card)}
.section-fold>summary{list-style:none;display:flex;align-items:center;justify-content:space-between;gap:16px;padding:18px 20px;cursor:pointer}
.section-fold>summary::-webkit-details-marker{display:none}
.section-fold>summary::after{content:"+";font:400 1.5rem/1 system-ui;color:var(--accent)}
.section-fold[open]>summary::after{content:"−"}
.section-fold>summary h2{margin:0;padding:0;border:0;min-height:0;font-size:1.4rem}
.section-fold>summary h2 small{display:block}
.section-fold>.box{border:0;box-shadow:none}
.section-fold>.lede{padding:0 20px 20px}
.section-fold .court{margin:0 16px 12px}
.page-shortcuts{position:fixed;right:16px;bottom:16px;z-index:20;display:flex;gap:1px;padding:4px;border:1px solid var(--line);border-radius:4px;background:var(--header);box-shadow:var(--shadow)}
.page-shortcuts a{padding:7px 10px;color:var(--ink);font-size:.72rem;text-decoration:none}
.page-shortcuts a:hover{color:var(--accent)}
footer{padding-bottom:40px}
@media(min-width:1000px){
 .item:has(>.thumb){grid-template-columns:150px minmax(0,1fr) 148px}
 .item:has(>.thumb)>.thumb{grid-column:3;grid-row:1 / 3;margin:0;align-self:start}
 .item:has(>.thumb)>p{grid-column:2}
 .item:has(>.thumb)>.srcs{grid-column:2}
}
@media(max-width:700px){
 .pictures{display:flex;overflow-x:auto;scroll-snap-type:x proximity;padding-bottom:10px}
 .pictures>.photo-card{flex:0 0 88%;scroll-snap-align:start}
 .section-fold>summary{padding:16px}
 .section-fold>summary h2{font-size:1.25rem}
}
@media print{.collection-controls,.page-shortcuts{display:none!important}[data-collection]>*[hidden]{display:block!important}}
.share-panel{margin-top:48px;padding-bottom:24px}
.share-panel h2{margin-top:0}
.share-actions{display:flex;flex-wrap:wrap;gap:10px}
.share-actions a,.share-actions button{padding:9px 14px;border:1px solid var(--line);border-radius:4px;background:var(--card);color:var(--ink);font:600 .78rem/1.5 ui-sans-serif,system-ui,sans-serif;text-decoration:none;cursor:pointer}
.share-actions a:hover,.share-actions button:hover{border-color:var(--accent);color:var(--accent)}
.share-actions button:focus-visible,.share-url:focus-visible{outline:2px solid var(--accent);outline-offset:4px}
.share-status{min-height:1.7em;color:var(--muted);font-size:.75rem;margin:10px 0 0}
.share-url{width:100%;max-width:440px;margin-top:10px;padding:10px;border:1px solid var(--line);border-radius:4px;background:var(--card);color:var(--ink);font-size:.8rem}
[hidden]{display:none!important}
@media(min-width:1000px){
  .item{display:grid;grid-template-columns:205px minmax(0,1fr);gap:0 24px}
  .item .meta{align-content:start;align-items:baseline;flex-direction:column;gap:6px;padding-top:4px}
  .item p{margin:0}
  .item .thumb,.item .srcs{grid-column:2}
  .item .thumb{justify-self:start}
}
@media(max-width:700px){
  html{scroll-padding-top:250px}
  .bar{padding:16px;gap:12px}
  .brand{gap:10px}
  .brand-mark{flex-basis:36px;width:36px;height:42px}
  h1{font-size:1.5rem}
  .brand h1::after{width:26px;margin-top:7px}
  .subtitle{font-size:.75rem;margin-top:6px}
  .live{padding:3px 6px;font-size:.55rem;gap:5px}
  .status-row{grid-column:1 / -1;gap:8px}
  .updated{font-size:.64rem}
  .theme{grid-row:1;padding:5px 8px;font-size:.68rem}
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
  .thumb img{max-width:180px}
  .hero img{max-height:220px}
}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
@media print{
  :root{--bg:#fff;--card:#fff;--header:#fff;--ink:#111;--muted:#444;--line:#ccc;--accent:#823616;--link:#823616;--vip-bg:#fff}
  .bar{position:static}.theme,.section-nav,.back-top,.share-panel{display:none}.pin,.person,.stat,.court{break-inside:avoid;box-shadow:none}
}
'''

LIVE_JS = r'''
function esc(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#x27;");
}

function hostOf(u) {
  var m = /^[a-z][a-z0-9+.-]*:\/\/([^/?#]*)/i.exec(String(u));
  var netloc = m ? m[1] : "";
  var at = netloc.lastIndexOf("@");
  if (at !== -1) netloc = netloc.slice(at + 1);
  return netloc.replace(/www\./g, "");
}

function links(value) {
  if (value == null || value === "") return "";
  var urls = Array.isArray(value) ? value : [value];
  if (!urls.length) return "";
  var out = '<span class="source-links" aria-label="Sources">';
  for (var i = 0; i < urls.length; i++) {
    var u = urls[i];
    var label = sourceLabel(u);
    out += '<a class="src" href="' + esc(u) + '" target="_blank" rel="noopener" aria-label="Read source ' + (i + 1) + ': ' + esc(label) + ' (opens a new tab)">' + (i + 1) + ' · ' + esc(label) + "</a>";
  }
  return out + '</span>';
}

var SOURCE_LABELS = __SOURCE_LABELS__;
function sourceLabel(url) {
  var host = hostOf(url);
  return SOURCE_LABELS[host] || host;
}

function updateId(item) {
  var value = 2166136261;
  for (var char of (item.t + '\n' + item.e)) value = Math.imul(value ^ char.codePointAt(0), 16777619) >>> 0;
  return 'update-' + value.toString(16).padStart(8, '0');
}

function formValue(value) {
  return encodeURIComponent(value).replace(/[!'()*]/g, function (char) {
    return '%' + char.charCodeAt(0).toString(16).toUpperCase();
  }).replace(/%20/g, '+');
}

function cardSharing(item) {
  var url = 'https://jantarmantar.sholock.com/#' + updateId(item);
  var chars = Array.from(item.e);
  var excerpt = chars.length <= 180 ? item.e : chars.slice(0, 179).join('') + '…';
  var short = 'Jantar Mantar update · ' + item.t + ' IST\n\n' + excerpt + '\n\nBot-compiled; verify sources.';
  var full = 'Jantar Mantar update · ' + item.t + ' IST\n\n' + item.e + '\n\nBot-compiled; verify linked sources.\n' + url;
  var xUrl = 'https://twitter.com/intent/tweet?text=' + formValue(short) + '&url=' + formValue(url);
  var whatsappUrl = 'https://wa.me/?text=' + formValue(full);
  var facebookUrl = 'https://www.facebook.com/sharer/sharer.php?u=' + formValue(url);
  return '<details class="card-share"><summary>Share update</summary><div class="card-share-options">'
    + '<a href="' + esc(xUrl) + '" target="_blank" rel="noopener noreferrer" aria-label="Share this update on X (opens a new tab)">X</a>'
    + '<a href="' + esc(whatsappUrl) + '" target="_blank" rel="noopener noreferrer" aria-label="Share this update on WhatsApp (opens a new tab)">WhatsApp</a>'
    + '<a href="' + esc(facebookUrl) + '" target="_blank" rel="noopener noreferrer" aria-label="Share this update on Facebook (opens a new tab)">Facebook</a>'
    + '<a class="update-permalink" href="' + esc(url) + '">Link to update</a>'
    + '<button type="button" class="copy-update" data-url="' + esc(url) + '" hidden>Copy link</button>'
    + '</div><input class="share-url card-share-url" value="' + esc(url) + '" readonly aria-label="Update link to copy" hidden>'
    + '<span class="card-share-status" role="status" aria-live="polite"></span></details>';
}

function importance(item) {
  var level = String((item && item.importance) || "routine").toLowerCase();
  if (level === "very-important" || level === "breaking" || level === "important" || level === "routine") return level;
  return "routine";
}

function clockMinutes(text) {
  var re = /(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)|\bnoon\b/gi;
  var found = [];
  var m;
  while ((m = re.exec(text)) !== null) {
    if (m[0].toLowerCase() === "noon") {
      found.push(12 * 60);
      continue;
    }
    var hh = parseInt(m[1], 10);
    var mm = parseInt(m[2] || "0", 10);
    var ap = m[3].toLowerCase().replace(/\./g, "");
    if (ap === "pm" && hh !== 12) hh += 12;
    if (ap === "am" && hh === 12) hh = 0;
    found.push(hh * 60 + mm);
  }
  return found.length ? Math.max.apply(null, found) : -1;
}

function orderedTimeline(items) {
  var rows = [];
  for (var idx = 0; idx < items.length; idx++) rows.push({ item: items[idx], idx: idx });
  rows.sort(function (a, b) {
    function key(x) {
      var dayM = /(\d+)\s*Oct/i.exec(x.item.t || "");
      var day = dayM ? parseInt(dayM[1], 10) : 0;
      return [day, clockMinutes(x.item.t || ""), x.idx];
    }
    var ka = key(a);
    var kb = key(b);
    for (var i = 0; i < 3; i++) if (ka[i] !== kb[i]) return kb[i] - ka[i];
    return 0;
  });
  var ordered = [];
  for (var j = 0; j < rows.length; j++) ordered.push(rows[j].item);
  return ordered;
}

function statusChip(status) {
  var low = String(status).toLowerCase();
  var kind = "unk";
  var label = "Unknown";
  if (low.indexOf("released") === 0) {
    kind = "rel";
    label = "Released";
  } else if (low.indexOf("held") === 0) {
    kind = "held";
    label = "Detained";
  }
  return '<span class="chip ' + kind + '">' + label + "</span>";
}

function badge(level) {
  var labels = { "very-important": "Very important", breaking: "Breaking", important: "Important" };
  if (!Object.prototype.hasOwnProperty.call(labels, level)) return "";
  return '<span class="badge ' + level + '">' + labels[level] + "</span>";
}

var VIP_NAMES = [
  "dhruv rathee", "abhijeet dipke", "saurav das", "ashutosh ranka", "ratna singh",
  "neha bora", "yogendra yadav", "mamata banerjee", "arvind kejriwal", "manish sisodia",
  "pinarayi vijayan", "john brittas",
  "k.n. balagopal", "m.a. baby", "brinda karat", "manik sarkar", "jitendra chaudhury",
  "elamaram kareem"
];

function isVip(name) {
  var low = String(name).toLowerCase();
  for (var i = 0; i < VIP_NAMES.length; i++) if (low.indexOf(VIP_NAMES[i]) !== -1) return true;
  return false;
}

function figure(image, kind) {
  if (!image || !image.url) return "";
  var alt = image.alt || "";
  var credit = image.credit || "";
  var src = image.source_url || "";
  var cap = "";
  if (credit && src) cap = '<figcaption class="credit"><a href="' + esc(src) + '" target="_blank" rel="noopener">' + esc(credit) + "</a></figcaption>";
  else if (credit) cap = '<figcaption class="credit">' + esc(credit) + "</figcaption>";
  return '<figure class="' + kind + '"><img src="' + esc(image.url) + '" alt="' + esc(alt) + '" loading="lazy" decoding="async" referrerpolicy="no-referrer" onerror="this.closest(' + "'figure'" + ').hidden=true">' + cap + "</figure>";
}

function feedItem(item, pinned) {
  var level = importance(item);
  var cls = pinned ? "pin" : "item";
  var shot = figure(item.image, pinned ? "hero" : "thumb");
  return '<article class="' + cls + " " + level + '" id="' + (pinned ? 'pin-' : '') + updateId(item) + '">'
    + (pinned ? shot : "")
    + '<div class="meta">' + badge(level) + "<time>" + esc(item.t) + '</time><span class="tz">IST</span></div>'
    + "<p>" + esc(item.e) + "</p>"
    + (pinned ? "" : shot)
    + '<div class="srcs">' + links(item.src) + "</div>"
    + cardSharing(item)
    + "</article>";
}

function pictureCards(rows) {
  var seen = new Set();
  var cards = "";
  for (var i = 0; i < rows.length; i++) {
    var image = rows[i].image;
    if (!image || !image.url || seen.has(image.url)) continue;
    seen.add(image.url);
    cards += '<article class="photo-card">' + figure(image, "hero")
      + '<p class="photo-caption">' + esc(image.alt || "Source preview") + '</p><div class="srcs">'
      + links(image.source_url) + '</div></article>';
  }
  return cards;
}

function renderParts(d) {
  if (!d || !d.timeline || !d.detainees) throw new Error("incomplete data");
  var fullTitle = String(d.title);
  var separator = /\s+[—–]\s+/.exec(fullTitle);
  var headerTitle = separator ? fullTitle.slice(0, separator.index) : fullTitle;
  var headerSubtitle = separator ? fullTitle.slice(separator.index + separator[0].length) : '';
  var ordered = orderedTimeline(d.timeline);
  var top = [];
  for (var i = 0; i < ordered.length; i++) if (importance(ordered[i]) === "very-important") top.push(ordered[i]);
  var stats = "";
  for (var s = 0; s < d.stats.length; s++) {
    var st = d.stats[s];
    stats += '<article class="stat"><p class="v">' + esc(st.value) + "</p><h3>" + esc(st.label) + '</h3><details class="stat-note"><summary>Context &amp; sources</summary><p>' + esc(st.note) + " " + links(st.src) + "</p></details></article>";
  }
  var pins = "";
  for (var p = 0; p < top.length; p++) pins += feedItem(top[p], true);
  var feed = "";
  for (var f = 0; f < ordered.length; f++) feed += feedItem(ordered[f], false);
  var people = "";
  for (var n = 0; n < d.detainees.length; n++) {
    var x = d.detainees[n];
    var vip = isVip(x.name);
    people += '<article class="person' + (vip ? " very-important" : "") + '"><div class="person-main"><div class="person-id"><h3>' + esc(x.name) + '</h3><span class="chips">' + (vip ? badge("very-important") : "") + statusChip(x.status) + "</span></div>"
      + figure(x.image, "thumb")
      + '<p class="who">' + esc(x.who) + "</p>"
      + '<p class="where"><span>Time</span> ' + esc(x.when) + "</p>"
      + '<p class="where"><span>Place</span> ' + esc(x.where) + "</p>"
      + '<p class="detail">' + esc(x.status) + "</p>"
      + '<p class="reason">' + esc(x.reason) + "</p>"
      + '<div class="srcs">' + links(x.src) + "</div></div></article>";
  }
  var joined = "";
  for (var j = 0; j < d.joined.length; j++) joined += "<li><b>" + esc(d.joined[j].name) + "</b> — " + esc(d.joined[j].role) + "</li>";
  var allegations = "";
  for (var a = 0; a < d.allegations.length; a++) {
    var al = d.allegations[a];
    allegations += "<li>" + esc(al.claim) + ' <span class="by">Alleged by: ' + esc(al.by) + "</span> " + links(al.src) + "</li>";
  }
  var govt = "";
  for (var g = 0; g < d.govt_position.length; g++) govt += "<li>" + esc(d.govt_position[g].point) + " " + links(d.govt_position[g].src) + "</li>";
  var legal = "";
  for (var l = 0; l < d.legal_context.length; l++) legal += "<li>" + esc(d.legal_context[l]) + "</li>";
  var courts = "";
  for (var c = 0; c < d.courts.length; c++) {
    var ct = d.courts[c];
    courts += '<article class="court"><p class="cd">' + esc(ct.date) + " · " + esc(ct.court) + "</p><p>" + esc(ct.action) + " " + links(ct.src) + "</p></article>";
  }
  var caveats = "";
  for (var k = 0; k < d.caveats.length; k++) caveats += "<li>" + esc(d.caveats[k]) + "</li>";
  var sources = "";
  for (var u = 0; u < d.sources.length; u++) sources += '<li><a href="' + esc(d.sources[u]) + '" target="_blank" rel="noopener"><span class="source-publisher">' + esc(sourceLabel(d.sources[u])) + '</span><span class="source-address">' + esc(d.sources[u]) + "</span></a></li>";
  return {
    title: String(d.title),
    titleHtml: esc(headerTitle),
    subtitleHtml: esc(headerSubtitle),
    updatedHtml: esc(d.last_updated_ist),
    stats: stats,
    pictures: pictureCards(ordered.concat(d.detainees)),
    pins: pins,
    feed: feed,
    lede: esc(d.summary),
    people: people,
    joined: joined,
    courts: courts,
    allegations: allegations,
    govt: govt,
    legal: legal,
    caveats: caveats,
    sources: sources
  };
}
globalThis.renderParts = renderParts;

var collectionLimits = {};
var lastOpenedHash = null;

function syncScrollPadding() {
  var header = document.querySelector('.bar');
  if (header) document.documentElement.style.scrollPaddingTop = Math.ceil(header.getBoundingClientRect().height + 24) + 'px';
}

function updateCollections() {
  document.querySelectorAll('[data-collection]').forEach(function (container) {
    var initial = Number(container.dataset.collection);
    var limit = collectionLimits[container.id] === undefined ? initial : collectionLimits[container.id];
    var total = container.children.length;
    Array.from(container.children).forEach(function (card, index) { card.hidden = index >= limit; });
    var controls = document.querySelector('[data-controls="' + container.id + '"]');
    controls.hidden = total <= initial;
    controls.querySelector('.collection-count').textContent = 'Showing ' + Math.min(limit, total) + ' of ' + total;
    controls.querySelector('[data-action="more"]').hidden = limit >= total;
    controls.querySelector('[data-action="all"]').hidden = limit >= total;
    controls.querySelector('[data-action="less"]').hidden = limit <= initial;
  });
  document.querySelectorAll('.copy-update').forEach(function (button) { button.hidden = false; });
}

function openHashSection(scroll) {
  var id;
  try { id = decodeURIComponent(location.hash.slice(1)); } catch (_) { return; }
  var target = document.getElementById(id);
  if (!target) return;
  var container = target.closest('[data-collection]');
  if (container && target.hidden) {
    var index = Array.from(container.children).indexOf(target);
    collectionLimits[container.id] = Math.max(index + 1, collectionLimits[container.id] || Number(container.dataset.collection));
    updateCollections();
  }
  var panel = target.closest('details');
  if (panel) panel.open = true;
  if (scroll !== false) target.scrollIntoView({ block: 'start' });
  lastOpenedHash = location.hash;
}

function initCollections() {
  syncScrollPadding();
  if (typeof ResizeObserver !== 'undefined') new ResizeObserver(syncScrollPadding).observe(document.querySelector('.bar'));
  updateCollections();
  document.querySelectorAll('[data-controls]').forEach(function (controls) {
    controls.addEventListener('click', function (event) {
      var button = event.target.closest('button');
      if (!button) return;
      var container = document.getElementById(controls.dataset.controls);
      var initial = Number(container.dataset.collection);
      var oldLimit = collectionLimits[container.id] === undefined ? initial : collectionLimits[container.id];
      var action = button.dataset.action;
      collectionLimits[container.id] = action === 'all' ? Infinity : action === 'less' ? initial : oldLimit + initial;
      updateCollections();
      if (button.hidden) {
        var next = controls.querySelector('button:not([hidden])');
        if (next) next.focus({ preventScroll: true });
      }
      if (action === 'less') container.scrollIntoView({ block: 'start' });
    });
  });
  window.addEventListener('hashchange', openHashSection);
  document.querySelectorAll('a[href^="#"]').forEach(function (link) {
    link.addEventListener('click', function () {
      if (link.hash === location.hash) openHashSection();
    });
  });
  if (location.hash) openHashSection();
  document.addEventListener('click', async function (event) {
    var button = event.target.closest('.copy-update');
    if (!button) return;
    var menu = button.closest('.card-share');
    var status = menu.querySelector('.card-share-status');
    try {
      await navigator.clipboard.writeText(button.dataset.url);
      status.textContent = 'Update link copied.';
    } catch (_) {
      var input = menu.querySelector('.card-share-url');
      input.hidden = false;
      input.focus();
      input.select();
      status.textContent = 'Select and copy this update link.';
    }
  });
  var printState;
  window.addEventListener('beforeprint', function () {
    printState = { limits: Object.assign({}, collectionLimits), panels: [] };
    document.querySelectorAll('details').forEach(function (panel) {
      printState.panels.push([panel, panel.open]);
      panel.open = true;
    });
    document.querySelectorAll('[data-collection]').forEach(function (container) { collectionLimits[container.id] = Infinity; });
    updateCollections();
  });
  window.addEventListener('afterprint', function () {
    if (!printState) return;
    collectionLimits = printState.limits;
    printState.panels.forEach(function (entry) { entry[0].open = entry[1]; });
    updateCollections();
  });
}

function applyRendered(p) {
  var openStatNotes = Array.from(document.querySelectorAll('#stats .stat')).filter(function (card) {
    var note = card.querySelector('.stat-note');
    return note && note.open;
  }).map(function (card) { return card.querySelector('h3').textContent; });
  var h1 = document.querySelector("header h1");
  var subtitle = document.querySelector("header .subtitle");
  var time = document.querySelector(".updated time");
  var map = {
    stats: p.stats,
    pictures: p.pictures,
    pins: p.pins,
    feed: p.feed,
    lede: p.lede,
    people: p.people,
    "joined-list": p.joined,
    "courts-col": p.courts,
    "allegations-list": p.allegations,
    "govt-list": p.govt,
    "legal-list": p.legal,
    "caveats-list": p.caveats,
    "source-list": p.sources
  };
  if (!h1 || !subtitle || !time || !document.getElementById("courts-col")) return;
  var key;
  for (key in map) if (!Object.prototype.hasOwnProperty.call(map, key) || !document.getElementById(key)) return;
  document.title = p.title;
  h1.innerHTML = p.titleHtml;
  subtitle.innerHTML = p.subtitleHtml;
  time.innerHTML = p.updatedHtml;
  for (key in map) if (Object.prototype.hasOwnProperty.call(map, key)) document.getElementById(key).innerHTML = map[key];
  document.querySelectorAll('#stats .stat').forEach(function (card) {
    if (openStatNotes.includes(card.querySelector('h3').textContent)) card.querySelector('.stat-note').open = true;
  });
  updateCollections();
  syncScrollPadding();
  if (location.hash.indexOf('#update-') === 0) openHashSection(lastOpenedHash !== location.hash);
  document.documentElement.setAttribute("data-live", "1");
}

var lastLivePayload = null;
function loadLiveData() {
  var url = "https://raw.githubusercontent.com/skshoyeb/jantarmantar/main/data.json?t=" + Date.now();
  fetch(url, { cache: "no-store" })
    .then(function (res) {
      if (!res.ok) throw new Error("HTTP " + res.status);
      return res.json();
    })
    .then(function (data) {
      var payload = JSON.stringify(data);
      if (payload === lastLivePayload) return;
      applyRendered(renderParts(data));
      lastLivePayload = payload;
    })
    .catch(function () {});
}

if (typeof document !== "undefined" && document.getElementById && document.getElementById("stats")) {
  initCollections();
  loadLiveData();
  setInterval(loadLiveData, 5 * 60 * 1000);
}
'''

LIVE_JS = LIVE_JS.replace('__SOURCE_LABELS__', json.dumps(SOURCE_LABELS, ensure_ascii=False))

page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(d["title"])}</title>
<meta name="description" content="{e(DESCRIPTION)}">
<meta name="robots" content="index,follow,max-image-preview:large">
<meta name="theme-color" content="#101719">
<link rel="canonical" href="{e(SITE_URL)}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{e(SITE_NAME)}">
<meta property="og:locale" content="en_IN">
<meta property="og:title" content="{e(d['title'])}">
<meta property="og:description" content="{e(DESCRIPTION)}">
<meta property="og:url" content="{e(SITE_URL)}">
<meta property="og:image" content="{e(SOCIAL_IMAGE)}">
<meta property="og:image:secure_url" content="{e(SOCIAL_IMAGE)}">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{e(SOCIAL_IMAGE_ALT)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(d['title'])}">
<meta name="twitter:description" content="{e(DESCRIPTION)}">
<meta name="twitter:image" content="{e(SOCIAL_IMAGE)}">
<meta name="twitter:image:alt" content="{e(SOCIAL_IMAGE_ALT)}">
<script type="application/ld+json">{structured_data}</script>
<style>{CSS}</style></head><body id="page-top">
<input id="light" class="sr" type="checkbox" aria-label="Switch to light mode">
<header class="bar"><div class="brand"><img class="brand-mark" src="/jantar-mantar-logo.png" alt="" width="58" height="58" decoding="async"><div class="brand-copy"><h1>{e(header_title)}</h1><p class="subtitle">{e(header_subtitle)}</p></div></div>
<div class="status-row"><span class="live"><span class="dot" aria-hidden="true"></span>Live</span><p class="updated">Last updated <time>{e(d["last_updated_ist"])}</time></p></div>
<label class="theme" for="light"><span class="off">Light</span><span class="on">Dark</span></label>
<nav class="section-nav" aria-label="Page sections">
<a href="#at-a-glance">At a glance</a><a href="#site-footer">Footer</a><a href="#pictures-heading">Pictures</a><a href="#highlights">Highlights</a><a href="#live-updates">Live updates</a><a href="#background">Background</a><a href="#detainees">Detainees</a><a href="#supporters">Supporters</a><a href="#courts">Courts</a><a href="#allegations">Allegations</a><a href="#government">Government</a><a href="#legal-context">Legal context</a><a href="#caveats">Caveats</a><a href="#sources">Sources</a>
</nav></header>
<main class="wrap">
<div class="disclaimer"><strong>Disclaimer:</strong> This data is auto-generated by a Grok bot. The bot compiled this dashboard while publishing the site, from news reports, official statements, and labelled social-media posts. It is not an official record and has not been checked by a human editor. Names, counts, times, and detention status can be incomplete or wrong. Check the linked sources before relying on it.</div>
<h2 id="at-a-glance">At a glance</h2>
<div class="stats" id="stats">{stats}</div>
<h2 id="pictures-heading">In pictures</h2>
<p class="section-note">Previews from linked reports. Images may show earlier or related events.</p>
<div class="pictures" id="pictures" data-collection="3">{pictures}</div>
<div class="collection-controls" data-controls="pictures" hidden><span class="collection-count"></span><button type="button" data-action="more" aria-controls="pictures">Show more</button><button type="button" data-action="all" aria-controls="pictures">Show all</button><button type="button" data-action="less" aria-controls="pictures" hidden>Show less</button></div>
<h2 id="highlights">Very important</h2>
<p class="section-note">Key leader detentions, pinned newest first. Each one is also in the feed below.</p>
<div class="top" id="pins" data-collection="4">{pins}</div>
<div class="collection-controls" data-controls="pins" hidden><span class="collection-count"></span><button type="button" data-action="more" aria-controls="pins">Show more</button><button type="button" data-action="all" aria-controls="pins">Show all</button><button type="button" data-action="less" aria-controls="pins" hidden>Show less</button></div>
<h2 id="live-updates">Live updates</h2>
<p class="section-note">Newest first. Times are IST.</p>
<div class="feed" id="feed" data-collection="10">{feed}</div>
<div class="collection-controls" data-controls="feed" hidden><span class="collection-count"></span><button type="button" data-action="more" aria-controls="feed">Show more</button><button type="button" data-action="all" aria-controls="feed">Show all</button><button type="button" data-action="less" aria-controls="feed" hidden>Show less</button></div>
<details class="section-fold"><summary><h2 id="background">Background</h2></summary>
<p class="lede" id="lede">{e(d["summary"])}</p></details>
<h2 id="detainees">Key people detained</h2>
<p class="section-note">Status chip, then the recorded time and place.</p>
<div class="people" id="people" data-collection="6">{people}</div>
<div class="collection-controls" data-controls="people" hidden><span class="collection-count"></span><button type="button" data-action="more" aria-controls="people">Show more</button><button type="button" data-action="all" aria-controls="people">Show all</button><button type="button" data-action="less" aria-controls="people" hidden>Show less</button></div>
<div class="two"><div><details class="section-fold"><summary><h2 id="supporters">Notable people who joined / backed it</h2></summary><div class="box"><ul id="joined-list">{joined}</ul></div></details></div>
<div><details class="section-fold"><summary><h2 id="courts">Court updates</h2></summary><div id="courts-col">{courts}</div></details></div></div>
<details class="section-fold"><summary><h2 id="allegations">Alleged govt failures &amp; rules broken <small>(these are allegations, not findings)</small></h2></summary><div class="box"><ul id="allegations-list">{allegations}</ul></div></details>
<div class="two"><div><details class="section-fold"><summary><h2 id="government">Government / police position</h2></summary><div class="box"><ul id="govt-list">{govt}</ul></div></details></div>
<div><details class="section-fold"><summary><h2 id="legal-context">Legal context (reference)</h2></summary><div class="box"><ul id="legal-list">{legal}</ul></div></details></div></div>
<details class="section-fold"><summary><h2 id="caveats">Caveats</h2></summary><div class="box"><ul id="caveats-list">{caveats}</ul></div></details>
<details class="section-fold"><summary><h2 id="sources">Sources</h2></summary><div class="box"><ul class="sources" id="source-list">{sources}</ul></div></details>
<section class="share-panel" aria-labelledby="share-heading">
<h2 id="share-heading">Share this dashboard</h2>
<p class="section-note">Bot-compiled updates. Please verify reports with the linked sources.</p>
<div class="share-actions">
<a href="{e(share_x)}" target="_blank" rel="noopener noreferrer" aria-label="Share on X (opens a new tab)">Share on X</a>
<a href="{e(share_whatsapp)}" target="_blank" rel="noopener noreferrer" aria-label="Share on WhatsApp (opens a new tab)">WhatsApp</a>
<a href="{e(share_facebook)}" target="_blank" rel="noopener noreferrer" aria-label="Share on Facebook (opens a new tab)">Facebook</a>
<button type="button" id="copy-link" hidden>Copy link</button>
</div>
<input class="share-url" id="share-url" type="url" value="{e(SITE_URL)}" readonly aria-label="Dashboard link to copy">
<p class="share-status" id="share-status" role="status" aria-live="polite"></p>
</section>
<footer id="site-footer">Updates compiled by Grok Bot from news reports, official statements and labelled social-media posts. Not an official record. Verify reports with the linked sources.<span class="footer-credit">&copy; 2026 Sholock. Source images belong to their respective owners.</span></footer>
</main><nav class="page-shortcuts" aria-label="Page shortcuts"><a href="#page-top">Back to top</a><a href="#site-footer">Footer</a></nav>
<script>
const copyButton = document.getElementById('copy-link');
const shareUrl = document.getElementById('share-url');
const shareStatus = document.getElementById('share-status');
copyButton.hidden = false;
shareUrl.hidden = true;
copyButton.addEventListener('click', async () => {{
  try {{
    await navigator.clipboard.writeText(shareUrl.value);
    shareStatus.textContent = 'Link copied.';
  }} catch {{
    shareUrl.hidden = false;
    shareUrl.focus();
    shareUrl.select();
    shareStatus.textContent = 'Select and copy the link below.';
  }}
}});
</script>
<script id="live-data">
{LIVE_JS}
</script></body></html>'''

open(os.path.join(ROOT, 'index.html'), 'w').write(page)
open(os.path.join(ROOT, 'robots.txt'), 'w').write('User-agent: *\nAllow: /\n\nSitemap: ' + SITE_URL + 'sitemap.xml\n')
lastmod = f'<lastmod>{e(updated_iso)}</lastmod>' if updated_iso else ''
open(os.path.join(ROOT, 'sitemap.xml'), 'w').write(
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    f'<url><loc>{e(SITE_URL)}</loc>{lastmod}</url></urlset>\n'
)
print('built', len(ordered), 'updates;', len(top), 'pinned')
