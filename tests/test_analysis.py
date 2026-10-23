"""Synthetic, auditable football sequences for the turnover definition."""

import copy
import math
import unittest

from racing_analysis.analysis import analyze_events


def event(index, time, *, team=1, possession=1, owner=None, kind="Pass", period=1,
          outcome=None, location=(30, 40), pattern="Regular Play", **extra):
    owner = team if owner is None else owner
    hours = int(time // 3600)
    minutes = int(time % 3600 // 60)
    seconds = time % 60
    result = {"id": f"event-{index}", "index": index, "period": period,
              "timestamp": f"{hours:02}:{minutes:02}:{seconds:06.3f}",
              "minute": int(time // 60) + (45 if period == 2 else 0), "second": int(seconds),
              "type": {"name": kind}, "team": {"id": team, "name": f"Equipo {team}"},
              "possession": possession, "possession_team": {"id": owner, "name": f"Equipo {owner}"},
              "player": {"id": team * 10, "name": f"Jugador {team}"},
              "play_pattern": {"name": pattern}}
    if location is not None:
        result["location"] = list(location)
    detail_key = {"Pass": "pass", "Dribble": "dribble", "Shot": "shot"}.get(kind)
    if detail_key:
        result[detail_key] = {"outcome": {"name": outcome}} if outcome else {}
    result.update(extra)
    return result


def attack(shot_time=20, loss_time=10, recovery_time=11, **loss_kwargs):
    return [event(1, loss_time, outcome="Incomplete", **loss_kwargs),
            event(2, recovery_time, team=2, possession=2, kind="Ball Recovery"),
            event(3, shot_time, team=2, possession=2, kind="Shot")]


class AnalysisTests(unittest.TestCase):
    def test_inclusive_window_boundary_and_first_shot(self):
        rows = attack(shot_time=20.125, loss_time=10.125)
        rows.append(event(4, 20.126, team=2, possession=2, kind="Shot"))
        loss = analyze_events(rows)["losses"][0]
        self.assertTrue(loss["dangerous"])
        self.assertEqual(loss["shot_event_id"], "event-3")
        self.assertEqual(loss["shot_seconds_after"], 10)
        self.assertEqual(len(loss["sequence"]), 3)
        self.assertFalse(analyze_events(attack(shot_time=20.126, loss_time=10.125))["losses"][0]["dangerous"])

    def test_windows_5_10_15_preserve_denominator(self):
        rows = attack(shot_time=21)
        results = [analyze_events(rows, window_seconds=window) for window in (5, 10, 15)]
        self.assertEqual([report["teams"][0]["losses"] for report in results], [1, 1, 1])
        self.assertEqual([report["teams"][0]["dangerous_losses"] for report in results], [0, 0, 1])

    def test_control_gap_boundary(self):
        self.assertEqual(len(analyze_events(attack(recovery_time=15))["losses"]), 1)
        self.assertEqual(len(analyze_events(attack(recovery_time=15.001))["losses"]), 0)

    def test_decimal_timestamp_boundaries_ignore_float_rounding_noise(self):
        rows = attack(loss_time=10.001, recovery_time=15.001, shot_time=20.001)
        self.assertTrue(analyze_events(rows)["losses"][0]["dangerous"])

    def test_period_change_is_not_a_loss(self):
        rows = [event(1, 2699, outcome="Incomplete"),
                event(2, 0, team=2, possession=2, kind="Ball Recovery", period=2),
                event(3, 2, team=2, possession=2, kind="Shot", period=2)]
        self.assertEqual(analyze_events(rows)["losses"], [])

    def test_shot_in_new_period_does_not_qualify(self):
        rows = attack(shot_time=2)
        rows[-1] = event(3, 2, team=2, possession=2, kind="Shot", period=2)
        result = analyze_events(rows)
        self.assertEqual(len(result["losses"]), 1)
        self.assertFalse(result["losses"][0]["dangerous"])

    def test_interruption_before_recovery_excludes_loss(self):
        for kind in ("Foul Committed", "Foul Won", "Offside", "Injury Stoppage", "Half End"):
            with self.subTest(kind=kind):
                rows = [event(1, 10, outcome="Incomplete"), event(2, 10.5, kind=kind),
                        event(3, 11, team=2, possession=2, kind="Ball Recovery")]
                self.assertEqual(analyze_events(rows)["losses"], [])

    def test_interruption_after_recovery_stops_risk(self):
        rows = attack()
        rows[-1]["index"] = 4
        rows.insert(2, event(3, 12, team=2, possession=2, kind="Foul Won"))
        rows[-1]["id"] = "event-4"
        result = analyze_events(rows)
        self.assertEqual(len(result["losses"]), 1)
        self.assertFalse(result["losses"][0]["dangerous"])

    def test_foul_advantage_keeps_ball_live(self):
        rows = attack()
        rows[-1].update(id="event-4", index=4)
        rows.insert(2, event(3, 12, team=2, possession=2, kind="Foul Won", foul_won={"advantage": True}))
        self.assertTrue(analyze_events(rows)["losses"][0]["dangerous"])

    def test_restart_and_out_candidates_are_excluded(self):
        for change in ({"out": True}, {"pass": {"outcome": {"name": "Out"}}},
                       {"pass": {"outcome": {"name": "Pass Offside"}}},
                       {"pass": {"outcome": {"name": "Incomplete"}, "type": {"name": "Free Kick"}}}):
            with self.subTest(change=change):
                rows = attack()
                rows[0].update(change)
                self.assertEqual(analyze_events(rows)["losses"], [])

    def test_opponent_restart_pattern_excludes_loss(self):
        for pattern in ("From Throw In", "From Free Kick", "From Goal Kick", "From Corner", "From Kick Off"):
            with self.subTest(pattern=pattern):
                rows = attack()
                rows[1]["play_pattern"]["name"] = pattern
                self.assertEqual(analyze_events(rows)["losses"], [])

    def test_only_last_candidate_in_possession_is_counted(self):
        rows = [event(1, 10, kind="Miscontrol"), event(2, 11, kind="Dispossessed"),
                event(3, 12, team=2, possession=2, kind="Ball Recovery"),
                event(4, 13, team=2, possession=2, kind="Shot")]
        result = analyze_events(rows)
        self.assertEqual(len(result["losses"]), 1)
        self.assertEqual(result["losses"][0]["event_id"], "event-2")

    def test_same_team_next_possession_is_not_loss(self):
        rows = [event(1, 10, outcome="Incomplete"), event(2, 11, possession=2, kind="Ball Recovery"),
                event(3, 12, team=2, possession=3, kind="Shot")]
        self.assertEqual(analyze_events(rows)["losses"], [])

    def test_controlled_action_cancels_earlier_candidate(self):
        for kind in ("Carry", "Pass", "Ball Receipt*", "Shot", "Ball Recovery"):
            with self.subTest(kind=kind):
                rows = [event(1, 10, outcome="Incomplete"), event(2, 11, kind=kind),
                        event(3, 12, team=2, possession=2, kind="Ball Recovery")]
                self.assertEqual(analyze_events(rows)["losses"], [])

    def test_shot_after_another_possession_does_not_qualify(self):
        rows = [event(1, 10, outcome="Incomplete"),
                event(2, 11, team=2, possession=2, kind="Ball Recovery"),
                event(3, 12, possession=3, kind="Ball Recovery"),
                event(4, 13, team=2, possession=4, kind="Shot")]
        self.assertFalse(analyze_events(rows)["losses"][0]["dangerous"])

    def test_unknown_location_is_in_denominator(self):
        for location in (None, (-1, 40), (50, math.nan), (121, 80)):
            with self.subTest(location=location):
                result = analyze_events(attack(location=location))
                self.assertEqual(result["teams"][0]["losses"], 1)
                self.assertEqual(result["teams"][0]["rate"], 1)
                self.assertEqual(result["losses"][0]["zone"], "unknown")
                self.assertEqual(result["teams"][0]["zones"][-1]["losses"], 1)
                self.assertTrue(result["warnings"])

    def test_pitch_boundary_coordinates(self):
        for location, expected in (((0, 0), "low_upper"), ((40, 80 / 3), "middle_central"),
                                   ((80, 160 / 3), "high_lower"), ((120, 80), "high_lower")):
            with self.subTest(location=location):
                self.assertEqual(analyze_events(attack(location=location))["losses"][0]["zone"], expected)

    def test_multiple_teams_and_zero_denominator(self):
        rows = attack()
        rows += [event(4, 30, team=2, possession=3, kind="Dribble", outcome="Incomplete"),
                 event(5, 31, possession=4, kind="Ball Recovery"),
                 event(6, 32, team=3, possession=5, kind="Ball Recovery")]
        teams = analyze_events(rows)["teams"]
        self.assertEqual([team["id"] for team in teams], [1, 2, 3])
        self.assertEqual([team["losses"] for team in teams], [1, 1, 0])
        self.assertEqual([team["rate"] for team in teams], [1, 0, 0])

    def test_input_is_not_mutated_and_index_orders_events(self):
        rows = attack()
        before = copy.deepcopy(rows)
        first = analyze_events(rows)
        self.assertEqual(rows, before)
        self.assertEqual(first, analyze_events(list(reversed(rows))))

    def test_shootouts_are_ignored(self):
        rows = attack() + [{"period": 5}]
        result = analyze_events(rows)
        self.assertEqual(result["total_events"], 4)
        self.assertEqual(len(result["losses"]), 1)
        self.assertIn("tanda", result["warnings"][-1])

    def test_shot_that_goes_out_still_qualifies(self):
        rows = attack()
        rows[-1]["out"] = True
        self.assertTrue(analyze_events(rows)["losses"][0]["dangerous"])

    def test_immediate_opponent_shot_can_start_possession_and_go_out(self):
        rows = [event(1, 10, outcome="Incomplete"),
                event(2, 11, team=2, possession=2, kind="Shot", out=True)]
        result = analyze_events(rows)
        self.assertEqual(len(result["losses"]), 1)
        self.assertTrue(result["losses"][0]["dangerous"])

    def test_explicit_recovery_stops_risk_despite_stale_possession_tag(self):
        rows = [event(1, 10, outcome="Incomplete"),
                event(2, 11, team=2, possession=2, kind="Ball Recovery"),
                event(3, 12, team=1, owner=2, possession=2, kind="Ball Recovery"),
                event(4, 13, team=2, possession=2, kind="Shot")]
        result = analyze_events(rows)
        self.assertEqual(len(result["losses"]), 1)
        self.assertFalse(result["losses"][0]["dangerous"])

    def test_missing_possession_and_pattern_warn_without_crashing(self):
        rows = attack()
        del rows[0]["possession"]
        del rows[0]["play_pattern"]
        result = analyze_events(rows)
        self.assertEqual(result["losses"], [])
        self.assertEqual(len(result["warnings"]), 2)

    def test_invalid_parameters_and_structure(self):
        for value in (0, -1, math.inf, math.nan, "10", None, True):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    analyze_events([], window_seconds=value)
                with self.assertRaises(ValueError):
                    analyze_events([], control_gap_seconds=value)
        for rows in (None, {}, [None], [{}], [event(1, 10), event(1, 11)]):
            with self.subTest(rows=rows):
                with self.assertRaises(ValueError):
                    analyze_events(rows)
        for change in ({"timestamp": "not a timestamp"}, {"period": True}, {"type": {}},
                       {"pass": "broken"}, {"team": {"name": "missing id"}}):
            with self.subTest(change=change):
                rows = attack()
                rows[0].update(change)
                with self.assertRaises(ValueError):
                    analyze_events(rows)

    def test_empty_match(self):
        result = analyze_events([])
        self.assertEqual(result["losses"], [])
        self.assertEqual(result["teams"], [])
        self.assertEqual(result["warnings"], [])


if __name__ == "__main__":
    unittest.main()
