"""GAME-DESIGN PARAMETERS. Chosen for gameplay, NOT NASA measurements."""
RESOURCE_MIN, RESOURCE_MAX = 0, 100
START = {"oxygen_level": 80, "power_level": 80, "radiation_protection_level": 60}
TOTAL_DAYS = 7
DAILY_DRAIN = {"oxygen_level": 6, "power_level": 5, "radiation_protection_level": 4}
ALERT_RADIATION_MULTIPLIER = {"calm": 1.0, "watch": 1.5, "storm": 2.0}
BALANCE_THRESHOLD, BALANCE_BONUS, COMPLETION_BONUS = 30, 5, 50
STORM_CONTINUE_WORK = {"radiation_protection_level": -10, "score": -10}
RESOURCES = ("oxygen_level", "power_level", "radiation_protection_level")
LABEL = {"oxygen_level": "oxygen", "power_level": "power",
         "radiation_protection_level": "radiation protection"}


def fx(o=0, p=0, r=0, s=0):
    return {"oxygen_level": o, "power_level": p,
            "radiation_protection_level": r, "score": s}


DECISIONS = {
    "power_allocation": {
        "research_boost": {"label": "Boost science research", "effects": fx(-2, -15, 0, 20),
            "lesson": "Research earns big points, but the extra power it uses cannot also run life support."},
        "life_support_priority": {"label": "Prioritise life support", "effects": fx(10, -8, 0, 10),
            "lesson": "Sending power to the air system keeps the crew breathing, but science waits."},
        "battery_save": {"label": "Save battery power", "effects": fx(-3, 10, 0, 5),
            "lesson": "Doing less saves energy now, but the crew still uses oxygen while they wait."},
    },
    "radiation_response": {
        "shelter_in_place": {"label": "Shelter in the storm room", "effects": fx(-3, -8, 10, 15),
            "lesson": "Taking shelter protects the crew and shield, but costs power and a little air."},
        "reinforce_shield": {"label": "Reinforce the shield", "effects": fx(0, -12, 20, 12),
            "lesson": "A stronger shield is the best protection, but it takes a lot of power."},
        "continue_work": {"label": "Keep working outside", "effects": fx(0, 0, -15, 10),
            "lesson": "Working on keeps the mission moving, but it wears down your protection."},
    },
    "life_support": {
        "run_oxygen_generator": {"label": "Run the oxygen generator", "effects": fx(15, -10, 0, 12),
            "lesson": "Making lots of oxygen is great, but the generator is a power hog."},
        "recycle_air": {"label": "Recycle the air", "effects": fx(6, -3, 0, 6),
            "lesson": "Recycling air is gentle on power but gives a smaller boost."},
        "conserve_oxygen": {"label": "Conserve oxygen", "effects": fx(3, 0, 0, 3),
            "lesson": "Resting quietly helps a little and costs nothing, but earns few points."},
    },
}
