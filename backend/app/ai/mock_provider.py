import random
import uuid
from typing import List, Dict, Optional, Any
from app.ai.base import (
    BaseVisionProvider, BaseStoryProvider, BaseImageProvider, BaseModerationProvider
)
from app.schemas.photo import HumanDetectionResult, VisionAnalysisOutput
from app.schemas.character import CharacterDNA, SpeechStyle
from app.schemas.story import StoryDiceRoll

class MockVisionProvider(BaseVisionProvider):
    async def detect_human(self, image_bytes: bytes, filename: str = "") -> HumanDetectionResult:
        # Check filename or byte header flags for human signals in test/dev
        lower_name = filename.lower() if filename else ""
        human_indicators = ["human", "person", "selfie", "portrait", "man", "woman", "face", "boy", "girl", "group"]
        
        for ind in human_indicators:
            if ind in lower_name:
                return HumanDetectionResult(
                    is_human_present=True,
                    confidence=0.98,
                    detected_labels=["person", "face", "clothing"]
                )
        
        # Also check for explicit test magic bytes
        if b"TEST_HUMAN_IMAGE" in image_bytes:
            return HumanDetectionResult(
                is_human_present=True,
                confidence=0.99,
                detected_labels=["person"]
            )
            
        return HumanDetectionResult(
            is_human_present=False,
            confidence=0.02,
            detected_labels=["animal", "domestic dog", "collar"]
        )

    async def analyze_non_human(self, image_bytes: bytes) -> VisionAnalysisOutput:
        # Sample non-human outputs
        subjects = [
            ("dog", "animal", "brown street indie", "brown", "sunny street with auto rickshaw", ["red collar", "tar road", "curb"], "overconfident smirk"),
            ("chai glass", "object", "cutting chai tumbler", "amber brown", "hyderabad tea stall", ["cutting glass", "saucer", "kettle"], "steamy wisdom"),
            ("vintage scooter", "vehicle", "bajaj chetak 1996", "sky blue", "narrow gully corner", ["kick pedal", "side mirror", "spare tire"], "exhausted pride"),
            ("cactus", "plant", "desert succulent", "dusty green", "computer desk", ["ceramic pot", "thorns", "sticky note"], "suspicious stare"),
            ("calculator", "gadget", "scientific calculator", "matte grey", "engineering college bench", ["LCD screen", "matrix buttons", "scratch marks"], "existential panic")
        ]
        subj, cat, breed, color, env, objs, expr = random.choice(subjects)
        return VisionAnalysisOutput(
            subject=subj,
            category=cat,
            breed_or_type=breed,
            color=color,
            environment=env,
            visible_objects=objs,
            estimated_expression=expr,
            is_human_present=False
        )

