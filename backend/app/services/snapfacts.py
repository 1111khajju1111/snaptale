from typing import Dict, Any, List
from app.schemas.snapfacts import SnapFactsResponse, SnapFactItem

CURATED_FACTS: Dict[str, List[str]] = {
    "dog": [
        "Dogs possess up to 300 million olfactory receptors in their noses, compared to about 6 million in humans.",
        "A dog's sense of smell is roughly 10,000 to 100,000 times more acute than a human's.",
        "Domestic dogs were the first animals to be domesticated by hunter-gatherers over 15,000 years ago."
    ],
    "cat": [
        "Cats have 32 muscles in each ear, allowing them to rotate their ears independently 180 degrees.",
        "A cat can jump up to six times its own height in a single bound.",
        "Cats spend about 70% of their lives sleeping and 15% grooming."
    ],
    "chai glass": [
        "The iconic Indian 'cutting chai glass' originated in Irani cafes of Mumbai and Hyderabad in the early 20th century.",
        "Cutting chai refers to half a cup of strongly brewed tea with milk and cardamom, designed for quick refreshing sips.",
        "The sturdy fluted glass design was engineered to withstand high temperatures and rapid hand-washing."
    ],
    "vintage scooter": [
        "Classic two-stroke geared scooters such as the Bajaj Chetak were introduced in India in 1972 and remained popular for over 30 years.",
        "The Chetak was named after the legendary stallion of Rajput ruler Maharana Pratap.",
        "In the 1980s, waiting lists for purchasing a brand-new Chetak scooter often exceeded 5 to 10 years."
    ],
    "cactus": [
        "Cacti are native to the Americas and store moisture in their thick, fleshy stems to survive prolonged droughts.",
        "Spines on a cactus are actually modified leaves that reduce water loss and protect from herbivores.",
        "Some saguaro cacti can live for over 200 years and grow taller than 40 feet."
    ]
}

def get_snapfacts_for_subject(subject: str) -> SnapFactsResponse:
    key = subject.lower().strip()
    matched_facts = []
    for k, facts in CURATED_FACTS.items():
        if k in key or key in k:
            matched_facts = facts
            break
    if not matched_facts:
        matched_facts = [
            f"{subject.title()} is a fascinating non-human subject with unique physical and material properties.",
            "In everyday life, inanimate objects and creatures experience physics and time in ways entirely distinct from human perception."
        ]

    fact_items = [
        SnapFactItem(category="Real-World Science / History", fact=f)
        for f in matched_facts
    ]
    return SnapFactsResponse(
        subject=subject,
        reality_facts=fact_items,
        fictional_comparison=f"SnapFacts shows the verified reality of {subject}, while SnapTale gives it hilarious fictional memories!",
        label_reality="🔵 REALITY — SnapFacts",
        label_imagination="🟣 IMAGINATION — SnapTale"
    )
