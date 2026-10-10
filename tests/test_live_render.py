"""The inline renderer must match the HTML build.py writes for the same data.json."""
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DISCLAIMER = (
    'Updates are compiled by Grok Bot from news reports, official statements and labelled social-media posts. '
    'This is not an official record and has not been reviewed by a human editor. Names, counts, times and detention '
    'status may be incomplete or incorrect; verify linked sources before relying on them.'
)

VIP_NAMES = (
    'dhruv rathee', 'abhijeet dipke', 'saurav das', 'ashutosh ranka', 'ratna singh',
    'neha bora', 'yogendra yadav', 'mamata banerjee', 'arvind kejriwal', 'manish sisodia',
    'pinarayi vijayan', 'john brittas',
    'k.n. balagopal', 'm.a. baby', 'brinda karat', 'manik sarkar', 'jitendra chaudhury',
    'elamaram kareem',
)


def inner_html(page, element_id):
    match = re.search(
        r'<([a-zA-Z0-9]+)\b[^>]*\bid="%s"[^>]*>' % re.escape(element_id),
        page,
    )
    if not match:
        raise AssertionError('missing id=' + element_id)
    tag = match.group(1)
    pos = match.end()
    depth = 1
    for token in re.finditer(r'<(/?)(%s)\b[^>]*>' % re.escape(tag), page[pos:], re.I):
        if token.group(1):
            depth -= 1
            if depth == 0:
                return page[pos:pos + token.start()]
        elif not token.group(0).endswith('/>'):
            depth += 1
    raise AssertionError('unclosed ' + element_id)


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
    return (int(day.group(1)) if day else 0, clock_minutes(item.get('t', '')), idx)


def chip(status):
    low = status.lower()
    if low.startswith('released'):
        return 'rel', 'Released'
    if low.startswith('held'):
        return 'held', 'Detained'
    return 'unk', 'Unknown'


def dom_signature(fragment):
    classes = []
    for tag, attrs in re.findall(r'<([a-zA-Z0-9]+)([^>]*)>', fragment):
        found = re.search(r'class="([^"]*)"', attrs)
        classes.append((tag.lower(), found.group(1) if found else ''))
    text = html.unescape(re.sub(r'<[^>]+>', ' ', fragment))
    text = re.sub(r'\s+', ' ', text).strip()
    return classes, text


