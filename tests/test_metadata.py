"""Validate crawler output and safe bot-data interpolation without extra packages."""
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SITE = 'https://jantarmantar.sholock.com/'


class HeadParser(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.meta = {}
        self.canonical = []
        self.structured = []
        self.sharing = []
        self.in_json = False
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'meta':
            key = a.get('name', a.get('property'))
            if key in self.meta:
                raise AssertionError('Duplicate metadata: ' + str(key))
            self.meta[key] = a.get('content')
        if tag == 'link' and a.get('rel') == 'canonical':
            self.canonical.append(a['href'])
        if tag == 'script':
            self.in_json = a.get('type') == 'application/ld+json'
        if tag == 'a' and a.get('href', '').startswith('https://twitter.com/intent/tweet?'):
            self.sharing.append(a['href'])

    def handle_endtag(self, tag):
        if tag == 'script':
            self.in_json = False

    def handle_data(self, data):
        if self.in_json:
            self.structured.append(data)


class MetadataTests(unittest.TestCase):
    def build(self, data=None):
        if data is None:
            data = json.loads((ROOT / 'data.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            shutil.copy2(ROOT / 'build.py', tmp / 'build.py')
            (tmp / 'data.json').write_text(json.dumps(data))
            subprocess.run([sys.executable, 'build.py'], cwd=tmp, check=True, capture_output=True)
            return {name: (tmp / name).read_text() for name in ['index.html', 'sitemap.xml', 'robots.txt']}

    def test_search_and_social_metadata(self):
        p = HeadParser(self.build()['index.html'])
        self.assertEqual(p.canonical, [SITE])
        self.assertEqual(p.meta['og:url'], SITE)
        self.assertEqual(p.meta['og:type'], 'website')
        self.assertEqual(p.meta['twitter:card'], 'summary_large_image')
        self.assertEqual(p.meta['twitter:title'], p.meta['og:title'])
        self.assertEqual(p.meta['twitter:description'], p.meta['description'])
        self.assertEqual(p.meta['og:image'], SITE + 'social-preview.png')
        self.assertEqual(p.meta['twitter:image'], p.meta['og:image'])
        self.assertTrue(p.meta['og:image:alt'])
        self.assertEqual((p.meta['og:image:width'], p.meta['og:image:height']), ('1200', '630'))

    def test_update_time_comes_from_bot_data(self):
        data = json.loads((ROOT / 'data.json').read_text())
        data['last_updated_ist'] = '10 Oct 2026, 4:37 PM IST'
        result = self.build(data)
        graph = json.loads(''.join(HeadParser(result['index.html']).structured))['@graph']
        self.assertEqual(graph[1]['dateModified'], '2026-10-10T16:37:00+05:30')
        xml = ET.fromstring(result['sitemap.xml'])
        ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        self.assertEqual(xml.find('s:url/s:loc', ns).text, SITE)
        self.assertEqual(xml.find('s:url/s:lastmod', ns).text, graph[1]['dateModified'])
        self.assertIn('Sitemap: ' + SITE + 'sitemap.xml', result['robots.txt'])

    def test_unknown_time_is_omitted_instead_of_fabricated(self):
        data = json.loads((ROOT / 'data.json').read_text())
        data['last_updated_ist'] = 'Awaiting update'
        result = self.build(data)
        graph = json.loads(''.join(HeadParser(result['index.html']).structured))['@graph']
        self.assertNotIn('dateModified', graph[1])
        self.assertNotIn('<lastmod>', result['sitemap.xml'])

    def test_title_is_safe_and_share_parameters_round_trip(self):
        data = json.loads((ROOT / 'data.json').read_text())
        data['title'] = 'Delhi "updates" & </script><script>alert(1)</script> #news'
        result = self.build(data)['index.html']
        p = HeadParser(result)
        graph = json.loads(''.join(p.structured))['@graph']
        self.assertEqual(graph[1]['name'], data['title'])
        self.assertEqual(p.meta['og:title'], data['title'])
        self.assertNotIn('</script><script>alert(1)</script>', result)
        params = parse_qs(urlparse(p.sharing[0]).query)
        self.assertEqual(params['url'], [SITE])
        self.assertTrue(params['text'][0].startswith(data['title']))

    def test_preview_asset_has_declared_dimensions(self):
        image = (ROOT / 'social-preview.png').read_bytes()
        self.assertEqual(image[:8], b'\x89PNG\r\n\x1a\n')
        self.assertEqual(struct.unpack('>II', image[16:24]), (1200, 630))
        ET.parse(ROOT / 'favicon.svg')

    def test_build_is_repeatable(self):
        self.assertEqual(self.build(), self.build())


if __name__ == '__main__':
    unittest.main()
