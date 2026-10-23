"""Self-contained, auditable HTML report for event-based football analysis."""

from __future__ import annotations

import html
import json
from urllib.parse import urlsplit


def _safe_url(value: object) -> str:
    """Only permit ordinary web links in the report's source anchor."""
    url = str(value or "https://github.com/statsbomb/open-data")
    try:
        parsed = urlsplit(url)
    except ValueError:
        return "https://github.com/statsbomb/open-data"
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return "https://github.com/statsbomb/open-data"
    return url


def render_report(analysis: dict, metadata: dict) -> str:
    """Render a local report without external scripts, fonts, or requests.

    All data-derived text is either HTML escaped or inserted through textContent.
    The JSON payload escapes characters that could terminate a script element.
    """
    payload = json.dumps(
        {"analysis": analysis, "metadata": metadata},
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )
    for unsafe, escaped in (
        ("&", "\\u0026"), ("<", "\\u003c"), (">", "\\u003e"),
        ("\u2028", "\\u2028"), ("\u2029", "\\u2029"),
    ):
        payload = payload.replace(unsafe, escaped)
    title = f"{metadata.get('home_team', 'Local')} · {metadata.get('away_team', 'Visitante')}"
    # Replace placeholders in a single pass so untrusted values cannot become
    # template directives for a subsequent replacement.
    replacements = {
        "TITLE": html.escape(title),
        "SUBTITLE": html.escape(" · ".join(str(metadata[key]) for key in
            ("competition", "season", "match_date") if metadata.get(key))),
        "DATA_LABEL": html.escape(str(metadata.get("data_label") or "Datos públicos de partidos")),
        "SOURCE_URL": html.escape(_safe_url(metadata.get("source_url")), quote=True),
        "PAYLOAD": payload,
    }
    import re
    return re.sub(r"@@([A-Z_]+)@@", lambda match: replacements[match.group(1)], _TEMPLATE)