class LiveRenderTests(unittest.TestCase):
    def test_unicode_update_sharing_matches_static_and_live(self):
        data = json.loads((ROOT / 'data.json').read_text())
        data['timeline'][0]['e'] = 'Quotes " & apostrophes\' emoji 🌏 हिन्दी ' + 'a' * 220
        data['timeline'][0]['src'] = ['https://example.com/a?x=1&y=2', 'https://www.thehindu.com/news/example']
        page, parts = self.build(data)
        self.assert_region('feed', inner_html(page, 'feed'), parts['feed'])
        self.assertIn('aria-label="Sources"', parts['feed'])
        self.assertIn('2 · The Hindu', parts['feed'])

    def build(self, data):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            shutil.copy2(ROOT / 'build.py', tmp / 'build.py')
            (tmp / 'data.json').write_text(json.dumps(data))
            subprocess.run([sys.executable, 'build.py'], cwd=tmp, check=True, capture_output=True, text=True)
            page = (tmp / 'index.html').read_text()
        script = re.search(r'<script id="live-data">([\s\S]*?)</script>', page)
        self.assertIsNotNone(script, 'live-data script missing')
        proc = subprocess.run(
            ['node', '-e', NODE],
            input=json.dumps({'html': page, 'data': data}),
            text=True,
            capture_output=True,
            check=True,
        )
        return page, json.loads(proc.stdout)

    def assert_region(self, label, static, rendered):
        if static == rendered:
            self.assertEqual(dom_signature(static), dom_signature(rendered))
            return
        n = 0
        limit = min(len(static), len(rendered))
        while n < limit and static[n] == rendered[n]:
            n += 1
        raise AssertionError(
            '%s mismatch at %s\nSTATIC: %r\nJS:     %r'
            % (label, n, static[max(0, n - 90):n + 90], rendered[max(0, n - 90):n + 90])
        )

    def test_js_matches_static_markup(self):
        data = json.loads((ROOT / 'data.json').read_text())
        page, parts = self.build(data)
        self.assertIn(DISCLAIMER, inner_html(page, 'site-footer'))
        self.assertNotIn('class="disclaimer"', page)
        self.assertIn('https://raw.githubusercontent.com/skshoyeb/jantarmantar/main/data.json?t=', page)
        self.assertIn('5 * 60 * 1000', page)
        self.assertIn('.catch(function () {})', page)

        h1 = re.search(r'<h1>(.*?)</h1>', page).group(1)
        updated = re.search(r'<p class="updated">Last updated <time>(.*?)</time>', page).group(1)
        self.assert_region('title', h1, parts['titleHtml'])
        subtitle = re.search(r'<p class="subtitle">(.*?)</p>', page).group(1)
        self.assert_region('subtitle', subtitle, parts['subtitleHtml'])
        self.assert_region('updated', updated, parts['updatedHtml'])
        self.assertEqual(parts['title'], data['title'])

        regions = {
            'stats': 'stats',
            'pictures': 'pictures',
            'pins': 'pins',
            'feed': 'feed',
            'lede': 'lede',
            'people': 'people',
            'joined': 'joined-list',
            'allegations': 'allegations-list',
            'govt': 'govt-list',
            'legal': 'legal-list',
            'caveats': 'caveats-list',
            'sources': 'source-list',
        }
        static = {name: inner_html(page, element_id) for name, element_id in regions.items()}
        courts = inner_html(page, 'courts-col')
        self.assertIn('<h2 id="courts">Court updates</h2>', page)
        static['courts'] = courts
        for name in list(regions) + ['courts']:
            self.assert_region(name, static[name], parts[name])

        self.assertEqual(
            [html.escape(person['name']) for person in data['detainees']],
            re.findall(r'<h3>(.*?)</h3>', static['people']),
        )
        articles = re.findall(r'<article class="(person(?: very-important)?)">(.*?)</article>', static['people'])
        self.assertEqual(len(articles), len(data['detainees']))
        for (cls, body), person in zip(articles, data['detainees']):
            vip = any(part in person['name'].lower() for part in VIP_NAMES)
            self.assertEqual('very-important' in cls, vip, person['name'])
            kind, label = chip(person['status'])
            self.assertIn('class="chip %s"' % kind, body, person['name'])
            self.assertIn('>%s</span>' % label, body, person['name'])

        ordered = [item for _, item in sorted(enumerate(data['timeline']), key=feed_sort_key, reverse=True)]
        self.assertEqual(
            [html.escape(item['t']) for item in ordered],
            re.findall(r'<time>(.*?)</time>', static['feed']),
        )
        pinned = [item for item in ordered if str(item.get('importance') or 'routine').lower() == 'very-important']
        self.assertEqual(
            [html.escape(item['t']) for item in pinned],
            re.findall(r'<time>(.*?)</time>', static['pins']),
        )
        for level in ('very-important', 'breaking', 'important', 'routine'):
            self.assertEqual(
                static['feed'].count('class="item %s"' % level),
                sum(1 for item in ordered if str(item.get('importance') or 'routine').lower() == level),
            )
        self.assertNotIn('class="pin breaking"', static['pins'])
        self.assertNotIn('class="pin important"', static['pins'])
        self.assertNotIn('class="pin routine"', static['pins'])
        self.assertEqual(static['lede'], html.escape(data['summary']))
        self.assertEqual(len(re.findall(r'<article class="stat"', static['stats'])), len(data['stats']))
        for stat in data['stats']:
            self.assertIn(html.escape(stat['value']), static['stats'])
            self.assertIn(html.escape(stat['label']), static['stats'])
        self.assertEqual(static['sources'].count('<li>'), len(data['sources']))
        self.assertEqual(static['caveats'].count('<li>'), len(data['caveats']))
        self.assertIn('class="sources"', page)
        self.assertIn(html.escape(data['sources'][0]), static['sources'])
        self.assertIn(html.escape(data['sources'][-1]), static['sources'])

        def with_image(rows):
            return sum(1 for row in rows if isinstance(row.get('image'), dict) and row['image'].get('url'))

        pinned = [item for item in data['timeline'] if str(item.get('importance') or '').lower() == 'very-important']
        self.assertEqual(static['pins'].count('<figure class="hero">'), with_image(pinned))
        self.assertEqual(static['feed'].count('<figure class="thumb">'), with_image(data['timeline']))
        self.assertEqual(static['people'].count('<figure class="thumb">'), with_image(data['detainees']))
        self.assertNotIn('<figure class="hero">', static['feed'])
        if with_image(data['timeline']):
            self.assertIn('loading="lazy"', static['feed'])
            self.assertIn('object-fit:cover', page)
            self.assertIn("onerror=\"this.closest('figure').hidden=true\"", static['feed'])
        expected_images = {
            row['image']['url'] for row in data['timeline'] + data['detainees']
            if isinstance(row.get('image'), dict) and row['image'].get('url')
        }
        self.assertEqual(static['pictures'].count('<article class="photo-card">'), len(expected_images))
        for url in expected_images:
            self.assertEqual(static['pictures'].count('src="' + html.escape(url) + '"'), 1)


NODE = r'''
const fs = require('fs');
const vm = require('vm');
let raw = '';
process.stdin.on('data', (c) => { raw += c; });
process.stdin.on('end', () => {
  const payload = JSON.parse(raw);
  const script = payload.html.match(/<script id="live-data">([\s\S]*?)<\/script>/);
  if (!script) throw new Error('missing live-data script');
  const context = {};
  vm.createContext(context);
  vm.runInContext(script[1], context);
  if (typeof context.renderParts !== 'function') throw new Error('renderParts missing');
  process.stdout.write(JSON.stringify(context.renderParts(payload.data)));
});
'''


if __name__ == '__main__':
    unittest.main()
