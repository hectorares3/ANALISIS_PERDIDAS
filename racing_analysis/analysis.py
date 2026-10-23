"""Conservative, reproducible turnover analysis for StatsBomb event JSON.

This describes associations, not tactical causes. A loss requires a failed pass
(excluding restarts), incomplete dribble, miscontrol or dispossession, followed
by a different possession belonging to the opponent within ``control_gap_seconds``.
The candidate must belong to its possession's team. The last eligible candidate
in a possession is used; a later controlled action by that team cancels it.
Out-of-play events, non-advantage fouls and restart possessions break continuity.

Danger means the first opponent shot in that *same* possession, no later than
``window_seconds`` after the loss and before an interruption. Shot quality,
off-ball positioning and causality are not inferred. Event timestamps, not the
rounded match clock, measure elapsed time; periods never join. Shootouts are
ignored. Coordinates are StatsBomb's 120 x 80 event coordinates. Grid labels
use neutral X low/middle/high and Y upper/central/lower, not left/right flanks.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Any


_RESTARTS = {"Corner", "Free Kick", "Goal Kick", "Kick Off", "Throw-in", "Throw In"}
_RESTART_PATTERNS = {
    "From Corner", "From Free Kick", "From Goal Kick", "From Kick Off", "From Throw In",
}
_STOP_TYPES = {
    "Offside", "Half End", "Half Start", "Injury Stoppage", "Referee Ball-Drop", "Ball Out",
}
_PASS_STOPS = {"Out", "Pass Offside", "Injury Clearance"}
_TIME_RE = re.compile(r"^(\d{2,}):([0-5]\d):([0-5]\d(?:\.\d+)?)$")
_TIME_EPSILON = 1e-9  # Ignore only binary floating-point noise at inclusive bounds.
_ZONE_X = (("low", "bajo"), ("middle", "medio"), ("high", "alto"))
_ZONE_Y = (("upper", "superior"), ("central", "central"), ("lower", "inferior"))
_ZONES = tuple(
    (f"{xkey}_{ykey}", f"X {xlabel} · Y {ylabel}")
    for xkey, xlabel in _ZONE_X for ykey, ylabel in _ZONE_Y
) + (("unknown", "Ubicación desconocida"),)


@dataclass(frozen=True)
class _Event:
    raw: dict[str, Any]
    event_id: str
    index: int
    period: int
    time: float
    minute: int
    second: float
    type: str
    team_id: int | None
    team: str | None
    possession: int | None
    owner_id: int | None
    owner: str | None


def _name(value: Any) -> str | None:
    return value.get("name") if isinstance(value, dict) and isinstance(value.get("name"), str) else None


def _positive_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} debe ser un número finito mayor que cero.")
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise ValueError(f"{field} debe ser un número finito mayor que cero.")
    return result


def _integer(value: Any, field: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{field} debe ser un entero >= {minimum}.")
    return value


def _team(value: Any, field: str) -> tuple[int | None, str | None]:
    if value is None:
        return None, None
    if not isinstance(value, dict) or not isinstance(value.get("name"), str) or not value["name"].strip():
        raise ValueError(f"{field} requiere un objeto con id y name.")
    return _integer(value.get("id"), f"{field}.id", minimum=1), value["name"]


def _normalize(events: list[dict[str, Any]]) -> list[_Event]:
    normalized: list[_Event] = []
    indexes: set[int] = set()
    identifiers: set[str] = set()
    for position, raw in enumerate(events):
        prefix = f"events[{position}]"
        if not isinstance(raw, dict):
            raise ValueError(f"{prefix} debe ser un objeto de evento.")
        period = _integer(raw.get("period"), f"{prefix}.period", minimum=1)
        # Shootout events cannot affect normal or extra-time play.
        if period > 4:
            continue
        index = _integer(raw.get("index"), f"{prefix}.index")
        if index in indexes:
            raise ValueError(f"Índice de evento duplicado: {index}.")
        indexes.add(index)
        event_id = raw.get("id")
        if not isinstance(event_id, str) or not event_id:
            raise ValueError(f"{prefix}.id debe ser un texto no vacío.")
        if event_id in identifiers:
            raise ValueError(f"Identificador de evento duplicado: {event_id}.")
        identifiers.add(event_id)
        timestamp = raw.get("timestamp")
        match = _TIME_RE.fullmatch(timestamp) if isinstance(timestamp, str) else None
        if match is None:
            raise ValueError(f"{prefix}.timestamp debe tener formato HH:MM:SS[.sss].")
        elapsed = int(match[1]) * 3600 + int(match[2]) * 60 + float(match[3])
        if not math.isfinite(elapsed):
            raise ValueError(f"{prefix}.timestamp debe ser finito.")
        type_name = _name(raw.get("type"))
        if not type_name:
            raise ValueError(f"{prefix}.type.name es obligatorio.")
        team_id, team_name = _team(raw.get("team"), f"{prefix}.team")
        owner_id, owner = _team(raw.get("possession_team"), f"{prefix}.possession_team")
        possession = raw.get("possession")
        if possession is not None:
            possession = _integer(possession, f"{prefix}.possession", minimum=1)
        minute = raw.get("minute", int(elapsed // 60) + {1: 0, 2: 45, 3: 90, 4: 105}[period])
        minute = _integer(minute, f"{prefix}.minute")
        second = raw.get("second", elapsed % 60)
        if isinstance(second, bool) or not isinstance(second, (int, float)) or not math.isfinite(second) or not 0 <= second < 60:
            raise ValueError(f"{prefix}.second debe estar entre 0 y 60 (excluido).")
        for detail in ("pass", "dribble", "foul_committed", "foul_won", "shot", "ball_recovery", "ball_receipt", "goalkeeper"):
            if detail in raw and not isinstance(raw[detail], dict):
                raise ValueError(f"{prefix}.{detail} debe ser un objeto.")
        normalized.append(_Event(raw, event_id, index, period, elapsed, minute, second, type_name,
                                 team_id, team_name, possession, owner_id, owner))
    return sorted(normalized, key=lambda event: (event.period, event.index))


def _interruption(event: _Event) -> bool:
    raw = event.raw
    if raw.get("out") is True or event.type in _STOP_TYPES:
        return True
    if event.type in {"Foul Committed", "Foul Won"}:
        detail = "foul_committed" if event.type == "Foul Committed" else "foul_won"
        return raw.get(detail, {}).get("advantage") is not True
    if event.type == "Pass":
        detail = raw.get("pass", {})
        return _name(detail.get("type")) in _RESTARTS or _name(detail.get("outcome")) in _PASS_STOPS
    return event.type == "Shot" and _name(raw.get("shot", {}).get("type")) == "Penalty"


def _candidate(event: _Event) -> bool:
    if event.team_id is None or event.team_id != event.owner_id or event.possession is None:
        return False
    if event.type in {"Miscontrol", "Dispossessed"}:
        return True
    if event.type == "Pass":
        detail = event.raw.get("pass", {})
        return _name(detail.get("outcome")) == "Incomplete" and _name(detail.get("type")) not in _RESTARTS
    return event.type == "Dribble" and _name(event.raw.get("dribble", {}).get("outcome")) == "Incomplete"


def _retained_control(event: _Event, team_id: int) -> bool:
    if event.team_id != team_id:
        return False
    if event.type in {"Carry", "Shot"}:
        return True
    if event.type == "Pass":
        return event.raw.get("pass", {}).get("outcome") is None
    if event.type == "Dribble":
        return _name(event.raw.get("dribble", {}).get("outcome")) == "Complete"
    if event.type == "Ball Receipt*":
        return event.raw.get("ball_receipt", {}).get("outcome") is None
    if event.type == "Ball Recovery":
        return event.raw.get("ball_recovery", {}).get("recovery_failure") is not True
    return False


def _location(event: _Event) -> tuple[float | None, float | None, str, str]:
    value = event.raw.get("location")
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return None, None, "unknown", _ZONES[-1][1]
    x, y = value[:2]
    if any(isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(item) for item in (x, y)):
        return None, None, "unknown", _ZONES[-1][1]
    if not 0 <= x <= 120 or not 0 <= y <= 80:
        return None, None, "unknown", _ZONES[-1][1]
    x_band = min(int(x / 40), 2)
    y_band = min(int(y / (80 / 3)), 2)
    key, label = _ZONES[x_band * 3 + y_band]
    return float(x), float(y), key, label


def _sequence_event(event: _Event) -> dict[str, Any]:
    return {"event_id": event.event_id, "index": event.index, "period": event.period,
            "minute": event.minute, "second": event.second, "team": event.team,
            "player": _name(event.raw.get("player")), "type": event.type}


def _segments(events: list[_Event]) -> list[tuple[int, int]]:
    """Unknown-possession events stay in the previous run to preserve stops."""
    segments: list[tuple[int, int]] = []
    start: int | None = None
    key: tuple[int, int, int] | None = None
    for offset, event in enumerate(events):
        if key is not None and event.period != key[0]:
            segments.append((start, offset))  # type: ignore[arg-type]
            start, key = None, None
        if event.possession is None or event.owner_id is None:
            continue
        event_key = (event.period, event.possession, event.owner_id)
        if event_key != key:
            if start is not None:
                segments.append((start, offset))
            start, key = offset, event_key
    if start is not None:
        segments.append((start, len(events)))
    return segments


def analyze_events(events: list[dict[str, Any]], window_seconds: float = 10.0,
                   control_gap_seconds: float = 5.0) -> dict[str, Any]:
    """Analyze one match's StatsBomb events without changing the input.

    Missing possession metadata cannot establish a loss. Missing or invalid
    coordinates remain valid losses in the unknown zone. Missing play patterns
    are reported; explicit restart patterns exclude the transition. IDs and
    event indexes must be unique within the match. Invalid structural input or
    nonpositive/nonfinite windows raise ``ValueError``.
    """
    window = _positive_number(window_seconds, "window_seconds")
    gap = _positive_number(control_gap_seconds, "control_gap_seconds")
    if not isinstance(events, list):
        raise ValueError("events debe ser una lista de eventos StatsBomb de un solo partido.")
    ordered = _normalize(events)
    teams: dict[int, dict[str, Any]] = {}
    for event in ordered:
        for team_id, team_name in ((event.team_id, event.team), (event.owner_id, event.owner)):
            if team_id is not None and team_id not in teams:
                teams[team_id] = {"id": team_id, "name": team_name, "losses": 0, "dangerous_losses": 0,
                                  "rate": 0.0, "zones": [{"key": key, "label": label, "losses": 0,
                                  "dangerous_losses": 0, "rate": 0.0} for key, label in _ZONES]}
    losses: list[dict[str, Any]] = []
    runs = _segments(ordered)
    for run_index in range(len(runs) - 1):
        start, end = runs[run_index]
        next_start, next_end = runs[run_index + 1]
        first, next_first = ordered[start], ordered[next_start]
        if first.period != next_first.period or first.owner_id == next_first.owner_id:
            continue
        # A transition across an unattributed period boundary is never continuous.
        if end != next_start:
            continue
        candidate_offset: int | None = None
        for offset in range(start, end):
            event = ordered[offset]
            if _interruption(event):
                candidate_offset = None
            elif _candidate(event):
                candidate_offset = offset
            elif candidate_offset is not None and _retained_control(event, first.owner_id):
                candidate_offset = None
        if candidate_offset is None:
            continue
        loss_event = ordered[candidate_offset]
        delay = next_first.time - loss_event.time
        next_is_open_shot = (next_first.type == "Shot"
                             and _name(next_first.raw.get("shot", {}).get("type")) != "Penalty")
        if delay < -_TIME_EPSILON or delay > gap + _TIME_EPSILON or (_interruption(next_first) and not next_is_open_shot):
            continue
        if _name(next_first.raw.get("play_pattern")) in _RESTART_PATTERNS:
            continue
        x, y, zone, zone_label = _location(loss_event)
        loss = {"team_id": loss_event.team_id, "team": loss_event.team,
                "player": _name(loss_event.raw.get("player")), "period": loss_event.period,
                "minute": loss_event.minute, "second": loss_event.second,
                "event_id": loss_event.event_id, "event_index": loss_event.index,
                "event_type": loss_event.type, "x": x, "y": y, "zone": zone,
                "zone_label": zone_label, "dangerous": False, "shot_event_id": None,
                "shot_player": None, "shot_seconds_after": None,
                "sequence": [_sequence_event(event) for event in ordered[candidate_offset:next_start]]}
        for offset in range(next_start, next_end):
            event = ordered[offset]
            elapsed = event.time - loss_event.time
            if elapsed < -_TIME_EPSILON or elapsed > window + _TIME_EPSILON:
                break
            loss["sequence"].append(_sequence_event(event))
            # Explicit recovery/control prevails over a delayed possession tag.
            if _retained_control(event, loss_event.team_id):
                break
            # A shot's resulting ball-out does not invalidate the shot itself.
            if (event.type == "Shot" and event.team_id == next_first.owner_id
                    and _name(event.raw.get("shot", {}).get("type")) != "Penalty"):
                loss.update(dangerous=True, shot_event_id=event.event_id,
                            shot_player=_name(event.raw.get("player")), shot_seconds_after=round(elapsed, 6))
                break
            if _interruption(event):
                break
        losses.append(loss)
        team = teams[loss_event.team_id]
        team["losses"] += 1
        team["dangerous_losses"] += int(loss["dangerous"])
        zone_counts = next(item for item in team["zones"] if item["key"] == zone)
        zone_counts["losses"] += 1
        zone_counts["dangerous_losses"] += int(loss["dangerous"])
    for team in teams.values():
        for counts in [team, *team["zones"]]:
            counts["rate"] = counts["dangerous_losses"] / counts["losses"] if counts["losses"] else 0.0
    warnings: list[str] = []
    missing_possession = sum(event.possession is None or event.owner_id is None for event in ordered)
    if missing_possession:
        warnings.append(f"{missing_possession} eventos sin posesión o equipo de posesión identificable; no confirman por sí solos una pérdida.")
    missing_patterns = sum(_name(event.raw.get("play_pattern")) is None for event in ordered)
    if missing_patterns:
        warnings.append(f"{missing_patterns} eventos sin patrón de juego; las interrupciones se comprueban con los demás campos disponibles.")
    unknown_locations = sum(loss["zone"] == "unknown" for loss in losses)
    if unknown_locations:
        warnings.append(f"{unknown_locations} pérdidas sin coordenadas válidas; están incluidas en el total y en la zona desconocida.")
    ignored = len(events) - len(ordered)
    if ignored:
        warnings.append(f"{ignored} eventos de periodos posteriores al cuarto (tanda de penaltis) excluidos.")
    return {"method_version": "0.1", "window_seconds": window, "control_gap_seconds": gap,
            "total_events": len(events), "teams": [teams[key] for key in sorted(teams)],
            "losses": losses, "warnings": warnings}
