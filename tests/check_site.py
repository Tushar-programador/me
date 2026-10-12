import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = (ROOT / "index.html").read_text(encoding="utf-8")
CSS = "".join(re.findall(r"<style>(.*?)</style>", HTML, re.S))


class Collector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.hrefs, self.scripts, self.links = set(), [], [], []
        self.metas, self.jsonld, self.tags, self.blank_links = [], [], [], []
        self.title, self._in_title, self._in_ld = "", False, False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.append(tag)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "a":
            if "href" in a:
                self.hrefs.append(a["href"])
            if a.get("target") == "_blank":
                self.blank_links.append(a)
        if tag == "script":
            if "src" in a:
                self.scripts.append(a["src"])
            self._in_ld = a.get("type") == "application/ld+json"
        if tag == "link":
            self.links.append(a)
        if tag == "meta":
            self.metas.append(a)
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag == "script":
            self._in_ld = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._in_ld:
            self.jsonld.append(data)


P = Collector()
P.feed(HTML)


class BaseChecks(unittest.TestCase):
    def test_landmarks(self):
        for tag in ("header", "nav", "main", "footer"):
            self.assertIn(tag, P.tags)
        self.assertEqual(P.tags.count("h1"), 1)

    def test_title_and_description(self):
        self.assertIn("Backend", P.title)
        self.assertIn("Cloud", P.title)
        desc = next((m["content"] for m in P.metas if m.get("name") == "description"), "")
        self.assertTrue(70 <= len(desc) <= 200, f"description length {len(desc)}")

    def test_no_external_scripts(self):
        self.assertEqual(P.scripts, [])

    def test_only_google_fonts_stylesheets(self):
        for link in P.links:
            if link.get("rel") == "stylesheet":
                self.assertTrue(link["href"].startswith("https://fonts.googleapis.com/"))

    def test_anchors_resolve(self):
        for href in P.hrefs:
            if href.startswith("#") and href != "#":
                self.assertIn(href[1:], P.ids, f"dangling anchor {href}")

    def test_resume_link_and_file(self):
        self.assertIn("Tushar_Kalra_Resume.pdf", P.hrefs)
        self.assertTrue((ROOT / "Tushar_Kalra_Resume.pdf").exists())

    # Review Focus 1
    def test_content_visible_without_js(self):
        self.assertIn("html.js .reveal", CSS)
        self.assertIsNone(re.search(r"(?<!html\.js )\.reveal\s*\{[^}]*opacity\s*:\s*0", CSS))

    # Review Focus 2
    def test_reduced_motion_rule(self):
        self.assertIn("prefers-reduced-motion", CSS)

    # Review Focus 3
    def test_blank_links_have_rel(self):
        for a in P.blank_links:
            rel = a.get("rel", "")
            self.assertIn("noopener", rel)
            self.assertIn("noreferrer", rel)

    # Review Focus 5
    def test_long_strings_wrap(self):
        self.assertIn("overflow-wrap:anywhere", CSS.replace(" ", ""))


if __name__ == "__main__":
    unittest.main()
