from dataclasses import dataclass, replace

from app.core import game_config as G


class InvalidDecision(ValueError):
    pass


@dataclass(frozen=True)
class State:
    oxygen_level: int
    power_level: int
    water_level: int
    food_level: int
    radiation_protection_level: int
    score: int
    current_day: int
    total_days: int
    mission_status: str
    alert_level: str


def clamp(v: int) -> int:
    return max(G.RESOURCE_MIN, min(G.RESOURCE_MAX, v))


def apply_decision(state: State, decision_type: str, option: str):
    """Pure function: (old state, choice) -> (new state, outcome)."""
    if state.mission_status != "active":
        raise InvalidDecision("mission_not_active")
    spec = G.DECISIONS.get(decision_type, {}).get(option)
    if spec is None:
        raise InvalidDecision("unknown_decision_or_option")
    if decision_type != G.MISSIONS[state.current_day - 1]["decision_type"]:
        raise InvalidDecision("decision_not_for_this_mission")

    vals = {r: getattr(state, r) for r in G.RESOURCES}
    score = state.score
    fx = dict(spec["effects"])
    if option == "continue_work" and state.alert_level == "storm":
        for k, v in G.STORM_CONTINUE_WORK.items():
            fx[k] = fx.get(k, 0) + v

    for r in G.RESOURCES:
        vals[r] = clamp(vals[r] + fx[r])
    score += fx["score"]

    mult = G.ALERT_RADIATION_MULTIPLIER[state.alert_level]
    drain = dict(G.DAILY_DRAIN)
    drain["radiation_protection_level"] = int(round(drain["radiation_protection_level"] * mult))
    for r in G.RESOURCES:
        vals[r] = clamp(vals[r] - drain[r])

    balanced = all(v >= G.BALANCE_THRESHOLD for v in vals.values())
    if balanced:
        score += G.BALANCE_BONUS
    score = max(0, score)

    empty = [r for r in G.RESOURCES if vals[r] <= 0]
    day_played = state.current_day
    if empty:
        status, day = "failed", day_played
    elif day_played >= state.total_days:
        status, day = "completed", day_played
        score += G.COMPLETION_BONUS
    else:
        status, day = "active", day_played + 1

    new = replace(state, **vals, score=score, current_day=day, mission_status=status)
    outcome = {
        "decision_effects": fx, "daily_drain": drain, "balance_bonus": balanced,
        "resource_changes": {r: vals[r] - getattr(state, r) for r in G.RESOURCES},
        "score_change": score - state.score,
        "day_played": day_played,
        "result": None if status == "active" else status,
        "feedback": build_feedback(spec, new, empty),
    }
    return new, outcome


def build_feedback(spec, new: State, empty: list) -> str:
    if new.mission_status == "failed":
        return f"Mission over: {G.LABEL[empty[0]]} ran out. Balance all your systems next time."
    if new.mission_status == "completed":
        return f"Mission complete! You kept every system running for {new.total_days} days."
    lowest = min(G.RESOURCES, key=lambda r: getattr(new, r))
    msg = spec["lesson"]
    if getattr(new, lowest) < G.BALANCE_THRESHOLD:
        msg += f" Careful: {G.LABEL[lowest]} is getting low."
    return msg
