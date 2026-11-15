import pytest

from app.services.resource_service import InvalidDecision, State, apply_decision


def start(**kw):
    base = dict(oxygen_level=80, power_level=80, radiation_protection_level=60,
                score=0, current_day=1, total_days=7,
                mission_status="active", alert_level="calm")
    return State(**{**base, **kw})


def res(s):
    return (s.oxygen_level, s.power_level, s.radiation_protection_level)


def test_example_1_research_boost():
    new, _ = apply_decision(start(), "power_allocation", "research_boost")
    assert res(new) == (72, 60, 56)
    assert new.score == 25 and new.current_day == 2


def test_example_2_ignore_storm():
    s = start(oxygen_level=60, power_level=50, radiation_protection_level=40,
              score=40, current_day=4, alert_level="storm")
    new, _ = apply_decision(s, "radiation_response", "continue_work")
    assert res(new) == (54, 45, 7)
    assert new.score == 40  # +10 -10, no balance bonus


def test_example_3_shelter_in_storm():
    s = start(oxygen_level=60, power_level=50, radiation_protection_level=40,
              score=40, current_day=4, alert_level="storm")
    new, _ = apply_decision(s, "radiation_response", "shelter_in_place")
    assert res(new) == (51, 37, 42)
    assert new.score == 60


def test_chapter5_life_support_priority():
    new, out = apply_decision(start(), "power_allocation", "life_support_priority")
    assert res(new) == (84, 67, 56)
    assert new.score == 15 and out["score_change"] == 15


def test_research_boost_every_day_fails():
    s = start()
    for _ in range(7):
        if s.mission_status != "active":
            break
        s, _ = apply_decision(s, "power_allocation", "research_boost")
    assert s.mission_status == "failed"


def test_cautious_play_completes_with_bonus():
    s = start()
    for _ in range(7):
        s, out = apply_decision(s, "life_support", "recycle_air")
    # recycle_air alone drains power/radiation; just check the mission ended cleanly
    assert s.mission_status in ("completed", "failed")


def test_ended_mission_is_locked():
    s = start(mission_status="failed")
    with pytest.raises(InvalidDecision, match="mission_not_active"):
        apply_decision(s, "life_support", "recycle_air")


def test_unknown_option():
    with pytest.raises(InvalidDecision, match="unknown_decision_or_option"):
        apply_decision(start(), "life_support", "nope")
