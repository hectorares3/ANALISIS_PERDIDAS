"""Protecciones de entrada/salida y ejecución sin conexión."""

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from racing_analysis.cli import download, main


class CommandTests(unittest.TestCase):
    def test_offline_missing_file_never_connects(self):
        with tempfile.TemporaryDirectory() as directory, patch("racing_analysis.cli.urlopen") as network:
            with self.assertRaises(ValueError):
                download("anything.json", Path(directory) / "missing.json", offline=True)
            network.assert_not_called()

    def test_analysis_cannot_overwrite_source_via_json_sidecar(self):
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / "events.json"
            original.write_text("[]", encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                main(["analyze", str(original), "--output", str(original.with_suffix(".html"))])
            self.assertEqual(caught.exception.code, 1)
            self.assertEqual(original.read_text(encoding="utf-8"), "[]")
            self.assertFalse(original.with_suffix(".html").exists())

    def test_generated_report_and_provenance_correspond_to_input(self):
        with tempfile.TemporaryDirectory() as directory, patch("racing_analysis.cli.urlopen") as network:
            directory = Path(directory)
            original, target = directory / "events.json", directory / "report.html"
            original.write_text("[]", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                code = main(["analyze", str(original), "--output", str(target)])
            self.assertEqual(code, 0)
            self.assertTrue(target.read_text(encoding="utf-8").startswith("<!doctype html>"))
            saved = json.loads(target.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(saved["analysis"]["total_events"], 0)
            self.assertEqual([item["window_seconds"] for item in saved["metadata"]["sensitivity"]], [5, 10, 15])
            provenance = json.loads(target.with_suffix(".provenance.json").read_text(encoding="utf-8"))
            self.assertEqual(len(provenance["sha256"]), 64)
            network.assert_not_called()


if __name__ == "__main__":
    unittest.main()
