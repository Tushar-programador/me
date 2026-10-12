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


class HeroChecks(unittest.TestCase):
    def test_hero_headline(self):
        self.assertIn('id="hero"', HTML)
        self.assertIn("Backend", HTML)
        self.assertRegex(HTML, r"<h1>\s*Tushar Kalra")
        self.assertIn("Cloud</b> Engineer", HTML)

    # Review Focus 4
    def test_pipeline_nodes_focusable(self):
        nodes = re.findall(r'<li class="node" tabindex="0">(.*?)</li>', HTML, re.S)
        self.assertEqual(len(nodes), 6)
        for n in nodes:
            tip = re.search(r'<span class="tip">(.*?)</span>', n, re.S)
            self.assertTrue(tip and len(tip.group(1).strip()) > 10)

    def test_pipeline_stages_in_order(self):
        labels = re.findall(r'<span class="n-label">(.*?)</span>', HTML)
        self.assertEqual(labels, ["Code", "CI/CD", "Docker", "Kubernetes", "AWS", "Observe"])

    def test_reduced_motion_hides_packet(self):
        block = re.search(r"@media\(prefers-reduced-motion:reduce\)\{(.*?)\n\}", CSS.replace(" ", ""), re.S)
        self.assertIn(".pipe::after{display:none", block.group(1))


class AboutExperienceChecks(unittest.TestCase):
    def test_sections_exist(self):
        self.assertIn('id="about"', HTML)
        self.assertIn('id="experience"', HTML)

    def test_stats_exact(self):
        stats = re.findall(r'<div class="stat[^"]*"><b>(.*?)</b><span>(.*?)</span></div>', HTML)
        self.assertEqual(
            stats,
            [("2+", "Years of experience"), ("70+", "Production REST APIs"),
             ("70%", "Less manual data entry"), ("60%+", "Faster invoice processing")],
        )

    def test_experience_facts(self):
        for s in ("Vervebot.io", "07/2024", "Present", "GitHub Actions", "Nginx", "PM2", "BullMQ", "Textract"):
            self.assertIn(s, HTML)

    def test_experience_has_two_tracks(self):
        self.assertEqual(len(re.findall(r'<div class="(?:cl|bk)">', HTML)), 2)


if __name__ == "__main__":
    unittest.main()
