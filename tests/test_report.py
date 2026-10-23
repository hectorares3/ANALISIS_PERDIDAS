import json
import re
import unittest

from racing_analysis.report import render_report


class ReportTests(unittest.TestCase):
    def test_untrusted_text_cannot_escape_script_or_html(self):
        attack = '</script><script>alert("owned")</script>&@@PAYLOAD@@'
        analysis = {"teams": [{"id": 1, "name": attack}], "losses": [], "warnings": [attack]}
        report = render_report(analysis, {"home_team": attack, "away_team": "B", "source_url": "javascript:alert(1)"})
        self.assertNotIn(attack, report)
        self.assertNotIn('href="javascript:', report)
        self.assertEqual(report.count('<script'), 2)
        self.assertIn('&lt;/script&gt;', report)
        payload = re.search(r'<script type="application/json" id="report-data">(.*?)</script>', report, re.S).group(1)
        self.assertEqual(json.loads(payload)["analysis"]["teams"][0]["name"], attack)

    def test_empty_analysis_has_valid_payload_and_no_external_assets(self):
        analysis = {"teams": [], "losses": [], "warnings": [], "window_seconds": 10, "control_gap_seconds": 5}
        report = render_report(analysis, {})
        self.assertIn('lang="es"', report)
        self.assertNotIn('<script src=', report)
        self.assertNotIn('<link ', report)
        self.assertIn('No se detectaron pérdidas para este equipo.', report)
        payload = re.search(r'<script type="application/json" id="report-data">(.*?)</script>', report, re.S).group(1)
        self.assertEqual(json.loads(payload)["analysis"], analysis)


if __name__ == "__main__":
    unittest.main()
