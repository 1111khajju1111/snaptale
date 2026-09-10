import random
from app.schemas.story import StoryDiceRoll

GENRES = [
    "Comedy", "Adventure", "Mystery", "Fantasy", "Sci-Fi",
    "Horror", "Drama", "Absurd", "Dark Comedy", "Thriller"
]

SETTINGS = [
    "Mars", "Ancient Rome", "Underwater City", "Haunted Castle",
    "Future Earth", "Jungle", "Moon", "Village", "Laboratory", "Alternate Universe"
]

GOALS = [
    "Save the world", "Find treasure", "Escape", "Solve mystery",
    "Become king", "Find a friend", "Stop invasion", "Survive"
]

CONFLICTS = [
    "Security guard refuses entry", "Rocket out of fuel", "Gravity reversed",
    "Misunderstood ancient prophecy", "Vacuum cleaner awakened", "Wifi password lost"
]

TWISTS = [
    "Hero is villain", "Villain helps hero", "Simulation", "Time loop",
    "Secret identity", "Alternate self", "Everything was a dream"
]

def roll_story_dice(chaos_mode: bool = False) -> StoryDiceRoll:
    genre = random.choice(GENRES)
    setting = random.choice(SETTINGS)
    goal = random.choice(GOALS)
    conflict = random.choice(CONFLICTS)
    twist = random.choice(TWISTS)
    
    if chaos_mode:
        # Chaos mode blends unexpected mashups
        genre = f"{random.choice(GENRES)} x {random.choice(GENRES)}"
        setting = f"{random.choice(SETTINGS)} in a parallel realm"

    return StoryDiceRoll(
        genre=genre,
        setting=setting,
        goal=goal,
        conflict=conflict,
        twist=twist,
        chaos_mode=chaos_mode
    )
