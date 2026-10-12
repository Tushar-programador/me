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


class SkillsEducationChecks(unittest.TestCase):
    def test_skill_tracks(self):
        self.assertIn('id="skills"', HTML)
        self.assertEqual(len(re.findall(r'<div class="track (?:bk|cl) reveal">', HTML)), 2)

    def test_key_skills_present(self):
        for s in ("Go", "Node.js", "NestJS", "TypeScript", "Socket.IO", "BullMQ", "MongoDB", "PostgreSQL", "Redis",
                  "AWS", "Docker", "Kubernetes", "Helm", "Terraform", "GitHub Actions", "Nginx", "Prometheus",
                  "Grafana", "OpenTelemetry", "CloudWatch", "System Design", "Microservices"):
            self.assertRegex(HTML, r"<li>%s</li>" % re.escape(s))

    def test_education(self):
        self.assertIn('id="education"', HTML)
        self.assertIn("Kurukshetra University", HTML)
        self.assertIn("2022 – 2025", HTML)


class ProjectChecks(unittest.TestCase):
    def test_five_projects_in_order(self):
        names = re.findall(r'<article class="proj[^"]*">.*?<h3>(.*?)</h3>', HTML, re.S)
        self.assertEqual(
            [re.sub(r"<.*?>", "", n).strip() for n in names],
            ["Production Cloud Deployment &amp; CI/CD Platform", "Production Reliability Platform",
             "ICMS", "Relook", "Outdraw"],
        )

    def test_personal_projects_tagged_and_linked(self):
        self.assertEqual(HTML.count("Personal project"), 2)
        self.assertIn("https://github.com/Tushar-programador/relook", P.hrefs)
        self.assertIn("https://github.com/Tushar-programador/outdraw", P.hrefs)

    def test_icms_has_no_percentage(self):
        icms = re.search(r'<article class="proj[^"]*">(?:(?!</article>).)*?<h3>ICMS</h3>.*?</article>', HTML, re.S).group(0)
        self.assertNotIn("%", icms)

    def test_track_colour_bullets_do_not_leak_into_project_cards(self):
        # .cl/.bk bullet colouring must stay scoped to the experience columns (.cols)
        self.assertIsNone(re.search(r"(^|\n)\.(?:cl|bk) li::before", CSS))

    def test_reliability_platform_mentions_go_and_k8s(self):
        card = re.search(r"<h3>Production Reliability Platform</h3>.*?</article>", HTML, re.S).group(0)
        for s in ("Go", "Kubernetes", "Terraform", "OpenTelemetry"):
            self.assertIn(s, card)


class ContactSeoChecks(unittest.TestCase):
    def test_contact_details(self):
        self.assertIn('id="contact"', HTML)
        for href in ("mailto:tusharkalra307@gmail.com", "tel:+917206405935",
                     "https://www.linkedin.com/in/tushar-kalra-developer/",
                     "https://github.com/Tushar-programador",
                     "https://tushar-programador.github.io/me/"):
            self.assertIn(href, P.hrefs)

    def test_open_to_roles(self):
        for role in ("Backend Engineer", "Software Engineer", "Cloud / DevOps Engineer", "Platform Engineer"):
            self.assertIn(role, HTML)

    def test_jsonld_person(self):
        data = json.loads("".join(P.jsonld))
        self.assertEqual(data["@type"], "Person")
        self.assertEqual(data["name"], "Tushar Kalra")
        self.assertIn("https://github.com/Tushar-programador", data["sameAs"])

    def test_no_leftover_markers(self):
        for m in ("<!--@", "@css-end", "@js-end"):
            self.assertNotIn(m, HTML)

    def test_no_solar_system_remnants(self):
        for s in ("three.min.js", "anime.min.js", "bg-canvas", "THREE."):
            self.assertNotIn(s, HTML)


class FinalReviewChecks(unittest.TestCase):
    def test_pipeline_stacks_before_labels_wrap(self):
        # at 6 columns "Kubernetes" needs ~82px; below ~860px nodes are too narrow and the word breaks
        m = re.search(r"@media\(max-width:(\d+)px\)\{\s*\.pipe\{grid-template-columns:1fr", CSS.replace(" ", ""))
        self.assertIsNotNone(m, "no single-column pipeline media query")
        self.assertGreaterEqual(int(m.group(1)), 860)

    def test_every_section_has_a_heading(self):
        for sid, body in re.findall(r'<section id="(\w+)">(.*?)</section>', HTML, re.S):
            self.assertRegex(body, r"<h[12][ >]", f"section #{sid} has no heading")

    def test_about_does_not_overclaim(self):
        # resume says Vervebot work "supported" deployment; K8s/Terraform come from projects only
        self.assertNotIn("I own", HTML)

    def test_reduced_motion_block_disables_animation(self):
        block = re.search(r"@media\(prefers-reduced-motion:reduce\)\{(.*?)\n\}", CSS.replace(" ", ""), re.S).group(1)
        self.assertIn("animation:none", block)
        self.assertIn("transition:none", block)

    def test_wrap_rule_is_on_body(self):
        self.assertRegex(CSS.replace(" ", ""), r"body\{[^}]*overflow-wrap:anywhere")

    def test_hero_h1_contains_role(self):
        h1 = re.search(r"<h1>(.*?)</h1>", HTML, re.S).group(1)
        self.assertIn("Tushar Kalra", h1)
        self.assertRegex(h1, r'<b class="amb">Backend</b>.*<b class="cy">Cloud</b> Engineer')

    def test_track_bullet_rules_are_scoped(self):
        for sel in re.findall(r"([^{}]+)\{", CSS):
            if re.search(r"\.(?:cl|bk)\s+li::before", sel):
                self.assertIn(".cols", sel, f"unscoped bullet rule: {sel.strip()}")

    def test_reveal_not_hidden_by_other_means(self):
        flat = CSS.replace(" ", "")
        self.assertNotIn(".reveal:not(.in)", flat)
        self.assertIsNone(re.search(r"(?<!html\.js)\.reveal[^{}]*\{[^}]*visibility:hidden", flat))


if __name__ == "__main__":
    unittest.main()
