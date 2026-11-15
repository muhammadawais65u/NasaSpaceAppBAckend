from uuid import uuid4

import httpx

from app.core import game_config as G
from tests.conftest import auth, donki_time

MISSIONS = "/api/v1/missions"
SAFE = ["build_on_sunny_ridge", "battery_save", "shelter_in_place", "ration_water",
        "seal_off_module", "eat_packaged_food", "send_data_home"]
POWER_HUNGRY = ["build_near_ice", "research_boost", "reinforce_shield", "recycle_water",
                "patch_from_inside"]


def decide(client, mission_id, option, day=1, player="alice", **extra):
    body = {"decision_type": G.MISSIONS[day - 1]["decision_type"], "selected_option": option,
            "request_id": str(uuid4()), **extra}
    return client.post(f"{MISSIONS}/{mission_id}/decision", json=body, headers=auth(player))


def levels(m):
    return (m["oxygen_level"], m["power_level"], m["water_level"], m["food_level"],
            m["radiation_protection_level"])


def test_health_and_config_need_no_token(client):
    assert client.get("/health?deep=true").json()["status"] == "ok"
    cfg = client.get("/api/v1/game/config").json()
    assert cfg["is_game_design"] is True and cfg["total_days"] == 7
    assert [m["day"] for m in cfg["missions"]] == [1, 2, 3, 4, 5, 6, 7]
    assert all(len(cfg["decisions"][m["decision_type"]]) == 3 for m in cfg["missions"])


def test_token_required(client):
    r = client.get(MISSIONS)
    assert r.status_code == 401 and r.json()["error"]["code"] == "missing_token"


def test_create_decide_and_restore(client):
    m = client.post(MISSIONS, headers=auth()).json()
    assert levels(m) == (70, 75, 65, 65, 55)
    assert (m["current_day"], m["score"], m["version"], m["alert_level"]) == (1, 0, 1, "calm")
    assert "user_id" not in m

    r = decide(client, m["id"], "build_near_ice", expected_version=1).json()
    assert r["replayed"] is False and r["outcome"]["score_change"] == 17
    saved = r["mission"]
    assert levels(saved) == (64, 58, 78, 60, 51)
    assert (saved["current_day"], saved["version"], saved["score"]) == (2, 2, 17)

    restored = client.get(f"{MISSIONS}?status=active&limit=1", headers=auth()).json()
    assert restored["count"] == 1 and restored["items"][0] == saved
    history = client.get(f"{MISSIONS}/{m['id']}/history", headers=auth()).json()["items"]
    assert [h["selected_option"] for h in history] == ["build_near_ice"]


def test_second_active_mission_is_rejected(client):
    m = client.post(MISSIONS, headers=auth()).json()
    r = client.post(MISSIONS, headers=auth())
    assert r.status_code == 409
    assert r.json()["error"] == {"code": "active_mission_exists",
                                 "message": "You already have an active mission.",
                                 "details": {"mission_id": m["id"]}}


def test_same_request_id_is_replayed_not_applied_twice(client):
    m = client.post(MISSIONS, headers=auth()).json()
    body = {"decision_type": "outpost_setup", "selected_option": "bury_the_habitat",
            "request_id": str(uuid4())}
    first = client.post(f"{MISSIONS}/{m['id']}/decision", json=body, headers=auth()).json()
    second = client.post(f"{MISSIONS}/{m['id']}/decision", json=body, headers=auth()).json()
    assert second["replayed"] is True
    assert second["mission"] == first["mission"] and second["outcome"] == first["outcome"]
    assert len(client.get(f"{MISSIONS}/{m['id']}/history", headers=auth()).json()["items"]) == 1


def test_stale_version_unknown_option_and_wrong_day(client):
    m = client.post(MISSIONS, headers=auth()).json()
    decide(client, m["id"], SAFE[0])
    stale = decide(client, m["id"], SAFE[1], day=2, expected_version=1)
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "version_conflict"
    bad = decide(client, m["id"], "teleport_home", day=2)
    assert bad.status_code == 400 and bad.json()["error"]["code"] == "unknown_decision_or_option"
    wrong_day = decide(client, m["id"], SAFE[0], day=1)
    assert wrong_day.status_code == 400
    assert wrong_day.json()["error"]["code"] == "decision_not_for_this_mission"
    assert client.get(f"{MISSIONS}/{m['id']}", headers=auth()).json()["version"] == 2


def test_other_players_mission_looks_missing(client):
    m = client.post(MISSIONS, headers=auth("alice")).json()
    for r in (client.get(f"{MISSIONS}/{m['id']}", headers=auth("bob")),
              client.get(f"{MISSIONS}/{m['id']}/history", headers=auth("bob")),
              decide(client, m["id"], SAFE[0], player="bob")):
        assert r.status_code == 404 and r.json()["error"]["code"] == "mission_not_found"
    assert client.get(MISSIONS, headers=auth("bob")).json()["count"] == 0
    assert client.get(f"{MISSIONS}/{m['id']}", headers=auth("alice")).json()["version"] == 1