class MockStoryProvider(BaseStoryProvider):
    async def generate_character_dna(self, vision: VisionAnalysisOutput, preferred_language: str = "te-en") -> CharacterDNA:
        subj = vision.subject.lower()
        if "dog" in subj:
            name = "Dogesh Bhai"
            species = "dog"
            archetype = "overconfident_hero"
            secret = "Secretly manages orbital satellite frequencies using barking resonances."
            fear = "High-powered vacuum cleaners and municipal vans."
            occ = "Retired neighborhood detective & Chief Street Strategist."
            origin = "Old City lanes, survived 47 territory disputes."
            abilities = ["Super sonic ear twitch", "360-degree parotta detection", "Instant meme pose"]
            weaknesses = ["Parotta smell", "Belly rubs will leak national secrets"]
        elif "chai" in subj or "glass" in subj:
            name = "Chai Cup Chari"
            species = "cutting chai glass"
            archetype = "old_school_uncle"
            secret = "Has witnessed 12,000 startup pitch fails at 2:00 AM."
            fear = "Dishwasher steam and people drinking sugarless green tea."
            occ = "Philosopher-in-Residence at Irani Cafe."
            origin = "Molded in 1994, never cracked once."
            abilities = ["Infuses boiling motivation", "Instant debate trigger", "Thermal resistance"]
            weaknesses = ["Slippery hands", "Room temperature tea"]
        else:
            name = f"{vision.subject.title()} King"
            species = vision.subject
            archetype = "deadpan_savage"
            secret = "Can decode alien radio frequencies through its micro-vibrations."
            fear = "Being dropped into a recycling bin."
            occ = "Underground Syndicate Advisor."
            origin = "Manufactured in a mystery warehouse."
            abilities = ["Stoic silence", "Extreme durability", "Unflinching gaze"]
            weaknesses = ["Direct rain", "High voltage magnets"]

        return CharacterDNA(
            name=name,
            species_or_object=species,
            personality=["brave", "sarcastic", "curious", "unapologetically lazy"],
            secret=secret,
            fear=fear,
            origin=origin,
            occupation=occ,
            abilities=abilities,
            weaknesses=weaknesses,
            appearance={"color": vision.color, "expression": vision.estimated_expression, "environment": vision.environment},
            comedy_archetype=archetype,
            humor_style=["sarcasm", "absurdity", "deadpan", "mass_roast"],
            speech_style=SpeechStyle(
                language=preferred_language,
                register="naatu",
                slang="naatu",
                code_switching=0.45
            ),
            sarcasm_level=0.88,
            meme_level=0.82,
            dramatic_level=0.91,
            telugu_slang_level=0.78,
            english_mix=0.35,
            punchline_frequency=0.89
        )

    async def generate_story(
        self,
        character_dna: CharacterDNA,
        dice: StoryDiceRoll,
        mode: str = "snaptale",
        language: str = "te-en",
        custom_prompt: Optional[str] = None
    ) -> Dict[str, str]:
        name = character_dna.name
        setting = dice.setting
        goal = dice.goal
        twist = dice.twist
        
        if mode == "snapplus":
            title = f"{name}: The Midnight Incident in {setting}"
            content = (
                f"SETUP: Anni quiet ga unnai anukune sariki, clock 3:00 AM kottindi in {setting}.\n"
                f"MISDIRECTION: {name} thought the mission was simply to {goal.lower()}. Normal ga aithe easy cake walk undedi.\n"
                f"ESCALATION: Sudden ga shadow nunchi black luxury van aagindi. Situation full ga out of control ayipoyindi ra! "
                f"Radio static sound lo weird voice: 'Target located.' {name} chilled down to the spine.\n"
                f"PUNCHLINE: Bro looked at the mysterious enemy and whispered: 'Naa daggaraki raavadaniki petrol rate kooda chuskovaledha bro?'\n"
                f"REACTION: Entire underworld syndicate froze in disbelief.\n"
                f"WHISTLE MOMENT: {name} triggered the secret device, turning the whole {setting} into pure cinematic smoke!"
            )
            punchline = "Bro entered as target... and walked out as the syndicate owner 💀"
        else:
            title = f"{name} and the {setting} Disaster"
            content = (
                f"SETUP: Idi evaroo expect cheyyani scene in {setting}.\n"
                f"CHARACTER: Mana {name} enters with pure mass attitude and unmatched swag.\n"
                f"PROBLEM: The only goal was to {goal.lower()}, but fate had zero respect for personal plans.\n"
                f"CONFLICT: Local security guard thought {name} was an ordinary entity. Pedda mistake mowa!\n"
                f"TWIST: Plot twist enti ante... {twist.lower()}! Antha sudden ga reveal ayindi!\n"
                f"CLIMAX: {name} pulled off the single greatest high-IQ escape move ever recorded.\n"
                f"ENDING: Bro literally cooked the entire universe and walked away without looking back at the blast."
            )
            punchline = "Bro literally cooked himself, yet still won the argument 💀"

        return {"title": title, "content": content, "punchline": punchline}

    async def mutate_story(
        self,
        original_story_content: str,
        character_dna: CharacterDNA,
        mutation_type: str,
        mode: str = "snaptale",
        language: str = "te-en",
        custom_instruction: Optional[str] = None
    ) -> Dict[str, str]:
        name = character_dna.name
        type_titles = {
            "funny": f"{name}: Maximum Comedy Chaos",
            "horror": f"{name}: The Haunted Nightmare",
            "dark": f"{name}: The Dark Underworld",
            "weird": f"{name}: The 4th Dimension Glitch",
            "space": f"{name} Goes to Mars",
            "royal": f"{name}: The Golden Dynasty",
            "mysterious": f"{name} & The Classified Dossier",
            "happy_ending": f"{name}: The Billionaire Retirement",
            "evil_hero": f"{name}: The Villain Origin"
        }
        title = type_titles.get(mutation_type.lower(), f"{name}: {mutation_type.title()} Branch")
        content = (
            f"BRANCH DIVERGENCE [{mutation_type.upper()}]:\n"
            f"Original continuity got split right in the middle of the timeline!\n"
            f"Mana {name} switched into {mutation_type} gear. "
            f"Telugu-English code-switching hits 100%: 'Rey aagu ra... story inka ayipoledhu!'\n"
            f"Now operating with {character_dna.comedy_archetype} instincts, {name} reshaped reality itself."
        )
        punchline = f"Parallel dimension lo kooda mana {name} swag taggede le!"
        return {"title": title, "content": content, "punchline": punchline}

    async def what_if_story(
        self,
        original_story_content: str,
        character_dna: CharacterDNA,
        scenario: str,
        mode: str = "snaptale",
        language: str = "te-en"
    ) -> Dict[str, str]:
        name = character_dna.name
        title = f"What If: {scenario}?"
        content = (
            f"WHAT IF MULTIVERSE BRANCH:\n"
            f"Scenario: '{scenario}'\n\n"
            f"Timeline fractured immediately. Instead of the usual routine, {name} woke up possessing absolute authority.\n"
            f"Bro looked at the new world and said: 'Situation full ga out of control ayipoyindi ra!'\n"
            f"Using abilities ({', '.join(character_dna.abilities[:2])}), {name} proved that whether hero or villain, "
            f"nobody can out-maneuver {name}!"
        )
        punchline = "One What-If thought... and entire multiverse got recalibrated."
        return {"title": title, "content": content, "punchline": punchline}

    async def continue_story(
        self,
        previous_story_content: str,
        character_dna: CharacterDNA,
        direction: Optional[str] = None,
        mode: str = "snaptale",
        language: str = "te-en"
    ) -> Dict[str, str]:
        name = character_dna.name
        title = f"{name}: Chapter Next — The Aftermath"
        content = (
            f"PREVIOUS CONTINUATION:\n"
            f"Continuing immediately after the chaotic climax:\n"
            f"Dust settle ayyaka, {name} got back on feet. "
            f"Direction chosen: {direction or 'Full throttle revenge'}.\n"
            f"'Arey aagu ra... main villain inka scene loki raale!'\n"
            f"{name} mobilized the local universe allies for the grand showdown."
        )
        punchline = "Chapter 1 was just warmup. Real cinema starts now 🔥"
        return {"title": title, "content": content, "punchline": punchline}

    async def chat_response(
        self,
        character_dna: CharacterDNA,
        chat_history: List[Dict[str, str]],
        message: str,
        universe_context: Optional[str] = None,
        is_snapplus: bool = False
    ) -> str:
        name = character_dna.name
        lower_msg = message.lower()
        
        if is_snapplus:
            replies = [
                f"'{message}' antunnavu... Earth lo EMI lu saripoledu ani ikkadiki vacha ra. Direct point ki ra 💀",
                f"Bro, dark hours lo philosophical questions adagaku. Already situation critical ga undi.",
                f"You think this is a game? Mars syndicate already tracking this transmission ra.",
                f"Hahaha, innocent fellow vi la unnavu. Secret cheppalante minimum cutting chai treat ivvali."
            ]
        else:
            replies = [
                f"Arey mowa, '{message}' ante ela respond avvali anukuntunnav? Naatu ga cheptunna, no compromise! 😂",
                f"Earth lo undi nannu question chestunnava? Wait, vacuum cleaner on cheyyaku bro, I yield!",
                f"Bro literally cooked himself with that question 💀 situation full out of control ayipoyindi!",
                f"Nenu {name} ra... street detective! Nee secret motham naku telusu."
            ]
            
        if "who are you" in lower_msg or "name" in lower_msg:
            return f"Nenu {name} — the {character_dna.occupation}. Naa gurinchi teliyakunda chat loki vachava mowa?"
        if "mars" in lower_msg:
            return "Mars ki shift ayya ra... Earth lo ticket rates and house rents tattukoleka Martian citizen ayipoya 💀"
        if "secret" in lower_msg:
            return f"Naa secret teliste tattukolev: {character_dna.secret}"

        return random.choice(replies)

