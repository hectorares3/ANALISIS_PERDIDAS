"""CLI sin dependencias externas. Ejecutar: python -m racing_analysis demo."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from .analysis import analyze_events
from .report import render_report

BASE = "https://raw.githubusercontent.com/hudl/open-data/master/"
DEMO_MATCH = 3943043


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def download(relative: str, destination: Path, offline: bool = False) -> Path:
    if destination.is_file():
        return destination
    if offline:
        raise ValueError(f"Falta {destination}. Ejecuta demo una vez con conexión.")
    request = Request(BASE + relative, headers={"User-Agent": "FootballAnalysisEducationalDemo/0.1"})
    with urlopen(request, timeout=60) as response:
        payload = response.read(20_000_001)
    if len(payload) > 20_000_000:
        raise ValueError("El archivo supera el límite de descarga de 20 MB.")
    if destination.suffix == ".json":
        json.loads(payload)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    temporary.write_bytes(payload)
    temporary.replace(destination)
    return destination


def demo_inputs(directory: Path, offline: bool) -> tuple[Path, dict]:
    matches_path = download("data/matches/55/282.json", directory / "euro2024_matches.json", offline)
    match = next((item for item in read_json(matches_path) if item.get("match_id") == DEMO_MATCH), None)
    if match is None:
        raise ValueError("El catálogo de partidos no contiene la demo esperada.")
    events = download(f"data/events/{DEMO_MATCH}.json", directory / f"{DEMO_MATCH}.json", offline)
    download("README.md", directory / "statsbomb_README.md", offline)
    download("LICENSE.pdf", directory / "statsbomb_LICENSE.pdf", offline)
    (directory / f"{DEMO_MATCH}.match.json").write_text(
        json.dumps(match, ensure_ascii=False, indent=2), encoding="utf-8")
    return events, {
        "match_id": DEMO_MATCH,
        "home_team": match["home_team"]["home_team_name"],
        "away_team": match["away_team"]["away_team_name"],
        "match_date": match["match_date"],
        "competition": match["competition"]["competition_name"],
        "season": match["season"]["season_name"],
        "source_url": "https://github.com/hudl/open-data",
        "data_label": "Datos reales de StatsBomb · demo educativa · un partido",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analiza pérdidas de balón y remates posteriores con datos StatsBomb.")
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="España–Inglaterra, final de la Eurocopa 2024")
    demo.add_argument("--data-dir", type=Path, default=Path("data/raw"))
    demo.add_argument("--offline", action="store_true", help="Utilizar solo archivos ya descargados")
    analyze = sub.add_parser("analyze", help="Analizar un JSON local de eventos de UN partido en formato StatsBomb")
    analyze.add_argument("events", type=Path)
    analyze.add_argument("--metadata", type=Path, help="JSON opcional con metadata normalizada del informe")
    for command in (demo, analyze):
        command.add_argument("--window", type=float, default=10.0, help="Ventana tras pérdida, en segundos (por defecto 10)")
        command.add_argument("--control-gap", type=float, default=5.0, help="Margen máximo para confirmar posesión rival")
        command.add_argument("--output", type=Path, default=Path("output/informe.html"))
    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
            event_path, metadata = demo_inputs(args.data_dir, args.offline)
        else:
            event_path = args.events
            metadata = read_json(args.metadata) if args.metadata else {}
            if not isinstance(metadata, dict):
                raise ValueError("Los metadatos deben ser un objeto JSON.")
            metadata.setdefault("data_label", "Archivo local · un partido · formato StatsBomb")
            metadata.setdefault("source_url", "https://github.com/hudl/open-data")
        if args.output.suffix.lower() != ".html":
            raise ValueError("La salida debe tener extensión .html.")
        output_paths = [args.output, args.output.with_suffix(".json"), args.output.with_suffix(".provenance.json")]
        inputs = [event_path.resolve()]
        if args.command == "analyze" and args.metadata:
            inputs.append(args.metadata.resolve())
        if any(path.resolve() in inputs for path in output_paths):
            raise ValueError("La salida no puede sobrescribir un archivo de entrada.")
        events = read_json(event_path)
        analysis = analyze_events(events, args.window, args.control_gap)
        metadata["generated_at"] = datetime.now(timezone.utc).isoformat()
        metadata["sensitivity"] = []
        for window in (5.0, 10.0, 15.0):
            alternative = analysis if window == args.window else analyze_events(events, window, args.control_gap)
            metadata["sensitivity"].append({"window_seconds": window, "teams": alternative["teams"]})
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(render_report(analysis, metadata), encoding="utf-8")
        args.output.with_suffix(".json").write_text(
            json.dumps({"metadata": metadata, "analysis": analysis}, ensure_ascii=False, indent=2, allow_nan=False),
            encoding="utf-8")
        provenance = {
            "source_url": metadata.get("source_url"),
            "match_id": metadata.get("match_id"),
            "events_file": str(event_path.resolve()),
            "sha256": hashlib.sha256(event_path.read_bytes()).hexdigest(),
            "generated_at": metadata["generated_at"],
            "method_version": analysis["method_version"],
            "window_seconds": args.window,
            "control_gap_seconds": args.control_gap,
            "scope": "Prototipo descriptivo educativo; no es un modelo de IA ni análisis de vídeo.",
        }
        args.output.with_suffix(".provenance.json").write_text(
            json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Informe: {args.output.resolve()}")
        print(f"Eventos leídos: {analysis['total_events']}")
        for team in analysis["teams"]:
            print(f"{team['name']}: {team['losses']} pérdidas detectadas; "
                  f"{team['dangerous_losses']} seguidas de remate en {args.window:g} s.")
        return 0
    except (OSError, URLError, ValueError, KeyError, StopIteration) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