_TEMPLATE = r'''<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<title>@@TITLE@@ — Análisis de pérdidas</title>
<style>
:root{--ink:#163c32;--muted:#5a6b63;--paper:#f5f3eb;--white:#fffef8;--line:#d8dfd2;--green:#265d49;--orange:#ba4e24;--lime:#d2e798;--soft:#e9eddf;--radius:18px}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.5 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}button,select,input{font:inherit}button,select{cursor:pointer}button:focus-visible,select:focus-visible,summary:focus-visible,input:focus-visible,a:focus-visible{outline:3px solid #ba4e24;outline-offset:4px}a{color:var(--green);text-underline-offset:3px}button{border:1px solid var(--ink);border-radius:9px;padding:9px 15px;color:var(--ink);background:transparent}button:hover{background:var(--soft)}.wrap{max-width:1220px;margin:auto;padding:35px 34px 45px}.topline{display:flex;justify-content:space-between;gap:20px;align-items:center;margin-bottom:37px}.wordmark{font-weight:800;letter-spacing:.16em;font-size:12px}.tag{font-size:11px;text-transform:uppercase;letter-spacing:.1em;font-weight:700;padding:6px 11px;border:1px solid #b7c4b6;border-radius:30px}.eyebrow{margin:0 0 9px;font-size:11px;text-transform:uppercase;letter-spacing:.15em;font-weight:800}.header{display:flex;justify-content:space-between;gap:24px;align-items:flex-end;margin-bottom:28px}.header h1{font-size:clamp(32px,4.6vw,56px);line-height:1.08;letter-spacing:-.045em;margin:0 0 15px;max-width:800px}.subtitle{font-size:15px;color:var(--muted);margin:0}.match-title{font-weight:700;font-size:20px;margin:0 0 3px}.scope{padding:13px 17px;background:var(--soft);border-left:3px solid #789750;border-radius:0 8px 8px 0;color:#3b5145;font-size:13px;margin:24px 0}.controls{display:flex;align-items:center;justify-content:space-between;gap:18px;flex-wrap:wrap;margin:28px 0 18px}.team-control{display:flex;align-items:center;gap:12px}.team-control label{font-weight:650;font-size:13px}select{border:1px solid #aabcae;border-radius:9px;padding:10px 35px 10px 12px;background:var(--white);color:var(--ink);max-width:100%}.controls .window{font-size:13px;color:var(--muted)}.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:24px}.kpi{background:var(--white);border:1px solid var(--line);padding:22px 24px;border-radius:var(--radius)}.kpi.accent{color:#f8f7ef;background:var(--ink);border-color:var(--ink)}.kpi-label{font-size:12px;display:block;margin:0 0 8px}.kpi-value{font-size:37px;font-weight:750;letter-spacing:-.04em;line-height:1.1;display:block}.kpi-note{font-size:11px;color:var(--muted);display:block;margin-top:9px}.accent .kpi-note{color:#d4dfd1}.grid{display:grid;grid-template-columns:minmax(0,1.75fr) minmax(270px,1fr);gap:22px}.card{border:1px solid var(--line);border-radius:var(--radius);padding:23px;background:var(--white);min-width:0}.card h2{font-size:18px;line-height:1.25;margin:0 0 7px;letter-spacing:-.02em}.description{font-size:12px;color:var(--muted);margin:0 0 18px}.pitch-shell{position:relative;overflow:hidden;border-radius:12px;background:#204c3b;border:1px solid #204c3b}.pitch{width:100%;display:block;max-height:470px}.pitch-lines{fill:none;stroke:#a8bbaa;stroke-width:2}.pitch-lines .center{fill:#a8bbaa}.point{stroke:#f9f6e8;stroke-width:2;cursor:help}.legend{display:flex;align-items:center;gap:18px;flex-wrap:wrap;font-size:11px;color:var(--muted);margin-top:12px}.legend span{display:inline-flex;align-items:center;gap:6px}.dot{display:inline-block;height:9px;width:9px;background:var(--lime);border-radius:50%;border:1px solid var(--green)}.dot.danger{background:var(--orange);border-color:var(--orange)}.zone-head,.zone-row{display:grid;grid-template-columns:minmax(100px,1fr) 50px 54px;gap:7px;align-items:center}.zone-head{font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);padding:0 0 8px;border-bottom:1px solid var(--line)}.zone-head span:not(:first-child),.zone-row span:not(:first-child){text-align:right}.zone-row{padding:10px 0;font-size:12px;border-bottom:1px solid #e9ecdf}.zone-name{display:grid;gap:5px}.bar{height:4px;background:var(--soft);border-radius:10px;overflow:hidden}.bar-fill{display:block;height:100%;background:#73945e}.empty{color:var(--muted);font-size:13px;padding:18px 0}.table-card{margin-top:22px}.table-top{display:flex;justify-content:space-between;align-items:center;gap:15px;flex-wrap:wrap}.toggle{font-size:12px;display:flex;align-items:center;gap:7px}.toggle input{accent-color:var(--green);width:16px;height:16px}.table-scroll{overflow-x:auto;margin:4px -3px 0}table{width:100%;border-collapse:collapse;font-size:12px;text-align:left}th{padding:12px 9px;font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);border-bottom:1px solid #adbda9;white-space:nowrap}td{padding:13px 9px;border-bottom:1px solid #e5e8dc;vertical-align:top}td:first-child,th:first-child{padding-left:3px}.badge{display:inline-block;padding:4px 8px;border-radius:20px;background:var(--soft);font-size:10px;white-space:nowrap}.badge.danger{background:#f5e6dc;color:#963b19}.shot-info{display:block;margin-top:4px;font-size:10px;color:var(--muted)}details{max-width:410px}summary{cursor:pointer;color:var(--green);white-space:nowrap}details[open] summary{margin-bottom:9px}.audit{font-size:11px;background:#f2f3eb;border:1px solid #e1e6d9;border-radius:7px;padding:10px;min-width:230px}.audit p{margin:0 0 7px;overflow-wrap:anywhere}.audit ol{margin:0;padding-left:18px}.audit li{padding:4px 0;border-top:1px solid #e1e6d9}.event-id{display:block;color:var(--muted);font-size:9px;overflow-wrap:anywhere;font-family:ui-monospace,SFMono-Regular,Consolas,monospace}.lower{display:grid;grid-template-columns:1fr 1fr;gap:22px;margin-top:22px}.lower h2{font-size:16px}.method-list{margin:12px 0 0;padding-left:18px;font-size:12px;color:#42594a}.method-list li{margin:7px 0}.lower p{font-size:12px;color:#42594a}.warning{padding:10px 13px;background:#faedda;border-left:3px solid #b9812d;font-size:12px;margin-top:12px}.footer{margin-top:25px;padding-top:17px;border-top:1px solid #ced7c8;display:flex;justify-content:space-between;gap:20px;color:var(--muted);font-size:10px;flex-wrap:wrap}.footer p{margin:0}.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)}.report-state{margin:0;color:var(--muted);font-size:11px}
@media(max-width:850px){.wrap{padding:24px 20px}.header{display:block}.grid{grid-template-columns:1fr}.kpis{grid-template-columns:repeat(2,1fr)}.lower{grid-template-columns:1fr}.topline{margin-bottom:28px}.header h1{font-size:42px}.kpi{padding:18px}.card{padding:19px}}
@media(max-width:440px){.wrap{padding:20px 13px}.tag{font-size:9px}.header h1{font-size:34px}.kpi-value{font-size:32px}.kpis{gap:9px}.team-control{width:100%;justify-content:space-between}.team-control select{max-width:72%}.topline{gap:8px}.controls{margin-top:22px}}
@media print{#print-team{position:static;width:auto;height:auto;clip:auto;overflow:visible;font-weight:700}body{background:white}.wrap{max-width:none;padding:0}.print-button,.controls select,.toggle{display:none}.kpi,.card{break-inside:avoid}.grid{grid-template-columns:1.6fr 1fr}.lower{grid-template-columns:1fr 1fr}.kpis{grid-template-columns:repeat(4,1fr)}.table-scroll{overflow:visible}details{max-width:none}summary{color:#163c32}.audit{min-width:0}.table-card{break-inside:auto}.header h1{font-size:38px}.topline{margin-bottom:20px}.pitch{max-height:330px}a{color:inherit}.controls{margin:15px 0}*{-webkit-print-color-adjust:exact;print-color-adjust:exact}.footer{font-size:9px}#print-team{position:static;width:auto;height:auto;clip:auto;font-weight:700}}
</style>
</head>
<body>
<main class="wrap">
<div class="topline"><div class="wordmark">LAB · FÚTBOL Y DATOS</div><span class="tag">Prototipo con datos públicos</span><button class="print-button" id="print">Imprimir / PDF</button></div>
<header class="header"><div><p class="eyebrow">Transición defensiva / Análisis exploratorio</p><h1>Después de perder<br>el balón.</h1><p class="match-title">@@TITLE@@</p><p class="subtitle">@@SUBTITLE@@</p></div></header>
<p class="scope"><strong>Muestra: un partido.</strong> Este informe identifica secuencias para revisar. Sus cifras no describen el rendimiento habitual de un equipo ni demuestran causas tácticas.</p>
<div class="controls"><div class="team-control"><label for="team">Equipo analizado</label><select id="team" aria-label="Equipo analizado"></select><span id="print-team" class="sr-only"></span></div><span class="window" id="window-label"></span></div>
<noscript><p class="warning">Activa JavaScript para consultar este informe local. Los cálculos ya están realizados; JavaScript muestra y filtra sus resultados.</p></noscript>
<section class="kpis" aria-label="Indicadores del equipo" aria-live="polite">
<div class="kpi"><span class="kpi-label">Pérdidas detectadas</span><strong class="kpi-value" id="losses">—</strong><span class="kpi-note">Con posesión rival registrada</span></div>
<div class="kpi accent"><span class="kpi-label">Con remate rival posterior</span><strong class="kpi-value" id="dangerous">—</strong><span class="kpi-note" id="danger-note">Dentro de la ventana analizada</span></div>
<div class="kpi"><span class="kpi-label">Proporción con remate</span><strong class="kpi-value" id="rate">—</strong><span class="kpi-note">Sobre las pérdidas detectadas</span></div>
<div class="kpi"><span class="kpi-label">Pérdidas localizadas</span><strong class="kpi-value" id="located">—</strong><span class="kpi-note">Con coordenadas para el mapa</span></div>
</section>
<div class="grid">
<section class="card"><h2>¿Dónde empieza la secuencia?</h2><p class="description">Cada punto marca el lugar de una pérdida. Pasa el cursor o usa Tab para ver el detalle.</p>
<div class="pitch-shell"><svg id="pitch" class="pitch" viewBox="-35 -35 1270 870" role="img" aria-labelledby="pitch-title pitch-desc"><title id="pitch-title">Ubicación de pérdidas de balón</title><desc id="pitch-desc">Campo con coordenadas de origen StatsBomb: 120 por 80 unidades. Los puntos naranjas indican remate rival posterior.</desc><rect x="-35" y="-35" width="1270" height="870" fill="#204c3b"/><g opacity=".18" fill="#729775"><rect x="0" width="150" height="800"/><rect x="300" width="150" height="800"/><rect x="600" width="150" height="800"/><rect x="900" width="150" height="800"/></g><g class="pitch-lines"><rect width="1200" height="800"/><path d="M600 0V800"/><circle cx="600" cy="400" r="100"/><circle class="center" cx="600" cy="400" r="3"/><path d="M0 180H180V620H0 M1200 180H1020V620H1200 M0 300H60V500H0 M1200 300H1140V500H1200"/><path d="M180 320A100 100 0 0 1 180 480 M1020 320A100 100 0 0 0 1020 480"/><circle class="center" cx="120" cy="400" r="3"/><circle class="center" cx="1080" cy="400" r="3"/><path d="M0 360H-20V440H0 M1200 360H1220V440H1200"/></g><g id="points"></g></svg></div>
<div class="legend"><span><i class="dot" aria-hidden="true"></i>Sin remate en la ventana</span><span><i class="dot danger" aria-hidden="true"></i>Con remate rival</span></div><p class="description" style="margin:10px 0 0">Coordenadas del evento registrado; no representan la posición continua de los jugadores.</p></section>
<section class="card"><h2>Zonas de pérdida</h2><p class="description">Recuento descriptivo de esta muestra. “Remate” cuenta pérdidas asociadas a un remate rival, no remates distintos.</p><div class="zone-head"><span>Zona</span><span>Pérdidas</span><span>Remate</span></div><div id="zones"></div><p class="description" style="margin:18px 0 0">Compara recuentos con cuidado: no se ajustan por las posesiones ni por el tiempo que se juega en cada zona.</p></section>
</div>
<section class="card table-card" id="sensitivity-card" hidden><h2>¿Cambia el resultado con la ventana?</h2><p class="description">La misma regla, calculada con distintos límites de tiempo. Comparación del equipo seleccionado; el resto del informe utiliza su ventana principal.</p><div class="table-scroll"><table><caption class="sr-only">Sensibilidad a la ventana temporal</caption><thead><tr><th scope="col">Ventana</th><th scope="col">Pérdidas</th><th scope="col">Con remate rival</th><th scope="col">Proporción</th></tr></thead><tbody id="sensitivity-rows"></tbody></table></div></section>
<section class="card table-card"><div class="table-top"><div><h2>Jugada a jugada</h2><p class="description">Abre “Ver secuencia” para auditar los eventos y sus identificadores.</p></div><label class="toggle"><input type="checkbox" id="danger-filter">Solo pérdidas con remate rival</label></div><p id="table-state" class="report-state" aria-live="polite"></p><div class="table-scroll"><table><caption class="sr-only">Pérdidas y secuencias del equipo seleccionado</caption><thead><tr><th scope="col">Momento</th><th scope="col">Jugador / evento</th><th scope="col">Zona</th><th scope="col">Resultado</th><th scope="col">Evidencia</th></tr></thead><tbody id="rows"></tbody></table></div></section>
<div class="lower"><section class="card"><h2>Cómo se ha calculado</h2><ol class="method-list"><li id="method-control"></li><li id="method-window"></li><li>Se conserva la secuencia de eventos para comprobar cada detección. La regla es una aproximación: el registro de acciones no describe todos los contactos con el balón.</li></ol><p id="method-version"></p><div id="warnings"></div></section><section class="card"><h2>Qué permite concluir</h2><p>Este informe ayuda a localizar secuencias que merecen revisión con vídeo. Una asociación temporal entre pérdida y remate no demuestra que la pérdida causara el remate ni identifica por sí sola un error táctico.</p><p>No estima distancias entre líneas, presión colectiva ni colocación de jugadores sin balón. Para ello hacen falta otras observaciones o datos de posiciones.</p><p><strong>Análisis por reglas, sin modelo de IA entrenado.</strong> No se han analizado vídeos ni se han validado recomendaciones para un cuerpo técnico.</p></section></div>
<footer class="footer"><p><strong>@@DATA_LABEL@@</strong><br>Fuente: <a href="@@SOURCE_URL@@" target="_blank" rel="noopener noreferrer">StatsBomb Open Data</a>. Datos y atribución: StatsBomb.<br>Demo educativa local, independiente y sin afiliación oficial a ningún club.</p><p id="provenance"></p></footer>
</main>
<script type="application/json" id="report-data">@@PAYLOAD@@</script>
<script>
'use strict';
const payload = JSON.parse(document.getElementById('report-data').textContent);
const analysis = payload.analysis || {}, metadata = payload.metadata || {};
const teams = Array.isArray(analysis.teams) ? analysis.teams : [];
const allLosses = Array.isArray(analysis.losses) ? analysis.losses : [];
const byId = id => document.getElementById(id);
const text = (id, value) => { byId(id).textContent = value; };
const el = (tag, value, className) => { const node = document.createElement(tag); if(value != null) node.textContent = String(value); if(className) node.className = className; return node; };
const numeric = value => typeof value === 'number' && Number.isFinite(value);
const formatNumber = value => Number(value || 0).toLocaleString('es-ES');
const seconds = value => numeric(value) ? value.toLocaleString('es-ES', {maximumFractionDigits:2}) : '—';
const moment = value => `${value.minute == null ? '—' : value.minute}:${String(value.second == null ? 0 : value.second).padStart(2,'0')} · P${value.period == null ? '—' : value.period}`;
const locationValid = loss => numeric(loss.x) && numeric(loss.y) && loss.x >= 0 && loss.x <= 120 && loss.y >= 0 && loss.y <= 80;
text('window-label', `Ventana de remate: ${seconds(analysis.window_seconds)} segundos`);
text('danger-note', `Hasta ${seconds(analysis.window_seconds)} s tras la pérdida`);
text('method-control', `Se buscan pérdidas candidatas seguidas de posesión rival registrada en un máximo de ${seconds(analysis.control_gap_seconds)} segundos. Las interrupciones y el cambio de periodo delimitan las secuencias.`);
text('method-window', `Una pérdida se marca “con remate” si el rival remata en los siguientes ${seconds(analysis.window_seconds)} segundos, antes de la recuperación del equipo analizado o de una interrupción.`);
text('method-version', `Método: ${analysis.method_version || 'sin versión'} · ${formatNumber(analysis.total_events)} eventos en el partido.`);
text('provenance', `Partido ${metadata.match_id == null ? '—' : metadata.match_id} · Generado: ${metadata.generated_at || 'sin fecha'}`);
for(const warning of (Array.isArray(analysis.warnings) ? analysis.warnings : [])) byId('warnings').append(el('p', warning, 'warning'));
for(const [index, team] of teams.entries()) { const option = el('option', team.name || 'Equipo sin nombre'); option.value = String(index); byId('team').append(option); }
if(!teams.length) { const option = el('option','Sin equipos disponibles'); byId('team').append(option); byId('team').disabled = true; }

function renderMap(losses) {
  const layer = byId('points'); layer.replaceChildren();
  // Draw orange markers last so dangerous losses remain visible in overlaps.
  const points = losses.filter(locationValid).slice().sort((a,b) => Number(a.dangerous) - Number(b.dangerous));
  for(const loss of points) {
    const circle = document.createElementNS('http://www.w3.org/2000/svg','circle');
    circle.setAttribute('cx',String(loss.x * 10)); circle.setAttribute('cy',String(loss.y * 10)); circle.setAttribute('r',loss.dangerous ? '11' : '8');
    circle.setAttribute('fill',loss.dangerous ? '#df7745' : '#d2e798'); circle.setAttribute('class','point'); circle.setAttribute('tabindex','0');
    const label = `${moment(loss)} · ${loss.player || 'Jugador no identificado'} · ${loss.zone_label || 'Sin zona'} · ${loss.dangerous ? 'Remate rival a los ' + seconds(loss.shot_seconds_after) + ' s' : 'Sin remate rival en la ventana'}`;
    circle.setAttribute('aria-label',label); const title = document.createElementNS('http://www.w3.org/2000/svg','title'); title.textContent = label; circle.append(title); layer.append(circle);
  }
}

function renderZones(team) {
  const root = byId('zones'); root.replaceChildren();
  const zones = Array.isArray(team.zones) ? team.zones : [];
  if(!zones.length) {root.append(el('p','No hay pérdidas para desglosar en zonas.','empty')); return;}
  const largest = Math.max(1, ...zones.map(zone => Number(zone.losses) || 0));
  for(const zone of zones) {
    const row = el('div',null,'zone-row'), name = el('span',null,'zone-name'); name.append(el('span',zone.label || zone.key || 'Sin zona'));
    const bar = el('span',null,'bar'), fill = el('span',null,'bar-fill'); fill.style.width = `${Math.max(0, Math.min(100, (Number(zone.losses) || 0) / largest * 100))}%`; bar.append(fill); name.append(bar);
    row.append(name,el('span',formatNumber(zone.losses)),el('span',formatNumber(zone.dangerous_losses))); root.append(row);
  }
}

function renderTable(losses) {
  const filtered = byId('danger-filter').checked ? losses.filter(loss => loss.dangerous) : losses;
  text('table-state', `${formatNumber(filtered.length)} de ${formatNumber(losses.length)} pérdidas mostradas. El filtro solo afecta a esta tabla.`);
  const root = byId('rows'); root.replaceChildren();
  if(!filtered.length) {const row = el('tr'), cell = el('td',byId('danger-filter').checked ? 'No se detectaron pérdidas con remate rival en esta selección.' : 'No se detectaron pérdidas para este equipo.','empty'); cell.colSpan = 5; row.append(cell); root.append(row); return;}
  for(const loss of filtered) {
    const row = el('tr'), playerCell = el('td'); playerCell.append(el('span',loss.player || 'Jugador no identificado'),el('span',loss.event_type || 'Evento sin tipo','shot-info'));
    const resultCell = el('td'); resultCell.append(el('span',loss.dangerous ? 'Con remate rival' : 'Sin remate',loss.dangerous ? 'badge danger' : 'badge'));
    if(loss.dangerous) resultCell.append(el('span',`${loss.shot_player || 'Rival'} · +${seconds(loss.shot_seconds_after)} s`,'shot-info'));
    const auditCell = el('td'), details = el('details'), audit = el('div',null,'audit'); details.append(el('summary','Ver secuencia'));
    const lossId = el('p','Pérdida · '); lossId.append(el('span',loss.event_id || 'ID no disponible','event-id')); audit.append(lossId);
    if(loss.shot_event_id) {const shotId = el('p','Remate · '); shotId.append(el('span',loss.shot_event_id,'event-id')); audit.append(shotId);}
    const sequence = Array.isArray(loss.sequence) ? loss.sequence : [];
    if(sequence.length) {const list = el('ol'); for(const event of sequence) {const item = el('li',`${moment(event)} · ${event.team || 'Sin equipo'} · ${event.player || '—'} · ${event.type || 'Evento'}`); item.append(el('span',`#${event.index == null ? '—' : event.index} · ${event.event_id || 'ID no disponible'}`,'event-id')); list.append(item);} audit.append(list);}
    else audit.append(el('p','Sin eventos de secuencia adjuntos.'));
    details.append(audit); auditCell.append(details); row.append(el('td',moment(loss)),playerCell,el('td',loss.zone_label || 'Sin coordenadas'),resultCell,auditCell); root.append(row);
  }
}

function renderSensitivity(team) {
  const samples = Array.isArray(metadata.sensitivity) ? metadata.sensitivity : [];
  const root = byId('sensitivity-rows'); root.replaceChildren();
  for(const sample of samples) {
    const item = (Array.isArray(sample.teams) ? sample.teams : []).find(candidate => String(candidate.id) === String(team.id));
    if(!item) continue;
    const row = el('tr');
    const rate = Number(item.losses) > 0 && numeric(item.rate) ? `${(item.rate * 100).toLocaleString('es-ES',{maximumFractionDigits:1})}%` : '—';
    row.append(el('td',`${seconds(sample.window_seconds)} s`),el('td',formatNumber(item.losses)),el('td',formatNumber(item.dangerous_losses)),el('td',rate)); root.append(row);
  }
  byId('sensitivity-card').hidden = !root.children.length;
}

function render() {
  const team = teams[Number(byId('team').value)] || {};
  const losses = allLosses.filter(loss => String(loss.team_id) === String(team.id));
  text('print-team',team.name || 'Sin equipo');
  text('losses',formatNumber(team.losses)); text('dangerous',formatNumber(team.dangerous_losses));
  text('rate',Number(team.losses) > 0 && numeric(team.rate) ? `${(team.rate * 100).toLocaleString('es-ES',{maximumFractionDigits:1})}%` : '—');
  text('located',formatNumber(losses.filter(locationValid).length)); renderMap(losses); renderZones(team); renderTable(losses); renderSensitivity(team);
}
byId('team').addEventListener('change',render);
byId('danger-filter').addEventListener('change',render);
byId('print').addEventListener('click',() => window.print());
render();
</script>
</body>
</html>'''
