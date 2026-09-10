import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import asyncio
from app.core.database import AsyncSessionLocal, engine, Base
from app.models.models import User, Profile, Universe, Character, Story, StoryBranch, Chat, ChatMessage

async def seed():
    print("[*] Seeding SnapTale database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        user = User(id="00000000-0000-0000-0000-000000000001", email="ram@snaptale.app")
        db.add(user)
        await db.flush()

        profile = Profile(
            id=user.id,
            username="ram_explorer",
            display_name="Ram",
            is_snapplus_eligible=True,
            snapplus_enabled=True,
            preferred_language="te-en"
        )
        db.add(profile)

        universe = Universe(
            user_id=user.id,
            name="Ram's Cinematic Multiverse",
            description="Home to Dogesh Bhai, Chai Cup Chari, and Speedy Somanna."
        )
        db.add(universe)
        await db.flush()

        dogesh = Character(
            user_id=user.id,
            universe_id=universe.id,
            name="Dogesh Bhai",
            species_or_object="dog",
            photo_url="https://images.unsplash.com/photo-1543466835-00a7907e9de1?auto=format&fit=crop&w=800&q=80",
            dna={
                "name": "Dogesh Bhai",
                "species_or_object": "dog",
                "personality": ["brave", "sarcastic", "curious", "lazy"],
                "secret": "Secretly manages orbital satellite frequencies using barking resonances.",
                "fear": "High-powered vacuum cleaners and municipal vans.",
                "origin": "Old City lanes, survived 47 territory disputes.",
                "occupation": "Retired neighborhood detective & Chief Street Strategist.",
                "abilities": ["Super sonic ear twitch", "360-degree parotta detection", "Instant meme pose"],
                "weaknesses": ["Parotta smell", "Belly rubs will leak national secrets"],
                "comedy_archetype": "overconfident_hero",
                "humor_style": ["sarcasm", "absurdity", "deadpan", "mass_roast"],
                "speech_style": {"language": "te-en", "register": "naatu", "slang": "naatu", "code_switching": 0.45},
                "sarcasm_level": 0.88,
                "meme_level": 0.82,
                "dramatic_level": 0.91,
                "telugu_slang_level": 0.78,
                "english_mix": 0.35,
                "punchline_frequency": 0.89
            },
            origin_story="Brown dog photographed on Old City street.",
            story_count=2,
            chat_count=1
        )
        db.add(dogesh)
        await db.flush()

        story1 = Story(
            user_id=user.id,
            character_id=dogesh.id,
            universe_id=universe.id,
            title="Dogesh Bhai and the Last Metro",
            content="SETUP: Hyderabad metro late night ticket counter.\nCONFLICT: Machine didn't accept UPI!\nTWIST: Dogesh Bhai secretly owned the transport authority.",
            punchline="Earth lo EMI lu saripoledu ra... Mars ki shift ayya",
            experience_mode="snaptale",
            language="te-en",
            generated_image_url="https://images.unsplash.com/photo-1543466835-00a7907e9de1?auto=format&fit=crop&w=800&q=80",
            privacy="public",
            moderation_status="approved",
            like_count=142
        )
        db.add(story1)
        await db.flush()

        story2 = Story(
            user_id=user.id,
            character_id=dogesh.id,
            universe_id=universe.id,
            title="Dogesh Bhai Goes to Mars",
            content="SETUP: Red Planet rover base.\nCONFLICT: Alien dust storm.\nTWIST: Aliens wanted Dogesh Bhai's street detective consulting.",
            punchline="Ticket price chusaka... I became Martian citizen",
            experience_mode="snaptale",
            language="te-en",
            generated_image_url="https://images.unsplash.com/photo-1543466835-00a7907e9de1?auto=format&fit=crop&w=800&q=80",
            privacy="public",
            moderation_status="approved",
            like_count=312
        )
        db.add(story2)
        await db.flush()

        branch = StoryBranch(
            parent_story_id=story1.id,
            child_story_id=story2.id,
            mutation_type="space",
            mutation_prompt="Send to Space",
            created_by=user.id
        )
        db.add(branch)

        chat = Chat(
            user_id=user.id,
            character_id=dogesh.id,
            universe_id=universe.id,
            title="Mars Mission",
            topic="mars",
            is_protected=False,
            language="te-en"
        )
        db.add(chat)
        await db.flush()

        db.add(ChatMessage(
            chat_id=chat.id,
            sender_type="user",
            content="Bro, why did you go to Mars?"
        ))
        db.add(ChatMessage(
            chat_id=chat.id,
            sender_type="character",
            content="Earth lo EMI lu saripoledu ra... Mars ki shift ayya"
        ))

        await db.commit()
    print("[+] SnapTale seed completed successfully!")

if __name__ == "__main__":
    asyncio.run(seed())