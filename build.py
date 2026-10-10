import json, html, os
d = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data.json')))
e = lambda s: html.escape(str(s))
def src(u): 
    from urllib.parse import urlparse
    return f'<a class="src" href="{e(u)}" target="_blank" rel="noopener">{e(urlparse(u).netloc.replace("www.",""))}</a>'
def badge(s):
    l = s.lower()
    c = 'rel' if l.startswith('released') else ('held' if l.startswith('held') else 'unk')
    return f'<span class="b {c}">{e(s)}</span>'
stats = ''.join(f'<div class="card"><div class="v">{e(s["value"])}</div><div class="l">{e(s["label"])}</div><div class="n">{e(s["note"])} {src(s["src"])}</div></div>' for s in d['stats'])
rows = ''.join(f'<tr><td><b>{e(x["name"])}</b><div class="sub">{e(x["who"])}</div></td><td>{e(x["when"])}</td><td>{e(x["where"])}</td><td>{e(x["reason"])}</td><td>{badge(x["status"])}</td><td>{src(x["src"])}</td></tr>' for x in d['detainees'])
tl = ''.join(f'<li><span class="t">{e(x["t"])}</span><span>{e(x["e"])} {src(x["src"])}</span></li>' for x in d['timeline'])
jn = ''.join(f'<li><b>{e(x["name"])}</b> — {e(x["role"])}</li>' for x in d['joined'])
al = ''.join(f'<li>{e(x["claim"])} <span class="by">Alleged by: {e(x["by"])}</span> {src(x["src"])}</li>' for x in d['allegations'])
gp = ''.join(f'<li>{e(x["point"])} {src(x["src"])}</li>' for x in d['govt_position'])
lc = ''.join(f'<li>{e(x)}</li>' for x in d['legal_context'])
ct = ''.join(f'<div class="court"><div class="cd">{e(x["date"])} · {e(x["court"])}</div><div>{e(x["action"])} {src(x["src"])}</div></div>' for x in d['courts'])
cv = ''.join(f'<li>{e(x)}</li>' for x in d['caveats'])
so = ''.join(f'<li><a href="{e(u)}" target="_blank" rel="noopener">{e(u)}</a></li>' for u in d['sources'])
page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(d["title"])}</title><style>
:root{{--bg:#f6f7f9;--fg:#15181d;--mut:#5b6472;--card:#fff;--bd:#e3e6ea;--acc:#c0392b;--ok:#1e8e3e;--warn:#b26a00}}
@media(prefers-color-scheme:dark){{:root{{--bg:#0f1216;--fg:#e8eaed;--mut:#9aa3ad;--card:#181c22;--bd:#2a3038;--acc:#ff6b5b;--ok:#4cc26b;--warn:#f0a43a}}}}
*{{box-sizing:border-box}}body{{margin:0;font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--fg)}}
.wrap{{max-width:1180px;margin:auto;padding:18px}}header h1{{margin:0 0 4px;font-size:1.6rem}}.upd{{color:var(--acc);font-weight:600}}
.live{{display:inline-block;background:var(--acc);color:#fff;border-radius:4px;padding:1px 7px;font-size:.75rem;margin-right:6px;font-weight:700}}
.sum{{background:var(--card);border:1px solid var(--bd);border-left:4px solid var(--acc);border-radius:8px;padding:12px 14px;margin:12px 0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}}
.card{{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:14px}}.v{{font-size:1.9rem;font-weight:800;color:var(--acc)}}.l{{font-weight:600}}.n{{color:var(--mut);font-size:.82rem;margin-top:4px}}
h2{{margin:26px 0 10px;font-size:1.2rem;border-bottom:2px solid var(--bd);padding-bottom:4px}}
.tw{{overflow-x:auto;background:var(--card);border:1px solid var(--bd);border-radius:10px}}table{{border-collapse:collapse;width:100%;min-width:860px}}
th,td{{text-align:left;vertical-align:top;padding:9px 10px;border-bottom:1px solid var(--bd);font-size:.88rem}}th{{background:var(--bg);position:sticky;top:0}}.sub{{color:var(--mut);font-size:.8rem}}
.b{{display:inline-block;padding:2px 8px;border-radius:12px;font-size:.78rem;font-weight:600}}.held{{background:#c0392b22;color:var(--acc)}}.rel{{background:#1e8e3e22;color:var(--ok)}}.unk{{background:#b26a0022;color:var(--warn)}}
.src{{font-size:.75rem;color:var(--mut);white-space:nowrap}}.src:before{{content:"↗ "}}a{{color:inherit}}
ul.tl{{list-style:none;padding:0;margin:0;border-left:3px solid var(--acc);}}ul.tl li{{display:flex;gap:12px;padding:6px 0 6px 14px;position:relative}}ul.tl li:before{{content:"";position:absolute;left:-7px;top:12px;width:11px;height:11px;border-radius:50%;background:var(--acc)}}
.t{{min-width:150px;font-weight:700;font-size:.85rem}}.two{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}@media(max-width:760px){{.two{{grid-template-columns:1fr}}.t{{min-width:95px}}}}
.box{{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:10px 16px}}.box li{{margin:6px 0}}.by{{display:block;color:var(--warn);font-size:.8rem}}
.court{{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:10px 14px;margin-bottom:8px}}.cd{{font-weight:700;color:var(--acc);font-size:.85rem}}
.sources li{{word-break:break-all;font-size:.8rem}}footer{{color:var(--mut);font-size:.8rem;margin:24px 0}}
</style></head><body><div class="wrap">
<header><h1>{e(d["title"])}</h1><div><span class="live">LIVE</span><span class="upd">Last updated: {e(d["last_updated_ist"])}</span></div></header>
<div class="sum">{e(d["summary"])}</div>
<div class="grid">{stats}</div>
<h2>Key people detained</h2><div class="tw"><table><thead><tr><th>Name</th><th>When (IST)</th><th>Where</th><th>Stated reason</th><th>Status</th><th>Source</th></tr></thead><tbody>{rows}</tbody></table></div>
<h2>Timeline of major highlights</h2><div class="box"><ul class="tl">{tl}</ul></div>
<div class="two"><div><h2>Notable people who joined / backed it</h2><div class="box"><ul>{jn}</ul></div></div>
<div><h2>Court updates</h2>{ct}</div></div>
<h2>Alleged govt failures & rules broken <small style="color:var(--warn)">(these are allegations, not findings)</small></h2><div class="box"><ul>{al}</ul></div>
<div class="two"><div><h2>Government / police position</h2><div class="box"><ul>{gp}</ul></div></div>
<div><h2>Legal context (reference)</h2><div class="box"><ul>{lc}</ul></div></div></div>
<h2>Caveats</h2><div class="box"><ul>{cv}</ul></div>
<h2>Sources</h2><div class="box"><ul class="sources">{so}</ul></div>
<footer>Compiled from mainstream media, official statements and labelled social-media posts. To refresh: edit data.json, then run <code>python3 build.py</code>.</footer>
</div></body></html>'''
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html'),'w').write(page)
print('built')
