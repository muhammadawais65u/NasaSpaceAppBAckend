"""GAME-DESIGN PARAMETERS. Chosen for gameplay, NOT NASA measurements."""

RESOURCE_MIN, RESOURCE_MAX = 0, 100
RESOURCES = ("oxygen_level", "power_level", "water_level", "food_level",
             "radiation_protection_level")
LABEL = {"oxygen_level": "oxygen", "power_level": "power", "water_level": "water",
         "food_level": "food", "radiation_protection_level": "radiation protection"}

START = {"oxygen_level": 70, "power_level": 75, "water_level": 65, "food_level": 65,
         "radiation_protection_level": 55}
DAILY_DRAIN = {"oxygen_level": 6, "power_level": 5, "water_level": 5, "food_level": 5,
               "radiation_protection_level": 4}
ALERT_RADIATION_MULTIPLIER = {"calm": 1.0, "watch": 1.5, "storm": 2.0}
BALANCE_THRESHOLD, BALANCE_BONUS, COMPLETION_BONUS = 30, 5, 50
STORM_CONTINUE_WORK = {"radiation_protection_level": -10, "score": -10}


def fx(o=0, p=0, w=0, f=0, r=0, s=0):
    return {"oxygen_level": o, "power_level": p, "water_level": w, "food_level": f,
            "radiation_protection_level": r, "score": s}


DECISIONS = {
    "outpost_setup": {
        "build_near_ice": {
            "label": "Build near the ice crater", "effects": fx(w=18, p=-12, s=12),
            "lesson": "Ice can be melted into water, but the crater is shady, so solar panels make less power there."},
        "build_on_sunny_ridge": {
            "label": "Build on the sunny ridge", "effects": fx(p=15, w=-10, s=12),
            "lesson": "Lots of sunlight means lots of power, but the water ice is far away."},
        "bury_the_habitat": {
            "label": "Cover the habitat with Moon soil", "effects": fx(r=18, p=-10, o=-4, s=15),
            "lesson": "A thick layer of Moon soil blocks radiation, but digging uses a lot of energy and air."},
    },
    "power_allocation": {
        "research_boost": {
            "label": "Boost science research", "effects": fx(o=-2, p=-15, s=20),
            "lesson": "Research earns big points, but the extra power it uses cannot also run life support."},
        "life_support_priority": {
            "label": "Prioritise life support", "effects": fx(o=10, p=-8, s=10),
            "lesson": "Sending power to the air system keeps the crew breathing, but science waits."},
        "battery_save": {
            "label": "Save battery power", "effects": fx(o=-3, p=12, f=-3, s=5),
            "lesson": "Doing less saves energy now, but the crew still uses air and food while they wait."},
    },
    "radiation_response": {
        "shelter_in_place": {
            "label": "Shelter in the storm room", "effects": fx(o=-3, p=-8, r=10, s=15),
            "lesson": "Taking shelter protects the crew and shield, but costs power and a little air."},
        "reinforce_shield": {
            "label": "Reinforce the shield", "effects": fx(p=-12, r=20, s=12),
            "lesson": "A stronger shield is the best protection, but it takes a lot of power."},
        "continue_work": {
            "label": "Keep working outside", "effects": fx(r=-15, f=4, s=10),
            "lesson": "Working on keeps the mission moving, but it wears down your protection."},
    },
    "water_system": {
        "recycle_water": {
            "label": "Recycle every drop", "effects": fx(w=16, p=-10, s=12),
            "lesson": "Astronauts clean and reuse almost all their water, but the recycling machine needs power."},
        "make_oxygen_from_water": {
            "label": "Turn water into oxygen", "effects": fx(o=16, w=-12, p=-5, s=12),
            "lesson": "Electricity can split water into oxygen to breathe, but that uses up water and power."},
        "ration_water": {
            "label": "Ration the water", "effects": fx(w=6, f=-6, s=4),
            "lesson": "Using less water makes it last longer, but the plants and crew get less than they need."},
    },
    "emergency_response": {
        "patch_from_inside": {
            "label": "Patch the leak from inside", "effects": fx(o=-8, p=-8, s=15),
            "lesson": "A quick patch stops the leak, but some air escapes while you work."},
        "spacewalk_repair": {
            "label": "Go outside to repair it", "effects": fx(o=-3, p=-5, r=-12, s=20),
            "lesson": "Fixing it from outside is the strongest repair, but outside there is no shelter from radiation."},
        "seal_off_module": {
            "label": "Seal off the damaged room", "effects": fx(o=-2, w=-8, f=-10, s=8),
            "lesson": "Closing the room is safe and fast, but the supplies stored inside are lost."},
    },
    "food_production": {
        "grow_greenhouse": {
            "label": "Grow vegetables in the greenhouse", "effects": fx(f=18, w=-12, p=-8, s=15),
            "lesson": "Fresh food is great for the crew, but plants need lots of water and light."},
        "grow_microgreens": {
            "label": "Grow fast baby greens", "effects": fx(f=8, w=-5, s=8),
            "lesson": "Small plants grow quickly with little water, but they make only a little food."},
        "eat_packaged_food": {
            "label": "Eat the packaged meals", "effects": fx(f=-6, p=3, s=4),
            "lesson": "Packaged meals need no water or light, but every pack eaten is one less in storage."},
    },
    "science_exploration": {
        "long_rover_trip": {
            "label": "Drive the rover to a far crater", "effects": fx(o=-8, p=-15, r=-8, s=30),
            "lesson": "Far-away places hold the best discoveries, but the trip uses air, power and time outside the shield."},
        "collect_nearby": {
            "label": "Collect rocks near the base", "effects": fx(o=-4, p=-6, s=15),
            "lesson": "Staying close is safer and cheaper, but you find fewer new things."},
        "send_data_home": {
            "label": "Send your data to Earth", "effects": fx(p=-4, s=8),
            "lesson": "Sharing results needs only a little power, but no new samples are collected."},
    },
}