def test_failed_mission_is_locked_and_new_one_can_start(client):
    m = client.post(MISSIONS, headers=auth()).json()
    for day, option in enumerate(POWER_HUNGRY, 1):
        last = decide(client, m["id"], option, day=day).json()
    assert last["outcome"]["result"] == "failed" and last["mission"]["power_level"] == 0
    again = decide(client, m["id"], SAFE[4], day=5)
    assert again.status_code == 409 and again.json()["error"]["code"] == "mission_not_active"
    assert client.post(MISSIONS, headers=auth()).status_code == 201


def test_full_mission_completes(client):
    m = client.post(MISSIONS, headers=auth()).json()
    for day, option in enumerate(SAFE, 1):
        last = decide(client, m["id"], option, day=day).json()
    assert last["outcome"]["result"] == "completed"
    assert last["mission"]["mission_status"] == "completed" and last["mission"]["current_day"] == 7


def test_validation_error_shape(client):
    m = client.post(MISSIONS, headers=auth()).json()
    r = client.post(f"{MISSIONS}/{m['id']}/decision", json={"decision_type": "x"}, headers=auth())
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"


FLARE = {"flrID": "FLR-1", "beginTime": None, "peakTime": "p", "classType": "M2.1",
         "sourceLocation": "N10E20", "link": "https://example.test/flr"}
CME = {"activityID": "CME-1", "startTime": None, "sourceLocation": "", "note": "n",
       "cmeAnalyses": [{"isMostAccurate": True, "speed": 245.0}], "link": "https://example.test/cme"}
STORM = {"gstID": "GST-1", "startTime": None, "link": "https://example.test/gst",
         "allKpIndex": [{"kpIndex": 5.67}, {"kpIndex": 6.0}]}


def test_space_weather_live_events_and_storm_alert(client, donki):
    donki["FLR"] = [{**FLARE, "beginTime": donki_time(20)}, {"flrID": "broken"}]
    donki["CME"] = [{**CME, "startTime": donki_time(3)}]
    donki["GST"] = [{**STORM, "startTime": donki_time(2)}]
    data = client.get("/api/v1/nasa/space-weather", headers=auth()).json()
    assert data["data_status"] == "live"
    assert [e["external_event_id"] for e in data["events"]] == ["GST-1", "CME-1", "FLR-1"]
    storm, cme, flare = data["events"]
    assert storm["summary"]["details"] == {"max_kp_index": 6.0}
    assert cme["summary"]["details"]["speed_km_s"] == 245.0
    assert flare["summary"]["title"] == "Solar flare, class M2.1"
    scenario = data["game_scenario"]
    assert scenario["alert_level"] == "storm" and scenario["is_simulation"] is True
    assert scenario["basis_event_id"] == storm["id"]

    mission = client.post(MISSIONS, headers=auth()).json()
    assert mission["alert_level"] == "storm" and mission["scenario_event_id"] == storm["id"]


def test_old_events_do_not_raise_an_alert(client, donki):
    donki["GST"] = [{**STORM, "startTime": donki_time(10)}]
    donki["FLR"] = [{**FLARE, "classType": "C3.0", "beginTime": donki_time(1)}]
    data = client.get("/api/v1/nasa/space-weather", headers=auth()).json()
    assert len(data["events"]) == 2 and data["game_scenario"]["alert_level"] == "calm"
    assert data["game_scenario"]["basis_event_id"] is None


def test_recent_m_flare_is_a_watch(client, donki):
    donki["FLR"] = [{**FLARE, "beginTime": donki_time(1)}]
    data = client.get("/api/v1/nasa/space-weather?days=7", headers=auth()).json()
    assert data["game_scenario"]["alert_level"] == "watch"


def test_nasa_outage_is_reported_honestly(client, donki):
    for t in donki:
        donki[t] = httpx.ConnectError("down")
    data = client.get("/api/v1/nasa/space-weather", headers=auth()).json()
    assert data["data_status"] == "unavailable" and data["events"] == []
    assert data["game_scenario"]["alert_level"] == "calm"
    assert client.post(MISSIONS, headers=auth()).json()["alert_level"] == "calm"


def test_one_failing_type_keeps_the_others_live(client, donki):
    donki["FLR"] = httpx.ConnectError("down")
    donki["CME"] = [{**CME, "startTime": donki_time(1)}]
    data = client.get("/api/v1/nasa/space-weather", headers=auth()).json()
    assert data["data_status"] == "live"
    assert data["type_status"] == {"FLR": "unavailable", "CME": "live", "GST": "live"}


def test_stored_events_are_served_as_cached_when_nasa_goes_down(client, donki):
    from app.services import nasa_service as nasa
    donki["CME"] = [{**CME, "startTime": donki_time(1)}]
    assert client.get("/api/v1/nasa/space-weather", headers=auth()).json()["data_status"] == "live"
    nasa._synced.clear()
    for t in donki:
        donki[t] = httpx.ConnectError("down")
    data = client.get("/api/v1/nasa/space-weather", headers=auth()).json()
    assert data["data_status"] == "cached" and len(data["events"]) == 1


def test_guest_sign_in_is_not_offered_in_local_mode(client):
    r = client.post("/api/v1/auth/guest")
    assert r.status_code == 404 and r.json()["error"]["code"] == "guest_sign_in_unavailable"
