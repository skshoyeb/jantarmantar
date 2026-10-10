"""Browser checks for progressive disclosure and live refresh integration.

Requires Python Playwright and Chromium. Remote images and live data are mocked;
these tests never depend on third-party news hosts or modify the repository data.
"""
import copy
import functools
import http.server
import json
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.parse import urlparse, parse_qs

try:
    from playwright.sync_api import sync_playwright, expect
except ImportError:
    sync_playwright = None

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@unittest.skipIf(sync_playwright is None, 'Python Playwright is required for browser checks')
class CompactUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        tmp = Path(cls.tmp.name)
        for name in ['build.py', 'data.json']:
            shutil.copy2(ROOT / name, tmp / name)
        subprocess.run([sys.executable, 'build.py'], cwd=tmp, check=True, capture_output=True)
        handler = functools.partial(QuietHandler, directory=str(tmp))
        cls.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'
        cls.data = json.loads((ROOT / 'data.json').read_text())
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(executable_path=shutil.which('chromium') or None)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def setUp(self):
        self.context = self.browser.new_context(reduced_motion='reduce')
        self.context.route('https://raw.githubusercontent.com/**', lambda route: route.fulfill(json=self.data))
        # Serve a local test image to exercise layout without hotlinking news hosts.
        preview = (ROOT / 'social-preview.png').read_bytes()
        self.context.route('**/*', lambda route: route.fallback() if route.request.resource_type != 'image'
                           else route.fulfill(body=preview, content_type='image/png'))
        self.page = self.context.new_page()
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [])

    def load(self, hash=''):
        self.page.goto(self.base + '/' + hash)
        expect(self.page.locator('html')).to_have_attribute('data-live', '1')

    def test_disclosure_and_layout_in_both_themes(self):
        for width in [1440, 768, 390, 320]:
            with self.subTest(width=width):
                self.page.set_viewport_size({'width': width, 'height': 900})
                self.load()
                self.assertEqual(self.page.locator('.disclaimer').count(), 0)
                self.assertEqual(self.page.locator('.section-nav a[href="#site-footer"]').count(), 0)
                self.assertTrue(self.page.locator('.section-nav a').evaluate_all('''links =>
                  links.every((link, index) => index === 0 ||
                    !!(document.getElementById(links[index - 1].hash.slice(1)).compareDocumentPosition(
                      document.getElementById(link.hash.slice(1))) & Node.DOCUMENT_POSITION_FOLLOWING))
                '''))
                for light in [False, True]:
                    if self.page.locator('#light').is_checked() != light:
                        self.page.locator('.theme').click()
                    self.assertEqual(self.page.locator('#feed>.item').count(), len(self.data['timeline']))
                    self.assertEqual(self.page.locator('#feed>.item:visible').count(), min(10, len(self.data['timeline'])))
                    self.assertLessEqual(self.page.locator('#pins>.pin:visible').count(), 4)
                    self.assertLessEqual(self.page.locator('#people>.person:visible').count(), 6)
                    self.assertLessEqual(self.page.locator('#pictures>.photo-card:visible').count(), 3)
                    self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                    controls = self.page.locator('[data-controls="feed"]')
                    controls.locator('[data-action="more"]').click()
                    self.assertEqual(self.page.locator('#feed>.item:visible').count(), min(20, len(self.data['timeline'])))
                    controls.locator('[data-action="all"]').click()
                    self.assertEqual(self.page.locator('#feed>.item:visible').count(), len(self.data['timeline']))
                    controls.locator('[data-action="less"]').click()
                    self.assertEqual(self.page.locator('#feed>.item:visible').count(), min(10, len(self.data['timeline'])))
                self.page.locator('.page-shortcuts a[href="#site-footer"]').click()
                expect(self.page.locator('footer')).to_be_in_viewport()
                self.assertIn('2026 Sholock', self.page.locator('footer').inner_text())
                self.assertNotIn('data.json', self.page.locator('footer').inner_text())

    def test_live_refresh_keeps_expansion_and_reference_panels(self):
        self.load()
        self.page.locator('#stats .stat-note summary').first.click()
        self.page.locator('[data-controls="feed"] [data-action="all"]').click()
        self.page.locator('[data-controls="people"] [data-action="more"]').click()
        self.page.locator('.section-nav a[href="#sources"]').click()
        self.assertTrue(self.page.locator('#sources').evaluate('(el)=>el.closest("details").open'))
        updated = copy.deepcopy(self.data)
        updated['title'] = 'Jantar Mantar 2.0 — Updated protest context, Delhi'
        updated['timeline'].append({'t': '10 Oct, 11:59 PM', 'e': 'Test live addition', 'importance': 'breaking', 'src': []})
        self.context.route('https://raw.githubusercontent.com/**', lambda route: route.fulfill(json=updated))
        self.page.evaluate('loadLiveData()')
        expect(self.page.locator('#feed>.item:visible')).to_have_count(len(updated['timeline']))
        self.assertEqual(self.page.locator('#feed>.item:visible').count(), len(updated['timeline']))
        self.assertEqual(self.page.locator('#people>.person:visible').count(), min(12, len(updated['detainees'])))
        self.assertTrue(self.page.locator('#sources').evaluate('(el)=>el.closest("details").open'))
        self.assertIn('Test live addition', self.page.locator('#feed').inner_text())
        expect(self.page.locator('header h1')).to_have_text('Jantar Mantar 2.0')
        expect(self.page.locator('header .subtitle')).to_have_text('Updated protest context, Delhi')
        self.assertEqual(self.page.locator('.status-row .live').count(), 1)
        self.assertTrue(self.page.locator('#stats .stat-note').first.evaluate('(el)=>el.open'))

    def test_deep_links_and_keyboard_open_collapsed_sections(self):
        self.load('#legal-context')
        heading = self.page.locator('#legal-context')
        self.assertTrue(heading.evaluate('(el)=>el.closest("details").open'))
        summary = self.page.locator('#sources').locator('..')
        summary.focus()
        self.page.keyboard.press('Enter')
        self.assertTrue(self.page.locator('#sources').evaluate('(el)=>el.closest("details").open'))
        summary.focus()
        self.page.keyboard.press('Enter')
        self.assertFalse(self.page.locator('#sources').evaluate('(el)=>el.closest("details").open'))
        self.page.locator('.section-nav a[href="#sources"]').click()
        self.assertTrue(self.page.locator('#sources').evaluate('(el)=>el.closest("details").open'))
        box = self.page.locator('#sources').bounding_box()
        self.assertGreaterEqual(box['y'], self.page.locator('.bar').bounding_box()['height'] - 1)

    def test_no_javascript_retains_every_record_and_native_panels(self):
        context = self.browser.new_context(java_script_enabled=False)
        try:
            context.route('**/*', lambda r: r.abort() if r.request.resource_type == 'image' else r.continue_())
            page = context.new_page()
            page.goto(self.base)
            self.assertEqual(page.locator('#feed>.item:visible').count(), len(self.data['timeline']))
            self.assertEqual(page.locator('#people>.person:visible').count(), len(self.data['detainees']))
            page.locator('#sources').locator('..').click()
            self.assertEqual(page.locator('#source-list>li:visible').count(), len(self.data['sources']))
        finally:
            context.close()

    def test_failed_images_and_print_keep_content_accessible(self):
        self.context.route('**/*', lambda r: r.abort() if r.request.resource_type == 'image' else r.fallback())
        self.load()
        self.assertGreater(self.page.locator('#feed>.item:visible').count(), 0)
        self.page.evaluate('window.dispatchEvent(new Event("beforeprint"))')
        self.assertEqual(self.page.locator('#feed>.item:visible').count(), len(self.data['timeline']))
        self.assertEqual(self.page.locator('#source-list>li:visible').count(), len(self.data['sources']))
        self.page.evaluate('window.dispatchEvent(new Event("afterprint"))')
        self.assertEqual(self.page.locator('#feed>.item:visible').count(), min(10, len(self.data['timeline'])))
        self.assertFalse(self.page.locator('#sources').evaluate('(el)=>el.closest("details").open'))

    def test_individual_update_sharing_and_reference_badges(self):
        self.context.grant_permissions(['clipboard-read', 'clipboard-write'], origin=self.base)
        self.load()
        ids = self.page.locator('[id]').evaluate_all('(els)=>els.map(el=>el.id)')
        self.assertEqual(len(ids), len(set(ids)))
        for width in [1440, 390, 320]:
            self.page.set_viewport_size({'width': width, 'height': 900})
            card = self.page.locator('#feed>.item').first
            menu = card.locator('.card-share')
            if not menu.evaluate('(el)=>el.open'):
                menu.locator('summary').click()
            url = menu.locator('.update-permalink').get_attribute('href')
            self.assertEqual(url, 'https://jantarmantar.sholock.com/#' + card.get_attribute('id'))
            share_urls = menu.locator('.card-share-options a').evaluate_all('(els)=>els.map(el=>el.href)')
            self.assertEqual(parse_qs(urlparse(share_urls[0]).query)['url'], [url])
            self.assertTrue(parse_qs(urlparse(share_urls[1]).query)['text'][0].endswith(url))
            self.assertEqual(parse_qs(urlparse(share_urls[2]).query)['u'], [url])
            menu.locator('.copy-update').click()
            expect(menu.locator('.card-share-status')).to_have_text('Update link copied.')
            self.assertEqual(self.page.evaluate('navigator.clipboard.readText()'), url)
            self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
        self.assertRegex(self.page.locator('#feed .src').first.inner_text(), r'^1 · .+')
        self.page.evaluate("Object.defineProperty(navigator, 'clipboard', {value: {writeText: async()=>{throw new Error('denied')}}, configurable: true})")
        menu.locator('.copy-update').click()
        expect(menu.locator('.card-share-url')).to_be_visible()
        self.assertEqual(menu.locator('.card-share-url').input_value(), url)

    def test_update_permalink_reveals_old_card_after_new_updates(self):
        self.load()
        target_id = self.page.locator('#feed>.item').nth(40).get_attribute('id')
        self.load('#' + target_id)
        target = self.page.locator('#' + target_id)
        expect(target).to_be_visible()
        expect(target).to_be_in_viewport()
        updated = copy.deepcopy(self.data)
        updated['timeline'].append({'t': '10 Oct, 11:59 PM', 'e': 'Inserted newer update', 'importance': 'routine', 'src': []})
        self.context.route('https://raw.githubusercontent.com/**', lambda route: route.fulfill(json=updated))
        self.page.evaluate('loadLiveData()')
        expect(self.page.locator('#feed>.item')).to_have_count(len(updated['timeline']))
        expect(target).to_be_visible()
        self.assertEqual(self.page.evaluate('location.hash'), '#' + target_id)

    def test_people_images_and_credits_do_not_overlap_metadata(self):
        for width in [1440, 1024, 768, 700, 390, 320]:
            for font_size in [16, 32]:
                with self.subTest(width=width, font_size=font_size):
                    self.page.set_viewport_size({'width': width, 'height': 900})
                    self.load()
                    self.page.add_style_tag(content=f'html{{font-size:{font_size}px}}')
                    self.page.locator('[data-controls="people"] [data-action="all"]').click()
                    result = self.page.locator('#people .person').evaluate_all('''cards => {
                      const collisions = [];
                      let checked = 0;
                      for (const card of cards) {
                        const figure = card.querySelector('figure:not([hidden])');
                        if (!figure) continue;
                        checked++;
                        const image = figure.getBoundingClientRect();
                        for (const text of card.querySelectorAll('.person-id,.who,.where,.detail,.reason,.srcs')) {
                          const box = text.getBoundingClientRect();
                          if (image.left < box.right - 1 && image.right > box.left + 1 &&
                              image.top < box.bottom - 1 && image.bottom > box.top + 1) {
                            collisions.push(card.querySelector('h3').textContent + ': ' + text.className);
                          }
                        }
                      }
                      return {checked, collisions};
                    }''')
                    self.assertGreater(result['checked'], 0)
                    self.assertEqual(result['collisions'], [])
                    self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= innerWidth'))

    def test_stat_context_uses_paragraphs_and_separate_sources(self):
        for width in [1440, 768, 390, 320]:
            with self.subTest(width=width):
                self.page.set_viewport_size({'width': width, 'height': 900})
                self.load()
                card = self.page.locator('#stats .stat').first
                card.locator('.stat-note summary').click()
                paragraphs = card.locator('.stat-context p').all_inner_texts()
                normalize = lambda text: re.sub(r'\s+', ' ', text).strip()
                self.assertEqual(normalize(' '.join(paragraphs)), normalize(self.data['stats'][0]['note']))
                self.assertGreater(len(paragraphs), 1)
                self.assertEqual(card.locator('.stat-context a').count(), 0)
                source_urls = card.locator('.stat-sources a').evaluate_all('(els)=>els.map(el=>el.getAttribute("href"))')
                expected = self.data['stats'][0]['src']
                self.assertEqual(source_urls, expected if isinstance(expected, list) else [expected])
                grid = self.page.locator('#stats').bounding_box()
                box = card.bounding_box()
                self.assertAlmostEqual(box['width'], grid['width'] - 2, delta=2)
                self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= innerWidth'))


if __name__ == '__main__':
    unittest.main()
