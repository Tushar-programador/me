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
        stats = re.findall(r'<div class="stat[^"]*"><b[^>]*>(.*?)</b><span>(.*?)</span></div>', HTML)
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
            self.assertRegex(HTML, r"<li>%s</li>|<span>%s</span></li>" % (re.escape(s), re.escape(s)))

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
        self.assertRegex(h1, r'<b class="be">Backend</b>.*<b class="cy">Cloud</b> Engineer')

    def test_track_bullet_rules_are_scoped(self):
        for sel in re.findall(r"([^{}]+)\{", CSS):
            if re.search(r"\.(?:cl|bk)\s+li::before", sel):
                self.assertIn(".cols", sel, f"unscoped bullet rule: {sel.strip()}")

    def test_reveal_not_hidden_by_other_means(self):
        flat = CSS.replace(" ", "")
        self.assertNotIn(".reveal:not(.in)", flat)
        self.assertIsNone(re.search(r"(?<!html\.js)\.reveal[^{}]*\{[^}]*visibility:hidden", flat))


def _lum(hexc):
    h = hexc.lstrip("#")
    r, g, b = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def _ratio(a, b):
    hi, lo = sorted((_lum(a), _lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _blend(bg, white_alpha):
    h = bg.lstrip("#")
    c = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    return "#%02x%02x%02x" % tuple(round(x * (1 - white_alpha) + 255 * white_alpha) for x in c)


def _token(name):
    return re.search(r"--%s:(#[0-9a-fA-F]{6})" % name, CSS).group(1)


class ThemeChecks(unittest.TestCase):
    def test_palette_tokens(self):
        flat = CSS.replace(" ", "")
        self.assertIn("--bg:#030014", flat)
        self.assertIn("--violet:", flat)
        for old in ("--amber", "#f5b041", "245,176,65", "#0a1424", "53,208,232"):
            self.assertNotIn(old, flat)

    def test_inter_font(self):
        fonts = next(l["href"] for l in P.links if l.get("rel") == "stylesheet")
        self.assertIn("family=Inter", fonts)
        self.assertNotIn("Space+Grotesk", fonts)
        self.assertIn("'Inter'", CSS)

    def test_particle_canvas(self):
        self.assertIn('<canvas id="stars" aria-hidden="true"></canvas>', HTML)
        self.assertRegex(CSS.replace(" ", ""), r"#stars\{[^}]*pointer-events:none")

    # Review Focus 2
    def test_particles_respect_reduced_motion_and_hidden_tab(self):
        js = re.search(r"getElementById\('stars'\)(.*?)\}\)\(\);", HTML, re.S).group(1)
        self.assertIn("prefers-reduced-motion", js)
        self.assertIn("document.hidden", js)

    def test_glass_fallback(self):
        self.assertIn("@supports not (backdrop-filter", CSS)

    def test_project_gradient_strip(self):
        self.assertIn(".proj::before", CSS.replace(" ", ""))

    def test_old_grid_removed(self):
        self.assertNotIn("background-size:48px", CSS.replace(" ", ""))

    # Review Focus 4
    def test_text_contrast(self):
        bg = _token("bg")
        surface = _blend(bg, 0.15)  # conservative: much lighter than the real 4.5% glass
        self.assertGreaterEqual(_ratio(_token("muted"), bg), 4.5)
        self.assertGreaterEqual(_ratio(_token("muted"), surface), 4.5)
        self.assertGreaterEqual(_ratio(_token("violet"), surface), 4.5)
        self.assertGreaterEqual(_ratio(_token("cyan"), surface), 4.5)


class HeroNavChecks(unittest.TestCase):
    def test_terminal_prompt_and_cursor(self):
        role = re.search(r'<span class="role">(.*?)</span>\s*</h1>', HTML, re.S).group(1)
        self.assertIn('<span class="prompt" aria-hidden="true">&gt;_</span>', role)
        self.assertIn('<span class="cursor" aria-hidden="true"></span>', role)

    def test_nav_icon_links(self):
        icons = re.findall(r'<a class="icon-link" href="([^"]+)" target="_blank" rel="noopener noreferrer" aria-label="([^"]+)">', HTML)
        self.assertEqual(icons, [("https://github.com/Tushar-programador", "GitHub"),
                                 ("https://www.linkedin.com/in/tushar-kalra-developer/", "LinkedIn")])

    def test_packet_dot_animates_transform_not_left(self):
        flat = CSS.replace(" ", "")
        block = re.search(r"@keyframesflow\{(.*?)\}\}", flat, re.S).group(1)
        self.assertIn("transform", block)
        self.assertNotIn("left", block)
        self.assertIn("88cqw", block)  # travel distance = 88% of the pipe (container-type on .pipe)
        self.assertIn("container-type:inline-size", flat)
        self.assertIn("animation:flow", flat)


class FlipCardChecks(unittest.TestCase):
    CARDS = re.findall(r'<button class="flip (?:bk|cl) reveal" type="button" aria-pressed="false">(.*?)</button>', HTML, re.S)

    def test_section_present_before_experience(self):
        self.assertIn('<section id="whatido">', HTML)
        self.assertLess(HTML.index('id="about"'), HTML.index('id="whatido"'))
        self.assertLess(HTML.index('id="whatido"'), HTML.index('id="experience"'))

    # Review Focus 3
    def test_flip_cards_are_buttons(self):
        self.assertEqual(len(self.CARDS), 6)
        titles = [re.search(r'<span class="f-title">(.*?)</span>', c).group(1) for c in self.CARDS]
        self.assertEqual(titles, ["Backend APIs", "Async &amp; data systems", "Cloud on AWS",
                                  "CI/CD automation", "Containers &amp; Kubernetes", "Observability &amp; reliability"])
        for c in self.CARDS:
            self.assertIn('<span class="face front">', c)
            self.assertIn('<span class="face back">', c)
            self.assertGreater(len(re.search(r'<span class="f-desc">(.*?)</span>', c, re.S).group(1)), 60)

    # Review Focus 3
    def test_flip_js_toggles_and_escape(self):
        js = re.search(r"querySelectorAll\('\.flip'\)(.*?)\}\);\s*\}\);", HTML, re.S).group(1)
        self.assertIn("aria-pressed", js)
        self.assertIn("Escape", js)

    # Review Focus 1
    def test_flip_cards_readable_without_js(self):
        flat = CSS.replace(" ", "")
        self.assertIn("html:not(.js).face{position:static", flat)
        self.assertIn("html:not(.js).flip-inner{", flat)

    # Review Focus 2
    def test_flip_reduced_motion_is_instant_swap(self):
        block = re.search(r"@media\(prefers-reduced-motion:reduce\)\{(.*?)\n\}", CSS.replace(" ", ""), re.S).group(1)
        self.assertIn(".flip-inner{transform:none", block)
        self.assertIn(".flip[aria-pressed=true].face.front{opacity:0", block)

    def test_reveal_not_on_flip_inner(self):
        # .reveal sets transform; on the rotating element it would cancel the flip
        self.assertNotIn('class="flip-inner reveal"', HTML)


class TileChecks(unittest.TestCase):
    def test_tiles_per_track(self):
        bk = re.search(r'<div class="track bk reveal">(.*?)</div>\s*<div class="track cl', HTML, re.S).group(1)
        cl = re.search(r'<div class="track cl reveal">(.*?)</div>\s*</div>\s*<div class="group core', HTML, re.S).group(1)
        self.assertEqual(len(re.findall(r'<li class="tile">', bk)), 13)
        self.assertEqual(len(re.findall(r'<li class="tile">', cl)), 23)

    def test_tile_marks_are_decorative(self):
        for mark in re.findall(r'<li class="tile">(<b[^>]*>)', HTML):
            self.assertEqual(mark, '<b aria-hidden="true">')

    def test_no_external_logo_assets(self):
        self.assertNotIn("<img", HTML)


class CountUpChecks(unittest.TestCase):
    def test_stats_carry_targets(self):
        got = re.findall(r'<b data-count="(\d+)" data-suffix="([^"]*)">([^<]*)</b>', HTML)
        self.assertEqual(got, [("2", "+", "2+"), ("70", "+", "70+"), ("70", "%", "70%"), ("60", "%+", "60%+")])

    # Review Focus 2
    def test_countup_skips_reduced_motion(self):
        js = re.search(r"\.stat b\[data-count\]'\)\)(.*?)\}\)\(\);", HTML, re.S).group(1)
        self.assertIn("prefers-reduced-motion", js)
        self.assertIn("IntersectionObserver", js)


if __name__ == "__main__":
    unittest.main()
