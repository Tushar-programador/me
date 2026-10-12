import html
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = (ROOT / "resume.html").read_text(encoding="utf-8")
TEXT = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[^>]*>.*?</\1>", "", RAW, flags=re.S)))
TEXT = re.sub(r"\s+", " ", TEXT)


class ResumeContent(unittest.TestCase):
    def test_title_and_headline_match_oct8_resume(self):
        self.assertIn("Cloud & DevOps Engineer", re.search(r"<title>(.*?)</title>", html.unescape(RAW)).group(1))
        self.assertIn("Cloud & DevOps Engineer · AWS · Docker · Kubernetes · Terraform · CI/CD · Node.js", TEXT)

    def test_summary(self):
        self.assertIn("Cloud & DevOps Engineer with 2+ years of software engineering experience", TEXT)

    def test_skill_groups(self):
        for label in ("Backend:", "Cloud:", "CI/CD & VCS:", "DevOps:", "Databases:", "Monitoring:", "Core Concepts:"):
            self.assertIn(label, TEXT)
        for s in ("NestJS", "Route 53", "Helm", "Terraform", "Prometheus", "Grafana", "CloudWatch", "Microservices"):
            self.assertIn(s, TEXT)

    def test_experience(self):
        self.assertIn("Software Engineer | DevOps / Cloud Focus", TEXT)
        self.assertIn("07/2024 – Present", TEXT)
        self.assertIn("Vervebot.io", TEXT)
        self.assertIn("Developed and maintained 70+ REST APIs", TEXT)
        self.assertIn("reduced manual data entry by 70%", TEXT)

    def test_projects_in_order(self):
        names = re.findall(r'<span class="et">(.*?)</span>', html.unescape(RAW))
        self.assertEqual(
            [n for n in names if not n.startswith("Software Engineer")],
            ["Production Cloud Deployment & CI/CD Platform", "Production Reliability Platform", "ICMS"],
        )
        self.assertIn("08/2025 – 02/2026", TEXT)
        self.assertIn("02/2024 – Present", TEXT)

    def test_education(self):
        self.assertIn("Bachelor of Computer Applications (BCA)", TEXT)
        self.assertIn("Kurukshetra University", TEXT)
        self.assertIn("2022 – 2025", TEXT)

    def test_old_content_removed(self):
        for old in ("Backend Developer", "70+ production-grade", "Relook", "Outdraw", "Open to Backend Developer"):
            self.assertNotIn(old, TEXT)

    def test_existing_features_kept(self):
        self.assertIn('id="bug-overlay"', RAW)
        self.assertIn("window.print()", RAW)
        self.assertIn("@media print", RAW)
        self.assertIn('href="index.html"', RAW)


if __name__ == "__main__":
    unittest.main()
