# SNAPTALE 📸✨
> **Every Picture Has a Story.**  
> *No humans. Just everything else.*

SnapTale is a complete, runnable, downloadable AI entertainment application that transforms photographs of animals, everyday objects, food, vehicles, gadgets, and non-human things into:
- **Persistent Characters** (with structured Character DNA, secrets, fears, abilities)
- **Cinematic Stories** (Telugu-English "naatu naatu maatalu" code switching, original comedy archetypes)
- **Two Dual Experiences**:
  - **😂 SnapTale**: General audience comedy, absurd humor, and light roasts.
  - **🔞 SnapTale+**: Mature dark comedy, thriller, and horror with age-gating & a 4-digit Argon2id private chat PIN.
- **Story Mutations & What If Branches** (non-destructive branching where original stories remain untouched)
- **Lore Tree** (interactive DAG visualizer of multiverse branches)
- **Multi-Thread Topic Chats** (topic-based conversations preserving character memory and DNA)
- **SnapFacts** (clear reality layer separating verified facts from fictional imagination)

---

## 🚫 The Non-Negotiable Human Image Rule
SnapTale strictly enforces server-side rejection for any photograph containing a human being, face, portrait, or selfie.
- Dog = Accepted ✅
- Chair = Accepted ✅
- Dog + Person = Rejected 🚫
- Response: `🚫 SnapTale can't use photos containing people. Try photographing an animal, object, vehicle, food, or anything else!`
- Temporary file deleted immediately; zero persistence in database.

---

## 🏗️ Architecture & Stack
- **Mobile Application**: Flutter 3.x + Dart (Android APK & iOS ready)
- **Backend API**: FastAPI + Python 3.10 (Modular AI provider abstraction: Gemini, OpenAI, Mock provider)
- **Database**: PostgreSQL on Aiven (asyncpg + SQLAlchemy ORM)
- **Auth & Storage**: Supabase Auth & Storage
- **Web Application**: Next.js 14 (App Router) + React + TypeScript + Tailwind CSS
- **Deployment**: Render (FastAPI Web Service), Vercel (Next.js Web Portal), UptimeRobot (`GET /health`)

---

## 🚀 Quickstart Guide

### 1. Backend Setup
```bash
cd backend
pip install -r requirements.txt
python -m pytest tests/
uvicorn app.main:app --reload --port 8000
```
Visit API Documentation: `http://localhost:8000/docs`  
Health check: `http://localhost:8000/health`

### 2. Next.js Web Frontend
```bash
cd web
npm install
npm run dev
```
Visit Web Showcase: `http://localhost:3000`

### 3. Flutter Mobile Application
```bash
cd mobile/flutter_app
flutter pub get
flutter test
flutter run
```
Build Release Android APK:
```bash
flutter build apk --release
```

### 4. Run All Tests
```bash
./scripts/test_all.bat
```

---

## 📜 License
MIT License.