class MockImageProvider(BaseImageProvider):
    async def generate_story_image(
        self,
        character_dna: CharacterDNA,
        story_title: str,
        scene_summary: str,
        mode: str = "snaptale"
    ) -> str:
        # Returns consistent placeholder CDN image for the character's species/object
        subj = character_dna.species_or_object.lower()
        if "dog" in subj:
            return "https://images.unsplash.com/photo-1543466835-00a7907e9de1?auto=format&fit=crop&w=800&q=80"
        elif "cat" in subj:
            return "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?auto=format&fit=crop&w=800&q=80"
        elif "car" in subj or "vehicle" in subj:
            return "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?auto=format&fit=crop&w=800&q=80"
        elif "tea" in subj or "cup" in subj or "glass" in subj:
            return "https://images.unsplash.com/photo-1517256064527-09c73fc73e38?auto=format&fit=crop&w=800&q=80"
        else:
            return "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=800&q=80"

class MockModerationProvider(BaseModerationProvider):
    async def check_content_safety(self, text: str, is_snapplus: bool = False) -> Dict[str, Any]:
        lower = text.lower()
        blocked_words = ["csam", "terrorist", "suicide instruction", "non-consensual sexual"]
        for b in blocked_words:
            if b in lower:
                return {"is_safe": False, "reason": "Severe policy violation detected", "action": "block"}
        return {"is_safe": True, "reason": "Content passed safety review", "action": "allow"}

    async def check_image_safety(self, image_bytes: bytes, is_snapplus: bool = False) -> Dict[str, Any]:
        # Dev/test-only stub. Never used when AI_PROVIDER=gemini; real image bytes
        # are never actually inspected here, so this must not run in production.
        if b"UNSAFE_TEST_IMAGE" in image_bytes:
            return {"is_safe": False, "reason": "Severe policy violation detected in test image", "action": "block"}
        return {"is_safe": True, "reason": "Mock image safety check passed", "action": "allow"}
