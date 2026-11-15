import itertools

import pytest

from app.core import game_config as G
from app.services.resource_service import InvalidDecision, State, apply_decision


def start(**kw):
    base = dict(oxygen_level=70, power_level=75, water_level=65, food_level=65,
                radiation_protection_level=55, score=0, current_day=1, total_days=7,
                mission_status="active", alert_level="calm")
    return State(**{**base, **kw})


def levels(s: State):
    return (s.oxygen_level, s.power_level, s.water_level, s.food_level,
            s.radiation_protection_level)


def test_day_1_build_near_ice():
    new, out = apply_decision(start(), "outpost_setup", "build_near_ice")
    assert levels(new) == (64, 58, 78, 60, 51)
    assert new.score == 17 and new.current_day == 2
    assert out["resource_changes"] == {
        "oxygen_level": -6, "power_level": -17, "water_level": 13, "food_level": -5,
        "radiation_protection_level": -4}


STORM_DAY_3 = dict(oxygen_level=60, power_level=50, water_level=50, food_level=50,
                   radiation_protection_level=40, score=40, current_day=3, alert_level="storm")


def test_ignoring_a_storm_wears_the_shield_down():
    new, out = apply_decision(start(**STORM_DAY_3), "radiation_response", "continue_work")
    assert levels(new) == (54, 45, 45, 49, 7)
    assert new.score == 40 and out["balance_bonus"] is False
    assert out["decision_effects"]["radiation_protection_level"] == -25
    assert "radiation protection is getting low" in out["feedback"]


def test_sheltering_in_the_same_storm():
    new, _ = apply_decision(start(**STORM_DAY_3), "radiation_response", "shelter_in_place")
    assert levels(new) == (51, 37, 45, 45, 42)
    assert new.score == 60


def test_alert_level_multiplies_shield_wear():
    drains = {alert: apply_decision(start(alert_level=alert), "outpost_setup", "build_near_ice")[1]
              ["daily_drain"]["radiation_protection_level"] for alert in ("calm", "watch", "storm")}
    assert drains == {"calm": 4, "watch": 6, "storm": 8}


def test_resource_at_zero_fails_mission():
    new, out = apply_decision(start(current_day=2, power_level=18), "power_allocation", "research_boost")
    assert new.power_level == 0 and new.mission_status == "failed"
    assert out["result"] == "failed" and "power ran out" in out["feedback"]
    assert new.current_day == 2


def test_surviving_last_day_completes_with_bonus():
    new, out = apply_decision(start(current_day=7, score=100), "science_exploration", "send_data_home")
    assert new.mission_status == "completed" and out["result"] == "completed"
    assert new.score == 100 + 8 + 5 + 50


def test_resources_never_exceed_100():
    new, _ = apply_decision(start(current_day=4, oxygen_level=98), "water_system", "make_oxygen_from_water")
    assert new.oxygen_level == 94


@pytest.mark.parametrize("decision_type, option, state, code", [
    ("outpost_setup", "nope", {}, "unknown_decision_or_option"),
    ("nope", "build_near_ice", {}, "unknown_decision_or_option"),
    ("outpost_setup", "research_boost", {}, "unknown_decision_or_option"),
    ("power_allocation", "research_boost", {}, "decision_not_for_this_mission"),
    ("outpost_setup", "build_near_ice", {"current_day": 2}, "decision_not_for_this_mission"),
    ("outpost_setup", "build_near_ice", {"mission_status": "failed"}, "mission_not_active"),
])
def test_invalid_decisions(decision_type, option, state, code):
    with pytest.raises(InvalidDecision, match=code):
        apply_decision(start(**state), decision_type, option)


def test_every_mission_has_three_options_and_no_option_is_free():
    assert G.TOTAL_DAYS == 7
    for mission in G.MISSIONS:
        options = G.DECISIONS[mission["decision_type"]]
        assert len(options) == 3
        for name, spec in options.items():
            costs = [v for k, v in spec["effects"].items() if k != "score" and v < 0]
            assert costs, f"{name} has no cost"


def survival_share(alert: str) -> float:
    options = [list(G.DECISIONS[m["decision_type"]]) for m in G.MISSIONS]
    survived = 0
    for seq in itertools.product(*options):
        s = start(alert_level=alert)
        for mission, option in zip(G.MISSIONS, seq):
            s, _ = apply_decision(s, mission["decision_type"], option)
            if s.mission_status != "active":
                break
        survived += s.mission_status == "completed"
    return survived / 3 ** 7


def test_game_is_winnable_but_not_trivial_and_storms_are_harder():
    calm, watch, storm = (survival_share(a) for a in ("calm", "watch", "storm"))
    assert 0.2 < storm < watch < calm < 0.7
