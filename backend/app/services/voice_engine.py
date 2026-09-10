from typing import Dict, Any

ORIGINAL_ARCHETYPES = [
    "Confused Legend",
    "Deadpan Savage",
    "Overthinking Genius",
    "Overconfident Hero",
    "Victim King",
    "Silent Killer",
    "Cunning Friend",
    "Innocent Idiot",
    "Mass Character",
    "Old-School Uncle",
    "Technical Fellow",
    "Dark Deadpan"
]

def get_archetype_profile(archetype_key: str) -> Dict[str, Any]:
    key = archetype_key.lower().replace(" ", "_")
    profiles = {
        "confused_legend": {
            "title": "Confused Legend",
            "tagline": "Accidentally solved the mystery while searching for his misplaced chappals.",
            "sarcasm": 0.75, "meme": 0.85, "dramatic": 0.80
        },
        "deadpan_savage": {
            "title": "Deadpan Savage",
            "tagline": "Zero facial expressions, 100% emotional damage.",
            "sarcasm": 0.95, "meme": 0.90, "dramatic": 0.40
        },
        "overconfident_hero": {
            "title": "Overconfident Hero",
            "tagline": "Will challenge gravity itself and ask for an apology afterwards.",
            "sarcasm": 0.85, "meme": 0.80, "dramatic": 0.95
        },
        "mass_character": {
            "title": "Mass Character",
            "tagline": "Background score plays automatically whenever he blinks.",
            "sarcasm": 0.70, "meme": 0.88, "dramatic": 0.98
        },
        "old_school_uncle": {
            "title": "Old-School Uncle",
            "tagline": "Compares every intergalactic crisis to how things were done in 1982.",
            "sarcasm": 0.80, "meme": 0.75, "dramatic": 0.85
        }
    }
    return profiles.get(key, {
        "title": archetype_key.title(),
        "tagline": "Original SnapTale comedy personality.",
        "sarcasm": 0.8, "meme": 0.8, "dramatic": 0.8
    })
