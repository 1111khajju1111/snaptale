# SnapTale Architecture Specification

## 1. System Overview
SnapTale turns photographs of animals and everyday non-human objects into persistent characters, unexpected stories, alternate realities, and interconnected personal universes.

**Core Philosophy**: "No humans. Just everything else."

### Core Pipeline
```
PHOTO 
  ↓ 
FILE VALIDATION 
  ↓ 
SERVER-SIDE HUMAN DETECTION 
  ├── HUMAN DETECTED → REJECT + UNLINK TEMP FILE + NO PERSISTENCE
  └── NON-HUMAN
        ↓
      AI VISION (Attributes, Expression, Environment)
        ↓
      CHARACTER ENGINE (DNA, Personality, Archetypes)
        ↓
      STORY DICE (Genre, Setting, Goal, Conflict, Twist)
        ↓
      VOICE ENGINE (English, Telugu, Telugu-English Naatu Maatalu)
        ↓
      STORY ENGINE (SnapTale Comedy vs SnapTale+ Mature Storytelling)
        ↓
      OUTPUT MODERATION
        ↓
      IMAGE ENGINE (1 generated image per story)
        ↓
      SAVE & SHARE (PostgreSQL + Object Storage)
```

## 2. Experiences
- **SnapTale (General Audience)**: Sarcastic, meme-style, absurd, chaotic, cinematic, light roast.
  Structure: SETUP → CHARACTER → PROBLEM → CONFLICT → TWIST → CLIMAX → ENDING.
- **SnapTale+ (Mature)**: Dark comedy, savage humor, horror, thriller, psychological themes, stronger language.
  Structure: SETUP → MISDIRECTION → ESCALATION → PUNCHLINE → REACTION → WHISTLE MOMENT.
  Strict age eligibility gating and 4-digit PIN lock for private chats.

## 3. Persistent Character DNA
Each character maintains a permanent identity across all branches, mutations, and chat threads:
- Name, species, origin, occupation, abilities, weaknesses, fear, secret.
- Comedy archetype, humor style, speech style, code-switching ratio, slang register.