MISSIONS = [
    {"title": "Establish Outpost", "decision_type": "outpost_setup",
     "description": "Build your Moon base and make it ready for astronauts!",
     "scenario": "The lander has touched down. Where and how should we build the base?",
     "objectives": ["Find a good location", "Build the habitat", "Install oxygen and power"]},
    {"title": "Power Management", "decision_type": "power_allocation",
     "description": "Keep your base powered for a successful mission!",
     "scenario": "The solar panels are working. Where should today's power go?",
     "objectives": ["Activate solar panels", "Store energy in batteries", "Manage power usage"]},
    {"title": "Radiation Protection", "decision_type": "radiation_response",
     "description": "The Sun can send out bursts of radiation. Keep your crew safe!",
     "scenario": "Mission Control is watching the Sun. How will the crew spend the day?",
     "objectives": ["Monitor radiation", "Activate shield", "Move crew to shelter"]},
    {"title": "Water & Life Support", "decision_type": "water_system",
     "description": "Keep water and oxygen levels stable!",
     "scenario": "The life-support system needs a plan for the water tanks.",
     "objectives": ["Activate water recycling", "Check oxygen levels", "Fix air filtration"]},
    {"title": "Final Emergency", "decision_type": "emergency_response",
     "description": "Handle the emergency and save your crew!",
     "scenario": "Alarm! A tiny space rock has made a hole and air is leaking out.",
     "objectives": ["Fix the critical system", "Restore oxygen", "Survive the crisis"]},
    {"title": "Food Production", "decision_type": "food_production",
     "description": "Grow food to keep your crew healthy!",
     "scenario": "The crew is hungry. How should we feed everyone?",
     "objectives": ["Build a greenhouse", "Grow vegetables", "Harvest food"]},
    {"title": "Scientific Exploration", "decision_type": "science_exploration",
     "description": "Explore the Moon and complete research!",
     "scenario": "Last day! How should the crew finish their science work?",
     "objectives": ["Explore craters", "Collect samples", "Send data to Earth"]},
]
TOTAL_DAYS = len(MISSIONS)
